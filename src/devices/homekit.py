#!/usr/bin/env python3
"""Control Apple Home devices via the Jarvis Bridge command switches.

This is the ONLY route to devices that exist solely in Apple Home
(e.g. the Eve watering systems, paired via Matter). Each command switch
needs a matching Home-app automation (see docs/setup-jarvis-switch.md).

Usage:
    python homekit.py list
    python homekit.py on "Jarvis Light"
    python homekit.py off "Jarvis Light"

Requires the Jarvis Bridge to be running (it owns the control socket).
"""

import os
import socket
import sys
from pathlib import Path

SOCKET_PATH = os.environ.get(
    "JARVIS_SOCKET",
    str(Path(__file__).resolve().parents[1] / "jarvis_switch" / "control.sock"),
)


def send(line: str) -> str:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(5)
    try:
        client.connect(SOCKET_PATH)
    except (FileNotFoundError, ConnectionRefusedError):
        sys.exit("Jarvis Bridge is not running (control socket unavailable).")
    with client:
        client.sendall(line.encode())
        return client.recv(4096).decode().strip()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1].lower()
    if cmd == "list":
        print(send("list"))
    elif cmd in ("on", "off") and len(sys.argv) >= 3:
        print(send(f"{cmd} {sys.argv[2]}"))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
