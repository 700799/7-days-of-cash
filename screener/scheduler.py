"""Watch mode — re-run the screener on a fixed interval, market-hour aware."""
from __future__ import annotations

import datetime as dt
import time
from typing import Callable, Optional

from .logger import get_logger

log = get_logger("best7days.scheduler")

# US market hours (Eastern). Naive comparison; daylight saving handled by user's local TZ
# only if they pass tz_offset_hours. Default assumes the host runs on ET.
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MIN = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MIN = 0


def watch(
    task: Callable[[], None],
    interval_minutes: int = 15,
    market_hours_only: bool = False,
    max_iterations: Optional[int] = None,
) -> None:
    """Run `task` every `interval_minutes` until interrupted.

    Args:
        task: zero-arg callable that runs one screening pass.
        interval_minutes: gap between runs.
        market_hours_only: if True, only run during weekday market hours.
        max_iterations: stop after N iterations (None for infinite).
    """
    iteration = 0
    log.info("watch started: interval=%dm market_hours_only=%s", interval_minutes, market_hours_only)
    try:
        while True:
            iteration += 1
            now = dt.datetime.now()
            if market_hours_only and not _is_market_open(now):
                next_open = _next_market_open(now)
                wait_sec = max(60, (next_open - now).total_seconds())
                log.info("market closed; sleeping until %s (%.0f min)", next_open.isoformat(timespec="minutes"), wait_sec / 60)
                time.sleep(min(wait_sec, 3600))
                continue

            log.info("iteration #%d starting at %s", iteration, now.isoformat(timespec="seconds"))
            try:
                task()
            except Exception as e:
                log.exception("task failed: %s", e)

            if max_iterations and iteration >= max_iterations:
                log.info("max iterations reached (%d), stopping", max_iterations)
                break

            log.info("sleeping %d minutes until next run", interval_minutes)
            time.sleep(interval_minutes * 60)
    except KeyboardInterrupt:
        log.info("watch interrupted by user")


def _is_market_open(now: dt.datetime) -> bool:
    if now.weekday() >= 5:
        return False
    open_t = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MIN, second=0, microsecond=0)
    close_t = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MIN, second=0, microsecond=0)
    return open_t <= now <= close_t


def _next_market_open(now: dt.datetime) -> dt.datetime:
    target = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MIN, second=0, microsecond=0)
    if now >= target:
        target += dt.timedelta(days=1)
    while target.weekday() >= 5:
        target += dt.timedelta(days=1)
    return target


def generate_cron(interval_minutes: int, command: str, market_hours_only: bool = True) -> str:
    """Generate a crontab entry the user can paste into their crontab."""
    if interval_minutes < 60:
        minute = f"*/{interval_minutes}"
        hour = "9-16" if market_hours_only else "*"
    else:
        hours = interval_minutes // 60
        minute = "30"
        hour = f"9-16/{hours}" if market_hours_only else f"*/{hours}"

    day = "1-5" if market_hours_only else "*"
    return f"{minute} {hour} * * {day} {command}"
