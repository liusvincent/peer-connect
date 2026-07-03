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

  newPc.addEventListener("connectionstatechange", () => {
    if (newPc.connectionState === "failed") {
      closePeerConnection(newPc);
    }
  });

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
    closePeerConnection(newPc);
    throw err;
  }
}

export async function handleWebRTCAnswer(sdp: string) {
  const currentPc = pc;
  
  if (!currentPc) {
    throw new Error("Peer Connection has not been created");
  }
  try {
    await currentPc.setRemoteDescription({
      type: "answer",
      sdp,
    });
    console.log("WebRTC answer applied");
  } catch (err) {
    closePeerConnection(currentPc);
    throw err;
  }
}

function closePeerConnection(
  connection: RTCPeerConnection | null,
) {
  if (!connection) return;

  connection.getReceivers().forEach((receiver) => {
    receiver.track?.stop();
  });

  connection.close();

  if (pc === connection) {
    pc = null;
  }
}

export function disconnectWebRTC() {
  closePeerConnection(pc);
}