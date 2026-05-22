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
    <div className="space-y-8 animate-fade-in">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          <span className="text-gradient">Dashboard</span>
        </h1>
        <p className="mt-1 text-sm text-gray-500">Real-time registration monitoring overview</p>
      </div>

      {/* Primary stats */}
      <div className="stagger-children grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Registrations"
          value={formatNumber(overview.total_registrations)}
          icon={TrendingUp}
          accent="blue"
        />
        <StatCard
          label="Completed"
          value={formatNumber(overview.completed)}
          icon={CheckCircle}
          accent="emerald"
          trend={{ value: formatPct(overview.success_rate_pct), positive: overview.success_rate_pct > 50 }}
        />
        <StatCard
          label="Failed"
          value={formatNumber(overview.failed)}
          icon={XCircle}
          accent="red"
        />
        <StatCard
          label="In Progress"
          value={formatNumber(overview.in_progress)}
          icon={Activity}
          accent="purple"
        />
      </div>

      {/* Secondary stats */}
      <div className="stagger-children grid gap-4 sm:grid-cols-2">
        <StatCard
          label="Active Websites"
          value={formatNumber(overview.active_websites)}
          icon={Globe}
          accent="blue"
        />
        <StatCard
          label="Active Proxies"
          value={formatNumber(overview.active_proxies)}
          icon={Server}
          accent="amber"
        />
      </div>

      {/* Daily success chart */}
      {metrics && metrics.daily.length > 0 && (
        <Card glow="blue" className="animate-fade-in-up">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-gray-300">
              Daily Success / Failure
              <span className="ml-2 text-xs font-normal text-gray-500">Last 14 Days</span>
            </CardTitle>
          </CardHeader>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics.daily} barCategoryGap="20%">
                <defs>
                  <linearGradient id="barSuccess" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#34d399" stopOpacity={0.9} />
                    <stop offset="100%" stopColor="#34d399" stopOpacity={0.5} />
                  </linearGradient>
                  <linearGradient id="barFailure" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f87171" stopOpacity={0.9} />
                    <stop offset="100%" stopColor="#f87171" stopOpacity={0.5} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" strokeOpacity={0.5} />
                <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={{ stroke: "#1f2937" }} />
                <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={{ stroke: "#1f2937" }} />
                <Tooltip
                  contentStyle={{
                    background: "rgba(17,24,39,0.95)",
                    border: "1px solid rgba(55,65,81,0.5)",
                    borderRadius: 12,
                    backdropFilter: "blur(8px)",
                    boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
                  }}
                  labelStyle={{ color: "#9ca3af", fontWeight: 600 }}
                  cursor={{ fill: "rgba(59,130,246,0.05)" }}
                />
                <Bar dataKey="success" fill="url(#barSuccess)" radius={[6, 6, 0, 0]} />
                <Bar dataKey="failure" fill="url(#barFailure)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Rankings table */}
      {rankings && rankings.length > 0 && (
        <Card className="animate-fade-in-up p-0 overflow-hidden">
          <CardHeader className="px-6 pt-6">
            <CardTitle className="text-base font-semibold text-gray-300">
              Website Rankings
              <span className="ml-2 text-xs font-normal text-gray-500">7 Days</span>
            </CardTitle>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-800/60">
                  <th className="px-6 pb-3 pt-0 text-xs font-semibold uppercase tracking-wider text-gray-500">Website</th>
                  <th className="px-6 pb-3 pt-0 text-xs font-semibold uppercase tracking-wider text-gray-500">Total</th>
                  <th className="px-6 pb-3 pt-0 text-xs font-semibold uppercase tracking-wider text-gray-500">Success</th>
                  <th className="px-6 pb-3 pt-0 text-xs font-semibold uppercase tracking-wider text-gray-500">Failed</th>
                  <th className="px-6 pb-3 pt-0 text-xs font-semibold uppercase tracking-wider text-gray-500">Rate</th>
                </tr>
              </thead>
              <tbody>
                {rankings.map((r, i) => (
                  <tr
                    key={r.website_id}
                    className="border-b border-gray-800/30 transition-colors hover:bg-gray-800/30"
                  >
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-gray-800 text-xs font-bold text-gray-400">
                          {i + 1}
                        </span>
                        <span className="font-medium text-white">{r.website_name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-3.5 font-mono text-gray-300">{r.total}</td>
                    <td className="px-6 py-3.5 font-mono text-emerald-400">{r.success}</td>
                    <td className="px-6 py-3.5 font-mono text-red-400">{r.failure}</td>
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-800">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-500"
                            style={{ width: `${Math.min(r.success_rate_pct, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs font-medium text-gray-400">{formatPct(r.success_rate_pct)}</span>
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
