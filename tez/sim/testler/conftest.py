"""The tools in araclar/ import each other by plain name (they run as scripts from that folder)."""

import os
import sys
from pathlib import Path

# as in the tools (kayit.py, goruntu.py): Gazebo's message modules need the pure Python protobuf, set before any import
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "araclar"))
