#!/usr/bin/env python3
"""Regenerate worker/src/engine/universe.ts from the public S&P 500 dataset.

Pulls constituents from the datasets/s-and-p-500-companies GitHub repo (more
Worker-friendly than scraping Wikipedia) and rewrites the SP500_TICKERS block.
The EXTENDED_TICKERS list is preserved as-is.

Usage:
    python scripts/gen_universe.py
"""
from __future__ import annotations

import csv
import io
import os
import re
import sys
import urllib.request

CSV_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
TARGET = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "worker", "src", "engine", "universe.ts",
)


def fmt(symbols: list[str]) -> str:
    out, line = [], "  "
    for s in symbols:
        tok = f'"{s}", '
        if len(line) + len(tok) > 98:
            out.append(line.rstrip())
            line = "  "
        line += tok
    if line.strip():
        out.append(line.rstrip(", ").rstrip() + ",")
    return "\n".join(out)


def main() -> int:
    req = urllib.request.Request(CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        rows = list(csv.DictReader(io.TextIOWrapper(resp, encoding="utf-8")))
    sp500 = sorted({r["Symbol"].replace(".", "-") for r in rows})
    if len(sp500) < 400:
        print(f"ERROR: only {len(sp500)} symbols fetched — refusing to overwrite", file=sys.stderr)
        return 1

    with open(TARGET) as f:
        src = f.read()
    new_block = f"export const SP500_TICKERS: readonly string[] = [\n{fmt(sp500)}\n];"
    src = re.sub(
        r"export const SP500_TICKERS: readonly string\[\] = \[.*?\];",
        new_block,
        src,
        flags=re.DOTALL,
    )
    with open(TARGET, "w") as f:
        f.write(src)
    print(f"Updated {TARGET} with {len(sp500)} S&P 500 symbols")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
