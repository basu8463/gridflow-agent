"use client";

import { useEffect, useMemo, useState } from "react";
import { CaseRecord, getCases, reviewCase } from "@/lib/api";

const FILTERS = [
  { id: "all", label: "All" },
  { id: "pending_review", label: "Needs review" },
  { id: "auto_approved", label: "Auto-approved" },
  { id: "approved", label: "Approved" },
  { id: "rejected", label: "Rejected" },
  { id: "needs_more_info", label: "More info" },
] as const;

function statusClass(status?: string) {
  switch (status) {
    case "approved":
    case "auto_approved":
      return "bg-teal/10 text-teal";
    case "rejected":
      return "bg-red-50 text-red-700";
    case "pending_review":
      return "bg-amber-50 text-amber-800";
    default:
      return "bg-sand text-navy";
  }
}

function when(ts?: number | null) {
  if (!ts) return "";
  return new Date(ts * 1000).toLocaleString();
}

export default function QueuePage() {
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function refresh() {
    try {
      setCases(await getCases());
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: cases.length };
    for (const item of cases) {
      const key = item.decision?.status ?? "processing";
      c[key] = (c[key] ?? 0) + 1;
    }
    return c;
  }, [cases]);

  const visible = cases.filter((c) =>
    filter === "all" ? true : c.decision?.status === filter,
  );

  async function act(
    id: string,
    action: "approve" | "override_reject" | "request_more_info",
  ) {
    setBusy(id);
    try {
      await reviewCase(id, action, `Reviewed via GridFlow queue (${action})`);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal">
        Human in the loop
      </p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-navy">
        Review queue
      </h1>
      <p className="mt-2 max-w-2xl text-sm text-muted">
        The agent drafts. You sign off. Approvals persist across restarts —
        this is the audit trail a DSO would keep.
      </p>

      <div className="mt-6 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => setFilter(f.id)}
            className={`rounded-full px-3 py-1.5 text-xs ${
              filter === f.id ? "bg-navy text-white" : "border border-line bg-white text-navy"
            }`}
          >
            {f.label}
            <span className="ml-1.5 opacity-70">{counts[f.id] ?? 0}</span>
          </button>
        ))}
      </div>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {visible.length === 0 && (
        <p className="mt-8 text-sm text-muted">
          No cases in this view. Run an application on the home page.
        </p>
      )}
      <ul className="mt-8 space-y-4">
        {visible.map((c) => {
          const d = c.decision;
          const extracted = c.extracted as
            | { connection_type?: string; requested_power_kw?: number }
            | null
            | undefined;
          const canReview =
            d &&
            (d.status === "pending_review" || d.status === "auto_approved");
          return (
            <li
              key={c.id}
              className="rounded-2xl border border-line bg-white p-5 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-mono text-xs text-muted">
                    #{c.id} · {when(c.created_at)}
                  </p>
                  <h2 className="mt-1 font-semibold text-navy">
                    {c.application.applicant_name} · {c.application.country}
                  </h2>
                  {extracted?.connection_type && (
                    <p className="mt-1 text-xs uppercase tracking-wide text-teal">
                      {extracted.connection_type.replaceAll("_", " ")}
                      {extracted.requested_power_kw != null
                        ? ` · ${extracted.requested_power_kw} kW`
                        : ""}
                    </p>
                  )}
                  <p className="mt-1 text-sm text-muted">
                    {c.application.description}
                  </p>
                </div>
                {d && (
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-medium uppercase tracking-wide ${statusClass(d.status)}`}
                  >
                    {d.status.replaceAll("_", " ")}
                  </span>
                )}
              </div>
              {d && (
                <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
                  <p>
                    <span className="text-muted">Draft outcome</span>
                    <br />
                    {d.outcome.replaceAll("_", " ")}
                  </p>
                  <p>
                    <span className="text-muted">Track / confidence</span>
                    <br />
                    {d.track} · {(d.confidence * 100).toFixed(0)}%
                  </p>
                  <p>
                    <span className="text-muted">Fee</span>
                    <br />
                    {d.fee_eur != null ? `€${d.fee_eur}` : "—"}
                  </p>
                </div>
              )}
              {d && (
                <p className="mt-3 text-sm leading-relaxed text-ink">
                  {d.justification}
                </p>
              )}
              {canReview && (
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    disabled={busy === c.id}
                    onClick={() => act(c.id, "approve")}
                    className="rounded-full bg-teal px-4 py-2 text-xs font-medium text-white"
                  >
                    Approve draft
                  </button>
                  <button
                    disabled={busy === c.id}
                    onClick={() => act(c.id, "request_more_info")}
                    className="rounded-full border border-line px-4 py-2 text-xs"
                  >
                    Request more info
                  </button>
                  <button
                    disabled={busy === c.id}
                    onClick={() => act(c.id, "override_reject")}
                    className="rounded-full border border-red-200 px-4 py-2 text-xs text-red-700"
                  >
                    Override → reject
                  </button>
                </div>
              )}
              {c.reviewer_note && (
                <p className="mt-3 text-xs text-muted">
                  Reviewer: {c.reviewer_note}
                  {c.reviewed_at ? ` · ${when(c.reviewed_at)}` : ""}
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
