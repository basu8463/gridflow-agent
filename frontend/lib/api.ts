export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type ApplicationInput = {
  country: string;
  applicant_name: string;
  address: string;
  description: string;
  documents: string[];
};

export type TraceEvent = {
  step: string;
  title: string;
  detail: string;
  data?: Record<string, unknown> | null;
  ts: number;
};

export type Decision = {
  outcome: string;
  track: string;
  justification: string;
  cited_rules: string[];
  conditions: string[];
  missing_documents: string[];
  fee_eur: number | null;
  sla_days: number | null;
  confidence: number;
  needs_human_review: boolean;
  status: string;
};

export type CaseRecord = {
  id: string;
  created_at: number;
  application: ApplicationInput;
  extracted?: Record<string, unknown> | null;
  decision?: Decision | null;
  trace: TraceEvent[];
  reviewer_note: string;
  reviewed_at: number | null;
};

export type CountryPack = {
  code: string;
  name: string;
  currency: string;
  connection_types: Record<
    string,
    {
      label: string;
      notify_only_max_kw: number;
      hard_limit_kw: number;
      required_documents: string[];
    }
  >;
  fees: {
    base_fee: number;
    per_kw_above_threshold: number;
    threshold_kw: number;
    currency: string;
  };
  sla: { notification_days: number; approval_days: number };
};

export async function getHealth() {
  const res = await fetch(`${API_URL}/health`);
  if (!res.ok) throw new Error("API unavailable");
  return res.json() as Promise<{
    ok: boolean;
    provider: string;
    countries: string[];
    confidence_threshold: number;
  }>;
}

export async function getCountries() {
  const res = await fetch(`${API_URL}/countries`);
  if (!res.ok) throw new Error("Failed to load countries");
  return res.json() as Promise<CountryPack[]>;
}

export async function getCases(status?: string) {
  const url = status
    ? `${API_URL}/cases?status=${encodeURIComponent(status)}`
    : `${API_URL}/cases`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to load cases");
  return res.json() as Promise<CaseRecord[]>;
}

export async function getStats() {
  const res = await fetch(`${API_URL}/stats`);
  if (!res.ok) throw new Error("Failed to load stats");
  return res.json() as Promise<{ total: number; by_status: Record<string, number> }>;
}

export async function reviewCase(
  id: string,
  action: "approve" | "override_reject" | "request_more_info",
  note = "",
) {
  const res = await fetch(`${API_URL}/cases/${id}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, note }),
  });
  if (!res.ok) throw new Error("Review failed");
  return res.json() as Promise<CaseRecord>;
}

export async function streamApplication(
  input: ApplicationInput,
  onEvent: (event: string, data: unknown) => void,
) {
  const res = await fetch(`${API_URL}/applications/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(input),
  });
  if (!res.ok || !res.body) {
    throw new Error(`Stream failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const chunks = buf.split("\n\n");
    buf = chunks.pop() ?? "";
    for (const chunk of chunks) {
      let event = "message";
      let data = "";
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) onEvent(event, JSON.parse(data));
    }
  }
}
