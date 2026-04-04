---
name: trade-analyzer
description: "Analyzes trade proposals when the user considers trading players, asks 'should I trade X for Y', evaluates a trade offer, or wants to find trade targets. Compares players' stats, evaluates H2H category impact, and considers roster fit. Triggers on: 'trade', 'swap', 'deal', 'give X for Y', 'trade target', 'should I accept', 'trade offer'."
---

# Trade Analyzer

When the user asks about a trade or is evaluating a trade proposal, follow these steps:

## Step 1: Understand the Categories
Call `get_scoring_categories` to know all 14 H2H categories and their direction. This is essential — a trade that looks bad in total points might be great for category balance.

## Step 2: Run the Trade Analysis
Call `analyze_trade` with the players being given and received (comma-separated names). This gives the baseline stat comparison.

## Step 3: Deep Player Evaluation
Call `get_player_info` for each player involved in the trade to get detailed season stats, injury status, and ownership trends.

## Step 4: Assess Roster Fit
Call `get_my_roster` to understand:
- What positions are covered after the trade?
- Does the trade create a positional gap?
- Are there bench players who can fill in?

## Step 5: Check Memory Context (if available)
If memory tools are available:
- Call `get_category_trends` to see which categories have been consistently strong or weak
- Call `get_matchup_history` to see if certain categories have been costing you matchups
- A trade that hurts a strong category but helps a weak one is often worth it — even if the "point value" goes down

## Step 6: Category Impact Analysis
Build a category-by-category impact table:

| Category | Direction | Current Strength | Impact | Net Effect |
|----------|-----------|-----------------|--------|------------|
| HR | Higher wins | STRONG | Lose 5 HR, Gain 2 HR | -3 HR (slight decline) |
| SB | Higher wins | WEAK | Lose 0 SB, Gain 15 SB | +15 SB (big improvement) |
| ERA | Lower wins | AVERAGE | ... | ... |

For each category:
- Will this trade help, hurt, or be neutral?
- Is the affected category one you're already strong/weak in?
- Could this flip a category from losing to winning in typical matchups?

**Critical reminders for reverse categories:**
- B_SO (lower wins): A player with fewer strikeouts is BETTER
- ERA (lower wins): Lower ERA is BETTER
- WHIP (lower wins): Lower WHIP is BETTER
- L (lower wins): Fewer losses is BETTER

## Step 7: Verdict
Give a clear recommendation:
- **Accept** / **Decline** / **Counter-offer**
- How many categories does this trade help vs hurt?
- What's the net category swing? (e.g., "You gain an edge in 3 categories but lose ground in 1")
- Is the positional fit workable?
- Any injury risks to flag?

## Step 8: Save to Memory (if available)
If the user completes a trade:
- Call `save_roster_move` with action="TRADE_SEND" for each player given away
- Call `save_roster_move` with action="TRADE_RECEIVE" for each player received
- Update `save_category_trend` if the trade significantly changes category projections
