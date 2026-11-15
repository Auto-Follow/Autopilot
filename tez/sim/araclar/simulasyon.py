"""Start and stop the thesis simulation (calistir.sh) from the Python tools; always shuts down, even after an error.

with Simulation(out_dir, world_file, headless=True, params={"FLW_TGT_DST": 10}) as sim:
    if sim.wait_ready(): ...
sim.problems()   # what was wrong with the run: processes left over, an external mode marked unresponsive

px4_start=["<module> start"]: PX4 commands calistir.sh runs once PX4 is up (calistir.sh --px4-baslat, in this order),
e.g. the start of an out-of-tree flight mode built with derle.sh --harici. wait_ready() then also waits until they
ran, and only such a run is checked for a mode the commander marked unresponsive (external_mode).

restart_logger(): PX4 v1.17.0's logger subscribes to its optional topics only if they exist when it starts
(LoggedTopics::add_topic, orb_exists). follow_target, follow_target_estimator and follow_target_status come into
being only with the first FOLLOW_TARGET and the Follow Target mode, so a follow_me run restarts the logger once they
exist: the ULog then has them, in a second file from that moment on (ulogs()).
"""

import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

from parametreler import Number, format_value

SIM_DIR = Path(__file__).resolve().parent.parent
REPO = SIM_DIR.parent.parent
BUILD = REPO / "build" / "px4_sitl_tez"
READY_LINE = "Startup script returned successfully"  # PX4 ran its whole rcS: attached to Gazebo, all modules up
FAILED_LINES = ("Startup script returned with return value", "Unknown model", "gz_bridge failed")
# what calistir.sh prints about the --px4-baslat commands (it runs them once `px4-logger status` succeeds)
START_DONE_LINE = "PX4 başlatma komutları tamam"
START_FAILED_LINES = ("PX4 başlatma komutu başarısız", "PX4 başlatma komutları çalıştırılamadı")
START_RESULT = re.compile(r"PX4 başlatma komutu (?:bitti|başarısız) \(çıkış kodu (-?\d+)\): (.*)$")
# the event of a run that left PX4 or Gazebo behind (problems(); m06_testi.py looks for it)
LEFT_RUNNING = "kapanıştan sonra çalışan PX4/Gazebo süreci kaldı"
UNRESPONSIVE = "unresponsive"  # commander: "No response from <id>, flagging unresponsive" (externalChecks.cpp)
# logger start arguments of the SITL start (init.d-posix/rcS + init.d/rc.logging with the parameter defaults this sim
# keeps: LOGGER_BUF 1000, EKF2_EN 1 -> poll ekf2_timestamps, SDLOG_MODE 1 -> -e, SDLOG_BACKEND 3 -> -m all)
LOGGER_START_ARGS = ("-b", "1000", "-t", "-p", "ekf2_timestamps", "-e", "-m", "all")


def running() -> bool:
    """A PX4 or Gazebo server process exists (from this or any other start)."""
    px4 = subprocess.run(["pgrep", "-x", "px4"], capture_output=True).returncode == 0
    gz = subprocess.run(["pgrep", "-f", "^gz sim"], capture_output=True).returncode == 0
    return px4 or gz


def command(
    world: str | Path, headless: bool, params: Mapping[str, Number] | None = None, px4_start: Sequence[str] = ()
) -> list[str]:
    """calistir.sh call; `params` are loaded after the .params files, in their order (the last one wins);
    `px4_start` are run in their order once PX4 is up."""
    args = [str(SIM_DIR / "calistir.sh"), "--dunya", str(world)]
    if headless:
        args.append("--ekransiz")
    for name, value in (params or {}).items():
        args += ["--param", f"{name}={format_value(value)}"]
    for text in px4_start:
        args += ["--px4-baslat", text]
    return args


