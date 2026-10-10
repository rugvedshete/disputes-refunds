import type { Status } from "./types";

export const money = (cents: number) =>
  (cents / 100).toLocaleString("es-ES", { style: "currency", currency: "EUR" });

export const dateTime = (iso: string) =>
  new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });

export const STATUS_LABEL: Record<Status, string> = {
  opened: "Opened",
  evidence_submitted: "Evidence submitted",
  under_review: "Under review",
  resolved: "Resolved",
};

export const ACTION_LABEL: Record<string, string> = {
  opened: "Dispute opened",
  evidence_submitted: "Evidence submitted",
  evidence_added: "More evidence added",
  review_started: "Review started",
  refund_approved: "Refund approved",
  rejected: "Dispute rejected",
};

export const newKey = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}-key`;
