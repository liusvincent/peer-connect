from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from aioquic.quic.configuration import QuicConfiguration
from aioquic.h3.connection import H3_ALPN
from aioquic.asyncio import serve

import asyncio

from webtransport import WebTransportProtocol

# front
# app = FastAPI()
# app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

# back
async def main():
    host = "localhost"
    port = 4433

    configuration = QuicConfiguration(is_client=False, alpn_protocols=H3_ALPN)
    configuration.load_cert_chain("cert.pem", "key.pem")

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