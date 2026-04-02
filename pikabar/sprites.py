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

from functools import lru_cache
from .palette import Y, LY, DY, BK, RD, W, PW, PR, OR, BR, SY, SLY, SDY, SRD, SOR, SLY2, SOR2

_ = None  # transparent pixel


# ============================================================
# Pikachu sprite factory
# ============================================================

@lru_cache(maxsize=32)
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
# Pichu sprite factory — smaller, cuter, no red cheeks
# ============================================================

@lru_cache(maxsize=32)
def make_pichu(left_eye=(BK, W), right_eye=(BK, W),
               tail_variant=0, feet_variant=0):
    """Generate a Pichu grid — baby Pokemon, big eyes, no cheeks.

    Pichu is the pre-evolution: very small, big round eyes,
    no red cheeks, tiny rounded ears. Much cuter and smaller than Pikachu.
    """
    # Tail pixel maps (small tail on left side, like baby Pikachu)
    if tail_variant == 0:
        tail = {
            (1, 1): Y,
            (2, 1): Y, (2, 2): Y,
            (3, 1): Y,
        }
    else:
        tail = {
            (1, 1): Y, (1, 2): Y,
            (2, 2): Y,
            (3, 1): Y, (3, 2): Y,
        }

    # Feet pixel maps
    if feet_variant == 0:
        feet = {(5, 7): DY, (5, 11): DY}
    else:
        feet = {(5, 8): DY, (5, 10): DY}

    # Build 6x15 grid
    grid = [[None] * 15 for _ in range(6)]

    # Ears — Pichu has tiny round ears (black tips + yellow)
    grid[0][5] = BK; grid[0][6] = Y
    grid[0][11] = Y; grid[0][12] = BK

    # Head — Pichu has a big round head (cols 6-12)
    for c in range(6, 13):
        grid[1][c] = Y

    # Eyes row — BIG EYES! That's Pichu's main characteristic
    # Left eye
    grid[2][5] = Y; grid[2][6] = Y; grid[2][7] = Y
    grid[2][8] = left_eye[0]; grid[2][9] = left_eye[1]
    # Right eye
    grid[2][10] = Y
    grid[2][11] = right_eye[0]; grid[2][12] = right_eye[1]; grid[2][13] = Y

    # Cheeks row — Pichu has YELLOW cheeks (no red yet!)
    for c in range(5, 14):
        grid[3][c] = Y

    # Body — slightly smaller than Pikachu (cols 6-12)
    for c in range(6, 13):
        grid[4][c] = Y

    # Apply tail, feet
    for (r, c), color in tail.items():
        grid[r][c] = color
    for (r, c), color in feet.items():
        grid[r][c] = color

    return grid


# ============================================================
# Raichu sprite factory — evolved form, orange palette, sleek
# ============================================================

@lru_cache(maxsize=32)
def make_raichu(left_eye=(BK, W), right_eye=(BK, W),
                tail_variant=0, feet_variant=0):
    """Generate a Raichu grid — sleek orange body, long pointed ears, lightning tail.

    Raichu is the evolved form: orange (not yellow), longer body,
    distinctive lightning bolt tail, elegant pointed ears.
    """
    # Tail pixel maps (lightning bolt style)
    if tail_variant == 0:
        tail = {
            (0, 1): OR,
            (1, 2): OR,
            (2, 1): OR, (2, 2): OR,
            (3, 1): OR,
            (4, 2): OR,
            (5, 3): OR,
        }
    else:
        tail = {
            (0, 1): OR, (0, 2): OR,
            (1, 1): OR,
            (2, 1): OR, (2, 2): OR,
            (3, 2): OR,
            (4, 1): OR,
            (5, 2): OR,
        }

    # Feet pixel maps
    if feet_variant == 0:
        feet = {(5, 7): DY, (5, 11): DY}
    else:
        feet = {(5, 8): DY, (5, 10): DY}

    # Build 6x15 grid
    grid = [[None] * 15 for _ in range(6)]

    # Ears — longer, pointed, orange with red tips
    grid[0][4] = RD; grid[0][5] = OR; grid[0][6] = OR
    grid[0][11] = OR; grid[0][12] = OR; grid[0][13] = RD

    # Head — sleek, slightly narrower
    for c in range(5, 13):
        grid[1][c] = OR

    # Eyes row
    grid[2][4] = OR; grid[2][5] = OR; grid[2][6] = OR
    grid[2][7] = left_eye[0]; grid[2][8] = left_eye[1]
    grid[2][9] = OR
    grid[2][10] = right_eye[0]; grid[2][11] = right_eye[1]
    grid[2][12] = OR; grid[2][13] = OR

    # Cheeks — same red cheeks as Pikachu (Raichu has them too)
    grid[3][5] = OR; grid[3][6] = RD; grid[3][7] = RD; grid[3][8] = OR
    grid[3][9] = OR; grid[3][10] = OR
    grid[3][11] = RD; grid[3][12] = RD; grid[3][13] = OR

    # Body — sleek orange
    for c in range(5, 13):
        grid[4][c] = OR

    # Apply tail, feet
    for (r, c), color in tail.items():
        grid[r][c] = color
    for (r, c), color in feet.items():
        grid[r][c] = color

    return grid


