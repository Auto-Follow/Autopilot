"""Scenario file (YAML) -> target path, ground truth and the Gazebo world with the animated target.

Coordinates are Gazebo world coordinates: x east, y north [m], the drone takes off at (0, 0) facing east.
The target's position at any sim time is computed from the path, not read back from Gazebo: Gazebo Harmonic
animates actors only on the rendering side and does not publish their pose. senaryo.py --dogrula checks the
rendered target against this computation with an overhead camera (dogrulama.py).
"""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

import yuruyus

SIM_DIR = Path(__file__).resolve().parent.parent
ACTOR_HIP_HEIGHT = 1.0  # [m] actor origin above ground for the Mingfei actor meshes
WAYPOINT_STEP = 0.2  # [s] spacing of the actor waypoints while it moves or turns
FOREVER = 100000.0  # [s] last "stand" segment; the script loops (see models/insan/KAYNAK.md) but never gets there
MAX_SPEED = 6.0  # [m/s] fastest allowed target (a sprinting adult)
SUCCESS_KEYS = {
    "kadrajda_kalma_min": "hedefin kadrajda kaldığı süre oranı, en az [0..1]",
    "en_uzun_kayip_max_s": "hedefin kadrajdan çıktığı en uzun aralık, en fazla [s]",
    "yatay_mesafe_max_m": "dron ile hedef arasındaki yatay mesafe, en fazla [m]",
}
DRONE_MODES = {"tez", "bekle"}
BEHAVIOUR_KEYS = {"dogal", "tohum", "hiz_dalgalanma", "yol_sapmasi_m"}


@dataclass
class Scenario:
    name: str
    description: str
    world: str
    altitude: float
    drone_mode: str
    start: tuple[float, float]
    start_time: float
    end_wait: float
    track: yuruyus.Track | None = None  # target motion (yuruyus.plan)
    walk_end: float = 0.0  # sim time when the last step of the path ends
    behaviour: yuruyus.Behaviour = field(default_factory=yuruyus.Behaviour)
    success: dict[str, float] = field(default_factory=dict)
    source: Path | None = None

    @property
    def end_time(self) -> float:
        return self.walk_end + self.end_wait

    def truth(self, t: float) -> tuple[float, float, float, float, str]:
        """Target (x, y, yaw, speed, animation) at sim time t."""
        return self.track.at(t)

    def path_length(self) -> float:
        return self.track.length()

    def bounds(self) -> tuple[float, float, float, float]:
        """(x_min, x_max, y_min, y_max) of the path [m]."""
        return (
            float(self.track.x.min()),
            float(self.track.x.max()),
            float(self.track.y.min()),
            float(self.track.y.max()),
        )


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


def _check_keys(d: dict, allowed: set[str], where: str) -> None:
    unknown = set(d) - allowed
    if unknown:
        raise ValueError(f"{where}: bilinmeyen alan(lar) {sorted(unknown)}; geçerli alanlar: {sorted(allowed)}")


def find_scenario(name_or_path: str) -> Path:
    path = Path(name_or_path)
    if path.suffix in (".yaml", ".yml") and path.is_file():
        return path.resolve()
    path = SIM_DIR / "senaryolar" / f"{name_or_path}.yaml"
    if path.is_file():
        return path
    known = sorted(p.stem for p in (SIM_DIR / "senaryolar").glob("*.yaml"))
    raise FileNotFoundError(f"Senaryo bulunamadı: {name_or_path}. Mevcut senaryolar: {', '.join(known)}")


