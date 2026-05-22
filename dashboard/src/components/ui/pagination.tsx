"use client";

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
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.ceil(total / limit);

  if (pages <= 1) return null;

  return (
    <div className="flex items-center justify-between border-t border-gray-800/60 px-2 pt-4">
      <p className="text-xs text-gray-500">
        {offset + 1}–{Math.min(offset + limit, total)} of {total}
      </p>
      <div className="flex gap-1">
        <button
          onClick={() => onChange(Math.max(0, offset - limit))}
          disabled={page === 1}
          className="rounded-lg p-1.5 text-gray-400 transition-all hover:bg-gray-800/60 hover:text-white disabled:opacity-30"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="flex items-center px-2 text-xs text-gray-500">
          {page} / {pages}
        </span>
        <button
          onClick={() => onChange(offset + limit)}
          disabled={page >= pages}
          className="rounded-lg p-1.5 text-gray-400 transition-all hover:bg-gray-800/60 hover:text-white disabled:opacity-30"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
