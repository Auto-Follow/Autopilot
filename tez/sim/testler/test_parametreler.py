"""Start parameter files (.params): parsing, rejected lines, load order and the PX4_PARAM_* environment."""

import re
from pathlib import Path

import pytest

import parametreler

GOOD = """
# real vehicle gains

IMU_GYRO_CUTOFF 30        # 4019_x500_v2
MC_ROLLRATE_P   0.14      # 4019_x500_v2
EKF2_HGT_REF    1         # 22.08.2026.params (GPS)
"""


def write(tmp_path: Path, text: str, name: str = "a.params") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_comments_and_blank_lines_are_skipped(tmp_path: Path) -> None:
    params = parametreler.read_file(write(tmp_path, GOOD))
    assert [(p.name, p.value) for p in params] == [
        ("IMU_GYRO_CUTOFF", 30),
        ("MC_ROLLRATE_P", 0.14),
        ("EKF2_HGT_REF", 1),
    ]
    assert isinstance(params[0].value, int) and isinstance(params[1].value, float)
    assert params[1].source == "a.params:5 # 4019_x500_v2"


@pytest.mark.parametrize(
    "line, message",
    [
        ("mc_rollrate_p 0.14  # x", "satır 2: 'mc_rollrate_p'"),
        ("MC_ROLLRATE_P_TOO_LONG 0.14  # x", "satır 2: 'MC_ROLLRATE_P_TOO_LONG'"),
        ("MC_ROLLRATE_P abc  # x", "satır 2: MC_ROLLRATE_P: değer sayı olmalı"),
        ("MC_ROLLRATE_P nan  # x", "satır 2: MC_ROLLRATE_P: değer sayı olmalı"),
        ("MC_ROLLRATE_P  # x", "satır 2: 'AD DEĞER  # kaynak'"),
        ("MC_ROLLRATE_P 0.14 0.15  # x", "satır 2: 'AD DEĞER  # kaynak'"),
        ("MC_ROLLRATE_P 0.14", "satır 2: MC_ROLLRATE_P: kaynak yorumu yok"),
        ("IMU_GYRO_CUTOFF 40  # again", "satır 2: IMU_GYRO_CUTOFF: aynı dosyada satır 1'de de var"),
    ],
)
def test_bad_lines_name_the_line_and_the_parameter(tmp_path: Path, line: str, message: str) -> None:
    path = write(tmp_path, f"IMU_GYRO_CUTOFF 30  # first\n{line}\n")
    with pytest.raises(ValueError, match=re.escape(f"a.params: {message}")):
        parametreler.read_file(path)


def test_load_order_last_one_wins(tmp_path: Path) -> None:
    real = write(tmp_path, "FLW_TGT_DST 8  # real\nFLW_TGT_HT 8  # real\nMPC_TILTMAX_AIR 45  # real\n", "r.params")
    sim = write(tmp_path, "FLW_TGT_HT 9  # sim\nSDLOG_PROFILE 163  # sim\n", "s.params")
    merged = parametreler.load(
        files=(real, sim),
        scenario={"FLW_TGT_DST": 10, "MPC_TILTMAX_AIR": 30},
        overrides=["MPC_TILTMAX_AIR=35", "FLW_TGT_DST=12.5"],
    )
    assert {n: p.value for n, p in merged.items()} == {
        "FLW_TGT_DST": 12.5,
        "FLW_TGT_HT": 9,
        "MPC_TILTMAX_AIR": 35,
        "SDLOG_PROFILE": 163,
    }
    assert merged["FLW_TGT_HT"].source == "s.params:1 # sim"
    assert merged["FLW_TGT_DST"].source == "--param"
    # the scenario layer sits between the files and the command line
    only_scenario = parametreler.load(files=(real,), scenario={"FLW_TGT_DST": 10})
    assert only_scenario["FLW_TGT_DST"].value == 10 and only_scenario["FLW_TGT_DST"].source == "takip.px4_parametreleri"
    # and it is checked like a file
    with pytest.raises(ValueError, match="takip.px4_parametreleri: 'flw_tgt_dst'"):
        parametreler.load(files=(), scenario={"flw_tgt_dst": 10})
    with pytest.raises(ValueError, match=r"takip\.px4_parametreleri: FLW_TGT_DST: değer sayı olmalı"):
        parametreler.load(files=(), scenario={"FLW_TGT_DST": True})


