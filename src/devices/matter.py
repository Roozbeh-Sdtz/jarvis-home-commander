#!/usr/bin/env python3
"""Aqara sensors (M3 hub) via LOCAL Matter — no cloud, no developer review.

The M3 is a Matter bridge. Matter multi-admin lets a second, local
controller (python-matter-server on this Mac) read the same sensors that
Apple Home sees. Fully local, works without internet.

Setup (once):
    1. pip install -r requirements-matter.txt        # same venv
    2. Start the Matter server (keep running, or use the launchd plist):
         matter-server --storage-path ~/Documents/Home_IoT/matter-data
    3. iPhone Home app -> the M3 hub accessory -> Accessory Details ->
       "Turn On Pairing Mode" -> note the setup code (e.g. 1234-567-8901).
    4. python matter.py commission 1234-567-8901
    5. python matter.py sensors

Usage — read:
    python matter.py sensors            # every temp/humidity sensor + battery
    python matter.py temp "Bedroom"     # one reading by (partial) name
    python matter.py humidity "Bedroom"
    python matter.py states             # doors / leak sensors / smoke (booleans)
    python matter.py nodes              # nodes/endpoints overview
    python matter.py ep 2               # debug: all attributes of one endpoint
    python matter.py raw                # full JSON dump

Friendly names: fill src/devices/matter_aliases.py (endpoint -> room name)
so "Bedroom" works instead of "ep 24". Until then, target devices by
endpoint: e.g. on "ep 23".

Usage — control (Matter is bidirectional):
    python matter.py on "Air Purifier"      # smart plugs (OnOff cluster)
    python matter.py off "Air Purifier"
    python matter.py open "Roller Shade"    # window coverings
    python matter.py close "Roller Shade"
    python matter.py position "Roller Shade" 40   # 0=closed .. 100=open

Usage — air conditioner (Matter thermostat):
    python matter.py ac                 # status: room temp, mode, setpoints
    python matter.py ac off             # modes: off | cool | heat | auto
    python matter.py ac cool 22         # cool to 22 C (also sets mode)
    python matter.py ac heat 21         # heat to 21 C (also sets mode)
    (fan speed is not bridged — Aqara app only)

Note: only what the M3 bridges into Matter is visible/controllable —
proprietary features (e.g. the IR aircon controller) may not appear.

Protocol verified against python-matter-server (see memory/decisions.md).
"""

import asyncio
import json
import sys

import aiohttp

URL = "ws://127.0.0.1:5580/ws"

# Matter cluster/attribute suffixes; runtime paths are "<endpoint>/<this>"
TEMP = "1026/0"      # TemperatureMeasurement.MeasuredValue  (unit: 0.01 C)
HUMIDITY = "1029/0"  # RelativeHumidityMeasurement.MeasuredValue (0.01 %)
LABEL = "57/5"       # BridgedDeviceBasicInformation.NodeLabel
BATTERY = "47/12"    # PowerSource.BatPercentRemaining (unit: 0.5 %)
ONOFF = "6/0"        # OnOff.OnOff (bool) — plugs/switches
COVER = "258/0"      # WindowCovering.Type — presence marks a shade
BOOL = "69/0"        # BooleanState.StateValue — door contact / leak sensors
PARTS = "29/3"       # Descriptor.PartsList — children of a composed device

# Thermostat cluster (513) — the Air Conditioner (verified from ep 2 dump)
AC_LOCAL_TEMP = "513/0"    # LocalTemperature (0.01 C)
AC_COOL_SET = "513/17"     # OccupiedCoolingSetpoint (0.01 C, writable)
AC_HEAT_SET = "513/18"     # OccupiedHeatingSetpoint (0.01 C, writable)
AC_MODE = "513/28"         # SystemMode (writable)
AC_MODES = {"off": 0, "auto": 1, "cool": 3, "heat": 4}
AC_MODE_NAMES = {v: k for k, v in AC_MODES.items()}
AC_MIN, AC_MAX = 16, 30    # setpoint limits from the device (1600..3000)

try:
    from matter_aliases import ALIASES  # endpoint -> your room/device name
except ImportError:
    ALIASES = {}


async def _rpc(*commands):
    """Send commands over the server's WebSocket API.

    The server starts on demand with a Jarvis session, so it may still be
    booting — retry for up to ~20 s before giving up.
    """
    for attempt in range(20):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(URL, max_msg_size=2 ** 26) as ws:
                    await ws.receive_json()  # server-info greeting
                    results = []
                    for idx, (cmd, args) in enumerate(commands):
                        await ws.send_json(
                            {"message_id": str(idx), "command": cmd,
                             "args": args}
                        )
                        while True:
                            msg = await ws.receive_json()
                            if msg.get("message_id") != str(idx):
                                continue  # unsolicited event push — ignore
                            if "error_code" in msg:
                                sys.exit(f"Matter server error: "
                                         f"{msg.get('details') or msg}")
                            results.append(msg.get("result"))
                            break
                    return results
        except aiohttp.ClientError:
            if attempt == 0:
                print("Matter server not up yet — waiting...", file=sys.stderr)
            await asyncio.sleep(1)
    sys.exit(
        "Matter server not reachable after 20 s. It starts automatically "
        "with a Jarvis session; to run it manually:\n"
        "  matter-server --storage-path ~/Documents/Home_IoT/matter-data"
    )


