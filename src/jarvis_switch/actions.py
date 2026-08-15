"""What Jarvis actually DOES. Edit this file freely — no HomeKit knowledge needed.

on_turn_on()  runs when Jarvis is turned ON  ("Hey Siri, Call Jarvis")
              -> starts the voice session: audio to HomePod + iPhone mic,
                 greeting, Codex voice mode. See session.py.
on_turn_off() runs when Jarvis is turned OFF ("Hey Siri, Dismiss Jarvis")
              -> farewell + restores audio devices.

Sessions run in a background thread so HomeKit never sees us as unresponsive.

To control real Apple Home devices from here, flip a command switch
(config.py) and let your Home-app automation do the rest:

    home.turn_on("Jarvis Light")
"""

import threading

import home  # noqa: F401  (available for custom automations)
import session


def on_turn_on():
    print("hi")
    threading.Thread(target=session.start, daemon=True).start()
    # Optional: also light up the living room when Jarvis wakes:
    # home.turn_on("Jarvis Light")


def on_turn_off():
    print("bye")
    threading.Thread(target=session.end, daemon=True).start()
    # home.turn_off("Jarvis Light")
