#!/usr/bin/env python3
"""Telegram bridge — the owner's pocket link to Jarvis. Receiving side.

A small daemon that long-polls the Telegram Bot API (outbound HTTPS only,
no open ports) and files everything the OWNER sends into the project inbox:

    inbox/messages.md                       text log, newest last
    inbox/2026-08-16_14-32-05_photo.jpg     media, timestamped (newest = last
    inbox/2026-08-16_14-40-11_voice.ogg      alphabetically — easy to find)

All other Telegram users are ignored. The bot replies "Saved" so you know
a message landed on the Mac.

Setup (once):
    1. Telegram: talk to @BotFather -> /newbot -> copy the token.
    2. echo "TELEGRAM_BOT_TOKEN=123:abc..." >> ../../.env
    3. python telegram_bot.py setup     # then send any message to your bot
       -> your chat id is captured and saved to .env automatically.

Run (normally handled by `./jarvis up`):
    python telegram_bot.py run
"""

import sys
import time
from datetime import datetime
from pathlib import Path

import requests

from common import ROOT, load_env, require, save_env_value

ENV = load_env()
INBOX = ROOT / "inbox"
MESSAGES = INBOX / "messages.md"
OFFSET_FILE = INBOX / ".offset"


def _token():
    return require(ENV, "TELEGRAM_BOT_TOKEN",
                   "Create a bot with @BotFather first (see docstring).")


def api(method, params=None, files=None, timeout=70):
    r = requests.post(
        f"https://api.telegram.org/bot{_token()}/{method}",
        data=params or {}, files=files, timeout=timeout,
    )
    payload = r.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram {method}: {payload}")
    return payload["result"]


def download(file_id, dest: Path):
    info = api("getFile", {"file_id": file_id})
    url = f"https://api.telegram.org/file/bot{_token()}/{info['file_path']}"
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    dest.write_bytes(r.content)


def classify(msg):
    """-> (kind, file_id, extension) for the media in a message, or None."""
    if "photo" in msg:                       # list of sizes; last = largest
        return "photo", msg["photo"][-1]["file_id"], ".jpg"
    if "voice" in msg:
        return "voice", msg["voice"]["file_id"], ".ogg"
    if "audio" in msg:
        name = msg["audio"].get("file_name", "")
        ext = Path(name).suffix or ".mp3"
        return "audio", msg["audio"]["file_id"], ext
    if "video" in msg:
        return "video", msg["video"]["file_id"], ".mp4"
    if "video_note" in msg:
        return "video", msg["video_note"]["file_id"], ".mp4"
    if "document" in msg:
        name = msg["document"].get("file_name", "document")
        ext = Path(name).suffix or ".bin"
        return "document", msg["document"]["file_id"], ext
    return None


def log_line(text):
    INBOX.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with MESSAGES.open("a") as f:
        f.write(f"- [{stamp}] {text}\n")


def handle(msg):
    """Save one owner message; returns a short receipt string."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    media = classify(msg)
    caption = msg.get("caption", "")
    if media:
        kind, file_id, ext = media
        INBOX.mkdir(exist_ok=True)
        dest = INBOX / f"{stamp}_{kind}{ext}"
        download(file_id, dest)
        log_line(f"[{kind} saved: {dest.name}]"
                 + (f" caption: {caption}" if caption else ""))
        return f"Saved {kind} ({dest.name})"
    if "text" in msg:
        log_line(msg["text"])
        return "Saved"
    return "Unsupported message type — text, photo, voice, video, files only."


def run():
    chat_id = require(ENV, "TELEGRAM_CHAT_ID",
                      "Run `python telegram_bot.py setup` first.")
    offset = 0
    if OFFSET_FILE.exists():
        try:
            offset = int(OFFSET_FILE.read_text().strip())
        except ValueError:
            pass
    print(f"Telegram bridge up — filing to {INBOX}")
    while True:
        try:
            updates = api("getUpdates", {"offset": offset + 1, "timeout": 50})
            for update in updates:
                offset = update["update_id"]
                INBOX.mkdir(exist_ok=True)
                OFFSET_FILE.write_text(str(offset))
                msg = update.get("message") or update.get("edited_message")
                if not msg:
                    continue
                if str(msg["chat"]["id"]) != str(chat_id):
                    continue  # not the owner — ignore silently
                receipt = handle(msg)
                api("sendMessage", {"chat_id": chat_id, "text": receipt})
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # noqa: BLE001 — a bridge must survive
            print(f"[warn] {exc}", file=sys.stderr)
            time.sleep(5)


def setup():
    _token()  # fail early if missing
    print("Send any message to your bot in Telegram now (waiting 120 s)...")
    deadline = time.time() + 120
    offset = 0
    while time.time() < deadline:
        for update in api("getUpdates", {"offset": offset + 1, "timeout": 30}):
            offset = update["update_id"]
            msg = update.get("message")
            if msg:
                chat_id = msg["chat"]["id"]
                save_env_value("TELEGRAM_CHAT_ID", str(chat_id))
                api("sendMessage", {"chat_id": chat_id,
                                    "text": "Linked to Jarvis. This chat is "
                                            "now your line to the house."})
                print(f"Linked. Chat id {chat_id} saved to .env.")
                return
    sys.exit("Timed out — no message received.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    {"run": run, "setup": setup}.get(cmd, lambda: sys.exit(__doc__))()
