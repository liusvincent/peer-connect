import { handleWebRTCAnswer } from "./webrtc";

let transport: WebTransport | null = null;
let writer: WritableStreamDefaultWriter<Uint8Array> | null = null;
let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

let readBuffer = "";

const HEXFINGERPRINT =
  "76dfb2cf33187dafb1c9f0d30245a2a338dc5b2f1fd89e0d4da8ee909cf3a9c3";

const convertHexToBytes = (hex: string): Uint8Array =>
  Uint8Array.from({ length: hex.length / 2 }, (_, i) =>
    parseInt(hex.slice(i * 2, i * 2 + 2), 16),
  );

const hash: Uint8Array = convertHexToBytes(HEXFINGERPRINT);

const encoder = new TextEncoder();
const decoder = new TextDecoder();

export async function connectWebTransport() {
  try {
    console.log("Creating WebTransport");
    transport = new WebTransport("https://localhost:4433/wt", {
      serverCertificateHashes: [
        {
          algorithm: "sha-256",
          value: hash.buffer as ArrayBuffer,
        },
      ],
    });

    await transport.ready;
    console.log("WebTransport Ready");

    const stream = await transport.createBidirectionalStream();
    writer = stream.writable.getWriter();
    reader = stream.readable.getReader();

    listenForMessage();
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

  try {
    const json = JSON.stringify(message) + "\n";
    await writer.write(encoder.encode(json));
  } catch (err) {
    console.error(err);
    throw err;
  }
}

export async function listenForMessage() {
  if (!reader) {
    throw new Error("WebTransport is not connected");
  }

  try {
    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        console.log("WebTransport stream closed");
        readBuffer += decoder.decode()
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
          console.log("Received:", message);
          if (message.type === "answer") {
            await handleWebRTCAnswer(message.sdp);
          }
        } catch (err) {
          console.error("Message error:", err);
        }
      }
    }
  } catch (err) {
    console.error("WebTransport error:", err);
  }
}
