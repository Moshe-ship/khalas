"""Rich terminal display for khalas results."""

from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table

console = Console()

BRANDING = "[bold magenta]khalas[/bold magenta] [dim]- Arabic Prompt Optimizer[/dim]"


# ---------------------------------------------------------------------------
# Ratio color helper
# ---------------------------------------------------------------------------


def _ratio_style(ratio: float) -> str:
    """Return a Rich color based on how bad the cost/token ratio is."""
    if ratio > 2.0:
        return "red bold"
    if ratio > 1.5:
        return "yellow"
    return "green"


def _truncate(text: str, length: int = 200) -> str:
    """Truncate text to *length* characters with an ellipsis."""
    if len(text) <= length:
        return text
    return text[:length] + "..."


# ---------------------------------------------------------------------------
# Compare — Arabic vs English side by side
# ---------------------------------------------------------------------------


def display_comparison(result: dict, console: Console = console) -> None:
    """Show Arabic vs English responses side by side with stats."""
    console.print()
    console.print(BRANDING)
    console.print()

    # ── Response comparison ──
    resp_table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        padding=(0, 1),
        title="Response Comparison",
    )

    resp_table.add_column("Arabic Response", style="bold white", max_width=60)
    resp_table.add_column("English Response", style="dim white", max_width=60)

    resp_table.add_row(
        _truncate(result.get("arabic_response", ""), 200),
        _truncate(result.get("english_response", ""), 200),
    )

    console.print(resp_table)
    console.print()

    # ── Stats table ──
    ar_tokens = result.get("arabic_tokens", 0)
    en_tokens = result.get("english_tokens", 0)
    token_ratio = ar_tokens / en_tokens if en_tokens else 0.0

    ar_cost = result.get("arabic_cost", 0.0)
    en_cost = result.get("english_cost", 0.0)
    cost_ratio = ar_cost / en_cost if en_cost else 0.0

    ar_latency = result.get("arabic_latency", 0.0)
    en_latency = result.get("english_latency", 0.0)

    ratio_color = _ratio_style(cost_ratio)

    stats = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        padding=(0, 1),
        title="Stats",
    )

    stats.add_column("Metric", style="bold white", min_width=10)
    stats.add_column("Arabic", justify="right", style="white")
    stats.add_column("English", justify="right", style="white")
    stats.add_column("Ratio", justify="right")

    stats.add_row(
        "Tokens",
        str(ar_tokens),
        str(en_tokens),
        f"[{ratio_color}]{token_ratio:.2f}x[/{ratio_color}]",
    )
    stats.add_row(
        "Cost",
        f"${ar_cost:.4f}",
        f"${en_cost:.4f}",
        f"[{ratio_color}]{cost_ratio:.2f}x[/{ratio_color}]",
    )
    stats.add_row(
        "Latency",
        f"{ar_latency:.2f}s",
        f"{en_latency:.2f}s",
        "",
    )

    console.print(stats)
    console.print()

    # ── Headline ──
    console.print(
        f"  [{ratio_color}]You're paying {cost_ratio:.1f}x more for Arabic[/{ratio_color}]"
    )
    console.print()


# ---------------------------------------------------------------------------
# Optimize — show optimization results
# ---------------------------------------------------------------------------


def display_optimization(results: dict, console: Console = console) -> None:
    """Show optimization results sorted by savings."""
    console.print()
    console.print(BRANDING)
    console.print()

    techniques = sorted(
        results.get("techniques", []),
        key=lambda t: t.get("savings_pct", 0),
        reverse=True,
    )

    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        padding=(0, 1),
        title="Optimization Results",
    )

    table.add_column("Technique", style="bold white", min_width=20)
    table.add_column("Tokens Before", justify="right", style="white")
    table.add_column("Tokens After", justify="right", style="white")
    table.add_column("Savings %", justify="right")
    table.add_column("Cost Saved", justify="right")

    best_name = techniques[0].get("name", "") if techniques else ""

    for t in techniques:
        name = t.get("name", "")
        savings_pct = t.get("savings_pct", 0)
        is_best = name == best_name
        name_style = "green bold" if is_best else "white"

        table.add_row(
            f"[{name_style}]{name}[/{name_style}]",
            str(t.get("tokens_before", 0)),
            str(t.get("tokens_after", 0)),
            f"[green]{savings_pct:.1f}%[/green]" if savings_pct > 0 else f"{savings_pct:.1f}%",
            f"${t.get('cost_saved', 0):.4f}",
        )

    console.print(table)
    console.print()

    # Show best optimized prompt
    optimized = results.get("optimized_prompt", "")
    if optimized:
        console.print("[bold]Best optimized prompt:[/bold]")
        console.print()
        console.print(f"  {optimized}")
        console.print()


