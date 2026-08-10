import { useRef, useState, type ReactNode } from "react";

import {
  WebTransportContext,
  type WebTransportStatus,
  type WebTransportUser,
} from "../contexts/WebTransportContext";

import {
  connectWebTransport,
  disconnectWebTransport,
  sendWebTransportRequest,
  sendMessage,
  listenToServerEvent
} from "../services/webtransport";

import type {
  ResponseFor,
  ClientRequest,
  ClientEvent,
  ServerEvent,
} from "../protocols";

export function WebTransportProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<WebTransportStatus>("disconnected");
  const [user, setUser] = useState<WebTransportUser | null>(null);

  const connectedRef = useRef(false);
  const connectionPromiseRef = useRef<Promise<void> | null>(null);

  async function connect(userName: string): Promise<void> {
    if (connectedRef.current) return;

    if (connectionPromiseRef.current) {
      return connectionPromiseRef.current;
    }

    setStatus("connecting");

    const connectionPromise = initializeConnection(userName);
    connectionPromiseRef.current = connectionPromise;

    try {
      return await connectionPromise;
    } finally {
      if (connectionPromiseRef.current === connectionPromise) {
        connectionPromiseRef.current = null;
      }
    }
  }

  async function initializeConnection(userName: string): Promise<void> {
    await connectWebTransport(handleClose);

    try {
      const message = {
        request_id: crypto.randomUUID(),
        type: "create-user",
        user_name: userName,
      } satisfies ClientRequest;

      const response = await sendWebTransportRequest(message);

      connectedRef.current = true;

      setUser({ id: response.id, name: userName });
      setStatus("connected");
    } catch (err) {
      await disconnectWebTransport(err);
      throw err;
    }
  }

  function handleClose(err?: unknown): void {
    if (err) {
      console.error("WebTransport Disconnected", err);
    }

    connectedRef.current = false;

    setUser(null);
    setStatus("disconnected");
  }

  async function disconnect(): Promise<void> {
    if (!connectedRef.current && !connectionPromiseRef.current) {
      return;
    }

    setStatus("disconnecting");
    await disconnectWebTransport();
  }

  async function request<T extends ClientRequest>(
    message: T,
  ): Promise<ResponseFor<T["type"]>> {
    if (!connectedRef.current) {
      return Promise.reject(new Error("WebTransport is not connected"));
    }
    return sendWebTransportRequest(message);
  }

  async function sendEvent<T extends ClientEvent>(message: T): Promise<void> {
    if (!connectedRef.current) {
      return Promise.reject(new Error("WebTransport is not connected"));
    }
    await sendMessage(message);
  }

  function listen(
    listener: (event: ServerEvent) => void | Promise<void>,
  ): () => void {
    return listenToServerEvent(listener);
  }

  return (
    <WebTransportContext.Provider
      value={{
        status,
        user,
        connect,
        disconnect,
        request,
        sendEvent,
        listen,
      }}
    >
      {children}
    </WebTransportContext.Provider>
  );
}
