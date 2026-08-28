#!/usr/bin/env python3
"""CLI demo: run one grid connection application through the GridFlow agent.

Usage:
  python run_demo.py                      # default heat pump case, Germany
  python run_demo.py --country AT         # same case, Austrian rulebook
  python run_demo.py --case evals/golden_cases.json --index 2
"""

from __future__ import annotations

import argparse
import json

from app.agent import run_application
from app.schemas import ApplicationInput

DEFAULT_CASE = {
    "country": "DE",
    "applicant_name": "Anna Schmidt",
    "address": "Lindenstraße 12, 50674 Köln",
    "description": (
        "We are installing a new air-source heat pump for our family home. "
        "The unit is a Vaillant aroTHERM plus with 14 kW electrical rating. "
        "Requesting grid connection approval."
    ),
    "documents": ["application_form", "heat_pump_datasheet", "electrician_confirmation"],
}

BOLD = "\033[1m"
GREEN = "\033[92m"
CYAN = "\033[96m"
DIM = "\033[2m"
END = "\033[0m"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", default=None, help="Override country (DE, AT)")
    parser.add_argument("--case", default=None, help="Path to JSON file with cases")
    parser.add_argument("--index", type=int, default=0, help="Case index in file")
    args = parser.parse_args()

    if args.case:
        with open(args.case) as f:
            data = json.load(f)
        case = data[args.index]["input"] if isinstance(data, list) else data
    else:
        case = dict(DEFAULT_CASE)

    if args.country:
        case["country"] = args.country.upper()

    application = ApplicationInput(**case)
    print(f"\n{BOLD}=== GridFlow Agent — processing application ==={END}\n")

    state = run_application(application)

    for event in state["trace"]:
        print(f"{CYAN}{BOLD}[{event['step']}]{END} {BOLD}{event['title']}{END}")
        print(f"    {event['detail']}")
        print()

    decision = state["decision"]
    print(f"{BOLD}=== DECISION ==={END}")
    print(f"  Outcome:     {GREEN}{BOLD}{decision['outcome']}{END}")
    print(f"  Track:       {decision['track']}")
    print(f"  Confidence:  {decision['confidence']:.2f}")
    print(f"  Human review: {'YES' if decision['needs_human_review'] else 'no'}")
    if decision["fee_eur"] is not None:
        print(f"  Fee:         EUR {decision['fee_eur']:.2f}")
    if decision["sla_days"]:
        print(f"  SLA:         {decision['sla_days']} working days")
    if decision["missing_documents"]:
        print(f"  Missing docs: {', '.join(decision['missing_documents'])}")
    if decision["conditions"]:
        print(f"  Conditions:  {'; '.join(decision['conditions'])}")
    print(f"\n  {DIM}Justification:{END} {decision['justification']}")
    print(f"  {DIM}Cited rules:{END} {', '.join(decision['cited_rules'])}\n")


if __name__ == "__main__":
    main()
