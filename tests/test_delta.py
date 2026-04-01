"""Tests for pikabar.delta — state persistence, delta computation, reaction selection."""

from pikabar.delta import (
    make_snapshot, compute_deltas, infer_events, pick_reaction,
    HP_CRITICAL_THRESHOLD, HP_DROP_LARGE,
    check_shiny, init_team_state, get_pokemon_state,
    get_species_from_stage, check_evolution,
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


# --- Shiny per-session tests ---

def test_shiny_new_session():
    """New session without prev_state should roll."""
    is_shiny, shiny_map = check_shiny(None, session_id="session-a")
    assert isinstance(is_shiny, bool)
    assert "session-a" in shiny_map


def test_shiny_persist_across_calls():
    """Shiny flag persists within same session."""
    prev_state = {"shiny_map": {"session-a": True}}
    is_shiny, shiny_map = check_shiny(prev_state, session_id="session-a")
    assert is_shiny is True
    assert shiny_map["session-a"] is True


def test_shiny_switch_session():
    """Switching sessions preserves individual shiny flags."""
    prev_state = {"shiny_map": {"session-a": True, "session-b": False}}

    is_shiny_a, _ = check_shiny(prev_state, session_id="session-a")
    is_shiny_b, _ = check_shiny(prev_state, session_id="session-b")

    assert is_shiny_a is True
    assert is_shiny_b is False


def test_shiny_migration():
    """Old single-bool shiny migrates to shiny_map."""
    prev_state = {"shiny": True, "session_id": "old-session"}
    is_shiny, shiny_map = check_shiny(prev_state, session_id="old-session")
    assert is_shiny is True
    assert shiny_map.get("old-session") is True


# --- Team and Evolution tests ---

def test_init_team_state():
    """Team state initializes with single slot."""
    team = init_team_state()
    assert "0" in team
    assert team["0"]["species"] == "pikachu"
    assert team["0"]["evolution_stage"] == 1


def test_get_pokemon_state():
    """Get Pokemon state from team."""
    team = init_team_state()
    state = get_pokemon_state(team)
    assert state["species"] == "pikachu"
    assert state["evolution_stage"] == 1


def test_get_pokemon_state_default():
    """Get Pokemon state returns defaults if missing."""
    state = get_pokemon_state(None)
    assert state["species"] == "pikachu"
    assert state["evolution_stage"] == 1


def test_get_species_from_stage():
    """Species derived from evolution stage."""
    assert get_species_from_stage(0) == "pichu"
    assert get_species_from_stage(1) == "pikachu"
    assert get_species_from_stage(2) == "raichu"


def test_check_evolution_below_threshold():
    """No evolution below cost threshold."""
    slot = {"species": "pikachu", "evolution_stage": 1, "cost_accumulated": 5.0}
    evolved, _ = check_evolution(slot)
    assert evolved is False


def test_check_evolution_at_threshold():
    """Evolution triggers at cost threshold."""
    slot = {"species": "pikachu", "evolution_stage": 1, "cost_accumulated": 10.0}
    evolved, new_stage = check_evolution(slot)
    assert evolved is True
    assert new_stage == 2  # Raichu


def test_check_evolution_already_final():
    """No evolution for final form."""
    slot = {"species": "raichu", "evolution_stage": 2, "cost_accumulated": 100.0}
    evolved, _ = check_evolution(slot)
    assert evolved is False
