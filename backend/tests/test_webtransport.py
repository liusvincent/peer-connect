import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from aioquic.h3.events import (
    DataReceived,
    HeadersReceived,
    WebTransportStreamDataReceived,
)

import webtransport
from meeting import UserNotCreated
from messages import (
    CreateRoomRequest,
    CreateUserRequest,
    CreateUserResponse,
    JoinLobbyRequest,
    JoinRoomRequest,
    LeaveRoomRequest,
    RequestErrorResponse,
    WebRTCOfferRequest,
    WebRTCReady,
)
from rooms import RoomManager
from webtransport import WebTransportProtocol, WebTransportSession


def stream_event(
    data: bytes,
    *,
    stream_id: int = 4,
    session_id: int = 0,
    stream_ended: bool = False,
) -> WebTransportStreamDataReceived:
    return WebTransportStreamDataReceived(
        data=data,
        stream_id=stream_id,
        session_id=session_id,
        stream_ended=stream_ended,
    )


def connect_headers(
    method: bytes = b"CONNECT",
    protocol: bytes = b"webtransport",
    path: bytes = b"/wt",
):
    return [
        (b":method", method),
        (b":protocol", protocol),
        (b":path", path),
    ]


def mock_handler(*, control_stream_id: int | None = 11):
    handler = MagicMock(spec=WebTransportSession)
    handler.control_stream_id = control_stream_id
    handler.message_queue = MagicMock(spec=asyncio.Queue)
    handler.message_queue.join = AsyncMock()
    handler.connection = MagicMock()
    handler.transmit = MagicMock()
    return handler


def make_session(**overrides):
    kwargs = {
        "connection": MagicMock(),
        "session_id": 0,
        "transmit": MagicMock(),
        "room_manager": MagicMock(spec=RoomManager),
        "request_termination": AsyncMock(),
    }
    kwargs.update(overrides)
    return WebTransportSession(**kwargs)


@pytest_asyncio.fixture
async def session():
    """Session for tests that do not need the background worker running."""
    instance = make_session()

    worker = instance.message_worker
    assert worker is not None

    instance.message_worker = None
    worker.cancel()
    await asyncio.gather(worker, return_exceptions=True)

    yield instance

    await instance.close()


@pytest.fixture
def protocol(monkeypatch):
    """Protocol without constructing a real aioquic transport."""
    monkeypatch.setattr(
        webtransport.QuicConnectionProtocol,
        "__init__",
        lambda self, *args, **kwargs: None,
    )

    instance = WebTransportProtocol(
        room_manager=MagicMock(spec=RoomManager),
    )
    instance.http = MagicMock()
    instance.transmit = MagicMock()

    return instance


class TestWebTransportSessionLifecycle:
    @pytest.mark.asyncio
    async def test_close_cancels_worker_and_closes_meeting(self):
        session = make_session(session_id=10)
        session.meeting.close = AsyncMock()
        worker = session.message_worker

        assert worker is not None

        await session.close()

        assert session.closed is True
        assert session.message_worker is None
        assert worker.cancelled()
        session.meeting.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self):
        session = make_session(session_id=10)
        session.meeting.close = AsyncMock()

        await session.close()
        await session.close()

        session.meeting.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_close_does_not_request_termination(self, session):
        await session.close()

        session.request_termination.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_terminate_requests_termination_once(self, session):
        await session.terminate()
        await session.terminate()

        session.request_termination.assert_awaited_once_with(session.session_id)

    @pytest.mark.asyncio
    async def test_failed_termination_can_be_retried(self, session):
        session.request_termination = AsyncMock(
            side_effect=RuntimeError("termination failed")
        )

        with pytest.raises(RuntimeError, match="termination failed"):
            await session.terminate()

        assert session.terminated is False

        session.request_termination = AsyncMock()
        await session.terminate()

        session.request_termination.assert_awaited_once_with(session.session_id)
        assert session.terminated is True

    @pytest.mark.asyncio
    async def test_terminal_meeting_sends_response_before_termination(self, session):
        operations = []
        response = RequestErrorResponse(
            request_id="request-1",
            message="meeting-ended",
        )

        session.dispatch_request = AsyncMock(return_value=response)
        session.meeting.closed = True
        session.send_message = lambda message: operations.append(("response", message))

        async def request_termination(session_id):
            operations.append(("termination", session_id))

        session.request_termination = request_termination

        await session.dispatch_message(
            b'{"type":"create-room","request_id":"request-1"}'
        )

        assert operations == [
            ("response", response),
            ("termination", session.session_id),
        ]

    @pytest.mark.asyncio
    async def test_open_meeting_does_not_request_termination(self, session):
        response = RequestErrorResponse(
            request_id="request-1",
            message="recoverable-error",
        )
        session.dispatch_request = AsyncMock(return_value=response)
        session.send_message = MagicMock()
        session.meeting.closed = False

        await session.dispatch_message(
            b'{"type":"create-room","request_id":"request-1"}'
        )

        session.send_message.assert_called_once_with(response)
        session.request_termination.assert_not_awaited()


