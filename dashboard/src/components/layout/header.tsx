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
    <header className="sticky top-0 z-20 border-b border-gray-800/60 bg-gray-950/80 backdrop-blur-xl">
      {/* Top accent line */}
      <div className="h-[2px] w-full bg-gradient-to-r from-blue-500 via-violet-500 to-fuchsia-500 opacity-60" />

      <div className="flex h-14 items-center justify-between px-6">
        <button
          onClick={onToggleSidebar}
          className="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-800/60 hover:text-white lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="flex-1" />

        <div className="flex items-center gap-3">
          {/* Live status indicator */}
          <div className="flex items-center gap-2 rounded-full border border-gray-800/60 px-3 py-1.5">
            {connected ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                </span>
                <span className="text-xs font-medium text-emerald-400">Live</span>
                <Wifi className="h-3.5 w-3.5 text-emerald-400" />
              </>
            ) : (
              <>
                <span className="h-2 w-2 rounded-full bg-gray-600" />
                <span className="text-xs font-medium text-gray-500">Offline</span>
                <WifiOff className="h-3.5 w-3.5 text-gray-500" />
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
