import VideoDisplay from "../components/VideoDisplay";

function VideoGrid() {
  return (
    <main>
      <div className="video-grid">
        {participants.map(participant) => (
            <VideoDisplay 
              key={participant.id}
              stream={participant.stream}
              name={participant.name}
              muted={participant.isLocal}
              mirrored={participant.isLocal}
            />
        )}
      </div>
    </main>
  );
}

export default VideoGrid;
