from aioquic.h3.connection import H3Connection, H3_ALPN
from aioquic.h3.events import WebTransportStreamDataReceived, HeadersReceived

from aioquic.asyncio import QuicConnectionProtocol, serve
import asyncio

from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import ProtocolNegotiated, ConnectionTerminated

from webrtc import WebRTCSession, StreamConfig

from typing import Callable

import json


class WebTransportHandler:
    """Handles a webTransport session within a connection"""

    def __init__(
        self,
        connection: H3Connection,
        stream_id: int,
        transmit: Callable[[], None],
    ):
        self.connection = connection
        self.stream_id = stream_id
        self.transmit = transmit
        self.webrtc = None
        self.buffer = b""
        self.config = StreamConfig()
        self.closed = False
        self.event_lock = asyncio.Lock()

    async def handle_event(self, event):
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

    async def handle_message(self, message: dict, stream_id: int):
        match message.get("type"):
            case "webrtc-offer":
                sdp = message.get("sdp")

                if not isinstance(sdp, str):
                    print("Invalid WebRTC offer:", message)
                    return

                if self.webrtc is None or self.webrtc.closed:
                    loop = asyncio.get_running_loop()

                    def on_coordinates(x: int, y: int) -> None:
                        loop.call_soon_threadsafe(
                            self.send_message,
                            stream_id,
                            {
                                "type": "coordinates",
                                "x": x,
                                "y": y,
                            },
                        )

                    self.webrtc = WebRTCSession(self.config, on_coordinates)

                try:
                    answer = await self.webrtc.handle_offer(sdp)
                except Exception:
                    await self.webrtc.close()
                    self.webrtc = None
                    raise

                self.send_message(stream_id, answer)

            case "set-fps":
                fps = message.get("fps")
                if isinstance(fps, int) and 1 <= fps <= 30:
                    self.config.fps = fps

            case _:
                print("Unknown Message")

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


class WebTransportProtocol(QuicConnectionProtocol):
    """QUIC protocol implementation for the webTransport server
    manages the connection of front to back end
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.http = None
        self.handlers = {}

    def quic_event_received(self, event):
        """Function is called whenever something happens on the QUIC connection"""
        print("Quic Event: ", type(event).__name__)

        if isinstance(event, ProtocolNegotiated):
            self.http = H3Connection(self._quic, enable_webtransport=True)

        if isinstance(event, ConnectionTerminated):
            print("terminated:", event.error_code, event.reason_phrase)
            asyncio.create_task(self.close_all_handlers())

        if self.http is not None:
            for h3_event in self.http.handle_event(event):
                self.http_event_received(h3_event)

    async def close_all_handlers(self):
        handlers = list(self.handlers.values())
        self.handlers.clear()

        await asyncio.gather(
            *(handler.close() for handler in handlers),
            return_exceptions=True,
        )

    def http_event_received(self, event):
        """Handles HTTP/3 events"""
        print("H3 event:", type(event).__name__)

        if isinstance(event, HeadersReceived):
            headers = dict(event.headers)
            print("headers:", headers)

            if (
                headers.get(b":method") == b"CONNECT"
                and headers.get(b":protocol") == b"webtransport"
                and headers.get(b":path") == b"/wt"
            ):
                handler = WebTransportHandler(
                    connection=self.http,
                    stream_id=event.stream_id,
                    transmit=self.transmit,
                )
                self.handlers[event.stream_id] = handler
                self.http.send_headers(
                    stream_id=event.stream_id,
                    headers=[
                        (b":status", b"200"),
                        (b"sec-webtransport-http3-draft", b"draft02"),
                    ],
                )
                self.transmit()
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


async def main():
    host = "localhost"
    port = 4433

    configuration = QuicConfiguration(is_client=False, alpn_protocols=H3_ALPN)
    configuration.load_cert_chain("localhost+2.pem", "localhost+2-key.pem")

    await serve(
        host=host,
        port=port,
        configuration=configuration,
        create_protocol=WebTransportProtocol,
    )
    print(f"WebTransport Server running on https://{host}:{port}/wt")

    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
