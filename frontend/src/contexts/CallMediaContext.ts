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
}; // have a feeling I might need to move this to the types folder

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
