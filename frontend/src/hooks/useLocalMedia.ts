import { useEffect, useState } from "react";

export function useLocalMedia() {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    let acquiredStream: MediaStream | null = null;

    async function startCamera() {
      try {
        acquiredStream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: true,
        });

        if (disposed) {
          acquiredStream.getTracks().forEach((track) => track.stop());
          return;
        }

        setStream(acquiredStream);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Could not access camera",
        );
      }
    }

    void startCamera();

    return () => {
      disposed = true;
      acquiredStream?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  return { stream, error };
}