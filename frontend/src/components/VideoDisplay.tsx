import { useEffect, useRef } from "react";

type VideoDisplayProps = {
  stream: MediaStream | null;
}

function VideoDisplay({ stream }: VideoDisplayProps ) {
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
    <section style={{ display: "flex", justifyContent: "center" }}>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        width={640}
        height={480}
      />
    </section>
  );
}

export default VideoDisplay;
