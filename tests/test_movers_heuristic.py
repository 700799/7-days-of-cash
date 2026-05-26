"""Tests for pure helper functions in api/movers.py.

No database, no network, no env-var setup needed — these functions are
deterministic arithmetic/string utilities.
"""
import pytest

from api.movers import _arrow_for, _format_change, _pct_change


# ---------------------------------------------------------------------------
# _arrow_for
# ---------------------------------------------------------------------------


def test_arrow_for_positive_large():
    assert _arrow_for(5.0) == "▲"


def test_arrow_for_positive_at_boundary():
    """Values strictly greater than 0.5 get the up arrow."""
    assert _arrow_for(0.51) == "▲"


def test_arrow_for_negative_large():
    assert _arrow_for(-5.0) == "▼"


def test_arrow_for_negative_at_boundary():
    """Values strictly less than -0.5 get the down arrow."""
    assert _arrow_for(-0.51) == "▼"


def test_arrow_for_small_positive():
    """0.3 is within the flat band (< 0.5 threshold)."""
    assert _arrow_for(0.3) == "▬"


def test_arrow_for_zero():
    assert _arrow_for(0.0) == "▬"


def test_arrow_for_exactly_positive_threshold():
    """0.5 is NOT strictly greater than 0.5, so it stays flat."""
    assert _arrow_for(0.5) == "▬"


def test_arrow_for_exactly_negative_threshold():
    """-0.5 is NOT strictly less than -0.5, so it stays flat."""
    assert _arrow_for(-0.5) == "▬"


# ---------------------------------------------------------------------------
# _format_change
# ---------------------------------------------------------------------------


def test_format_change_positive():
    assert _format_change(12.3) == "+12.3%"


def test_format_change_negative():
    assert _format_change(-5.7) == "-5.7%"


def test_format_change_zero():
    assert _format_change(0.0) == "+0.0%"


def test_format_change_one_decimal_place():
    """Output is always formatted to exactly one decimal place."""
    assert _format_change(1.0) == "+1.0%"
    assert _format_change(-1.0) == "-1.0%"


def test_format_change_rounds_to_one_decimal():
    """Python f-string :.1f rounds, not truncates."""
    assert _format_change(2.25) == "+2.2%"   # rounds down (banker's rounding)
    assert _format_change(2.35) == "+2.4%"   # rounds up


# ---------------------------------------------------------------------------
# _pct_change
# ---------------------------------------------------------------------------


def test_pct_change_gain():
    assert _pct_change(110.0, 100.0) == pytest.approx(10.0)


def test_pct_change_loss():
    assert _pct_change(0.0, 100.0) == pytest.approx(-100.0)


def test_pct_change_no_change():
    assert _pct_change(100.0, 100.0) == pytest.approx(0.0)


def test_pct_change_division_by_zero_guard():
    """When prior is 0.0 (or any non-positive value), returns 0.0 without raising."""
    assert _pct_change(100.0, 0.0) == 0.0


def test_pct_change_prior_negative_guard():
    """Negative prior is treated the same as zero — returns 0.0."""
    assert _pct_change(100.0, -50.0) == 0.0


def test_pct_change_large_gain():
    assert _pct_change(200.0, 100.0) == pytest.approx(100.0)


def test_pct_change_fractional():
    assert _pct_change(105.5, 100.0) == pytest.approx(5.5)


