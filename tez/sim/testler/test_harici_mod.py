"""Plugging an out-of-tree PX4 module into the sim (spec 2026-11-10-m06-sim-ortami, task group 10): the start commands
of the scenario and of the command line reach calistir.sh in their order, the run waits until calistir.sh has run
them, and only a run with them is checked for an external mode the commander marked unresponsive."""

import subprocess
from pathlib import Path

import pytest

import hedef
import senaryo
import simulasyon

EXTERNAL = """
ad: harici
drone: {yukseklik_m: 9}
takip:
  kaynak: tez_los
  mod_adi: Tez Auto Follow
  los: hakem
  px4_baslat: [tez_auto_follow start, tez_auto_follow status]
  px4_parametreleri: {FLW_TGT_DST: 9}
algilama: {etkin: false}
video: {mp4: false}
hedef:
  baslangic: [10, 0]
  yol:
    - {nokta: [20, 0], hiz_mps: 1.0}
zamanlama: {baslama_s: 60, son_bekleme_s: 5}
"""
RCS_DONE = "INFO  [init] Startup script returned successfully\n"
UNRESPONSIVE = "WARN  [health_and_arming_checks] No response from 0, flagging unresponsive\n"  # externalChecks.cpp


def write(tmp_path: Path, text: str) -> str:
    path = tmp_path / "s.yaml"
    path.write_text(text, encoding="utf-8")
    return str(path)


def values(args: list[str], flag: str) -> list[str]:
    return [args[i + 1] for i, arg in enumerate(args) if arg == flag]


def test_start_commands_reach_calistir_in_order(tmp_path: Path) -> None:
    """takip.px4_baslat, then --px4-baslat, in their order, after the start parameters (takip.px4_parametreleri, then
    --param); the run may start (wired since task group 10) and the mode name is left to PX4's list."""
    cli = hedef.CommandLine(params=("MPC_XY_VEL_MAX=5",), px4_start=("af_extra start",))
    sc = hedef.load(write(tmp_path, EXTERNAL), cli)
    hedef.check_wired(sc)
    senaryo.check_mode(sc)  # not a stock name, but an external mode registers after PX4 starts
    sim = senaryo.simulation(sc, tmp_path / "out", tmp_path / "w.sdf", headless=True)
    args = sim.command()
    assert args[:4] == [str(simulasyon.SIM_DIR / "calistir.sh"), "--dunya", str(tmp_path / "w.sdf"), "--ekransiz"]
    assert values(args, "--param") == ["FLW_TGT_DST=9", "MPC_XY_VEL_MAX=5"]
    starts = ["tez_auto_follow start", "tez_auto_follow status", "af_extra start"]
    assert values(args, "--px4-baslat") == starts
    assert args.index("--px4-baslat") > max(i for i, arg in enumerate(args) if arg == "--param")
    assert sim.external_mode
    assert senaryo.settings(sc)["takip"]["px4_baslat"] == starts  # ozet.json "ayarlar"

    stock = hedef.load(
        write(tmp_path, EXTERNAL.replace("  px4_baslat: [tez_auto_follow start, tez_auto_follow status]\n", ""))
    )
    sim = senaryo.simulation(stock, tmp_path / "out", tmp_path / "w.sdf", headless=False)
    assert "--px4-baslat" not in sim.command() and "--ekransiz" not in sim.command()
    assert not sim.external_mode
    with pytest.raises(ValueError, match="'Tez Auto Follow' PX4'ün seçilebilir modları arasında yok"):
        senaryo.check_mode(stock)  # without a start command only PX4's own modes exist


