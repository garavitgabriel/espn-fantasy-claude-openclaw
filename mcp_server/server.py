"""ESPN Fantasy Baseball MCP Server.

Supports stdio (local), SSE, and streamable-http transports.
Exposes 16 tools for league management: rosters, standings, matchups,
free agents, player comparison, trade analysis, scoring categories,
roster slot config, draft board tracking, and roster needs.
"""

import os

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "espn-baseball",
    instructions=(
        "ESPN Fantasy Baseball tools for league 'El Rey' (H2H Categories, Auction draft). "
        "Use these to scout opponents, find free agents, analyze matchups, "
        "recommend roster moves, and assist during draft day. "
        "Start with get_scoring_categories and get_roster_slots to understand "
        "league settings before making recommendations."
    ),
)

# Register all tools
from .tools import register_tools
register_tools(mcp)

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)
