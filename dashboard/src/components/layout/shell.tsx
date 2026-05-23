"use client";

import { useTheme } from "@/contexts/theme-context";
import type { ReactNode } from "react";
import { useState, useEffect } from "react";
import { AnimatedBackground } from "./animated-bg";
import { Header } from "./header";
import { Sidebar } from "./sidebar";

const SIDEBAR_KEY = "autoreg-sidebar-collapsed";

export function Shell({ children }: { children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const { theme } = useTheme();

  useEffect(() => {
    const saved = localStorage.getItem(SIDEBAR_KEY);
    if (saved === "true") setCollapsed(true);
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(SIDEBAR_KEY, String(next));
      return next;
    });
  };

  return (
    <div className={`flex h-screen transition-colors duration-300 ${
      theme === "dark" ? "bg-gray-950 text-white" : "bg-slate-50 text-slate-900"
    }`}>
      <AnimatedBackground />

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/60 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar — always visible on lg+, toggle on mobile */}
      <div
        className={`${mobileOpen ? "translate-x-0" : "-translate-x-full"} fixed inset-y-0 left-0 z-30 transition-all duration-300 lg:translate-x-0`}
      >
        <Sidebar collapsed={collapsed} onToggleCollapse={toggleCollapsed} />
      </div>

      {/* Main content */}
      <div className={`relative z-10 flex flex-1 flex-col transition-all duration-300 ${
        collapsed ? "lg:pl-16" : "lg:pl-64"
      }`}>
        <Header onToggleSidebar={() => setMobileOpen((o) => !o)} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
