import "./App.css";

import Header from "./components/Header";
import Status from "./components/Status";
import VideoDisplay from "./components/VideoDisplay";
import ControlPanel from "./components/ControlPanel";
import BallData from "./components/BallData";

import {
  connectWebTransport,
  sendMessage,
  disconnectWebTransport,
} from "./services/webtransport";
import {
  startWebRTC,
  handleWebRTCAnswer,
  disconnectWebRTC,
} from "./services/webrtc";

import { useState, useEffect } from "react";

function App() {
  const [status, setStatus] = useState("Disconnected");
  const [webrtcActive, setWebRTCActive] = useState(false);
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);
  const [fps, setFps] = useState(30);
  const [ballX, setX] = useState<number | null>(null);
  const [ballY, setY] = useState<number | null>(null);

  const handleStartWebRTC = async () => {
    setWebRTCActive(true);
    try {
      await startWebRTC(setRemoteStream, resetWebRTCState);
    } catch (err) {
      setWebRTCActive(false);
      console.error("Failed to start WebRTC:", err);
    }
  };

  const resetWebRTCState = () => {
    setWebRTCActive(false);
    setRemoteStream(null);
    setX(null);
    setY(null);
  }

  const handleBallCoords = (ballX: number, ballY: number) => {
    setX(ballX);
    setY(ballY);
  };

  const handleConnect = async () => {
    setStatus("Connecting...");
    const ok = await connectWebTransport({
      onAnswer: handleWebRTCAnswer,
      onCoordinates: handleBallCoords,
      onDisconnect: resetDisconnectedState,
    });
    setStatus(ok ? "Connected" : "Disconnected");
  };

  const resetDisconnectedState = () => {
    disconnectWebRTC();
    resetWebRTCState();
    setStatus("Disconnected");
  };

  const handleDisconnect = async () => {
    try {
      await disconnectWebTransport();
    } finally {
      resetDisconnectedState();
    }
  };

  // WebTransport fps change
  useEffect(() => {
    if (status !== "Connected") return;

    const timeout = setTimeout(() => {
      sendMessage({
        type: "set-fps",
        fps,
      }).catch(console.error);
    }, 250);
    return () => clearTimeout(timeout);
  }, [fps, status]);

  return (
    <>
      <Header />
      <Status status={status} />
      <VideoDisplay stream={remoteStream} />
      <ControlPanel
        onConnect={handleConnect}
        onDisconnect={handleDisconnect}
        onSendOffer={handleStartWebRTC}
        onFps={setFps}
        fps={fps}
        status={status}
        webrtcActive={webrtcActive}
      />
      <BallData x={ballX} y={ballY} />
    </>
  );
}

export default App;