class Simulation:
    def __init__(
        self,
        out: Path,
        world: str | Path = "duz_alan",
        headless: bool = True,
        params: Mapping[str, Number] | None = None,
        px4_start: Sequence[str] = (),
    ) -> None:
        self.out = out
        self.world = world
        self.headless = headless
        self.params = dict(params or {})
        self.px4_start = tuple(px4_start)
        self.log_path = out / "sim.log"
        self.proc: subprocess.Popen | None = None
        self.started = 0.0

    @property
    def external_mode(self) -> bool:
        """Only a module started after PX4 (--px4-baslat) can register an external mode, and only such a mode can be
        marked unresponsive by the commander; stock runs are not checked for it."""
        return bool(self.px4_start)

    def command(self) -> list[str]:
        return command(self.world, self.headless, self.params, self.px4_start)

    def __enter__(self) -> "Simulation":
        if running():
            raise RuntimeError("Zaten çalışan bir PX4 veya Gazebo var; önce onu kapatın")
        self.out.mkdir(parents=True, exist_ok=True)
        # calistir.sh runs parametreler.py; give it this interpreter unless the caller chose one
        env = {**os.environ, "TEZ_PYTHON": os.environ.get("TEZ_PYTHON") or sys.executable}
        self.started = time.time()
        self.proc = subprocess.Popen(
            self.command(),
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
        """PX4 ran its rcS and, with start commands, calistir.sh ran them all (a failed one = False). The start
        commands may finish before rcS does (they wait for the logger, which rcS starts second to last)."""
        needed = (READY_LINE, START_DONE_LINE) if self.px4_start else (READY_LINE,)
        failed = FAILED_LINES + (START_FAILED_LINES if self.px4_start else ())
        t_end = time.monotonic() + timeout
        while time.monotonic() < t_end:
            if self.proc.poll() is not None:
                return False
            text = self.log()
            if any(line in text for line in failed):
                return False
            if all(line in text for line in needed):
                return True
            time.sleep(1)
        return False

    def start_results(self) -> list[dict]:
        """[{"komut", "cikis_kodu"}] of the start commands calistir.sh ran, in their order (from sim.log)."""
        found = (START_RESULT.search(line) for line in self.log().splitlines())
        return [{"komut": m.group(2), "cikis_kodu": int(m.group(1))} for m in found if m]

    def unresponsive(self) -> list[str]:
        """sim.log lines in which the commander flagged an external mode unresponsive; [] without one."""
        if not self.external_mode:
            return []
        return [line.strip() for line in self.log().splitlines() if UNRESPONSIVE in line.lower()]

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

    def restart_logger(self) -> tuple[bool, str]:
        """Stop PX4's logger and start it again with the start arguments: a new ULog file with every topic that
        exists now. -> (both commands succeeded, their output)."""
        texts, ok = [], True
        for args in (("stop",), ("start", *LOGGER_START_ARGS)):
            done = subprocess.run(
                [str(BUILD / "bin" / "px4-logger"), *args],
                cwd=BUILD / "rootfs",
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            ok &= done.returncode == 0
            texts.append(f"logger {args[0]}: {done.returncode} {(done.stdout + done.stderr).strip()}")
        return ok, "; ".join(texts)

    def problems(self) -> list[str]:
        """Checks after stop(): nothing left running; with an external mode, the commander never dropped it."""
        found = []
        for _ in range(10):  # Gazebo may need a few seconds after calistir.sh has returned
            if not running():
                break
            time.sleep(1)
        else:
            found.append(LEFT_RUNNING)
        lines = self.unresponsive()
        if lines:
            found.append(
                f"PX4 harici modu 'unresponsive' olarak işaretledi (sim.log, {len(lines)} satır; ilki: {lines[0]})"
            )
        return found

    def ulogs(self) -> list[Path]:
        """ULog files of this start, oldest first (more than one after restart_logger())."""
        logs = [p for p in (BUILD / "rootfs" / "log").rglob("*.ulg") if p.stat().st_mtime >= self.started]
        return sorted(logs, key=lambda p: p.stat().st_mtime)

    def newest_ulog(self) -> Path | None:
        logs = self.ulogs()
        return logs[-1] if logs else None
