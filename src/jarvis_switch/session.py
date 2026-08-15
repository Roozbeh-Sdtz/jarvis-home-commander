"""Jarvis voice session orchestration (macOS only).

start():  save current audio devices -> route output to HomePod, input to
          iPhone mic -> speak greeting through HomePod -> focus Codex and
          activate voice mode (Ctrl+M).
end():    speak farewell -> restore the audio devices that were active before.

Requires:  brew install switchaudio-osx
           Accessibility permission for the process sending the keystroke
           (System Settings -> Privacy & Security -> Accessibility).

Test without HomeKit:  python session.py start   /   python session.py end
"""

import logging
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from config import (
    AUDIO_INPUT,
    AUDIO_OUTPUT,
    AUDIO_OUTPUT_AIRPLAY,
    AUDIO_OUTPUT_SHORTCUT,
    CODEX_APP,
    FAREWELL,
    GREETING,
    MATTER_ON_DEMAND,
    NEW_CHAT_FIRST,
    NEW_CHAT_KEY,
    NEW_CHAT_MODIFIERS,
    VOICE,
    VOICE_HOTKEY_KEY,
    VOICE_HOTKEY_MODIFIERS,
)

log = logging.getLogger("session")

_saved = {}  # audio devices active before the session started


def _run(cmd, timeout=30):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


# --- Audio routing (SwitchAudioSource) ----------------------------------

def _sas(*args):
    if not shutil.which("SwitchAudioSource"):
        log.error("SwitchAudioSource not found. Install: brew install switchaudio-osx")
        return None
    r = _run(["SwitchAudioSource", *args])
    if r.returncode != 0:
        log.error("SwitchAudioSource %s failed: %s", args, r.stderr.strip())
        return None
    return r.stdout.strip()


def current_device(kind):  # kind: "output" | "input"
    return _sas("-c", "-t", kind)


def set_device(kind, name):
    return _sas("-s", name, "-t", kind) is not None


# --- Matter server lifecycle (on-demand with the session) ---------------

MATTER_BIN = Path(__file__).resolve().parent / ".venv" / "bin" / "matter-server"
MATTER_STORAGE = Path(__file__).resolve().parents[2] / "matter-data"
MATTER_PIDFILE = Path("/tmp/jarvis-matter.pid")  # only for servers WE spawned


def _matter_running():
    try:
        with socket.create_connection(("127.0.0.1", 5580), timeout=1):
            return True
    except OSError:
        return False


def start_matter():
    """Spawn matter-server in the background (session start)."""
    if not MATTER_ON_DEMAND:
        return
    if _matter_running():
        log.info("Matter server already running — leaving it as-is")
        return
    if not MATTER_BIN.exists():
        log.warning("matter-server not installed (requirements-matter.txt) — "
                    "Aqara commands won't work this session")
        return
    log_file = open("/tmp/matter.log", "ab")
    proc = subprocess.Popen(
        [str(MATTER_BIN), "--storage-path", str(MATTER_STORAGE)],
        stdout=log_file, stderr=log_file, start_new_session=True,
    )
    MATTER_PIDFILE.write_text(str(proc.pid))
    log.info("Matter server starting in background (pid %s)", proc.pid)


def stop_matter():
    """Stop the matter-server ONLY if this session spawned it."""
    if not MATTER_PIDFILE.exists():
        return  # not ours (launchd/manual) — leave running
    try:
        os.kill(int(MATTER_PIDFILE.read_text().strip()), signal.SIGTERM)
        log.info("Matter server stopped")
    except (ValueError, ProcessLookupError, PermissionError):
        pass
    MATTER_PIDFILE.unlink(missing_ok=True)


# --- AirPlay routing via the menu-bar Sound flyout ----------------------

def _airplay_script(target):
    """Open the Sound flyout, click the output whose AXIdentifier matches.

    Control Center labels output rows as checkboxes with
    AXIdentifier "sound-device-<name>" (discovered via sound-dump,
    2026-08-15). Requires: Sound icon always in menu bar + Accessibility
    permission.
    """
    return (
        'tell application "System Events"\n'
        '  tell process "ControlCenter"\n'
        '    click (first menu bar item of menu bar 1 '
        'whose description contains "Sound" or description contains "sound")\n'
        '    delay 2\n'
        '    set elems to entire contents of window 1\n'
        '    repeat with e in elems\n'
        '      try\n'
        '        if class of e is checkbox then\n'
        '          set i to (value of attribute "AXIdentifier" of e) as text\n'
        f'          if i contains "{target}" then\n'
        '            if (value of e) as text is "1" then\n'
        '              key code 53\n'
        '              return "ok (already active)"\n'
        '            end if\n'
        '            click e\n'
        '            delay 0.5\n'
        '            key code 53\n'
        '            return "ok (clicked " & i & ")"\n'
        '          end if\n'
        '        end if\n'
        '      end try\n'
        '    end repeat\n'
        '    key code 53\n'
        '  end tell\n'
        'end tell\n'
        'return "notfound"'
    )


