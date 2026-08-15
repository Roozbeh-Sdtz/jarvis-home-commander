# Setup: Jarvis Bridge on the Mac

**Requirements**: Python ≥3.9 (`python3 --version`), Mac and iPhone on the **same Wi-Fi network**. Bonjour/mDNS is built into macOS — nothing to install for that.

The project already lives at `~/Documents/Home_IoT` on the Mac.

## 1. Install

```bash
cd ~/Documents/Home_IoT/src/jarvis_switch
python3 -m venv .venv --prompt Jarvis
source .venv/bin/activate
pip install -r requirements.txt
```

(The folder stays `.venv` so tools and the launchd plist find it; `--prompt`
makes your shell show `(Jarvis)` when it's active. macOS has no bare
`python` command — outside the venv use `python3`.)

## 2. Run

```bash
python jarvis.py
```

If macOS asks *"Do you want the application Python to accept incoming network connections?"* → click **Allow**.

The terminal shows a **QR code and an 8-digit PIN**. Leave it running.

## 3. Pair with Apple Home (once)

On the iPhone: **Home app → + → Add Accessory → scan the QR code** in the terminal
(or *More options… → Jarvis Bridge → enter the PIN*). Ignore the "uncertified accessory" warning — expected for DIY accessories.

Pairing the bridge adds **all** its switches at once: `Jarvis` (the voice trigger) and `Jarvis Light` (a command switch Python controls). If you ever paired the old standalone Jarvis switch: remove it in the Home app and delete `jarvis.state` first.

## 4. Test

- "Hey Siri, turn on Jarvis" → terminal prints `hi`
- "Hey Siri, turn off Jarvis" → terminal prints `bye`
- Toggling in the Home app or via HomeKit automations does the same.

## Let Python control your real devices (command switches)

`Jarvis Light` is a *command switch*: Python flips it (`home.turn_on("Jarvis Light")`), and a Home-app automation makes your real light follow. Create the two automations once, on the iPhone:

1. Home app → **Automation** tab → **+** → **An Accessory is Controlled**
2. Choose **Jarvis Light** → *Turns On* → Next → select your real light → set it **On** → Done
3. Repeat: **Jarvis Light** → *Turns Off* → your real light **Off**

These automations run on your **HomePod (home hub)** — fully local. Add more command switches by editing `COMMAND_SWITCHES` in `config.py` (one per routine, e.g. `"Jarvis Garden"`), restarting, and adding the matching automations.

Note: a home hub (HomePod or Apple TV) is required for automations to run.

## Custom Siri phrase: "Call Jarvis"

Switches only respond to "turn on/off …", but **Siri activates Scenes by name alone**:

1. Home app → **+** → **Add Scene** → **Custom**
2. Name it exactly `Call Jarvis`
3. **Add Accessories** → Jarvis → make sure the tile shows it turning **On** → Done
4. Repeat with a scene named `Dismiss Jarvis` that sets the switch **Off**

Now "Hey Siri, Call Jarvis" → `hi`, and "Hey Siri, Dismiss Jarvis" → `bye`.

Caveat: if you have a contact named Jarvis, Siri may try to phone them — pick another phrase like "Wake up Jarvis". Any phrase works as long as it's the scene name.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Accessory not found while pairing | Same Wi-Fi? If firewall is on: System Settings → Network → Firewall → allow Python (or turn firewall off to test) |
| "Accessory not responding" later | Script stopped or Mac asleep — see "Keep the Mac awake" below |
| Want to re-pair | Stop script, delete `jarvis.state`, remove accessory from Home app, start again |

## Keep the Mac awake

A sleeping Mac = unresponsive accessory. Either System Settings → **Battery/Energy** → prevent sleep when plugged in, or run with:

```bash
caffeinate -i python jarvis.py
```

## Make it permanent (optional, launchd)

`com.jarvis.bridge.plist` in this folder is ready for your username/paths. Install it:

```bash
cp com.jarvis.bridge.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.jarvis.bridge.plist
```

Jarvis now starts at login and restarts if it crashes. Watch the hi/bye output:

```bash
tail -f /tmp/jarvis.log
```

Stop it: `launchctl unload ~/Library/LaunchAgents/com.jarvis.bridge.plist`

## Customize

Edit `actions.py` — put any Python in `on_turn_on()` / `on_turn_off()`. Control Home devices with `home.turn_on("<command switch>")` / `home.turn_off(...)`; add switches in `config.py`. Optionally, `home.run_shortcut("Name")` runs a macOS Shortcut by name (check whether your Shortcuts app has "Home" actions — then shortcuts can set scenes directly).
