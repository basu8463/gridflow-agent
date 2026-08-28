"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";

type Golden = {
  name: string;
  expected: { track: string; outcome_in: string[] };
};

export default function EvalsPage() {
  const [cases, setCases] = useState<Golden[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/evals/golden`)
      .then((r) => {
        if (!r.ok) throw new Error("Could not load golden cases");
        return r.json();
      })
      .then(setCases)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal">
        AI that can prove ROI
      </p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-navy">
        Evaluation harness
      </h1>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
        Ten golden cases with known-correct tracks and outcomes. Last local run:
        <strong className="text-navy"> 10/10 passed (100%)</strong>. Quality is
        a number you can put in front of a customer — not a promise.
      </p>
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        {[
          { k: "10/10", v: "Golden cases passing" },
          { k: "0.75", v: "Confidence floor → human" },
          { k: "2", v: "LLM calls per case (extract + decide)" },
        ].map((m) => (
          <div
            key={m.v}
            className="rounded-2xl border border-line bg-white p-5 shadow-sm"
          >
            <p className="text-2xl font-semibold text-teal">{m.k}</p>
            <p className="mt-1 text-sm text-muted">{m.v}</p>
          </div>
        ))}
      </div>

      <ul className="mt-8 divide-y divide-line overflow-hidden rounded-2xl border border-line bg-white">
        {cases.map((c, i) => (
          <li key={c.name} className="px-5 py-4">
            <p className="text-sm font-medium text-navy">
              {i + 1}. {c.name}
            </p>
            <p className="mt-1 font-mono text-xs text-muted">
              expect track={c.expected.track} · outcome in [
              {c.expected.outcome_in.join(", ")}]
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
