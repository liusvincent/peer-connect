import { useState, type ReactNode } from "react";

import { useWebTransport } from "../hooks/useWebTransport";
import { RoomContext } from "../contexts/RoomContext";

import type { Room } from "../types/models";
import type { ClientRequest } from "../protocols";

export function RoomProvider({ children }: { children: ReactNode }) {
  const transport = useWebTransport();

  const [room, setRoom] = useState<Room | null>(null);

  const activeRoom = transport.status === "disconnected" ? null : room;

  function ensureDisconnected(): void {
    if (transport.status !== "disconnected") {
      throw new Error("You are already in a room session");
    }
  }

  async function createRoom(userName: string): Promise<Room> {
    ensureDisconnected();

    await transport.connect(userName);

    const message = {
      request_id: crypto.randomUUID(),
      type: "create-room",
    } satisfies ClientRequest;

    try {
      const response = await transport.request(message);

      setRoom(response.room);
      return response.room;
    } catch (err) {
      await transport.disconnect();
      throw err;
    }
  }

  async function joinLobby(roomId: string, userName: string): Promise<Room> {
    ensureDisconnected();

    await transport.connect(userName);

    const message = {
      request_id: crypto.randomUUID(),
      type: "join-lobby",
      room_id: roomId,
    } satisfies ClientRequest;

    try {
      const response = await transport.request(message);

      setRoom(response.room);
      return response.room;
    } catch (err) {
      await transport.disconnect();
      throw err;
    }
  }

  async function joinRoom(): Promise<Room> {
    const message = {
      request_id: crypto.randomUUID(),
      type: "join-room",
    } satisfies ClientRequest;

    const response = await transport.request(message);

    setRoom(response.room);
    return response.room;
  }

  async function leaveRoom() {
    if (!room) {
      throw new Error("Not currently in a room");
    }

    const message = {
      request_id: crypto.randomUUID(),
      type: "leave-room",
    } satisfies ClientRequest;

    await transport.request(message);

    setRoom(null);
    await transport.disconnect();
  }

  return (
    <RoomContext.Provider
      value={{
        room: activeRoom,
        createRoom,
        joinRoom,
        joinLobby,
        leaveRoom,
      }}
    >
      {children}
    </RoomContext.Provider>
  );
}
