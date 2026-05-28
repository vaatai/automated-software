"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { useFetch } from "@/hooks/use-fetch";
import { useThemeClasses } from "@/hooks/use-theme-classes";
import { rentals } from "@/lib/api";
import type { RentalItem } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Clock, Globe, Phone, PhoneCall, Plus, Server, Timer, X } from "lucide-react";
import { useCallback, useState } from "react";

const COUNTRIES = [
  { code: "US", name: "United States", dial: "+1" },
  { code: "GB", name: "United Kingdom", dial: "+44" },
  { code: "IN", name: "India", dial: "+91" },
  { code: "RU", name: "Russia", dial: "+7" },
  { code: "DE", name: "Germany", dial: "+49" },
  { code: "FR", name: "France", dial: "+33" },
  { code: "BR", name: "Brazil", dial: "+55" },
  { code: "CA", name: "Canada", dial: "+1" },
  { code: "AU", name: "Australia", dial: "+61" },
  { code: "JP", name: "Japan", dial: "+81" },
  { code: "KR", name: "South Korea", dial: "+82" },
  { code: "CN", name: "China", dial: "+86" },
  { code: "ID", name: "Indonesia", dial: "+62" },
  { code: "PH", name: "Philippines", dial: "+63" },
  { code: "NG", name: "Nigeria", dial: "+234" },
  { code: "PK", name: "Pakistan", dial: "+92" },
  { code: "MX", name: "Mexico", dial: "+52" },
  { code: "TR", name: "Turkey", dial: "+90" },
  { code: "EG", name: "Egypt", dial: "+20" },
  { code: "UA", name: "Ukraine", dial: "+380" },
  { code: "PL", name: "Poland", dial: "+48" },
  { code: "NL", name: "Netherlands", dial: "+31" },
  { code: "SE", name: "Sweden", dial: "+46" },
  { code: "IT", name: "Italy", dial: "+39" },
  { code: "ES", name: "Spain", dial: "+34" },
  { code: "TH", name: "Thailand", dial: "+66" },
  { code: "VN", name: "Vietnam", dial: "+84" },
  { code: "ZA", name: "South Africa", dial: "+27" },
  { code: "KE", name: "Kenya", dial: "+254" },
  { code: "CO", name: "Colombia", dial: "+57" },
];

