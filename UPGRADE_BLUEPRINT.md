# ESPN Fantasy Plugin — Upgrade Blueprint

## Purpose

This document is a comprehensive guide for bringing the ESPN Fantasy Baseball MCP plugin to the same level of maturity as the [Rappi Claude Plugin](https://github.com/garavitgabriel/rappi-claude-plugin). Pass this to an agent to create a plan and execute.

The Rappi plugin is the **reference implementation** — it works across Claude Code, Claude Desktop, Claude Cowork (web), and OpenClaw, with 39 MCP tools, 7 MCP resources, 4 skills, a memory system, CLI, and full documentation. This blueprint maps what ESPN has, what it's missing, and exactly how to close each gap.

---

## Current State: ESPN Fantasy Plugin

| Aspect | Current | Target (match Rappi) |
|--------|---------|---------------------|
| MCP Tools | 16 | 16 (already complete for the domain) |
| MCP Resources | 0 | 5+ (workflow playbooks, skill resources) |
| Skills | 8 (in plugin/) | 8 (keep, but move to repo root) |
| Commands | 5 (in plugin/commands/) | 5 (keep, but move to repo root) |
| Agent | 1 (in plugin/agents/) | 1 (keep, but move to repo root) |
| Memory | SQLite MCP (in plugin/memory/) | SQLite MCP (keep, integrate better) |
| CLI | 16 subcommands (argparse) | 16 (consider migrating to Typer for consistency) |
| Auth | `.env` file with ESPN cookies | `.env` + `espn auth token` CLI command |
| Transport | stdio + SSE (Railway) | stdio + SSE (same pattern) |
| OpenClaw support | None | Bundle compatible + install script |
| Cowork plugin | None (plugin/ dir exists but not packaged) | `build-plugin` CLI command generates zip |
| Documentation | CLAUDE.md + README.md | CLAUDE.md + README.md + docs/openclaw-setup.md |
| Tests | pytest (basic) | pytest (expand coverage) |
| CI | None | GitHub Actions |
| Open source files | LICENSE only | LICENSE + CONTRIBUTING.md + .env.example + CI |
| Package manager | venv + requirements.txt | uv + pyproject.toml (modern Python) |

---

## Architecture Comparison

### Rappi (reference)

```
rappi-claude-plugin/          ← ONE repo, ONE package
├── .claude-plugin/           ← Plugin manifest (repo root)
├── .mcp.json                 ← MCP config (repo root)
├── skills/                   ← Skills (repo root)
├── agents/                   ← Agent (repo root)
├── src/rappi/                ← Python package
│   ├── mcp/server.py         ← 39 tools + 7 resources
│   ├── services/             ← Business logic
│   ├── memory/               ← SQLite persistence
│   ├── cli/                  ← Typer CLI
│   ├── models/               ← Pydantic models
│   └── constants.py          ← All API config
├── docs/                     ← Platform-specific guides
├── install-openclaw.sh       ← OpenClaw installer
└── pyproject.toml            ← uv/hatch managed
```

### ESPN (current)

```
espn-api/                     ← Forked repo
├── .mcp.json                 ← Points to local venv Python (hardcoded path!)
├── espn_api/                 ← Upstream library (don't modify)
├── mcp_server/               ← MCP server + CLI + tools
│   ├── server.py             ← FastMCP server (16 tools)
│   ├── tools.py              ← Tool definitions
│   ├── formatters.py         ← Output formatters
│   ├── config.py             ← ESPN League config
│   └── cli.py                ← Argparse CLI
├── plugin/                   ← Plugin bundle (SEPARATE from root)
│   ├── .claude-plugin/       ← Plugin manifest
│   ├── .mcp.json             ← Remote SSE + local memory
│   ├── skills/               ← 8 skills
│   ├── commands/             ← 5 commands
│   ├── agents/               ← 1 agent
│   └── memory/               ← SQLite memory MCP server
├── venv/                     ← Committed? Should be gitignored
├── requirements.txt          ← Deps
└── setup.py                  ← Legacy packaging
```

### Key Structural Issue

The ESPN plugin has the **plugin bundle inside a subdirectory** (`plugin/`), separate from the MCP server at the root. This means:

1. Claude Code doesn't auto-discover the plugin (it looks at repo root for `.claude-plugin/`)
2. OpenClaw can't install the repo as a bundle (no `.claude-plugin/` at root)
3. Users must use `--plugin-dir ./plugin` manually
4. The `.mcp.json` at root has a hardcoded absolute venv path

**Fix:** Move plugin artifacts to repo root (same as Rappi).

---

## Gap Analysis — What Needs to Change

### 1. STRUCTURAL: Move plugin to repo root (HIGH PRIORITY)

**Current:** `plugin/.claude-plugin/`, `plugin/skills/`, `plugin/agents/`, `plugin/commands/`
**Target:** `.claude-plugin/`, `skills/`, `agents/`, `commands/` at repo root

Steps:
- Move `plugin/.claude-plugin/` → `.claude-plugin/`
- Move `plugin/skills/` → `skills/`
- Move `plugin/agents/` → `agents/`
- Move `plugin/commands/` → `commands/`
- Move `plugin/memory/` → `memory/` (or integrate into mcp_server)
- Update `plugin/.mcp.json` → `.mcp.json` (merge with existing)
- Remove `plugin/` directory
- Update `plugin/settings.json` → `.claude/settings.json`

### 2. FIX .mcp.json (HIGH PRIORITY)

**Current root `.mcp.json`:**
```json
{
  "mcpServers": {
    "espn-baseball": {
      "command": "/Users/gabrielgaravit/Projects/espn-api/venv/bin/python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/Users/gabrielgaravit/Projects/espn-api"
    }
  }
}
```

**Problem:** Hardcoded absolute path. Won't work for anyone else.

**Target (after migrating to uv):**
```json
{
  "mcpServers": {
    "espn-fantasy": {
      "command": "uv",
      "args": ["run", "--project", ".", "espn-mcp"]
    },
    "espn-memory": {
      "command": "uv",
      "args": ["run", "--project", "./memory", "python", "server.py"],
      "env": {
        "MEMORY_DB_PATH": "~/.espn-fantasy/memory.db"
      }
    }
  }
}
```

### 3. MIGRATE TO UV + PYPROJECT.TOML (MEDIUM PRIORITY)

**Current:** `setup.py` + `requirements.txt` + `venv/`
**Target:** `pyproject.toml` + `uv.lock` (managed by uv)

Steps:
- Create `pyproject.toml` with all deps and entry points
- Add entry point: `espn-mcp` → `mcp_server.server:run_server`
- Add entry point: `espn` → `mcp_server.cli:main` (CLI)
- Remove `setup.py`, `setup.cfg`, `requirements.txt`, `requirementsV2.txt`
- Delete `venv/` from repo (should be gitignored)
- Update `.mcp.json` to use `uv run`
- Update Dockerfile/Procfile for uv

### 4. ADD MCP RESOURCES (MEDIUM PRIORITY)

Rappi has 7 resources. ESPN has 0. Add these to `mcp_server/server.py`:

```python
@mcp.resource("espn://workflow/season")
async def season_workflow() -> str:
    """Weekly workflow for in-season management."""
    # Matchup scouting → roster optimization → waiver claims → trade analysis

@mcp.resource("espn://workflow/draft")
async def draft_workflow() -> str:
    """Auction draft day playbook."""
    # Budget strategy → position scarcity → nomination targets → bid guidance

@mcp.resource("espn://info/league-settings")
async def league_settings_info() -> str:
    """League format, scoring categories, roster slots."""
    # H2H Categories, 14 cats, roster config

@mcp.resource("espn://skill/matchup-scout")
async def skill_matchup_scout() -> str:
    """Matchup scouting skill as MCP resource."""

@mcp.resource("espn://skill/free-agent-finder")
async def skill_free_agent_finder() -> str:
    """Free agent recommendations skill as MCP resource."""

# ... one resource per skill (8 total)
```

This lets OpenClaw and other MCP clients auto-discover workflow instructions.

### 5. ADD AUTH CLI COMMAND (MEDIUM PRIORITY)

**Current:** Users manually edit `.env` with ESPN cookies (ESPN_S2, ESPN_SWID)
**Target:** CLI command for easy setup, especially headless servers

```bash
espn auth token <ESPN_S2> <ESPN_SWID>           # Set credentials
espn auth token <ESPN_S2> <ESPN_SWID> --league 612122596 --team "Gabriel"
espn auth status                                 # Verify connection
espn auth logout                                 # Clear credentials
```

Store in `~/.espn-fantasy/config.json` (same pattern as Rappi's `~/.rappi/config.json`).

**How to get ESPN cookies:**
1. Log in to ESPN Fantasy at fantasy.espn.com
2. Open browser DevTools → Application → Cookies
3. Copy `espn_s2` and `SWID` values

### 6. ADD OPENCLAW SUPPORT (MEDIUM PRIORITY)

Same pattern as Rappi:

```bash
# install-openclaw.sh
# - Checks for uv, installs if missing
# - uv sync
# - openclaw mcp set espn-fantasy ...
# - Copies skills to ~/.openclaw/workspace/skills/
# - Prints next steps
```

Add `docs/openclaw-setup.md` with:
- Local installation (stdio)
- Remote installation (Railway SSE)
- Auth on headless servers
- Tool naming (`mcp__espn-fantasy__*` vs `espn-fantasy__*`)

### 7. ADD BUILD-PLUGIN CLI COMMAND (MEDIUM PRIORITY)

Same pattern as Rappi:

```bash
espn build-plugin build --target claude --url https://your-railway.app/sse
espn build-plugin build --target openclaw
espn build-plugin build --target openclaw --url https://your-railway.app/sse
```

Generates a zip with: `.claude-plugin/`, `.mcp.json`, `skills/`, `commands/`, `agents/`.

### 8. UPDATE DOCUMENTATION (MEDIUM PRIORITY)

**README.md** should match Rappi's structure:
- How It Works (example conversations)
- Install (Prerequisites, Setup, Authenticate, Activate)
  - Claude Code, Claude Desktop, Claude Cowork, OpenClaw (4 platforms)
- What You Can Do (Skills, Conversational, CLI)
- MCP Tools Reference (collapsible, all 16)
- Deployment (Railway)
- Security
- Development

**CLAUDE.md** — already good, just needs:
- OpenClaw mention
- Resource documentation
- Updated file paths after restructure

### 9. ADD OPEN SOURCE FILES (LOW PRIORITY)

- `CONTRIBUTING.md` — how to add tools, skills, formatters
- `.env.example` — template with placeholder values
- `.github/workflows/ci.yml` — pytest on push/PR
- `.gitignore` — make sure `venv/`, `.env`, `*.db` are excluded
- `.dockerignore` — exclude tests, .claude, venv

### 10. IMPROVE DOCKERFILE (LOW PRIORITY)

**Current:** Uses `Procfile` (Heroku-style)
**Target:** Proper `Dockerfile` like Rappi:

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
RUN uv sync --frozen --no-dev
ENV MCP_TRANSPORT=sse
CMD ["uv", "run", "espn-mcp"]
```

```json
// railway.json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": { "builder": "DOCKERFILE" },
  "deploy": { "healthcheckPath": "/health", "healthcheckTimeout": 10 }
}
```

---

## Implementation Order (Recommended)

### Phase 1: Foundation (do first)
1. **Migrate to uv + pyproject.toml** — everything else depends on this
2. **Move plugin to repo root** — enables auto-discovery
3. **Fix .mcp.json** — use `uv run` instead of hardcoded venv path
4. **Add `espn auth token` command** — enables headless setup

### Phase 2: Platform Support
5. **Add MCP resources** — workflow playbooks + skill resources
6. **Add `build-plugin` CLI** — generates Cowork and OpenClaw zips
7. **Add OpenClaw support** — install script + docs
8. **Update README** — match Rappi's structure with 4 platforms

### Phase 3: Polish
9. **Add open source files** — CONTRIBUTING.md, .env.example, CI
10. **Improve Dockerfile** — proper Docker build with uv
11. **Expand tests** — cover tools, formatters, CLI
12. **Update CLAUDE.md** — reflect all changes

---

## Key Patterns to Copy from Rappi

### 1. FastMCP Server Pattern (transport_security in constructor)
```python
# ESPN already does this correctly — same pattern as Rappi
transport = os.environ.get("MCP_TRANSPORT", "stdio")
_mcp_kwargs = dict(name="espn-fantasy", instructions="...")
if transport in ("sse", "streamable-http", "http"):
    _mcp_kwargs["transport_security"] = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    )
