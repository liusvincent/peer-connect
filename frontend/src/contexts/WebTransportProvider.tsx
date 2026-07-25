import { useState, type ReactNode } from "react";
import { WebTransportContext, type ConnectionStatus } from "./WebTransportContext";
import {
  connectWebTransport,
  disconnectWebTransport,
  request,
} from "../services/webtransport";

export function WebTransportProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");

  const ensureConnected = async () => {
    if (status === "connected") {
      return;
    }

    setStatus("connecting");
    const ok = await connectWebTransport();
    
    if (!ok) {
      setStatus("disconnected");
      throw new Error("Failed to connect to WebTransport");
    }

    setStatus("connected");
  }

  const joinRoom = async (roomId: string) => {
    await ensureConnected();

    const requestId = crypto.randomUUID();

    const response = await request({
      type: "join-room",
      request_id: requestId,
      room_id: roomId,
    });

    if (response.type !== "joined-room") {
      throw new Error("Unexpected server response");
    }

    return { roomId: response.room_id };
  };

  const createRoom = async () => {
    await ensureConnected();

    const requestId = crypto.randomUUID();

    const response = await request({
      type: "create-room",
      request_id: requestId,
    });


    if (response.type !== "joined-room") {
      throw new Error("Unexpected server response");
    }

    return { roomId: response.room_id };
  }

  const disconnect = async () => {
    await disconnectWebTransport();
    setStatus("disconnected");
  };

  return (
    <WebTransportContext.Provider
      value={{
        status,
        joinRoom,
        createRoom,
        disconnect,
      }}
    >
      {children}
    </WebTransportContext.Provider>
  );
}