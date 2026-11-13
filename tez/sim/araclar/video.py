#!/usr/bin/env python3
"""kosu.mp4 of a run (spec "9. Ölçütler, rapor ve MP4 video"): the drone camera on the left, a top view of the scene
on the right, one 2000x720 frame per 1/15 s of sim time over the referee's recording (the drone in its mode: the
follow start while the person stands, then the recording window).

    ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/video.py tez/sim/sonuclar/<klasör>
    ... --kareleri-sil      delete kareler/ afterwards (senaryo.py does that itself unless --kareleri-sakla)

Made offline after the run (senaryo.py hands it to rapor.write) from the files of the run folder only: the camera
frames goruntu_yayini.py kept during the recording (kareler/<t_us>.jpg, 1280x720), dogru_cevap.csv (referee),
algilama.csv + kutular.csv (model), tez_los.csv, follow_target.csv, ozet.json (camera, mount, mode, FLW_TGT_DST) and
PX4's ULog (follow_target_status, follow_target_estimator: what PX4 assumed). So the video never slows the run down,
every tracking source gets the same video from the same files, and a run with kept frames can be made again.

Left, 1280x720, the drone camera: the referee's boxes of that frame (target blue, other people orange), the model
result PX4 had at that moment (the newest one sent by then: the chosen box thick red with its confidence, the others
thin; it belongs to an older frame, so it lags behind the person), "HEDEF YOK" while the last TEZ_LOS said so, sim
time, PX4 mode and end-to-end delay.
Right, 720x720, the top view (north up, the report's colours): trees, people and their last 10 s, the drone and its
nose, the camera's footprint on the ground, the 3 m warning ring and the camera's near limit around the person, where
the drone should be (FLW_TGT_DST behind the walking person), the FOLLOW_TARGET points of the last 3 s and, in
follow_me, PX4's own target estimate and its filtered target (the one the drone is placed around), the course it
assumes, the place it sends the drone to now (its position setpoint) and its final aim; a scale bar, the horizontal
distance and a short status line at the bottom (red: "YANLIŞ KİŞİ" when the chosen box PX4 had is on another person
by the referee, the rule of yanlis_kisi_orani (olcum.wrong_person), with the person dressed like the target named;
lock lost, no target, closer than the camera's near limit or 3 m, target out of view; the cause of a < 6 m pass of
ozet.json "yakin_gecis").

Frames go raw (bgr24) through a pipe to ffmpeg: libx264, yuv420p, veryfast, crf 23, +faststart, 15 fps; VLC 3.0.20
plays it. OpenCV's VideoWriter is not used: the pip OpenCV has no H.264 encoder.
"""

import argparse
import functools
import json
import math
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import dunya
import matplotlib
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

import goruntu_yayini
import hedef
import kamera
import konumlama
import olcum
import rapor

FPS = goruntu_yayini.FPS
LEFT = goruntu_yayini.FRAME_SIZE  # (1280, 720) camera panel
RIGHT = (720, 720)  # top view
SIZE = (LEFT[0] + RIGHT[0], LEFT[1])  # (2000, 720)
VIDEO_NAME = "kosu.mp4"
CAMERA_WIDTH = 2304  # [px] of the drone camera; boxes are in its pixels
TRAIL_S = 10.0  # [s] of the drone's and the people's path shown behind them
FOLLOW_POINTS_S = 3.0  # [s] of FOLLOW_TARGET points shown (the jitter of the position PX4 gets)
# what the video reads of PX4's ULog (olcum.Px4Follow: the estimator, the task's status, its setpoint, the EKF origin)
PX4_TOPICS = ("follow_target_estimator", "follow_target_status", "trajectory_setpoint", "vehicle_local_position")
FOOTPRINT_MAX_M = 60.0  # [m] a camera ray that misses the ground (or meets it farther) is cut here
FOOTPRINT_STEPS = 8  # pieces per image edge of the footprint polygon
VIEW_MARGIN_M = 7.0  # [m] around half the drone-target distance
VIEW_HALF_MIN_M, VIEW_HALF_MAX_M = 11.0, 26.0  # [m] limits of the half width the view shows
VIEW_HALF_PX = 285  # [px] that half width on the panel
VIEW_SMOOTH_S = 1.5  # [s] time constant of the view centre following the drone-target midpoint
LEGEND_H, STATUS_H = 60, 58  # [px] bands of the top view
PX4_COURSE_ARROW_M = 3.0  # [m]
TARGET_ARROW_S = 1.5  # [s] the person's arrow is its speed times this
STANDING_SPEED = 0.1  # [m/s] below: the person stands (PX4: MINIMUM_SPEED_FOR_TARGET_MOVING)
PX4_COURSE_SPEED = 1.0  # [m/s] PX4 updates its target course only above this (TARGET_SPEED_DEADZONE_...)
SUB = 4  # cv2 fixed-point bits: coordinates in 1/16 px


def _bgr(hex_colour: str) -> tuple[int, int, int]:
    r, g, b = (int(hex_colour[i : i + 2], 16) for i in (1, 3, 5))
    return b, g, r


TARGET_BGR = _bgr(rapor.TARGET_COLOR)
OTHER_BOX_BGR = _bgr(rapor.DRONE_COLOR)  # other people's referee boxes: orange (onizleme.py)
DRONE_BGR = _bgr(rapor.DRONE_COLOR)
OTHERS_BGR = _bgr(rapor.OTHERS_COLOR)
TREE_BGR = _bgr(rapor.TREE_COLOR)
WARNING_BGR = _bgr(rapor.WARNING_COLOR)
PX4_BGR = _bgr(rapor.PX4_COLOR)
SURFACE_BGR = _bgr(rapor.SURFACE)
TEXT_BGR = _bgr(rapor.TEXT)
TEXT2_BGR = _bgr(rapor.TEXT_2)
GRID_BGR = _bgr(rapor.GRID)
MODEL_BGR = _bgr("#eb1e1e")  # the model's boxes: red, brighter than the warning red on grass
BEHIND_BGR = _bgr("#1a7f37")  # where the drone should be
AMBER_BGR = _bgr("#9a6700")
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"  # DejaVu Sans of the pinned matplotlib: Turkish letters


@functools.cache
def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size)


@dataclass(frozen=True)
class Label:
    """A text drawn after the shapes (PIL: the letters ı, ş, ğ; cv2 has none). Colours in BGR like the frame."""

    x: float
    y: float
    text: str
    colour: tuple[int, int, int] = WHITE
    size: int = 16
    bold: bool = False
    anchor: str = "la"
    stroke: int = 0
    stroke_colour: tuple[int, int, int] = BLACK


def render_labels(frame: np.ndarray, labels: Sequence[Label]) -> np.ndarray:
    """The labels on a BGR frame (PIL does not care about the channel order; the colours are BGR as well)."""
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)
    for lb in labels:
        draw.text(
            (lb.x, lb.y),
            lb.text,
            fill=lb.colour,
            font=font(lb.size, lb.bold),
            anchor=lb.anchor,
            stroke_width=lb.stroke,
            stroke_fill=lb.stroke_colour,
        )
    return np.asarray(img)


def text_width(text: str, size: int, bold: bool = False) -> float:
    return font(size, bold).getlength(text)


def fit_text(text: str, width: float, bold: bool, sizes: Sequence[int] = (15, 13, 12, 11, 10)) -> tuple[str, int]:
    """(text, font size) that fits `width` [px]: the largest size, else the smallest with the last " · " items left
    out (the first one stays)."""
    for size in sizes:
        if text_width(text, size, bold) <= width:
            return text, size
    items = text.split(" · ")
    while len(items) > 1 and text_width(" · ".join(items), sizes[-1], bold) > width:
        items.pop()
    return " · ".join(items), sizes[-1]


