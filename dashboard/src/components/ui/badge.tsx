import { statusBadgeClasses } from "@/lib/utils";

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={statusBadgeClasses(status)}>
      {status.replace(/_/g, " ")}
    </span>
  );
}
