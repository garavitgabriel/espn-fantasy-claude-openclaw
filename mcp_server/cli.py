"""CLI for ESPN Fantasy Baseball — mirrors MCP server tools."""

import argparse
import sys

from .config import get_league, get_my_team
from . import formatters


def cmd_roster(args):
    league = get_league()
    team = get_my_team(league)
    if not team:
        return "Could not find your team. Check ESPN_TEAM_NAME."
    return formatters.fmt_roster(team)


def cmd_team_roster(args):
    league = get_league()
    name_lower = args.team_name.lower()
    for team in league.teams:
        if name_lower in team.team_name.lower():
            return formatters.fmt_roster(team)
    available = ", ".join(t.team_name for t in league.teams)
    return f"Team '{args.team_name}' not found. Available teams: {available}"


def cmd_matchup(args):
    league = get_league()
    my_team = get_my_team(league)
    if not my_team:
        return "Could not find your team."
    matchup_period = args.week if args.week > 0 else None
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


def cmd_standings(args):
    league = get_league()
    return formatters.fmt_standings(league.standings())


def cmd_free_agents(args):
    league = get_league()
    kwargs = {"size": args.size}
    if args.position:
        kwargs["position"] = args.position.upper()
    players = league.free_agents(**kwargs)
    header = "## Free Agents" + (f" — {args.position.upper()}" if args.position else "") + "\n\n"
    return header + formatters.fmt_free_agents(players)


def cmd_activity(args):
    league = get_league()
    activities = league.recent_activity(size=args.size)
    return "## Recent Activity\n\n" + formatters.fmt_activity(activities)


def cmd_box_scores(args):
    league = get_league()
    matchup_period = args.week if args.week > 0 else None
    try:
        box_scores = league.box_scores(matchup_period=matchup_period)
    except (KeyError, TypeError):
        return "No box score data available yet (season may not have started)."
    return "\n\n---\n\n".join(formatters.fmt_box_score(bs) for bs in box_scores)


def cmd_player(args):
    league = get_league()
    player = league.player_info(name=args.name)
    if player is None:
        return f"Player '{args.name}' not found. Try the exact ESPN name."
    if isinstance(player, list):
        return "\n\n---\n\n".join(formatters.fmt_player_detail(p) for p in player)
    return formatters.fmt_player_detail(player)


def cmd_compare(args):
    league = get_league()
    p1 = league.player_info(name=args.player1)
    p2 = league.player_info(name=args.player2)
    if p1 is None:
        return f"Player '{args.player1}' not found."
    if p2 is None:
        return f"Player '{args.player2}' not found."
    return formatters.fmt_compare(p1, p2)


def cmd_rosters(args):
    league = get_league()
    return "## League Rosters Overview\n\n" + formatters.fmt_league_rosters(league.teams)


def cmd_trade(args):
    league = get_league()
    give_names = [n.strip() for n in args.give.split(",")]
    recv_names = [n.strip() for n in args.receive.split(",")]

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


def cmd_scoring(args):
    league = get_league()
    return formatters.fmt_scoring_categories(league.settings._raw_scoring_settings)


def cmd_slots(args):
    league = get_league()
    data = league.espn_request.get_league()
    slot_counts = data['settings'].get('rosterSettings', {}).get('lineupSlotCounts', {})
    return formatters.fmt_roster_slots(slot_counts)


def cmd_draft(args):
    league = get_league()
    data = league.espn_request.get_league()
    draft_settings = data['settings'].get('draftSettings', {})
    slot_counts = data['settings'].get('rosterSettings', {}).get('lineupSlotCounts', {})
    result = formatters.fmt_draft_board(league.draft, league.teams, draft_settings)
    my_team = get_my_team(league)
    if my_team and league.draft:
        result += "\n\n---\n\n" + formatters.fmt_roster_needs(my_team, slot_counts)
    return result


def cmd_needs(args):
    league = get_league()
    my_team = get_my_team(league)
    if not my_team:
        return "Could not find your team. Check ESPN_TEAM_NAME."
    data = league.espn_request.get_league()
    slot_counts = data['settings'].get('rosterSettings', {}).get('lineupSlotCounts', {})
    return formatters.fmt_roster_needs(my_team, slot_counts)


def cmd_refresh(args):
    import mcp_server.config as cfg
    league = get_league()
    league.refresh()
    cfg._league_instance = league
    return "League data refreshed successfully. Current week: " + str(league.current_week)


def main():
    parser = argparse.ArgumentParser(
        prog="espn-cli",
        description="ESPN Fantasy Baseball CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # roster
    sub.add_parser("roster", help="Show my roster")

    # team-roster
    p = sub.add_parser("team-roster", help="Show a team's roster")
    p.add_argument("team_name", help="Full or partial team name")

    # matchup
    p = sub.add_parser("matchup", help="Show my current matchup")
    p.add_argument("--week", type=int, default=0, help="Matchup week (0=current)")

    # standings
    sub.add_parser("standings", help="Show league standings")

    # free-agents
    p = sub.add_parser("free-agents", help="Show best available free agents")
    p.add_argument("--position", default="", help="Position filter (C, 1B, SS, OF, SP, ...)")
    p.add_argument("--size", type=int, default=25, help="Number of results")

    # activity
    p = sub.add_parser("activity", help="Show recent league activity")
    p.add_argument("--size", type=int, default=25, help="Number of transactions")

    # box-scores
    p = sub.add_parser("box-scores", help="Show all matchup box scores")
    p.add_argument("--week", type=int, default=0, help="Matchup week (0=current)")

    # player
    p = sub.add_parser("player", help="Show detailed player info")
    p.add_argument("name", help="Player's full name")

    # compare
    p = sub.add_parser("compare", help="Compare two players side-by-side")
    p.add_argument("player1", help="First player's full name")
    p.add_argument("player2", help="Second player's full name")

    # rosters
    sub.add_parser("rosters", help="Overview of all league rosters")

    # trade
    p = sub.add_parser("trade", help="Analyze a potential trade")
    p.add_argument("--give", required=True, help="Comma-separated player names to give")
    p.add_argument("--receive", required=True, help="Comma-separated player names to receive")

    # scoring
    sub.add_parser("scoring", help="Show league scoring categories")

    # slots
    sub.add_parser("slots", help="Show roster slot configuration")

    # draft
    sub.add_parser("draft", help="Show draft board and auction budgets")

    # needs
    sub.add_parser("needs", help="Show my roster position needs")

    # refresh
    sub.add_parser("refresh", help="Refresh league data from ESPN")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "roster": cmd_roster,
        "team-roster": cmd_team_roster,
        "matchup": cmd_matchup,
        "standings": cmd_standings,
        "free-agents": cmd_free_agents,
        "activity": cmd_activity,
        "box-scores": cmd_box_scores,
        "player": cmd_player,
        "compare": cmd_compare,
        "rosters": cmd_rosters,
        "trade": cmd_trade,
        "scoring": cmd_scoring,
        "slots": cmd_slots,
        "draft": cmd_draft,
        "needs": cmd_needs,
        "refresh": cmd_refresh,
    }

    handler = dispatch[args.command]
    print(handler(args))


if __name__ == "__main__":
    main()