class TestWebTransportSessionBuffer:
    @pytest.mark.asyncio
    async def test_incomplete_message_buffer(self, session):
        await session.handle_event(stream_event(b'{"type":"create-room"'))

        assert session.buffer == b'{"type":"create-room"'
        assert session.message_queue.empty()

    @pytest.mark.asyncio
    async def test_message_across_events(self, session):
        await session.handle_event(stream_event(b'{"type":"create-'))
        await session.handle_event(stream_event(b'room","request_id":"123"}\n'))

        assert session.buffer == b""
        assert session.message_queue.get_nowait() == (
            b'{"type":"create-room","request_id":"123"}'
        )
        assert session.message_queue.empty()

    @pytest.mark.asyncio
    async def test_extracts_multiple_messages_from_one_event(self, session):
        await session.handle_event(stream_event(b"first\nsecond\nthird\n"))

        assert session.buffer == b""
        assert session.message_queue.get_nowait() == b"first"
        assert session.message_queue.get_nowait() == b"second"
        assert session.message_queue.get_nowait() == b"third"
        assert session.message_queue.empty()

    @pytest.mark.asyncio
    async def test_retains_trailing_partial_message(self, session):
        await session.handle_event(stream_event(b"first\nsecond\npartial"))

        assert session.message_queue.get_nowait() == b"first"
        assert session.message_queue.get_nowait() == b"second"
        assert session.message_queue.empty()
        assert session.buffer == b"partial"

    @pytest.mark.asyncio
    async def test_ignores_empty_lines(self, session):
        await session.handle_event(stream_event(b"\n\nmessage\n\n"))

        assert session.message_queue.get_nowait() == b"message"
        assert session.message_queue.empty()
        assert session.buffer == b""


class TestWebTransportSessionDispatch:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("client_request", "handler_name"),
        [
            (
                WebRTCOfferRequest(
                    type="webrtc-offer",
                    request_id="request-1",
                    sdp="test-sdp",
                ),
                "handle_webrtc_offer",
            ),
            (
                CreateUserRequest(
                    type="create-user",
                    request_id="request-1",
                    user_name="john doe",
                ),
                "handle_create_user",
            ),
            (
                CreateRoomRequest(type="create-room", request_id="request-1"),
                "handle_create_room",
            ),
            (
                JoinLobbyRequest(
                    type="join-lobby",
                    request_id="request-1",
                    room_id="room-1",
                ),
                "handle_join_lobby",
            ),
            (
                JoinRoomRequest(type="join-room", request_id="request-1"),
                "handle_join_room",
            ),
            (
                LeaveRoomRequest(type="leave-room", request_id="request-1"),
                "handle_leave_room",
            ),
        ],
    )
    async def test_routes_request_to_correct_handler(
        self,
        session,
        client_request,
        handler_name,
    ):
        expected = RequestErrorResponse(
            request_id=client_request.request_id,
            message="test-response",
        )
        handler = AsyncMock(return_value=expected)
        setattr(session.meeting, handler_name, handler)

        response = await session.dispatch_request(client_request)

        handler.assert_awaited_once_with(client_request)
        assert response is expected

    @pytest.mark.asyncio
    async def test_dispatch_message_parses_and_sends_response(self, session):
        expected = CreateUserResponse(
            request_id="request-1",
            id="user-1",
        )
        session.meeting.handle_create_user = AsyncMock(return_value=expected)
        session.send_message = MagicMock()

        await session.dispatch_message(
            b'{"type":"create-user","request_id":"request-1","user_name":"john doe"}'
        )

        session.meeting.handle_create_user.assert_awaited_once()
        request = session.meeting.handle_create_user.await_args.args[0]

        assert request.type == "create-user"
        assert request.request_id == "request-1"
        assert request.user_name == "john doe"
        session.send_message.assert_called_once_with(expected)

    @pytest.mark.asyncio
    async def test_dispatches_webrtc_ready_event(self, session):
        session.meeting.handle_webrtc_ready = AsyncMock()
        session.send_message = MagicMock()

        await session.dispatch_message(b'{"type":"webrtc-ready","event_id":"event-1"}')

        session.meeting.handle_webrtc_ready.assert_awaited_once_with()
        session.send_message.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error", "message"),
        [
            (UserNotCreated(), "user-not-created"),
            (RuntimeError("unexpected failure"), "internal-server-error"),
        ],
        ids=["meeting-error", "unexpected-error"],
    )
    async def test_request_errors_are_converted(self, session, error, message):
        session.meeting.handle_create_room = AsyncMock(side_effect=error)
        request = CreateRoomRequest(
            type="create-room",
            request_id="request-1",
        )

        response = await session.dispatch_request(request)

        assert response.type == "request-error"
        assert response.request_id == "request-1"
        assert response.message == message

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error", "message"),
        [
            (UserNotCreated(), "user-not-created"),
            (RuntimeError("unexpected failure"), "internal-server-error"),
        ],
        ids=["meeting-error", "unexpected-error"],
    )
    async def test_event_errors_are_converted(self, session, error, message):
        session.meeting.handle_webrtc_ready = AsyncMock(side_effect=error)

        response = await session.dispatch_event(WebRTCReady(event_id="event-1"))

        assert response is not None
        assert response.type == "event-error"
        assert response.event_id == "event-1"
        assert response.message == message


