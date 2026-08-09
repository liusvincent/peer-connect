import { useContext } from "react";
import { CallMediaContext } from "../contexts/CallMediaContext";

export function useCallMedia() {
  const context = useContext(CallMediaContext);

  if (!context) {
    throw new Error(
      "useCallMedia must be used inside CallMediaProvider",
    );
  }

  return context;
}