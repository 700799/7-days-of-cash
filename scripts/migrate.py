#!/usr/bin/env python3
"""One-shot Postgres schema migration. Run after first deploy and after schema bumps.

Usage:
    DATABASE_URL=postgresql://... python scripts/migrate.py
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    if not os.environ.get("DATABASE_URL"):
        print("ERROR: DATABASE_URL is not set", file=sys.stderr)
        return 2
    from api.db import init_schema

    init_schema()
    print("Schema initialized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
