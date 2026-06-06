"""Write/mutation tools for the ESPN Fantasy Baseball MCP.

Plugin-style package: each operation lives in its own module so parallel worktrees
never edit the same file. The registrars below fan out to every module.

Default posture is read-only — every operation is gated by ESPN_WRITE_ENABLED and a
payload-bound confirm token (see _base.write_flow and docs/writes/00-BRIEF.md).
"""

from . import roster, lineup, trades

_MODULES = (roster, lineup, trades)


def register_write_tools(mcp):
    """Register all write tools on the MCP server."""
    for module in _MODULES:
        module.register_tools(mcp)


def register_write_commands(app):
    """Register all write commands on the Typer CLI app."""
    for module in _MODULES:
        module.register_commands(app)
