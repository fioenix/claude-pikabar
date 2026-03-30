"""Tests for pikabar.info_panel — layout engine and formatters."""

from pikabar.info_panel import (
    format_model, format_git, format_cost, decorate,
    DECORATED_LINES, INFO_COL,
)
from pikabar.palette import visible_len
from pikabar.renderer import grid_to_lines
from pikabar.sprites import IDLE_FRAMES, THINKING_SP, BALL_FRAMES
import re


def strip_ansi(s):
    return re.sub(r'\033\[[^m]*m', '', s)


# --- format_model ---

def test_format_model_opus():
    result = strip_ansi(format_model("claude-opus-4-6", "Opus"))
    assert "Lv.4" in result
    assert "OPUS" in result


def test_format_model_sonnet():
    result = strip_ansi(format_model("claude-sonnet-4-6", "Sonnet"))
    assert "Lv.4" in result
    assert "SONNET" in result


def test_format_model_unknown():
    result = strip_ansi(format_model("unknown", ""))
    assert "Lv.?" in result


# --- format_git ---

def test_format_git_full():
    result = strip_ansi(format_git("main", 3, 2))
    assert "main" in result
    assert "+3" in result
    assert "~2" in result


def test_format_git_no_branch():
    assert format_git(None) == ""
    assert format_git("") == ""


def test_format_git_clean():
    result = strip_ansi(format_git("main", 0, 0))
    assert "main" in result
    assert "+" not in result
    assert "~" not in result


# --- format_cost ---

def test_format_cost_zero():
    assert format_cost(0) == ""
    assert format_cost(None) == ""


def test_format_cost_tiny():
    result = strip_ansi(format_cost(0.005))
    assert "<$0.01" in result


def test_format_cost_normal():
    result = strip_ansi(format_cost(0.42))
    assert "$0.42" in result


def test_format_cost_high():
    result = strip_ansi(format_cost(2.85))
    assert "$2.85" in result


# --- decorate (integration) ---

def _session(**overrides):
    base = {
        "model_id": "claude-opus-4-6",
        "model_name": "Opus",
        "branch": "main",
        "staged": 2,
        "modified": 1,
        "hp_pct": 72,
        "hp_window": "5h",
        "pp_pct": 85,
        "cost_usd": 0.42,
        "_tick": 0,
    }
    base.update(overrides)
    return base


def test_decorate_returns_correct_line_count():
    sprite = grid_to_lines(IDLE_FRAMES[0])
    lines = decorate("idle", sprite, 0, session=_session())
    assert len(lines) == DECORATED_LINES


def test_decorate_all_reactions_produce_correct_lines():
    reactions = ["idle", "thinking", "staging", "committed",
                 "recovered", "compacted", "hit", "faint"]
    sprites = {
        "idle": IDLE_FRAMES[0], "thinking": THINKING_SP,
        "staging": IDLE_FRAMES[0], "committed": IDLE_FRAMES[0],
        "recovered": IDLE_FRAMES[0], "compacted": IDLE_FRAMES[0],
        "hit": IDLE_FRAMES[0], "faint": BALL_FRAMES[0],
    }
    from pikabar.sprites import (STAGING_SP, COMMITTED_SP, RECOVERED_SP,
                                  HIT_SP, COMPACTED_SP)
    sprites.update({
        "staging": STAGING_SP, "committed": COMMITTED_SP,
        "recovered": RECOVERED_SP, "compacted": COMPACTED_SP,
        "hit": HIT_SP,
    })
    for reaction in reactions:
        s = _session(hp_pct=0) if reaction == "faint" else _session()
        sprite = grid_to_lines(sprites[reaction])
        lines = decorate(reaction, sprite, 0, session=s)
        assert len(lines) == DECORATED_LINES, f"{reaction} produced {len(lines)} lines"


def test_decorate_info_alignment():
    """All info markers should start at the same terminal column."""
    import unicodedata

    def tcol(s):
        return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1
                   for c in s)

    sprite = grid_to_lines(THINKING_SP)
    cols = set()
    for tick in range(4):
        lines = decorate("thinking", sprite, tick, session=_session())
        for line in lines:
            plain = strip_ansi(line)
            for marker in ["Lv.", "HP ", "PP "]:
                pos = plain.find(marker)
                if pos >= 0:
                    cols.add(tcol(plain[:pos]) + 1)

    assert len(cols) == 1, f"Misaligned info columns: {cols}"
