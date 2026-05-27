"use client";

import { useState } from "react";
import { Trash2, Bell } from "lucide-react";
import { createAlert, deleteAlert } from "@/lib/api";
import { useAlerts, useBillingStatus } from "@/lib/hooks";

export function PriceAlerts() {
  const { isPro, loading: tierLoading } = useBillingStatus(true);
  const { alerts, loading, mutate } = useAlerts(isPro);

  const [symbol, setSymbol] = useState("");
  const [condition, setCondition] = useState<"above" | "below">("above");
  const [target, setTarget] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (tierLoading) return null;

  if (!isPro) {
    return (
      <section className="border border-b7-green-border p-3">
        <h2 className="text-b7-green uppercase text-sm mb-2">{`> PRICE ALERTS`}</h2>
        <p className="text-b7-green-muted text-xs">
          {`> Pro feature — upgrade to set price alerts and get email notifications.`}
        </p>
        <a
          href="/#pricing"
          className="inline-block mt-2 text-xs text-b7-green border border-b7-green-border px-3 py-1 hover:bg-b7-green/10 transition uppercase"
        >
          Upgrade to Pro →
        </a>
      </section>
    );
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const sym = symbol.trim().toUpperCase();
    const tgt = parseFloat(target);
    if (!sym || !Number.isFinite(tgt) || tgt <= 0) {
      setError("Enter a valid symbol and price.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createAlert(sym, condition, tgt);
      setSymbol("");
      setTarget("");
      mutate();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create alert");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteAlert(id);
      mutate();
    } catch {
      /* ignore */
    }
  }

  const active = alerts.filter((a) => !a.triggered);
  const triggered = alerts.filter((a) => a.triggered);

  return (
    <section className="border border-b7-green-border p-3 space-y-3">
      <h2 className="text-b7-green uppercase text-sm flex items-center gap-2">
        <Bell size={14} aria-hidden="true" />
        {`> PRICE ALERTS`}
        <span className="text-b7-green-muted text-xs font-normal">
          ({active.length}/10 active)
        </span>
      </h2>

      {/* Create form */}
      <form onSubmit={handleCreate} className="flex flex-wrap gap-2 items-end">
        <div className="flex flex-col gap-1">
          <label className="text-b7-green-muted text-xs uppercase">Symbol</label>
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            placeholder="NVDA"
            maxLength={10}
            className="bg-black border border-b7-green-border text-b7-green text-xs px-2 py-1 w-24 uppercase placeholder:text-b7-green-muted/50 focus:outline-none focus:ring-1 focus:ring-b7-green"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-b7-green-muted text-xs uppercase">Condition</label>
          <select
            value={condition}
            onChange={(e) => setCondition(e.target.value as "above" | "below")}
            className="bg-black border border-b7-green-border text-b7-green text-xs px-2 py-1 focus:outline-none focus:ring-1 focus:ring-b7-green"
          >
            <option value="above">Above</option>
            <option value="below">Below</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-b7-green-muted text-xs uppercase">Price ($)</label>
          <input
            type="number"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="500.00"
            step="0.01"
            min="0.01"
            className="bg-black border border-b7-green-border text-b7-green text-xs px-2 py-1 w-28 focus:outline-none focus:ring-1 focus:ring-b7-green"
          />
        </div>
        <button
          type="submit"
          disabled={saving}
          className="px-3 py-1 border border-b7-green text-b7-green hover:bg-b7-green/10 transition text-xs uppercase disabled:opacity-50"
        >
          {saving ? "Adding…" : "+ Add Alert"}
        </button>
      </form>

      {error && (
        <p className="text-red-400 text-xs">{`! ${error}`}</p>
      )}

      {/* Active alerts */}
      {loading ? (
        <div className="text-b7-green-muted text-xs">Loading alerts…</div>
      ) : active.length === 0 ? (
        <div className="text-b7-green-muted text-xs">{`> No active alerts`}</div>
      ) : (
        <ul className="space-y-1">
          {active.map((alert) => (
            <li
              key={alert.id}
              className="flex items-center justify-between border border-b7-green-border/40 px-2 py-1 text-xs"
            >
              <span className="text-b7-green font-bold">{alert.symbol}</span>
              <span className="text-b7-green-dim mx-2">
                {alert.condition === "above" ? "▲ above" : "▼ below"} ${alert.target.toFixed(2)}
              </span>
              <button
                type="button"
                onClick={() => handleDelete(alert.id)}
                className="text-b7-green-muted hover:text-red-400 transition"
                aria-label={`Delete alert for ${alert.symbol}`}
              >
                <Trash2 size={12} />
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Triggered alerts (history) */}
      {triggered.length > 0 && (
        <div className="space-y-1">
          <div className="text-b7-green-muted text-xs uppercase">Triggered</div>
          {triggered.map((alert) => (
            <div
              key={alert.id}
              className="flex items-center justify-between px-2 py-1 text-xs opacity-60 border border-b7-green-border/20"
            >
              <span className="line-through text-b7-green-muted">{alert.symbol}</span>
              <span className="text-b7-green-muted mx-2">
                {alert.condition === "above" ? "▲" : "▼"} ${alert.target.toFixed(2)} ✓ triggered
              </span>
              <button
                type="button"
                onClick={() => handleDelete(alert.id)}
                className="text-b7-green-muted hover:text-red-400 transition"
                aria-label={`Remove triggered alert for ${alert.symbol}`}
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
