"""Format espn_api objects into markdown tables for AI consumption."""

from espn_api.baseball.constant import POSITION_MAP, STATS_MAP


def fmt_player(p, show_stats=True):
    """Format a single player as a table row."""
    slot = p.lineupSlot or p.position
    injury = f" ({p.injuryStatus})" if p.injuryStatus and p.injuryStatus != "ACTIVE" else ""
    owned = f"{p.percent_owned}%" if p.percent_owned >= 0 else ""
    pts = p.total_points

    row = f"| {p.name}{injury} | {slot} | {p.proTeam} | {pts} | {owned} |"
    return row


def fmt_roster(team):
    """Format a team's roster as a markdown table."""
    lines = [
        f"## {team.team_name} ({team.wins}-{team.losses}-{team.ties})",
        "",
        "| Player | Slot | Team | Points | %Own |",
        "|--------|------|------|--------|------|",
    ]

    starters = []
    bench = []
    il = []
    for p in team.roster:
        slot = p.lineupSlot or ""
        if slot == "BE":
            bench.append(p)
        elif slot == "IL":
            il.append(p)
        else:
            starters.append(p)

    if starters:
        lines.append("| **Starters** | | | | |")
        for p in starters:
            lines.append(fmt_player(p))
    if bench:
        lines.append("| **Bench** | | | | |")
        for p in bench:
            lines.append(fmt_player(p))
    if il:
        lines.append("| **IL** | | | | |")
        for p in il:
            lines.append(fmt_player(p))

    return "\n".join(lines)


def fmt_standings(teams):
    """Format standings as a markdown table."""
    lines = [
        "| # | Team | W | L | T |",
        "|---|------|---|---|---|",
    ]
    for i, team in enumerate(teams, 1):
        lines.append(f"| {i} | {team.team_name} | {team.wins} | {team.losses} | {team.ties} |")
    return "\n".join(lines)


def fmt_free_agents(players):
    """Format free agents list."""
    lines = [
        "| Player | Pos | Team | Points | %Own | %Start |",
        "|--------|-----|------|--------|------|--------|",
    ]
    for p in players:
        pos = p.position
        owned = f"{p.percent_owned}%" if p.percent_owned >= 0 else ""
        started = f"{p.percent_started}%" if p.percent_started >= 0 else ""
        lines.append(f"| {p.name} | {pos} | {p.proTeam} | {p.total_points} | {owned} | {started} |")
    return "\n".join(lines)


def fmt_matchup_h2h_category(box_score):
    """Format an H2H Category matchup."""
    home = box_score.home_team
    away = box_score.away_team
    home_name = home.team_name if hasattr(home, 'team_name') else str(home)
    away_name = away.team_name if hasattr(away, 'team_name') else str(away)

    lines = [
        f"## {away_name} vs {home_name}",
        "",
    ]

    # Check if we have category stats
    if hasattr(box_score, 'home_stats') and box_score.home_stats:
        lines.append(f"**Score: {away_name} {getattr(box_score, 'away_wins', '?')}-{getattr(box_score, 'home_wins', '?')}-{getattr(box_score, 'home_ties', '?')} {home_name}**")
        lines.append("")
        lines.append(f"| Category | {away_name} | {home_name} | Winner |")
        lines.append("|----------|------------|------------|--------|")

        home_stats = box_score.home_stats
        away_stats = getattr(box_score, 'away_stats', {}) or {}

        for cat in home_stats:
            h_val = home_stats[cat]['value']
            h_result = home_stats[cat]['result']
            a_val = away_stats.get(cat, {}).get('value', '')
            # Format nicely
            if isinstance(h_val, float):
                h_display = f"{h_val:.3f}" if h_val < 1 else f"{h_val:.2f}"
            else:
                h_display = str(h_val)
            if isinstance(a_val, float):
                a_display = f"{a_val:.3f}" if a_val < 1 else f"{a_val:.2f}"
            else:
                a_display = str(a_val)

            if h_result == "WIN":
                winner = home_name
            elif h_result == "LOSS":
                winner = away_name
            else:
                winner = "TIE"
            lines.append(f"| {cat} | {a_display} | {h_display} | {winner} |")
    else:
        lines.append("No category data available for this matchup.")

    return "\n".join(lines)


