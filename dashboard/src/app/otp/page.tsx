"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { StatCard } from "@/components/ui/stat-card";
import { useFetch } from "@/hooks/use-fetch";
import { useThemeClasses } from "@/hooks/use-theme-classes";
import { monitoring } from "@/lib/api";
import { formatNumber, formatPct } from "@/lib/utils";
import { CheckCircle, Clock, Mail, Phone } from "lucide-react";
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

const COLORS = ["#34d399", "#fbbf24", "#60a5fa", "#f87171"];

export default function OtpPage() {
  const { data, loading, error } = useFetch(
    () => monitoring.otpStatus(),
    [],
    15000,
  );
  const tc = useThemeClasses();

  const tooltipStyle = {
    background: tc.dark ? "rgba(17,24,39,0.95)" : "rgba(255,255,255,0.95)",
    border: tc.dark ? "1px solid rgba(55,65,81,0.5)" : "1px solid rgba(226,232,240,0.8)",
    borderRadius: 12,
    boxShadow: tc.dark ? "0 8px 32px rgba(0,0,0,0.3)" : "0 8px 32px rgba(0,0,0,0.08)",
    color: tc.dark ? "#d1d5db" : "#334155",
  };

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBanner message={error} />;
  if (!data) return null;

  const emailPie = [
    { name: "Verified", value: data.email_otp_verified },
    { name: "Pending", value: data.email_otp_pending },
    { name: "Other", value: Math.max(0, data.total_registrations - data.email_otp_verified - data.email_otp_pending) },
  ].filter((d) => d.value > 0);

  const mobilePie = [
    { name: "Verified", value: data.mobile_otp_verified },
    { name: "Pending", value: data.mobile_otp_pending },
    { name: "Other", value: Math.max(0, data.total_registrations - data.mobile_otp_verified - data.mobile_otp_pending) },
  ].filter((d) => d.value > 0);

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          <span className="text-gradient">OTP Tracking</span>
        </h1>
        <p className={`mt-1 text-sm ${tc.subtext}`}>Email and mobile verification status</p>
      </div>

      <div className="stagger-children grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Email Verified" value={formatNumber(data.email_otp_verified)} icon={Mail} accent="emerald"
          trend={{ value: formatPct(data.email_verification_rate_pct), positive: data.email_verification_rate_pct > 50 }} />
        <StatCard label="Email Pending" value={formatNumber(data.email_otp_pending)} icon={Clock} accent="amber" />
        <StatCard label="Mobile Verified" value={formatNumber(data.mobile_otp_verified)} icon={Phone} accent="purple"
          trend={{ value: formatPct(data.mobile_verification_rate_pct), positive: data.mobile_verification_rate_pct > 50 }} />
        <StatCard label="Mobile Pending" value={formatNumber(data.mobile_otp_pending)} icon={Clock} accent="amber" />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card glow="emerald" className="animate-fade-in-up">
          <CardHeader>
            <CardTitle className={`text-base font-semibold ${tc.dark ? "text-gray-300" : "text-slate-700"}`}>Email OTP Distribution</CardTitle>
          </CardHeader>
          {emailPie.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={emailPie} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} innerRadius={45} strokeWidth={2} stroke={tc.dark ? "#030712" : "#f8fafc"} label>
                    {emailPie.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className={`py-8 text-center text-sm ${tc.muted}`}>No email OTP data</p>
          )}
        </Card>

        <Card glow="purple" className="animate-fade-in-up">
          <CardHeader>
            <CardTitle className={`text-base font-semibold ${tc.dark ? "text-gray-300" : "text-slate-700"}`}>Mobile OTP Distribution</CardTitle>
          </CardHeader>
          {mobilePie.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={mobilePie} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} innerRadius={45} strokeWidth={2} stroke={tc.dark ? "#030712" : "#f8fafc"} label>
                    {mobilePie.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className={`py-8 text-center text-sm ${tc.muted}`}>No mobile OTP data</p>
          )}
        </Card>
      </div>

      <Card className="animate-fade-in-up">
        <CardHeader>
          <CardTitle className={`text-base font-semibold ${tc.dark ? "text-gray-300" : "text-slate-700"}`}>Verification Summary</CardTitle>
        </CardHeader>
        <div className="grid gap-6 sm:grid-cols-2">
          <div className={`flex items-center gap-4 rounded-xl p-4 ${tc.dark ? "bg-gray-800/30" : "bg-slate-50"}`}>
            <div className="rounded-xl bg-emerald-500/10 p-3">
              <CheckCircle className="h-6 w-6 text-emerald-400" />
            </div>
            <div>
              <p className={`text-sm ${tc.label}`}>Email Verification Rate</p>
              <p className={`text-2xl font-bold ${tc.heading}`}>{formatPct(data.email_verification_rate_pct)}</p>
            </div>
          </div>
          <div className={`flex items-center gap-4 rounded-xl p-4 ${tc.dark ? "bg-gray-800/30" : "bg-slate-50"}`}>
            <div className="rounded-xl bg-purple-500/10 p-3">
              <CheckCircle className="h-6 w-6 text-purple-400" />
            </div>
            <div>
              <p className={`text-sm ${tc.label}`}>Mobile Verification Rate</p>
              <p className={`text-2xl font-bold ${tc.heading}`}>{formatPct(data.mobile_verification_rate_pct)}</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
