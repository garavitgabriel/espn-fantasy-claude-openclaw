"""Allow running the MCP server via `python -m mcp_server`."""

import os

from .server import mcp

transport = os.environ.get("MCP_TRANSPORT", "stdio")
if transport in ("sse", "streamable-http", "http"):
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", os.environ.get("MCP_PORT", "8000")))
    mcp.run(transport=transport, host=host, port=port)
else:
    mcp.run(transport=transport)
