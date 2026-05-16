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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Daily Limits</h1>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white focus:border-blue-600 focus:outline-none"
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
        <Card className="p-0">
          <CardHeader className="px-6 pt-6">
            <CardTitle>Daily Usage ({data.period_days} Days)</CardTitle>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-gray-500">
                  <th className="px-6 py-3 font-medium">Date</th>
                  <th className="px-6 py-3 font-medium">Website</th>
                  <th className="px-6 py-3 font-medium">Limit</th>
                  <th className="px-6 py-3 font-medium">Used</th>
                  <th className="px-6 py-3 font-medium">Success</th>
                  <th className="px-6 py-3 font-medium">Failed</th>
                  <th className="px-6 py-3 font-medium">Utilization</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item, i) => (
                  <tr key={i} className="border-b border-gray-800/50">
                    <td className="px-6 py-3 font-mono text-xs text-gray-400">{item.date}</td>
                    <td className="px-6 py-3 text-white">{item.website_name}</td>
                    <td className="px-6 py-3">{item.daily_limit}</td>
                    <td className="px-6 py-3">{item.registration_count}</td>
                    <td className="px-6 py-3 text-emerald-400">{item.success_count}</td>
                    <td className="px-6 py-3 text-red-400">{item.failure_count}</td>
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-16 overflow-hidden rounded-full bg-gray-800">
                          <div
                            className={cn(
                              "h-full rounded-full",
                              item.utilization_pct > 90 ? "bg-red-500" : item.utilization_pct > 70 ? "bg-yellow-500" : "bg-emerald-500",
                            )}
                            style={{ width: `${Math.min(item.utilization_pct, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-400">{formatPct(item.utilization_pct)}</span>
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
