# Decision log

Append-only. Newest last.

## 2026-08-14 — Use HAP-python instead of Homebridge/Home Assistant

**Context**: the owner wants an Apple Home switch that triggers Python code on his Linux laptop ("Jarvis": on→hi, off→bye).

**Decision**: HAP-python, running directly on the laptop.

**Why**: pure Python (the target action IS Python code — zero glue needed), no Node/Homebridge install, no cloud, no extra webhook hop. The laptop itself becomes the HomeKit accessory.

**Rejected**: Homebridge + webhook plugin (extra Node service + HTTP hop), Home Assistant (heavyweight for one switch), cloud services like IFTTT (latency, privacy, dependency).

## 2026-08-14 — Separate `actions.py` from HomeKit plumbing

**Decision**: accessory classes never contain user behavior; they call functions in a sibling `actions.py`.

**Why**: future agents/users edit behavior without touching (or understanding) HAP protocol code.

## 2026-08-14 — Target machine is macOS, not Linux

**Context**: the owner corrected earlier info: the home laptop is a Mac. It's the same machine that holds this project folder (`~/Documents/Home_IoT`).

**Changes**: setup guide rewritten for macOS (Bonjour built-in, firewall allow-prompt, `caffeinate`); systemd unit replaced by launchd agent `com.jarvis.bridge.plist`; no file copying step needed. Python code unchanged — HAP-python is cross-platform.

## 2026-08-14 — Command-switch bridge for Python→Apple Home control

**Context**: the owner wants Python (triggered by "Call Jarvis" on HomePod) to control real Apple Home devices (lights, garden watering). Apple exposes no public API to the Home database; accessories already paired to Apple Home cannot be paired by a second Python controller (aiohomekit route rejected).

**Decision**: refactored standalone switch into a HAP **Bridge** (`jarvis.py`): trigger switch `Jarvis` + command switches (config-driven, currently `Jarvis Light`). Python flips command switches via `home.py`; Home-app automations on the HomePod hub relay to real devices. Fully local, uses only supported HomeKit mechanisms.

**Also considered**: `shortcuts run` CLI (Route 2) — kept as optional helper `home.run_shortcut()`; depends on Home actions being available in macOS Shortcuts, unverified on the owner's machine.

**Migration note**: old `jarvis_switch.py` deleted. If the standalone switch was ever paired: remove from Home app + delete `jarvis.state` before pairing the bridge.

## 2026-08-14 — Jarvis voice sessions (HomePod + iPhone mic + Codex)

**Context**: the owner wants "Siri, Call Jarvis" to open a natural voice conversation: Codex voice agent on the Mac, heard via HomePod (AirPlay output), spoken to via iPhone (Continuity mic), acting as "Jarvis" with the ability to run local device scripts.

**Decisions**:
- Codex voice activated by **Ctrl+M keystroke** via AppleScript (documented shortcut), NOT pixel-clicking — resilient to window layout. Requires Accessibility permission.
- Audio via `SwitchAudioSource` (brew); session saves prior devices and **restores them on Dismiss** — the Mac isn't left hijacked.
- Greeting via `say -v Daniel` after rerouting = audible self-test of the AirPlay path.
- **Control socket** (Unix, 0600) added to the bridge so out-of-process scripts (the voice agent) can flip command switches; `src/devices/homekit.py` is the client. This was required — command switches live inside the bridge process.
- Persona via Codex's native AGENTS.md convention: AGENTS.md routes voice sessions to `agents/jarvis.md`.
- Device routes, local-first: Hue = local CLIP v2 (richer than Apple Home); HomeWizard P1 = local API v2 (verified against official docs); Eve watering = command switches (Matter/Apple-Home-only, no direct path); Bosch = Home Connect cloud (scaffold); Aqara = cloud scaffold, Matter multi-admin via M3 flagged as better future option.

## 2026-08-15 — AirPlay output routing via Control Center (WORKING)

**Problem**: HomePod/AirPlay outputs are invisible to SwitchAudioSource while idle (AirPlay targets only become CoreAudio devices when active), and macOS Shortcuts lacks the iOS-only "Set Playback Destination" action.

