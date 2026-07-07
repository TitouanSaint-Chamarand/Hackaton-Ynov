"""Charge le fichier .env à la racine du repo si les variables ne sont pas déjà définies."""

from __future__ import annotations

import os
from pathlib import Path


def load_repo_env() -> None:
    path = Path(__file__).resolve()
    if len(path.parents) <= 2:
        return

    env_path = path.parents[2] / ".env"
    if not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
