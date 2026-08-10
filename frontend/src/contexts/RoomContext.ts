import { createContext } from "react";
import type { Room } from "../types/models"

type RoomContextValue = {
  room: Room | null;

  createRoom: (userName: string) => Promise<Room>;
  joinLobby: (roomId: string, userName: string) => Promise<Room>;
  joinRoom: () => Promise<Room>;
  leaveRoom: () => Promise<void>;
};

export const RoomContext = createContext<RoomContextValue | undefined>(
  undefined,
);
