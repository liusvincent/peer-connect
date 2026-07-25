import { createContext } from "react";

export type ConnectionStatus = "disconnected" | "connecting" | "connected";

type RoomInfo = {
    roomId: string
}

type WebTransportContextValue = {
  status: ConnectionStatus;
  joinRoom: (roomId: string) => Promise<RoomInfo>;
  createRoom: () => Promise<RoomInfo>;
  disconnect: () => Promise<void>;
};

export const WebTransportContext =
  createContext<WebTransportContextValue | null>(null);


