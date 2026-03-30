"""Tests for Track B features: greeting, confetti, shiny, critical HP, streak."""

import random
from datetime import date
from unittest.mock import patch

from pikabar.flavor import (
    get_session_greeting, get_critical_flavor,
    SESSION_GREETINGS, SESSION_DAY_GREETINGS, CRITICAL_FLAVOR,
)
from pikabar.delta import check_shiny, compute_streak, SHINY_CHANCE
from pikabar.info_panel import format_model, decorate_committed, _info_lines
from pikabar.sprites import (
    SHINY_IDLE_FRAMES, SHINY_COMMITTED_SP, make_shiny_pika,
)
from pikabar.palette import SY, SDY, Y, visible_len
from pikabar.renderer import grid_to_lines


# ============================================================
# Feature 1: Session Greeting
# ============================================================

def test_session_greeting_returns_valid_text():
    text = get_session_greeting()
    all_greetings = SESSION_GREETINGS + list(SESSION_DAY_GREETINGS.values())
    assert text in all_greetings


def test_session_greeting_day_override():
    """Monday (weekday=0) should sometimes return day greeting."""
    with patch("pikabar.flavor.datetime") as mock_dt:
        mock_dt.now.return_value.weekday.return_value = 0
        with patch("pikabar.flavor.random") as mock_rand:
            mock_rand.random.return_value = 0.1  # < 0.5 → use day greeting
            mock_rand.choice.return_value = SESSION_GREETINGS[0]
            result = get_session_greeting()
            assert result == SESSION_DAY_GREETINGS[0]


def test_info_lines_session_start_shows_greeting():
    """Session start event triggers greeting on extra line."""
    session = {
        "model_id": "claude-opus-4-6",
        "model_name": "Opus",
        "hp_pct": 80,
        "hp_window": "5h",
        "pp_pct": 90,
        "events": ["session_start"],
        "_tick": 0,
    }
    info = _info_lines(session)
    assert len(info) == 5
    # Extra line (info[4]) should have greeting text (non-empty, colored)
    assert info[4] != ""
    assert "\033[" in info[4]  # has ANSI color codes


# ============================================================
# Feature 2: Commit Confetti
# ============================================================

def test_committed_confetti_has_variety():
    """Committed decorator should produce varied confetti across ticks."""
    sprite = grid_to_lines(SHINY_IDLE_FRAMES[0])
    results = set()
    for tick in range(8):
        lines = decorate_committed(sprite, tick, session={"_tick": tick})
        # Line 0 has above effects — should differ across ticks
        results.add(lines[0])
    # At least 2 different above patterns (confetti is random per tick)
    assert len(results) >= 2


# ============================================================
# Feature 3: Shiny Pikachu
# ============================================================

def test_shiny_propagates_from_prev_state():
    """If prev state is shiny, current stays shiny."""
    assert check_shiny({"shiny": True}) is True
    assert check_shiny({"shiny": False}) is False


def test_shiny_new_session_rolls():
    """New session (no prev state) rolls for shiny."""
    with patch("pikabar.delta.random") as mock_rand:
        mock_rand.random.return_value = 0.0001  # < 1/500 = shiny
        assert check_shiny(None) is True
        mock_rand.random.return_value = 0.5  # > 1/500 = not shiny
        assert check_shiny(None) is False


def test_shiny_sprite_uses_different_palette():
    """Shiny Pikachu body uses SY (208) not Y (220)."""
    normal = SHINY_IDLE_FRAMES[0]
    # Body pixel at row 1, col 6 should be SY (208)
    assert normal[1][6] == SY
    # Cheek at row 3, col 6 should be SDY (197=SRD)
    from pikabar.palette import SRD
    assert normal[3][6] == SRD


def test_shiny_sprite_dimensions():
    """All shiny sprites should be 6x15 (3 terminal lines)."""
    for frame in SHINY_IDLE_FRAMES:
        assert len(frame) == 6
        assert all(len(row) == 15 for row in frame)
        lines = grid_to_lines(frame)
        assert len(lines) == 3


# ============================================================
# Feature 4: Critical HP Drama
# ============================================================

def test_critical_flavor_returns_valid():
    text = get_critical_flavor()
    assert text in CRITICAL_FLAVOR


def test_info_lines_critical_hp_shows_danger():
    """HP < 10% should show DANGER label instead of window label."""
    session = {
        "model_id": "claude-opus-4-6",
        "model_name": "Opus",
        "hp_pct": 5,
        "hp_window": "5h",
        "pp_pct": 90,
        "events": [],
        "_tick": 1,
    }
    info = _info_lines(session)
    # HP line (info[2]) should contain DANGER
    assert "DANGER" in info[2]
    # Should NOT contain "5h limit"
    assert "5h limit" not in info[2]


def test_info_lines_normal_hp_no_danger():
    """HP >= 10% should show normal label."""
    session = {
        "model_id": "claude-opus-4-6",
        "model_name": "Opus",
        "hp_pct": 50,
        "hp_window": "5h",
        "pp_pct": 90,
        "events": [],
        "_tick": 1,
    }
    info = _info_lines(session)
    assert "DANGER" not in info[2]
    assert "5h limit" in info[2]


def test_info_lines_critical_hp_shows_critical_flavor():
    """HP < 10% should show critical flavor text on extra line."""
    session = {
        "model_id": "claude-opus-4-6",
        "model_name": "Opus",
        "hp_pct": 3,
        "hp_window": "5h",
        "pp_pct": 90,
        "events": [],
        "_tick": 5,
    }
    info = _info_lines(session)
    # Extra line should have critical flavor (non-empty)
    assert info[4] != ""


# ============================================================
# Feature 5: Streak Counter
# ============================================================

def test_streak_new_session():
    streak, last = compute_streak(None)
    assert streak == 1
    assert last == date.today().isoformat()


def test_streak_same_day():
    today = date.today().isoformat()
    streak, last = compute_streak({"streak": 3, "last_active": today})
    assert streak == 3
    assert last == today


def test_streak_consecutive_day():
    from datetime import timedelta
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    streak, last = compute_streak({"streak": 5, "last_active": yesterday})
    assert streak == 6
    assert last == date.today().isoformat()


def test_streak_broken():
    from datetime import timedelta
    three_days_ago = (date.today() - timedelta(days=3)).isoformat()
    streak, last = compute_streak({"streak": 10, "last_active": three_days_ago})
    assert streak == 1


def test_format_model_with_streak():
    result = format_model("claude-opus-4-6", "Opus", streak_days=5)
    assert "Lv.4" in result
    assert "OPUS" in result
    assert "x5" in result  # streak display


def test_format_model_no_streak():
    result = format_model("claude-opus-4-6", "Opus", streak_days=1)
    assert "x1" not in result  # no streak below 2
    assert "Lv.4" in result
