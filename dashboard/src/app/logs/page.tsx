"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";
import { useFetch } from "@/hooks/use-fetch";
import { monitoring, type LogParams } from "@/lib/api";
import { levelColor, timeAgo } from "@/lib/utils";
import { AlertCircle, Search } from "lucide-react";
import { useState } from "react";

export default function LogsPage() {
  const [offset, setOffset] = useState(0);
  const [level, setLevel] = useState("");
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const limit = 30;

  const params: LogParams = {
    limit,
    offset,
    level: level || undefined,
    search: search || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  };

  const { data, loading, error } = useFetch(
    () => monitoring.logs(params),
    [offset, level, search, dateFrom, dateTo],
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Error Logs</h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
          <input
            placeholder="Search logs..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
            className="rounded-lg border border-gray-800 bg-gray-900 py-2 pl-10 pr-4 text-sm text-white placeholder-gray-500 focus:border-blue-600 focus:outline-none"
          />
        </div>
        <select
          value={level}
          onChange={(e) => { setLevel(e.target.value); setOffset(0); }}
          className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white focus:border-blue-600 focus:outline-none"
        >
          <option value="">All Levels</option>
          <option value="DEBUG">DEBUG</option>
          <option value="INFO">INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="ERROR">ERROR</option>
          <option value="CRITICAL">CRITICAL</option>
        </select>
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => { setDateFrom(e.target.value); setOffset(0); }}
          className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white focus:border-blue-600 focus:outline-none"
        />
        <input
          type="date"
          value={dateTo}
          onChange={(e) => { setDateTo(e.target.value); setOffset(0); }}
          className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white focus:border-blue-600 focus:outline-none"
        />
      </div>

      {error && <ErrorBanner message={error} />}
      {loading && !data && <Spinner />}

      {data && data.items.length === 0 && (
        <EmptyState icon={AlertCircle} title="No logs found" description="Adjust your filters or check back later" />
      )}

      {data && data.items.length > 0 && (
        <Card className="p-0">
          <CardHeader className="px-6 pt-6">
            <CardTitle>Task Logs ({data.total})</CardTitle>
          </CardHeader>
          <div className="divide-y divide-gray-800">
            {data.items.map((log) => (
              <div key={log.id} className="px-6 py-4">
                <div className="flex items-center gap-3">
                  <span className={`text-xs font-semibold ${levelColor(log.level)}`}>
                    {log.level}
                  </span>
                  {log.step && (
                    <span className="rounded bg-gray-800 px-2 py-0.5 text-xs text-gray-400">{log.step}</span>
                  )}
                  <span className="ml-auto text-xs text-gray-600">
                    {timeAgo(log.created_at)}
                  </span>
                </div>
                <p className="mt-1 text-sm text-gray-300">{log.message}</p>
                {log.details && (
                  <pre className="mt-2 max-h-32 overflow-auto rounded bg-gray-800/50 p-2 text-xs text-gray-500">
                    {log.details}
                  </pre>
                )}
                {log.registration_id && (
                  <p className="mt-1 text-xs text-gray-600">Registration #{log.registration_id}</p>
                )}
              </div>
            ))}
          </div>
          <div className="px-6 pb-4">
            <Pagination total={data.total} limit={limit} offset={offset} onChange={setOffset} />
          </div>
        </Card>
      )}
    </div>
  );
}
