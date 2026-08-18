import { useLocalMedia } from "../hooks/useLocalMedia";
import VideoPlayer from "./VideoPlayer";

import {
  Mic,
  MicOff,
  Video,
  VideoOff,
} from "lucide-react";

export default function VideoPreview() {
  const { stream, cameraEnabled, micEnabled, setCameraEnabled, setMicEnabled } =
    useLocalMedia();

  return (
    <div className="relative w-full aspect-video overflow-hidden rounded-xl bg-gray-900">
      {stream && (
        <VideoPlayer
          stream={stream}
          muted={micEnabled}
          className={cameraEnabled ? "" : "invisible"}
        />
      )}

      {!stream && (
        <div className="absolute inset-0 grid place-content-center text-white">
          <p className="text-md text-zinc-300">
            Camera access is required
          </p>
        </div>
      )}

      {stream && !cameraEnabled && (
       <div className="absolute inset-0 grid place-content-center text-white">
          <p className="mt-3 text-md text-zinc-300">
            Camera is off
          </p>
        </div>
      )}

      <div className="absolute bottom-1 left-1/2 flex -translate-x-1/2 items-center gap-3 p-2">
        <button
          type="button"
          onClick={() => setMicEnabled(!micEnabled)}
          className={`grid h-11 w-11 place-content-center rounded-full transition ${
            micEnabled
              ? "bg-zinc-300 text-gray"
              : "bg-red-300 text-gray"
          }`}
        >
          {micEnabled ? <Mic size={20} /> : <MicOff size={20} />}
        </button>

        <button
          type="button"
          onClick={() => setCameraEnabled(!cameraEnabled)}
          className={`grid h-11 w-11 place-content-center rounded-full transition ${
            cameraEnabled
              ? "bg-zinc-300 text-gray"
              : "bg-red-300 text-gray"
          }`}
        >
          {cameraEnabled ? <Video size={20} /> : <VideoOff size={20} />}
        </button>
      </div>
    </div>
  );
}
