"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { useFetch } from "@/hooks/use-fetch";
import { monitoring } from "@/lib/api";
import { cn, formatPct } from "@/lib/utils";
import { Clock } from "lucide-react";
import { useState } from "react";

export default function LimitsPage() {
  const [days, setDays] = useState(7);
  const { data, loading, error } = useFetch(
    () => monitoring.dailyUsage({ days }),
    [days],
    30000,
  );

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            <span className="text-gradient">Daily Limits</span>
          </h1>
          <p className="mt-1 text-sm text-gray-500">Per-website daily usage and utilization</p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-xl border border-gray-700/60 bg-gray-800/80 px-4 py-2 text-sm text-white transition-all focus:border-blue-600/60 focus:outline-none focus:ring-1 focus:ring-blue-600/30"
        >
          <option value={7}>7 Days</option>
          <option value={14}>14 Days</option>
          <option value={30}>30 Days</option>
        </select>
      </div>

      {error && <ErrorBanner message={error} />}
      {loading && !data && <Spinner />}

      {data && data.items.length === 0 && (
        <EmptyState icon={Clock} title="No usage data" description="Daily usage data will appear once registrations are processed" />
      )}

      {data && data.items.length > 0 && (
        <Card className="p-0 overflow-hidden">
          <CardHeader className="px-6 pt-6">
            <CardTitle className="text-base font-semibold text-gray-300">
              Daily Usage
              <span className="ml-2 text-xs font-normal text-gray-500">{data.period_days} Days</span>
            </CardTitle>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-800/60">
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Date</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Website</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Limit</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Used</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Success</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Failed</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Utilization</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item, i) => (
                  <tr key={i} className="border-b border-gray-800/30 transition-colors hover:bg-gray-800/30">
                    <td className="px-6 py-3.5 font-mono text-xs text-gray-400">{item.date}</td>
                    <td className="px-6 py-3.5 font-medium text-white">{item.website_name}</td>
                    <td className="px-6 py-3.5 font-mono text-gray-400">{item.daily_limit}</td>
                    <td className="px-6 py-3.5 font-mono text-gray-300">{item.registration_count}</td>
                    <td className="px-6 py-3.5 font-mono text-emerald-400">{item.success_count}</td>
                    <td className="px-6 py-3.5 font-mono text-red-400">{item.failure_count}</td>
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <div className="h-2 w-20 overflow-hidden rounded-full bg-gray-800/60">
                          <div
                            className={cn(
                              "h-full rounded-full bg-gradient-to-r transition-all duration-500",
                              item.utilization_pct > 90 ? "from-red-500 to-red-400" : item.utilization_pct > 70 ? "from-yellow-500 to-yellow-400" : "from-emerald-500 to-emerald-400",
                            )}
                            style={{ width: `${Math.min(item.utilization_pct, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs font-medium text-gray-400">{formatPct(item.utilization_pct)}</span>
                      </div>
                    </td>
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