# ============================================================
# Shiny sprite factories (mutate base sprite colors)
# ============================================================

@lru_cache(maxsize=32)
def make_shiny_pika(left_eye=(BK, W), right_eye=(BK, W),
                    tail_variant=0, feet_variant=0):
    """Shiny Pikachu — orange palette swap, like the games."""
    grid = make_pika(left_eye, right_eye, tail_variant, feet_variant)
    # Swap palette: Y→SY, LY→SLY, DY→SDY, RD→SRD
    COLOR_MAP = {Y: SY, LY: SLY, DY: SDY, RD: SRD}
    for r in range(len(grid)):
        for c in range(len(grid[r])):
            if grid[r][c] in COLOR_MAP:
                grid[r][c] = COLOR_MAP[grid[r][c]]
    return grid


@lru_cache(maxsize=32)
def make_shiny_pichu(left_eye=(BK, W), right_eye=(BK, W),
                     tail_variant=0, feet_variant=0):
    """Shiny Pichu — same as regular (already yellowish)."""
    grid = make_pichu(left_eye, right_eye, tail_variant, feet_variant)
    # Swap palette: Y→SY, LY→SLY, DY→SDY
    COLOR_MAP = {Y: SY, LY: SLY, DY: SDY}
    for r in range(len(grid)):
        for c in range(len(grid[r])):
            if grid[r][c] in COLOR_MAP:
                grid[r][c] = COLOR_MAP[grid[r][c]]
    return grid


@lru_cache(maxsize=32)
def make_shiny_raichu(left_eye=(BK, W), right_eye=(BK, W),
                      tail_variant=0, feet_variant=0):
    """Shiny Raichu — golden/tan palette swap."""
    grid = make_raichu(left_eye, right_eye, tail_variant, feet_variant)
    # Swap palette: OR→SOR, LY→SLY2, DY→SOR2
    COLOR_MAP = {OR: SOR, LY: SLY2, DY: SOR2}
    for r in range(len(grid)):
        for c in range(len(grid[r])):
            if grid[r][c] in COLOR_MAP:
                grid[r][c] = COLOR_MAP[grid[r][c]]
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


@lru_cache(maxsize=8)
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
# Reaction sprites factory (cached)
# ============================================================

@lru_cache(maxsize=64)
def _make_reaction_frames(species_key):
    """Generate all reaction sprites for a species. Cached per species."""
    # Base eye configurations
    eyes_normal = (BK, W)
    eyes_glance = (W, BK)
    eyes_pain = (Y, DY)

    # Get the factory function
    if species_key == "pichu":
        factory = make_pichu
    elif species_key == "raichu":
        factory = make_raichu
    else:
        factory = make_pika

    # Idle: subtle life cycle (frame % 3)
    idle = [
        factory(left_eye=eyes_normal, right_eye=eyes_normal, tail_variant=0, feet_variant=1),  # normal
        factory(left_eye=eyes_glance, right_eye=eyes_glance, tail_variant=0, feet_variant=1),  # glancing
        factory(left_eye=eyes_normal, right_eye=eyes_normal, tail_variant=1, feet_variant=1),  # tail sway
    ]

    # All other reactions
    thinking = factory(left_eye=eyes_glance, right_eye=eyes_glance, tail_variant=1, feet_variant=0)
    committed = factory(left_eye=eyes_normal, right_eye=(Y, DY), tail_variant=1, feet_variant=0)
    recovered = factory(left_eye=eyes_normal, right_eye=eyes_normal, tail_variant=0, feet_variant=1)
    hit = factory(left_eye=eyes_pain, right_eye=eyes_pain, tail_variant=0, feet_variant=1)
    compacted = factory(left_eye=eyes_pain, right_eye=eyes_pain, tail_variant=0, feet_variant=0)

    return {
        "idle_frames": idle,
        "thinking": thinking,
        "staging": thinking,  # same as thinking
        "committed": committed,
        "recovered": recovered,
        "hit": hit,
        "compacted": compacted,
    }


