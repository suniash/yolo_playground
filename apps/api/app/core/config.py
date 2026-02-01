from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("VAP_DATA_DIR", ROOT_DIR / "data"))

DEFAULT_PROFILE = "soccer"

FIELD_DIMENSIONS = {
    "soccer": {"length": 105.0, "width": 68.0},
    "basketball": {"length": 28.0, "width": 15.0},
}
