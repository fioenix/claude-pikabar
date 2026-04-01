"""Tests for Agent Teams awareness feature."""

from pikabar.info_panel import (
    format_agent_label, format_party_balls, _info_lines,
    decorate_idle, DECORATED_LINES,
)
from pikabar.flavor import get_agent_flavor, AGENT_FLAVOR
from pikabar.palette import visible_len
from pikabar.renderer import grid_to_lines
from pikabar.sprites import IDLE_FRAMES


def _make_session(**overrides):
    """Build a minimal session dict with defaults."""
    base = {
        "model_id": "claude-sonnet-4-6",
        "model_name": "Sonnet",
        "hp_pct": 70,
        "hp_window": "5h",
        "pp_pct": 80,
        "events": [],
        "_tick": 0,
    }
    base.update(overrides)
    return base


# ============================================================
# format_agent_label
# ============================================================

def test_format_agent_label_basic():
    result = format_agent_label("dev-lead")
    assert "DEV-LEAD" in result
    assert "\033[" in result  # has ANSI codes


def test_format_agent_label_truncation():
    result = format_agent_label("super-long-agent-name-here")
    # Should be truncated with ellipsis
    assert "\u2026" in result
    # Visible length should be reasonable (not overflow panel)
    assert visible_len(result) <= 28


def test_format_agent_label_with_worktree():
    result = format_agent_label("dev-lead", "my-feat")
    assert "DEV-LEAD" in result
    assert "my-feat" in result
    assert "@" in result


# ============================================================
# format_party_balls
# ============================================================

def test_format_party_balls():
    result = format_party_balls()
    assert "\u25cf" in result  # filled ball ●
    assert result.count("\u25cb") == 5  # 5 empty balls ○


# ============================================================
# _info_lines agent mode
# ============================================================

def test_info_lines_agent_mode():
    session = _make_session(agent_name="dev-lead", worktree_name="my-feature")
    info = _info_lines(session)
    assert len(info) == 5
    # Line 0 should contain agent name (above info)
    assert "DEV-LEAD" in info[0]
    # Line 1 should still contain model (Lv.N SPECIES preserved)
    assert "SONNET" in info[1]


def test_info_lines_normal_mode():
    session = _make_session()
    info = _info_lines(session)
    assert len(info) == 5
    # Line 0 should be empty (no agent)
    assert info[0] == ""
    # Line 1 should contain model name
    assert "SONNET" in info[1]


# ============================================================
# Decorators with agent mode
# ============================================================

def test_decorate_idle_agent_side_balls():
    session = _make_session(agent_name="dev-lead")
    sprite = grid_to_lines(IDLE_FRAMES[0])
    lines = decorate_idle(sprite, 0, session=session)
    assert len(lines) == DECORATED_LINES
    # Party balls should appear as side effect on sprite line 1
    assert "\u25cf" in lines[1]  # filled ball beside sprite
    # Agent name should appear in above info (line 0 right side)
    assert "DEV-LEAD" in lines[0]


def test_decorate_idle_normal_no_balls():
    session = _make_session()
    sprite = grid_to_lines(IDLE_FRAMES[0])
    lines = decorate_idle(sprite, 0, session=session)
    assert len(lines) == DECORATED_LINES
    # No party balls anywhere
    assert "\u25cf" not in lines[0]
    assert "\u25cf" not in lines[1]


# ============================================================
# Agent flavor
# ============================================================

def test_get_agent_flavor_with_name():
    result = get_agent_flavor("dev-lead")
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_agent_flavor_long_name():
    result = get_agent_flavor("very-long-agent-name-exceeding-limit")
    assert result in AGENT_FLAVOR


# ============================================================
# End-to-end: statusline with agent JSON
# ============================================================

def test_statusline_agent_json():
    from pikabar.statusline import render_statusline
    data = {
        "model": {"id": "claude-sonnet-4-6", "display_name": "Sonnet"},
        "agent": {"name": "dev-lead"},
        "worktree": {"name": "auth-refactor", "branch": "worktree-auth-refactor"},
        "rate_limits": {"five_hour": {"used_percentage": 30}},
        "cost": {"total_cost_usd": 0.15},
    }
    output = render_statusline(data)
    assert "DEV-LEAD" in output
    assert "\u25cf" in output  # party ball
