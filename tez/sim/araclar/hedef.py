"""Scenario file (YAML) -> target path, ground truth and the Gazebo world with the animated target.

Coordinates are Gazebo world coordinates: x east, y north [m], the drone takes off at (0, 0) facing east.
The target's position at any sim time is computed from the path, not read back from Gazebo: Gazebo Harmonic
animates actors only on the rendering side and does not publish their pose. senaryo.py --dogrula checks the
rendered target against this computation with an overhead camera (dogrulama.py).
"""

import copy
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import dunya
import numpy as np
import yaml

import kusurlar
import parametreler
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
# Faz A blocks of spec 2026-11-10-m06-sim-ortami ("Senaryo alanları"). takip.kaynak: who steers the drone after
# takeoff: yok = open loop (PX4 "Hold"), follow_me = stock Follow Me ("Follow Target"), tez_los = an external mode
# chosen by takip.mod_adi. takip.los: where the line of sight sent as TEZ_LOS comes from, (i) the model's box or
# (ii) the referee (kayit.py los_govde).
TRACKING_SOURCES = ("yok", "follow_me", "tez_los")
LOS_SOURCES = ("model", "hakem")
TRACKING_KEYS = {"kaynak", "mod_adi", "los", "px4_baslat", "px4_parametreleri"}
# YAML key -> attribute of Detection / Delay; the command line flag that replaces it, if there is one
DETECTION_FIELDS = {"etkin": "enabled", "model": "model", "imgsz": "imgsz", "conf": "conf", "sinif": "class_name"}
DETECTION_FIELDS |= {"cekirdek": "cores"}
DELAY_FIELDS = {"ek_ms": "extra_ms", "titresim_ms": "jitter_ms", "saat_ofset_ms": "clock_offset_ms"}
DELAY_FIELDS |= {"saat_kayma_ppm": "clock_drift_ppm"}
FLAGS = {"algilama.model": "--model", "algilama.imgsz": "--imgsz", "algilama.conf": "--conf"}
FLAGS |= {"algilama.sinif": "--sinif", "gecikme.ek_ms": "--gecikme-ms"}
TAKEOFF_PARAM = "MIS_TAKEOFF_ALT"  # px4_baglanti.takeoff sets it from drone.yukseklik_m
# Follow Me's height above home (spec 6): drone.yukseklik_m unless the scenario or --param gives it; the 45 deg camera
# keeps the person in view only if height and distance change together (camera report, 6/8 failed every time)
FOLLOW_HEIGHT_PARAM = "FLW_TGT_HT"
FOLLOW_HEIGHT_SOURCE = "drone.yukseklik_m (follow_me)"
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


@dataclass(frozen=True)
class Tracking:
    """takip: who steers the drone after takeoff and what goes to PX4."""

    source: str = "yok"  # TRACKING_SOURCES
    mode_name: str | None = None  # AVAILABLE_MODES name of the mode tez_los switches to (required there)
    los: str | None = "model"  # LOS_SOURCES; None = no LOS (model off and nothing to steer, source "yok")
    px4_start: tuple[str, ...] = ()  # PX4 commands after start: takip.px4_baslat, then --px4-baslat
    px4_params: tuple[parametreler.Param, ...] = ()  # takip.px4_parametreleri, then --param (load order)


@dataclass(frozen=True)
class Detection:
    """algilama: the person detector that runs on the drone camera's frames."""

    enabled: bool = True  # false: no model process (--modelsiz)
    model: Path | None = None  # None: the default model file (~/auto-follow-modeller/, task group 3)
    imgsz: int | None = None  # [px] model input size; None: the training size stored in the .pt
    conf: float = 0.25  # (0..1] confidence threshold
    class_name: str | int | None = None  # class name or number; None: the class named "person" (any case)
    cores: int = 4  # torch threads; the rest of the CPU stays with Gazebo and PX4


@dataclass(frozen=True)
class Delay:
    """gecikme: artificial delay on the capture -> PX4 path and the clock model of the sent time stamps."""

    extra_ms: float = 0.0  # [ms]
    jitter_ms: float = 0.0  # [ms] uniform, seeded
    clock_offset_ms: float = 0.0  # [ms]
    clock_drift_ppm: float = 0.0  # [ppm]


