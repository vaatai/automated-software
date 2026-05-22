"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { useFetch } from "@/hooks/use-fetch";
import { registrations, websites } from "@/lib/api";
import { Play, Rocket } from "lucide-react";
import { useState } from "react";

export default function RegistrationsPage() {
  const { data: siteList } = useFetch(() => websites.list({ limit: 100, offset: 0 }), []);
  const [selectedWebsite, setSelectedWebsite] = useState<number | null>(null);
  const [count, setCount] = useState(1);
  const [priority, setPriority] = useState("normal");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWebsite) return;
    setSubmitting(true);
    setErr(null);
    setResult(null);
    try {
      await registrations.create({ website_id: selectedWebsite, count, priority });
      setResult(`Queued ${count} registration(s)`);
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Failed");
    } finally {
      setSubmitting(false);
    }
  };

  const inputClasses = "w-full rounded-xl border border-gray-700/60 bg-gray-800/80 px-4 py-2.5 text-sm text-white transition-all focus:border-blue-600/60 focus:outline-none focus:ring-1 focus:ring-blue-600/30";

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          <span className="text-gradient">Registrations</span>
        </h1>
        <p className="mt-1 text-sm text-gray-500">Queue new registration tasks</p>
      </div>

      <Card glow="blue" className="max-w-lg">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base font-semibold text-gray-300">
            <div className="rounded-lg bg-blue-500/10 p-2">
              <Rocket className="h-4 w-4 text-blue-400" />
            </div>
            Start Registrations
          </CardTitle>
        </CardHeader>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-400">Website</label>
            <select
              required
              value={selectedWebsite ?? ""}
              onChange={(e) => setSelectedWebsite(Number(e.target.value))}
              className={inputClasses}
            >
              <option value="" disabled>Select a website</option>
              {siteList?.items.map((w) => (
                <option key={w.id} value={w.id}>{w.name} ({w.domain})</option>
              ))}
            </select>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-400">Count</label>
              <input
                type="number"
                min={1}
                max={1000}
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
                className={inputClasses}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-400">Priority</label>
              <select value={priority} onChange={(e) => setPriority(e.target.value)} className={inputClasses}>
                <option value="high">High</option>
                <option value="normal">Normal</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>

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
