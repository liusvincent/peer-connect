import { parseServerMessage } from "../protocols";

import type {
  ServerMessage,
  ClientMessage,
  ServerEvent,
  ServerResponse,
  ClientRequest,
  ResponseFor,
} from "../protocols";

// For certs purposes /////////////////////////////////////////////////////
const HEXFINGERPRINT =
  "046D80AB15021666C11D634F2C8DE82E2BCF6D774D99F95EBBCA96841F9DF621";
  // "EE74209213E6B24FD64F0F6A04EAC3DAE5A1D4FD36413696EC4AA213D2847C10";

const convertHexToBytes = (hex: string): Uint8Array =>
  Uint8Array.from({ length: hex.length / 2 }, (_, i) =>
    parseInt(hex.slice(i * 2, i * 2 + 2), 16),
  );

const hash: Uint8Array = convertHexToBytes(HEXFINGERPRINT);
//////////////////////////////////////////////////////////////////////////

const WEBTRANSPORT_URL = import.meta.env.VITE_WEBTRANSPORT_URL;

if (!WEBTRANSPORT_URL) {
  throw new Error("VITE_WEBTRANSPORT_URL is not configured");
}

let transport: WebTransport | null = null;
let writer: WritableStreamDefaultWriter<Uint8Array> | null = null;
let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

window.addEventListener("pagehide", () => {
  transport?.close({
    closeCode: 0,
    reason: "page closed",
  });
});

type CloseProviderHandler = (error?: unknown) => void;

let closeHandler: CloseProviderHandler | null = null;

export async function connectWebTransport(onClose: CloseProviderHandler): Promise<void> {
  if (transport && writer && reader) {
    return;
  }

  try {
    // clean up incomplete/stale connections
    await disconnectWebTransport();
    closeHandler = onClose;

    console.log(WEBTRANSPORT_URL)
    console.log("Creating WebTransport");

    transport = new WebTransport(WEBTRANSPORT_URL, {
      serverCertificateHashes: [
        { algorithm: "sha-256", value: hash.buffer as ArrayBuffer },
      ],
    });

    await transport.ready;

    const stream = await transport.createBidirectionalStream();

    writer = stream.writable.getWriter();
    reader = stream.readable.getReader();

    void listenForMessage(reader);
  } catch (err) {
    await disconnectWebTransport().catch((cleanupErr: unknown) => {
      console.error("WebTransport Cleanup Failed", cleanupErr);
    });
    throw new Error("Establish WebTransport Connection Failed", { cause: err });
  }
}

async function listenForMessage(
  currentReader: ReadableStreamDefaultReader<Uint8Array>,
): Promise<void> {
  let readBuffer = "";
  let closeError: unknown;
  const decoder = new TextDecoder();

  try {
    while (true) {
      const { value, done } = await currentReader.read();

      if (done) {
        console.log("WebTransport stream closed");
        break;
      }

      if (!value) continue;

      readBuffer += decoder.decode(value, { stream: true });

      let newlineIndex;

      while ((newlineIndex = readBuffer.indexOf("\n")) !== -1) {
        const rawMessage = readBuffer.slice(0, newlineIndex);
        readBuffer = readBuffer.slice(newlineIndex + 1);

        if (!rawMessage.trim()) continue;

        try {
          const message = JSON.parse(rawMessage) as ServerMessage;
          await handleMessage(message);
        } catch (err) {
          console.error("Invalid Server Message", err);
        }
      }
    }
  } catch (err) {
    closeError = err;
  } finally {
    if (reader === currentReader) {
      await disconnectWebTransport(closeError);
    }
  }
}

async function handleMessage(
  message: ServerMessage,
): Promise<void> {
  if ("request_id" in message) {
    handleResponse(message);
    return;
  }

  if ("event_id" in message) {
    await handleEvent(message);
    return;
  }
}

type ServerEventListener = (
  event: ServerEvent,
) => void | Promise<void>;

const serverEventListeners = new Set<ServerEventListener>();

export function listenToServerEvent(
  handler: ServerEventListener,
): () => void {
  serverEventListeners.add(handler);

  return () => {
    serverEventListeners.delete(handler);
  };
}

async function handleEvent(
  event: ServerEvent,
): Promise<void> {
   if (event.type === "event-error") {
    console.error(
      `Server failed to process event ${event.event_id}: ${event.message}`,
    );
    return;
  }

  for (const listener of serverEventListeners) {
    await listener(event);
  }
}

type PendingRequest = {
  resolve: (message: ServerResponse) => void;
  reject: (error: Error) => void;
  timeout: ReturnType<typeof setTimeout>;
};

const pendingRequests = new Map<string, PendingRequest>();

function handleResponse(message: ServerResponse): void {
  if (!message.request_id) return;

  const pending = pendingRequests.get(message.request_id);
  if (!pending) return;

  removePendingRequest(message.request_id);

  if (message.type === "request-error") {
    pending.reject(new Error(message.message));
    return;
  }

  pending.resolve(message);
}

export async function sendWebTransportRequest<T extends ClientRequest>(
  message: T,
): Promise<ResponseFor<T["type"]>> {
  const responsePromise = waitForResponse(message.request_id);

  try {
    await sendMessage(message);
    const response = await responsePromise;
    return parseServerMessage<T["type"]>(message.type, response);
  } finally {
    removePendingRequest(message.request_id);
  }
}

async function waitForResponse(
  requestId: string,
  timeoutMs: number = 10_000,
): Promise<ServerResponse> {
  if (pendingRequests.has(requestId)) {
    return Promise.reject(new Error(`Duplicate request ID: ${requestId}`));
  }

  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      pendingRequests.delete(requestId);
      reject(new Error("Server response timed out"));
    }, timeoutMs);

    pendingRequests.set(requestId, {
      resolve,
      reject,
      timeout,
    });
  });
}

export async function sendMessage(message: ClientMessage): Promise<void> {
  if (!writer) {
    throw new Error("WebTransport is not connected");
  }
  const encodedMessage = new TextEncoder().encode(
    `${JSON.stringify(message)}\n`,
  );
  await writer.write(encodedMessage);
}

function removePendingRequest(requestId: string): void {
  const pending = pendingRequests.get(requestId);
  if (!pending) return;

  clearTimeout(pending.timeout);
  pendingRequests.delete(requestId);
}

export async function disconnectWebTransport(err?: unknown): Promise<void> {
  const oldReader = reader;
  const oldWriter = writer;
  const oldTransport = transport;
  const oldCloseHandler = closeHandler;

  reader = null;
  writer = null;
  transport = null;
  closeHandler = null;

  rejectPendingRequests(new Error("WebTransport disconnected", { cause: err }));

  await Promise.allSettled([oldReader?.cancel(), oldWriter?.close()]);

  oldReader?.releaseLock();
  oldWriter?.releaseLock();
  oldTransport?.close();

  oldCloseHandler?.(err);
}

function rejectPendingRequests(err: Error): void {
  for (const pending of pendingRequests.values()) {
    clearTimeout(pending.timeout);
    pending.reject(err);
  }

  pendingRequests.clear();
}
