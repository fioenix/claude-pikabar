"""Pikachu and Pokeball pixel art sprites.

Design N final: eyes look RIGHT, tail on LEFT.
6 rows x 15 cols = 3 terminal lines per pikachu.
7 rows x 11 cols = 4 terminal lines per pokeball.

Reaction sprites:
  IDLE_FRAMES   — subtle life cycle (normal + occasional glance)
  THINKING_SP   — glancing, tail raised, alert
  STAGING_SP    — same as thinking (alert but softer via decoration)
  COMMITTED_SP  — winking, tail raised, proud
  RECOVERED_SP  — normal, relaxed
  HIT_SP        — eyes closed (pain squint)
  COMPACTED_SP  — eyes closed (sleeping)
  BALL_FRAMES   — pokeball wobble (faint/ratelimited)
"""

from .palette import Y, LY, DY, BK, RD, W, PW, PR, SY, SLY, SDY, SRD

_ = None  # transparent pixel


# ============================================================
# Pikachu sprite factory
# ============================================================

def make_pika(left_eye=(BK, W), right_eye=(BK, W),
              tail_variant=0, feet_variant=0):
    """Generate a Pikachu grid with configurable eyes, tail, feet.

    Eyes: tuple of (pupil, highlight) colors.
    Tail: 0=center, 1=shifted.
    Feet: 0=spread, 1=together.
    """
    # Tail pixel maps
    if tail_variant == 0:
        tail = {
            (1, 1): Y,
            (2, 1): Y, (2, 2): Y,
            (3, 1): Y,
            (4, 2): Y, (4, 3): Y,
            (5, 4): Y,
        }
    else:
        tail = {
            (1, 1): Y, (1, 2): Y,
            (2, 2): Y,
            (3, 1): Y, (3, 2): Y,
            (4, 2): Y,
            (5, 4): Y,
        }

    # Feet pixel maps
    if feet_variant == 0:
        feet = {(5, 7): DY, (5, 11): DY}
    else:
        feet = {(5, 8): DY, (5, 10): DY}

    # Build 6x15 grid
    grid = [[None] * 15 for _ in range(6)]

    # Ears
    grid[0][5] = BK; grid[0][6] = Y; grid[0][12] = Y; grid[0][13] = BK

    # Head
    for c in range(6, 13):
        grid[1][c] = Y

    # Eyes row
    grid[2][5] = Y; grid[2][6] = Y
    grid[2][7] = left_eye[0]; grid[2][8] = left_eye[1]
    grid[2][9] = Y
    grid[2][10] = right_eye[0]; grid[2][11] = right_eye[1]
    grid[2][12] = Y; grid[2][13] = Y

    # Cheeks
    grid[3][5] = Y; grid[3][6] = RD; grid[3][7] = RD; grid[3][8] = Y
    grid[3][9] = Y; grid[3][10] = Y
    grid[3][11] = RD; grid[3][12] = RD; grid[3][13] = Y

    # Body
    for c in range(6, 13):
        grid[4][c] = Y

    # Apply tail, feet
    for (r, c), color in tail.items():
        grid[r][c] = color
    for (r, c), color in feet.items():
        grid[r][c] = color

    return grid


# ============================================================
# Pokeball sprite factory
# ============================================================

def _shift_row(row, n):
    """Shift row contents by n pixels. Positive=right, negative=left."""
    if n == 0:
        return row[:]
    if n > 0:
        return [None] * n + row[:-n]
    else:
        return row[-n:] + [None] * (-n)


def make_pokeball(tilt=0):
    """Generate a Pokeball grid (7 rows x 11 cols).

    Wobble: bottom-pivot physics. Top rows shift ±1px, bottom stays fixed.
    """
    base = [
        [_,  _,  _,  BK, BK, BK, BK, BK, _,  _,  _],   # 0: top curve
        [_,  BK, PR, PR, PR, PR, PR, PR, PR, BK, _],     # 1: red
        [BK, PR, PR, PR, PR, BK, PR, PR, PR, PR, BK],    # 2: red + btn top
        [BK, BK, BK, BK, BK, W,  BK, BK, BK, BK, BK],   # 3: band + button
        [BK, PW, PW, PW, PW, BK, PW, PW, PW, PW, BK],    # 4: white + btn bot
        [_,  BK, PW, PW, PW, PW, PW, PW, PW, BK, _],     # 5: white
        [_,  _,  _,  BK, BK, BK, BK, BK, _,  _,  _],     # 6: bottom curve
    ]

    if tilt == 0:
        return base

    # Bottom-pivot: rows 0-3 shift, rows 4-6 stay
    shift_amounts = [1, 1, 1, 1, 0, 0, 0]
    direction = tilt
    return [_shift_row(row, direction * shift_amounts[r])
            for r, row in enumerate(base)]


