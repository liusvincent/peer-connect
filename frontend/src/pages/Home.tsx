import { useNavigate } from "react-router-dom";
import { useState } from "react";

import JoinRoomForm from "../components/JoinRoomForm";
import { useWebTransport } from "../hooks/useWebTransport";

function Home() {
  const navigate = useNavigate();
  const { joinRoom, createRoom } = useWebTransport();
  
  const [error, setError] = useState<string | null>(null);

  const handleJoin = async (roomId: string) => {
    console.log("joining room: ", roomId);
    setError(null);

    try {
        const session = await joinRoom(roomId);
        navigate(`/lobby/${encodeURIComponent(session.roomId)}`)
    } catch (err) {
        console.error(err);
        setError("Could not join the room")
    }
  };

  const handleCreate = async () => {
    setError(null);

    try {
      const session = await createRoom();
      navigate(`/lobby/${encodeURIComponent(session.roomId)}`);
    } catch (error) {
      console.error(error);
      setError("Could not create the room.");
    }
  };

  return (
    <main>
      <JoinRoomForm onJoin={handleJoin} onCreate={handleCreate} />
      {error && <p role="alert">{error}</p>}
    </main>
  );
}

export default Home;
