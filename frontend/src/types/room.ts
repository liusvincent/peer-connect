type ParticipantRole = "host" | "co" | "member";

export type Participant = {
  id: string;
  name: string;
  role: ParticipantRole;
};

export type Room = {
  id: string;
  participant_ids: string[];
  lobby_ids: string[];
  participants: Participant[];
};