"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { useFetch } from "@/hooks/use-fetch";
import { monitoring } from "@/lib/api";
import { cn, formatNumber } from "@/lib/utils";
import { Inbox } from "lucide-react";

const QUEUE_LABELS: Record<string, { label: string; color: string; barColor: string }> = {
  "registrations.high": { label: "High Priority", color: "text-red-400", barColor: "from-red-500 to-red-400" },
  registrations: { label: "Normal Priority", color: "text-blue-400", barColor: "from-blue-500 to-blue-400" },
  "registrations.low": { label: "Low Priority", color: "text-gray-400", barColor: "from-gray-500 to-gray-400" },
  dead_letter: { label: "Dead Letter Queue", color: "text-yellow-400", barColor: "from-yellow-500 to-yellow-400" },
  monitoring: { label: "Monitoring", color: "text-purple-400", barColor: "from-purple-500 to-purple-400" },
};

export default function QueuesPage() {
  const { data, loading, error } = useFetch(
    () => monitoring.queues(),
    [],
    5000,
  );

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBanner message={error} />;
  if (!data) return null;

  const total = Object.values(data).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          <span className="text-gradient">Queues</span>
        </h1>
        <p className="mt-1 text-sm text-gray-500">Task queue depths and priorities</p>
      </div>

      <Card glow="blue">
        <CardHeader>
          <CardTitle className="text-base font-semibold text-gray-300">Queue Depths</CardTitle>
          <span className="rounded-full bg-gray-800/80 px-3 py-1 text-sm font-mono text-gray-400">{formatNumber(total)} total</span>
        </CardHeader>

        <div className="space-y-5">
          {Object.entries(data).map(([name, depth]) => {
            const meta = QUEUE_LABELS[name] || { label: name, color: "text-gray-400", barColor: "from-gray-500 to-gray-400" };
            const pct = total > 0 ? (depth / total) * 100 : 0;
            return (
              <div key={name} className="group">
                <div className="mb-2 flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2.5">
                    <Inbox className={cn("h-4 w-4 transition-transform group-hover:scale-110", meta.color)} />
                    <span className="font-medium text-gray-300">{meta.label}</span>
                  </div>
                  <span className="font-mono font-bold text-white">{formatNumber(depth)}</span>
                </div>
                <div className="h-2.5 overflow-hidden rounded-full bg-gray-800/60">
                  <div
                    className={cn(
                      "h-full rounded-full bg-gradient-to-r transition-all duration-700",
                      meta.barColor,
                      depth === 0 && "opacity-0",
                    )}
                    style={{ width: `${Math.max(pct, depth > 0 ? 3 : 0)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
