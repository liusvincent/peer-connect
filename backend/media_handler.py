from aiortc import MediaStreamTrack

from webrtc import WebRTCSession

from rooms import Participant, RoomManager

from messages import (
    ServerMessage, 
    WebRTCRenegotiationOffer, 
    WebRTCRenegotiationAnswer, 
    MediaSubscriptionInfo
)

import asyncio

from typing import Callable
from uuid import uuid4


class MediaHandler:
    """ A WebTransport Session Media Handler:
    """
    def __init__(self, 
        participant: Participant, 
        room_manager: RoomManager, 
        send_message: Callable[[ServerMessage], None]
    ) -> None:
        self.participant = participant
        self.room_manager = room_manager
        self.send_message = send_message

        self.webrtc: WebRTCSession | None = None
        self.media_ready = False

        self.renegotiation_lock = asyncio.Lock()
        self.pending_negotiation_id: str | None = None
        self.renegotiation_needed = False

    async def handle_webrtc_offer(self, offer_sdp: str) -> str:
        """ Handle the initial webrtc offer
        that was sent from the client
        """
        if self.webrtc is None or self.webrtc.closed:
            self.webrtc = WebRTCSession(
                self._publish_track,
                self._unpublish_track,
            )

        try:
            answer_sdp = await self.webrtc.handle_initial_offer(offer_sdp)
        except Exception:
            await self.close()
            raise
    
        return answer_sdp

    async def close(self) -> None:
        """ Close Media (WebRTC) Session
        """
        webrtc = self.webrtc
        self.webrtc = None
        if webrtc is not None:
            await webrtc.close()

        self.media_ready = False

    async def _publish_track(self, track: MediaStreamTrack):
        """ Callback helper function: for WebRTCSession
        If an incoming track arrives from this participant,
        Publish it to the other participants in room
        """
        if not self.media_ready:
            return

        participant = self.participant

        if participant is None or participant.room_id is None:
            return

        await self.room_manager.publish_track(
            participant_id=participant.id,
            room_id=participant.room_id,
            track=track,
        )
    
    async def _unpublish_track(self, track_id: str) -> None:
        """ Callback helper function: for WebRTCSession
        """
        if not self.media_ready:
            return

        participant = self.participant

        if participant is None or participant.room_id is None:
            return

        await self.room_manager.unpublish_track(
            participant_id=participant.id,
            room_id=participant.room_id,
            track_id=track_id,
        )

    async def _subscribe_to_track(
        self,
        publisher_id: str,
        track_id: str,
        track: MediaStreamTrack,
    ) -> None:
        """ Callback helper function: for Participant
        if another participant in room has published a track,
        this participant should receive it
        """
        if self.webrtc is None:
            return

        added = self.webrtc.add_remote_participant_track(
            publisher_id=publisher_id,
            track_id=track_id,
            track=track,
        )

        if added:
            await self.renegotiate_webrtc()

    async def _unsubscribe_from_track(
        self,
        publisher_id: str,
        track_id: str,
    ) -> None:
        """ Callback helper function: for Participant
        """
        if self.webrtc is None:
            return

        removed = await self.webrtc.remove_remote_participant_track(
            publisher_id,
            track_id,
        )

        if removed: 
            await self.renegotiate_webrtc()

    async def renegotiate_webrtc(self):
        if self.webrtc is None:
            return

        async with self.renegotiation_lock:
            if self.pending_negotiation_id is not None:
                self.renegotiation_needed = True
                return

            offer_sdp, outgoing_media = await self.webrtc.create_renegotiation_offer()

            event_id = str(uuid4())
            self.pending_negotiation_id = event_id

            try:
                self.send_message(
                    WebRTCRenegotiationOffer(
                        event_id=event_id,
                        sdp=offer_sdp,
                        media = [
                            MediaSubscriptionInfo(
                                mid=item.mid,
                                participant_id=item.participant_id,
                                track_id=item.track_id,
                                kind=item.kind,
                            )
                            for item in outgoing_media
                        ]
                    )
                )
            except Exception:
                self.pending_negotiation_id = None
                raise

    async def handle_renegotiation_answer(
        self, 
        message: WebRTCRenegotiationAnswer
    ) -> None: 
        if self.webrtc is None:
            return

        start_next = False

        async with self.renegotiation_lock:
            if message.event_id != self.pending_negotiation_id:
                return

            await self.webrtc.apply_renegotiation_answer(
                message.sdp
            )

            self.pending_negotiation_id = None
            start_next = self.renegotiation_needed
            self.renegotiation_needed = False

        if start_next:
            await self.renegotiate_webrtc()

    async def handle_webrtc_ready(self) -> None:
        if self.media_ready:
            return

        participant = self.participant
        webrtc = self.webrtc

        if (participant is None
            or participant.room_id is None
            or webrtc is None
            ):
            return

        try:
            await self.room_manager.activate_participant_media(
                participant_id=participant.id,
                room_id=participant.room_id,
                incoming_tracks=list(
                    webrtc.incoming_tracks.values()
                ),
            )
        except Exception:
            raise

        self.media_ready = True