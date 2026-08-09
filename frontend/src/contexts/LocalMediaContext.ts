import { createContext } from "react";

export type LocalMediaStatus = "idle" | "requesting" | "ready" | "error";

type LocalMediaContextValue = {
  stream: MediaStream | null;
  status: LocalMediaStatus;
  error: string | null;
  cameraEnabled: boolean;
  micEnabled: boolean;

  start: () => Promise<MediaStream>;
  stop: () => void;
  setCameraEnabled: (enabled: boolean) => void;
  setMicEnabled: (enabled: boolean) => void;
  clearError: () => void;
};

export const LocalMediaContext = createContext<
  LocalMediaContextValue | undefined
>(undefined);
