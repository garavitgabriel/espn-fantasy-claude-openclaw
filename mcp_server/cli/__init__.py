"""ESPN Fantasy Baseball CLI — mirrors MCP server tools."""

import typer
from rich.console import Console

from mcp_server.config import (
    describe_available_teams,
    get_league,
    get_my_team,
    get_my_team_error,
    resolve_team,
)
from mcp_server import formatters
from mcp_server import write_ops
from mcp_server.cli.auth import app as auth_app
from mcp_server.cli.build_plugin import app as build_plugin_app

app = typer.Typer(
    name="espn",
    help="ESPN Fantasy Baseball CLI",
    no_args_is_help=True,
)
console = Console()

app.add_typer(auth_app, name="auth", help="Authentication commands")
app.add_typer(build_plugin_app, name="build-plugin", help="Build plugin bundles")


# ---------------------------------------------------------------------------
# League data commands (top-level)
# ---------------------------------------------------------------------------


@app.command()
def roster(
    team: str = typer.Option(None, "--team", "-t", help="Team name (default: my team)"),
) -> None:
    """Show a team's roster."""
    league = get_league()
    if team:
        t = resolve_team(league, team)
        if not t:
            console.print(f"Team '{team}' not found. Available: {describe_available_teams(league)}")
            raise typer.Exit(1)
    else:
        t = get_my_team(league)
        if not t:
            console.print(get_my_team_error(league))
            raise typer.Exit(1)
    console.print(formatters.fmt_roster(t))


@app.command()
def matchup(
    week: int = typer.Option(0, "--week", "-w", help="Matchup week (0=current)"),
) -> None:
    """Show my current matchup."""
    league = get_league()
    my_team = get_my_team(league)
    if not my_team:
        console.print(get_my_team_error(league))
        raise typer.Exit(1)
    matchup_period = week if week > 0 else None
    try:
        box_scores = league.box_scores(matchup_period=matchup_period)
    except (KeyError, TypeError):
        console.print("No matchup data available yet (season may not have started).")
        raise typer.Exit(1)
    for bs in box_scores:
        home = bs.home_team
        away = bs.away_team
        home_id = home.team_id if hasattr(home, "team_id") else home
        away_id = away.team_id if hasattr(away, "team_id") else away
        if home_id == my_team.team_id or away_id == my_team.team_id:
            console.print(formatters.fmt_box_score(bs))
            return
    console.print("Could not find your matchup this week.")


@app.command()
def standings() -> None:
    """Show league standings."""
    league = get_league()
    console.print(formatters.fmt_standings(league.standings()))


@app.command(name="free-agents")
def free_agents(
    position: str = typer.Option("", "--position", "-p", help="Position filter (C, 1B, SS, OF, SP, ...)"),
    size: int = typer.Option(25, "--size", "-s", help="Number of results"),
) -> None:
    """Show best available free agents."""
    league = get_league()
    kwargs: dict = {"size": size}
    if position:
        kwargs["position"] = position.upper()
    players = league.free_agents(**kwargs)
    header = "## Free Agents" + (f" — {position.upper()}" if position else "") + "\n\n"
    console.print(header + formatters.fmt_free_agents(players))


@app.command()
def activity(
    size: int = typer.Option(25, "--size", "-s", help="Number of transactions"),
    team: str = typer.Option("", "--team", "-t", help="Filter to a team (partial match)"),
    scoring_period: int = typer.Option(0, "--period", "-p", help="Filter to a matchup period (0=no filter)"),
) -> None:
    """Show recent league activity."""
    from mcp_server.tools import _activity_matches

    league = get_league()
    team_obj = None
    if team:
        team_obj = resolve_team(league, team)
        if not team_obj:
            console.print(f"Team '{team}' not found. Available: {describe_available_teams(league)}")
            raise typer.Exit(1)

    fetch_size = max(size, 200) if scoring_period > 0 or team_obj else size
    activities = league.recent_activity(size=fetch_size)
    filtered = [act for act in activities if _activity_matches(act, team_obj, scoring_period, league)]
    if size and len(filtered) > size and not team_obj and scoring_period == 0:
        filtered = filtered[:size]

    header_bits = []
    if team_obj:
        header_bits.append(team_obj.team_name)
    if scoring_period > 0:
        header_bits.append(f"matchup period {scoring_period}")
    suffix = f"filtered: {', '.join(header_bits)}" if header_bits else ""
    console.print("## Recent Activity\n\n" + formatters.fmt_activity(filtered, title_suffix=suffix))


