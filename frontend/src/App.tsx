import "./App.css";

import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Lobby from "./pages/Lobby";
import Room from "./pages/Room";
import { WebTransportProvider } from "./contexts/WebTransportProvider";


function App() {
  return (
    <BrowserRouter>
      <WebTransportProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/lobby/:roomId" element={<Lobby />} />
          <Route path="/room/:roomId" element={<Room />} />
        </Routes>
      </WebTransportProvider>
    </BrowserRouter>
  );
}

export default App;
