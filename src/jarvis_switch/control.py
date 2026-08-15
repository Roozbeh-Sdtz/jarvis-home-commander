"""Control socket: lets separate processes flip the bridge's command switches.

Why: command switches live inside the running bridge process, but the voice
agent (and any script) runs in its own process. This Unix domain socket is
the hand-off.

Security: filesystem socket with 0600 permissions — only this user, never
the network. See docs/security.md.

Protocol (one text line per connection):
    on <switch name>     -> "ok"
    off <switch name>    -> "ok"
    list                 -> one switch name per line
    anything else        -> "err: ..."
"""

import logging
import os
import socket
import threading

import home
from config import SOCKET_PATH

log = logging.getLogger("control")


def start_server(path=None):
    path = path or SOCKET_PATH
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    os.chmod(path, 0o600)
    srv.listen(4)
    threading.Thread(target=_accept_loop, args=(srv,), daemon=True).start()
    log.info("Control socket listening at %s", path)


def _accept_loop(srv):
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=_handle, args=(conn,), daemon=True).start()


def _handle(conn):
    with conn:
        try:
            line = conn.recv(1024).decode("utf-8", "replace").strip()
            reply = _dispatch(line)
        except Exception as exc:  # noqa: BLE001 — never crash the bridge
            reply = f"err: {exc}"
        try:
            conn.sendall((reply + "\n").encode())
        except OSError:
            pass


def _dispatch(line):
    parts = line.split(maxsplit=1)
    cmd = parts[0].lower() if parts else ""
    if cmd == "list":
        names = home.names()
        return "\n".join(names) if names else "(no command switches)"
    if cmd in ("on", "off") and len(parts) == 2:
        name = parts[1].strip().strip('"')
        if cmd == "on":
            home.turn_on(name)
        else:
            home.turn_off(name)
        return "ok"
    return "err: usage: on <switch> | off <switch> | list"
