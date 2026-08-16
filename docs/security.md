# Security — home IoT commander (always-on Mac on Ethernet)

This Mac is permanently on the home network and runs accessories that execute code. Treat it accordingly.

## Threat model (what we're defending against)

1. **Someone on the LAN pairing with an unpaired accessory** — an advertised HAP accessory accepts pairing from anyone who has the PIN until the first controller pairs.
2. **Theft of pairing keys** — `jarvis.state` contains the accessory's long-term keys.
3. **The internet** — the accessory must never be reachable from outside the LAN.
4. **Privilege escalation via actions** — `actions.py` executes arbitrary code; a bug there runs with the daemon's privileges.
5. **Compromise of the Mac itself** — it's the hub; harden the host.

## What the protocol already gives us

HomeKit (HAP) pairing uses SRP; sessions are end-to-end encrypted (ChaCha20-Poly1305). After the first pairing, the accessory rejects new controllers unless you add them via Apple Home. This is real security — the weak points are around it, not in it.

## Rules for this project

### Pairing & keys
- **Pair immediately after first launch.** Don't leave an unpaired accessory advertising overnight.
- `*.state` files are secrets: never commit, copy, or back them up to cloud sync. The code sets `umask 077` so they're created readable by your user only.
- To decommission an accessory: remove it in the Home app **and** delete its `.state` file.

### Network
- **No port forwarding. Ever.** For remote access use Apple's hub path (HomePod/Apple TV as home hub) — Apple relays it encrypted; the Mac stays LAN-only.
- Keep the macOS firewall **on**; allow only the incoming Python connection it asks about.
- If the router supports it, put untrusted IoT gadgets (cameras, plugs, etc.) on a separate VLAN/guest network. This Mac stays on the trusted segment with the iPhone.
- Optional: pin the accessory to the Ethernet interface by passing `address="<ethernet-ip>"` to `AccessoryDriver` so it never listens on Wi-Fi.

### Code & privileges
- Everything runs as the normal user via a **LaunchAgent** — never root, never `sudo` inside `actions.py`.
- Secrets needed by future actions (API keys, tokens): environment variables or macOS Keychain (`security` CLI), never hardcoded in the repo.
- Validate/limit what actions do: prefer specific commands over shelling out with interpolated strings; no `eval`, no building shell commands from external input.
- Keep dependencies updated: `pip list --outdated` in the venv periodically; update macOS itself with auto-updates on.

### Host hardening (one-time checklist)
- [ ] FileVault on (System Settings → Privacy & Security)
- [ ] Automatic macOS updates on
- [ ] Remote Login (SSH) off — or key-only if needed
- [ ] Screen Sharing off unless actively used
- [ ] Strong login password, screen locks when idle
- [ ] Firewall on (Network → Firewall), stealth mode on

### Repo hygiene
- `.gitignore` excludes `*.state`, `.venv/`, `__pycache__/`, `.env`. Keep it that way if the project ever gets a remote.
- Logs (`/tmp/jarvis.log`) shouldn't contain secrets — print events, not credentials.

## Capability register (append when adding capability)

**Control socket** (`control.sock`, added 2026-08-14): Unix domain socket,
0600, lets local processes flip command switches. Risk: any process running
as this user can drive Home automations. Mitigation: filesystem-only (never
TCP), single-user Mac, commands limited to on/off of pre-declared switches.

**`.env` device secrets** (added 2026-08-14): Hue app key, HomeWizard token,
Bosch OAuth tokens. Risk: full device/API access if leaked. Mitigation:
0600 perms, gitignored, voice agent explicitly forbidden from reading it
(agents/jarvis.md); local tokens only work on the LAN anyway.

**Voice agent** (agents/jarvis.md): can execute the device scripts. Risk:
prompt injection / misfire triggering actuators. Mitigation: agent must
confirm before irreversible actions (watering); scripts expose narrow
verbs only (on/off/read), no shell passthrough; appliances are read-only.

**Local Matter server** (added 2026-08-15): `matter-server` on port 5580,
fabric credentials in `matter-data/` (gitignored — treat like `*.state`:
never copy or commit). Risk: a Matter controller can command devices, not
just read. Mitigation: localhost use only — keep the firewall ON so the
port isn't reachable from the LAN; the M3 remains primarily paired to
Apple Home (removing our fabric in the Aqara/Home app revokes access).

**Telegram bridge** (added 2026-08-16): long-polling daemon (outbound HTTPS
only — policy-compliant, no ports). Risks: bot token in `.env` grants
message access (mitigate: 0600, gitignored, revocable via @BotFather);
inbound media lands in `inbox/` (gitignored — personal content); the bridge
hard-filters on the owner's chat id, so strangers messaging the bot are
dropped before any processing. The agent may read inbox media but must
never send `.env` or repo secrets out via notify.py.

## For future agents

Any new accessory or action MUST be reviewed against this file before deployment. If you add capability (network calls, subprocess, file writes), append the risk and mitigation to this doc.
