import { useEffect, useRef } from "react";

type VideoDisplayProps = {
  stream: MediaStream | null;
  name: string;
  muted?: boolean;
  mirrored?: boolean;
};

function VideoDisplay({
  stream,
  name,
  muted = false,
  mirrored = false,
}: VideoDisplayProps) {
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
    <article className="video-tile">
      {stream ? (
        <video
        ref={videoRef}
        autoPlay
        playsInline
        muted={muted}
        className={mirrored ? "video--mirrored" : undefined}
      />
      ) : (
        <div className="video-placeholder">
          <span>{name.slice(0, 1).toUpperCase()}</span>
          <p>Camera off</p>
        </div>
      )}
      <footer className="video-tile__name">{name}</footer>
    </article>
  );
}

export default VideoDisplay;
