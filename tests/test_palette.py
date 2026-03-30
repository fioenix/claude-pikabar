"""Tests for pikabar.palette — terminal escape helpers."""

from pikabar.palette import fg, bg, visible_len, RST


def test_fg_returns_ansi_escape():
    assert fg(220) == "\033[38;5;220m"


def test_fg_none_returns_empty():
    assert fg(None) == ""


def test_bg_returns_ansi_escape():
    assert bg(16) == "\033[48;5;16m"


def test_visible_len_plain_text():
    assert visible_len("hello") == 5


def test_visible_len_strips_ansi():
    s = f"{fg(220)}hello{RST}"
    assert visible_len(s) == 5


def test_visible_len_wide_char():
    # ⚡ is East Asian Width "W" = 2 terminal columns
    assert visible_len("\u26a1") == 2


def test_visible_len_mixed_ansi_and_wide():
    s = f"  {fg(220)}\u26a1{RST} text"
    # 2 spaces + ⚡(2 cols) + space + "text"(4) = 9
    assert visible_len(s) == 9


def test_visible_len_empty():
    assert visible_len("") == 0


def test_visible_len_block_chars():
    # Block chars (▀▄█) are East Asian Width "A" = 1 col in most terminals
    assert visible_len("▀▄█") == 3