def fmt_box_score(box_score):
    """Format any box score type."""
    if hasattr(box_score, 'home_stats'):
        return fmt_matchup_h2h_category(box_score)
    # Fallback for points-based
    home = box_score.home_team
    away = box_score.away_team
    home_name = home.team_name if hasattr(home, 'team_name') else str(home)
    away_name = away.team_name if hasattr(away, 'team_name') else str(away)
    home_score = getattr(box_score, 'home_score', '?')
    away_score = getattr(box_score, 'away_score', '?')
    return f"**{away_name}** {away_score} - {home_score} **{home_name}**"


def fmt_activity(activities):
    """Format recent activity."""
    lines = [
        "| Date | Action | Player | Team |",
        "|------|--------|--------|------|",
    ]
    for act in activities:
        for action in act.actions:
            team_name = action[0].team_name if hasattr(action[0], 'team_name') else str(action[0])
            action_type = action[1]
            player_name = action[2] if len(action) > 2 else ""
            lines.append(f"| {act.date} | {action_type} | {player_name} | {team_name} |")
    return "\n".join(lines)


def fmt_player_detail(player):
    """Format detailed player info."""
    lines = [
        f"## {player.name}",
        f"- **Position:** {player.position}",
        f"- **Team:** {player.proTeam}",
        f"- **Injury:** {player.injuryStatus or 'Healthy'}",
        f"- **% Owned:** {player.percent_owned}%",
        f"- **Total Points:** {player.total_points}",
        "",
    ]

    # Season stats (scoring period 0)
    season_stats = player.stats.get(0, {})
    breakdown = season_stats.get('breakdown', {})
    if breakdown:
        lines.append("### Season Stats")
        lines.append("| Stat | Value |")
        lines.append("|------|-------|")
        for stat, val in sorted(breakdown.items()):
            if isinstance(val, float):
                display = f"{val:.3f}" if abs(val) < 1 and val != 0 else f"{val:.1f}"
            else:
                display = str(val)
            lines.append(f"| {stat} | {display} |")

    return "\n".join(lines)


def fmt_compare(p1, p2):
    """Side-by-side comparison table for two players."""
    lines = [
        f"## {p1.name} vs {p2.name}",
        "",
        f"| Attribute | {p1.name} | {p2.name} |",
        "|-----------|-----------|-----------|",
        f"| Position | {p1.position} | {p2.position} |",
        f"| Team | {p1.proTeam} | {p2.proTeam} |",
        f"| Total Points | {p1.total_points} | {p2.total_points} |",
        f"| % Owned | {p1.percent_owned}% | {p2.percent_owned}% |",
        f"| Injury | {p1.injuryStatus or 'Healthy'} | {p2.injuryStatus or 'Healthy'} |",
        "",
    ]

    s1 = p1.stats.get(0, {}).get('breakdown', {})
    s2 = p2.stats.get(0, {}).get('breakdown', {})
    all_stats = sorted(set(list(s1.keys()) + list(s2.keys())))

    if all_stats:
        lines.append("### Season Stats")
        lines.append(f"| Stat | {p1.name} | {p2.name} |")
        lines.append("|------|-----------|-----------|")
        for stat in all_stats:
            v1 = s1.get(stat, "—")
            v2 = s2.get(stat, "—")
            if isinstance(v1, float):
                v1 = f"{v1:.3f}" if abs(v1) < 1 and v1 != 0 else f"{v1:.1f}"
            if isinstance(v2, float):
                v2 = f"{v2:.3f}" if abs(v2) < 1 and v2 != 0 else f"{v2:.1f}"
            lines.append(f"| {stat} | {v1} | {v2} |")

    return "\n".join(lines)


