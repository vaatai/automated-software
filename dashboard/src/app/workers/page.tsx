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
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          <span className="text-gradient">Workers</span>
        </h1>
        <p className="mt-1 text-sm text-gray-500">Celery worker health and active tasks</p>
      </div>

      <div className="stagger-children grid gap-4 sm:grid-cols-2">
        <StatCard label="Total Workers" value={formatNumber(data.worker_count)} icon={Server} accent="blue" />
        <StatCard label="Active Tasks" value={formatNumber(data.workers.reduce((a, w) => a + w.active_tasks, 0))} icon={Cpu} accent="purple" />
      </div>

      {data.workers.length === 0 && (
        <EmptyState icon={Server} title="No workers online" description="Start Celery workers to process registrations" />
      )}

      <div className="stagger-children space-y-4">
        {data.workers.map((worker) => (
          <Card key={worker.name} className="animate-fade-in-up">
            <CardHeader>
              <CardTitle className="text-base font-semibold text-gray-300">{worker.name}</CardTitle>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-400/10 px-3 py-1 text-xs font-medium text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                Online
              </span>
            </CardHeader>

            <div className="grid gap-4 text-sm sm:grid-cols-3 lg:grid-cols-5">
              {[
                { label: "Active Tasks", value: worker.active_tasks },
                { label: "Reserved Tasks", value: worker.reserved_tasks },
                { label: "Total Completed", value: formatNumber(worker.total_completed) },
                { label: "Pool Processes", value: worker.pool_processes ?? "\u2014" },
                { label: "Uptime", value: worker.uptime ? `${Math.round(worker.uptime / 3600)}h` : "\u2014" },
              ].map((item) => (
                <div key={item.label} className="rounded-lg bg-gray-800/30 p-3">
                  <p className="text-xs text-gray-500">{item.label}</p>
                  <p className="mt-0.5 text-lg font-bold text-white">{item.value}</p>
                </div>
              ))}
            </div>

            {worker.active_task_details.length > 0 && (
              <div className="mt-4 border-t border-gray-800/40 pt-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">Active Task Details</p>
                <div className="space-y-2">
                  {worker.active_task_details.map((t) => (
                    <div key={t.id} className="flex items-center justify-between rounded-lg bg-gray-800/30 px-4 py-2.5 text-xs transition-colors hover:bg-gray-800/50">
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
    </div>
  );
}
