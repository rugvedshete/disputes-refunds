import { STATUS_LABEL } from "../format";
import type { Dispute } from "../types";

export default function StatusBadge({ d }: { d: Pick<Dispute, "status" | "resolution"> }) {
  const label = d.status === "resolved" && d.resolution
    ? d.resolution === "refund" ? "Refunded" : "Rejected"
    : STATUS_LABEL[d.status];
  const tone = d.status === "resolved" ? d.resolution ?? "resolved" : d.status;
  return <span className={`badge badge-${tone}`}>{label}</span>;
}
