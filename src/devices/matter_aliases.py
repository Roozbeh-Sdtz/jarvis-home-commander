"""Friendly names for Matter endpoints (node 1 = Aqara M3 bridge).

The M3 exposes PRODUCT names ("Aqara Temp/Humidity Sensor"), not your room
names — fill this map so Jarvis can answer "bedroom temperature".

HOW TO IDENTIFY which endpoint is which room:
  - Temp sensors: run `python matter.py sensors`, compare the readings with
    the Aqara app (each sensor's current value differs slightly), OR breathe
    on one sensor and re-run — the endpoint whose humidity jumped is it.
  - Plugs/shades: `python matter.py on "ep 23"` (or off) and see which
    device reacts. Same idea for shades with open/close.
  - Leak sensors: touch the contact pins of one with a wet finger and run
    `python matter.py states`.

Endpoint numbers from the dump of 2026-08-16 (re-run `python matter.py
nodes` if devices are re-paired and numbers shift).
"""

ALIASES = {
    # --- certain ---
    2: "Air Conditioner",
    35: "Smoke Detector",
    36: "Main Door",

    # --- temp/humidity sensors: 24, 27, 30 — identify & fill in ---
    # 24: "Bedroom",
    # 27: "Living Room",
    # 30: "Work Room",

    # --- smart plugs: 23, 38 — Air Purifier / Camera ---
    # 23: "Air Purifier",
    # 38: "Camera Plug",

    # --- roller shades: 37, 39 — Bedroom / Work Room ---
    # 37: "Bedroom Shade",
    # 39: "Work Room Shade",

    # --- leak sensors: 20, 21, 22, 33, 34 —
    #     Sink / Micro-Drip / Radiator / Toilet / Utility Room ---
    # 20: "Sink Leak",
    # 21: "Micro-Drip Leak",
    # 22: "Radiator Leak",
    # 33: "Toilet Leak",
    # 34: "Utility Room Leak",
}
