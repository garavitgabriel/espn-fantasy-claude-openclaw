---
name: draft-assistant
description: "Assists during auction drafts with real-time budget tracking, roster needs analysis, player scouting, and bid recommendations. Triggers on: 'draft', 'auction', 'who should I bid on', 'budget', 'nominate', 'how much should I spend', 'draft board', 'keeper', 'draft strategy'. Designed for auction format ($280 budget, ~20 active slots)."
---

# Draft Assistant — Auction Draft Expert

When the user is preparing for or actively participating in an auction draft, follow this workflow. This skill is designed for **auction drafts** with a $280 budget and ~20 active roster slots.

## Pre-Draft Setup (run once at the start)

### Step 1: Load League Settings
Call these in sequence to understand the league structure:
1. `get_scoring_categories` — The 14 H2H categories and their direction
2. `get_roster_slots` — How many of each position are needed (C, 1B, 2B, 3B, SS, OF, UTIL, SP, RP, P, BE, IL)

### Step 2: Load Memory Context
If memory tools are available:
- Call `get_full_context` to load any prior draft picks already recorded, preferences (punt categories, draft strategy), and watchlist targets
- Call `get_preferences` specifically to check for keys like `draft_strategy`, `punt_categories`, `target_players`

### Step 3: Establish Budget Framework
Present the budget breakdown to the user:
- **Total budget:** $280
- **Active slots:** ~20 (varies by league settings — check roster slots)
- **Average cost per slot:** ~$14
- **Star tier:** $40-60+ (elite players, first 2-3 rounds)
- **Mid tier:** $15-30 (solid starters)
- **Value tier:** $1-10 (bench, streamers, speculative adds)
- **$1 minimum:** Every roster slot costs at least $1, so reserve enough $1 slots for the end

Ask the user about their draft strategy if no preference is saved:
- Balanced approach vs. stars-and-scrubs?
- Any categories to punt?
- Must-have players or positions?

Save their answers with `set_preference`.

## During the Draft (repeating cycle)

### Step 4: Track the Draft Board
When the user asks for an update or a new player is nominated:
1. Call `refresh_data` to get the latest
2. Call `get_draft_board` to see:
   - All picks so far with auction prices
   - Remaining budget per team
   - Which teams are running low on cash
3. Call `get_roster_needs` to see your unfilled positions

### Step 5: Evaluate a Nominated Player
When a player is nominated or the user asks "should I bid on X?":
1. Call `get_player_info` for the nominated player — stats, position, ownership
2. Check which categories this player helps. Map their stats to the 14 scoring categories:
   - **Hitting:** AVG, HR, OPS, R, RBI, SB, B_SO (lower wins)
   - **Pitching:** ERA (lower wins), WHIP (lower wins), K, W, L (lower wins), SV, HLD
3. Check `get_roster_needs` — do you need this position?
4. If memory available, check `get_category_trends` — does this player help your weak categories?

### Step 6: Bid Recommendation
Provide a clear recommendation:

1. **Max bid price** — What's the most you should pay? Factor in:
   - Remaining budget and slots to fill
   - Position scarcity (C and SS have only 1 slot each — premium)
   - Category impact (helps weak categories = worth more)
   - Other teams' remaining budgets (if few teams can afford him, you might get a deal)
2. **Walk-away price** — At what price is this player no longer worth it for your team?
3. **Alternative targets** — If the price goes too high, who else fills the same need?

### Step 7: Record Picks
After each pick (yours or opponents'):
- If memory available, call `save_draft_pick` with: season, player_name, position, bid_amount
- Track your remaining budget mentally and flag when it's getting tight

## Key Bidding Strategies

### Position Scarcity Rules
- **C, SS** — Only 1 slot each. Premium positions. Bid aggressively for elite options early.
- **OF** — Multiple slots. More depth available. Can wait for value.
- **SP/RP/P** — Flexible pitcher slots. Target elite arms early, fill with streamers late.
- **UTIL/BE** — Fill last with $1 bids.

### Budget Pacing
After each pick, calculate:
- Remaining budget
- Remaining roster slots to fill
- Max bid on next player = remaining budget - (remaining slots - 1) × $1
- If max bid is getting close to $1 per slot, stop bidding on expensive players

### Opponent Budget Exploitation
- When only 2-3 teams can afford a player, the price drops. Identify these moments.
- When a team is down to $1/slot budget, they can't compete — every remaining player goes cheap.
- Track which teams have spent heavily and which are saving.

### Category-First Bidding
- Don't just bid on the "best" player. Bid on players who help categories you're losing.
- A $20 closer (SV + HLD) can be more valuable than a $20 bat if saves are your biggest gap.
- Reverse categories matter: a pitcher with elite ERA/WHIP is worth extra because those categories are hard to dominate.

## Post-Draft Summary
After the draft completes:
1. Call `get_my_roster` to see the final roster
2. Call `get_roster_needs` to check for any gaps
3. Review category coverage — are all 14 categories addressed?
4. Identify immediate free agent targets for any weak spots
5. If memory available, save a `set_preference` with key `draft_recap` summarizing the strategy used and results
