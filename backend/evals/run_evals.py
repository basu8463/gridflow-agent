#!/usr/bin/env python3
"""Evaluation harness: run every golden case through the agent and score it.

Checks two things per case:
  1. track    — did deterministic routing pick the right procedure?
  2. outcome  — is the decision within the accepted outcome set?

Usage:  python evals/run_evals.py [--only N]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import run_application  # noqa: E402
from app.schemas import ApplicationInput  # noqa: E402

GOLDEN = Path(__file__).parent / "golden_cases.json"

BOLD, GREEN, RED, DIM, END = "\033[1m", "\033[92m", "\033[91m", "\033[2m", "\033[0m"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=int, default=None, help="Run a single case by index")
    args = parser.parse_args()

    cases = json.loads(GOLDEN.read_text())
    if args.only is not None:
        cases = [cases[args.only]]

    results = []
    t0 = time.time()
    for i, case in enumerate(cases):
        state = run_application(ApplicationInput(**case["input"]))
        decision = state["decision"]
        track_ok = decision["track"] == case["expected"]["track"]
        outcome_ok = decision["outcome"] in case["expected"]["outcome_in"]
        passed = track_ok and outcome_ok
        results.append(passed)
        icon = f"{GREEN}PASS{END}" if passed else f"{RED}FAIL{END}"
        print(f"[{i}] {icon} {case['name']}")
        print(
            f"     {DIM}track={decision['track']} ({'ok' if track_ok else 'expected ' + case['expected']['track']}) · "
            f"outcome={decision['outcome']} ({'ok' if outcome_ok else 'expected ' + str(case['expected']['outcome_in'])}) · "
            f"confidence={decision['confidence']:.2f}{END}"
        )

    elapsed = time.time() - t0
    passed = sum(results)
    print(f"\n{BOLD}=== {passed}/{len(results)} passed ({passed / len(results) * 100:.0f}%) in {elapsed:.1f}s ==={END}")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
