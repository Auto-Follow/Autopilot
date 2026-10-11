"""Scenario file (YAML) -> target path, ground truth and the Gazebo world with the animated target.

Coordinates are Gazebo world coordinates: x east, y north [m], the drone takes off at (0, 0) facing east.
The target's position at any sim time is computed from the path, not read back from Gazebo: Gazebo Harmonic
animates actors only on the rendering side and does not publish their pose. senaryo.py --dogrula checks the
rendered target against this computation with an overhead camera (dogrulama.py).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import dunya
import numpy as np
import yaml

import yuruyus

SIM_DIR = Path(__file__).resolve().parent.parent
ACTOR_HIP_HEIGHT = 1.0  # [m] the actor's root (hips) is put at the waypoint height (Mingfei actor meshes)
WAYPOINT_STEP = 0.2  # [s] spacing of the actor waypoints while it moves or turns
FOREVER = 100000.0  # [s] last "stand" segment; the script loops (see models/insan/KAYNAK.md) but never gets there
MAX_SPEED = 6.0  # [m/s] fastest allowed target (a sprinting adult)
SUCCESS_KEYS = {
    "kadrajda_kalma_min": "hedefin kadrajda kaldığı süre oranı, en az [0..1]",
    "gorunur_kalma_min": "hedefin gerçekten göründüğü (örtülmediği) süre oranı, en az [0..1]",
    "en_uzun_kayip_max_s": "hedefin kadrajdan çıktığı en uzun aralık, en fazla [s]",
    "yatay_mesafe_max_m": "dron ile hedef arasındaki yatay mesafe, en fazla [m]",
}
DRONE_MODES = {"tez", "bekle"}
BEHAVIOUR_KEYS = {"dogal", "tohum", "hiz_dalgalanma", "yol_sapmasi_m"}
PERSON_KEYS = {"baslangic", "yol", "davranis", "kiyafet"}
TARGET_LABEL = 1  # segmentation label of the target; the other people get OTHER_LABEL + i
OTHER_LABEL = 11

# Clothes of the Mingfei actor: the colours of its sweater, jeans and skin materials (diffuse = ambient, linear RGB)
COLOURS = {
    "yesil": (0.098, 0.255, 0.075),  # the model's own sweater
    "kot": (0.057, 0.092, 0.351),  # the model's own jeans
    "kirmizi": (0.50, 0.04, 0.04),
    "turuncu": (0.75, 0.25, 0.03),
    "sari": (0.70, 0.55, 0.08),
    "mavi": (0.06, 0.16, 0.50),
    "lacivert": (0.03, 0.04, 0.15),
    "mor": (0.25, 0.07, 0.35),
    "beyaz": (0.78, 0.78, 0.76),
    "gri": (0.25, 0.25, 0.27),
    "siyah": (0.03, 0.03, 0.035),
    "kahverengi": (0.25, 0.14, 0.06),
    "bej": (0.55, 0.47, 0.33),
    "haki": (0.30, 0.30, 0.15),
}
SKINS = {
    "acik": (0.90, 0.68, 0.55),
    "orta": (0.80, 0.551, 0.394),
    "esmer": (0.55, 0.35, 0.23),
    "koyu": (0.28, 0.17, 0.11),
}
MATERIALS = {"ust": "sweater-green-effect", "alt": "jeans-blue-effect", "ten": "skin-mat-effect"}


@dataclass(frozen=True)
class Clothes:
    top: str = "yesil"
    bottom: str = "kot"
    skin: str = "orta"

    def skin_file(self) -> str:
        """File name of the actor mesh with these colours (models/insan/meshes; made by write_world)."""
        if self == Clothes():
            return "walk.dae"
        return f"giysi_{self.top}_{self.bottom}_{self.skin}.dae"


@dataclass
class Person:
    """Someone else in the scene: walks their own path, not the target (a distractor for the vision code)."""

    start: tuple[float, float]
    track: yuruyus.Track
    walk_end: float
    clothes: Clothes = field(default_factory=Clothes)


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
    clothes: Clothes = field(default_factory=Clothes)  # of the target
    others: list[Person] = field(default_factory=list)

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
    _check_keys(d, {"ad", "aciklama", "dunya", "drone", "hedef", "diger_insanlar", "zamanlama", "basari"}, path.name)

    drone = d.get("drone") or {}
    _check_keys(drone, {"yukseklik_m", "mod"}, "drone")
    mode = drone.get("mod", "tez")
    if mode not in DRONE_MODES:
        raise ValueError(f"drone.mod: {sorted(DRONE_MODES)} olmalı, gelen: {mode!r}")

    target = d.get("hedef") or {}
    _check_keys(target, PERSON_KEYS | {"tur"}, "hedef")
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
        clothes=_clothes(target.get("kiyafet") or {}, "hedef.kiyafet"),
    )
    sc.track, sc.walk_end = yuruyus.plan(
        sc.start, sc.start_time, _steps(sc.start, target.get("yol"), "hedef.yol"), sc.behaviour
    )
    others = d.get("diger_insanlar") or []
    if not isinstance(others, list):
        raise ValueError("diger_insanlar: liste olmalı")
    for i, o in enumerate(others):
        sc.others.append(_person(o, f"diger_insanlar[{i}]", sc.start_time))
    _check_trees(sc)
    return sc


def _person(d: object, where: str, start_time: float) -> Person:
    if not isinstance(d, dict):
        raise ValueError(f"{where}: {{baslangic: [x, y], yol: [...]}} olmalı")
    _check_keys(d, PERSON_KEYS | {"gecikme_s"}, where)
    start = _point(d.get("baslangic"), f"{where}.baslangic")
    begin = start_time + _number(d, "gecikme_s", where, 0.0)
    behaviour = _behaviour(d.get("davranis") or {}, f"{where}.davranis")
    track, end = yuruyus.plan(start, begin, _steps(start, d.get("yol"), f"{where}.yol"), behaviour)
    return Person(start, track, end, _clothes(d.get("kiyafet") or {}, f"{where}.kiyafet"))


def _clothes(d: object, where: str) -> Clothes:
    if not isinstance(d, dict):
        raise ValueError(f"{where}: {{ust: renk, alt: renk, ten: ton}} olmalı")
    _check_keys(d, set(MATERIALS), where)
    default = Clothes()
    top, bottom, skin = d.get("ust", default.top), d.get("alt", default.bottom), d.get("ten", default.skin)
    for key, value, allowed in (("ust", top, COLOURS), ("alt", bottom, COLOURS), ("ten", skin, SKINS)):
        if value not in allowed:
            raise ValueError(f"{where}.{key}: {sorted(allowed)} olmalı, gelen: {value!r}")
    return Clothes(top, bottom, skin)


def _check_trees(sc: Scenario) -> None:
    """Nobody may walk through a tree trunk of the world (actors do not collide; it would look like a ghost)."""
    spec = dunya.load(sc.world)
    if spec is None or not spec.trees:
        return
    people = [("hedef", sc.track)] + [(f"diger_insanlar[{i}]", o.track) for i, o in enumerate(sc.others)]
    for who, tr in people:
        for t in spec.trees:
            d = np.hypot(tr.x - t.x, tr.y - t.y)
            k = int(np.argmin(d))
            if d[k] < t.trunk_radius + 0.3:
                raise ValueError(
                    f"{who}: yol {tr.t[k]:.0f} s'de ({tr.x[k]:.1f}, {tr.y[k]:.1f}) noktasında bir ağaç "
                    f"gövdesinden geçiyor ({t.kind}, ({t.x:.1f}, {t.y:.1f})); yolu değiştirin"
                )


def _behaviour(d: dict, where: str = "hedef.davranis") -> yuruyus.Behaviour:
    _check_keys(d, BEHAVIOUR_KEYS, where)
    default = yuruyus.Behaviour()
    natural = d.get("dogal", default.natural)
    if not isinstance(natural, bool):
        raise ValueError(f"{where}.dogal: true/false olmalı, gelen: {natural!r}")
    seed = d.get("tohum", default.seed)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError(f"{where}.tohum: tam sayı olmalı, gelen: {seed!r}")
    variation = _number(d, "hiz_dalgalanma", where, default.speed_variation)
    if variation > 0.3:
        raise ValueError(f"{where}.hiz_dalgalanma: en fazla 0.3 (oran), gelen: {variation}")
    return yuruyus.Behaviour(natural, seed, variation, _number(d, "yol_sapmasi_m", where, default.wander_m))


def _steps(start: tuple[float, float], path: object, name: str = "hedef.yol") -> list[tuple]:
    """yol -> [("move", (x, y), speed) | ("wait", seconds)], checked step by step."""
    if not isinstance(path, list) or not path:
        raise ValueError(f"{name}: en az bir adım olmalı (liste)")
    steps: list[tuple] = []
    pos = start
    for i, step in enumerate(path):
        where = f"{name}[{i}]"
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


def actor_sdf(name: str, tr: yuruyus.Track, clothes: Clothes, label: int, first: int = 0) -> tuple[str, int]:
    """One person as a Gazebo actor whose script follows the track (one trajectory per animation stretch).

    `first` is the first free animation file spelling (see below); returns the SDF and the next free one.
    """
    z = ACTOR_HIP_HEIGHT
    trajectories, animations = [], []
    pieces = [(a, b, str(tr.kind[a])) for a, b in _runs(tr.kind)]
    spelling = first
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
        anim = kind
        if kind != "stand":
            # gz-sim 8 turns <interpolate_x> (legs locked to the distance walked) on only for the first trajectory
            # that uses an animation file (SceneManager.cc, animInterpolateCheck, shared by all actors); later ones
            # would play by time and the feet would slide. Every moving trajectory of every actor gets its own
            # spelling of the file path.
            anim = f"{kind}_{i}"
            path = "./" * spelling + f"{kind}_tez.dae"
            spelling += 1
            animations.append(
                f'      <animation name="{anim}"><filename>model://insan/meshes/{path}</filename>'
                "<interpolate_x>true</interpolate_x></animation>"
            )
        trajectories.append(
            f'        <trajectory id="{i}" type="{anim}">\n' + "\n".join(waypoints) + "\n        </trajectory>"
        )
    last = len(tr.t) - 1
    end_pose = f"{tr.x[last]:.4f} {tr.y[last]:.4f} {z} 0 0 {tr.yaw[last]:.6f}"
    trajectories.append(
        f'        <trajectory id="{len(pieces)}" type="stand">\n'
        f"          <waypoint><time>0</time><pose>{end_pose}</pose></waypoint>\n"
        f"          <waypoint><time>{FOREVER:.0f}</time><pose>{end_pose}</pose></waypoint>\n        </trajectory>"
    )
    body = "\n".join(trajectories)
    anims = "\n".join(animations)
    sdf = f"""
    <actor name="{name}">
      <skin><filename>model://insan/meshes/{clothes.skin_file()}</filename></skin>
      <animation name="stand"><filename>model://insan/meshes/stand.dae</filename></animation>
      <!-- moving trajectories use walk_tez.dae / run_tez.dae: the same cycles, starting with the feet together and
           with the hip travel scaled to the real stride (kur.sh, araclar/animasyon.py) -->
{anims}
      <script>
        <!-- loop=false freezes Gazebo while a camera renders the actor; the last segment lasts {FOREVER:.0f} s -->
        <loop>true</loop>
        <delay_start>0</delay_start>
        <auto_start>true</auto_start>
{body}
      </script>
      <!-- label seen by segmentation cameras: 0 background, {TARGET_LABEL} target, {OTHER_LABEL}+ other people -->
      <plugin filename="gz-sim-label-system" name="gz::sim::systems::Label"><label>{label}</label></plugin>
    </actor>