@dataclass(frozen=True)
class Video:
    mp4: bool = True  # kosu.mp4 after the run (--videosuz: false)
    qgc: bool = False  # live H.264 RTP to QGroundControl (--qgc)
    keep_frames: bool = False  # keep the MP4's frames (--kareleri-sakla; command line only)


@dataclass(frozen=True)
class CommandLine:
    """senaryo.py options that replace the scenario's values; None / False / empty keeps the YAML value."""

    model: str | None = None  # --model
    imgsz: int | None = None  # --imgsz
    conf: float | None = None  # --conf
    class_name: str | None = None  # --sinif (name or number)
    no_model: bool = False  # --modelsiz
    source: str | None = None  # --takip
    mode_name: str | None = None  # --mod-adi
    los: str | None = None  # --los
    params: tuple[str, ...] = ()  # --param NAME=VALUE, loaded after takip.px4_parametreleri
    px4_start: tuple[str, ...] = ()  # --px4-baslat, run after takip.px4_baslat
    delay_ms: float | None = None  # --gecikme-ms (gecikme.ek_ms)
    qgc: bool = False  # --qgc
    no_video: bool = False  # --videosuz
    keep_frames: bool = False  # --kareleri-sakla


@dataclass
class Scenario:
    name: str
    description: str
    world: str
    altitude: float
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
    tracking: Tracking = field(default_factory=Tracking)
    detection: Detection = field(default_factory=Detection)
    delay: Delay = field(default_factory=Delay)
    defects: dict = field(default_factory=dict)  # kusurlar (kusurlar.py; all off in Faz A)
    video: Video = field(default_factory=Video)

    @property
    def tracking_source(self) -> str:
        return self.tracking.source

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
    if not math.isfinite(value):
        raise ValueError(f"{where}.{key}: sonlu bir sayı olmalı, gelen: {value}")
    if value < minimum:
        raise ValueError(f"{where}.{key}: en az {minimum} olmalı, gelen: {value}")
    return float(value)


def _integer(d: dict, key: str, where: str, default: int | None = None, minimum: int = 0) -> int:
    value = d.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{where}.{key}: tam sayı olmalı, gelen: {value!r}")
    if value < minimum:
        raise ValueError(f"{where}.{key}: en az {minimum} olmalı, gelen: {value}")
    return value


def _flag(d: dict, key: str, where: str, default: bool) -> bool:
    value = d.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{where}.{key}: true/false olmalı, gelen: {value!r}")
    return value


def _block(d: dict, key: str, example: str) -> dict:
    """A block of the scenario (absent or empty = {}); anything but a dict is refused with an example."""
    value = d.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{key}: sözlük (alan: değer) olmalı, ör. {key}: {example}; gelen: {value!r}")
    return value


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


def load(name_or_path: str, command_line: CommandLine | None = None) -> Scenario:
    """Read and check a scenario file, with senaryo.py's options in place of the YAML values they replace; every
    mistake is reported with the field it is in."""
    path = find_scenario(name_or_path)
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(d, dict):
        raise ValueError(f"{path.name}: YAML sözlük (alan: değer) olmalı")
    top_keys = {"ad", "aciklama", "dunya", "drone", "takip", "hedef", "diger_insanlar", "zamanlama", "basari"}
    top_keys |= {"algilama", "gecikme", "kusurlar", "video"}
    _check_keys(d, top_keys, path.name)
    cli = command_line or CommandLine()
    d = _with_command_line(d, cli)

    drone = d.get("drone") or {}
    if "mod" in drone:
        raise ValueError(
            "drone.mod: kaldırıldı (iskelet tez modu yok); yerine takip.kaynak yazın, ör. takip: {kaynak: yok} "
            "= dron PX4 Hold'da bekler"
        )
    _check_keys(drone, {"yukseklik_m"}, "drone")
    altitude = _number(drone, "yukseklik_m", "drone", 10.0, minimum=2.0)
    detection = read_detection(_block(d, "algilama", "{etkin: true, conf: 0.25}"))
    tracking = _tracking(_block(d, "takip", "{kaynak: yok}"), detection.enabled, cli, altitude)

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
        altitude=altitude,
        start=_point(target.get("baslangic"), "hedef.baslangic"),
        start_time=_number(timing, "baslama_s", "zamanlama", 60.0, minimum=20.0),
        end_wait=_number(timing, "son_bekleme_s", "zamanlama", 5.0),
        behaviour=_behaviour(target.get("davranis") or {}),
        success={k: _number(success, k, "basari") for k in success},
        source=path,
        clothes=_clothes(target.get("kiyafet") or {}, "hedef.kiyafet"),
        tracking=tracking,
        detection=detection,
        delay=_delay(_block(d, "gecikme", "{ek_ms: 0}")),
        defects=_defects(_block(d, "kusurlar", "{}")),
        video=_video(_block(d, "video", "{mp4: true, qgc: false}"), cli.keep_frames),
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


