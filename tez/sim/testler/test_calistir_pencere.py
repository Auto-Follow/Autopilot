"""calistir.sh starts the Gazebo window without the Qt variables that cv2 leaves in a Python caller's environment.

opencv-python sets QT_QPA_PLATFORM_PLUGIN_PATH and QT_QPA_FONTDIR to its own Qt plugins when cv2 is imported. senaryo.py
imports cv2 before it starts calistir.sh, so without this the window (system Qt) aborted at start (15.11.2026).
"""

import re
from pathlib import Path

CALISTIR = Path(__file__).resolve().parents[1] / "calistir.sh"


def gui_lines() -> list[str]:
    """The lines that start the window (in the background), not the hint in the warning text."""
    lines = CALISTIR.read_text().splitlines()
    return [line for line in lines if re.search(r"\bgz sim -g\b", line) and line.rstrip().endswith("&")]


def test_the_window_is_started_without_the_qt_variables_of_cv2() -> None:
    lines = gui_lines()
    assert len(lines) == 1, lines
    for var in ("QT_QPA_PLATFORM_PLUGIN_PATH", "QT_QPA_FONTDIR", "QT_PLUGIN_PATH"):
        assert f"-u {var}" in lines[0], (var, lines[0])


def test_importing_cv2_sets_the_variables_the_script_removes() -> None:
    """The reason for the unset: if a cv2 version stops setting them this test says so (the unset stays harmless)."""
    import os
    import subprocess
    import sys

    code = "import os, cv2; print(os.environ.get('QT_QPA_PLATFORM_PLUGIN_PATH', ''))"
    env = {k: v for k, v in os.environ.items() if not k.startswith("QT_")}
    try:
        out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):  # pragma: no cover
        return
    if out.returncode != 0:  # cv2 not installed in this interpreter: nothing to check
        return
    assert "cv2" in out.stdout


def test_the_script_warns_when_the_window_dies() -> None:
    text = CALISTIR.read_text()
    assert 'kill -0 "$GUI_PID"' in text
    assert "Gazebo penceresi açılamadı" in text
