import { sendMessage } from "./webtransport";

let pc: RTCPeerConnection | null = null;

export async function startWebRTC(
  onRemoteStream: (stream: MediaStream) => void,
) {
  if (pc && pc.connectionState !== "closed") {
    console.log("WebRTC already started");
    return;
  }

  const newPc = new RTCPeerConnection();
  pc = newPc;

  const remoteStream = new MediaStream();

  try {
    newPc.addEventListener("track", (event) => {
      remoteStream.addTrack(event.track);
      onRemoteStream(remoteStream)
    });

    newPc.addTransceiver("video", { direction: "recvonly" });

    const offer = await newPc.createOffer();
    await newPc.setLocalDescription(offer);

    await sendMessage({
      type: "webrtc-offer",
      sdp: newPc.localDescription!.sdp,
    });
  } catch (err) {
    newPc.close();
    if (pc === newPc) {
      pc = null;
    }
    throw err;
  }
}

export async function handleWebRTCAnswer(sdp: string) {
  if (!pc) {
    throw new Error("Peer Connection has not been created");
  }
  await pc.setRemoteDescription({
    type: "answer",
    sdp,
  });
  console.log("WebRTC answer applied");
}
