import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";
import { Card } from "./card";

export function StatCard({
  label,
  value,
  icon: Icon,
  trend,
  className,
}: {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  trend?: { value: string; positive: boolean };
  className?: string;
}) {
  return (
    <Card className={cn("flex items-start gap-4", className)}>
      {Icon && (
        <div className="rounded-lg bg-gray-800 p-3">
          <Icon className="h-5 w-5 text-gray-400" />
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="text-sm text-gray-400">{label}</p>
        <p className="mt-1 text-2xl font-semibold text-white">{value}</p>
        {trend && (
          <p
            className={cn(
              "mt-1 text-xs",
              trend.positive ? "text-emerald-400" : "text-red-400",
            )}
          >
            {trend.value}
          </p>
        )}
      </div>
    </Card>
  );
}
