type CallControlProps = {
  onCamera: () => void;
  onMic: () => void;
  onEnd: () => void;
};

export default function CallControl({
  onCamera,
  onMic,
  onEnd,
}: CallControlProps) {
  return (
    <div>
      <button onClick={onCamera}>Camera</button>
      <button onClick={onMic}>Mic</button>
      <button onClick={onEnd}>End</button>
    </div>
  );
}
