#!/usr/bin/env python3
"""Bosch appliances (washing machine, dishwasher, dryer) — Home Connect API.

SCAFFOLD, needs one-time cloud setup (Home Connect is cloud-only):
    1. Register (free): https://developer.home-connect.com
    2. Create an application -> Authorization Flow: "Device Flow" -> get Client ID.
    3. Save it:   echo "BOSCH_CLIENT_ID=..." >> ../../.env
    4. Authorize once:   python bosch.py auth
       (visit the printed URL, log in with your Home Connect account)

Usage (after auth):
    python bosch.py appliances          # list + connection state
    python bosch.py status <haId>       # active program / remaining time
"""

import sys
import time

import requests

from common import load_env, require, save_env_value

API = "https://api.home-connect.com"
ENV = load_env()


def _client_id():
    return require(ENV, "BOSCH_CLIENT_ID",
                   "Register at developer.home-connect.com (Device Flow) first.")


def auth():
    r = requests.post(f"{API}/security/oauth/device_authorization",
                      data={"client_id": _client_id()}, timeout=10)
    r.raise_for_status()
    d = r.json()
    print(f"Visit: {d['verification_uri_complete']}")
    print("Waiting for you to authorize...")
    while True:
        time.sleep(d.get("interval", 5))
        t = requests.post(f"{API}/security/oauth/token", data={
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": d["device_code"],
            "client_id": _client_id(),
        }, timeout=10)
        if t.status_code == 200:
            tokens = t.json()
            save_env_value("BOSCH_ACCESS_TOKEN", tokens["access_token"])
            save_env_value("BOSCH_REFRESH_TOKEN", tokens["refresh_token"])
            print("Authorized. Tokens saved to .env.")
            return
        if t.json().get("error") != "authorization_pending":
            sys.exit(f"Auth failed: {t.text}")


def _headers():
    token = require(ENV, "BOSCH_ACCESS_TOKEN", "Run `python bosch.py auth` first.")
    return {"Authorization": f"Bearer {token}",
            "Accept": "application/vnd.bsh.sdk.v1+json"}


def _refresh():
    """Access tokens expire ~daily; trade the refresh token for a new one."""
    refresh_token = ENV.get("BOSCH_REFRESH_TOKEN")
    if not refresh_token:
        return False
    r = requests.post(f"{API}/security/oauth/token", data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": _client_id(),
    }, timeout=10)
    if r.status_code != 200:
        return False
    tokens = r.json()
    ENV["BOSCH_ACCESS_TOKEN"] = tokens["access_token"]
    save_env_value("BOSCH_ACCESS_TOKEN", tokens["access_token"])
    if tokens.get("refresh_token"):
        ENV["BOSCH_REFRESH_TOKEN"] = tokens["refresh_token"]
        save_env_value("BOSCH_REFRESH_TOKEN", tokens["refresh_token"])
    return True


def _get(path):
    """GET with automatic one-shot token refresh on 401."""
    r = requests.get(f"{API}{path}", headers=_headers(), timeout=10)
    if r.status_code == 401 and _refresh():
        r = requests.get(f"{API}{path}", headers=_headers(), timeout=10)
    if r.status_code == 401:
        sys.exit("Not authorized and refresh failed — run `python bosch.py auth` "
                 "(refresh tokens expire after ~2 months or when revoked).")
    return r


def main():
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if cmd == "auth":
        auth()
    elif cmd == "appliances":
        r = _get("/api/homeappliances")
        r.raise_for_status()
        for a in r.json()["data"]["homeappliances"]:
            state = "connected" if a["connected"] else "offline"
            print(f"{a['type']:<15} {a['name']:<25} {state}   haId={a['haId']}")
    elif cmd == "status" and len(sys.argv) >= 3:
        ha_id = sys.argv[2]
        r = _get(f"/api/homeappliances/{ha_id}/programs/active")
        if r.status_code == 404:
            print("No active program.")
            return
        r.raise_for_status()
        import json
        print(json.dumps(r.json(), indent=2))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
