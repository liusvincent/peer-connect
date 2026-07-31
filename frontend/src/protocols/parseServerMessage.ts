import type { ClientRequest } from "./clientMessages";
import type { ServerResponse } from "./serverMessages";

const responseTypes = {
  "webrtc-offer": "webrtc-answer",
  "create-id": "id-answer",
  "join-room": "joined-room",
  "join-lobby": "joined-lobby",
  "create-room": "joined-room",
  "leave-room": "left-room",
} as const;

type ResponseFor<T extends ClientRequest["type"]> = Extract<
  ServerResponse,
  { type: (typeof responseTypes)[T] }
>;

export function parseServerMessage<T extends ClientRequest["type"]>(
  requestType: T,
  response: ServerResponse,
): ResponseFor<T> {
  if (response.type === "request-error") {
    throw new Error(response.message);
  }

  if (response.type !== responseTypes[requestType]) {
    throw new Error(`Unexpected response: ${response.type}`);
  }

  return response as ResponseFor<T>;
}
