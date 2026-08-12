import { useEffect, useRef, useState, type ReactNode } from "react";

import type { ClientRequest, ServerEvent } from "../protocols";

import { useWebTransport } from "../hooks/useWebTransport";
import { useLocalMedia } from "../hooks/useLocalMedia";

import {
  type CallMediaStatus,
  type RemoteParticipantMedia,
  type RemoteSubscription,
  CallMediaContext,
} from "../contexts/CallMediaContext";

import {
  type WebRTCSession,
  type RemoteTrackInfo,
  createWebRTCSession,
} from "../services/webrtc";

export function CallMediaProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<CallMediaStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [remoteMedia, setRemoteMedia] = useState<RemoteParticipantMedia[]>([]);
  const [connectionState, setConnectionState] = useState<RTCPeerConnectionState | null>(null);

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
    return transport.listen(handleWebRTCOfferNeeded)
  }, [transport]);

  const negotiationRef = useRef<Promise<void>>(Promise.resolve());

  function handleWebRTCOfferNeeded(event: ServerEvent): void {
    if (event.type !== "webrtc-offer-needed")
      return

    negotiationRef.current = negotiationRef.current
      .then(() => renegotiate(event))
      .catch((err) => {
        console.error("WebRTC renegotiation failed", err);
      });
  }

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

      session.addLocalStream(localStream)

      const offerSdp = await session.createOffer();

      const message = {
        request_id: crypto.randomUUID(),
        type: "webrtc-offer",
        sdp: offerSdp,
      } satisfies ClientRequest;

      const answer = await transport.request(message);

      remoteByMidRef.current = new Map(
        answer.media_info.map((item) => [
          item.mid,
          {
            participantId: item.participant_id,
            trackId: item.track_id,
            kind: item.kind,
            track: null,
          },
        ]),
      );


      await session.applyAnswer(answer.sdp);

      await transport.sendEvent({
        type: "webrtc-ready",
        event_id: crypto.randomUUID(),
      })

      return session;
    } catch (err) {
      if (sessionRef.current === session) {
        stop();
      } else {
        session.close();
      }
      throw err;
    }
  }

  function stop(): void {
    const session = sessionRef.current;
    if (sessionRef.current === session) {
      sessionRef.current = null;
      remoteByMidRef.current.clear();
      startPromiseRef.current = null;

      setStatus("idle");
      setConnectionState(null);
      setRemoteMedia([]);
    }

    session?.close();
  }

  function handleRemoteTrack(media: RemoteTrackInfo): void {
    if (!media.mid) return;

    const subscription = remoteByMidRef.current.get(media.mid);
    if (!subscription) return;

    subscription.track = media.track;

    setRemoteMedia((current) =>
      addTrackToParticipant(
        current,
        subscription.participantId,
        media.track,
      ),
    );
  }

  function addTrackToParticipant(
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

  function handleConnectionStateChange(state: RTCPeerConnectionState): void {
    if (!sessionRef.current) {
      return;
    }
    
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

  async function renegotiate(event: ServerEvent): Promise<void> {
    const session = sessionRef.current;
    
    if (!session) {
      return;
    }

    try {
      session.addReceivingTransceivers(event.media_hint);

      const offerSdp = await session.createOffer();

      const message = {
        request_id: event.event_id,
        type: "webrtc-offer",
        sdp: offerSdp,
      } satisfies ClientRequest;

      const answer = await transport.request(message);

      const previous = remoteByMidRef.current;

      remoteByMidRef.current = new Map(
        answer.media_info.map((item) => {
          const existing = previous.get(item.mid);

          const sameSubscription =
            existing?.participantId === item.participant_id &&
            existing.trackId === item.track_id;

          return [
            item.mid,
            {
              participantId: item.participant_id,
              trackId: item.track_id,
              kind: item.kind,
              track: sameSubscription ? existing.track : null,
            },
          ];
        }),
      );
        
      await session.applyAnswer(answer.sdp);
    } catch (err) {
      stop()
      throw err
    }
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