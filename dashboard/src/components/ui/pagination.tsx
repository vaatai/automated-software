"use client";

import { useTheme } from "@/contexts/theme-context";
import { cn } from "@/lib/utils";
import { ChevronLeft, ChevronRight } from "lucide-react";

export function Pagination({
  total,
  limit,
  offset,
  onChange,
}: {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
}) {
  const { theme } = useTheme();
  const dark = theme === "dark";
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.ceil(total / limit);

  if (pages <= 1) return null;

  const btnCls = cn(
    "rounded-lg p-1.5 transition-all disabled:opacity-30",
    dark
      ? "text-gray-400 hover:bg-gray-800/60 hover:text-white"
      : "text-slate-400 hover:bg-slate-100 hover:text-slate-900",
  );

  return (
    <div className={cn(
      "flex items-center justify-between border-t px-2 pt-4",
      dark ? "border-gray-800/60" : "border-slate-200",
    )}>
      <p className={cn("text-xs", dark ? "text-gray-500" : "text-slate-400")}>
        {offset + 1}–{Math.min(offset + limit, total)} of {total}
      </p>
      <div className="flex gap-1">
        <button onClick={() => onChange(Math.max(0, offset - limit))} disabled={page === 1} className={btnCls}>
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className={cn("flex items-center px-2 text-xs", dark ? "text-gray-500" : "text-slate-400")}>
          {page} / {pages}
        </span>
        <button onClick={() => onChange(offset + limit)} disabled={page >= pages} className={btnCls}>
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
