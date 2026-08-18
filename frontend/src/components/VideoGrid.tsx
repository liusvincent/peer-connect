import { useCallMedia } from "../hooks/useCallMedia";
import { useLocalMedia } from "../hooks/useLocalMedia"
import { useWebTransport } from "../hooks/useWebTransport"
import { useRoom } from "../hooks/useRoom"

import VideoTile from "./VideoTile";

export default function VideoGrid() {
  const callMedia = useCallMedia();
  const localMedia = useLocalMedia();
  const { room } = useRoom();
  const transport = useWebTransport();

  return (
    <section className="grid w-full grid-cols-1 gap-3 p-3 sm:grid-cols-[repeat(auto-fit,minmax(280px,1fr))]">
      <VideoTile
        stream={localMedia.stream}
        name={transport.user?.name ?? "You"}
        cameraEnabled={localMedia.cameraEnabled}
        muted
      />

      {callMedia.remoteMedia.map(({ participantId, stream }) => {
        const participant = room?.participants[participantId];

        const hasLiveVideo = stream
          .getVideoTracks()
          .some((track) => track.readyState === "live");

        return (
          <VideoTile
            key={participantId}
            stream={stream}
            name={participant?.name ?? participantId}
            cameraEnabled={hasLiveVideo}
          />
        );
      })}
    </section>
  );
}
