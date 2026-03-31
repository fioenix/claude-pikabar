# CLAUDE.md — pikabar

## What is this?

pikabar is a Pokemon-style statusline extension for Claude Code. It renders a Pikachu pixel art mascot with an HP bar, status badges, flavor text, and creative features in the terminal.

**Version**: 0.3.1 | **License**: MIT | **Python**: 3.8+ (pure stdlib, zero deps)

## Architecture

```
pikabar/
├── pikabar/
│   ├── __init__.py          # Version (__version__) + exports
│   ├── statusline.py        # ENTRY POINT: Claude Code stdin JSON → stdout ANSI
│   ├── cli.py               # CLI: install | uninstall | update | (no args = statusline)
│   ├── palette.py           # ANSI 256-color constants + terminal escapes + visible_len()
│   ├── renderer.py          # Half-block pixel engine (▀▄█ with fg/bg colors)
│   ├── sprites.py           # Pixel art grids: Pikachu (8 states) + Shiny + Pokeball (7x11)
│   ├── hp_bar.py            # HP/PP bar rendering + Pokemon status badges
│   ├── info_panel.py        # 5-line layout engine with 8 reaction decorators
│   ├── delta.py             # State persistence + delta detection + reaction selection + shiny + streak
│   ├── flavor.py            # 64 battle narrator texts + session greetings + critical flavor + easter eggs
│   └── animator.py          # Demo-only animation engine (cursor-up loop)
├── tests/
│   ├── test_palette.py      # fg, bg, visible_len (wide chars)
│   ├── test_hp_bar.py       # hp_color, render_hp_bar, render_pp_bar, get_badge
│   ├── test_delta.py        # make_snapshot, compute_deltas, infer_events, pick_reaction
│   ├── test_info_panel.py   # format_model, format_git, format_cost, decorate alignment
│   ├── test_smoke.py        # End-to-end statusline with empty/full/malformed JSON
│   ├── test_cli.py          # install, uninstall, update, backup/restore
│   └── test_track_b.py      # Session greeting, confetti, shiny, critical HP, streak
├── demo.py                  # Interactive demo (not used in production)
├── pyproject.toml           # Package config: claude-pikabar
├── assets/pikabar-preview.png
└── LICENSE
```

## Data Flow

```
Claude Code ──JSON stdin──▶ statusline.py ──stdout──▶ Terminal (Ink.js renderer)
                               │
                               ├── Extract: model, rate_limits, context_window, cost, session_id
                               ├── Git info (cached 5s in /tmp/pikabar-git-cache)
                               ├── Load prev state (/tmp/pikabar-state-{workspace_hash})
                               ├── Compute deltas → infer events → pick reaction
                               ├── Shiny check (per session_id, 1/1024 chance)
                               ├── Streak counter (consecutive active days)
                               ├── Render sprite → grid_to_lines (half-block engine)
                               ├── Decorate (5-line layout: sprite + effects + info)
                               ├── Save state (atomic write)
                               └── Output 5 lines of ANSI art (prefixed \033[0m for Ink.js)
```

## Key Design Decisions

- **HP = rate limit quota remaining** (not context window). Full HP = safe, empty = rate limited.
- **PP = context window remaining** (inverted: 100 - used_percentage).
- **Lv.N** = first digit of model version from `model.id` (e.g., `claude-opus-4-6` → Lv.4)
- **One status badge at a time**, priority: FRZ > PAR > SLP > PSN > BRN
- **No external dependencies** — pure Python 3.8+ stdlib only
- **Space-padding, NOT CSI CHA** — Ink.js (Claude Code terminal) does not support `\033[nG`. All column alignment uses `visible_len()` + space padding.
- **visible_len()** uses `unicodedata.east_asian_width()` for correct terminal width (⚡ = 2 cols).
- **INFO_COL = 20** — absolute column where info text starts (sprite 15 + side effect 3 + 2 gap).
- **DECORATED_LINES = 5** — all reactions produce exactly 5 lines for zero vertical jitter.
- **Git caching** at 5-second intervals in `/tmp/pikabar-git-cache`.
- **Frame persistence** in `/tmp/pikabar-frame` for sprite animation across statusline calls.
- **State persistence** in `/tmp/pikabar-state-{hash}` — per-workspace, atomic writes.
- **ensure_ascii=False** when writing `settings.json` to preserve Unicode (e.g., Vietnamese).
- **Smart python3 path** — uses `python3` if it resolves to the same interpreter, full path as fallback (venv/pyenv safety).

## Creative Features (Track B, v0.3.0+)

| Feature | Location | Description |
|---------|----------|-------------|
| **Session Greeting** | `flavor.py`, `info_panel.py` | Pokemon-style welcome on first call. Day-aware (Mon/Fri/Sat/Sun variants, 50% chance). |
| **Commit Confetti** | `info_panel.py` `decorate_committed()` | Multi-color particles (`·+*✦♥` in 8 colors) replace hearts. Deterministic per tick via seeded RNG. |
| **Shiny Pikachu** | `sprites.py`, `delta.py`, `palette.py` | 1/1024 (2^10) chance per session. Orange palette swap (SY/SLY/SDY/SRD). Keyed by `session_id` — each session rolls independently, persists across calls. Max 20 sessions in `shiny_map`. |
| **Critical HP Drama** | `info_panel.py`, `flavor.py` | HP < 10% → red bold DANGER label + dramatic flavor text on extra line. |
| **Streak Counter** | `delta.py`, `info_panel.py` | Consecutive active days tracked via `last_active` date. ≥2 days shows `x{N}` beside model name with escalating flame color (208→202→196). |

