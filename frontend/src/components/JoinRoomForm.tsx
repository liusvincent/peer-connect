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
      <div>
        <div className="flex gap-1.5">
          <div className="flex items-center w-140 bg-gray-200 text-gray-700 rounded-full px-1.5 py-1">
            <input
              className="bg-gray-200 rounded-full px-6 py-3 outline-none"
              placeholder="Enter your display name"
              onChange={(event) => setUserName(event.target.value)}
            />

            <div className="h-8 w-[1.5px] translate-y-0.5 bg-gray-400" />

            <input
              className="flex-1 bg-transparent px-6 py-3 outline-none"
              placeholder="Enter room code"
              onChange={(event) => setRoomCode(event.target.value)}
            />

            <button
              className="
                bg-blue-600 text-white rounded-full px-6 py-3 outline-none
                disabled:bg-gray-300
                disabled:text-gray-600
              "
              onClick={() => onJoin(roomCode.trim(), userName.trim())}
              disabled={!validRoomCode || !validName}
            >
              Join
            </button>
          </div>

          <button
            className="
              bg-green-100 text-black rounded-full px-6 py-3 outline-none
              disabled:bg-gray-300
              disabled:text-gray-600
            "
            onClick={() => onCreate(userName.trim())}
            disabled={!validName}
          >
            New
          </button>
        </div>
      </div>
    </section>
  );
}
