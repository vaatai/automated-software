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
  const iconClasses = ICON_GRADIENTS[accent] || ICON_GRADIENTS.default;

  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-xl border border-gray-800/80 bg-gradient-to-br from-gray-900 to-gray-900/80 p-5 shadow-lg transition-all duration-300 hover:-translate-y-0.5 hover:border-gray-700/80 hover:shadow-xl",
        className,
      )}
    >
      {/* Subtle gradient overlay on hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />

      <div className="relative flex items-start gap-4">
        {Icon && (
          <div className={cn("rounded-xl bg-gradient-to-br p-3 transition-transform duration-300 group-hover:scale-110", iconClasses)}>
            <Icon className="h-5 w-5" />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-sm text-gray-400">{label}</p>
          <p className="animate-count-up mt-1 text-2xl font-bold tracking-tight text-white">
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
