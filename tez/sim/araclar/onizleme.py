#!/usr/bin/env python3
"""Look at a world (or a scenario) through a camera like the drone's, without PX4: photos or an MP4 video.

    P=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python
    $P tez/sim/araclar/onizleme.py --dunya cayir                         # photo from the hover point (0, 0, 10 m)
    $P tez/sim/araclar/onizleme.py --senaryo kivrimli_yuruyus --video 60:90
    ... --kamera 0,0,10,35,0      camera x, y, z [m], pitch down [deg], yaw [deg, 0 = east, 90 = north];
                                  default pitch: the drone's default mount (kamera.NOMINAL_TILT_DEG)
    ... --zaman 5,20,40           sim times of the photos [s]
    ... --tepe                    camera straight down from above the middle of the scene instead
    ... --etiket                  draw the referee's boxes (segmentation): target blue, other people orange

The camera has the drone camera's lens and resolution (Camera Module 3: 66 deg, 2304x1296) but does not move;
the drone itself stands on the ground at (0, 0). Output: tez/sim/sonuclar/<date>_onizleme_<name>/. The video is
H.264 MP4 (VLC) at half the camera's resolution, through the same ffmpeg pipe and box drawing as kosu.mp4 (video.py).
"""

import argparse
import datetime as dt
import math
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")  # protobuf 7.x in ~/.local
os.environ.setdefault("GZ_IP", "127.0.0.1")

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from gz.msgs10.image_pb2 import Image  # noqa: E402
from gz.transport13 import Node, SubscribeOptions  # noqa: E402
from PIL import Image as PilImage  # noqa: E402

import hedef  # noqa: E402
import kamera  # noqa: E402
import video  # noqa: E402
from kayit import IMAGE_TYPE, SEG_SCALE, label_channel, read_image, visible_parts  # noqa: E402
from simulasyon import REPO, SIM_DIR, running  # noqa: E402

