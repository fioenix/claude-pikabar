"""Info panel layout — Pokemon-style statusline display.

Two-zone layout (5 lines):
  Zone 1 (left): sprite + floating effects (above + beside)
  Zone 2 (right): info text space-padded to INFO_COL

  Line 0: [effects above sprite]           (no info — aligns left/right bottom)
  Line 1: [sprite 0] [side effect]         [Lv.N MODEL badge | git]
  Line 2: [sprite 1] [side effect]         [HP bar]
  Line 3: [sprite 2] [side effect]         [PP bar]
  Line 4: [pad / sprite 3 if Pokeball]     [extra/flavor]

Effects REPLACE whitespace at fixed positions — never INSERT.
Info is padded to INFO_COL via spaces (Ink.js does not support CSI CHA).

8 reaction decorators (priority order):
  faint > hit > compacted > thinking > recovered > committed > staging > idle
"""

from .palette import fg, bg, RST, BOLD, SUBTLE, DIM, GOLD, GREEN, RD, visible_len
from .hp_bar import render_hp_bar, render_pp_bar, get_badge
from .flavor import (
    get_flavor_text, get_session_greeting, get_critical_flavor,
    get_evolution_flavor, get_agent_flavor,
)

# Layout constants
SP = ""            # no left margin — flush to terminal left edge
INFO_COL = 20      # absolute column where info text starts
DECORATED_LINES = 5  # 1 above + 3 sprite + 1 pad (Pikachu) or 1 above + 4 sprite (Pokeball)


# ============================================================
# Model / git formatters
# ============================================================

def format_model(model_id="", display_name="", streak_days=0, pokemon_name=None):
    """Format model as 'Lv.N SPECIES' (Pokemon style) + optional streak flame.

    Args:
        model_id: Full model ID string (e.g., "claude-opus-4-6")
        display_name: Display name from Claude Code (e.g., "Opus 4")
        streak_days: Consecutive active days for flame indicator
        pokemon_name: Pokemon species name to display (pichu, pikachu, raichu)
                    If None, derives from display_name like before.
    """
    import re
    level = "?"
    match = re.search(r'(?:opus|sonnet|haiku)-(\d+)', model_id.lower())
    if match:
        level = match.group(1)

    # Use Pokemon species name if provided, otherwise fallback to model name
    if pokemon_name:
        species = pokemon_name.upper()
    else:
        species = display_name.split()[0].upper() if display_name else "CLAUDE"

    base = f"{BOLD}Lv.{level}{RST} {BOLD}{species}{RST}"
    if streak_days >= 2:
        # Flame color escalates: 2-4 = orange, 5-9 = red-orange, 10+ = bright red
        if streak_days >= 10:
            flame_c = 196  # bright red
        elif streak_days >= 5:
            flame_c = 202  # red-orange
        else:
            flame_c = 208  # orange
        # Use ASCII flame char — emoji rendering varies across terminals
        base = f"{base} {fg(flame_c)}x{streak_days}{RST}"
    return base


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


def format_cost(cost_usd):
    """Format session cost: $0.42 — compact, dim when low."""
    if not cost_usd or cost_usd <= 0:
        return ""
    if cost_usd < 0.01:
        return f"{fg(SUBTLE)}<$0.01{RST}"
    if cost_usd < 1.0:
        return f"{fg(SUBTLE)}${cost_usd:.2f}{RST}"
    return f"{fg(GOLD)}${cost_usd:.2f}{RST}"


# ============================================================
# Agent Teams formatters
# ============================================================

def format_agent_label(agent_name, worktree_name=""):
    """Format agent identity for the above info slot (line 0).

    Shows agent name in bold gold + optional worktree location.
    Max ~28 visible chars to fit the panel.
    """
    name = agent_name.upper()
    if len(name) > 14:
        name = name[:13] + "\u2026"  # ellipsis
    label = f"{BOLD}{fg(GOLD)}{name}{RST}"
    if worktree_name:
        wt = worktree_name
        if len(wt) > 12:
            wt = wt[:11] + "\u2026"
        label = f"{label} {fg(DIM)}@ {wt}{RST}"
    return label


