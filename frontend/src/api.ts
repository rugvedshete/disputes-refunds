import type { DisputeDetail, DisputeList, Refund, Session, Status } from "./types";

const BASE = "/api";
const KEY = "session";

export const loadSession = (): Session | null => {
  try { return JSON.parse(localStorage.getItem(KEY) ?? "null"); } catch { return null; }
};
export const saveSession = (s: Session | null) =>
  s ? localStorage.setItem(KEY, JSON.stringify(s)) : localStorage.removeItem(KEY);

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function request<T>(path: string, opts: { method?: string; body?: unknown; headers?: Record<string, string> } = {}): Promise<T> {
  const token = loadSession()?.access_token;
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      method: opts.method ?? "GET",
      headers: {
        ...(opts.body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...opts.headers,
      },
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Check your connection and try again.");
  }
  if (res.status === 401 && token) window.dispatchEvent(new Event("auth:expired"));
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) message = data.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch { /* keep default */ }
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) => request<Session>("/auth/login", { method: "POST", body: { email, password } }),
  listDisputes: (p: { status?: Status | ""; q?: string }) => {
    const qs = new URLSearchParams();
    if (p.status) qs.set("status", p.status);
    if (p.q) qs.set("q", p.q);
    return request<DisputeList>(`/disputes?${qs}`);
  },
  getDispute: (id: string) => request<DisputeDetail>(`/disputes/${id}`),
  createDispute: (body: { order_ref: string; amount_cents: number; reason: string }) =>
    request<unknown>("/disputes", { method: "POST", body }),
  addEvidence: (id: number, description: string) =>
    request<DisputeDetail>(`/disputes/${id}/evidence`, { method: "POST", body: { description } }),
  startReview: (id: number) => request<DisputeDetail>(`/disputes/${id}/review`, { method: "POST" }),
  // The Idempotency-Key makes a retried or double-clicked refund safe.
  refund: (id: number, key: string) =>
    request<Refund>(`/disputes/${id}/refund`, { method: "POST", headers: { "Idempotency-Key": key } }),
  reject: (id: number, note: string) =>
    request<DisputeDetail>(`/disputes/${id}/reject`, { method: "POST", body: { note } }),
};