@app.command(name="box-scores")
def box_scores(
    week: int = typer.Option(0, "--week", "-w", help="Matchup week (0=current)"),
) -> None:
    """Show all matchup box scores."""
    league = get_league()
    matchup_period = week if week > 0 else None
    try:
        scores = league.box_scores(matchup_period=matchup_period)
    except (KeyError, TypeError):
        console.print("No box score data available yet (season may not have started).")
        raise typer.Exit(1)
    console.print("\n\n---\n\n".join(formatters.fmt_box_score(bs) for bs in scores))


@app.command()
def player(
    name: str = typer.Argument(..., help="Player's full name"),
) -> None:
    """Show detailed player info."""
    league = get_league()
    p = league.player_info(name=name)
    if p is None:
        console.print(f"Player '{name}' not found. Try the exact ESPN name.")
        raise typer.Exit(1)
    if isinstance(p, list):
        console.print("\n\n---\n\n".join(formatters.fmt_player_detail(x) for x in p))
    else:
        console.print(formatters.fmt_player_detail(p))


@app.command()
def compare(
    player1: str = typer.Argument(..., help="First player's full name"),
    player2: str = typer.Argument(..., help="Second player's full name"),
) -> None:
    """Compare two players side-by-side."""
    league = get_league()
    p1 = league.player_info(name=player1)
    p2 = league.player_info(name=player2)
    if p1 is None:
        console.print(f"Player '{player1}' not found.")
        raise typer.Exit(1)
    if p2 is None:
        console.print(f"Player '{player2}' not found.")
        raise typer.Exit(1)
    console.print(formatters.fmt_compare(p1, p2))


@app.command()
def rosters() -> None:
    """Overview of all league rosters."""
    league = get_league()
    console.print("## League Rosters Overview\n\n" + formatters.fmt_league_rosters(league.teams))


@app.command()
def trade(
    give: str = typer.Option(..., "--give", "-g", help="Comma-separated player names to give"),
    receive: str = typer.Option(..., "--receive", "-r", help="Comma-separated player names to receive"),
) -> None:
    """Analyze a potential trade."""
    league = get_league()
    give_names = [n.strip() for n in give.split(",")]
    recv_names = [n.strip() for n in receive.split(",")]

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
        console.print("Errors: " + "; ".join(errors))
        raise typer.Exit(1)

    console.print(formatters.fmt_trade_analysis(give_list, recv_list))


@app.command()
def scoring() -> None:
    """Show league scoring categories."""
    league = get_league()
    console.print(formatters.fmt_scoring_categories(league.settings._raw_scoring_settings))


@app.command()
def slots() -> None:
    """Show roster slot configuration."""
    league = get_league()
    data = league.espn_request.get_league()
    slot_counts = data["settings"].get("rosterSettings", {}).get("lineupSlotCounts", {})
    console.print(formatters.fmt_roster_slots(slot_counts))


@app.command()
def draft() -> None:
    """Show draft board and auction budgets."""
    league = get_league()
    data = league.espn_request.get_league()
    draft_settings = data["settings"].get("draftSettings", {})
    slot_counts = data["settings"].get("rosterSettings", {}).get("lineupSlotCounts", {})
    result = formatters.fmt_draft_board(league.draft, league.teams, draft_settings)
    my_team = get_my_team(league)
    if not my_team:
        result += "\n\n---\n\n" + get_my_team_error(league)
    elif league.draft:
        result += "\n\n---\n\n" + formatters.fmt_roster_needs(my_team, slot_counts)
    console.print(result)


@app.command()
def needs() -> None:
    """Show my roster position needs."""
    league = get_league()
    my_team = get_my_team(league)
    if not my_team:
        console.print(get_my_team_error(league))
        raise typer.Exit(1)
    data = league.espn_request.get_league()
    slot_counts = data["settings"].get("rosterSettings", {}).get("lineupSlotCounts", {})
    console.print(formatters.fmt_roster_needs(my_team, slot_counts))


@app.command()
def refresh() -> None:
    """Refresh league data from ESPN."""
    import mcp_server.config as cfg

    league = get_league()
    league.refresh()
    cfg._league_instance = league
    console.print(f"League data refreshed successfully. Current week: {league.current_week}")


# ---------------------------------------------------------------------------
# Phase B — New commands
# ---------------------------------------------------------------------------


