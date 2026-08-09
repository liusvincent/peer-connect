type ParticipantRole = "host" | "co" | "member";

export type Participant = {
  id: string;
  name: string;
  role: ParticipantRole;
};

export type Room = {
  id: string;
  lobby: Record<string, Participant>;
  participants: Record<string, Participant>;
};