"""Scenario file (YAML) -> target path, ground truth and the Gazebo world with the animated target.

Coordinates are Gazebo world coordinates: x east, y north [m], the drone takes off at (0, 0) facing east.
The target's position at any sim time is computed from the path, not read back from Gazebo: Gazebo Harmonic
animates actors only on the rendering side and does not publish their pose. senaryo.py --dogrula checks the
rendered target against this computation with an overhead camera.
"""

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SIM_DIR = Path(__file__).resolve().parent.parent
RUN_SPEED = 2.0  # [m/s] above this the target uses the run animation instead of walk
ACTOR_HIP_HEIGHT = 1.0  # [m] actor origin above ground for the Mingfei actor meshes
WAYPOINT_STEP = 0.2  # [s] spacing of the actor waypoints along a walk/run segment
FOREVER = 100000.0  # [s] last "stand" segment; the script loops (see models/insan/KAYNAK.md) but never gets there
SUCCESS_KEYS = {
    "kadrajda_kalma_min": "hedefin kadrajda kaldığı süre oranı, en az [0..1]",
    "en_uzun_kayip_max_s": "hedefin kadrajdan çıktığı en uzun aralık, en fazla [s]",
    "yatay_mesafe_max_m": "dron ile hedef arasındaki yatay mesafe, en fazla [m]",
}
DRONE_MODES = {"tez", "bekle"}
OVERHEAD_HFOV = 1.2  # [rad] verification camera (--dogrula)
OVERHEAD_SIZE = (1600, 1200)  # [px]


@dataclass
class Segment:
    t0: float  # [s] sim time
    t1: float
    kind: str  # Gazebo animation: stand | walk | run
    p0: tuple[float, float]
    p1: tuple[float, float]
    yaw: float  # [rad] heading in the world frame (0 = east)

    @property
    def speed(self) -> float:
        return math.dist(self.p0, self.p1) / (self.t1 - self.t0) if self.kind != "stand" else 0.0


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
    segments: list[Segment] = field(default_factory=list)
    success: dict[str, float] = field(default_factory=dict)
    source: Path | None = None

    @property
    def walk_end(self) -> float:
        """Sim time when the last movement ends (the final stand segment excluded)."""
        return self.segments[-2].t1 if len(self.segments) > 1 else self.start_time

    @property
    def end_time(self) -> float:
        return self.walk_end + self.end_wait

    def truth(self, t: float) -> tuple[float, float, float, float, str]:
        """Target (x, y, yaw, speed, animation) at sim time t."""
        for s in self.segments:
            if t < s.t1:
                f = 0.0 if s.kind == "stand" else max(0.0, (t - s.t0) / (s.t1 - s.t0))
                x = s.p0[0] + f * (s.p1[0] - s.p0[0])
                y = s.p0[1] + f * (s.p1[1] - s.p0[1])
                return x, y, s.yaw, s.speed, s.kind
        last = self.segments[-1]
        return last.p1[0], last.p1[1], last.yaw, 0.0, "stand"

    def path_length(self) -> float:
        return sum(math.dist(s.p0, s.p1) for s in self.segments)


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
    _check_keys(target, {"tur", "baslangic", "yol"}, "hedef")
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
        success={k: _number(success, k, "basari") for k in success},
        source=path,
    )
    sc.segments = _segments(sc, target.get("yol") or [])
    return sc


def _segments(sc: Scenario, path: list) -> list[Segment]:
    if not isinstance(path, list) or not path:
        raise ValueError("hedef.yol: en az bir adım olmalı (liste)")
    # Moves first, so the waiting target already faces its first direction.
    pos, t = sc.start, sc.start_time
    first_move = next((step for step in path if isinstance(step, dict) and "nokta" in step), None)
    yaw = 0.0
    if first_move is not None:
        p = _point(first_move["nokta"], "hedef.yol[...].nokta")
        yaw = math.atan2(p[1] - pos[1], p[0] - pos[0])
    segments = [Segment(0.0, t, "stand", pos, pos, yaw)]
    for i, step in enumerate(path):
        where = f"hedef.yol[{i}]"
        if not isinstance(step, dict):
            raise ValueError(f"{where}: {{nokta: [x, y], hiz_mps: v}} veya {{dur_s: s}} olmalı")
        if "dur_s" in step:
            _check_keys(step, {"dur_s"}, where)
            duration = _number(step, "dur_s", where, minimum=0.1)
            segments.append(Segment(t, t + duration, "stand", pos, pos, yaw))
            t += duration
            continue
        _check_keys(step, {"nokta", "hiz_mps"}, where)
        target = _point(step.get("nokta"), f"{where}.nokta")
        speed = _number(step, "hiz_mps", where, minimum=0.1)
        if speed > 6.0:
            raise ValueError(f"{where}.hiz_mps: insan için en fazla 6 m/s, gelen: {speed}")
        distance = math.dist(pos, target)
        if distance < 0.05:
            raise ValueError(f"{where}.nokta: bir önceki noktayla aynı yer")
        yaw = math.atan2(target[1] - pos[1], target[0] - pos[0])
        duration = distance / speed
        segments.append(Segment(t, t + duration, "run" if speed > RUN_SPEED else "walk", pos, target, yaw))
        pos, t = target, t + duration
    segments.append(Segment(t, t + FOREVER, "stand", pos, pos, yaw))
    return segments


