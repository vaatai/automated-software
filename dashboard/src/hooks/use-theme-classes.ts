"use client";

import { useTheme } from "@/contexts/theme-context";

export function useThemeClasses() {
  const { theme } = useTheme();
  const dark = theme === "dark";

  return {
    dark,
    heading: dark ? "text-white" : "text-slate-900",
    subtext: dark ? "text-gray-500" : "text-slate-400",
    label: dark ? "text-gray-400" : "text-slate-500",
    value: dark ? "text-white" : "text-slate-900",
    muted: dark ? "text-gray-500" : "text-slate-400",
    tableRow: dark
      ? "border-b border-gray-800/30 transition-colors hover:bg-gray-800/30"
      : "border-b border-slate-100 transition-colors hover:bg-slate-50",
    tableBorder: dark ? "border-gray-800/60" : "border-slate-200",
    tableHead: dark ? "text-gray-500" : "text-slate-400",
    inputCls: dark
      ? "w-full rounded-xl border border-gray-700/60 bg-gray-800/80 px-4 py-2.5 text-sm text-white transition-all focus:border-blue-600/60 focus:outline-none focus:ring-1 focus:ring-blue-600/30"
      : "w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 transition-all focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/30",
    badge: (color: string) => {
      if (dark) {
        return `bg-${color}-500/10 text-${color}-400`;
      }
      return `bg-${color}-50 text-${color}-600`;
    },
  };
}
