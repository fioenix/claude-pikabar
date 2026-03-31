#!/usr/bin/env python3
"""pikabar statusline — Claude Code integration script.

Reads JSON session data from stdin (piped by Claude Code),
computes deltas from previous call to infer reactions,
renders Pikachu pixel art + Pokemon-style info panel,
and prints multi-line output to stdout.

Usage in ~/.claude/settings.json:
{
    "statusLine": {
        "type": "command",
        "command": "python3 /path/to/pikabar/pikabar/statusline.py"
    }
}

Claude Code calls this script on each state update (debounced ~300ms).
State persisted in /tmp/pikabar-state-{hash} for delta detection.
Git info cached in /tmp/pikabar-git-cache for performance.
"""

import json
import os
import subprocess
import sys
import time

# Ensure pikabar package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pikabar.renderer import grid_to_lines
from pikabar.info_panel import decorate
from pikabar.delta import (
    load_state, save_state, make_snapshot,
    compute_deltas, infer_events, pick_reaction,
    check_shiny, compute_streak,
    get_species_for_model, check_evolution, check_team_evolution,
    EVOLUTION_STAGES, DEFAULT_TEAM, init_team_state, get_pokemon_for_model,
    get_team_slot_index,
)
from pikabar.sprites import (
    POKEMON_SPECIES, get_species_sprites,
    BALL_FRAMES,
)

# --- Temp file paths ---
FRAME_FILE = "/tmp/pikabar-frame"
GIT_CACHE_FILE = "/tmp/pikabar-git-cache"
GIT_CACHE_MAX_AGE = 5  # seconds

# --- Reaction → sprite key mapping (species-agnostic) ---
REACTION_KEYS = {
    "idle":      "idle_frames",
    "thinking":  "thinking",
    "staging":   "staging",
    "committed": "committed",
    "recovered": "recovered",
    "hit":       "hit",
    "compacted": "compacted",
    "faint":     "faint",  # special: uses BALL_FRAMES
}


def read_frame():
    """Read and increment frame counter from temp file."""
    try:
        with open(FRAME_FILE) as f:
            frame = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        frame = 0
    with open(FRAME_FILE, "w") as f:
        f.write(str(frame + 1))
    return frame


def get_git_info(cwd):
    """Get git branch and file counts, with caching."""
    try:
        if os.path.exists(GIT_CACHE_FILE):
            age = time.time() - os.path.getmtime(GIT_CACHE_FILE)
            if age < GIT_CACHE_MAX_AGE:
                with open(GIT_CACHE_FILE) as f:
                    parts = f.read().strip().split("|")
                    if len(parts) == 3:
                        return parts[0], int(parts[1] or 0), int(parts[2] or 0)
    except (OSError, ValueError):
        pass

    try:
        subprocess.check_output(
            ["git", "rev-parse", "--git-dir"],
            cwd=cwd, stderr=subprocess.DEVNULL
        )
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=cwd, text=True, stderr=subprocess.DEVNULL
        ).strip()
        staged_out = subprocess.check_output(
            ["git", "diff", "--cached", "--numstat"],
            cwd=cwd, text=True, stderr=subprocess.DEVNULL
        ).strip()
        modified_out = subprocess.check_output(
            ["git", "diff", "--numstat"],
            cwd=cwd, text=True, stderr=subprocess.DEVNULL
        ).strip()
        staged = len(staged_out.split("\n")) if staged_out else 0
        modified = len(modified_out.split("\n")) if modified_out else 0

        with open(GIT_CACHE_FILE, "w") as f:
            f.write(f"{branch}|{staged}|{modified}")
        return branch, staged, modified
    except (subprocess.CalledProcessError, FileNotFoundError):
        with open(GIT_CACHE_FILE, "w") as f:
            f.write("||")
        return "", 0, 0


def compute_hp(data):
    """Compute HP% = 100 - max(5h_used, 7d_used)."""
    rate = data.get("rate_limits")
    if not rate:
        return None, None

    five_h = rate.get("five_hour", {}).get("used_percentage")
    seven_d = rate.get("seven_day", {}).get("used_percentage")

    if five_h is None and seven_d is None:
        return None, None

    if five_h is not None and seven_d is not None:
        if five_h >= seven_d:
            return max(0, int(100 - five_h)), "5h"
        else:
            return max(0, int(100 - seven_d)), "7d"
    elif five_h is not None:
        return max(0, int(100 - five_h)), "5h"
    else:
        return max(0, int(100 - seven_d)), "7d"


def get_sprite(reaction, frame, shiny=False, species="pikachu"):
    """Select the appropriate sprite grid for a reaction and species.

    Args:
        reaction: Reaction name (idle, thinking, staging, committed, etc.)
        frame: Frame counter for idle animation cycling
        shiny: Whether to use shiny variant
        species: Pokemon species key (pichu, pikachu, raichu)

    Returns:
        6x15 pixel grid (list of lists)
    """
    if reaction == "faint":
        return BALL_FRAMES[frame % len(BALL_FRAMES)]

    sprites = get_species_sprites(species, shiny=shiny)
    key = REACTION_KEYS.get(reaction, "idle_frames")

    if key == "idle_frames":
        frames = sprites["idle_frames"]
        return frames[frame % len(frames)]
    return sprites.get(key, sprites["idle_frames"][0])


