"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { useFetch } from "@/hooks/use-fetch";
import { monitoring } from "@/lib/api";
import { Camera, X } from "lucide-react";
import { useState } from "react";

export default function ScreenshotsPage() {
  const { data, loading, error } = useFetch(
    () => monitoring.screenshots({ limit: 50 }),
    [],
  );
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          <span className="text-gradient">Screenshots</span>
        </h1>
        <p className="mt-1 text-sm text-gray-500">Failure screenshots for debugging</p>
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
              <div className="relative aspect-video overflow-hidden bg-gray-800/50">
                <img
                  src={ss.screenshot_path}
                  alt={`Registration #${ss.registration_id}`}
                  className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-gray-950/80 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
              </div>
              <div className="p-4">
                <p className="text-sm font-medium text-gray-300 truncate">Registration #{ss.registration_id}</p>
                <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                  <span>{ss.status}</span>
                  <span>·</span>
                  <span>{ss.created_at ?? "—"}</span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in" onClick={() => setSelected(null)}>
          <div className="relative max-h-[90vh] max-w-[90vw] animate-fade-in-up">
            <button onClick={() => setSelected(null)} className="absolute -right-3 -top-3 rounded-full bg-gray-800 p-2 text-gray-400 shadow-lg transition-colors hover:bg-gray-700 hover:text-white">
              <X className="h-4 w-4" />
            </button>
            <img src={selected} alt="Screenshot" className="max-h-[85vh] rounded-xl border border-gray-700 shadow-2xl" />
          </div>
        </div>
      )}
    </div>
  );
}
