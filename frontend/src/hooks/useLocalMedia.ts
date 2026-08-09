import { useContext } from "react";
import { LocalMediaContext } from "../contexts/LocalMediaContext";

export function useLocalMedia() {
  const context = useContext(LocalMediaContext);

  if (!context) {
    throw new Error(
      "useLocalMedia must be used inside LocalMediaProvider",
    );
  }

  return context;
}