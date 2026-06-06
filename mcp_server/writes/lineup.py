"""WT-B — set lineup (activate / bench / swap). See docs/writes/wt-b-lineup.md.

STUB: filled in by the WT-B worktree. Must define register_tools(mcp) and
register_commands(app). Use mcp_server.writes._base helpers; do not touch other files.
"""

from . import _base  # noqa: F401  (worktree uses _base helpers)


def register_tools(mcp):
    """Register set_lineup tool."""
    pass


def register_commands(app):
    """Register lineup CLI command."""
    pass
