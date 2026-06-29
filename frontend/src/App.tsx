import "./App.css";

import Header from "./components/Header";
import Status from "./components/Status";
import VideoDisplay from "./components/VideoDisplay";
import ControlPanel from "./components/ControlPanel";
import BallData from "./components/BallData";

import { connectWebTransport, sendMessage } from "./services/webtransport"

import { useState } from "react";

function App() {
  const [status, setStatus] = useState("Disconnected")

  const handleConnect = async () => {
    setStatus("Connecting...")
    const ok = await connectWebTransport()
    setStatus(ok ? "Connected" : "Disconnected")
  }

  const [ballX] = useState<number | null>(null);
  const [ballY] = useState<number | null>(null);

  return (
    <>
      <Header />
      <Status status={status} />
      <VideoDisplay />
      <ControlPanel 
        onConnect={handleConnect} 
        onSendMessage={() => sendMessage({type: "ping"})} 
      />
      <BallData x={ballX} y={ballY} />
    </>
  );
}

export default App;
