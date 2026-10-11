#!/usr/bin/env python3
"""Copies of the Mingfei actor's walk/run animations (COLLADA) that do not glide. Measured with a side camera
(2026-10-11):

1. The cycles begin in mid-stride, so a target setting off from standing started in a frozen lunge. The copy starts
   at another frame, where the feet pass each other.
2. The hips travel ~9 % further per cycle than the legs step (the motion capture was retargeted to a skeleton with
   other proportions). Gazebo moves the actor by the hip travel (interpolate_x), so the planted foot slid forward
   ~0.12-0.2 m/s at 1.4 m/s. The copy scales the hip travel to the real stride.

    python3 tez/sim/araclar/animasyon.py <source.dae> <target.dae> <offset_m> [stride_scale]

offset_m: hip travel [m] from the first frame to the new first frame; stride_scale: factor on the hip travel. Plain
Python (kur.sh runs it before any venv). Frame k0 becomes the first, the frames before it move to the end, and the
hip translation of the moved frames is advanced by one cycle so it keeps growing.
"""

import re
import sys

ROOT = "Hips"


def _floats(text: str) -> list[float]:
    return [float(v) for v in text.split()]


def _fmt(values: list[float]) -> str:
    return " ".join(f"{v:.6g}" for v in values)


def retime(dae: str, offset_m: float, stride_scale: float = 1.0) -> str:
    root = re.search(r'<animation id="[^"]*">(?:(?!</animation>).)*target="' + ROOT + r'/transform"', dae, re.S)
    if root is None:
        raise ValueError(f"no {ROOT} animation channel")
    arrays = re.findall(r'<float_array id="[^"]+" count="(\d+)">([^<]*)</float_array>', root.group(0))
    n = int(arrays[0][0])
    hips = _floats(arrays[1][1])
    x = [hips[16 * i + 3] for i in range(n)]
    k0 = min(range(n), key=lambda i: abs(x[i] - x[0] - offset_m))
    # The loop closes from the last frame back to the first: one cycle further plus one frame of travel
    cycle = x[-1] - x[0] + (x[-1] - x[0]) / (n - 1)
    order = list(range(k0, n)) + list(range(k0))

    def reorder(match: re.Match) -> str:
        count, values = int(match.group(2)), _floats(match.group(3))
        if count == n:  # key times stay as they are
            return match.group(0)
        if count != 16 * n:
            raise ValueError(f"unexpected array size {count} (frames {n})")
        frames = [values[16 * i : 16 * i + 16] for i in order]
        if match.group(1).find(f"_{ROOT}_") >= 0:
            for j, i in enumerate(order):
                frames[j][3] = x[0] + stride_scale * (frames[j][3] + (cycle if i < k0 else 0.0) - x[k0])
        return (
            f'<float_array id="{match.group(1)}" count="{count}">{_fmt([v for f in frames for v in f])}</float_array>'
        )

    def channel(match: re.Match) -> str:
        return re.sub(r'<float_array id="([^"]+)" count="(\d+)">([^<]*)</float_array>', reorder, match.group(0))

    lib = re.search(r"<library_animations>.*?</library_animations>", dae, re.S)
    body = re.sub(r'<animation id="[^"]*">.*?</animation>', channel, lib.group(0), flags=re.S)
    return dae[: lib.start()] + body + dae[lib.end() :]


if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    src, dst, offset = sys.argv[1], sys.argv[2], float(sys.argv[3])
    scale = float(sys.argv[4]) if len(sys.argv) == 5 else 1.0
    with open(src, encoding="utf-8") as f:
        text = f.read()
    with open(dst, "w", encoding="utf-8") as f:
        f.write(retime(text, offset, scale))
