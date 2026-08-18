import { Navigate, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";

import { useWebTransport } from "../hooks/useWebTransport";
import { useRoom } from "../hooks/useRoom";
import { useLocalMedia } from "../hooks/useLocalMedia";

import VideoPreview from "../components/VideoPreview";

export default function Lobby() {
  const navigate = useNavigate();
  const transport = useWebTransport();
  const { room, joinRoom } = useRoom();
  const localMedia = useLocalMedia();

  const [lobbyError, setLobbyError] = useState<string | null>(null);

  useEffect(() => {
    if (!room || !transport.user) return;
    void localMedia.start().catch(() => {});
  }, []);

  if (!room || !transport.user) {
    return <Navigate to="/" replace />;
  }

  async function handleJoinRoom(): Promise<void> {
    setLobbyError(null);
    try {
      const room = await joinRoom();
      navigate(`/room/${encodeURIComponent(room.id)}`);
    } catch (err) {
      console.error(err);
      setLobbyError("Could not join the room.");
    }
  }

  const displayedError = lobbyError ?? localMedia.error;

  function closeErrorDialog(): void {
    setLobbyError(null);
    localMedia.clearError();
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6 gap-20">
      <div className="w-[800px]">
        <VideoPreview />
      </div>

      <div className="flex flex-col items-center justify-center gap-3">
        <h2 className="text-2xl">
          Ready to Join?
        </h2>
        <button
          className="bg-blue-600 w-25 text-white rounded-full px-6 py-3 outline-none"
          onClick={handleJoinRoom}
        >
          Join
        </button>
      </div>

      {displayedError && (
        <div className="fixed bottom-12 left-4 max-w-sm bg-gray-900 px-4 py-3 text-sm text-white shadow-lg">
          <div className="flex items-center gap-4">
            <p>{lobbyError}</p>

            <button
              onClick={() => closeErrorDialog()}
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
