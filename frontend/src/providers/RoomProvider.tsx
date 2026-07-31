import { useState, type ReactNode } from "react";
import { useWebTransport } from "../hooks/useWebTransport";
import { RoomContext } from "../contexts/RoomContext";
import type { Room } from "../types/room";
import { type ClientRequest, parseServerMessage } from "../protocols";

export function RoomProvider({ children }: { children: ReactNode }) {
  const transport = useWebTransport();

  const [room, setRoom] = useState<Room | null>(null);

  const createRoom = async (userName: string): Promise<Room> => {
    const message = {
      request_id: crypto.randomUUID(),
      type: "create-room",
      user_name: userName,
    } satisfies ClientRequest;

    const rawResponse = await transport.request(message);
    const response = parseServerMessage(message.type, rawResponse);

    setRoom(response.room);
    return response.room;
  };

  const joinLobby = async (roomId: string, userName: string): Promise<Room> => {
    const message = {
      request_id: crypto.randomUUID(),
      type: "join-lobby",
      room_id: roomId,
      user_name: userName,
    } satisfies ClientRequest;

    const rawResponse = await transport.request(message);
    const response = parseServerMessage(message.type, rawResponse);

    setRoom(response.room);
    return response.room;
  };

  const joinRoom = async (): Promise<Room> => {
    const message = {
      request_id: crypto.randomUUID(),
      type: "join-room",
    } satisfies ClientRequest;

    const rawResponse = await transport.request(message);
    const response = parseServerMessage(message.type, rawResponse);

    setRoom(response.room);
    return response.room;
  };

  const leaveRoom = async () => {
    if (!room) {
      throw new Error("Not currently in a room");
    }

    const message = {
      request_id: crypto.randomUUID(),
      type: "leave-room",
      room_id: room.id,
    } satisfies ClientRequest;

    const rawResponse = await transport.request(message);
    parseServerMessage(message.type, rawResponse);

    setRoom(null);
    await transport.disconnect();
  };

  return (
    <RoomContext.Provider
      value={{
        room,
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
