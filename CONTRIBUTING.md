# Contributing

## Setup

```bash
git clone https://github.com/garavitgabriel/espn-api.git
cd espn-api
uv sync --group dev

# Authenticate (pick one)
uv sync --extra browser && uv run playwright install chromium
uv run espn auth login          # browser login — easiest
# or: uv run espn auth token <ESPN_S2> <ESPN_SWID>
```

## Running Tests

```bash
uv run pytest
```

## Project Structure

- **`espn_api/`** — Upstream ESPN Fantasy API library. Avoid modifying unless fixing upstream bugs.
- **`mcp_server/`** — MCP server, CLI, and tools. This is where most development happens.
  - `tools.py` — MCP tool definitions (registered on FastMCP)
  - `resources.py` — MCP resource definitions
  - `formatters.py` — Pure functions that turn espn_api objects into markdown tables
  - `config.py` — League singleton and credential loading
  - `auth.py` — ConfigManager for `~/.espn-fantasy/config.json`
  - `cli/` — Typer CLI with subcommands
  - `server.py` — FastMCP server entry point

## Adding a New MCP Tool

1. **Formatter**: Add a `fmt_*` function in `formatters.py` if you need new output formatting.
2. **Tool**: Add a `@mcp.tool()` function in `tools.py` inside `register_tools()`.
3. **CLI**: Add a `@app.command()` function in `cli/__init__.py`.
4. **Docs**: Update the CLI commands table in `README.md` and the tool mapping in `CLAUDE.md`.

## Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md` with frontmatter (`name`, `description`) and step-by-step instructions.
2. Reference MCP tool names (`get_*`, `compare_*`, `analyze_*`).
3. Include conditional memory steps: "If memory tools are available, call X."
4. Update the skill mapping table in `CLAUDE.md`.

## Code Style

- Formatters are the **single source of truth** for output. Both tools and CLI call formatters.
- MCP tools and CLI commands are **1:1**. When adding a new capability, add it to both.
- The league uses **H2H Categories** scoring. Advice should focus on winning individual stat categories.
