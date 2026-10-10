import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Empty, ErrorBox, Loading } from "../components/States";
import StatusBadge from "../components/StatusBadge";
import { dateTime, money, STATUS_LABEL } from "../format";
import type { Dispute, Status } from "../types";

const FILTERS: (Status | "")[] = ["", "opened", "evidence_submitted", "under_review", "resolved"];

export default function DisputesList() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<Status | "">("");
  const [items, setItems] = useState<Dispute[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const reload = useCallback(() => setReloadTick((n) => n + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const timer = setTimeout(async () => { // debounce typing in the search box
      try {
        const res = await api.listDisputes({ status, q: q.trim() });
        if (!cancelled) { setItems(res.items); setTotal(res.total); }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 250);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [q, status, reloadTick]);

  return (
    <>
      <div className="row between">
        <h1>{session?.role === "agent" ? "All disputes" : "My disputes"}</h1>
        {session?.role === "customer" && <NewDispute onCreated={reload} />}
      </div>

      <div className="toolbar">
        <input type="search" placeholder="Search by order, customer, reason or ID" value={q}
               onChange={(e) => setQ(e.target.value)} aria-label="Search disputes" />
        <div className="chips" role="group" aria-label="Filter by status">
          {FILTERS.map((f) => (
            <button key={f || "all"} className={status === f ? "chip active" : "chip"} onClick={() => setStatus(f)}>
              {f ? STATUS_LABEL[f] : "All"}
            </button>
          ))}
        </div>
      </div>

      {loading ? <Loading text="Loading disputes…" />
        : error ? <ErrorBox message={error} onRetry={reload} />
        : items.length === 0 ? <Empty>{q || status ? "No disputes match these filters." : "No disputes yet."}</Empty>
        : (
          <>
            <div className="table-wrap">
              <table>
                <thead><tr><th>ID</th><th>Order</th><th>Customer</th><th className="num">Amount</th><th>Status</th><th>Opened</th></tr></thead>
                <tbody>
                  {items.map((d) => (
                    <tr key={d.id} tabIndex={0} onClick={() => navigate(`/disputes/${d.id}`)}
                        onKeyDown={(e) => e.key === "Enter" && navigate(`/disputes/${d.id}`)}>
                      <td>#{d.id}</td><td>{d.order_ref}</td><td>{d.customer_email}</td>
                      <td className="num">{money(d.amount_cents)}</td>
                      <td><StatusBadge d={d} /></td><td>{dateTime(d.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="hint">Showing {items.length} of {total}</p>
          </>
        )}
    </>
  );
}

function NewDispute({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [order, setOrder] = useState("");
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.createDispute({ order_ref: order, amount_cents: Math.round(parseFloat(amount) * 100), reason });
      setOpen(false); setOrder(""); setAmount(""); setReason("");
      onCreated();
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  if (!open) return <button className="primary" onClick={() => setOpen(true)}>Open a dispute</button>;
  return (
    <form className="panel inline-form" onSubmit={submit}>
      <label>Order reference<input value={order} onChange={(e) => setOrder(e.target.value)} required /></label>
      <label>Amount (EUR)<input type="number" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required /></label>
      <label>What went wrong?<input value={reason} onChange={(e) => setReason(e.target.value)} required minLength={3} /></label>
      {error && <p className="inline-error" role="alert">{error}</p>}
      <div className="row"><button className="primary" disabled={busy}>{busy ? "Opening…" : "Open dispute"}</button>
        <button type="button" className="ghost" onClick={() => setOpen(false)}>Cancel</button></div>
    </form>
  );
}
