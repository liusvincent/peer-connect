import { useWebTransport } from "../hooks/useWebTransport";

export default function Footer() {
  const transport = useWebTransport();

  return (
    <footer className="fixed inset-x-0 bottom-0 bg-gray-200 px-4 py-2 font-mono text-xs text-gray-700">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-1">
        <span>
          WebTransport:{" "}
          <span>{transport.status}</span>
        </span>

        <span>
          Participant ID:{" "}
          <span>
            {transport.user?.id ?? "—"}
          </span>
        </span>

        <span>
          Display Name:{" "}
          <span>
            {transport.user?.name ?? "—"}
          </span>
        </span>
      </div>
    </footer>
  );
}
