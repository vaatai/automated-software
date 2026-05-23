"use client";

import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";
import { useFetch } from "@/hooks/use-fetch";
import { useThemeClasses } from "@/hooks/use-theme-classes";
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
  const tc = useThemeClasses();

  const { data, loading, error } = useFetch(
    () => monitoring.logs({ limit, offset, level: level !== "all" ? level : undefined, search: search || undefined }),
    [offset, level, search],
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
          <span className="text-gradient">Error Logs</span>
        </h1>
        <p className={`mt-1 text-sm ${tc.subtext}`}>Task logs with level filtering and search</p>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className={`absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 ${tc.muted}`} />
          <input
            type="text"
            placeholder="Search logs..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
            className={`pl-10 pr-4 ${tc.inputCls}`}
          />
        </div>
        <select
          value={level}
          onChange={(e) => { setLevel(e.target.value); setOffset(0); }}
          className={tc.inputCls}
          style={{ width: "auto" }}
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
          <div className={`divide-y ${tc.dark ? "divide-gray-800/30" : "divide-slate-100"}`}>
            {data.items.map((log, i) => (
              <div key={i} className={`group px-3 sm:px-6 py-3 sm:py-4 transition-colors ${
                tc.dark ? "hover:bg-gray-800/20" : "hover:bg-slate-50"
              }`}>
                <div className="flex items-center gap-3 mb-1.5">
                  <span className={cn("inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold", LEVEL_STYLES[log.level] || LEVEL_STYLES.DEBUG)}>
                    {log.level}
                  </span>
                  {log.step && (
                    <span className={`rounded-md px-2 py-0.5 text-xs ${tc.dark ? "bg-gray-800/60 text-gray-400" : "bg-slate-100 text-slate-500"}`}>{log.step}</span>
                  )}
                  <span className={`ml-auto text-xs ${tc.dark ? "text-gray-600" : "text-slate-400"}`}>{log.created_at}</span>
                </div>
                <p className={`text-sm ${tc.dark ? "text-gray-300" : "text-slate-600"}`}>{log.message}</p>
                {log.registration_id && (
                  <p className={`mt-1 text-xs font-mono ${tc.dark ? "text-gray-600" : "text-slate-400"}`}>Registration: #{log.registration_id}</p>
                )}
              </div>
            ))}
          </div>
          <div className="px-3 sm:px-6 pb-4">
            <Pagination total={data.total} limit={limit} offset={offset} onChange={setOffset} />
          </div>
        </Card>
      )}
    </div>
  );
}
