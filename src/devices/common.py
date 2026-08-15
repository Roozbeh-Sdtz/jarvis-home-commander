"""Shared helpers for device scripts. Secrets live in <project root>/.env."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # Home_IoT/
ENV_FILE = ROOT / ".env"


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def require(env, key, hint):
    value = env.get(key)
    if not value:
        sys.exit(f"Missing {key} in {ENV_FILE}. {hint}")
    return value


def save_env_value(key, value):
    """Append/replace a key in .env (creates the file with 0600 if needed)."""
    lines = []
    if ENV_FILE.exists():
        lines = [
            l for l in ENV_FILE.read_text().splitlines()
            if not l.strip().startswith(f"{key}=")
        ]
    lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n")
    ENV_FILE.chmod(0o600)
