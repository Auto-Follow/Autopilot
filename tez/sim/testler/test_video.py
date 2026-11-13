"""kosu.mp4 (video.py) without a simulation: the 2000x720 frame, where the boxes land in the camera panel, which model
result PX4 had at a moment, the top view's geometry, the status line, the ffmpeg pipe (a fake ffmpeg, no encoder) and
a whole video from a small run folder."""

import json
import math
import shutil
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import pytest

import goruntu_yayini
import hedef
import kamera
import konumlama
import video

CM3 = kamera.Camera(2304, 1296, 1773.9, 1773.9, 1152.0, 648.0)


class FakeFfmpeg:
    """subprocess.Popen stand-in: keeps the command and every byte written to its stdin; "encodes" on wait()."""

    last: "FakeFfmpeg | None" = None

    def __init__(self, cmd: list[str], **_: object) -> None:
        self.cmd = cmd
        self.data = bytearray()
        self.stdin = self
        self.returncode: int | None = None
        FakeFfmpeg.last = self

    def write(self, data: bytes) -> int:
        self.data += data
        return len(data)

    def close(self) -> None:
        pass

    def wait(self, timeout: float | None = None) -> int:
        self.returncode = 0
        Path(self.cmd[-1]).write_bytes(b"mp4")
        return 0

    def kill(self) -> None:
        self.returncode = -9


def test_frame_is_2000_by_720_camera_left_top_view_right() -> None:
    left = np.full((720, 1280, 3), 10, np.uint8)
    right = np.full((720, 720, 3), 200, np.uint8)
    frame = video.compose(left, right)
    assert frame.shape == (720, 2000, 3) and frame.shape[0] % 2 == 0 and frame.shape[1] % 2 == 0  # yuv420p
    assert (frame[:, :1280] == 10).all() and (frame[:, 1280:] == 200).all()
    assert video.SIZE == (2000, 720) and video.LEFT == (1280, 720) and video.RIGHT == (720, 720)
    with pytest.raises(ValueError):
        video.compose(left[:, :1000], right)


def test_boxes_land_where_they_are_in_the_full_resolution_image() -> None:
    """Boxes are pixel edges of the 2304x1296 camera image; the panel shows it at 1280x720 (factor 1280/2304)."""
    assert video.to_panel((1152.0, 648.0, 2304.0, 1296.0)) == pytest.approx((640.0, 360.0, 1280.0, 720.0))
    img = np.zeros((720, 1280, 3), np.uint8)
    video.draw_box(img, (461.0, 259.0, 922.0, 778.0), video.TARGET_BGR, 3)  # panel: (256.1, 143.9) .. (512.2, 432.2)
    assert tuple(img[144, 380]) == video.TARGET_BGR  # top edge
    assert tuple(img[300, 256]) == video.TARGET_BGR  # left edge
    assert tuple(img[432, 380]) == video.TARGET_BGR  # bottom edge
    assert not img[300, 380].any() and not img[100, 380].any()  # inside and above: untouched


def test_the_model_result_px4_had_at_a_moment() -> None:
    """The newest result that had gone out by then (send time); a refused one counts from when it left the delay
    line, one without either from when it was ready. Before the first one: none."""
    rows = pd.DataFrame(
        {
            "t_us": [60_000_000, 60_100_000, 60_200_000],
            "t": [60.0, 60.1, 60.2],
            "gonderim_sim": [60.13, math.nan, 60.33],
            "serbest_sim": [60.13, 60.25, 60.33],
            "hazir_sim": [60.12, 60.24, 60.32],
            "secim": ["izleme", "eslesmedi", "izleme"],
            "secilen_kutu": [0, math.nan, 1],
            "secilen_guven": [0.8, math.nan, 0.6],
            "uctan_uca_ms": [130.0, math.nan, 130.0],
        }
    )
    boxes = {60_000_000: [(1, 2, 3, 4, 0.8)], 60_200_000: [(5, 6, 7, 8, 0.3), (9, 9, 12, 12, 0.6)]}
    model = video.ModelTimeline(rows, boxes)
    assert model.at(60.12) is None
    assert model.at(60.2).t == pytest.approx(60.0) and model.at(60.2).boxes == [(1, 2, 3, 4, 0.8)]
    assert model.at(60.3).state == "eslesmedi" and model.at(60.3).boxes == []
    shown = model.at(60.4)
    assert shown.t == pytest.approx(60.2) and shown.chosen == 1 and shown.age_s == pytest.approx(0.2)


