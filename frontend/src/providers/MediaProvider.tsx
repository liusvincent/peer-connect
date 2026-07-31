import { useState, type ReactNode } from "react";

import { useMedia } from "../hooks/useWebTransport";

import {
  MediaContext,
} from "../contexts/MediaContext";

import { type ClientRequest, parseServerMessage } from "../protocols";

export function MediaProvider({ children }: { children: ReactNode }) {
    
    return (
        <MediaContext.Provider
          value={{
            peerConnectionState,
            localStream,
            remoteStreams,
            startCamera,
            stopCamera,
            connectWebRTC,
            disconnectWebRTC,
          }}
        >
          {children}
        </MediaContext.Provider>
      );
}