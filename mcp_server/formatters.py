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


def fmt_schedule(team, current_week=None):
    """Format a team's full season schedule."""
    schedule = getattr(team, 'schedule', [])
    if not schedule:
        return f"No schedule data available for {team.team_name}."

    lines = [
        f"## Schedule — {team.team_name}",
        "",
        "| Week | Opponent | Result | Score |",
        "|------|----------|--------|-------|",
    ]

    for i, matchup in enumerate(schedule):
        week = i + 1
        # Determine opponent and result
        home = matchup.home_team
        away = matchup.away_team
        home_name = home.team_name if hasattr(home, 'team_name') else str(home)
        away_name = away.team_name if hasattr(away, 'team_name') else str(away)

        is_home = hasattr(home, 'team_id') and home.team_id == team.team_id
        opponent = away_name if is_home else home_name

        # Score
        my_score = matchup.home_final_score if is_home else matchup.away_final_score
        opp_score = matchup.away_final_score if is_home else matchup.home_final_score

        # Live score if available
        my_live = (matchup.home_team_live_score if is_home else matchup.away_team_live_score) if hasattr(matchup, 'home_team_live_score') else None
        opp_live = (matchup.away_team_live_score if is_home else matchup.home_team_live_score) if hasattr(matchup, 'away_team_live_score') else None

        marker = " **<<**" if current_week and week == current_week else ""

        if my_live is not None and opp_live is not None and current_week and week == current_week:
            result = "In Progress"
            score = f"{my_live:.1f} - {opp_live:.1f}"
        elif my_score and opp_score:
            winner = getattr(matchup, 'winner', None)
            if winner == "HOME" and is_home or winner == "AWAY" and not is_home:
                result = "**W**"
            elif winner == "HOME" and not is_home or winner == "AWAY" and is_home:
                result = "L"
            elif winner == "UNDECIDED":
                result = "—"
            else:
                result = "—"
            score = f"{my_score:.1f} - {opp_score:.1f}"
        else:
            result = "Upcoming"
            score = "—"

        lines.append(f"| {week}{marker} | {opponent} | {result} | {score} |")

    return "\n".join(lines)


def fmt_league_settings(settings):
    """Format comprehensive league settings."""
    lines = [
        f"## League Settings — {settings.name}",
        "",
        "### Format",
        f"- **Scoring type:** {settings.scoring_type or '—'}",
        f"- **Teams:** {settings.team_count}",
        f"- **Regular season weeks:** {settings.reg_season_count}",
        f"- **Playoff teams:** {settings.playoff_team_count}",
        f"- **Playoff matchup length:** {settings.playoff_matchup_period_length} week(s)",
        f"- **Median scoring bonus:** {'Yes' if settings.median_scoring else 'No'}",
        "",
        "### Trades",
        f"- **Veto votes required:** {settings.veto_votes_required}",
    ]

    if settings.trade_deadline:
        from datetime import datetime
        try:
            deadline = datetime.fromtimestamp(settings.trade_deadline / 1000)
            lines.append(f"- **Trade deadline:** {deadline.strftime('%b %d, %Y')}")
        except (ValueError, OSError):
            lines.append(f"- **Trade deadline:** {settings.trade_deadline}")
    else:
        lines.append("- **Trade deadline:** None set")

    lines += [
        "",
        "### Acquisitions",
        f"- **FAAB (auction budget for waivers):** {'Yes' if settings.faab else 'No'}",
    ]
    if settings.faab:
        lines.append(f"- **FAAB budget:** ${settings.acquisition_budget}")

    lines += [
        "",
        "### Tiebreakers",
        f"- **Regular season tie rule:** {settings.tie_rule}",
        f"- **Playoff tie rule:** {settings.playoff_tie_rule}",
        f"- **Playoff seed tie rule:** {getattr(settings, 'playoff_seed_tie_rule', '—')}",
    ]

    if settings.keeper_count:
        lines += [
            "",
            f"### Keepers: {settings.keeper_count} per team",
        ]

    division_map = getattr(settings, 'division_map', {})
    if division_map:
        lines += [
            "",
            "### Divisions",
        ]
        for div_id, div_name in division_map.items():
            lines.append(f"- {div_name}")

    return "\n".join(lines)


