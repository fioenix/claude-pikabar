"""Tests for pikabar.hp_bar — HP/PP bars and badges."""

from pikabar.hp_bar import (
    hp_color, render_hp_bar, render_pp_bar, get_badge,
    HP_GREEN, HP_YELLOW, HP_RED,
)
from pikabar.palette import visible_len


# --- hp_color ---

def test_hp_color_green_above_50():
    assert hp_color(75) == HP_GREEN
    assert hp_color(51) == HP_GREEN


def test_hp_color_yellow_20_to_50():
    assert hp_color(50) == HP_YELLOW
    assert hp_color(21) == HP_YELLOW


def test_hp_color_red_below_20():
    assert hp_color(20) == HP_RED
    assert hp_color(1) == HP_RED


def test_hp_color_zero():
    assert hp_color(0) == HP_RED


# --- render_hp_bar ---

def test_hp_bar_returns_string():
    result = render_hp_bar(50)
    assert isinstance(result, str)
    assert len(result) > 0


def test_hp_bar_none_shows_unknown():
    result = render_hp_bar(None)
    assert "?" in visible_len.__module__ or "?" in result  # contains ? chars
    assert "---" in result


def test_hp_bar_100_all_filled():
    result = render_hp_bar(100)
    # Should contain filled blocks but no empty blocks
    assert "\u2588" in result  # █
    assert "\u2591" not in result  # no ░


def test_hp_bar_0_all_empty():
    result = render_hp_bar(0)
    assert "\u2591" in result  # ░


# --- render_pp_bar ---

def test_pp_bar_returns_string():
    result = render_pp_bar(80)
    assert isinstance(result, str)
    assert "\u2588" in result  # █


def test_pp_bar_none_shows_unknown():
    result = render_pp_bar(None)
    assert "?" in result


# --- get_badge ---

def test_badge_empty_when_healthy():
    assert get_badge(80) == ""
    assert get_badge(60) == ""


def test_badge_brn_at_35():
    badge = get_badge(35)
    assert badge is not None
    assert "BRN" in badge


def test_badge_psn_at_15():
    badge = get_badge(15)
    assert badge is not None
    assert "PSN" in badge


def test_badge_par_when_rate_limited():
    badge = get_badge(0, is_rate_limited=True)
    assert badge is not None
    assert "PAR" in badge