def fmt_trade_analysis(give_list, recv_list):
    """Format a trade evaluation table."""
    lines = [
        "## Trade Analysis",
        "",
        "### You Give",
        "| Player | Pos | Team | Points | %Own |",
        "|--------|-----|------|--------|------|",
    ]
    give_total = 0
    for p in give_list:
        give_total += p.total_points
        lines.append(f"| {p.name} | {p.position} | {p.proTeam} | {p.total_points} | {p.percent_owned}% |")

    lines += [
        "",
        "### You Receive",
        "| Player | Pos | Team | Points | %Own |",
        "|--------|-----|------|--------|------|",
    ]
    recv_total = 0
    for p in recv_list:
        recv_total += p.total_points
        lines.append(f"| {p.name} | {p.position} | {p.proTeam} | {p.total_points} | {p.percent_owned}% |")

    diff = recv_total - give_total
    sign = "+" if diff >= 0 else ""
    lines += [
        "",
        f"**Points differential: {sign}{diff:.1f}** (receive - give)",
    ]

    return "\n".join(lines)


def fmt_league_rosters(teams):
    """Brief overview of all teams."""
    lines = [
        "| Team | W-L-T | Roster Size | Key Players |",
        "|------|-------|-------------|-------------|",
    ]
    for team in teams:
        record = f"{team.wins}-{team.losses}-{team.ties}"
        size = len(team.roster)
        # Top 3 by points
        top = sorted(team.roster, key=lambda p: p.total_points, reverse=True)[:3]
        key = ", ".join(p.name for p in top)
        lines.append(f"| {team.team_name} | {record} | {size} | {key} |")
    return "\n".join(lines)


def fmt_scoring_categories(raw_scoring_settings):
    """Format the league's H2H scoring categories from raw settings."""
    items = raw_scoring_settings.get('scoringItems', [])
    if not items:
        return "No scoring categories found."

    hitting = []
    pitching = []
    for item in items:
        stat_id = item['statId']
        name = STATS_MAP.get(stat_id, f"stat_{stat_id}")
        reverse = item.get('isReverseItem', False)
        direction = "lower wins" if reverse else "higher wins"
        entry = (name, direction)
        # Pitching stats start at stat ID 32
        if stat_id >= 32:
            pitching.append(entry)
        else:
            hitting.append(entry)

    lines = [
        f"## Scoring Categories ({len(items)} total: {len(hitting)} hitting, {len(pitching)} pitching)",
        "",
        "### Hitting",
        "| Category | Direction |",
        "|----------|-----------|",
    ]
    for name, direction in hitting:
        lines.append(f"| {name} | {direction} |")

    lines += [
        "",
        "### Pitching",
        "| Category | Direction |",
        "|----------|-----------|",
    ]
    for name, direction in pitching:
        lines.append(f"| {name} | {direction} |")

    return "\n".join(lines)


def fmt_roster_slots(lineup_slot_counts):
    """Format roster slot configuration from raw lineupSlotCounts."""
    active = []
    bench_il = []
    total_active = 0

    for slot_id_str, count in sorted(lineup_slot_counts.items(), key=lambda x: int(x[0])):
        if count == 0:
            continue
        slot_id = int(slot_id_str)
        pos = POSITION_MAP.get(slot_id, f"Unknown({slot_id})")
        if slot_id in (16, 17):  # BE, IL
            bench_il.append((pos, count))
        else:
            active.append((pos, count))
            total_active += count

    lines = [
        f"## Roster Configuration ({total_active} active slots)",
        "",
        "### Active Lineup",
        "| Position | Slots |",
        "|----------|-------|",
    ]
    for pos, count in active:
        lines.append(f"| {pos} | {count} |")

    lines += [
        "",
        "### Bench & IL",
        "| Type | Slots |",
        "|------|-------|",
    ]
    for pos, count in bench_il:
        lines.append(f"| {pos} | {count} |")

    return "\n".join(lines)


