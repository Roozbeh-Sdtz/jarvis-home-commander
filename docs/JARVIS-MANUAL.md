# JARVIS — Owner's Manual

Everything you need to operate and extend Jarvis, in one place.
Project home: `~/Documents/Home_IoT`

---

## 0. Starting Jarvis from the terminal

**The one command** — starts the bridge (background), opens Codex, checks
everything:

```bash
cd ~/Documents/Home_IoT && ./jarvis
```

Also: `./jarvis status` · `./jarvis logs` · `./jarvis down`. First run ever
(unpaired) starts in the foreground so you can scan the pairing QR.

**Under the hood — 1: the brain** (HomeKit bridge; what `./jarvis` runs):

```bash
cd ~/Documents/Home_IoT/src/jarvis_switch
source .venv/bin/activate
python jarvis.py
```

**2 — Start a voice session** (what Siri normally triggers; second tab):

```bash
cd ~/Documents/Home_IoT/src/jarvis_switch
source .venv/bin/activate
python session.py start   # audio → HomePod/iPhone, greeting, Codex voice chat
python session.py end     # farewell + audio restored
```

**Where commands run — rule of thumb:** bridge & voice →
`~/Documents/Home_IoT/src/jarvis_switch`; device scripts →
`~/Documents/Home_IoT/src/devices` (venv:
`source ../jarvis_switch/.venv/bin/activate`). Every `python` command needs
the venv active. `SwitchAudioSource`/`launchctl`/`echo >> .env`: anywhere.

Prerequisite: Codex running, front window on a chat inside the Home_IoT project.

## 1. What Jarvis is

Say **"Siri, Call Jarvis"** near the HomePod → your Mac routes its sound to
the HomePod, its microphone to your iPhone, greets you out loud, and opens
a Codex voice chat inside this project. That chat *is* Jarvis: it knows the
house (via `agents/jarvis.md`) and runs the device scripts below on your
behalf. **"Siri, Dismiss Jarvis"** ends the session and restores your Mac's
audio.

```
Siri/HomePod → Jarvis Bridge (HomeKit) → session.py → Codex voice chat
                                                          │
        Hue lights ── HomeWizard P1 ── Bosch appliances ──┤ (runs scripts)
        Apple Home devices (Eve watering) via homekit.py ─┘
```

---

## 2. The files you'll actually touch

| What | Full path |
|---|---|
| **Main settings** (audio, hotkey, switches, greeting) | `~/Documents/Home_IoT/src/jarvis_switch/config.py` |
| **Device secrets** (IPs, tokens) | `~/Documents/Home_IoT/.env` |
| **Jarvis's behavior** (what it does on on/off) | `~/Documents/Home_IoT/src/jarvis_switch/actions.py` |
| **Jarvis's personality & abilities** | `~/Documents/Home_IoT/agents/jarvis.md` |
| Device scripts | `~/Documents/Home_IoT/src/devices/` |

The Python environment lives at
`~/Documents/Home_IoT/src/jarvis_switch/.venv`. Before running
any script by hand:

```bash
cd ~/Documents/Home_IoT/src/devices          # or src/jarvis_switch
source ../jarvis_switch/.venv/bin/activate   # prompt shows (Jarvis)
```

---

## 3. Audio: pointing sound at the HomePod and mic at the iPhone

Edit `~/Documents/Home_IoT/src/jarvis_switch/config.py`:

```python
AUDIO_OUTPUT = "HomePod Living Room"          # where Jarvis's voice goes
AUDIO_INPUT  = "Your iPhone Microphone"  # what Jarvis hears
```

The names must match **exactly** what macOS reports. To list them:

```bash
SwitchAudioSource -a -t output    # find your HomePod's AirPlay name
SwitchAudioSource -a -t input     # find the iPhone Continuity mic name
```

**AirPlay outputs (HomePod, Q-Series soundbar):** these do NOT appear in
`SwitchAudioSource` while idle, and macOS Shortcuts lacks the iOS-only
"Set Playback Destination" action (checked 2026-08-15). The session
instead clicks the device in the menu-bar Sound flyout via accessibility:

1. One-time: System Settings → Control Center → Sound →
   **Always Show in Menu Bar**.
2. config.py: `AUDIO_OUTPUT_AIRPLAY = "Living Room"` (name exactly as in
   the Sound menu; `""` disables → falls back to `AUDIO_OUTPUT`).
3. Test alone: `python session.py airplay`

Restore on "Dismiss" still works — the previous output is a normal device.

Notes:
- The iPhone mic appears via Continuity: iPhone nearby, same Apple ID,
  Bluetooth + Wi-Fi on. If missing: System Settings → General →
  AirDrop & Handoff.
- Test the routing alone (no Siri needed):
  ```bash
  cd ~/Documents/Home_IoT/src/jarvis_switch && source .venv/bin/activate
  python session.py start    # greeting should come from the HomePod
  python session.py end      # audio devices restored
  ```
