import type { LucideIcon } from "lucide-react";

export function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
}) {
  return (
    <div className="animate-fade-in flex flex-col items-center justify-center py-16 text-center">
      <div className="animate-float mb-4 rounded-2xl bg-gradient-to-br from-gray-800/80 to-gray-900/80 p-5">
        <Icon className="h-10 w-10 text-gray-500" />
      </div>
      <p className="text-sm font-medium text-gray-400">{title}</p>
      {description && (
        <p className="mt-1.5 max-w-xs text-xs text-gray-500">{description}</p>
      )}
    </div>
  );
}
