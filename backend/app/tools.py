"""Agent tools. Deterministic mocks standing in for real DSO systems.

In production these would call the grid operator's GIS / asset systems.
They are deterministic (hash-based) so demos and evals are reproducible.
"""

from __future__ import annotations

import hashlib


def _stable_int(seed: str, mod: int) -> int:
    return int(hashlib.sha256(seed.encode()).hexdigest(), 16) % mod


def lookup_dso(address: str, country: str) -> dict:
    """Mock DSO (distribution system operator) lookup by address."""
    operators = {
        "DE": ["Netz Rheinland GmbH (demo)", "Stadtwerke Musterstadt Netz (demo)", "Bayernnetz Süd (demo)"],
        "AT": ["Wien Netze (demo)", "Netz Oberösterreich (demo)", "Salzburg Netz (demo)"],
    }
    pool = operators.get(country.upper(), ["Generic Grid Co (demo)"])
    return {
        "dso_name": pool[_stable_int(address, len(pool))],
        "grid_area": f"{country.upper()}-{_stable_int(address, 900) + 100}",
    }


def check_grid_capacity(address: str, requested_kw: float) -> dict:
    """Mock local transformer capacity check. Deterministic per address."""
    headroom_kw = 15 + _stable_int(address + "cap", 46)  # 15–60 kW headroom
    sufficient = requested_kw <= headroom_kw
    return {
        "substation_id": f"SUB-{_stable_int(address, 9000) + 1000}",
        "headroom_kw": headroom_kw,
        "requested_kw": requested_kw,
        "sufficient": sufficient,
    }


def validate_documents(rulebook: dict, connection_type: str, provided: list[str]) -> dict:
    """Compare provided documents against the rulebook's requirements."""
    required = rulebook["connection_types"][connection_type]["required_documents"]
    provided_set = {d.strip().lower() for d in provided}
    missing = [d for d in required if d.lower() not in provided_set]
    return {"required": required, "provided": sorted(provided_set), "missing": missing}


def determine_track(rulebook: dict, connection_type: str, requested_kw: float) -> dict:
    """Notification vs approval track, and hard-limit check, per rulebook."""
    ct = rulebook["connection_types"][connection_type]
    if requested_kw > ct["hard_limit_kw"]:
        return {"track": "approval", "exceeds_hard_limit": True, "hard_limit_kw": ct["hard_limit_kw"]}
    track = "notification" if requested_kw <= ct["notify_only_max_kw"] else "approval"
    return {
        "track": track,
        "exceeds_hard_limit": False,
        "notify_only_max_kw": ct["notify_only_max_kw"],
        "hard_limit_kw": ct["hard_limit_kw"],
    }


def calculate_fee(rulebook: dict, requested_kw: float) -> dict:
    """Connection fee per the rulebook's fee schedule."""
    fees = rulebook["fees"]
    surcharge_kw = max(0.0, requested_kw - fees["threshold_kw"])
    total = fees["base_fee"] + surcharge_kw * fees["per_kw_above_threshold"]
    return {
        "base_fee": fees["base_fee"],
        "surcharge_kw": round(surcharge_kw, 1),
        "per_kw_rate": fees["per_kw_above_threshold"],
        "total_eur": round(total, 2),
    }
