---
name: category-strategist
description: "Analyzes season-long H2H category patterns to identify strengths, weaknesses, punt targets, and strategic adjustments. Uses memory trends to show how categories have evolved over time. Triggers on: 'category analysis', 'what categories am I good at', 'what should I punt', 'category strategy', 'where am I weak', 'season analysis', 'how are my stats', 'stat trends', 'category breakdown', 'what do I need to improve'."
---

# Category Strategist — Season-Long H2H Analysis

When the user asks about their category strengths, weaknesses, or overall strategy, provide a comprehensive analysis of their performance across all 14 H2H categories.

## Step 1: Gather Current Data
1. `get_standings` — Overall record and league position
2. `get_my_roster` — Current roster and season stats
3. `get_scoring_categories` — The 14 categories and their direction

## Step 2: Load Historical Context (if memory available)
If memory tools are available:
1. `get_category_trends` — All recorded category assessments over time
2. `get_matchup_history` — Past matchup results with category breakdowns
3. `get_preferences` — Check for existing strategy preferences (punt categories, etc.)

## Step 3: Category-by-Category Assessment
For each of the 14 categories, assess the team's strength:

### Hitting Categories
| Category | Direction | Assessment Method |
|----------|-----------|-------------------|
| AVG | Higher wins | Roster-wide batting average from season stats |
| HR | Higher wins | Total HR from roster |
| OPS | Higher wins | Roster-wide OPS |
| R | Higher wins | Total runs scored |
| RBI | Higher wins | Total RBI |
| SB | Higher wins | Total stolen bases — often carried by 1-2 specialists |
| B_SO | **Lower wins** | Total batter strikeouts — fewer is better |

### Pitching Categories
| Category | Direction | Assessment Method |
|----------|-----------|-------------------|
| ERA | **Lower wins** | Roster-wide ERA — weighted by innings |
| WHIP | **Lower wins** | Roster-wide WHIP — weighted by innings |
| K | Higher wins | Total pitcher strikeouts |
| W | Higher wins | Total wins |
| L | **Lower wins** | Total losses — fewer is better |
| SV | Higher wins | Total saves — typically 1-2 closers |
| HLD | Higher wins | Total holds — middle relievers |

For each category, rate as: **DOMINANT** / **STRONG** / **AVERAGE** / **WEAK** / **PUNTING**

## Step 4: Trend Analysis (with memory)
If category trends exist in memory, analyze the trajectory:
- Which categories are **improving**? (WEAK → AVERAGE, AVERAGE → STRONG)
- Which are **declining**? (STRONG → AVERAGE)
- Which have been **consistently weak**? (WEAK for 3+ weeks = punt candidate)
- Which have been **consistently strong**? (STRONG for 3+ weeks = protect)

Cross-reference with matchup history:
- Which categories have you won most often?
- Which categories have cost you the most matchups?
- Are there categories you're losing by narrow margins? (high-value improvement targets)

## Step 5: Strategic Recommendations

### Category Tiers
Group the 14 categories into tiers:

**Tier 1 — Dominant (protect at all costs)**
Categories where you consistently win. Do NOT trade away players who drive these.

**Tier 2 — Competitive (push to win)**
Categories you win ~50% of the time. Small roster moves can flip these.

**Tier 3 — Weak but Fixable (target for improvement)**
Categories you lose often but could improve with targeted pickups or trades.

**Tier 4 — Punt Candidates**
Categories so weak that investing resources to fix them isn't worth it. Better to concede and dominate elsewhere.

### Action Plan
Based on the tier analysis:

1. **Protect** — Name the categories to never sacrifice in trades
2. **Target** — Name 2-3 categories to improve via:
   - Free agent pickups (call `get_free_agents` filtered for relevant positions)
   - Trade targets (which player archetypes would help?)
3. **Punt** — Name categories to concede and explain the math:
   - "If you punt ERA and WHIP, you only need to win 8 of 12 remaining categories"
   - "Punting SV means you can trade your closer for hitting upgrades"
4. **Category math** — In a 14-category H2H matchup, you need 8 to win. Show how the strategy gets to 8+.

### Trade Targets by Category Need
For each Tier 3 category, suggest the type of player to target:
- Weak in SB → "Target a speed specialist like [type of player]"
- Weak in SV → "Target a closer from a team with a surplus"
- Weak in K → "Your pitching staff needs a high-K arm"

## Step 6: Save to Memory (if available)
- `save_category_trend` for each of the 14 categories with current assessment
- If the user makes strategic decisions (e.g., "let's punt saves"), `set_preference` with key `punt_categories`
- If specific trade targets are identified, `add_to_watchlist` for those player archetypes
