"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  CaseRecord,
  CountryPack,
  TraceEvent,
  getCountries,
  streamApplication,
} from "@/lib/api";
import { SAMPLES } from "@/lib/samples";

const ALL_DOCS = [
  "application_form",
  "heat_pump_datasheet",
  "electrician_confirmation",
  "pv_datasheet",
  "installer_certificate",
  "site_plan",
  "charger_datasheet",
  "load_calculation",
  "network_access_contract",
  "tor_conformity_certificate",
];

function outcomeStyle(outcome?: string) {
  switch (outcome) {
    case "approve":
      return "bg-teal text-white";
    case "approve_with_conditions":
      return "bg-teal-2 text-navy";
    case "request_documents":
      return "bg-amber-500 text-white";
    case "reject":
      return "bg-red-600 text-white";
    default:
      return "bg-navy text-white";
  }
}

export default function HomePage() {
  const [countries, setCountries] = useState<CountryPack[]>([]);
  const [country, setCountry] = useState("DE");
  const [name, setName] = useState("Anna Schmidt");
  const [address, setAddress] = useState("Lindenstraße 12, 50674 Köln");
  const [description, setDescription] = useState(
    "Installing an air-source heat pump, Vaillant aroTHERM plus, 14 kW electrical rating. Requesting grid connection.",
  );
  const [documents, setDocuments] = useState<string[]>([
    "application_form",
    "heat_pump_datasheet",
    "electrician_confirmation",
  ]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [trace, setTrace] = useState<TraceEvent[]>([]);
  const [result, setResult] = useState<CaseRecord | null>(null);

  useEffect(() => {
    getCountries()
      .then(setCountries)
      .catch((e) => setError(String(e)));
  }, []);

  const pack = countries.find((c) => c.code === country);
  const countryDocs = useMemo(() => {
    if (!pack) return ALL_DOCS;
    const required = new Set(
      Object.values(pack.connection_types).flatMap((t) => t.required_documents),
    );
    return ALL_DOCS.filter((d) => required.has(d));
  }, [pack]);

  function loadSample(id: string) {
    const sample = SAMPLES.find((s) => s.id === id);
    if (!sample) return;
    setCountry(sample.input.country);
    setName(sample.input.applicant_name);
    setAddress(sample.input.address);
    setDescription(sample.input.description);
    setDocuments(sample.input.documents);
    setTrace([]);
    setResult(null);
    setError(null);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setRunning(true);
    setError(null);
    setTrace([]);
    setResult(null);
    try {
      await streamApplication(
        {
          country,
          applicant_name: name,
          address,
          description,
          documents,
        },
        (event, data) => {
          if (event === "trace") {
            setTrace((prev) => [...prev, data as TraceEvent]);
          }
          if (event === "done") {
            setResult(data as CaseRecord);
          }
        },
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  }

  const decision = result?.decision;

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      <section>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal">
          Case officer desk
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-navy">
          Process a grid connection
        </h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
          Same agent, different country. Switch DE → AT and the rulebook pack
          changes — limits, documents, fees — without a code change.
        </p>

        <div className="mt-5 flex flex-wrap gap-2">
          {SAMPLES.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => loadSample(s.id)}
              className="rounded-full border border-line bg-white px-3 py-1.5 text-xs text-navy hover:border-teal"
            >
              {s.label}
            </button>
          ))}
        </div>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-navy">Country rulebook</span>
            <select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              className="w-full rounded-xl border border-line bg-white px-3 py-2"
            >
              {countries.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.name} ({c.code})
                </option>
              ))}
            </select>
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-navy">Applicant</span>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-xl border border-line bg-white px-3 py-2"
                required
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-navy">Address</span>
              <input
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                className="w-full rounded-xl border border-line bg-white px-3 py-2"
                required
              />
            </label>
          </div>

          <label className="block text-sm">
            <span className="mb-1 block font-medium text-navy">
              Application (free text)
            </span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              className="w-full rounded-xl border border-line bg-white px-3 py-2"
              required
            />
          </label>

          <fieldset>
            <legend className="mb-2 text-sm font-medium text-navy">
              Documents attached
            </legend>
            <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
              {countryDocs.map((doc) => (
                <label key={doc} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={documents.includes(doc)}
                    onChange={(e) =>
                      setDocuments((prev) =>
                        e.target.checked
                          ? [...prev, doc]
                          : prev.filter((d) => d !== doc),
                      )
                    }
                  />
                  <span className="font-mono text-xs">{doc}</span>
                </label>
              ))}
            </div>
          </fieldset>

          {pack && (
            <p className="text-xs text-muted">
              Heat pump notify limit {pack.connection_types.heat_pump.notify_only_max_kw} kW
              · solar {pack.connection_types.solar_pv.notify_only_max_kw} kW
              · EV {pack.connection_types.ev_charger.notify_only_max_kw} kW
              · base fee €{pack.fees.base_fee}
            </p>
          )}

          <button
            type="submit"
            disabled={running}
            className="rounded-full bg-navy px-5 py-2.5 text-sm font-medium text-white hover:bg-navy-2 disabled:opacity-60"
          >
            {running ? "Agent running…" : "Run agent"}
          </button>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </form>
      </section>

      <section className="rounded-2xl border border-line bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-muted">
          Agent trace
        </h2>
        {trace.length === 0 && !running && (
          <p className="mt-6 text-sm text-muted">
            Submit an application. Each step — extract, retrieve rules, validate,
            capacity, fee, decide — appears here as it runs.
          </p>
        )}
        <ol className="mt-4 space-y-4">
          {trace.map((event, i) => (
            <li key={`${event.step}-${i}`} className="flex gap-3">
              <span className="trace-dot mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full bg-teal-2" />
              <div>
                <p className="text-sm font-semibold text-navy">{event.title}</p>
                <p className="mt-0.5 text-sm text-muted">{event.detail}</p>
                <p className="mt-1 font-mono text-[11px] uppercase tracking-wide text-teal">
                  {event.step}
                </p>
              </div>
            </li>
          ))}
        </ol>

        {decision && (
          <div className="mt-6 rounded-xl border border-line bg-sand p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${outcomeStyle(decision.outcome)}`}
              >
                {decision.outcome.replaceAll("_", " ")}
              </span>
              <span className="text-xs text-muted">
                {decision.track} track · confidence{" "}
                {(decision.confidence * 100).toFixed(0)}%
                {decision.needs_human_review ? " · human review" : " · auto-approvable"}
              </span>
            </div>
            <p className="mt-3 text-sm leading-relaxed">{decision.justification}</p>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted">
              {decision.fee_eur != null && (
                <>
                  <dt>Fee</dt>
                  <dd className="text-ink">€{decision.fee_eur.toFixed(0)}</dd>
                </>
              )}
              {decision.sla_days != null && (
                <>
                  <dt>SLA</dt>
                  <dd className="text-ink">{decision.sla_days} working days</dd>
                </>
              )}
              <dt>Cited rules</dt>
              <dd className="font-mono text-ink">
                {decision.cited_rules.join(", ") || "—"}
              </dd>
              {decision.missing_documents.length > 0 && (
                <>
                  <dt>Missing</dt>
                  <dd className="font-mono text-ink">
                    {decision.missing_documents.join(", ")}
                  </dd>
                </>
              )}
            </dl>
            {result && (
              <p className="mt-3 text-xs text-muted">
                Case {result.id} is in the{" "}
                <a href="/queue" className="underline">
                  review queue
                </a>
                .
              </p>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
