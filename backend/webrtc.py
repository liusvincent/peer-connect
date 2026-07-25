from aiortc import RTCPeerConnection, RTCSessionDescription, RTCRtpSender

class WebRTCSession:
    def __init__(self) -> None:
        self.pc = RTCPeerConnection()
        self.closed = False

        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print("WebRTC state:", self.pc.connectionState)

            if self.pc.connectionState in ("failed", "closed"):
                await self.close()

    async def handle_offer(self, sdp: str) -> dict:

        offer = RTCSessionDescription(sdp=sdp, type="offer")
        await self.pc.setRemoteDescription(offer)

        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)

        return {
            "type": "webrtc-answer",
            "sdp": self.pc.localDescription.sdp,
        }

    async def close(self) -> None:
        if self.closed:
            return

        self.closed = True
        await self.pc.close()
