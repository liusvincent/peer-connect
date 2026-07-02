import "./App.css";

import Header from "./components/Header";
import Status from "./components/Status";
import VideoDisplay from "./components/VideoDisplay";
import ControlPanel from "./components/ControlPanel";
import BallData from "./components/BallData";

import { connectWebTransport } from "./services/webtransport";
import { startWebRTC } from "./services/webrtc";

import { useState } from "react";

function App() {
  const [status, setStatus] = useState("Disconnected");
  const [ remoteStream, setRemoteStream ] = useState<MediaStream |null>(null);

  const handleStartWebRTC = () => {
    void startWebRTC(setRemoteStream);
  }
  
  const handleConnect = async () => {
    setStatus("Connecting...");
    const ok = await connectWebTransport();
    setStatus(ok ? "Connected" : "Disconnected");
  };

  const [ballX] = useState<number | null>(null);
  const [ballY] = useState<number | null>(null);

  return (
    <>
      <Header />
      <Status status={status} />
      <VideoDisplay stream={remoteStream} />
      <ControlPanel onConnect={handleConnect} onSendOffer={handleStartWebRTC} />
      <BallData x={ballX} y={ballY} />
    </>
  );
}

export default App;
