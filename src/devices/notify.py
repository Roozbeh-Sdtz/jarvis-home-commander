#!/usr/bin/env python3
"""Send a message/photo/file to the owner's Telegram. The agent's pen.

Usage:
    python notify.py "The dryer just finished, sir."
    python notify.py --photo /path/to/chart.png "Energy use this week"
    python notify.py --file /path/to/report.pdf "As requested"

Requires TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env
(see telegram_bot.py for one-time setup).
"""

import sys
from pathlib import Path

import requests

from common import load_env, require

ENV = load_env()


def _send(method, params, files=None):
    token = require(ENV, "TELEGRAM_BOT_TOKEN", "Telegram not set up yet.")
    params["chat_id"] = require(ENV, "TELEGRAM_CHAT_ID",
                                "Run `python telegram_bot.py setup` first.")
    r = requests.post(f"https://api.telegram.org/bot{token}/{method}",
                      data=params, files=files, timeout=60)
    payload = r.json()
    if not payload.get("ok"):
        sys.exit(f"Telegram error: {payload}")
    print("sent")


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args[0] in ("--photo", "--file") and len(args) >= 2:
        path = Path(args[1]).expanduser()
        if not path.exists():
            sys.exit(f"No such file: {path}")
        caption = " ".join(args[2:])
        with path.open("rb") as fh:
            if args[0] == "--photo":
                _send("sendPhoto", {"caption": caption}, {"photo": fh})
            else:
                _send("sendDocument", {"caption": caption}, {"document": fh})
    else:
        _send("sendMessage", {"text": " ".join(args)})


if __name__ == "__main__":
    main()
