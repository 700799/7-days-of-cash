"""Multi-format exporter: CSV, JSON, Excel, Parquet, HTML."""
from __future__ import annotations

import os
from datetime import datetime
from typing import List

import pandas as pd


def save_outputs(
    df: pd.DataFrame,
    output_dir: str = "outputs",
    formats: List[str] = None,
    prefix: str = "screener",
) -> List[str]:
    formats = formats or ["csv"]
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = []

    for fmt in formats:
        fmt = fmt.lower().strip()
        path = os.path.join(output_dir, f"{prefix}_{ts}.{_ext(fmt)}")
        try:
            if fmt == "csv":
                df.to_csv(path, index=False)
            elif fmt == "json":
                df.to_json(path, orient="records", indent=2)
            elif fmt in ("xlsx", "excel"):
                df.to_excel(path, index=False, sheet_name="screener")
            elif fmt == "parquet":
                df.to_parquet(path, index=False)
            elif fmt == "html":
                _save_html(df, path)
            elif fmt == "markdown" or fmt == "md":
                df.to_markdown(path, index=False)
            else:
                continue
            paths.append(path)
        except Exception:
            continue

    # Also write a "latest" symlink-style file for easy access
    latest_csv = os.path.join(output_dir, f"{prefix}_latest.csv")
    try:
        df.to_csv(latest_csv, index=False)
        if latest_csv not in paths:
            paths.append(latest_csv)
    except Exception:
        pass

    return paths


def _ext(fmt: str) -> str:
    return {
        "excel": "xlsx",
        "markdown": "md",
    }.get(fmt, fmt)


def _save_html(df: pd.DataFrame, path: str) -> None:
    style = """
    <style>
      body{background:#000;color:#0f0;font-family:'JetBrains Mono',Consolas,monospace;padding:1rem;}
      h1{color:#0f0;border-bottom:1px solid #0a0;}
      table{border-collapse:collapse;width:100%;margin-top:1rem;}
      th,td{border:1px solid #0a0;padding:.4rem .8rem;text-align:left;}
      th{background:#020;color:#0f0;}
      tr:nth-child(even){background:#010;}
      .meta{color:#0a0;font-size:.9rem;}
    </style>
    """
    meta = f"<p class='meta'>Generated {datetime.now().isoformat(timespec='seconds')} — {len(df)} rows</p>"
    html = df.to_html(index=False, escape=False, classes="screener")
    full = f"<!doctype html><html><head><meta charset='utf-8'>{style}<title>Best7Days</title></head><body><h1>&gt; BEST 7 DAYS RESULTS</h1>{meta}{html}</body></html>"
    with open(path, "w") as f:
        f.write(full)
