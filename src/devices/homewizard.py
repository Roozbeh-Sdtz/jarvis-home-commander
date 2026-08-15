#!/usr/bin/env python3
"""HomeWizard P1 meter — local API v2 (electricity + gas). No cloud.

Setup (once):
    1. Find the P1 meter's IP (HomeWizard app -> meter -> settings, or router).
    2. Save it:      echo "HW_P1_IP=192.168.x.x" >> ../../.env
    3. Get a token — run this, then PRESS the button on the P1 meter:
                     python homewizard.py pair

Usage:
    python homewizard.py summary    # human-readable: power now, totals, gas
    python homewizard.py power      # current usage in watts
    python homewizard.py gas        # gas meter reading
    python homewizard.py raw        # full JSON measurement

API reference: https://api-documentation.homewizard.com/docs/category/api-v2
"""

import json
import sys
import time

import requests
import urllib3

from common import load_env, require, save_env_value

urllib3.disable_warnings()  # device cert is signed by HomeWizard's own CA

ENV = load_env()


def _base():
    ip = require(ENV, "HW_P1_IP", "Add your P1 meter's IP first.")
    return f"https://{ip}"


def _headers():
    token = require(ENV, "HW_P1_TOKEN", "Run `python homewizard.py pair` first.")
    return {"Authorization": f"Bearer {token}", "X-Api-Version": "2"}


def pair():
    print("Press the button on the P1 meter now (polling for 60s)...")
    for _ in range(30):
        r = requests.post(
            f"{_base()}/api/user",
            json={"name": "local/jarvis"},
            headers={"X-Api-Version": "2"},
            verify=False, timeout=5,
        )
        if r.status_code == 200:
            token = r.json()["token"]
            save_env_value("HW_P1_TOKEN", token)
            print("Paired. Token saved to .env.")
            return
        time.sleep(2)
    sys.exit("Timed out — button was not pressed.")


def measurement():
    r = requests.get(f"{_base()}/api/measurement",
                     headers=_headers(), verify=False, timeout=10)
    r.raise_for_status()
    return r.json()


def gas_reading(data):
    for ext in data.get("external", []):
        if ext.get("type") == "gas_meter":
            return ext["value"], ext.get("unit", "m3"), ext.get("timestamp")
    return None, None, None


def main():
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "summary"

    if cmd == "pair":
        pair()
        return

    data = measurement()
    if cmd == "raw":
        print(json.dumps(data, indent=2))
    elif cmd == "power":
        print(f"{data.get('power_w', '?')} W")
    elif cmd == "gas":
        value, unit, ts = gas_reading(data)
        print(f"{value} {unit} (at {ts})" if value is not None else "No gas meter found.")
    elif cmd == "summary":
        power = data.get("power_w")
        imported = data.get("energy_import_kwh")
        exported = data.get("energy_export_kwh")
        print(f"Current power: {power} W"
              + (" (exporting)" if isinstance(power, (int, float)) and power < 0 else ""))
        if imported is not None:
            print(f"Total imported: {imported} kWh")
        if exported:
            print(f"Total exported: {exported} kWh")
        value, unit, _ = gas_reading(data)
        if value is not None:
            print(f"Gas meter: {value} {unit}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
