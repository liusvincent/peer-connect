// VideoTile.tsx
import VideoPlayer from "./VideoPlayer";

type VideoTileProps = {
  stream: MediaStream | null;
  name: string;
  cameraEnabled: boolean;
  muted?: boolean;
};

export default function VideoTile({
  stream,
  name,
  cameraEnabled,
  muted = false,
}: VideoTileProps) {
  const initial = name.trim().charAt(0).toUpperCase() || "?";
  const showVideo = stream !== null && cameraEnabled;

  return (
    <article className="relative aspect-video min-w-0 overflow-hidden rounded-xl bg-gray-900">
      {stream && (
        <VideoPlayer
          stream={stream}
          muted={muted}
          className={showVideo ? "" : "invisible"}
        />
      )}

      {!showVideo && (
        <div className="absolute inset-0 grid place-content-center text-center text-white">
          <span className="text-5xl font-semibold">{initial}</span>
        </div>
      )}

      <span className="absolute bottom-2 left-2 rounded-md px-2 py-1 text-sm text-white">
        {name}
      </span>
    </article>
  );
}