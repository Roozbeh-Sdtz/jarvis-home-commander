"""Jarvis Bridge — virtual HomeKit bridge run on the always-on Mac.

Hosts:
  - "Jarvis"        trigger switch: toggling it in Apple Home runs actions.py
  - command switches (config.py): Python flips them; Home-app automations
    make real accessories follow. This is how Python controls Apple Home.

Usage:
    python jarvis.py
Then pair once via the QR code / PIN printed in the terminal
(Home app: + -> Add Accessory). Pairing the bridge adds all switches.

NOTE: if you previously paired the old standalone Jarvis switch, remove it
from the Home app and delete jarvis.state before first run of the bridge.
"""

import logging
import os
import signal
from pathlib import Path

from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_SWITCH

import actions
import control
import home
from config import BRIDGE_NAME, COMMAND_SWITCHES, TRIGGER_SWITCH

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")

# Pairing state — contains keys, keep private (see docs/security.md).
STATE_FILE = Path(__file__).resolve().parent / "jarvis.state"
PORT = 51826


class JarvisSwitch(Accessory):
    """The trigger switch: HomeKit -> Python."""

    category = CATEGORY_SWITCH

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        service = self.add_preload_service("Switch")
        self.char_on = service.configure_char("On", setter_callback=self._on_toggle)

    def _on_toggle(self, value):
        if value:
            actions.on_turn_on()
        else:
            actions.on_turn_off()


class CommandSwitch(Accessory):
    """A switch Python flips to drive Home-app automations: Python -> HomeKit."""

    category = CATEGORY_SWITCH

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        service = self.add_preload_service("Switch")
        self.char_on = service.configure_char("On", setter_callback=self._on_toggle)

    def _on_toggle(self, value):
        # Someone flipped it from the Home app side; just log it.
        logging.info("[%s] set to %s from Apple Home", self.display_name, value)

    def set(self, value: bool):
        """Flip from Python. Notifies HomeKit -> triggers automations."""
        self.char_on.set_value(bool(value))


def main():
    # Security: files we create (incl. jarvis.state, which holds pairing
    # keys) are readable by this user only. See docs/security.md.
    os.umask(0o077)
    if STATE_FILE.exists():
        STATE_FILE.chmod(0o600)

    # Optional (see docs/security.md): pass address="<ethernet-ip>" to bind
    # the bridge to the wired interface only.
    driver = AccessoryDriver(port=PORT, persist_file=str(STATE_FILE))

    bridge = Bridge(driver, BRIDGE_NAME)
    bridge.add_accessory(JarvisSwitch(driver, TRIGGER_SWITCH))
    for name in COMMAND_SWITCHES:
        switch = CommandSwitch(driver, name)
        bridge.add_accessory(switch)
        home.register(name, switch)

    driver.add_accessory(accessory=bridge)
    control.start_server()  # lets device scripts flip command switches
    signal.signal(signal.SIGTERM, driver.signal_handler)
    driver.start()  # prints QR code + pairing PIN, then blocks


if __name__ == "__main__":
    main()