## Session Dict Keys

The `session` dict passed to decorators contains:

```python
{
    "model_id": str,        # e.g. "claude-opus-4-6"
    "model_name": str,      # e.g. "Opus"
    "hp_pct": int|None,     # 0-100, rate limit remaining
    "hp_window": str|None,  # "5h" or "7d"
    "pp_pct": int|None,     # 0-100, context remaining (inverted)
    "cost_usd": float,      # session total cost
    "branch": str,          # git branch name
    "staged": int,          # staged file count
    "modified": int,        # modified file count
    "events": list[str],    # inferred events (session_start, committed, etc.)
    "deltas": dict,         # computed deltas from prev state
    "reaction": str,        # picked reaction name
    "shiny": bool,          # is current session shiny
    "streak_days": int,     # consecutive active days
    "_tick": int,           # frame counter
}
```

## State Snapshot Keys (persisted to /tmp)

```python
{
    "ts": float,            # timestamp
    "hp": int|None,         # HP percentage
    "hw": str|None,         # HP window ("5h"/"7d")
    "ctx": int|None,        # context used percentage
    "cost": float,          # session cost USD
    "dur": int,             # duration ms
    "br": str,              # git branch
    "stg": int,             # staged count
    "mod": int,             # modified count
    "shiny_map": dict,      # {session_id: bool} per-session shiny flags
    "session_id": str,      # current session ID
    "streak": int,          # consecutive active days
    "last_active": str,     # ISO date "YYYY-MM-DD"
}
```

## Reaction System

Priority order (highest first):

| Reaction | Trigger | Sprite | Effects |
|----------|---------|--------|---------|
| faint | HP < 15% | Pokeball wobble | Retry countdown |
| hit | Heavy HP burst (≥10% drop) | Closed eyes | Sweat drops |
| compacted | Context drop >20% | Sleeping eyes | ZZZ + SLP badge |
| thinking | Long operation (>8s) | Alert, glancing | Lightning ⚡ |
| recovered | HP jumped ≥20% | Normal | Green sparkles ✦ |
| committed | Staged→0 (commit detected) | Winking | Confetti particles |
| staging | Files modified/staged | Alert | Yellow stars * |
| idle | Default | Normal cycle | None |

## Rendering Technique

Each terminal character = 2 pixel rows using Unicode upper half-block (▀):
- Foreground color = top pixel, Background color = bottom pixel
- Full block (█) = both same color, Space = both transparent
- Pikachu: 6 rows × 15 cols = 3 terminal lines
- Pokeball: 7 rows × 11 cols = 4 terminal lines

## Commands

```bash
# Install/manage
pikabar install          # Auto-configure Claude Code settings.json
pikabar uninstall        # Remove + restore backup
pikabar update           # Pull latest from GitHub + refresh settings
pikabar --version        # Show version

# Test
pytest                   # Full suite (76 tests)
pytest tests/test_track_b.py  # Track B features only

# Manual test with mock JSON
echo '{"model":{"id":"claude-opus-4-6","display_name":"Opus"},"cost":{"total_cost_usd":0.42},"rate_limits":{"five_hour":{"used_percentage":28}}}' | python3 pikabar/statusline.py

# Force shiny (inject state)
echo '{"ts":1,"hp":80,"hw":"5h","ctx":null,"cost":0,"dur":0,"br":"","stg":0,"mod":0,"shiny_map":{"test":true},"session_id":"test","streak":5,"last_active":"2026-04-01"}' > /tmp/pikabar-state
echo '{"model":{"id":"claude-opus-4-6","display_name":"Opus"},"session_id":"test","rate_limits":{"five_hour":{"used_percentage":20}}}' | python3 pikabar/statusline.py

# Demo mode (cycles all reactions)
python3 demo.py
```

## Coding Conventions

- All color values are ANSI 256-color indices (0-255)
- `None` = transparent pixel in sprite grids
- Space-padding for column alignment (never CSI CHA `\033[nG`)
- `visible_len()` for terminal width (accounts for wide chars)
- Prefix output lines with `\033[0m` to prevent Ink.js whitespace trimming
- Atomic state writes via `os.replace()` (POSIX)
- Tests use `pytest` with `-p no:opik` flag (avoid global plugin conflict)

## Claude Code Statusline JSON

Claude Code pipes this JSON to stdin on each interaction:

```
session_id, transcript_path,
model.{id, display_name},
workspace.{current_dir, project_dir},
context_window.{used_percentage, remaining_percentage, context_window_size, ...},
cost.{total_cost_usd, total_duration_ms, total_api_duration_ms, total_lines_added, total_lines_removed},
rate_limits.{five_hour.{used_percentage, resets_at}, seven_day.{used_percentage, resets_at}},
version, output_style.name, vim.mode, agent.name, worktree.{name, path, branch, ...}
```

No animation loop — each call renders one frame and exits.
