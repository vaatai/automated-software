"use client";

import { StatusBadge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";
import { useFetch } from "@/hooks/use-fetch";
import { useThemeClasses } from "@/hooks/use-theme-classes";
import { websites, type WebsiteCreatePayload } from "@/lib/api";
import { Globe, Plus, Search, Trash2, X } from "lucide-react";
import { useState } from "react";

export default function WebsitesPage() {
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const limit = 20;
  const tc = useThemeClasses();

  const { data, loading, error, refetch } = useFetch(
    () => websites.list({ limit, offset, search: search || undefined }),
    [offset, search],
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            <span className="text-gradient">Websites</span>
          </h1>
          <p className={`mt-1 text-sm ${tc.subtext}`}>Manage target websites for registration</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="group flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 px-5 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-blue-500/30 w-full sm:w-auto"
        >
          <Plus className="h-4 w-4 transition-transform group-hover:rotate-90" /> Add Website
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className={`absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 ${tc.muted}`} />
        <input
          type="text"
          placeholder="Search websites..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
          className={`pl-10 pr-4 ${tc.inputCls}`}
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
                <tr className={`border-b ${tc.tableBorder}`}>
                  <th className={`px-3 sm:px-6 py-3.5 text-xs font-semibold uppercase tracking-wider ${tc.tableHead}`}>Name</th>
                  <th className={`hidden sm:table-cell px-3 sm:px-6 py-3.5 text-xs font-semibold uppercase tracking-wider ${tc.tableHead}`}>Domain</th>
                  <th className={`px-3 sm:px-6 py-3.5 text-xs font-semibold uppercase tracking-wider ${tc.tableHead}`}>Status</th>
                  <th className={`hidden sm:table-cell px-3 sm:px-6 py-3.5 text-xs font-semibold uppercase tracking-wider ${tc.tableHead}`}>Daily Limit</th>
                  <th className={`px-3 sm:px-6 py-3.5 text-xs font-semibold uppercase tracking-wider ${tc.tableHead}`}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((w) => (
                  <tr key={w.id} className={tc.tableRow}>
                    <td className={`px-3 sm:px-6 py-4 font-medium ${tc.heading}`}>{w.name}</td>
                    <td className={`hidden sm:table-cell px-3 sm:px-6 py-4 ${tc.label} truncate max-w-[200px]`}>{w.domain || w.url}</td>
                    <td className="px-3 sm:px-6 py-4"><StatusBadge status={w.status} /></td>
                    <td className={`hidden sm:table-cell px-3 sm:px-6 py-4 font-mono text-sm ${tc.label}`}>{w.max_registrations_per_day}</td>
                    <td className="px-3 sm:px-6 py-4">
                      <button
                        onClick={async () => {
                          if (confirm("Delete this website?")) {
                            await websites.delete(w.id);
                            refetch();
                          }
                        }}
                        className={`rounded-lg p-2 transition-all hover:bg-red-500/10 hover:text-red-400 ${tc.muted}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-3 sm:px-6 pb-4">
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
  const [name, setName] = useState("");
  const [registrationUrl, setRegistrationUrl] = useState("");
  const [dailyLimit, setDailyLimit] = useState(100);
  const [requiresEmailOtp, setRequiresEmailOtp] = useState(false);
  const [requiresMobileOtp, setRequiresMobileOtp] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");
  const tc = useThemeClasses();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErr("");
    try {
      const payload: WebsiteCreatePayload = {
        name,
        url: registrationUrl,
        form_config: {
          registration_url: registrationUrl,
          steps: [{ step_name: "Registration", fields: {}, submit_button: { selector: "button[type=submit]" } }],
        },
        requires_email_otp: requiresEmailOtp,
        requires_mobile_otp: requiresMobileOtp,
        max_registrations_per_day: dailyLimit,
      };
      await websites.create(payload);
      onCreated();
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Failed to create");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-fade-in p-4">
      <div className={`w-full max-w-md max-h-[90vh] overflow-y-auto rounded-2xl border p-6 shadow-2xl animate-fade-in-up ${
        tc.dark
          ? "border-gray-800/60 bg-gray-900/95"
          : "border-slate-200 bg-white"
      }`}>
        <div className="mb-5 flex items-center justify-between">
          <h2 className={`text-lg font-bold ${tc.heading}`}>Add Website</h2>
          <button onClick={onClose} className={`rounded-lg p-1.5 transition-colors ${
            tc.dark ? "text-gray-400 hover:bg-gray-800 hover:text-white" : "text-slate-400 hover:bg-slate-100 hover:text-slate-900"
          }`}>
            <X className="h-5 w-5" />
          </button>
        </div>
        {err && <div className="mb-4"><ErrorBanner message={err} /></div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={`mb-1.5 block text-sm font-medium ${tc.label}`}>Name</label>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={tc.inputCls}
              placeholder="My Website"
            />
          </div>
          <div>
            <label className={`mb-1.5 block text-sm font-medium ${tc.label}`}>Registration URL</label>
            <input
              required
              type="url"
              value={registrationUrl}
              onChange={(e) => setRegistrationUrl(e.target.value)}
              className={tc.inputCls}
              placeholder="https://example.com/register"
            />
          </div>
          <div>
            <label className={`mb-1.5 block text-sm font-medium ${tc.label}`}>Daily Limit</label>
            <input
              type="number"
              min={1}
              value={dailyLimit}
              onChange={(e) => setDailyLimit(Number(e.target.value))}
              className={tc.inputCls}
            />
          </div>

          {/* OTP Options */}
          <div className="space-y-3">
            <label className={`block text-sm font-medium ${tc.label}`}>Verification Options</label>
            <label className={`flex items-center gap-3 rounded-xl border px-4 py-3 cursor-pointer transition-colors ${
              tc.dark
                ? "border-gray-700 hover:bg-gray-800/40"
                : "border-slate-200 hover:bg-slate-50"
            }`}>
              <input type="checkbox" checked={requiresEmailOtp} onChange={(e) => setRequiresEmailOtp(e.target.checked)}
                className="h-4 w-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500" />
              <div>
                <span className={`text-sm font-medium ${tc.heading}`}>Email OTP</span>
                <p className={`text-xs ${tc.muted}`}>Verify via email code (MailSlurp)</p>
              </div>
            </label>
            <label className={`flex items-center gap-3 rounded-xl border px-4 py-3 cursor-pointer transition-colors ${
              tc.dark
                ? "border-gray-700 hover:bg-gray-800/40"
                : "border-slate-200 hover:bg-slate-50"
            }`}>
              <input type="checkbox" checked={requiresMobileOtp} onChange={(e) => setRequiresMobileOtp(e.target.checked)}
                className="h-4 w-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500" />
              <div>
                <span className={`text-sm font-medium ${tc.heading}`}>Mobile OTP</span>
                <p className={`text-xs ${tc.muted}`}>Verify via SMS code (5SIM/PVAPins)</p>
              </div>
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className={`rounded-xl px-5 py-2.5 text-sm transition-colors ${
              tc.dark ? "text-gray-400 hover:bg-gray-800 hover:text-white" : "text-slate-400 hover:bg-slate-100 hover:text-slate-900"
            }`}>
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
