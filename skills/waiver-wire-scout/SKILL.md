---
name: waiver-wire-scout
description: "Monitors recent league transactions (drops, trades, adds) to find overlooked players and recommend waiver pickups. Triggers on: 'waiver wire', 'who got dropped', 'recent transactions', 'league activity', 'any good drops', 'what moves happened', 'waivers', 'claims'."
---

# Waiver Wire Scout

When the user asks about recent league activity, wants to scan the waiver wire, or is looking for overlooked pickups from other teams' drops, follow this workflow.

## Step 1: Pull Recent Transactions
Call `get_recent_activity` with size=25 to see the latest league transactions — adds, drops, and trades.

## Step 2: Load Your Context
1. `get_my_roster` — Current roster to identify needs
2. `get_scoring_categories` — The 14 H2H categories

If memory tools are available:
3. `get_full_context` — Watchlist, category trends, preferences, past roster moves
4. `get_roster_moves` — Your own recent moves to avoid re-adding someone you just dropped

## Step 3: Identify Opportunities
Scan the recent activity for:

### Dropped Players Worth Grabbing
- Players dropped by other teams who still have value
- Filter out players you recently dropped yourself (check memory)
- Focus on players with decent ownership % — if they were widely owned, the drop might be a mistake or a roster crunch move

### Trade Fallout
- When teams make trades, they often need to drop roster players to make room
- These "trade casualties" can be valuable pickups

### Trending Adds
- If multiple teams are adding the same position, there may be a scarcity developing
- If a player was added then quickly dropped, they might be underperforming expectations

## Step 4: Evaluate Top Targets
For the 3-5 most interesting dropped or available players:
1. `get_player_info` for each — detailed stats, injury status, ownership trends
2. Map their production to the 14 H2H categories
3. Cross-reference with your category needs (from memory trends or current roster analysis)

## Step 5: Present the Waiver Wire Report

### Section 1: Notable Drops
List players recently dropped by other teams with:
- Player name, position, who dropped them
- Their season stats and category contributions
- Why they might have been dropped (injury? roster crunch? underperformance?)
- Whether they fit YOUR category needs

### Section 2: Recommended Pickups
Rank the top 3 pickup targets:
1. **Player name** — Position, key categories they help
2. **Who to drop** — Suggest the weakest roster player at the same position or a bench spot
3. **Category impact** — Which of the 14 categories improve with this swap?
4. **Urgency** — High (someone else will grab them), Medium (worth claiming), Low (monitor)

### Section 3: Players to Watch
Players who aren't must-adds right now but are trending:
- Recently called up prospects
- Players returning from injury
- Hot streaks on low ownership

## Step 6: Save to Memory (if available)
- If the user picks someone up: `save_roster_move` with action="ADD" and `save_roster_move` with action="DROP" for whoever was dropped
- Add interesting players to `add_to_watchlist` with a reason (e.g., "Dropped by Team X, monitor for 1 week")
- Remove any watchlist players who were picked up: `remove_from_watchlist`
