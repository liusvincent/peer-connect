let transport: WebTransport | null = null;
let writer: WritableStreamDefaultWriter<Uint8Array> | null = null;
// let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

const HEXFINGERPRINT =
  "76dfb2cf33187dafb1c9f0d30245a2a338dc5b2f1fd89e0d4da8ee909cf3a9c3";

const convertHexToBytes = (hex: string): Uint8Array =>
  Uint8Array.from({ length: hex.length / 2 }, (_, i) =>
    parseInt(hex.slice(i * 2, i * 2 + 2), 16),
  );

const hash: Uint8Array = convertHexToBytes(HEXFINGERPRINT);

const encoder = new TextEncoder();
// const decoder = new TextDecoder();

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
    // reader = stream.readable.getReader()
    return true;
  } catch (err) {
    console.error(err);
    return false;
  }
}

export async function sendMessage(message: object) {
  if (!writer) {
    throw new Error("WebTransport is not Connected");
  }

  try {
    const json = JSON.stringify(message);
    await writer.write(encoder.encode(json));
  } catch (err) {
    console.error(err);
  }
}
