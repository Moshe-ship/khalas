"""CLI entry point for khalas."""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn

from khalas.display import (
    console,
    display_comparison,
    display_config_status,
    display_explain,
    display_json,
    display_optimization,
    display_savings,
)


# ── Subcommand handlers ────────────────────────────────────────────


def _cmd_compare(args: argparse.Namespace) -> int:
    """Run the compare subcommand — Arabic vs English side by side."""
    from khalas.optimizer import compare_languages

    with console.status("[bold magenta]Comparing Arabic vs English...[/bold magenta]"):
        result = compare_languages(
            arabic_prompt=args.arabic_prompt,
            english_prompt=args.english_prompt,
            provider=args.provider,
            model=args.model,
        )

    if args.json:
        display_json(result)
    else:
        display_comparison(result)

    return 0


def _cmd_optimize(args: argparse.Namespace) -> int:
    """Run the optimize subcommand — try all techniques, show savings."""
    from khalas.optimizer import optimize_prompt

    techniques = None
    if args.techniques:
        techniques = [t.strip() for t in args.techniques.split(",")]

    with console.status("[bold magenta]Optimizing prompt...[/bold magenta]"):
        results = optimize_prompt(
            prompt=args.prompt,
            provider=args.provider,
            model=args.model,
            techniques=techniques,
        )

    if args.json:
        display_json(results)
    else:
        display_optimization(results)

    return 0


def _cmd_savings(args: argparse.Namespace) -> int:
    """Run the savings subcommand — project monthly savings."""
    from khalas.optimizer import compare_languages, project_savings

    with console.status("[bold magenta]Calculating savings...[/bold magenta]"):
        comparison = compare_languages(
            arabic_prompt=args.arabic_prompt,
            english_prompt=args.english_prompt,
            provider=args.provider,
            model=args.model,
        )
        savings = project_savings(comparison, volume_millions=args.volume)

    if args.json:
        display_json(savings)
    else:
        display_savings(savings)

    return 0


def _cmd_explain(_args: argparse.Namespace) -> int:
    """Run the explain subcommand — show optimization techniques."""
    display_explain()
    return 0


def _cmd_config(args: argparse.Namespace) -> int:
    """Run the config subcommand — show configured providers."""
    from khalas.config import list_configured, ENV_KEYS

    configured = list_configured()
    unconfigured = [p for p in ENV_KEYS if p not in configured]
    display_config_status(configured, unconfigured)
    return 0


# ── Argument parser construction ───────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="khalas",
        description=(
            "Arabic Prompt Optimizer — compare AR vs EN, optimize for fewer tokens."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_get_version()}",
    )

    subparsers = parser.add_subparsers(dest="command")

    # ── compare ──
    compare_parser = subparsers.add_parser(
        "compare", help="Compare Arabic vs English prompts (default)"
    )
    compare_parser.add_argument(
        "arabic_prompt",
        help="Arabic prompt text",
    )
    compare_parser.add_argument(
        "english_prompt",
        help="Equivalent English prompt text",
    )
    compare_parser.add_argument(
        "--provider",
        required=True,
        help="LLM provider (e.g. openai, anthropic, google)",
    )
    compare_parser.add_argument(
        "--model",
        default=None,
        help="Model override (default: provider's default model)",
    )
    compare_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results as JSON",
    )

    # ── optimize ──
    optimize_parser = subparsers.add_parser(
        "optimize", help="Try all optimization techniques on a prompt"
    )
    optimize_parser.add_argument(
        "prompt",
        help="Arabic prompt text to optimize",
    )
    optimize_parser.add_argument(
        "--provider",
        required=True,
        help="LLM provider (e.g. openai, anthropic, google)",
    )
    optimize_parser.add_argument(
        "--model",
        default=None,
        help="Model override (default: provider's default model)",
    )
    optimize_parser.add_argument(
        "--techniques",
        default=None,
        help="Comma-separated list of techniques to try",
    )
    optimize_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results as JSON",
    )

    # ── savings ──
    savings_parser = subparsers.add_parser(
        "savings", help="Project monthly savings"
    )
    savings_parser.add_argument(
        "arabic_prompt",
        help="Arabic prompt text",
    )
    savings_parser.add_argument(
        "english_prompt",
        help="Equivalent English prompt text",
    )
    savings_parser.add_argument(
        "--provider",
        required=True,
        help="LLM provider (e.g. openai, anthropic, google)",
    )
    savings_parser.add_argument(
        "--model",
        default=None,
        help="Model override (default: provider's default model)",
    )
    savings_parser.add_argument(
        "--volume",
        type=float,
        default=1.0,
        help="Million tokens per month (default: 1)",
    )
    savings_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results as JSON",
    )

    # ── explain ──
    subparsers.add_parser(
        "explain", help="Explain optimization techniques"
    )

    # ── config ──
    config_parser = subparsers.add_parser(
        "config", help="Show configured providers"
    )
    config_parser.add_argument(
        "--show",
        action="store_true",
        default=True,
        help="Show provider configuration status (default)",
    )

    return parser


def _get_version() -> str:
    """Return the package version string."""
    from khalas import __version__

    return __version__


# ── Entry point ────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> NoReturn:
    """Main entry point for the khalas CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Default to compare when no subcommand is given.
    if args.command is None:
        args = parser.parse_args(["compare", *(argv or sys.argv[1:])])

    dispatch = {
        "compare": _cmd_compare,
        "optimize": _cmd_optimize,
        "savings": _cmd_savings,
        "explain": _cmd_explain,
        "config": _cmd_config,
    }

    try:
        handler = dispatch[args.command]
        code = handler(args)
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        code = 130
    except BrokenPipeError:
        # Silently handle piping to head/less.
        code = 0

    sys.exit(code)
