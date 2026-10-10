export type Role = "customer" | "agent";
export type Status = "opened" | "evidence_submitted" | "under_review" | "resolved";

export interface Session { access_token: string; email: string; role: Role }

export interface Dispute {
  id: number;
  customer_id: number;
  customer_email: string;
  order_ref: string;
  amount_cents: number;
  reason: string;
  status: Status;
  resolution: "refund" | "reject" | null;
  resolution_note: string | null;
  created_at: string;
  updated_at: string;
}
export interface Evidence { id: number; submitted_by: number; description: string; created_at: string }
export interface AuditEntry {
  id: number; action: string; from_status: string | null; to_status: string;
  note: string | null; actor_email: string; actor_role: Role; created_at: string;
}
export interface Refund { id: number; amount_cents: number; created_at: string }
export interface DisputeDetail extends Dispute {
  evidence: Evidence[];
  audit_logs: AuditEntry[];
  refund: Refund | null;
}
export interface DisputeList { items: Dispute[]; total: number }