def load(name_or_path: str) -> Scenario:
    """Read and check a scenario file; every mistake is reported with the field it is in."""
    path = find_scenario(name_or_path)
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(d, dict):
        raise ValueError(f"{path.name}: YAML sözlük (alan: değer) olmalı")
    _check_keys(d, {"ad", "aciklama", "dunya", "drone", "hedef", "zamanlama", "basari"}, path.name)

    drone = d.get("drone") or {}
    _check_keys(drone, {"yukseklik_m", "mod"}, "drone")
    mode = drone.get("mod", "tez")
    if mode not in DRONE_MODES:
        raise ValueError(f"drone.mod: {sorted(DRONE_MODES)} olmalı, gelen: {mode!r}")

    target = d.get("hedef") or {}
    _check_keys(target, {"tur", "baslangic", "yol", "davranis"}, "hedef")
    if target.get("tur", "insan") != "insan":
        raise ValueError(f"hedef.tur: şimdilik sadece 'insan' var, gelen: {target.get('tur')!r}")

    timing = d.get("zamanlama") or {}
    _check_keys(timing, {"baslama_s", "son_bekleme_s"}, "zamanlama")

    world = d.get("dunya", "duz_alan")
    if not (SIM_DIR / "worlds" / f"{world}.sdf").is_file():
        raise ValueError(f"dunya: tez/sim/worlds/{world}.sdf yok")

    success = d.get("basari") or {}
    _check_keys(success, set(SUCCESS_KEYS), "basari")

    sc = Scenario(
        name=str(d.get("ad", path.stem)),
        description=str(d.get("aciklama", "")),
        world=world,
        altitude=_number(drone, "yukseklik_m", "drone", 10.0, minimum=2.0),
        drone_mode=mode,
        start=_point(target.get("baslangic"), "hedef.baslangic"),
        start_time=_number(timing, "baslama_s", "zamanlama", 60.0, minimum=20.0),
        end_wait=_number(timing, "son_bekleme_s", "zamanlama", 5.0),
        behaviour=_behaviour(target.get("davranis") or {}),
        success={k: _number(success, k, "basari") for k in success},
        source=path,
    )
    sc.track, sc.walk_end = yuruyus.plan(sc.start, sc.start_time, _steps(sc.start, target.get("yol")), sc.behaviour)
    return sc


def _behaviour(d: dict) -> yuruyus.Behaviour:
    _check_keys(d, BEHAVIOUR_KEYS, "hedef.davranis")
    default = yuruyus.Behaviour()
    natural = d.get("dogal", default.natural)
    if not isinstance(natural, bool):
        raise ValueError(f"hedef.davranis.dogal: true/false olmalı, gelen: {natural!r}")
    seed = d.get("tohum", default.seed)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError(f"hedef.davranis.tohum: tam sayı olmalı, gelen: {seed!r}")
    variation = _number(d, "hiz_dalgalanma", "hedef.davranis", default.speed_variation)
    if variation > 0.3:
        raise ValueError(f"hedef.davranis.hiz_dalgalanma: en fazla 0.3 (oran), gelen: {variation}")
    return yuruyus.Behaviour(natural, seed, variation, _number(d, "yol_sapmasi_m", "hedef.davranis", default.wander_m))


def _steps(start: tuple[float, float], path: object) -> list[tuple]:
    """hedef.yol -> [("move", (x, y), speed) | ("wait", seconds)], checked step by step."""
    if not isinstance(path, list) or not path:
        raise ValueError("hedef.yol: en az bir adım olmalı (liste)")
    steps: list[tuple] = []
    pos = start
    for i, step in enumerate(path):
        where = f"hedef.yol[{i}]"
        if not isinstance(step, dict):
            raise ValueError(f"{where}: {{nokta: [x, y], hiz_mps: v}} veya {{dur_s: s}} olmalı")
        if "dur_s" in step:
            _check_keys(step, {"dur_s"}, where)
            steps.append(("wait", _number(step, "dur_s", where, minimum=0.1)))
            continue
        _check_keys(step, {"nokta", "hiz_mps"}, where)
        target = _point(step.get("nokta"), f"{where}.nokta")
        speed = _number(step, "hiz_mps", where, minimum=0.1)
        if speed > MAX_SPEED:
            raise ValueError(f"{where}.hiz_mps: insan için en fazla {MAX_SPEED:.0f} m/s, gelen: {speed}")
        if np.hypot(target[0] - pos[0], target[1] - pos[1]) < 0.05:
            raise ValueError(f"{where}.nokta: bir önceki noktayla aynı yer")
        steps.append(("move", target, speed))
        pos = target
    return steps


