import { createContext } from "react";
import type { ClientRequest, ServerResponse } from "../protocols";

export type WebTransportStatus =
  | "disconnected"
  | "disconnecting"
  | "connecting"
  | "reconnecting" // reconnection still needs to be implemented
  | "connected";

type WebTransportContextValue = {
  status: WebTransportStatus;
  id: string;

  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  request: (message: ClientRequest) => Promise<ServerResponse>;
};

export const WebTransportContext =
  createContext<WebTransportContextValue | null>(null);
