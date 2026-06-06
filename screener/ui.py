"""gstack-style terminal UI: ASCII banner, pill toggles, agent scores, strategy guide."""

from __future__ import annotations

from typing import Any, Dict, List, Set

import pandas as pd
import questionary
from questionary import Style as QStyle
from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from rich.text import Text

console = Console()

# Colour tokens
G = "bright_green"
DG = "green"
Y = "yellow"
R = "red"
W = "white"
DIM = "dim bright_green"
CYAN = "cyan"

PILL_STYLE = QStyle(
    [
        ("qmark", "fg:ansigreen bold"),
        ("question", "fg:ansigreen bold"),
        ("pointer", "fg:ansigreen bold"),
        ("highlighted", "fg:ansiblack bg:ansigreen bold"),
        ("selected", "fg:ansigreen"),
        ("separator", "fg:ansigreen"),
        ("instruction", "fg:ansidarkgray"),
        ("text", "fg:ansigreen"),
        ("disabled", "fg:ansidarkgray italic"),
    ]
)

FILTER_CHOICES = [
    ("[ PRICE >= $2 ]", "min_price"),
    ("[ GAIN >= +8% (7d) ]", "min_gain_7d"),
    ("[ AVG VOL >= 500K ]", "min_avg_volume"),
    ("[ RSI <= 80 ]", "max_rsi"),
    ("[ MARKET CAP FILTER ]", "market_cap"),
    ("[ EXCLUDE VOLATILE ]", "exclude_volatility"),
    ("[ DOLLAR VOL >= $5M ]", "min_dollar_vol"),
    ("[ NEAR 52W HIGH ]", "near_52w_high"),
]

AGENT_CHOICES = [
    ("[ * MOMENTUM ]", "momentum"),
    ("[ + BREAKOUT ]", "breakout"),
    ("[ ^ VOLUME SURGE ]", "volume_surge"),
    ("[ > RELATIVE STRENGTH ]", "relative_strength"),
    ("[ ~ MEAN REVERSION ]", "mean_reversion"),
]

BANNER = r"""
  ██████╗ ███████╗███████╗████████╗     ███████╗    ██████╗  █████╗ ██╗   ██╗███████╗
  ██╔══██╗██╔════╝██╔════╝╚══██╔══╝     ╚════██║   ██╔══██╗██╔══██╗╚██╗ ██╔╝██╔════╝
  ██████╔╝█████╗  ███████╗   ██║            ██╔╝   ██║  ██║███████║ ╚████╔╝ ███████╗
  ██╔══██╗██╔══╝  ╚════██║   ██║           ██╔╝    ██║  ██║██╔══██║  ╚██╔╝  ╚════██║
  ██████╔╝███████╗███████║   ██║           ██║     ██████╔╝██║  ██║   ██║   ███████║
  ╚═════╝ ╚══════╝╚══════╝   ╚═╝           ╚═╝     ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝
"""

TAGLINE = "Multi-agent uptrend screener. Volume confirmed. Benchmark compared."
SUBTAGLINE = "5 strategy agents. 7 benchmarks. SQLite-cached. Watch mode."


def print_banner(version: str = "2.0", cache_stats: Dict[str, int] | None = None) -> None:
    console.print()
    console.print(Align.center(Text(BANNER, style=Style(color=G, bold=True))))
    console.print(Align.center(Text(f'"{TAGLINE}"', style=Style(color=DG, italic=True))))
    console.print(Align.center(Text(SUBTAGLINE, style=Style(color=DG))))
    console.print()

    stats_text = "—"
    if cache_stats:
        stats_text = f"{cache_stats.get('fresh', 0)} fresh / {cache_stats.get('total', 0)} total"

    stats = [
        Panel(
            Align.center(Text("S&P 500\nNASDAQ\nRUSSELL 2000\nExtended", style=G)),
            title=f"[bold {G}]> UNIVERSE[/]",
            border_style=DG,
            padding=(0, 1),
        ),
        Panel(
            Align.center(Text("5\nstrategy agents", style=f"bold {G}")),
            title=f"[bold {G}]> AGENTS[/]",
            border_style=DG,
            padding=(0, 1),
        ),
        Panel(
            Align.center(Text("VOO QQQ VXF IWM\nVTIAX GLD TLT", style=G)),
            title=f"[bold {G}]> BENCHMARKS[/]",
            border_style=DG,
            padding=(0, 1),
        ),
        Panel(
            Align.center(Text("RSI MACD ATR\nMAs Vol Trend", style=G)),
            title=f"[bold {G}]> METRICS[/]",
            border_style=DG,
            padding=(0, 1),
        ),
        Panel(
            Align.center(Text(f"v{version}\n{stats_text}", style=DG)),
            title=f"[bold {G}]> CACHE[/]",
            border_style=DG,
            padding=(0, 1),
        ),
    ]
    console.print(Columns(stats, equal=True, expand=True))
    console.print()


