import { createContext } from "react";
import type {
  ClientRequest,
  ResponseFor,
  ClientEvent,
  ServerEvent,
} from "../protocols";

export type WebTransportStatus =
  | "disconnected"
  | "disconnecting"
  | "connecting"
  | "reconnecting" // reconnection still needs to be implemented
  | "connected";

export type WebTransportUser = {
  id: string;
  name: string;
};

type WebTransportContextValue = {
  status: WebTransportStatus;
  user: WebTransportUser | null;

  connect: (userName: string) => Promise<void>;
  disconnect: () => Promise<void>;
  request: <T extends ClientRequest>(
    message: T,
  ) => Promise<ResponseFor<T["type"]>>;
  sendEvent: <T extends ClientEvent>(message: T) => Promise<void>;
  listen: (
    listener: (event: ServerEvent) => void | Promise<void>,
  ) => () => void;
};

export const WebTransportContext =
  createContext<WebTransportContextValue | null>(null);
