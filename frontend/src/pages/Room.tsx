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

    return () => {
      callMedia.stop()
    }
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
    navigate(`/`, { replace: true });
    await leaveRoom();
  }

  return (
    <main className="flex min-h-screen flex-col overflow-hidden bg-[#202124] pb-8 text-white">
      <header className="flex items-center justify-between px-5 py-3">
        <div>
          <p className="text-sm text-gray-400">
            Room: {room.id}
          </p>
        </div>

        <div className="rounded-full bg-[#303134] px-4 py-2 text-sm text-gray-300">
          {callMedia.status}
        </div>
      </header>

      <section className="flex min-h-0 flex-1 items-center justify-center overflow-auto px-4 py-2">
        <div className="w-full max-w-7xl">
          <VideoGrid />
        </div>
      </section>

      <div className="p-3">
        <CallControl
          cameraEnabled={localMedia.cameraEnabled}
          micEnabled={localMedia.micEnabled}
          onCamera={handleCamera}
          onMic={handleMic}
          onEnd={handleLeaveRoom}
        />
      </div>
    </main>
  );
}
