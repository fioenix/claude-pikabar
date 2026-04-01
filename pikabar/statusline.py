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
    SHINY_IDLE_FRAMES, SHINY_THINKING_SP, SHINY_STAGING_SP,
    SHINY_COMMITTED_SP, SHINY_RECOVERED_SP, SHINY_HIT_SP,
    SHINY_COMPACTED_SP,
)
from pikabar.info_panel import decorate
from pikabar.delta import (
    load_state, save_state, make_snapshot,
    compute_deltas, infer_events, pick_reaction,
    check_shiny, compute_streak,
)

# --- Temp file paths ---
GIT_CACHE_FILE = "/tmp/pikabar-git-cache"
GIT_CACHE_MAX_AGE = 5  # seconds

# --- Time-based frame rates (fps per reaction) ---
REACTION_FPS = {
    "idle":      2.0,
    "thinking":  2.0,
    "staging":   1.0,  # single frame, fps irrelevant
    "committed": 1.0,
    "recovered": 1.0,
    "hit":       1.0,
    "compacted": 1.5,
    "faint":     6.0,
}

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

SHINY_REACTION_SPRITES = {
    "idle":      None,  # uses SHINY_IDLE_FRAMES
    "thinking":  SHINY_THINKING_SP,
    "staging":   SHINY_STAGING_SP,
    "committed": SHINY_COMMITTED_SP,
    "recovered": SHINY_RECOVERED_SP,
    "hit":       SHINY_HIT_SP,
    "compacted": SHINY_COMPACTED_SP,
    "faint":     None,  # pokeball is pokeball, shiny or not
}


def get_time_frame(reaction, num_frames):
    """Select frame index based on wall-clock time and reaction FPS.

    Returns int in [0, num_frames). Each statusline call renders the
    frame that is 'correct' for the current moment, so animation
    progresses even if call intervals are irregular.
    """
    if num_frames <= 1:
        return 0
    fps = REACTION_FPS.get(reaction, 2.0)
    return int(time.time() * fps) % num_frames


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


def get_sprite(reaction, shiny=False):
    """Select the appropriate sprite grid for a reaction using time-based frame."""
    if reaction == "faint":
        frame = get_time_frame("faint", len(BALL_FRAMES))
        return BALL_FRAMES[frame]
    if shiny:
        if reaction == "idle":
            frame = get_time_frame("idle", len(SHINY_IDLE_FRAMES))
            return SHINY_IDLE_FRAMES[frame]
        return SHINY_REACTION_SPRITES.get(reaction, SHINY_IDLE_FRAMES[0])
    if reaction == "idle":
        frame = get_time_frame("idle", len(IDLE_FRAMES))
        return IDLE_FRAMES[frame]
    return REACTION_SPRITES.get(reaction, IDLE_FRAMES[0])


def render_statusline(data):
    """Render the complete pikabar statusline output."""
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

    # Agent / worktree fields (absent in normal sessions)
    agent_name = data.get("agent", {}).get("name") or ""
    worktree_name = data.get("worktree", {}).get("name") or ""
    worktree_branch = data.get("worktree", {}).get("branch") or ""

    # --- Delta detection ---
    snapshot = make_snapshot(
        hp_pct, hp_window, context_pct,
        cost_usd, duration_ms, branch, staged, modified,
    )
    prev_state = load_state(cwd)
    deltas = compute_deltas(prev_state, snapshot)
    events = infer_events(deltas, snapshot, prev_state)

    # --- Feature 3: Shiny Pikachu (1/1024 per session) ---
    session_id = data.get("session_id", "")
    is_shiny, shiny_map = check_shiny(prev_state, session_id)
    snapshot["shiny_map"] = shiny_map
    snapshot["session_id"] = session_id

    # --- Feature 5: Streak counter (consecutive active days) ---
    streak_days, last_active = compute_streak(prev_state)
    snapshot["streak"] = streak_days
    snapshot["last_active"] = last_active

    save_state(snapshot, cwd)

    # --- Pick reaction ---
    reaction = pick_reaction(events, snapshot)

    # --- Build session dict for decorators ---
    # PP = context remaining (inverted)
    pp_pct = (100 - context_pct) if context_pct is not None else None

    # Time-based tick for decorators (2 fps baseline)
    tick = int(time.time() * 2)

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
        "shiny": is_shiny,
        "streak_days": streak_days,
        "agent_name": agent_name,
        "worktree_name": worktree_name,
        "worktree_branch": worktree_branch,
        "_tick": tick,
    }

    # --- Select sprite and decorate ---
    sprite_grid = get_sprite(reaction, shiny=is_shiny)
    sprite_lines = grid_to_lines(sprite_grid)
    output_lines = decorate(reaction, sprite_lines, tick, session=session)

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
