"""Smoke test — verify the statusline script runs end-to-end."""

import subprocess
import sys
import json


def test_statusline_empty_json():
    """Empty JSON input should produce output without crashing."""
    result = subprocess.run(
        [sys.executable, "-m", "pikabar.statusline"],
        input="{}",
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert len(result.stdout.strip()) > 0


def test_statusline_full_json():
    """Full Claude Code JSON should produce multi-line output."""
    data = json.dumps({
        "model": {"id": "claude-opus-4-6", "display_name": "Opus"},
        "cost": {"total_cost_usd": 0.42, "total_duration_ms": 192000},
        "rate_limits": {"five_hour": {"used_percentage": 28}},
        "context_window": {"used_percentage": 15},
    })
    result = subprocess.run(
        [sys.executable, "-m", "pikabar.statusline"],
        input=data,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    lines = result.stdout.strip().split("\n")
    assert len(lines) >= 3  # At minimum: above + sprite lines


def test_statusline_malformed_json():
    """Malformed JSON should not crash — graceful fallback."""
    result = subprocess.run(
        [sys.executable, "-m", "pikabar.statusline"],
        input="not json at all",
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