def _with_command_line(d: dict, cli: CommandLine) -> dict:
    """The scenario with the command line's values put into its blocks; they are checked afterwards like YAML values
    (--param and --px4-baslat add to the scenario's lists instead, see _tracking)."""
    values = {
        ("takip", "kaynak"): cli.source,
        ("takip", "mod_adi"): cli.mode_name,
        ("takip", "los"): cli.los,
        ("algilama", "etkin"): False if cli.no_model else None,
        ("algilama", "model"): cli.model,
        ("algilama", "imgsz"): cli.imgsz,
        ("algilama", "conf"): cli.conf,
        ("algilama", "sinif"): cli.class_name,
        ("gecikme", "ek_ms"): cli.delay_ms,
        ("video", "mp4"): False if cli.no_video else None,
        ("video", "qgc"): True if cli.qgc else None,
    }
    merged = dict(d)
    for (block, key), value in values.items():
        current = merged.get(block) or {}
        if value is not None and isinstance(current, dict):  # a broken block is reported by its own check
            merged[block] = {**current, key: value}
    return merged


def _tracking(d: dict, detection_on: bool, cli: CommandLine, altitude: float) -> Tracking:
    _check_keys(d, TRACKING_KEYS, "takip")
    source = d.get("kaynak", "yok")
    if source not in TRACKING_SOURCES:
        raise ValueError(f"takip.kaynak: {list(TRACKING_SOURCES)} olmalı (--takip), gelen: {source!r}")
    mode_name = d.get("mod_adi")
    if mode_name is not None and not (isinstance(mode_name, str) and mode_name.strip()):
        raise ValueError(f"takip.mod_adi: PX4 mod adı (metin) olmalı, gelen: {mode_name!r}")
    if source == "tez_los" and mode_name is None:
        raise ValueError(
            "takip.mod_adi: takip.kaynak tez_los iken zorunlu: PX4'ün AVAILABLE_MODES listesindeki (QGC'de görünen) "
            "ad; komut satırında --mod-adi"
        )
    starts = _commands(_or_empty(d, "px4_baslat", []), "takip.px4_baslat") + _commands(
        list(cli.px4_start), "--px4-baslat"
    )
    params = _or_empty(d, "px4_parametreleri", {})
    if not isinstance(params, dict):
        raise ValueError(f"takip.px4_parametreleri: {{AD: sayı}} sözlüğü olmalı, gelen: {params!r}")
    px4_params = parametreler.from_mapping(params) + [parametreler.parse_assignment(text) for text in cli.params]
    for p in px4_params:
        if p.name == TAKEOFF_PARAM:
            raise ValueError(f"{p.source}: {p.name}: kalkış yüksekliğini drone.yukseklik_m verir; burada yazılmaz")
    if source == "follow_me" and all(p.name != FOLLOW_HEIGHT_PARAM for p in px4_params):
        # first of the scenario's layer: after the .params files (their 8 m), before nothing that names it
        px4_params.insert(0, parametreler.Param(FOLLOW_HEIGHT_PARAM, altitude, FOLLOW_HEIGHT_SOURCE))
    return Tracking(source, mode_name, _los(d, source, detection_on), tuple(starts), tuple(px4_params))


