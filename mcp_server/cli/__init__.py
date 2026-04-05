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
) -> None:
    """Show recent league activity."""
    league = get_league()
    activities = league.recent_activity(size=size)
    console.print("## Recent Activity\n\n" + formatters.fmt_activity(activities))


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
) -> None:
    """Get a batter's stats vs each MLB team."""
    from mcp_server import espn_public_api

    league = get_league()
    athlete_id = espn_public_api.resolve_athlete_id(league, name)
    if not athlete_id:
        console.print(f"Could not find ESPN athlete ID for '{name}'.")
        raise typer.Exit(1)
    try:
        data = espn_public_api.get_batter_vs_team(athlete_id)
        console.print(formatters.fmt_batter_vs_team(data, name))
    except Exception as e:
        console.print(f"Failed to fetch batter vs team: {e}")
        raise typer.Exit(1)


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


def main() -> None:
    app()
