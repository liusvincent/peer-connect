type ClientRequestBase = {
  request_id: string;
};

export type WebRTCOfferRequest = ClientRequestBase & {
  type: "webrtc-offer";
  sdp: string;
};

export type CreateIdRequest = ClientRequestBase & {
  type: "create-id";
};

export type CreateRoomRequest = ClientRequestBase & {
  type: "create-room";
  user_name: string;
};

export type JoinLobbyRequest = ClientRequestBase& {
  type: "join-lobby";
  room_id: string;
  user_name: string;
}

export type JoinRoomRequest = ClientRequestBase & {
  type: "join-room";
};

export type LeaveRoomRequest = ClientRequestBase & {
  type: "leave-room";
  room_id: string;
};

// export type AdmitParticipant = ClientRequestBase & {
//   type: "admit-participant";
//   room_id: string;
//   participant_id: string;
// }

// export type DenyParticipant = ClientRequestBase & {
//   type: "deny-participant";
//   room_id: string;
//   participant_id: string;
// }

// export type KickParticipant = ClientRequestBase & {
//   type: "kick-participant";
//   room_id: string;
//   participant_id: string;
// }

// export type ToggleMuteParticipant = ClientRequestBase & {
//   type: "toggle-mute-participant";
//   room_id: string;
//   participant_id: string;
// }

export type ClientRequest =
  | WebRTCOfferRequest
  | CreateIdRequest
  | JoinRoomRequest
  | JoinLobbyRequest
  | CreateRoomRequest
  | LeaveRoomRequest;
