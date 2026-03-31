"""Delta detection — track what changed between statusline calls.

Persists a minimal state snapshot to /tmp/pikabar-state-{hash} and
computes deltas + inferred events on each call. Pure functions except
for file I/O (load_state / save_state).
"""

import hashlib
import json
import os
import random
import time
from datetime import date
from typing import Dict, List, Optional, Tuple

# --- File paths ---
STATE_DIR = "/tmp"
STATE_PREFIX = "pikabar-state"


def _workspace_id(cwd: str) -> str:
    """Short hash of cwd for per-workspace isolation."""
    return hashlib.md5(cwd.encode()).hexdigest()[:8]


def _state_path(cwd: str = "") -> str:
    """Return state file path, scoped to workspace if cwd given."""
    if cwd:
        return os.path.join(STATE_DIR, f"{STATE_PREFIX}-{_workspace_id(cwd)}")
    return os.path.join(STATE_DIR, STATE_PREFIX)


def load_state(cwd: str = "") -> Optional[dict]:
    """Load previous state snapshot. Returns None if missing/corrupt."""
    path = _state_path(cwd)
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def save_state(snapshot: dict, cwd: str = "") -> None:
    """Persist current state snapshot. Atomic write, best-effort."""
    path = _state_path(cwd)
    try:
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(snapshot, f)
        os.replace(tmp, path)  # atomic on POSIX
    except OSError:
        pass


def make_snapshot(hp_pct, hp_window, context_pct,
                  cost_usd, duration_ms, branch, staged, modified):
    """Build a state snapshot dict from current call data."""
    return {
        "ts": time.time(),
        "hp": hp_pct,
        "hw": hp_window,
        "ctx": context_pct,
        "cost": cost_usd,
        "dur": duration_ms,
        "br": branch,
        "stg": staged,
        "mod": modified,
    }


# ============================================================
# Shiny Pikachu (Feature 3) — 1/500 chance per session start
# ============================================================

SHINY_CHANCE = 1 / 1024  # 2^10, Nintendo-style power-of-2


def check_shiny(prev_state):
    """Roll for shiny on session start. Persists across calls within a session.

    Returns True if shiny. If prev_state has shiny=True, propagate it.
    If no prev_state (new session), roll 1/500.
    """
    if prev_state is not None:
        return prev_state.get("shiny", False)
    return random.random() < SHINY_CHANCE


# ============================================================
# Streak counter (Feature 5) — consecutive active days
# ============================================================

def compute_streak(prev_state):
    """Compute streak_days from previous state.

    Returns (streak_days, last_active_date_str).
    A streak continues if last_active was today or yesterday.
    """
    today = date.today().isoformat()

    if prev_state is None:
        return 1, today

    last_date_str = prev_state.get("last_active")
    prev_streak = prev_state.get("streak", 0)

    if not last_date_str:
        return 1, today

    if last_date_str == today:
        # Same day — keep current streak
        return max(prev_streak, 1), today

    try:
        last_date = date.fromisoformat(last_date_str)
        delta_days = (date.today() - last_date).days
        if delta_days == 1:
            # Consecutive day — increment
            return prev_streak + 1, today
        else:
            # Streak broken
            return 1, today
    except (ValueError, TypeError):
        return 1, today


def _safe_sub(a, b):
    """Subtract two optional numbers. Returns None if either is None."""
    if a is None or b is None:
        return None
    return a - b


# ============================================================
# Team System (Feature 7) — Each model gets a different Pokemon
# ============================================================

# Default team - 6 Pokemon slots
# Each slot has a starter species that can evolve independently
DEFAULT_TEAM = ["pikachu", "pikachu", "pichu", "raichu", "pichu", "raichu"]

# Model family to team slot mapping
MODEL_TEAM_SLOTS = {
    "opus":   0,   # Opus → slot 0 (Pikachu)
    "sonnet": 1,   # Sonnet → slot 1 (Pikachu)
    "haiku":  2,   # Haiku → slot 2 (Pichu)
    "claude": 3,   # Other Claude → slot 3 (Raichu)
}

# Per-slot evolution state (tracks each Pokemon on the team independently)
def get_team_slot_index(model_id):
    """Get team slot index for a model."""
    model_lower = model_id.lower()
    for key, slot in MODEL_TEAM_SLOTS.items():
        if key in model_lower:
            return slot
    return 3  # Default to slot 3