def shade(img: np.ndarray, x0: int, y0: int, x1: int, y1: int, colour: tuple[int, int, int], alpha: float) -> None:
    """Blend a rectangle of colour into img in place."""
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(img.shape[1], x1), min(img.shape[0], y1)
    if x1 <= x0 or y1 <= y0:
        return
    roi = img[y0:y1, x0:x1].astype(np.float32)
    img[y0:y1, x0:x1] = (roi * (1.0 - alpha) + np.array(colour, np.float32) * alpha).astype(np.uint8)


def compose(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Camera panel | top view -> one SIZE frame (both even: yuv420p)."""
    if left.shape != (LEFT[1], LEFT[0], 3) or right.shape != (RIGHT[1], RIGHT[0], 3):
        raise ValueError(f"paneller {LEFT} ve {RIGHT} olmalı: {left.shape}, {right.shape}")
    return np.ascontiguousarray(np.concatenate([left, right], axis=1))


# --- camera panel ---------------------------------------------------------------------------------------------------


def to_panel(box: Sequence[float], scale: float = LEFT[0] / CAMERA_WIDTH) -> tuple[float, float, float, float]:
    """A box in camera pixels (pixel edges) -> panel pixels."""
    return tuple(float(v) * scale for v in box[:4])


def draw_box(
    img: np.ndarray,
    box: Sequence[float],
    colour: tuple[int, int, int],
    width: int,
    scale: float = LEFT[0] / CAMERA_WIDTH,
) -> tuple[int, int, int, int] | None:
    """Rectangle of a camera-pixel box on a panel; returns its panel corners (None for a NaN box)."""
    u0, v0, u1, v1 = to_panel(box, scale)
    if not all(math.isfinite(v) for v in (u0, v0, u1, v1)):
        return None
    corners = (round(u0), round(v0), round(u1), round(v1))
    cv2.rectangle(img, corners[:2], corners[2:], colour, width)
    return corners


def referee_boxes(row: Mapping, prefixes: Sequence[str]) -> list[tuple[str, tuple[float, float, float, float]]]:
    """(prefix, box) of every person the referee sees in a row (visible pixels; none for a hidden person)."""
    out = []
    for p in prefixes:
        box = tuple(float(row.get(f"{p}_kutu_{k}", math.nan)) for k in ("u0", "v0", "u1", "v1"))
        if all(math.isfinite(v) for v in box):
            out.append((p, box))
    return out


def draw_referee(
    img: np.ndarray, boxes: Sequence[tuple[str, Sequence[float]]], labels: list[Label], scale: float, dx: float = 0.0
) -> None:
    """The referee's boxes: target blue, other people orange, with their names (onizleme.py uses it too)."""
    for prefix, box in boxes:
        colour = TARGET_BGR if prefix == "hedef" else OTHER_BOX_BGR
        corners = draw_box(img, box, colour, 2, scale)
        if corners is not None:
            name = "hedef (hakem)" if prefix == "hedef" else prefix
            labels.append(Label(dx + corners[0], corners[1] - 3, name, colour, 15, True, "lb", 2, WHITE))


@dataclass(frozen=True)
class ModelView:
    """The model result PX4 had at a moment."""

    t: float  # [s sim] capture of its frame
    boxes: list[tuple]  # (u0, v0, u1, v1, guven) in camera pixels, most confident first
    chosen: int | None  # index of the target's box
    state: str  # takip.Choice.state
    reason: str  # kilitsiz_neden
    misses: int
    age_s: float  # [s sim] the moment - capture


class ModelTimeline:
    """The model's results (algilama.csv + kutular.csv) by the time PX4 had them: when they were sent, else when they
    left the delay line (refused), else when they were ready (the referee's LOS went instead), else when the model
    finished."""

    WHEN = ("gonderim_sim", "serbest_sim", "hazir_sim", "bitis_sim")

    def __init__(self, rows: pd.DataFrame, boxes: Mapping[int, Sequence[tuple]]) -> None:
        when = pd.Series(np.nan, index=rows.index)
        for col in self.WHEN:
            if col in rows:
                when = when.fillna(pd.to_numeric(rows[col], errors="coerce"))
        ok = when.notna().to_numpy()
        order = np.argsort(when.to_numpy()[ok], kind="stable")
        self._rows = rows[ok].iloc[order].reset_index(drop=True)
        self._when = when.to_numpy()[ok][order]
        self._boxes = boxes

    def at(self, t: float) -> ModelView | None:
        i = int(np.searchsorted(self._when, t, side="right")) - 1
        if i < 0:
            return None
        r = self._rows.iloc[i]
        chosen = r.get("secilen_kutu", math.nan)
        misses = r.get("ardisik_kacirma", 0)
        reason = r.get("kilitsiz_neden", "")
        return ModelView(
            t=float(r["t"]),
            boxes=list(self._boxes.get(int(r["t_us"]), [])),
            chosen=None if pd.isna(chosen) else int(chosen),
            state=str(r.get("secim", "")),
            reason="" if pd.isna(reason) else str(reason),
            misses=0 if pd.isna(misses) else int(misses),
            age_s=t - float(r["t"]),
        )


STATE_TEXT = {
    "izleme": "hedef izleniyor",
    "ilk_kilit": "ilk kilit",
    "yeniden_kilit": "yeniden kilit",
    "eslesmedi": "bu karede hedef bulunamadı",
    "kilit_kaybi": "kilit kaybı",
    "kilitsiz": "kilit yok",
}


def draw_camera(img: np.ndarray, m: "Moment", labels: list[Label]) -> None:
    """Camera panel overlays (img: the 1280x720 frame, BGR, drawn in place)."""
    draw_referee(img, m.referee_boxes, labels, LEFT[0] / CAMERA_WIDTH)
    model = m.model
    if model is not None:
        for i, b in enumerate(model.boxes):
            chosen = i == model.chosen
            corners = draw_box(img, b, MODEL_BGR, 4 if chosen else 1)
            if chosen and corners is not None:
                labels.append(Label(corners[2] + 4, corners[3], f"{b[4]:.2f}", MODEL_BGR, 18, True, "lb", 2, WHITE))
    shade(img, 0, 0, 760, 64 if not m.repeated else 86, BLACK, 0.45)
    delay = f"uçtan uca {m.delay_ms:.0f} ms" if math.isfinite(m.delay_ms) else "uçtan uca –"
    labels.append(Label(14, 8, f"t = {m.t:.1f} s   ·   {m.mode or '–'}   ·   {delay}", WHITE, 21, True))
    if model is None:
        line = "model: sonuç yok" if m.has_model else "model yok (--modelsiz)"
    else:
        state = STATE_TEXT.get(model.state, model.state)
        if model.state == "eslesmedi":
            state += f" ({model.misses}. kare)"
        elif model.state == "kilitsiz" and model.reason:
            state += f" ({model.reason})"
        line = f"PX4'teki son model sonucu: {1000 * model.age_s:.0f} ms önceki kare, {len(model.boxes)} kutu, {state}"
    labels.append(Label(14, 38, line, WHITE, 16))
    if m.repeated:
        labels.append(Label(14, 60, "bu an için kamera karesi yok: önceki kare gösteriliyor", (120, 200, 255), 15))
    legend = (
        ("mavi: hakem, hedef", (255, 190, 120)),
        ("turuncu: hakem, diğer insanlar", (80, 160, 255)),
        ("kırmızı: PX4'teki model sonucu (kalın: seçilen)", (110, 110, 255)),
    )
    width = max(round(text_width(text, 15, True)) for text, _ in legend)
    shade(img, LEFT[0] - width - 26, 0, LEFT[0], 72, BLACK, 0.45)
    for k, (text, colour) in enumerate(legend):
        labels.append(Label(LEFT[0] - 12, 9 + 21 * k, text, colour, 15, True, "ra"))
    if m.no_target:
        labels.append(Label(LEFT[0] / 2, 120, "HEDEF YOK", WARNING_BGR, 44, True, "mm", 3, WHITE))


def placeholder(text: str) -> np.ndarray:
    img = np.full((LEFT[1], LEFT[0], 3), 70, np.uint8)
    return render_labels(img, [Label(LEFT[0] / 2, LEFT[1] / 2, text, (200, 200, 200), 28, True, "mm")]).copy()


# --- top view -------------------------------------------------------------------------------------------------------


def optical_to_world(q_wxyz: Sequence[float], mount: np.ndarray) -> np.ndarray:
    """Rotation optical -> Gazebo world (ENU) of the drone camera: the model's orientation (FLU -> ENU) after the
    mount (C_cb: optical -> body FRD)."""
    return kamera.quat_to_dcm(*q_wxyz) @ kamera.FLU_TO_FRD @ np.asarray(mount, dtype=float)


@functools.cache
def _edge_rays(camera: kamera.Camera, steps: int = FOOTPRINT_STEPS) -> np.ndarray:
    """Unit optical rays along the image border (pixel edges), clockwise from the top left."""
    w, h = camera.width, camera.height
    us, vs = np.linspace(0, w, steps + 1), np.linspace(0, h, steps + 1)
    border = (
        [(u, 0.0) for u in us[:-1]]
        + [(float(w), v) for v in vs[:-1]]
        + [(u, float(h)) for u in us[::-1][:-1]]
        + [(0.0, v) for v in vs[::-1][:-1]]
    )
    return np.array([camera.pixel_to_los(u, v) for u, v in border])


def ground_footprint(camera: kamera.Camera, cam_pos: Sequence[float], r_wo: np.ndarray) -> np.ndarray:
    """(n, 2) world x, y [m] where the image border meets the ground (z = 0); rays that miss it, or meet it farther
    than FOOTPRINT_MAX_M, end at that horizontal distance."""
    p = np.asarray(cam_pos, dtype=float)
    rays = _edge_rays(camera) @ np.asarray(r_wo).T
    out = []
    for r in rays:
        horizontal = math.hypot(r[0], r[1])
        if r[2] < -1e-9:
            s = -p[2] / r[2]
            if s * horizontal <= FOOTPRINT_MAX_M:
                out.append((p[0] + s * r[0], p[1] + s * r[1]))
                continue
        if horizontal > 1e-9:
            out.append((p[0] + FOOTPRINT_MAX_M * r[0] / horizontal, p[1] + FOOTPRINT_MAX_M * r[1] / horizontal))
    return np.array(out).reshape(-1, 2)


@dataclass(frozen=True)
class TopView:
    """World x east, y north [m] -> panel pixels, north up."""

    centre: tuple[float, float]
    px_per_m: float
    centre_px: tuple[int, int] = (RIGHT[0] // 2, (LEGEND_H + RIGHT[1] - STATUS_H) // 2)

    def px(self, x: float, y: float) -> tuple[int, int]:
        return (
            round(self.centre_px[0] + (x - self.centre[0]) * self.px_per_m),
            round(self.centre_px[1] - (y - self.centre[1]) * self.px_per_m),
        )

    def fixed(self, x: float, y: float) -> tuple[int, int]:
        """Same point in cv2 fixed point (SUB bits)."""
        u = self.centre_px[0] + (x - self.centre[0]) * self.px_per_m
        v = self.centre_px[1] - (y - self.centre[1]) * self.px_per_m
        return round(u * (1 << SUB)), round(v * (1 << SUB))

    def r(self, metres: float) -> int:
        return max(1, round(metres * self.px_per_m * (1 << SUB)))


def scale_bar_m(px_per_m: float) -> float:
    """The longest of 1, 2, 5, 10, 20 m that stays at most 160 px long."""
    fitting = [m for m in (1.0, 2.0, 5.0, 10.0, 20.0) if m * px_per_m <= 160]
    return fitting[-1] if fitting else 1.0


def _dashed_circle(img: np.ndarray, c: tuple[int, int], r: int, colour: tuple, width: int) -> None:
    length = 2 * math.pi * r / (1 << SUB)
    n = max(8, int(length / 12))
    step = 360.0 / n
    for i in range(n):
        a = i * step
        cv2.ellipse(img, c, (r, r), 0, a, a + 0.55 * step, colour, width, cv2.LINE_AA, SUB)


def _dashed_line(img: np.ndarray, a: tuple[int, int], b: tuple[int, int], colour: tuple, width: int) -> None:
    length = math.hypot(b[0] - a[0], b[1] - a[1]) / (1 << SUB)
    n = max(1, int(length / 9))
    for i in range(0, n, 2):
        p = (round(a[0] + (b[0] - a[0]) * i / n), round(a[1] + (b[1] - a[1]) * i / n))
        q = (round(a[0] + (b[0] - a[0]) * (i + 1) / n), round(a[1] + (b[1] - a[1]) * (i + 1) / n))
        cv2.line(img, p, q, colour, width, cv2.LINE_AA, SUB)


def _blend(img: np.ndarray, overlay: np.ndarray, alpha: float) -> None:
    cv2.addWeighted(overlay, alpha, img, 1.0 - alpha, 0.0, dst=img)


def _star(c: tuple[int, int], r: int) -> np.ndarray:
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((round(c[0] + rr * math.cos(a)), round(c[1] + rr * math.sin(a))))
    return np.array(pts, np.int32)


def _triangle(c: tuple[int, int], heading_enu: float, size: float) -> np.ndarray:
    """Drone symbol: tip along the nose (ENU heading [rad], 0 = east, counter-clockwise; panel v points down)."""
    fx, fy = math.cos(heading_enu), -math.sin(heading_enu)
    sx, sy = -fy, fx
    s = size * (1 << SUB)
    tip = (c[0] + fx * s, c[1] + fy * s)
    left = (c[0] - 0.6 * fx * s + 0.62 * sx * s, c[1] - 0.6 * fy * s + 0.62 * sy * s)
    right = (c[0] - 0.6 * fx * s - 0.62 * sx * s, c[1] - 0.6 * fy * s - 0.62 * sy * s)
    return np.array([tip, left, right], np.float64).round().astype(np.int32)


@dataclass(frozen=True)
class Px4View:
    """What PX4's Follow Target had at a moment (ULog, olcum.Px4Follow; NED angles, 0 = north)."""

    estimate: tuple[float, float] | None  # [m] world x, y of follow_target_estimator (lat_est, lon_est)
    speed: float  # [m/s] |vel_est| horizontal
    stale: bool
    course: float  # [rad] tracked_target_course
    orbit: float  # [rad] orbit_angle_setpoint
    follow_angle: float  # [rad]
    filtered: tuple[float, float] | None = None  # [m] F: the task's filtered target the drone is placed around
    setpoint: tuple[float, float] | None = None  # [m] P: trajectory_setpoint, where PX4 sends the drone now
    aim: tuple[float, float] | None = None  # [m] desired_position_raw: FLW_TGT_DST behind the assumed course


def px4_marks(view: Px4View, distance: float) -> dict:
    """World x, y of the PX4 marks of the top view: base (F, else E: the course arrow starts there), ring (where PX4
    sends the drone now: its position setpoint, else base + FLW_TGT_DST along the orbit angle), cross (its final aim:
    desired_position_raw, else base + FLW_TGT_DST along course + follow angle). The task places the drone around F,
    not E; at a corner the two are metres apart (task group 9), so E + FLW_TGT_DST (task group 8) was off as much."""
    base = view.filtered or view.estimate
    out = {"base": base, "estimate": view.estimate, "filtered": view.filtered, "ring": None, "cross": None}
    if base is None:
        return out
    aim = view.course + view.follow_angle
    out["ring"] = view.setpoint or (
        base[0] + distance * math.sin(view.orbit),
        base[1] + distance * math.cos(view.orbit),
    )
    out["cross"] = view.aim or (base[0] + distance * math.sin(aim), base[1] + distance * math.cos(aim))
    return out


@dataclass(frozen=True)
class Situation:
    """What the status line talks about at a moment."""

    t: float
    start_s: float  # the person starts walking
    following: bool  # the tracking source follows (not "yok")
    speed: float  # [m/s] the person's true speed
    distance: float  # [m] drone - person, horizontal
    near_limit: float = math.nan  # [m] the camera's near ground limit
    in_view: bool = True  # the person's centre is in the image
    behind_error: float = math.nan  # [deg]
    lock: str = ""  # the model result's selection state ("" without a model)
    misses: int = 0
    no_target: bool = False  # the last TEZ_LOS said "no target"
    px4_speed: float = math.nan  # [m/s] PX4's speed estimate of the person
    px4_course_deg: float = math.nan  # [deg] PX4's assumed course
    px4_stale: bool = False
    near_pass: str = ""  # cause of the < 6 m pass this moment is in (ozet.json "yakin_gecis"), "" if none
    wrong_person: int | None = None  # insan<i> the chosen box PX4 had is on (olcum.wrong_person), None if not
    wrong_same_clothes: bool = False  # that person is dressed like the target


def status(s: Situation) -> tuple[str, str, str]:
    """(first line, second line, level: normal | uyari | alarm) of the status line."""
    if s.t < s.start_s and s.speed < STANDING_SPEED:
        phase = f"Takip başı: hedef duruyor, {s.start_s:.0f} s'de yürümeye başlayacak"
    elif s.speed < STANDING_SPEED:
        phase = "Hedef duruyor"
    elif s.speed > 2.0:
        phase = f"Hedef koşuyor ({s.speed:.1f} m/s)"
    else:
        phase = f"Hedef yürüyor ({s.speed:.1f} m/s)"
    line1 = f"{phase} · dron–hedef {s.distance:.1f} m"
    if s.following and math.isfinite(s.behind_error):
        line1 += f" · arkada kalma hatası {s.behind_error:.0f}°"
    alarms = []
    if s.wrong_person is not None:
        same = " (hedefle aynı kıyafetli)" if s.wrong_same_clothes else ""
        alarms.append(f"YANLIŞ KİŞİ{same}: PX4'e giden kutu insan{s.wrong_person} üstünde")
    if s.distance < olcum.NEAR_DISTANCE_M:
        alarms.append(f"dron hedefe {olcum.NEAR_DISTANCE_M:g} m'den yakın ({s.distance:.1f} m)")
    elif math.isfinite(s.near_limit) and s.distance < s.near_limit:
        alarms.append(f"dron kameranın yakın görüş sınırı ({s.near_limit:.1f} m) içinde: ayaklar kadrajın altında")
    if not s.in_view:
        alarms.append("hedef kadraj dışında")
    if s.lock == "kilit_kaybi":
        alarms.append("kilit kaybı: model hedefi 10 karedir bulamadı")
    elif s.lock == "kilitsiz":
        alarms.append("kilit yok (hakemle yeniden kilit bekleniyor)")
    if s.no_target:
        alarms.append("PX4'e 'hedef yok' gidiyor")
    if s.px4_stale:
        alarms.append("PX4 kestirimi bayat (3 s'dir FOLLOW_TARGET yok)")
    near_pass = (
        f"{olcum.CLOSE_PASS_M:g} m'den yakın geçiş: {rapor.NEAR_PASS_TEXT.get(s.near_pass, s.near_pass)}"
        if s.near_pass
        else ""
    )
    if alarms:
        return line1, " · ".join((alarms[:1] + [near_pass] + alarms[1:2]) if near_pass else alarms[:2]), "alarm"
    warnings = [near_pass] if near_pass else []
    if s.following and math.isfinite(s.behind_error) and s.behind_error > olcum.OVERSHOOT_DEG:
        warnings.append("dron hedefin yanında/önünde (köşede aşma)")
    if s.lock == "eslesmedi":
        warnings.append(f"model hedefi bu karede bulamadı ({s.misses}. kare)")
    px4 = ""
    if math.isfinite(s.px4_speed):
        px4 = f"PX4: hedefin hızı {s.px4_speed:.1f} m/s"
        if s.px4_speed >= PX4_COURSE_SPEED:
            px4 += " (≥ 1 m/s: rota güncellenir)"
        if math.isfinite(s.px4_course_deg):
            north = " (başlangıç: kuzey varsayımı)" if s.px4_course_deg == 0.0 else ""
            px4 += f", varsaydığı rota {s.px4_course_deg:.0f}°{north}"
    if warnings:
        return line1, " · ".join(warnings + ([px4] if px4 else [])), "uyari"
    return line1, px4, "normal"


def draw_map(m: "Moment", view: TopView, run: "Run", labels: list[Label]) -> np.ndarray:
    img = np.full((RIGHT[1], RIGHT[0], 3), SURFACE_BGR, np.uint8)
    step = 5.0 if view.px_per_m >= 12 else 10.0
    x0 = view.centre[0] - RIGHT[0] / 2 / view.px_per_m
    y0 = view.centre[1] - RIGHT[1] / 2 / view.px_per_m
    for gx in np.arange(math.floor(x0 / step) * step, x0 + RIGHT[0] / view.px_per_m + step, step):
        u = view.px(gx, 0.0)[0]
        cv2.line(img, (u, 0), (u, RIGHT[1]), GRID_BGR, 1)
    for gy in np.arange(math.floor(y0 / step) * step, y0 + RIGHT[1] / view.px_per_m + step, step):
        v = view.px(0.0, gy)[1]
        cv2.line(img, (0, v), (RIGHT[0], v), GRID_BGR, 1)
    if run.trees:
        overlay = img.copy()
        for x, y, r in run.trees:
            cv2.circle(overlay, view.fixed(x, y), view.r(r), TREE_BGR, -1, cv2.LINE_AA, SUB)
        _blend(img, overlay, 0.25)
        for x, y, _ in run.trees:
            cv2.circle(img, view.fixed(x, y), 2 << SUB, TREE_BGR, -1, cv2.LINE_AA, SUB)
    if run.path is not None:  # the person's whole planned path, faint
        pts = [view.fixed(x, y) for x, y in run.path]
        for a, b in zip(pts[:-1:2], pts[1::2], strict=False):
            cv2.line(img, a, b, (225, 205, 180), 1, cv2.LINE_AA, SUB)
    if m.footprint is not None and len(m.footprint) >= 3:
        poly = np.array([view.fixed(x, y) for x, y in m.footprint], np.int32)
        overlay = img.copy()
        cv2.fillPoly(overlay, [poly], TARGET_BGR, cv2.LINE_AA, SUB)
        _blend(img, overlay, 0.10)
        cv2.polylines(img, [poly], True, (225, 180, 140), 1, cv2.LINE_AA, SUB)
    tx, ty = m.target
    tc = view.fixed(tx, ty)
    _dashed_circle(img, tc, view.r(olcum.NEAR_DISTANCE_M), WARNING_BGR, 2)
    if math.isfinite(m.near_limit):
        _dashed_circle(img, tc, view.r(m.near_limit), TEXT2_BGR, 1)
    for trail, colour, width in ((m.target_trail, TARGET_BGR, 2), (m.drone_trail, DRONE_BGR, 2)):
        if len(trail) >= 2:
            pts = np.array([view.fixed(x, y) for x, y in trail], np.int32)
            cv2.polylines(img, [pts], False, colour, width, cv2.LINE_AA, SUB)
    for trail in m.other_trails:
        if len(trail) >= 2:
            pts = np.array([view.fixed(x, y) for x, y in trail], np.int32)
            cv2.polylines(img, [pts], False, OTHERS_BGR, 1, cv2.LINE_AA, SUB)
    for x, y in m.others:
        cv2.circle(img, view.fixed(x, y), 6 << SUB, OTHERS_BGR, -1, cv2.LINE_AA, SUB)
    for x, y, age in m.follow_points:
        newest = age < 0.15
        light = tuple(int(c + (255 - c) * min(0.6, age / FOLLOW_POINTS_S)) for c in PX4_BGR)
        cv2.circle(img, view.fixed(x, y), (4 if newest else 3) << SUB, light, -1, cv2.LINE_AA, SUB)
    px4 = m.px4
    marks = px4_marks(px4, run.follow_distance or 0.0) if px4 is not None else None
    if marks is not None and marks["base"] is not None:
        bx, by = marks["base"]
        bc = view.fixed(bx, by)
        if (run.follow_distance or 0.0) > 0:  # where PX4 sends the drone now and its final aim
            cv2.circle(img, view.fixed(*marks["ring"]), 8 << SUB, PX4_BGR, 2, cv2.LINE_AA, SUB)
            gx, gy = view.fixed(*marks["cross"])
            d = 6 << SUB
            cv2.line(img, (gx - d, gy - d), (gx + d, gy + d), PX4_BGR, 2, cv2.LINE_AA, SUB)
            cv2.line(img, (gx - d, gy + d), (gx + d, gy - d), PX4_BGR, 2, cv2.LINE_AA, SUB)
        head = view.fixed(
            bx + PX4_COURSE_ARROW_M * math.sin(px4.course), by + PX4_COURSE_ARROW_M * math.cos(px4.course)
        )
        cv2.arrowedLine(img, bc, head, PX4_BGR, 3, cv2.LINE_AA, SUB, 0.3)
        s = 6 << SUB
        if marks["filtered"] is not None:  # F, outlined, and how far it is from the estimate
            if marks["estimate"] is not None:
                _dashed_line(img, view.fixed(*marks["estimate"]), bc, PX4_BGR, 1)
            cv2.rectangle(img, (bc[0] - s, bc[1] - s), (bc[0] + s, bc[1] + s), WHITE, -1, cv2.LINE_AA, SUB)
            cv2.rectangle(img, (bc[0] - s, bc[1] - s), (bc[0] + s, bc[1] + s), PX4_BGR, 2, cv2.LINE_AA, SUB)
        if marks["estimate"] is not None:
            ec = view.fixed(*marks["estimate"])
            cv2.rectangle(img, (ec[0] - s, ec[1] - s), (ec[0] + s, ec[1] + s), PX4_BGR, -1, cv2.LINE_AA, SUB)
    if m.behind is not None:
        star = _star(view.fixed(*m.behind), 11 << SUB)
        cv2.fillPoly(img, [star], BEHIND_BGR, cv2.LINE_AA, SUB)
    dc = view.fixed(*m.drone)
    _dashed_line(img, dc, tc, TEXT2_BGR, 1)
    if m.distance >= 4.0:
        mid = view.px((m.drone[0] + tx) / 2, (m.drone[1] + ty) / 2)
        labels.append(Label(RIGHT_X + mid[0], mid[1] - 6, f"{m.distance:.1f} m", TEXT_BGR, 15, True, "mb", 3, WHITE))
    else:  # too close for the middle of the line: next to the drone
        du, dv = view.px(*m.drone)
        labels.append(Label(RIGHT_X + du + 16, dv, f"{m.distance:.1f} m", WARNING_BGR, 15, True, "lm", 3, WHITE))
    cv2.circle(img, tc, 8 << SUB, WHITE, -1, cv2.LINE_AA, SUB)
    cv2.circle(img, tc, 7 << SUB, TARGET_BGR, -1, cv2.LINE_AA, SUB)
    if m.speed >= STANDING_SPEED:
        length = max(1.0, m.speed * TARGET_ARROW_S)
        head = view.fixed(tx + length * math.cos(m.target_yaw), ty + length * math.sin(m.target_yaw))
        cv2.arrowedLine(img, tc, head, TARGET_BGR, 3, cv2.LINE_AA, SUB, 0.3)
    tri = _triangle(dc, m.drone_heading, 13.0)
    cv2.fillPoly(img, [tri], DRONE_BGR, cv2.LINE_AA, SUB)
    cv2.polylines(img, [tri], True, WHITE, 1, cv2.LINE_AA, SUB)
    _map_furniture(img, view, run, m, labels)
    return img


RIGHT_X = LEFT[0]  # x of the top view in the whole frame (labels are drawn on the whole frame)


def _legend_items(run: "Run") -> list[list[tuple[str, tuple, str]]]:
    dst = f"{run.follow_distance:g}" if run.follow_distance else "8"
    rows = [[("dot", TARGET_BGR, "hedef"), ("tri", DRONE_BGR, "dron (burnu)")]]
    if run.others:
        rows[0].append(("dot", OTHERS_BGR, "diğer insanlar"))
    if run.source != "yok":
        rows[0].append(("star", BEHIND_BGR, f"olması gereken yer ({dst} m arkası)"))
    rows.append(
        [
            ("ring", WARNING_BGR, "3 m"),
            ("ring", TEXT2_BGR, "kameranın yakın sınırı"),
            ("area", TARGET_BGR, "kameranın gördüğü yer"),
            ("line", DRONE_BGR, f"son {TRAIL_S:.0f} s"),
        ]
    )
    if run.source == "follow_me":  # the PX4 row is full: FOLLOW_TARGET goes to the end of the row above
        rows[-1].append(("dots", PX4_BGR, "FOLLOW_TARGET"))
        rows.append(
            [
                ("square", PX4_BGR, "PX4 kestirimi"),
                ("open_square", PX4_BGR, "süzülmüş hedefi"),
                ("arrow", PX4_BGR, "varsaydığı rota"),
                ("circle", PX4_BGR, "gönderdiği yer"),
                ("cross", PX4_BGR, "hedeflediği"),
            ]
        )
    return rows


def _legend_symbol(img: np.ndarray, kind: str, colour: tuple, u: int, v: int) -> None:
    c = (u << SUB, v << SUB)
    if kind == "dot":
        cv2.circle(img, c, 5 << SUB, colour, -1, cv2.LINE_AA, SUB)
    elif kind == "tri":
        cv2.fillPoly(img, [_triangle(c, 0.0, 8.0)], colour, cv2.LINE_AA, SUB)
    elif kind == "star":
        cv2.fillPoly(img, [_star(c, 7 << SUB)], colour, cv2.LINE_AA, SUB)
    elif kind == "ring":
        _dashed_circle(img, c, 6 << SUB, colour, 2)
    elif kind == "area":
        shade(img, u - 7, v - 5, u + 7, v + 5, colour, 0.25)
    elif kind == "line":
        cv2.line(img, (c[0] - (8 << SUB), c[1]), (c[0] + (8 << SUB), c[1]), colour, 2, cv2.LINE_AA, SUB)
    elif kind == "dots":
        for k in (-6, 0, 6):
            cv2.circle(img, (c[0] + (k << SUB), c[1]), 2 << SUB, colour, -1, cv2.LINE_AA, SUB)
    elif kind == "square":
        cv2.rectangle(img, (u - 5, v - 5), (u + 5, v + 5), colour, -1)
    elif kind == "open_square":
        cv2.rectangle(img, (u - 5, v - 5), (u + 5, v + 5), colour, 2)
    elif kind == "arrow":
        cv2.arrowedLine(img, (c[0] - (8 << SUB), c[1]), (c[0] + (8 << SUB), c[1]), colour, 2, cv2.LINE_AA, SUB, 0.4)
    elif kind == "circle":
        cv2.circle(img, c, 6 << SUB, colour, 2, cv2.LINE_AA, SUB)
    elif kind == "cross":
        d = 5 << SUB
        cv2.line(img, (c[0] - d, c[1] - d), (c[0] + d, c[1] + d), colour, 2, cv2.LINE_AA, SUB)
        cv2.line(img, (c[0] - d, c[1] + d), (c[0] + d, c[1] - d), colour, 2, cv2.LINE_AA, SUB)


def _map_furniture(img: np.ndarray, view: TopView, run: "Run", m: "Moment", labels: list[Label]) -> None:
    """Legend band, scale bar, north arrow and the status band."""
    shade(img, 0, 0, RIGHT[0], LEGEND_H, SURFACE_BGR, 0.88)
    cv2.line(img, (0, LEGEND_H), (RIGHT[0], LEGEND_H), GRID_BGR, 1)
    rows = _legend_items(run)
    row_h = LEGEND_H / max(3, len(rows))
    for k, items in enumerate(rows):
        v = round(row_h * (k + 0.5))
        u = 10
        for kind, colour, text in items:
            _legend_symbol(img, kind, colour, u + 8, v)
            labels.append(Label(RIGHT_X + u + 20, v, text, TEXT_BGR, 13, False, "lm"))
            u += 20 + round(text_width(text, 13)) + 14
    bar = scale_bar_m(view.px_per_m)
    u0, v0 = 16, RIGHT[1] - STATUS_H - 18
    u1 = u0 + round(bar * view.px_per_m)
    cv2.line(img, (u0, v0), (u1, v0), TEXT_BGR, 3)
    for u in (u0, u1):
        cv2.line(img, (u, v0 - 5), (u, v0 + 5), TEXT_BGR, 2)
    labels.append(Label(RIGHT_X + (u0 + u1) / 2, v0 - 7, f"{bar:g} m", TEXT_BGR, 14, True, "mb", 3, WHITE))
    nu, nv = RIGHT[0] - 24, RIGHT[1] - STATUS_H - 44
    cv2.arrowedLine(img, (nu, nv + 22), (nu, nv - 4), TEXT_BGR, 2, cv2.LINE_AA, 0, 0.35)
    labels.append(Label(RIGHT_X + nu, nv + 26, "K", TEXT_BGR, 14, True, "mt", 3, WHITE))
    line1, line2, level = status(m.situation)
    y0 = RIGHT[1] - STATUS_H
    background = {"normal": (238, 238, 236), "uyari": (205, 238, 255), "alarm": (215, 215, 250)}[level]
    shade(img, 0, y0, RIGHT[0], RIGHT[1], background, 1.0)
    second = {"normal": TEXT2_BGR, "uyari": AMBER_BGR, "alarm": WARNING_BGR}[level]
    line1, size1 = fit_text(line1, RIGHT[0] - 20, True)
    line2, size2 = fit_text(line2, RIGHT[0] - 20, level != "normal")
    labels.append(Label(RIGHT_X + 10, y0 + 17, line1, TEXT_BGR, size1, True, "lm"))
    if line2:
        labels.append(Label(RIGHT_X + 10, y0 + 41, line2, second, size2, level != "normal", "lm"))


# --- the run's files ------------------------------------------------------------------------------------------------


class Px4Timeline:
    """PX4's Follow Target internals of the run's ULog files (olcum.Px4Follow), as last logged at each moment."""

    def __init__(self, follow: olcum.Px4Follow | None) -> None:
        self.follow = follow
        self.ok = follow is not None

    def at(self, t: float) -> Px4View | None:
        if self.follow is None or t < self.follow.est_t[0] or t < self.follow.st_t[0]:
            return None
        now = self.follow.at(t, hold=True)

        def point(xy: np.ndarray) -> tuple[float, float] | None:
            return (float(xy[0]), float(xy[1])) if np.isfinite(xy).all() else None

        return Px4View(
            estimate=point(now["E"]),
            speed=now["speed"],
            stale=now["stale"],
            course=now["course"],
            orbit=now["orbit"],
            follow_angle=now["follow_angle"],
            filtered=point(now["F"]),
            setpoint=point(now["P"]),
            aim=point(now["aim"]),
        )


def _read_csv(path: Path) -> pd.DataFrame | None:
    if not path.is_file() or path.stat().st_size == 0:
        return None
    try:
        return pd.read_csv(path)
    except (pd.errors.EmptyDataError, ValueError):
        return None


def _boxes(path: Path) -> dict[int, list[tuple]]:
    df = _read_csv(path)
    if df is None or df.empty:
        return {}
    df = df.sort_values(["t_us", "kutu"])
    return {
        int(k): [tuple(float(v) for v in r) for r in g[["u0", "v0", "u1", "v1", "guven"]].to_numpy()]
        for k, g in df.groupby("t_us")
    }


def _sent(df: pd.DataFrame | None, columns: Sequence[str]) -> dict[str, np.ndarray] | None:
    """Rows that went out (sonuc gonderildi), by send time; the columns as float arrays."""
    if df is None or df.empty or "sonuc" not in df:
        return None
    sent = df[df["sonuc"] == "gonderildi"].sort_values("gonderim_sim")
    if sent.empty:
        return None
    return {c: pd.to_numeric(sent[c], errors="coerce").to_numpy(dtype=float) for c in ("gonderim_sim", *columns)}


@dataclass
class Run:
    folder: Path
    scenario: hedef.Scenario
    ref: dict[str, np.ndarray]  # dogru_cevap.csv columns, sorted by t
    ref_rows: pd.DataFrame
    ref_keys: dict[int, int]  # round(t * 1e6) -> row
    prefixes: list[str]  # people with referee boxes: hedef, insan1, ...
    others: int
    camera: kamera.Camera
    mount: np.ndarray  # C_cb
    source: str
    modes: list[tuple[float, str]]  # (start [s], name), in time order
    follow_distance: float | None
    model: ModelTimeline | None
    los: dict[str, np.ndarray] | None
    follow: dict[str, np.ndarray] | None
    px4: Px4Timeline | None
    trees: list[tuple[float, float, float]] = field(default_factory=list)
    tilt_deg: float = kamera.NOMINAL_TILT_DEG  # [deg] the run's camera tilt (ozet.json "ayarlar" "kamera")
    path: list[tuple[float, float]] | None = None
    has_model: bool = False
    near_passes: list[dict] = field(default_factory=list)  # ozet.json "yakin_gecis" "olaylar"
    same_clothes: frozenset[int] = frozenset()  # the other people dressed like the target (1-based)


def load(folder: Path) -> Run:
    """Everything the video needs from a run folder (FileNotFoundError without ozet.json or dogru_cevap.csv)."""
    summary = json.loads((folder / "ozet.json").read_text(encoding="utf-8"))
    sc = hedef.load(str(folder / "senaryo.yaml"))
    ref_rows = pd.read_csv(folder / "dogru_cevap.csv").sort_values("t").reset_index(drop=True)
    ref = {c: ref_rows[c].to_numpy() for c in ref_rows.columns}
    keys = {round(float(t) * 1e6): i for i, t in enumerate(ref["t"])}
    prefixes = ["hedef"] + [f"insan{i}" for i in range(1, len(sc.others) + 1) if f"insan{i}_kutu_u0" in ref]
    camera = rapor.camera_of(summary.get("kamera")) or kamera.Camera(CAMERA_WIDTH, 1296, 1773.9, 1773.9, 1152.0, 648.0)
    mount_info = summary.get("kamera_montaji") or {}
    mount = np.asarray(mount_info.get("dcm_optik_govde") or konumlama.NOMINAL_MOUNT, dtype=float)
    settings = summary.get("ayarlar") or {}
    source = (settings.get("takip") or {}).get("kaynak", sc.tracking_source)
    tilt = float((settings.get("kamera") or {}).get("egim_deg", sc.camera.tilt_deg))  # --kamera-egim is in ayarlar
    mode = summary.get("mod") or {}
    if mode.get("ulog"):
        modes = [(float(s["baslangic_s"]), str(s["ad"])) for s in mode["ulog"]]
    else:
        modes = [(float(t), str(n)) for t, n in mode.get("mavlink") or []]
    distance = None
    if source != "yok":
        entry = (settings.get("px4_parametreleri") or {}).get("FLW_TGT_DST") or {}
        value = entry.get("px4") if entry.get("px4") is not None else entry.get("deger")
        distance = float(value) if value is not None else None
    detections = _read_csv(folder / "algilama.csv")
    model = ModelTimeline(detections, _boxes(folder / "kutular.csv")) if detections is not None else None
    world = konumlama.world_geo(hedef.SIM_DIR / "worlds" / f"{sc.world}.sdf")
    ulogs = [p for p in [*sorted(folder.glob("ucus_once*.ulg")), folder / "ucus.ulg"] if p.is_file()]
    px4 = None
    if source == "follow_me" and ulogs:
        topics = olcum.Topics.read(ulogs, PX4_TOPICS)
        px4 = Px4Timeline(olcum.Px4Follow.from_topics(topics, world, distance))
        px4 = px4 if px4.ok else None
    spec = dunya.load(sc.world)
    trees = [
        (t.x, t.y, dunya.TREE_KINDS[t.kind].crown_radii[0] * t.scale) for t in (spec.trees if spec is not None else [])
    ]
    path = list(zip(sc.track.x[::10].tolist(), sc.track.y[::10].tolist(), strict=True)) if sc.track else None
    return Run(
        folder=folder,
        scenario=sc,
        ref=ref,
        ref_rows=ref_rows,
        ref_keys=keys,
        prefixes=prefixes,
        others=len(sc.others),
        camera=camera,
        mount=mount,
        source=source,
        modes=modes,
        follow_distance=distance,
        model=model,
        los=_sent(_read_csv(folder / "tez_los.csv"), ("hedef", "uctan_uca_ms")),
        follow=_sent(_read_csv(folder / "follow_target.csv"), ("x", "y")),
        px4=px4,
        trees=trees,
        tilt_deg=tilt,
        path=path,
        has_model=detections is not None,
        near_passes=list((summary.get("yakin_gecis") or {}).get("olaylar") or []),
        same_clothes=frozenset(i for i, o in enumerate(sc.others, start=1) if o.clothes == sc.clothes),
    )


# --- one moment -----------------------------------------------------------------------------------------------------


@dataclass
class Moment:
    t: float
    repeated: bool
    referee_boxes: list
    model: ModelView | None
    has_model: bool
    no_target: bool
    delay_ms: float
    mode: str
    drone: tuple[float, float]
    drone_heading: float  # [rad] ENU, 0 = east
    target: tuple[float, float]
    target_yaw: float  # [rad] ENU
    speed: float
    distance: float
    near_limit: float
    footprint: np.ndarray | None
    drone_trail: np.ndarray
    target_trail: np.ndarray
    others: list[tuple[float, float]]
    other_trails: list[np.ndarray]
    behind: tuple[float, float] | None
    follow_points: list[tuple[float, float, float]]
    px4: Px4View | None
    situation: Situation


def _latest(times: np.ndarray, t: float) -> int:
    return int(np.searchsorted(times, t, side="right")) - 1


def moment(run: Run, t: float, frame_t: float | None, repeated: bool) -> Moment:
    """Everything drawn for sim time t; frame_t: the time of the camera frame shown (its referee boxes)."""
    ref = run.ref
    i = max(0, _latest(ref["t"], t))
    row = run.ref_rows.iloc[i]
    box_row = run.ref_keys.get(round(frame_t * 1e6)) if frame_t is not None else None
    boxes = referee_boxes(run.ref_rows.iloc[box_row], run.prefixes) if box_row is not None else []
    drone = (float(ref["dron_x"][i]), float(ref["dron_y"][i]))
    target = (float(ref["hedef_x"][i]), float(ref["hedef_y"][i]))
    yaw = float(ref["hedef_yaw"][i])
    speed = float(ref["hedef_hiz"][i])
    distance = float(ref["yatay_mesafe"][i])
    since = (ref["t"] > t - TRAIL_S) & (ref["t"] <= t)
    trail = lambda xs, ys: np.stack([ref[xs][since], ref[ys][since]], axis=1).astype(float)  # noqa: E731
    others = [(float(row[f"insan{k}_x"]), float(row[f"insan{k}_y"])) for k in range(1, run.others + 1)]
    other_trails = [trail(f"insan{k}_x", f"insan{k}_y") for k in range(1, run.others + 1)]
    cam_z = float(row["kamera_z"])
    near = float(olcum.frame_limits(run.camera, np.array([cam_z]), run.tilt_deg)[0][0])
    footprint = None
    if all(f"dron_q{c}" in row for c in "wxyz"):
        q = [float(row[f"dron_q{c}"]) for c in "wxyz"]
        cam = (float(row["kamera_x"]), float(row["kamera_y"]), cam_z)
        footprint = ground_footprint(run.camera, cam, optical_to_world(q, run.mount))
    following = run.source != "yok"
    behind = None
    error = math.nan
    if following and speed >= olcum.MOVING_SPEED:
        orbit = math.degrees(math.atan2(drone[1] - target[1], drone[0] - target[0]))
        error = abs(float(olcum.wrap_deg(orbit - (math.degrees(yaw) + 180.0))))
        dst = run.follow_distance or 8.0
        behind = (target[0] - dst * math.cos(yaw), target[1] - dst * math.sin(yaw))
    model = run.model.at(t) if run.model is not None else None
    wrong = None
    if model is not None and model.chosen is not None and model.chosen < len(model.boxes):
        k = run.ref_keys.get(round(model.t * 1e6))  # the referee of the model result's own frame
        if k is not None:
            wrong = olcum.wrong_person(model.boxes[model.chosen][:4], run.ref_rows.iloc[k], run.others)
    no_target, delay = False, math.nan
    if run.los is not None:
        j = _latest(run.los["gonderim_sim"], t)
        if j >= 0:
            no_target = run.los["hedef"][j] == 0
            delay = float(run.los["uctan_uca_ms"][j])
    points = []
    if run.follow is not None:
        f = run.follow
        recent = (f["gonderim_sim"] > t - FOLLOW_POINTS_S) & (f["gonderim_sim"] <= t)
        points = [
            (float(x), float(y), t - float(s))
            for x, y, s in zip(f["x"][recent], f["y"][recent], f["gonderim_sim"][recent], strict=True)
        ]
    px4 = run.px4.at(t) if run.px4 is not None else None
    near_pass = next((e["sebep"] for e in run.near_passes if e["baslangic_s"] <= t <= e["bitis_s"]), "")
    mode = ""
    for start, name in run.modes:
        if start <= t:
            mode = name
    situation = Situation(
        t=t,
        start_s=run.scenario.start_time,
        following=following,
        speed=speed,
        distance=distance,
        near_limit=near,
        in_view=bool(row.get("kadrajda", True)),
        behind_error=error,
        lock=model.state if model is not None else "",
        misses=model.misses if model is not None else 0,
        no_target=no_target,
        px4_speed=px4.speed if px4 is not None else math.nan,
        px4_course_deg=math.degrees(px4.course) if px4 is not None else math.nan,
        px4_stale=px4.stale if px4 is not None else False,
        near_pass=near_pass,
        wrong_person=wrong,
        wrong_same_clothes=wrong is not None and wrong in run.same_clothes,
    )
    return Moment(
        t=t,
        repeated=repeated,
        referee_boxes=boxes,
        model=model,
        has_model=run.has_model,
        no_target=no_target,
        delay_ms=delay,
        mode=mode,
        drone=drone,
        drone_heading=math.radians(90.0 - float(ref["dron_yaw_deg"][i])),
        target=target,
        target_yaw=yaw,
        speed=speed,
        distance=distance,
        near_limit=near,
        footprint=footprint,
        drone_trail=trail("dron_x", "dron_y"),
        target_trail=trail("hedef_x", "hedef_y"),
        others=others,
        other_trails=other_trails,
        behind=behind,
        follow_points=points,
        px4=px4,
        situation=situation,
    )


# --- frames, view, video --------------------------------------------------------------------------------------------


def frames_by_slot(folder: Path) -> dict[int, tuple[float, Path]]:
    """The kept camera frames by their 1/FPS s slot: {round(t * FPS): (t, path)}."""
    out: dict[int, tuple[float, Path]] = {}
    for p in sorted(folder.glob("*.jpg")) if folder.is_dir() else []:
        t = goruntu_yayini.frame_time(p)
        k = round(t * FPS)
        if k not in out or abs(t - k / FPS) < abs(out[k][0] - k / FPS):
            out[k] = (t, p)
    return out


def timeline(
    t0: float, t1: float, frames: Mapping[int, tuple[float, Path]]
) -> list[tuple[int, tuple[float, Path] | None, bool]]:
    """[(slot, the frame shown, missing)] for every 1/FPS s from t0 to t1: a slot without its own frame shows the one
    before (None before the first)."""
    plan, last = [], None
    for k in range(math.ceil(t0 * FPS - 1e-9), math.floor(t1 * FPS + 1e-9) + 1):
        if k in frames:
            last = frames[k]
            plan.append((k, last, False))
        else:
            plan.append((k, last, True))
    return plan


def view_plan(run: Run, times: Sequence[float]) -> tuple[np.ndarray, float]:
    """(view centre per time, px per m): the scale fits the drone and the person all along (one scale per video, so
    the scale bar does not change); the centre follows their midpoint smoothly."""
    ref = run.ref
    d = np.asarray(ref["yatay_mesafe"], float)
    half = float(np.clip(np.nanpercentile(d, 98) / 2 + VIEW_MARGIN_M, VIEW_HALF_MIN_M, VIEW_HALF_MAX_M))
    mx = (np.asarray(ref["dron_x"], float) + np.asarray(ref["hedef_x"], float)) / 2
    my = (np.asarray(ref["dron_y"], float) + np.asarray(ref["hedef_y"], float)) / 2
    tt = np.asarray(ref["t"], float)
    cx, cy = np.interp(times, tt, mx), np.interp(times, tt, my)
    out = np.empty((len(times), 2))
    for k in range(len(times)):
        if k == 0:
            out[k] = (cx[0], cy[0])
            continue
        a = 1.0 - math.exp(-(times[k] - times[k - 1]) / VIEW_SMOOTH_S)
        out[k] = out[k - 1] + a * (np.array([cx[k], cy[k]]) - out[k - 1])
    return out, VIEW_HALF_PX / half


def ffmpeg_command(path: Path, size: tuple[int, int] = SIZE, fps: int = FPS) -> list[str]:
    """Raw BGR frames on stdin -> H.264 MP4 that VLC 3.0.20 plays (yuv420p, moov atom first)."""
    w, h = size
    return [
        "ffmpeg",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s",
        f"{w}x{h}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(path),
    ]


class Encoder:
    """ffmpeg through a pipe: write() one BGR frame of `size` at a time; leaving the block finishes the file
    (RuntimeError with ffmpeg's message if it failed)."""

    def __init__(self, path: Path, size: tuple[int, int] = SIZE, fps: int = FPS) -> None:
        if size[0] % 2 or size[1] % 2:
            raise ValueError(f"yuv420p için boyutlar çift olmalı: {size[0]}x{size[1]}")
        self.path, self.size, self.frames = path, size, 0
        self._log = tempfile.TemporaryFile()
        self._proc = subprocess.Popen(
            ffmpeg_command(path, size, fps), stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self._log
        )

    def write(self, frame: np.ndarray) -> None:
        if frame.shape != (self.size[1], self.size[0], 3) or frame.dtype != np.uint8:
            raise ValueError(f"kare {self.size[0]}x{self.size[1]} BGR uint8 olmalı: {frame.shape} {frame.dtype}")
        try:
            self._proc.stdin.write(memoryview(np.ascontiguousarray(frame)).cast("B"))
        except BrokenPipeError:
            raise RuntimeError(f"ffmpeg kapandı: {self._message()}") from None
        self.frames += 1

    def _message(self) -> str:
        self._log.seek(0)
        return self._log.read().decode(errors="replace").strip()[-500:]

    def close(self) -> None:
        self._proc.stdin.close()
        code = self._proc.wait(timeout=300)
        if code != 0:
            raise RuntimeError(f"ffmpeg çıkış kodu {code}: {self._message()}")

    def __enter__(self) -> "Encoder":
        return self

    def __exit__(self, kind: type | None, *_: object) -> None:
        if kind is None:
            self.close()
        else:
            self._proc.kill()
        self._log.close()


def make(folder: Path, recorder_books: dict | None = None, keep_frames: bool = True) -> dict:
    """kosu.mp4 of a run folder; returns ozet.json "video". keep_frames False: kareler/ is deleted afterwards (also
    when the video failed: the frames are 0.1-0.2 GB per run)."""
    started = time.monotonic()
    frames_dir = folder / goruntu_yayini.FRAMES_DIR
    try:
        run = load(folder)
        if len(run.ref["t"]) < 2:
            return {"hata": "hakem kaydı yok: video yapılmadı", "kayit": recorder_books}
        plan = timeline(float(run.ref["t"][0]), float(run.ref["t"][-1]), frames_by_slot(frames_dir))
        times = [entry[0] if entry is not None and not missing else k / FPS for k, entry, missing in plan]
        centres, px_per_m = view_plan(run, times)
        no_frame = placeholder("kamera karesi yok (--videosuz değilse goruntu_yayini kaydetmedi)")
        cache: tuple[Path | None, np.ndarray | None] = (None, None)
        with Encoder(folder / VIDEO_NAME) as enc:
            for (_k, entry, missing), t, centre in zip(plan, times, centres, strict=True):
                if entry is None:
                    left = no_frame.copy()
                else:
                    if cache[0] != entry[1]:
                        img = cv2.imread(str(entry[1]))
                        cache = (entry[1], img if img is not None and img.shape == no_frame.shape else None)
                    left = cache[1].copy() if cache[1] is not None else no_frame.copy()
                m = moment(run, t, entry[0] if entry is not None else None, missing and entry is not None)
                labels: list[Label] = []
                draw_camera(left, m, labels)
                right = draw_map(m, TopView((float(centre[0]), float(centre[1])), px_per_m), run, labels)
                enc.write(render_labels(compose(left, right), labels))
        shown = sum(1 for _, entry, missing in plan if entry is not None and not missing)
        return {
            "dosya": VIDEO_NAME,
            "boyut": list(SIZE),
            "fps": FPS,
            "kare_sayisi": len(plan),
            "sure_s": len(plan) / FPS,
            "baslangic_s": plan[0][0] / FPS,
            "bitis_s": plan[-1][0] / FPS,
            "kamera_karesi": shown,
            "eksik_kare": len(plan) - shown,
            "uretim_s": time.monotonic() - started,
            "kareler": "saklandı" if keep_frames else "silindi",
            "kayit": recorder_books,
        }
    finally:
        if not keep_frames and frames_dir.is_dir():
            shutil.rmtree(frames_dir, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("klasor", type=Path, help="bir koşunun klasörü (tez/sim/sonuclar/<klasör>)")
    ap.add_argument("--kareleri-sil", action="store_true", help="video yapıldıktan sonra kareler/ silinir")
    args = ap.parse_args()
    if not (args.klasor / "ozet.json").is_file():
        print(f"{args.klasor}: ozet.json yok (bir senaryo koşusunun klasörü değil)", file=sys.stderr)
        return 2
    info = make(args.klasor, keep_frames=not args.kareleri_sil)
    if "hata" in info:
        print(f"Video yapılmadı: {info['hata']}", file=sys.stderr)
        return 1
    print(
        f"{args.klasor / VIDEO_NAME}: {info['kare_sayisi']} kare ({info['sure_s']:.1f} s), kamera karesi "
        f"{info['kamera_karesi']}, eksik {info['eksik_kare']}, {info['uretim_s']:.0f} s'de"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
