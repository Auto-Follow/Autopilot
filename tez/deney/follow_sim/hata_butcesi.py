#!/usr/bin/env python3
"""Monte Carlo error budget of the flat-ground geolocation for real hardware error levels.

For each follow geometry (height, distance) the target is placed at the image point where the drone sees it, then
the inputs are disturbed with typical Pixhawk 6C / Camera Module 3 error levels and the horizontal error is measured.
Writes sonuclar/hata_butcesi.md and .json.
"""
import json
import math
from pathlib import Path

import numpy as np

import geolocation as geoloc

HERE = Path(__file__).resolve().parent
N = 4000
# 1-sigma error levels (assumptions, to be replaced by measured values)
SOURCES = {
    "yaw (yön) 2°": dict(yaw=2.0),
    "roll/pitch 0.5°": dict(rp=0.5),
    "yükseklik 0.5 m (baro/GPS)": dict(h=0.5),
    "piksel 5 px (tespit)": dict(px=5.0),
    "kamera montaj açısı 1°": dict(mount=1.0),
    "zemin eğimi/engebe 0.3 m": dict(ground=0.3),
}
ALL = dict(yaw=2.0, rp=0.5, h=0.5, px=5.0, mount=1.0, ground=0.3)
GEOMETRIES = [(3, 8), (5, 8), (8, 8), (12, 8), (8, 5), (8, 12), (12, 12)]


def run(height, dist, pitch_deg, err, rng):
    cam = geoloc.CameraModel.from_hfov(1.1519, 2304, 1296, pitch_down_deg=pitch_deg)
    q = geoloc.euler_to_quat(0.0, 0.0, 0.0)  # flying north, target straight ahead
    pos = (0.0, 0.0, -height)
    u, v, _ = geoloc.point_to_pixel(cam, (dist, 0.0, 0.0), q, pos)
    if not (0 <= v < cam.height):
        return None
    errs = []
    for _ in range(N):
        r = math.radians(rng.normal(0, err.get("rp", 0)))
        p = math.radians(rng.normal(0, err.get("rp", 0)))
        y = math.radians(rng.normal(0, err.get("yaw", 0)))
        c = geoloc.CameraModel.from_hfov(1.1519, 2304, 1296,
                                         pitch_down_deg=pitch_deg + rng.normal(0, err.get("mount", 0)))
        fix = geoloc.pixel_to_ground(c, u + rng.normal(0, err.get("px", 0)), v + rng.normal(0, err.get("px", 0)),
                                     geoloc.euler_to_quat(r, p, y), (0.0, 0.0, -height + rng.normal(0, err.get("h", 0))),
                                     rng.normal(0, err.get("ground", 0)))
        if fix is not None:
            errs.append(math.hypot(fix.north - dist, fix.east))
    return np.median(errs), np.quantile(errs, 0.95), math.degrees(math.atan2(height, dist))


def main():
    rng = np.random.default_rng(1)
    rows = []
    for h, d in GEOMETRIES:
        pitch = math.degrees(math.atan2(h, d))  # camera centered on the target (best case for that geometry)
        row = {"yukseklik": h, "mesafe": d, "bakis_acisi": round(pitch, 1)}
        for name, err in list(SOURCES.items()) + [("HEPSİ", ALL)]:
            res = run(h, d, pitch, err, rng)
            row[name] = None if res is None else (round(res[0], 2), round(res[1], 2))
        rows.append(row)
    lines = ["| yük. / mes. | bakış | " + " | ".join(list(SOURCES) + ["HEPSİ"]) + " |",
             "|---|---|" + "---|" * (len(SOURCES) + 1)]
    for r in rows:
        cells = [f"{r[k][0]:.2f} / {r[k][1]:.2f}" if r[k] else "—" for k in list(SOURCES) + ["HEPSİ"]]
        lines.append(f"| {r['yukseklik']} / {r['mesafe']} m | {r['bakis_acisi']}° | " + " | ".join(cells) + " |")
    text = ("Medyan / %95 yatay hata (m). Her satırda kamera hedefe ortalanmış, tek hata kaynağı 1σ:\n\n"
            + "\n".join(lines) + "\n")
    out = HERE / "sonuclar"
    out.mkdir(exist_ok=True)
    (out / "hata_butcesi.md").write_text(text, encoding="utf-8")
    (out / "hata_butcesi.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(text)


if __name__ == "__main__":
    main()
