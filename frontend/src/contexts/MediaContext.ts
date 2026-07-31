import { createContext } from "react";


export type MediaContextValue = {
  peerConnectionState: RTCPeerConnectionState | null;
  localStream: MediaStream | null;
  remoteStreams: Map<string, MediaStream>;

  startCamera: () => Promise<void>;
  stopCamera: () => void;
  connectWebRTC: () => Promise<void>;
  disconnectWebRTC: () => void;
};


export const MediaContext =
  createContext<MediaContextValue | undefined>(undefined);