mcp = FastMCP(**_mcp_kwargs)
```

### 2. Uvicorn + Starlette for HTTP (already implemented)
ESPN already has the correct pattern with `/health` endpoint.

### 3. Config Manager Pattern
```python
# ~/.espn-fantasy/config.json
class ESPNConfig(BaseModel):
    espn_s2: str | None = None
    espn_swid: str | None = None
    league_id: int = 612122596
    year: int = 2026
    team_name: str = "Gabriel"

class ConfigManager:
    def load(self) -> ESPNConfig: ...
    def save(self, config: ESPNConfig): ...
    def update(self, **kwargs) -> ESPNConfig: ...
```

Environment variables override file config (for Railway deployment):
- `ESPN_S2`, `ESPN_SWID`, `ESPN_LEAGUE_ID`, `ESPN_YEAR`, `ESPN_TEAM_NAME`

### 4. Skills as MCP Resources
```python
@mcp.resource("espn://skill/matchup-scout")
async def skill_matchup_scout() -> str:
    """Matchup scouting — analyze your H2H matchup and find advantages."""
    return """# Matchup Scout
    ## Steps
    1. get_standings — current league position
    2. get_matchup — this week's H2H breakdown
    3. get_team_roster on opponent — find their weaknesses
    ...
    """
```

### 5. Build-Plugin CLI
```python
@app.command()
def build(
    url: str = typer.Option(None, "--url"),
    target: str = typer.Option("claude", "--target", "-t"),
    output: str = typer.Option(None, "--output", "-o"),
) -> None:
    """Build a plugin bundle for Claude Cowork or OpenClaw."""
