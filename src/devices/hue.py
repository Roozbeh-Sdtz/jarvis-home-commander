#!/usr/bin/env python3
"""Philips Hue — local API (CLIP v2) via the Hue Bridge. No cloud.

Setup (once):
    1. Find bridge IP (Hue app -> Settings -> My Hue system -> bridge, or
       https://discovery.meethue.com).
    2. Save it:            echo "HUE_BRIDGE_IP=192.168.x.x" >> ../../.env
    3. PRESS the bridge's round link button, then within 30s:
                           python hue.py pair

Usage:
    python hue.py lights                  # names + on/off + brightness
    python hue.py on "Living room"
    python hue.py off "Bedroom"
    python hue.py bri "Living room" 40    # brightness 0-100
"""

import json
import sys

import requests
import urllib3

from common import load_env, require, save_env_value

urllib3.disable_warnings()  # bridge uses a self-signed cert on the LAN

ENV = load_env()


def _base():
    ip = require(ENV, "HUE_BRIDGE_IP", "Add your Hue Bridge IP first.")
    return f"https://{ip}"


def _headers():
    key = require(ENV, "HUE_APP_KEY", "Run `python hue.py pair` first (press the bridge button).")
    return {"hue-application-key": key}


def pair():
    resp = requests.post(
        f"{_base()}/api",
        json={"devicetype": "jarvis#mac", "generateclientkey": True},
        verify=False, timeout=10,
    ).json()
    if "error" in resp[0]:
        sys.exit(f"Bridge says: {resp[0]['error']['description']} "
                 "(press the round link button on the bridge, then retry within 30s)")
    key = resp[0]["success"]["username"]
    save_env_value("HUE_APP_KEY", key)
    print("Paired. App key saved to .env.")


def _get_lights():
    r = requests.get(f"{_base()}/clip/v2/resource/light",
                     headers=_headers(), verify=False, timeout=10)
    r.raise_for_status()
    return r.json()["data"]


def _find(name):
    lights = _get_lights()
    matches = [l for l in lights
               if l["metadata"]["name"].lower() == name.lower()]
    if not matches:  # try substring match
        matches = [l for l in lights
                   if name.lower() in l["metadata"]["name"].lower()]
    if not matches:
        sys.exit(f"No light matching {name!r}. Try: python hue.py lights")
    if len(matches) > 1:
        sys.exit("Ambiguous, matches: "
                 + ", ".join(l["metadata"]["name"] for l in matches))
    return matches[0]


def _put(light_id, body):
    r = requests.put(f"{_base()}/clip/v2/resource/light/{light_id}",
                     headers=_headers(), json=body, verify=False, timeout=10)
    r.raise_for_status()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1].lower()

    if cmd == "pair":
        pair()
    elif cmd == "lights":
        for l in _get_lights():
            state = "ON " if l["on"]["on"] else "off"
            bri = l.get("dimming", {}).get("brightness", "-")
            print(f"{state} {int(bri) if bri != '-' else '-':>3}%  {l['metadata']['name']}")
    elif cmd in ("on", "off") and len(sys.argv) >= 3:
        light = _find(sys.argv[2])
        _put(light["id"], {"on": {"on": cmd == "on"}})
        print("ok")
    elif cmd == "bri" and len(sys.argv) >= 4:
        light = _find(sys.argv[2])
        level = max(0, min(100, float(sys.argv[3])))
        _put(light["id"], {"on": {"on": level > 0}, "dimming": {"brightness": level}})
        print("ok")
    elif cmd == "raw":
        print(json.dumps(_get_lights(), indent=2))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