@lru_cache(maxsize=64)
def _make_shiny_reaction_frames(species_key):
    """Generate all shiny reaction sprites for a species. Cached per species."""
    # Base eye configurations
    eyes_normal = (BK, W)
    eyes_glance = (W, BK)

    # Get the shiny factory function
    if species_key == "pichu":
        shiny_factory = make_shiny_pichu
        eyes_pain = (SY, SDY)
    elif species_key == "raichu":
        shiny_factory = make_shiny_raichu
        eyes_pain = (SOR, SOR2)
    else:
        shiny_factory = make_shiny_pika
        eyes_pain = (SY, SDY)

    # Idle: subtle life cycle
    idle = [
        shiny_factory(left_eye=eyes_normal, right_eye=eyes_normal, tail_variant=0, feet_variant=1),
        shiny_factory(left_eye=eyes_glance, right_eye=eyes_glance, tail_variant=0, feet_variant=1),
        shiny_factory(left_eye=eyes_normal, right_eye=eyes_normal, tail_variant=1, feet_variant=1),
    ]

    # All other reactions
    thinking = shiny_factory(left_eye=eyes_glance, right_eye=eyes_glance, tail_variant=1, feet_variant=0)
    committed = shiny_factory(left_eye=eyes_normal, right_eye=eyes_pain, tail_variant=1, feet_variant=0)
    recovered = shiny_factory(left_eye=eyes_normal, right_eye=eyes_normal, tail_variant=0, feet_variant=1)
    hit = shiny_factory(left_eye=eyes_pain, right_eye=eyes_pain, tail_variant=0, feet_variant=1)
    compacted = shiny_factory(left_eye=eyes_pain, right_eye=eyes_pain, tail_variant=0, feet_variant=0)

    return {
        "idle_frames": idle,
        "thinking": thinking,
        "staging": thinking,
        "committed": committed,
        "recovered": recovered,
        "hit": hit,
        "compacted": compacted,
    }


# --- Backwards-compat: Pikachu reaction sprites (module-level for direct import) ---
_IDLE_PIKA = _make_reaction_frames("pikachu")
IDLE_FRAMES = _IDLE_PIKA["idle_frames"]
THINKING_SP = _IDLE_PIKA["thinking"]
STAGING_SP = _IDLE_PIKA["staging"]
COMMITTED_SP = _IDLE_PIKA["committed"]
RECOVERED_SP = _IDLE_PIKA["recovered"]
HIT_SP = _IDLE_PIKA["hit"]
COMPACTED_SP = _IDLE_PIKA["compacted"]

_SHINY_PIKA = _make_shiny_reaction_frames("pikachu")
SHINY_IDLE_FRAMES = _SHINY_PIKA["idle_frames"]
SHINY_THINKING_SP = _SHINY_PIKA["thinking"]
SHINY_STAGING_SP = _SHINY_PIKA["staging"]
SHINY_COMMITTED_SP = _SHINY_PIKA["committed"]
SHINY_RECOVERED_SP = _SHINY_PIKA["recovered"]
SHINY_HIT_SP = _SHINY_PIKA["hit"]
SHINY_COMPACTED_SP = _SHINY_PIKA["compacted"]

_PICHU_REACTIONS = _make_reaction_frames("pichu")
PICHU_IDLE_FRAMES = _PICHU_REACTIONS["idle_frames"]
PICHU_THINKING_SP = _PICHU_REACTIONS["thinking"]
PICHU_STAGING_SP = _PICHU_REACTIONS["staging"]
PICHU_COMMITTED_SP = _PICHU_REACTIONS["committed"]
PICHU_RECOVERED_SP = _PICHU_REACTIONS["recovered"]
PICHU_HIT_SP = _PICHU_REACTIONS["hit"]
PICHU_COMPACTED_SP = _PICHU_REACTIONS["compacted"]

_SHINY_PICHU = _make_shiny_reaction_frames("pichu")
SHINY_PICHU_IDLE_FRAMES = _SHINY_PICHU["idle_frames"]
SHINY_PICHU_THINKING_SP = _SHINY_PICHU["thinking"]
SHINY_PICHU_STAGING_SP = _SHINY_PICHU["staging"]
SHINY_PICHU_COMMITTED_SP = _SHINY_PICHU["committed"]
SHINY_PICHU_RECOVERED_SP = _SHINY_PICHU["recovered"]
SHINY_PICHU_HIT_SP = _SHINY_PICHU["hit"]
SHINY_PICHU_COMPACTED_SP = _SHINY_PICHU["compacted"]

_RAICHU_REACTIONS = _make_reaction_frames("raichu")
RAICHU_IDLE_FRAMES = _RAICHU_REACTIONS["idle_frames"]
RAICHU_THINKING_SP = _RAICHU_REACTIONS["thinking"]
RAICHU_STAGING_SP = _RAICHU_REACTIONS["staging"]
RAICHU_COMMITTED_SP = _RAICHU_REACTIONS["committed"]
RAICHU_RECOVERED_SP = _RAICHU_REACTIONS["recovered"]
RAICHU_HIT_SP = _RAICHU_REACTIONS["hit"]
RAICHU_COMPACTED_SP = _RAICHU_REACTIONS["compacted"]

