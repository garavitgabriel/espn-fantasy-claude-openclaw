---
name: free-agent-finder
description: "Finds and recommends free agents when the user needs a player, asks about the waiver wire, needs a position filled, wants to stream a pitcher, or asks 'who should I pick up'. Searches by position, compares top options, and recommends based on H2H category impact. Triggers on: 'free agent', 'waiver', 'pickup', 'pick up', 'stream', 'available', position needs like 'I need a shortstop'."
---

# Free Agent Finder

When the user is looking for free agent pickups or waiver wire targets, follow these steps:

## Step 1: Understand the League Categories
Call `get_scoring_categories` to know which 14 stats matter and their direction (some are reverse — lower wins).

## Step 2: Assess Current Roster
Call `get_my_roster` to see the current team composition, stats, and any gaps.

## Step 3: Identify Needs
- If the user specified a position, use that position.
- If not, call `get_roster_needs` to identify which positions are unfilled or weakest.
- Check memory if available: call `get_category_trends` to identify which categories need help, and `get_watchlist` to see if there are players already being tracked.

## Step 4: Search Free Agents
Call `get_free_agents` with the target position filter. Request up to 25 results to have a good pool.

## Step 5: Deep Evaluation
For the top 3-5 candidates from the free agent list, call `get_player_info` for each to get detailed stat breakdowns. If comparing two close options, use `compare_players`.

## Step 6: Present Recommendations
Rank the candidates by **category impact**, not just total points. For each recommendation:

1. **Player name and position**
2. **Key categories they help**: Which of the 14 categories will improve?
3. **Categories they might hurt**: e.g., a power hitter with high B_SO (bad in a lower-wins category)
4. **Ownership %**: How likely is someone else to grab them?
5. **Verdict**: Clear recommendation on who to pick up and who to drop

For the reverse categories (B_SO, ERA, WHIP, L), remember that **lower values are better**. A pitcher with high K but also high ERA is a mixed bag.

## Step 7: Log to Memory (if available)
- If the user decides to pick someone up, call `save_roster_move` with action="ADD" and the player details
- If they drop someone, call `save_roster_move` with action="DROP"
- If a candidate was on the watchlist, call `remove_from_watchlist` after pickup
- If they want to monitor someone for later, call `add_to_watchlist`
