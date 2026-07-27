// for certs purposes
const HEXFINGERPRINT =
  "27ce3136a2b7de8cf8dc2059c21141b3179f099d0b2e829b56279ddafac132b5";

const convertHexToBytes = (hex: string): Uint8Array =>
  Uint8Array.from({ length: hex.length / 2 }, (_, i) =>
    parseInt(hex.slice(i * 2, i * 2 + 2), 16),
  );

const hash: Uint8Array = convertHexToBytes(HEXFINGERPRINT);
// end of certs

type ServerMessage = 
  | { type: "webrtc-answer"; request_id: string; sdp: string }
  | { type: "request-error"; request_id: string; message: string }
  | { type: "joined-room"; request_id: string; participant_id: string; room_id: string }
  | { type: "left-room"; request_id: string; participant_id: string; room_id: string };

export type ClientRequest = 
  | { type: "webrtc-offer"; request_id: string; sdp: string }
  | { type: "join-room"; request_id: string; room_id: string } 
  | { type: "create-room"; request_id: string; }
  | { type: "leave-room"; request_id: string };
  
type PendingRequest = {
  resolve: (message: ServerMessage) => void;
  reject: (error: Error) => void;
  timeout: ReturnType<typeof setTimeout>;
};

const pendingRequests = new Map<string, PendingRequest>();

// type MessageType = ServerMessage["type"];

// type MessageHandler<T extends MessageType> = (
//   message: Extract<ServerMessage, { type: T }>
// ) => void;

// const listeners = new Map<MessageType, Set<(message: ServerMessage) => void>>();

let transport: WebTransport | null = null;
let writer: WritableStreamDefaultWriter<Uint8Array> | null = null;
let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

export async function connectWebTransport() {
  if (transport && writer && reader) {
    return true;
  } // if connection already exists
  
  // clean up incomplete/stale connections
  await disconnectWebTransport();

  try {
    console.log("Creating WebTransport");
    const currentTransport = new WebTransport("https://localhost:4433/wt", {
      serverCertificateHashes: [
        {
          algorithm: "sha-256",
          value: hash.buffer as ArrayBuffer,
        },
      ],
    });

    await currentTransport.ready;

    const stream = await currentTransport.createBidirectionalStream();

    transport = currentTransport
    writer = stream.writable.getWriter();
    reader = stream.readable.getReader();

    void listenForMessage(reader);
    return true;
  } catch (err) {
    console.error(err);
    return false;
  }
}

function removePendingRequest(requestId: string) {
  const pending = pendingRequests.get(requestId);
  if (!pending) return;

  clearTimeout(pending.timeout);
  pendingRequests.delete(requestId);
}

export async function request(message: ClientRequest) {
  const responsePromise = waitForResponse(message.request_id);
  try {
    await sendMessage(message);
  } catch (err) {
    removePendingRequest(message.request_id);
    throw err;
  }
  
  return responsePromise;
}

export async function sendMessage(message: object) {
  if (!writer) {
    throw new Error("WebTransport is not connected");
  }
  const encoder = new TextEncoder();
  const json = JSON.stringify(message) + "\n";
  await writer.write(encoder.encode(json));
}

async function waitForResponse(
  requestId: string,
  timeoutMs: number = 10_000,
): Promise<ServerMessage> {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      pendingRequests.delete(requestId);
      reject(new Error("Server response timed out"));
    }, timeoutMs);

    pendingRequests.set(requestId, {
      resolve,
      reject,
      timeout
    });
  });
}

function handleMessage(message: ServerMessage) {
  if (!message.request_id) return;

  const pending = pendingRequests.get(message.request_id);
  if (!pending) return;

  clearTimeout(pending.timeout);
  pendingRequests.delete(message.request_id);

  if (message.type === "request-error") {
    pending.reject(new Error(message.message));
  } else {
    pending.resolve(message);
  }
}

export async function listenForMessage(
  currentReader: ReadableStreamDefaultReader<Uint8Array>,
) {
  let readBuffer = "";
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
          const message = JSON.parse(rawMessage);
          handleMessage(message);
        } catch (err) {
          console.error(err);
        }
      }
    }
  } catch (err) {
    console.error(err);
  } finally {
    if (reader === currentReader) {
      await disconnectWebTransport();
    }
  }
}

export async function disconnectWebTransport() {
  const oldReader = reader;
  const oldWriter = writer;
  const oldTransport = transport;

  reader = null;
  writer = null;
  transport = null;

  await Promise.allSettled([
    oldReader?.cancel(),
    oldWriter?.close(),
  ]);

  oldReader?.releaseLock();
  oldWriter?.releaseLock();
  oldTransport?.close();
}