import "./App.css";

import Header from "./components/Header";
import Status from "./components/Status";
import VideoDisplay from "./components/VideoDisplay";
import ControlPanel from "./components/ControlPanel";
import BallData from "./components/BallData";

import { useState } from "react";

function App() {
  const [status, setStatus] = useState("Disconnected")

  const handleConnect = () => {
    setStatus("Connecting...")
    // to be expanded on
    // setStatus("Connected")
  }

  const [ballX, setBallX] = useState<number | null>(null);
  const [ballY, setBallY] = useState<number | null>(null);

  return (
    <>
      <Header />
      <Status status={status} />
      <VideoDisplay />
      <ControlPanel onConnect={handleConnect} />
      <BallData x={ballX} y={ballY} />
    </>
  );
}

export default App;
