from aioquic.h3.connection import H3Connection
from aioquic.h3.events import (
    WebTransportStreamDataReceived,
    HeadersReceived,
    DataReceived,
)
from aioquic.quic.events import ProtocolNegotiated, ConnectionTerminated
from aioquic.asyncio import QuicConnectionProtocol
import asyncio

from rooms import RoomManager, RoomError

from pydantic import ValidationError
from messages import (
    ClientRequest,
    ServerResponse,
    ServerMessage,
    ClientRequestBase,
    CreateRoomRequest,
    CreateUserRequest,
    JoinLobbyRequest,
    JoinRoomRequest,
    LeaveRoomRequest,
    RequestErrorResponse,
    WebRTCOfferRequest,
    WebRTCReady,
    MessageErrorResponse,
    ClientEvent,
    ClientEventBase,
    EventErrorResponse,
    parse_client_message,
    serialize_server_message,
)

from meeting import MeetingHandler, MeetingError

from collections.abc import Callable, Awaitable
import traceback
import json


class WebTransportSession:
    """WebTransport Session Handler:
    Handles webtransport events, requests from the client
    """

    def __init__(
        self,
        connection: H3Connection,
        session_id: int,
        transmit: Callable[[], None],
        room_manager: RoomManager,
        request_termination: Callable[[int], Awaitable[None]],
    ) -> None:
        # transport dependencies
        self.connection = connection
        self.session_id = session_id
        self.transmit = transmit
        self.request_termination = request_termination
        self.control_stream_id: int | None = None

        # session-owned states
        self.meeting = MeetingHandler(room_manager, self.send_message, self.terminate)
        self.closed = False
        self.terminated = False

        # message handling
        self.event_lock = asyncio.Lock()
        self.buffer = b""
        self.message_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.message_worker: asyncio.Task[None] | None = asyncio.create_task(
            self.process_messages()
        )

    async def handle_event(self, event: WebTransportStreamDataReceived) -> None:
        """Listens for messages from the WebTransport stream
        appends messages into a queue to be processed by self.message_worker
        """
        async with self.event_lock:
            if self.closed:
                return

            # capture stream_id from event
            if self.control_stream_id is None:
                self.control_stream_id = event.stream_id

            elif event.stream_id != self.control_stream_id:
                raise RuntimeError(
                    f"Unexpected stream {event.stream_id}; "
                    f"expected control stream {self.control_stream_id}"
                )

            self.buffer += event.data

            while b"\n" in self.buffer:
                message, self.buffer = self.buffer.split(b"\n", 1)

                if message:
                    self.message_queue.put_nowait(message)

    async def process_messages(self) -> None:
        """Function for worker thread to process any queued messages"""
        while not self.closed:
            message = await self.message_queue.get()

            try:
                await self.dispatch_message(message)
            except asyncio.CancelledError:
                raise
            except Exception as err:
                print(f"Message handler failed: {err}")
                traceback.print_exc()
            finally:
                self.message_queue.task_done()

    async def dispatch_message(self, raw_message: bytes) -> None:
        try:
            message = parse_client_message(json.loads(raw_message))
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError):
            self.send_message(MessageErrorResponse(message="invalid-message"))
            return
    
        print(message.type)

        try:
            match message:
                case ClientEventBase():
                    response = await self.dispatch_event(message)

                    if response:
                        self.send_message(response)

                case ClientRequestBase():
                    response = await self.dispatch_request(message)
                    self.send_message(response)

        finally:
            if self.meeting.closed:
                await self.terminate()

    async def dispatch_event(self, event: ClientEvent) -> ServerMessage | None:
        try:
            match event:
                case WebRTCReady():
                    await self.meeting.handle_webrtc_ready()
                    return None

        except (RoomError, MeetingError) as error:
            return EventErrorResponse(
                event_id=event.event_id,
                message=error.code,
            )

        except Exception:
            traceback.print_exc()
            return EventErrorResponse(
                event_id=event.event_id,
                message="internal-server-error",
            )

    async def dispatch_request(self, request: ClientRequest) -> ServerResponse:
        """Dispatches request to its correct request_handler
        returns a ServerResponse to be sent back to the client
        """
        try:
            match request:
                case WebRTCOfferRequest():
                    return await self.meeting.handle_webrtc_offer(request)
                case CreateUserRequest():
                    return await self.meeting.handle_create_user(request)
                case CreateRoomRequest():
                    return await self.meeting.handle_create_room(request)
                case JoinLobbyRequest():
                    return await self.meeting.handle_join_lobby(request)
                case JoinRoomRequest():
                    return await self.meeting.handle_join_room(request)
                case LeaveRoomRequest():
                    return await self.meeting.handle_leave_room(request)
                case _:
                    return RequestErrorResponse(
                        request_id=request.request_id,
                        message=f"{request.type}-not-implemented",
                    )

        except (RoomError, MeetingError) as error:
            return RequestErrorResponse(
                request_id=request.request_id,
                message=error.code,
            )

        except Exception:
            traceback.print_exc()
            return RequestErrorResponse(
                request_id=request.request_id,
                message="internal-server-error",
            )

    def send_message(self, message: ServerMessage) -> None:
        """Send a message through the WebTransport stream
        serialize the message according to Server Message
        """
        if self.closed:
            return

        if self.control_stream_id is None:
            raise RuntimeError("Control stream has not been established")

        payload = serialize_server_message(message)
        data = (json.dumps(payload, separators=(",", ":")) + "\n").encode()

        self.connection._quic.send_stream_data(
            stream_id=self.control_stream_id,
            data=data,
            end_stream=False,
        )

        self.transmit()

    async def close(self) -> None:
        """Release resources owned by this session:
        - clear worker
        - clear webrtc
        - clear participant
        """
        async with self.event_lock:
            if self.closed:
                return

            self.closed = True

            worker = self.message_worker
            self.message_worker = None

            if worker and worker is not asyncio.current_task():
                worker.cancel()
                await asyncio.gather(worker, return_exceptions=True)

            try:
                await self.meeting.close()
            except Exception as err:
                print(f"Meeting cleanup failed: {err}")
                traceback.print_exc()

    async def terminate(self) -> None:
        if self.closed or self.terminated:
            return

        self.terminated = True

        try:
            await self.request_termination(self.session_id)
        except Exception:
            self.terminated = False
            raise


