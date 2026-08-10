from aiortc.contrib.media import MediaRelay
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

    on_track_published: (
        Callable[[str, str, MediaStreamTrack], Awaitable[None]] | None
    ) = None

    on_track_unpublished: (
        Callable[[str, str], Awaitable[None]]
        | None
    ) = None


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

        for publisher_id, track_id in published_keys:
            await self.unpublish_track(
                publisher_id,
                track_id,
            )

        participant.room_id = None
        participant.role = Role.MEMBER

    def has_no_participants(self) -> bool:
        return not self.participants

    def close(self) -> None:
        for participant in self.participants.values():
            participant.room_id = None
            participant.role = Role.MEMBER

        for participant in self.lobby.values():
            participant.room_id = None
            participant.role = Role.MEMBER

        self.media_participants.clear()
        self.participants.clear()
        self.lobby.clear()

    async def publish_track(self, publisher_id: str, track: MediaStreamTrack) -> None:
        """ For all participants (subscribers) create a proxy track
        then add the proxy track to their webrtc
        """
        if publisher_id not in self.participants:
            raise ParticipantNotFound(publisher_id)

        key = (publisher_id, track.id)

        if key in self.published_tracks:
            return

        self.published_tracks[key] = track

        callbacks = []

        subscribers = list(self.participants.items())
        for subscriber_id, subscriber in subscribers:
            if subscriber_id == publisher_id:
                continue   

            if subscriber_id not in self.media_participants:
                continue

            relayed_track = self.relay.subscribe(track)

            callbacks.append(
                subscriber.on_track_published(
                    publisher_id,
                    track.id,
                    relayed_track,
                )
            )

        await asyncio.gather(*callbacks)

    async def unpublish_track(self, publisher_id: str, track_id: str) -> None:
        """ For all participants remove the publisher's relayed track
        """
        key = (publisher_id, track_id)
        track = self.published_tracks.pop(key, None)

        if track is None:
            return

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

        await asyncio.gather(*callbacks)

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

        for track in incoming_tracks:
            await self.publish_track(participant_id, track)

        await self._subscribe_to_existing_tracks(participant)

    async def _subscribe_to_existing_tracks(self, subscriber: Participant) -> None:
        """ For all published track,
        subscribe to each one of them unless it's yours
        """
        published_tracks = list(self.published_tracks.items())
        for (publisher_id, track_id), track in published_tracks:
            if publisher_id == subscriber.id:
                continue

            relayed_track = self.relay.subscribe(track)

            await subscriber.on_track_published(
                publisher_id,
                track_id,
                relayed_track,
            )

    def broadcast() -> None:
        pass


class RoomManager:
    """ Handles all room on the server
    """
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}

    def create_room(self, participant: Participant) -> Room:
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
    
    def join_room(self, participant: Participant, room_id: str) -> Room:
        room = self._get_room(room_id)

        if participant.room_id == room_id:
            return room # repeated join
            
        room.add_to_lobby(participant)
        return room

    async def admit_participant(self, participant_id: str, room_id: str) -> Room:
        room = self._get_room(room_id)
        await room.admit_participant(participant_id)
        return room

    async def leave_room(self, participant_id: str, room_id: str) -> None:
        room = self._get_room(room_id)
        await room.remove_participant(participant_id)

        if room.has_no_participants(): 
            self.close_room(room_id)

    def close_room(self, room_id: str) -> None:
        room = self._get_room(room_id)
        del self.rooms[room_id]
        room.close()    

    async def publish_track(self, 
        participant_id: str, 
        room_id: str,
        track: MediaStreamTrack,
    ) -> None:
        room = self._get_room(room_id)
        await room.publish_track(participant_id, track)

    async def unpublish_track(
        self,
        participant_id: str,
        room_id: str,
        track_id: str,
    ) -> None:
        room = self._get_room(room_id)

        await room.unpublish_track(
            participant_id,
            track_id,
        )

    async def activate_participant_media(
        self,
        participant_id: str,
        room_id: str,
        incoming_tracks: list[MediaStreamTrack],
    ) -> None:
        room = self._get_room(room_id)

        await room.activate_participant_media(
            participant_id,
            incoming_tracks,
        )
