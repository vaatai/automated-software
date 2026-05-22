"use client";

import { StatusBadge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";
import { useFetch } from "@/hooks/use-fetch";
import { websites, type WebsiteCreatePayload } from "@/lib/api";
import { Globe, Plus, Search, Trash2, X } from "lucide-react";
import { useState } from "react";

export default function WebsitesPage() {
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const limit = 20;

  const { data, loading, error, refetch } = useFetch(
    () => websites.list({ limit, offset, search: search || undefined }),
    [offset, search],
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            <span className="text-gradient">Websites</span>
          </h1>
          <p className="mt-1 text-sm text-gray-500">Manage target websites for registration</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="group flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 px-5 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-blue-500/30"
        >
          <Plus className="h-4 w-4 transition-transform group-hover:rotate-90" /> Add Website
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
        <input
          type="text"
          placeholder="Search websites..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
          className="w-full rounded-xl border border-gray-800/60 bg-gray-900/80 py-2.5 pl-10 pr-4 text-sm text-white placeholder-gray-500 shadow-sm transition-all focus:border-blue-600/60 focus:outline-none focus:ring-1 focus:ring-blue-600/30"
        />
      </div>

      {error && <ErrorBanner message={error} />}
      {loading && !data && <Spinner />}

      {data && data.items.length === 0 && (
        <EmptyState icon={Globe} title="No websites found" description="Add your first website to get started" />
      )}

      {data && data.items.length > 0 && (
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-800/60">
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Name</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Domain</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Status</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Daily Limit</th>
                  <th className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((w) => (
                  <tr key={w.id} className="border-b border-gray-800/30 transition-colors hover:bg-gray-800/30">
                    <td className="px-6 py-4 font-medium text-white">{w.name}</td>
                    <td className="px-6 py-4 text-gray-400">{w.domain}</td>
                    <td className="px-6 py-4"><StatusBadge status={w.status} /></td>
                    <td className="px-6 py-4 font-mono text-sm text-gray-400">{w.max_registrations_per_day}</td>
                    <td className="px-6 py-4">
                      <button
                        onClick={async () => {
                          if (confirm("Delete this website?")) {
                            await websites.delete(w.id);
                            refetch();
                          }
                        }}
                        className="rounded-lg p-2 text-gray-500 transition-all hover:bg-red-500/10 hover:text-red-400"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-6 pb-4">
            <Pagination total={data.total} limit={limit} offset={offset} onChange={setOffset} />
          </div>
        </Card>
      )}

      {showCreate && (
        <CreateWebsiteModal
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); refetch(); }}
        />
      )}
    </div>
  );
}

function CreateWebsiteModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState<WebsiteCreatePayload>({
    name: "",
    domain: "",
    registration_url: "",
    max_registrations_per_day: 100,
  });
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErr("");
    try {
      await websites.create(form);
      onCreated();
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Failed to create");
    } finally {
      setSubmitting(false);
    }
  };

  const inputClasses = "w-full rounded-xl border border-gray-700/60 bg-gray-800/80 px-4 py-2.5 text-sm text-white transition-all focus:border-blue-600/60 focus:outline-none focus:ring-1 focus:ring-blue-600/30";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md rounded-2xl border border-gray-800/60 bg-gray-900/95 p-6 shadow-2xl animate-fade-in-up">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">Add Website</h2>
          <button onClick={onClose} className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-800 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>
        {err && <div className="mb-4"><ErrorBanner message={err} /></div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-400">Name</label>
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className={inputClasses}
              placeholder="My Website"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-400">Domain</label>
            <input
              required
              value={form.domain}
              onChange={(e) => setForm({ ...form, domain: e.target.value })}
              className={inputClasses}
              placeholder="example.com"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-400">Registration URL</label>
            <input
              required
              type="url"
              value={form.registration_url}
              onChange={(e) => setForm({ ...form, registration_url: e.target.value })}
              className={inputClasses}
              placeholder="https://example.com/register"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-400">Daily Limit</label>
            <input
              type="number"
              min={1}
              value={form.max_registrations_per_day}
              onChange={(e) => setForm({ ...form, max_registrations_per_day: Number(e.target.value) })}
              className={inputClasses}
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-xl px-5 py-2.5 text-sm text-gray-400 transition-colors hover:bg-gray-800 hover:text-white">
              Cancel
            </button>
            <button type="submit" disabled={submitting} className="rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 px-5 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition-all hover:shadow-xl disabled:opacity-50">
              {submitting ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
