#!/usr/bin/env python3
"""Measures the received video under the Wi-Fi model of goruntu_yayini.py (needs a running stream).

For every (delay, loss) setting: sends it to the stream (UDP 5611), waits, then counts decoded frames on UDP 5601 for
a few seconds and saves one frame as PNG. Restores a perfect link at the end.

  tez/deney/follow_sim/.venv/bin/python tez/deney/follow_sim/video/wifi_olcum.py
"""
import argparse
import json
import socket
import time
from pathlib import Path

import cv2
import gi
import numpy as np

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

SETTINGS = [(0, 0.0), (0, 0.01), (0, 0.03), (0, 0.05), (0, 0.10), (300, 0.0), (300, 0.03)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cikti", type=Path, default=Path(__file__).resolve().parent.parent / "sonuclar" / "video")
    p.add_argument("--sure", type=float, default=8.0, help="seconds measured per setting")
    args = p.parse_args()
    args.cikti.mkdir(parents=True, exist_ok=True)
    Gst.init(None)
    pipe = Gst.parse_launch(
        'udpsrc port=5601 caps="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=96" '
        "! rtpjitterbuffer latency=50 drop-on-latency=true ! rtph264depay ! h264parse ! avdec_h264 "
        "! videoconvert ! video/x-raw,format=BGR ! appsink name=sink max-buffers=1 drop=true sync=false "
        "emit-signals=true")
    sink = pipe.get_by_name("sink")
    frames = {"n": 0, "last": None}

    def on_sample(s):
        sample = s.emit("pull-sample")
        buf, caps = sample.get_buffer(), sample.get_caps().get_structure(0)
        ok, info = buf.map(Gst.MapFlags.READ)
        if ok:
            frames["last"] = np.frombuffer(info.data, np.uint8).reshape(caps.get_value("height"),
                                                                        caps.get_value("width"), 3).copy()
            buf.unmap(info)
        frames["n"] += 1
        return Gst.FlowReturn.OK

    sink.connect("new-sample", on_sample)
    pipe.set_state(Gst.State.PLAYING)
    ctl = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    results = []
    try:
        for delay, loss in SETTINGS:
            ctl.sendto(json.dumps({"delay_ms": delay, "loss": loss}).encode(), ("127.0.0.1", 5611))
            time.sleep(3.0)
            n0, t0 = frames["n"], time.monotonic()
            snaps = []
            while time.monotonic() - t0 < args.sure:
                time.sleep(args.sure / 4)
                if frames["last"] is not None:
                    snaps.append(frames["last"])
            fps = (frames["n"] - n0) / (time.monotonic() - t0)
            name = f"gecikme{delay}_kayip{loss * 100:g}.png"
            if snaps:
                cv2.imwrite(str(args.cikti / name), snaps[len(snaps) // 2])
            results.append({"gecikme_ms": delay, "kayip": loss, "alinan_fps": round(fps, 1), "kare": name})
            print(results[-1], flush=True)
    finally:
        ctl.sendto(json.dumps({"delay_ms": 0, "loss": 0.0}).encode(), ("127.0.0.1", 5611))
        pipe.set_state(Gst.State.NULL)
    (args.cikti / "video_olcum.json").write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
