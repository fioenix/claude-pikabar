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
from pikabar.sprites import (
    IDLE_FRAMES, THINKING_SP, STAGING_SP, COMMITTED_SP,
    RECOVERED_SP, HIT_SP, COMPACTED_SP, BALL_FRAMES,
)
from pikabar.info_panel import decorate
from pikabar.delta import (
    load_state, save_state, make_snapshot,
    compute_deltas, infer_events, pick_reaction,
)

# --- Temp file paths ---
FRAME_FILE = "/tmp/pikabar-frame"
GIT_CACHE_FILE = "/tmp/pikabar-git-cache"
GIT_CACHE_MAX_AGE = 5  # seconds

# --- Reaction → sprite mapping ---
REACTION_SPRITES = {
    "idle":      None,  # uses IDLE_FRAMES[frame % N]
    "thinking":  THINKING_SP,
    "staging":   STAGING_SP,
    "committed": COMMITTED_SP,
    "recovered": RECOVERED_SP,
    "hit":       HIT_SP,
    "compacted": COMPACTED_SP,
    "faint":     None,  # uses BALL_FRAMES[frame % N]
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


def get_sprite(reaction, frame):
    """Select the appropriate sprite grid for a reaction."""
    if reaction == "faint":
        return BALL_FRAMES[frame % len(BALL_FRAMES)]
    if reaction == "idle":
        return IDLE_FRAMES[frame % len(IDLE_FRAMES)]
    return REACTION_SPRITES.get(reaction, IDLE_FRAMES[0])


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
    save_state(snapshot, cwd)

    # --- Pick reaction ---
    reaction = pick_reaction(events, snapshot)

    # --- Build session dict for decorators ---
    # PP = context remaining (inverted)
    pp_pct = (100 - context_pct) if context_pct is not None else None

    session = {
        "model_id": model_id,
        "model_name": model_name,
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
        "_tick": frame,
    }

    # --- Select sprite and decorate ---
    sprite_grid = get_sprite(reaction, frame)
    sprite_lines = grid_to_lines(sprite_grid)
    output_lines = decorate(reaction, sprite_lines, frame, session=session)

    # Prefix each line with \033[0m to prevent Ink.js whitespace trimming
    return "\n".join(f"\033[0m{line}" for line in output_lines)


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        data = {}

    print(render_statusline(data))


if __name__ == "__main__":
    main()
