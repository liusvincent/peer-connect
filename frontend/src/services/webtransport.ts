const HEXFINGERPRINT =
  "76dfb2cf33187dafb1c9f0d30245a2a338dc5b2f1fd89e0d4da8ee909cf3a9c3";

const convertHexToBytes = (hex: string): Uint8Array =>
  Uint8Array.from({ length: hex.length / 2 }, (_, i) =>
    parseInt(hex.slice(i * 2, i * 2 + 2), 16),
  );

const hash: Uint8Array = convertHexToBytes(HEXFINGERPRINT);

type WebTransportHandlers = {
  onCoordinates?: (x: number, y: number) => void;
  onAnswer?: (sdp: string) => Promise<void>;
  onDisconnect?: () => void;
};

let transport: WebTransport | null = null;
let writer: WritableStreamDefaultWriter<Uint8Array> | null = null;
let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

export async function connectWebTransport(
  handlers: WebTransportHandlers = {}
) {
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

    void listenForMessage(reader, handlers);
    return true;
  } catch (err) {
    console.error(err);
    return false;
  }
}

export async function sendMessage(message: object) {
  if (!writer) {
    throw new Error("WebTransport is not connected");
  }
  const encoder = new TextEncoder();
  const json = JSON.stringify(message) + "\n";
  await writer.write(encoder.encode(json));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

async function handleMessage(
  message: unknown,
  handlers: WebTransportHandlers = {},
) {
  if (!isRecord(message) || typeof message.type !== "string") {
    console.warn("Invalid message:", message);
    return;
  }
  switch (message.type) {
    case "answer":
      if (typeof message.sdp !== "string") {
      console.warn("Invalid WebRTC answer:", message);
      break;
    }
      await handlers.onAnswer?.(message.sdp);
      break;

    case "coordinates":
      if (typeof message.x === "number" && typeof message.y === "number") {
        handlers.onCoordinates?.(message.x, message.y);
      }
      break;

    default:
      console.warn("Unknown message:", message);
  }
}

export async function listenForMessage(
  currentReader: ReadableStreamDefaultReader<Uint8Array>,
  handlers: WebTransportHandlers = {},
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
          await handleMessage(message, handlers);
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
      handlers.onDisconnect?.();
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