from messages import (
    ClientRequest,
    ServerResponse,
    ServerMessage,
    CreateRoomRequest,
    CreateUserRequest,
    JoinLobbyRequest,
    JoinedLobbyResponse,
    JoinRoomRequest,
    JoinedRoomResponse,
    LeaveRoomRequest,
    LeftRoomResponse,
    WebRTCOfferRequest,
    WebRTCAnswerResponse,
    WebRTCOfferNeeded,
    CreateUserResponse,
    RoomUpdated,
)

from rooms import Participant, RoomManager, Room
from aiortc import MediaStreamTrack
from webrtc import WebRTCSession
from typing import Callable, Awaitable
from uuid import uuid4

import traceback


class MeetingError(Exception):
    code = "meeting-error"


class MeetingEnded(MeetingError):
    code = "meeting-ended"


class UserAlreadyCreated(MeetingError):
    code = "user-already-created"


class UserNotCreated(MeetingError):
    code = "user-not-created"


class UserNotInRoom(MeetingError):
    code = "user-not-in-room"


class WebRTCUnavailable(MeetingError):
    code = "webrtc-unavailable"


class MeetingHandler:
    """Handler for meeting logic"""

    def __init__(
        self,
        room_manager: RoomManager,
        send_message: Callable[[ServerMessage], None],
        on_terminated: Callable[[], Awaitable[None]],
    ) -> None:
        self.room_manager = room_manager
        self.send_message = send_message
        self.on_terminated = on_terminated

        self.participant: Participant | None = None
        self.webrtc: WebRTCSession | None = None
        self.media_ready = False
        self.closed = False

    def _is_open(self) -> None:
        if self.closed:
            raise MeetingEnded()

    def _require_participant(self) -> Participant:
        self._is_open()

        participant = self.participant

        if participant is None:
            raise UserNotCreated()

        return participant

    def _require_participant_in_room(self) -> tuple[Participant, str]:
        participant = self._require_participant()

        if participant.room_id is None:
            raise UserNotInRoom()

        return participant, participant.room_id

    def _require_webrtc(self) -> WebRTCSession:
        self._is_open()

        webrtc = self.webrtc

        if (
            webrtc is None
            or webrtc.closed
            or webrtc.pc.connectionState in ("failed", "closed")
        ):
            raise WebRTCUnavailable()

        return webrtc

    async def _handle_webrtc_terminated(self) -> None:
        if self.closed:
            return

        try:
            await self.close()
        finally:
            await self.on_terminated()

    async def handle_webrtc_offer(self, request: ClientRequest) -> ServerResponse:
        self._is_open()

        assert isinstance(request, WebRTCOfferRequest)

        if self.webrtc is None:
            self.webrtc = WebRTCSession(
                self._publish_track,
                self._unpublish_track,
                self._handle_webrtc_terminated,
            )

        try:
            answer_sdp, outgoing_media = await self.webrtc.handle_offer(request.sdp)
        except Exception as err:
            print(f"WebRTC offer failed: {type(err).__name__}: {err}")
            traceback.print_exc()
            await self.close()
            raise

        return WebRTCAnswerResponse(
            request_id=request.request_id, sdp=answer_sdp, media_info=outgoing_media
        )

    async def _publish_track(self, track: MediaStreamTrack):
        """Callback helper function: for WebRTCSession
        If an incoming track arrives from this participant,
        Publish it to the other participants in room
        """
        if not self.media_ready:
            return

        participant, room_id = self._require_participant_in_room()

        await self.room_manager.publish_track(
            participant_id=participant.id,
            room_id=room_id,
            track=track,
        )

    async def _unpublish_track(self, track_id: str) -> None:
        """Callback helper function: for WebRTCSession"""
        if not self.media_ready:
            return

        participant, room_id = self._require_participant_in_room()

        await self.room_manager.unpublish_track(
            participant_id=participant.id,
            room_id=room_id,
            track_id=track_id,
        )

    async def handle_create_user(self, request: ClientRequest) -> ServerResponse:
        self._is_open()

        assert isinstance(request, CreateUserRequest)

        if self.participant:
            raise UserAlreadyCreated()

        user_id = str(uuid4())
        user_name = request.user_name

        self.participant = Participant(
            id=user_id,
            name=user_name,
            on_track_published=self._subscribe_to_track,
            on_track_unpublished=self._unsubscribe_from_track,
            on_negotiation_needed=self._request_negotiation,
            on_room_updated=self._send_room_update,
        )

        return CreateUserResponse(
            request_id=request.request_id,
            id=user_id,
        )

    async def _subscribe_to_track(
        self,
        publisher_id: str,
        track_id: str,
        track: MediaStreamTrack,
    ) -> None:
        """Callback helper function: for Participant
        if another participant in room has published a track,
        this participant should receive it
        """
        webrtc = self.webrtc

        if (
            self.closed
            or webrtc is None
            or webrtc.closed
            or webrtc.pc.connectionState in ("failed", "closed")
        ):
            track.stop()
            return

        await webrtc.add_remote_participant_track(
            publisher_id=publisher_id,
            track_id=track_id,
            track=track,
        )

    async def _unsubscribe_from_track(
        self,
        publisher_id: str,
        track_id: str,
    ) -> None:
        """Callback helper function: for Participant"""
        webrtc = self.webrtc

        if (
            self.closed
            or webrtc is None
            or webrtc.closed
            or webrtc.pc.connectionState in ("failed", "closed")
        ):
            return

        await webrtc.remove_remote_participant_track(
            publisher_id,
            track_id,
        )

    def _request_negotiation(self) -> None:
        webrtc = self.webrtc

        if (
            self.closed
            or webrtc is None
            or webrtc.closed
            or webrtc.pc.connectionState in ("failed", "closed")
        ):
            return

        self.send_message(
            WebRTCOfferNeeded(
                event_id=str(uuid4()),
                media_hint=webrtc._get_media_hints(),
            )
        )

    def _send_room_update(self, room: Room) -> None:
        self.send_message(
            RoomUpdated(
                event_id=str(uuid4()),
                room=room,
            )
        )

    async def handle_webrtc_ready(self) -> None:
        if self.media_ready:
            return

        participant, room_id = self._require_participant_in_room()
        webrtc = self._require_webrtc()

        self.media_ready = True
        incoming_tracks = list(webrtc.incoming_tracks.values())

        try:
            await self.room_manager.activate_participant_media(
                participant_id=participant.id,
                room_id=room_id,
                incoming_tracks=incoming_tracks,
            )
        except Exception:
            await self.close()
            raise

    async def handle_join_lobby(self, request: ClientRequest) -> ServerResponse:
        assert isinstance(request, JoinLobbyRequest)

        participant = self._require_participant()

        room = await self.room_manager.join_room(
            participant,
            request.room_id,
        )

        return JoinedLobbyResponse(
            request_id=request.request_id,
            room=room,
        )

    async def handle_join_room(self, request: ClientRequest) -> ServerResponse:
        assert isinstance(request, JoinRoomRequest)

        participant, room_id = self._require_participant_in_room()

        room = await self.room_manager.admit_participant(
            participant.id,
            room_id,
        )

        return JoinedRoomResponse(
            request_id=request.request_id,
            room=room,
        )

    async def handle_create_room(self, request: ClientRequest) -> ServerResponse:
        assert isinstance(request, CreateRoomRequest)

        participant = self._require_participant()

        room = await self.room_manager.create_room(
            participant,
        )

        return JoinedRoomResponse(
            request_id=request.request_id,
            room=room,
        )

    async def handle_leave_room(self, request: ClientRequest) -> ServerResponse:
        assert isinstance(request, LeaveRoomRequest)

        _, room_id = self._require_participant_in_room()

        await self.close()

        return LeftRoomResponse(
            request_id=request.request_id,
            room_id=room_id,
        )

    async def close(self) -> None:
        if self.closed:
            return

        self.closed = True
        self.media_ready = False

        participant = self.participant
        webrtc = self.webrtc
        room_id = participant.room_id if participant else None

        try:
            if participant and room_id:
                await self.room_manager.leave_room(
                    participant_id=participant.id,
                    room_id=room_id,
                )
        finally:
            try:
                if webrtc is not None:
                    await webrtc.close()
            finally:
                self.webrtc = None
                self.participant = None
