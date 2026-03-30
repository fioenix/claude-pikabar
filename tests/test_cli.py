"""Tests for pikabar.cli — install/uninstall/update commands."""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock

from pikabar.cli import install, uninstall, update, SETTINGS_PATH


def _with_temp_settings(fn):
    """Run fn with SETTINGS_PATH pointing to a temp file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = os.path.join(tmpdir, ".claude", "settings.json")
        with patch("pikabar.cli.SETTINGS_PATH", fake_path):
            return fn(fake_path)


def test_install_creates_settings():
    def run(path):
        install()
        assert os.path.exists(path)
        with open(path) as f:
            settings = json.load(f)
        assert "statusLine" in settings
        assert settings["statusLine"]["type"] == "command"
        assert "pikabar" in settings["statusLine"]["command"]
        return settings

    _with_temp_settings(run)


def test_install_backs_up_existing():
    def run(path):
        # Create existing settings with a different statusLine
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "other-tool"}}, f)

        install()
        with open(path) as f:
            settings = json.load(f)
        assert "_pikabar_backup_statusLine" in settings
        assert settings["_pikabar_backup_statusLine"]["command"] == "other-tool"
        assert "pikabar" in settings["statusLine"]["command"]

    _with_temp_settings(run)


def test_uninstall_removes_statusline():
    def run(path):
        install()
        uninstall()
        with open(path) as f:
            settings = json.load(f)
        assert "statusLine" not in settings

    _with_temp_settings(run)


def test_uninstall_restores_backup():
    def run(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "other-tool"}}, f)

        install()
        uninstall()
        with open(path) as f:
            settings = json.load(f)
        assert settings["statusLine"]["command"] == "other-tool"
        assert "_pikabar_backup_statusLine" not in settings

    _with_temp_settings(run)


def test_update_refreshes_command():
    """Update should refresh the statusLine command in settings."""
    def run(path):
        install()
        # Verify pikabar is installed
        with open(path) as f:
            before = json.load(f)
        assert "pikabar" in before["statusLine"]["command"]

        # Mock pip install to succeed without actually calling pip
        with patch("pikabar.cli.subprocess.check_call"):
            update()

        with open(path) as f:
            after = json.load(f)
        # Command should still contain pikabar (refreshed, not removed)
        assert "pikabar" in after["statusLine"]["command"]

    _with_temp_settings(run)
