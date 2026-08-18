import { useEffect, useRef } from "react";

type VideoPlayerProps = {
  stream: MediaStream | null;
  muted?: boolean;
  className?: string;
};

export default function VideoPlayer({
  stream,
  muted = false,
  className = "",
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    video.srcObject = stream;

    return () => {
      video.srcObject = null;
    };
  }, [stream]);

  return (
    <video
      ref={videoRef}
      autoPlay
      playsInline
      muted={muted}
      className={`h-full w-full object-cover -scale-x-100 ${className}`}
    />
  );
}
