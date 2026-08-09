import { useState, useRef, useEffect, type ReactNode } from "react";

import {
  LocalMediaContext,
  type LocalMediaStatus,
} from "../contexts/LocalMediaContext";

export function LocalMediaProvider({ children }: { children: ReactNode }) {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [status, setStatus] = useState<LocalMediaStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [cameraEnabled, setCameraEnabledState] = useState<boolean>(false);
  const [micEnabled, setMicEnabledState] = useState<boolean>(false);

  const streamRef = useRef<MediaStream | null>(null);
  const startPromiseRef = useRef<Promise<MediaStream> | null>(null);

  useEffect(() => {
    return () => {
      stopTracks(streamRef.current);
      streamRef.current = null;
    };
  }, []);

  async function start(): Promise<MediaStream> {
    if (streamRef.current) {
      return streamRef.current;
    }

    if (startPromiseRef.current) {
      return startPromiseRef.current;
    }

    setStatus("requesting");
    setError(null);

    const startPromise = acquireMedia();
    startPromiseRef.current = startPromise;

    try {
      return await startPromise;
    } finally {
      if (startPromiseRef.current === startPromise) {
        startPromiseRef.current = null;
      }
    }
  }

  async function acquireMedia(): Promise<MediaStream> {
    try {
      const acquiredStream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true,
      });

      streamRef.current = acquiredStream;
      setStream(acquiredStream);

      setCameraEnabledState(
        acquiredStream.getVideoTracks().some((track) => track.enabled),
      );

      setMicEnabledState(
        acquiredStream.getAudioTracks().some((track) => track.enabled),
      );

      setStatus("ready");

      return acquiredStream;
    } catch (err) {
      setStatus("error");
      setError(getErrorMessage(err));
      throw err;
    }
  }

  function stop(): void {
    stopTracks(streamRef.current);
    streamRef.current = null;

    setStream(null);
    setStatus("idle");
    setError(null);
    setCameraEnabledState(false);
    setMicEnabledState(false);
  }

  function setCameraEnabled(enabled: boolean): void {
    const tracks = streamRef.current?.getVideoTracks() ?? [];

    for (const track of tracks) {
      track.enabled = enabled;
    }

    setCameraEnabledState(enabled && tracks.length > 0);
  }

  function setMicEnabled(enabled: boolean): void {
    const tracks = streamRef.current?.getAudioTracks() ?? [];

    for (const track of tracks) {
      track.enabled = enabled;
    }

    setMicEnabledState(enabled && tracks.length > 0);
  }

  function clearError(): void {
    setError(null);
  }

  return (
    <LocalMediaContext.Provider
      value={{
        stream,
        status,
        error,
        cameraEnabled,
        micEnabled,
        start,
        stop,
        setCameraEnabled,
        setMicEnabled,
        clearError,
      }}
    >
      {children}
    </LocalMediaContext.Provider>
  );
}

function stopTracks(stream: MediaStream | null): void {
  for (const track of stream?.getTracks() ?? []) {
    track.stop();
  }
}

function getErrorMessage(err: unknown): string {
  if (err instanceof DOMException) {
    switch (err.name) {
      case "NotAllowedError":
        return "Camera or microphone permission was denied.";

      case "NotFoundError":
        return "No camera or microphone was found.";

      case "NotReadableError":
        return "The camera or microphone could not be accessed.";
    }
  }

  return err instanceof Error
    ? err.message
    : "Could not access the camera and microphone.";
}
