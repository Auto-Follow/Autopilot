#!/usr/bin/env python3
"""Camera tilt x height x distance scan of a follow scenario with the model in the loop (spec
2026-11-10-m06-sim-ortami, tasks.md Görev Grubu 17, brought forward): plan the grid, fly every combination with
toplu.py (resumable), add the scan's per-run numbers and rank the combinations by the decision rule.

    ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/tarama.py plan --cikti tez/sim/sonuclar/T \
        --temel takip_yuruyen --egim 30 35 40 45 --yukseklik 8 10 12 15 --carpan 0.8 1 1.25 --ek-mesafe 8
    ... kos --cikti tez/sim/sonuclar/T --asama asama1 --tekrar 1 -- --videosuz     (-- : flags for every senaryo.py)
    ... kos --cikti tez/sim/sonuclar/T --asama asama2 --tekrar 3 --sadece ID ID ...
    ... ozet --cikti tez/sim/sonuclar/T --asama asama1 [--aday 6]                 (table, gates, scores, candidates)

Grid: for every tilt and height the distance d = h / tan(tilt) (the camera report's rule, at 45 deg height = distance:
the camera's axis meets the ground near the person's feet) times each factor, plus the report's extra distances
(8 m: its "lowest successful setting" table flew 8 m behind at every tilt), rounded to 0.1 m. A combination is flown
only if the person (feet and head) is inside the vertical field of view at level flight with FRAME_MARGIN_DEG to spare.

Scenario of a combination (written into <cikti>/senaryolar/, not in git): the base scenario's path, shifted east so
the person starts d ahead of the drone (centred in the image at take-off; the drone takes off at (0, 0) facing east),
same shape and timing; drone.yukseklik_m = h (FLW_TGT_HT follows it), FLW_TGT_DST = d, kamera.egim_deg = tilt; the
tracking block of the template scenario (follow_me, model, FLW_TGT_RS) for every base, so all runs track alike.

Every stage is a folder <cikti>/<asama>/ with one toplu.py folder per combination and durum.json (the combinations
that are done); an interrupted `kos` starts again where it stopped and never flies a finished combination again.

Decision rule (written before the runs, implementation/gorev-grubu-17-on-kamera-acisi.md):
  1. gates, every run: at least GATE_MIN_DISTANCE_M from the person (the 3 m warning of decision 3, 12.11), the person
     not lost at the end (the stock mode never found them again: the camera report's "success"), a valid run;
  2. a score per group (GROUPS), min-max over the combinations that passed (best 1, worst 0), the mean of a group's
     metrics; total = the mean of the groups (equal weights); sim_puani the same without the geometry group;
  3. stage-2 candidates: the best of each tilt, then the next best overall, plus the 45 deg 8/8 and 10/10 references.
"""

import argparse
import datetime as dt
import json
import math
import statistics
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

import hedef