- Greeting text/voice: `GREETING`, `FAREWELL`, `VOICE` in the same file.

---

## 4. Electricity & gas — HomeWizard P1  ✅ configured

**Full setup from scratch** (redo if meter reset / IP changed / token lost):

1. HomeWizard app → Settings → Meters → P1 → enable **Local API**; note the
   IP (give it a DHCP reservation in the router); firmware ≥ 6 required.
2. `echo "HW_P1_IP=192.168.x.x" >> ~/Documents/Home_IoT/.env`
3. `python homewizard.py pair` → press the meter's physical button within
   60 s (token saves to `.env` automatically).
4. Verify: `python homewizard.py summary`

**Daily use:**

```bash
python homewizard.py summary   # power now, kWh totals, gas reading
python homewizard.py power     # just current watts (negative = exporting)
python homewizard.py gas       # gas meter reading
```

Ask Jarvis: *"How much power is the house using?" / "What's the gas reading?"*

---

## 5. Appliances — Bosch Home Connect  ✅ configured

**Full setup from scratch:**

1. Account at developer.home-connect.com — **same email** as your Home
   Connect phone-app account.
2. Register Application: ID `Jarvis`, OAuth Flow **Device Flow**, testing
   account blank, redirect blank, all Advanced boxes unchecked. Copy the
   Client ID.
3. `echo "BOSCH_CLIENT_ID=..." >> ~/Documents/Home_IoT/.env`
4. `python bosch.py auth` → open printed URL, log in, approve.
5. Verify: `python bosch.py appliances`

Works from any network (cloud API). Fresh Client IDs may need ~5 min
before `auth` accepts them.

**Daily use:**

```bash
python bosch.py appliances       # washer, dishwasher, dryer + state
python bosch.py status <haId>    # active program + remaining time
```

Ask Jarvis: *"Is the washing machine done?" / "Anything running at home?"*

**Tokens (normal behavior):** access tokens expire ~daily *by design*; the
script auto-refreshes them via the refresh token (~2-month lifetime) since
2026-08-15. If it still reports unauthorized, the refresh token lapsed —
rerun `python bosch.py auth` (expected roughly every 2 months).

---

## 6. Lights — Philips Hue  🔲 do this next (you're home)

Local API on your Hue Bridge Pro — no cloud, instant response.

1. Find the bridge IP: Hue app → Settings → My Hue system → your bridge →
   ℹ️ — or visit https://discovery.meethue.com. Give the bridge a DHCP
   reservation in your router while you're there.
2. Save the IP:
   ```bash
   echo "HUE_BRIDGE_IP=192.168.x.x" >> ~/Documents/Home_IoT/.env
   ```
3. **Walk to the bridge and press the round link button**, then within 30s:
   ```bash
   cd ~/Documents/Home_IoT/src/devices
   source ../jarvis_switch/.venv/bin/activate
   python hue.py pair            # saves HUE_APP_KEY to .env automatically
   ```
4. Test:
   ```bash
   python hue.py lights                  # every light, its state & brightness
   python hue.py on "Living room"        # name matching is forgiving
   python hue.py bri "Living room" 40    # 0–100 %
   python hue.py off "Living room"
   ```

Ask Jarvis: *"Turn on the living room lights" / "Dim the bedroom to 20 percent."*

---

## 7. Sensors — Aqara (M3 hub)  — LOCAL Matter route (implemented)

The M3 is a Matter bridge; a local Matter server on the Mac reads the same
sensors Apple Home sees. No cloud, no developer review, works offline.

1. `pip install -r src/devices/requirements-matter.txt` (same venv; big
   download — CHIP SDK. If wheels fail, use Python 3.12).
2. For SETUP ONLY, run the server manually (venv active):
   `matter-server --storage-path ~/Documents/Home_IoT/matter-data`.
   Afterwards it's **on-demand**: sessions start/stop it automatically
   (`MATTER_ON_DEMAND` in config.py); first query of a session may wait a
   few seconds. launchd plist remains an always-on alternative.
3. Home app → M3 accessory → Accessory Details → **Turn On Pairing Mode**
   → `python matter.py commission <code>` within ~15 min.
4. After ~1 min: `python matter.py sensors` / `python matter.py temp "Bedroom"`.
5. Also working (verified live 2026-08-16): `states` (doors/leaks/smoke),
   `on|off "<plug>"`, `open|close|position "<shade>" N`, and the aircon:
   `ac` (status) / `ac cool 22` / `ac heat 21` / `ac off|auto` (16-30 C;
   fan speed not bridged — Aqara app only).
6. Room names: fill `src/devices/matter_aliases.py` (endpoint → name);
   until then target devices as `"ep N"`.