def test_camera_footprint_on_the_ground() -> None:
    """Level drone at the take-off point looking east, nominal 45 deg mount, camera 8 m above the ground: the image's
    bottom edge meets the ground 8 / tan(45 + 20.07 deg) ahead of the camera, the top edge 8 / tan(45 - 20.07 deg);
    rays that miss the ground are cut at the farthest range."""
    r_wo = video.optical_to_world((1.0, 0.0, 0.0, 0.0), konumlama.NOMINAL_MOUNT)
    pts = video.ground_footprint(CM3, (0.151, 0.0, 8.0), r_wo)
    half = math.atan2(648.0, 1773.9)
    on_axis = pts[np.abs(pts[:, 1]) < 1e-6]
    assert on_axis[:, 0].min() == pytest.approx(0.151 + 8.0 / math.tan(math.pi / 4 + half), abs=0.01)
    assert on_axis[:, 0].max() == pytest.approx(0.151 + 8.0 / math.tan(math.pi / 4 - half), abs=0.01)
    level = video.optical_to_world((1.0, 0.0, 0.0, 0.0), kamera.camera_to_body(0.0))  # looking at the horizon
    far = video.ground_footprint(CM3, (0.0, 0.0, 8.0), level)
    assert np.hypot(far[:, 0], far[:, 1]).max() == pytest.approx(video.FOOTPRINT_MAX_M, abs=0.01)


def test_top_view_north_up_and_its_scale_bar() -> None:
    view = video.TopView((10.0, 0.0), 30.0)
    cu, cv = view.centre_px
    assert view.px(10.0, 0.0) == (cu, cv)
    assert view.px(12.0, 0.0) == (cu + 60, cv)  # east is right
    assert view.px(10.0, 1.0) == (cu, cv - 30)  # north is up
    assert video.scale_bar_m(30.0) == 5.0 and video.scale_bar_m(10.0) == 10.0 and video.scale_bar_m(60.0) == 2.0


def test_status_line_says_what_happens_and_turns_red() -> None:
    """Lock lost, no target, closer than the camera's near limit (or 3 m), target out of view: red. Standing before
    the walk: the follow start; PX4's speed estimate above 1 m/s is what updates its course."""
    calm = video.Situation(t=40.0, start_s=60.0, following=True, speed=0.0, distance=8.1, near_limit=3.9)
    line1, line2, level = video.status(calm)
    assert "Takip başı" in line1 and "8.1 m" in line1 and level == "normal"
    _, line2, _ = video.status(video.Situation(**{**calm.__dict__, "px4_speed": 1.3, "px4_course_deg": 0.0}))
    assert "1.3 m/s" in line2 and "rota" in line2 and "kuzey" in line2
    walking = video.Situation(t=65.0, start_s=60.0, following=True, speed=1.4, distance=7.5, behind_error=23.0)
    line1, _, level = video.status(walking)
    assert "yürüyor" in line1 and "23°" in line1 and level == "normal"
    for change, words in (
        ({"distance": 2.4}, "3 m"),
        ({"distance": 3.5, "near_limit": 3.9}, "yakın görüş sınırı"),
        ({"lock": "kilit_kaybi"}, "kilit"),
        ({"no_target": True}, "hedef yok"),
        ({"in_view": False}, "kadraj dışında"),
    ):
        _, line2, level = video.status(video.Situation(**{**walking.__dict__, **change}))
        assert level == "alarm" and words in line2, change
    _, line2, level = video.status(video.Situation(**{**walking.__dict__, "behind_error": 120.0}))
    assert level == "uyari" and "önünde" in line2
    # a near pass of ozet.json (task group 9): its cause, orange at 5 m, with the red 3 m alarm at 2.4 m
    _, line2, level = video.status(video.Situation(**{**walking.__dict__, "distance": 5.0, "near_pass": "kose"}))
    assert level == "uyari" and "6 m" in line2 and "köşe" in line2
    _, line2, level = video.status(video.Situation(**{**walking.__dict__, "distance": 2.4, "near_pass": "kose"}))
    assert level == "alarm" and "3 m" in line2 and "köşe" in line2


