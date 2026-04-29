"""Support helpers for tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure src/ is on the path for all tests
_src = str(Path(__file__).resolve().parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
