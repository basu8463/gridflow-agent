"""Settings and rulebook loading."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
RULEBOOKS_DIR = DATA_DIR / "rulebooks"
CHROMA_DIR = BACKEND_DIR / ".chroma"

load_dotenv(BACKEND_DIR / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Agent decisions below this confidence are always routed to a human.
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))

# Comma-separated browser origins allowed to call the API (local + Vercel).
FRONTEND_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]
FRONTEND_ORIGIN_REGEX = os.getenv(
    "FRONTEND_ORIGIN_REGEX",
    r"https://.*\.vercel\.app",
)


def available_countries() -> list[str]:
    return sorted(p.name.upper() for p in RULEBOOKS_DIR.iterdir() if p.is_dir())


@lru_cache(maxsize=8)
def load_rulebook(country: str) -> dict:
    """Load a country's rulebook config. New market = new folder, zero code."""
    path = RULEBOOKS_DIR / country.lower() / "config.yaml"
    if not path.exists():
        raise ValueError(f"No rulebook pack for country '{country}'. Available: {available_countries()}")
    with open(path) as f:
        return yaml.safe_load(f)


def rulebook_documents(country: str) -> list[tuple[str, str]]:
    """Return (filename, content) for every rules markdown file in a pack."""
    folder = RULEBOOKS_DIR / country.lower()
    return [(p.name, p.read_text()) for p in sorted(folder.glob("*.md"))]
