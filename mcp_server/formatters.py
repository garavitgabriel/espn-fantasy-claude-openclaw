"""Format espn_api objects into markdown tables for AI consumption."""

from espn_api.baseball.constant import POSITION_MAP, STATS_MAP


def _fmt_owned(percent_owned):
    """Format percent owned, handling -1 (unknown) as —."""
    if percent_owned is None or percent_owned < 0:
        return "—"
    return f"{percent_owned}%"


def _fmt_started(percent_started):
    """Format percent started, handling -1 (unknown) as —."""
    if percent_started is None or percent_started < 0:
        return "—"
    return f"{percent_started}%"


def _fmt_stat_value(val):
    """Format a stat value for display."""
    if isinstance(val, float):
        return f"{val:.3f}" if abs(val) < 1 and val != 0 else f"{val:.1f}"
    return str(val)


def fmt_player(p, show_stats=True):
    """Format a single player as a table row."""
    slot = p.lineupSlot or p.position
    injury = f" ({p.injuryStatus})" if p.injuryStatus and p.injuryStatus != "ACTIVE" else ""
    owned = _fmt_owned(p.percent_owned)
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
        owned = _fmt_owned(p.percent_owned)
        started = _fmt_started(p.percent_started)
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

    home_stats = getattr(box_score, 'home_stats', None)
    if not home_stats:
        lines.append("No category data available for this matchup.")
        return "\n".join(lines)

    lines.append(f"**Score: {away_name} {getattr(box_score, 'away_wins', '?')}-{getattr(box_score, 'home_wins', '?')}-{getattr(box_score, 'home_ties', '?')} {home_name}**")
    lines.append("")
    lines.append(f"| Category | {away_name} | {home_name} | Winner |")
    lines.append("|----------|------------|------------|--------|")

    away_stats = getattr(box_score, 'away_stats', None) or {}

    for cat in home_stats:
        h_val = home_stats[cat]['value']
        h_result = home_stats[cat]['result']
        a_val = away_stats.get(cat, {}).get('value', '')
        h_display = _fmt_stat_value(h_val)
        a_display = _fmt_stat_value(a_val)

        if h_result == "WIN":
            winner = home_name
        elif h_result == "LOSS":
            winner = away_name
        else:
            winner = "TIE"
        lines.append(f"| {cat} | {a_display} | {h_display} | {winner} |")

    return "\n".join(lines)


def fmt_box_score(box_score):
    """Format any box score type."""
    home_stats = getattr(box_score, 'home_stats', None)
    if home_stats:
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
            team_obj = action[0] if len(action) > 0 else None
            team_name = team_obj.team_name if team_obj and hasattr(team_obj, 'team_name') else str(team_obj or "—")
            action_type = action[1] if len(action) > 1 else "UNKNOWN"
            player_name = action[2] if len(action) > 2 else ""
            lines.append(f"| {act.date} | {action_type} | {player_name} | {team_name} |")
    return "\n".join(lines)


def fmt_player_detail(player):
    """Format detailed player info with season stats, projections, and eligibility."""
    eligible = ", ".join(
        s for s in getattr(player, 'eligibleSlots', [])
        if s not in ('BE', 'IL', 'IR', 'UTIL', 'IF')
    )
    acq = getattr(player, 'acquisitionType', None) or "—"

    lines = [
        f"## {player.name}",
        f"- **Position:** {player.position}",
        f"- **Eligible slots:** {eligible or player.position}",
        f"- **Team:** {player.proTeam}",
        f"- **Injury:** {player.injuryStatus or 'Healthy'}",
        f"- **% Owned:** {_fmt_owned(player.percent_owned)}",
        f"- **% Started:** {_fmt_started(player.percent_started)}",
        f"- **Acquired via:** {acq}",
        f"- **Total Points:** {player.total_points}",
        f"- **Projected Points:** {getattr(player, 'projected_total_points', 0)}",
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
            lines.append(f"| {stat} | {_fmt_stat_value(val)} |")

    # Projected stats
    projected = season_stats.get('projected_breakdown', {})
    if projected:
        lines.append("")
        lines.append("### Projected Stats")
        lines.append("| Stat | Projected |")
        lines.append("|------|-----------|")
        for stat, val in sorted(projected.items()):
            lines.append(f"| {stat} | {_fmt_stat_value(val)} |")

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
        f"| Projected Points | {getattr(p1, 'projected_total_points', 0)} | {getattr(p2, 'projected_total_points', 0)} |",
        f"| % Owned | {_fmt_owned(p1.percent_owned)} | {_fmt_owned(p2.percent_owned)} |",
        f"| % Started | {_fmt_started(p1.percent_started)} | {_fmt_started(p2.percent_started)} |",
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
            if v1 != "—":
                v1 = _fmt_stat_value(v1)
            if v2 != "—":
                v2 = _fmt_stat_value(v2)
            lines.append(f"| {stat} | {v1} | {v2} |")

    return "\n".join(lines)


def fmt_trade_analysis(give_list, recv_list):
    """Format a trade evaluation with points AND category breakdown."""
    lines = [
        "## Trade Analysis",
        "",
        "### You Give",
        "| Player | Pos | Team | Points | Projected | %Own |",
        "|--------|-----|------|--------|-----------|------|",
    ]
    give_total = 0
    give_proj = 0
    for p in give_list:
        give_total += p.total_points
        proj = getattr(p, 'projected_total_points', 0)
        give_proj += proj
        lines.append(f"| {p.name} | {p.position} | {p.proTeam} | {p.total_points} | {proj} | {_fmt_owned(p.percent_owned)} |")

    lines += [
        "",
        "### You Receive",
        "| Player | Pos | Team | Points | Projected | %Own |",
        "|--------|-----|------|--------|-----------|------|",
    ]
    recv_total = 0
    recv_proj = 0
    for p in recv_list:
        recv_total += p.total_points
        proj = getattr(p, 'projected_total_points', 0)
        recv_proj += proj
        lines.append(f"| {p.name} | {p.position} | {p.proTeam} | {p.total_points} | {proj} | {_fmt_owned(p.percent_owned)} |")

    diff = recv_total - give_total
    proj_diff = recv_proj - give_proj
    sign = "+" if diff >= 0 else ""
    proj_sign = "+" if proj_diff >= 0 else ""
    lines += [
        "",
        f"**Points differential: {sign}{diff:.1f}** (receive - give)",
        f"**Projected differential: {proj_sign}{proj_diff:.1f}** (receive - give)",
    ]

    # Category-by-category comparison
    give_cats = {}
    recv_cats = {}
    for p in give_list:
        for stat, val in p.stats.get(0, {}).get('breakdown', {}).items():
            give_cats[stat] = give_cats.get(stat, 0) + (val or 0)
    for p in recv_list:
        for stat, val in p.stats.get(0, {}).get('breakdown', {}).items():
            recv_cats[stat] = recv_cats.get(stat, 0) + (val or 0)

    all_cats = sorted(set(list(give_cats.keys()) + list(recv_cats.keys())))
    if all_cats:
        lines += [
            "",
            "### Category Impact",
            "| Category | Give Total | Receive Total | Diff |",
            "|----------|-----------|---------------|------|",
        ]
        for cat in all_cats:
            g = give_cats.get(cat, 0)
            r = recv_cats.get(cat, 0)
            d = r - g
            d_sign = "+" if d >= 0 else ""
            lines.append(f"| {cat} | {_fmt_stat_value(g)} | {_fmt_stat_value(r)} | {d_sign}{_fmt_stat_value(d)} |")

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
