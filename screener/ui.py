import os
import json
from datetime import datetime
from typing import Dict, Any, List, Set, Optional

import pandas as pd
import questionary
from questionary import Style as QStyle
from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.style import Style
from rich.rule import Rule

console = Console()

# ── colour tokens ────────────────────────────────────────────────────────────
G  = "bright_green"       # primary green
DG = "green"              # dim green
Y  = "yellow"             # highlights / warnings
R  = "red"                # negative / bad
W  = "white"              # neutral text
DIM = "dim bright_green"  # secondary text

PILL_STYLE = QStyle([
    ("qmark",        "fg:ansigreen bold"),
    ("question",     "fg:ansigreen bold"),
    ("pointer",      "fg:ansigreen bold"),
    ("highlighted",  "fg:ansiblack bg:ansigreen bold"),
    ("selected",     "fg:ansigreen"),
    ("separator",    "fg:ansigreen"),
    ("instruction",  "fg:ansidarkgray"),
    ("text",         "fg:ansigreen"),
    ("disabled",     "fg:ansidarkgray italic"),
])

FILTER_CHOICES = [
    ("[ PRICE ≥ $2 ]",           "min_price"),
    ("[ GAIN ≥ +8% (7d) ]",      "min_gain_7d"),
    ("[ AVG VOL ≥ 500K ]",       "min_avg_volume"),
    ("[ RSI ≤ 80 ]",             "max_rsi"),
    ("[ MARKET CAP FILTER ]",    "market_cap"),
    ("[ EXCLUDE VOLATILE ]",     "exclude_volatility"),
]

BANNER = r"""
  ██████╗ ███████╗███████╗████████╗     ███████╗    ██████╗  █████╗ ██╗   ██╗███████╗
  ██╔══██╗██╔════╝██╔════╝╚══██╔══╝     ╚════██║   ██╔══██╗██╔══██╗╚██╗ ██╔╝██╔════╝
  ██████╔╝█████╗  ███████╗   ██║            ██╔╝   ██║  ██║███████║ ╚████╔╝ ███████╗
  ██╔══██╗██╔══╝  ╚════██║   ██║           ██╔╝    ██║  ██║██╔══██║  ╚██╔╝  ╚════██║
  ██████╔╝███████╗███████║   ██║           ██║     ██████╔╝██║  ██║   ██║   ███████║
  ╚═════╝ ╚══════╝╚══════╝   ╚═╝           ╚═╝     ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝
"""

TAGLINE    = "7-day uptrend screener.  Volume confirmed.  Benchmark compared."
SUBTAGLINE = "One mission: find the leaders."


def _g(text: str, bold: bool = False) -> Text:
    t = Text(text, style=Style(color=G, bold=bold))
    return t


def print_banner() -> None:
    console.print()
    banner_text = Text(BANNER, style=Style(color=G, bold=True))
    console.print(Align.center(banner_text))
    console.print(Align.center(Text(f'"{TAGLINE}"', style=Style(color=DG, italic=True))))
    console.print(Align.center(Text(SUBTAGLINE, style=Style(color=DG))))
    console.print()

    # Stats row  (gstack "by the numbers" style)
    stats = [
        Panel(
            Align.center(Text("S&P 500\nNASDAQ\nRUSSELL 2000", style=G)),
            title="[bold green]> UNIVERSES[/]",
            border_style=DG,
            padding=(0, 2),
        ),
        Panel(
            Align.center(Text("7\ntrading days", style=f"bold {G}")),
            title="[bold green]> LOOKBACK[/]",
            border_style=DG,
            padding=(0, 2),
        ),
        Panel(
            Align.center(Text("VOO  ·  VXF\nVTIAX", style=G)),
            title="[bold green]> BENCHMARKS[/]",
            border_style=DG,
            padding=(0, 2),
        ),
        Panel(
            Align.center(Text("RSI · Vol Trend\nRel Vol · Avg Vol", style=G)),
            title="[bold green]> METRICS[/]",
            border_style=DG,
            padding=(0, 2),
        ),
    ]
    console.print(Columns(stats, equal=True, expand=True))
    console.print()


def run_pill_toggles(defaults: Optional[Set[str]] = None) -> Set[str]:
    all_keys = [v for _, v in FILTER_CHOICES]
    if defaults is None:
        defaults = set(all_keys)

    default_labels = [
        label for label, key in FILTER_CHOICES if key in defaults
    ]

    console.print(f"[bold {G}]> ACTIVE FILTERS[/]  [dim green](space to toggle, enter to confirm)[/]")
    console.print()

    selected = questionary.checkbox(
        "Select filters to apply:",
        choices=[
            questionary.Choice(label, value=key, checked=(key in defaults))
            for label, key in FILTER_CHOICES
        ],
        style=PILL_STYLE,
    ).ask()

    if selected is None:
        selected = all_keys

    console.print()
    active = set(selected)
    active_labels = [label for label, key in FILTER_CHOICES if key in active]
    console.print(
        f"[bold {G}]  FILTERS LOCKED:[/] " +
        "  ".join(f"[{G}]{l}[/{G}]" for l in active_labels)
    )
    console.print()
    return active


