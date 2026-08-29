import type { Room, MediaHint, MediaInfo } from "../types/models";

type ServerResponseBase = {
  request_id: string;
};

export type WebRTCAnswerResponse = ServerResponseBase & {
  type: "webrtc-answer";
  sdp: string;
  media_info: MediaInfo[];
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

export type WebRTCOfferNeeded = ServerEventBase & {
  type: "webrtc-offer-needed";
  media_hint: MediaHint[];
}

export type RoomUpdated = ServerEventBase & {
  type: "room-updated";
  room: Room;
}

export type EventErrorResponse = ServerEventBase & {
  type: "event-error";
  message: string;
}

export type ServerEvent = WebRTCOfferNeeded | RoomUpdated | EventErrorResponse;

export type MessageErrorResponse = {
  type: "message-error";
  message: string;
};

export type ServerMessage = ServerResponse | ServerEvent | MessageErrorResponse;
