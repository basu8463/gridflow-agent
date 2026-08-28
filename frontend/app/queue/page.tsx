"use client";

import { useEffect, useState } from "react";
import { CaseRecord, getCases, reviewCase } from "@/lib/api";

export default function QueuePage() {
  const [cases, setCases] = useState<CaseRecord[]>([]);
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
        Low-confidence decisions, missing documents, and rejections always land
        here. The agent drafts; a human signs off.
      </p>
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {cases.length === 0 && (
        <p className="mt-8 text-sm text-muted">
          No cases yet. Run an application on the home page.
        </p>
      )}
      <ul className="mt-8 space-y-4">
        {cases.map((c) => {
          const d = c.decision;
          return (
            <li
              key={c.id}
              className="rounded-2xl border border-line bg-white p-5 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-mono text-xs text-muted">#{c.id}</p>
                  <h2 className="mt-1 font-semibold text-navy">
                    {c.application.applicant_name} · {c.application.country}
                  </h2>
                  <p className="mt-1 text-sm text-muted">
                    {c.application.description}
                  </p>
                </div>
                {d && (
                  <span className="rounded-full bg-sand px-3 py-1 text-xs font-medium uppercase tracking-wide text-navy">
                    {d.status.replaceAll("_", " ")}
                  </span>
                )}
              </div>
              {d && (
                <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
                  <p>
                    <span className="text-muted">Outcome</span>
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
              {d?.status === "pending_review" && (
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
                <p className="mt-3 text-xs text-muted">Note: {c.reviewer_note}</p>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