def format_party_balls(num_agents=1, tick=0):
    """Render animated Pokemon party ball string for side effects.

    Shows 6 ball slots based on number of active agents:
    - Active balls (●) take turns pulsing in sequence
    - Remaining slots hollow (○)

    Args:
        num_agents: Number of active agents (1-6)
        tick: Frame tick for animation timing
    """
    num_agents = max(1, min(6, num_agents))

    # Which ball is pulsing (cycles through active balls)
    pulse_pos = tick % num_agents

    # Colors
    main_color = 220  # gold
    pulse_color = 228  # bright gold
    empty = f"{fg(DIM)}\u25cb{RST}"  # ○

    # Build balls
    balls = []
    for i in range(6):
        if i < num_agents:
            if i == pulse_pos:
                balls.append(f"{fg(pulse_color)}\u25cf{RST}")  # ◉ bright (pulsing)
            else:
                balls.append(f"{fg(main_color)}\u25cf{RST}")  # ● filled
        else:
            balls.append(empty)  # ○ hollow

    return " " + "".join(balls)


# ============================================================
# Layout builder (two-zone with space-padding)
# ============================================================

def _line(sprite, info_str, above_str=None, right_eff=""):
    """Build one output line: zone 1 (sprite+effect) + zone 2 (info at INFO_COL).

    Uses space-padding instead of CSI CHA (\\033[nG) because Ink.js
    (Claude Code's terminal renderer) does not support absolute column
    positioning. The sprite content width is measured after stripping
    ANSI escapes, then padded to INFO_COL.

    above_str: decoration-only line (no sprite, effects float above).
    right_eff: effect chars placed right after sprite.
    """
    if above_str is not None:
        zone1 = f"{SP}{above_str}"
    else:
        zone1 = f"{SP}{sprite}{right_eff}"
    # Pad zone 1 to INFO_COL (1-indexed), then append info
    pad = max(1, INFO_COL - 1 - visible_len(zone1))
    return f"{zone1}{' ' * pad}{info_str}"


def _build(sprite_lines, info, above="", sides=None):
    """Standard builder: 1 above + sprite + padding = DECORATED_LINES.

    Args:
        sprite_lines: Rendered sprite terminal lines (3 for Pikachu, 4 for Pokeball).
        info: List of info strings for zone 2 (6 items, indexed by line number).
        above: Effect string for the line above sprite.
        sides: List of side effect strings per sprite row.
    """
    lines = []
    # Line 0: above effects + info[0] (normally empty)
    info_0 = info[0] if len(info) > 0 else ""
    lines.append(_line(None, info_0, above_str=above))

    # Sprite lines with side effects + info
    for i, sp in enumerate(sprite_lines):
        inf = info[i + 1] if (i + 1) < len(info) else ""
        eff = sides[i] if sides and i < len(sides) else ""
        lines.append(_line(sp, inf, right_eff=eff))

    # Pad to fixed height, continuing info on pad lines (PP bar, extra)
    idx = len(lines)
    while len(lines) < DECORATED_LINES:
        inf = info[idx] if idx < len(info) else ""
        if inf:
            lines.append(_line("", inf))
        else:
            lines.append("")
        idx += 1
    return lines[:DECORATED_LINES]


# ============================================================
# Common info builder
# ============================================================