@app.command()
def schedule(
    team: str = typer.Option("", "--team", "-t", help="Team name (default: my team)"),
) -> None:
    """Show a team's full season schedule with results."""
    league = get_league()
    if team:
        t = resolve_team(league, team)
        if not t:
            console.print(f"Team '{team}' not found. Available: {describe_available_teams(league)}")
            raise typer.Exit(1)
    else:
        t = get_my_team(league)
        if not t:
            console.print(get_my_team_error(league))
            raise typer.Exit(1)
    try:
        league.scoreboard()
    except Exception:
        pass
    console.print(formatters.fmt_schedule(t, current_week=league.current_week))


@app.command()
def settings() -> None:
    """Show comprehensive league settings (playoffs, trades, FAAB, divisions)."""
    league = get_league()
    console.print(formatters.fmt_league_settings(league.settings))


@app.command()
def search(
    query: str = typer.Argument(..., help="Partial player name to search"),
) -> None:
    """Search for players by partial name (fuzzy matching)."""
    import difflib

    league = get_league()
    query_lower = query.lower()

    matching_names = [
        name for name in league.player_map.keys()
        if isinstance(name, str) and query_lower in name.lower()
    ]
    if len(matching_names) < 3:
        all_names = [n for n in league.player_map.keys() if isinstance(n, str)]
        fuzzy = difflib.get_close_matches(query, all_names, n=10, cutoff=0.5)
        for name in fuzzy:
            if name not in matching_names:
                matching_names.append(name)

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

    console.print(formatters.fmt_player_search(players[:10], query))


@app.command()
def scoreboard(
    week: int = typer.Option(0, "--week", "-w", help="Matchup week (0=current)"),
) -> None:
    """Show matchup scoreboard with scores and winners."""
    league = get_league()
    matchup_period = week if week > 0 else None
    try:
        matchups = league.scoreboard(matchupPeriod=matchup_period)
    except Exception as e:
        console.print(f"No scoreboard data available: {e}")
        raise typer.Exit(1)

    if not matchups:
        console.print("No matchups found for this week.")
        return

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

    console.print("\n".join(lines))


# ---------------------------------------------------------------------------
# Phase C — ESPN public API commands
# ---------------------------------------------------------------------------


@app.command()
def news(
    name: str = typer.Argument(..., help="Player's full name"),
) -> None:
    """Get latest news, injury status, and next game for a player."""
    from mcp_server import espn_public_api

    league = get_league()
    athlete_id = espn_public_api.resolve_athlete_id(league, name)
    if not athlete_id:
        console.print(f"Could not find ESPN athlete ID for '{name}'.")
        raise typer.Exit(1)
    try:
        data = espn_public_api.get_player_overview(athlete_id)
        console.print(formatters.fmt_player_news(data, name))
    except Exception as e:
        console.print(f"Failed to fetch news: {e}")
        raise typer.Exit(1)


@app.command()
def splits(
    name: str = typer.Argument(..., help="Player's full name"),
    season: int = typer.Option(0, "--season", "-s", help="Season year (0=current)"),
) -> None:
    """Get player splits: vs LHP/RHP, home/away, by month, etc."""
    from mcp_server import espn_public_api

    league = get_league()
    athlete_id = espn_public_api.resolve_athlete_id(league, name)
    if not athlete_id:
        console.print(f"Could not find ESPN athlete ID for '{name}'.")
        raise typer.Exit(1)
    try:
        data = espn_public_api.get_player_splits(athlete_id, season=season if season > 0 else None)
        console.print(formatters.fmt_player_splits(data, name))
    except Exception as e:
        console.print(f"Failed to fetch splits: {e}")
        raise typer.Exit(1)


@app.command()
def gamelog(
    name: str = typer.Argument(..., help="Player's full name"),
    category: str = typer.Option("", "--category", "-c", help="batting or pitching"),
) -> None:
    """Get a player's game-by-game stats (last 20 games)."""
    from mcp_server import espn_public_api

    league = get_league()
    athlete_id = espn_public_api.resolve_athlete_id(league, name)
    if not athlete_id:
        console.print(f"Could not find ESPN athlete ID for '{name}'.")
        raise typer.Exit(1)
    try:
        data = espn_public_api.get_player_gamelog(athlete_id, category=category if category else None)
        console.print(formatters.fmt_player_gamelog(data, name))
    except Exception as e:
        console.print(f"Failed to fetch game log: {e}")
        raise typer.Exit(1)


