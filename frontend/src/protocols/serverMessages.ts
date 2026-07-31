import type { Room } from "../types/room";

type ServerResponseBase = {
  request_id: string;
};

export type WebRTCAnswerResponse = ServerResponseBase & {
  type: "webrtc-answer";
  sdp: string;
};

export type CreateIdResponse = ServerResponseBase & {
  type: "id-answer";
  id: string;
};

export type RequestErrorResponse = ServerResponseBase & {
  type: "request-error";
  message: string;
};

export type JoinedRoomResponse = ServerResponseBase & {
  type: "joined-room";
  room: Room;
};

export type JoinedLobbyResponse = ServerResponseBase & {
  type: "joined-lobby";
  room: Room;
};

export type LeftRoomResponse = ServerResponseBase & {
  type: "left-room";
  room_id: string;
};

export type ServerResponse =
  | WebRTCAnswerResponse
  | CreateIdResponse
  | RequestErrorResponse
  | JoinedLobbyResponse
  | JoinedRoomResponse
  | LeftRoomResponse;
