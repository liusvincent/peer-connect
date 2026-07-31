import {
  type ServerResponse,
  type ClientRequest,
} from "../protocols"

// for certs purposes
const HEXFINGERPRINT =
  "27ce3136a2b7de8cf8dc2059c21141b3179f099d0b2e829b56279ddafac132b5";

const convertHexToBytes = (hex: string): Uint8Array =>
  Uint8Array.from({ length: hex.length / 2 }, (_, i) =>
    parseInt(hex.slice(i * 2, i * 2 + 2), 16),
  );

const hash: Uint8Array = convertHexToBytes(HEXFINGERPRINT);
// end of certs
  
type PendingRequest = {
  resolve: (message: ServerResponse) => void;
  reject: (error: Error) => void;
  timeout: ReturnType<typeof setTimeout>;
};

const pendingRequests = new Map<string, PendingRequest>();

let transport: WebTransport | null = null;
let writer: WritableStreamDefaultWriter<Uint8Array> | null = null;
let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

export async function connectWebTransport() {
  if (transport && writer && reader) {
    return;
  } // connection already exists
  
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
  } catch (err) {
    throw new Error("Establish WebTransport Connection Failed", {
      cause: err,
    });
  }
}

export async function sendWebTransportRequest(message: ClientRequest) {
  const responsePromise = waitForResponse(message.request_id);
  try {
    await sendMessage(message);
  } catch (err) {
    removePendingRequest(message.request_id);
    throw err;
  }
  
  return responsePromise;
}

async function waitForResponse(
  requestId: string,
  timeoutMs: number = 10_000,
): Promise<ServerResponse> {
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

export async function sendMessage(message: object) {
  if (!writer) {
    throw new Error("WebTransport is not connected");
  }
  const encoder = new TextEncoder();
  const json = JSON.stringify(message) + "\n";
  await writer.write(encoder.encode(json));
}

function removePendingRequest(requestId: string) {
  const pending = pendingRequests.get(requestId);
  if (!pending) return;

  clearTimeout(pending.timeout);
  pendingRequests.delete(requestId);
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

function handleMessage(message: ServerResponse) {
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