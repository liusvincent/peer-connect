import { useContext } from "react";
import { WebTransportContext } from "../contexts/WebTransportContext";

export function useWebTransport() {
  const context = useContext(WebTransportContext);

  if (!context) {
    throw new Error(
      "useWebTransport must be used inside WebTransportProvider",
    );
  }

  return context;
}