def _info_lines(session, badge_override=None, line0_override=None, extra_override=None):
    """Build the 5 right-column info strings.

    Layout (5 lines):
      [0] (empty)              above line — effects only, no info
      [1] model + badge + git  sprite row 0
      [2] HP bar               sprite row 1
      [3] PP bar               sprite row 2
      [4] extra/flavor         pad row
    """
    s = session or {}
    tick = s.get("_tick", 0)
    agent_name = s.get("agent_name", "")
    worktree_name = s.get("worktree_name", "")
    is_agent = bool(agent_name)

    # [0] Above info: agent label when in agent mode
    above_info = ""
    if is_agent:
        above_info = format_agent_label(agent_name, worktree_name)

    # [1] Model + badge + git + cost (always shows Lv.N SPECIES)
    if line0_override is not None:
        model_line = line0_override
    else:
        streak = s.get("streak_days", 0)
        model = format_model(
            s.get("model_id", ""),
            s.get("model_name", "Opus"),
            streak_days=streak,
            pokemon_name=s.get("pokemon_name"),
        )
        if badge_override is not None:
            badge = badge_override
        else:
            badge = get_badge(s.get("hp_pct"))
        badge_str = f" {badge}" if badge else ""
        git = format_git(s.get("branch"), s.get("staged", 0), s.get("modified", 0))
        git_str = f" {fg(DIM)}|{RST} {git}" if git else ""
        cost = format_cost(s.get("cost_usd", 0))
        cost_str = f" {fg(DIM)}|{RST} {cost}" if cost else ""
        model_line = f"{model}{badge_str}{git_str}{cost_str}"

    # [2] HP bar — "5h limit" or "7d limit", or "DANGER" when critical
    hp = render_hp_bar(s.get("hp_pct"), tick=tick)
    hp_pct = s.get("hp_pct")
    hp_window = s.get("hp_window")
    if hp_pct is not None and hp_pct < 10:
        # Feature 4: Critical HP drama — red DANGER label
        hp_label = f"{fg(RD)}{BOLD}DANGER{RST}"
    elif hp_window and hp_pct is not None:
        hp_label = f"{fg(SUBTLE)}{hp_window} limit{RST}"
    else:
        hp_label = f"{fg(SUBTLE)}limit{RST}"
    hp_line = f"{hp} {hp_label}"

    # [3] PP bar — "ctx left"
    pp = render_pp_bar(s.get("pp_pct"))
    pp_label = f"{fg(SUBTLE)}ctx left{RST}"
    pp_line = f"{pp} {pp_label}"

    # [4] Extra line: override > evolution > agent flavor > session greeting > critical HP drama > empty
    pokemon_name = s.get("pokemon_name", "Pikachu")
    if extra_override is not None:
        extra = extra_override
    elif s.get("just_evolved"):
        # Feature 6: Evolution notification (highest priority)
        extra = f"{fg(220)}{get_evolution_flavor(pokemon_name)}{RST}"
    elif is_agent and not s.get("events"):
        # Agent Teams flavor (fioenix feature)
        extra = f"{fg(GOLD)}{get_agent_flavor(agent_name)}{RST}"
    elif "session_start" in s.get("events", []):
        # Feature 1: Session greeting on first call
        extra = f"{fg(228)}{get_session_greeting(pokemon_name)}{RST}"
    elif hp_pct is not None and hp_pct < 10:
        # Feature 4: Critical HP drama flavor text
        extra = f"{fg(RD)}{get_critical_flavor(pokemon_name)}{RST}"
    else:
        extra = ""

    return [above_info, model_line, hp_line, pp_line, extra]


# ============================================================
# Decoration functions per reaction
# ============================================================

def _agent_sides(session, tick=0):
    """Return party balls as side effect list if in agent mode, else None."""
    s = session or {}
    if not s.get("agent_name"):
        return None
    num_agents = s.get("num_agents", 1)
    balls = format_party_balls(num_agents, tick)
    return [balls, "", ""]


def _merge_sides(base_sides, agent_sides):
    """Merge agent side effects with reaction side effects.

    Agent sides (party balls) go on row 0, reaction sides fill the rest.
    If agent has balls on row 0, reaction effect on row 0 is replaced.
    """
    if agent_sides is None:
        return base_sides
    if base_sides is None:
        return agent_sides
    merged = list(agent_sides)
    for i in range(len(base_sides)):
        if i < len(merged) and merged[i]:
            continue  # agent side takes priority
        if i < len(merged):
            merged[i] = base_sides[i]
        else:
            merged.append(base_sides[i])
    return merged