TOPIC = "/onizleme/image"
SEG_TOPIC = "/onizleme_seg"
HFOV = 1.151917  # [rad] Camera Module 3 Standard, as models/x500_tez
SIZE = (2304, 1296)
VIDEO_SIZE = (SIZE[0] // 2, SIZE[1] // 2)  # [px] of the MP4
VIDEO_FPS = 10


def camera_sdf(x: float, y: float, z: float, pitch_deg: float, yaw_deg: float, rate: float, labels: bool) -> str:
    seg = (
        f"""
        <sensor name="segmentasyon" type="segmentation">
          <topic>{SEG_TOPIC}</topic>
          <always_on>1</always_on>
          <update_rate>{rate}</update_rate>
          <camera>
            <segmentation_type>instance</segmentation_type>
            <horizontal_fov>{HFOV}</horizontal_fov>
            <image><width>{SIZE[0] // SEG_SCALE}</width><height>{SIZE[1] // SEG_SCALE}</height></image>
            <clip><near>0.1</near><far>500</far></clip>
          </camera>
        </sensor>"""
        if labels
        else ""
    )
    return f"""
    <model name="onizleme_kamerasi">
      <static>true</static>
      <pose>{x} {y} {z} 0 {math.radians(pitch_deg):.6f} {math.radians(yaw_deg):.6f}</pose>
      <link name="link">
        <sensor name="kamera" type="camera">
          <topic>{TOPIC}</topic>
          <always_on>1</always_on>
          <update_rate>{rate}</update_rate>
          <camera>
            <horizontal_fov>{HFOV}</horizontal_fov>
            <image><width>{SIZE[0]}</width><height>{SIZE[1]}</height></image>
            <clip><near>0.1</near><far>500</far></clip>
          </camera>
        </sensor>{seg}
      </link>
    </model>
"""


def world_text(scenario: str | None, world: str | None, extra: str, out: Path) -> tuple[Path, str]:
    """World file with the preview camera (and the scenario's people, if a scenario is given); returns (path, world
    name)."""
    if scenario:
        sc = hedef.load(scenario)
        path = hedef.write_world(sc, out, extra)
        return path, sc.world
    text = (SIM_DIR / "worlds" / f"{world}.sdf").read_text(encoding="utf-8")
    path = out / "dunya.sdf"
    path.write_text(text.replace("</world>", extra + "  </world>", 1), encoding="utf-8")
    return path, world


def people_of(scenario: str | None) -> dict[int, str]:
    """Segmentation label -> column prefix of everybody in the scenario (only the world: nobody but a target)."""
    others = len(hedef.load(scenario).others) if scenario else 0
    return {hedef.TARGET_LABEL: "hedef"} | {hedef.OTHER_LABEL + i: f"insan{i + 1}" for i in range(others)}


class Frames:
    def __init__(self, wanted: list[float], video: tuple[float, float] | None, people: dict[int, str] | None) -> None:
        self.wanted = wanted
        self.video = video
        self.people = people
        self.photos: dict[float, np.ndarray] = {}
        self.clip: list[tuple[float, np.ndarray]] = []
        self.boxes: dict[int, dict] = {}  # frame time [us] -> visible_parts()
        self.last = 0.0
        self.lock = threading.Lock()
        self.node = Node()
        self.node.subscribe(Image, TOPIC, self.on_image)
        if people:  # raw (kayit.read_image): Gazebo's segmentation frames carry a header that grows every frame
            self.node.subscribe_raw(SEG_TOPIC + "/labels_map", self.on_labels, IMAGE_TYPE, SubscribeOptions())

    def on_labels(self, raw: bytes, _info: object) -> None:
        frame = read_image(raw)
        parts = visible_parts(label_channel(frame), self.people)
        with self.lock:
            self.boxes[round(frame.t * 1e6)] = parts

    def annotate(self, t: float, bgr: np.ndarray) -> np.ndarray:
        """Draw the people's boxes of the segmentation frame taken at the same time on a BGR frame of any size
        (video.draw_referee: target blue, other people orange, as in kosu.mp4)."""
        parts = self.boxes.get(round(t * 1e6))
        if parts is None:
            return bgr
        scale = bgr.shape[1] / SIZE[0]
        img = np.ascontiguousarray(bgr)
        labels: list[video.Label] = []
        video.draw_referee(img, video.referee_boxes(parts, list(self.people.values())), labels, scale)
        size = max(14, round(36 * scale))
        if parts["hedef_piksel"] == 0:
            text = "Hedef görünmüyor (örtülü veya kadraj dışı)"
            labels.append(video.Label(20, 15, text, video.TARGET_BGR, size, True, "la", 2, video.WHITE))
        labels.append(video.Label(20, img.shape[0] - 15, f"t = {t:.1f} s", video.WHITE, size, True, "lb", 2))
        return video.render_labels(img, labels)

    def on_image(self, msg: Image) -> None:
        t = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        img = None
        with self.lock:
            self.last = t
            for want in self.wanted:
                if want not in self.photos and abs(t - want) < 0.051:
                    img = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.width, 3).copy()
                    self.photos[want] = img
            if self.video and self.video[0] <= t <= self.video[1]:
                if img is None:
                    img = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.width, 3).copy()
                self.clip.append((t, img))

    def done(self) -> bool:
        with self.lock:
            end = max(self.wanted + ([self.video[1]] if self.video else []))
            return self.last > end + 0.2


def capture(world: Path, frames: Frames, out: Path) -> bool:
    """Run Gazebo without a window on the world until `frames` has every frame it waits for (Gazebo's log goes to
    out/sim.log); False if Gazebo stopped or the frames did not come."""
    env = dict(os.environ)
    env["GZ_SIM_RESOURCE_PATH"] = f"{SIM_DIR / 'models'}:{SIM_DIR / 'worlds'}:{REPO / 'Tools/simulation/gz/models'}"
    env["GZ_SIM_SERVER_CONFIG_PATH"] = str(SIM_DIR / "server.config")
    log = (out / "sim.log").open("w")
    proc = subprocess.Popen(
        ["gz", "sim", "-s", "-r", "--headless-rendering", "--verbose=1", str(world)], env=env, stdout=log, stderr=log
    )
    end = max(frames.wanted + ([frames.video[1]] if frames.video else []))
    print(f"Gazebo açıldı; {end:.0f} s simülasyon zamanı bekleniyor...", flush=True)
    try:
        t_wall = time.monotonic()
        while not frames.done():
            if proc.poll() is not None:
                print(f"Gazebo kapandı (bkz. {out / 'sim.log'})", file=sys.stderr)
                return False
            if time.monotonic() - t_wall > 120 + 4 * end:
                print("Zaman aşımı: kareler gelmedi", file=sys.stderr)
                return False
            time.sleep(0.5)
    finally:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(15)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()
    if frames.people:
        time.sleep(0.5)  # the last segmentation frames
    return True


