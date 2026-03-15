"""Allow running the MCP server via `python -m mcp_server`."""

import os

from .server import mcp

transport = os.environ.get("MCP_TRANSPORT", "stdio")
mcp.run(transport=transport)
