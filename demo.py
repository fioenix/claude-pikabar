#!/usr/bin/env python3
"""pikabar demo — Preview all reaction states with Pokemon-style info panel.

Usage:
    python demo.py [option]

Options:
    0 = Unified demo (reactions transition in one view, loops)
    1 = All reactions separately
    2 = Idle
    3 = Thinking
    4 = Staging
    5 = Committed
    6 = Recovered
    7 = Compacted
    8 = Hit
    9 = Faint
"""

import sys

from pikabar.palette import fg, RST, BOLD, Y, GOLD, DY, SUBTLE
from pikabar.sprites import (
    IDLE_FRAMES, THINKING_SP, STAGING_SP, COMMITTED_SP,
    RECOVERED_SP, HIT_SP, COMPACTED_SP, BALL_FRAMES,
)
from pikabar.info_panel import (
    decorate_idle, decorate_thinking, decorate_staging,
    decorate_committed, decorate_recovered, decorate_compacted,
    decorate_hit, decorate_faint,
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
    "pp_pct": 85,
    "cost_usd": 0.42,
}

# Session states for each demo segment
SESSIONS = {
    "idle":      {**DEMO_SESSION, "hp_pct": 85, "pp_pct": 95},
    "thinking":  {**DEMO_SESSION, "hp_pct": 72, "pp_pct": 80},
    "staging":   {**DEMO_SESSION, "hp_pct": 65, "pp_pct": 70, "staged": 5, "modified": 3},
    "committed": {**DEMO_SESSION, "hp_pct": 60, "pp_pct": 65, "staged": 0, "modified": 0},
    "recovered": {**DEMO_SESSION, "hp_pct": 90, "pp_pct": 60},
    "compacted": {**DEMO_SESSION, "hp_pct": 45, "pp_pct": 90},
    "hit":       {**DEMO_SESSION, "hp_pct": 20, "pp_pct": 40},
    "faint":     {**DEMO_SESSION, "hp_pct": 0, "pp_pct": 30},
}

# Unified demo segments: (label, frames, fps, duration_secs, decorate_fn)
UNIFIED_SEGMENTS = [
    ("idle",      IDLE_FRAMES,      2,   4, decorate_idle),
    ("thinking",  [THINKING_SP],    2,   4, decorate_thinking),
    ("staging",   [STAGING_SP],     2,   3, decorate_staging),
    ("committed", [COMMITTED_SP],   2,   3, decorate_committed),
    ("idle",      IDLE_FRAMES,      2,   3, decorate_idle),
    ("thinking",  [THINKING_SP],    2,   3, decorate_thinking),
    ("hit",       [HIT_SP],         2,   3, decorate_hit),
    ("compacted", [COMPACTED_SP],   1.5, 4, decorate_compacted),
    ("recovered", [RECOVERED_SP],   2,   3, decorate_recovered),
    ("idle",      IDLE_FRAMES,      2,   3, decorate_idle),
    ("faint",     BALL_FRAMES,      6,   5, decorate_faint),
]


# Individual state configs: (name, frames, duration, fps, decorate_fn, session_key)
STATES = {
    "2": ("Idle",       IDLE_FRAMES,      8,  2,   decorate_idle,      "idle"),
    "3": ("Thinking",   [THINKING_SP],    8,  2,   decorate_thinking,  "thinking"),
    "4": ("Staging",    [STAGING_SP],     8,  2,   decorate_staging,   "staging"),
    "5": ("Committed",  [COMMITTED_SP],   8,  2,   decorate_committed, "committed"),
    "6": ("Recovered",  [RECOVERED_SP],   8,  2,   decorate_recovered, "recovered"),
    "7": ("Compacted",  [COMPACTED_SP],   8,  1.5, decorate_compacted, "compacted"),
    "8": ("Hit",        [HIT_SP],         8,  2,   decorate_hit,       "hit"),
    "9": ("Faint",      BALL_FRAMES,      8,  6,   decorate_faint,     "faint"),
}


def main():
    print(f"\n{fg(GOLD)}{BOLD}{'=' * 56}")
    print(f"  pikabar — Pokemon-Style Statusline Demo")
    print(f"{'=' * 56}{RST}")
    print(f"\n  {fg(GOLD)}0{RST} = Unified demo (all reactions in one view, loops)")
    print(f"  {fg(GOLD)}1{RST} = All reactions separately")
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
