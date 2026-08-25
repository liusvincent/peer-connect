from aioquic.quic.configuration import QuicConfiguration
from aioquic.h3.connection import H3_ALPN
from aioquic.asyncio import serve

import asyncio
from functools import partial

from webtransport import WebTransportProtocol
from rooms import RoomManager

import os


async def main():
    host = os.getenv("PEER_CONNECT_HOST", "127.0.0.1")
    port = int(os.getenv("PEER_CONNECT_PORT", "4433"))
    cert_path = os.getenv("PEER_CONNECT_CERT_PATH", "cert.pem")
    key_path = os.getenv("PEER_CONNECT_KEY_PATH", "key.pem")

    configuration = QuicConfiguration(is_client=False, alpn_protocols=H3_ALPN)
    configuration.load_cert_chain(cert_path, key_path)

    room_manager = RoomManager()

    server = await serve(
        host=host,
        port=port,
        configuration=configuration,
        create_protocol=partial(WebTransportProtocol, room_manager=room_manager),
    )
    print(f"WebTransport Server Running on https://{host}:{port}/wt")

    try:
        await asyncio.Event().wait()
    finally:
        print("Shutting Down WebTransport Server...")

        server.close()
        await room_manager.close()

        print("WebTransport Server Ended")


if __name__ == "__main__":
    asyncio.run(main())