def _los(d: dict, source: str, detection_on: bool) -> str | None:
    """takip.los; not given = the model's box while the model runs. LOS (i) needs the model's boxes."""
    los = d.get("los")
    if los is not None and los not in LOS_SOURCES:
        raise ValueError(f"takip.los: {list(LOS_SOURCES)} olmalı (--los), gelen: {los!r}")
    if detection_on:
        return los or "model"
    if los == "model":
        raise ValueError(
            "takip.los: model, algılama kapalıyken (algilama.etkin: false / --modelsiz) kullanılamaz: model kutusu "
            "yok; hakem seçin (--los hakem) ya da algılamayı açın"
        )
    if los is None and source != "yok":
        raise ValueError(
            f"takip.los: algılama kapalıyken takip.kaynak {source} bir LOS kaynağı ister: takip.los: hakem "
            "(--los hakem) yazın ya da algılamayı açın"
        )
    return los  # "hakem", or None: open loop without a model, no LOS at all


def _or_empty(d: dict, key: str, empty: object) -> object:
    """d[key]; a key written without a value (YAML null) counts as empty, any other value is checked by the caller."""
    value = d.get(key)
    return empty if value is None else value


def _commands(value: object, where: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f'{where}: komut listesi olmalı, ör. ["<modül> start"]; gelen: {value!r}')
    for i, command in enumerate(value):
        if not isinstance(command, str) or not command.strip():
            raise ValueError(f"{where}[{i}]: PX4 komutu (metin) olmalı, gelen: {command!r}")
    return list(value)


def read_detection(d: dict) -> Detection:
    """The algilama block (YAML keys) -> Detection; also model_dene.py's options, so both follow one set of rules."""
    _check_keys(d, set(DETECTION_FIELDS), "algilama")
    default = Detection()
    model = d.get("model")
    if model is not None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError(f"algilama.model: model dosyasının yolu olmalı (--model), gelen: {model!r}")
        model = Path(model).expanduser().absolute()  # a relative path is relative to the working folder
    imgsz = _integer(d, "imgsz", "algilama", minimum=32) if d.get("imgsz") is not None else None
    conf = _number(d, "conf", "algilama", default.conf)
    if not 0 < conf <= 1:
        raise ValueError(f"algilama.conf: 0'dan büyük, en fazla 1 olmalı (güven eşiği), gelen: {conf}")
    return Detection(
        enabled=_flag(d, "etkin", "algilama", default.enabled),
        model=model,
        imgsz=imgsz,
        conf=conf,
        class_name=_class_name(d.get("sinif")),
        cores=_integer(d, "cekirdek", "algilama", default.cores, minimum=1),
    )