class TestWebTransportProtocolConnect:
    def test_accepts_valid_connect(self, protocol, monkeypatch):
        handler = mock_handler()
        session_factory = MagicMock(return_value=handler)
        monkeypatch.setattr(
            webtransport,
            "WebTransportSession",
            session_factory,
        )

        event = HeadersReceived(
            headers=connect_headers(),
            stream_id=0,
            stream_ended=False,
        )

        protocol.http_event_received(event)

        session_factory.assert_called_once_with(
            connection=protocol.http,
            session_id=0,
            transmit=protocol.transmit,
            room_manager=protocol.room_manager,
            request_termination=protocol.terminate_handler,
        )
        assert protocol.handlers[0] is handler
        protocol.http.send_headers.assert_called_once_with(
            stream_id=0,
            headers=[
                (b":status", b"200"),
                (b"sec-webtransport-http3-draft", b"draft02"),
            ],
        )
        protocol.transmit.assert_called_once_with()

    @pytest.mark.parametrize(
        "headers",
        [
            connect_headers(method=b"GET"),
            connect_headers(protocol=b"invalid-protocol"),
            connect_headers(path=b"/invalid-path"),
        ],
    )
    def test_rejects_invalid_connect(self, protocol, headers):
        event = HeadersReceived(
            headers=headers,
            stream_id=0,
            stream_ended=False,
        )

        protocol.http_event_received(event)

        assert protocol.handlers == {}
        protocol.http.send_headers.assert_called_once_with(
            stream_id=0,
            headers=[(b":status", b"404")],
            end_stream=True,
        )
        protocol.transmit.assert_called_once_with()


class TestWebTransportProtocolEventRouting:
    @pytest.mark.asyncio
    async def test_routes_event_using_session_id(self, protocol):
        handler = mock_handler()
        protocol.handlers[7] = handler
        event = stream_event(
            b"message\n",
            session_id=7,
            stream_id=11,
        )

        await protocol.handle_webtransport_event(event)

        handler.handle_event.assert_awaited_once_with(event)

    @pytest.mark.asyncio
    async def test_ignores_unknown_session(self, protocol):
        await protocol.handle_webtransport_event(
            stream_event(
                b"message\n",
                session_id=999,
                stream_id=11,
            )
        )

        assert protocol.handlers == {}

    @pytest.mark.asyncio
    async def test_stream_end_drains_queue_before_closing(self, protocol):
        handler = mock_handler()
        protocol.handlers[7] = handler
        protocol.close_handler = AsyncMock()

        event = stream_event(
            b"final-message\n",
            session_id=7,
            stream_id=11,
            stream_ended=True,
        )

        await protocol.handle_webtransport_event(event)

        handler.handle_event.assert_awaited_once_with(event)
        handler.message_queue.join.assert_awaited_once_with()
        protocol.close_handler.assert_awaited_once_with(7)

    @pytest.mark.asyncio
    async def test_handler_error_closes_session_and_stream(self, protocol):
        handler = mock_handler()
        handler.handle_event.side_effect = RuntimeError("handler failed")
        protocol.handlers[7] = handler

        await protocol.handle_webtransport_event(
            stream_event(
                b"message\n",
                session_id=7,
                stream_id=11,
            )
        )

        assert 7 not in protocol.handlers
        handler.close.assert_awaited_once_with()
        handler.connection._quic.send_stream_data.assert_called_once_with(
            stream_id=11,
            data=b"",
            end_stream=True,
        )
        handler.transmit.assert_called_once_with()