def print_market_summary(benchmarks: Dict[str, Dict[str, Any]]) -> None:
    console.print(Rule(f"[bold {G}]> BENCHMARK COMPARISON  (7-day)[/]", style=DG))
    console.print()

    panels = []
    for ticker, info in benchmarks.items():
        pct = info.get("change_7d", 0.0)
        price = info.get("price", 0.0)
        color = G if pct >= 0 else R
        arrow = "▲" if pct >= 0 else "▼"
        sign  = "+" if pct >= 0 else ""

        content = Text(justify="center")
        content.append(f"${price:.2f}\n", style=W)
        content.append(f"{arrow} {sign}{pct:.2f}%\n", style=f"bold {color}")
        content.append(info.get("description", ""), style=DIM)

        panels.append(Panel(
            Align.center(content),
            title=f"[bold {G}]{ticker}[/]  [dim green]{info.get('name', '')}[/]",
            border_style=color,
            padding=(0, 3),
        ))

    console.print(Columns(panels, equal=True, expand=True))
    console.print()


def print_results_table(df: pd.DataFrame, benchmarks: Dict[str, Dict[str, Any]]) -> None:
    voo_7d = benchmarks.get("VOO", {}).get("change_7d", 0.0)
    vxf_7d = benchmarks.get("VXF", {}).get("change_7d", 0.0)

    console.print(Rule(f"[bold {G}]> TOP UPTREND LEADERS  (7-day, volume confirmed)[/]", style=DG))
    console.print()

    table = Table(
        box=box.SQUARE,
        border_style=DG,
        header_style=f"bold {G}",
        show_lines=False,
        expand=True,
    )

    table.add_column("#",          style=DIM,         width=4,  justify="right")
    table.add_column("TICKER",     style=f"bold {G}", width=8)
    table.add_column("PRICE",      style=W,           width=9,  justify="right")
    table.add_column("7d %",       style=W,           width=9,  justify="right")
    table.add_column("vs VOO",     style=W,           width=9,  justify="right")
    table.add_column("vs VXF",     style=W,           width=9,  justify="right")
    table.add_column("AVG VOL",    style=DG,          width=11, justify="right")
    table.add_column("REL VOL",    style=DG,          width=9,  justify="right")
    table.add_column("VOL↑5d",     style=DG,          width=9,  justify="center")
    table.add_column("VOL↑7d",     style=DG,          width=9,  justify="center")
    table.add_column("RSI",        style=W,           width=7,  justify="right")
    table.add_column("SIGNAL",     style=W,           width=14)

    for i, row in df.iterrows():
        pct      = row["change_7d"]
        rsi      = row["rsi_14"]
        rel_vol  = row["rel_vol"]
        v5       = row["vol_trend_5d"]
        v7       = row["vol_trend_7d"]

        pct_color  = G if pct >= 0 else R
        rsi_color  = R if rsi > 75 else (Y if rsi > 65 else G)
        rvol_color = G if rel_vol >= 1.5 else (Y if rel_vol >= 1.0 else DIM)

        vs_voo = pct - voo_7d
        vs_vxf = pct - vxf_7d
        vs_voo_str = f"[{'bright_green' if vs_voo >= 0 else 'red'}]{'+' if vs_voo >= 0 else ''}{vs_voo:.1f}%[/]"
        vs_vxf_str = f"[{'bright_green' if vs_vxf >= 0 else 'red'}]{'+' if vs_vxf >= 0 else ''}{vs_vxf:.1f}%[/]"

        v5_str = f"[{G}]▲[/]" if v5 > 0 else f"[{R}]▼[/]"
        v7_str = f"[{G}]▲[/]" if v7 > 0 else f"[{R}]▼[/]"

        signal = _signal_label(pct, rsi, rel_vol, v5, v7)

        table.add_row(
            str(i + 1),
            row["ticker"],
            f"${row['price']:.2f}",
            f"[{pct_color}]+{pct:.1f}%[/]" if pct >= 0 else f"[{pct_color}]{pct:.1f}%[/]",
            vs_voo_str,
            vs_vxf_str,
            _fmt_vol(row["avg_vol_20d"]),
            f"[{rvol_color}]{rel_vol:.2f}x[/]",
            v5_str,
            v7_str,
            f"[{rsi_color}]{rsi:.0f}[/]",
            signal,
        )

    console.print(table)
    console.print()


