"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";
import { useFetch } from "@/hooks/use-fetch";
import { monitoring } from "@/lib/api";
import { cn } from "@/lib/utils";
import { AlertCircle, Search } from "lucide-react";
import { useState } from "react";

const LEVEL_STYLES: Record<string, string> = {
  ERROR: "bg-red-500/10 text-red-400 border-red-500/20",
  WARNING: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  INFO: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  DEBUG: "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

export default function LogsPage() {
  const [offset, setOffset] = useState(0);
  const [level, setLevel] = useState("all");
  const [search, setSearch] = useState("");
  const limit = 30;

  const { data, loading, error } = useFetch(
    () => monitoring.logs({ limit, offset, level: level !== "all" ? level : undefined, search: search || undefined }),
    [offset, level, search],
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          <span className="text-gradient">Error Logs</span>
        </h1>
        <p className="mt-1 text-sm text-gray-500">Task logs with level filtering and search</p>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="Search logs..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
            className="w-full rounded-xl border border-gray-800/60 bg-gray-900/80 py-2.5 pl-10 pr-4 text-sm text-white placeholder-gray-500 shadow-sm transition-all focus:border-blue-600/60 focus:outline-none focus:ring-1 focus:ring-blue-600/30"
          />
        </div>
        <select
          value={level}
          onChange={(e) => { setLevel(e.target.value); setOffset(0); }}
          className="rounded-xl border border-gray-700/60 bg-gray-800/80 px-4 py-2.5 text-sm text-white transition-all focus:border-blue-600/60 focus:outline-none focus:ring-1 focus:ring-blue-600/30"
        >
          <option value="all">All Levels</option>
          <option value="ERROR">Error</option>
          <option value="WARNING">Warning</option>
          <option value="INFO">Info</option>
          <option value="DEBUG">Debug</option>
        </select>
      </div>

      {error && <ErrorBanner message={error} />}
      {loading && !data && <Spinner />}

      {data && data.items.length === 0 && (
        <EmptyState icon={AlertCircle} title="No logs found" description="Task logs will appear as registrations are processed" />
      )}

      {data && data.items.length > 0 && (
        <Card className="p-0 overflow-hidden">
          <div className="divide-y divide-gray-800/30">
            {data.items.map((log, i) => (
              <div key={i} className="group px-6 py-4 transition-colors hover:bg-gray-800/20">
                <div className="flex items-center gap-3 mb-1.5">
                  <span className={cn("inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold", LEVEL_STYLES[log.level] || LEVEL_STYLES.DEBUG)}>
                    {log.level}
                  </span>
                  {log.step && (
                    <span className="rounded-md bg-gray-800/60 px-2 py-0.5 text-xs text-gray-400">{log.step}</span>
                  )}
                  <span className="ml-auto text-xs text-gray-600">{log.created_at}</span>
                </div>
                <p className="text-sm text-gray-300">{log.message}</p>
                {log.registration_id && (
                  <p className="mt-1 text-xs font-mono text-gray-600">Registration: #{log.registration_id}</p>
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
