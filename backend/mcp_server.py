"""GridFlow MCP server — same deterministic tools, callable by any MCP client.

This is how tools would be shared across agents in a production platform
(Claude Desktop, Cursor, another service). The LangGraph agent uses the
Python functions directly; MCP is the inter-agent interface.

Run (stdio):
    .venv/bin/python mcp_server.py
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app import config as app_config
from app import rules as app_rules
from app import tools as grid_tools

mcp = FastMCP("gridflow")


@mcp.tool()
def lookup_dso(address: str, country: str) -> dict:
    """Find the distribution system operator (DSO) responsible for an address."""
    return grid_tools.lookup_dso(address, country)


@mcp.tool()
def check_grid_capacity(address: str, requested_kw: float) -> dict:
    """Check local transformer headroom for a requested connection capacity."""
    return grid_tools.check_grid_capacity(address, requested_kw)


@mcp.tool()
def determine_track(country: str, connection_type: str, requested_kw: float) -> dict:
    """Determine notification vs approval track per the country rulebook."""
    rulebook = app_config.load_rulebook(country)
    return grid_tools.determine_track(rulebook, connection_type, requested_kw)


@mcp.tool()
def calculate_fee(country: str, requested_kw: float) -> dict:
    """Calculate the connection fee per the country rulebook's fee schedule."""
    rulebook = app_config.load_rulebook(country)
    return grid_tools.calculate_fee(rulebook, requested_kw)


@mcp.tool()
def search_rules(country: str, query: str, k: int = 4) -> list[dict]:
    """Semantic search over a country's grid connection rulebook."""
    return app_rules.retrieve(country, query, k=k)


if __name__ == "__main__":
    mcp.run()
