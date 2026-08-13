import type { MediaHint } from "../types/models";

export type RemoteTrackInfo = {
  track: MediaStreamTrack;
  stream: MediaStream | null;
  mid: string | null;
};

type WebRTCSessionOptions = {
  onRemoteTrack: (media: RemoteTrackInfo) => void;
  onConnectionStateChange?: (state: RTCPeerConnectionState) => void;
};

export interface WebRTCSession {
  addLocalStream: (localStream: MediaStream) => void;
  handleReceivingTransceivers: (media: MediaHint[]) => void;
  createOffer: () => Promise<string>;
  applyAnswer: (sdp: string) => Promise<void>;
  close: () => void;
};

export function createWebRTCSession(options: WebRTCSessionOptions): WebRTCSession {
  const pc = new RTCPeerConnection();

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

  let localStreamAdded = false;

  function addLocalStream(localStream: MediaStream): void {
    if (closed) {
      throw new Error("WebRTC session has already closed");
    }

    if (localStreamAdded) {
      return;
    }
    
    for (const track of localStream.getTracks()) {
      pc.addTrack(track, localStream);
    }

    localStreamAdded = true;
  }

  // const preparedSubscriptions = new Set<string>();
  const recvTransceivers = new Map<string, RTCRtpTransceiver>();

  function handleReceivingTransceivers(media: MediaHint[]): void {
    if (closed) {
      throw new Error("WebRTC session has already closed");
    }

    const desiredKeys = new Set(
      media.map((item) => `${item.participant_id}:${item.track_id}`),
    );

    // Remove subscriptions that the server no longer advertises.
    for (const [key, transceiver] of recvTransceivers) {
      if (!desiredKeys.has(key)) {
        transceiver.receiver.track?.stop();
        transceiver.stop();
        recvTransceivers.delete(key);
      }
    }

    // Add newly advertised subscriptions.
    for (const item of media) {
      const key = `${item.participant_id}:${item.track_id}`;

      if (!recvTransceivers.has(key)) {
        const transceiver = pc.addTransceiver(item.kind, {
          direction: "recvonly",
        });

        recvTransceivers.set(key, transceiver);
      }
    }
  }

  async function createOffer(): Promise<string> {
    try {
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
    addLocalStream,
    handleReceivingTransceivers,
    createOffer,
    applyAnswer,
    close,
  };
}
