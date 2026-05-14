"""User preferences — email digest opt-in (none / daily / weekly)."""
from __future__ import annotations

import re
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from ..auth import get_current_user
from ..db import get_conn
from ..models import User

router = APIRouter(prefix="/api/preferences", tags=["preferences"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DigestFrequency = Literal["none", "daily", "weekly"]


class Preferences(BaseModel):
    digest_frequency: DigestFrequency = "none"
    digest_email: Optional[str] = None
    last_sent_at: Optional[str] = None


class PreferencesUpdate(BaseModel):
    digest_frequency: DigestFrequency
    digest_email: Optional[str] = Field(default=None, max_length=320)

    @field_validator("digest_email")
    @classmethod
    def _check_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not EMAIL_RE.match(v.strip()):
            raise ValueError("invalid email")
        return v.strip().lower()


@router.get("", response_model=Preferences)
def get_preferences(user: User = Depends(get_current_user)) -> Preferences:
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                "SELECT digest_frequency, digest_email, last_sent_at "
                "FROM user_preferences WHERE user_id=%s",
                [user.id],
            )
            row = cur.fetchone()
    if row is None:
        return Preferences()
    return Preferences(
        digest_frequency=row[0],
        digest_email=row[1],
        last_sent_at=row[2].isoformat() if row[2] else None,
    )


@router.patch("", response_model=Preferences)
def update_preferences(
    payload: PreferencesUpdate,
    user: User = Depends(get_current_user),
) -> Preferences:
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """INSERT INTO user_preferences(user_id, digest_frequency, digest_email, updated_at)
                   VALUES (%s, %s, %s, now())
                   ON CONFLICT (user_id) DO UPDATE
                     SET digest_frequency = EXCLUDED.digest_frequency,
                         digest_email     = EXCLUDED.digest_email,
                         updated_at       = now()
                   RETURNING digest_frequency, digest_email, last_sent_at""",
                [user.id, payload.digest_frequency, payload.digest_email],
            )
            row = cur.fetchone()
    return Preferences(
        digest_frequency=row[0],
        digest_email=row[1],
        last_sent_at=row[2].isoformat() if row[2] else None,
    )
