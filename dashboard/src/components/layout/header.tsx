"use client";

import { useWebSocket } from "@/hooks/use-websocket";
import { Menu, Wifi, WifiOff } from "lucide-react";

export function Header({
  onToggleSidebar,
}: {
  onToggleSidebar?: () => void;
}) {
  const { connected } = useWebSocket();

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-gray-800 bg-gray-950/80 px-6 backdrop-blur-sm">
      <button
        onClick={onToggleSidebar}
        className="rounded p-2 text-gray-400 hover:bg-gray-800 lg:hidden"
      >
        <Menu className="h-5 w-5" />
      </button>

      <div className="flex-1" />

      <div className="flex items-center gap-2 text-xs">
        {connected ? (
          <>
            <Wifi className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-emerald-400">Live</span>
          </>
        ) : (
          <>
            <WifiOff className="h-3.5 w-3.5 text-gray-500" />
            <span className="text-gray-500">Offline</span>
          </>
        )}
      </div>
    </header>
  );
}
