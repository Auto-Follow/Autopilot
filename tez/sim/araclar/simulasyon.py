"""Start and stop the thesis simulation (calistir.sh) from the Python tools; always shuts down, even after an error.

with Simulation(out_dir, world_file, headless=True, params={"FLW_TGT_DST": 10}) as sim:
    if sim.wait_ready(): ...
sim.problems()   # what was wrong with the run: processes left over, an external mode marked unresponsive
"""

import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path

from parametreler import Number, format_value

SIM_DIR = Path(__file__).resolve().parent.parent
REPO = SIM_DIR.parent.parent
BUILD = REPO / "build" / "px4_sitl_tez"
READY_LINE = "Startup script returned successfully"  # PX4 ran its whole rcS: attached to Gazebo, all modules up
FAILED_LINES = ("Startup script returned with return value", "Unknown model", "gz_bridge failed")


def running() -> bool:
    """A PX4 or Gazebo server process exists (from this or any other start)."""
    px4 = subprocess.run(["pgrep", "-x", "px4"], capture_output=True).returncode == 0
    gz = subprocess.run(["pgrep", "-f", "^gz sim"], capture_output=True).returncode == 0
    return px4 or gz


def command(world: str | Path, headless: bool, params: Mapping[str, Number] | None = None) -> list[str]:
    """calistir.sh call; `params` are loaded after the .params files, in their order (the last one wins)."""
    args = [str(SIM_DIR / "calistir.sh"), "--dunya", str(world)]
    if headless:
        args.append("--ekransiz")
    for name, value in (params or {}).items():
        args += ["--param", f"{name}={format_value(value)}"]
    return args


class Simulation:
    def __init__(
        self,
        out: Path,
        world: str | Path = "duz_alan",
        headless: bool = True,
        params: Mapping[str, Number] | None = None,
        external_mode: bool = False,
    ) -> None:
        self.out = out
        self.world = world
        self.headless = headless
        self.params = dict(params or {})
        # Only an out-of-tree mode can be marked unresponsive by the commander; stock runs do not check for it.
        self.external_mode = external_mode
        self.log_path = out / "sim.log"
        self.proc: subprocess.Popen | None = None
        self.started = 0.0

    def __enter__(self) -> "Simulation":
        if running():
            raise RuntimeError("Zaten çalışan bir PX4 veya Gazebo var; önce onu kapatın")
        self.out.mkdir(parents=True, exist_ok=True)
        # calistir.sh runs parametreler.py; give it this interpreter unless the caller chose one
        env = {**os.environ, "TEZ_PYTHON": os.environ.get("TEZ_PYTHON") or sys.executable}
        self.started = time.time()
        self.proc = subprocess.Popen(
            command(self.world, self.headless, self.params),
            stdin=subprocess.DEVNULL,
            stdout=self.log_path.open("w"),
            stderr=subprocess.STDOUT,
            env=env,
        )
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    def log(self) -> str:
        return self.log_path.read_text(errors="replace") if self.log_path.is_file() else ""

    def wait_ready(self, timeout: float = 150.0) -> bool:
        t_end = time.monotonic() + timeout
        while time.monotonic() < t_end:
            if self.proc.poll() is not None:
                return False
            text = self.log()
            if any(line in text for line in FAILED_LINES):
                return False
            if READY_LINE in text:
                return True
            time.sleep(1)
        return False

    def stop(self) -> None:
        if self.proc is None or self.proc.poll() is not None:
            return
        # px4-shutdown talks to the daemon through the rootfs folder; calistir.sh then stops Gazebo
        subprocess.run(
            [str(BUILD / "bin" / "px4-shutdown")], cwd=BUILD / "rootfs", capture_output=True, timeout=20, check=False
        )
        try:
            self.proc.wait(40)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            self.proc.wait(10)

    def problems(self) -> list[str]:
        """Checks after stop(): nothing left running; with an external mode, the commander never dropped it."""
        found = []
        for _ in range(10):  # Gazebo may need a few seconds after calistir.sh has returned
            if not running():
                break
            time.sleep(1)
        else:
            found.append("kapanıştan sonra çalışan PX4/Gazebo süreci kaldı")
        if self.external_mode and "unresponsive" in self.log().lower():
            found.append("PX4 harici modu 'unresponsive' olarak işaretledi (sim.log)")
        return found

    def newest_ulog(self) -> Path | None:
        logs = [p for p in (BUILD / "rootfs" / "log").rglob("*.ulg") if p.stat().st_mtime >= self.started]
        return max(logs, key=lambda p: p.stat().st_mtime) if logs else None
