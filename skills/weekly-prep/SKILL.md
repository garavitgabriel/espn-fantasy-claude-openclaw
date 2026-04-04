---
name: weekly-prep
description: "Provides a start-of-week briefing with matchup preview, injury report, roster optimization, and streaming recommendations. Triggers on: 'weekly prep', 'week preview', 'set my lineup', 'start or sit', 'lineup help', 'who should I start', 'injury report', 'prepare for this week', 'monday briefing', 'weekly outlook'."
---

# Weekly Prep — Start-of-Week Briefing

When the user asks for help preparing for the week, setting their lineup, or wants a weekly briefing, follow this comprehensive workflow.

## Step 1: Load Context
Run these calls to establish the full picture:
1. `get_standings` — Current league position and record
2. `get_matchup(week=0)` — This week's opponent and any early category data
3. `get_my_roster` — Current roster with stats and injury status

If memory tools are available:
4. `get_full_context` — Load matchup history, category trends, watchlist, and preferences

## Step 2: Matchup Preview
From the matchup data, identify the opponent. Then:
1. `get_team_roster` with the opponent's name — see their full roster
2. If memory available, check `get_matchup_history` for past results vs this opponent

Present the **Matchup Preview**:
- Opponent name, record, and standing
- Past results vs this opponent (from memory)
- Their key players by position
- Preliminary category projection: which categories you're likely to win/lose based on season stats

## Step 3: Injury & Status Report
Scan your roster (from Step 1) for:
- **Injured players** — Anyone with injuryStatus (Day-to-Day, IL, Out)
- **Empty lineup slots** — Positions without a starter
- **IL-eligible players** — Players who should be moved to IL to free a roster spot

Present a clear **Injury Report**:
- List each injured player with their status and position
- Flag if an injury creates a lineup gap
- Recommend IL moves if applicable

## Step 4: Lineup Optimization
Based on the matchup opponent and your roster:

### Start/Sit Decisions
For each position with multiple eligible players (e.g., UTIL slot, bench bats):
- Who has better stats in the categories that matter this week?
- Are there platoon advantages or favorable pitching matchups?

### Category-Targeted Lineup
Based on the opponent's strengths and weaknesses:
- If they're weak in SB → make sure your speed guys are in the lineup
- If they're strong in HR but weak in AVG → consider high-contact, low-power options
- If pitching categories are close → every starter matters, consider streaming

### Streaming Recommendations
If there are close categories that could be swung with a stream:
1. `get_free_agents` filtered by the needed position (usually SP for streaming pitchers)
2. Identify 2-day starters or favorable matchup streamers
3. Recommend the pickup and who to drop

## Step 5: Strategic Recommendations
Synthesize everything into a **Week Plan**:

1. **Categories to Win** (3-4 you're favored in) — protect these, don't make moves that hurt them
2. **Categories to Target** (2-3 that are close) — streaming or lineup optimization could flip these
3. **Categories to Punt** (2-3 you're heavily outmatched) — don't waste roster moves chasing these
4. **Target category score**: e.g., "Aim for 8-5-1 this week"
5. **Key actions**: specific lineup changes, streams, or pickups to make

## Step 6: Save to Memory (if available)
- `save_category_trend` for each category with your projected strength this week (STRONG/AVERAGE/WEAK)
- If the user makes any roster moves based on recommendations, `save_roster_move` for each
- If there are players to watch for later, `add_to_watchlist`
