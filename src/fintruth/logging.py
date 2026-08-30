"""Process-wide logging setup."""

from __future__ import annotations

import logging
import sys

from fintruth.config import get_settings


def setup_logging(level: str | None = None) -> None:
    """Configure root logger once. Safe to call multiple times."""
    resolved = (level or get_settings().log_level).upper()
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(resolved)
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(resolved)
