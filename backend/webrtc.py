from aiortc import RTCPeerConnection, RTCSessionDescription, RTCRtpSender

import queue
import threading

from ball import BallVideoTrack, ball_worker

from typing import Callable

import asyncio


class WebRTCSession:
    def __init__(self, config, on_coordinates: Callable[[int, int], None]):
        self.pc = RTCPeerConnection()
        self.frame_queue = queue.Queue(maxsize=3)
        self.stop_event = threading.Event()
        self.worker = None

        self.config = config
        self.on_coordinates = on_coordinates

        self.track = BallVideoTrack(self.frame_queue)

        self.closed = False

        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print("WebRTC state:", self.pc.connectionState)

            if self.pc.connectionState in ("failed", "closed"):
                await self.close()

    async def handle_offer(self, sdp: str) -> dict:
        if self.worker is None:
            self.worker = threading.Thread(
                target=ball_worker,
                args=(
                    self.frame_queue,
                    self.stop_event,
                    self.config,
                    self.on_coordinates,
                ),
                daemon=True,
            )
            self.worker.start()

        offer = RTCSessionDescription(sdp=sdp, type="offer")
        await self.pc.setRemoteDescription(offer)

        sender = self.pc.addTrack(self.track)

        transceiver = next(t for t in self.pc.getTransceivers() if t.sender == sender)

        codecs = RTCRtpSender.getCapabilities("video").codecs
        h264_codecs = [
            codec for codec in codecs if codec.mimeType.lower() == "video/h264"
        ]

        transceiver.setCodecPreferences(h264_codecs)

        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)

        return {
            "type": "answer",
            "sdp": self.pc.localDescription.sdp,
        }

    async def close(self):
        if self.closed:
            return

        self.closed = True
        self.stop_event.set()
        self.track.stop()
        await self.pc.close()

        if self.worker and self.worker.is_alive():
            await asyncio.to_thread(self.worker.join, 2)