def _class_name(value: object) -> str | int | None:
    """algilama.sinif / --sinif: a class number (also written as text, "0") or a class name of the model."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError(f"algilama.sinif: sınıf adı ya da 0 veya daha büyük bir numara olmalı, gelen: {value!r}")


def _defects(d: dict) -> dict:
    """kusurlar: checked by the camera defects stage itself; a Faz B field stops here, before anything starts."""
    kusurlar.check(d)
    return copy.deepcopy(d)


def _delay(d: dict) -> Delay:
    _check_keys(d, set(DELAY_FIELDS), "gecikme")
    signed = {"saat_ofset_ms", "saat_kayma_ppm"}  # the clock may be early or late, fast or slow
    values = {
        attr: _number(d, key, "gecikme", 0.0, minimum=-math.inf if key in signed else 0.0)
        for key, attr in DELAY_FIELDS.items()
    }
    return Delay(**values)


def _video(d: dict, keep_frames: bool) -> Video:
    _check_keys(d, {"mp4", "qgc"}, "video")
    default = Video()
    return Video(_flag(d, "mp4", "video", default.mp4), _flag(d, "qgc", "video", default.qgc), keep_frames)


def start_params(sc: Scenario, files: tuple[Path, ...] = parametreler.FILES) -> dict[str, parametreler.Param]:
    """Every PX4 start parameter of the run in load order (files -> takip.px4_parametreleri -> --param)."""
    return parametreler.merge(*(parametreler.read_file(f) for f in files), sc.tracking.px4_params)


def settings(sc: Scenario) -> dict:
    """Every setting the run uses, for ozet.json "ayarlar": the scenario's blocks after the command line, all PX4
    start parameters with their source, and the defaults that are not in effect yet (see not_in_effect)."""
    t, a, v = sc.tracking, sc.detection, sc.video
    detection = {key: getattr(a, attr) for key, attr in DETECTION_FIELDS.items()}
    detection["model"] = str(a.model) if a.model is not None else None
    return {
        "takip": {"kaynak": t.source, "mod_adi": t.mode_name, "los": t.los, "px4_baslat": list(t.px4_start)},
        "algilama": detection,
        "gecikme": {key: getattr(sc.delay, attr) for key, attr in DELAY_FIELDS.items()},
        "kusurlar": copy.deepcopy(sc.defects),
        "video": {"mp4": v.mp4, "qgc": v.qgc, "kareleri_sakla": v.keep_frames},
        "px4_parametreleri": {n: {"deger": p.value, "kaynak": p.source} for n, p in start_params(sc).items()},
        "henuz_bagli_degil": not_in_effect(sc),
    }


# Settings that later task groups of spec 2026-11-10-m06-sim-ortami wire in (tasks.md 2.5). unwired() stops a run
# that gives one of them a value other than its default, before the simulation starts; nothing is silently ignored.
# not_in_effect() lists the defaults that do not act yet. Each task group deletes its lines when it wires them in.
def unwired(sc: Scenario) -> list[str]:
    """'<setting>: Görev grubu N'de bağlanacak' for every setting of the run that is not wired yet."""
    t, v = sc.tracking, sc.video
    found: list[tuple[str, int]] = []
    if t.px4_start:
        found.append(("takip.px4_baslat / --px4-baslat", 10))
    found += [(text, 12) for text in _changed("gecikme", sc.delay, Delay(), DELAY_FIELDS)]
    if v.qgc:
        found.append(("video.qgc: true (--qgc)", 11))
    if v.keep_frames:
        found.append(("--kareleri-sakla", 8))
    return [f"{what}: {in_group(group)} bağlanacak" for what, group in found]


def not_in_effect(sc: Scenario) -> dict[str, int]:
    """Settings left at a default that a later task group wires in -> that group; they do not act in this run."""
    found = {}
    if sc.video.mp4:
        found["video.mp4"] = 8  # no kosu.mp4 yet
    return found


def check_wired(sc: Scenario) -> None:
    """Raise ValueError (one line per setting) if the run asks for something a later task group wires in."""
    found = unwired(sc)
    if found:
        lines = "".join(f"\n  - {line}" for line in found)
        raise ValueError(f"bu ayarlar henüz bağlanmadı, simülasyon açılmadı:{lines}")


def _changed(block: str, value: object, default: object, names: dict[str, str]) -> list[str]:
    """'<block>.<key>: <value> (<flag>)' for every field of a settings block that differs from its default."""
    found = []
    for key, attr in names.items():
        if getattr(value, attr) != getattr(default, attr):
            flag = FLAGS.get(f"{block}.{key}")
            found.append(f"{block}.{key}: {getattr(value, attr)}" + (f" ({flag})" if flag else ""))
    return found


LOCATIVE_UNITS = {1: "de", 2: "de", 3: "te", 4: "te", 5: "te", 6: "da", 7: "de", 8: "de", 9: "da"}
LOCATIVE_TENS = {1: "da", 2: "de"}  # on, yirmi


def in_group(number: int) -> str:
    """ "Görev grubu 6'da": the Turkish locative suffix follows how the number is read (altı'da, dört'te, on'da)."""
    suffix = LOCATIVE_UNITS[number % 10] if number % 10 else LOCATIVE_TENS[number // 10]
    return f"Görev grubu {number}'{suffix}"


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
