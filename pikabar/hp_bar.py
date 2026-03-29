"""HP bar and status badge rendering.

HP = Rate limit quota REMAINING (100 - used%).
Full HP = safe. Empty HP = rate limited (paralyzed).
"""

from .palette import (
    fg, bg, RST, BOLD,
    HP_GREEN, HP_YELLOW, HP_RED, DIM, SUBTLE,
    BADGE_PAR, BADGE_SLP, BADGE_PSN, BADGE_BRN, BADGE_FRZ,
)

# Bar dimensions
BAR_WIDTH = 16
# Use ASCII-safe characters for Claude Code compatibility
# (Unicode block elements render double-wide in Ink.js)
BAR_FILL = "#"
BAR_EMPTY = "."


def hp_color(hp_pct):
    """Return the 256-color code for the given HP percentage."""
    if hp_pct > 50:
        return HP_GREEN
    elif hp_pct > 20:
        return HP_YELLOW
    else:
        return HP_RED


def render_hp_bar(hp_pct, tick=0, width=BAR_WIDTH):
    """Render the HP bar string.

    Args:
        hp_pct: HP remaining (0-100). None if no data.
        tick: animation tick for flash effect at critical HP.
        width: bar width in characters.

    Returns:
        Formatted string like "HP ████████████░░░░ 72% 5h"
    """
    if hp_pct is None:
        # No rate limit data available
        unknown = "?" * width
        return f"{fg(SUBTLE)}HP {fg(DIM)}{unknown}{RST} {fg(SUBTLE)}---{RST}"

    hp_pct = max(0, min(100, hp_pct))
    filled = int(width * hp_pct / 100)
    empty = width - filled

    color = hp_color(hp_pct)

    # Flash effect at critical HP (<5%)
    if hp_pct < 5 and tick % 2 == 1:
        color = DIM  # alternate between red and dim

    bar = f"{fg(color)}{BAR_FILL * filled}{fg(DIM)}{BAR_EMPTY * empty}{RST}"
    pct_str = f"{fg(color)}{hp_pct}%{RST}"

    return f"{fg(SUBTLE)}HP{RST} {bar} {pct_str}"


def render_hp_line(hp_pct, window_label=None, tick=0):
    """Render the full HP line including rate window label.

    Args:
        hp_pct: HP remaining (0-100). None if no data.
        window_label: "5h" or "7d" — which rate window is binding.
        tick: animation tick.
    """
    bar = render_hp_bar(hp_pct, tick=tick)
    if window_label and hp_pct is not None:
        return f"{bar} {fg(SUBTLE)}{window_label}{RST}"
    return bar


# ============================================================
# Status badges (Pokemon game-accurate colors)
# ============================================================

def _badge(text, colors):
    """Render a colored badge like [PAR]."""
    return f"{BOLD}{fg(colors['fg'])}{bg(colors['bg'])} {text} {RST}"


BADGE_SPECS = {
    "FRZ": BADGE_FRZ,
    "PAR": BADGE_PAR,
    "SLP": BADGE_SLP,
    "PSN": BADGE_PSN,
    "BRN": BADGE_BRN,
}


def get_badge(hp_pct, is_compacting=False, is_rate_limited=False):
    """Determine which status badge to show (one at a time, priority order).

    Priority: FRZ > PAR > SLP > PSN > BRN > none.
    """
    if is_rate_limited and is_compacting:
        return _badge("FRZ", BADGE_FRZ)
    if is_rate_limited:
        return _badge("PAR", BADGE_PAR)
    if is_compacting:
        return _badge("SLP", BADGE_SLP)
    if hp_pct is not None:
        if hp_pct <= 15:
            return _badge("PSN", BADGE_PSN)
        if hp_pct <= 35:
            return _badge("BRN", BADGE_BRN)
    return ""