```

### 6. Headless Auth
```python
@app.command()
def token(
    espn_s2: str = typer.Argument(...),
    espn_swid: str = typer.Argument(...),
    league_id: int = typer.Option(612122596),
    team_name: str = typer.Option("Gabriel"),
) -> None:
    """Set ESPN credentials directly — no browser needed."""
```

---

## What NOT to Change

- **`espn_api/` directory** — This is the upstream fork. Don't modify unless fixing upstream bugs.
- **Tool logic in `tools.py`** — The 16 tools are correct for the domain. Don't add tools just to match Rappi's count.
- **Formatter pattern** — `formatters.py` as single source of truth for output is a good pattern. Keep it.
- **Memory MCP as separate server** — This is actually more modular than Rappi's integrated approach. Keep the two-server architecture.
- **H2H Categories focus** — The league-specific context is a feature, not a limitation.

---

## Files to Create (New)

| File | Purpose |
|------|---------|
| `pyproject.toml` | Modern Python packaging with entry points |
| `docs/openclaw-setup.md` | OpenClaw installation guide |
| `install-openclaw.sh` | One-command OpenClaw installer |
| `CONTRIBUTING.md` | How to add tools, skills, formatters |
| `.env.example` | Template with placeholder ESPN credentials |
| `.github/workflows/ci.yml` | pytest + lint on push |
| `Dockerfile` | Proper Docker build replacing Procfile |
| `mcp_server/auth.py` | Auth CLI commands (token, status, logout) |
| `mcp_server/build_plugin.py` | Build-plugin CLI command |

## Files to Move

| From | To |
|------|-----|
| `plugin/.claude-plugin/` | `.claude-plugin/` |
| `plugin/skills/` | `skills/` |
| `plugin/agents/` | `agents/` |
| `plugin/commands/` | `commands/` |
| `plugin/memory/` | `memory/` |
| `plugin/.mcp.json` | merge into `.mcp.json` |
| `plugin/settings.json` | `.claude/settings.json` |

## Files to Delete

| File | Reason |
|------|--------|
| `plugin/` | Moved to root |
| `setup.py` | Replaced by pyproject.toml |
| `setup.cfg` | Replaced by pyproject.toml |
| `requirements.txt` | Replaced by pyproject.toml |
| `requirementsV2.txt` | Replaced by pyproject.toml |
| `venv/` | Should never be committed |
| `Procfile` | Replaced by Dockerfile |

---

## Reference: Rappi Plugin Repo

The complete reference implementation is at:
- **Repo:** https://github.com/garavitgabriel/rappi-claude-plugin
- **Local:** `/Users/gabrielgaravit/Projects/Rappi Claude Plugin/`
- **Key files to study:**
  - `src/rappi/mcp/server.py` — 39 tools + 7 resources, SSE transport pattern
  - `src/rappi/cli/build_plugin.py` — build-plugin with --target flag
  - `src/rappi/cli/auth.py` — auth login/token/status/logout commands
  - `install-openclaw.sh` — OpenClaw installer script
  - `docs/openclaw-setup.md` — OpenClaw setup guide
  - `README.md` — 4-platform documentation structure
  - `CLAUDE.md` — Developer reference
  - `pyproject.toml` — Modern Python packaging with uv
