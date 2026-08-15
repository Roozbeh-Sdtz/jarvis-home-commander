# Setup: Jarvis voice sessions (HomePod + iPhone mic + Codex)

What happens on "Siri, Call Jarvis": the bridge runs `session.start()` →
Mac output routes to the HomePod, input to your iPhone mic → a greeting
plays in the living room → Codex is focused and voice mode activated
(Ctrl+M). "Dismiss Jarvis" plays a farewell and restores your audio.

## 1. Install the audio switcher

```bash
brew install switchaudio-osx
```

## 2. Find your exact device names

```bash
SwitchAudioSource -a -t output    # find the HomePod's AirPlay name
SwitchAudioSource -a -t input     # find the iPhone Continuity mic name
```

The iPhone mic appears only when the iPhone is nearby, unlocked recently,
same Apple ID, Bluetooth/Wi-Fi on (Continuity). If it's not listed, check
System Settings → General → AirDrop & Handoff.

Put both names in `src/jarvis_switch/config.py` (`AUDIO_OUTPUT`,
`AUDIO_INPUT`). Also set `CODEX_APP` if the app isn't named "Codex", and
customize `GREETING` / `FAREWELL` / `VOICE` (`say -v ?` lists voices —
"Daniel" is pleasantly Jarvis-like).

## 3. Permissions (one-time)

- **Accessibility**: the process running the bridge (Terminal, or Python
  if launched via launchd) needs System Settings → Privacy & Security →
  Accessibility, so it may send the Ctrl+M keystroke.
- **Microphone**: Codex needs mic access (Privacy & Security → Microphone),
  otherwise Ctrl+M silently does nothing.
- **Codex**: open the Codex app once, sign in, and set its working folder
  to `~/Documents/Home_IoT` so it reads `AGENTS.md` → `agents/jarvis.md`
  and becomes Jarvis.
- **Voice chat hotkey**: Codex → Settings → Voice → "Voice chat hotkey" →
  set **⌃⌥⌘J**. This must match `VOICE_HOTKEY_*` in `config.py`. (Note:
  Ctrl+M is *dictation* — typing by voice. The voice chat hotkey starts the
  actual conversational mode, and works globally.)
- **Project context** (verified 2026-08-14): leave Codex's front window on
  a chat **inside the Home_IoT project** (create one chat there once).
  The script then sends Cmd+N (new chat in the same project) followed by
  the voice hotkey — the voice chat attaches to the project and can read
  this folder. The bare hotkey without a project chat in front opens a
  floating, project-less voice chat instead.

## 4. Test without HomeKit

```bash
cd ~/Documents/Home_IoT/src/jarvis_switch
source .venv/bin/activate
python session.py start   # audio should switch, HomePod speaks, Codex opens
python session.py end     # farewell + audio restored
```

When this works, the full chain works: "Siri, Call Jarvis" → same thing.

## Known rough edges

- AirPlay adds ~1-2s latency and the first `say` may clip; if the greeting
  is cut off, add a `time.sleep(2)` before `speak()` in `session.py`.
- If you change the hotkey in Codex settings, mirror it in `config.py`
  (`VOICE_HOTKEY_KEY`, `VOICE_HOTKEY_MODIFIERS`).
- The Mac must not sleep (see setup-jarvis-switch.md).
