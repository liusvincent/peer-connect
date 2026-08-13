from aioquic.h3.connection import H3Connection
from aioquic.h3.events import WebTransportStreamDataReceived, HeadersReceived
from aioquic.quic.events import ProtocolNegotiated, ConnectionTerminated
from aioquic.asyncio import QuicConnectionProtocol
import asyncio

from rooms import RoomManager, RoomError

from messages import (
    ClientRequest, ServerResponse, ServerMessage, 
    ClientRequestBase, CreateRoomRequest, 
    CreateUserRequest, JoinLobbyRequest,
    JoinRoomRequest, LeaveRoomRequest,
    RequestErrorResponse, WebRTCOfferRequest,
    WebRTCReady, MessageErrorResponse,
    ClientEvent, ClientEventBase, 
    EventErrorResponse,
    parse_client_message, serialize_server_message,
)

from meeting import MeetingHandler, MeetingError

from collections.abc import Callable
import traceback
import json


class WebTransportSession:
    """ WebTransport Session Handler:
    Handles webtransport events, requests from the client
    """
    def __init__(
        self,
        connection: H3Connection,
        session_id: int,
        transmit: Callable[[], None],
        room_manager: RoomManager
    ) -> None:
        # transport dependencies
        self.connection = connection
        self.session_id = session_id
        self.transmit = transmit
        self.stream_id: int | None = None

        # session-owned states
        self.meeting = MeetingHandler(room_manager, self.send_message)
        self.closed = False

        # message handling
        self.buffer = b""
        self.message_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.message_worker: asyncio.Task[None] | None = (
            asyncio.create_task(self.process_messages())
        )

    async def handle_event(self, event: WebTransportStreamDataReceived) -> None:
        """ Listens for messages from the WebTransport stream
        appends messages into a queue to be processed by self.message_worker
        """
        # capture stream_id from event
        if self.stream_id is None:
            self.stream_id = event.stream_id

        elif event.stream_id != self.stream_id:
            raise RuntimeError(
                f"Unexpected stream {event.stream_id}; "
                f"expected control stream {self.stream_id}"
            )

        self.buffer += event.data

        while b"\n" in self.buffer:
            message, self.buffer = self.buffer.split(b"\n", 1)

            if message:
                self.message_queue.put_nowait(message)

    async def process_messages(self) -> None:
        """ Function for worker thread to process any queued messages
        """
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
        message = parse_client_message(json.loads(raw_message))
        print(message.type)

        match message:
            case ClientEventBase():
                response = await self.dispatch_event(message)

                if response:
                    self.send_message(response)

            case ClientRequestBase():
                response = await self.dispatch_request(message)
                self.send_message(response)

            case _:
                self.send_message(MessageErrorResponse(
                    message=f"{message.type}-not-implemented"
                ))

    async def dispatch_event(self, event: ClientEvent) -> ServerMessage | None:
        try:
            match event:
                case WebRTCReady():
                    await self.meeting.handle_webrtc_ready()
                    return None
                case _:
                    return EventErrorResponse(
                        event_id=event.event_id,
                        message=f"{event.type}-not-implemented",
                    )

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
        """ Dispatches request to its correct request_handler
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
        """ Send a message through the WebTransport stream
        serialize the message according to Server Message
        """
        if self.closed:
            return

        payload = serialize_server_message(message)
        data = (json.dumps(payload, separators=(",", ":")) + "\n").encode()

        self.connection._quic.send_stream_data(
            stream_id=self.stream_id,
            data=data,
            end_stream=False,
        )

        self.transmit()

    async def close(self) -> None:
        """ Close WebTransport Session:
        - clear worker
        - clear webrtc
        - clear participant
        """
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


class WebTransportProtocol(QuicConnectionProtocol):
    """ QUIC protocol implementation for a WebTransport connection:
    Filters HTTP/3 events from QUIC events,
    instantiates a WebTransport session,
    and forwards relevant events to the session.
    """
    def __init__(self, *args, room_manager: RoomManager, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.http: H3Connection | None = None
        self.handlers: dict[int, WebTransportSession] = {}
        self.room_manager = room_manager

    def quic_event_received(self, event):
        if isinstance(event, ProtocolNegotiated):
            self.http = H3Connection(self._quic, enable_webtransport=True)

        if isinstance(event, ConnectionTerminated):
            print("terminated:", event.error_code, event.reason_phrase)
            asyncio.create_task(self.close_all_handlers())

        if self.http is not None:
            for h3_event in self.http.handle_event(event):
                self.http_event_received(h3_event)

    def http_event_received(self, event):
        if isinstance(event, HeadersReceived):
            headers = dict(event.headers)

            if (headers.get(b":method") == b"CONNECT"
                and headers.get(b":protocol") == b"webtransport"
                and headers.get(b":path") == b"/wt"
            ):
                handler = WebTransportSession(
                    connection=self.http,
                    session_id=event.stream_id,
                    transmit=self.transmit,
                    room_manager = self.room_manager
                )

                self.handlers[event.stream_id] = handler

                self.http.send_headers(
                    stream_id=event.stream_id,
                    headers=[
                        (b":status", b"200"),
                        (b"sec-webtransport-http3-draft", b"draft02"),
                    ],
                )

                print("WebTransport connected")

            else:
                self.http.send_headers(
                    stream_id=event.stream_id,
                    headers=[(b":status", b"404")],
                    end_stream=True,
                )

            self.transmit()

        elif isinstance(event, WebTransportStreamDataReceived):
            asyncio.create_task(self.handle_webtransport_event(event))


    async def handle_webtransport_event(self, event):
        handler = self.handlers.get(event.session_id)

        if handler is None:
            return

        try:
            await handler.handle_event(event)
        except Exception as err:
            print("WebTransport handler failed:", err)
            self.handlers.pop(event.session_id, None)

            await handler.close()

            handler.connection._quic.send_stream_data(
                stream_id=event.stream_id,
                data=b"",
                end_stream=True,
            )
            
            handler.transmit()
            return

        if event.stream_ended:
            self.handlers.pop(event.session_id, None)
            await handler.close()

    async def close_all_handlers(self):
        handlers = list(self.handlers.values())
        self.handlers.clear()

        await asyncio.gather(
            *(handler.close() for handler in handlers),
            return_exceptions=True,
        )
    