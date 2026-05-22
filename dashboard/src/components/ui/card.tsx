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
  return (
    <div
      onClick={onClick}
      className={cn(
        "relative rounded-xl border border-gray-800/80 bg-gradient-to-br from-gray-900 to-gray-900/80 p-6 shadow-lg transition-all duration-300 hover:border-gray-700/80 hover:shadow-xl",
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
  return (
    <h3 className={cn("text-sm font-medium text-gray-400", className)}>
      {children}
    </h3>
  );
}