SIM_DIR = hedef.SIM_DIR
TOPLU = Path(__file__).resolve().parent / "toplu.py"
VFOV_HALF_DEG = math.degrees(math.atan2(648.0, 1773.9))  # [deg] models/x500_tez: 66 deg HFOV, 16:9
CAMERA_AHEAD_M = 0.151  # [m] camera optical centre ahead of base_link (konumlama.NOMINAL_OFFSET_FRD)
CAMERA_ABOVE_HOME_M = -0.035  # [m] camera below base_link
HOME_ABOVE_GROUND_M = 0.227  # [m] base_link above the ground at arming (konumlama.GROUND_BELOW_HOME_M)
HEAD_M = 1.75  # [m] the person's head (kayit.TARGET_POINTS)
FRAME_MARGIN_DEG = 2.0  # [deg] the person's feet and head this far inside the image edges at level flight
DEDUPE_M = 0.75  # [m] a planned distance this close to another of the same tilt and height is not planned again
TEMPLATE = "takip_yuruyen"  # the tracking block (follow_me, model, FLW_TGT_RS) every combination flies with
STALE_S = 3.0  # [s] PX4 marks its target estimate stale after this long without FOLLOW_TARGET
GATE_MIN_DISTANCE_M = 3.0  # [m] decision 3 (12.11): the 3 m warning
REFERENCES = ((45.0, 8.0, 8.0), (45.0, 10.0, 10.0))  # (tilt, height, distance): the camera report's 8/8 and 10/10
# Groups of the decision rule: (metric, +1 bigger is better / -1 smaller is better). Geometry: not measured, it
# follows from tilt, height and distance (horizon margin, ground-height sensitivity, height above heads).
GROUPS = {
    "guvenlik": (("en_az_yatay_mesafe_m", 1), ("mesafe_6m_alti_orani", -1), ("mesafe_4m_alti_orani", -1)),
    "sureklilik": (
        ("kisi_sonda_kayip", -1),
        ("kilit_kaybi_sayisi", -1),
        ("en_uzun_kayip_s", -1),
        ("hedef_kadrajda_orani", 1),
        ("gorunur_kalma", 1),
    ),
    "algilama": (("algilama_orani", 1), ("kisi_kutu_boyu_px", 1)),
    "konum": (("konum_hatasi_ort_m", -1), ("konum_hatasi_p95_m", -1)),
    "salinim": (("arkada_kalma_hatasi_ort_deg", -1), ("bagil_mesafe_hatasi", -1), ("baslangic_yorunge_donusu_deg", -1)),
    "kose": (("kose_px4_yetisme_ort_s", -1), ("kose_px4_yetismedi_sayisi", -1), ("kose_arkada_kalma_maks_deg", -1)),
    "geometri": (("ufuk_payi_deg", 1), ("zemin_duyarliligi", -1), ("bas_ustu_m", 1)),
}
GROUP_NAMES = {
    "guvenlik": "Güvenlik",
    "sureklilik": "Takip sürekliliği",
    "algilama": "Algılama",
    "konum": "Konum hatası",
    "salinim": "Salınım / arkada kalma",
    "kose": "Köşede yetişme",
    "geometri": "Geometri (sim dışı)",
}
SUMMARY_KEYS = tuple(k for group in GROUPS.values() for k, _ in group) + (
    "yatay_mesafe_ort_m",
    "yakin_mesafe_3m_suresi_s",
    "kadrajda_kalma",
    "secim_dogru_orani",
    "los_aci_hatasi_ort_deg",
    "px4_kestirim_hatasi_ort_m",
    "px4_kestirim_bayat_s",
    "kadraj_yakin_sinir_m",
    "dron_yukseklik_ort_m",
    "model_ms_ort",
    "rtf_ort",
    "mod_korunma_orani",
    "kisi_model_girisi_px",
    "kisi_bas_ayak_px",
    "son_follow_target_s",
    "yaklasma_m",
    "kose_yaklasma_m",
    "durma_yaklasma_m",
    "kose_pay_asimi_m",
    "kadraj_disi_alt_s",
    "kadraj_disi_yan_s",
    "kadraj_disi_ust_s",
    "kadraj_yakin_sinir_alti_s",
    "burun_kalkisi_maks_deg",
    "dinamik_pay_asimi_m",
)