@app.command(name="mlb-games")
def mlb_games(
    date: str = typer.Option("", "--date", "-d", help="Date in YYYYMMDD format (empty=today)"),
) -> None:
    """Show today's MLB games with scores and status."""
    from mcp_server import espn_public_api

    if not date:
        from datetime import datetime
        date = datetime.now().strftime("%Y%m%d")
    try:
        data = espn_public_api.get_mlb_games(date)
        console.print(formatters.fmt_mlb_games(data, date))
    except Exception as e:
        console.print(f"Failed to fetch MLB games: {e}")
        raise typer.Exit(1)


@app.command(name="vs-team")
def vs_team(
    name: str = typer.Argument(..., help="Batter's full name"),
    opponent: str = typer.Option("", "--opponent", "-o", help="Team abbrev (e.g. SEA). Empty = auto-detect."),
) -> None:
    """Get a batter's stats vs a specific team's pitchers."""
    from mcp_server import espn_public_api

    league = get_league()
    athlete_id = espn_public_api.resolve_athlete_id(league, name)
    if not athlete_id:
        console.print(f"Could not find ESPN athlete ID for '{name}'.")
        raise typer.Exit(1)
    try:
        data = espn_public_api.get_batter_vs_team(athlete_id, opponent_team=opponent or None)
        body = formatters.fmt_batter_vs_team(data, name)
        if opponent:
            display = (data.get("statistics", {}) or {}).get("displayName", "") or ""
            if opponent.strip().upper() not in display.upper():
                body = (
                    f"> ⚠️ Requested team `{opponent}` but ESPN returned data for: "
                    f"`{display or 'unknown'}`. Treat as auto-detected.\n\n"
                ) + body
        console.print(body)
    except Exception as e:
        console.print(f"Failed to fetch batter vs team: {e}")
        raise typer.Exit(1)


@app.command(name="probable-pitchers")
def probable_pitchers(
    date: str = typer.Option("", "--date", "-d", help="Date in YYYYMMDD format (empty=today)"),
) -> None:
    """Show probable starting pitchers for all MLB games on a date."""
    from mcp_server import espn_public_api

    if not date:
        from datetime import datetime
        date = datetime.now().strftime("%Y%m%d")
    try:
        data = espn_public_api.get_mlb_scoreboard(date)
        console.print(formatters.fmt_probable_pitchers(data, date))
    except Exception as e:
        console.print(f"Failed to fetch probable pitchers: {e}")
        raise typer.Exit(1)


@app.command(name="sp-schedule")
def sp_schedule(
    name: str = typer.Argument(..., help="Pitcher's full name"),
) -> None:
    """Show a pitcher's next scheduled start."""
    from mcp_server import espn_public_api

    league = get_league()
    athlete_id = espn_public_api.resolve_athlete_id(league, name)
    if not athlete_id:
        console.print(f"Could not find ESPN athlete ID for '{name}'.")
        raise typer.Exit(1)
    try:
        data = espn_public_api.get_player_overview(athlete_id)
        console.print(formatters.fmt_sp_schedule(data, name))
    except Exception as e:
        console.print(f"Failed to fetch next start: {e}")
        raise typer.Exit(1)


@app.command(name="weekly-moves")
def weekly_moves(
    team: str = typer.Option("", "--team", "-t", help="Team name (default: my team)"),
    scoring_period: int = typer.Option(0, "--period", "-p", help="Matchup period (0=current)"),
) -> None:
    """Show add/drop count for a team in a matchup period."""
    from mcp_server.tools import _matchup_period_for_date

    league = get_league()
    if team:
        t = resolve_team(league, team)
        if not t:
            console.print(f"Team '{team}' not found. Available: {describe_available_teams(league)}")
            raise typer.Exit(1)
    else:
        t = get_my_team(league)
        if not t:
            console.print(get_my_team_error(league))
            raise typer.Exit(1)

    target_period = scoring_period if scoring_period > 0 else league.currentMatchupPeriod
    activities = league.recent_activity(size=200)
    moves_used = 0
    move_actions = {"FA ADDED", "WAIVER ADDED", "DROPPED"}
    for act in activities:
        mp = _matchup_period_for_date(league, getattr(act, "date", None))
        if mp != target_period:
            continue
        for action in act.actions:
            team_obj = action[0] if action else None
            if getattr(team_obj, "team_id", None) != t.team_id:
                continue
            action_type = action[1] if len(action) > 1 else ""
            if action_type in move_actions:
                moves_used += 1

    raw_acq = {}
    try:
        data = league.espn_request.get_league()
        raw_acq = data.get("settings", {}).get("acquisitionSettings", {}) or {}
    except Exception:
        raw_acq = {}
    move_limit = raw_acq.get("matchupAcquisitionLimit") or raw_acq.get("acquisitionLimitPerMatchup")
    if not isinstance(move_limit, int) or move_limit <= 0:
        move_limit = None

    console.print(formatters.fmt_weekly_moves(t.team_name, target_period, moves_used, move_limit))


