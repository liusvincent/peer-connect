type ClientRequestBase = {
  request_id: string;
};

export type WebRTCOfferRequest = ClientRequestBase & {
  type: "webrtc-offer";
  sdp: string;
};

export type CreateUserRequest = ClientRequestBase & {
  type: "create-user";
  user_name: string;
};

export type CreateRoomRequest = ClientRequestBase & {
  type: "create-room";
};

export type JoinLobbyRequest = ClientRequestBase & {
  type: "join-lobby";
  room_id: string;
};

export type JoinRoomRequest = ClientRequestBase & {
  type: "join-room";
};

export type LeaveRoomRequest = ClientRequestBase & {
  type: "leave-room";
};

export type ClientRequest =
  | WebRTCOfferRequest
  | CreateUserRequest
  | CreateRoomRequest
  | JoinLobbyRequest
  | JoinRoomRequest
  | LeaveRoomRequest;

type ClientEventBase = {
  event_id: string;
};

export type WebRTCRenegotiationAnswer = ClientEventBase & {
  type: "webrtc-renegotiation-answer";
  sdp: string;
};

export type WebRTCReady = ClientEventBase & {
  type: "webrtc-ready";
};

export type ClientEvent = WebRTCRenegotiationAnswer | WebRTCReady;

export type ClientMessage = ClientRequest | ClientEvent;