def decorate_idle(sprite_lines, tick, session=None):
    """Idle: calm, nothing notable."""
    sides = _agent_sides(session, tick)
    info = _info_lines(session)
    return _build(sprite_lines, info, sides=sides)


def decorate_staging(sprite_lines, tick, session=None):
    """Staging: files changed or cost spike — sparkles beside sprite."""
    sc_list = [228, 220, 230, 226]
    sc = sc_list[tick % len(sc_list)]
    spark = f"{fg(sc)}*{RST}"

    side_patterns = [
        [f" {spark}", "",          ""],
        ["",          f" {spark}", ""],
        ["",          "",          f" {spark}"],
        [f" {spark}", "",          f" {spark}"],
    ]
    sides = side_patterns[tick % len(side_patterns)]
    sides = _merge_sides(sides, _agent_sides(session, tick))

    info = _info_lines(session)
    return _build(sprite_lines, info, sides=sides)


def decorate_committed(sprite_lines, tick, session=None):
    """Committed: confetti particles float above + beside sprite."""
    # Multi-color confetti — dense celebration particles
    confetti_chars = ["·", "+", "*", "✦", "♥", "·", "+", "*"]
    confetti_colors = [RD, 204, 228, 114, 141, 208, 81, 219]
    import random
    _rng = random.Random(tick)  # deterministic per tick for consistency

    def _particle():
        ch = confetti_chars[_rng.randint(0, len(confetti_chars) - 1)]
        cc = confetti_colors[_rng.randint(0, len(confetti_colors) - 1)]
        return f"{fg(cc)}{ch}{RST}"

    # Dense confetti above: 3-4 particles scattered
    p = [_particle() for _ in range(6)]
    above_patterns = [
        f"    {p[0]}   {p[1]}     {p[2]}  {p[3]}",
        f"      {p[0]}  {p[1]}   {p[2]}    {p[3]}",
        f"   {p[0]}     {p[1]}  {p[2]}   {p[3]}",
        f"     {p[0]}    {p[1]}    {p[2]} {p[3]}",
    ]
    above = above_patterns[tick % len(above_patterns)]

    s1, s2, s3 = _particle(), _particle(), _particle()
    side_patterns = [
        [f" {s1}", "",      f" {s2}"],
        [f" {s1}", f" {s2}", ""],
        ["",      f" {s1}", f" {s2}"],
        [f" {s1}", f" {s2}", f" {s3}"],
    ]
    sides = side_patterns[tick % len(side_patterns)]
    sides = _merge_sides(sides, _agent_sides(session, tick))

    info = _info_lines(session)
    return _build(sprite_lines, info, above=above, sides=sides)


def decorate_recovered(sprite_lines, tick, session=None):
    """Recovered: green sparkles beside sprite."""
    sc_list = [114, 156, 150, 120]
    sc = sc_list[tick % len(sc_list)]
    spark = f"{fg(sc)}✦{RST}"

    side_patterns = [
        [f" {spark}", "",          ""],
        ["",          f" {spark}", ""],
        ["",          "",          f" {spark}"],
        ["",          f" {spark}", ""],
    ]
    sides = side_patterns[tick % len(side_patterns)]
    sides = _merge_sides(sides, _agent_sides(session, tick))

    info = _info_lines(session)
    return _build(sprite_lines, info, sides=sides)


