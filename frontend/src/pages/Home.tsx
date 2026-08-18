import { useNavigate } from "react-router-dom";
import { useState } from "react";
import JoinRoomForm from "../components/JoinRoomForm";
import { useRoom } from "../hooks/useRoom";

export default function Home() {
  const navigate = useNavigate();
  const { joinLobby, createRoom } = useRoom();

  const [error, setError] = useState<string | null>(null);

  async function handleJoin(roomId: string, userName: string): Promise<void> {
    setError(null);

    try {
      const room = await joinLobby(roomId, userName);
      navigate(`/lobby/${encodeURIComponent(room.id)}`);
    } catch (err) {
      console.error(err);
      setError("Could not join the room");
    }
  };

  async function handleCreate(userName: string): Promise<void> {
    setError(null);

    try {
      const room = await createRoom(userName);
      navigate(`/room/${encodeURIComponent(room.id)}`);
    } catch (error) {
      console.error(error);
      setError("Could not create the room.");
    }
  };

  return (
    <main className="flex min-h-screen justify-center p-6">
      <JoinRoomForm onJoin={handleJoin} onCreate={handleCreate} />
      
      {error && (
        <div className="fixed bottom-12 left-4 max-w-sm bg-gray-900 px-4 py-3 text-sm text-white shadow-lg">
          <div className="flex items-center gap-4">
            <p>{error}</p>

            <button
              onClick={() => setError(null)}
              className="ml-auto font-medium text-blue-300 hover:text-blue-200"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
