import {
  Mic,
  MicOff,
  Video,
  VideoOff,
  PhoneOff
} from "lucide-react";

type CallControlProps = {
  cameraEnabled: boolean;
  micEnabled: boolean;
  onCamera: () => void;
  onMic: () => void;
  onEnd: () => void;
};

export default function CallControl({
  cameraEnabled,
  micEnabled,
  onCamera,
  onMic,
  onEnd,
}: CallControlProps) {
  return (
    <div className="flex justify-center gap-7">
      <button 
        type="button" 
        onClick={onCamera}
        className={`grid h-11 w-11 place-content-center rounded-full transition ${
            micEnabled
              ? "bg-zinc-700 text-gray-200"
              : "bg-red-300 text-gray"
          }`}
      >
        {cameraEnabled ? <Video /> : <VideoOff />}
      </button>

      <button 
        type="button" 
        onClick={onMic}
        className={`grid h-11 w-11 place-content-center rounded-full transition ${
          cameraEnabled
            ? "bg-zinc-700 text-gray-200"
            : "bg-red-300 text-gray"
        }`}
      >
        {micEnabled ? <Mic /> : <MicOff />}
      </button>

      <button 
        type="button" 
        onClick={onEnd}
        className="grid h-11 w-11 place-content-center rounded-full transition bg-red-600"
      >
        <PhoneOff />
      </button>
    </div>
  );
}