def _endpoints(node):
    """{"ep/cluster/attr": val} -> {ep: {"cluster/attr": val}}"""
    grouped = {}
    for path, value in (node.get("attributes") or {}).items():
        endpoint, rest = path.split("/", 1)
        grouped.setdefault(endpoint, {})[rest] = value
    return grouped


def _parent_map(endpoints):
    """child endpoint -> parent endpoint, from Descriptor.PartsList."""
    parent = {}
    for endpoint, attrs in endpoints.items():
        parts = attrs.get(PARTS)
        if isinstance(parts, list):
            for child in parts:
                try:
                    parent[int(child)] = int(endpoint)
                except (TypeError, ValueError):
                    continue
    return parent


def _label_for(root, labels, node_id):
    """Alias > bridged label (+[ep] to disambiguate duplicates) > fallback."""
    if root in ALIASES:
        return ALIASES[root]
    if root in labels:
        return f"{labels[root]} [ep {root}]"
    return f"node {node_id} ep {root}"


def _sensor_rows(nodes):
    """One row per composed DEVICE (children merged into their parent)."""
    rows = {}
    for node in nodes:
        endpoints = _endpoints(node)
        parent = _parent_map(endpoints)
        labels = {int(ep): a[LABEL] for ep, a in endpoints.items() if a.get(LABEL)}
        for endpoint, attrs in endpoints.items():
            values = {"temp": attrs.get(TEMP), "humidity": attrs.get(HUMIDITY),
                      "battery": attrs.get(BATTERY)}
            if all(v is None for v in values.values()):
                continue
            root = parent.get(int(endpoint), int(endpoint))
            key = (node.get("node_id"), root)
            row = rows.setdefault(key, {
                "label": _label_for(root, labels, node.get("node_id")),
                "temp": None, "humidity": None, "battery": None,
            })
            for field, value in values.items():
                if value is not None:
                    row[field] = value
    # only devices that actually measure temp/humidity (skip battery-only)
    return [r for r in rows.values()
            if r["temp"] is not None or r["humidity"] is not None]


def _fmt(row):
    parts = []
    if row["temp"] is not None:
        parts.append(f"{row['temp'] / 100:.1f} C")
    if row["humidity"] is not None:
        parts.append(f"{row['humidity'] / 100:.0f} %rh")
    if row["battery"] is not None:
        parts.append(f"bat {row['battery'] / 2:.0f} %")
    return f"{row['label']:<32} {'  '.join(parts)}"


def _find(rows, name):
    matches = [r for r in rows if name.lower() in r["label"].lower()]
    if not matches:
        sys.exit(f"No device matching {name!r}. Try: python matter.py nodes")
    if len(matches) > 1:
        sys.exit("Ambiguous, matches: " + ", ".join(r["label"] for r in matches))
    return matches[0]


def _device_rows(nodes, *suffixes):
    """Endpoints that carry any of the given cluster/attribute suffixes."""
    rows = []
    for node in nodes:
        endpoints = _endpoints(node)
        parent = _parent_map(endpoints)
        labels = {int(ep): a[LABEL] for ep, a in endpoints.items() if a.get(LABEL)}
        for endpoint, attrs in endpoints.items():
            if any(s in attrs for s in suffixes):
                ep = int(endpoint)
                root = parent.get(ep, ep)
                # alias may target the acting endpoint OR its labeled parent
                label = (ALIASES.get(ep) or ALIASES.get(root)
                         or _label_for(root, labels, node.get("node_id")))
                rows.append({
                    "node": node.get("node_id"),
                    "endpoint": ep,
                    "label": label if ALIASES.get(ep) or ALIASES.get(root)
                             else f"{label}" if str(ep) == str(root)
                             else f"{label} (ep {ep})",
                    "attrs": attrs,
                })
    return rows


async def _write(row, suffix, value):
    await _rpc(("write_attribute", {
        "node_id": row["node"],
        "attribute_path": f"{row['endpoint']}/{suffix}",
        "value": value,
    }))


async def _command(row, cluster_id, command_name, payload=None):
    await _rpc(("device_command", {
        "node_id": row["node"],
        "endpoint_id": row["endpoint"],
        "cluster_id": cluster_id,
        "command_name": command_name,
        "payload": payload or {},
    }))


