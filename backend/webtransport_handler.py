from aioquic.h3.connection import H3Connection
from aioquic.h3.events import WebTransportStreamDataReceived
import asyncio

from rooms import Participant, RoomManager, RoomError

from messages import (
    ClientRequest, ServerResponse,
    ClientRequestBase,
    CreateRoomRequest, 
    CreateUserRequest,
    JoinLobbyRequest,
    JoinRoomRequest,
    LeaveRoomRequest,
    RequestErrorResponse,
    WebRTCOfferRequest,
    WebRTCRenegotiationAnswer,
    WebRTCReady,
    ServerMessage,
    parse_client_message, serialize_server_message,
)

import request_handler

from media_handler import MediaHandler

from dataclasses import dataclass
from collections.abc import Callable
import traceback
import json


class WebTransportHandler:
    """ WebTransport Session Handler:
    Handles webtransport events, requests from the client
    also owns the participant and WebRTC resources associated with the session
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

        self.room_manager = room_manager

        # session-owned states
        self.closed = False

        self.participant: Participant | None = None
        self.media: MediaHandler | None = None

        self.buffer = b""
        self.buffer_lock = asyncio.Lock()
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

        async with self.buffer_lock:
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
                await self.handle_message(message)
            except asyncio.CancelledError:
                raise
            except Exception as err:
                print(f"Message handler failed: {err}")
                traceback.print_exc()
            finally:
                self.message_queue.task_done()

    async def handle_message(self, raw_message: bytes) -> None:
        message = parse_client_message(json.loads(raw_message))

        match message:
            case WebRTCReady():
                await self.media.handle_webrtc_ready()

            case WebRTCRenegotiationAnswer():
                print("received webrtc renegotiation")
                await self.media.handle_renegotiation_answer(message)
                print("webrtc renegotiated")

            case ClientRequestBase():
                response = await self.dispatch_request(message)
                self.send_message(response)

    async def dispatch_request(self, request: ClientRequest) -> ServerResponse:
        """ Dispatches request to its correct request_handler
        returns a ServerResponse object to be sent back to the client
        """
        try:
            match request:
                case WebRTCOfferRequest():
                    return await request_handler.handle_webrtc_offer(self, request)
                case CreateUserRequest():
                    return await request_handler.handle_create_user(self, request)
                case CreateRoomRequest():
                    return await request_handler.handle_create_room(self, request)
                case JoinLobbyRequest():
                    return await request_handler.handle_join_lobby(self, request)
                case JoinRoomRequest():
                    return await request_handler.handle_join_room(self, request)
                case LeaveRoomRequest():
                    return await request_handler.handle_leave_room(self, request)
                case _:
                    return await request_handler.handle_not_implemented(request)
                
        except (RoomError, request_handler.UserError) as error:
            return RequestErrorResponse(
                request_id=request.request_id,
                message=error.code,
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
        """ Close WebTransport Session
        """
        if self.closed:
            return

        self.closed = True

        worker = self.message_worker
        self.message_worker = None

        if worker and worker is not asyncio.current_task():
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)

        if self.media:
            try:
                await self.media.close()
            except Exception as err:
                print(f"Media cleanup failed: {err}")
        
        if self.participant and self.participant.room_id:
            try:
                await self.room_manager.leave_room(
                    self.participant.id,
                    self.participant.room_id,
                )
                
            except RoomError as err:
                print(f"Session cleanup skipped: {err.code}")