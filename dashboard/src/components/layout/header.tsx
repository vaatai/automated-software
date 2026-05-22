"use client";

import { useTheme } from "@/contexts/theme-context";
import { cn } from "@/lib/utils";
import { useWebSocket } from "@/hooks/use-websocket";
import { Menu, Moon, Sun, Wifi, WifiOff } from "lucide-react";

export function Header({
  onToggleSidebar,
}: {
  onToggleSidebar?: () => void;
}) {
  const { connected } = useWebSocket();
  const { theme, toggle } = useTheme();
  const dark = theme === "dark";

  return (
    <header className={cn(
      "sticky top-0 z-20 border-b backdrop-blur-xl transition-colors duration-300",
      dark
        ? "border-gray-800/60 bg-gray-950/80"
        : "border-slate-200 bg-white/80",
    )}>
      {/* Top accent line */}
      <div className="h-[2px] w-full bg-gradient-to-r from-blue-500 via-violet-500 to-fuchsia-500 opacity-60" />

      <div className="flex h-14 items-center justify-between px-6">
        <button
          onClick={onToggleSidebar}
          className={cn(
            "rounded-lg p-2 transition-colors lg:hidden",
            dark
              ? "text-gray-400 hover:bg-gray-800/60 hover:text-white"
              : "text-slate-400 hover:bg-slate-100 hover:text-slate-900",
          )}
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="flex-1" />

        <div className="flex items-center gap-3">
          {/* Theme toggle */}
          <button
            onClick={toggle}
            className={cn(
              "group relative flex h-9 w-9 items-center justify-center rounded-xl border transition-all duration-300 hover:scale-105",
              dark
                ? "border-gray-700/60 bg-gray-800/60 text-yellow-400 hover:border-yellow-500/40 hover:bg-gray-800"
                : "border-slate-200 bg-white text-slate-600 shadow-sm hover:border-blue-300 hover:bg-blue-50 hover:text-blue-600",
            )}
            title={dark ? "Switch to light mode" : "Switch to dark mode"}
          >
            {dark ? (
              <Sun className="h-4 w-4 transition-transform duration-300 group-hover:rotate-45" />
            ) : (
              <Moon className="h-4 w-4 transition-transform duration-300 group-hover:-rotate-12" />
            )}
          </button>

          {/* Live status indicator */}
          <div className={cn(
            "flex items-center gap-2 rounded-full border px-3 py-1.5",
            dark ? "border-gray-800/60" : "border-slate-200",
          )}>
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
                <span className={cn("h-2 w-2 rounded-full", dark ? "bg-gray-600" : "bg-slate-300")} />
                <span className={cn("text-xs font-medium", dark ? "text-gray-500" : "text-slate-400")}>Offline</span>
                <WifiOff className={cn("h-3.5 w-3.5", dark ? "text-gray-500" : "text-slate-400")} />
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
