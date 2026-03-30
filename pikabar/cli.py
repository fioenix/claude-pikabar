"""pikabar CLI — install/uninstall/update commands for Claude Code integration.

Usage:
    pikabar install     Auto-configure Claude Code to use pikabar
    pikabar uninstall   Remove pikabar from Claude Code settings
    pikabar update      Pull latest version from GitHub and refresh
    pikabar             (no args, stdin) Run as statusline renderer
"""

import json
import os
import shutil
import subprocess
import sys


SETTINGS_PATH = os.path.expanduser("~/.claude/settings.json")
REPO_URL = "https://github.com/fioenix/claude-pikabar.git"


def _find_statusline_command():
    """Return the best command string for the statusline entry."""
    # If installed via pip, the module is importable system-wide
    return f"{sys.executable} -m pikabar.statusline"


def _load_settings():
    """Load existing settings.json or return empty dict."""
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r") as f:
            try:
                return json.load(f)
            except (json.JSONDecodeError, ValueError):
                return {}
    return {}


def _save_settings(settings):
    """Write settings.json (create ~/.claude/ if needed)."""
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")


def install():
    """Add pikabar statusLine to Claude Code settings."""
    settings = _load_settings()
    command = _find_statusline_command()

    old_statusline = settings.get("statusLine")
    if old_statusline:
        old_cmd = old_statusline.get("command", "")
        if "pikabar" in old_cmd:
            print(f"pikabar is already installed.")
            print(f"  command: {old_cmd}")
            return 0
        # Back up existing statusLine config
        settings["_pikabar_backup_statusLine"] = old_statusline
        print(f"Backed up existing statusLine config.")

    settings["statusLine"] = {
        "type": "command",
        "command": command,
        "padding": 1,
    }
    _save_settings(settings)

    print(f"pikabar installed!")
    print(f"  settings: {SETTINGS_PATH}")
    print(f"  command:  {command}")
    print(f"\nRestart Claude Code to see Pikachu.")
    return 0


def uninstall():
    """Remove pikabar statusLine from Claude Code settings."""
    settings = _load_settings()
    statusline = settings.get("statusLine", {})

    if "pikabar" not in statusline.get("command", ""):
        print("pikabar is not currently installed.")
        return 0

    # Restore backup if exists
    backup = settings.pop("_pikabar_backup_statusLine", None)
    if backup:
        settings["statusLine"] = backup
        print(f"Restored previous statusLine config.")
    else:
        settings.pop("statusLine", None)
        print(f"Removed statusLine config.")

    _save_settings(settings)
    print(f"pikabar uninstalled from {SETTINGS_PATH}")
    return 0


def update():
    """Pull latest from GitHub, reinstall, and refresh settings."""
    from pikabar import __version__ as old_version
    print(f"Current version: {old_version}")
    print(f"Updating from {REPO_URL} ...")

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade",
             f"git+{REPO_URL}", "--quiet"],
        )
    except subprocess.CalledProcessError as e:
        print(f"pip install failed (exit {e.returncode}).")
        print("Try manually: pip install --upgrade git+https://github.com/fioenix/claude-pikabar.git")
        return 1

    # Re-import to get new version (force reload)
    try:
        import importlib
        import pikabar
        importlib.reload(pikabar)
        new_version = pikabar.__version__
    except Exception:
        new_version = "?"

    # Refresh command in settings.json (Python path may have changed)
    settings = _load_settings()
    statusline = settings.get("statusLine", {})
    if "pikabar" in statusline.get("command", ""):
        command = _find_statusline_command()
        settings["statusLine"]["command"] = command
        _save_settings(settings)
        print(f"Refreshed statusLine command.")

    if new_version == old_version:
        print(f"Already up to date: {new_version}")
    else:
        print(f"Updated: {old_version} → {new_version}")
    print("Restart Claude Code to apply changes.")
    return 0


def main():
    """CLI entry point: install | uninstall | update | (default: statusline renderer)."""
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "install":
            sys.exit(install())
        elif cmd == "uninstall":
            sys.exit(uninstall())
        elif cmd == "update":
            sys.exit(update())
        elif cmd in ("--help", "-h", "help"):
            print(__doc__.strip())
            sys.exit(0)
        elif cmd == "--version":
            from pikabar import __version__
            print(f"pikabar {__version__}")
            sys.exit(0)
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: pikabar [install|uninstall|update|--version]")
            sys.exit(1)
    else:
        # No args = statusline mode (reads JSON from stdin)
        from pikabar.statusline import main as statusline_main
        statusline_main()
