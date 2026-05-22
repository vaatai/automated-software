"use client";

import { useTheme } from "@/contexts/theme-context";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
}) {
  const { theme } = useTheme();
  const dark = theme === "dark";

  return (
    <div className="animate-fade-in flex flex-col items-center justify-center py-16 text-center">
      <div className={cn(
        "animate-float mb-4 rounded-2xl bg-gradient-to-br p-5",
        dark ? "from-gray-800/80 to-gray-900/80" : "from-slate-100 to-white",
      )}>
        <Icon className={cn("h-10 w-10", dark ? "text-gray-500" : "text-slate-400")} />
      </div>
      <p className={cn("text-sm font-medium", dark ? "text-gray-400" : "text-slate-500")}>{title}</p>
      {description && (
        <p className={cn("mt-1.5 max-w-xs text-xs", dark ? "text-gray-500" : "text-slate-400")}>{description}</p>
      )}
    </div>
  );
}
