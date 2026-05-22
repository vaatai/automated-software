"use client";

import { useTheme } from "@/contexts/theme-context";
import type { ReactNode } from "react";
import { useState } from "react";
import { AnimatedBackground } from "./animated-bg";
import { Header } from "./header";
import { Sidebar } from "./sidebar";

export function Shell({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { theme } = useTheme();

  return (
    <div className={`flex h-screen transition-colors duration-300 ${
      theme === "dark" ? "bg-gray-950 text-white" : "bg-slate-50 text-slate-900"
    }`}>
      <AnimatedBackground />

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/60 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar — always visible on lg+, toggle on mobile */}
      <div
        className={`${sidebarOpen ? "translate-x-0" : "-translate-x-full"} fixed inset-y-0 left-0 z-30 transition-transform lg:translate-x-0`}
      >
        <Sidebar />
      </div>

      {/* Main content */}
      <div className="relative z-10 flex flex-1 flex-col lg:pl-64">
        <Header onToggleSidebar={() => setSidebarOpen((o) => !o)} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
