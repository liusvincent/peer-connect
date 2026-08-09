export type WebRTCSession = {
  createOffer: (localStream: MediaStream) => Promise<string>;
  createAnswer: (offerSdp: string) => Promise<string>;
  applyAnswer: (sdp: string) => Promise<void>;
  close: () => void;
};

export type RemoteTrackInfo = {
  track: MediaStreamTrack;
  stream: MediaStream | null;
  mid: string | null;
};

type WebRTCSessionOptions = {
  onRemoteTrack: (media: RemoteTrackInfo) => void;
  onConnectionStateChange?: (state: RTCPeerConnectionState) => void;
};

export function createWebRTCSession(
  options: WebRTCSessionOptions,
): WebRTCSession {
  const pc = new RTCPeerConnection();

  let started = false;
  let closed = false;

  pc.addEventListener("track", (event) => {
    options.onRemoteTrack({
      track: event.track,
      stream: event.streams[0] ?? null,
      mid: event.transceiver.mid,
    });
  });

  pc.addEventListener("connectionstatechange", () => {
    options.onConnectionStateChange?.(pc.connectionState);
  });

  async function createOffer(localStream: MediaStream): Promise<string> {
    if (started) {
      throw new Error("WebRTC session has already started");
    }

    started = true;

    try {
      for (const track of localStream.getTracks()) {
        pc.addTrack(track, localStream);
      }

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      if (!pc.localDescription) {
        throw new Error("WebRTC local description was not created");
      }

      return pc.localDescription.sdp;
    } catch (err) {
      close();
      throw new Error("Failed to create WebRTC offer", { cause: err });
    }
  }

  async function createAnswer(offerSdp: string): Promise<string> {
    if (closed) {
      throw new Error("WebRTC session has already closed");
    }

    try {
      await pc.setRemoteDescription({
        type: "offer",
        sdp: offerSdp,
      });

      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);

      if (!pc.localDescription) {
        throw new Error("WebRTC local description was not created");
      }

      return pc.localDescription.sdp;
    } catch (err) {
      close();
      throw new Error("Failed to answer WebRTC offer", { cause: err });
    }
  }

  async function applyAnswer(sdp: string): Promise<void> {
    if (closed) {
      throw new Error("WebRTC session has already closed");
    }

    try {
      await pc.setRemoteDescription({
        type: "answer",
        sdp,
      });
    } catch (err) {
      close();
      throw new Error("Failed to apply WebRTC answer", { cause: err });
    }
  }

  function close(): void {
    if (closed) return;
    closed = true;

    for (const receiver of pc.getReceivers()) {
      receiver.track?.stop();
    }

    pc.close();
  }

  return {
    createOffer,
    createAnswer,
    applyAnswer,
    close,
  };
}
