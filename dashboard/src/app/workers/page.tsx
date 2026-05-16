"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { StatCard } from "@/components/ui/stat-card";
import { useFetch } from "@/hooks/use-fetch";
import { monitoring } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import { Cpu, Server } from "lucide-react";

export default function WorkersPage() {
  const { data, loading, error } = useFetch(
    () => monitoring.workers(),
    [],
    10000,
  );

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBanner message={error} />;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Worker Monitoring</h1>

      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard
          label="Total Workers"
          value={formatNumber(data.worker_count)}
          icon={Server}
        />
        <StatCard
          label="Active Tasks"
          value={formatNumber(data.workers.reduce((a, w) => a + w.active_tasks, 0))}
          icon={Cpu}
        />
      </div>

      {data.workers.length === 0 && (
        <EmptyState icon={Server} title="No workers online" description="Start Celery workers to process registrations" />
      )}

      {data.workers.map((worker) => (
        <Card key={worker.name}>
          <CardHeader>
            <CardTitle>{worker.name}</CardTitle>
            <span className="rounded-full bg-emerald-400/10 px-2.5 py-0.5 text-xs font-medium text-emerald-400">
              Online
            </span>
          </CardHeader>

          <div className="grid gap-4 text-sm sm:grid-cols-3">
            <div>
              <p className="text-gray-500">Active Tasks</p>
              <p className="text-lg font-semibold text-white">{worker.active_tasks}</p>
            </div>
            <div>
              <p className="text-gray-500">Reserved Tasks</p>
              <p className="text-lg font-semibold text-white">{worker.reserved_tasks}</p>
            </div>
            <div>
              <p className="text-gray-500">Total Completed</p>
              <p className="text-lg font-semibold text-white">{formatNumber(worker.total_completed)}</p>
            </div>
            <div>
              <p className="text-gray-500">Pool Processes</p>
              <p className="text-lg font-semibold text-white">{worker.pool_processes ?? "—"}</p>
            </div>
            <div>
              <p className="text-gray-500">Uptime</p>
              <p className="text-lg font-semibold text-white">
                {worker.uptime ? `${Math.round(worker.uptime / 3600)}h` : "—"}
              </p>
            </div>
          </div>

          {worker.active_task_details.length > 0 && (
            <div className="mt-4 border-t border-gray-800 pt-4">
              <p className="mb-2 text-xs font-medium text-gray-500">Active Task Details</p>
              <div className="space-y-2">
                {worker.active_task_details.map((t) => (
                  <div key={t.id} className="flex items-center justify-between rounded-lg bg-gray-800/50 px-3 py-2 text-xs">
                    <span className="font-mono text-gray-400">{t.id?.slice(0, 12)}</span>
                    <span className="text-gray-500">{t.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}
