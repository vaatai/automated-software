"use client";

import { useTheme } from "@/contexts/theme-context";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

const ICON_GRADIENTS: Record<string, string> = {
  blue: "from-blue-500/20 to-blue-600/10 text-blue-400",
  emerald: "from-emerald-500/20 to-emerald-600/10 text-emerald-400",
  red: "from-red-500/20 to-red-600/10 text-red-400",
  purple: "from-purple-500/20 to-purple-600/10 text-purple-400",
  amber: "from-amber-500/20 to-amber-600/10 text-amber-400",
  default: "from-gray-700/50 to-gray-800/50 text-gray-400",
};

const ICON_GRADIENTS_LIGHT: Record<string, string> = {
  blue: "from-blue-100 to-blue-50 text-blue-600",
  emerald: "from-emerald-100 to-emerald-50 text-emerald-600",
  red: "from-red-100 to-red-50 text-red-600",
  purple: "from-purple-100 to-purple-50 text-purple-600",
  amber: "from-amber-100 to-amber-50 text-amber-600",
  default: "from-slate-100 to-slate-50 text-slate-500",
};

export function StatCard({
  label,
  value,
  icon: Icon,
  trend,
  className,
  accent = "default",
}: {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  trend?: { value: string; positive: boolean };
  className?: string;
  accent?: "blue" | "emerald" | "red" | "purple" | "amber" | "default";
}) {
  const { theme } = useTheme();
  const dark = theme === "dark";
  const iconClasses = dark
    ? ICON_GRADIENTS[accent] || ICON_GRADIENTS.default
    : ICON_GRADIENTS_LIGHT[accent] || ICON_GRADIENTS_LIGHT.default;

  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-xl border p-5 shadow-lg transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl",
        dark
          ? "border-gray-800/80 bg-gradient-to-br from-gray-900 to-gray-900/80 hover:border-gray-700/80"
          : "border-slate-200 bg-white/80 hover:border-slate-300",
        className,
      )}
    >
      <div className={cn(
        "absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100",
        !dark && "from-blue-50/30 to-transparent",
      )} />

      <div className="relative flex items-start gap-4">
        {Icon && (
          <div className={cn("rounded-xl bg-gradient-to-br p-3 transition-transform duration-300 group-hover:scale-110", iconClasses)}>
            <Icon className="h-5 w-5" />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className={cn("text-sm", dark ? "text-gray-400" : "text-slate-500")}>{label}</p>
          <p className={cn("animate-count-up mt-1 text-2xl font-bold tracking-tight", dark ? "text-white" : "text-slate-900")}>
            {value}
          </p>
          {trend && (
            <div className="mt-1.5 flex items-center gap-1">
              <span
                className={cn(
                  "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                  trend.positive
                    ? "bg-emerald-400/10 text-emerald-400"
                    : "bg-red-400/10 text-red-400",
                )}
              >
                {trend.positive ? "\u2191" : "\u2193"} {trend.value}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
