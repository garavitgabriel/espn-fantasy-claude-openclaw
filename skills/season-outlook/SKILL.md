---
name: season-outlook
description: "Provides a season-level analysis with record trends, category evolution, roster trajectory, and playoff positioning. Best used at end of week or month for big-picture perspective. Triggers on: 'season outlook', 'how is my season going', 'playoff chances', 'season review', 'monthly recap', 'big picture', 'overall analysis', 'season trend', 'am I on track'."
---

# Season Outlook — Big Picture Analysis

When the user wants a high-level view of their season trajectory, playoff positioning, or a recap of recent performance, follow this workflow.

## Step 1: Gather Current State
1. `get_standings` — League standings with full records
2. `get_my_roster` — Current roster composition and stats
3. `get_scoring_categories` — The 14 H2H categories for reference

## Step 2: Load Season History from Memory
If memory tools are available (this skill benefits heavily from memory):
1. `get_matchup_history` — All recorded weekly results with category breakdowns
2. `get_category_trends` — Category assessments over time
3. `get_roster_moves` — Full transaction log for the season
4. `get_preferences` — Strategy settings (punt categories, etc.)

## Step 3: Record & Trend Analysis

### Win/Loss Trajectory
From standings and matchup history:
- Current record and league rank
- Recent form: last 3-5 weeks results
- Are you trending up (winning more recently) or down?
- How many games back from a playoff spot (or first place)?

### Category Evolution
From category trends in memory:
- Which categories have **improved** over the season? (credit roster moves)
- Which have **declined**? (flag concern)
- Which have been **consistently dominant**? (core strengths)
- Which have been **consistently weak**? (punt candidates or improvement targets)
- Are your punt categories actually being punted, or are you accidentally investing in them?

If no memory trends exist, analyze the current roster stats vs league averages by running `get_league_rosters` and comparing.

### Roster Moves Assessment
From roster moves in memory:
- How many adds/drops this season?
- Have the moves improved the roster? (compare early-season vs now)
- Any moves that backfired? (dropped someone who performed well after)
- Trade history: did you win or lose your trades?

## Step 4: Playoff Positioning

### Standings Math
- How many teams make the playoffs? (typically top 4-6 in a 10-12 team league)
- Current rank vs cutoff
- How many wins needed over remaining weeks to clinch?
- Which teams are you competing with for the last spot?

### Strength of Schedule
Call `get_box_scores` for recent weeks to understand the competitive landscape:
- Who are the strongest teams right now?
- Do you have favorable matchups coming up?
- Any must-win weeks against direct playoff competitors?

## Step 5: Present the Season Outlook

### The Dashboard
```
Record: X-Y-Z | Rank: #N | Playoff Position: IN/OUT/BUBBLE
Recent Form (L5): W-W-L-W-L
Category Record: [Wins]-[Losses]-[Ties] across all categories
```

### Category Health Report
A table of all 14 categories with:
| Category | Direction | Strength | Trend | Action |
|----------|-----------|----------|-------|--------|
| HR | Higher | STRONG | Stable | Protect |
| SB | Higher | WEAK | Improving | Keep targeting |
| ERA | Lower | AVERAGE | Declining | Concern — investigate |

### Key Insights
3-5 bullet points on the most important observations:
- "Your pitching has carried you — ERA/WHIP/K are your best categories"
- "SB has improved since adding [player] in week 8"
- "You're losing close matchups by 1-2 categories — fixing HLD could flip those"

### Recommendations
Concrete next steps prioritized by impact:
1. **Immediate** — Roster moves to make this week
2. **Short-term** — Trade targets or free agent strategies for the next 2-3 weeks
3. **Long-term** — Strategic shifts for playoff positioning (change punt strategy? go all-in on pitching?)

## Step 6: Save to Memory (if available)
- `save_category_trend` for each of the 14 categories with current assessment
- If strategic decisions are made (e.g., "start punting L and W"), `set_preference` with updated punt categories
- `add_to_watchlist` for any trade targets or free agents identified