def init_team_state():
    """Initialize team state with default team and per-slot evolution stages."""
    team_state = {}
    for i, species in enumerate(DEFAULT_TEAM):
        team_state[i] = {
            "species": species,
            "evolution_stage": 0,
            "cost_accumulated": 0.0,  # Track cost per Pokemon
        }
    return team_state


def get_pokemon_for_model(model_id, team_state):
    """Get the current Pokemon species for a model from team state.

    Args:
        model_id: Model ID string
        team_state: Dict of team slot → Pokemon state

    Returns:
        Tuple of (species_key, evolution_stage, slot_index)
    """
    slot = get_team_slot_index(model_id)
    if team_state is None or slot not in team_state:
        # Initialize team state
        return DEFAULT_TEAM[slot], 0, slot

    slot_state = team_state[slot]
    # Apply evolution stage
    stage = slot_state.get("evolution_stage", 0)
    species = slot_state.get("species", DEFAULT_TEAM[slot])

    EVOLUTION_STAGES = ["pichu", "pikachu", "raichu"]
    if stage > 0 and stage < len(EVOLUTION_STAGES):
        species = EVOLUTION_STAGES[stage]

    return species, stage, slot


# ============================================================
# Model → Species mapping (Feature 2)
# ============================================================

MODEL_SPECIES_MAP = {
    "opus":   "pikachu",
    "sonnet": "pikachu",
    "haiku":  "pichu",
}

EVOLUTION_STAGES = ["pichu", "pikachu", "raichu"]

EVOLUTION_THRESHOLDS = {
    "pichu":   {"cost": 1.0},   # ~1 session worth of usage
    "pikachu": {"cost": 10.0},  # ~10 sessions worth of usage
}


def get_species_for_model(model_id, evolution_stage=0):
    """Derive base species from model_id, then apply evolution stage.

    Evolution stage overrides the base species if the Pokemon has evolved
    from its starter form (e.g., Haiku starts as Pichu but can evolve).

    Args:
        model_id: Full model ID string (e.g., "claude-opus-4-6")
        evolution_stage: 0=pichu, 1=pikachu, 2=raichu (or -1=unknown)

    Returns:
        Species key string ("pichu", "pikachu", or "raichu")
    """
    # Determine base species from model
    base = "pikachu"  # default
    model_lower = model_id.lower()
    for key, species in MODEL_SPECIES_MAP.items():
        if key in model_lower:
            base = species
            break

    # Apply evolution stage
    if evolution_stage > 0 and evolution_stage < len(EVOLUTION_STAGES):
        return EVOLUTION_STAGES[evolution_stage]
    return base


def check_evolution(prev_state, cur_snapshot):
    """Check if current Pokemon should evolve.

    Evolution happens when:
    - Pichu reaches $1.00 cumulative cost
    - Pikachu reaches $10.00 cumulative cost

    Args:
        prev_state: Previous state snapshot (None on session start)
        cur_snapshot: Current snapshot being built

    Returns:
        Tuple of (evolved: bool, new_stage: int)
    """
    # Get current stage (0=pichu, 1=pikachu, 2=raichu)
    stage = cur_snapshot.get("evolution_stage", 0)
    species = cur_snapshot.get("species", "pikachu")

    # Check if there's a next evolution available
    threshold = EVOLUTION_THRESHOLDS.get(species)
    if threshold is None:
        # Already at final form (Raichu)
        return False, stage

    # Check all threshold conditions
    for key, required in threshold.items():
        if cur_snapshot.get(key, 0) < required:
            return False, stage

    # All conditions met — evolve!
    new_stage = stage + 1
    return True, new_stage


def check_team_evolution(slot_state):
    """Check if a team Pokemon should evolve.

    Args:
        slot_state: Dict with species, evolution_stage, cost_accumulated

    Returns:
        Tuple of (evolved: bool, new_stage: int)
    """
    species = slot_state.get("species", "pikachu")
    stage = slot_state.get("evolution_stage", 0)
    cost = slot_state.get("cost_accumulated", 0.0)

    threshold = EVOLUTION_THRESHOLDS.get(species)
    if threshold is None:
        return False, stage

    for key, required in threshold.items():
        if key == "cost" and cost < required:
            return False, stage

    return True, stage + 1


