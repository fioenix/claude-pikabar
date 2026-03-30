"""Tests for pikabar.delta — state persistence, delta computation, reaction selection."""

from pikabar.delta import (
    make_snapshot, compute_deltas, infer_events, pick_reaction,
    HP_CRITICAL_THRESHOLD, HP_DROP_LARGE,
)


# --- make_snapshot ---

def test_make_snapshot_basic():
    snap = make_snapshot(
        hp_pct=72, hp_window="5h", context_pct=25,
        cost_usd=0.42, duration_ms=192000,
        branch="main", staged=2, modified=1,
    )
    assert snap["hp"] == 72
    assert snap["hw"] == "5h"
    assert snap["ctx"] == 25
    assert snap["cost"] == 0.42
    assert snap["br"] == "main"
    assert snap["stg"] == 2
    assert "ts" in snap


def test_make_snapshot_none_values():
    snap = make_snapshot(None, None, None, 0, 0, "", 0, 0)
    assert snap["hp"] is None
    assert snap["ctx"] is None


# --- compute_deltas ---

def test_deltas_no_previous():
    cur = make_snapshot(72, "5h", 25, 0.42, 192000, "main", 2, 1)
    deltas = compute_deltas(None, cur)
    # No previous state = no computable deltas (None)
    assert deltas["hp_delta"] is None
    assert deltas["context_delta"] is None


def test_deltas_hp_change():
    prev = make_snapshot(80, "5h", 20, 0.10, 60000, "main", 0, 0)
    cur = make_snapshot(60, "5h", 30, 0.42, 120000, "main", 2, 1)
    deltas = compute_deltas(prev, cur)
    assert deltas["hp_delta"] == -20
    assert deltas["context_delta"] == 10
    assert abs(deltas["cost_delta"] - 0.32) < 0.001  # float comparison
    assert deltas["staged_delta"] == 2


def test_deltas_branch_changed():
    prev = make_snapshot(80, "5h", 20, 0.10, 60000, "main", 0, 0)
    cur = make_snapshot(80, "5h", 20, 0.10, 60000, "feature", 0, 0)
    deltas = compute_deltas(prev, cur)
    assert deltas["branch_changed"] is True


# --- infer_events ---

def test_infer_hp_recovered():
    prev = make_snapshot(30, "5h", 20, 0.10, 60000, "main", 0, 0)
    cur = make_snapshot(80, "5h", 20, 0.10, 60000, "main", 0, 0)
    deltas = compute_deltas(prev, cur)
    events = infer_events(deltas, cur, prev)
    assert "hp_recovered" in events


def test_infer_committed():
    prev = make_snapshot(72, "5h", 20, 0.10, 60000, "main", 3, 0)
    cur = make_snapshot(72, "5h", 20, 0.10, 60000, "main", 0, 0)
    deltas = compute_deltas(prev, cur)
    events = infer_events(deltas, cur, prev)
    assert "committed" in events


# --- pick_reaction ---

def test_pick_faint_when_critical():
    cur = make_snapshot(5, "5h", 20, 0.10, 60000, "main", 0, 0)
    reaction = pick_reaction([], cur)
    assert reaction == "faint"


def test_pick_idle_by_default():
    cur = make_snapshot(80, "5h", 20, 0.10, 60000, "main", 0, 0)
    reaction = pick_reaction([], cur)
    assert reaction == "idle"


def test_pick_hit_on_heavy_burst():
    cur = make_snapshot(40, "5h", 50, 0.50, 60000, "main", 0, 0)
    reaction = pick_reaction(["heavy_burst"], cur)
    assert reaction == "hit"


def test_pick_compacted():
    cur = make_snapshot(72, "5h", 50, 0.10, 60000, "main", 0, 0)
    reaction = pick_reaction(["compacted"], cur)
    assert reaction == "compacted"


def test_pick_priority_faint_over_hit():
    """Faint has higher priority than hit."""
    cur = make_snapshot(5, "5h", 20, 0.10, 60000, "main", 0, 0)
    reaction = pick_reaction(["heavy_burst"], cur)
    assert reaction == "faint"