def run_pill_toggles(defaults: Set[str] | None = None) -> Set[str]:
    all_keys = [v for _, v in FILTER_CHOICES]
    default_set = defaults if defaults is not None else set(all_keys)

    console.print(
        f"[bold {G}]> ACTIVE FILTERS[/]  [dim green](space to toggle, enter to confirm)[/]"
    )
    console.print()
    selected = questionary.checkbox(
        "Select filters to apply:",
        choices=[
            questionary.Choice(label, value=key, checked=(key in default_set))
            for label, key in FILTER_CHOICES
        ],
        style=PILL_STYLE,
    ).ask()
    if selected is None:
        selected = list(default_set)
    console.print()
    active = set(selected)
    active_labels = [label for label, key in FILTER_CHOICES if key in active]
    console.print(
        f"[bold {G}]  FILTERS LOCKED:[/] " + "  ".join(f"[{G}]{l}[/{G}]" for l in active_labels[:6])
    )
    console.print()
    return active


def run_agent_toggles(defaults: Set[str] | None = None) -> List[str]:
    all_keys = [v for _, v in AGENT_CHOICES]
    default_set = defaults if defaults is not None else set(all_keys)

    console.print(
        f"[bold {G}]> ACTIVE AGENTS[/]  [dim green](space to toggle, enter to confirm)[/]"
    )
    console.print()
    selected = questionary.checkbox(
        "Select strategy agents:",
        choices=[
            questionary.Choice(label, value=key, checked=(key in default_set))
            for label, key in AGENT_CHOICES
        ],
        style=PILL_STYLE,
    ).ask()
    if selected is None or not selected:
        selected = list(default_set)
    console.print()
    active_labels = [label for label, key in AGENT_CHOICES if key in selected]
    console.print(
        f"[bold {G}]  AGENTS LOCKED:[/] " + "  ".join(f"[{G}]{l}[/{G}]" for l in active_labels)
    )
    console.print()
    return list(selected)


def print_market_summary(
    benchmarks: Dict[str, Dict[str, Any]],
    regime: Dict[str, str] | None = None,
) -> None:
    console.print(Rule(f"[bold {G}]> BENCHMARK COMPARISON  (7-day)[/]", style=DG))
    console.print()

    panels = []
    for ticker, info in benchmarks.items():
        pct = info.get("change_7d", 0.0)
        price = info.get("price", 0.0)
        color = G if pct >= 0 else R
        arrow = "up" if pct >= 0 else "dn"
        sign = "+" if pct >= 0 else ""
        content = Text(justify="center")
        content.append(f"${price:.2f}\n", style=W)
        content.append(f"{arrow} {sign}{pct:.2f}%\n", style=f"bold {color}")
        content.append(info.get("description", ""), style=DIM)
        panels.append(
            Panel(
                Align.center(content),
                title=f"[bold {G}]{ticker}[/]  [dim green]{info.get('name', '')}[/]",
                border_style=color,
                padding=(0, 1),
            )
        )
    console.print(Columns(panels, equal=True, expand=True))
    console.print()

    if regime:
        trend_color = {"bullish": G, "bearish": R, "mixed": Y}.get(regime.get("trend", ""), W)
        risk_color = {"on": G, "off": R, "neutral": Y}.get(regime.get("risk", ""), W)
        regime_text = Text()
        regime_text.append("  REGIME:  ", style=f"bold {G}")
        regime_text.append(
            f"trend={regime.get('trend', '?').upper()}  ", style=f"bold {trend_color}"
        )
        regime_text.append(f"risk={regime.get('risk', '?').upper()}  ", style=f"bold {risk_color}")
        regime_text.append(
            f"leadership={regime.get('leadership', '?').upper()}", style=f"bold {CYAN}"
        )
        console.print(regime_text)
        console.print()