def actor_sdf(sc: Scenario) -> str:
    trajectories = []
    z = ACTOR_HIP_HEIGHT
    for i, s in enumerate(sc.segments):
        # Gazebo fills a trajectory with a Catmull-Rom spline: with only its two end points a 10 m walk runs
        # slow-fast-slow and is up to 0.5 m off the straight line in time (2026-10-11 test). Evenly spaced points
        # on a line make the spline linear between them, which leaves a ~1 cm error in the first and last step.
        n = 1 if s.kind == "stand" else max(1, math.ceil((s.t1 - s.t0) / WAYPOINT_STEP))
        waypoints = []
        for k in range(n + 1):
            f = k / n
            x = s.p0[0] + f * (s.p1[0] - s.p0[0])
            y = s.p0[1] + f * (s.p1[1] - s.p0[1])
            waypoints.append(
                f"          <waypoint><time>{f * (s.t1 - s.t0):.4f}</time>"
                f"<pose>{x:.4f} {y:.4f} {z} 0 0 {s.yaw:.6f}</pose></waypoint>"
            )
        trajectories.append(
            f'        <trajectory id="{i}" type="{s.kind}">\n' + "\n".join(waypoints) + "\n        </trajectory>"
        )
    body = "\n".join(trajectories)
    return f"""
    <!-- Target written by tez/sim/araclar/hedef.py from {sc.source.name if sc.source else "scenario"} -->
    <actor name="hedef">
      <skin><filename>model://insan/meshes/walk.dae</filename></skin>
      <animation name="stand"><filename>model://insan/meshes/stand.dae</filename></animation>
      <animation name="walk"><filename>model://insan/meshes/walk.dae</filename><interpolate_x>true</interpolate_x></animation>
      <animation name="run"><filename>model://insan/meshes/run.dae</filename><interpolate_x>true</interpolate_x></animation>
      <script>
        <!-- loop=false freezes Gazebo while a camera renders the actor; the last segment lasts {FOREVER:.0f} s -->
        <loop>true</loop>
        <delay_start>0</delay_start>
        <auto_start>true</auto_start>
{body}
      </script>
    </actor>
"""


def overhead_camera(sc: Scenario, height: float) -> tuple[str, tuple[float, float, float]]:
    """Static nadir camera over the target path (verification only). Image up = +x (east), image right = -y."""
    xs = [p for s in sc.segments for p in (s.p0[0], s.p1[0])]
    ys = [p for s in sc.segments for p in (s.p0[1], s.p1[1])]
    pos = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, height)
    sdf = f"""
    <model name="dogrulama_kamerasi">
      <static>true</static>
      <pose>{pos[0]:.3f} {pos[1]:.3f} {height:.3f} 0 1.570796 0</pose>
      <link name="link">
        <sensor name="tepe" type="camera">
          <topic>/dogrulama/image</topic>
          <always_on>1</always_on>
          <update_rate>10</update_rate>
          <camera>
            <horizontal_fov>{OVERHEAD_HFOV}</horizontal_fov>
            <image><width>{OVERHEAD_SIZE[0]}</width><height>{OVERHEAD_SIZE[1]}</height></image>
            <clip><near>1</near><far>{height + 20:.0f}</far></clip>
          </camera>
        </sensor>
      </link>
    </model>
"""
    return sdf, pos


def overhead_height(sc: Scenario) -> float:
    """Height [m] at which the overhead camera sees the whole path with a 4 m margin."""
    xs = [p for s in sc.segments for p in (s.p0[0], s.p1[0])]
    ys = [p for s in sc.segments for p in (s.p0[1], s.p1[1])]
    half_h = math.tan(OVERHEAD_HFOV / 2)  # horizontal image axis covers y
    half_v = half_h * OVERHEAD_SIZE[1] / OVERHEAD_SIZE[0]  # vertical image axis covers x
    need_x = (max(xs) - min(xs)) / 2 + 4
    need_y = (max(ys) - min(ys)) / 2 + 4
    return max(25.0, need_x / half_v, need_y / half_h)


def write_world(sc: Scenario, out: Path, verify: bool) -> tuple[Path, tuple[float, float, float] | None]:
    """Scenario world = base world + target (+ overhead camera, no shadows when verifying)."""
    base = (SIM_DIR / "worlds" / f"{sc.world}.sdf").read_text(encoding="utf-8")
    if "</world>" not in base:
        raise ValueError(f"{sc.world}.sdf: </world> bulunamadı")
    extra = actor_sdf(sc)
    camera_pos = None
    if verify:
        cam_sdf, camera_pos = overhead_camera(sc, overhead_height(sc))
        extra += cam_sdf
        # Shadows shift the measured centroid of the target by ~0.5 m (2026-10-11 test)
        base = re.sub(r"<shadows>true</shadows>", "<shadows>false</shadows>", base)
        base = re.sub(r"<cast_shadows>true</cast_shadows>", "<cast_shadows>false</cast_shadows>", base)
    world = base.replace("</world>", extra + "  </world>", 1)
    path = out / "dunya.sdf"
    path.write_text(world, encoding="utf-8")
    return path, camera_pos