**Solution** (verified working): script the menu-bar Sound flyout via accessibility. Key discovery: Control Center exposes each output row as a *checkbox* with no name/title, but with **AXIdentifier `sound-device-<name>`** (e.g. `sound-device-Living Room`, `sound-device-Q-Series Soundbar`). `session.py route_airplay()` clicks by identifier; skips the click if already active (they're toggles). Prereq: Sound icon "Always Show in Menu Bar" + Accessibility permission. Debug helper: `python session.py sound-dump`.

## 2026-08-15 — Aqara sensors via LOCAL Matter multi-admin (implemented)

**Context**: Aqara cloud developer application stuck in moderation; the owner asked for a local alternative. The M3 is a Matter bridge; Matter multi-admin allows a second fabric.

**Decision**: run `python-matter-server` locally (port 5580, storage `matter-data/` — gitignored, contains fabric secrets); commission the M3 via Apple Home's "Turn On Pairing Mode"; `src/devices/matter.py` is a raw-WebSocket CLI client (commission / nodes / sensors / temp / humidity).

**Protocol facts (verified in sandbox against the package)**: envelope `{message_id, command, args}` → `{message_id, result|error_code}`; commands `commission_with_code` (args: code, network_only), `get_nodes`. Attribute paths `"ep/cluster/attr"` decimal: temp `1026/0` (0.01°C), humidity `1029/0` (0.01%), bridged label `57/5`, battery `47/12` (0.5%). Parsing unit-tested. NOT yet run against the real M3 — commissioning pending the owner.

**Cloud route** (`aqara.py` scaffold) kept as optional backup if/when moderation approves.

**Addendum (2026-08-16, post-commissioning)**: real M3 dump facts — single node (id 1), 23 endpoints. Temp/humidity sensors are **composed devices**: labeled parent endpoint (24/27/30) + unlabeled measurement children (25-26/28-29/31-32); `matter.py` merges children into the parent row via Descriptor.PartsList (`29/3`). Bridged NodeLabels are PRODUCT names (duplicates!), so user-facing names live in `src/devices/matter_aliases.py` (endpoint→name; ep numbers stable unless re-paired). **The Air Conditioner IS bridged (ep 2)** as a Matter Thermostat (device type 769, cluster 513). From the real dump: LocalTemperature `513/0`, cooling/heating setpoints `513/17`/`513/18` (writable, limits 16-30 C), SystemMode `513/28` (writable; 0=off 1=auto 3=cool 4=heat), only accepted command is SetpointRaiseLower → we use `write_attribute` instead. NO FanControl cluster — wind speed stays Aqara-app-only. `matter.py ac` verbs implemented and **verified against the real AC 2026-08-16**. Devices addressable by "ep N" until aliased.

**Addendum (same day)**: matter-server runs **on-demand** with the session (the owner's preference — no always-on process): `session.start()` spawns it (pidfile /tmp/jarvis-matter.pid), `session.end()` kills only what it spawned; already-running servers (launchd/manual) are detected via port 5580 and left alone. `matter.py` retries connection for 20 s to cover boot time. Trade-off accepted: no background monitoring while Jarvis is off; first query of a session is slower.

## 2026-08-16 — Published to GitHub; sanitization policy (BINDING)

**Rules for all tracked files, forever**: no personal names, emails, absolute `/Users/<name>` paths (use `~/Documents/Home_IoT`), device serials, or credentials. Machine-specific values go in `config_local.py` (gitignored, overrides config.py via star-import). Secrets stay in `.env`, `*.state`, `matter-data/` — all gitignored. launchd plists use `YOUR_USERNAME` placeholders (activated via sed one-liner in their comments). Owner is referred to as "the owner" in memory/docs. Before any commit: `git grep -il` for personal terms. **One deliberate exception**: the LICENSE copyright line carries the owner's full name, by his explicit choice (2026-08-16) — do NOT sanitize it.

## 2026-08-16 — Jarvis persona: film-inspired, original writing

**Decision**: `agents/jarvis.md` personality modeled on the cinematic J.A.R.V.I.S. archetype — British-butler composure, deadpan understatement, affectionate dry sarcasm toward the owner only, anticipatory competence, wry-but-prompt compliance, wit→zero during real incidents (leak/smoke). Guardrails: ≤1 flourish per reply, act before quipping. All example lines and the config greeting/farewell are ORIGINAL writing in that style — no movie dialogue is reproduced (IP hygiene for the public repo).

## 2026-08-14 — Security-first posture (Mac = always-on IoT commander)

**Context**: the Mac stays on Ethernet permanently as the central home IoT hub, so it's a standing target on the home network.

**Decision**: adopted a written security policy (`docs/security.md`) binding on all future work. Key points: LAN-only (never port-forward; remote access only via Apple home hub relay), `*.state` pairing keys are secrets (`umask 077` + chmod 600 in code, gitignored), everything runs as unprivileged user via LaunchAgent, no hardcoded secrets (env/Keychain), host hardening checklist (FileVault, firewall, SSH off). AGENTS.md rule #6 requires reviewing that doc before adding any capability.
