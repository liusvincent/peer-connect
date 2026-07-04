type ControlPanelProps = {
  onConnect: () => void;
  onDisconnect: () => void;
  onSendOffer: () => void;
  onFps: (fps: number) => void;
  fps: number;
  status: string;
  webrtcActive: boolean;
};

function ControlPanel({
  onConnect,
  onDisconnect,
  onSendOffer,
  onFps,
  fps,
  status,
  webrtcActive,
}: ControlPanelProps) {
  return (
    <section>
      <button onClick={onConnect} disabled={status !== "Disconnected"}>
        Connect
      </button>
      <button onClick={onDisconnect} disabled={status !== "Connected"}>
        Disconnect
      </button>
      <button onClick={onSendOffer} disabled={status !== "Connected" || webrtcActive}>
        Start WebRTC
      </button>
      <label>
        FPS: {fps}
        <input
          type="range"
          min="1"
          max="30"
          value={fps}
          onChange={(event) => {
            onFps(Number(event.target.value));
          }}
          disabled={status !== "Connected"}
        />
      </label>
    </section>
  );
}

export default ControlPanel;
