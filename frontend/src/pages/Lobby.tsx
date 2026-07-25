import { Navigate, useNavigate, useParams } from "react-router-dom";

function Lobby() {
  const { roomId } = useParams();
  const navigate = useNavigate();

  if (!roomId) {
    return <Navigate to="/" replace />;
  }

  const handleEnterRoom = () => {
    navigate(`/room/${encodeURIComponent(roomId)}`);
  };

  return (
    <main>
      <p>Room: {roomId}</p>

      <button onClick={handleEnterRoom}>Enter room</button>
    </main>
  );
}

export default Lobby;
