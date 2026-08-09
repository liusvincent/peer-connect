import { useCallMedia } from "../hooks/useCallMedia";
import { useLocalMedia } from "../hooks/useLocalMedia"
import { useWebTransport } from "../hooks/useWebTransport"
import { useRoom } from "../hooks/useRoom"

import VideoDisplay from "../components/VideoDisplay";

export default function VideoGrid() {
  const callMedia = useCallMedia();
  const localMedia = useLocalMedia();
  const { room } = useRoom();
  const transport = useWebTransport();

  return (
    <section className="video-grid">
      <VideoDisplay
        stream={localMedia.stream}
        name={transport.user?.name ?? "You"}
        muted
        mirrored
        cameraEnabled={localMedia.cameraEnabled}
      />

      {callMedia.remoteMedia.map(({ participantId, stream }) => {
        const participant = room?.participants[participantId];

        const hasLiveVideo = stream
          .getVideoTracks()
          .some((track) => track.readyState === "live");

        return (
          <VideoDisplay
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
