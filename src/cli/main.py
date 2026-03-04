"""
Hedge Fund 13F Tracker - CLI entry point.
Usage: tracker [command] [options]
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich import box

# Allow running directly without install
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db.queries import list_funds, list_holdings, list_quarters

console = Console()


# ── Root group ──────────────────────────────────────────────────────────────

@click.group()
@click.version_option("0.1.0", prog_name="tracker")
def cli():
    """Monitor hedge fund 13F filings from the SEC."""


# ── funds ────────────────────────────────────────────────────────────────────

@cli.group()
def funds():
    """Commands for tracked hedge funds."""


@funds.command("list")
def funds_list():
    """List all tracked hedge funds."""
    rows = list_funds()
    if not rows:
        console.print("[yellow]No funds found. Run: python scripts/init_db.py[/]")
        return

    table = Table(title="Tracked Funds", box=box.ROUNDED)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Fund Name", style="bold cyan")
    table.add_column("CIK", style="dim")
    table.add_column("Manager")
    table.add_column("Status")

    for f in rows:
        status = "[green]Active[/]" if f["active"] else "[red]Inactive[/]"
        table.add_row(
            str(f["id"]),
            f["name"],
            f["cik"] or "—",
            f["manager"] or "—",
            status,
        )

    console.print(table)


# ── holdings ─────────────────────────────────────────────────────────────────

@cli.group()
def holdings():
    """Query fund position holdings."""


@holdings.command("show")
@click.argument("fund_name")
@click.option("--quarter", "-q", default=None, help='Quarter e.g. "2024Q4"')
@click.option("--top", "-n", default=0, help="Show top N positions (0 = all)")
def holdings_show(fund_name: str, quarter: str | None, top: int):
    """Show holdings for FUND_NAME."""
    quarters = list_quarters(fund_name)
    if not quarters:
        console.print(f"[red]Fund not found or no data:[/] {fund_name}")
        console.print("Tip: run [bold]tracker funds list[/] to see available funds.")
        raise SystemExit(1)

    q = quarter or quarters[0]
    rows = list_holdings(fund_name, q)

    if not rows:
        console.print(f"[yellow]No holdings for {fund_name!r} in {q}[/]")
        return

    fund_display = rows[0]["fund_name"]
    title = f"{fund_display} — {q}"
    if top:
        rows = rows[:top]
        title += f" (top {top})"

    table = Table(title=title, box=box.ROUNDED)
    table.add_column("Ticker", style="bold yellow", width=8)
    table.add_column("Company", style="cyan")
    table.add_column("Shares", justify="right")
    table.add_column("Value $K", justify="right")
    table.add_column("% Port.", justify="right")
    table.add_column("Change", justify="center")

    CHANGE_COLORS = {
        "NEW": "bold green",
        "ADDED": "green",
        "REDUCED": "red",
        "SOLD": "bold red",
    }

    for pos in rows:
        ct = pos["change_type"] or ""
        cp = pos["change_pct"]
        change_str = ct
        if cp is not None:
            sign = "+" if cp > 0 else ""
            change_str = f"{ct} {sign}{cp:.1f}%"
        color = CHANGE_COLORS.get(ct, "white")

        table.add_row(
            pos["ticker"],
            pos["company_name"],
            f"{pos['shares']:,}",
            f"{pos['value_usd']:,.0f}",
            f"{pos['pct_portfolio']:.1f}%" if pos["pct_portfolio"] else "—",
            f"[{color}]{change_str}[/]" if change_str else "—",
        )

    console.print(table)


@holdings.command("quarters")
@click.argument("fund_name")
def holdings_quarters(fund_name: str):
    """List available quarters for FUND_NAME."""
    quarters = list_quarters(fund_name)
    if not quarters:
        console.print(f"[red]No data found for:[/] {fund_name}")
        raise SystemExit(1)
    console.print(f"Available quarters for [bold]{fund_name}[/]:")
    for q in quarters:
        console.print(f"  • {q}")


# ── analytics (Sprint 2 stub) ─────────────────────────────────────────────

@cli.group()
def analyze():
    """Analytics and consensus commands (Sprint 2)."""


@analyze.command("consensus")
@click.option("--quarter", "-q", default=None, help="Quarter to analyze")
@click.option("--min-funds", default=3, show_default=True, help="Min funds holding position")
def analyze_consensus(quarter: str | None, min_funds: int):
    """Find tickers held by MIN_FUNDS or more funds. [Sprint 2]"""
    console.print("[dim]Consensus analysis coming in Sprint 2.[/]")


@analyze.command("changes")
@click.argument("fund_name")
@click.option("--threshold", "-t", default=20.0, show_default=True,
              help="Alert threshold % change")
def analyze_changes(fund_name: str, threshold: float):
    """Show significant position changes for FUND_NAME. [Sprint 2]"""
    console.print("[dim]Change detection coming in Sprint 2.[/]")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
