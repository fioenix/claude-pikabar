"""Info panel layout — Pokemon-style statusline display.

Layout (5 lines, info-above-sprite):
  Line 0: Lv.N MODEL [badge] | branch +staged ~modified
  Line 1: HP ############.... 72% 5h  P$0.42 3m12s  > flavor
  Line 2: [sprite line 0]  [effects]
  Line 3: [sprite line 1]  [effects]
  Line 4: [sprite line 2]  [effects]

Info lines (0-1) are pure ASCII/ANSI text — guaranteed alignment.
Sprite lines (2-4) use half-block Unicode — may render wider in some
terminals but no text alignment depends on them.
"""

from .palette import fg, bg, RST, BOLD, SUBTLE, DIM, GOLD, GREEN, RD
from .hp_bar import render_hp_line, get_badge, hp_color
from .flavor import get_flavor_text

# Minimum output lines (padded if fewer). Demo = 5, statusline = 6 (with backdrop padding).
MIN_LINES = 5

# Sprite prefix (indentation for non-backdrop mode)
SP = "  "


# ============================================================
# Model / git / cost formatters
# ============================================================

def format_model(model_id="", display_name=""):
    """Format model as 'Lv.N SPECIES' (Pokemon style).

    Uses display_name for species (e.g. "Opus" -> "OPUS")
    and model_id for level (e.g. "claude-opus-4-6" -> first digit = 4).

    Claude Code JSON provides:
      model.id = "claude-opus-4-6"
      model.display_name = "Opus"
    """
    import re

    # Species from display_name — take first word only
    # Claude Code sends "Opus 4.6 (1M context)", we just want "OPUS"
    species = display_name.split()[0].upper() if display_name else "CLAUDE"

    # Level from model_id version number
    level = "?"
    # Match pattern like "opus-4", "sonnet-4", "sonnet-3-5", "haiku-3-5"
    match = re.search(r'(?:opus|sonnet|haiku)-(\d+)', model_id.lower())
    if match:
        level = match.group(1)

    return f"{fg(GOLD)}{BOLD}Lv.{level}{RST} {fg(GOLD)}{species}{RST}"


def format_git(branch=None, staged=0, modified=0):
    """Format git info: branch +staged ~modified."""
    if not branch:
        return ""
    parts = [f"{fg(SUBTLE)}{branch}{RST}"]
    if staged:
        parts.append(f"{fg(GREEN)}+{staged}{RST}")
    if modified:
        parts.append(f"{fg(GOLD)}~{modified}{RST}")
    return " ".join(parts)


def format_cost_time(cost_usd=0.0, duration_secs=0):
    """Format cost and duration: P$0.42 3m12s."""
    cost = f"{fg(GREEN)}P${cost_usd:.2f}{RST}"
    mins = duration_secs // 60
    secs = duration_secs % 60
    if mins > 0:
        time_str = f"{fg(SUBTLE)}{mins}m{secs:02d}s{RST}"
    else:
        time_str = f"{fg(SUBTLE)}{secs}s{RST}"
    return f"{cost}  {time_str}"


# ============================================================
# Layout builder
# ============================================================

def _build(info_line0, info_line1, sprite_lines, sides=None):
    """Standard builder: 2 info lines + N sprite lines.

    Args:
        info_line0: First info line (model, badge, git)
        info_line1: Second info line (HP, cost, flavor)
        sprite_lines: List of rendered sprite terminal lines (3 for demo, 4 with padding)
        sides: Optional list of side effects per sprite line
    """
    lines = []
    # Info lines (pure text, no half-blocks)
    lines.append(f"{SP}{info_line0}")
    lines.append(f"{SP}{info_line1}")
    # Sprite lines (SP indents the whole sprite/backdrop block)
    for i, sp in enumerate(sprite_lines):
        eff = sides[i] if sides and i < len(sides) else ""
        lines.append(f"{SP}{sp}{eff}")
    while len(lines) < MIN_LINES:
        lines.append("")
    return lines


# ============================================================
# Decoration functions per state
# ============================================================

