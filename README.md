# J.A.R.V.I.S. — a voice-first home commander on your Mac

> *"Hey Siri, wake up — daddy's home."*
> Your HomePod answers, your Mac's audio moves to the living room, and a
> conversational AI agent that knows your whole house starts listening
> through your iPhone. Ask it anything: *dim the lights, is the washing
> machine done, how warm is the bedroom, cool the living room to 22.*

A DIY, local-first home assistant that turns an always-on Mac into the
brain of your smart home — built entirely from supported mechanisms, no
jailbreaks, no cloud lock-in, no Homebridge.

## How it works

```
 "Siri, Call Jarvis"  (HomePod / iPhone / Watch)
        │  HomeKit scene flips a virtual switch
        ▼
 Jarvis Bridge  — HAP-python virtual HomeKit bridge on the Mac
        │  switch callback = session orchestrator
        ▼
 session.py — routes Mac audio → HomePod (AirPlay), mic → iPhone
        │     speaks a greeting, opens a Codex voice chat in this project
        ▼
 The voice agent (persona: agents/jarvis.md) runs device scripts:
   ├─ Philips Hue          local CLIP v2 API          (lights)
   ├─ HomeWizard P1        local API v2               (electricity + gas)
   ├─ Aqara via Matter     local multi-admin fabric   (sensors, plugs,
   │                                                   shades, AC, leaks)
   ├─ Bosch Home Connect   cloud API, auto-refresh    (washer/dryer/dishwasher)
   └─ Apple-Home-only devices (e.g. Eve) via command switches:
      Python flips a virtual switch → your Home-app automation reacts
```

Three ideas make this work:

1. **The Mac pretends to be a HomeKit accessory** ([HAP-python](https://github.com/ikalchev/HAP-python)) — that's how Siri reaches Python without any API from Apple.
2. **Command switches** solve Python→Apple-Home control: virtual switches your Home-hub automations react to.
3. **Matter multi-admin** gives Python peer status with Apple Home on the same devices — the same bridge your Home app talks to, one extra local controller.

## Features

- **Custom wake phrases** via HomeKit scenes — any number of them
- **Full-duplex room voice**: HomePod speaks, iPhone listens (Continuity mic)
- **Session lifecycle**: audio devices saved & restored, Matter server started on demand, farewell on dismiss
- **Local-first**: lights, energy, sensors, and AC all work with the internet down
- **Agent-ready repository**: `AGENTS.md` routes AI coding agents (development) and the voice persona (`agents/jarvis.md`); project memory in `memory/` lets any agent continue where the last one stopped
- **Security posture built-in**: no port forwarding, secrets gitignored with 0600 perms, unprivileged user, written policy in `docs/security.md`

## Quick start

Full step-by-step lives in **[docs/JARVIS-MANUAL.md](docs/JARVIS-MANUAL.md)**
(or open `docs/JARVIS-MANUAL.html` for the interactive version). Condensed:

```bash
# 0. Daily driver — after setup, this is the only command you need:
./jarvis                               # bridge up + Codex open + status
./jarvis status | logs | down

# 1. One-time setup: bridge + voice session core
cd src/jarvis_switch
python3 -m venv .venv --prompt Jarvis
source .venv/bin/activate
pip install -r requirements.txt
python jarvis.py                       # pair the QR with Apple Home, once

# 2. Create scenes in the Home app: "Call Jarvis" (switch ON),
#    "Dismiss Jarvis" (OFF) — the scene NAME is your Siri phrase.

# 3. Devices you own (each is optional, see the manual):
cp .env.example .env && chmod 600 .env # secrets live here, never in git
python hue.py pair                     # press the Hue bridge button
python homewizard.py pair              # press the P1 meter button
python bosch.py auth                   # Home Connect device flow
pip install -r requirements-matter.txt # local Matter for Aqara/Matter hubs
python matter.py commission <code>     # share from Apple Home pairing mode
```

Requires: macOS with an always-on Mac, a HomePod or Apple TV (home hub),
Python ≥ 3.10, and the Codex desktop app for the voice agent.

## Repository layout

| Path | Purpose |
|---|---|
| `src/jarvis_switch/` | HomeKit bridge, voice session orchestration, control socket |
| `src/devices/` | One CLI per integration (`hue`, `homewizard`, `bosch`, `matter`, `homekit`) |
| `agents/jarvis.md` | The voice assistant's persona, abilities, and guardrails |
| `AGENTS.md` | Entry point for AI agents (routes voice vs development sessions) |
| `memory/` | Project state + append-only decision log — agents continue seamlessly |
| `docs/` | The owner's manual (md + interactive html), device guides, security policy |

## Hard-won discoveries (so you don't have to)

- Apple Home has **no public API** — the accessory side of HomeKit is your way in, and command switches your way out.
- The global Codex voice hotkey opens a *project-less* chat; a project chat needs the front window on the project + Cmd+N first.
- AirPlay outputs are **invisible to CoreAudio while idle**; macOS Shortcuts lacks "Set Playback Destination" (iOS-only). Clicking the Sound-menu flyout via accessibility works — rows are checkboxes with `AXIdentifier sound-device-<name>`.
- Aqara M3 bridges its Zigbee children into Matter as **composed devices** with product-name labels — merge children via `Descriptor.PartsList` and keep your own alias map.
- Matter thermostats may accept **no mode commands** — write `SystemMode`/setpoint attributes instead.

## Security

Read `docs/security.md` before deploying. Highlights: LAN-only (remote
access via Apple's home-hub relay, never port forwarding), all credentials
in gitignored files with owner-only permissions, HomeKit pairing keys and
Matter fabric storage treated as secrets, everything runs unprivileged.

## License

MIT — see [LICENSE](LICENSE).
