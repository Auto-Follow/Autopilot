#!/usr/bin/env python3
"""World generator: tez/sim/worlds/<ad>.yaml -> textured ground and trees for tez/sim/worlds/<ad>.sdf.

    python3 tez/sim/araclar/dunya.py cayir        (kur.sh runs it for every world that has a .yaml)

A real field is not one photo repeated every 1.4 m: from 10 m up a tiled texture shows as a grid. The central area
is therefore baked into unique tiles (~1.2 cm/px, about what the drone camera resolves on the ground from 10 m) by
mixing CC0 photo textures (kur.sh downloads them) with smooth noise masks: two kinds of grass, worn patches, leaf
litter under the trees and dirt paths. Every texture is laid in cells, each randomly rotated and shifted and blended
with its neighbours (stochastic tiling, Source.stochastic), so its own repeat disappears too. The ground outside the
central area is one periodic tile at half the resolution (only seen from far away).

Output (not in git, made again when the .yaml or this generator changes): tez/sim/models/<ad>_cevre/ with
model.sdf (ground tiles as visuals, trees with simple collision shapes), meshes/*.obj and textures/*.jpg.
Coordinates: Gazebo world, x east, y north [m].
"""

import hashlib
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

SIM_DIR = Path(__file__).resolve().parent.parent
TEXTURES = SIM_DIR / "models" / "dokular"  # kur.sh
TREE_MODELS = SIM_DIR / "models" / "agaclar"  # kur.sh
VERSION = "1"  # bump when the output of this generator changes for the same .yaml

TILE_M = 24.0  # [m] central tiles
TILE_PX = 2048  # per tile image, 1.19 cm/px
MARGIN_PX = 16  # every tile image also holds this much of its neighbours: the GPU's texture filtering (and its
# smaller mipmap levels) reads past the tile edge, which drew thin seams between the tiles without it
OUTER_M = 48.0  # [m] periodic outer tile: large enough for the broad colour variation (up to 30 m features)
OUTER_PX = 1680  # 2.9 cm/px (seen from far away only); many divisors, so every texture repeats exactly in it
SEAM = 0.15  # half width of the blend between neighbouring texture cells, in cells
NOISE_STEP = 8  # [px] noise and distance fields are computed on a coarser grid and interpolated
JPEG_QUALITY = 90

# name -> (file below models/dokular, real size of one texture tile [m], mean colour it is scaled to); sizes from the
# publishers' pages. The photos were exposed differently (worn ground came out twice as bright as grass), so each is
# brought to a plausible mean albedo for its kind of ground.
SOURCES = {
    "cim": ("Grass001_1K-JPG_Color.jpg", 1.4, (0.30, 0.40, 0.18)),  # ambientCG Grass001: dense green grass
    "cim_acik": ("Grass004_1K-JPG_Color.jpg", 1.4, (0.40, 0.45, 0.20)),  # ambientCG Grass004: lighter, drier grass
    "asinmis": ("Ground037_1K-JPG_Color.jpg", 2.1, (0.36, 0.36, 0.22)),  # ambientCG Ground037: worn grass and soil
    "yaprak": ("forrest_ground_01_diff_1k.jpg", 2.0, (0.30, 0.27, 0.17)),  # Poly Haven forrest_ground_01: leaf litter
    "toprak": ("dry_mud_field_001_diff_1k.jpg", 3.0, (0.40, 0.34, 0.26)),  # Poly Haven dry_mud_field_001: dirt track
}


@dataclass(frozen=True)
class TreeKind:
    """Fuel tree model (models/agaclar/<name>) measured at scale 1: trunk and crown for collisions and checks."""

    mesh: str  # submeshes "Bark" and "Branch"
    trunk_radius: float  # [m]
    crown_base: float  # [m] height where the crown starts
    crown_centre: tuple[float, float, float]  # [m] ellipsoid approximating the crown
    crown_radii: tuple[float, float, float]
    scale: tuple[float, float]  # random scale range of the instances
    litter: float  # [m] radius of leaf litter around the trunk at scale 1


