"""File logging for Thumbforge inside Krita."""

from __future__ import annotations

import datetime as _dt
import os
import traceback


def log_path() -> str:
    root = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "krita")
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, "thumbforge.log")


def log(message: str) -> None:
    timestamp = _dt.datetime.now().isoformat(timespec="seconds")
    with open(log_path(), "a", encoding="utf-8") as handle:
        handle.write(timestamp + " " + message + "\n")


def log_exception(context: str, exc: Exception) -> None:
    log(context + ": " + str(exc))
    with open(log_path(), "a", encoding="utf-8") as handle:
        handle.write(traceback.format_exc() + "\n")
