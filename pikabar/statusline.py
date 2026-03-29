#!/usr/bin/env python3
"""pikabar statusline — Claude Code integration script.

Reads JSON session data from stdin (piped by Claude Code),
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
Frame counter persisted in /tmp/pikabar-frame for sprite animation.
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
    THINK_FRAMES, COMPACT_FRAME, BALL_FRAMES,
)
from pikabar.info_panel import (
    decorate_thinking, decorate_compact, decorate_ratelimit,
)

# --- Temp file paths ---
FRAME_FILE = "/tmp/pikabar-frame"
GIT_CACHE_FILE = "/tmp/pikabar-git-cache"
GIT_CACHE_MAX_AGE = 5  # seconds


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


def infer_state(data, hp_pct):
    """Infer Pikachu's emotional state."""
    if hp_pct is not None and hp_pct <= 0:
        return "ratelimited"
    ctx = data.get("context_window", {})
    used_pct = ctx.get("used_percentage")
    if used_pct is not None and used_pct > 90:
        return "compacting"
    return "active"


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
    duration_secs = duration_ms // 1000

    hp_pct, hp_window = compute_hp(data)

    session = {
        "model_id": model_id,
        "model_name": model_name,
        "hp_pct": hp_pct,
        "hp_window": hp_window,
        "branch": branch,
        "staged": staged,
        "modified": modified,
        "cost": cost_usd,
        "duration": duration_secs,
    }

    # --- Determine state and select sprite ---
    state = infer_state(data, hp_pct)

    if state == "ratelimited":
        frames = BALL_FRAMES
    elif state == "compacting":
        frames = [COMPACT_FRAME]
    else:
        # Default: thinking animation (eyes glancing, tail sway)
        frames = THINK_FRAMES

    sprite_grid = frames[frame % len(frames)]
    sprite_lines = grid_to_lines(sprite_grid)

    # --- Delegate to the appropriate decorator ---
    if state == "ratelimited":
        output_lines = decorate_ratelimit(sprite_lines, frame, session=session)
    elif state == "compacting":
        output_lines = decorate_compact(sprite_lines, frame, session=session)
    else:
        output_lines = decorate_thinking(sprite_lines, frame, session=session)

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
