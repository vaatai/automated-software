import clsx, { type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatNumber(n: number): string {
  return new Intl.NumberFormat("en-US").format(n);
}

export function formatPct(n: number): string {
  return `${n.toFixed(1)}%`;
}

export function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function statusColor(status: string): string {
  switch (status.toLowerCase()) {
    case "completed": return "text-emerald-400";
    case "failed": return "text-red-400";
    case "in_progress": return "text-blue-400";
    case "pending": return "text-yellow-400";
    case "cancelled": return "text-gray-400";
    case "daily_limit_reached": return "text-orange-400";
    case "email_otp_pending":
    case "mobile_otp_pending": return "text-purple-400";
    default: return "text-gray-400";
  }
}

export function statusBadgeClasses(status: string): string {
  const base = "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium";
  switch (status.toLowerCase()) {
    case "completed": return `${base} bg-emerald-400/10 text-emerald-400`;
    case "failed": return `${base} bg-red-400/10 text-red-400`;
    case "in_progress": return `${base} bg-blue-400/10 text-blue-400`;
    case "pending": return `${base} bg-yellow-400/10 text-yellow-400`;
    case "cancelled": return `${base} bg-gray-400/10 text-gray-400`;
    default: return `${base} bg-gray-400/10 text-gray-400`;
  }
}

export function levelColor(level: string): string {
  switch (level.toUpperCase()) {
    case "ERROR":
    case "CRITICAL": return "text-red-400";
    case "WARNING": return "text-yellow-400";
    case "INFO": return "text-blue-400";
    case "DEBUG": return "text-gray-400";
    default: return "text-gray-400";
  }
}
