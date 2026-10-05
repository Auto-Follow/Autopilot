#!/usr/bin/env python3
"""Annotated camera stream (Vision-like prototype).

camera frame -> target detection -> overlay -> H.264 -> RTP/UDP to the ground station (QGC and/or viewer)

In simulation the frames come from the Gazebo camera topic. On the real drone the source would be picamera2 and
the detection the Vision algorithm; the overlay + encoding + streaming part is meant to stay the same.
The detection here is only a placeholder: it looks for the saturated red body of the simulated target.

Raspberry Pi 5 has no hardware H.264 encoder, so x264 runs on the CPU there too; keep the stream small.

Wi-Fi model: a netsim element delays / drops the RTP packets (not the detection report: Vision runs on board).
Set it with --wifi-delay / --wifi-loss or at runtime with a UDP JSON {"delay_ms": 300, "loss": 0.05} to port 5611
(the panel does this).
"""
import os

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

import argparse
import fcntl
import json
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import cv2
import gi
import numpy as np
from gz.msgs10.image_pb2 import Image
from gz.transport13 import Node, SubscribeOptions

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

LOCK_FILE = "/tmp/follow_video.lock"
NO_FRAME_EXIT_S = 15.0  # exit when the simulation is gone (only after frames were received)
MIN_TARGET_PIXELS = 12  # on the 1/4 scaled detection image
DETECTION_ADDR = ("127.0.0.1", 5610)  # per-frame detection result for the panel's Vision mode (follow_core.py)
CONTROL_PORT = 5611  # Wi-Fi impairment settings for the video packets


def windows_host_ip():
    """QGC host: the Windows side (default gateway) under WSL2, otherwise this machine."""
    try:
        wsl = "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        wsl = False
    if not wsl:
        return "127.0.0.1"
    out = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True).stdout.split()
    return out[2] if len(out) > 2 else "127.0.0.1"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--world", default=os.environ.get("PX4_GZ_WORLD", "renkli_duz"))
    p.add_argument("--model", default="x500_mono_cam_0")
    p.add_argument("--hosts", default=os.environ.get("FOLLOW_VIDEO_HOSTS"),
                   help="comma separated host:port list (default: <Windows>:5600 for QGC, 127.0.0.1:5601 for "
                        "video_izleyici.py)")
    p.add_argument("--width", type=int, default=1280, help="stream width (px)")
    p.add_argument("--height", type=int, default=720, help="stream height (px)")
    p.add_argument("--fps", type=int, default=int(os.environ.get("FOLLOW_VIDEO_FPS", 15)),
                   help="stream frame rate (default 15, or FOLLOW_VIDEO_FPS); the gz camera produces 30")
    p.add_argument("--bitrate", type=int, default=2000, help="kbit/s")
    p.add_argument("--keyframe", type=float, default=1.0,
                   help="key frame interval (s); after a lost packet the picture recovers at the next key frame")
    p.add_argument("--wifi-delay", type=int, default=int(os.environ.get("FOLLOW_WIFI_DELAY_MS", 0)),
                   help="added one-way delay of the video packets (ms)")
    p.add_argument("--wifi-loss", type=float, default=float(os.environ.get("FOLLOW_WIFI_LOSS", 0)),
                   help="video packet loss probability (0-1)")
    return p.parse_args()


class FrameSource:
    """Latest Gazebo camera frame (RGB). Only a subscription lives in this process, so no transport deadlock.

    The callback only keeps the raw bytes; parsing a 9 MB image with the pure-python protobuf takes ~14 ms, so only
    the frame that is actually streamed gets parsed. (Throttling the subscription to the stream rate is not an
    option: against a 30 Hz camera it accepts every 2nd or 3rd frame and ends up at ~10-12 fps instead of 15.)
    """

    def __init__(self, world, model):
        self.topic = f"/world/{world}/model/{model}/link/camera_link/sensor/imager/image"
        self._lock = threading.Lock()
        self._raw = None
        self.stamp = 0.0  # time.monotonic() of the last frame
        self.node = Node()
        self.node.subscribe_raw(self.topic, self._on_image, "gz.msgs.Image", SubscribeOptions())

    def _on_image(self, data, _info):
        with self._lock:
            self._raw = data
            self.stamp = time.monotonic()

    def latest(self):
        """(frame, sim_time) of the newest image, or (None, 0) if there is none or it is not RGB."""
        with self._lock:
            raw = self._raw
        if raw is None:
            return None, 0.0
        msg = Image.FromString(raw)
        frame = np.frombuffer(msg.data, dtype=np.uint8)
        if frame.size != msg.width * msg.height * 3:
            return None, 0.0  # only RGB_INT8 is expected from the gz camera
        return frame.reshape(msg.height, msg.width, 3), msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9