class WebTransportProtocol(QuicConnectionProtocol):
    """QUIC protocol implementation for a WebTransport connection:
    Filters HTTP/3 events from QUIC events,
    instantiates a WebTransport session,
    and forwards relevant events to the session.
    """

    def __init__(self, *args, room_manager: RoomManager, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.http: H3Connection | None = None
        self.handlers: dict[int, WebTransportSession] = {}
        self.room_manager = room_manager
        self.tasks: set[asyncio.Task] = set()
        self.closed = False

    async def heartbeat(self) -> None:
        try:
            while not self.closed:
                await asyncio.sleep(20)
                await self.ping()
        except asyncio.CancelledError:
            raise
        except ConnectionError:
            await self.close_all_handlers()

    def quic_event_received(self, event) -> None:
        if isinstance(event, ProtocolNegotiated):
            self.http = H3Connection(self._quic, enable_webtransport=True)
            self.spawn(self.heartbeat())

        if isinstance(event, ConnectionTerminated):
            print("terminated:", event.error_code, event.reason_phrase)
            self.spawn(self.close_all_handlers())

        if self.http is not None:
            for h3_event in self.http.handle_event(event):
                self.http_event_received(h3_event)

    def http_event_received(self, event) -> None:
        if isinstance(event, HeadersReceived):
            headers = dict(event.headers)

            if (
                headers.get(b":method") == b"CONNECT"
                and headers.get(b":protocol") == b"webtransport"
                and headers.get(b":path") == b"/wt"
            ):
                handler = WebTransportSession(
                    connection=self.http,
                    session_id=event.stream_id,
                    transmit=self.transmit,
                    room_manager=self.room_manager,
                    request_termination=self.terminate_handler,
                )

                self.handlers[event.stream_id] = handler

                self.http.send_headers(
                    stream_id=event.stream_id,
                    headers=[
                        (b":status", b"200"),
                        (b"sec-webtransport-http3-draft", b"draft02"),
                    ],
                )

                print("WebTransport Session Created: ", event.stream_id)

            else:
                self.http.send_headers(
                    stream_id=event.stream_id,
                    headers=[(b":status", b"404")],
                    end_stream=True,
                )

            self.transmit()

        elif isinstance(event, WebTransportStreamDataReceived):
            self.spawn(self.handle_webtransport_event(event))

        elif (
            isinstance(event, DataReceived)
            and event.stream_ended
            and event.stream_id in self.handlers
        ):
            self.spawn(self.close_handler(event.stream_id))

    def spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def handle_webtransport_event(self, event) -> None:
        handler = self.handlers.get(event.session_id)

        if handler is None:
            return

        try:
            await handler.handle_event(event)
        except Exception as err:
            print(f"WebTransport Session {event.session_id} Failed: {err}")

            await self.close_handler(event.session_id)

            handler.connection._quic.send_stream_data(
                stream_id=event.stream_id,
                data=b"",
                end_stream=True,
            )

            handler.transmit()
            return

        if event.stream_ended:
            await handler.message_queue.join()
            await self.close_handler(event.session_id)

    async def close_handler(self, session_id: int) -> None:
        print("Webtransport Session Ended", session_id)

        handler = self.handlers.pop(session_id, None)

        if handler is None:
            return

        try:
            await handler.close()
        except Exception as err:
            print(f"Handler {session_id} cleanup failed: {err}")

    async def close_all_handlers(self):
        if self.closed:
            return

        self.closed = True

        handlers = list(self.handlers.values())
        self.handlers.clear()

        await asyncio.gather(
            *(handler.close() for handler in handlers),
            return_exceptions=True,
        )

    async def terminate_handler(self, session_id: int) -> None:
        handler = self.handlers.get(session_id)

        if handler is None:
            return

        if handler.control_stream_id is not None:
            handler.connection._quic.send_stream_data(
                stream_id=handler.control_stream_id,
                data=b"",
                end_stream=True,
            )
            handler.transmit()

        await self.close_handler(session_id)
