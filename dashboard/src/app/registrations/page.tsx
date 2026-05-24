"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { useFetch } from "@/hooks/use-fetch";
import { useThemeClasses } from "@/hooks/use-theme-classes";
import { registrations, rentals, websites } from "@/lib/api";
import type { RentalItem } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Phone, Play, Rocket, Timer } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

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

export default function RegistrationsPage() {
  const { data: siteList } = useFetch(() => websites.list({ limit: 100, offset: 0 }), []);
  const [selectedWebsite, setSelectedWebsite] = useState<number | null>(null);
  const [count, setCount] = useState(1);
  const [priority, setPriority] = useState("normal");
  const [phoneCountry, setPhoneCountry] = useState("US");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [activeRentals, setActiveRentals] = useState<RentalItem[]>([]);
  const [selectedRentalId, setSelectedRentalId] = useState<number | null>(null);
  const tc = useThemeClasses();

  const selectedSite = siteList?.items.find((w) => w.id === selectedWebsite);
  const needsMobileOtp = selectedSite?.requires_mobile_otp;

  // Load active rentals for the selected country when mobile OTP is needed
  const loadActiveRentals = useCallback(async () => {
    if (!needsMobileOtp) {
      setActiveRentals([]);
      return;
    }
    try {
      const res = await rentals.active(phoneCountry);
      setActiveRentals(res.items);
    } catch {
      setActiveRentals([]);
    }
  }, [needsMobileOtp, phoneCountry]);

  useEffect(() => {
    loadActiveRentals();
  }, [loadActiveRentals]);

  const selectedRental = activeRentals.find((r) => r.id === selectedRentalId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWebsite) return;
    setSubmitting(true);
    setErr(null);
    setResult(null);
    try {
      const custom_data: Record<string, unknown> = {};
      if (needsMobileOtp) {
        custom_data.phone_country = phoneCountry;
        if (selectedRental) {
          custom_data.reuse_rental_id = selectedRental.id;
          custom_data.reuse_phone = selectedRental.phone_number;
          custom_data.reuse_provider = selectedRental.provider;
          custom_data.reuse_order_id = selectedRental.order_id;
          custom_data.reuse_otp_count = selectedRental.otp_count;
          custom_data.reuse_last_otp = selectedRental.otp_code;
        }
      }
      await registrations.create({
        website_id: selectedWebsite,
        count,
        priority,
        custom_data: Object.keys(custom_data).length > 0 ? custom_data : undefined,
      });
      const reuseMsg = selectedRental ? ` reusing ${selectedRental.phone_number}` : "";
      setResult(`Queued ${count} registration(s)${needsMobileOtp ? ` with ${phoneCountry} numbers${reuseMsg}` : ""}`);
      loadActiveRentals();
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in px-0 sm:px-0">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
          <span className="text-gradient">Registrations</span>
        </h1>
        <p className={`mt-1 text-sm ${tc.subtext}`}>Queue new registration tasks</p>
      </div>

      <Card glow="blue" className="max-w-lg">
        <CardHeader>
          <CardTitle className={`flex items-center gap-2 text-base font-semibold ${tc.dark ? "text-gray-300" : "text-slate-700"}`}>
            <div className="rounded-lg bg-blue-500/10 p-2">
              <Rocket className="h-4 w-4 text-blue-400" />
            </div>
            Start Registrations
          </CardTitle>
        </CardHeader>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className={`mb-1.5 block text-sm font-medium ${tc.label}`}>Website</label>
            <select
              required
              value={selectedWebsite ?? ""}
              onChange={(e) => setSelectedWebsite(Number(e.target.value))}
              className={tc.inputCls}
            >
              <option value="" disabled>Select a website</option>
              {siteList?.items.map((w) => (
                <option key={w.id} value={w.id}>{w.name} ({w.url || w.domain})</option>
              ))}
            </select>
          </div>

          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
            <div>
              <label className={`mb-1.5 block text-sm font-medium ${tc.label}`}>Count</label>
              <input
                type="number"
                min={1}
                max={1000}
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
                className={tc.inputCls}
              />
            </div>
            <div>
              <label className={`mb-1.5 block text-sm font-medium ${tc.label}`}>Priority</label>
              <select value={priority} onChange={(e) => setPriority(e.target.value)} className={tc.inputCls}>
                <option value="high">High</option>
                <option value="normal">Normal</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>

          {/* Country selector for mobile OTP */}
          {needsMobileOtp && (
            <div className="animate-fade-in-up space-y-4">
              <div>
                <label className={`mb-1.5 flex items-center gap-2 text-sm font-medium ${tc.label}`}>
                  <Phone className="h-3.5 w-3.5" /> Phone Number Country
                </label>
                <select
                  value={phoneCountry}
                  onChange={(e) => { setPhoneCountry(e.target.value); setSelectedRentalId(null); }}
                  className={tc.inputCls}
                >
                  {COUNTRIES.map((c) => (
                    <option key={c.code} value={c.code}>{c.name} ({c.dial})</option>
                  ))}
                </select>
                <p className={`mt-1 text-xs ${tc.muted}`}>Country for renting temporary phone numbers for this batch</p>
              </div>

              {/* Active rentals for reuse */}
              {activeRentals.length > 0 && (
                <div className={cn(
                  "rounded-xl border p-4",
                  tc.dark ? "border-blue-500/20 bg-blue-950/20" : "border-blue-200 bg-blue-50/50",
                )}>
                  <p className={`mb-2 flex items-center gap-2 text-sm font-medium ${tc.dark ? "text-blue-400" : "text-blue-600"}`}>
                    <Phone className="h-3.5 w-3.5" />
                    Reuse an active rented number (24h rental)
                  </p>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="rental"
                        checked={selectedRentalId === null}
                        onChange={() => setSelectedRentalId(null)}
                        className="accent-blue-500"
                      />
                      <span className={`text-sm ${tc.label}`}>Rent a new number</span>
                    </label>
                    {activeRentals.map((r) => (
                      <label key={r.id} className={cn(
                        "flex items-center gap-2 rounded-lg p-2 transition-colors",
                        selectedRentalId === r.id
                          ? tc.dark ? "bg-blue-500/10" : "bg-blue-100"
                          : "",
                      )}>
                        <input
                          type="radio"
                          name="rental"
                          checked={selectedRentalId === r.id}
                          onChange={() => setSelectedRentalId(r.id)}
                          className="accent-blue-500"
                        />
                        <span className={`font-mono text-sm ${tc.value}`}>{r.phone_number}</span>
                        <span className={cn(
                          "text-xs font-medium",
                          r.remaining_seconds > 3600 ? "text-emerald-400" : r.remaining_seconds > 600 ? "text-amber-400" : "text-red-400",
                        )}>
                          <Timer className="mr-0.5 inline h-3 w-3" />
                          {formatTimeLeft(r.remaining_seconds)}
                        </span>
                        <span className={`text-xs ${tc.muted}`}>
                          ({r.otp_count} OTPs · {r.provider})
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {err && <ErrorBanner message={err} />}
          {result && (
            <div className="animate-fade-in-up flex items-center gap-2 rounded-xl border border-emerald-900/40 bg-emerald-900/10 px-4 py-3 text-sm text-emerald-400">
              <Play className="h-4 w-4" />
              {result}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || !selectedWebsite}
            className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 py-3 text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition-all hover:-translate-y-0.5 hover:shadow-xl hover:shadow-blue-500/30 disabled:opacity-50 disabled:hover:translate-y-0"
          >
            {submitting ? "Queueing..." : "Start Registrations"}
          </button>
        </form>
      </Card>

      {(!siteList || siteList.items.length === 0) && (
        <EmptyState icon={Play} title="No websites configured" description="Add a website first on the Websites page" />
      )}
    </div>
  );
}
