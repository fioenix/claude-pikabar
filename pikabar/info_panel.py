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
from .flavor import get_flavor_text

# Layout constants
SP = ""            # no left margin — flush to terminal left edge
INFO_COL = 20      # absolute column where info text starts
DECORATED_LINES = 5  # 1 above + 3 sprite + 1 pad (Pikachu) or 1 above + 4 sprite (Pokeball)


# ============================================================
# Model / git formatters
# ============================================================

def format_model(model_id="", display_name=""):
    """Format model as 'Lv.N SPECIES' (Pokemon style)."""
    import re
    species = display_name.split()[0].upper() if display_name else "CLAUDE"
    level = "?"
    match = re.search(r'(?:opus|sonnet|haiku)-(\d+)', model_id.lower())
    if match:
        level = match.group(1)
    return f"{BOLD}Lv.{level}{RST} {BOLD}{species}{RST}"


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

    # [1] Model + badge + git + cost
    if line0_override is not None:
        model_line = line0_override
    else:
        model = format_model(s.get("model_id", ""), s.get("model_name", "Opus"))
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

    # [2] HP bar — "5h limit" or "7d limit" or just "limit"
    hp = render_hp_bar(s.get("hp_pct"), tick=tick)
    hp_window = s.get("hp_window")
    if hp_window and s.get("hp_pct") is not None:
        hp_label = f"{fg(SUBTLE)}{hp_window} limit{RST}"
    else:
        hp_label = f"{fg(SUBTLE)}limit{RST}"
    hp_line = f"{hp} {hp_label}"

    # [3] PP bar — "ctx left"
    pp = render_pp_bar(s.get("pp_pct"))
    pp_label = f"{fg(SUBTLE)}ctx left{RST}"
    pp_line = f"{pp} {pp_label}"

    # [4] Extra line (override or empty)
    extra = extra_override if extra_override is not None else ""

    return ["", model_line, hp_line, pp_line, extra]


# ============================================================
# Decoration functions per reaction
# ============================================================

def decorate_idle(sprite_lines, tick, session=None):
    """Idle: calm, nothing notable."""
    info = _info_lines(session)
    return _build(sprite_lines, info)


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

    info = _info_lines(session)
    return _build(sprite_lines, info, sides=sides)


def decorate_committed(sprite_lines, tick, session=None):
    """Committed: hearts float above + beside sprite."""
    hc_list = [RD, 204, 197, 203]
    hc = hc_list[tick % len(hc_list)]
    h = f"{fg(hc)}♥{RST}"

    above_patterns = [
        f"        {h}      {h}",
        f"     {h}        {h}",
        f"          {h}  {h}",
        f"    {h}    {h}",
    ]
    above = above_patterns[tick % len(above_patterns)]

    side_patterns = [
        [f" {h}", "",     ""],
        ["",     f" {h}", ""],
        ["",     "",     f" {h}"],
        [f" {h}", "",     f" {h}"],
    ]
    sides = side_patterns[tick % len(side_patterns)]

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
