import type { AssetStatus } from "../types/railsight";

interface StatusBadgeProps {
  status: AssetStatus;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`status-badge status-${status}`}>{status}</span>;
}