def write_video(
    clip: list[tuple[float, np.ndarray]],
    stem: Path,
    annotate: Callable[[float, np.ndarray], np.ndarray] | None = None,
) -> Path:
    """The clip's RGB frames, in time order, as <stem>.mp4 at VIDEO_SIZE and VIDEO_FPS (video.Encoder: H.264,
    yuv420p, +faststart); annotate(t, bgr) draws on each frame."""
    path = stem.with_suffix(".mp4")
    with video.Encoder(path, size=VIDEO_SIZE, fps=VIDEO_FPS) as enc:
        for t, img in sorted(clip, key=lambda c: c[0]):
            bgr = cv2.cvtColor(cv2.resize(img, VIDEO_SIZE, interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2BGR)
            enc.write(annotate(t, bgr) if annotate is not None else bgr)
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--dunya", help="tez/sim/worlds/<ad>.sdf")
    src.add_argument("--senaryo", help="senaryo adı veya .yaml yolu (dünyası + hedefi)")
    camera = f"0,0,10,{kamera.NOMINAL_TILT_DEG:g},0"  # the drone camera over the take-off point, default mount
    ap.add_argument("--kamera", default=camera, help=f"x,y,z,eğim_derece,yön_derece (varsayılan {camera})")
    ap.add_argument("--tepe", action="store_true", help="sahnenin ortasının üstünden dik aşağı bak")
    ap.add_argument("--zaman", default="3", help="fotoğraf zamanları [s], virgülle")
    ap.add_argument("--video", help="başlangıç:bitiş [s] arası MP4 video (10 kare/s, VLC)")
    ap.add_argument("--etiket", action="store_true", help="hakemin kutularını çiz: hedef mavi, diğer insanlar turuncu")
    ap.add_argument("--cikti", type=Path)
    args = ap.parse_args()

    if running():
        print("Zaten çalışan bir PX4 veya Gazebo var; önce onu kapatın", file=sys.stderr)
        return 2
    try:
        cam = [float(v) for v in args.kamera.split(",")]
        wanted = [float(v) for v in args.zaman.split(",")] if args.zaman else []
        video = tuple(float(v) for v in args.video.split(":")) if args.video else None
    except ValueError:
        print("--kamera, --zaman veya --video biçimi hatalı (--help)", file=sys.stderr)
        return 2
    if len(cam) != 5 or (video and len(video) != 2):
        print("--kamera beş sayı, --video başlangıç:bitiş olmalı", file=sys.stderr)
        return 2
    if args.tepe:
        if args.senaryo:
            x0, x1, y0, y1 = hedef.load(args.senaryo).bounds()
            cam = [(x0 + x1) / 2, (y0 + y1) / 2, max(30.0, 1.2 * max(x1 - x0, y1 - y0)), 90, 0]
        else:
            cam = [cam[0], cam[1], 40, 90, 0]
    name = Path(args.senaryo).stem if args.senaryo else args.dunya
    out = args.cikti or SIM_DIR / "sonuclar" / f"{dt.datetime.now():%Y%m%d_%H%M%S}_onizleme_{name}"
    out.mkdir(parents=True, exist_ok=True)
    rate = VIDEO_FPS if video else 20
    world, _ = world_text(args.senaryo, args.dunya, camera_sdf(*cam, rate, args.etiket), out)
    people = people_of(args.senaryo) if args.etiket else None
    frames = Frames(wanted, video, people)
    if not capture(world, frames, out):
        return 1

    for t, img in sorted(frames.photos.items()):
        path = out / f"kare_{t:07.2f}.png"
        if people:
            img = cv2.cvtColor(frames.annotate(t, cv2.cvtColor(img, cv2.COLOR_RGB2BGR)), cv2.COLOR_BGR2RGB)
        PilImage.fromarray(img).save(path)
        print(f"Fotoğraf: {path}")
    if frames.clip:
        video_path = write_video(frames.clip, out / name, frames.annotate if people else None)
        print(f"Video: {video_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
