"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { StatCard } from "@/components/ui/stat-card";
import { useFetch } from "@/hooks/use-fetch";
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

const tooltipStyle = {
  background: "rgba(17,24,39,0.95)",
  border: "1px solid rgba(55,65,81,0.5)",
  borderRadius: 12,
  boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
};

export default function OtpPage() {
  const { data, loading, error } = useFetch(
    () => monitoring.otpStatus(),
    [],
    15000,
  );

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
        <p className="mt-1 text-sm text-gray-500">Email and mobile verification status</p>
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
            <CardTitle className="text-base font-semibold text-gray-300">Email OTP Distribution</CardTitle>
          </CardHeader>
          {emailPie.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={emailPie} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} innerRadius={45} strokeWidth={2} stroke="#030712" label>
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
            <p className="py-8 text-center text-sm text-gray-500">No email OTP data</p>
          )}
        </Card>

        <Card glow="purple" className="animate-fade-in-up">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-gray-300">Mobile OTP Distribution</CardTitle>
          </CardHeader>
          {mobilePie.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={mobilePie} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} innerRadius={45} strokeWidth={2} stroke="#030712" label>
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
            <p className="py-8 text-center text-sm text-gray-500">No mobile OTP data</p>
          )}
        </Card>
      </div>

      <Card className="animate-fade-in-up">
        <CardHeader>
          <CardTitle className="text-base font-semibold text-gray-300">Verification Summary</CardTitle>
        </CardHeader>
        <div className="grid gap-6 sm:grid-cols-2">
          <div className="flex items-center gap-4 rounded-xl bg-gray-800/30 p-4">
            <div className="rounded-xl bg-emerald-500/10 p-3">
              <CheckCircle className="h-6 w-6 text-emerald-400" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Email Verification Rate</p>
              <p className="text-2xl font-bold text-white">{formatPct(data.email_verification_rate_pct)}</p>
            </div>
          </div>
          <div className="flex items-center gap-4 rounded-xl bg-gray-800/30 p-4">
            <div className="rounded-xl bg-purple-500/10 p-3">
              <CheckCircle className="h-6 w-6 text-purple-400" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Mobile Verification Rate</p>
              <p className="text-2xl font-bold text-white">{formatPct(data.mobile_verification_rate_pct)}</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