# ---------------------------------------------------------------------------
# Savings — monthly projection
# ---------------------------------------------------------------------------


def display_savings(savings: dict, console: Console = console) -> None:
    """Show monthly and annual savings projection."""
    console.print()
    console.print(BRANDING)
    console.print()

    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        padding=(0, 1),
        title="Savings Projection",
    )

    table.add_column("Metric", style="bold white", min_width=20)
    table.add_column("Current", justify="right", style="white")
    table.add_column("Optimized", justify="right", style="green")
    table.add_column("Savings", justify="right", style="yellow")

    monthly_tokens_cur = savings.get("monthly_tokens_current", 0)
    monthly_tokens_opt = savings.get("monthly_tokens_optimized", 0)
    monthly_cost_cur = savings.get("monthly_cost_current", 0.0)
    monthly_cost_opt = savings.get("monthly_cost_optimized", 0.0)
    annual_cur = monthly_cost_cur * 12
    annual_opt = monthly_cost_opt * 12

    table.add_row(
        "Monthly Tokens",
        f"{monthly_tokens_cur:,.0f}",
        f"{monthly_tokens_opt:,.0f}",
        f"{monthly_tokens_cur - monthly_tokens_opt:,.0f}",
    )
    table.add_row(
        "Monthly Cost",
        f"${monthly_cost_cur:,.2f}",
        f"${monthly_cost_opt:,.2f}",
        f"${monthly_cost_cur - monthly_cost_opt:,.2f}",
    )
    table.add_row(
        "Annual Projection",
        f"${annual_cur:,.2f}",
        f"${annual_opt:,.2f}",
        f"${annual_cur - annual_opt:,.2f}",
    )

    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# Config status
# ---------------------------------------------------------------------------


def display_config_status(
    configured: list[str],
    unconfigured: list[str],
    console: Console = console,
) -> None:
    """Show which providers are configured and which are not."""
    console.print()
    console.print(BRANDING)
    console.print()

    if configured:
        console.print("[bold]Configured providers:[/bold]")
        for name in configured:
            console.print(f"  [green]  {name}[/green]")

    if unconfigured:
        console.print("[bold]Unconfigured providers:[/bold]")
        for name in unconfigured:
            console.print(f"  [red]  {name}[/red]")

    console.print()


# ---------------------------------------------------------------------------
# Explain — optimization techniques
# ---------------------------------------------------------------------------


def display_explain(console: Console = console) -> None:
    """Explain the optimization techniques khalas uses."""
    console.print()
    console.print(BRANDING)
    console.print()

    console.print("[bold]Why does Arabic cost more?[/bold]")
    console.print()
    console.print(
        "  Arabic text typically uses 2-4x more tokens than equivalent English\n"
        "  because LLM tokenizers are trained predominantly on English data.\n"
        "  Each Arabic word often fragments into multiple subword tokens, while\n"
        "  common English words stay as single tokens."
    )
    console.print()

    console.print("[bold]Optimization techniques:[/bold]")
    console.print()

    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        padding=(0, 1),
    )

    table.add_column("Technique", style="bold white", min_width=24)
    table.add_column("Description")

    table.add_row(
        "Transliteration",
        "Convert Arabic to Arabizi (transliterated Latin) to reduce token count",
    )
    table.add_row(
        "Hybrid",
        "Mix Arabic keywords with English structure for prompts",
    )
    table.add_row(
        "Prompt Compression",
        "Remove redundant words and shorten the Arabic prompt",
    )
    table.add_row(
        "English Translation",
        "Translate the full prompt to English as an upper-bound baseline",
    )
    table.add_row(
        "System Prompt Tuning",
        "Move static Arabic instructions into a reusable system prompt",
    )

    console.print(table)
    console.print()

    console.print("[bold]Usage:[/bold]")
    console.print()
    console.print("  1. Run [bold cyan]khalas compare[/bold cyan] to see the Arabic vs English gap")
    console.print("  2. Run [bold cyan]khalas optimize[/bold cyan] to try all techniques on your prompt")
    console.print("  3. Run [bold cyan]khalas savings[/bold cyan] to project monthly cost reduction")
    console.print()


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def display_json(data: dict) -> None:
    """Print data as formatted JSON."""
    print(json.dumps(data, ensure_ascii=False, indent=2))
