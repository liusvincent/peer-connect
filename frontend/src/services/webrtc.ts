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
  const pc = new RTCPeerConnection({
    iceServers: [
      { urls: "stun:stun.l.google.com:19302" }
    ]
  });

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

  pc.addEventListener("icegatheringstatechange", () => {
    console.log("ICE gathering state:", pc.iceGatheringState);
  });

  pc.addEventListener("iceconnectionstatechange", () => {
    console.log("ICE connection state:", pc.iceConnectionState);
  });

  pc.addEventListener("icecandidate", (event) => {
    console.log("ICE candidate:", event.candidate?.candidate ?? "complete");
  });

  pc.addEventListener("icecandidateerror", (event) => {
    console.error("ICE candidate error:", event);
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

  type RecvSlot = {
    transceiver: RTCRtpTransceiver;
    kind: "audio" | "video";
    subscriptionKey: string | null;
  }

  const recvSlots: RecvSlot[] = [];
  const activeByKey = new Map<string, RecvSlot>();

  function releaseSlot(key: string): void {
    const slot = activeByKey.get(key);
    if (!slot) return;

    slot.transceiver.direction = "inactive"
    slot.subscriptionKey = null;
    activeByKey.delete(key);
  }

  function acquireSlot(key: string, kind: "audio" | "video"): RecvSlot {
    const existing = activeByKey.get(key);
    if (existing) return existing;

    let slot = recvSlots.find(
      (candidate) => 
        candidate.subscriptionKey === null && 
        candidate.kind === kind
    );

    if (!slot) {
      slot = {
        transceiver: pc.addTransceiver(kind, {
          direction: "recvonly",
        }),
        kind,
        subscriptionKey: null,
      };

      recvSlots.push(slot);
    } else {
      slot.transceiver.direction = "recvonly";
    }

    slot.subscriptionKey = key;
    activeByKey.set(key, slot);

    return slot;
  }

  function handleReceivingTransceivers(media: MediaHint[]): void {
    if (closed) {
      throw new Error("WebRTC session has already closed");
    }

    const desiredByKey = new Map(
      media.map((item) => [
        `${item.participant_id}:${item.track_id}`, 
        item,
      ]),
    );

    // Release slots to be reused
    for (const key of [...activeByKey.keys()]) {
      if (!desiredByKey.has(key)) {
        releaseSlot(key);
      }
    }

    // Reuse slots or allocate new ones
    for (const [key, item] of desiredByKey) {
      acquireSlot(key, item.kind);
    }
  }

  function waitForIceGathering(pc: RTCPeerConnection): Promise<void> {
    if (pc.iceGatheringState === "complete") {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      const cleanup = () => {
        pc.removeEventListener("icegatheringstatechange", handleGathering);
        pc.removeEventListener("connectionstatechange", handleConnection);
      };

      const handleGathering = () => {
        if (pc.iceGatheringState === "complete") {
          cleanup();
          resolve();
        }
      };

      const handleConnection = () => {
        if (pc.connectionState === "closed") {
          cleanup();
          reject(new Error("Peer connection closed during ICE gathering"));
        }
      };

      pc.addEventListener("icegatheringstatechange", handleGathering);
      pc.addEventListener("connectionstatechange", handleConnection);
    });
  }
  
  async function createOffer(): Promise<string> {
    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      await waitForIceGathering(pc);

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
