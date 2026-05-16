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

const COLORS = ["#34d399", "#f87171", "#fbbf24", "#60a5fa"];

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
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">OTP Verification Tracking</h1>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Email Verified"
          value={formatNumber(data.email_otp_verified)}
          icon={Mail}
          trend={{ value: formatPct(data.email_verification_rate_pct), positive: data.email_verification_rate_pct > 50 }}
        />
        <StatCard
          label="Email Pending"
          value={formatNumber(data.email_otp_pending)}
          icon={Clock}
        />
        <StatCard
          label="Mobile Verified"
          value={formatNumber(data.mobile_otp_verified)}
          icon={Phone}
          trend={{ value: formatPct(data.mobile_verification_rate_pct), positive: data.mobile_verification_rate_pct > 50 }}
        />
        <StatCard
          label="Mobile Pending"
          value={formatNumber(data.mobile_otp_pending)}
          icon={Clock}
        />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Email OTP Distribution</CardTitle>
          </CardHeader>
          {emailPie.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={emailPie} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                    {emailPie.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 8 }} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-gray-500">No email OTP data</p>
          )}
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Mobile OTP Distribution</CardTitle>
          </CardHeader>
          {mobilePie.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={mobilePie} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                    {mobilePie.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 8 }} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-gray-500">No mobile OTP data</p>
          )}
        </Card>
      </div>

      {/* Summary card */}
      <Card>
        <CardHeader>
          <CardTitle>Verification Summary</CardTitle>
        </CardHeader>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-emerald-400" />
            <div>
              <p className="text-sm text-gray-400">Email Verification Rate</p>
              <p className="text-lg font-semibold">{formatPct(data.email_verification_rate_pct)}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-emerald-400" />
            <div>
              <p className="text-sm text-gray-400">Mobile Verification Rate</p>
              <p className="text-lg font-semibold">{formatPct(data.mobile_verification_rate_pct)}</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
