# Agent instructions — Home_IoT

**ROUTING — read this first.** Two kinds of AI sessions run in this folder:

1. **Jarvis voice sessions** (Codex opened for spoken conversation, typically
   right after the owner says "Siri, Call Jarvis"): STOP here and follow
   `agents/jarvis.md` instead. You are Jarvis, a home assistant — not a developer.
   If the session begins with casual/spoken requests about the home (lights,
   temperature, energy, watering, appliances), it's a voice session.
2. **Development sessions** (building/extending this project): continue below.

---

You are an AI agent working on the owner's home automation project. Read this file first, then `memory/project-state.md`.

## Ground rules

1. **Read before acting**: `memory/project-state.md` (current state) and `memory/decisions.md` (why things are the way they are).
2. **Update memory after every meaningful change**: append to `memory/decisions.md` for architectural choices; rewrite the relevant section of `memory/project-state.md` for state changes.
3. **Keep it expandable**: new accessories go in `src/<accessory_name>/` as self-contained modules. Behavior (what happens on events) lives in each accessory's `actions.py`, separate from HomeKit plumbing.
4. **Target environment**: the code runs on the owner's Mac (macOS), same Wi-Fi network as his iPhone. The project folder IS on that Mac at `~/Documents/Home_IoT`. Agent sandboxes are Linux — you can import/unit-test HAP-python there, but never pair/run the real accessory from a sandbox.
5. **Docs**: every user-facing feature gets a guide in `docs/`.
6. **Security first**: this Mac is an always-on IoT commander on the home network. Before adding any capability, read `docs/security.md` and comply — no root/sudo, no hardcoded secrets, no exposing ports beyond the LAN, `*.state` files are secret. Append new risks + mitigations to that doc.

## Architecture summary

- HAP-python (pure Python HomeKit Accessory Protocol) — the laptop advertises itself as a HomeKit accessory via mDNS.
- Each accessory = one directory under `src/` with: the accessory class, an `actions.py` with the user's custom behavior, `requirements.txt`, and optional launchd plist (macOS autostart).
- Pairing state persists in `*.state` files (gitignore-worthy, machine-specific — never copy between machines).

## The bridge pattern (current architecture)

`src/jarvis_switch/jarvis.py` runs a single HAP **Bridge** hosting all accessories:

- **Trigger switches** (HomeKit→Python): user/Siri toggles them; callbacks run `actions.py`.
- **Command switches** (Python→HomeKit): `actions.py` calls `home.turn_on/turn_off("<name>")`; Home-app automations (created by the owner in the UI, running on his HomePod hub) make real accessories follow. This is the ONLY way Python controls devices already paired to Apple Home — there is no public API, and re-pairing them to a Python controller is not possible.

## Extending

- New command switch: add name to `COMMAND_SWITCHES` in `config.py`, restart; then the owner must add the matching on/off automations in the Home app (tell him — agents can't do this step).
- New accessory type (`Lightbulb`, `TemperatureSensor`, …): add a class in `jarvis.py`, add to the bridge — see HAP-python docs.
- Never rename paired switches or delete `jarvis.state` casually: both break pairing/automations.
