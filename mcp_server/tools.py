"""MCP tool definitions and handlers for ESPN Fantasy Baseball."""

import difflib
import logging

from mcp.server.fastmcp import FastMCP

from .config import get_league, get_my_team, get_my_team_error, resolve_team, describe_available_teams
from . import formatters
from . import espn_public_api

logger = logging.getLogger(__name__)


def _resolve_player(league, name: str):
    """Resolve a player by name, handling the list return case.

    Returns (player, error_msg). On success error_msg is None.
    On failure player is None and error_msg has suggestions.
    """
    result = league.player_info(name=name)
    if result is None:
        # Try fuzzy matching
        all_names = list(league.player_map.keys())
        close = difflib.get_close_matches(name, all_names, n=3, cutoff=0.6)
        if close:
            suggestions = ", ".join(f'"{n}"' for n in close)
            return None, f"Player '{name}' not found. Did you mean: {suggestions}?"
        return None, f"Player '{name}' not found. Try the exact ESPN name."
    # player_info can return a list
    if isinstance(result, list):
        return result[0], None
    return result, None


def register_tools(mcp: FastMCP):
    """Register all tools on the MCP server."""

    @mcp.tool()
    def get_my_roster() -> str:
        """Get my fantasy baseball team's roster with stats, positions, and injury status."""
        league = get_league()
        team = get_my_team(league)
        if not team:
            return get_my_team_error(league)
        return formatters.fmt_roster(team)

    @mcp.tool()
    def get_team_roster(team_name: str) -> str:
        """Get any team's roster by team name (partial match).

        Args:
            team_name: Full or partial team name to search for
        """
        league = get_league()
        team = resolve_team(league, team_name)
        if team:
            return formatters.fmt_roster(team)
        return f"Team '{team_name}' not found. Available teams: {describe_available_teams(league)}"

    @mcp.tool()
    def get_matchup(week: int = 0) -> str:
        """Get my team's current or specific week matchup with category-by-category breakdown.

        Args:
            week: Matchup period (0 = current week)
        """
        league = get_league()
        my_team = get_my_team(league)
        if not my_team:
            return get_my_team_error(league)

        matchup_period = week if week > 0 else None
        try:
            box_scores = league.box_scores(matchup_period=matchup_period)
        except Exception as e:
            return f"No matchup data available: {e}"

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
        except Exception as e:
            return f"No box score data available: {e}"
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
        player, error = _resolve_player(league, player_name)
        if error:
            return error
        return formatters.fmt_player_detail(player)

    @mcp.tool()
    def compare_players(player1: str, player2: str) -> str:
        """Side-by-side comparison of two players' stats.

        Args:
            player1: First player's full name
            player2: Second player's full name
        """
        league = get_league()
        p1, err1 = _resolve_player(league, player1)
        p2, err2 = _resolve_player(league, player2)

        errors = [e for e in (err1, err2) if e]
        if errors:
            return "\n".join(errors)

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
            p, err = _resolve_player(league, name)
            if err:
                errors.append(err)
            else:
                give_list.append(p)

        for name in recv_names:
            p, err = _resolve_player(league, name)
            if err:
                errors.append(err)
            else:
                recv_list.append(p)

        if errors:
            return "\n".join(errors)

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
        if not my_team:
            result += "\n\n---\n\n" + get_my_team_error(league)
        elif league.draft:
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
            return get_my_team_error(league)
        data = league.espn_request.get_league()
        slot_counts = data['settings'].get('rosterSettings', {}).get('lineupSlotCounts', {})
        return formatters.fmt_roster_needs(my_team, slot_counts)

    @mcp.tool()
    def refresh_data() -> str:
        """Pull the latest data from ESPN. Use this to get updated stats/scores."""
        import mcp_server.config as cfg

        try:
            league = get_league()
            league.refresh()
            cfg._league_instance = league
            return f"League data refreshed successfully. Current week: {league.current_week}"
        except Exception as e:
            return f"Refresh failed: {e}. ESPN may be temporarily unavailable, or your credentials may have expired."

    # ------------------------------------------------------------------
    # Phase B — New tools from existing espn_api data
    # ------------------------------------------------------------------

    @mcp.tool()
    def get_schedule(team_name: str = "") -> str:
        """Get a team's full season schedule with results and upcoming matchups.

        Shows wins/losses, scores, and marks the current week. Essential for
        strength-of-schedule analysis and playoff planning.

        Args:
            team_name: Team name (partial match). Empty = my team.
        """
        league = get_league()
        if team_name:
            team = resolve_team(league, team_name)
            if not team:
                return f"Team '{team_name}' not found. Available teams: {describe_available_teams(league)}"
        else:
            team = get_my_team(league)
            if not team:
                return get_my_team_error(league)

        # Load scoreboard to populate schedule with Team objects
        try:
            league.scoreboard()
        except Exception:
            pass  # Schedule may already be populated from init

        return formatters.fmt_schedule(team, current_week=league.current_week)

    @mcp.tool()
    def get_league_settings() -> str:
        """Get comprehensive league configuration: playoff structure, trade deadline,
        FAAB budget, divisions, tiebreakers, keeper count, and more.

        Use this to understand the full league rules beyond just scoring categories.
        """
        league = get_league()
        return formatters.fmt_league_settings(league.settings)

    @mcp.tool()
    def search_player(query: str) -> str:
        """Search for players by partial name. Returns up to 10 matches.

        Use this when you're not sure of the exact ESPN name. Unlike get_player_info
        which requires an exact match, this does fuzzy matching.

        Args:
            query: Partial player name (e.g. "ohtani", "judge", "acuna")
        """
        league = get_league()
        query_lower = query.lower()

        # Search player_map for matching names
        matching_names = [
            name for name in league.player_map.keys()
            if isinstance(name, str) and query_lower in name.lower()
        ]

        # Also try fuzzy matching if few results
        if len(matching_names) < 3:
            all_names = [n for n in league.player_map.keys() if isinstance(n, str)]
            fuzzy = difflib.get_close_matches(query, all_names, n=10, cutoff=0.5)
            for name in fuzzy:
                if name not in matching_names:
                    matching_names.append(name)

        # Resolve to Player objects (up to 10)
        players = []
        for name in matching_names[:10]:
            try:
                p = league.player_info(name=name)
                if p is None:
                    continue
                if isinstance(p, list):
                    players.extend(p)
                else:
                    players.append(p)
            except Exception:
                continue

        return formatters.fmt_player_search(players[:10], query)

    @mcp.tool()
    def get_scoreboard(week: int = 0) -> str:
        """Get the matchup scoreboard for a given week — shows all matchups with scores.

        Lighter than get_box_scores — shows scores and winners without category details.
        Includes live scores for the current week.

        Args:
            week: Matchup period (0 = current week)
        """
        league = get_league()
        matchup_period = week if week > 0 else None
        try:
            matchups = league.scoreboard(matchupPeriod=matchup_period)
        except Exception as e:
            return f"No scoreboard data available: {e}"

        if not matchups:
            return "No matchups found for this week."

        display_week = week if week > 0 else league.currentMatchupPeriod
        lines = [
            f"## Scoreboard — Week {display_week}",
            "",
            "| Away | Score | Home | Score | Winner |",
            "|------|-------|------|-------|--------|",
        ]

        for m in matchups:
            home_name = m.home_team.team_name if hasattr(m.home_team, 'team_name') else str(m.home_team)
            away_name = m.away_team.team_name if hasattr(m.away_team, 'team_name') else str(m.away_team)

            # Use live scores if available, else final scores
            home_live = getattr(m, 'home_team_live_score', None)
            away_live = getattr(m, 'away_team_live_score', None)

            if home_live is not None and away_live is not None:
                h_score = f"{home_live:.1f}"
                a_score = f"{away_live:.1f}"
            else:
                h_score = f"{m.home_final_score:.1f}" if m.home_final_score else "—"
                a_score = f"{m.away_final_score:.1f}" if m.away_final_score else "—"

            winner = getattr(m, 'winner', 'UNDECIDED')
            if winner == "HOME":
                winner_name = home_name
            elif winner == "AWAY":
                winner_name = away_name
            else:
                winner_name = "—"

            lines.append(f"| {away_name} | {a_score} | {home_name} | {h_score} | {winner_name} |")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Phase C — New tools from discovered ESPN public APIs
    # ------------------------------------------------------------------

    @mcp.tool()
    def get_player_news(player_name: str) -> str:
        """Get latest news, injury status, and next game for a player.

        Uses ESPN's public player profile API. Returns rotowire injury blurbs,
        recent headlines, and the player's next scheduled game.

        Args:
            player_name: Player's full name (e.g. "Shohei Ohtani")
        """
        league = get_league()
        athlete_id = espn_public_api.resolve_athlete_id(league, player_name)
        if not athlete_id:
            return f"Could not find ESPN athlete ID for '{player_name}'. Try the exact ESPN name."
        try:
            data = espn_public_api.get_player_overview(athlete_id)
            return formatters.fmt_player_news(data, player_name)
        except Exception as e:
            return f"Failed to fetch news for '{player_name}': {e}"

    @mcp.tool()
    def get_player_splits(player_name: str, season: int = 0) -> str:
        """Get player splits: vs LHP/RHP, home/away, by month, by count, etc.

        Shows 9 categories of splits with detailed batting/pitching stats.
        Critical for evaluating platoon players and matchup-dependent value.

        Args:
            player_name: Player's full name
            season: Season year (0 = current)
        """
        league = get_league()
        athlete_id = espn_public_api.resolve_athlete_id(league, player_name)
        if not athlete_id:
            return f"Could not find ESPN athlete ID for '{player_name}'. Try the exact ESPN name."
        try:
            data = espn_public_api.get_player_splits(
                athlete_id,
                season=season if season > 0 else None,
            )
            return formatters.fmt_player_splits(data, player_name)
        except Exception as e:
            return f"Failed to fetch splits for '{player_name}': {e}"

    @mcp.tool()
    def get_player_gamelog(player_name: str, category: str = "") -> str:
        """Get a player's game-by-game stats for the current season.

        Shows the last 20 games with full stat lines. Use this to identify
        hot/cold streaks, recent form, and matchup-specific performance.

        Args:
            player_name: Player's full name
            category: Filter by "batting" or "pitching" (empty = all)
        """
        league = get_league()
        athlete_id = espn_public_api.resolve_athlete_id(league, player_name)
        if not athlete_id:
            return f"Could not find ESPN athlete ID for '{player_name}'. Try the exact ESPN name."
        try:
            data = espn_public_api.get_player_gamelog(
                athlete_id,
                category=category if category else None,
            )
            return formatters.fmt_player_gamelog(data, player_name)
        except Exception as e:
            return f"Failed to fetch game log for '{player_name}': {e}"

    @mcp.tool()
    def get_mlb_games(date: str = "") -> str:
        """Get today's MLB games with scores and status.

        Shows all games for a given date — useful for checking which teams
        are playing (streaming pitchers, bench off-day players).

        Args:
            date: Date in YYYYMMDD format (empty = today)
        """
        if not date:
            from datetime import datetime
            date = datetime.now().strftime("%Y%m%d")
        try:
            data = espn_public_api.get_mlb_games(date)
            return formatters.fmt_mlb_games(data, date)
        except Exception as e:
            return f"Failed to fetch MLB games for {date}: {e}"

    @mcp.tool()
    def get_batter_vs_team(player_name: str) -> str:
        """Get a batter's stats vs each MLB team (all 30 teams).

        Shows batting performance broken down by opponent team — critical for
        evaluating matchup-dependent hitters and planning weekly lineups.

        Args:
            player_name: Player's full name (e.g. "Freddie Freeman")
        """
        league = get_league()
        athlete_id = espn_public_api.resolve_athlete_id(league, player_name)
        if not athlete_id:
            return f"Could not find ESPN athlete ID for '{player_name}'. Try the exact ESPN name."
        try:
            data = espn_public_api.get_batter_vs_team(athlete_id)
            return formatters.fmt_batter_vs_team(data, player_name)
        except Exception as e:
            return f"Failed to fetch batter vs team for '{player_name}': {e}"

    @mcp.tool()
    def get_pro_schedule(week: int = 0) -> str:
        """Get MLB pro team schedule — which teams play how many games.

        Essential for streaming pitcher decisions: start pitchers whose teams
        have more games, bench players on off-days.

        Args:
            week: Scoring period/week (0 = current overview)
        """
        from .config import ESPN_S2, ESPN_SWID, ESPN_YEAR

        try:
            data = espn_public_api.get_pro_team_schedule(ESPN_YEAR, ESPN_S2, ESPN_SWID)
            return formatters.fmt_pro_schedule(data, week=week if week > 0 else None)
        except Exception as e:
            return f"Failed to fetch pro team schedule: {e}"

    @mcp.tool()
    def get_league_chat() -> str:
        """Get the league message board — recent messages and trash talk.

        Shows the latest 15 threads with author, date, and message preview.
        """
        from .config import ESPN_S2, ESPN_SWID, ESPN_YEAR, ESPN_LEAGUE_ID

        try:
            data = espn_public_api.get_league_chat(ESPN_YEAR, ESPN_LEAGUE_ID, ESPN_S2, ESPN_SWID)
            return formatters.fmt_league_chat(data)
        except Exception as e:
            return f"Failed to fetch league chat: {e}"