def detect_red_target(rgb):
    """Placeholder detector: bounding box of saturated red pixels. Returns (x0, y0, x1, y1) in full-res pixels."""
    step = 4
    small = rgb[::step, ::step].astype(np.int16)
    r, g, b = small[..., 0], small[..., 1], small[..., 2]
    # ratio based, so the shaded (dark red) legs count too; soft ground colors and the skin-colored head do not
    mask = (r > 50) & (r > 2 * g + 20) & (r > 2 * b + 20)
    if np.count_nonzero(mask) < MIN_TARGET_PIXELS:
        return None
    ys, xs = np.nonzero(mask)
    return xs.min() * step, ys.min() * step, (xs.max() + 1) * step, (ys.max() + 1) * step


def draw_overlay(bgr, box, full_w, full_h, fps, sim_time):
    """Draws on the stream-sized frame; texts report full-resolution pixel coordinates (as used for geolocation)."""
    h, w = bgr.shape[:2]
    sx, sy = w / full_w, h / full_h
    cx, cy = w // 2, h // 2
    white, green, red, yellow = (255, 255, 255), (60, 220, 60), (40, 40, 255), (0, 220, 255)
    font = cv2.FONT_HERSHEY_SIMPLEX

    cv2.line(bgr, (cx - 25, cy), (cx + 25, cy), white, 1, cv2.LINE_AA)
    cv2.line(bgr, (cx, cy - 25), (cx, cy + 25), white, 1, cv2.LINE_AA)

    if box is not None:
        x0, y0, x1, y1 = box
        u, v = (x0 + x1) / 2, y1  # bottom-center = ground contact point, the pixel used for geolocation
        p0, p1 = (int(x0 * sx), int(y0 * sy)), (int(x1 * sx), int(y1 * sy))
        foot = (int(u * sx), int(v * sy))
        cv2.rectangle(bgr, p0, p1, green, 2, cv2.LINE_AA)
        cv2.line(bgr, (cx, cy), foot, yellow, 1, cv2.LINE_AA)
        cv2.circle(bgr, foot, 5, red, -1, cv2.LINE_AA)
        lines = [(f"HEDEF  (u, v) = ({u:.0f}, {v:.0f}) px", green),
                 (f"merkezden sapma  du = {u - full_w / 2:+.0f}  dv = {v - full_h / 2:+.0f} px", white)]
    else:
        lines = [("HEDEF YOK", red)]

    for i, (text, color) in enumerate(lines):
        y = 32 + i * 30
        cv2.putText(bgr, text, (16, y), font, 0.75, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(bgr, text, (16, y), font, 0.75, color, 2, cv2.LINE_AA)
    info = f"{fps:4.1f} fps | kamera {full_w}x{full_h} -> yayin {w}x{h} | t = {sim_time:7.1f} s"
    cv2.putText(bgr, info, (16, h - 16), font, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(bgr, info, (16, h - 16), font, 0.55, white, 1, cv2.LINE_AA)
    cv2.putText(bgr, "PROTOTIP: renk esikli tespit", (w - 330, h - 16), font, 0.55, yellow, 1, cv2.LINE_AA)


def build_pipeline(args, hosts):
    clients = ",".join(hosts)
    desc = (
        f"appsrc name=src is-live=true format=time do-timestamp=true "
        f"caps=video/x-raw,format=BGR,width={args.width},height={args.height},framerate={args.fps}/1 "
        f"! queue leaky=downstream max-size-buffers=2 ! videoconvert ! video/x-raw,format=I420 "
        f"! x264enc tune=zerolatency speed-preset=ultrafast bitrate={args.bitrate} "
        f"key-int-max={max(1, round(args.keyframe * args.fps))} "
        f"! video/x-h264,profile=constrained-baseline "
        f"! rtph264pay config-interval=1 pt=96 mtu=1400 "
        f"! netsim name=wifi delay-probability=0 drop-probability=0 allow-reordering=false "
        f"! multiudpsink clients={clients} sync=false async=false"
    )
    pipeline = Gst.parse_launch(desc)
    return pipeline, pipeline.get_by_name("src"), pipeline.get_by_name("wifi")


def set_wifi(netsim, delay_ms, loss):
    """Constant one-way delay + random packet loss on the RTP packets."""
    delay_ms = max(0, int(delay_ms))
    netsim.set_property("min-delay", delay_ms)
    netsim.set_property("max-delay", delay_ms)
    netsim.set_property("delay-probability", 1.0 if delay_ms > 0 else 0.0)
    netsim.set_property("drop-probability", min(1.0, max(0.0, float(loss))))
    print(f"Wi-Fi benzetimi: gecikme {delay_ms} ms, paket kaybi %{100 * float(loss):.1f}", flush=True)


def control_listener(netsim):
    """Runtime Wi-Fi settings from the panel (UDP JSON on CONTROL_PORT)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("127.0.0.1", CONTROL_PORT))
    except OSError:
        return
    while True:
        try:
            cfg = json.loads(sock.recv(1024))
            set_wifi(netsim, cfg.get("delay_ms", 0), cfg.get("loss", 0.0))
        except (OSError, ValueError, TypeError):
            continue


def main():
    args = parse_args()
    lock = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("Goruntu yayini zaten calisiyor.")
        return 0

    hosts = (args.hosts.split(",") if args.hosts else [f"{windows_host_ip()}:5600", "127.0.0.1:5601"])
    Gst.init(None)
    pipeline, appsrc, netsim = build_pipeline(args, hosts)
    set_wifi(netsim, args.wifi_delay, args.wifi_loss)
    threading.Thread(target=control_listener, args=(netsim,), daemon=True).start()
    pipeline.set_state(Gst.State.PLAYING)
    source = FrameSource(args.world, args.model)
    detection_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"Kamera: {source.topic}\nYayin: H.264 RTP -> {', '.join(hosts)}  ({args.width}x{args.height}, "
          f"{args.fps} fps, {args.bitrate} kbit/s)", flush=True)

    period = 1.0 / args.fps
    last_stamp, fps, t_prev = 0.0, 0.0, time.monotonic()
    try:
        while True:
            t0 = time.monotonic()
            stamp = source.stamp
            if stamp == last_stamp:  # no new camera frame yet
                if stamp and t0 - stamp > NO_FRAME_EXIT_S:
                    print("Kamera goruntusu kesildi, cikiliyor.", flush=True)
                    break
                time.sleep(0.005)
                continue
            last_stamp = stamp
            frame, sim_time = source.latest()
            if frame is None:
                continue
            box = detect_red_target(frame)
            full_h, full_w = frame.shape[:2]
            report = {"stamp": time.monotonic(), "sim_time": float(sim_time), "seen": box is not None}
            if box is not None:
                # A box touching the bottom / left / right border is cut off: its bottom-center is not the foot point
                edge = 8
                clipped = box[3] >= full_h - edge or box[0] <= edge or box[2] >= full_w - edge
                report.update(u=float(box[0] + box[2]) / 2, v=float(box[3]), clipped=bool(clipped))
            try:  # the detection report must never stop the video
                detection_sock.sendto(json.dumps(report).encode(), DETECTION_ADDR)
            except (OSError, TypeError, ValueError):
                pass
            out = cv2.resize(frame, (args.width, args.height), interpolation=cv2.INTER_AREA)
            out = cv2.cvtColor(out, cv2.COLOR_RGB2BGR)
            now = time.monotonic()
            fps = 0.9 * fps + 0.1 / max(now - t_prev, 1e-3) if fps else 1.0 / max(now - t_prev, 1e-3)
            t_prev = now
            draw_overlay(out, box, full_w, full_h, fps, sim_time)
            appsrc.emit("push-buffer", Gst.Buffer.new_wrapped(out.tobytes()))
            time.sleep(max(0.0, period - (time.monotonic() - t0)))
    except KeyboardInterrupt:
        pass
    finally:
        appsrc.emit("end-of-stream")
        pipeline.set_state(Gst.State.NULL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
