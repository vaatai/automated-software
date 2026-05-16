"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { useFetch } from "@/hooks/use-fetch";
import { registrations, websites } from "@/lib/api";
import { Play } from "lucide-react";
import { useState } from "react";

export default function RegistrationsPage() {
  const { data: siteList, loading } = useFetch(() => websites.list({ limit: 200 }), []);
  const [websiteId, setWebsiteId] = useState<number | "">("");
  const [count, setCount] = useState(1);
  const [priority, setPriority] = useState("normal");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!websiteId) return;
    setSubmitting(true);
    setResult(null);
    setErr(null);
    try {
      await registrations.create({ website_id: Number(websiteId), count, priority });
      setResult(`Queued ${count} registration(s) for website #${websiteId}`);
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Failed to queue");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Trigger Registrations</h1>

      <Card className="max-w-lg">
        <CardHeader>
          <CardTitle>Queue New Registrations</CardTitle>
        </CardHeader>

        {loading && <Spinner />}

        {!loading && (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm text-gray-400">Website</label>
              <select
                required
                value={websiteId}
                onChange={(e) => setWebsiteId(e.target.value ? Number(e.target.value) : "")}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white focus:border-blue-600 focus:outline-none"
              >
                <option value="">Select website...</option>
                {siteList?.items.map((w) => (
                  <option key={w.id} value={w.id}>{w.name} ({w.domain})</option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm text-gray-400">Count</label>
              <input
                type="number"
                min={1}
                max={500}
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white focus:border-blue-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm text-gray-400">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white focus:border-blue-600 focus:outline-none"
              >
                <option value="high">High</option>
                <option value="normal">Normal</option>
                <option value="low">Low</option>
              </select>
            </div>

            {result && (
              <div className="rounded-lg border border-emerald-900/50 bg-emerald-900/20 px-4 py-3 text-sm text-emerald-400">
                {result}
              </div>
            )}
            {err && <ErrorBanner message={err} />}

            <button
              type="submit"
              disabled={submitting || !websiteId}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              {submitting ? "Queuing..." : "Start Registrations"}
            </button>
          </form>
        )}
      </Card>
    </div>
  );
}
