"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { StatCard } from "@/components/ui/stat-card";
import { useThemeClasses } from "@/hooks/use-theme-classes";
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
  const tc = useThemeClasses();

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
        <p className={`mt-1 text-sm ${tc.subtext}`}>Real-time registration monitoring overview</p>
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
            <CardTitle className={`text-base font-semibold ${tc.dark ? "text-gray-300" : "text-slate-700"}`}>
              Daily Success / Failure
              <span className={`ml-2 text-xs font-normal ${tc.subtext}`}>Last 14 Days</span>
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
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke={tc.dark ? "#1f2937" : "#e2e8f0"}
                  strokeOpacity={0.5}
                />
                <XAxis
                  dataKey="date"
                  tick={{ fill: tc.dark ? "#6b7280" : "#94a3b8", fontSize: 11 }}
                  axisLine={{ stroke: tc.dark ? "#1f2937" : "#e2e8f0" }}
                />
                <YAxis
                  tick={{ fill: tc.dark ? "#6b7280" : "#94a3b8", fontSize: 11 }}
                  axisLine={{ stroke: tc.dark ? "#1f2937" : "#e2e8f0" }}
                />
                <Tooltip
                  contentStyle={{
                    background: tc.dark ? "rgba(17,24,39,0.95)" : "rgba(255,255,255,0.95)",
                    border: tc.dark ? "1px solid rgba(55,65,81,0.5)" : "1px solid rgba(226,232,240,0.8)",
                    borderRadius: 12,
                    backdropFilter: "blur(8px)",
                    boxShadow: tc.dark ? "0 8px 32px rgba(0,0,0,0.3)" : "0 8px 32px rgba(0,0,0,0.08)",
                    color: tc.dark ? "#d1d5db" : "#334155",
                  }}
                  labelStyle={{ color: tc.dark ? "#9ca3af" : "#64748b", fontWeight: 600 }}
                  cursor={{ fill: tc.dark ? "rgba(59,130,246,0.05)" : "rgba(59,130,246,0.06)" }}
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
            <CardTitle className={`text-base font-semibold ${tc.dark ? "text-gray-300" : "text-slate-700"}`}>
              Website Rankings
              <span className={`ml-2 text-xs font-normal ${tc.subtext}`}>7 Days</span>
            </CardTitle>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className={`border-b ${tc.tableBorder}`}>
                  <th className={`px-6 pb-3 pt-0 text-xs font-semibold uppercase tracking-wider ${tc.tableHead}`}>Website</th>
                  <th className={`px-6 pb-3 pt-0 text-xs font-semibold uppercase tracking-wider ${tc.tableHead}`}>Total</th>
                  <th className={`px-6 pb-3 pt-0 text-xs font-semibold uppercase tracking-wider ${tc.tableHead}`}>Success</th>
                  <th className={`px-6 pb-3 pt-0 text-xs font-semibold uppercase tracking-wider ${tc.tableHead}`}>Failed</th>
                  <th className={`px-6 pb-3 pt-0 text-xs font-semibold uppercase tracking-wider ${tc.tableHead}`}>Rate</th>
                </tr>
              </thead>
              <tbody>
                {rankings.map((r, i) => (
                  <tr key={r.website_id} className={tc.tableRow}>
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <span className={`flex h-6 w-6 items-center justify-center rounded-md text-xs font-bold ${
                          tc.dark ? "bg-gray-800 text-gray-400" : "bg-slate-100 text-slate-500"
                        }`}>
                          {i + 1}
                        </span>
                        <span className={`font-medium ${tc.heading}`}>{r.website_name}</span>
                      </div>
                    </td>
                    <td className={`px-6 py-3.5 font-mono ${tc.dark ? "text-gray-300" : "text-slate-600"}`}>{r.total}</td>
                    <td className="px-6 py-3.5 font-mono text-emerald-400">{r.success}</td>
                    <td className="px-6 py-3.5 font-mono text-red-400">{r.failure}</td>
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-2">
                        <div className={`h-1.5 w-16 overflow-hidden rounded-full ${tc.dark ? "bg-gray-800" : "bg-slate-200"}`}>
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-500"
                            style={{ width: `${Math.min(r.success_rate_pct, 100)}%` }}
                          />
                        </div>
                        <span className={`text-xs font-medium ${tc.label}`}>{formatPct(r.success_rate_pct)}</span>
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
