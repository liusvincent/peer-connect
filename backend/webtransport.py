from aioquic.h3.connection import H3Connection, H3_ALPN
from aioquic.h3.events import WebTransportStreamDataReceived, HeadersReceived

from aioquic.asyncio import QuicConnectionProtocol, serve
import asyncio

from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import ProtocolNegotiated, ConnectionTerminated 


from typing import Callable

import json

class WebTransportHandler:
    """ Handles a webTransport session within a connection
    """
    def __init__(
        self,
        connection: H3Connection,
        stream_id: int,
        transmit: Callable[[], None],
    ):
        self.connection = connection
        self.stream_id = stream_id
        self.transmit = transmit

    def handle_event(self, event):
        if isinstance(event, WebTransportStreamDataReceived):
            print("session:", event.session_id)
            print("stream:", event.stream_id)
            self.handle_message(event.data)

    def handle_message(self, data: bytes):
        text = data.decode("utf-8")
        message = json.loads(text)
        print("message", message)

class WebTransportProtocol(QuicConnectionProtocol):
    """ QUIC protocol implementation for the webTransport server
    manages the connection of front to back end
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.http = None
        self.handlers = {}

    def quic_event_received(self, event):
        """ Function is called whenever something happens on the QUIC connection
        """
        print("Quic Event: ", type(event).__name__)
        
        if isinstance(event, ConnectionTerminated):
            print("terminated:", event.error_code, event.reason_phrase)

        if isinstance(event, ProtocolNegotiated):
            self.http = H3Connection(self._quic, enable_webtransport=True)
        
        if self.http is not None:
            for h3_event in self.http.handle_event(event):
                self.http_event_received(h3_event)

    def http_event_received(self, event):
        """ Handles HTTP/3 events
        """
        print("H3 event:", type(event).__name__)

        if isinstance(event, HeadersReceived):
            headers = dict(event.headers)
            print("headers:", headers)

            if (headers.get(b":method") == b"CONNECT"
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
                    headers=[(b":status", b"200"),
                             (b"sec-webtransport-http3-draft", b"draft02")],
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
            handler = self.handlers.get(event.session_id)
            if handler is not None:
                handler.handle_event(event)
    
async def main():
    host = "localhost"
    port = 4433

    configuration = QuicConfiguration(is_client=False, alpn_protocols=H3_ALPN)
    configuration.load_cert_chain("localhost+2.pem", "localhost+2-key.pem")

    await serve(host=host, port=port, configuration=configuration, create_protocol=WebTransportProtocol)
    print(f"WebTransport Server running on https://{host}:{port}/wt")
    
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
