import { useWebTransport } from "../hooks/useWebTransport";

function Footer() {
  const { status: webTransportStatus, roomSession } = useWebTransport();

  return (
    <footer>
      <p>
        WebTransport Connection: <span>{webTransportStatus}</span>
        <br />
        Participant ID: <span>{roomSession?.participantId ?? "—"}</span>
        <br />
        Room ID: <span>{roomSession?.roomId ?? "—"}</span>
        <br />
        User Name: <span>{roomSession?.userName ?? "—"}</span>
      </p>
    </footer>
  );
}

export default Footer;
