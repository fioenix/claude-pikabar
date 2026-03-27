#!/usr/bin/env python3
"""pikabar demo — Preview all animation states with Pokemon-style info panel.

Usage:
    python demo.py [option]

Options:
    0 = Unified demo (states transition in one view, loops)
    1 = All states separately
    2 = Thinking
    3 = Streaming
    4 = Tool Use
    5 = Subagent
    6 = Compacting
    7 = Rate Limited
"""

import sys

from pikabar.palette import fg, RST, BOLD, Y, GOLD
from pikabar.sprites import (
    THINK_FRAMES, STREAM_FRAMES, TOOL_FRAMES,
    SUBAGENT_FRAMES, COMPACT_FRAME, BALL_FRAMES,
)
from pikabar.info_panel import (
    decorate_thinking, decorate_streaming, decorate_tool,
    decorate_subagent, decorate_compact, decorate_ratelimit,
)
from pikabar.animator import animate, animate_unified


# Simulated session data for demo (real data comes from Claude Code JSON)
DEMO_SESSION = {
    "model_id": "claude-opus-4-6",
    "model_name": "Opus",
    "branch": "main",
    "staged": 2,
    "modified": 1,
    "hp_pct": 72,
    "hp_window": "5h",
    "cost": 0.42,
    "duration": 192,  # 3m12s
}

# Session states for each demo segment
SESSIONS = {
    "thinking":    {**DEMO_SESSION, "hp_pct": 85},
    "streaming":   {**DEMO_SESSION, "hp_pct": 72},
    "tool_use":    {**DEMO_SESSION, "hp_pct": 55, "staged": 5, "modified": 2},
    "subagent":    {**DEMO_SESSION, "hp_pct": 45, "cost": 1.20},
    "compacting":  {**DEMO_SESSION, "hp_pct": 30, "cost": 2.50, "duration": 480},
    "ratelimit":   {**DEMO_SESSION, "hp_pct": 0, "cost": 3.10, "duration": 720},
}

# Unified demo segments: (label, frames, fps, duration_secs, decorate_fn)
UNIFIED_SEGMENTS = [
    ("thinking",   THINK_FRAMES,    2,   4,  decorate_thinking),
    ("streaming",  STREAM_FRAMES,   2.5, 5,  decorate_streaming),
    ("tool_use",   TOOL_FRAMES,     4,   3,  decorate_tool),
    ("streaming",  STREAM_FRAMES,   2.5, 3,  decorate_streaming),
    ("tool_use",   TOOL_FRAMES,     4,   2,  decorate_tool),
    ("subagent",   SUBAGENT_FRAMES, 2,   4,  decorate_subagent),
    ("streaming",  STREAM_FRAMES,   2.5, 3,  decorate_streaming),
    ("compacting", [COMPACT_FRAME], 1.5, 4,  decorate_compact),
    ("thinking",   THINK_FRAMES,    2,   3,  decorate_thinking),
    ("streaming",  STREAM_FRAMES,   2.5, 4,  decorate_streaming),
    ("ratelimit",  BALL_FRAMES,     6,   5,  decorate_ratelimit),
]


# Individual state configs: (name, frames, duration, fps, decorate_fn, session_key)
STATES = {
    "2": ("Thinking 💭",    THINK_FRAMES,    8,  2,   decorate_thinking,  "thinking"),
    "3": ("Streaming ▍",   STREAM_FRAMES,   10, 2.5, decorate_streaming, "streaming"),
    "4": ("Tool Use ⚡",    TOOL_FRAMES,     8,  4,   decorate_tool,      "tool_use"),
    "5": ("Subagent ♥",    SUBAGENT_FRAMES, 8,  2,   decorate_subagent,  "subagent"),
    "6": ("Compacting 💤",  [COMPACT_FRAME], 8,  1.5, decorate_compact,   "compacting"),
    "7": ("Rate Limited 🔴", BALL_FRAMES,    8,  6,   decorate_ratelimit, "ratelimit"),
}


def main():
    print(f"\n{fg(GOLD)}{BOLD}{'=' * 56}")
    print(f"  pikabar — Pokemon-Style Statusline Demo")
    print(f"{'=' * 56}{RST}")
    print(f"\n  {fg(GOLD)}0{RST} = Unified demo (all states in one view, loops)")
    print(f"  {fg(GOLD)}1{RST} = All states separately")
    for key in sorted(STATES.keys()):
        name = STATES[key][0]
        print(f"  {fg(GOLD)}{key}{RST} = {name}")
    print()

    choice = "0"
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        try:
            choice = input(f"  {fg(178)}>{RST} ") or "0"
        except (EOFError, KeyboardInterrupt):
            choice = "0"

    if choice == "0":
        # Build session data that evolves across segments
        session = dict(DEMO_SESSION)
        animate_unified(UNIFIED_SEGMENTS, loop=True, session=session)

    elif choice == "1":
        for key in sorted(STATES.keys()):
            name, frames, dur, fps, dec_fn, sess_key = STATES[key]
            session = SESSIONS[sess_key]
            animate(name, frames, duration=dur, fps=fps,
                    decorate_fn=dec_fn, session=session)

    elif choice in STATES:
        name, frames, dur, fps, dec_fn, sess_key = STATES[choice]
        session = SESSIONS[sess_key]
        animate(name, frames, duration=dur, fps=fps,
                decorate_fn=dec_fn, session=session)

    else:
        print(f"  Unknown option: {choice}")
        sys.exit(1)


if __name__ == "__main__":
    main()