def decorate_thinking(sprite_lines, tick, session=None):
    """Thinking: lightning ⚡ above + beside sprite."""
    bc_list = [220, 178, 228, 220]
    bc = bc_list[tick % len(bc_list)]
    b = f"{fg(bc)}⚡{RST}"

    above_patterns = [
        f"       {b}     {b}",
        f"    {b}        {b}",
        f"         {b}  {b}",
        f"   {b}    {b}",
    ]
    above = above_patterns[tick % len(above_patterns)]

    side_patterns = [
        ["",     f" {b}",  ""],
        [f" {b}", "",      f" {b}"],
        ["",     f" {b}",  f" {b}"],
        [f" {b}", f" {b}", ""],
    ]
    sides = side_patterns[tick % len(side_patterns)]
    sides = _merge_sides(sides, _agent_sides(session, tick))

    info = _info_lines(session)
    return _build(sprite_lines, info, above=above, sides=sides)


def decorate_compacted(sprite_lines, tick, session=None):
    """Compacted: ZZZ float above + beside sleeping sprite."""
    s = session or {}
    badge = get_badge(s.get("hp_pct"), is_compacting=True)

    z_cycle = tick % 4
    zc_list = [240, 245, 250, 245]
    zc = zc_list[z_cycle]

    z_above = [
        f"               {fg(250)}Z{RST}",
        f"             {fg(245)}Z{RST}  {fg(250)}Z{RST}",
        f"           {fg(240)}z{RST}  {fg(245)}Z{RST}  {fg(250)}Z{RST}",
        f"             {fg(240)}z{RST}  {fg(245)}Z{RST}",
    ]
    above = z_above[z_cycle]

    z = f"{fg(zc)}z{RST}"
    side_patterns = [
        [f" {z}", "",    ""],
        ["",     f" {z}", ""],
        ["",     "",     f" {z}"],
        [f" {z}", "",    f" {z}"],
    ]
    sides = side_patterns[z_cycle]
    sides = _merge_sides(sides, _agent_sides(session, tick))

    info = _info_lines(session, badge_override=badge)
    return _build(sprite_lines, info, above=above, sides=sides)


def decorate_hit(sprite_lines, tick, session=None):
    """Hit: sweat drops beside sprite."""
    s = session or {}
    badge = get_badge(s.get("hp_pct"))

    sw_list = [117, 153, 159, 153]
    sw = sw_list[tick % len(sw_list)]
    drop = f"{fg(sw)};{RST}"

    side_patterns = [
        [f" {drop}", "",         ""],
        ["",         f" {drop}", ""],
        [f" {drop}", "",         f" {drop}"],
        ["",         "",         f" {drop}"],
    ]
    sides = side_patterns[tick % len(side_patterns)]
    sides = _merge_sides(sides, _agent_sides(session, tick))

    info = _info_lines(session, badge_override=badge)
    return _build(sprite_lines, info, sides=sides)


def decorate_faint(sprite_lines, tick, session=None):
    """Faint: Pokeball, retry countdown, no effects."""
    s = session or {}
    badge = get_badge(0, is_rate_limited=True)
    mins = s.get("retry_min", max(1, 4 - (tick // 6)))

    retry_line = f"{fg(SUBTLE)}Retry ~{mins}m{RST}"
    info = _info_lines(session, badge_override=badge, extra_override=retry_line)
    return _build(sprite_lines, info)


# ============================================================
# Reaction dispatcher
# ============================================================

DECORATORS = {
    "idle":      decorate_idle,
    "staging":   decorate_staging,
    "committed": decorate_committed,
    "recovered": decorate_recovered,
    "thinking":  decorate_thinking,
    "compacted": decorate_compacted,
    "hit":       decorate_hit,
    "faint":     decorate_faint,
}


def decorate(reaction, sprite_lines, tick, session=None):
    """Dispatch to the correct decorator for a reaction."""
    fn = DECORATORS.get(reaction, decorate_idle)
    return fn(sprite_lines, tick, session=session)


# Backwards-compat aliases
def decorate_compact(sprite_lines, tick, session=None):
    return decorate_compacted(sprite_lines, tick, session=session)

def decorate_ratelimit(sprite_lines, tick, session=None):
    return decorate_faint(sprite_lines, tick, session=session)