def test_command_line_assignment() -> None:
    assert parametreler.parse_assignment("FLW_TGT_DST=10") == parametreler.Param("FLW_TGT_DST", 10, "--param")
    assert parametreler.parse_assignment(" FLW_TGT_HT = -1.5e1 ").value == -15.0
    for text in ("FLW_TGT_DST:10", "FLW_TGT_DST", "flw_tgt_dst=10", "FLW_TGT_DST=", "FLW_TGT_DST=on"):
        with pytest.raises(ValueError, match="--param"):
            parametreler.parse_assignment(text)


def test_environment_lines() -> None:
    merged = parametreler.merge(
        [parametreler.Param("SDLOG_PROFILE", 163, "s"), parametreler.Param("MC_ROLLRATE_D", 0.004, "r")],
        [parametreler.Param("FLW_TGT_DST", 8.0, "x"), parametreler.Param("MPC_XY_VEL_MAX", 1e-7, "x")],
    )
    assert parametreler.env_lines(merged) == [
        "PX4_PARAM_SDLOG_PROFILE=163",
        "PX4_PARAM_MC_ROLLRATE_D=0.004",
        "PX4_PARAM_FLW_TGT_DST=8",
        "PX4_PARAM_MPC_XY_VEL_MAX=1e-07",
    ]


def test_values_read_back_from_px4() -> None:
    """F0 compares every loaded value with PARAM_VALUE: INT32 arrives bit for bit in the float field, floats as
    float32."""
    import struct

    from px4_baglanti import decode_param_value, mavutil

    as_float = struct.unpack("<f", struct.pack("<i", 4001))[0]  # what pymavlink hands over for SYS_AUTOSTART 4001
    assert decode_param_value(as_float, mavutil.mavlink.MAV_PARAM_TYPE_INT32) == 4001
    minus_one = struct.unpack("<f", struct.pack("<i", -1))[0]  # a NaN bit pattern
    assert decode_param_value(minus_one, mavutil.mavlink.MAV_PARAM_TYPE_INT32) == -1
    float32 = struct.unpack("<f", struct.pack("<f", 0.14))[0]
    assert decode_param_value(float32, mavutil.mavlink.MAV_PARAM_TYPE_REAL32) == float32
    assert parametreler.matches(0.14, float32) and parametreler.matches(163, 163) and parametreler.matches(0, 0.0)
    assert not parametreler.matches(0.14, 0.15) and not parametreler.matches(0.004, 0.003)
    assert not parametreler.matches(8, None)


def test_shipped_files_and_command_line(capsys: pytest.CaptureFixture[str]) -> None:
    """The files in tez/sim/parametreler are valid; the command calistir.sh runs prints them (+ --param last)."""
    merged = parametreler.load()
    assert merged["SDLOG_PROFILE"].value == 163
    gains = {"IMU_GYRO_CUTOFF": 30, "MC_ROLLRATE_P": 0.14, "MC_PITCHRATE_P": 0.14, "MC_ROLLRATE_I": 0.3}
    gains |= {"MC_PITCHRATE_I": 0.3, "MC_ROLLRATE_D": 0.004, "MC_PITCHRATE_D": 0.004}
    assert {n: merged[n].value for n in gains} == gains
    assert "MIS_TAKEOFF_ALT" not in merged and not any(n.startswith("CA_") for n in merged)

    assert parametreler.main(["--param", "FLW_TGT_DST=10"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert "PX4_PARAM_SDLOG_PROFILE=163" in lines and "PX4_PARAM_FLW_TGT_DST=10" in lines
    assert len(lines) == len(merged | {"FLW_TGT_DST": None})

    assert parametreler.main(["--param", "FLW_TGT_DST=on"]) == 2
    assert "--param" in capsys.readouterr().err
