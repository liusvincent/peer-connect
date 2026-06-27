type ControlPanelProps = {
  onConnect: () => void;
};

function ControlPanel({ onConnect }: ControlPanelProps) {
  return (
    <section>
      <button onClick={onConnect}>Connect</button>
    </section>
  );
}

export default ControlPanel;
