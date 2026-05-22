"use client";

import { useTheme } from "@/contexts/theme-context";

export function AutoRegLogo({ size = 40 }: { size?: number }) {
  const { theme } = useTheme();
  const dark = theme === "dark";

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="shrink-0"
    >
      <defs>
        <linearGradient id="logo-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#3b82f6" />
          <stop offset="50%" stopColor="#8b5cf6" />
          <stop offset="100%" stopColor="#06b6d4" />
        </linearGradient>
        <linearGradient id="logo-inner" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#60a5fa" />
          <stop offset="100%" stopColor="#a78bfa" />
        </linearGradient>
      </defs>
      {/* Outer rounded square */}
      <rect
        x="2"
        y="2"
        width="36"
        height="36"
        rx="10"
        fill={dark ? "#111827" : "#f8fafc"}
        stroke="url(#logo-grad)"
        strokeWidth="2.5"
      />
      {/* "A" letter stylized as circuit/automation symbol */}
      <path
        d="M20 8L10 30h4l2-5h8l2 5h4L20 8zm0 7l2.5 7h-5L20 15z"
        fill="url(#logo-inner)"
      />
      {/* Circuit dots */}
      <circle cx="10" cy="12" r="1.5" fill="#3b82f6" opacity="0.7" />
      <circle cx="30" cy="12" r="1.5" fill="#8b5cf6" opacity="0.7" />
      <circle cx="10" cy="32" r="1.5" fill="#06b6d4" opacity="0.7" />
      <circle cx="30" cy="32" r="1.5" fill="#8b5cf6" opacity="0.7" />
      {/* Circuit lines */}
      <line x1="10" y1="12" x2="10" y2="18" stroke="#3b82f6" strokeWidth="0.8" opacity="0.4" />
      <line x1="30" y1="12" x2="30" y2="18" stroke="#8b5cf6" strokeWidth="0.8" opacity="0.4" />
      {/* Pulse ring */}
      <rect
        x="2"
        y="2"
        width="36"
        height="36"
        rx="10"
        fill="none"
        stroke="url(#logo-grad)"
        strokeWidth="1"
        opacity="0.3"
        className="animate-pulse"
      />
    </svg>
  );
}
