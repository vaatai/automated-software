"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import { useFetch } from "@/hooks/use-fetch";
import { useThemeClasses } from "@/hooks/use-theme-classes";
import { campaigns, websites } from "@/lib/api";
import type { CampaignEntry, CampaignEntryResult, CampaignResponse } from "@/lib/api";
import { cn } from "@/lib/utils";
import { CheckCircle, Globe, Phone, Play, Plus, Rocket, Target, Trash2, XCircle } from "lucide-react";
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

interface EntryRow {
  id: number;
  website_id: number | null;
  country: string;
  count: number;
  priority: string;
}

let nextId = 1;

function makeEntry(): EntryRow {
  return { id: nextId++, website_id: null, country: "US", count: 1, priority: "normal" };
}

export default function CampaignsPage() {
  const { data: siteList } = useFetch(() => websites.list({ limit: 100, offset: 0 }), []);
  const tc = useThemeClasses();

  const [entries, setEntries] = useState<EntryRow[]>([makeEntry()]);
  const [durationHours, setDurationHours] = useState(24);
  const [launching, setLaunching] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<CampaignResponse | null>(null);

  const addEntry = useCallback(() => {
    setEntries((prev) => [...prev, makeEntry()]);
  }, []);

  const removeEntry = useCallback((id: number) => {
    setEntries((prev) => prev.length > 1 ? prev.filter((e) => e.id !== id) : prev);
  }, []);

  const updateEntry = useCallback((id: number, field: keyof EntryRow, value: string | number | null) => {
    setEntries((prev) => prev.map((e) => e.id === id ? { ...e, [field]: value } : e));
  }, []);

  const countryGroups = entries.reduce<Record<string, number>>((acc, e) => {
    acc[e.country] = (acc[e.country] || 0) + 1;
    return acc;
  }, {});
  const uniqueCountries = Object.keys(countryGroups).length;
  const sharedCountries = Object.entries(countryGroups).filter(([, c]) => c > 1);

  const handleLaunch = async () => {
    const valid = entries.filter((e) => e.website_id);
    if (valid.length === 0) return;
    setLaunching(true);
    setErr(null);
    setResult(null);
    try {
      const campaignEntries: CampaignEntry[] = valid.map((e) => ({
        website_id: e.website_id!,
        country: e.country,
        count: e.count,
        priority: e.priority,
      }));
      const res = await campaigns.launch({ entries: campaignEntries, duration_hours: durationHours });
      setResult(res);
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Failed to launch campaign");
    } finally {
      setLaunching(false);
    }
  };

  const getWebsiteName = (id: number) => {
    const w = siteList?.items.find((w) => w.id === id);
    return w?.name ?? `Website #${id}`;
  };

  return (
    <div className="space-y-8 animate-fade-in px-0 sm:px-0">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
          <span className="text-gradient">Campaigns</span>
        </h1>
        <p className={`mt-1 text-sm ${tc.subtext}`}>
          Run simultaneous registrations across multiple websites and countries
        </p>
      </div>

      {/* Info banner about number sharing */}
      <div className={cn(
        "flex items-start gap-3 rounded-xl border p-4",
        tc.dark ? "border-blue-500/20 bg-blue-950/20" : "border-blue-200 bg-blue-50/50",
      )}>
        <Target className={cn("mt-0.5 h-5 w-5 shrink-0", tc.dark ? "text-blue-400" : "text-blue-600")} />
        <div className={`text-sm ${tc.dark ? "text-blue-300" : "text-blue-700"}`}>
          <p className="font-medium">How campaigns work:</p>
          <ul className="mt-1 space-y-0.5 text-xs opacity-80">
            <li>• Websites with the <strong>same country</strong> automatically share the same rented number</li>
            <li>• If you already have an active rental for a country, it will be reused (no extra cost)</li>
            <li>• New numbers are rented only for countries that don&apos;t have an active rental</li>
            <li>• All registrations run simultaneously in parallel</li>
          </ul>
        </div>
      </div>

      <Card glow="blue">
        <CardHeader>
          <CardTitle className={`flex items-center gap-2 text-base font-semibold ${tc.dark ? "text-gray-300" : "text-slate-700"}`}>
            <div className="rounded-lg bg-blue-500/10 p-2">
              <Rocket className="h-4 w-4 text-blue-400" />
            </div>
            Campaign Builder
          </CardTitle>
        </CardHeader>

        <div className="space-y-4">
          {/* Entries */}
          <div className="space-y-3">
            {entries.map((entry, idx) => (
              <div
                key={entry.id}
                className={cn(
                  "animate-fade-in-up rounded-xl border p-4 transition-all",
                  tc.dark ? "border-gray-800 bg-gray-900/50" : "border-slate-200 bg-slate-50/50",
                )}
                style={{ animationDelay: `${idx * 50}ms` }}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className={cn(
                    "inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider",
                    tc.dark ? "text-gray-500" : "text-slate-400",
                  )}>
                    <Play className="h-3 w-3" /> Entry {idx + 1}
                  </span>
                  {entries.length > 1 && (
                    <button
                      onClick={() => removeEntry(entry.id)}
                      className="rounded-lg p-1.5 text-red-400 transition-colors hover:bg-red-500/10"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>

                <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
                  <div>
                    <label className={`mb-1 block text-xs font-medium ${tc.label}`}>Website</label>
                    <select
                      value={entry.website_id ?? ""}
                      onChange={(e) => updateEntry(entry.id, "website_id", e.target.value ? Number(e.target.value) : null)}
                      className={cn(tc.inputCls, "text-sm")}
                    >
                      <option value="">Select website</option>
                      {siteList?.items.map((w) => (
                        <option key={w.id} value={w.id}>{w.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className={`mb-1 flex items-center gap-1 text-xs font-medium ${tc.label}`}>
                      <Globe className="h-3 w-3" /> Country
                    </label>
                    <select
                      value={entry.country}
                      onChange={(e) => updateEntry(entry.id, "country", e.target.value)}
                      className={cn(tc.inputCls, "text-sm")}
                    >
                      {COUNTRIES.map((c) => (
                        <option key={c.code} value={c.code}>{c.name} ({c.dial})</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className={`mb-1 block text-xs font-medium ${tc.label}`}>Count</label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={entry.count}
                      onChange={(e) => updateEntry(entry.id, "count", Number(e.target.value))}
                      className={cn(tc.inputCls, "text-sm")}
                    />
                  </div>
                  <div>
                    <label className={`mb-1 block text-xs font-medium ${tc.label}`}>Priority</label>
                    <select
                      value={entry.priority}
                      onChange={(e) => updateEntry(entry.id, "priority", e.target.value)}
                      className={cn(tc.inputCls, "text-sm")}
                    >
                      <option value="high">High</option>
                      <option value="normal">Normal</option>
                      <option value="low">Low</option>
                    </select>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Add entry button */}
          <button
            onClick={addEntry}
            className={cn(
              "flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed py-3 text-sm font-medium transition-all hover:-translate-y-0.5",
              tc.dark
                ? "border-gray-700 text-gray-400 hover:border-blue-500/40 hover:text-blue-400"
                : "border-slate-300 text-slate-500 hover:border-blue-400 hover:text-blue-600",
            )}
          >
            <Plus className="h-4 w-4" /> Add Another Website
          </button>

          {/* Number sharing summary */}
          {uniqueCountries > 0 && (
            <div className={cn(
              "rounded-xl border p-3",
              tc.dark ? "border-gray-800 bg-gray-900/30" : "border-slate-200 bg-slate-50",
            )}>
              <div className="flex flex-wrap items-center gap-2">
                <Phone className={cn("h-4 w-4", tc.dark ? "text-emerald-400" : "text-emerald-600")} />
                <span className={`text-sm font-medium ${tc.dark ? "text-gray-300" : "text-slate-700"}`}>
                  {uniqueCountries} phone number{uniqueCountries > 1 ? "s" : ""} needed
                </span>
                {sharedCountries.length > 0 && (
                  <span className={`text-xs ${tc.muted}`}>
                    (sharing: {sharedCountries.map(([c, n]) => `${c} × ${n} websites`).join(", ")})
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Duration selector */}
          <div>
            <label className={`mb-1.5 block text-sm font-medium ${tc.label}`}>Number Rental Duration</label>
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
              {[
                { value: 1, label: "1h" },
                { value: 6, label: "6h" },
                { value: 12, label: "12h" },
                { value: 24, label: "24h" },
                { value: 48, label: "2d" },
                { value: 168, label: "7d" },
              ].map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setDurationHours(opt.value)}
                  className={cn(
                    "rounded-lg px-3 py-2 text-xs font-medium transition-all",
                    durationHours === opt.value
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
          </div>

          {err && <ErrorBanner message={err} />}

          {/* Launch button */}
          <button
            onClick={handleLaunch}
            disabled={launching || entries.every((e) => !e.website_id)}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 py-3.5 text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition-all hover:-translate-y-0.5 hover:shadow-xl hover:shadow-blue-500/30 disabled:opacity-50 disabled:hover:translate-y-0"
          >
            {launching ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Launching Campaign...
              </>
            ) : (
              <>
                <Rocket className="h-4 w-4" />
                Launch Campaign ({entries.filter((e) => e.website_id).length} entries)
              </>
            )}
          </button>
        </div>
      </Card>

      {/* Results */}
      {result && (
        <Card glow={result.total_failed > 0 ? "red" : "emerald"} className="animate-fade-in-up">
          <CardHeader>
            <CardTitle className={`flex items-center gap-2 text-base font-semibold ${tc.dark ? "text-gray-300" : "text-slate-700"}`}>
              <div className={cn(
                "rounded-lg p-2",
                result.total_failed === 0 ? "bg-emerald-500/10" : "bg-amber-500/10",
              )}>
                {result.total_failed === 0
                  ? <CheckCircle className="h-4 w-4 text-emerald-400" />
                  : <XCircle className="h-4 w-4 text-amber-400" />}
              </div>
              Campaign Results
            </CardTitle>
          </CardHeader>

          {/* Summary stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <div className={cn("rounded-lg p-3 text-center", tc.dark ? "bg-gray-800/50" : "bg-slate-100")}>
              <p className={`text-xs ${tc.muted}`}>Total Queued</p>
              <p className={`text-xl font-bold ${tc.dark ? "text-emerald-400" : "text-emerald-600"}`}>{result.total_queued}</p>
            </div>
            <div className={cn("rounded-lg p-3 text-center", tc.dark ? "bg-gray-800/50" : "bg-slate-100")}>
              <p className={`text-xs ${tc.muted}`}>Failed</p>
              <p className={`text-xl font-bold ${result.total_failed > 0 ? "text-red-400" : tc.dark ? "text-gray-400" : "text-slate-500"}`}>{result.total_failed}</p>
            </div>
            <div className={cn("rounded-lg p-3 text-center", tc.dark ? "bg-gray-800/50" : "bg-slate-100")}>
              <p className={`text-xs ${tc.muted}`}>Numbers Reused</p>
              <p className={`text-xl font-bold ${tc.dark ? "text-blue-400" : "text-blue-600"}`}>{result.numbers_reused}</p>
            </div>
            <div className={cn("rounded-lg p-3 text-center", tc.dark ? "bg-gray-800/50" : "bg-slate-100")}>
              <p className={`text-xs ${tc.muted}`}>New Rentals</p>
              <p className={`text-xl font-bold ${tc.dark ? "text-violet-400" : "text-violet-600"}`}>{result.numbers_rented}</p>
            </div>
          </div>

          {/* Per-entry results */}
          <div className="overflow-x-auto">
            <table className={cn("w-full text-left text-sm", tc.dark ? "text-gray-300" : "text-slate-700")}>
              <thead>
                <tr className={cn("border-b text-xs uppercase tracking-wider", tc.dark ? "border-gray-800 text-gray-500" : "border-slate-200 text-slate-400")}>
                  <th className="pb-2 pr-4">Website</th>
                  <th className="pb-2 pr-4">Country</th>
                  <th className="pb-2 pr-4">Phone</th>
                  <th className="pb-2 pr-4">Queued</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {result.results.map((r: CampaignEntryResult, i: number) => (
                  <tr
                    key={i}
                    className={cn(
                      "border-b animate-fade-in",
                      tc.dark ? "border-gray-800/50" : "border-slate-100",
                    )}
                    style={{ animationDelay: `${i * 80}ms` }}
                  >
                    <td className="py-2.5 pr-4 font-medium">{getWebsiteName(r.website_id)}</td>
                    <td className="py-2.5 pr-4">
                      <span className={cn(
                        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
                        tc.dark ? "bg-gray-800 text-gray-300" : "bg-slate-100 text-slate-600",
                      )}>
                        <Globe className="h-3 w-3" /> {r.country}
                      </span>
                    </td>
                    <td className="py-2.5 pr-4 font-mono text-xs">
                      {r.phone_number || <span className={tc.muted}>—</span>}
                    </td>
                    <td className="py-2.5 pr-4">{r.queued}/{r.count}</td>
                    <td className="py-2.5">
                      {r.error ? (
                        <span className="flex items-center gap-1 text-xs text-red-400">
                          <XCircle className="h-3 w-3" /> {r.error}
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-xs text-emerald-400">
                          <CheckCircle className="h-3 w-3" /> Queued
                        </span>
                      )}
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
