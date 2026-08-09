from aioquic.h3.connection import H3Connection
from aioquic.h3.events import WebTransportStreamDataReceived, HeadersReceived
from aioquic.quic.events import ProtocolNegotiated, ConnectionTerminated
from aioquic.asyncio import QuicConnectionProtocol
import asyncio

from webtransport_handler import WebTransportHandler

from rooms import RoomManager

class WebTransportProtocol(QuicConnectionProtocol):
    """ QUIC protocol implementation for a WebTransport connection:
    Filters HTTP/3 events from QUIC events,
    instantiates a WebTransport session,
    and forwards relevant events to the session.
    """
    def __init__(self, *args, room_manager: RoomManager, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.http: H3Connection | None = None
        self.handlers: dict[int, WebTransportHandler] = {}
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
                handler = WebTransportHandler(
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

                print("WebTransport connected") # debug

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