"use client";

import { StatusBadge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";
import { StatCard } from "@/components/ui/stat-card";
import { useFetch } from "@/hooks/use-fetch";
import { useWebSocket } from "@/hooks/use-websocket";
import { monitoring } from "@/lib/api";
import { formatNumber, timeAgo } from "@/lib/utils";
import { Activity, Clock, Zap } from "lucide-react";
import { useEffect, useState } from "react";

export default function TasksPage() {
  const [offset, setOffset] = useState(0);
  const limit = 30;

  const { data: overview, loading, error } = useFetch(
    () => monitoring.overview(),
    [],
    5000,
  );

  const { data: activeData, refetch } = useFetch(
    () => monitoring.active({ limit, offset }),
    [offset],
    10000,
  );

  const { lastMessage } = useWebSocket<{ type: string }>();

  useEffect(() => {
    if (lastMessage?.type === "registration_update") refetch();
  }, [lastMessage, refetch]);

  if (loading && !overview) return <Spinner />;
  if (error) return <ErrorBanner message={error} />;
  if (!overview) return null;

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          <span className="text-gradient">Running Tasks</span>
        </h1>
        <p className="mt-1 text-sm text-gray-500">Live view of active registration tasks</p>
      </div>

      <div className="stagger-children grid gap-4 sm:grid-cols-3">
        <StatCard label="In Progress" value={formatNumber(overview.in_progress)} icon={Activity} accent="purple" />
        <StatCard label="Pending" value={formatNumber(overview.pending)} icon={Clock} accent="amber" />
        <StatCard label="Completed" value={formatNumber(overview.completed)} icon={Zap} accent="emerald" />
      </div>

      {activeData && activeData.items.length === 0 && overview.in_progress === 0 && (
        <EmptyState icon={Activity} title="No active tasks" description="Start a registration to see live tasks here" />
      )}

      {activeData && activeData.items.length > 0 && (
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-800/60">
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">ID</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Status</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Error</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Started</th>
                </tr>
              </thead>
              <tbody>
                {activeData.items.map((task) => (
                  <tr key={task.id} className="border-b border-gray-800/30 transition-colors hover:bg-gray-800/30">
                    <td className="px-6 py-3.5 font-mono text-xs text-gray-400">#{task.id}</td>
                    <td className="px-6 py-3.5"><StatusBadge status={task.status} /></td>
                    <td className="px-6 py-3.5 text-sm text-gray-400 max-w-xs truncate">{task.error_message ?? "—"}</td>
                    <td className="px-6 py-3.5 text-xs text-gray-500">{task.created_at ? timeAgo(task.created_at) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-6 pb-4">
            <Pagination total={activeData.total} limit={limit} offset={offset} onChange={setOffset} />
          </div>
        </Card>
      )}
    </div>
  );
}