def print_results_table(
    df: pd.DataFrame,
    benchmarks: Dict[str, Dict[str, Any]],
    show_agents: bool = True,
) -> None:
    voo_7d = benchmarks.get("VOO", {}).get("change_7d", 0.0)
    qqq_7d = benchmarks.get("QQQ", {}).get("change_7d", 0.0)

    console.print(Rule(f"[bold {G}]> TOP UPTREND LEADERS  (multi-agent ranked)[/]", style=DG))
    console.print()

    table = Table(
        box=box.SQUARE,
        border_style=DG,
        header_style=f"bold {G}",
        show_lines=False,
        expand=True,
    )

    table.add_column("#", style=DIM, width=4, justify="right")
    table.add_column("TICKER", style=f"bold {G}", width=8)
    table.add_column("PRICE", style=W, width=9, justify="right")
    table.add_column("7d %", style=W, width=8, justify="right")
    table.add_column("vs VOO", style=W, width=8, justify="right")
    table.add_column("vs QQQ", style=W, width=8, justify="right")
    table.add_column("RVOL", style=DG, width=7, justify="right")
    table.add_column("RSI", style=W, width=6, justify="right")
    table.add_column("MACD", style=W, width=8, justify="right")
    table.add_column("52W", style=W, width=8, justify="right")
    if show_agents:
        table.add_column("MOM", style=W, width=5, justify="right")
        table.add_column("BRK", style=W, width=5, justify="right")
        table.add_column("VOL", style=W, width=5, justify="right")
        table.add_column("RS", style=W, width=5, justify="right")
        table.add_column("MR", style=W, width=5, justify="right")
    table.add_column("SCORE", style=f"bold {G}", width=7, justify="right")
    table.add_column("STRATEGY", style=CYAN, width=12)

    for i, row in df.iterrows():
        pct = row["change_7d"]
        rsi = row["rsi_14"]
        rel_vol = row["rel_vol"]
        macd = row.get("macd_hist", 0.0)
        pct_52w = row.get("pct_from_52w_high", 0.0)

        pct_color = G if pct >= 0 else R
        rsi_color = R if rsi > 75 else (Y if rsi > 65 else G)
        rvol_color = G if rel_vol >= 1.5 else (Y if rel_vol >= 1.0 else DIM)
        macd_color = G if macd > 0 else R
        e52_color = G if pct_52w > -5 else (Y if pct_52w > -15 else R)

        vs_voo = pct - voo_7d
        vs_qqq = pct - qqq_7d

        cells = [
            str(i + 1),
            row["ticker"],
            f"${row['price']:.2f}",
            f"[{pct_color}]{'+' if pct >= 0 else ''}{pct:.1f}%[/]",
            f"[{G if vs_voo >= 0 else R}]{'+' if vs_voo >= 0 else ''}{vs_voo:.1f}%[/]",
            f"[{G if vs_qqq >= 0 else R}]{'+' if vs_qqq >= 0 else ''}{vs_qqq:.1f}%[/]",
            f"[{rvol_color}]{rel_vol:.1f}x[/]",
            f"[{rsi_color}]{rsi:.0f}[/]",
            f"[{macd_color}]{macd:+.2f}[/]",
            f"[{e52_color}]{pct_52w:+.0f}%[/]",
        ]

        if show_agents:
            for key in (
                "momentum",
                "breakout",
                "volume_surge",
                "relative_strength",
                "mean_reversion",
            ):
                s = row.get(f"score_{key}", 0.0)
                col = G if s >= 75 else (Y if s >= 55 else (DIM if s >= 35 else R))
                cells.append(f"[{col}]{s:.0f}[/]")

        cells.append(f"[bold {G}]{row['composite_score']:.0f}[/]")
        cells.append(_strategy_short(row.get("best_strategy", "")))
        table.add_row(*cells)

    console.print(table)
    console.print()


def _strategy_short(name: str) -> str:
    return {
        "momentum": "* MOMENTUM",
        "breakout": "+ BREAKOUT",
        "volume_surge": "^ VOL SURGE",
        "relative_strength": "> REL STR",
        "mean_reversion": "~ MEAN REV",
    }.get(name, name)


def print_summary_stats(
    df: pd.DataFrame, elapsed: float, total_scanned: int, cache_hits: int = 0
) -> None:
    console.print(Rule(f"[bold {G}]> SCAN SUMMARY[/]", style=DG))
    console.print()

    avg_gain = df["change_7d"].mean() if len(df) else 0
    strong = len(df[df["composite_score"] >= 75]) if len(df) else 0
    moderate = (
        len(df[(df["composite_score"] >= 55) & (df["composite_score"] < 75)]) if len(df) else 0
    )

    cols = [
        Panel(
            Align.center(Text(f"{total_scanned:,}\nscanned", style=G)),
            title=f"[bold {G}]> UNIVERSE[/]",
            border_style=DG,
            padding=(0, 1),
        ),
        Panel(
            Align.center(Text(f"{len(df)}\nleaders", style=f"bold {G}")),
            title=f"[bold {G}]> RESULTS[/]",
            border_style=DG,
            padding=(0, 1),
        ),
        Panel(
            Align.center(Text(f"+{avg_gain:.1f}%\navg 7d gain", style=G)),
            title=f"[bold {G}]> AVG GAIN[/]",
            border_style=DG,
            padding=(0, 1),
        ),
        Panel(
            Align.center(Text(f"{strong} strong\n{moderate} moderate", style=G)),
            title=f"[bold {G}]> CONVICTION[/]",
            border_style=DG,
            padding=(0, 1),
        ),
        Panel(
            Align.center(Text(f"{cache_hits:,}\ncache hits", style=CYAN)),
            title=f"[bold {G}]> CACHE[/]",
            border_style=DG,
            padding=(0, 1),
        ),
        Panel(
            Align.center(Text(f"{elapsed:.1f}s\nscan time", style=DG)),
            title=f"[bold {G}]> SPEED[/]",
            border_style=DG,
            padding=(0, 1),
        ),
    ]
    console.print(Columns(cols, equal=True, expand=True))
    console.print()