def test_unresponsive_is_looked_for_only_with_an_external_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A stock run is never checked for "unresponsive"; a run with start commands is, from its sim.log."""
    monkeypatch.setattr(simulasyon, "running", lambda: False)  # nothing left running after the stop
    for name, px4_start, log, found in (
        ("stok", (), RCS_DONE + UNRESPONSIVE, 0),
        ("harici_temiz", ("tez_auto_follow start",), RCS_DONE, 0),
        ("harici_unresponsive", ("tez_auto_follow start",), RCS_DONE + UNRESPONSIVE + UNRESPONSIVE, 2),
    ):
        out = tmp_path / name
        out.mkdir()
        (out / "sim.log").write_text(log, encoding="utf-8")
        sim = simulasyon.Simulation(out, px4_start=px4_start)
        assert sim.external_mode == bool(px4_start)
        assert sim.unresponsive() == [UNRESPONSIVE.strip()] * found
        problems = sim.problems()
        assert len(problems) == (1 if found else 0)
        if found:
            assert "'unresponsive'" in problems[0] and "2 satır" in problems[0] and "No response from 0" in problems[0]


class _Running:
    """calistir.sh still running (subprocess.Popen.poll)."""

    def poll(self) -> None:
        return None


def test_the_run_waits_until_calistir_ran_the_start_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With start commands PX4 is ready once rcS is done and calistir.sh ran them all (in either order); a failed
    command or a logger that never came up is a failed start. The lines are the ones calistir.sh prints."""
    monkeypatch.setattr(simulasyon.time, "sleep", lambda _s: None)

    def ready(px4_start: tuple[str, ...], log: str) -> bool:
        sim = simulasyon.Simulation(tmp_path, px4_start=px4_start)
        sim.proc = _Running()
        sim.log_path.write_text(log, encoding="utf-8")
        return sim.wait_ready(timeout=0.05)

    ran = (
        "PX4 başlatma komutu: x start\n"
        "INFO  [x] started\n"
        "PX4 başlatma komutu bitti (çıkış kodu 0): x start\n"
        "PX4 başlatma komutları tamam (1 komut)\n"
    )
    failed = "PX4 başlatma komutu: x start\nPX4 başlatma komutu başarısız (çıkış kodu 1): x start\n"
    no_logger = "PX4 başlatma komutları çalıştırılamadı: px4-logger status 90 s içinde başarılı olmadı\n"
    assert ready((), RCS_DONE)
    assert not ready(("x start",), RCS_DONE)  # rcS is done, the commands are not
    assert ready(("x start",), ran + RCS_DONE)  # they wait for the logger, which rcS starts second to last
    assert ready(("x start",), RCS_DONE + ran)
    assert not ready(("x start",), RCS_DONE + failed)
    assert not ready(("x start",), no_logger)

    sim = simulasyon.Simulation(tmp_path, px4_start=("x start", "y start"))
    sim.log_path.write_text(ran + "PX4 başlatma komutu başarısız (çıkış kodu -1): y start\n", encoding="utf-8")
    assert sim.start_results() == [{"komut": "x start", "cikis_kodu": 0}, {"komut": "y start", "cikis_kodu": -1}]

    script = (simulasyon.SIM_DIR / "calistir.sh").read_text(encoding="utf-8")
    for line in (simulasyon.START_DONE_LINE, *simulasyon.START_FAILED_LINES):
        assert f'echo "{line}' in script
    assert 'echo "PX4 başlatma komutu bitti (çıkış kodu 0): $text"' in script
    assert 'echo "PX4 başlatma komutu başarısız (çıkış kodu $status): $text"' in script


@pytest.mark.skipif(not (simulasyon.BUILD / "bin" / "px4").is_file(), reason="PX4 derlenmemiş (tez/sim/derle.sh)")
def test_calistir_refuses_a_start_command_before_anything_starts(tmp_path: Path) -> None:
    """A command this build does not have (an out-of-tree module that was not built in), an empty one or a missing
    value stops calistir.sh with exit code 2 before Gazebo or PX4 start. The world does not exist either: if the start
    commands were not checked first, the message would be about the world."""

    def run(*args: str) -> subprocess.CompletedProcess:
        world = ["--dunya", str(tmp_path / "yok.sdf")]
        return subprocess.run(
            [str(simulasyon.SIM_DIR / "calistir.sh"), *world, *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    missing = run("--px4-baslat", "logger status", "--px4-baslat", "yok_boyle_modul start")
    assert missing.returncode == 2
    assert "'yok_boyle_modul' bu PX4 derlemesinde yok" in missing.stderr and "derle.sh --harici" in missing.stderr
    empty = run("--px4-baslat", "  ")
    assert empty.returncode == 2 and "boş PX4 komutu" in empty.stderr
    no_value = run("--px4-baslat")
    assert no_value.returncode == 2 and "--px4-baslat bir değer ister" in no_value.stderr
    stock = run("--px4-baslat", "logger status")  # a command of the stock build passes; then the world is missing
    assert stock.returncode == 2 and "Dünya dosyası yok" in stock.stderr
