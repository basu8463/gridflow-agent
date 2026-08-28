"use client";

import { useEffect, useState } from "react";
import { CountryPack, getCountries } from "@/lib/api";

export default function RulesPage() {
  const [packs, setPacks] = useState<CountryPack[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCountries()
      .then(setPacks)
      .catch((e) => setError(String(e)));
  }, []);

  const de = packs.find((p) => p.code === "DE");
  const at = packs.find((p) => p.code === "AT");
  const types = de ? Object.keys(de.connection_types) : [];

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal">
        New country = content, not code
      </p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-navy">
        Rulebook packs
      </h1>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
        Germany took years of domain work. Austria is a folder of markdown +
        YAML. The agent, tools, and graph stay the same.
      </p>
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {de && at && (
        <div className="mt-8 overflow-x-auto rounded-2xl border border-line bg-white shadow-sm">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-sand text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-3">Rule</th>
                <th className="px-4 py-3">Germany</th>
                <th className="px-4 py-3">Austria</th>
              </tr>
            </thead>
            <tbody>
              {types.map((key) => (
                <tr key={key} className="border-t border-line">
                  <td className="px-4 py-3 font-medium text-navy">
                    {de.connection_types[key].label} notify limit
                  </td>
                  <td className="px-4 py-3">
                    {de.connection_types[key].notify_only_max_kw} kW
                  </td>
                  <td className="px-4 py-3">
                    {at.connection_types[key].notify_only_max_kw} kW
                  </td>
                </tr>
              ))}
              <tr className="border-t border-line">
                <td className="px-4 py-3 font-medium text-navy">Base fee</td>
                <td className="px-4 py-3">€{de.fees.base_fee}</td>
                <td className="px-4 py-3">€{at.fees.base_fee}</td>
              </tr>
              <tr className="border-t border-line">
                <td className="px-4 py-3 font-medium text-navy">
                  Capacity surcharge
                </td>
                <td className="px-4 py-3">
                  €{de.fees.per_kw_above_threshold}/kW above {de.fees.threshold_kw} kW
                </td>
                <td className="px-4 py-3">
                  €{at.fees.per_kw_above_threshold}/kW above {at.fees.threshold_kw} kW
                </td>
              </tr>
              <tr className="border-t border-line">
                <td className="px-4 py-3 font-medium text-navy">Approval SLA</td>
                <td className="px-4 py-3">{de.sla.approval_days} working days</td>
                <td className="px-4 py-3">{at.sla.approval_days} working days</td>
              </tr>
              <tr className="border-t border-line">
                <td className="px-4 py-3 font-medium text-navy">
                  Extra documents
                </td>
                <td className="px-4 py-3 text-muted">None beyond DE baseline</td>
                <td className="px-4 py-3">
                  network_access_contract, tor_conformity_certificate
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-6 text-xs text-muted">
        Demo rules inspired by German/Austrian connection practice — not legal
        advice. The architecture is the point.
      </p>
    </div>
  );
}
