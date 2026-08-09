import { useEffect, useRef, useState, type ReactNode } from "react";

import { useWebTransport } from "../hooks/useWebTransport";
import { useLocalMedia } from "../hooks/useLocalMedia";

import {
  type WebRTCSession,
  type RemoteTrackInfo,
  createWebRTCSession,
} from "../services/webrtc";

import type { ClientRequest, ServerEvent } from "../protocols";

import {
  type CallMediaStatus,
  type RemoteParticipantMedia,
  CallMediaContext,
} from "../contexts/CallMediaContext";

type RemoteSubscription = {
  participantId: string;
  trackId: string;
  kind: "audio" | "video";
  track: MediaStreamTrack | null;
}

export function CallMediaProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<CallMediaStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [remoteMedia, setRemoteMedia] = useState<RemoteParticipantMedia[]>([]);
  const [connectionState, setConnectionState] =
    useState<RTCPeerConnectionState | null>(null);

  const transport = useWebTransport();
  const localMedia = useLocalMedia();

  const sessionRef = useRef<WebRTCSession | null>(null);
  const startPromiseRef = useRef<Promise<WebRTCSession> | null>(null);

  const remoteByMidRef = useRef<Map<string, RemoteSubscription>>(new Map());

  useEffect(() => {
    return () => {
      sessionRef.current?.close();
      sessionRef.current = null;
      remoteByMidRef.current.clear();
    };
  }, []);

  useEffect(() => {
    return transport.listen(handleRenegotiation)
  }, [transport]);

  async function start(): Promise<WebRTCSession> {
    if (sessionRef.current) {
      return sessionRef.current;
    }

    if (startPromiseRef.current) {
      return startPromiseRef.current;
    }

    setStatus("connecting");
    setError(null);

    const startPromise = startSession();

    startPromiseRef.current = startPromise;

    try {
      return await startPromise;
    } finally {
      if (startPromiseRef.current === startPromise) {
        startPromiseRef.current = null;
      }
    }
  }

  async function startSession(): Promise<WebRTCSession> {
    const session = createWebRTCSession({
      onRemoteTrack(media) {
        handleRemoteTrack(media);
      },
      onConnectionStateChange(state) {
        handleConnectionStateChange(state);
      },
    });

    sessionRef.current = session;

    try {
      const localStream = localMedia.stream ?? (await localMedia.start());

      const offerSdp = await session.createOffer(localStream);

      const message = {
        request_id: crypto.randomUUID(),
        type: "webrtc-offer",
        sdp: offerSdp,
      } satisfies ClientRequest;

      const answer = await transport.request(message);

      await session.applyAnswer(answer.sdp);

      await transport.sendEvent({
        type: "webrtc-ready",
        event_id: crypto.randomUUID(),
      })

      return session;
    } catch (err) {
      stop();
      throw err;
    }
  }

  function handleRemoteTrack(media: RemoteTrackInfo): void {
    if (!media.mid) {
      return;
    }

    const remote = remoteByMidRef.current.get(media.mid);
    if (!remote) return;

    remote.track = media.track

    setRemoteMedia((current) =>
      addParticipantTrack(current, remote.participantId, media.track),
    );
  }

  function addParticipantTrack(
    current: RemoteParticipantMedia[],
    participantId: string,
    track: MediaStreamTrack,
  ): RemoteParticipantMedia[] {
    const existing = current.find(
      (participant) => participant.participantId === participantId,
    );

    if (!existing) {
      return [
        ...current,
        {
          participantId,
          stream: new MediaStream([track]),
        },
      ];
    }

    if (!existing.stream.getTrackById(track.id)) {
      existing.stream.addTrack(track);
    }

    return [...current];
  }

  function stop(): void {
    const session = sessionRef.current;
    resetSession(session);
    session?.close();
  }

  function handleConnectionStateChange(state: RTCPeerConnectionState): void {
    setConnectionState(state);

    if (state === "connected") {
      setStatus("connected");
      return;
    }

    if (state === "failed") {
      endFailedSession(sessionRef.current);
      return;
    }

    if (state === "closed") {
      resetSession(sessionRef.current);
    }
  }

  function endFailedSession(session: WebRTCSession | null): void {
    if (!session || sessionRef.current !== session) {
      return;
    }

    sessionRef.current = null;
    remoteByMidRef.current.clear();
    session.close();

    setStatus("error");
    setRemoteMedia([]);
    setError("The call connection failed.");
  }

  function resetSession(session: WebRTCSession | null): void {
    if (!session || sessionRef.current !== session) {
      return;
    }

    sessionRef.current = null;
    remoteByMidRef.current.clear();

    setStatus("idle");
    setConnectionState(null);
    setRemoteMedia([]);
  }

  function clearError(): void {
    setError(null);

    if (status === "error") {
      setStatus("idle");
    }
  }

  async function handleRenegotiation(event: ServerEvent): Promise<void> {
    console.log("received server event", event);
    if (event.type !== "webrtc-renegotiation-offer")
      return

    const session = sessionRef.current;
    if (!session) {
      return;
    }

    const previous = remoteByMidRef.current;
    const next = new Map<string, RemoteSubscription>();

    for (const item of event.media) {
      const existing = previous.get(item.mid);

      const sameSubscription =
        existing?.participantId === item.participant_id &&
        existing.trackId === item.track_id;

      next.set(item.mid, {
        participantId: item.participant_id,
        trackId: item.track_id,
        kind: item.kind,
        track: sameSubscription ? existing.track : null,
      });
    }

    const removedTracks = new Set<MediaStreamTrack>();

    for (const [mid, previousSubscription] of previous) {
      if (!previousSubscription.track) {
        continue;
      }

      const nextSubscription = next.get(mid);

      if (nextSubscription?.track !== previousSubscription.track) {
        removedTracks.add(previousSubscription.track);
      }
    }

    remoteByMidRef.current = next;

    if (removedTracks.size > 0) {
      setRemoteMedia((current) =>
        current.flatMap((participant) => {
          const remainingTracks = participant.stream
            .getTracks()
            .filter((track) => !removedTracks.has(track));

          if (remainingTracks.length === 0) {
            return [];
          }

          return [{
            ...participant,
            stream: new MediaStream(remainingTracks),
          }];
        }),
      );

      for (const track of removedTracks) {
        track.stop();
      }
    }

    const answerSdp = await session.createAnswer(event.sdp);
    console.log("created renegotiation answer");

    await transport.sendEvent({
      type: "webrtc-renegotiation-answer",
      event_id: event.event_id,
      sdp: answerSdp,
    });
    console.log("sent renegotiation answer");
  }

  return (
    <CallMediaContext.Provider
      value={{
        status,
        connectionState,
        error,
        remoteMedia,
        start,
        stop,
        clearError,
      }}
    >
      {children}
    </CallMediaContext.Provider>
  );
}