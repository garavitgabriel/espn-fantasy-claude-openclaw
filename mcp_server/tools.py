"""MCP tool definitions and handlers for ESPN Fantasy Baseball."""

from mcp.server.fastmcp import FastMCP

from .config import get_league, get_my_team
from . import formatters


def register_tools(mcp: FastMCP):
    """Register all tools on the MCP server."""

    @mcp.tool()
    def get_my_roster() -> str:
        """Get my fantasy baseball team's roster with stats, positions, and injury status."""
        league = get_league()
        team = get_my_team(league)
        if not team:
            return "Could not find your team. Check ESPN_TEAM_NAME."
        return formatters.fmt_roster(team)

    @mcp.tool()
    def get_team_roster(team_name: str) -> str:
        """Get any team's roster by team name (partial match).

        Args:
            team_name: Full or partial team name to search for
        """
        league = get_league()
        name_lower = team_name.lower()
        for team in league.teams:
            if name_lower in team.team_name.lower():
                return formatters.fmt_roster(team)
        available = ", ".join(t.team_name for t in league.teams)
        return f"Team '{team_name}' not found. Available teams: {available}"

    @mcp.tool()
    def get_matchup(week: int = 0) -> str:
        """Get my team's current or specific week matchup with category-by-category breakdown.

        Args:
            week: Matchup period (0 = current week)
        """
        league = get_league()
        my_team = get_my_team(league)
        if not my_team:
            return "Could not find your team."

        matchup_period = week if week > 0 else None
        try:
            box_scores = league.box_scores(matchup_period=matchup_period)
        except (KeyError, TypeError):
            return "No matchup data available yet (season may not have started)."

        for bs in box_scores:
            home = bs.home_team
            away = bs.away_team
            home_id = home.team_id if hasattr(home, 'team_id') else home
            away_id = away.team_id if hasattr(away, 'team_id') else away
            if home_id == my_team.team_id or away_id == my_team.team_id:
                return formatters.fmt_box_score(bs)

        return "Could not find your matchup this week."

    @mcp.tool()
    def get_standings() -> str:
        """Get current league standings sorted by rank."""
        league = get_league()
        return formatters.fmt_standings(league.standings())

    @mcp.tool()
    def get_free_agents(position: str = "", size: int = 25) -> str:
        """Get best available free agents, optionally filtered by position.

        Args:
            position: Position filter (C, 1B, 2B, 3B, SS, OF, SP, RP, DH, UTIL). Empty = all positions.
            size: Number of results (default 25)
        """
        league = get_league()
        kwargs = {"size": size}
        if position:
            kwargs["position"] = position.upper()
        players = league.free_agents(**kwargs)
        header = f"## Free Agents" + (f" — {position.upper()}" if position else "") + "\n\n"
        return header + formatters.fmt_free_agents(players)

    @mcp.tool()
    def get_recent_activity(size: int = 25) -> str:
        """Get recent league transactions (adds, drops, trades).

        Args:
            size: Number of transactions to return (default 25)
        """
        league = get_league()
        activities = league.recent_activity(size=size)
        return "## Recent Activity\n\n" + formatters.fmt_activity(activities)

    @mcp.tool()
    def get_box_scores(week: int = 0) -> str:
        """Get all matchup box scores for a given week.

        Args:
            week: Matchup period (0 = current week)
        """
        league = get_league()
        matchup_period = week if week > 0 else None
        try:
            box_scores = league.box_scores(matchup_period=matchup_period)
        except (KeyError, TypeError):
            return "No box score data available yet (season may not have started)."
        results = []
        for bs in box_scores:
            results.append(formatters.fmt_box_score(bs))
        return "\n\n---\n\n".join(results)

    @mcp.tool()
    def get_player_info(player_name: str) -> str:
        """Get detailed stats and info for a specific player.

        Args:
            player_name: Player's full name (e.g. "Shohei Ohtani")
        """
        league = get_league()
        player = league.player_info(name=player_name)
        if player is None:
            return f"Player '{player_name}' not found. Try the exact ESPN name."
        if isinstance(player, list):
            return "\n\n---\n\n".join(formatters.fmt_player_detail(p) for p in player)
        return formatters.fmt_player_detail(player)

    @mcp.tool()
    def compare_players(player1: str, player2: str) -> str:
        """Side-by-side comparison of two players' stats.

        Args:
            player1: First player's full name
            player2: Second player's full name
        """
        league = get_league()
        p1 = league.player_info(name=player1)
        p2 = league.player_info(name=player2)

        if p1 is None:
            return f"Player '{player1}' not found."
        if p2 is None:
            return f"Player '{player2}' not found."

        return formatters.fmt_compare(p1, p2)

    @mcp.tool()
    def get_league_rosters() -> str:
        """Overview of all 12 teams' rosters — useful for finding trade targets."""
        league = get_league()
        return "## League Rosters Overview\n\n" + formatters.fmt_league_rosters(league.teams)

    @mcp.tool()
    def analyze_trade(give_players: str, receive_players: str) -> str:
        """Evaluate a potential trade by comparing the players you'd give vs receive.

        Args:
            give_players: Comma-separated names of players you'd give away
            receive_players: Comma-separated names of players you'd receive
        """
        league = get_league()
        give_names = [n.strip() for n in give_players.split(",")]
        recv_names = [n.strip() for n in receive_players.split(",")]

        give_list = []
        recv_list = []
        errors = []

        for name in give_names:
            p = league.player_info(name=name)
            if p is None:
                errors.append(f"'{name}' not found")
            else:
                give_list.append(p)

        for name in recv_names:
            p = league.player_info(name=name)
            if p is None:
                errors.append(f"'{name}' not found")
            else:
                recv_list.append(p)

        if errors:
            return "Errors: " + "; ".join(errors)

        return formatters.fmt_trade_analysis(give_list, recv_list)

    @mcp.tool()
    def get_scoring_categories() -> str:
        """Get this league's H2H scoring categories — essential for valuing players correctly.

        Returns the exact stat categories used in head-to-head matchups,
        including which ones are 'reverse' (lower is better, e.g. ERA, WHIP).
        """
        league = get_league()
        raw = league.settings._raw_scoring_settings
        return formatters.fmt_scoring_categories(raw)

    @mcp.tool()
    def get_roster_slots() -> str:
        """Get the league's roster slot configuration (how many C, 1B, OF, P, bench, IL slots)."""
        league = get_league()
        data = league.espn_request.get_league()
        slot_counts = data['settings'].get('rosterSettings', {}).get('lineupSlotCounts', {})
        return formatters.fmt_roster_slots(slot_counts)

    @mcp.tool()
    def get_draft_board() -> str:
        """Get draft results: picks, prices (auction), team budgets, and keeper status.

        During a live auction draft, use this + refresh_data to track spending in real time.
        """
        league = get_league()
        data = league.espn_request.get_league()
        draft_settings = data['settings'].get('draftSettings', {})
        slot_counts = data['settings'].get('rosterSettings', {}).get('lineupSlotCounts', {})
        result = formatters.fmt_draft_board(league.draft, league.teams, draft_settings)
        # Append roster needs for my team
        my_team = get_my_team(league)
        if my_team and league.draft:
            result += "\n\n---\n\n" + formatters.fmt_roster_needs(my_team, slot_counts)
        return result

    @mcp.tool()
    def get_roster_needs() -> str:
        """Analyze my roster against required positions — shows which slots are still empty.

        Critical during draft to know what positions to target next.
        """
        league = get_league()
        my_team = get_my_team(league)
        if not my_team:
            return "Could not find your team. Check ESPN_TEAM_NAME."
        data = league.espn_request.get_league()
        slot_counts = data['settings'].get('rosterSettings', {}).get('lineupSlotCounts', {})
        return formatters.fmt_roster_needs(my_team, slot_counts)

    @mcp.tool()
    def refresh_data() -> str:
        """Pull the latest data from ESPN. Use this to get updated stats/scores."""
        from .config import _league_instance
        import mcp_server.config as cfg

        league = get_league()
        league.refresh()
        # Update the cached instance reference
        cfg._league_instance = league
        return "League data refreshed successfully. Current week: " + str(league.current_week)
