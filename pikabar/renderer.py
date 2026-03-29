"""Half-block pixel art renderer.

Each terminal character represents 2 pixel rows using the upper half-block
character (U+2580). Foreground = top pixel, background = bottom pixel.
"""

from .palette import fg, bg, RST

# Dark backdrop color for Claude Code mode.
# Transparent pixels become dark blocks so all columns render at the same width.
# (Claude Code's Ink.js renders Unicode blocks wider than ASCII spaces)
BACKDROP = 235  # #262626 — near-black, blends with most dark terminals


def render_line(top_row, bot_row, backdrop=None):
    """Render a single terminal line from two pixel rows.

    Args:
        top_row: List of color values (or None for transparent).
        bot_row: List of color values (or None for transparent).
        backdrop: If set, transparent pixels use this color instead of space.
                  This ensures all columns use block characters (same width).
    """
    cols = max(len(top_row), len(bot_row))
    out = ""
    for c in range(cols):
        top = top_row[c] if c < len(top_row) else None
        bot = bot_row[c] if c < len(bot_row) else None

        # Apply backdrop to transparent pixels
        if backdrop is not None:
            if top is None:
                top = backdrop
            if bot is None:
                bot = backdrop

        if top is None and bot is None:
            out += " "
        elif top == bot:
            out += f"{fg(top)}█{RST}"
        elif top is not None and bot is None:
            out += f"{fg(top)}▀{RST}"
        elif top is None and bot is not None:
            out += f"{fg(bot)}▄{RST}"
        else:
            out += f"{fg(top)}{bg(bot)}▀{RST}"
    return out


def pad_grid(grid, left=1, right=1, top=1, bottom=1):
    """Add transparent padding around a pixel grid.

    Padding cells are None, which become backdrop-colored when
    rendered with backdrop=COLOR. This creates a visible border
    around the sprite that looks intentional, not like a rendering bug.
    """
    width = len(grid[0]) if grid else 0
    new_width = left + width + right
    padded = []
    for _ in range(top):
        padded.append([None] * new_width)
    for row in grid:
        padded.append([None] * left + list(row) + [None] * right)
    for _ in range(bottom):
        padded.append([None] * new_width)
    return padded


def grid_to_lines(grid, backdrop=None):
    """Convert a pixel grid (list of rows) to terminal lines.

    Each pair of pixel rows becomes one terminal line via half-block rendering.
    Pads with an empty row if the grid has an odd number of rows.

    Args:
        grid: 2D list of color values (or None for transparent).
        backdrop: If set, fills transparent pixels with this color.
                  Use for Claude Code where block chars render wider than spaces.
    """
    g = [row[:] for row in grid]
    if len(g) % 2 != 0:
        g.append([None] * len(g[0]))
    return [render_line(g[r], g[r + 1], backdrop=backdrop) for r in range(0, len(g), 2)]
