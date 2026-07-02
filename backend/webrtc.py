from aiortc import RTCPeerConnection, RTCSessionDescription, RTCRtpSender

import queue
import threading

from ball import BallVideoTrack, ball_worker

class WebRTCSession:
    def __init__(self):
        self.pc = RTCPeerConnection()
        self.frame_queue = queue.Queue(maxsize=3)
        self.stop_event = threading.Event()
        self.worker = None

        self.track = BallVideoTrack(self.frame_queue)

    async def handle_offer(self, sdp: str) -> dict:
        if self.worker is None:
            self.worker = threading.Thread(
                target=ball_worker,
                args=(self.frame_queue, self.stop_event),
                daemon=True,
            )
            self.worker.start()
        
        offer = RTCSessionDescription(sdp=sdp, type="offer")
        await self.pc.setRemoteDescription(offer)
        
        sender = self.pc.addTrack(self.track)

        transceiver = next(
            t for t in self.pc.getTransceivers()
            if t.sender == sender
        )

        codecs = RTCRtpSender.getCapabilities("video").codecs
        h264_codecs = [
            codec for codec in codecs
            if codec.mimeType.lower() == "video/h264"
        ]

        transceiver.setCodecPreferences(h264_codecs)

        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)

        return {
            "type": "answer",
            "sdp": self.pc.localDescription.sdp,
        }
    
    async def close(self):
        self.stop_event.set()
        await self.pc.close()