def render_statusline(data):
    """Render the complete pikabar statusline output."""
    frame = read_frame()

    # --- Extract data from Claude Code JSON ---
    model_id = data.get("model", {}).get("id", "")
    display_name = data.get("model", {}).get("display_name", "Claude")
    model_name = display_name.split()[0] if display_name else "Claude"

    cwd = data.get("workspace", {}).get("current_dir", data.get("cwd", ""))
    branch, staged, modified = get_git_info(cwd) if cwd else ("", 0, 0)

    cost_usd = data.get("cost", {}).get("total_cost_usd", 0) or 0
    duration_ms = data.get("cost", {}).get("total_duration_ms", 0) or 0

    hp_pct, hp_window = compute_hp(data)
    context_pct = data.get("context_window", {}).get("used_percentage")

    # --- Delta detection ---
    snapshot = make_snapshot(
        hp_pct, hp_window, context_pct,
        cost_usd, duration_ms, branch, staged, modified,
    )
    prev_state = load_state(cwd)
    deltas = compute_deltas(prev_state, snapshot)
    events = infer_events(deltas, snapshot, prev_state)

    # --- Feature 3: Shiny (1/1024 per session) ---
    is_shiny = check_shiny(prev_state)
    snapshot["shiny"] = is_shiny

    # --- Feature 5: Streak counter (consecutive active days) ---
    streak_days, last_active = compute_streak(prev_state)
    snapshot["streak"] = streak_days
    snapshot["last_active"] = last_active

    # --- Feature 7: Team System ---
    # Initialize or load team state
    if prev_state and "team" in prev_state:
        team_state = prev_state["team"]
    else:
        team_state = init_team_state()

    # Get current team slot for this model
    slot_index = get_team_slot_index(model_id)
    slot_key = str(slot_index)  # Use string key for JSON compatibility

    slot_state = team_state.get(slot_key, {
        "species": DEFAULT_TEAM[slot_index],
        "evolution_stage": 0,
        "cost_accumulated": 0.0,
    })

    # Get Pokemon species with evolution applied
    base_species, evolution_stage, _ = get_pokemon_for_model(model_id, team_state)

    # Accumulate cost for this Pokemon
    # Use existing cost from team state, add current session cost
    prev_slot_cost = slot_state.get("cost_accumulated", 0.0)
    new_cost = prev_slot_cost + cost_usd
    slot_state["cost_accumulated"] = new_cost

    # Check for evolution for this team slot
    just_evolved = False
    evolved, new_stage = check_team_evolution(slot_state)
    if evolved:
        evolution_stage = new_stage
        base_species = EVOLUTION_STAGES[new_stage]
        slot_state["evolution_stage"] = evolution_stage
        slot_state["species"] = base_species
        just_evolved = True

    # Update team state with string key
    team_state[slot_key] = slot_state

    # Update snapshot and team state
    snapshot["team"] = team_state
    snapshot["species"] = base_species
    snapshot["evolution_stage"] = evolution_stage
    snapshot["team_slot"] = slot_index

    # Get final species for display
    species = base_species
    pokemon_name = POKEMON_SPECIES[species]["name"]

    save_state(snapshot, cwd)

    # --- Pick reaction ---
    reaction = pick_reaction(events, snapshot)

    # --- Build session dict for decorators ---
    # PP = context remaining (inverted)
    pp_pct = (100 - context_pct) if context_pct is not None else None

    session = {
        "model_id": model_id,
        "model_name": model_name,
        "species": species,
        "pokemon_name": pokemon_name,
        "evolution_stage": evolution_stage,
        "just_evolved": just_evolved,
        "hp_pct": hp_pct,
        "hp_window": hp_window,
        "pp_pct": pp_pct,
        "cost_usd": cost_usd,
        "branch": branch,
        "staged": staged,
        "modified": modified,
        "events": events,
        "deltas": deltas,
        "reaction": reaction,
        "shiny": is_shiny,
        "streak_days": streak_days,
        "_tick": frame,
    }

    # --- Select sprite and decorate ---
    sprite_grid = get_sprite(reaction, frame, shiny=is_shiny, species=species)
    sprite_lines = grid_to_lines(sprite_grid)
    output_lines = decorate(reaction, sprite_lines, frame, session=session)

    # Prefix each line with \033[0m to prevent Ink.js whitespace trimming
    return "\n".join(f"\033[0m{line}" for line in output_lines)


def main():
    if sys.stdin.isatty():
        print("pikabar: no input on stdin — nothing to render.")
        print("This script is called by Claude Code, not directly.")
        print()
        print("  Quick start:  pikabar install")
        print("  Manual test:  echo '{}' | python3 pikabar/statusline.py")
        print("  Demo mode:    python3 demo.py")
        sys.exit(0)

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        data = {}

    print(render_statusline(data))


if __name__ == "__main__":
    main()
