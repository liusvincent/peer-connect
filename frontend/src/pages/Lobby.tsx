import { Navigate, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";

import { useWebTransport } from "../hooks/useWebTransport";
import { useRoom } from "../hooks/useRoom";
import { useLocalMedia } from "../hooks/useLocalMedia";

import VideoPreview from "../components/VideoPreview";

export default function Lobby() {
  const navigate = useNavigate();
  const transport = useWebTransport();
  const { room, joinRoom, leaveRoom } = useRoom();
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

  async function handleLeaveLobby(): Promise<void> {
    setLobbyError(null);
    try {
      await leaveRoom();
      localMedia.stop();

      navigate("/", { replace: true });
    } catch (error) {
      console.error(error);
      setLobbyError("Could not leave the lobby.");
    }
  }

  const displayedError = lobbyError ?? localMedia.error;

  function closeErrorDialog(): void {
    setLobbyError(null);
    localMedia.clearError();
  }

  return (
    <main>
      <VideoPreview name={transport.user.name} />
      <button onClick={handleJoinRoom}>Join</button>
      <button onClick={handleLeaveLobby}>Leave</button>
      <dialog open={displayedError !== null}>
        <p>{displayedError}</p>
        {lobbyError && (
          <button onClick={closeErrorDialog}>Close</button>
        )}
      </dialog>
    </main>
  );
}
