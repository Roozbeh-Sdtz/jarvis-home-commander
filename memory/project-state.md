# Project state

_Last updated: 2026-08-14_

## Status

- **Jarvis switch**: implemented, verified in sandbox (imports + accessory instantiation). NOT yet deployed/paired on the Linux laptop — waiting for the owner to run it there.

## Deployed environment

- Target: the owner's **Mac** (macOS), wired **Ethernet**, always on — the central home IoT commander. Project folder lives on it at `~/Documents/Home_IoT`.
- Security policy in force: `docs/security.md` (LAN-only, unprivileged user, state files secret). Host-hardening checklist there is NOT yet confirmed done by the owner.
- Nothing installed yet by agents (no venv, not paired). Setup is manual per `docs/setup-jarvis-switch.md`.

## Components

| Component | Path | State |
|---|---|---|
| Launcher | `./jarvis` (repo root) | one-command server start: `up` (bg bridge + Codex + Telegram bridge + checks, foreground if unpaired), `status`, `logs`, `down` |
| Telegram bridge | `src/devices/telegram_bot.py` + `notify.py` | code complete, offline-tested 2026-08-16. Pending owner: BotFather token → .env → `setup` → test notify |
| Jarvis Bridge | `src/jarvis_switch/jarvis.py` | bridge: `Jarvis` trigger + `Jarvis Light` command switch + control socket; sandbox-tested |
| Voice session | `src/jarvis_switch/session.py` | **VERIFIED on real Mac 2026-08-14**: audio routing + greeting + Codex voice chat WITH project context (recipe: front window on a project chat → Cmd+N → global voice hotkey ⌃⌥⌘J). Requires terminal Accessibility permission |
| Control socket | `src/jarvis_switch/control.py` | on/off/list via Unix socket 0600; sandbox-tested end-to-end |
| home API | `src/jarvis_switch/home.py` | `turn_on/turn_off/names`, `run_shortcut` |
| Voice persona | `agents/jarvis.md` | Jarvis identity + device command map (AGENTS.md routes to it) |
| Hue | `src/devices/hue.py` | **WORKING 2026-08-15** — paired, lights controllable |
| HomeWizard P1 | `src/devices/homewizard.py` | **WORKING 2026-08-14** — paired, token in .env, tested live |
| Apple Home CLI | `src/devices/homekit.py` | sandbox-tested via socket |
| Bosch | `src/devices/bosch.py` | **WORKING** — Device Flow app "Jarvis". Token auto-refresh added 2026-08-15 (access token expires daily by design; refresh token ~2 months) |
| Aqara — local Matter | `src/devices/matter.py` + matter-server | **FULLY WORKING 2026-08-16**: sensors reading live; **AC control verified on real hardware** (`ac cool/heat/off/auto`, setpoints 16-30 C via write_attribute; no fan control — not bridged). On-demand lifecycle with sessions. Pending: the owner fills `matter_aliases.py` (room names) |
| Aqara — cloud | `src/devices/aqara.py` | backup stub; developer application awaiting Aqara moderation |

Full voice pipeline (session → greeting → project voice chat → Jarvis persona → runs bosch.py live) **verified end-to-end 2026-08-14** at university (no HomePod).

User-side steps pending: set AUDIO_OUTPUT to the HomePod name (the owner is home now, doing this via docs/JARVIS-MANUAL.md §3); hue pair (§6); Aqara Part A (§7); pair Jarvis Bridge + scenes + automations (§8); launchd autostart.

**docs/JARVIS-MANUAL.md is the canonical human guide**; **docs/JARVIS-MANUAL.html** is its interactive twin (the owner's preferred view — dark themed, copy buttons, persistent checklist). Agents: when anything changes, update BOTH.

## Siri phrases

- Custom phrase via HomeKit Scenes: "Call Jarvis" (on) / "Dismiss Jarvis" (off) — user creates these in the Home app, see setup guide. Scenes are iPhone-side only; no code involved.

## Next likely steps

- Replace print statements in `src/jarvis_switch/actions.py` with real automation.
- If more accessories are added, migrate to an AccessoryBridge (see AGENTS.md).
- Optional: install launchd agent (`src/jarvis_switch/com.jarvis.bridge.plist`) so it survives reboots/login.

## Open questions

- Which Python version is on the Mac? (Guide assumes ≥3.9 via `python3`.)
