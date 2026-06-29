from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from webtransport import WebTransportHandler

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")