Sensor names come from the M3's bridged labels — rename in the Aqara app
if unhelpful. The cloud route (`aqara.py`, application awaiting Aqara
moderation) remains as optional backup.

---

## 7b. The Siri chain — pair the bridge & wake phrases

1. Start the bridge (keep running): `cd ~/Documents/Home_IoT/src/jarvis_switch
   && source .venv/bin/activate && python jarvis.py` — prints QR + PIN.
2. iPhone → Home app → + → Add Accessory → scan the terminal QR (or More
   options… → Jarvis Bridge → enter PIN). Accept the "uncertified" warning.
   Both switches arrive: **Jarvis** (trigger) and **Jarvis Light**.
3. Scenes (Siri speaks scene names; several scenes may flip one switch):
   `Call Jarvis` → Jarvis **On** · `Wake up, daddy's home` → Jarvis **On**
   · `Dismiss Jarvis` → Jarvis **Off**.
4. Test with bridge running + Codex on a project chat: "Hey Siri, Call
   Jarvis" → `hi` in terminal → HomePod greeting → voice chat.

Re-pair from scratch: stop bridge, delete `jarvis.state`, remove bridge
from Home app, start again. Phrase tips: the spoken phrase is exactly the
scene name — rename until Siri hears it reliably.

## 8. Apple Home devices — Eve watering & anything else  🔲 needs bridge pairing

Devices that exist only in Apple Home are reached via **command switches**:
virtual switches Python flips, which your Home-app automations react to.

1. Pair the Jarvis Bridge (at home, once): run the bridge, scan the QR from
   the Home app — full steps in `docs/setup-jarvis-switch.md`.
2. Add a switch per routine in
   `~/Documents/Home_IoT/src/jarvis_switch/config.py`:
   ```python
   COMMAND_SWITCHES = ["Jarvis Light", "Jarvis Water Garden"]
   ```
   Restart the bridge — new switches appear in Apple Home automatically.
3. In the Home app, for each switch create two automations:
   *turns on → …* and *turns off → …* (e.g. run the Eve watering scene).
4. Use (bridge must be running):
   ```bash
   python homekit.py list
   python homekit.py on "Jarvis Water Garden"
   ```

Ask Jarvis: *"Water the garden"* — it will confirm first (that's by design).

---

## 8b. Telegram — your pocket link to Jarvis (optional)

Jarvis→you: the agent sends notes/photos worth keeping (`notify.py`).
You→Jarvis: text/photos/voice/videos land in `inbox/` (timestamped; text in
`inbox/messages.md`) and you ask Jarvis to "check what I sent you".
Outbound HTTPS only; the bot ignores everyone but you.

1. @BotFather → `/newbot` → copy token →
   `echo "TELEGRAM_BOT_TOKEN=..." >> ~/Documents/Home_IoT/.env`
2. `cd ~/Documents/Home_IoT/src/devices && source
   ../jarvis_switch/.venv/bin/activate && python telegram_bot.py setup`
   → send any message to the bot (chat id saves automatically).
3. Test: `python notify.py "Hello from the house."`
4. `./jarvis up` starts/stops the bridge from now on.

**How it knows it's you:** `setup` captures your permanent chat ID from the
first message received and saves `TELEGRAM_CHAT_ID` to `.env`; the daemon
silently drops all other senders, and `notify.py` can only write to that
ID. Re-link: delete the `TELEGRAM_CHAT_ID` line and run `setup` again.
Bot hygiene: pick a non-obvious @username, `/setjoingroups` → Disable in
@BotFather, `/revoke` if the token ever leaks.

## 9. Improvement queue (for future dev sessions)

- Bosch: implement token auto-refresh (`bosch.py`).
- Aqara: implement Part B once credentials exist.
- Bridge autostart via launchd
  (`src/jarvis_switch/com.jarvis.bridge.plist`, guide in
  `docs/setup-jarvis-switch.md`).
- Optional: Matter multi-admin for Aqara/Eve to go fully local.

## 10. Troubleshooting quick reference

| Symptom | Fix |
|---|---|
| Greeting plays on Mac speakers | HomePod name wrong in config.py, or different network — re-check `SwitchAudioSource -a -t output` |
| Voice chat opens without project | Codex front window must be on a chat inside Home_IoT before the session starts |
| "not allowed to send keystrokes" | Terminal needs Accessibility permission (System Settings → Privacy & Security) |
| `homekit.py`: "Bridge is not running" | Start it: `python jarvis.py` in `src/jarvis_switch` (venv active) |
| Bosch "Token expired" | `python bosch.py auth` |
| Hue "link button not pressed" | Press the round button, retry `pair` within 30s |
| Any script: "Missing X in .env" | Add that key — see §4-8 or `.env.example` |
| Several .env values suddenly gone | `cp .env.example .env` was re-run — it OVERWRITES. Use `cp -n` if ever unsure. Re-add Client ID + re-run pair/auth |
