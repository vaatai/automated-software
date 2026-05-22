"use client";

import { useEffect, useState } from "react";

export function LoadingScreen() {
  const [progress, setProgress] = useState(0);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setInterval(() => {
      setProgress((p) => {
        if (p >= 100) {
          clearInterval(timer);
          setTimeout(() => setVisible(false), 300);
          return 100;
        }
        return p + Math.random() * 25 + 10;
      });
    }, 150);
    return () => clearInterval(timer);
  }, []);

  if (!visible) return null;

  return (
    <div
      className={`fixed inset-0 z-[100] flex flex-col items-center justify-center bg-gray-950 transition-opacity duration-500 ${
        progress >= 100 ? "opacity-0 pointer-events-none" : "opacity-100"
      }`}
    >
      {/* Logo animation */}
      <div className="relative mb-8">
        {/* Outer spinning ring */}
        <div className="absolute -inset-4 animate-spin-slow">
          <svg width="88" height="88" viewBox="0 0 88 88" fill="none">
            <circle
              cx="44"
              cy="44"
              r="42"
              stroke="url(#ring-grad)"
              strokeWidth="1.5"
              strokeDasharray="8 6"
              opacity="0.4"
            />
            <defs>
              <linearGradient id="ring-grad" x1="0" y1="0" x2="88" y2="88">
                <stop stopColor="#3b82f6" />
                <stop offset="0.5" stopColor="#8b5cf6" />
                <stop offset="1" stopColor="#06b6d4" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        {/* Inner logo */}
        <svg width="56" height="56" viewBox="0 0 40 40" fill="none" className="animate-pulse">
          <defs>
            <linearGradient id="load-grad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="50%" stopColor="#8b5cf6" />
              <stop offset="100%" stopColor="#06b6d4" />
            </linearGradient>
            <linearGradient id="load-inner" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#60a5fa" />
              <stop offset="100%" stopColor="#a78bfa" />
            </linearGradient>
          </defs>
          <rect x="2" y="2" width="36" height="36" rx="10" fill="#111827" stroke="url(#load-grad)" strokeWidth="2.5" />
          <path d="M20 8L10 30h4l2-5h8l2 5h4L20 8zm0 7l2.5 7h-5L20 15z" fill="url(#load-inner)" />
          <circle cx="10" cy="12" r="1.5" fill="#3b82f6" opacity="0.7" />
          <circle cx="30" cy="12" r="1.5" fill="#8b5cf6" opacity="0.7" />
          <circle cx="10" cy="32" r="1.5" fill="#06b6d4" opacity="0.7" />
          <circle cx="30" cy="32" r="1.5" fill="#8b5cf6" opacity="0.7" />
        </svg>
      </div>

      {/* Brand name */}
      <h1 className="mb-6 text-2xl font-bold tracking-tight">
        <span className="text-gradient">AutoReg</span>
      </h1>

      {/* Progress bar */}
      <div className="w-48 overflow-hidden rounded-full bg-gray-800/60">
        <div
          className="h-1 rounded-full bg-gradient-to-r from-blue-500 via-violet-500 to-cyan-500 transition-all duration-300 ease-out"
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>

      {/* Loading text */}
      <p className="mt-3 text-xs text-gray-500 animate-pulse">
        Initializing dashboard...
      </p>

      {/* Background decorative orbs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute left-1/4 top-1/4 h-64 w-64 rounded-full bg-blue-600/5 blur-3xl animate-bg-float-1" />
        <div className="absolute right-1/4 bottom-1/4 h-48 w-48 rounded-full bg-violet-600/5 blur-3xl animate-bg-float-2" />
      </div>
    </div>
  );
}
