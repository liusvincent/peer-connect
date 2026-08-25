from __future__ import annotations

from aiortc.contrib.media import MediaRelay, MediaBlackhole
from aiortc import MediaStreamTrack

from typing import Callable, Awaitable
from dataclasses import dataclass
from enum import StrEnum
from uuid import uuid4
import asyncio


class RoomError(Exception):
    code = "room-error"

class RoomNotFound(RoomError):
    code = "room-not-found"

class ParticipantAlreadyInRoom(RoomError):
    code = "participant-already-in-room"  

class ParticipantAlreadyJoined(RoomError):
    code = "participant-already-joined"

class ParticipantNotFound(RoomError):
    code = "participant-not-found" 


class Role(StrEnum):
    HOST = "host"
    CO = "co"
    MEMBER = "member"

@dataclass
class Participant:
    id: str
    name: str
    room_id: str | None = None
    role: Role = Role.MEMBER

    on_track_published: Callable[[str, str, MediaStreamTrack], Awaitable[None]] | None = None
    on_track_unpublished: Callable[[str, str], Awaitable[None]] | None = None
    on_negotiation_needed: Callable[[], None] | None = None
    on_room_updated: Callable[[Room], None] | None = None


class Room:
    """ Room Logic Handler
    """
    def __init__(self, room_id: str) -> None:
        self.id = room_id
        self.participants: dict[str, Participant] = {}
        self.lobby: dict[str, Participant] = {}

        self.published_tracks: dict[tuple[str, str], MediaStreamTrack] = {}
        self.media_participants: set[str] = set()
        self.relay = MediaRelay()
        self.track_sinks: dict[
            tuple[str, str],
            tuple[MediaBlackhole, MediaStreamTrack],
        ] = {}

    def _ensure_can_join(self, participant: Participant) -> None:
        if participant.room_id is not None:
            raise ParticipantAlreadyInRoom(participant.id)

        if participant.id in self.participants or participant.id in self.lobby:
            raise ParticipantAlreadyJoined(participant.id)

    def add_participant(self, participant: Participant) -> None:
        self._ensure_can_join(participant)

        self.participants[participant.id] = participant
        participant.room_id = self.id

    def add_to_lobby(self, participant: Participant) -> None:
        self._ensure_can_join(participant)

        self.lobby[participant.id] = participant
        participant.room_id = self.id

    async def admit_participant(self, participant_id: str) -> None:
        participant = self.lobby.pop(participant_id, None)

        if participant is None:
            raise ParticipantNotFound(participant_id)

        self.participants[participant_id] = participant

    async def remove_participant(self, participant_id: str) -> None:
        participant = self.participants.pop(participant_id, None)

        if participant is None:
            participant = self.lobby.pop(participant_id, None)

        if participant is None:
            raise ParticipantNotFound(participant_id)

        self.media_participants.discard(participant_id)

        published_keys = [
            key for key in self.published_tracks
            if key[0] == participant_id
        ]

        affected = set()

        for publisher_id, track_id in published_keys:
            affected.update( 
                await self.unpublish_track(
                    publisher_id,
                    track_id,
                )
            )

        self.request_negotiation(affected)

        participant.room_id = None
        participant.role = Role.MEMBER

    def has_no_participants(self) -> bool:
        return not self.participants

    async def close(self) -> None:
        sinks = list(self.track_sinks.values())
        self.track_sinks.clear()

        await asyncio.gather(
            *(sink.stop() for sink, _ in sinks),
            return_exceptions=True,
        )

        for _, sink_track in sinks:
            sink_track.stop()

        for participant in (*self.participants.values(), *self.lobby.values()):
            participant.room_id = None
            participant.role = Role.MEMBER

        self.published_tracks.clear()
        self.media_participants.clear()
        self.participants.clear()
        self.lobby.clear()

    async def publish_track(
        self, publisher_id: str, track: MediaStreamTrack
    ) -> set[str]:
        """ For all participants (subscribers) create a proxy track
        then add the proxy track to their webrtc
        """
        affected = set()

        if publisher_id not in self.participants:
            raise ParticipantNotFound(publisher_id)

        key = (publisher_id, track.id)

        if key in self.published_tracks:
            return affected

        self.published_tracks[key] = track

        sink_track = self.relay.subscribe(track, buffered=False)

        sink = MediaBlackhole()
        sink.addTrack(sink_track)
        await sink.start()

        self.track_sinks[key] = (sink, sink_track)

        callbacks = []

        subscribers = list(self.participants.items())
        for subscriber_id, subscriber in subscribers:
            if subscriber_id == publisher_id:
                continue   

            if subscriber_id not in self.media_participants:
                continue

            relayed_track = self.relay.subscribe(track, buffered=False)

            callbacks.append(
                subscriber.on_track_published(
                    publisher_id,
                    track.id,
                    relayed_track,
                )
            )

            affected.add(subscriber_id)

        await asyncio.gather(*callbacks)
        return affected

    async def unpublish_track(self, publisher_id: str, track_id: str) -> set[str]:
        """ For all participants remove the publisher's relayed track
        """
        affected = set()

        key = (publisher_id, track_id)
        track = self.published_tracks.pop(key, None)

        if track is None:
            return affected

        sink_entry = self.track_sinks.pop(key, None)

        if sink_entry is not None:
            sink, sink_track = sink_entry
            await sink.stop()
            sink_track.stop()

        callbacks = []

        subscribers = list(self.participants.items())
        for subscriber_id, subscriber in subscribers:
            if subscriber_id == publisher_id:
                continue

            if subscriber_id not in self.media_participants:
                continue

            callbacks.append( 
                subscriber.on_track_unpublished(
                    publisher_id, track_id
                )
            )

            affected.add(subscriber_id)

        await asyncio.gather(*callbacks)
        return affected

    async def activate_participant_media(
        self,
        participant_id: str,
        incoming_tracks: list[MediaStreamTrack],
    ) -> None:
        """ Catch up: Initialization
        Publish your tracks
        and suscribe to your remote peer tracks
        """
        participant = self.participants.get(participant_id)

        if participant is None:
            raise ParticipantNotFound(participant_id)

        self.media_participants.add(participant_id)

        affected = set()

        for track in incoming_tracks:
            affected.update(await self.publish_track(participant_id, track))

        subscribed = await self._subscribe_to_existing_tracks(participant)

        if subscribed:
            affected.add(participant.id)

        self.request_negotiation(affected)

    async def _subscribe_to_existing_tracks(self, subscriber: Participant) -> bool:
        """ For all published track,
        subscribe to each one of them unless it's yours
        """
        subscribed = False
        published_tracks = list(self.published_tracks.items())

        for (publisher_id, track_id), track in published_tracks:
            if publisher_id == subscriber.id:
                continue

            relayed_track = self.relay.subscribe(track, buffered=False)

            await subscriber.on_track_published(
                publisher_id,
                track_id,
                relayed_track,
            )

            subscribed = True

        return subscribed

    def request_negotiation(self, participant_ids: set[str]) -> None:
        for participant_id in participant_ids:
            participant = self.participants.get(participant_id)

            if participant and participant.on_negotiation_needed:
                participant.on_negotiation_needed()

    def notify_room_updated(self, *, exclude_id: str | None = None) -> None:
        recipients = [
            *self.participants.values(),
            *self.lobby.values(),
        ]

        for participant in recipients:
            if participant.id == exclude_id:
                continue

            if participant.on_room_updated:
                participant.on_room_updated(self)

    def broadcast() -> None:
        pass


