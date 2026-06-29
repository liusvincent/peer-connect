type ControlPanelProps = {
  onConnect: () => void
  onSendMessage: () => void
};

function ControlPanel({ onConnect, onSendMessage }: ControlPanelProps) {
  return (
    <section>
      <button onClick={onConnect}>Connect</button>
      <button onClick={onSendMessage}>Send Message</button>
    </section>
  );
}

export default ControlPanel;
