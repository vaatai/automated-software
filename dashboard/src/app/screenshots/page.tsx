"use client";

import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { useFetch } from "@/hooks/use-fetch";
import { useThemeClasses } from "@/hooks/use-theme-classes";
import { monitoring } from "@/lib/api";
import { Camera, X } from "lucide-react";
import { useState } from "react";

export default function ScreenshotsPage() {
  const { data, loading, error } = useFetch(
    () => monitoring.screenshots({ limit: 50 }),
    [],
  );
  const [selected, setSelected] = useState<string | null>(null);
  const tc = useThemeClasses();

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          <span className="text-gradient">Screenshots</span>
        </h1>
        <p className={`mt-1 text-sm ${tc.subtext}`}>Failure screenshots for debugging</p>
      </div>

      {error && <ErrorBanner message={error} />}
      {loading && !data && <Spinner />}

      {data && data.items.length === 0 && (
        <EmptyState icon={Camera} title="No screenshots" description="Screenshots are captured when registration tasks fail" />
      )}

      {data && data.items.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {data.items.map((ss, i) => (
            <Card key={i} className="group cursor-pointer overflow-hidden p-0 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl" onClick={() => setSelected(ss.screenshot_path)}>
              <div className={`relative aspect-video overflow-hidden ${tc.dark ? "bg-gray-800/50" : "bg-slate-100"}`}>
                <img
                  src={ss.screenshot_path}
                  alt={`Registration #${ss.registration_id}`}
                  className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                  loading="lazy"
                />
                <div className={`absolute inset-0 bg-gradient-to-t opacity-0 transition-opacity group-hover:opacity-100 ${
                  tc.dark ? "from-gray-950/80 to-transparent" : "from-slate-900/60 to-transparent"
                }`} />
              </div>
              <div className="p-4">
                <p className={`text-sm font-medium truncate ${tc.dark ? "text-gray-300" : "text-slate-700"}`}>Registration #{ss.registration_id}</p>
                <div className={`mt-1 flex items-center gap-2 text-xs ${tc.muted}`}>
                  <span>{ss.status}</span>
                  <span>&middot;</span>
                  <span>{ss.created_at ?? "\u2014"}</span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in" onClick={() => setSelected(null)}>
          <div className="relative max-h-[90vh] max-w-[90vw] animate-fade-in-up">
            <button onClick={() => setSelected(null)} className={`absolute -right-3 -top-3 rounded-full p-2 shadow-lg transition-colors ${
              tc.dark ? "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white" : "bg-white text-slate-400 hover:bg-slate-50 hover:text-slate-900"
            }`}>
              <X className="h-4 w-4" />
            </button>
            <img src={selected} alt="Screenshot" className={`max-h-[85vh] rounded-xl border shadow-2xl ${tc.dark ? "border-gray-700" : "border-slate-200"}`} />
          </div>
        </div>
      )}
    </div>
  );
}
