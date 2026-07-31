import { useNavigate } from "react-router-dom";
import { useState } from "react";
import JoinRoomForm from "../components/JoinRoomForm";
import { useRoom } from "../hooks/useRoom";

function Home() {
  const navigate = useNavigate();
  const { joinLobby, createRoom } = useRoom();

  const [error, setError] = useState<string | null>(null);

  const handleJoin = async (roomId: string, userName: string) => {
    console.log("joining room: ", roomId);
    setError(null);

    try {
      const joinedRoom = await joinLobby(roomId, userName);
      navigate(`/lobby/${encodeURIComponent(joinedRoom.id)}`);
    } catch (err) {
      console.error(err);
      setError("Could not join the room");
    }
  };

  const handleCreate = async (userName: string) => {
    console.log("Creating room...");
    setError(null);

    try {
      const joinedRoom = await createRoom(userName);
      navigate(`/room/${encodeURIComponent(joinedRoom.id)}`);
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