def decorate_thinking(sprite_lines, tick, session=None):
    """Thinking state: eyes glance, gentle tail sway."""
    s = session or {}

    model = format_model(s.get("model_id", ""), s.get("model_name", "Opus"))
    badge = get_badge(s.get("hp_pct"), is_compacting=False)
    git = format_git(s.get("branch"), s.get("staged", 0), s.get("modified", 0))
    hp = render_hp_line(s.get("hp_pct"), s.get("hp_window"), tick=tick)
    cost_time = format_cost_time(s.get("cost", 0), s.get("duration", 0))

    flavor, _ = get_flavor_text("thinking", s.get("hp_pct"), tick=tick)
    flavor_str = f"  {fg(DIM)}>{RST} {fg(SUBTLE)}{flavor}{RST}" if flavor else ""

    badge_str = f" {badge}" if badge else ""
    git_str = f" {fg(DIM)}|{RST} {git}" if git else ""

    line0 = f"{model}{badge_str}{git_str}"
    line1 = f"{hp}  {cost_time}{flavor_str}"

    return _build(line0, line1, sprite_lines)


def decorate_streaming(sprite_lines, tick, session=None):
    """Streaming state: winking eye, text output."""
    s = session or {}

    model = format_model(s.get("model_id", ""), s.get("model_name", "Opus"))
    badge = get_badge(s.get("hp_pct"))
    git = format_git(s.get("branch"), s.get("staged", 0), s.get("modified", 0))
    hp = render_hp_line(s.get("hp_pct"), s.get("hp_window"), tick=tick)
    cost_time = format_cost_time(s.get("cost", 0), s.get("duration", 0))

    flavor, _ = get_flavor_text("streaming", s.get("hp_pct"), tick=tick)
    flavor_str = f"  {fg(DIM)}|{RST} {fg(GREEN)}>{RST}{fg(SUBTLE)} {flavor}{RST}" if flavor else f"  {fg(DIM)}|{RST} {fg(GREEN)}>{RST}{fg(SUBTLE)} Streaming...{RST}"

    badge_str = f" {badge}" if badge else ""
    git_str = f" {fg(DIM)}|{RST} {git}" if git else ""

    line0 = f"{model}{badge_str}{git_str}"
    line1 = f"{hp}  {cost_time}{flavor_str}"

    return _build(line0, line1, sprite_lines)


def decorate_tool(sprite_lines, tick, session=None):
    """Tool Use state: lightning bolts around sprite."""
    s = session or {}

    tools = s.get("tools", ["Read src/app.ts", "Grep 'handleError'",
                             "Edit utils.ts", "Bash: npm test"])
    tool = tools[tick % len(tools)] if tools else "Working..."

    model = format_model(s.get("model_id", ""), s.get("model_name", "Opus"))
    badge = get_badge(s.get("hp_pct"))
    git = format_git(s.get("branch"), s.get("staged", 0), s.get("modified", 0))
    hp = render_hp_line(s.get("hp_pct"), s.get("hp_window"), tick=tick)
    cost_time = format_cost_time(s.get("cost", 0), s.get("duration", 0))

    badge_str = f" {badge}" if badge else ""
    git_str = f" {fg(DIM)}|{RST} {git}" if git else ""

    line0 = f"{model}{badge_str}{git_str}"
    line1 = f"{hp}  {cost_time}  {fg(DIM)}|{RST} {fg(GOLD)}!{RST} {fg(SUBTLE)}{tool[:25]}{RST}"

    # Lightning effects next to sprite
    bc_list = [220, 178, 228, 220]
    bc = bc_list[tick % len(bc_list)]
    b = f"{fg(bc)}*{RST}"

    side_patterns = [
        [f" {b}",  "",     f" {b}"],
        ["",      f" {b}", ""],
        [f" {b}", f" {b}", ""],
        ["",      "",      f" {b}"],
    ]
    sides = side_patterns[tick % len(side_patterns)]

    return _build(line0, line1, sprite_lines, sides=sides)


