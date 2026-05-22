"use client";

import { StatusBadge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { StatCard } from "@/components/ui/stat-card";
import { useFetch } from "@/hooks/use-fetch";
import { useWebSocket } from "@/hooks/use-websocket";
import { monitoring } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import { Activity, Clock, Zap } from "lucide-react";

export default function TasksPage() {
  const { data, loading, error } = useFetch(
    () => monitoring.overview(),
    [],
    5000,
  );
  interface WsMessage {
    recent_tasks?: { id?: string; website_name?: string; status?: string; current_step?: string; started_at?: string }[];
  }
  const { lastMessage } = useWebSocket<WsMessage>();

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBanner message={error} />;
  if (!data) return null;

  const recentTasks = lastMessage?.recent_tasks ?? [];

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          <span className="text-gradient">Running Tasks</span>
        </h1>
        <p className="mt-1 text-sm text-gray-500">Live view of active registration tasks</p>
      </div>

      <div className="stagger-children grid gap-4 sm:grid-cols-3">
        <StatCard label="In Progress" value={formatNumber(data.in_progress)} icon={Activity} accent="purple" />
        <StatCard label="Pending" value={formatNumber(data.pending)} icon={Clock} accent="amber" />
        <StatCard label="Completed" value={formatNumber(data.completed)} icon={Zap} accent="emerald" />
      </div>

      {recentTasks.length === 0 && (
        <EmptyState icon={Activity} title="No active tasks" description="Start a registration to see live tasks here" />
      )}

      {recentTasks.length > 0 && (
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-800/60">
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Task ID</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Website</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Status</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Step</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Started</th>
                </tr>
              </thead>
              <tbody>
                {recentTasks.map((task, i) => (
                  <tr key={task.id ?? i} className="border-b border-gray-800/30 transition-colors hover:bg-gray-800/30">
                    <td className="px-6 py-3.5 font-mono text-xs text-gray-400">{task.id?.slice(0, 12) ?? "—"}</td>
                    <td className="px-6 py-3.5 font-medium text-white">{task.website_name ?? "—"}</td>
                    <td className="px-6 py-3.5"><StatusBadge status={task.status ?? "unknown"} /></td>
                    <td className="px-6 py-3.5 text-gray-400">{task.current_step ?? "—"}</td>
                    <td className="px-6 py-3.5 text-xs text-gray-500">{task.started_at ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
