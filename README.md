# GridFlow — Vertical AI Agent for Grid Connection Workflows

An AI agent that processes grid connection applications end-to-end: reads the
request, checks it against country-specific regulations (RAG), calls grid
tools, drafts a justified decision — and routes it to a human for approval.

Built as a scoped-down, original demonstration of the vertical-AI agent
patterns used in energy-tech platforms (agentic orchestration, tool-calling,
RAG over regulations, human-in-the-loop, evaluation-driven quality).

## Why this exists

Two hard problems for vertical AI in energy:

1. **Regulations don't scale across borders.** Every country has different
   connection rules, documents, and fee schedules. GridFlow treats each
   country as a **rulebook pack** (`backend/data/rulebooks/<country>/`) —
   markdown rules + a YAML config. Expanding to a new market is a content
   problem, not an engineering problem. Switch the country dropdown and the
   same agent applies different rules.

2. **AI must prove ROI, not promise it.** GridFlow ships with an
   **evaluation harness** (`backend/evals/`): golden test cases with known
   correct outcomes, scored on every change. Low-confidence decisions are
   always routed to a human — trust is earned with numbers.

## Architecture

```
Application (free text + documents)
        │
        ▼
┌─ extract ──────┐  LLM: structured extraction (type, kW)
├─ retrieve ─────┤  RAG: top-k rules from country pack (Chroma)
├─ validate ─────┤  tool: documents vs rulebook requirements, track routing
├─ capacity ─────┤  tool: local transformer headroom check
├─ fee ──────────┤  tool: fee schedule from rulebook config
└─ decide ───────┘  LLM: justified decision citing rule IDs + confidence
        │
        ▼
Human review queue (approve / override)
```

- **LangGraph** state machine, every step emits a visible trace event
- **Claude** (Anthropic) primary, **OpenAI fallback** via a provider-routing
  layer — no provider imports outside `app/llm.py`
- **Deterministic tools decide the numbers** (fees, tracks, capacity); the
  LLM extracts structure and writes justifications. LLMs never invent fees.
- **Guardrails**: policy outcomes (missing docs → request_documents,
  over hard limit → reject) are enforced in code, not hoped for in prompts
- **Chroma** vector store, one chunk per rule → retrieved chunks map 1:1 to
  citable rule IDs

## Run it

```bash
cd backend
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY

# Single application through the agent, with live trace:
.venv/bin/python run_demo.py                 # heat pump, Germany
.venv/bin/python run_demo.py --country AT    # same request, Austrian rules

# Evaluation harness (10 golden cases):
.venv/bin/python evals/run_evals.py
```

## Rulebook packs

| | Germany (DE) | Austria (AT) |
|---|---|---|
| Heat pump notify limit | 12 kW | 15 kW |
| Solar PV notify limit | 30 kW | 20 kW |
| EV charger notify limit | 11 kW | 7.4 kW |
| Extra documents | — | network access contract, TOR certificate |
| Base fee | €500 | €400 |

> Rulebooks are simplified demo rules inspired by real German/Austrian
> connection practice — clearly not legal advice. The point is the
> architecture: rules as swappable content.

## API

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000
```

- `POST /applications` — run the agent, return the case
- `POST /applications/stream` — SSE: `trace` events then `done`
- `GET /cases` · `POST /cases/{id}/review` — human-in-the-loop queue
- `GET /countries` · `GET /rulebooks/{DE|AT}` — swappable packs
- `GET /evals/golden` — evaluation cases

## Frontend

```bash
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm install && npm run dev
```

Open http://localhost:3000 — run a DE heat pump, switch to AT, watch the rulebook change the outcome.

## Status

- [x] Day 1 — agent core, rulebook packs (DE/AT), tools, RAG, eval harness
- [x] Day 2 — FastAPI + SSE trace streaming + Next.js operator UI
- [ ] Day 3 — polish, deploy (Vercel frontend + Render API)
