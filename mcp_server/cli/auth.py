"""CLI commands for ESPN authentication."""

import typer
from rich.console import Console
from rich.table import Table

from mcp_server.auth import ConfigManager

app = typer.Typer()
console = Console()


@app.command()
def token(
    espn_s2: str = typer.Argument(..., help="ESPN espn_s2 cookie value"),
    espn_swid: str = typer.Argument(..., help="ESPN SWID cookie value (include curly braces)"),
    league_id: int = typer.Option(612122596, "--league", "-l", help="ESPN league ID"),
    year: int = typer.Option(2026, "--year", "-y", help="Season year"),
    team_name: str = typer.Option("Gabriel", "--team", "-t", help="Your team name (partial match)"),
) -> None:
    """Set ESPN credentials directly — no browser needed.

    Get your cookies from ESPN Fantasy > browser DevTools > Application > Cookies:
    copy the values of espn_s2 and SWID.
    """
    config_manager = ConfigManager()
    config_manager.update(
        espn_s2=espn_s2,
        espn_swid=espn_swid,
        league_id=league_id,
        year=year,
        team_name=team_name,
    )

    # Verify credentials by connecting to ESPN
    try:
        from mcp_server.config import get_league

        # Force reimport with new credentials
        import importlib
        import mcp_server.config as cfg
        importlib.reload(cfg)
        league = cfg.get_league()
        team = cfg.get_my_team(league)
        team_info = f"Team: {team.team_name}" if team else "Team: (could not resolve)"
        console.print(f"[green]Credentials saved.[/green] League: {league.settings.name} | {team_info}")
    except Exception as e:
        console.print(f"[yellow]Credentials saved but verification failed:[/yellow] {e}")
        console.print("The credentials may still work — try [bold]espn auth status[/bold].")


@app.command()
def status() -> None:
    """Check your authentication status and show config."""
    config_manager = ConfigManager()
    config = config_manager.load()

    if not config.espn_s2 or not config.espn_swid:
        console.print("[red]Not authenticated.[/red] Run: [bold]espn auth token <ESPN_S2> <ESPN_SWID>[/bold]")
        raise typer.Exit(1)

    table = Table(title="ESPN Fantasy Config", show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("ESPN_S2", config.espn_s2[:20] + "..." if config.espn_s2 else "—")
    table.add_row("ESPN_SWID", config.espn_swid or "—")
    table.add_row("League ID", str(config.league_id))
    table.add_row("Year", str(config.year))
    table.add_row("Team Name", config.team_name)
    table.add_row("Config File", str(config_manager._path))
    console.print(table)

    # Try to connect
    try:
        import importlib
        import mcp_server.config as cfg
        importlib.reload(cfg)
        league = cfg.get_league()
        team = cfg.get_my_team(league)
        console.print(f"\n[green]Connected.[/green] League: {league.settings.name}")
        if team:
            console.print(f"Your team: {team.team_name} (id={team.team_id})")
    except Exception as e:
        console.print(f"\n[red]Connection failed:[/red] {e}")


@app.command()
def logout() -> None:
    """Clear saved ESPN credentials."""
    config_manager = ConfigManager()
    config_manager.update(espn_s2=None, espn_swid=None)
    console.print("[green]Credentials cleared.[/green]")