"""
    return sdf, spelling


def actors_sdf(sc: Scenario) -> str:
    """The target ("hedef") and the other people ("insan_1", ...) of the scenario."""
    src = sc.source.name if sc.source else "scenario"
    text, spelling = actor_sdf("hedef", sc.track, sc.clothes, TARGET_LABEL)
    parts = [f"\n    <!-- People written by tez/sim/araclar/hedef.py from {src} -->", text]
    for i, o in enumerate(sc.others, start=1):
        text, spelling = actor_sdf(f"insan_{i}", o.track, o.clothes, OTHER_LABEL + i - 1, spelling)
        parts.append(text)
    return "".join(parts)


def make_skin(clothes: Clothes) -> None:
    """Write the actor mesh with these clothes (a copy of walk.dae with other material colours) if missing."""
    meshes = SIM_DIR / "models" / "insan" / "meshes"
    out = meshes / clothes.skin_file()
    if out.is_file():
        return
    text = (meshes / "walk.dae").read_text(encoding="utf-8")
    colours = {"ust": COLOURS[clothes.top], "alt": COLOURS[clothes.bottom], "ten": SKINS[clothes.skin]}
    for key, effect in MATERIALS.items():
        start = text.index(f'<effect id="{effect}">')
        end = text.index("</effect>", start)
        rgb = " ".join(f"{c:.4f}" for c in colours[key])
        block = re.sub(r'(<color sid="(?:ambient|diffuse)">)[^<]*(</color>)', rf"\g<1>{rgb} 1\g<2>", text[start:end])
        text = text[:start] + block + text[end:]
    tmp = out.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(out)


def write_world(sc: Scenario, out: Path, extra_sdf: str = "", shadows: bool = True) -> Path:
    """Scenario world = base world + target (+ extra models, e.g. the overhead check camera)."""
    world = (SIM_DIR / "worlds" / f"{sc.world}.sdf").read_text(encoding="utf-8")
    if "</world>" not in world:
        raise ValueError(f"{sc.world}.sdf: </world> bulunamadı")
    if not shadows:
        world = world.replace("<shadows>true</shadows>", "<shadows>false</shadows>")
        world = world.replace("<cast_shadows>true</cast_shadows>", "<cast_shadows>false</cast_shadows>")
    for clothes in {sc.clothes, *(o.clothes for o in sc.others)}:
        make_skin(clothes)
    world = world.replace("</world>", actors_sdf(sc) + extra_sdf + "  </world>", 1)
    path = out / "dunya.sdf"
    path.write_text(world, encoding="utf-8")
    return path
