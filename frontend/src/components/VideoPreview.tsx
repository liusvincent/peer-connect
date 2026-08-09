import { useLocalMedia } from "../hooks/useLocalMedia";
import VideoDisplay from "../components/VideoDisplay";

type VideoPreviewProps = {
  name: string;
};

export default function VideoPreview({ name }: VideoPreviewProps) {
  const {
    stream,
    cameraEnabled,
    micEnabled,
    setCameraEnabled,
    setMicEnabled,
  } = useLocalMedia();

  return (
    <div className="video-preview">
      <VideoDisplay
        stream={stream}
        name={name}
        cameraEnabled={cameraEnabled}
        muted
        mirrored
      />

      <div className="video-preview__controls">
        <button
          className="media-control"
          onClick={() => setMicEnabled(!micEnabled)}
        >
          {micEnabled ? "Mic on" : "Mic off"}
        </button>

        <button
          className="media-control"
          onClick={() => setCameraEnabled(!cameraEnabled)}
        >
          {cameraEnabled ? "Camera on" : "Camera off"}
        </button>
      </div>
    </div>
  );
}