def log(text: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {text}", flush=True)


# --- the grid -------------------------------------------------------------------------------------------------------


def centre_distance(tilt_deg: float, height: float) -> float:
    """[m] d = h / tan(tilt): the camera report's rule (45 deg: height = distance)."""
    return height / math.tan(math.radians(tilt_deg))


def view(tilt_deg: float, height: float, distance: float) -> dict:
    """Where the person's feet and head are below the horizon from the camera at level flight [deg], the image's
    bottom and top edge, and whether the person fits with FRAME_MARGIN_DEG to spare. height: above home (FLW_TGT_HT),
    distance: base_link to the person, horizontal (FLW_TGT_DST)."""
    cam_h = height + CAMERA_ABOVE_HOME_M + HOME_ABOVE_GROUND_M
    ahead = distance - CAMERA_AHEAD_M
    feet = math.degrees(math.atan2(cam_h, ahead))
    head = math.degrees(math.atan2(cam_h - HEAD_M, ahead))
    bottom, top = tilt_deg + VFOV_HALF_DEG, tilt_deg - VFOV_HALF_DEG
    fits = ahead > 0 and feet <= bottom - FRAME_MARGIN_DEG and head >= top + FRAME_MARGIN_DEG
    return {"ayak_deg": feet, "bas_deg": head, "alt_kenar_deg": bottom, "ust_kenar_deg": top, "sigar": fits}


def geometry(tilt_deg: float, height: float, distance: float) -> dict:
    """What tilt, height and distance mean outside the sim: the nose pitch-up that brings the horizon into the image
    [deg], the flat-ground position shift per metre of ground-height (or GPS height) error [m/m] and the height above
    the heads [m]."""
    return {
        "ufuk_payi_deg": tilt_deg - VFOV_HALF_DEG,
        "zemin_duyarliligi": distance / height,
        "bas_ustu_m": height - HEAD_M,
    }


HFOV_HALF_DEG = 33.0  # [deg] models/x500_tez: 66 deg horizontal field of view
CORNER_WINDOW_S = 8.0  # [s] after a turn starts, the closest approach of that corner is looked for this long
CORNER_MIN_TURN_DEG = 45.0  # olcum.CORNER_TURN_DEG
STOP_AFTER_S = 1.0  # [s] the stop window runs this far into the start after the stop


def margins(tilt_deg: float, height: float, distance: float) -> dict:
    """Geometry of a combination at level flight (explanatory columns, not scored): the camera's near and far ground
    limit [m from base_link], the approach margin (distance - near limit: the drone this much closer and the feet are
    below the image), the fall-behind margin (far limit - distance), the ground width the image covers across the
    person's feet (2 tan(HFOV/2) times their depth along the optical axis: room to slip out sideways at a corner),
    the slant range and depression angle to the person's body centre (0.9 m) [m, deg]."""
    cam_h = height + CAMERA_ABOVE_HOME_M + HOME_ABOVE_GROUND_M
    tilt, half = math.radians(tilt_deg), math.radians(VFOV_HALF_DEG)
    near = CAMERA_AHEAD_M + cam_h / math.tan(tilt + half)
    far = CAMERA_AHEAD_M + cam_h / math.tan(tilt - half) if tilt > half else math.inf
    ahead = distance - CAMERA_AHEAD_M
    depth = ahead * math.cos(tilt) + cam_h * math.sin(tilt)  # the feet's depth along the optical axis
    return {
        "yakin_sinir_m": near,
        "uzak_sinir_m": far,
        "yaklasma_payi_m": distance - near,
        "geri_kalma_payi_m": far - distance,
        "genislik_m": 2.0 * math.tan(math.radians(HFOV_HALF_DEG)) * depth,
        "egik_mesafe_m": math.hypot(ahead, cam_h - 0.9),
        "bakis_deg": math.degrees(math.atan2(cam_h - 0.9, ahead)),
    }


def combination_id(base: str, tilt: float, height: float, distance: float) -> str:
    prefix = "" if base == TEMPLATE else f"{base}_"
    return f"{prefix}e{tilt:g}_h{height:g}_d{distance:.1f}"


def _load_yaml(name: str) -> dict:
    return yaml.safe_load(hedef.find_scenario(name).read_text(encoding="utf-8"))


def variant(base: dict, template: dict, tilt: float, height: float, distance: float, name: str) -> dict:
    """The base scenario flown at (tilt, height, distance): see the module text."""
    d = json.loads(json.dumps(base))  # deep copy of plain YAML data
    target = d["hedef"]
    shift = distance - float(target["baslangic"][0])
    target["baslangic"] = [round(float(target["baslangic"][0]) + shift, 3), float(target["baslangic"][1])]
    for step in target.get("yol") or []:
        if "nokta" in step:
            step["nokta"] = [round(float(step["nokta"][0]) + shift, 3), float(step["nokta"][1])]
    takip = json.loads(json.dumps(template["takip"]))
    takip["px4_parametreleri"] = {**(takip.get("px4_parametreleri") or {}), "FLW_TGT_DST": distance}
    takip["px4_parametreleri"].pop("FLW_TGT_HT", None)  # Follow Me's height = drone.yukseklik_m
    d.update(
        ad=name,
        aciklama=(
            f"{base.get('ad', '')} yolu, {shift:+.1f} m doğuya kaydırılmış (kişi dronun {distance:g} m önünde başlar); "
            f"kamera {tilt:g}°, dron {height:g} m yükseklikte, kişinin {distance:g} m gerisinde (tarama.py)"
        ),
        drone={"yukseklik_m": height},
        takip=takip,
        kamera={"egim_deg": tilt},
    )
    return d


def make_plan(
    out: Path,
    base: str,
    tilts: Sequence[float],
    heights: Sequence[float],
    factors: Sequence[float],
    extra: Sequence[float],
    append: bool = False,
) -> dict:
    """Write <out>/plan.json and the scenario of every combination (<out>/senaryolar/<id>.yaml); -> the plan.
    append: keep what plan.json already has and add the new combinations after it (another band of the grid, or the
    same settings on another base path: a repeat is only looked for among the combinations of the same base)."""
    base_d, template = _load_yaml(base), _load_yaml(TEMPLATE)
    folder = out / "senaryolar"
    folder.mkdir(parents=True, exist_ok=True)
    combos, left, first_base = [], [], base
    if append and (out / "plan.json").is_file():
        old = read_plan(out)
        combos, left, first_base = old["bilesimler"], old["atlanan"], old.get("temel", TEMPLATE)
    for entry in combos + left:  # plans written before the field: every entry belongs to the plan's first base
        entry.setdefault("temel", first_base)
    for tilt in tilts:
        for height in heights:
            centre = centre_distance(tilt, height)
            wanted = [(round(centre * f, 1), "merkez" if f == 1.0 else f"carpan_{f:g}") for f in factors]
            wanted += [(round(e, 1), f"rapor_{e:g}m") for e in extra]
            planned = [
                c["mesafe_m"]
                for c in combos
                if (c["temel"], c["egim_deg"], c["yukseklik_m"]) == (base, float(tilt), float(height))
            ]
            for distance, kind in wanted:
                if any(abs(distance - p) < DEDUPE_M for p in planned):
                    continue
                v = view(tilt, height, distance)
                entry = {"temel": base, "egim_deg": float(tilt), "yukseklik_m": float(height), "mesafe_m": distance}
                entry["tur"] = kind
                if entry in [{k: a[k] for k in entry} for a in left]:
                    continue
                if not v["sigar"]:
                    reason = (
                        f"kişi kadraja sığmıyor: ayak {v['ayak_deg']:.1f}°, baş {v['bas_deg']:.1f}° aşağıda; görüntü "
                        f"{v['ust_kenar_deg']:.1f}–{v['alt_kenar_deg']:.1f}° (± {FRAME_MARGIN_DEG:g}° pay)"
                    )
                    left.append(entry | {"neden": reason})
                    continue
                planned.append(distance)
                cid = combination_id(base, tilt, height, distance)
                path = folder / f"{cid}.yaml"
                scenario = variant(base_d, template, tilt, height, distance, cid)
                path.write_text(yaml.safe_dump(scenario, allow_unicode=True, sort_keys=False), encoding="utf-8")
                hedef.load(str(path))  # every planned scenario must load (path, trees, fields)
                combos.append({"id": cid, **entry, "kadraj": v, "geometri": geometry(tilt, height, distance)})
                combos[-1]["senaryo"] = str(path)
    plan = {"temel": first_base, "sablon": TEMPLATE, "bilesimler": combos, "atlanan": left}
    (out / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    return plan


def read_plan(out: Path) -> dict:
    return json.loads((out / "plan.json").read_text(encoding="utf-8"))


# --- flying ---------------------------------------------------------------------------------------------------------


def toplu_runner(combination: dict, folder: Path, repeat: int, extra: list[str]) -> int:
    """toplu.py for one combination: its own process (it starts a senaryo.py per run); its log next to it."""
    cmd = [sys.executable, str(TOPLU), "--senaryo", combination["senaryo"], "--tekrar", str(repeat)]
    cmd += ["--cikti", str(folder)] + (["--", *extra] if extra else [])
    with folder.with_suffix(".log").open("a", encoding="utf-8") as f:
        return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode


def _write_state(path: Path, state: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def run_stage(
    out: Path,
    stage: str,
    repeat: int,
    extra: Sequence[str],
    only: Sequence[str] | None = None,
    runner: Callable[[dict, Path, int, list[str]], int] = toplu_runner,
) -> list[str]:
    """Fly every planned combination (or `only` these ids) `repeat` times into <out>/<stage>/<id>/, skipping the ones
    durum.json lists as done; -> the ids flown now. A combination is done once its toplu.json is there."""
    plan = read_plan(out)
    combos = {c["id"]: c for c in plan["bilesimler"]}
    ids = list(only) if only else list(combos)
    unknown = [i for i in ids if i not in combos]
    if unknown:
        raise ValueError(f"planda olmayan bileşim(ler): {unknown}")
    folder = out / stage
    folder.mkdir(parents=True, exist_ok=True)
    state_path = folder / "durum.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    state.setdefault("bitti", {})
    state.update(asama=stage, tekrar=repeat, bayraklar=list(extra))
    todo = [i for i in ids if i not in state["bitti"]]
    log(f"{stage}: {len(ids)} bileşim, {len(ids) - len(todo)} bitmiş, {len(todo)} kalan ({repeat} koşu, {extra})")
    flown, started = [], dt.datetime.now()
    for n, cid in enumerate(todo, start=1):
        target = folder / cid
        if target.exists():  # an interrupted attempt: kept aside, flown again from the start
            target.rename(folder / f"{cid}_yarim_{dt.datetime.now():%H%M%S}")
        log(f"{stage} {n}/{len(todo)}: {cid}")
        code = runner(combos[cid], target, repeat, list(extra))
        flown.append(cid)
        if code == 2:
            raise ValueError(f"{cid}: toplu.py ayarı reddetti (çıkış 2), ayrıntı: {target.with_suffix('.log')}")
        if not (target / "toplu.json").is_file():
            log(f"UYARI: {cid}: toplu.json yazılmadı (çıkış {code}); bitmiş sayılmadı")
            continue
        state["bitti"][cid] = {"klasor": str(target), "cikis": code, "bitis": f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}"}
        _write_state(state_path, state)
        eta = dt.datetime.now() + (dt.datetime.now() - started) / n * (len(todo) - n)
        log(f"{cid} bitti (çıkış {code}); kalan {len(todo) - n}, tahmini bitiş {eta:%H:%M}")
    return flown


# --- the scan's numbers ---------------------------------------------------------------------------------------------


def run_numbers(folder: Path, end: float, imgsz: int, start: float = 60.0) -> dict:
    """Per run, from its files: the person lost at the end (the last FOLLOW_TARGET that went out more than STALE_S
    before the end, or none at all: PX4's estimate was stale and the stock mode never found them again), the median
    height of the person's referee box (visible frames from the walk on, `start` [s]) and of the head-to-feet
    projection [px], and what the model sees of the box at its input size."""
    ft = folder / "follow_target.csv"  # opened with the first attempt: missing = no FOLLOW_TARGET ever went out
    attempts = pd.read_csv(ft) if ft.is_file() else pd.DataFrame(columns=["t", "sonuc"])
    sent = attempts[attempts["sonuc"] == "gonderildi"]
    last = float(sent["t"].max()) if not sent.empty else math.nan
    m = {
        "son_follow_target_s": last,
        "sonda_kayip_s": end - last if math.isfinite(last) else math.nan,
        "kisi_sonda_kayip": float(not (math.isfinite(last) and end - last <= STALE_S)),
    }
    ref = pd.read_csv(folder / "dogru_cevap.csv")
    walk = ref[(ref["t"] >= start) & ref["gorunur"].astype(bool)] if "gorunur" in ref else ref.iloc[0:0]
    box = (walk["hedef_kutu_v1"] - walk["hedef_kutu_v0"]).dropna()
    m["kisi_kutu_boyu_px"] = float(box.median()) if not box.empty else math.nan
    m["kisi_model_girisi_px"] = m["kisi_kutu_boyu_px"] * imgsz / 2304.0
    span = (walk["ayak_v"] - walk["bas_v"]).dropna() if "bas_v" in walk else pd.Series(dtype=float)
    m["kisi_bas_ayak_px"] = float(span.median()) if not span.empty else math.nan
    return m


def approach_numbers(
    folder: Path, start: float, distance: float, corners: Sequence[dict], tilt_deg: float = 45.0
) -> dict:
    """Per run, from dogru_cevap.csv and ozet.json "koseler": how much closer than FLW_TGT_DST the drone came [m]
    from the walk on, in the stop (the corner that starts after a stop: its stop and STOP_AFTER_S into the start) and
    after the turns (CORNER_WINDOW_S from a turn of at least CORNER_MIN_TURN_DEG, the largest); how long the person's
    body centre was out of the image below, at a side and above it from the walk on [s]; the drone's largest nose-up
    pitch [deg] and how far the near limit with the drone's own pitch (the image's bottom edge at tilt + vfov/2 -
    pitch below the horizon) came beyond the drone-person distance at most [m] (> 0: the feet were below the
    image), both from the walk on."""
    ref = pd.read_csv(folder / "dogru_cevap.csv").sort_values("t")
    t, d = ref["t"].to_numpy(dtype=float), ref["yatay_mesafe"].to_numpy(dtype=float)
    dt = np.diff(t, append=t[-1] + (t[-1] - t[-2] if len(t) > 1 else 0.0))

    def closest(a: float, b: float) -> float:
        sel = (t >= a) & (t <= b)
        return float(distance - np.min(d[sel])) if sel.any() else math.nan

    m = {"yaklasma_m": closest(start, math.inf), "kose_yaklasma_m": math.nan, "durma_yaklasma_m": math.nan}
    turns = [
        closest(c["baslangic_s"], c["baslangic_s"] + CORNER_WINDOW_S)
        for c in corners
        if (c.get("donus_deg") or 0.0) >= CORNER_MIN_TURN_DEG
    ]
    if turns:
        m["kose_yaklasma_m"] = max(turns)
    stops = [c for c in corners[1:] if (c.get("durus_s") or 0.0) > 0.5]
    if stops:
        c = stops[0]
        m["durma_yaklasma_m"] = closest(c["baslangic_s"] - c["durus_s"], c["baslangic_s"] + STOP_AFTER_S)
    walk = t >= start
    u, v = ref["merkez_u"].to_numpy(dtype=float), ref["merkez_v"].to_numpy(dtype=float)
    below, above, side = walk & (v >= 1296.0), walk & (v < 0.0), walk & ((u < 0.0) | (u >= 2304.0))
    side &= ~below & ~above  # a corner of the image counts once, as below / above
    m["kadraj_disi_alt_s"] = float(dt[below].sum())
    m["kadraj_disi_ust_s"] = float(dt[above].sum())
    m["kadraj_disi_yan_s"] = float(dt[side].sum())
    pitch = ref["dron_pitch_deg"].to_numpy(dtype=float) if "dron_pitch_deg" in ref else np.zeros(len(t))
    edge = np.radians(tilt_deg + VFOV_HALF_DEG - pitch)
    cam_h = ref["kamera_z"].to_numpy(dtype=float) if "kamera_z" in ref else np.full(len(t), math.nan)
    near = np.where(edge > 0.02, cam_h / np.tan(np.clip(edge, 0.02, None)) + CAMERA_AHEAD_M, np.inf)
    m["burun_kalkisi_maks_deg"] = float(np.max(pitch[walk])) if walk.any() else math.nan
    m["dinamik_pay_asimi_m"] = float(np.max((near - d)[walk])) if walk.any() else math.nan
    return m


def collect(out: Path, stage: str) -> list[dict]:
    """Every combination of a stage with its runs: ozet.json "olcutler" + run_numbers + the relative distance error."""
    plan = read_plan(out)
    combos = []
    for c in plan["bilesimler"]:
        folder = out / stage / c["id"]
        if not (folder / "toplu.json").is_file():
            continue
        runs = []
        for run in sorted(folder.glob("kosu_*")):
            if "_deneme" in run.name or not (run / "ozet.json").is_file():
                continue
            s = json.loads((run / "ozet.json").read_text(encoding="utf-8"))
            sc = hedef.load(str(run / "senaryo.yaml"))
            imgsz = (s.get("ayarlar") or {}).get("algilama", {}).get("model_bilgisi", {}).get("imgsz") or 640
            m = {k: (math.nan if v is None else v) for k, v in s["olcutler"].items() if not isinstance(v, dict | list)}
            m |= run_numbers(run, sc.end_time, int(imgsz), sc.start_time)
            m |= approach_numbers(run, sc.start_time, c["mesafe_m"], s.get("koseler") or [], c["egim_deg"])
            m["bagil_mesafe_hatasi"] = m.get("yatay_mesafe_hatasi_ort_m", math.nan) / c["mesafe_m"]
            margin = margins(c["egim_deg"], c["yukseklik_m"], c["mesafe_m"])["yaklasma_payi_m"]
            m["kose_pay_asimi_m"] = m["kose_yaklasma_m"] - margin  # > 0: the corner put the feet below the image
            m["sonuc"] = s.get("sonuc")
            m["klasor"] = str(run)
            runs.append(m)
        combos.append({**c, "kosular": runs})
    return combos


# --- the decision rule ----------------------------------------------------------------------------------------------


def _mean(values: Sequence[float]) -> float:
    ok = [float(v) for v in values if v is not None and isinstance(v, int | float) and math.isfinite(v)]
    return statistics.fmean(ok) if ok else math.nan


def gate(runs: Sequence[dict]) -> dict:
    """Every run: at least GATE_MIN_DISTANCE_M from the person, the person not lost at the end, a valid run."""
    reasons = []
    closest = min((r.get("en_az_yatay_mesafe_m", math.nan) for r in runs), default=math.nan)
    if not closest >= GATE_MIN_DISTANCE_M:
        reasons.append(f"en az yatay mesafe {closest:.2f} m < {GATE_MIN_DISTANCE_M:g} m")
    lost = sum(1 for r in runs if r.get("kisi_sonda_kayip") == 1.0)
    if lost:
        reasons.append(f"kişi sonda kaybedildi ({lost}/{len(runs)} koşu)")
    invalid = sum(1 for r in runs if r.get("sonuc", "GEÇTİ") == "TAMAMLANMADI")
    if invalid or not runs:
        reasons.append(f"geçersiz koşu ({invalid}/{len(runs)})")
    return {"gecti": not reasons, "neden": "; ".join(reasons), "en_az_m": closest, "kayip": lost, "kosu": len(runs)}


def rank(combos: Sequence[dict]) -> list[dict]:
    """Gates, group scores, total and rank of every combination (see the module text); the raw means stay."""
    table = []
    for c in combos:
        means = {k: _mean([r.get(k) for r in c["kosular"]]) for k in SUMMARY_KEYS if k not in GROUPS["geometri"]}
        geo = geometry(c["egim_deg"], c["yukseklik_m"], c["mesafe_m"])
        means |= geo
        spread = {
            k: (min(vals), max(vals))
            for k in SUMMARY_KEYS
            if (
                vals := [float(r[k]) for r in c["kosular"] if isinstance(r.get(k), int | float) and math.isfinite(r[k])]
            )
        }
        explain = margins(c["egim_deg"], c["yukseklik_m"], c["mesafe_m"])
        means |= explain
        table.append(
            {**c, "ort": means, "aralik": spread, "geometri": geo, "aciklama": explain, "kapi": gate(c["kosular"])}
        )
    passed = [r for r in table if r["kapi"]["gecti"]]
    for r in table:
        scores = {}
        for group, metrics in GROUPS.items():
            values = []
            for key, sign in metrics:
                pool = [p["ort"][key] for p in passed if math.isfinite(p["ort"][key])]
                x = r["ort"][key]
                if not pool or not math.isfinite(x):
                    continue
                lo, hi = min(pool), max(pool)
                s = 1.0 if hi == lo else (x - lo) / (hi - lo)
                values.append(min(1.0, max(0.0, s if sign > 0 else 1.0 - s)))
            scores[group] = statistics.fmean(values) if values else math.nan
        r["puanlar"] = scores
        ok = [v for v in scores.values() if math.isfinite(v)]
        r["toplam"] = statistics.fmean(ok) if ok else math.nan
        sim = [v for k, v in scores.items() if k != "geometri" and math.isfinite(v)]
        r["sim_puani"] = statistics.fmean(sim) if sim else math.nan
        r["sira"] = None
    for i, r in enumerate(sorted(passed, key=lambda p: -p["toplam"]), start=1):
        r["sira"] = i
    return table


def candidates(table: Sequence[dict], count: int = 6) -> list[dict]:
    """Stage 2: the best of each tilt among the combinations that passed, then the next best overall up to `count`,
    then the REFERENCES; -> [{id, neden}] in that order."""
    passed = sorted((r for r in table if r["kapi"]["gecti"]), key=lambda r: r["sira"])
    chosen: list[dict] = []
    for tilt in sorted({r["egim_deg"] for r in passed}):
        best = next(r for r in passed if r["egim_deg"] == tilt)
        chosen.append({"id": best["id"], "neden": f"{tilt:g}° için en iyi (sıra {best['sira']})", "sira": best["sira"]})
    chosen.sort(key=lambda c: c["sira"])
    chosen = chosen[:count]
    for r in passed:
        if len(chosen) >= count:
            break
        if all(c["id"] != r["id"] for c in chosen):
            chosen.append({"id": r["id"], "neden": f"sıradaki en iyi (sıra {r['sira']})", "sira": r["sira"]})
    for tilt, height, distance in REFERENCES:
        ref = next(
            (
                r
                for r in table
                if (r["egim_deg"], r["yukseklik_m"]) == (tilt, height) and abs(r["mesafe_m"] - distance) < 0.05
            ),
            None,
        )
        if ref is None:
            continue
        name = f"başvuru {tilt:g}° {height:g}/{distance:g}"
        found = next((c for c in chosen if c["id"] == ref["id"]), None)
        if found is not None:
            found["neden"] += f"; {name}"
        else:
            chosen.append({"id": ref["id"], "neden": name, "sira": ref["sira"]})
    return chosen


def summary_frame(table: Sequence[dict]) -> pd.DataFrame:
    """One row per combination: parameters, gate, scores, rank and the raw means (ozet.csv)."""
    rows = []
    for r in table:
        row = {k: r[k] for k in ("id", "egim_deg", "yukseklik_m", "mesafe_m", "tur")}
        row |= {"kosu": r["kapi"]["kosu"], "kapi": r["kapi"]["gecti"], "kapi_neden": r["kapi"]["neden"]}
        row |= {"sira": r["sira"], "toplam": r["toplam"], "sim_puani": r["sim_puani"]}
        row |= {f"puan_{g}": v for g, v in r["puanlar"].items()} | r["ort"]
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["kapi", "toplam"], ascending=[False, False])


def write_summary(out: Path, stage: str, count: int) -> dict:
    table = rank(collect(out, stage))
    chosen = candidates(table, count) if stage == "asama1" else []
    folder = out / stage
    summary_frame(table).to_csv(folder / "ozet.csv", index=False)
    data = {"asama": stage, "bilesimler": table, "adaylar": chosen}
    (folder / "ozet.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1, default=lambda v: None), encoding="utf-8"
    )
    return data


# --- command line ---------------------------------------------------------------------------------------------------


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="komut", required=True)
    p = sub.add_parser("plan", help="ızgarayı ve her bileşimin senaryosunu yaz")
    p.add_argument("--cikti", type=Path, required=True)
    p.add_argument("--temel", default=TEMPLATE, help="yolu kullanılan senaryo (varsayılan takip_yuruyen)")
    p.add_argument("--egim", type=float, nargs="+", required=True, metavar="DERECE")
    p.add_argument("--yukseklik", type=float, nargs="+", required=True, metavar="M")
    p.add_argument("--carpan", type=float, nargs="+", default=[1.0], help="merkez mesafesinin çarpanları")
    p.add_argument("--ek-mesafe", type=float, nargs="*", default=[], metavar="M", help="ek mesafeler (ör. 8)")
    p.add_argument("--ekle", action="store_true", help="var olan plana ekle (ızgaranın başka bir bandı)")
    k = sub.add_parser("kos", help="bileşimleri toplu.py ile koş (biteni tekrarlamaz)")
    k.add_argument("--cikti", type=Path, required=True)
    k.add_argument("--asama", default="asama1")
    k.add_argument("--tekrar", type=int, default=1)
    k.add_argument("--sadece", nargs="+", metavar="ID", help="yalnız bu bileşimler")
    k.add_argument("senaryo_bayraklari", nargs="*", help="-- işaretinden sonra: her koşuda senaryo.py'ye verilir")
    o = sub.add_parser("ozet", help="aşamanın tablosu, kapılar, puanlar ve (aşama 1'de) aşama 2 adayları")
    o.add_argument("--cikti", type=Path, required=True)
    o.add_argument("--asama", default="asama1")
    o.add_argument("--aday", type=int, default=6, help="aşama 2 aday sayısı (başvurular hariç)")
    return ap


def main() -> int:
    args = parser().parse_args()
    try:
        if args.komut == "plan":
            args.cikti.mkdir(parents=True, exist_ok=True)
            plan = make_plan(
                args.cikti, args.temel, args.egim, args.yukseklik, args.carpan, args.ek_mesafe, append=args.ekle
            )
            n, left = len(plan["bilesimler"]), len(plan["atlanan"])
            log(f"{n} bileşim planlandı, {left} atlandı: {args.cikti / 'plan.json'}")
            for a in plan["atlanan"]:
                log(f"  atlandı: {a['egim_deg']:g}° {a['yukseklik_m']:g} m / {a['mesafe_m']:g} m: {a['neden']}")
        elif args.komut == "kos":
            run_stage(args.cikti, args.asama, args.tekrar, args.senaryo_bayraklari, args.sadece)
        else:
            data = write_summary(args.cikti, args.asama, args.aday)
            passed = sorted((r for r in data["bilesimler"] if r["kapi"]["gecti"]), key=lambda r: r["sira"])
            for r in passed[:12]:
                log(f"{r['sira']:2d}. {r['id']}: toplam {r['toplam']:.3f}, sim {r['sim_puani']:.3f}")
            for c in data["adaylar"]:
                log(f"aday: {c['id']} ({c['neden']})")
    except (ValueError, FileNotFoundError) as e:
        print(f"Tarama hatası: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