class RoomManager:
    """ Handles all room on the server
    """
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}
        self.lock = asyncio.Lock()

    async def create_room(self, participant: Participant) -> Room:
        async with self.lock:
            room_id = str(uuid4())
            room = Room(room_id)

            room.add_participant(participant)
            self.rooms[room_id] = room       
            participant.role = Role.HOST 

            return room

    def _get_room(self, room_id: str) -> Room:
        room = self.rooms.get(room_id)

        if room is None:
            raise RoomNotFound()
        
        return room
    
    async def join_room(self, participant: Participant, room_id: str) -> Room:
        async with self.lock:
            room = self._get_room(room_id)

            if participant.room_id == room_id:
                return room # repeated join
                
            room.add_to_lobby(participant)
            room.notify_room_updated(exclude_id=participant.id)

            return room

    async def admit_participant(self, participant_id: str, room_id: str) -> Room:
        async with self.lock:
            room = self._get_room(room_id)

            await room.admit_participant(participant_id)
            room.notify_room_updated(exclude_id=participant_id)
            
            return room

    async def leave_room(self, participant_id: str, room_id: str) -> None:
        async with self.lock:
            room = self._get_room(room_id)
            await room.remove_participant(participant_id)

            if room.has_no_participants(): 
                await self._close_room(room_id)
            else:
                room.notify_room_updated()

    async def _close_room(self, room_id: str) -> None:
        room = self._get_room(room_id)
        del self.rooms[room_id]
        await room.close()    

    async def publish_track(self, 
        participant_id: str, 
        room_id: str,
        track: MediaStreamTrack,
    ) -> None: 
        async with self.lock:
            room = self._get_room(room_id)

            affected = await room.publish_track(participant_id, track)

            room.request_negotiation(affected)


    async def unpublish_track(
        self,
        participant_id: str,
        room_id: str,
        track_id: str,
    ) -> None:
        async with self.lock:
            room = self._get_room(room_id)

            affected = await room.unpublish_track(
                participant_id,
                track_id,
            )

            room.request_negotiation(affected)

    async def activate_participant_media(
        self,
        participant_id: str,
        room_id: str,
        incoming_tracks: list[MediaStreamTrack],
    ) -> None:
        async with self.lock:
            room = self._get_room(room_id)

            await room.activate_participant_media(
                participant_id,
                incoming_tracks,
            )

    async def close(self) -> None:
        async with self.lock:
            rooms = list(self.rooms.values())
            self.rooms.clear()

            await asyncio.gather(
                *(room.close() for room in rooms),
                return_exceptions=True,
            )
