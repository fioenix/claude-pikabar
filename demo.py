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
    A = Pichu (all reactions)
    B = Raichu (all reactions)
    S = Shiny Pichu
    R = Shiny Raichu
    T = Agent Teams (party balls, agent label, agent flavor)
"""

import sys

from pikabar.palette import fg, RST, BOLD, Y, GOLD, DY, SUBTLE
from pikabar.sprites import (
    IDLE_FRAMES, THINKING_SP, STAGING_SP, COMMITTED_SP,
    RECOVERED_SP, HIT_SP, COMPACTED_SP, BALL_FRAMES,
    PICHU_IDLE_FRAMES, PICHU_THINKING_SP, PICHU_STAGING_SP,
    PICHU_COMMITTED_SP, PICHU_RECOVERED_SP, PICHU_HIT_SP,
    PICHU_COMPACTED_SP, RAICHU_IDLE_FRAMES, RAICHU_THINKING_SP,
    RAICHU_STAGING_SP, RAICHU_COMMITTED_SP, RAICHU_RECOVERED_SP,
    RAICHU_HIT_SP, RAICHU_COMPACTED_SP, SHINY_PICHU_IDLE_FRAMES,
    SHINY_RAICHU_IDLE_FRAMES,
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

# Pichu segments
PICHU_SEGMENTS = [
    ("idle",      PICHU_IDLE_FRAMES,    2,   3, decorate_idle),
    ("thinking",  [PICHU_THINKING_SP],  2,   3, decorate_thinking),
    ("staging",   [PICHU_STAGING_SP],   2,   2, decorate_staging),
    ("committed", [PICHU_COMMITTED_SP], 2,   2, decorate_committed),
    ("hit",       [PICHU_HIT_SP],       2,   2, decorate_hit),
    ("compacted", [PICHU_COMPACTED_SP], 1.5, 3, decorate_compacted),
    ("recovered", [PICHU_RECOVERED_SP], 2,   2, decorate_recovered),
    ("idle",      PICHU_IDLE_FRAMES,    2,   3, decorate_idle),
]

# Raichu segments
RAICHU_SEGMENTS = [
    ("idle",      RAICHU_IDLE_FRAMES,    2,   3, decorate_idle),
    ("thinking",  [RAICHU_THINKING_SP],  2,   3, decorate_thinking),
    ("staging",   [RAICHU_STAGING_SP],   2,   2, decorate_staging),
    ("committed", [RAICHU_COMMITTED_SP], 2,   2, decorate_committed),
    ("hit",       [RAICHU_HIT_SP],       2,   2, decorate_hit),
    ("compacted", [RAICHU_COMPACTED_SP], 1.5, 3, decorate_compacted),
    ("recovered", [RAICHU_RECOVERED_SP], 2,   2, decorate_recovered),
    ("idle",      RAICHU_IDLE_FRAMES,    2,   3, decorate_idle),
]

# Shiny variants
SHINY_PICHU_SEGMENTS = [
    ("idle",      SHINY_PICHU_IDLE_FRAMES,    2,   4, decorate_idle),
    ("thinking",  [PICHU_THINKING_SP],         2,   3, decorate_thinking),
    ("staging",   [PICHU_STAGING_SP],          2,   2, decorate_staging),
    ("idle",      SHINY_PICHU_IDLE_FRAMES,    2,   4, decorate_idle),
]

SHINY_RAICHU_SEGMENTS = [
    ("idle",      SHINY_RAICHU_IDLE_FRAMES,    2,   4, decorate_idle),
    ("thinking",  [RAICHU_THINKING_SP],         2,   3, decorate_thinking),
    ("staging",   [RAICHU_STAGING_SP],          2,   2, decorate_staging),
    ("idle",      SHINY_RAICHU_IDLE_FRAMES,    2,   4, decorate_idle),
]

# Agent Teams segments
AGENT_SEGMENTS = [
    ("idle",      IDLE_FRAMES,      2,   4, decorate_idle),
    ("thinking",  [THINKING_SP],    2,   4, decorate_thinking),
    ("staging",   [STAGING_SP],     2,   3, decorate_staging),
    ("committed", [COMMITTED_SP],   2,   3, decorate_committed),
    ("recovered", [RECOVERED_SP],    2,   3, decorate_recovered),
    ("idle",      IDLE_FRAMES,      2,   3, decorate_idle),
]

# Agent Teams sessions
AGENT_SESSIONS = {
    "idle":      {**DEMO_SESSION, "hp_pct": 85, "pp_pct": 95},
    "thinking":  {**DEMO_SESSION, "hp_pct": 72, "pp_pct": 80},
    "staging":   {**DEMO_SESSION, "hp_pct": 65, "pp_pct": 70, "staged": 5, "modified": 3},
    "committed": {**DEMO_SESSION, "hp_pct": 60, "pp_pct": 65, "staged": 0, "modified": 0},
    "recovered": {**DEMO_SESSION, "hp_pct": 90, "pp_pct": 60},
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
    print(f"  {fg(GOLD)}A{RST} = Pichu (all reactions)")
    print(f"  {fg(GOLD)}B{RST} = Raichu (all reactions)")
    print(f"  {fg(GOLD)}S{RST} = Shiny Pichu")
    print(f"  {fg(GOLD)}R{RST} = Shiny Raichu")
    print(f"  {fg(GOLD)}T{RST} = Agent Teams (1 agent)")
    print(f"  {fg(GOLD)}T2{RST} = Agent Teams (2 agents)")
    print(f"  {fg(GOLD)}T3{RST} = Agent Teams (3 agents)")
    print(f"  {fg(GOLD)}T6{RST} = Agent Teams (6 agents - full party)")
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

    elif choice.upper() == "A":
        session = dict(DEMO_SESSION)
        session["pokemon_name"] = "PICHU"
        session["species"] = "pichu"
        animate_unified(PICHU_SEGMENTS, loop=True, session=session)

    elif choice.upper() == "B":
        session = dict(DEMO_SESSION)
        session["pokemon_name"] = "RAICHU"
        session["species"] = "raichu"
        animate_unified(RAICHU_SEGMENTS, loop=True, session=session)

    elif choice.upper() == "S":
        session = dict(DEMO_SESSION)
        session["pokemon_name"] = "PICHU"
        session["species"] = "pichu"
        session["shiny"] = True
        animate_unified(SHINY_PICHU_SEGMENTS, loop=True, session=session)

    elif choice.upper() == "R":
        session = dict(DEMO_SESSION)
        session["pokemon_name"] = "RAICHU"
        session["species"] = "raichu"
        session["shiny"] = True
        animate_unified(SHINY_RAICHU_SEGMENTS, loop=True, session=session)

    elif choice.upper() == "T":
        # Agent Teams demo - simulates Claude Code Agent Teams mode
        session = dict(DEMO_SESSION)
        session["agent_name"] = "research-bot"
        session["worktree_name"] = "feature-x"
        session["worktree_branch"] = "feat/x"
        session["pokemon_name"] = "PIKACHU"
        session["species"] = "pikachu"
        session["num_agents"] = 1  # Show 1 active agent
        # Use the unified segments but with agent info
        animate_unified(AGENT_SEGMENTS, loop=True, session=session)

    elif choice.upper() == "T2":
        # Agent Teams demo - 2 active agents
        session = dict(DEMO_SESSION)
        session["agent_name"] = "research-bot"
        session["worktree_name"] = "feature-x"
        session["worktree_branch"] = "feat/x"
        session["pokemon_name"] = "PIKACHU"
        session["species"] = "pikachu"
        session["num_agents"] = 2  # Show 2 active agents
        animate_unified(AGENT_SEGMENTS, loop=True, session=session)

    elif choice.upper() == "T3":
        # Agent Teams demo - 3 active agents
        session = dict(DEMO_SESSION)
        session["agent_name"] = "research-bot"
        session["worktree_name"] = "feature-x"
        session["worktree_branch"] = "feat/x"
        session["pokemon_name"] = "PIKACHU"
        session["species"] = "pikachu"
        session["num_agents"] = 3  # Show 3 active agents
        animate_unified(AGENT_SEGMENTS, loop=True, session=session)

    elif choice.upper() == "T6":
        # Agent Teams demo - 6 active agents (full team!)
        session = dict(DEMO_SESSION)
        session["agent_name"] = "research-bot"
        session["worktree_name"] = "feature-x"
        session["worktree_branch"] = "feat/x"
        session["pokemon_name"] = "PIKACHU"
        session["species"] = "pikachu"
        session["num_agents"] = 6  # Show 6 active agents (full party)
        animate_unified(AGENT_SEGMENTS, loop=True, session=session)

    else:
        print(f"  Unknown option: {choice}")
        sys.exit(1)


if __name__ == "__main__":
    main()
