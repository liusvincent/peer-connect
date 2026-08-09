import type { ClientRequest } from "./clientMessages";
import type { ServerResponse } from "./serverMessages";

type GoodServerResponse = Exclude<ServerResponse, { type: "request-error" }>;

const responseTypes = {
  "webrtc-offer": "webrtc-answer",
  "create-user": "user-answer",
  "join-room": "joined-room",
  "join-lobby": "joined-lobby",
  "create-room": "joined-room",
  "leave-room": "left-room",
} as const satisfies Record<ClientRequest["type"], GoodServerResponse["type"]>;

export type ResponseFor<T extends ClientRequest["type"]> = Extract<
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

  const expectedType = responseTypes[requestType];

  if (response.type !== expectedType) {
    throw new Error(
      `Expected ${expectedType}, received ${response.type}`,
    );
  }

  return response as ResponseFor<T>;
}