TREE_KINDS = {
    # Fuel OpenRobotics "Oak tree" v7 (CC0): 6.5 m tall, crown ~9 m across
    "mese": TreeKind("mese/meshes/oak_tree.dae", 0.3, 1.5, (-0.4, 0.2, 3.9), (4.6, 4.0, 2.5), (1.0, 1.5), 4.0),
    # Fuel OpenRobotics "Pine Tree" v6 (CC0): 5 m tall, crown 3.2 m across
    "cam": TreeKind("cam/meshes/pine_tree.dae", 0.15, 0.6, (0.0, 0.0, 2.4), (1.3, 1.3, 2.2), (1.6, 2.4), 1.8),
}
CLEAR_RADIUS = 8.0  # [m] no trees around the drone's take-off point (0, 0)


@dataclass
class Tree:
    kind: str
    x: float
    y: float
    yaw: float
    scale: float

    @property
    def trunk_radius(self) -> float:
        return TREE_KINDS[self.kind].trunk_radius * self.scale

    @property
    def height(self) -> float:
        k = TREE_KINDS[self.kind]
        return (k.crown_centre[2] + k.crown_radii[2]) * self.scale


@dataclass
class Trail:
    points: np.ndarray  # (n, 2) smooth centre line
    width: float


@dataclass
class World:
    name: str
    seed: int
    centre: tuple[float, float]
    size: float  # [m] side of the baked central area
    outer: float  # [m] side of the whole ground
    paths: list[Trail] = field(default_factory=list)
    trees: list[Tree] = field(default_factory=list)
    source: Path | None = None

    @property
    def model_dir(self) -> Path:
        return SIM_DIR / "models" / f"{self.name}_cevre"

    def origin(self) -> tuple[float, float]:
        """South-west corner of the central area."""
        return self.centre[0] - self.size / 2, self.centre[1] - self.size / 2

    def blocked(self, x: float, y: float, margin: float = 0.3) -> Tree | None:
        """The tree whose trunk (plus margin) contains the point, if any."""
        for t in self.trees:
            if math.hypot(x - t.x, y - t.y) < t.trunk_radius + margin:
                return t
        return None


# --- scenario-style checks (Turkish messages name the field) ---------------------------------------------------


def _check_keys(d: dict, allowed: set[str], where: str) -> None:
    unknown = set(d) - allowed
    if unknown:
        raise ValueError(f"{where}: bilinmeyen alan(lar) {sorted(unknown)}; geçerli alanlar: {sorted(allowed)}")


def _point(value: object, where: str) -> tuple[float, float]:
    if not (isinstance(value, list | tuple) and len(value) == 2 and all(isinstance(v, int | float) for v in value)):
        raise ValueError(f"{where}: [x, y] biçiminde iki sayı olmalı (metre), gelen: {value!r}")
    return float(value[0]), float(value[1])


def _number(d: dict, key: str, where: str, default: float | None = None, minimum: float = 0.0) -> float:
    value = d.get(key, default)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{where}.{key}: sayı olmalı, gelen: {value!r}")
    if value < minimum:
        raise ValueError(f"{where}.{key}: en az {minimum} olmalı, gelen: {value}")
    return float(value)


def _kind(value: object, where: str) -> str:
    if value not in TREE_KINDS:
        raise ValueError(f"{where}: ağaç türü {sorted(TREE_KINDS)} olmalı, gelen: {value!r}")
    return str(value)


def spec_path(name: str) -> Path:
    return SIM_DIR / "worlds" / f"{name}.yaml"