def print_strategy_guide() -> None:
    console.print(Rule(f"[bold {G}]> STRATEGY GUIDE  (5 agents)[/]", style=DG))
    console.print()

    strategies = [
        (
            "MOMENTUM",
            "*",
            [
                "Multi-timeframe gains (5d, 7d, 20d)",
                "Vol trend rising 5d AND 7d",
                "RSI healthy 55-75",
                "MACD bullish + above 50-MA",
                "",
                "Entry: pullback to 5d EMA",
                "Exit:  RSI > 80 or vol dies",
            ],
        ),
        (
            "BREAKOUT",
            "+",
            [
                "Rel Vol > 2.0x on breakout",
                "Within 5% of 52-week high",
                "RSI 58-72 (breakout zone)",
                "Gap up + MACD bullish",
                "",
                "Entry: break + close above",
                "Exit:  close back below level",
            ],
        ),
        (
            "VOLUME SURGE",
            "^",
            [
                "Vol trend 5d AND 7d rising",
                "Rel Vol > 1.5x avg",
                "Dollar volume > $10M (liquid)",
                "Price beginning to follow",
                "",
                "Entry: surge day or next open",
                "Exit:  vol drops below avg",
            ],
        ),
        (
            "REL STRENGTH",
            ">",
            [
                "Outperform VOO + VXF + QQQ",
                "Sustained 20d outperformance",
                "Bonus: up in down markets",
                "True leadership signal",
                "",
                "Entry: RS leaders hold long",
                "Exit:  when RS rolls over",
            ],
        ),
        (
            "MEAN REVERT",
            "~",
            [
                "50-MA > 200-MA (LT uptrend)",
                "Pulled back to 20-MA",
                "RSI cooled to 35-50",
                "Price stabilizing 5d",
                "",
                "Entry: at/near 20-MA",
                "Exit:  back to recent high",
            ],
        ),
    ]

    panels = []
    for name, icon, lines in strategies:
        content = Text()
        for line in lines:
            if line == "":
                content.append("\n")
            elif line.startswith("Entry:") or line.startswith("Exit:"):
                label, rest = line.split(":", 1)
                content.append(f"{label}:", style=f"bold {Y}")
                content.append(f"{rest}\n", style=W)
            else:
                content.append(f"* {line}\n", style=G)
        panels.append(
            Panel(
                content,
                title=f"[bold {G}]{icon} {name}[/]",
                border_style=DG,
                padding=(0, 1),
            )
        )
    console.print(Columns(panels, equal=True, expand=True))
    console.print()


def print_top_reasons(df: pd.DataFrame, n: int = 5) -> None:
    if df.empty:
        return
    console.print(Rule(f"[bold {G}]> TOP {min(n, len(df))} — REASONING[/]", style=DG))
    console.print()
    for i, row in df.head(n).iterrows():
        line = Text()
        line.append(f"  {i + 1:>2}. ", style=DIM)
        line.append(f"{row['ticker']:<6}", style=f"bold {G}")
        line.append(f" {row['composite_score']:>5.1f}  ", style=f"bold {G}")
        line.append(f"{_strategy_short(row.get('best_strategy', ''))}  ", style=CYAN)
        line.append(f"{row.get('top_reasons', '')}", style=W)
        console.print(line)
        if row.get("flags"):
            console.print(f"        [{Y}]flags: {row['flags']}[/]")
    console.print()


def print_save_summary(paths: List[str]) -> None:
    if not paths:
        return
    console.print(Rule(f"[bold {G}]> SAVED OUTPUTS[/]", style=DG))
    for p in paths:
        console.print(f"  [{G}]>[/] [{W}]{p}[/]")
    console.print()
