"use client";

import { StatusBadge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";
import { useFetch } from "@/hooks/use-fetch";
import { useWebSocket } from "@/hooks/use-websocket";
import { monitoring, type PaginatedRegistrations } from "@/lib/api";
import { timeAgo } from "@/lib/utils";
import { Activity } from "lucide-react";
import { useEffect, useState } from "react";

export default function TasksPage() {
  const [offset, setOffset] = useState(0);
  const limit = 30;

  const { data, loading, error, refetch } = useFetch(
    () => monitoring.active({ limit, offset }),
    [offset],
    10000,
  );

  const { lastMessage } = useWebSocket<{ type: string }>();

  useEffect(() => {
    if (lastMessage?.type === "registration_update") refetch();
  }, [lastMessage, refetch]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Running Tasks</h1>

      {error && <ErrorBanner message={error} />}
      {loading && !data && <Spinner />}

      {data && data.items.length === 0 && (
        <EmptyState icon={Activity} title="No active tasks" description="All registration tasks have completed" />
      )}

      {data && data.items.length > 0 && (
        <TaskTable data={data} limit={limit} offset={offset} onPageChange={setOffset} />
      )}
    </div>
  );
}

function TaskTable({
  data,
  limit,
  offset,
  onPageChange,
}: {
  data: PaginatedRegistrations;
  limit: number;
  offset: number;
  onPageChange: (o: number) => void;
}) {
  return (
    <Card className="p-0">
      <CardHeader className="px-6 pt-6">
        <CardTitle>Active Registrations ({data.total})</CardTitle>
      </CardHeader>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-500">
              <th className="px-6 py-3 font-medium">ID</th>
              <th className="px-6 py-3 font-medium">Website</th>
              <th className="px-6 py-3 font-medium">Status</th>
              <th className="px-6 py-3 font-medium">Task ID</th>
              <th className="px-6 py-3 font-medium">Started</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((r) => (
              <tr key={r.id} className="border-b border-gray-800/50">
                <td className="px-6 py-3 font-mono text-xs text-gray-400">#{r.id}</td>
                <td className="px-6 py-3">{r.website_id}</td>
                <td className="px-6 py-3"><StatusBadge status={r.status} /></td>
                <td className="px-6 py-3 font-mono text-xs text-gray-500">
                  {r.celery_task_id ? r.celery_task_id.slice(0, 8) : "—"}
                </td>
                <td className="px-6 py-3 text-gray-500">
                  {r.created_at ? timeAgo(r.created_at) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="px-6 pb-4">
        <Pagination total={data.total} limit={limit} offset={offset} onChange={onPageChange} />
      </div>
    </Card>
  );
}
