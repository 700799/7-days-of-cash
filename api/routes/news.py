"""News routes — wraps yfinance news with a 15-minute cache."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter

from ..models import NewsItem
from ..news_provider import get_market_news, get_ticker_news

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/ticker/{symbol}", response_model=List[NewsItem])
def ticker_news(symbol: str) -> List[NewsItem]:
    return [NewsItem(**item) for item in get_ticker_news(symbol)]


@router.get("/market", response_model=List[NewsItem])
def market_news() -> List[NewsItem]:
    return [NewsItem(**item) for item in get_market_news()]
