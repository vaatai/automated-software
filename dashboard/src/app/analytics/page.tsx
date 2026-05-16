"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { StatCard } from "@/components/ui/stat-card";
import { useFetch } from "@/hooks/use-fetch";
import { monitoring } from "@/lib/api";
import { formatNumber, formatPct } from "@/lib/utils";
import { CheckCircle, TrendingUp, XCircle } from "lucide-react";
import { useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function AnalyticsPage() {
  const [days, setDays] = useState(30);

  const { data: metrics, loading, error } = useFetch(
    () => monitoring.successMetrics({ days }),
    [days],
  );
  const { data: hourly } = useFetch(
    () => monitoring.hourlyMetrics({ hours: 48 }),
    [],
  );
  const { data: weekly } = useFetch(
    () => monitoring.weeklyMetrics({ weeks: 12 }),
    [],
  );

  if (loading && !metrics) return <Spinner />;
  if (error) return <ErrorBanner message={error} />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white focus:border-blue-600 focus:outline-none"
        >
          <option value={7}>7 Days</option>
          <option value={14}>14 Days</option>
          <option value={30}>30 Days</option>
          <option value={90}>90 Days</option>
        </select>
      </div>

      {metrics && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard
              label="Overall Success Rate"
              value={formatPct(metrics.overall_success_rate_pct)}
              icon={TrendingUp}
              trend={{ value: `${formatNumber(metrics.total_success)} total`, positive: true }}
            />
            <StatCard
              label="Total Successes"
              value={formatNumber(metrics.total_success)}
              icon={CheckCircle}
            />
            <StatCard
              label="Total Failures"
              value={formatNumber(metrics.total_failure)}
              icon={XCircle}
            />
          </div>

          {/* Daily area chart */}
          <Card>
            <CardHeader>
              <CardTitle>Daily Success Rate</CardTitle>
            </CardHeader>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={metrics.daily}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} unit="%" />
                  <Tooltip
                    contentStyle={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 8 }}
                    labelStyle={{ color: "#9ca3af" }}
                  />
                  <Area
                    type="monotone"
                    dataKey="success_rate_pct"
                    stroke="#34d399"
                    fill="#34d399"
                    fillOpacity={0.1}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </>
      )}

      {/* Hourly chart */}
      {hourly && hourly.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Hourly Registrations (Last 48h)</CardTitle>
          </CardHeader>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hourly}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis
                  dataKey="hour"
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  tickFormatter={(h: number) => `${h}:00`}
                />
                <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 8 }}
                  labelStyle={{ color: "#9ca3af" }}
                />
                <Bar dataKey="success" fill="#34d399" stackId="a" />
                <Bar dataKey="failure" fill="#f87171" stackId="a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Weekly chart */}
      {weekly && weekly.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Weekly Registrations (12 Weeks)</CardTitle>
          </CardHeader>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weekly}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis
                  dataKey="week"
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  tickFormatter={(w: number) => `W${w}`}
                />
                <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 8 }}
                  labelStyle={{ color: "#9ca3af" }}
                />
                <Bar dataKey="success" fill="#34d399" stackId="a" />
                <Bar dataKey="failure" fill="#f87171" stackId="a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}
    </div>
  );
}
