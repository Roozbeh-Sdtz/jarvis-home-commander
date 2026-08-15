#!/usr/bin/env python3
"""Aqara sensors (via M3 hub) — SCAFFOLD, needs one-time cloud setup.

STATUS: not yet functional. Aqara has no fully open local API; options:

  Option A (this scaffold): Aqara Open Cloud API
    1. Create a developer account: https://developer.aqara.com
    2. Create a project -> get AppId, AppKey, KeyId; note your region domain
       (e.g. open-ger.aqara.com for Europe).
    3. Authorize your account and store in .env:
       AQARA_DOMAIN=, AQARA_APP_ID=, AQARA_APP_KEY=, AQARA_KEY_ID=, AQARA_TOKEN=
    4. Implement query.resource.value for your sensor IDs below.

  Option B (better long-term, fully local): the M3 is a Matter bridge —
    commission it into a second fabric (python-matter-server) via
    Apple Home -> accessory -> "Turn On Pairing Mode". Then read sensors
    locally with no cloud. Bigger build; see memory/decisions.md.

Usage (once configured):
    python aqara.py temp bedroom
"""

import sys

from common import load_env

ENV = load_env()

# Map friendly names -> Aqara device/resource ids (fill after setup)
SENSORS = {
    # "bedroom": {"subject_id": "lumi.xxxx", "resource_id": "0.1.85"},
}


def main():
    if not ENV.get("AQARA_APP_ID"):
        sys.exit(
            "Aqara is not configured yet.\n"
            "Follow the setup steps in this file's docstring "
            "(developer.aqara.com), then fill SENSORS and implement the "
            "query call. See docs/devices.md."
        )
    sys.exit("Aqara scaffold: signing + query.resource.value not implemented yet.")


if __name__ == "__main__":
    main()
