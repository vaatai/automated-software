"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { StatCard } from "@/components/ui/stat-card";
import { useFetch } from "@/hooks/use-fetch";
import { useThemeClasses } from "@/hooks/use-theme-classes";
import { monitoring } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import { Cpu, Server } from "lucide-react";

export default function WorkersPage() {
  const { data, loading, error } = useFetch(
    () => monitoring.workers(),
    [],
    10000,
  );
  const tc = useThemeClasses();

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBanner message={error} />;
  if (!data) return null;

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
          <span className="text-gradient">Workers</span>
        </h1>
        <p className={`mt-1 text-sm ${tc.subtext}`}>Celery worker health and active tasks</p>
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
              <CardTitle className={`text-base font-semibold ${tc.dark ? "text-gray-300" : "text-slate-700"}`}>{worker.name}</CardTitle>
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
                <div key={item.label} className={`rounded-lg p-3 ${tc.dark ? "bg-gray-800/30" : "bg-slate-50"}`}>
                  <p className={`text-xs ${tc.muted}`}>{item.label}</p>
                  <p className={`mt-0.5 text-lg font-bold ${tc.heading}`}>{item.value}</p>
                </div>
              ))}
            </div>

            {worker.active_task_details.length > 0 && (
              <div className={`mt-4 border-t pt-4 ${tc.dark ? "border-gray-800/40" : "border-slate-200"}`}>
                <p className={`mb-2 text-xs font-semibold uppercase tracking-wider ${tc.muted}`}>Active Task Details</p>
                <div className="space-y-2">
                  {worker.active_task_details.map((t) => (
                    <div key={t.id} className={`flex items-center justify-between rounded-lg px-4 py-2.5 text-xs transition-colors ${
                      tc.dark ? "bg-gray-800/30 hover:bg-gray-800/50" : "bg-slate-50 hover:bg-slate-100"
                    }`}>
                      <span className={`font-mono ${tc.label}`}>{t.id?.slice(0, 12)}</span>
                      <span className={tc.muted}>{t.name}</span>
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
