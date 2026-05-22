"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { StatCard } from "@/components/ui/stat-card";
import { useFetch } from "@/hooks/use-fetch";
import { useThemeClasses } from "@/hooks/use-theme-classes";
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
  const tc = useThemeClasses();

  const tooltipStyle = {
    background: tc.dark ? "rgba(17,24,39,0.95)" : "rgba(255,255,255,0.95)",
    border: tc.dark ? "1px solid rgba(55,65,81,0.5)" : "1px solid rgba(226,232,240,0.8)",
    borderRadius: 12,
    backdropFilter: "blur(8px)",
    boxShadow: tc.dark ? "0 8px 32px rgba(0,0,0,0.3)" : "0 8px 32px rgba(0,0,0,0.08)",
    color: tc.dark ? "#d1d5db" : "#334155",
  };
  const axisColor = tc.dark ? "#6b7280" : "#94a3b8";
  const gridColor = tc.dark ? "#1f2937" : "#e2e8f0";

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
    <div className="space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            <span className="text-gradient">Analytics</span>
          </h1>
          <p className={`mt-1 text-sm ${tc.subtext}`}>Registration performance metrics and trends</p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className={tc.inputCls}
          style={{ width: "auto" }}
        >
          <option value={7}>7 Days</option>
          <option value={14}>14 Days</option>
          <option value={30}>30 Days</option>
          <option value={90}>90 Days</option>
        </select>
      </div>

      {metrics && (
        <>
          <div className="stagger-children grid gap-4 sm:grid-cols-3">
            <StatCard
              label="Overall Success Rate"
              value={formatPct(metrics.overall_success_rate_pct)}
              icon={TrendingUp}
              accent="emerald"
              trend={{ value: `${formatNumber(metrics.total_success)} total`, positive: true }}
            />
            <StatCard
              label="Total Successes"
              value={formatNumber(metrics.total_success)}
              icon={CheckCircle}
              accent="emerald"
            />
            <StatCard
              label="Total Failures"
              value={formatNumber(metrics.total_failure)}
              icon={XCircle}
              accent="red"
            />
          </div>

          <Card glow="emerald" className="animate-fade-in-up">
            <CardHeader>
              <CardTitle className={`text-base font-semibold ${tc.dark ? "text-gray-300" : "text-slate-700"}`}>
                Daily Success Rate
              </CardTitle>
            </CardHeader>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={metrics.daily}>
                  <defs>
                    <linearGradient id="areaGreen" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#34d399" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} strokeOpacity={0.5} />
                  <XAxis dataKey="date" tick={{ fill: axisColor, fontSize: 11 }} axisLine={{ stroke: gridColor }} />
                  <YAxis tick={{ fill: axisColor, fontSize: 11 }} unit="%" axisLine={{ stroke: gridColor }} />
                  <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: axisColor, fontWeight: 600 }} />
                  <Area type="monotone" dataKey="success_rate_pct" stroke="#34d399" strokeWidth={2} fill="url(#areaGreen)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </>
      )}

      {hourly && hourly.length > 0 && (
        <Card className="animate-fade-in-up">
          <CardHeader>
            <CardTitle className={`text-base font-semibold ${tc.dark ? "text-gray-300" : "text-slate-700"}`}>
              Hourly Registrations
              <span className={`ml-2 text-xs font-normal ${tc.subtext}`}>Last 48h</span>
            </CardTitle>
          </CardHeader>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hourly}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} strokeOpacity={0.5} />
                <XAxis dataKey="hour" tick={{ fill: axisColor, fontSize: 11 }} tickFormatter={(h: number) => `${h}:00`} axisLine={{ stroke: gridColor }} />
                <YAxis tick={{ fill: axisColor, fontSize: 11 }} axisLine={{ stroke: gridColor }} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: axisColor }} />
                <Bar dataKey="success" fill="#34d399" stackId="a" radius={[4, 4, 0, 0]} opacity={0.85} />
                <Bar dataKey="failure" fill="#f87171" stackId="a" radius={[4, 4, 0, 0]} opacity={0.85} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {weekly && weekly.length > 0 && (
        <Card className="animate-fade-in-up">
          <CardHeader>
            <CardTitle className={`text-base font-semibold ${tc.dark ? "text-gray-300" : "text-slate-700"}`}>
              Weekly Registrations
              <span className={`ml-2 text-xs font-normal ${tc.subtext}`}>12 Weeks</span>
            </CardTitle>
          </CardHeader>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weekly}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} strokeOpacity={0.5} />
                <XAxis dataKey="week" tick={{ fill: axisColor, fontSize: 11 }} tickFormatter={(w: number) => `W${w}`} axisLine={{ stroke: gridColor }} />
                <YAxis tick={{ fill: axisColor, fontSize: 11 }} axisLine={{ stroke: gridColor }} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: axisColor }} />
                <Bar dataKey="success" fill="#34d399" stackId="a" radius={[4, 4, 0, 0]} opacity={0.85} />
                <Bar dataKey="failure" fill="#f87171" stackId="a" radius={[4, 4, 0, 0]} opacity={0.85} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}
    </div>
  );
}
