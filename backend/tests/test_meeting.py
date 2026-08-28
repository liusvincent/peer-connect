import pytest
from unittest.mock import AsyncMock, MagicMock

from meeting import MeetingHandler, UserNotCreated
from messages import CreateRoomRequest, JoinRoomRequest, WebRTCOfferRequest
from rooms import Participant, RoomManager, RoomNotFound
from webrtc import WebRTCSession


def make_participant(**overrides):
    kwargs = {
        "id": "user-1",
        "name": "john doe",
        "room_id": "room-1",
    }
    kwargs.update(overrides)
    return Participant(**kwargs)


def make_meeting():
    return MeetingHandler(
        room_manager=MagicMock(spec=RoomManager),
        send_message=MagicMock(),
        on_terminated=AsyncMock(),
    )

def make_webrtc():
    return WebRTCSession(
        publish_track=AsyncMock(),
        unpublish_track=AsyncMock(),
        on_terminated=AsyncMock(),
    )

class TestMeetingLifecycle:
    def test_starts_open_without_user_or_webrtc(self):
        handler = make_meeting()

        assert handler.closed is False
        assert handler.media_ready is False
        assert handler.participant is None
        assert handler.webrtc is None

    @pytest.mark.asyncio
    async def test_close_clears_user_and_webrtc(self):
        handler = make_meeting()
        participant = make_participant()
        webrtc = MagicMock(spec=WebRTCSession)

        handler.participant = participant
        handler.webrtc = webrtc
        handler.media_ready = True

        await handler.close()

        assert handler.closed is True
        assert handler.media_ready is False
        assert handler.participant is None
        assert handler.webrtc is None

        handler.room_manager.leave_room.assert_awaited_once_with(
            participant_id="user-1",
            room_id="room-1",
        )
        webrtc.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_close_does_not_request_transport_termination(self):
        handler = make_meeting()

        await handler.close()

        handler.on_terminated.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self):
        handler = make_meeting()
        participant = make_participant()
        webrtc = MagicMock(spec=WebRTCSession)

        handler.participant = participant
        handler.webrtc = webrtc

        await handler.close()
        await handler.close()

        handler.room_manager.leave_room.assert_awaited_once_with(
            participant_id="user-1",
            room_id="room-1",
        )
        webrtc.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_close_clears_resources_when_leaving_room_fails(self):
        handler = make_meeting()
        participant = make_participant()
        webrtc = MagicMock(spec=WebRTCSession)

        handler.participant = participant
        handler.webrtc = webrtc
        handler.room_manager.leave_room.side_effect = RuntimeError(
            "leave failed"
        )

        with pytest.raises(RuntimeError, match="leave failed"):
            await handler.close()

        assert handler.closed is True
        assert handler.participant is None
        assert handler.webrtc is None
        webrtc.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_webrtc_termination_closes_meeting_and_transport(self):
        handler = make_meeting()
        participant = make_participant()
        webrtc = MagicMock(spec=WebRTCSession)

        handler.participant = participant
        handler.webrtc = webrtc

        await handler._handle_webrtc_terminated()

        assert handler.closed is True
        assert handler.participant is None
        assert handler.webrtc is None

        handler.on_terminated.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_webrtc_termination_is_idempotent(self):
        handler = make_meeting()

        await handler._handle_webrtc_terminated()
        await handler._handle_webrtc_terminated()

        handler.on_terminated.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_webrtc_termination_still_terminates_when_close_fails(self):
        handler = make_meeting()
        handler.close = AsyncMock(
            side_effect=RuntimeError("cleanup failed")
        )

        with pytest.raises(RuntimeError, match="cleanup failed"):
            await handler._handle_webrtc_terminated()

        handler.on_terminated.assert_awaited_once_with()


class TestWebRTCOffers:
    @pytest.mark.asyncio
    async def test_offer_error_closes_meeting_and_reraises(self):
        handler = make_meeting()
        webrtc = MagicMock(spec=WebRTCSession)

        webrtc.handle_offer.side_effect = RuntimeError("offer failed")
        handler.webrtc = webrtc

        with pytest.raises(RuntimeError, match="offer failed"):
            await handler.handle_webrtc_offer(
                WebRTCOfferRequest(
                    type="webrtc-offer",
                    request_id="request-1",
                    sdp="invalid-sdp",
                )
            )

        assert handler.closed is True
        assert handler.webrtc is None
        webrtc.close.assert_awaited_once_with()


class TestRoomRequests:
    @pytest.mark.asyncio
    async def test_meeting_error_does_not_close_meeting(self):
        handler = make_meeting()

        request = CreateRoomRequest(
            type="create-room",
            request_id="request-1",
        )

        with pytest.raises(UserNotCreated):
            await handler.handle_create_room(request)

        assert handler.closed is False

    @pytest.mark.asyncio
    async def test_room_error_does_not_close_meeting(self):
        handler = make_meeting()
        handler.participant = make_participant(room_id="invalid")

        handler.room_manager.admit_participant.side_effect = RoomNotFound()

        request = JoinRoomRequest(
            type="join-room",
            request_id="request-1",
        )

        with pytest.raises(RoomNotFound):
            await handler.handle_join_room(request)

        handler.room_manager.admit_participant.assert_awaited_once_with(
            "user-1",
            "invalid",
        )
        assert handler.closed is False