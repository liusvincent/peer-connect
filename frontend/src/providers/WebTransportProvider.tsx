import { useRef, useState, type ReactNode } from "react";

import {
  WebTransportContext,
  type WebTransportStatus,
} from "../contexts/WebTransportContext";

import {
  connectWebTransport,
  disconnectWebTransport,
  sendWebTransportRequest,
} from "../services/webtransport";

import {
  type ServerResponse,
  type ClientRequest,
  parseServerMessage,
} from "../protocols";

export function WebTransportProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<WebTransportStatus>("disconnected");
  const [id, setId] = useState<string>("");

  const connectionPromiseRef = useRef<Promise<void> | null>(null);

  const initializeConnection = async () => {
    await connectWebTransport();

    const message = {
      request_id: crypto.randomUUID(),
      type: "create-id",
    } satisfies ClientRequest;

    const rawResponse = await sendWebTransportRequest(message);
    const response = parseServerMessage(message.type, rawResponse);

    setId(response.id);
  };

  const connectedRef = useRef(false);

  const connect = async () => {
    if (connectedRef.current) return;

    if (!connectionPromiseRef.current) {
      setStatus("connecting");

      connectionPromiseRef.current = initializeConnection()
        .then(() => {
          connectedRef.current = true;
          setStatus("connected");
        })
        .catch((err) => {
          connectedRef.current = false;
          setStatus("disconnected");
          throw err;
        })
        .finally(() => {
          connectionPromiseRef.current = null;
        });
    }

    await connectionPromiseRef.current;
  };

  const disconnect = async () => {
    setStatus("disconnecting");

    try {
      await disconnectWebTransport();
    } finally {
      connectedRef.current = false;
      connectionPromiseRef.current = null;
      setId("");
      setStatus("disconnected");
    }
  };

  const request = async (message: ClientRequest): Promise<ServerResponse> => {
    await connect();
    return sendWebTransportRequest(message);
  };

  return (
    <WebTransportContext.Provider
      value={{
        status,
        id,
        connect,
        disconnect,
        request,
      }}
    >
      {children}
    </WebTransportContext.Provider>
  );
}
