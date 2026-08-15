"""home — the API actions.py uses to reach Apple Home devices.

Route 1 (preferred): command switches.
    home.turn_on("Jarvis Light")   -> flips the virtual switch; your
    Home-app automation makes the real device follow. Fully local.

Route 2 (optional): macOS Shortcuts.
    home.run_shortcut("Water Garden") -> runs a Shortcut by name via the
    `shortcuts` CLI. Only useful if your macOS Shortcuts app has Home
    actions ("Control My Home") or the shortcut does something else useful.
"""

import logging
import subprocess

log = logging.getLogger("home")

_switches = {}  # name -> CommandSwitch accessory; filled by jarvis.py at startup


def register(name, accessory):
    """Called by jarvis.py. Not for use in actions.py."""
    _switches[name] = accessory


def names():
    """All registered command switch names."""
    return sorted(_switches)


def turn_on(name: str):
    _set(name, True)


def turn_off(name: str):
    _set(name, False)


def _set(name, value):
    switch = _switches.get(name)
    if switch is None:
        raise KeyError(
            f"No command switch named {name!r}. "
            f"Add it to COMMAND_SWITCHES in config.py and restart."
        )
    switch.set(value)
    log.info("Command switch %r -> %s", name, "ON" if value else "OFF")


def run_shortcut(name: str, timeout: int = 30) -> bool:
    """Run a macOS Shortcut by name. Returns True on success."""
    try:
        result = subprocess.run(
            ["shortcuts", "run", name],
            capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        log.error("`shortcuts` CLI not found — are we on macOS?")
        return False
    except subprocess.TimeoutExpired:
        log.error("Shortcut %r timed out after %ss", name, timeout)
        return False
    if result.returncode != 0:
        log.error("Shortcut %r failed: %s", name, result.stderr.strip())
        return False
    return True
