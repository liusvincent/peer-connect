import { Navigate, useNavigate } from "react-router-dom";
import { useEffect } from "react";

import { useWebTransport } from "../hooks/useWebTransport";
import { useRoom } from "../hooks/useRoom";
import { useLocalMedia } from "../hooks/useLocalMedia";
import { useCallMedia } from "../hooks/useCallMedia";

import VideoGrid from "../components/VideoGrid";
import CallControl from "../components/CallControl"

export default function Room() {
  const navigate = useNavigate();
  const transport = useWebTransport();
  const { room, leaveRoom } = useRoom();
  const localMedia = useLocalMedia();
  const callMedia = useCallMedia();

  useEffect(() => {
    if (!room || !transport.user) {
      return;
    }

    void callMedia.start().catch((err) => {
      console.error("Could not start the call", err);
    });
  }, []);

  if (!room || !transport.user) {
    return <Navigate to="/" replace />;
  }

  function handleCamera(): void {
    localMedia.setCameraEnabled(!localMedia.cameraEnabled)
  }

  function handleMic(): void {
    localMedia.setMicEnabled(!localMedia.micEnabled)
  }

  async function handleLeaveRoom(): Promise<void> {
    await leaveRoom();
    navigate(`/`, { replace: true });
  }

  return (
    <main>
      <VideoGrid />
      <CallControl 
        onCamera={handleCamera}
        onMic={handleMic}
        onEnd={handleLeaveRoom}
      />
    </main>
  );
}
