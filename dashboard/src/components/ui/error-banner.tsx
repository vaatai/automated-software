import { AlertTriangle } from "lucide-react";

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="animate-fade-in-up flex items-center gap-3 rounded-xl border border-red-900/40 bg-gradient-to-r from-red-900/20 to-red-900/10 px-4 py-3 text-sm text-red-400 shadow-lg shadow-red-900/10">
      <div className="rounded-lg bg-red-500/10 p-1.5">
        <AlertTriangle className="h-4 w-4" />
      </div>
      <span>{message}</span>
    </div>
  );
}
