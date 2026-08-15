# Device integrations — status & setup

All scripts live in `src/devices/`, run with the project venv, and read
secrets from `<project root>/.env` (copy `.env.example`, `chmod 600 .env`).
Preference order: **local API > cloud API > Apple Home command switch**.

Step-by-step setup lives in **docs/JARVIS-MANUAL.md** — this table tracks status.

| System | Route | Status |
|---|---|---|
| HomeWizard P1 (electricity + gas) | Local API v2 | ✅ **working** (2026-08-14) |
| Bosch washer/dishwasher/dryer | Home Connect cloud API | ✅ **working** (2026-08-14); token auto-refresh TODO |
| Philips Hue (all lights) | Local CLIP v2 on Hue Bridge | ✅ **working** (2026-08-15) |
| Eve watering ×3 (Matter, Apple Home) | Command switches via Jarvis Bridge | 🔲 needs bridge pairing + automations (manual §8) |
| Aqara — sensors, plugs, shades, door/leak/smoke, **AC** (M3 hub) | **Local Matter multi-admin** (matter-server, on-demand with sessions) | ✅ **working** (2026-08-16), AC control verified live. Pending: room aliases in `matter_aliases.py` |
| Aqara cloud API | developer.aqara.com | backup only; application awaiting moderation |

## Notes per system

**Hue** — the bridge is also in Apple Home, but the local Hue API is richer
(exact brightness, colors, effects) and doesn't need automations. Use it as
the primary route for lights.

**HomeWizard P1** — read-only data: current power (negative = exporting),
kWh totals per tariff, gas meter reading. Great for "Jarvis, how much power
are we using?"

**Eve watering** — Matter accessories in Apple Home only. Python can't talk
to them directly; the command-switch + automation pattern is the supported
route. Consider one switch per zone. Watering is irreversible — the voice
agent is instructed to confirm before triggering.

**Bosch** — cloud only, OAuth device flow. Token refresh isn't implemented
yet (re-auth when it expires) — a good next task for a dev agent.

**Aqara** — two paths: quick (cloud developer API, this scaffold) or better
(M3 is a Matter bridge → commission into a second local fabric with
python-matter-server; fully local, no cloud). Decide when needed; record in
memory/decisions.md.
