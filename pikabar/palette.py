"""ANSI 256-color palette and terminal escape helpers."""

import re as _re
import unicodedata as _unicodedata

# --- Pikachu colors ---
Y  = 220   # Yellow (body)
LY = 228   # Light yellow
DY = 178   # Dark yellow (shadows, closed eyes)
OR = 214   # Orange
BK = 16    # Black (outline, pupils)
RD = 203   # Red (cheeks)
BR = 94    # Brown
W  = 231   # White (eye highlights)

# --- Shiny Pikachu colors (orange-tinted, like game shiny variants) ---
SY  = 208   # Shiny body (orange instead of yellow)
SLY = 215   # Shiny light (lighter orange)
SDY = 166   # Shiny dark (deep orange shadows)
SRD = 197   # Shiny cheeks (magenta-pink instead of red)

# --- Pokeball colors ---
PW = 255   # Pokeball white
PR = 196   # Pokeball red

# --- HP bar colors ---
HP_GREEN  = 34    # >50% remaining
HP_YELLOW = 178   # 20-50%
HP_RED    = 196   # <20%

# --- Badge colors (Pokemon game-accurate) ---
BADGE_PAR = {"bg": 220, "fg": 16}    # Paralyzed: gold bg, black text
BADGE_SLP = {"bg": 243, "fg": 231}   # Sleep: gray bg, white text
BADGE_PSN = {"bg": 91,  "fg": 231}   # Poison: purple bg, white text
BADGE_BRN = {"bg": 202, "fg": 231}   # Burn: orange bg, white text
BADGE_FRZ = {"bg": 117, "fg": 16}    # Frozen: ice blue bg, black text

# --- UI colors ---
DIM    = 240   # Dim gray (empty bars, separators)
SUBTLE = 245   # Subtle gray (secondary text)
GREEN  = 114   # Bright green (cost, git additions)
GOLD   = 220   # Gold (model name, warnings)

# --- Terminal escapes ---
RST  = "\033[0m"
BOLD = "\033[1m"
HIDE = "\033[?25l"
SHOW = "\033[?25h"
CLR  = "\033[2K"


def fg(n):
    """Foreground color from 256-palette."""
    return f"\033[38;5;{n}m" if n is not None else ""


def bg(n):
    """Background color from 256-palette."""
    return f"\033[48;5;{n}m" if n is not None else ""


def UP(n):
    """Move cursor up n lines."""
    return f"\033[{n}A" if n > 0 else ""


def visible_len(s):
    """Count terminal column width of an ANSI-escaped string.

    Accounts for wide characters (e.g. ⚡ = 2 cols) using
    Unicode East Asian Width. W/F = 2 cols, everything else = 1.
    """
    stripped = _re.sub(r'\033\[[^m]*m', '', s)
    width = 0
    for ch in stripped:
        eaw = _unicodedata.east_asian_width(ch)
        width += 2 if eaw in ('W', 'F') else 1
    return width
