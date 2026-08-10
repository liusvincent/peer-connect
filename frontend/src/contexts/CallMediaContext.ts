import { createContext } from "react";
import type { WebRTCSession } from "../services/webrtc";

export type CallMediaStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "disconnecting"
  | "error";

export type RemoteParticipantMedia = { 
  participantId: string;
  stream: MediaStream;
};

export type RemoteSubscription = {
  participantId: string;
  trackId: string;
  kind: "audio" | "video";
  track: MediaStreamTrack | null;
}

type CallMediaContextValue = {
  status: CallMediaStatus;
  connectionState: RTCPeerConnectionState | null;
  error: string | null;
  remoteMedia: readonly RemoteParticipantMedia[];

  start: () => Promise<WebRTCSession>;
  stop: () => void;
  clearError: () => void;
};

export const CallMediaContext = createContext<
  CallMediaContextValue | undefined
>(undefined);
