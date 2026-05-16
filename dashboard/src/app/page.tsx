"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { StatCard } from "@/components/ui/stat-card";
import { useFetch } from "@/hooks/use-fetch";
import { monitoring } from "@/lib/api";
import { formatNumber, formatPct } from "@/lib/utils";
import {
  Activity,
  CheckCircle,
  Globe,
  Server,
  TrendingUp,
  XCircle,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function DashboardPage() {
  const { data: overview, loading, error } = useFetch(
    () => monitoring.overview(),
    [],
    15000,
  );
  const { data: metrics } = useFetch(
    () => monitoring.successMetrics({ days: 14 }),
    [],
    30000,
  );
  const { data: rankings } = useFetch(
    () => monitoring.rankings({ days: 7 }),
    [],
    30000,
  );

  if (loading && !overview) return <Spinner />;
  if (error) return <ErrorBanner message={error} />;
  if (!overview) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Registrations"
          value={formatNumber(overview.total_registrations)}
          icon={TrendingUp}
        />
        <StatCard
          label="Completed"
          value={formatNumber(overview.completed)}
          icon={CheckCircle}
          trend={{ value: formatPct(overview.success_rate_pct), positive: overview.success_rate_pct > 50 }}
        />
        <StatCard
          label="Failed"
          value={formatNumber(overview.failed)}
          icon={XCircle}
        />
        <StatCard
          label="In Progress"
          value={formatNumber(overview.in_progress)}
          icon={Activity}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard
          label="Active Websites"
          value={formatNumber(overview.active_websites)}
          icon={Globe}
        />
        <StatCard
          label="Active Proxies"
          value={formatNumber(overview.active_proxies)}
          icon={Server}
        />
      </div>

      {/* Daily success chart */}
      {metrics && metrics.daily.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Daily Success / Failure (Last 14 Days)</CardTitle>
          </CardHeader>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics.daily}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 11 }} />
                <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 8 }}
                  labelStyle={{ color: "#9ca3af" }}
                />
                <Bar dataKey="success" fill="#34d399" radius={[4, 4, 0, 0]} />
                <Bar dataKey="failure" fill="#f87171" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Rankings table */}
      {rankings && rankings.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Website Rankings (7 Days)</CardTitle>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-gray-500">
                  <th className="pb-3 font-medium">Website</th>
                  <th className="pb-3 font-medium">Total</th>
                  <th className="pb-3 font-medium">Success</th>
                  <th className="pb-3 font-medium">Failed</th>
                  <th className="pb-3 font-medium">Rate</th>
                </tr>
              </thead>
              <tbody>
                {rankings.map((r) => (
                  <tr key={r.website_id} className="border-b border-gray-800/50">
                    <td className="py-3 text-white">{r.website_name}</td>
                    <td className="py-3">{r.total}</td>
                    <td className="py-3 text-emerald-400">{r.success}</td>
                    <td className="py-3 text-red-400">{r.failure}</td>
                    <td className="py-3">{formatPct(r.success_rate_pct)}</td>
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
