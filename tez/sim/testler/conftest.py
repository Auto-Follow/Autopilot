"""The tools in araclar/ import each other by plain name (they run as scripts from that folder)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "araclar"))