async def main():
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "sensors"

    if cmd == "commission" and len(sys.argv) >= 3:
        code = sys.argv[2]
        result = (await _rpc(
            ("commission_with_code", {"code": code, "network_only": True})
        ))[0]
        node_id = result.get("node_id") if isinstance(result, dict) else result
        print(f"Commissioned. Node id: {node_id}")
        print("Give it ~1 minute to interview the bridge, then run: "
              "python matter.py sensors")
        return

    nodes = (await _rpc(("get_nodes", {})))[0] or []
    if cmd == "raw":
        print(json.dumps(nodes, indent=2, default=str))
    elif cmd == "ep" and len(sys.argv) >= 3:
        # Debug: dump all attributes of one endpoint (e.g. the aircon, ep 2)
        target = sys.argv[2]
        for node in nodes:
            endpoints = _endpoints(node)
            if target in endpoints:
                print(f"node {node.get('node_id')} endpoint {target}:")
                for path, value in sorted(
                    endpoints[target].items(),
                    key=lambda kv: [int(x) for x in kv[0].split("/")],
                ):
                    print(f"  {path:<10} {value!r}")
    elif cmd == "nodes":
        for node in nodes:
            endpoints = _endpoints(node)
            print(f"node {node.get('node_id')} — {len(endpoints)} endpoints")
            for endpoint, attrs in sorted(endpoints.items(), key=lambda x: int(x[0])):
                label = attrs.get(LABEL)
                if label:
                    print(f"  ep {endpoint}: {label}")
    elif cmd == "sensors":
        rows = _sensor_rows(nodes)
        if not rows:
            sys.exit("No temp/humidity sensors found (yet). Commissioned? "
                     "Interview can take a minute after commissioning.")
        for row in rows:
            print(_fmt(row))
    elif cmd in ("temp", "humidity") and len(sys.argv) >= 3:
        row = _find(_sensor_rows(nodes), sys.argv[2])
        value = row[cmd]
        if value is None:
            sys.exit(f"{row['label']} has no {cmd} reading.")
        unit = "C" if cmd == "temp" else "%"
        print(f"{value / 100:.1f} {unit}  ({row['label']})")
    elif cmd == "states":
        rows = _device_rows(nodes, BOOL)
        if not rows:
            sys.exit("No contact/leak sensors visible (yet).")
        for row in rows:
            raw = row["attrs"].get(BOOL)
            label = row["label"]
            lower = label.lower()
            if "leak" in lower or "water" in lower:
                # Water leak detectors: true = LEAK
                text = "LEAK DETECTED" if raw else "dry"
            elif "door" in lower or "window" in lower or "contact" in lower:
                # Contact sensors: true = closed
                text = "closed" if raw else "OPEN"
            else:
                text = f"state={raw}"
            print(f"{label:<32} {text}")
    elif cmd in ("on", "off") and len(sys.argv) >= 3:
        row = _find(_device_rows(nodes, ONOFF), sys.argv[2])
        await _command(row, 6, "On" if cmd == "on" else "Off")
        print(f"ok — {row['label']} {cmd}")
    elif cmd in ("open", "close") and len(sys.argv) >= 3:
        row = _find(_device_rows(nodes, COVER), sys.argv[2])
        await _command(row, 258, "UpOrOpen" if cmd == "open" else "DownOrClose")
        print(f"ok — {row['label']} {cmd}")
    elif cmd == "ac":
        acs = _device_rows(nodes, AC_LOCAL_TEMP)
        if not acs:
            sys.exit("No thermostat/AC endpoint found.")
        ac = acs[0]
        sub = sys.argv[2].lower() if len(sys.argv) > 2 else "status"
        if sub == "status":
            attrs = ac["attrs"]
            mode = AC_MODE_NAMES.get(attrs.get(AC_MODE), attrs.get(AC_MODE))
            temp = attrs.get(AC_LOCAL_TEMP)
            print(f"{ac['label']}: mode={mode}"
                  + (f", room {temp / 100:.1f} C" if temp is not None else "")
                  + f", cool setpoint {attrs.get(AC_COOL_SET, 0) / 100:.0f} C"
                  + f", heat setpoint {attrs.get(AC_HEAT_SET, 0) / 100:.0f} C")
        elif sub in AC_MODES and len(sys.argv) == 3:
            await _write(ac, AC_MODE, AC_MODES[sub])
            print(f"ok — {ac['label']} mode: {sub}")
        elif sub in ("cool", "heat") and len(sys.argv) >= 4:
            degrees = max(AC_MIN, min(AC_MAX, float(sys.argv[3])))
            setpoint = AC_COOL_SET if sub == "cool" else AC_HEAT_SET
            await _write(ac, setpoint, int(degrees * 100))
            await _write(ac, AC_MODE, AC_MODES[sub])
            print(f"ok — {ac['label']}: {sub} to {degrees:.0f} C")
        else:
            sys.exit("Usage: ac | ac off|cool|heat|auto | ac cool 22 | ac heat 21")
    elif cmd == "position" and len(sys.argv) >= 4:
        row = _find(_device_rows(nodes, COVER), sys.argv[2])
        percent_open = max(0, min(100, int(sys.argv[3])))
        # Matter counts lift in 100ths of percent CLOSED; invert for humans
        await _command(row, 258, "GoToLiftPercentage",
                       {"liftPercent100thsValue": (100 - percent_open) * 100})
        print(f"ok — {row['label']} to {percent_open}% open")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    asyncio.run(main())