def decorate_subagent(sprite_lines, tick, session=None):
    """Subagent state: hearts floating around sprite."""
    s = session or {}
    n_agents = s.get("n_agents", 3)
    agents = s.get("agent_names", ["Dev", "QC", "UX"])
    active = agents[tick % len(agents)] if agents else "Agent"

    hc_list = [RD, 204, 197, 203]
    hc = hc_list[tick % len(hc_list)]
    h = f"{fg(hc)}<3{RST}"

    model = format_model(s.get("model_id", ""), s.get("model_name", "Opus"))
    badge = get_badge(s.get("hp_pct"))
    hp = render_hp_line(s.get("hp_pct"), s.get("hp_window"), tick=tick)
    cost_time = format_cost_time(s.get("cost", 0), s.get("duration", 0))

    hearts = f"{fg(RD)}{'<3 ' * n_agents}{RST}"
    badge_str = f" {badge}" if badge else ""

    line0 = f"{model}{badge_str} {fg(DIM)}|{RST} {hearts}"
    line1 = f"{hp}  {cost_time}  {fg(DIM)}|{RST} {fg(GREEN)}{active}{RST} {fg(SUBTLE)}working...{RST}"

    side_patterns = [
        [f" {h}", "",     ""],
        ["",     f" {h}", ""],
        ["",     "",     f" {h}"],
        [f" {h}", "",     f" {h}"],
    ]
    sides = side_patterns[tick % len(side_patterns)]

    return _build(line0, line1, sprite_lines, sides=sides)


def decorate_compact(sprite_lines, tick, session=None):
    """Compacting state: sleeping Pikachu with ZZZ."""
    s = session or {}

    model = format_model(s.get("model_id", ""), s.get("model_name", "Opus"))
    badge = get_badge(s.get("hp_pct"), is_compacting=True)
    hp = render_hp_line(s.get("hp_pct"), s.get("hp_window"), tick=tick)
    cost_time = format_cost_time(s.get("cost", 0), s.get("duration", 0))

    flavor, _ = get_flavor_text("compacting", s.get("hp_pct"), tick=tick)
    flavor_str = f"  {fg(DIM)}>{RST} {fg(SUBTLE)}{flavor}{RST}" if flavor else ""

    badge_str = f" {badge}" if badge else ""

    line0 = f"{model}{badge_str}"
    line1 = f"{hp}  {cost_time}{flavor_str}"

    # ZZZ effects next to sprite
    z_cycle = tick % 4
    zc_list = [240, 245, 250, 245]
    zc = zc_list[z_cycle]
    z = f"{fg(zc)}z{RST}"

    side_patterns = [
        [f" {z}", "",    ""],
        ["",     f" {z}", ""],
        ["",     "",     f" {z}"],
        [f" {z}", "",    f" {z}"],
    ]
    sides = side_patterns[z_cycle]

    return _build(line0, line1, sprite_lines, sides=sides)


def decorate_ratelimit(sprite_lines, tick, session=None):
    """Rate Limited state: Pokeball wobble, retry countdown."""
    s = session or {}
    mins = s.get("retry_min", max(1, 4 - (tick // 6)))

    model = format_model(s.get("model_id", ""), s.get("model_name", "Opus"))
    badge = get_badge(0, is_rate_limited=True)  # HP=0 when rate limited
    hp = render_hp_line(0, s.get("hp_window"), tick=tick)  # HP = 0
    cost_time = format_cost_time(s.get("cost", 0), s.get("duration", 0))

    flavor, _ = get_flavor_text("ratelimited", hp_pct=0, tick=tick)
    flavor_str = f"  {fg(DIM)}>{RST} {fg(SUBTLE)}{flavor}{RST}" if flavor else ""

    badge_str = f" {badge}" if badge else ""

    line0 = f"{model}{badge_str} {fg(DIM)}|{RST} {fg(SUBTLE)}Retry ~{mins}m{RST}"
    line1 = f"{hp}  {cost_time}{flavor_str}"

    return _build(line0, line1, sprite_lines)
