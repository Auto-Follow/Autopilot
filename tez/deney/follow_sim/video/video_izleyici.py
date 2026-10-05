#!/usr/bin/env python3
"""Ground station video window, independent from QGroundControl (e.g. on a second monitor).

Receives the H.264 RTP/UDP stream (default port 5601), decodes it with GStreamer and shows it in a resizable
OpenCV window. Drag the window to the other monitor, then press F for full screen.
Keys: F = full screen on/off, Q or Esc = quit.
"""
import argparse
import sys
import time

import cv2
import gi
import numpy as np

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

WINDOW = "Drone kamerasi"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", type=int, default=5601, help="UDP port of the RTP H.264 stream")
    p.add_argument("--latency", type=int, default=50, help="jitter buffer (ms); higher = smoother, more delay")
    return p.parse_args()


def build_pipeline(port, latency):
    desc = (
        f'udpsrc port={port} caps="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=96" '
        f"! rtpjitterbuffer latency={latency} drop-on-latency=true ! rtph264depay ! h264parse ! avdec_h264 "
        f"! videoconvert ! video/x-raw,format=BGR "
        f"! appsink name=sink max-buffers=1 drop=true sync=false"
    )
    pipeline = Gst.parse_launch(desc)
    return pipeline, pipeline.get_by_name("sink")


def waiting_frame(port):
    img = np.zeros((360, 640, 3), np.uint8)
    cv2.putText(img, "Goruntu bekleniyor...", (150, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 200, 200), 2)
    cv2.putText(img, f"UDP {port} (H.264 RTP)", (205, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (140, 140, 140), 1)
    return img


def main():
    args = parse_args()
    Gst.init(None)
    pipeline, sink = build_pipeline(args.port, args.latency)
    pipeline.set_state(Gst.State.PLAYING)

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow(WINDOW, 1280, 720)
    fullscreen = False
    last_frame_time = 0.0
    try:
        while True:
            sample = sink.emit("try-pull-sample", 100 * Gst.MSECOND)
            if sample is not None:
                caps = sample.get_caps().get_structure(0)
                w, h = caps.get_value("width"), caps.get_value("height")
                buf = sample.get_buffer()
                ok, info = buf.map(Gst.MapFlags.READ)
                if ok:
                    stride = info.size // h
                    frame = np.ndarray((h, w, 3), np.uint8, info.data, strides=(stride, 3, 1)).copy()
                    buf.unmap(info)
                    cv2.imshow(WINDOW, frame)
                    last_frame_time = time.monotonic()
            elif time.monotonic() - last_frame_time > 2.0:
                cv2.imshow(WINDOW, waiting_frame(args.port))

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
            if key in (ord("f"), ord("F")):
                fullscreen = not fullscreen
                cv2.setWindowProperty(WINDOW, cv2.WND_PROP_FULLSCREEN,
                                      cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL)
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:  # window closed with the X button
                break
    except KeyboardInterrupt:
        pass
    finally:
        pipeline.set_state(Gst.State.NULL)
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
