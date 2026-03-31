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
