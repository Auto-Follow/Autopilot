#!/usr/bin/env python3
"""Look at a world (or a scenario) through a camera like the drone's, without PX4: photos or a WebM video.

    P=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python
    $P tez/sim/araclar/onizleme.py --dunya cayir                         # photo from the hover point (0, 0, 10 m)
    $P tez/sim/araclar/onizleme.py --senaryo kivrimli_yuruyus --video 60:90
    ... --kamera 0,0,10,45,0      camera x, y, z [m], pitch down [deg], yaw [deg, 0 = east, 90 = north]
    ... --zaman 5,20,40           sim times of the photos [s]
    ... --tepe                    camera straight down from above the middle of the scene instead
    ... --etiket                  draw the referee's boxes (segmentation): target blue, other people orange

The camera has the drone camera's lens and resolution (Camera Module 3: 66 deg, 2304x1296) but does not move;
the drone itself stands on the ground at (0, 0). Output: tez/sim/sonuclar/<date>_onizleme_<name>/.
"""

import argparse
import datetime as dt
import math
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")  # protobuf 7.x in ~/.local
os.environ.setdefault("GZ_IP", "127.0.0.1")

import numpy as np  # noqa: E402
from gz.msgs10.image_pb2 import Image  # noqa: E402
from gz.transport13 import Node  # noqa: E402
from PIL import Image as PilImage  # noqa: E402
from PIL import ImageDraw, ImageFont  # noqa: E402

import hedef  # noqa: E402
from kayit import SEG_SCALE, visible_parts  # noqa: E402
from simulasyon import REPO, SIM_DIR, running  # noqa: E402

TOPIC = "/onizleme/image"
SEG_TOPIC = "/onizleme_seg"
TARGET_BOX = (42, 120, 214)  # report palette: target blue, drone/others orange
OTHER_BOX = (235, 104, 52)
HFOV = 1.151917  # [rad] Camera Module 3 Standard, as models/x500_tez
SIZE = (2304, 1296)
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
        if people:
            self.node.subscribe(Image, SEG_TOPIC + "/labels_map", self.on_labels)

    def on_labels(self, msg: Image) -> None:
        t = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        labels = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.width, 3)[:, :, 2]
        parts = visible_parts(labels, self.people)
        with self.lock:
            self.boxes[round(t * 1e6)] = parts

    def annotate(self, t: float, img: np.ndarray) -> np.ndarray:
        """Draw the people's boxes of the segmentation frame taken at the same time."""
        parts = self.boxes.get(round(t * 1e6))
        if parts is None:
            return img
        pil = PilImage.fromarray(img)
        draw = ImageDraw.Draw(pil)
        font = ImageFont.load_default(size=36)
        for prefix in self.people.values():
            if parts[f"{prefix}_piksel"] == 0:
                continue
            box = [parts[f"{prefix}_kutu_{k}"] for k in ("u0", "v0", "u1", "v1")]
            colour = TARGET_BOX if prefix == "hedef" else OTHER_BOX
            draw.rectangle(box, outline=colour, width=5)
            draw.text((box[0], box[1] - 42), "HEDEF" if prefix == "hedef" else prefix, fill=colour, font=font)
        if parts["hedef_piksel"] == 0:
            draw.text((40, 30), "Hedef görünmüyor (örtülü veya kadraj dışı)", fill=TARGET_BOX, font=font)
        draw.text((40, SIZE[1] - 70), f"t = {t:.1f} s", fill=(255, 255, 255), font=font)
        return np.asarray(pil)

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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--dunya", help="tez/sim/worlds/<ad>.sdf")
    src.add_argument("--senaryo", help="senaryo adı veya .yaml yolu (dünyası + hedefi)")
    ap.add_argument("--kamera", default="0,0,10,45,0", help="x,y,z,eğim_derece,yön_derece (varsayılan 0,0,10,45,0)")
    ap.add_argument("--tepe", action="store_true", help="sahnenin ortasının üstünden dik aşağı bak")
    ap.add_argument("--zaman", default="3", help="fotoğraf zamanları [s], virgülle")
    ap.add_argument("--video", help="başlangıç:bitiş [s] arası WebM video (10 kare/s)")
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
        PilImage.fromarray(frames.annotate(t, img) if people else img).save(path)
        print(f"Fotoğraf: {path}")
    if frames.clip:
        tmp = out / "kareler"
        tmp.mkdir(exist_ok=True)
        for i, (t, img) in enumerate(sorted(frames.clip, key=lambda c: c[0])):
            if people:
                img = frames.annotate(t, img)
            PilImage.fromarray(img).resize((SIZE[0] // 2, SIZE[1] // 2)).save(tmp / f"{i:05d}.png")
        video_path = out / f"{name}.webm"
        subprocess.run(
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-y",
                "-framerate",
                str(VIDEO_FPS),
                "-i",
                str(tmp / "%05d.png"),
                "-c:v",
                "libvpx-vp9",
                "-b:v",
                "0",
                "-crf",
                "32",
                "-row-mt",
                "1",
                str(video_path),
            ],
            check=True,
        )
        shutil.rmtree(tmp)
        print(f"Video: {video_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