def _signal_label(pct: float, rsi: float, rel_vol: float, v5: float, v7: float) -> str:
    if rsi > 75 and pct > 15:
        return f"[{Y}]⚡ OVEREXTENDED[/]"
    if rel_vol >= 2.0 and v5 > 0 and v7 > 0:
        return f"[bold {G}]★ VOL SURGE[/]"
    if pct >= 12 and v5 > 0:
        return f"[bold {G}]▲ MOMENTUM[/]"
    if rel_vol >= 1.5 and rsi < 70:
        return f"[{G}]◆ BREAKOUT[/]"
    if pct > 8:
        return f"[{DG}]● TRENDING[/]"
    return f"[{DIM}]· WATCH[/]"


def _fmt_vol(v: float) -> str:
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v/1_000:.0f}K"
    return str(int(v))


def print_strategy_guide() -> None:
    console.print(Rule(f"[bold {G}]> STRATEGY GUIDE[/]", style=DG))
    console.print()

    strategies = [
        (
            "MOMENTUM",
            "★",
            [
                "7d% gain is strong",
                "Volume rising (both trends ▲)",
                "RSI 55–75  =  healthy trend",
                "Institutions are accumulating",
                "",
                "Entry: pullback to 5d EMA",
                "Exit:  RSI > 80 or vol collapses",
            ],
        ),
        (
            "BREAKOUT",
            "◆",
            [
                "Rel Vol > 2.0x on breakout day",
                "RSI crossing above 60",
                "Price near 52-week high",
                "Low float = explosive moves",
                "",
                "Entry: break + close above level",
                "Exit:  close back below breakout",
            ],
        ),
        (
            "VOLUME SURGE",
            "▲",
            [
                "Vol Trend 5d AND 7d both ▲",
                "Rel Vol > 1.5x avg",
                "Smart money moving in early",
                "Price often lags volume by 1-3d",
                "",
                "Entry: on surge day or next open",
                "Exit:  vol drops below avg",
            ],
        ),
        (
            "RELATIVE STRENGTH",
            "►",
            [
                "Stock 7d% >> VOO + VXF 7d%",
                "vs VOO column shows alpha",
                "True leaders outperform in",
                "both up AND down markets",
                "",
                "Entry: RS leaders hold longer",
                "Exit:  when RS line rolls over",
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
                content.append(f"• {line}\n", style=G)

        panels.append(Panel(
            content,
            title=f"[bold {G}]{icon} {name}[/]",
            border_style=DG,
            padding=(0, 1),
        ))

    console.print(Columns(panels, equal=True, expand=True))
    console.print()


def print_summary_stats(df: pd.DataFrame, elapsed: float, total_scanned: int) -> None:
    console.print(Rule(f"[bold {G}]> SCAN SUMMARY[/]", style=DG))
    console.print()

    avg_gain  = df["change_7d"].mean() if len(df) else 0
    avg_rsi   = df["rsi_14"].mean()    if len(df) else 0
    surge     = len(df[df["rel_vol"] >= 2.0]) if len(df) else 0
    momentum  = len(df[df["change_7d"] >= 12]) if len(df) else 0

    cols = [
        Panel(Align.center(Text(f"{total_scanned:,}\ntickers scanned", style=G)),
              title=f"[bold {G}]> UNIVERSE[/]", border_style=DG, padding=(0,2)),
        Panel(Align.center(Text(f"{len(df)}\nleaders found", style=f"bold {G}")),
              title=f"[bold {G}]> RESULTS[/]", border_style=DG, padding=(0,2)),
        Panel(Align.center(Text(f"+{avg_gain:.1f}%\navg 7-day gain", style=G)),
              title=f"[bold {G}]> AVG GAIN[/]", border_style=DG, padding=(0,2)),
        Panel(Align.center(Text(f"{surge} surge  |  {momentum} momentum\nby signal type", style=G)),
              title=f"[bold {G}]> SIGNALS[/]", border_style=DG, padding=(0,2)),
        Panel(Align.center(Text(f"{elapsed:.1f}s\nscan time", style=DG)),
              title=f"[bold {G}]> SPEED[/]", border_style=DG, padding=(0,2)),
    ]
    console.print(Columns(cols, equal=True, expand=True))
    console.print()


def save_outputs(
    df: pd.DataFrame,
    output_dir: str = "outputs",
    save_json: bool = False,
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_path = os.path.join(output_dir, f"screener_{ts}.csv")
    df.to_csv(csv_path, index=False)

    if save_json:
        json_path = os.path.join(output_dir, f"screener_{ts}.json")
        df.to_json(json_path, orient="records", indent=2)
        console.print(f"[{DG}]  Saved JSON → {json_path}[/]")

    console.print(f"[{G}]> SAVED → {csv_path}[/]")
    return csv_path