class TestWebTransportProtocolTermination:
    @pytest.mark.asyncio
    async def test_terminate_ends_stream_and_closes_handler(self, protocol):
        handler = mock_handler()
        protocol.handlers[7] = handler

        await protocol.terminate_handler(7)

        handler.connection._quic.send_stream_data.assert_called_once_with(
            stream_id=11,
            data=b"",
            end_stream=True,
        )
        handler.transmit.assert_called_once_with()
        handler.close.assert_awaited_once_with()
        assert 7 not in protocol.handlers

    @pytest.mark.asyncio
    async def test_terminate_without_control_stream(self, protocol):
        handler = mock_handler(control_stream_id=None)
        protocol.handlers[7] = handler

        await protocol.terminate_handler(7)

        handler.connection._quic.send_stream_data.assert_not_called()
        handler.transmit.assert_not_called()
        handler.close.assert_awaited_once_with()
        assert 7 not in protocol.handlers

    @pytest.mark.asyncio
    async def test_terminate_unknown_handler_is_noop(self, protocol):
        await protocol.terminate_handler(999)

        assert protocol.handlers == {}


class TestWebTransportProtocolClosing:
    @pytest.mark.asyncio
    async def test_close_handler_removes_and_closes_handler(self, protocol):
        handler = mock_handler()
        protocol.handlers[7] = handler

        await protocol.close_handler(7)

        assert 7 not in protocol.handlers
        handler.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_close_handler_is_idempotent(self, protocol):
        handler = mock_handler()
        protocol.handlers[7] = handler

        await protocol.close_handler(7)
        await protocol.close_handler(7)

        handler.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_close_all_handlers(self, protocol):
        first = mock_handler()
        second = mock_handler()
        protocol.handlers = {1: first, 2: second}

        await protocol.close_all_handlers()

        assert protocol.closed is True
        assert protocol.handlers == {}
        first.close.assert_awaited_once_with()
        second.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_close_all_handlers_is_idempotent(self, protocol):
        handler = mock_handler()
        protocol.handlers[7] = handler

        await protocol.close_all_handlers()
        await protocol.close_all_handlers()

        handler.close.assert_awaited_once_with()


class TestWebTransportProtocolConnectStreamLifecycle:
    @pytest.mark.asyncio
    async def test_connect_stream_end_closes_handler(self, protocol):
        handler = mock_handler()
        protocol.handlers[7] = handler
        protocol.close_handler = AsyncMock()

        protocol.http_event_received(
            DataReceived(
                data=b"",
                stream_id=7,
                stream_ended=True,
            )
        )

        tasks = list(protocol.tasks)
        assert len(tasks) == 1

        await asyncio.gather(*tasks)

        protocol.close_handler.assert_awaited_once_with(7)

    @pytest.mark.parametrize(
        ("stream_id", "stream_ended"),
        [
            (7, False),
            (999, True),
        ],
        ids=["unfinished-stream", "unknown-stream"],
    )
    def test_does_not_close_when_not_applicable(
        self,
        protocol,
        stream_id,
        stream_ended,
    ):
        if stream_id == 7:
            protocol.handlers[7] = mock_handler()

        protocol.close_handler = AsyncMock()

        protocol.http_event_received(
            DataReceived(
                data=b"some-data" if not stream_ended else b"",
                stream_id=stream_id,
                stream_ended=stream_ended,
            )
        )

        assert protocol.tasks == set()
        protocol.close_handler.assert_not_awaited()
