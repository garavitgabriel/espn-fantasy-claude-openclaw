"""ESPN Fantasy Baseball MCP Server.

Supports stdio (local), SSE, and streamable-http transports.
Exposes 16 tools for league management: rosters, standings, matchups,
free agents, player comparison, trade analysis, scoring categories,
roster slot config, draft board tracking, and roster needs.
"""

import os

from mcp.server.fastmcp import FastMCP

# When deployed to a cloud host (e.g. Railway), the MCP SDK's DNS rebinding
# protection rejects requests whose Host header isn't localhost.  Disable it
# for network transports so external clients can connect.
transport = os.environ.get("MCP_TRANSPORT", "stdio")
_mcp_kwargs: dict = dict(
    name="espn-baseball",
    instructions=(
        "ESPN Fantasy Baseball tools for league 'El Rey' (H2H Categories, Auction draft). "
        "Use these to scout opponents, find free agents, analyze matchups, "
        "recommend roster moves, and assist during draft day. "
        "Start with get_scoring_categories and get_roster_slots to understand "
        "league settings before making recommendations."
    ),
)

if transport in ("sse", "streamable-http", "http"):
    try:
        from mcp.server.auth.settings import TransportSecuritySettings
    except ImportError:
        from mcp.server.transport_security import TransportSecuritySettings  # type: ignore[no-redef]
    _mcp_kwargs["transport_security"] = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    )

mcp = FastMCP(**_mcp_kwargs)

# Register all tools and resources
from .tools import register_tools
from .resources import register_resources
register_tools(mcp)
register_resources(mcp)


def run_server():
    """Start the MCP server with the configured transport."""
    if transport in ("sse", "streamable-http", "http"):
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", os.environ.get("MCP_PORT", "8000")))

        # For HTTP transports, add a /health endpoint for Railway healthchecks.
        # The SSE endpoint (/sse) keeps connections open for streaming, which
        # doesn't work well as a healthcheck target.
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route, Mount

        def health(_request):
            return PlainTextResponse("ok")

        mcp_app = mcp.sse_app() if transport == "sse" else mcp.streamable_http_app()

        app = Starlette(
            routes=[
                Route("/health", health),
                Mount("/", app=mcp_app),
            ],
        )

        import uvicorn
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run(transport=transport)


if __name__ == "__main__":
    run_server()
