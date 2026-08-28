"""Rulebook RAG: index each rule as a chunk in Chroma, retrieve by query.

Chunking strategy: every `## Rule XX-YY-N` section is one chunk. Rules are
natural retrieval units — the agent cites rule IDs, and retrieved chunks
map 1:1 to citable rules.
"""

from __future__ import annotations

import re

import chromadb

from . import config

_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    return _client


def _split_rules(markdown: str, source: str) -> list[dict]:
    """Split a rulebook markdown file into one chunk per `## ` section."""
    chunks = []
    sections = re.split(r"\n(?=## )", markdown)
    for section in sections:
        section = section.strip()
        if not section.startswith("## "):
            continue
        title_line = section.splitlines()[0].removeprefix("## ").strip()
        rule_id_match = re.match(r"Rule ([A-Z]{2}-[A-Z]+-\d+)", title_line)
        rule_id = rule_id_match.group(1) if rule_id_match else title_line
        chunks.append({"id": rule_id, "title": title_line, "text": section, "source": source})
    return chunks


def index_country(country: str, force: bool = False) -> int:
    """(Re)index one country's rulebook pack. Returns chunk count."""
    client = _get_client()
    name = f"rules_{country.lower()}"
    if force:
        try:
            client.delete_collection(name)
        except Exception:
            pass
    collection = client.get_or_create_collection(name)
    if collection.count() > 0 and not force:
        return collection.count()

    all_chunks = []
    for filename, content in config.rulebook_documents(country):
        all_chunks.extend(_split_rules(content, filename))

    if all_chunks:
        collection.add(
            ids=[c["id"] for c in all_chunks],
            documents=[c["text"] for c in all_chunks],
            metadatas=[{"title": c["title"], "source": c["source"]} for c in all_chunks],
        )
    return len(all_chunks)


def retrieve(country: str, query: str, k: int = 4) -> list[dict]:
    """Retrieve the k most relevant rules for a query."""
    index_country(country)
    collection = _get_client().get_or_create_collection(f"rules_{country.lower()}")
    result = collection.query(query_texts=[query], n_results=min(k, collection.count()))
    hits = []
    for i in range(len(result["ids"][0])):
        hits.append(
            {
                "rule_id": result["ids"][0][i],
                "title": result["metadatas"][0][i]["title"],
                "source": result["metadatas"][0][i]["source"],
                "text": result["documents"][0][i],
                "distance": round(result["distances"][0][i], 4) if result.get("distances") else None,
            }
        )
    return hits
