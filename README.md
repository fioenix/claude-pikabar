# pikabar

A Pokemon-style statusline for [Claude Code](https://code.claude.com).

Pikachu pixel art mascot with an HP bar, status badges, and battle narrator flavor text — right in your terminal.

```
  ▄█▀         ▄███████▀       Lv.4 OPUS │ main +2 ~1
  ██▄  ▄▀ █▄▀█ █▄▀█ ██       HP ████████████░░░░ 72% 5h
  █▀  █▀▀█ ██ █▀▀█ ██       P$0.42 3m12s │ ▶ PIKACHU used FOCUS.
       ▀▄   ▀▄
```

## Features

- **Pikachu pixel art** rendered with Unicode half-blocks (▀▄█) + ANSI 256-color
- **6 emotional states**: Thinking, Streaming, Tool Use, Subagent, Compacting, Rate Limited
- **HP bar** = rate limit quota remaining (green > yellow > red, like the games)
- **Status badges**: `[PAR]` `[SLP]` `[PSN]` `[BRN]` `[FRZ]` with game-accurate colors
- **Lv.N SPECIES** model display (Lv.4 OPUS, Lv.3 SONNET)
- **P$** Pokedollar cost tracking
- **Pokeball wobble** when rate limited (Pikachu recalled!)
- **48 flavor texts** + easter eggs in Pokemon battle narrator voice
- **Git branch** + staged/modified counts with caching

## Quick Start

### 1. Clone

```bash
git clone https://github.com/user/pikabar.git ~/.claude/pikabar
```

### 2. Configure Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/pikabar/pikabar/statusline.py",
    "padding": 1
  }
}
```

### 3. Done

The statusline appears automatically on your next Claude Code interaction.

## Demo Mode

Preview all animation states without Claude Code:

```bash
cd pikabar
python3 demo.py
```

Options:
- `0` = Unified demo (all states transition in one view)
- `1` = All states separately
- `2-7` = Individual states (Thinking, Streaming, Tool Use, Subagent, Compacting, Rate Limited)

## How It Works

Claude Code pipes JSON session data to the statusline script via stdin on each interaction. pikabar reads the JSON, extracts metrics, renders the Pikachu sprite + info panel, and prints multi-line ANSI-colored output to stdout.

### Data Flow

```
Claude Code ──JSON stdin──▶ pikabar/statusline.py ──stdout──▶ Terminal
                               │
                               ├── Reads model, cost, duration, rate limits
                               ├── Computes HP% from rate limit quota remaining
                               ├── Selects sprite frame (persisted in /tmp/pikabar-frame)
                               ├── Gets git info (cached in /tmp/pikabar-git-cache)
                               └── Renders pixel art + HP bar + badges + flavor text
```

### HP Bar Semantics

HP represents your **rate limit quota remaining** — the resource developers actually care about:

| HP | Color | Meaning |
|---|---|---|
| >50% | Green | Plenty of quota left |
| 20-50% | Yellow | Burning through moves |
| 5-20% | Red | Danger zone |
| <5% | Flashing red | About to faint |
| 0% | Pokeball appears | Rate limited (paralyzed!) |

HP uses whichever rate window (5-hour or 7-day) is more constrained.
When no rate limit data is available (before first API call), shows `HP ??? ---`.

### Status Badges

One badge at a time, matching Pokemon game colors and priority:

| Badge | Trigger | Color |
|---|---|---|
| `FRZ` | HP=0 + compacting | Ice blue |
| `PAR` | Rate limited | Gold |
| `SLP` | Compacting context | Gray |
| `PSN` | HP <= 15% | Purple |
| `BRN` | HP <= 35% | Orange |

### Available Data (from Claude Code)

pikabar reads these fields from the [Claude Code statusline JSON](https://code.claude.com/docs/en/statusline):

| Field | Used For |
|---|---|
| `model.id`, `model.display_name` | Lv.N SPECIES display |
| `cost.total_cost_usd` | Pokedollar cost (P$) |
| `cost.total_duration_ms` | Session duration |
| `rate_limits.five_hour.used_percentage` | HP bar (inverted) |
| `rate_limits.seven_day.used_percentage` | HP bar fallback |
| `rate_limits.*.resets_at` | Retry countdown |
| `workspace.current_dir` | Git info (cached) |
| `context_window.used_percentage` | Compacting state inference |

## Project Structure

```
pikabar/
├── demo.py                  # Interactive demo (python3 demo.py)
├── pikabar/
│   ├── __init__.py
│   ├── palette.py           # ANSI 256-color constants + terminal escapes
│   ├── renderer.py          # Half-block pixel art engine
│   ├── sprites.py           # Pikachu (6 states) + Pokeball pixel grids
│   ├── hp_bar.py            # HP bar + status badges
│   ├── info_panel.py        # 5-line layout with decoration functions
│   ├── flavor.py            # 48 flavor texts + easter eggs
│   ├── animator.py          # Demo animation engine
│   └── statusline.py        # Claude Code integration (reads stdin JSON)
├── LICENSE                  # MIT
└── README.md
```

## Requirements

- Python 3.8+
- A 256-color terminal (iTerm2, Kitty, WezTerm, Alacritty, Windows Terminal)
- [Claude Code](https://code.claude.com) for the statusline integration
- No external Python dependencies

## Performance

- Script runs on each Claude Code interaction (~300ms debounce)
- Git operations cached for 5 seconds (`/tmp/pikabar-git-cache`)
- Frame counter persisted in `/tmp/pikabar-frame`
- No network calls, no API tokens consumed

## Testing

```bash
# Test with mock Claude Code JSON input
echo '{"model":{"id":"claude-opus-4-6","display_name":"Opus"},"context_window":{"used_percentage":25},"cost":{"total_cost_usd":0.42,"total_duration_ms":192000},"rate_limits":{"five_hour":{"used_percentage":28}}}' | python3 pikabar/statusline.py
```

## License

MIT

## Credits

Inspired by the [Claude Code statusline API](https://code.claude.com/docs/en/statusline) and every Pokemon game ever made.
