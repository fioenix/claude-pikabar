# CLAUDE.md — pikabar

## What is this?

pikabar is a Pokemon-style statusline extension for Claude Code. It renders a Pikachu pixel art mascot with an HP bar, status badges, and flavor text in the terminal.

## Architecture

```
pikabar/
├── pikabar/statusline.py    # ENTRY POINT: Claude Code integration (stdin JSON → stdout)
├── pikabar/palette.py       # Color constants (ANSI 256), terminal escapes
├── pikabar/renderer.py      # Half-block pixel engine (▀▄█ with fg/bg colors)
├── pikabar/sprites.py       # Pixel art grids: Pikachu (8 states) + Pokeball (7x11)
├── pikabar/hp_bar.py        # HP/PP bar rendering + Pokemon status badges
├── pikabar/info_panel.py    # 5-line layout engine with 8 reaction decorators
├── pikabar/delta.py         # State persistence + delta detection + reaction selection
├── pikabar/flavor.py        # 64 battle narrator texts + easter eggs
├── pikabar/animator.py      # Demo-only animation engine (cursor-up loop)
├── tests/                   # pytest test suite
└── demo.py                  # Interactive demo (not used in production)
```

## Key Design Decisions

- **HP = rate limit quota remaining** (not context window). Full HP = safe, empty = rate limited.
- **Context window is NOT displayed** — the Pikachu sleeping/compact state communicates compaction visually.
- **Lv.N** = first digit of model version from `model.id` (e.g., `claude-opus-4-6` → Lv.4)
- **One status badge at a time**, priority: FRZ > PAR > SLP > PSN > BRN
- **No external dependencies** — pure Python 3.8+ stdlib
- **Git caching** at 5-second intervals for performance
- **Frame persistence** in `/tmp/pikabar-frame` for sprite animation across statusline calls

## Rendering Technique

Each terminal character = 2 pixel rows using Unicode upper half-block (▀):
- Foreground color = top pixel
- Background color = bottom pixel
- Full block (█) = both same color
- Space = both transparent

## Commands

```bash
# Run demo
python3 demo.py

# Test with mock Claude Code JSON
echo '{"model":{"id":"claude-opus-4-6","display_name":"Opus"},"cost":{"total_cost_usd":0.42,"total_duration_ms":192000},"rate_limits":{"five_hour":{"used_percentage":28}}}' | python3 pikabar/statusline.py

# Test imports
python3 -c "from pikabar.statusline import render_statusline; print('OK')"
```

## Coding Conventions

- All color values are ANSI 256-color indices (0-255)
- `None` = transparent pixel in sprite grids
- Session data dicts use `model_id`, `model_name`, `hp_pct`, `hp_window`, `branch`, `staged`, `modified`, `cost`, `duration`
- Info panel uses absolute column positioning (`\033[{n}G`) to prevent text jitter from variable-width sprites/effects
- All states produce exactly `DECORATED_LINES = 5` output lines for zero vertical jitter

## Integration

The statusline script (`pikabar/statusline.py`) is configured in `~/.claude/settings.json`:
```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 /path/to/pikabar/pikabar/statusline.py"
  }
}
```

Claude Code pipes JSON to stdin on each interaction. The script prints multi-line ANSI output to stdout. No animation loop — each call renders one frame and exits.
