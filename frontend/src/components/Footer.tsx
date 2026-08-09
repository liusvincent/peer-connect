import { useWebTransport } from "../hooks/useWebTransport";

export default function Footer() {
  const transport = useWebTransport();

  return (
    <footer>
      <p>
        WebTransport Connection: <span>{transport.status}</span>
        <br />
        {/* RTCPeerConnection State : <span>{}</span> */}
        {/* <br /> */}
        Participant ID: <span>{transport.user?.id ?? "—"}</span>
        <br />
        Display Name: <span>{transport.user?.name ?? "—"}</span>
      </p>
    </footer>
  );
}
