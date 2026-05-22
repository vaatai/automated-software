"use client";

import { useTheme } from "@/contexts/theme-context";

export function AnimatedBackground() {
  const { theme } = useTheme();

  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      {/* Floating gradient orbs */}
      <div
        className={`absolute -left-32 -top-32 h-96 w-96 rounded-full blur-3xl animate-bg-float-1 ${
          theme === "dark"
            ? "bg-blue-500/8"
            : "bg-blue-400/10"
        }`}
      />
      <div
        className={`absolute -right-32 top-1/4 h-80 w-80 rounded-full blur-3xl animate-bg-float-2 ${
          theme === "dark"
            ? "bg-violet-500/6"
            : "bg-violet-400/8"
        }`}
      />
      <div
        className={`absolute -bottom-32 left-1/3 h-72 w-72 rounded-full blur-3xl animate-bg-float-3 ${
          theme === "dark"
            ? "bg-emerald-500/5"
            : "bg-emerald-400/8"
        }`}
      />
      <div
        className={`absolute right-1/4 top-2/3 h-64 w-64 rounded-full blur-3xl animate-bg-float-1 ${
          theme === "dark"
            ? "bg-fuchsia-500/4"
            : "bg-fuchsia-400/6"
        }`}
        style={{ animationDelay: "3s" }}
      />

      {/* Grid overlay */}
      <div
        className={`absolute inset-0 ${
          theme === "dark"
            ? "bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)]"
            : "bg-[linear-gradient(rgba(0,0,0,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,0,0,0.03)_1px,transparent_1px)]"
        } bg-[size:60px_60px]`}
      />
    </div>
  );
}