def test_where_px4_sends_the_drone_comes_from_its_own_setpoint() -> None:
    """The ring (where PX4 sends the drone now) is trajectory_setpoint and the cross (its final aim) is
    desired_position_raw, both around F, the task's filtered target: at a corner F is metres ahead of the
    estimator's E, so E + FLW_TGT_DST along the orbit angle (the drawing of task group 8) was off by as much. Without
    those topics (older ULogs) the marks fall back to E."""
    view = video.Px4View(
        estimate=(20.0, 12.0),
        speed=2.0,
        stale=False,
        course=0.0,
        orbit=math.pi,
        follow_angle=math.pi,
        filtered=(20.5, 15.0),
        setpoint=(20.4, 7.6),
        aim=(20.5, 7.0),
    )
    marks = video.px4_marks(view, 8.0)
    assert marks["ring"] == (20.4, 7.6) and marks["cross"] == (20.5, 7.0) and marks["base"] == (20.5, 15.0)
    old = video.px4_marks(video.Px4View((20.0, 12.0), 2.0, False, 0.0, math.pi, math.pi), 8.0)
    assert old["base"] == (20.0, 12.0) and old["ring"] == pytest.approx((20.0, 4.0))
    assert old["cross"] == pytest.approx((20.0, 4.0)) and old["filtered"] is None


def test_frames_go_raw_bgr_through_a_pipe_to_ffmpeg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(video.subprocess, "Popen", FakeFfmpeg)
    red = np.zeros((720, 2000, 3), np.uint8)
    red[..., 2] = 255  # BGR: red
    with video.Encoder(tmp_path / "kosu.mp4") as enc:
        enc.write(red)
        enc.write(red)
    cmd = FakeFfmpeg.last.cmd
    i = cmd.index("-i")
    before, after = cmd[:i], cmd[i:]

    def value(part: list[str], flag: str) -> str:
        return part[part.index(flag) + 1]

    assert cmd[0] == "ffmpeg" and value(before, "-f") == "rawvideo" and value(before, "-pix_fmt") == "bgr24"
    assert value(before, "-s") == "2000x720" and value(before, "-r") == "15" and value(cmd, "-i") == "-"
    assert value(after, "-c:v") == "libx264" and value(after, "-pix_fmt") == "yuv420p"
    assert value(after, "-preset") == "veryfast" and value(after, "-crf") == "23"
    assert value(after, "-movflags") == "+faststart" and cmd[-1] == str(tmp_path / "kosu.mp4")
    assert len(FakeFfmpeg.last.data) == 2 * 2000 * 720 * 3 and bytes(FakeFfmpeg.last.data[:3]) == b"\x00\x00\xff"
    with pytest.raises(ValueError), video.Encoder(tmp_path / "x.mp4", size=(641, 360)):
        pass  # odd sizes cannot be yuv420p


def run_folder(tmp_path: Path, frames: bool = True) -> Path:
    """A small follow_me run 60..61 s: referee rows at 30 Hz, camera frames on the 15 fps grid, two model results."""
    folder = tmp_path / "kosu"
    folder.mkdir(parents=True)
    shutil.copy(hedef.SIM_DIR / "senaryolar" / "takip_yuruyen.yaml", folder / "senaryo.yaml")
    times = [round(round(k / 30 / 0.004) * 0.004, 3) for k in range(1800, 1831)]
    rows = [
        {
            "t": t,
            "dron_x": 2.0,
            "dron_y": 0.0,
            "dron_z": 8.0,
            "dron_qw": 1.0,
            "dron_qx": 0.0,
            "dron_qy": 0.0,
            "dron_qz": 0.0,
            "dron_yaw_deg": 90.0,
            "kamera_x": 2.151,
            "kamera_y": 0.0,
            "kamera_z": 7.965,
            "hedef_x": 10.0 + 1.4 * (t - 60.0),
            "hedef_y": 0.0,
            "hedef_yaw": 0.0,
            "hedef_hiz": 1.4,
            "yatay_mesafe": 8.0 + 1.4 * (t - 60.0),
            "kadrajda": True,
            "gorunur": True,
            "hedef_kutu_u0": 1100.0,
            "hedef_kutu_v0": 500.0,
            "hedef_kutu_u1": 1200.0,
            "hedef_kutu_v1": 700.0,
        }
        for t in times
    ]
    pd.DataFrame(rows).to_csv(folder / "dogru_cevap.csv", index=False, float_format="%.4f")
    pd.DataFrame(
        {
            "t_us": [60_000_000, 60_400_000],
            "t": [60.0, 60.4],
            "secim": ["izleme", "izleme"],
            "secilen_kutu": [0, 0],
            "secilen_guven": [0.8, 0.7],
            "hazir_sim": [60.12, 60.52],
            "serbest_sim": [60.12, 60.52],
            "gonderim_sim": [60.12, 60.52],
            "uctan_uca_ms": [120.0, 120.0],
        }
    ).to_csv(folder / "algilama.csv", index=False)
    pd.DataFrame(
        {"t_us": [60_000_000, 60_400_000], "kutu": [0, 0], "u0": [1090.0] * 2, "v0": [495.0] * 2}
        | {"u1": [1205.0] * 2, "v1": [705.0] * 2, "guven": [0.8, 0.7]}
    ).to_csv(folder / "kutular.csv", index=False)
    summary = {
        "kamera": CM3.as_dict(),
        "kamera_montaji": None,
        "ayarlar": {
            "takip": {"kaynak": "follow_me", "mod": "Follow Target", "los": "model"},
            "px4_parametreleri": {"FLW_TGT_DST": {"deger": 8, "px4": 8.0}},
        },
        "mod": {"ulog": [], "mavlink": [[25.0, "Follow Target"]]},
    }
    (folder / "ozet.json").write_text(json.dumps(summary), encoding="utf-8")
    if frames:
        (folder / "kareler").mkdir()
        rgb = np.full((1296, 2304, 3), 90, np.uint8)
        picker = goruntu_yayini.GridPicker()
        for t in times:
            if picker.pick(t, 60.0, 61.0) is not None:
                goruntu_yayini.write_jpeg(rgb, folder / "kareler" / goruntu_yayini.frame_name(t))
    return folder


