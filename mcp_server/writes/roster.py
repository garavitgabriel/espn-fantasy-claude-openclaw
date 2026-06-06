"""WT-A — roster moves (add / drop / waiver). See docs/writes/wt-a-roster.md.

STUB: filled in by the WT-A worktree. Must define register_tools(mcp) and
register_commands(app). Use mcp_server.writes._base helpers; do not touch other files.
"""

from . import _base  # noqa: F401  (worktree uses _base helpers)


def register_tools(mcp):
    """Register add_player / drop_player / waiver_claim tools."""
    pass


def register_commands(app):
    """Register add / drop / waiver CLI commands."""
    pass
