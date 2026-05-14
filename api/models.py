"""Pydantic schemas exposed by the API."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


class User(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None


class TickerCreate(BaseModel):
    symbol: str
    note: Optional[str] = None

    @field_validator("symbol")
    @classmethod
    def _normalize_symbol(cls, v: str) -> str:
        v = v.strip().upper()
        if not SYMBOL_RE.match(v):
            raise ValueError("symbol must match ^[A-Z][A-Z0-9.\\-]{0,9}$")
        return v


class TickerUpdate(BaseModel):
    note: Optional[str] = None


class Ticker(BaseModel):
    symbol: str
    note: Optional[str] = None
    added_at: Optional[datetime] = None


class NewsItem(BaseModel):
    title: str
    publisher: Optional[str] = None
    link: Optional[str] = None
    published_at: Optional[datetime] = None
    thumbnail: Optional[str] = None


class ScreenerRequest(BaseModel):
    tickers: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    agents: Optional[List[str]] = None


class ScreenerResultRow(BaseModel):
    model_config = ConfigDict(extra="allow")
    ticker: str
    price: Optional[float] = None
    change_7d: Optional[float] = None
    composite_score: Optional[float] = None
    best_strategy: Optional[str] = None
    top_reasons: Optional[str] = None


class ScreenerResponse(BaseModel):
    regime: Dict[str, Any] = Field(default_factory=dict)
    benchmarks: Dict[str, Any] = Field(default_factory=dict)
    results: List[Dict[str, Any]] = Field(default_factory=list)
    ran_at: datetime
