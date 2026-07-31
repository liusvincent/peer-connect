import { Navigate, useNavigate, useParams } from "react-router-dom";
import { useWebTransport } from "../hooks/useWebTransport";

function Lobby() {
  const { roomId } = useParams();
  const navigate = useNavigate();
  const { disconnect } = useWebTransport();

  if (!roomId) {
    return <Navigate to="/" replace />;
  }

  const handleEnterRoom = () => {
    navigate(`/room/${encodeURIComponent(roomId)}`);
  };

  const handleLeaveLobby = async () => {
    await disconnect();
    navigate(`/`, {replace: true});
  };

  return (
    <main>
      <p>Room: {roomId}</p>
      
      <button onClick={handleEnterRoom}>Enter room</button>
      <button onClick={handleLeaveLobby}>Leave lobby</button>
    </main>
  );
}

export default Lobby;