@app.command(name="pro-schedule")
def pro_schedule(
    days: int = typer.Option(7, "--days", "-d", help="Days to look ahead (default 7)"),
) -> None:
    """Show MLB pro team schedule — games per team over the next N days."""
    from mcp_server import espn_public_api
    from mcp_server.config import ESPN_S2, ESPN_SWID, ESPN_YEAR

    league = get_league()
    try:
        data = espn_public_api.get_pro_team_schedule(ESPN_YEAR, ESPN_S2, ESPN_SWID)
        console.print(formatters.fmt_pro_schedule(
            data,
            current_scoring_period=league.scoringPeriodId,
            days=days,
        ))
    except Exception as e:
        console.print(f"Failed to fetch pro schedule: {e}")
        raise typer.Exit(1)


@app.command()
def chat() -> None:
    """Show league message board / chat."""
    from mcp_server import espn_public_api
    from mcp_server.config import ESPN_S2, ESPN_SWID, ESPN_YEAR, ESPN_LEAGUE_ID

    try:
        data = espn_public_api.get_league_chat(ESPN_YEAR, ESPN_LEAGUE_ID, ESPN_S2, ESPN_SWID)
        console.print(formatters.fmt_league_chat(data))
    except Exception as e:
        console.print(f"Failed to fetch league chat: {e}")
        raise typer.Exit(1)


@app.command(name="verify-auth")
def verify_auth() -> None:
    """Verify cookie auth health without performing any write."""
    league = get_league()
    console.print(write_ops.verify_auth(league))


@app.command(name="set-lineup")
def set_lineup(
    assignments_json: str = typer.Argument(..., help="JSON list of lineup assignment items"),
) -> None:
    """Safely stage or execute lineup slot changes for my team."""
    import json

    league = get_league()
    team = get_my_team(league)
    if not team:
        console.print(get_my_team_error(league))
        raise typer.Exit(1)
    assignments = json.loads(assignments_json)
    console.print(write_ops.set_lineup(league, team, assignments))


@app.command(name="add-drop")
def add_drop(
    add_player: str = typer.Option(..., "--add", help="Player to add"),
    drop_player: str = typer.Option(..., "--drop", help="Player to drop"),
    remaining_moves: int = typer.Option(0, "--remaining-moves", help="Remaining weekly moves"),
) -> None:
    """Safely stage or execute a free-agent add/drop for my team."""
    league = get_league()
    team = get_my_team(league)
    if not team:
        console.print(get_my_team_error(league))
        raise typer.Exit(1)
    add_obj, add_error = _resolve_player(league, add_player)
    if add_error:
        console.print(add_error)
        raise typer.Exit(1)
    drop_obj, drop_error = _resolve_player(league, drop_player)
    if drop_error:
        console.print(drop_error)
        raise typer.Exit(1)
    console.print(write_ops.add_drop(league, team, add_obj, drop_obj, remaining_moves))


@app.command(name="propose-trade")
def propose_trade(
    trade_partner_team_id: int = typer.Option(..., "--partner", help="Trade partner team id"),
    give_player_ids: str = typer.Option(..., "--give", help="Comma-separated player ids to give"),
    receive_player_ids: str = typer.Option(..., "--receive", help="Comma-separated player ids to receive"),
) -> None:
    """Return an approval-required trade proposal object."""
    league = get_league()
    team = get_my_team(league)
    if not team:
        console.print(get_my_team_error(league))
        raise typer.Exit(1)
    give_ids = [int(value.strip()) for value in give_player_ids.split(',') if value.strip()]
    receive_ids = [int(value.strip()) for value in receive_player_ids.split(',') if value.strip()]
    console.print(write_ops.propose_trade(league, team, trade_partner_team_id, give_ids, receive_ids))


@app.command(name="accept-trade")
def accept_trade(
    proposal_id: int = typer.Option(..., "--proposal-id", help="Trade proposal id"),
) -> None:
    """Return an approval-required trade acceptance object."""
    league = get_league()
    team = get_my_team(league)
    if not team:
        console.print(get_my_team_error(league))
        raise typer.Exit(1)
    console.print(write_ops.accept_trade(league, team, proposal_id))


def main() -> None:
    app()