def dump_sound_menu():
    """`python session.py sound-dump` — list everything in the Sound flyout.

    Use this to find how macOS labels the AirPlay devices, then match
    AUDIO_OUTPUT_AIRPLAY (or fix the click matching) accordingly.
    """
    script = (
        'tell application "System Events"\n'
        '  tell process "ControlCenter"\n'
        '    click (first menu bar item of menu bar 1 '
        'whose description contains "Sound" or description contains "sound")\n'
        '    delay 2\n'
        '    set out to ""\n'
        '    repeat with w in windows\n'
        '      set elems to entire contents of w\n'
        '      repeat with e in elems\n'
        '        set c to ""\n'
        '        set n to ""\n'
        '        set d to ""\n'
        '        set v to ""\n'
        '        set i to ""\n'
        '        set t to ""\n'
        '        try\n'
        '          set c to (class of e) as text\n'
        '        end try\n'
        '        try\n'
        '          set n to name of e\n'
        '        end try\n'
        '        try\n'
        '          set d to description of e\n'
        '        end try\n'
        '        try\n'
        '          set v to (value of e) as text\n'
        '        end try\n'
        '        try\n'
        '          set i to (value of attribute "AXIdentifier" of e) as text\n'
        '        end try\n'
        '        try\n'
        '          set t to title of e\n'
        '        end try\n'
        '        set out to out & c & " | name=" & n & " | desc=" & d '
        '& " | val=" & v & " | id=" & i & " | title=" & t & linefeed\n'
        '      end repeat\n'
        '    end repeat\n'
        '    key code 53\n'
        '    return out\n'
        '  end tell\n'
        'end tell'
    )
    r = _run(["osascript", "-e", script], timeout=120)
    print(r.stdout.strip() or r.stderr.strip() or "(nothing found)")


def route_airplay(target=None):
    """Route output to an AirPlay device by clicking it in the Sound menu."""
    target = target or AUDIO_OUTPUT_AIRPLAY
    r = _run(["osascript", "-e", _airplay_script(target)], timeout=60)
    out = (r.stdout or "").strip()
    if out.startswith("ok"):
        log.info("Output routed to AirPlay %r via Sound menu (%s)", target, out)
        return True
    log.error(
        "AirPlay routing to %r failed: %s %s — is the Sound icon set to "
        "'Always Show in Menu Bar' (System Settings > Control Center)?",
        target, out, r.stderr.strip(),
    )
    return False


# --- Codex activation ---------------------------------------------------

def _keystroke(key, modifiers):
    mods = ", ".join(f"{m} down" for m in modifiers)
    return (f'tell application "System Events" to keystroke "{key}" '
            f'using {{{mods}}}')


def activate_codex():
    """Open a NEW voice chat INSIDE the project.

    Codex's front window must be on a chat in the Home_IoT project.
    Cmd+N -> new chat in the same project; voice hotkey -> voice chat
    attached to it, with folder access. Verified working 2026-08-14.
    """
    steps = [f'tell application "{CODEX_APP}" to activate', 'delay 2']
    if NEW_CHAT_FIRST:
        steps += [_keystroke(NEW_CHAT_KEY, NEW_CHAT_MODIFIERS), 'delay 1']
    steps += [_keystroke(VOICE_HOTKEY_KEY, VOICE_HOTKEY_MODIFIERS)]
    r = _run(["osascript", "-e", "\n".join(steps)])
    if r.returncode != 0:
        log.error("osascript failed: %s", r.stderr.strip())
        log.error(
            "Does this terminal have Accessibility permission? "
            "(System Settings > Privacy & Security > Accessibility)"
        )
        return False
    log.info("Voice chat opened in project via Cmd+N + hotkey")
    return True


# --- Speech -------------------------------------------------------------

def speak(text):
    """Speak via macOS TTS on the CURRENT output device (HomePod once routed)."""
    cmd = ["say", "-v", VOICE, text] if VOICE else ["say", text]
    _run(cmd, timeout=60)


# --- Session lifecycle --------------------------------------------------

def start():
    start_matter()  # boots in background while the greeting plays
    _saved["output"] = current_device("output")
    _saved["input"] = current_device("input")
    log.info("Saved audio devices: %s", _saved)

    if AUDIO_OUTPUT_AIRPLAY:
        # HomePod/soundbar: idle AirPlay targets are invisible to
        # SwitchAudioSource, so click them in the menu-bar Sound flyout.
        if route_airplay():
            time.sleep(2)  # AirPlay connection settles before the greeting
        else:
            log.error("Greeting will play on the current output device")
    elif AUDIO_OUTPUT_SHORTCUT:
        r = _run(["shortcuts", "run", AUDIO_OUTPUT_SHORTCUT], timeout=30)
        if r.returncode != 0:
            log.error("Shortcut %r failed (%s) — greeting will play locally",
                      AUDIO_OUTPUT_SHORTCUT, r.stderr.strip())
        else:
            log.info("Output routed via Shortcut %r", AUDIO_OUTPUT_SHORTCUT)
    elif not set_device("output", AUDIO_OUTPUT):
        log.error("Could not route output to %r — greeting will play locally", AUDIO_OUTPUT)
    if not set_device("input", AUDIO_INPUT):
        log.error("Could not route input to %r — is the iPhone nearby/unlocked?", AUDIO_INPUT)

    speak(GREETING)      # heard on the HomePod = routing confirmed
    activate_codex()     # Codex now listens via the iPhone mic


def end():
    speak(FAREWELL)
    out, inp = _saved.get("output"), _saved.get("input")
    if out:
        set_device("output", out)
    if inp:
        set_device("input", inp)
    stop_matter()
    log.info("Audio devices restored.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    action = sys.argv[1] if len(sys.argv) > 1 else "start"
    {"start": start, "end": end, "airplay": route_airplay,
     "sound-dump": dump_sound_menu}[action]()
