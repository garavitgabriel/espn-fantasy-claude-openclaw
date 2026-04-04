---
name: matchup-scout
description: "Scouts the current matchup when the user asks about their matchup, how they're doing this week, who they're playing, or their opponent's team. Pulls standings, matchup category breakdown, and opponent roster to give full context. Triggers on: 'matchup', 'how am I doing', 'who am I playing', 'opponent', 'this week', H2H category performance questions."
---

# Matchup Scout

When the user asks about their current matchup, opponent, or weekly performance, follow these steps:

## Step 1: Get League Context
Call `get_standings` to see where the user's team ranks and their record.

## Step 2: Get Live Matchup
Call `get_matchup` with week=0 (current week) to get the category-by-category breakdown. This shows which categories you're winning, losing, or tied in.

## Step 3: Scout the Opponent
From the matchup result, identify the opponent team name. Then:
- Call `get_team_roster` with the opponent's team name to see their full roster
- Call `get_my_roster` to see your own roster for comparison

## Step 4: Check Memory (if available)
If the memory tools are available:
- Call `get_matchup_history` filtered by the opponent's name to see past results against them
- Call `get_category_trends` to understand which categories you've been strong or weak in recently

## Step 5: Analyze and Recommend
Present a structured analysis:

1. **Category Scoreboard**: List all 14 categories with current status (Winning/Losing/Tied) and the values for both teams
2. **Key Opponent Players**: Highlight their best performers driving the categories they're winning
3. **Strategic Recommendations**:
   - Which categories to **press** (you're close to winning)
   - Which categories to **protect** (you're barely ahead)
   - Which categories to **concede** (too far behind, not worth chasing)
4. **Roster Moves**: If there are free agent pickups that could flip a close category, suggest them

Remember: 4 categories are **reverse** (lower wins): B_SO, ERA, WHIP, L. When these show a lower value for the user, that's GOOD.

## Step 6: Save to Memory (if available)
If you observe notable category trends (e.g., consistently weak in SV, dominant in HR), call `save_category_trend` for each notable category.
