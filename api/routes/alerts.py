"""Price alert CRUD — Pro-only feature.

Users can set up to 10 alerts per symbol/condition/target combination.
Alerts are checked on each cron refresh and trigger an email if price
crosses the target. Once triggered, the alert stays in the list (marked
triggered=TRUE) so users can see their history.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from ..auth import get_current_user
from ..db import get_conn
from ..models import User
from ..tier import PRO_ALERT_LIMIT

router = APIRouter(prefix="/api/alerts", tags=["alerts"])
log = logging.getLogger(__name__)


class AlertCreate(BaseModel):
    symbol: str
    condition: str  # "above" | "below"
    target: float

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, v: str) -> str:
        if v not in ("above", "below"):
            raise ValueError("condition must be 'above' or 'below'")
        return v

    @field_validator("target")
    @classmethod
    def validate_target(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("target price must be positive")
        return round(v, 4)


def _list_alerts_for_user(user_id: str) -> List[Dict[str, Any]]:
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """SELECT id, symbol, condition, target, triggered, created_at
                   FROM price_alerts
                   WHERE user_id = %s
                   ORDER BY created_at DESC""",
                [user_id],
            )
            rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "symbol": r[1],
            "condition": r[2],
            "target": float(r[3]),
            "triggered": r[4],
            "created_at": r[5].isoformat() if r[5] else None,
        }
        for r in rows
    ]


@router.get("")
def list_alerts(user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """Return all price alerts for the authenticated Pro user."""
    return _list_alerts_for_user(user.id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_alert(
    payload: AlertCreate,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a price alert. Max 10 active alerts per Pro user."""
    existing = _list_alerts_for_user(user.id)
    active_count = sum(1 for a in existing if not a["triggered"])
    if active_count >= PRO_ALERT_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Alert limit reached ({PRO_ALERT_LIMIT} active alerts max). Delete one to add another.",
        )

    with get_conn() as c:
        with c.cursor() as cur:
            try:
                cur.execute(
                    """INSERT INTO price_alerts (user_id, symbol, condition, target)
                       VALUES (%s, %s, %s, %s)
                       RETURNING id, symbol, condition, target, triggered, created_at""",
                    [user.id, payload.symbol, payload.condition, payload.target],
                )
                row = cur.fetchone()
            except Exception as e:
                if "unique" in str(e).lower():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Identical alert already exists.",
                    )
                raise

    return {
        "id": row[0],
        "symbol": row[1],
        "condition": row[2],
        "target": float(row[3]),
        "triggered": row[4],
        "created_at": row[5].isoformat() if row[5] else None,
    }


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(alert_id: int, user: User = Depends(get_current_user)) -> None:
    """Delete a price alert (must belong to authenticated user)."""
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                "SELECT id FROM price_alerts WHERE id = %s AND user_id = %s",
                [alert_id, user.id],
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Alert not found")
            cur.execute(
                "DELETE FROM price_alerts WHERE id = %s AND user_id = %s",
                [alert_id, user.id],
            )
    return None
