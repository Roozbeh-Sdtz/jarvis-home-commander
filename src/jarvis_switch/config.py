"""Bridge configuration. Edit this file to add capabilities.

COMMAND SWITCHES are virtual switches that exist so Python can drive
Apple Home: when actions.py flips one (via home.turn_on/turn_off), a
Home-app automation you create ("When <switch> turns on -> ...") makes
real accessories react. One switch per routine.

After adding a name here:
1. Restart the bridge (the new switch appears in Apple Home automatically).
2. In the Home app create two automations: "<name> turns on -> ..." and
   "<name> turns off -> ...".

Naming tip: prefix with "Jarvis" so Siri never confuses the virtual
switch with the real device ("Jarvis Light" vs your actual "Light").
"""

import os
from pathlib import Path

BRIDGE_NAME = "Jarvis Bridge"
TRIGGER_SWITCH = "Jarvis"  # toggling this in Apple Home runs actions.py

COMMAND_SWITCHES = [
    "Jarvis Light",
]

# --- Voice session (see docs/setup-jarvis-voice.md) ---------------------
CODEX_APP = "Codex"  # macOS app name of the Codex desktop app

# Must MATCH the "Voice chat hotkey" you set in Codex -> Settings -> Voice.
# Recommended: Control+Option+Command+J
VOICE_HOTKEY_KEY = "j"
VOICE_HOTKEY_MODIFIERS = ["control", "option", "command"]

# Voice chat with project context: Codex's front window must be on a chat
# INSIDE the Home_IoT project (create one chat there once). Then Cmd+N
# makes a new chat in the same project, and the voice hotkey attaches to
# it. Verified working 2026-08-14.
NEW_CHAT_FIRST = True
NEW_CHAT_KEY = "n"
NEW_CHAT_MODIFIERS = ["command"]

# Exact device names as listed by:  SwitchAudioSource -a -t output / -t input
# NOTE: AirPlay targets (HomePod "Living Room", AirPlay soundbars) are
# INVISIBLE to SwitchAudioSource until active — use AUDIO_OUTPUT_SHORTCUT
# for those instead.
AUDIO_OUTPUT = "External Headphones"     # CoreAudio fallback output
AUDIO_INPUT = "MacBook Pro Microphone"   # iPhone Continuity mic when home

# AirPlay routing (HomePod "Living Room", Q-Series soundbar):
# macOS Shortcuts has NO "Set Playback Destination" action (iOS-only,
# checked 2026-08-15), so we script the menu-bar Sound flyout instead and
# click the device by name. PREREQUISITE: System Settings -> Control
# Center -> Sound -> "Always Show in Menu Bar".
# Set to "" to disable and fall back to AUDIO_OUTPUT via SwitchAudioSource.
AUDIO_OUTPUT_AIRPLAY = "Living Room"   # name exactly as in the Sound menu

# (kept for future macOS versions that may add the Shortcuts action)
AUDIO_OUTPUT_SHORTCUT = ""

VOICE = "Daniel"  # macOS TTS voice for greeting/farewell (`say -v ?` to list)
# In-character defaults; personalize in config_local.py if you like.
GREETING = ("Good evening, sir. All systems are online, and I have taken "
            "the liberty of listening.")
FAREWELL = "Very good, sir. Going dark — do try not to need me immediately."

# --- Matter server lifecycle --------------------------------------------
# True: the Matter server (Aqara sensors) starts automatically when a
# Jarvis session begins and stops on dismiss — no always-on process.
# If a server is ALREADY running (launchd/manual), the session leaves it
# untouched. False: manage matter-server yourself.
MATTER_ON_DEMAND = True

# --- Control socket (lets device scripts flip command switches) ---------
SOCKET_PATH = os.environ.get(
    "JARVIS_SOCKET", str(Path(__file__).resolve().parent / "control.sock")
)

# --- Machine-specific overrides (NOT tracked by git) --------------------
# Put personal values (your exact device names etc.) in config_local.py —
# it overrides anything above and never reaches the repository.
try:
    from config_local import *  # noqa: F401,F403
except ImportError:
    pass