_SHINY_RAICHU = _make_shiny_reaction_frames("raichu")
SHINY_RAICHU_IDLE_FRAMES = _SHINY_RAICHU["idle_frames"]
SHINY_RAICHU_THINKING_SP = _SHINY_RAICHU["thinking"]
SHINY_RAICHU_STAGING_SP = _SHINY_RAICHU["staging"]
SHINY_RAICHU_COMMITTED_SP = _SHINY_RAICHU["committed"]
SHINY_RAICHU_RECOVERED_SP = _SHINY_RAICHU["recovered"]
SHINY_RAICHU_HIT_SP = _SHINY_RAICHU["hit"]
SHINY_RAICHU_COMPACTED_SP = _SHINY_RAICHU["compacted"]

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
# Pokemon species registry — maps species key to sprites
# ============================================================

POKEMON_SPECIES = {
    "pichu": {
        "name": "Pichu",
        "idle_frames": PICHU_IDLE_FRAMES,
        "thinking": PICHU_THINKING_SP,
        "staging": PICHU_STAGING_SP,
        "committed": PICHU_COMMITTED_SP,
        "recovered": PICHU_RECOVERED_SP,
        "hit": PICHU_HIT_SP,
        "compacted": PICHU_COMPACTED_SP,
        "shiny_idle_frames": SHINY_PICHU_IDLE_FRAMES,
        "shiny_thinking": SHINY_PICHU_THINKING_SP,
        "shiny_staging": SHINY_PICHU_STAGING_SP,
        "shiny_committed": SHINY_PICHU_COMMITTED_SP,
        "shiny_recovered": SHINY_PICHU_RECOVERED_SP,
        "shiny_hit": SHINY_PICHU_HIT_SP,
        "shiny_compacted": SHINY_PICHU_COMPACTED_SP,
    },
    "pikachu": {
        "name": "Pikachu",
        "idle_frames": IDLE_FRAMES,
        "thinking": THINKING_SP,
        "staging": STAGING_SP,
        "committed": COMMITTED_SP,
        "recovered": RECOVERED_SP,
        "hit": HIT_SP,
        "compacted": COMPACTED_SP,
        "shiny_idle_frames": SHINY_IDLE_FRAMES,
        "shiny_thinking": SHINY_THINKING_SP,
        "shiny_staging": SHINY_STAGING_SP,
        "shiny_committed": SHINY_COMMITTED_SP,
        "shiny_recovered": SHINY_RECOVERED_SP,
        "shiny_hit": SHINY_HIT_SP,
        "shiny_compacted": SHINY_COMPACTED_SP,
    },
    "raichu": {
        "name": "Raichu",
        "idle_frames": RAICHU_IDLE_FRAMES,
        "thinking": RAICHU_THINKING_SP,
        "staging": RAICHU_STAGING_SP,
        "committed": RAICHU_COMMITTED_SP,
        "recovered": RAICHU_RECOVERED_SP,
        "hit": RAICHU_HIT_SP,
        "compacted": RAICHU_COMPACTED_SP,
        "shiny_idle_frames": SHINY_RAICHU_IDLE_FRAMES,
        "shiny_thinking": SHINY_RAICHU_THINKING_SP,
        "shiny_staging": SHINY_RAICHU_STAGING_SP,
        "shiny_committed": SHINY_RAICHU_COMMITTED_SP,
        "shiny_recovered": SHINY_RAICHU_RECOVERED_SP,
        "shiny_hit": SHINY_RAICHU_HIT_SP,
        "shiny_compacted": SHINY_RAICHU_COMPACTED_SP,
    },
}


def get_species_sprites(species="pikachu", shiny=False):
    """Get sprite set for a species. Falls back to Pikachu."""
    spec = POKEMON_SPECIES.get(species, POKEMON_SPECIES["pikachu"])
    prefix = "shiny_" if shiny else ""
    return {
        "idle_frames": spec.get(f"{prefix}idle_frames", spec["idle_frames"]),
        "thinking": spec.get(f"{prefix}thinking", spec["thinking"]),
        "staging": spec.get(f"{prefix}staging", spec["staging"]),
        "committed": spec.get(f"{prefix}committed", spec["committed"]),
        "recovered": spec.get(f"{prefix}recovered", spec["recovered"]),
        "hit": spec.get(f"{prefix}hit", spec["hit"]),
        "compacted": spec.get(f"{prefix}compacted", spec["compacted"]),
    }


# ============================================================
# Backwards-compat aliases (used by demo.py / animator.py)
# ============================================================

THINK_FRAMES = IDLE_FRAMES
COMPACT_FRAME = COMPACTED_SP
