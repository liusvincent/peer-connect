from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack, RTCRtpSender
from aiortc.contrib.media import MediaRelay

from typing import Callable, Awaitable
from dataclasses import dataclass

import asyncio


@dataclass(frozen=True)
class OutgoingMediaInfo:
    mid: str
    participant_id: str
    track_id: str
    kind: str

class WebRTCSession:
    def __init__(
        self, 
        track_callback: Callable[[MediaStreamTrack], Awaitable[None]],
        track_ended_callback: Callable[[str], Awaitable[None]],
    ) -> None:
        self.pc = RTCPeerConnection()

        self.incoming_tracks: dict[str, MediaStreamTrack] = {} # local tracks
        self.outgoing_senders: dict[tuple[str, str], RTCRtpSender] = {} # remote tracks

        self.closed = False
        self.negotiation_lock = asyncio.Lock()

        self.track_callback = track_callback
        self.track_ended_callback = track_ended_callback

        @self.pc.on("track")
        async def on_track(track: MediaStreamTrack):
            track_id = track.id
            self.incoming_tracks[track_id] = track

            @track.on("ended")
            async def on_ended() -> None:
                removed = self.incoming_tracks.pop(track_id, None)
                if removed is None:
                    return
                await self.track_ended_callback(track_id)

            await self.track_callback(track)

        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print("WebRTC state:", self.pc.connectionState)

            if self.pc.connectionState in ("failed", "closed"):
                await self.close()

    async def handle_initial_offer(self, sdp: str) -> str:
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

            return self.pc.localDescription.sdp

    def add_remote_participant_track(
        self, 
        publisher_id: str, 
        track_id: str,
        track: MediaStreamTrack,
    ) -> bool:
        """ Attach another participant's track
        affects outgoing_senders
        """
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
        key = (publisher_id, track_id)
        sender = self.outgoing_senders.pop(key, None)

        if sender is None:
            return False

        old_track = sender.track
        sender.replaceTrack(None)

        for transceiver in self.pc.getTransceivers():
            if transceiver.sender is sender:
                await transceiver.stop()
                break

        if old_track is not None:
            old_track.stop()

        return True

    async def create_renegotiation_offer(self) -> tuple[str, list[OutgoingMediaInfo]]:
        """ Create an offer after outgoing tracks have been added
        """
        async with self.negotiation_lock:
            if self.closed:
                raise RuntimeError("WebRTC session is closed")

            if self.pc.signalingState != "stable":
                raise RuntimeError(
                    f"Cannot negotiate while signaling state is "
                    f"{self.pc.signalingState!r}"
                )

            offer = await self.pc.createOffer()
            await self.pc.setLocalDescription(offer)

            media = self.get_outgoing_media()

            return self.pc.localDescription.sdp, media

    async def apply_renegotiation_answer(self, sdp: str) -> None:
        """ Apply the browser's answer to a server-created offer
        """
        async with self.negotiation_lock:
            if self.closed:
                raise RuntimeError("WebRTC session is closed")

            await self.pc.setRemoteDescription(
                RTCSessionDescription(sdp=sdp, type="answer")
            )

    async def close(self) -> None:
        if self.closed:
            return

        self.closed = True
        track_ids = list(self.incoming_tracks)
        self.incoming_tracks.clear()
        self.outgoing_senders.clear()

        await self.pc.close()

        await asyncio.gather(
            *(self.track_ended_callback(track_id) for track_id in track_ids),
            return_exceptions=True,
        )

    def get_outgoing_media(self) -> list[OutgoingMediaInfo]:
        media: list[OutgoingMediaInfo] = []

        transceiver_by_sender = {
            id(transceiver.sender): transceiver
            for transceiver in self.pc.getTransceivers()
        }

        for (participant_id, track_id), sender in self.outgoing_senders.items():
            transceiver = transceiver_by_sender.get(id(sender))

            if transceiver is None or transceiver.mid is None:
                continue

            track = sender.track

            if track is None:
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
