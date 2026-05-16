"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { useFetch } from "@/hooks/use-fetch";
import { monitoring } from "@/lib/api";
import { cn, formatNumber } from "@/lib/utils";
import { Inbox } from "lucide-react";

const QUEUE_LABELS: Record<string, { label: string; color: string }> = {
  "registrations.high": { label: "High Priority", color: "text-red-400" },
  registrations: { label: "Normal Priority", color: "text-blue-400" },
  "registrations.low": { label: "Low Priority", color: "text-gray-400" },
  dead_letter: { label: "Dead Letter Queue", color: "text-yellow-400" },
  monitoring: { label: "Monitoring", color: "text-purple-400" },
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
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Queue Monitoring</h1>

      <Card>
        <CardHeader>
          <CardTitle>Queue Depths</CardTitle>
          <span className="text-sm text-gray-400">{formatNumber(total)} total</span>
        </CardHeader>

        <div className="space-y-4">
          {Object.entries(data).map(([name, depth]) => {
            const meta = QUEUE_LABELS[name] || { label: name, color: "text-gray-400" };
            const pct = total > 0 ? (depth / total) * 100 : 0;
            return (
              <div key={name}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <Inbox className={cn("h-4 w-4", meta.color)} />
                    <span className="text-gray-300">{meta.label}</span>
                  </div>
                  <span className="font-mono text-white">{formatNumber(depth)}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-gray-800">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all",
                      depth > 0 ? "bg-blue-500" : "bg-transparent",
                    )}
                    style={{ width: `${Math.min(pct, 100)}%` }}
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
