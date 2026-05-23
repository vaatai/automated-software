"use client";

import { useTheme } from "@/contexts/theme-context";
import type { ReactNode } from "react";
import { useState, useEffect, useCallback } from "react";
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

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(SIDEBAR_KEY, String(next));
      return next;
    });
  }, []);

  const closeMobile = useCallback(() => setMobileOpen(false), []);

  return (
    <div className={`flex h-screen overflow-hidden transition-colors duration-300 ${
      theme === "dark" ? "bg-gray-950 text-white" : "bg-slate-50 text-slate-900"
    }`}>
      <AnimatedBackground />

      {/* Mobile overlay backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={closeMobile}
        />
      )}

      {/* Mobile sidebar — slides in from left as overlay */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-64 transition-transform duration-300 ease-in-out lg:hidden ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <Sidebar
          collapsed={false}
          onToggleCollapse={toggleCollapsed}
          onCloseMobile={closeMobile}
          isMobileOpen={true}
        />
      </div>

      {/* Desktop sidebar — always visible, collapsible */}
      <div
        className={`hidden lg:block fixed inset-y-0 left-0 z-30 transition-all duration-300 ${
          collapsed ? "w-16" : "w-64"
        }`}
      >
        <Sidebar
          collapsed={collapsed}
          onToggleCollapse={toggleCollapsed}
          onCloseMobile={closeMobile}
          isMobileOpen={false}
        />
      </div>

      {/* Main content — full width on mobile, offset on desktop */}
      <div className={`relative z-10 flex w-full flex-1 flex-col transition-all duration-300 ${
        collapsed ? "lg:pl-16" : "lg:pl-64"
      }`}>
        <Header onToggleSidebar={() => setMobileOpen((o) => !o)} />
        <main className="flex-1 overflow-y-auto p-3 sm:p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
