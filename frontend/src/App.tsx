import { BrowserRouter, Outlet, Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import Lobby from "./pages/Lobby";
import Room from "./pages/Room";
import Footer from "./components/Footer";

import { WebTransportProvider } from "./providers/WebTransportProvider";
import { RoomProvider } from "./providers/RoomProvider";
import { LocalMediaProvider } from "./providers/LocalMediaProvider";
import { CallMediaProvider } from "./providers/CallMediaProvider";

function MeetingLayout() {
  return (
    <LocalMediaProvider>
      <CallMediaProvider>
        <Outlet />
      </CallMediaProvider>
    </LocalMediaProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <WebTransportProvider>
        <RoomProvider>
          <Routes>
            <Route path="/" element={<Home />} />

            <Route element={<MeetingLayout />}>
              <Route path="/lobby/:roomId" element={<Lobby />} />
              <Route path="/room/:roomId" element={<Room />} />
            </Route>
          </Routes>
          
          <Footer />
        </RoomProvider>
      </WebTransportProvider>
    </BrowserRouter>
  );
}