def compute_deltas(prev, cur):
    """Compute deltas between previous and current snapshots.

    Returns dict with: time_delta, hp_delta, context_delta,
    cost_delta, duration_delta, branch_changed, staged_delta, modified_delta.
    """
    if prev is None:
        return {
            "time_delta": 0.0,
            "hp_delta": None,
            "context_delta": None,
            "cost_delta": 0.0,
            "duration_delta": 0,
            "branch_changed": False,
            "staged_delta": 0,
            "modified_delta": 0,
        }
    return {
        "time_delta": max(0, cur["ts"] - prev.get("ts", cur["ts"])),
        "hp_delta": _safe_sub(cur.get("hp"), prev.get("hp")),
        "context_delta": _safe_sub(cur.get("ctx"), prev.get("ctx")),
        "cost_delta": max(0, (cur.get("cost", 0) or 0) - (prev.get("cost", 0) or 0)),
        "duration_delta": max(0, (cur.get("dur", 0) or 0) - (prev.get("dur", 0) or 0)),
        "branch_changed": cur.get("br", "") != prev.get("br", ""),
        "staged_delta": (cur.get("stg", 0) or 0) - (prev.get("stg", 0) or 0),
        "modified_delta": (cur.get("mod", 0) or 0) - (prev.get("mod", 0) or 0),
    }


# ============================================================
# Event inference — map deltas to named events
# ============================================================

# Thresholds (tunable)
HP_CRITICAL_THRESHOLD = 15
HP_DROP_LARGE = -10
HP_RECOVERED_MIN = 20
CONTEXT_COMPACTION_DROP = -20
COST_SPIKE = 0.10
DURATION_LONG_MS = 8000
IDLE_TIMEOUT = 300  # 5 minutes


def infer_events(deltas, cur, prev):
    """Map deltas to a list of event names.

    Args:
        deltas: Output of compute_deltas().
        cur: Current snapshot.
        prev: Previous snapshot (None on first call).

    Returns:
        List of event name strings.
    """
    events = []

    if prev is None:
        events.append("session_start")
        return events

    hd = deltas["hp_delta"]
    cd = deltas["context_delta"]
    td = deltas["time_delta"]
    dd = deltas["duration_delta"]

    # Time-based
    if td > IDLE_TIMEOUT:
        events.append("long_idle")

    # Context compaction: large negative jump
    if cd is not None and cd < CONTEXT_COMPACTION_DROP:
        events.append("compacted")

    # HP events
    if hd is not None:
        if hd <= HP_DROP_LARGE:
            events.append("heavy_burst")
        if hd >= HP_RECOVERED_MIN:
            events.append("hp_recovered")

    # HP threshold crossing
    prev_hp = prev.get("hp")
    cur_hp = cur.get("hp")
    if prev_hp is not None and cur_hp is not None:
        if cur_hp < HP_CRITICAL_THRESHOLD <= prev_hp:
            events.append("hp_critical")

    # Cost spike
    if deltas["cost_delta"] > COST_SPIKE:
        events.append("big_operation")

    # Long tool run (duration delta proxy)
    if dd > DURATION_LONG_MS:
        events.append("long_operation")

    # Git activity — staged went from >0 to 0 = committed
    prev_stg = prev.get("stg", 0) or 0
    cur_stg = cur.get("stg", 0) or 0
    if prev_stg > 0 and cur_stg == 0:
        events.append("committed")
    elif deltas["staged_delta"] > 0 or deltas["modified_delta"] > 0:
        events.append("code_written")

    if deltas["branch_changed"]:
        events.append("branch_switch")

    return events


# ============================================================
# Reaction selection — priority-ordered mapping
# ============================================================

# Priority order (highest first): faint > hit > compacted > thinking > recovered > committed > staging > idle
REACTION_PRIORITY = [
    ("faint",     lambda e, c: c.get("hp") is not None and c["hp"] < HP_CRITICAL_THRESHOLD),
    ("hit",       lambda e, c: "heavy_burst" in e),
    ("compacted", lambda e, c: "compacted" in e),
    ("thinking",  lambda e, c: "long_operation" in e),
    ("recovered", lambda e, c: "hp_recovered" in e),
    ("committed", lambda e, c: "committed" in e),
    ("staging",   lambda e, c: "code_written" in e or "big_operation" in e),
    ("idle",      lambda e, c: True),
]


def pick_reaction(events, cur):
    """Select highest-priority reaction based on events and current state.

    Returns reaction name string.
    """
    for name, test in REACTION_PRIORITY:
        if test(events, cur):
            return name
    return "idle"
