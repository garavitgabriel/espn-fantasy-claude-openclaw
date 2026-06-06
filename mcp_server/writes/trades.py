"""WT-C — trades (propose / cancel). See docs/writes/wt-c-trades.md.

STUB: filled in by the WT-C worktree. Must define register_tools(mcp) and
register_commands(app). Use mcp_server.writes._base helpers; do not touch other files.
Accept/reject are OUT OF SCOPE (payloads never captured).
"""

from . import _base  # noqa: F401  (worktree uses _base helpers)


def register_tools(mcp):
    """Register propose_trade / cancel_trade tools."""
    pass


def register_commands(app):
    """Register propose-trade / cancel-trade CLI commands."""
    pass
