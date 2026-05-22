import { statusBadgeClasses } from "@/lib/utils";

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={statusBadgeClasses(status)}>
      <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {status.replace(/_/g, " ")}
    </span>
  );
}