def load(name: str) -> World | None:
    """Read tez/sim/worlds/<name>.yaml; None for a world without one (e.g. duz_alan: plain ground, no trees)."""
    path = spec_path(name)
    if not path.is_file():
        return None
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(d, dict):
        raise ValueError(f"{path.name}: YAML sözlük (alan: değer) olmalı")
    _check_keys(d, {"ad", "aciklama", "tohum", "alan", "yollar", "agaclar", "agac_gruplari"}, path.name)
    if d.get("ad", name) != name:
        raise ValueError(f"{path.name}: ad alanı dosya adıyla aynı olmalı ({name})")
    seed = d.get("tohum", 0)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError(f"tohum: tam sayı olmalı, gelen: {seed!r}")
    area = d.get("alan") or {}
    _check_keys(area, {"merkez", "boyut_m", "dis_boyut_m"}, "alan")
    size = _number(area, "boyut_m", "alan", 120.0, minimum=TILE_M)
    if abs(size / TILE_M - round(size / TILE_M)) > 1e-6:
        raise ValueError(f"alan.boyut_m: {TILE_M:.0f} m'nin katı olmalı, gelen: {size}")
    w = World(
        name=name,
        seed=seed,
        centre=_point(area.get("merkez", [0, 0]), "alan.merkez"),
        size=size,
        outer=_number(area, "dis_boyut_m", "alan", 500.0, minimum=size),
        source=path,
    )
    rng = np.random.default_rng(seed)
    for i, p in enumerate(d.get("yollar") or []):
        where = f"yollar[{i}]"
        if not isinstance(p, dict):
            raise ValueError(f"{where}: {{noktalar: [[x, y], ...], genislik_m: w}} olmalı")
        _check_keys(p, {"noktalar", "genislik_m"}, where)
        pts = p.get("noktalar")
        if not isinstance(pts, list) or len(pts) < 2:
            raise ValueError(f"{where}.noktalar: en az iki nokta olmalı")
        pts = np.array([_point(q, f"{where}.noktalar[{k}]") for k, q in enumerate(pts)])
        w.paths.append(Trail(_smooth_line(pts), _number(p, "genislik_m", where, 1.5, minimum=0.3)))
    for i, t in enumerate(d.get("agaclar") or []):
        where = f"agaclar[{i}]"
        if not isinstance(t, dict):
            raise ValueError(f"{where}: {{tur: mese|cam, konum: [x, y]}} olmalı")
        _check_keys(t, {"tur", "konum", "olcek"}, where)
        kind = _kind(t.get("tur"), f"{where}.tur")
        x, y = _point(t.get("konum"), f"{where}.konum")
        lo, hi = TREE_KINDS[kind].scale
        scale = _number(t, "olcek", where, float(rng.uniform(lo, hi)), minimum=0.2)
        w.trees.append(Tree(kind, x, y, float(rng.uniform(0, 2 * math.pi)), scale))
    for i, g in enumerate(d.get("agac_gruplari") or []):
        where = f"agac_gruplari[{i}]"
        if not isinstance(g, dict):
            raise ValueError(f"{where}: {{merkez: [x, y], yaricap_m: r, sayi: n, turler: [...]}} olmalı")
        _check_keys(g, {"merkez", "yaricap_m", "sayi", "turler"}, where)
        cx, cy = _point(g.get("merkez"), f"{where}.merkez")
        radius = _number(g, "yaricap_m", where, minimum=1.0)
        count = int(_number(g, "sayi", where, minimum=1))
        kinds = [_kind(k, f"{where}.turler") for k in (g.get("turler") or sorted(TREE_KINDS))]
        _scatter(w, rng, cx, cy, radius, count, kinds)
    for i, t in enumerate(w.trees):
        if math.hypot(t.x, t.y) < CLEAR_RADIUS:
            raise ValueError(
                f"ağaç {i} ({t.kind}, {t.x:.1f}, {t.y:.1f}): dronun kalkış yerine {CLEAR_RADIUS:.0f} m'den yakın"
            )
    return w


def _scatter(w: World, rng: np.random.Generator, cx: float, cy: float, r: float, n: int, kinds: list[str]) -> None:
    """n trees in a disc, not on a path, not too close to each other or to the take-off point."""
    placed = 0
    for _ in range(200 * n):
        if placed == n:
            return
        a, d = rng.uniform(0, 2 * math.pi), r * math.sqrt(rng.uniform())
        x, y = cx + d * math.cos(a), cy + d * math.sin(a)
        kind = kinds[int(rng.integers(len(kinds)))]
        lo, hi = TREE_KINDS[kind].scale
        scale = float(rng.uniform(lo, hi))
        gap = 0.45 * TREE_KINDS[kind].crown_radii[0] * scale
        if math.hypot(x, y) < CLEAR_RADIUS or path_distance(w.paths, np.array([x]), np.array([y]))[0] < 1.5:
            continue
        if any(
            math.hypot(x - t.x, y - t.y) < gap + 0.45 * TREE_KINDS[t.kind].crown_radii[0] * t.scale for t in w.trees
        ):
            continue
        w.trees.append(Tree(kind, x, y, float(rng.uniform(0, 2 * math.pi)), scale))
        placed += 1
    raise ValueError(f"ağaç grubu ({cx}, {cy}): {n} ağaç {r} m yarıçapa sığmadı; yarıçapı büyütün veya sayıyı azaltın")


