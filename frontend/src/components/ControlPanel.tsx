type ControlPanelProps = {
  onConnect: () => void;
  onSendOffer: () => void;
};

function ControlPanel({ onConnect, onSendOffer }: ControlPanelProps) {
  return (
    <section>
      <button onClick={onConnect}>Connect</button>
      <button onClick={onSendOffer}>Start WebRTC</button>
    </section>
  );
}

export default ControlPanel;
