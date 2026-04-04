"""Build plugin bundles for Claude Cowork and OpenClaw."""

import json
import shutil
import tempfile
from pathlib import Path
from zipfile import ZipFile

import typer
from rich.console import Console

app = typer.Typer()
console = Console()

TARGETS = ("claude", "openclaw")


def _find_project_root() -> Path:
    """Find the project root by looking for .claude-plugin/plugin.json."""
    # Try relative to this file first (mcp_server/cli/build_plugin.py -> root)
    root = Path(__file__).parent.parent.parent
    if (root / ".claude-plugin" / "plugin.json").exists():
        return root
    # Fall back to cwd
    cwd = Path.cwd()
    if (cwd / ".claude-plugin" / "plugin.json").exists():
        return cwd
    raise typer.BadParameter("Could not find project root (no .claude-plugin/plugin.json found)")


def _build_bundle(
    root: Path,
    tmp_path: Path,
    *,
    target: str,
    url: str | None,
    include_memory: bool,
) -> None:
    """Assemble a plugin bundle in tmp_path."""
    # Copy plugin manifest
    plugin_dir = tmp_path / ".claude-plugin"
    plugin_dir.mkdir()
    shutil.copy2(root / ".claude-plugin" / "plugin.json", plugin_dir / "plugin.json")

    # Copy skills
    skills_src = root / "skills"
    if skills_src.exists():
        shutil.copytree(skills_src, tmp_path / "skills")

    # Copy agents
    agents_src = root / "agents"
    if agents_src.exists():
        shutil.copytree(agents_src, tmp_path / "agents")

    # Copy commands
    commands_src = root / "commands"
    if commands_src.exists():
        shutil.copytree(commands_src, tmp_path / "commands")

    # Build .mcp.json
    mcp_servers: dict = {}

    if url:
        mcp_servers["espn-baseball"] = {"type": "url", "url": url}
    else:
        mcp_servers["espn-baseball"] = {
            "command": "uv",
            "args": ["run", "--project", ".", "espn-mcp"],
        }

    if include_memory:
        memory_src = root / "memory"
        if memory_src.exists():
            shutil.copytree(memory_src, tmp_path / "memory")
            mcp_servers["espn-memory"] = {
                "command": "uv",
                "args": ["run", "--project", "./memory", "python", "server.py"],
                "env": {"MEMORY_DB_PATH": "~/.espn-fantasy/memory.db"},
            }

    mcp_config = {"mcpServers": mcp_servers}
    (tmp_path / ".mcp.json").write_text(json.dumps(mcp_config, indent=2) + "\n")


@app.command()
def build(
    url: str = typer.Option(
        None, "--url",
        help="MCP server SSE URL (e.g. https://your-app.up.railway.app/sse). Omit for local stdio.",
    ),
    target: str = typer.Option(
        "claude", "--target", "-t",
        help=f"Target platform: {', '.join(TARGETS)}",
    ),
    output: str = typer.Option(
        None, "--output", "-o",
        help="Output path for the zip file (default: ~/Desktop/espn-fantasy-{target}-plugin.zip)",
    ),
    include_memory: bool = typer.Option(
        True, "--memory/--no-memory",
        help="Include the memory MCP server in the bundle",
    ),
) -> None:
    """Build a plugin bundle for Claude Cowork or OpenClaw."""
    if target not in TARGETS:
        raise typer.BadParameter(f"Unknown target '{target}'. Choose from: {', '.join(TARGETS)}")

    root = _find_project_root()

    if output is None:
        output = str(Path.home() / "Desktop" / f"espn-fantasy-{target}-plugin.zip")
    output_path = Path(output)

    # Claude Cowork requires a remote URL
    if target == "claude" and url is None:
        raise typer.BadParameter(
            "Claude Cowork requires --url (your Railway SSE endpoint). "
            "Example: --url https://your-app.up.railway.app/sse"
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        _build_bundle(root, tmp_path, target=target, url=url, include_memory=include_memory)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output_path, "w") as zf:
            for file in sorted(tmp_path.rglob("*")):
                if file.is_file():
                    arcname = file.relative_to(tmp_path)
                    zf.write(file, arcname)

    console.print(f"\n[green]Plugin zip created:[/green] {output_path}")
    if url:
        console.print(f"[dim]MCP transport:[/dim] HTTP (SSE) → {url}")
    else:
        console.print("[dim]MCP transport:[/dim] stdio (local)")

    console.print(f"\n[bold]Next steps ({target}):[/bold]")
    if target == "claude":
        console.print("1. Upload the zip to Cowork > Customize > Plugins")
        console.print(f"2. Add remote MCP connector with URL: {url}")
        console.print('3. Start a conversation and try: "Show my fantasy baseball standings"')
    else:
        if url:
            console.print(f"1. openclaw plugins install {output_path}")
        else:
            console.print(f"1. openclaw plugins install {root}")
            console.print(f"   (or from zip: openclaw plugins install {output_path})")
        console.print("2. openclaw gateway restart")
        console.print('3. Start a conversation and try: "Show my fantasy baseball standings"')