def _runs(kind: np.ndarray) -> list[tuple[int, int]]:
    """[first, last] sample index of every stretch with one animation; neighbours share their boundary sample."""
    change = np.flatnonzero(kind[1:] != kind[:-1]) + 1
    starts = np.concatenate([[0], change])
    ends = np.concatenate([change, [len(kind) - 1]])
    return [(int(a), int(b)) for a, b in zip(starts, ends, strict=True) if b > a]


def actor_sdf(sc: Scenario) -> str:
    """The target as a Gazebo actor whose script follows sc.track (one trajectory per animation stretch)."""
    tr = sc.track
    z = ACTOR_HIP_HEIGHT
    trajectories = []
    pieces = [(a, b, str(tr.kind[a])) for a, b in _runs(tr.kind)]
    for i, (a, b, kind) in enumerate(pieces):
        span = slice(a, b + 1)
        still = kind == "stand" and max(np.ptp(tr.x[span]), np.ptp(tr.y[span]), np.ptp(tr.yaw[span])) < 1e-3
        # Gazebo fills a trajectory with a Catmull-Rom spline through its waypoints: a point every 0.2 s keeps it on
        # the track (only two end points made a 10 m walk run slow-fast-slow, up to 0.5 m off; 2026-10-11 test).
        step = max(1, round(WAYPOINT_STEP / yuruyus.DT))
        idx = [a, b] if still else sorted({*range(a, b, step), b})
        waypoints = [
            f"          <waypoint><time>{tr.t[k] - tr.t[a]:.4f}</time>"
            f"<pose>{tr.x[k]:.4f} {tr.y[k]:.4f} {z} 0 0 {tr.yaw[k]:.6f}</pose></waypoint>"
            for k in idx
        ]
        trajectories.append(
            f'        <trajectory id="{i}" type="{kind}">\n' + "\n".join(waypoints) + "\n        </trajectory>"
        )
    last = len(tr.t) - 1
    trajectories.append(
        f'        <trajectory id="{len(pieces)}" type="stand">\n'
        f"          <waypoint><time>0</time><pose>{tr.x[last]:.4f} {tr.y[last]:.4f} {z} 0 0 {tr.yaw[last]:.6f}</pose>"
        f"</waypoint>\n          <waypoint><time>{FOREVER:.0f}</time><pose>{tr.x[last]:.4f} {tr.y[last]:.4f} {z} 0 0 "
        f"{tr.yaw[last]:.6f}</pose></waypoint>\n        </trajectory>"
    )
    body = "\n".join(trajectories)
    return f"""
    <!-- Target written by tez/sim/araclar/hedef.py from {sc.source.name if sc.source else "scenario"} -->
    <actor name="hedef">
      <skin><filename>model://insan/meshes/walk.dae</filename></skin>
      <animation name="stand"><filename>model://insan/meshes/stand.dae</filename></animation>
      <!-- *_tez.dae: the same cycles starting with the feet together (kur.sh, araclar/animasyon.py) -->
      <animation name="walk"><filename>model://insan/meshes/walk_tez.dae</filename><interpolate_x>true</interpolate_x></animation>
      <animation name="run"><filename>model://insan/meshes/run_tez.dae</filename><interpolate_x>true</interpolate_x></animation>
      <script>
        <!-- loop=false freezes Gazebo while a camera renders the actor; the last segment lasts {FOREVER:.0f} s -->
        <loop>true</loop>
        <delay_start>0</delay_start>
        <auto_start>true</auto_start>
{body}
      </script>
    </actor>
"""


def write_world(sc: Scenario, out: Path, extra_sdf: str = "", shadows: bool = True) -> Path:
    """Scenario world = base world + target (+ extra models, e.g. the overhead check camera)."""
    world = (SIM_DIR / "worlds" / f"{sc.world}.sdf").read_text(encoding="utf-8")
    if "</world>" not in world:
        raise ValueError(f"{sc.world}.sdf: </world> bulunamadı")
    if not shadows:
        world = world.replace("<shadows>true</shadows>", "<shadows>false</shadows>")
        world = world.replace("<cast_shadows>true</cast_shadows>", "<cast_shadows>false</cast_shadows>")
    world = world.replace("</world>", actor_sdf(sc) + extra_sdf + "  </world>", 1)
    path = out / "dunya.sdf"
    path.write_text(world, encoding="utf-8")
    return path
