"use client";

import { useTheme } from "@/contexts/theme-context";
import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export function Card({
  children,
  className,
  glow,
  onClick,
}: {
  children: ReactNode;
  className?: string;
  glow?: "blue" | "emerald" | "purple" | "red";
  onClick?: () => void;
}) {
  const { theme } = useTheme();
  const dark = theme === "dark";

  return (
    <div
      onClick={onClick}
      className={cn(
        "relative rounded-xl border p-4 sm:p-6 shadow-lg transition-all duration-300 hover:shadow-xl",
        dark
          ? "border-gray-800/80 bg-gradient-to-br from-gray-900 to-gray-900/80 hover:border-gray-700/80"
          : "border-slate-200 bg-white/80 hover:border-slate-300",
        glow === "blue" && "glow-blue",
        glow === "emerald" && "glow-emerald",
        glow === "purple" && "glow-purple",
        glow === "red" && "glow-red",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-4 flex items-center justify-between", className)}>
      {children}
    </div>
  );
}

export function CardTitle({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const { theme } = useTheme();

  return (
    <h3 className={cn(
      "text-sm font-medium",
      theme === "dark" ? "text-gray-400" : "text-slate-500",
      className,
    )}>
      {children}
    </h3>
  );
}
