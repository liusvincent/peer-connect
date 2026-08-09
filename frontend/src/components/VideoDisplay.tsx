import { useEffect, useRef } from "react";

type VideoDisplayProps = {
  stream: MediaStream | null;
  name: string;
  muted?: boolean;
  mirrored?: boolean;
  cameraEnabled?: boolean;
};

export default function VideoDisplay({
  stream,
  name,
  muted = false,
  mirrored = false,
  cameraEnabled = true,
}: VideoDisplayProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !cameraEnabled) return;
    video.srcObject = stream;
    return () => {
      video.srcObject = null;
    };
  }, [stream, cameraEnabled]);

  const showVideo = stream && cameraEnabled;
  const initial = name.trim().charAt(0).toUpperCase() || "?";

  return (
    <article className="video-tile">
      {showVideo ? (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted={muted}
          className={mirrored ? "video--mirrored" : undefined}
        />
      ) : (
        <div className="video-placeholder">
          <span>{initial}</span>
          <p>Camera off</p>
        </div>
      )}
      <footer className="video-tile__name">{name}</footer>
    </article>
  );
}