def test_whole_video_of_a_run_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """One frame per 1/15 s of the referee's recording (its first to its last row), each 2000x720; the frames folder
    goes afterwards unless it is kept. Without camera frames the top view still plays (the camera panel says so)."""
    monkeypatch.setattr(video.subprocess, "Popen", FakeFfmpeg)
    folder = run_folder(tmp_path)
    info = video.make(folder, {"yazilan": 16}, keep_frames=True)
    assert info["kare_sayisi"] == 16 and info["kamera_karesi"] == 16 and info["eksik_kare"] == 0
    assert info["sure_s"] == pytest.approx(16 / 15) and info["boyut"] == [2000, 720] and info["fps"] == 15
    assert info["kayit"] == {"yazilan": 16} and (folder / "kosu.mp4").is_file()
    assert len(FakeFfmpeg.last.data) == 16 * 2000 * 720 * 3 and (folder / "kareler").is_dir()
    frame = np.frombuffer(bytes(FakeFfmpeg.last.data[: 2000 * 720 * 3]), np.uint8).reshape(720, 2000, 3)
    assert abs(int(np.median(frame[400:700, 100:1200])) - 90) < 10  # the camera frame on the left

    video.make(folder, None, keep_frames=False)
    assert not (folder / "kareler").exists()
    info = video.make(run_folder(tmp_path / "b", frames=False))
    assert info["kare_sayisi"] == 16 and info["kamera_karesi"] == 0 and info["eksik_kare"] == 16


def test_frames_of_a_folder_by_slot_and_the_timeline(tmp_path: Path) -> None:
    """Every JPEG goes to its nearest 1/15 s slot; slots without one show the frame before (counted as missing)."""
    folder = tmp_path / "kareler"
    folder.mkdir()
    for t in (60.0, 60.068, 60.2):  # slot 901 (60.067) is there, slot 902 (60.133) is not
        (folder / goruntu_yayini.frame_name(t)).write_bytes(b"")
    found = video.frames_by_slot(folder)
    assert sorted(found) == [900, 901, 903] and found[901][0] == pytest.approx(60.068)
    plan = video.timeline(60.0, 60.2, found)
    assert [k for k, _, _ in plan] == [900, 901, 902, 903]
    assert [missing for _, _, missing in plan] == [False, False, True, False]
    assert plan[2][1] == found[901]  # the frame before
    assert cv2.imread(str(found[900][1])) is None  # (empty files are fine for the plan)


def test_preview_video_is_mp4_through_the_same_pipe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """onizleme.py writes MP4 (H.264) through video.Encoder instead of WebM: half the camera's resolution, its own
    frame rate, RGB frames turned into the pipe's BGR."""
    import onizleme

    monkeypatch.setattr(video.subprocess, "Popen", FakeFfmpeg)
    rgb = np.zeros((1296, 2304, 3), np.uint8)
    rgb[..., 0] = 255  # RGB red
    path = onizleme.write_video([(61.0, rgb), (60.9, rgb), (61.1, rgb)], tmp_path / "onizleme")
    assert path.suffix == ".mp4" and path.is_file()
    cmd = FakeFfmpeg.last.cmd
    assert cmd[cmd.index("-s") + 1] == "1152x648" and cmd[cmd.index("-r") + 1] == str(onizleme.VIDEO_FPS)
    assert "libx264" in cmd and len(FakeFfmpeg.last.data) == 3 * 1152 * 648 * 3
    assert bytes(FakeFfmpeg.last.data[:3]) == b"\x00\x00\xff"