def _smooth_line(pts: np.ndarray, step: float = 0.25) -> np.ndarray:
    """Catmull-Rom curve through the points, sampled about every `step` metres."""
    p = np.vstack([2 * pts[0] - pts[1], pts, 2 * pts[-1] - pts[-2]])
    out = []
    for i in range(1, len(p) - 2):
        n = max(2, int(np.hypot(*(p[i + 1] - p[i])) / step))
        s = np.linspace(0, 1, n, endpoint=False)[:, None]
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        out.append(
            0.5
            * (2 * p1 + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s**2 + (-p0 + 3 * p1 - 3 * p2 + p3) * s**3)
        )
    out.append(pts[-1:])
    return np.vstack(out)


def path_distance(paths: list[Trail], x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Distance [m] from each point to the nearest path edge (negative inside a path); +inf without paths."""
    best = np.full(x.shape, np.inf)
    q = np.stack([x.ravel(), y.ravel()], axis=1)
    for p in paths:
        a, b = p.points[:-1], p.points[1:]
        ab = b - a
        ab2 = np.maximum((ab**2).sum(axis=1), 1e-12)
        d = np.full(len(q), np.inf)
        for k in range(0, len(a), 256):  # chunks keep the (points x segments) arrays small
            s = slice(k, k + 256)
            t = np.clip(((q[:, None, :] - a[None, s]) * ab[None, s]).sum(axis=2) / ab2[None, s], 0, 1)
            proj = a[None, s] + t[..., None] * ab[None, s]
            d = np.minimum(d, np.sqrt(((q[:, None, :] - proj) ** 2).sum(axis=2)).min(axis=1))
        best = np.minimum(best, d.reshape(x.shape) - p.width / 2)
    return best


# --- noise -----------------------------------------------------------------------------------------------------


def _hash(ix: np.ndarray, iy: np.ndarray, seed: int) -> np.ndarray:
    """Deterministic uniform [0, 1) per integer lattice point (integer mixing, same on every machine)."""
    m = np.uint64(0xFFFFFFFF)
    h = (ix.astype(np.int64).astype(np.uint64) * np.uint64(0x27D4EB2D)) & m
    h = (h ^ (iy.astype(np.int64).astype(np.uint64) * np.uint64(0x165667B1))) & m
    h = (h + np.uint64((seed * 0x9E3779B9) & 0xFFFFFFFF)) & m
    for mult in (0x2C1B3C6D, 0x297A2D39):
        h = (h ^ (h >> np.uint64(15))) & m
        h = (h * np.uint64(mult)) & m
    h = h ^ (h >> np.uint64(15))
    return h.astype(np.float64) / 4294967296.0


def value_noise(x: np.ndarray, y: np.ndarray, wavelength: float, seed: int, period: float | None = None) -> np.ndarray:
    """Smooth noise in [-1, 1] with features about `wavelength` metres apart; periodic in x and y if `period` is set."""
    n = max(1, round(period / wavelength)) if period else None
    if n:
        wavelength = period / n  # a whole number of cells per period
    gx, gy = x / wavelength, y / wavelength
    ix, iy = np.floor(gx), np.floor(gy)
    fx, fy = gx - ix, gy - iy
    ux, uy = fx * fx * fx * (fx * (fx * 6 - 15) + 10), fy * fy * fy * (fy * (fy * 6 - 15) + 10)

    def corner(dx: int, dy: int) -> np.ndarray:
        cx, cy = ix + dx, iy + dy
        if n:
            cx, cy = np.mod(cx, n), np.mod(cy, n)
        return _hash(cx, cy, seed)

    top = corner(0, 0) * (1 - ux) + corner(1, 0) * ux
    bottom = corner(0, 1) * (1 - ux) + corner(1, 1) * ux
    return 2 * (top * (1 - uy) + bottom * uy) - 1


def fbm(
    x: np.ndarray, y: np.ndarray, wavelength: float, seed: int, octaves: int = 3, period: float | None = None
) -> np.ndarray:
    """Fractal noise, roughly unit standard deviation."""
    total, amp, norm = np.zeros_like(x), 1.0, 0.0
    for o in range(octaves):
        total += amp * value_noise(x, y, wavelength / 2**o, seed + 1013 * o, period)
        norm += amp * amp
        amp *= 0.5
    return total / math.sqrt(norm) * 1.7  # value noise has std ~0.6 per octave


def smoothstep(e0: float, e1: float, v: np.ndarray) -> np.ndarray:
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# --- baking ----------------------------------------------------------------------------------------------------


class Source:
    """One photo texture at the bake resolution, in its four 90 deg rotations (for the stochastic tiling).

    Brightness changes across the photo (light falloff, a darker corner) repeat with the texture and show as a grid
    from above; they are removed (periodic high-pass, features larger than a quarter of the tile) and the large-scale
    variation comes from the noise masks instead.
    """

    def __init__(
        self, file: Path, size_m: float, mean: tuple[float, float, float], px_m: float, exact_px: int | None = None
    ) -> None:
        n = exact_px or max(8, round(size_m / px_m))
        img = Image.open(file).convert("RGB").resize((n, n), Image.LANCZOS)
        a = np.asarray(img, dtype=np.float64) / 255.0
        f = np.fft.fftfreq(n)
        sigma = n / 4
        low = np.exp(-2 * (np.pi * sigma) ** 2 * (f[:, None] ** 2 + f[None, :] ** 2))
        blur = np.real(np.fft.ifft2(np.fft.fft2(a, axes=(0, 1)) * low[..., None], axes=(0, 1)))
        a = (a - blur) + a.mean(axis=(0, 1))
        a = a * (np.array(mean) / a.mean(axis=(0, 1)))
        self.n = n
        self.stack = np.stack([np.rot90(a, k) for k in range(4)]).astype(np.float32)  # (rotation, row, col, rgb)

    def stochastic(self, gx: np.ndarray, gy: np.ndarray, seed: int, period_px: int | None = None) -> np.ndarray:
        """Colour at global pixel indices (gx east along columns, gy north along rows, both 1-D).

        The ground is cut into cells about 0.7 texture tiles wide; every cell shows the texture rotated by a random
        multiple of 90 deg and shifted randomly, and neighbouring cells blend over a narrow seam. No two neighbours
        repeat, so the texture's own features (a dark spot, a twig) no longer line up into a grid.
        """
        m = max(1, round(period_px / (0.7 * self.n))) if period_px else None
        cell = period_px / m if m else 0.7 * self.n
        out = 0.0
        cols, rows = gx / cell, gy / cell
        i0, j0 = np.floor(cols).astype(np.int64), np.floor(rows).astype(np.int64)
        sx, sy = smoothstep(0.5 - SEAM, 0.5 + SEAM, cols - i0), smoothstep(0.5 - SEAM, 0.5 + SEAM, rows - j0)
        ci = np.arange(i0.min(), i0.max() + 2)
        cj = np.arange(j0.min(), j0.max() + 2)
        ci_grid, cj_grid = np.meshgrid(np.mod(ci, m) if m else ci, np.mod(cj, m) if m else cj)
        k_tab = (_hash(ci_grid, cj_grid, seed) * 4).astype(np.int64)
        ox_tab = (_hash(ci_grid, cj_grid, seed + 1) * self.n).astype(np.int64)
        oy_tab = (_hash(ci_grid, cj_grid, seed + 2) * self.n).astype(np.int64)
        for di, wx in ((0, 1 - sx), (1, sx)):
            for dj, wy in ((0, 1 - sy), (1, sy)):
                a = (i0 + di - ci[0])[None, :]
                b = (j0 + dj - cj[0])[:, None]
                r = np.mod(-gy[:, None] + oy_tab[b, a], self.n)
                c = np.mod(gx[None, :] + ox_tab[b, a], self.n)
                out = out + self.stack[k_tab[b, a], r, c] * (wy[:, None] * wx[None, :])[..., None]
        return out


def _bilinear_up(coarse: np.ndarray, step: int, size: int) -> np.ndarray:
    """Upsample a field sampled every `step` px (with one extra sample at the far edge) to size x size px."""
    m = coarse.shape[0]
    pos = (np.arange(size) + 0.5) / step
    i0 = np.clip(np.floor(pos).astype(int), 0, m - 2)
    f = (pos - i0)[:, None]
    w = np.zeros((size, m))
    w[np.arange(size), i0] = 1 - f[:, 0]
    w[np.arange(size), i0 + 1] = f[:, 0]
    return w @ coarse @ w.T


class Baker:
    def __init__(self, w: World) -> None:
        self.w = w
        self.px = TILE_M / (TILE_PX - 2 * MARGIN_PX)
        self.src = {k: Source(TEXTURES / f, s, mean, self.px) for k, (f, s, mean) in SOURCES.items()}

    def _layer(self, name: str, gx: np.ndarray, gy: np.ndarray, period_px: int | None) -> np.ndarray:
        return self.src[name].stochastic(gx, gy, self.w.seed + 7919 * list(SOURCES).index(name), period_px)

    def fields(self, x: np.ndarray, y: np.ndarray, period: float | None = None, central: bool = True) -> dict:
        """Mixing weights and colour modulation at world points (computed on the coarse grid)."""
        s = self.w.seed
        f = {
            "light": smoothstep(-0.6, 0.9, fbm(x, y, 18.0, s + 101, 3, period)),  # lighter grass in broad areas
            "worn": 0.7 * smoothstep(0.9, 1.7, fbm(x, y, 7.0, s + 202, 4, period)),  # worn patches
            "tone": 0.09 * fbm(x, y, 30.0, s + 303, 3, period) + 0.04 * fbm(x, y, 4.0, s + 404, 2, period),
        }
        if central:
            edge = 0.25 * fbm(x, y, 1.5, s + 505, 2)
            d = path_distance(self.w.paths, x, y) + edge
            f["path"] = smoothstep(0.15, -0.25, d)
            f["path_edge"] = smoothstep(1.2, 0.0, d) * (1 - f["path"])  # trampled strip along the path
            litter = np.zeros_like(x)
            for t in self.w.trees:
                r = TREE_KINDS[t.kind].litter * t.scale
                litter = np.maximum(litter, smoothstep(r, 0.35 * r, np.hypot(x - t.x, y - t.y)))
            f["litter"] = 0.85 * litter * smoothstep(-0.6, 0.6, fbm(x, y, 2.0, s + 606, 3) + 1.5 * litter - 0.9)
        return f

    def bake(self, x0: float, y0: float, size_m: float, px_count: int, central: bool = True) -> np.ndarray:
        """RGB uint8 image of the square [x0, x0+size] x [y0, y0+size]; row 0 is the north edge."""
        step = NOISE_STEP
        m = px_count // step + 1
        cx = x0 + np.arange(m) * step * size_m / px_count
        cy = y0 + size_m - np.arange(m) * step * size_m / px_count
        grid_x, grid_y = np.meshgrid(cx, cy)
        period = None if central else size_m
        coarse = self.fields(grid_x, grid_y, period, central)

        def up(a: np.ndarray) -> np.ndarray:
            return _bilinear_up(a, step, px_count).astype(np.float32)

        px = size_m / px_count
        gx = round(x0 / px) + np.arange(px_count)
        gy = round((y0 + size_m) / px) - np.arange(px_count)
        per = None if central else px_count

        img = self._layer("cim", gx, gy, per)
        layers = [("cim_acik", 0.85 * up(coarse["light"]))]
        if central:  # patches would repeat with the periodic outer tile
            layers += [
                ("asinmis", up(coarse["worn"])),
                ("yaprak", up(coarse["litter"])),
                ("asinmis", 0.8 * up(coarse["path_edge"])),
                ("toprak", up(coarse["path"])),
            ]
        for name, weight in layers:
            if weight.max() > 0.002:  # most tiles have no path or tree
                img = _mix(img, self._layer(name, gx, gy, per), weight)
        img = img * (1 + up(coarse["tone"]))[..., None]
        return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def _mix(a: np.ndarray, b: np.ndarray, w: np.ndarray) -> np.ndarray:
    return a + (b - a) * w[..., None]


# --- output ----------------------------------------------------------------------------------------------------


def _quad_obj(x0: float, y0: float, x1: float, y1: float, uv0: float = 0.0, uv1: float = 1.0) -> str:
    return (
        f"v {x0:.3f} {y0:.3f} 0\nv {x1:.3f} {y0:.3f} 0\nv {x1:.3f} {y1:.3f} 0\nv {x0:.3f} {y1:.3f} 0\n"
        f"vt {uv0:.6f} {uv0:.6f}\nvt {uv1:.6f} {uv0:.6f}\nvt {uv1:.6f} {uv1:.6f}\nvt {uv0:.6f} {uv1:.6f}\nvn 0 0 1\n"
        "f 1/1/1 2/2/1 3/3/1\nf 1/1/1 3/3/1 4/4/1\n"
    )


def _ring_obj(w: World, tile: float) -> str:
    """Square ring between the central area and the outer edge; UV in tiles of `tile` metres (repeating)."""
    ax, ay = w.origin()
    bx, by = ax + w.size, ay + w.size
    h = w.outer / 2
    rects = [(-h, -h, h, ay), (-h, by, h, h), (-h, ay, ax, by), (bx, ay, h, by)]
    out, k = [], 0
    for x0, y0, x1, y1 in rects:
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            out.append(f"v {x:.3f} {y:.3f} 0\nvt {x / tile:.4f} {y / tile:.4f}\n")
        out.append(
            f"f {k + 1}/{k + 1}/1 {k + 2}/{k + 2}/1 {k + 3}/{k + 3}/1\n"
            f"f {k + 1}/{k + 1}/1 {k + 3}/{k + 3}/1 {k + 4}/{k + 4}/1\n"
        )
        k += 4
    return "vn 0 0 1\n" + "".join(out)


def _ground_visual(name: str, mesh: str, texture: str) -> str:
    return f"""      <visual name="{name}">
        <cast_shadows>false</cast_shadows>
        <geometry><mesh><uri>{mesh}</uri></mesh></geometry>
        <material>
          <ambient>1 1 1 1</ambient>
          <diffuse>1 1 1 1</diffuse>
          <specular>0.03 0.03 0.03 1</specular>
          <pbr><metal><albedo_map>{texture}</albedo_map><metalness>0</metalness><roughness>0.95</roughness></metal></pbr>
        </material>
      </visual>"""


def _tree_link(i: int, t: Tree) -> str:
    k = TREE_KINDS[t.kind]
    s = t.scale
    mesh = f"model://agaclar/{k.mesh}"
    tex = f"model://agaclar/{t.kind}/materials/textures"
    bark_tex, branch_tex = (
        (f"{tex}/bark_diffuse.png", f"{tex}/branch_diffuse.png")
        if t.kind == "mese"
        else (f"{tex}/bark_diffuse.png", f"{tex}/branch_2_diffuse.png")
    )
    scale = f"{s:.3f} {s:.3f} {s:.3f}"
    cc = [c * s for c in k.crown_centre]
    cr = [r * s for r in k.crown_radii]
    trunk_h = k.crown_base * s + 0.5 * cr[2]
    return f"""    <link name="agac_{i}">
      <pose>{t.x:.3f} {t.y:.3f} 0 0 0 {t.yaw:.4f}</pose>
      <collision name="govde">
        <pose>0 0 {trunk_h / 2:.3f} 0 0 0</pose>
        <geometry>
          <cylinder><radius>{k.trunk_radius * s:.3f}</radius><length>{trunk_h:.3f}</length></cylinder>
        </geometry>
      </collision>
      <collision name="tac">
        <pose>{cc[0]:.3f} {cc[1]:.3f} {cc[2]:.3f} 0 0 0</pose>
        <geometry><ellipsoid><radii>{cr[0]:.3f} {cr[1]:.3f} {cr[2]:.3f}</radii></ellipsoid></geometry>
      </collision>
      <visual name="dal">
        <geometry>
          <mesh><uri>{mesh}</uri><submesh><name>Branch</name></submesh><scale>{scale}</scale></mesh>
        </geometry>
        <material>
          <double_sided>true</double_sided>
          <diffuse>1 1 1 1</diffuse>
          <pbr><metal><albedo_map>{branch_tex}</albedo_map><metalness>0</metalness><roughness>0.9</roughness></metal></pbr>
        </material>
      </visual>
      <visual name="kabuk">
        <geometry>
          <mesh><uri>{mesh}</uri><submesh><name>Bark</name></submesh><scale>{scale}</scale></mesh>
        </geometry>
        <material>
          <diffuse>1 1 1 1</diffuse>
          <pbr><metal><albedo_map>{bark_tex}</albedo_map><metalness>0</metalness><roughness>0.95</roughness></metal></pbr>
        </material>
      </visual>
    </link>"""


def fingerprint(w: World) -> str:
    """Changes when the world file, this generator or a source texture changes."""
    h = hashlib.sha256(VERSION.encode())
    h.update(w.source.read_bytes())
    h.update(Path(__file__).read_bytes())
    for f, *_ in SOURCES.values():
        h.update(f.encode() + str((TEXTURES / f).stat().st_size).encode())
    return h.hexdigest()[:16]


def generate(w: World, log: Callable[[str], None] = print) -> Path:
    """Write models/<name>_cevre/ unless it is already up to date; returns the model folder."""
    out = w.model_dir
    stamp = out / ".tamam"
    fp = fingerprint(w)
    if stamp.is_file() and stamp.read_text().strip() == fp:
        log(f"Dünya '{w.name}' güncel: {out}")
        return out
    for d in ("meshes", "textures"):
        (out / d).mkdir(parents=True, exist_ok=True)
    stamp.unlink(missing_ok=True)
    baker = Baker(w)
    n = round(w.size / TILE_M)
    ax, ay = w.origin()
    visuals = []
    for j in range(n):
        for i in range(n):
            x0, y0 = ax + i * TILE_M, ay + j * TILE_M
            name = f"zemin_{i}_{j}"
            log(f"  zemin parçası {j * n + i + 1}/{n * n}")
            m = MARGIN_PX * baker.px
            img = baker.bake(x0 - m, y0 - m, TILE_M + 2 * m, TILE_PX)
            Image.fromarray(img).save(out / "textures" / f"{name}.jpg", quality=JPEG_QUALITY)
            uv = MARGIN_PX / TILE_PX
            (out / "meshes" / f"{name}.obj").write_text(_quad_obj(x0, y0, x0 + TILE_M, y0 + TILE_M, uv, 1 - uv))
            visuals.append(
                _ground_visual(name, f"model://{out.name}/meshes/{name}.obj", f"model://{out.name}/textures/{name}.jpg")
            )
    log("  dış zemin")
    Image.fromarray(baker_outer(w).bake(0.0, 0.0, OUTER_M, OUTER_PX, central=False)).save(
        out / "textures" / "zemin_dis.jpg", quality=JPEG_QUALITY
    )
    (out / "meshes" / "zemin_dis.obj").write_text(_ring_obj(w, OUTER_M))
    visuals.append(
        _ground_visual(
            "zemin_dis", f"model://{out.name}/meshes/zemin_dis.obj", f"model://{out.name}/textures/zemin_dis.jpg"
        )
    )

    trees = "\n".join(_tree_link(i, t) for i, t in enumerate(w.trees))
    (out / "model.sdf").write_text(
        f"""<?xml version="1.0"?>
<sdf version="1.9">
  <!-- Generated by tez/sim/araclar/dunya.py from worlds/{w.name}.yaml; do not edit (kur.sh makes it again). -->
  <model name="{out.name}">
    <static>true</static>
    <link name="zemin">
{chr(10).join(visuals)}
    </link>
{trees}
  </model>
</sdf>
""",
        encoding="utf-8",
    )
    (out / "model.config").write_text(
        f"""<?xml version="1.0"?>
<model>
  <name>{out.name}</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <description>Generated ground and trees of the {w.name} world (tez/sim/araclar/dunya.py). Textures:
    ambientCG and Poly Haven (CC0); trees: Gazebo Fuel OpenRobotics Oak tree / Pine Tree (CC0).
    See models/dokular/KAYNAK.md.</description>
</model>
""",
        encoding="utf-8",
    )
    stamp.write_text(fp + "\n")
    log(f"Dünya '{w.name}' üretildi: {out} ({n * n} zemin parçası, {len(w.trees)} ağaç)")
    return out


def baker_outer(w: World) -> Baker:
    """Baker for the periodic outer tile: every texture is resized to repeat a whole number of times in one tile."""
    b = Baker(w)
    divisors = [d for d in range(1, OUTER_PX + 1) if OUTER_PX % d == 0]
    for k, (f, s, mean) in SOURCES.items():
        reps = min(divisors, key=lambda d: abs(d - OUTER_M / s))
        b.src[k] = Source(TEXTURES / f, s, mean, OUTER_M / OUTER_PX, exact_px=OUTER_PX // reps)
    return b


def main() -> int:
    if len(sys.argv) != 2:
        print("Kullanım: dunya.py <dünya adı>   (tez/sim/worlds/<ad>.yaml)", file=sys.stderr)
        return 2
    missing = [f for f, *_ in SOURCES.values() if not (TEXTURES / f).is_file()]
    missing += [k for k in TREE_KINDS if not (TREE_MODELS / k / ".tamam").is_file()]
    if missing:
        print(f"Eksik dosyalar ({', '.join(missing)}). Önce: tez/sim/kur.sh", file=sys.stderr)
        return 2
    try:
        w = load(sys.argv[1])
    except ValueError as e:
        print(f"Dünya dosyası hatası: {e}", file=sys.stderr)
        return 2
    if w is None:
        print(f"{spec_path(sys.argv[1])} yok", file=sys.stderr)
        return 2
    generate(w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