function formatTimeLeft(seconds: number): string {
  if (seconds <= 0) return "Expired";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m left`;
  return `${m}m left`;
}

function statusBadge(status: string, dark: boolean) {
  const styles: Record<string, string> = {
    rented: dark ? "bg-blue-500/10 text-blue-400 ring-blue-500/20" : "bg-blue-50 text-blue-600 ring-blue-500/20",
    otp_received: dark ? "bg-emerald-500/10 text-emerald-400 ring-emerald-500/20" : "bg-emerald-50 text-emerald-600 ring-emerald-500/20",
    finished: dark ? "bg-gray-500/10 text-gray-400 ring-gray-500/20" : "bg-slate-50 text-slate-500 ring-slate-500/20",
    cancelled: dark ? "bg-amber-500/10 text-amber-400 ring-amber-500/20" : "bg-amber-50 text-amber-600 ring-amber-500/20",
    expired: dark ? "bg-red-500/10 text-red-400 ring-red-500/20" : "bg-red-50 text-red-600 ring-red-500/20",
  };
  return cn(
    "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
    styles[status] || (dark ? "bg-gray-500/10 text-gray-400" : "bg-slate-50 text-slate-500"),
  );
}

export default function RentalsPage() {
  const { data, loading, error, refetch } = useFetch(
    () => rentals.list({ limit: 50, offset: 0 }),
    [],
    15000,
  );
  const tc = useThemeClasses();
  const [showRentDialog, setShowRentDialog] = useState(false);
  const [rentCountry, setRentCountry] = useState("US");
  const [rentDuration, setRentDuration] = useState(24);
  const [customDuration, setCustomDuration] = useState("");
  const [rentLabel, setRentLabel] = useState("");
  const [rentProvider, setRentProvider] = useState<string>("");
  const [renting, setRenting] = useState(false);
  const [rentErr, setRentErr] = useState<string | null>(null);
  const [releasing, setReleasing] = useState<number | null>(null);

  const effectiveDuration = rentDuration === -1 ? (parseFloat(customDuration) || 1) : rentDuration;

  const handleRent = useCallback(async () => {
    setRenting(true);
    setRentErr(null);
    try {
      await rentals.rent({ country: rentCountry, label: rentLabel || undefined, duration_hours: effectiveDuration, preferred_provider: rentProvider || undefined });
      setShowRentDialog(false);
      setRentLabel("");
      refetch();
    } catch (e) {
      setRentErr(e instanceof Error ? e.message : "Failed to rent number");
    } finally {
      setRenting(false);
    }
  }, [rentCountry, rentLabel, effectiveDuration, rentProvider, refetch]);

  const handleRelease = useCallback(async (id: number) => {
    setReleasing(id);
    try {
      await rentals.release(id);
      refetch();
    } catch {
      // ignore
    } finally {
      setReleasing(null);
    }
  }, [refetch]);

  const activeCount = data?.items.filter((r: RentalItem) => r.status === "rented" || r.status === "otp_received").length ?? 0;
  const totalOtps = data?.items.reduce((sum: number, r: RentalItem) => sum + r.otp_count, 0) ?? 0;

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBanner message={error} />;

  return (
    <div className="space-y-8 animate-fade-in px-0 sm:px-0">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            <span className="text-gradient">Rented Numbers</span>
          </h1>
          <p className={`mt-1 text-sm ${tc.subtext}`}>
            Manage phone number rentals with custom duration for multi-OTP verification
          </p>
        </div>
        <button
          onClick={() => setShowRentDialog(true)}
          className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 px-4 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition-all hover:-translate-y-0.5 hover:shadow-xl hover:shadow-blue-500/30"
        >
          <Plus className="h-4 w-4" />
          Rent New Number
        </button>
      </div>

      {/* Stats */}
      <div className="grid gap-3 sm:gap-4 grid-cols-2 lg:grid-cols-3 stagger-children">
        <Card glow="blue" className="p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-500/10 p-2.5">
              <Phone className="h-5 w-5 text-blue-400" />
            </div>
            <div>
              <p className={`text-xs font-medium ${tc.muted}`}>Active Rentals</p>
              <p className={`text-2xl font-bold ${tc.value}`}>{activeCount}</p>
            </div>
          </div>
        </Card>
        <Card glow="emerald" className="p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-emerald-500/10 p-2.5">
              <PhoneCall className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <p className={`text-xs font-medium ${tc.muted}`}>Total OTPs Received</p>
              <p className={`text-2xl font-bold ${tc.value}`}>{totalOtps}</p>
            </div>
          </div>
        </Card>
        <Card glow="purple" className="p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-violet-500/10 p-2.5">
              <Globe className="h-5 w-5 text-violet-400" />
            </div>
            <div>
              <p className={`text-xs font-medium ${tc.muted}`}>Total Numbers</p>
              <p className={`text-2xl font-bold ${tc.value}`}>{data?.total ?? 0}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Rent Dialog */}
      {showRentDialog && (
        <Card glow="blue" className="max-w-md animate-fade-in-up">
          <CardHeader>
            <CardTitle className={`flex items-center gap-2 text-base font-semibold ${tc.dark ? "text-gray-300" : "text-slate-700"}`}>
              <div className="rounded-lg bg-blue-500/10 p-2">
                <Phone className="h-4 w-4 text-blue-400" />
              </div>
              Rent a Phone Number
            </CardTitle>
          </CardHeader>
          <div className="space-y-4">
            <div>
              <label className={`mb-1.5 flex items-center gap-2 text-sm font-medium ${tc.label}`}>
                <Globe className="h-3.5 w-3.5" /> Country
              </label>
              <select value={rentCountry} onChange={(e) => setRentCountry(e.target.value)} className={tc.inputCls}>
                {COUNTRIES.map((c) => (
                  <option key={c.code} value={c.code}>{c.name} ({c.dial})</option>
                ))}
              </select>
            </div>
            <div>
              <label className={`mb-1.5 flex items-center gap-2 text-sm font-medium ${tc.label}`}>
                <Clock className="h-3.5 w-3.5" /> Rental Duration
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { value: 1, label: "1 Hour" },
                  { value: 6, label: "6 Hours" },
                  { value: 12, label: "12 Hours" },
                  { value: 24, label: "24 Hours" },
                  { value: 48, label: "2 Days" },
                  { value: -1, label: "Custom" },
                ].map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setRentDuration(opt.value)}
                    className={cn(
                      "rounded-lg px-3 py-2 text-xs font-medium transition-all",
                      rentDuration === opt.value
                        ? "bg-blue-600 text-white shadow-md shadow-blue-500/20"
                        : tc.dark
                          ? "bg-gray-800 text-gray-300 hover:bg-gray-700"
                          : "bg-slate-100 text-slate-600 hover:bg-slate-200",
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              {rentDuration === -1 && (
                <div className="mt-2 flex items-center gap-2">
                  <input
                    type="number"
                    min={0.5}
                    max={720}
                    step={0.5}
                    value={customDuration}
                    onChange={(e) => setCustomDuration(e.target.value)}
                    placeholder="Hours"
                    className={tc.inputCls}
                  />
                  <span className={`text-sm ${tc.muted}`}>hours</span>
                </div>
              )}
              <p className={`mt-1 text-xs ${tc.muted}`}>
                Number will be available for {effectiveDuration < 1 ? `${Math.round(effectiveDuration * 60)} minutes` : effectiveDuration === 1 ? "1 hour" : `${effectiveDuration} hours`}
              </p>
            </div>
            <div>
              <label className={`mb-1.5 flex items-center gap-2 text-sm font-medium ${tc.label}`}>
                <Server className="h-3.5 w-3.5" /> SMS Provider
              </label>
              <select value={rentProvider} onChange={(e) => setRentProvider(e.target.value)} className={tc.inputCls}>
                <option value="">Auto (default order)</option>
                <option value="pvapins">PVAPins</option>
                <option value="5sim">5SIM</option>
                <option value="sms-activate">SMS-Activate</option>
              </select>
              <p className={`mt-1 text-xs ${tc.muted}`}>
                {rentProvider ? `${rentProvider} will be tried first, others as fallback` : rentCountry === "IN" ? "India: PVAPins → 5SIM → SMS-Activate" : "5SIM → PVAPins → SMS-Activate"}
              </p>
            </div>
            <div>
              <label className={`mb-1.5 block text-sm font-medium ${tc.label}`}>Label (optional)</label>
              <input
                type="text"
                value={rentLabel}
                onChange={(e) => setRentLabel(e.target.value)}
                placeholder="e.g. For Gmail registrations"
                className={tc.inputCls}
              />
            </div>
            {rentErr && <ErrorBanner message={rentErr} />}
            <div className="flex gap-3">
              <button
                onClick={handleRent}
                disabled={renting}
                className="flex-1 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition-all hover:-translate-y-0.5 disabled:opacity-50"
              >
                {renting ? "Renting..." : "Rent Number"}
              </button>
              <button
                onClick={() => { setShowRentDialog(false); setRentErr(null); }}
                className={cn(
                  "rounded-xl px-4 py-2.5 text-sm font-medium transition-all",
                  tc.dark ? "bg-gray-800 text-gray-300 hover:bg-gray-700" : "bg-slate-100 text-slate-600 hover:bg-slate-200",
                )}
              >
                Cancel
              </button>
            </div>
          </div>
        </Card>
      )}

      {/* Rentals Table */}
      {data && data.items.length > 0 ? (
        <Card glow="blue">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className={`border-b text-left ${tc.tableBorder}`}>
                  <th className={`px-3 py-3 text-xs font-medium uppercase tracking-wider ${tc.tableHead}`}>Phone</th>
                  <th className={`px-3 py-3 text-xs font-medium uppercase tracking-wider ${tc.tableHead} hidden sm:table-cell`}>Country</th>
                  <th className={`px-3 py-3 text-xs font-medium uppercase tracking-wider ${tc.tableHead}`}>Status</th>
                  <th className={`px-3 py-3 text-xs font-medium uppercase tracking-wider ${tc.tableHead}`}>OTPs</th>
                  <th className={`px-3 py-3 text-xs font-medium uppercase tracking-wider ${tc.tableHead} hidden md:table-cell`}>Provider</th>
                  <th className={`px-3 py-3 text-xs font-medium uppercase tracking-wider ${tc.tableHead}`}>Time Left</th>
                  <th className={`px-3 py-3 text-xs font-medium uppercase tracking-wider ${tc.tableHead} hidden lg:table-cell`}>Label</th>
                  <th className={`px-3 py-3 ${tc.tableHead}`}></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((r: RentalItem) => {
                  const isActive = r.status === "rented" || r.status === "otp_received";
                  const countryInfo = COUNTRIES.find((c) => c.code === r.country);
                  return (
                    <tr key={r.id} className={tc.tableRow}>
                      <td className={`px-3 py-3 font-mono text-sm ${tc.value}`}>{r.phone_number}</td>
                      <td className={`px-3 py-3 hidden sm:table-cell ${tc.label}`}>
                        {countryInfo ? `${countryInfo.name} (${countryInfo.dial})` : r.country}
                      </td>
                      <td className="px-3 py-3">
                        <span className={statusBadge(r.status, tc.dark)}>{r.status.replace("_", " ")}</span>
                      </td>
                      <td className={`px-3 py-3 ${tc.value}`}>
                        <span className={cn(
                          "inline-flex items-center gap-1 font-semibold",
                          r.otp_count > 0 ? "text-emerald-400" : tc.muted,
                        )}>
                          {r.otp_count}
                        </span>
                      </td>
                      <td className={`px-3 py-3 hidden md:table-cell ${tc.label}`}>{r.provider}</td>
                      <td className="px-3 py-3">
                        {isActive ? (
                          <span className={cn(
                            "flex items-center gap-1 text-xs font-medium",
                            r.remaining_seconds > 3600 ? "text-emerald-400" : r.remaining_seconds > 600 ? "text-amber-400" : "text-red-400",
                          )}>
                            <Timer className="h-3 w-3" />
                            {formatTimeLeft(r.remaining_seconds)}
                          </span>
                        ) : (
                          <span className={`text-xs ${tc.muted}`}>—</span>
                        )}
                      </td>
                      <td className={`px-3 py-3 hidden lg:table-cell text-xs ${tc.muted} max-w-[150px] truncate`}>
                        {r.label || "—"}
                      </td>
                      <td className="px-3 py-3">
                        {isActive && (
                          <button
                            onClick={() => handleRelease(r.id)}
                            disabled={releasing === r.id}
                            className={cn(
                              "rounded-lg px-2 py-1 text-xs font-medium transition-all",
                              tc.dark
                                ? "bg-red-500/10 text-red-400 hover:bg-red-500/20"
                                : "bg-red-50 text-red-600 hover:bg-red-100",
                            )}
                            title="Release number"
                          >
                            {releasing === r.id ? "..." : "Release"}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <EmptyState
          icon={Phone}
          title="No rented numbers"
          description="Rent a phone number to start receiving OTPs for multiple website registrations"
        />
      )}
    </div>
  );
}
