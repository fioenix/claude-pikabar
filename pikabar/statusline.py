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

No animation loop — Claude Code calls this script on each update.
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

from pikabar.palette import fg, RST, SUBTLE, DIM, GOLD, GREEN
from pikabar.renderer import grid_to_lines
from pikabar.sprites import (
    THINK_FRAMES, STREAM_FRAMES, TOOL_FRAMES,
    SUBAGENT_FRAMES, COMPACT_FRAME, BALL_FRAMES,
)
from pikabar.hp_bar import render_hp_line, get_badge
from pikabar.info_panel import format_model, format_git, format_cost_time, INFO_COL
from pikabar.flavor import get_flavor_text

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
    """Compute HP% = 100 - max(5h_used, 7d_used). Returns (hp_pct, window_label) or (None, None)."""
    rate = data.get("rate_limits")
    if not rate:
        return None, None

    five_h = rate.get("five_hour", {}).get("used_percentage")
    seven_d = rate.get("seven_day", {}).get("used_percentage")

    if five_h is None and seven_d is None:
        return None, None

    # Use whichever window is more constrained (higher used = lower remaining)
    if five_h is not None and seven_d is not None:
        if five_h >= seven_d:
            return max(0, int(100 - five_h)), "5h"
        else:
            return max(0, int(100 - seven_d)), "7d"
    elif five_h is not None:
        return max(0, int(100 - five_h)), "5h"
    else:
        return max(0, int(100 - seven_d)), "7d"


def get_retry_minutes(data):
    """Calculate minutes until rate limit resets. Returns None if not rate limited."""
    rate = data.get("rate_limits", {})
    now = time.time()
    min_wait = None
    for window in ["five_hour", "seven_day"]:
        w = rate.get(window, {})
        used = w.get("used_percentage", 0) or 0
        resets_at = w.get("resets_at")
        if used >= 99 and resets_at:
            wait = max(1, int((resets_at - now) / 60))
            if min_wait is None or wait < min_wait:
                min_wait = wait
    return min_wait


def infer_state(data, hp_pct):
    """Infer Pikachu's emotional state from available data.

    Claude Code doesn't expose an explicit state machine.
    We infer from context changes and rate limit status.
    """
    # Rate limited: HP = 0
    if hp_pct is not None and hp_pct <= 0:
        return "ratelimited"

    # Check context for compacting (used% dropped significantly)
    ctx = data.get("context_window", {})
    used_pct = ctx.get("used_percentage")

    # If context > 90%, likely compacting soon or happening
    if used_pct is not None and used_pct > 90:
        return "compacting"

    # Default: cycle between thinking and streaming based on frame
    return "active"


def select_frames(state, frame):
    """Select sprite frames based on state."""
    if state == "ratelimited":
        return BALL_FRAMES
    elif state == "compacting":
        return [COMPACT_FRAME]
    else:
        # Cycle between think and stream frames for visual variety
        cycles = [THINK_FRAMES, STREAM_FRAMES, TOOL_FRAMES, STREAM_FRAMES]
        return cycles[(frame // 8) % len(cycles)]


def COL(n):
    """Absolute column positioning."""
    return f"\033[{n}G"


def render_statusline(data):
    """Render the complete pikabar statusline output."""
    frame = read_frame()

    # --- Extract data from Claude Code JSON ---
    model_id = data.get("model", {}).get("id", "")
    model_name = data.get("model", {}).get("display_name", "Claude")

    cwd = data.get("workspace", {}).get("current_dir", data.get("cwd", ""))
    branch, staged, modified = get_git_info(cwd) if cwd else ("", 0, 0)

    cost_usd = data.get("cost", {}).get("total_cost_usd", 0) or 0
    duration_ms = data.get("cost", {}).get("total_duration_ms", 0) or 0
    duration_secs = duration_ms // 1000

    hp_pct, hp_window = compute_hp(data)

    # --- Determine state and select sprite ---
    state = infer_state(data, hp_pct)
    frames = select_frames(state, frame)
    sprite_grid = frames[frame % len(frames)]
    sprite_lines = grid_to_lines(sprite_grid)

    # --- Build info lines ---
    is_rate_limited = (state == "ratelimited")
    is_compacting = (state == "compacting")

    model_str = format_model(model_id, model_name)
    badge = get_badge(hp_pct, is_compacting=is_compacting, is_rate_limited=is_rate_limited)
    git_str = format_git(branch, staged, modified)
    hp_str = render_hp_line(hp_pct, hp_window, tick=frame)
    cost_time_str = format_cost_time(cost_usd, duration_secs)

    # Flavor text
    state_key = state if state != "active" else "streaming"
    flavor, _ = get_flavor_text(state_key, hp_pct, cost_usd, duration_secs // 60, tick=frame)

    # --- Compose lines ---
    badge_part = f" {badge}" if badge else ""
    git_part = f" {fg(DIM)}│{RST} {git_str}" if git_str else ""
    flavor_part = f" {fg(DIM)}│{RST} {fg(SUBTLE)}▶ {flavor}{RST}" if flavor else ""

    # Rate limited: show retry time
    if is_rate_limited:
        retry = get_retry_minutes(data)
        if retry:
            flavor_part = f" {fg(DIM)}│{RST} {fg(SUBTLE)}Retry ~{retry}m{RST}"

    info_lines = [
        f"{model_str}{badge_part}{git_part}",
        hp_str,
        f"{cost_time_str}{flavor_part}",
    ]

    # --- Output multi-line statusline ---
    # Each sprite line paired with info, using absolute column positioning
    output_lines = []
    for i, sp in enumerate(sprite_lines):
        info = info_lines[i] if i < len(info_lines) else ""
        output_lines.append(f"  {sp}{COL(INFO_COL)}{info}")

    # Extra info lines if sprite has fewer lines than info
    for i in range(len(sprite_lines), len(info_lines)):
        output_lines.append(f"{COL(INFO_COL)}{info_lines[i]}")

    return "\n".join(output_lines)


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Graceful fallback if no/bad input
        print("[pikabar] waiting for data...")
        return

    output = render_statusline(data)
    print(output)


if __name__ == "__main__":
    main()
