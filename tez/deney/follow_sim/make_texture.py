#!/usr/bin/env python3
"""Generate the colorful checker texture used by the renkli_zemin ground model (pure Python, no PIL)."""
import random
import struct
import zlib
from pathlib import Path

SIZE = 2048          # texture resolution (px)
TILES = 40           # tiles per side -> 200 m plane / 40 = 5 m tiles
LINE_PX = 3          # dark grid line thickness (px)
PALETTE = [  # soft colors on purpose: the red target must stay the most salient object
    (142, 202, 230), (33, 158, 188), (126, 200, 160), (183, 228, 199), (255, 214, 165),
    (253, 255, 182), (202, 255, 191), (189, 178, 255), (160, 196, 255), (255, 198, 255),
    (205, 180, 219), (233, 237, 201), (204, 213, 174), (250, 237, 205), (212, 163, 115),
]


def main():
    rng = random.Random(42)
    colors = [[rng.choice(PALETTE) for _ in range(TILES)] for _ in range(TILES)]
    tile_px = SIZE / TILES
    rows = bytearray()
    for y in range(SIZE):
        rows.append(0)  # PNG filter type: none
        ty = int(y / tile_px)
        on_hline = (y % tile_px) < LINE_PX
        for x in range(SIZE):
            tx = int(x / tile_px)
            if on_hline or (x % tile_px) < LINE_PX:
                rows += b"\x28\x28\x28"
            else:
                rows += bytes(colors[ty][tx])

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(rows), 6)) + chunk(b"IEND", b"")
    out = Path(__file__).parent / "models/renkli_zemin/materials/textures/renkli_zemin.png"
    out.write_bytes(png)
    print(f"wrote {out} ({len(png) // 1024} KiB)")


if __name__ == "__main__":
    main()