# ============================================================
# Reaction sprites
# ============================================================

# --- Idle: subtle life cycle (frame % 3) ---
IDLE_FRAMES = [
    make_pika(left_eye=(BK, W), right_eye=(BK, W), tail_variant=0, feet_variant=1),  # normal
    make_pika(left_eye=(W, BK), right_eye=(W, BK), tail_variant=0, feet_variant=1),  # glancing
    make_pika(left_eye=(BK, W), right_eye=(BK, W), tail_variant=1, feet_variant=1),  # tail sway
]

# --- Thinking: focused, alert ---
THINKING_SP = make_pika(left_eye=(W, BK), right_eye=(W, BK), tail_variant=1, feet_variant=0)

# --- Staging: alert (same sprite as thinking, differentiated by decoration) ---
STAGING_SP = THINKING_SP

# --- Committed: winking, proud ---
COMMITTED_SP = make_pika(left_eye=(BK, W), right_eye=(Y, DY), tail_variant=1, feet_variant=0)

# --- Recovered: normal, relaxed ---
RECOVERED_SP = make_pika(left_eye=(BK, W), right_eye=(BK, W), tail_variant=0, feet_variant=1)

# --- Hit: eyes closed (pain) ---
HIT_SP = make_pika(left_eye=(Y, DY), right_eye=(Y, DY), tail_variant=0, feet_variant=1)

# --- Compacted: eyes closed (sleeping) ---
COMPACTED_SP = make_pika(left_eye=(Y, DY), right_eye=(Y, DY), tail_variant=0, feet_variant=0)

# --- Faint: Pokeball wobble ---
_B0 = make_pokeball(tilt=0)
_BR = make_pokeball(tilt=1)
_BL = make_pokeball(tilt=-1)
BALL_FRAMES = [
    _BR, _BR,    # lean right (hold)
    _B0,          # pass through center
    _BL, _BL,    # lean left (hold)
    _B0,          # pass through center
]


# ============================================================
# Backwards-compat aliases (used by demo.py / animator.py)
# ============================================================

THINK_FRAMES = IDLE_FRAMES
COMPACT_FRAME = COMPACTED_SP


# ============================================================
# Shiny Pikachu variants (Feature 3: 1/500 per session)
# ============================================================

def make_shiny_pika(left_eye=(BK, W), right_eye=(BK, W),
                    tail_variant=0, feet_variant=0):
    """Shiny Pikachu — orange palette swap, like the games."""
    # Reuse make_pika but patch colors after generation
    grid = make_pika(left_eye, right_eye, tail_variant, feet_variant)
    # Swap palette: Y→SY, LY→SLY, DY→SDY, RD→SRD
    COLOR_MAP = {Y: SY, LY: SLY, DY: SDY, RD: SRD}
    for r in range(len(grid)):
        for c in range(len(grid[r])):
            if grid[r][c] in COLOR_MAP:
                grid[r][c] = COLOR_MAP[grid[r][c]]
    return grid


SHINY_IDLE_FRAMES = [
    make_shiny_pika(left_eye=(BK, W), right_eye=(BK, W), tail_variant=0, feet_variant=1),
    make_shiny_pika(left_eye=(W, BK), right_eye=(W, BK), tail_variant=0, feet_variant=1),
    make_shiny_pika(left_eye=(BK, W), right_eye=(BK, W), tail_variant=1, feet_variant=1),
]

SHINY_THINKING_SP = make_shiny_pika(left_eye=(W, BK), right_eye=(W, BK), tail_variant=1, feet_variant=0)
SHINY_STAGING_SP = SHINY_THINKING_SP
SHINY_COMMITTED_SP = make_shiny_pika(left_eye=(BK, W), right_eye=(SY, SDY), tail_variant=1, feet_variant=0)
SHINY_RECOVERED_SP = make_shiny_pika(left_eye=(BK, W), right_eye=(BK, W), tail_variant=0, feet_variant=1)
SHINY_HIT_SP = make_shiny_pika(left_eye=(SY, SDY), right_eye=(SY, SDY), tail_variant=0, feet_variant=1)
SHINY_COMPACTED_SP = make_shiny_pika(left_eye=(SY, SDY), right_eye=(SY, SDY), tail_variant=0, feet_variant=0)
