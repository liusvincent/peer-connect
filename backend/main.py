from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from aioquic.quic.configuration import QuicConfiguration
from aioquic.h3.connection import H3_ALPN
from aioquic.asyncio import serve

import asyncio
from functools import partial

from webtransport_protocol import WebTransportProtocol
from rooms import RoomManager


# front
# app = FastAPI()
# app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

# back
async def main():
    host = "localhost"
    port = 4433

    configuration = QuicConfiguration(is_client=False, alpn_protocols=H3_ALPN)
    configuration.load_cert_chain("cert.pem", "key.pem")

    room_manager = RoomManager()

    server = await serve(
        host=host,
        port=port,
        configuration=configuration,
        create_protocol=partial(
            WebTransportProtocol,
            room_manager=room_manager,
        ),
    )
    print(f"WebTransport Server running on https://{host}:{port}/wt")

    try:
        await asyncio.Event().wait()
    finally:
        print("Shutting down WebTransport Server...")
        server.close()


if __name__ == "__main__":
    asyncio.run(main())