"""Start and stop the thesis simulation (calistir.sh) from the Python tools; always shuts down, even after an error.

with Simulation(out_dir, world_file, headless=True) as sim:
    if sim.wait_ready(): ...
sim.problems()   # what was wrong with the run: processes left over, mode marked unresponsive
"""

import subprocess
import time
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parent.parent
REPO = SIM_DIR.parent.parent
BUILD = REPO / "build" / "px4_sitl_tez"
READY_LINE = "registered as"  # tez_auto_follow is registered with the commander: PX4 is up and attached to Gazebo


def running() -> bool:
    """A PX4 or Gazebo server process exists (from this or any other start)."""
    px4 = subprocess.run(["pgrep", "-x", "px4"], capture_output=True).returncode == 0
    gz = subprocess.run(["pgrep", "-f", "^gz sim"], capture_output=True).returncode == 0
    return px4 or gz


class Simulation:
    def __init__(self, out: Path, world: str | Path = "duz_alan", headless: bool = True) -> None:
        self.out = out
        self.world = world
        self.headless = headless
        self.log_path = out / "sim.log"
        self.proc: subprocess.Popen | None = None
        self.started = 0.0

    def __enter__(self) -> "Simulation":
        if running():
            raise RuntimeError("Zaten çalışan bir PX4 veya Gazebo var; önce onu kapatın")
        self.out.mkdir(parents=True, exist_ok=True)
        args = [str(SIM_DIR / "calistir.sh"), "--dunya", str(self.world)] + (["--ekransiz"] if self.headless else [])
        self.started = time.time()
        self.proc = subprocess.Popen(
            args, stdin=subprocess.DEVNULL, stdout=self.log_path.open("w"), stderr=subprocess.STDOUT
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
            if READY_LINE in self.log():
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
        """Checks after stop(): nothing left running, the commander never dropped the thesis mode."""
        found = []
        for _ in range(10):  # Gazebo may need a few seconds after calistir.sh has returned
            if not running():
                break
            time.sleep(1)
        else:
            found.append("kapanıştan sonra çalışan PX4/Gazebo süreci kaldı")
        if "unresponsive" in self.log().lower():
            found.append("PX4 tez modunu 'unresponsive' olarak işaretledi (sim.log)")
        return found

    def newest_ulog(self) -> Path | None:
        logs = [p for p in (BUILD / "rootfs" / "log").rglob("*.ulg") if p.stat().st_mtime >= self.started]
        return max(logs, key=lambda p: p.stat().st_mtime) if logs else None
