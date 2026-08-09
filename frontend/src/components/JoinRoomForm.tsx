import { useState } from "react";

type JoinRoomFormProps = {
  onJoin: (roomCode: string, userName: string) => Promise<void>;
  onCreate: (userName: string) => Promise<void>;
};

export default function JoinRoomForm({ onJoin, onCreate }: JoinRoomFormProps) {
  const [roomCode, setRoomCode] = useState("");
  const [userName, setUserName] = useState("");

  const validName = userName.trim() !== "";
  const validRoomCode = roomCode.trim() !== "";

  return (
    <section>
      <div className="join-row">
        <div className="join-box">
          <input
            placeholder="Enter your display name"
            onChange={(event) => setUserName(event.target.value)}
          />
          <input
            placeholder="Enter room code or link"
            onChange={(event) => setRoomCode(event.target.value)}
          />
          <button
            onClick={() => onJoin(roomCode.trim(), userName.trim())}
            disabled={!validRoomCode || !validName}
          >
            Join Room
          </button>
          <button 
            onClick={() => onCreate(userName.trim())}
            disabled={!validName}
          >
            Create New Room
          </button>
        </div>
      </div>
    </section>
  );
}
