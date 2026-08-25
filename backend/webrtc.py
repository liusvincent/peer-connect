from aiortc import (
    RTCPeerConnection, 
    RTCSessionDescription, 
    MediaStreamTrack, 
    RTCRtpSender, 
    RTCConfiguration,
    RTCIceServer
)

from typing import Callable, Awaitable
from dataclasses import dataclass

import asyncio


@dataclass(frozen=True)
class OutgoingMediaHint:
    participant_id: str
    track_id: str
    kind: str

@dataclass(frozen=True)
class OutgoingMediaInfo(OutgoingMediaHint):
    mid: str 


class WebRTCSession:
    def __init__(
        self, 
        publish_track: Callable[[MediaStreamTrack], Awaitable[None]],
        unpublish_track: Callable[[str], Awaitable[None]],
        on_terminated: Callable[[], Awaitable[None]]
    ) -> None:
        configuration = RTCConfiguration(
            iceServers=[
                RTCIceServer(
                    urls=["stun:stun.l.google.com:19302"],
                ),
            ],
        )
        
        self.pc = RTCPeerConnection(configuration=configuration)

        # handles local tracks
        self.incoming_tracks: dict[str, MediaStreamTrack] = {} 
         # handles remote tracks
        self.outgoing_senders: dict[tuple[str, str], RTCRtpSender] = {}

        self.closed = False
        self.negotiation_lock = asyncio.Lock()

        self.publish_track = publish_track
        self.unpublish_track = unpublish_track
        self.on_terminated = on_terminated

        @self.pc.on("track")
        async def on_track(track: MediaStreamTrack):
            if self.closed:
                track.stop()
                return

            track_id = track.id
            self.incoming_tracks[track_id] = track

            @track.on("ended")
            async def on_ended() -> None:
                removed = self.incoming_tracks.pop(track_id, None)
                if removed is None:
                    return
                await self.unpublish_track(track_id)

            await self.publish_track(track)

        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print("WebRTC state:", self.pc.connectionState)

            if self.closed:
                return

            if self.pc.connectionState in ("failed", "closed"):
                await self.on_terminated()

    async def handle_offer(self, sdp: str) -> tuple[str, list[OutgoingMediaInfo]]:
        """ Handle the offer created by the browser 
        returns the sdp answer
        """
        async with self.negotiation_lock:
            if self.closed:
                raise RuntimeError("WebRTC session is closed")
            
            offer = RTCSessionDescription(sdp=sdp, type="offer")
            await self.pc.setRemoteDescription(offer)

            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)

            media = self._get_outgoing_media()

            return self.pc.localDescription.sdp, media

    async def add_remote_participant_track(
        self, 
        publisher_id: str, 
        track_id: str,
        track: MediaStreamTrack,
    ) -> bool:
        """ Attach another participant's track
        affects outgoing_senders
        """
        async with self.negotiation_lock:
            if self.closed:
                raise RuntimeError("WebRTC session is closed")

            key = (publisher_id, track_id)

            if key in self.outgoing_senders:
                return False

            self.outgoing_senders[key] = self.pc.addTrack(track)
            return True

    async def remove_remote_participant_track(
        self,
        publisher_id: str,
        track_id: str,
    ) -> bool:
        async with self.negotiation_lock:
            if self.closed:
                raise RuntimeError("WebRTC session is closed")
            
            key = (publisher_id, track_id)
            sender = self.outgoing_senders.pop(key, None)

            if sender is None:
                return False

            old_relayed_track = sender.track
            sender.replaceTrack(None)

            for transceiver in self.pc.getTransceivers():
                if transceiver.sender is sender:
                    await transceiver.stop()
                    break

            if old_relayed_track is not None:
                old_relayed_track.stop()

            return True

    async def close(self) -> None:
        async with self.negotiation_lock:
            if self.closed:
                return

            self.closed = True

            self.incoming_tracks.clear()
            self.outgoing_senders.clear()

            await self.pc.close()

    def _get_outgoing_media(self) -> list[OutgoingMediaInfo]:
        transceiver_by_sender = {
            id(transceiver.sender): transceiver
            for transceiver in self.pc.getTransceivers()
        }

        media = []

        for (participant_id, track_id), sender in self.outgoing_senders.items():
            track = sender.track
            if track is None:
                continue

            transceiver = transceiver_by_sender.get(id(sender))

            if transceiver is None or transceiver.mid is None:
                continue

            media.append(
                OutgoingMediaInfo(
                    mid=transceiver.mid,
                    participant_id=participant_id,
                    track_id=track_id,
                    kind=track.kind,
                )
            )

        return media

    def _get_media_hints(self) -> list[OutgoingMediaHint]:
        hints = []

        for (participant_id, track_id), sender in self.outgoing_senders.items():
            track = sender.track

            if track is None:
                continue

            hints.append(
                OutgoingMediaHint(
                    participant_id=participant_id,
                    track_id=track_id,
                    kind=track.kind,
                )
            )

        return hints