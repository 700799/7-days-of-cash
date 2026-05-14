"""Unit tests for the filter pipeline."""
from screener.filters import apply_filters


def _rec(ticker, price=10, change_7d=10, vol=1_000_000, rsi=60, dvol=20_000_000, e52=-5):
    return {
        "ticker": ticker, "price": price, "change_7d": change_7d,
        "avg_vol_20d": vol, "rsi_14": rsi, "dollar_vol_20d": dvol,
        "pct_from_52w_high": e52, "avg_range_pct": 5.0,
    }


def test_empty_records_returns_empty_df():
    assert apply_filters([], {}).empty


def test_min_price_filter():
    recs = [_rec("A", price=1.5), _rec("B", price=10)]
    out = apply_filters(recs, {"min_price": 2.0, "active_filters": {"min_price"}})
    assert out["ticker"].tolist() == ["B"]


def test_min_gain_filter():
    recs = [_rec("A", change_7d=3), _rec("B", change_7d=15)]
    out = apply_filters(recs, {"min_gain_7d": 8.0, "active_filters": {"min_gain_7d"}})
    assert out["ticker"].tolist() == ["B"]


def test_max_rsi_filter():
    recs = [_rec("A", rsi=85), _rec("B", rsi=60)]
    out = apply_filters(recs, {"max_rsi": 80, "active_filters": {"max_rsi"}})
    assert out["ticker"].tolist() == ["B"]


def test_results_sorted_by_score_when_present():
    recs = [
        {**_rec("A", change_7d=10), "composite_score": 50},
        {**_rec("B", change_7d=10), "composite_score": 90},
    ]
    out = apply_filters(recs, {"active_filters": set()})
    assert out["ticker"].tolist()[0] == "B"


def test_top_n_caps_results():
    recs = [_rec(f"T{i}", change_7d=10 + i) for i in range(50)]
    out = apply_filters(recs, {"top_n": 10, "active_filters": set()})
    assert len(out) == 10


def test_min_dollar_vol_filter():
    recs = [_rec("A", dvol=1_000_000), _rec("B", dvol=20_000_000)]
    out = apply_filters(recs, {"min_dollar_vol": 5_000_000, "active_filters": {"min_dollar_vol"}})
    assert out["ticker"].tolist() == ["B"]
