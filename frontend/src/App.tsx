import "./App.css";

import { BrowserRouter, Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import Lobby from "./pages/Lobby";
import Room from "./pages/Room";
import Footer from "./components/Footer";

import { WebTransportProvider } from "./providers/WebTransportProvider";
import { RoomProvider } from "./providers/RoomProvider";
import { MediaProvider } from "./providers/MediaProvider";

function App() {
  return (
    <BrowserRouter>
      <WebTransportProvider>
        <RoomProvider>
          <MediaProvider>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/lobby/:roomId" element={<Lobby />} />
              <Route path="/room/:roomId" element={<Room />} />
            </Routes>
            <Footer />
          </MediaProvider>
        </RoomProvider>
      </WebTransportProvider>
    </BrowserRouter>
  );
}

export default App;