def fmt_draft_board(draft_picks, teams, draft_settings):
    """Format draft results with auction prices and team budgets."""
    draft_type = draft_settings.get('type', 'UNKNOWN')
    budget = draft_settings.get('auctionBudget', 0)

    if not draft_picks:
        lines = [
            f"## Draft Board ({draft_type})",
            "",
        ]
        if draft_type == 'AUCTION':
            lines.append(f"**Budget:** ${budget} per team")
            lines.append("")
        lines.append("Draft has not happened yet. No picks recorded.")
        return "\n".join(lines)

    # Build spending tracker per team
    team_spent = {}
    team_picks = {}
    for team in teams:
        team_spent[team.team_id] = 0
        team_picks[team.team_id] = 0

    lines = [
        f"## Draft Board ({draft_type})",
        "",
    ]

    if draft_type == 'AUCTION':
        lines += [
            f"**Budget:** ${budget} per team",
            "",
            "### Picks",
            "| # | Player | Team | Price | Keeper |",
            "|---|--------|------|-------|--------|",
        ]
        for i, pick in enumerate(draft_picks, 1):
            team_name = pick.team.team_name if pick.team else "?"
            keeper = "Yes" if pick.keeper_status else ""
            price = f"${pick.bid_amount}" if pick.bid_amount else "$0"
            lines.append(f"| {i} | {pick.playerName} | {team_name} | {price} | {keeper} |")
            if pick.team:
                team_spent[pick.team.team_id] = team_spent.get(pick.team.team_id, 0) + (pick.bid_amount or 0)
                team_picks[pick.team.team_id] = team_picks.get(pick.team.team_id, 0) + 1

        lines += [
            "",
            "### Team Budgets",
            "| Team | Spent | Remaining | Picks |",
            "|------|-------|-----------|-------|",
        ]
        for team in sorted(teams, key=lambda t: team_spent.get(t.team_id, 0), reverse=True):
            spent = team_spent.get(team.team_id, 0)
            remaining = budget - spent
            picks = team_picks.get(team.team_id, 0)
            lines.append(f"| {team.team_name} | ${spent} | ${remaining} | {picks} |")
    else:
        # Snake/standard draft
        lines += [
            "### Picks",
            "| Round | Pick | Player | Team |",
            "|-------|------|--------|------|",
        ]
        for pick in draft_picks:
            team_name = pick.team.team_name if pick.team else "?"
            lines.append(f"| {pick.round_num} | {pick.round_pick} | {pick.playerName} | {team_name} |")

    return "\n".join(lines)


def fmt_roster_needs(team, lineup_slot_counts):
    """Analyze a team's roster against required slots to find gaps."""
    # Count filled positions
    filled = {}
    for p in team.roster:
        slot = p.lineupSlot or ""
        if slot and slot not in ("BE", "IL"):
            filled[slot] = filled.get(slot, 0) + 1

    lines = [
        f"## Roster Needs — {team.team_name}",
        "",
        "| Position | Required | Filled | Need |",
        "|----------|----------|--------|------|",
    ]

    total_needs = 0
    for slot_id_str, count in sorted(lineup_slot_counts.items(), key=lambda x: int(x[0])):
        if count == 0:
            continue
        slot_id = int(slot_id_str)
        if slot_id in (16, 17):  # Skip BE, IL
            continue
        pos = POSITION_MAP.get(slot_id, f"Unknown({slot_id})")
        current = filled.get(pos, 0)
        need = max(0, count - current)
        total_needs += need
        status = f"**{need}**" if need > 0 else "0"
        lines.append(f"| {pos} | {count} | {current} | {status} |")

    lines += [
        "",
        f"**Total empty slots: {total_needs}**",
    ]

    return "\n".join(lines)
