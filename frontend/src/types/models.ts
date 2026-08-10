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

export type MediaHint = {
  participant_id: string;
  track_id: string;
  kind: "audio" | "video";
};

export type MediaInfo = MediaHint & {
  mid: string;
};
