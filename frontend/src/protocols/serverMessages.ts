import type { Room } from "../types/room";

type ServerResponseBase = {
  request_id: string;
};

export type WebRTCAnswerResponse = ServerResponseBase & {
  type: "webrtc-answer";
  sdp: string;
};

export type CreateUserResponse = ServerResponseBase & {
  type: "user-answer";
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
  | CreateUserResponse
  | RequestErrorResponse
  | JoinedLobbyResponse
  | JoinedRoomResponse
  | LeftRoomResponse;

type ServerEventBase = {
  event_id: string;
};

export type WebRTCRenegotiationOFfer = ServerEventBase & {
  type: "webrtc-renegotiation-offer";
  sdp: string;
  media: Array<{
    mid: string;
    participant_id: string;
    track_id: string;
    kind: "audio" | "video";
  }>;
};

export type ServerEvent = WebRTCRenegotiationOFfer;

export type ServerMessage = ServerResponse | ServerEvent;
