"""MCP resources — workflow playbooks and skill summaries.

Resources are static text that MCP clients can auto-discover.
They provide workflow instructions for agents and tools like OpenClaw.
"""


def register_resources(mcp):
    """Register all MCP resources on the FastMCP instance."""

    @mcp.resource("espn://workflow/season-management")
    async def season_management_workflow() -> str:
        """Weekly season management playbook for H2H Categories leagues."""
        return """\
# Fantasy Baseball Season Management

## Weekly Workflow

### 1. Matchup Analysis
- Call `get_matchup` to see your current H2H category breakdown
- Identify which categories you're winning and losing
- Focus roster moves on categories that are close (within striking distance)

### 2. Roster Optimization
- Call `get_my_roster` to review your current lineup
- Check for injured or benched players
- Ensure your best players are in active slots

### 3. Free Agent Scouting
- Call `get_free_agents` filtered by positions where you're weakest
- Look for players who help in categories you're losing this week
- Use `compare` to evaluate FA vs your current player at that position

### 4. Waiver Wire & Trades
- Call `get_recent_activity` to see what other teams are doing
- Call `get_league_rosters` to find trade targets on other teams
- Use `analyze_trade` before proposing any deals

### 5. Category Strategy
- Call `get_standings` to see where you stand in each category across the league
- Target categories where a small improvement moves you up several spots
- In H2H, winning 8-6 is the same as winning 14-0 — focus on the margin categories

## Key Principles
- **H2H Categories**: You win individual stat categories, not total points
- **Punting**: It's valid to punt 1-2 categories to dominate the rest
- **Streaming**: For pitching categories (K, W, SV, HLD), streaming pitchers can swing close weeks
- **Lower-is-better stats**: B_SO (batter strikeouts), WHIP, ERA, L (losses) — lower wins
"""

    @mcp.resource("espn://workflow/draft-day")
    async def draft_day_workflow() -> str:
        """Auction draft day playbook ($280 budget)."""
        return """\
# Auction Draft Day Playbook

## Pre-Draft Setup
1. Call `get_scoring_categories` to know all 14 categories
2. Call `get_roster_slots` to see how many of each position you need
3. Budget: $280 per team, ~20 active roster slots → ~$14 average per player

## During Draft
1. Call `refresh_data` then `get_draft_board` to see picks, prices, and remaining budgets
2. Call `get_roster_needs` to track which positions you still need to fill
3. Use `get_player_info` and `compare_players` to evaluate nomination targets

## Budget Strategy
- **Stars & scrubs**: Spend $40-60+ on 4-5 elite players, fill the rest at $1-5
- **Balanced**: Spread budget more evenly ($10-25 per player)
- **Track opponent budgets**: When rivals are low on cash, you can win players cheaply
- **Position scarcity**: C and SS have only 1 slot each — elite options are rare and expensive

## The 14 Categories
| Hitting (7) | Pitching (7) |
|---|---|
| AVG | WHIP (lower wins) |
| HR | ERA (lower wins) |
| OPS | K (strikeouts) |
| R (runs) | W (wins) |
| RBI | L (lower wins) |
| SB (stolen bases) | SV (saves) |
| B_SO (lower wins) | HLD (holds) |

## Tips
- Don't overspend early — prices tend to drop as budgets shrink
- Nominate players you DON'T want early to drain opponent budgets
- $1 closers late in the draft can carry your SV/HLD categories
- Track which categories each team is building toward to predict demand
"""

    @mcp.resource("espn://info/league-settings")
    async def league_settings_info() -> str:
        """League format, scoring categories, and roster configuration."""
        return """\
# El Rey — League Settings

## Format
- **League**: El Rey (league ID 612122596)
- **Scoring**: Head-to-Head Categories (H2H)
- **Draft**: Auction ($280 budget per team)
- **Sport**: MLB Baseball

## Scoring Categories (14 total)

### Hitting (7 categories)
| Category | Abbreviation | Direction |
|---|---|---|
| Batting Average | AVG | Higher wins |
| Home Runs | HR | Higher wins |
| OPS | OPS | Higher wins |
| Runs | R | Higher wins |
| RBI | RBI | Higher wins |
| Stolen Bases | SB | Higher wins |
| Batter Strikeouts | B_SO | **Lower wins** |

### Pitching (7 categories)
| Category | Abbreviation | Direction |
|---|---|---|
| WHIP | WHIP | **Lower wins** |
| ERA | ERA | **Lower wins** |
| Strikeouts | K | Higher wins |
| Wins | W | Higher wins |
| Losses | L | **Lower wins** |
| Saves | SV | Higher wins |
| Holds | HLD | Higher wins |

## Key Notes
- Each weekly matchup is decided by winning more categories than your opponent
- 4 categories are "lower is better": B_SO, WHIP, ERA, L
- Winning 8-6 counts the same as winning 14-0 in the standings
"""

    @mcp.resource("espn://skill/matchup-scout")
    async def skill_matchup_scout() -> str:
        """Matchup scouting — analyze your H2H matchup and find advantages."""
        return """\
# Matchup Scout

## Steps
1. `get_standings` — Check current league position and momentum
2. `get_matchup` — View this week's H2H category breakdown
3. `get_team_roster` (opponent) — Find their lineup weaknesses
4. `get_my_roster` — Review your lineup for optimization opportunities
5. `get_free_agents` — Find pickups that target close categories

## Analysis Framework
- Identify categories you're currently winning vs losing
- Focus on "swing" categories (close margins) — these decide the matchup
- Check if opponent has injured or IL players creating a category gap
- Recommend lineup changes or free agent pickups to flip close categories
"""

    @mcp.resource("espn://skill/free-agent-finder")
    async def skill_free_agent_finder() -> str:
        """Free agent recommendations — find the best available players."""
        return """\
# Free Agent Finder

## Steps
1. `get_scoring_categories` — Understand what stats matter
2. `get_my_roster` — Identify position gaps and weak spots
3. `get_roster_needs` — See which positions need filling
4. `get_free_agents` (filter by position) — Browse available players
5. `get_player_info` — Deep dive on promising candidates
6. `compare_players` — Head-to-head comparison vs your current player

## Evaluation Criteria
- Category impact: Which of the 14 categories does this player help?
- Position scarcity: Is this a thin position (C, SS) or deep (OF, UTIL)?
- Roster fit: Does the player fill a gap or duplicate existing strength?
- Recent performance vs season stats — is the player trending up or down?
"""
