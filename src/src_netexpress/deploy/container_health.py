"""Healthcheck Docker unique pour les processus web et Celery."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import urllib.request


def check_web() -> int:
    port = os.getenv("PORT", "8000")
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/readyz/",
            timeout=4,
        ) as response:
            return 0 if response.status == 200 else 1
    except Exception:
        return 1


def check_worker() -> int:
    destination = f"worker@{socket.gethostname()}"
    try:
        result = subprocess.run(
            [
                "celery",
                "-A",
                "netexpress",
                "inspect",
                "ping",
                "--destination",
                destination,
                "--timeout",
                "4",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=6,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1
    return 0 if result.returncode == 0 else 1


def main() -> int:
    process_type = os.getenv("PROCESS_TYPE", "web").strip().lower()
    if process_type == "worker":
        return check_worker()
    if process_type == "web":
        return check_web()
    return 1


if __name__ == "__main__":
    sys.exit(main())
