""" Personal Notes to keep track:
WebTransport.py contains code for signaling between front and backend

There is one server controlling everything with multiple handlers,
a handler for each client connection

Server controls every room with one RoomManager

What can each client do:
- They can join/leave a room
- Kick someone
- Accept stream of others' webcam
- Send stream of their webcam
- Use the room's chat

What the server can do:
- Start a room
- End a room
"""

from aioquic.h3.connection import H3Connection, H3_ALPN
from aioquic.h3.events import WebTransportStreamDataReceived, HeadersReceived
from aioquic.quic.events import ProtocolNegotiated, ConnectionTerminated
from aioquic.asyncio import QuicConnectionProtocol, serve
import asyncio

from webrtc import WebRTCSession
from rooms import Participant, RoomManager

from uuid import uuid4
from typing import Callable
import json

class WebTransportHandler:
    """Handles a given WebTransport session
    """
    def __init__(
        self,
        connection: H3Connection,
        stream_id: int,
        transmit: Callable[[], None],
        room_manager: RoomManager
    ) -> None:
        self.connection = connection
        self.stream_id = stream_id
        self.transmit = transmit
        
        self.buffer = b""
        self.closed = False
        self.event_lock = asyncio.Lock()

        self.webrtc: WebRTCSession | None = None
        self.participant: Participant | None = None
        self.room_manager = room_manager

    async def handle_event(self, event) -> None:
        if not isinstance(event, WebTransportStreamDataReceived):
            return
        async with self.event_lock:
            self.buffer += event.data
            while b"\n" in self.buffer:
                raw_message, self.buffer = self.buffer.split(b"\n", 1)
                if not raw_message:
                    continue
                try:
                    message = json.loads(raw_message.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as err:
                    print("Invalid JSON:", err)
                    continue

                if not isinstance(message, dict):
                    print("Message must be an object:", message)
                    continue

                await self.handle_message(message, event.stream_id)

    async def handle_message(self, message: dict, stream_id: int) -> None:
        match message.get("type"):
            case "webrtc-offer":
                sdp = message.get("sdp")
                if not isinstance(sdp, str):
                    self.send_message(stream_id, {
                        "type": "request-error",
                        "request_id": message.get("request_id"),
                        "message": "invalid-webrtc-offer",
                    })
                    return
                if self.webrtc is None or self.webrtc.closed:
                    self.webrtc = WebRTCSession()
                try:
                    answer = await self.webrtc.handle_offer(sdp)
                except Exception:
                    await self.webrtc.close()
                    self.webrtc = None
                    raise

                self.send_message(stream_id, {
                    "type": answer["type"],
                    "request_id": message.get("request_id"),
                    "sdp": answer["sdp"],
                })

            case "join-room":
                # room_id = message.get("room_id")
                # self.participant = Participant(
                #     id=uuid4(),
                #     name="test-name",
                #     stream_id=stream_id,
                #     send=self.send_message,
                #     room_manager=self.room_manager
                # )
                # await self.room_manager.join_room(self.participant, room_id)
                self.send_message(stream_id, {
                    "type": "joined-room",
                    "request_id": message.get("request_id"),
                    "room_id": "testid",
                })

            case "create-room":
                # self.participant = Participant(
                #     id=uuid4(),
                #     name="test-name",
                #     stream_id=stream_id,
                #     send=self.send_message,
                #     room_manager=self.room_manager
                # )
                # await self.room_manager.join_room(self.participant, room_id)
                self.send_message(stream_id, {
                    "type": "joined-room",
                    "request_id": message.get("request_id"),
                    "room_id": "testid",
                })

            case "leave-room":
                # participant_id = message.get("participant_id")
                # room_id = message.get("room_id")
                # await self.room_manager.leave(participant_id, room_id)
                pass

            case _:
                print("Unknown message type:", message.get("type"))
                self.send_message(stream_id, {
                    "type": "error",
                    "request_id": message.get("request_id"),
                    "message": "unknown-message-type",
                })

    def send_message(self, stream_id: int, message: dict):
        if self.closed:
            return

        data = (json.dumps(message) + "\n").encode("utf-8")

        self.connection._quic.send_stream_data(
            stream_id=stream_id,
            data=data,
            end_stream=False,
        )
        self.transmit()

    async def close(self):
        if self.closed:
            return

        self.closed = True

        if self.webrtc is not None:
            await self.webrtc.close()
            self.webrtc = None


        self.room_manager.leave(self.participant.id, self.participant.room_id)


class WebTransportProtocol(QuicConnectionProtocol):
    """QUIC protocol implementation for the webTransport server
    manages the signaling connection front to back end
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.http: H3Connection = None
        self.handlers: set[WebTransportHandler] = {} # check if type hint is right
        self.room_manager = RoomManager()

    def quic_event_received(self, event):
        """Function is called whenever something happens on the QUIC connection
        """
        print("Quic Event: ", type(event).__name__) # for debugging

        if isinstance(event, ProtocolNegotiated):
            self.http = H3Connection(self._quic, enable_webtransport=True)

        if isinstance(event, ConnectionTerminated):
            print("terminated:", event.error_code, event.reason_phrase)
            asyncio.create_task(self.close_all_handlers())

        if self.http is not None:
            for h3_event in self.http.handle_event(event):
                self.http_event_received(h3_event)

    def http_event_received(self, event):
        """QUIC event is a http event
        """
        print("H3 event:", type(event).__name__) # for debugging

        if isinstance(event, HeadersReceived):
            headers = dict(event.headers)
            print("headers:", headers) # for debugging

            if (headers.get(b":method") == b"CONNECT"
                and headers.get(b":protocol") == b"webtransport"
                and headers.get(b":path") == b"/wt"
            ):
                handler = WebTransportHandler(
                    connection=self.http,
                    stream_id=event.stream_id,
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
                print("WebTransport connected") # for debugging
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
        """http event is webtransport event
        """
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