def fmt_player_search(results, query):
    """Format player search results."""
    if not results:
        return f"No players found matching '{query}'."

    lines = [
        f"## Search Results for '{query}' ({len(results)} matches)",
        "",
        "| Player | Pos | Team | Points | %Own |",
        "|--------|-----|------|--------|------|",
    ]
    for p in results:
        owned = _fmt_owned(p.percent_owned)
        lines.append(f"| {p.name} | {p.position} | {p.proTeam} | {p.total_points} | {owned} |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Phase C — ESPN Public API formatters
# ---------------------------------------------------------------------------


def fmt_player_news(overview_data: dict, player_name: str) -> str:
    """Format player news from ESPN public API overview endpoint."""
    lines = [f"## News — {player_name}", ""]

    # Rotowire blurb (injury/status)
    rotowire = overview_data.get("rotowire", {})
    if rotowire:
        blurb = rotowire.get("blurb", "")
        if blurb:
            lines.append(f"**Status:** {blurb}")
            lines.append("")

    # Next game
    next_game = overview_data.get("nextGame", {})
    if next_game:
        event = next_game.get("event", {})
        game_name = event.get("name", "")
        game_date = event.get("date", "")
        if game_name:
            lines.append(f"**Next game:** {game_name}" + (f" ({game_date[:10]})" if game_date else ""))
            lines.append("")

    # News articles
    news = overview_data.get("news", {})
    articles = news.get("items", []) if isinstance(news, dict) else []
    if articles:
        lines.append("### Recent Headlines")
        for article in articles[:8]:
            headline = article.get("headline", "")
            description = article.get("description", "")
            published = article.get("published", "")[:10] if article.get("published") else ""
            if headline:
                line = f"- **{headline}**"
                if published:
                    line += f" ({published})"
                lines.append(line)
                if description:
                    lines.append(f"  {description[:200]}")
    else:
        lines.append("No recent news.")

    return "\n".join(lines)


def fmt_player_splits(splits_data: dict, player_name: str) -> str:
    """Format player splits from ESPN public API."""
    lines = [f"## Splits — {player_name}", ""]

    split_categories = splits_data.get("splitCategories", [])
    if not split_categories:
        return f"No split data available for {player_name}."

    for category in split_categories:
        cat_name = category.get("displayName", "Unknown")
        splits = category.get("splits", [])
        if not splits:
            continue

        # Get stat headers from first split
        stats = splits[0].get("stats", [])
        if not stats:
            continue
        headers = splits[0].get("abbreviations", []) or [f"S{i}" for i in range(len(stats))]

        lines.append(f"### {cat_name}")
        header_row = "| Split | " + " | ".join(headers) + " |"
        separator = "|-------|" + "|".join(["------"] * len(headers)) + "|"
        lines.append(header_row)
        lines.append(separator)

        for split in splits:
            split_name = split.get("displayName", "—")
            split_stats = split.get("stats", [])
            vals = [str(v) if v is not None else "—" for v in split_stats]
            lines.append(f"| {split_name} | " + " | ".join(vals) + " |")

        lines.append("")

    return "\n".join(lines)


def fmt_player_gamelog(gamelog_data: dict, player_name: str) -> str:
    """Format player game log from ESPN public API.

    Response structure: labels at top level, game data in
    seasonTypes[0].categories[0].events (list of {eventId, stats}).
    Event details (date, opponent) are in the top-level events dict keyed by eventId.
    """
    lines = [f"## Game Log — {player_name}", ""]

    # Labels are at top level
    labels = gamelog_data.get("labels", [])
    # Event metadata (date, opponent) is in top-level events dict
    events_meta = gamelog_data.get("events", {})
    if not isinstance(events_meta, dict):
        events_meta = {}

    # Game stats are in seasonTypes[0].categories[0].events
    season_types = gamelog_data.get("seasonTypes", [])
    if not season_types:
        return f"No game log data available for {player_name}."

    for st in season_types:
        st_name = st.get("displayName", "")
        display_team = st.get("displayTeam", "")
        if st_name:
            lines.append(f"### {st_name}" + (f" ({display_team})" if display_team else ""))
            lines.append("")

        categories = st.get("categories", [])
        for cat in categories:
            cat_name = cat.get("displayName", "")
            cat_events = cat.get("events", [])

            if not cat_events:
                continue

            if cat_name:
                lines.append(f"**{cat_name}**")

            display_labels = labels[:12] if labels else [f"S{i}" for i in range(len(cat_events[0].get("stats", [])))][:12]
            header = "| Game | " + " | ".join(display_labels) + " |"
            sep = "|------|" + "|".join(["------"] * len(display_labels)) + "|"
            lines.append(header)
            lines.append(sep)

            for event in cat_events[:20]:
                event_id = event.get("eventId", "")
                stats = event.get("stats", [])
                vals = [str(v) if v is not None else "—" for v in stats[:12]]
                while len(vals) < len(display_labels):
                    vals.append("—")

                # Try to get game info from events metadata
                meta = events_meta.get(str(event_id), {})
                if isinstance(meta, dict):
                    opp = meta.get("opponent", {})
                    opp_abbrev = opp.get("abbreviation", "") if isinstance(opp, dict) else ""
                    game_date = meta.get("gameDate", "")[:10]
                    game_label = f"{game_date} vs {opp_abbrev}" if opp_abbrev else event_id
                else:
                    game_label = str(event_id)

                lines.append(f"| {game_label} | " + " | ".join(vals) + " |")

            # Totals
            totals = cat.get("totals", [])
            if totals:
                vals = [str(v) if v is not None else "—" for v in totals[:12]]
                while len(vals) < len(display_labels):
                    vals.append("—")
                lines.append(f"| **Totals** | " + " | ".join(vals) + " |")

            lines.append("")

    return "\n".join(lines)


def fmt_mlb_games(games_data: dict, date: str) -> str:
    """Format MLB games for a specific date.

    Response has events[] with competitors[] (home/away teams with scores).
    """
    events = games_data.get("events", [])
    if not events:
        return f"No MLB games found for {date}."

    lines = [
        f"## MLB Games — {date[:4]}-{date[4:6]}-{date[6:]}",
        "",
        "| Away | Score | Home | Score | Status |",
        "|------|-------|------|-------|--------|",
    ]

    for event in events:
        competitors = event.get("competitors", [])

        away_name = "?"
        away_score = "—"
        home_name = "?"
        home_score = "—"

        for comp in competitors:
            abbrev = comp.get("abbreviation", comp.get("name", "?"))
            score = comp.get("score", "—")
            if score is not None:
                score = str(int(score)) if isinstance(score, float) and score == int(score) else str(score)
            else:
                score = "—"
            if comp.get("homeAway") == "home":
                home_name = abbrev
                home_score = score
            else:
                away_name = abbrev
                away_score = score

        # Status
        full_status = event.get("fullStatus", {})
        status_type = full_status.get("type", {})
        status = status_type.get("shortDetail", status_type.get("detail", event.get("summary", "—")))

        lines.append(f"| {away_name} | {away_score} | {home_name} | {home_score} | {status} |")

    return "\n".join(lines)


def fmt_batter_vs_team(data: dict, player_name: str) -> str:
    """Format batter vs team stats from ESPN public API.

    Response structure: statistics is a dict with 'labels', 'statistics' (list of pitcher matchups),
    and 'displayName' (e.g. "career statistics vs. Washington Nationals pitchers").
    """
    lines = [f"## {player_name} — Batter vs Team", ""]

    # Next game info
    next_game = data.get("nextGame", {})
    if next_game:
        event = next_game.get("event", {})
        if event:
            lines.append(f"**Next game:** {event.get('name', '—')} ({event.get('date', '')[:10]})")
            lines.append("")

    # statistics is a dict, not a list
    stats_obj = data.get("statistics", {})
    if not stats_obj or not isinstance(stats_obj, dict):
        lines.append("No batter vs team data available.")
        return "\n".join(lines)

    title = stats_obj.get("displayName", "")
    if title:
        lines.append(f"**{title}**")
        lines.append("")

    labels = stats_obj.get("labels", [])
    inner_stats = stats_obj.get("statistics", [])

    if not labels or not inner_stats:
        lines.append("No batter vs team data available.")
        return "\n".join(lines)

    display_labels = labels[:12]
    lines.append("| Pitcher | " + " | ".join(display_labels) + " |")
    lines.append("|---------|" + "|".join(["------"] * len(display_labels)) + "|")

    for entry in inner_stats:
        name = entry.get("displayName", "—") if isinstance(entry, dict) else str(entry)
        stats = entry.get("stats", []) if isinstance(entry, dict) else []
        vals = [str(v) if v is not None else "—" for v in stats[:12]]
        while len(vals) < len(display_labels):
            vals.append("—")
        lines.append(f"| {name} | " + " | ".join(vals) + " |")

    # Totals
    totals = stats_obj.get("totals", [])
    if totals:
        vals = [str(v) if v is not None else "—" for v in totals[:12]]
        while len(vals) < len(display_labels):
            vals.append("—")
        lines.append(f"| **Total** | " + " | ".join(vals) + " |")

    return "\n".join(lines)


def fmt_pro_schedule(data: dict, current_scoring_period: int = 0, days: int = 7) -> str:
    """Format MLB pro team schedule — games per team over the next N days.

    proGamesByScoringPeriod is keyed by scoring period ID (day-level).
    We count games in a window starting from current_scoring_period.

    Args:
        data: Response from proTeamSchedules_wl API.
        current_scoring_period: The current scoring period (day number in season).
        days: How many days to look ahead (default 7).
    """
    settings = data.get("settings", {})
    pro_teams = settings.get("proTeams", [])

    if not pro_teams:
        return "No pro team schedule data available."

    if not current_scoring_period:
        return "No current scoring period available. Call refresh_data first."

    period_range = list(range(current_scoring_period, current_scoring_period + days))

    lines = [
        f"## MLB Schedule — Next {days} Days (periods {period_range[0]}-{period_range[-1]})",
        "",
        "| Team | Games | Off Days |",
        "|------|-------|----------|",
    ]

    team_data = []
    for team in pro_teams:
        abbrev = team.get("abbrev", "—")
        if abbrev == "FA" or not abbrev:
            continue
        schedule = team.get("proGamesByScoringPeriod", {})
        game_days = [p for p in period_range if schedule.get(str(p))]
        off_days = days - len(game_days)
        team_data.append((abbrev, len(game_days), off_days))

    for abbrev, game_count, off_days in sorted(team_data, key=lambda x: -x[1]):
        off_str = str(off_days) if off_days > 0 else "—"
        lines.append(f"| {abbrev} | {game_count} | {off_str} |")

    return "\n".join(lines)


def fmt_league_chat(data: dict) -> str:
    """Format league message board / chat."""
    topics = data.get("topics", [])
    if not topics:
        return "No league messages found."

    lines = ["## League Chat", ""]

    for topic in topics[:15]:
        author = topic.get("author", "—")
        date = topic.get("date", "")
        if isinstance(date, int):
            from datetime import datetime
            try:
                date = datetime.fromtimestamp(date / 1000).strftime("%b %d %H:%M")
            except (ValueError, OSError):
                date = str(date)

        messages = topic.get("messages", [])
        first_msg = messages[0] if messages else {}
        text = first_msg.get("message", first_msg.get("content", ""))
        total = topic.get("totalMessageCount", len(messages))

        if text:
            preview = text[:150] + ("..." if len(text) > 150 else "")
            lines.append(f"**{author}** ({date})" + (f" — {total} replies" if total > 1 else ""))
            lines.append(f"> {preview}")
            lines.append("")

    return "\n".join(lines)
