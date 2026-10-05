#!/usr/bin/env python3
"""Analysis of the deney.py logs: camera tilt / visibility, geolocation accuracy, FOLLOW_TARGET latency and loss.

  python3 tez/deney/follow_sim/analiz.py sonuclar/kamera_egim40
  python3 tez/deney/follow_sim/analiz.py sonuclar/geolocation_egim40 sonuclar/gecikme_egim40

Writes PNG figures and ozet.md / analiz.json next to the CSV files.
"""
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geolocation as geoloc  # noqa: E402

# Must match follow_core.py (kept here so the analysis runs without the gz python bindings)
CAMERA_OFFSET = np.array([0.12, 0.03, 0.242])  # model frame, FLU
BASE_LINK_Z_IN_MODEL = 0.24
BODY_HEIGHT_LANDED_M = 0.227
HFOV_RAD, IMAGE_W, IMAGE_H = 1.1519, 2304, 1296
FOCAL_PX = (IMAGE_W / 2) / math.tan(HFOV_RAD / 2)
TARGET_HEIGHT_M = 1.79
PX4_STALE_S = 3.0
PITCHES = list(range(0, 75, 5))
MARGIN_PX = 20  # a point this close to the border does not count as in frame

T_ENU_NED = np.array([[0, 1, 0], [1, 0, 0], [0, 0, -1.0]])
F_FLU_FRD = np.diag([1.0, -1.0, -1.0])


def quat_matrices(qw, qx, qy, qz):
    """(n,) arrays -> (n, 3, 3) rotation matrices."""
    w, x, y, z = (np.asarray(a, dtype=float) for a in (qw, qx, qy, qz))
    return np.stack([
        np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)], -1),
        np.stack([2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)], -1),
        np.stack([2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], -1)], -2)


def load(directory):
    runs = {}
    for f in sorted(Path(directory).glob("*.csv")):
        d = pd.read_csv(f)
        if "mode" not in d:  # kadraj_tablosu.csv and other outputs
            continue
        d = d[d["mode"] == "Follow Me"].dropna(subset=["dx"]).reset_index(drop=True)
        d["tt"] = d["t"] - d["t"].iloc[0]
        runs[f.stem] = d
    meta = {}
    if (Path(directory) / "ozet.json").exists():
        meta = {s["name"]: s for s in json.loads((Path(directory) / "ozet.json").read_text())["senaryolar"]}
    return runs, meta


# ------------------------------------------------------------------------------------------- visibility
def project(d, pitch_deg, z, gimbal=False):
    """Pixel (u, v) and depth of the ground-truth target point at height z for a camera tilted pitch_deg down.
    gimbal=True: roll/pitch stabilized camera (only the drone's yaw turns it)."""
    R = quat_matrices(d.qw, d.qx, d.qy, d.qz)  # model -> world (ENU / FLU)
    if gimbal:
        yaw = np.arctan2(R[:, 1, 0], R[:, 0, 0])
        R = quat_matrices(np.cos(yaw / 2), 0 * yaw, 0 * yaw, np.sin(yaw / 2))
    p = d[["dx", "dy", "dz"]].to_numpy()
    cam = p + R @ CAMERA_OFFSET
    a = math.radians(pitch_deg)
    tilt = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])  # +a = down
    Rc = R @ tilt
    rel = np.stack([d.tx - cam[:, 0], d.ty - cam[:, 1], z - cam[:, 2]], -1)
    c = np.einsum("nji,nj->ni", Rc, rel)  # camera FLU
    depth = c[:, 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        u = IMAGE_W / 2 - FOCAL_PX * c[:, 1] / depth
        v = IMAGE_H / 2 - FOCAL_PX * c[:, 2] / depth
    return u, v, depth


def in_frame(u, v, depth):
    return ((depth > 0) & (u >= MARGIN_PX) & (u < IMAGE_W - MARGIN_PX) & (v >= MARGIN_PX)
            & (v < IMAGE_H - MARGIN_PX))


def longest_gap(t, visible):
    """Longest continuous time [s] the target is out of frame, and the number of gaps longer than 3 s."""
    best, start, n_long = 0.0, None, 0
    for ti, vis in zip(t, visible):
        if not vis and start is None:
            start = ti
        elif vis and start is not None:
            best = max(best, ti - start)
            n_long += (ti - start) > PX4_STALE_S
            start = None
    if start is not None:
        best = max(best, t.iloc[-1] - start)
        n_long += (t.iloc[-1] - start) > PX4_STALE_S
    return best, n_long


def visibility_table(runs):
    rows = []
    for name, d in runs.items():
        hd = np.hypot(d.dx - d.tx, d.dy - d.ty)
        cam_h = d.dz + CAMERA_OFFSET[2]
        dep = np.degrees(np.arctan2(cam_h, hd))
        for pitch in PITCHES:
            foot = in_frame(*project(d, pitch, 0.0))
            head = in_frame(*project(d, pitch, TARGET_HEIGHT_M))
            gap, n_long = longest_gap(d.tt, foot)
            gimbal = in_frame(*project(d, pitch, 0.0, gimbal=True))
            rows.append({"senaryo": name, "egim": pitch, "ayak_kadrajda": foot.mean() * 100,
                         "gimbal_ayak_kadrajda": gimbal.mean() * 100,
                         "tum_vucut": (foot & head).mean() * 100, "en_uzun_kayip_s": gap, "kayip_3s_ustu": n_long,
                         "ortalama_bakis_acisi": dep.mean(), "bakis_acisi_min": dep.quantile(0.02),
                         "bakis_acisi_max": dep.quantile(0.98)})
    return pd.DataFrame(rows)


def scenario_key(name):
    nums = [float(x) for x in "".join(c if c.isdigit() or c == "." else " " for c in name).split()]
    return nums if nums else [0]


def plot_visibility(table, out):
    names = sorted(table.senaryo.unique(), key=scenario_key)
    grid = np.array([[table[(table.senaryo == n) & (table.egim == p)].ayak_kadrajda.iloc[0] for p in PITCHES]
                     for n in names])
    fig, ax = plt.subplots(figsize=(11, 0.55 * len(names) + 1.8))
    im = ax.imshow(grid, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(PITCHES)), [f"{p}°" for p in PITCHES])
    ax.set_yticks(range(len(names)), [n.replace("ht", "yük. ").replace("_dst", " m / mes. ") + " m" for n in names])
    for i in range(len(names)):
        for j in range(len(PITCHES)):
            ax.text(j, i, f"{grid[i, j]:.0f}", ha="center", va="center", fontsize=8,
                    color="black" if 25 < grid[i, j] < 90 else "white")
    ax.set_xlabel("Kamera eğimi (aşağı)")
    ax.set_title("Hedefin ayak noktası kadrajda (% süre) — test parkuru, Follow Me")
    fig.colorbar(im, ax=ax, fraction=0.025)
    fig.tight_layout()
    fig.savefig(out / "kadraj_isi_haritasi.png", dpi=130)
    plt.close(fig)


def plot_pixel_timeline(d, name, out, pitches=(0, 20, 40, 55)):
    fig, ax = plt.subplots(figsize=(11, 4))
    for p in pitches:
        _, v, depth = project(d, p, 0.0)
        v = np.where(depth > 0, v, np.nan)
        ax.plot(d.tt, v, label=f"eğim {p}°", lw=1.2)
    ax.axhspan(0, IMAGE_H, color="tab:green", alpha=0.08, label="kadraj (0–1296 px)")
    ax.set_ylim(IMAGE_H * 2.2, -IMAGE_H * 1.2)
    ax.set_xlabel("zaman (s)")
    ax.set_ylabel("ayak noktası v (px, aşağı +)")
    ax.set_title(f"Hedefin dikey piksel konumu — {name}")
    ax.legend(loc="lower right", fontsize=8, ncol=5)
    fig.tight_layout()
    fig.savefig(out / f"piksel_zaman_{name}.png", dpi=130)
    plt.close(fig)


# ------------------------------------------------------------------------------------------- geolocation
def yaw_deg(R):
    return np.degrees(np.arctan2(R[:, 1, 0], R[:, 0, 0]))


def geolocation_stats(d):
    """Total fix error and its parts: EKF heading error and the fix with the true (Gazebo) pose."""
    f = d.dropna(subset=["fix_err"])
    if f.empty:
        return None
    # true heading (NED) from Gazebo, EKF heading from PX4
    R_true = T_ENU_NED @ quat_matrices(d.qw, d.qx, d.qy, d.qz) @ F_FLU_FRD
    out = {"n": int(len(f)), "medyan_m": f.fix_err.median(), "p95_m": f.fix_err.quantile(0.95),
           "ortalama_kuzey_m": f.fix_err_n.mean(), "ortalama_dogu_m": f.fix_err_e.mean(),
           "ortalama_kamera_yuksekligi_m": f.fix_h.mean(), "ortalama_bakis_acisi": f.fix_dep.mean()}
    if "ekf_qw" in d:
        e = d.dropna(subset=["ekf_qw"])
        R_ekf = quat_matrices(e.ekf_qw, e.ekf_qx, e.ekf_qy, e.ekf_qz)
        dyaw = (yaw_deg(R_ekf) - yaw_deg(R_true[e.index]) + 180) % 360 - 180
        # the two poses are sampled ~tens of ms apart: compare only while the drone barely turns
        true_yaw = np.unwrap(np.radians(yaw_deg(R_true)))
        rate = np.degrees(np.abs(np.gradient(true_yaw, d.tt.to_numpy())))[e.index]
        calm = rate < 5.0
        out["ekf_yon_hatasi_ort_derece"] = float(np.mean(dyaw[calm]))
        out["ekf_yon_hatasi_std_derece"] = float(np.std(dyaw[calm]))
        true_d = -(d.dz[e.index] + BASE_LINK_Z_IN_MODEL)  # base_link down, world z = 0 at the ground
        out["ekf_yukseklik_hatasi_ort_m"] = float(np.mean(-(e.ekf_d - BODY_HEIGHT_LANDED_M) - (-true_d)))
    # fix with the true pose at the frame time + the detected pixel: what is left is detector + flat-ground error
    true_errs = []
    t_sim = d.sim_t.to_numpy()
    for _, r in f.iterrows():
        k = np.searchsorted(t_sim, r.fix_sim_t)
        if k <= 0 or k >= len(d):
            continue
        w = (r.fix_sim_t - t_sim[k - 1]) / max(1e-9, t_sim[k] - t_sim[k - 1])
        a, b = d.iloc[k - 1], d.iloc[k]
        lerp = lambda c: a[c] + w * (b[c] - a[c])  # noqa: E731
        R = quat_matrices(*[np.array([lerp(c)]) for c in ("qw", "qx", "qy", "qz")])[0]
        R /= np.cbrt(np.linalg.det(R))
        base = np.array([lerp("dx"), lerp("dy"), lerp("dz")]) + R @ np.array([0, 0, BASE_LINK_Z_IN_MODEL])
        R_ned = T_ENU_NED @ R @ F_FLU_FRD
        q = _dcm_to_quat(R_ned)
        cam = geoloc.CameraModel.from_hfov(HFOV_RAD, IMAGE_W, IMAGE_H, pitch_down_deg=PITCH_FOR_GEO,
                                           offset_frd=(CAMERA_OFFSET[0], -CAMERA_OFFSET[1],
                                                       -(CAMERA_OFFSET[2] - BASE_LINK_Z_IN_MODEL)))
        if not np.isfinite(r.det_u) or not np.isfinite(r.det_v):
            continue
        fix = geoloc.pixel_to_ground(cam, r.det_u, r.det_v, q, (base[1], base[0], -base[2]), 0.0)
        if fix is None:
            continue
        true_errs.append(math.hypot(fix.north - lerp("ty"), fix.east - lerp("tx")))
    if true_errs:
        out["gercek_poz_ile_medyan_m"] = float(np.median(true_errs))
        out["gercek_poz_ile_p95_m"] = float(np.quantile(true_errs, 0.95))
    return out


PITCH_FOR_GEO = 40.0


def _dcm_to_quat(R):
    w = math.sqrt(max(0.0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
    x = math.copysign(math.sqrt(max(0.0, 1 + R[0, 0] - R[1, 1] - R[2, 2])) / 2, R[2, 1] - R[1, 2])
    y = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] + R[1, 1] - R[2, 2])) / 2, R[0, 2] - R[2, 0])
    z = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] - R[1, 1] + R[2, 2])) / 2, R[1, 0] - R[0, 1])
    return w, x, y, z


def plot_geolocation(runs, out):
    names = [n for n, d in runs.items() if d.fix_err.notna().any()]
    if not names:
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    for n in names:
        d = runs[n]
        axes[0].plot(d.tt, d.fix_err, lw=0.8, label=n)
        f = d.dropna(subset=["fix_err"])
        axes[1].scatter(f.fix_err_e, f.fix_err_n, s=3, alpha=0.4, label=n)
    axes[0].set_xlabel("zaman (s)")
    axes[0].set_ylabel("yatay hata (m)")
    axes[0].set_title("Kameradan hesaplanan hedef konumunun hatası")
    axes[0].legend(fontsize=7)
    axes[1].axhline(0, color="gray", lw=0.5)
    axes[1].axvline(0, color="gray", lw=0.5)
    axes[1].set_aspect("equal")
    axes[1].set_xlabel("doğu hatası (m)")
    axes[1].set_ylabel("kuzey hatası (m)")
    axes[1].set_title("Hata dağılımı")
    fig.tight_layout()
    fig.savefig(out / "geolocation_hata.png", dpi=130)
    plt.close(fig)


# ------------------------------------------------------------------------------------------- tracking
def tracking_stats(d, meta):
    hd = np.hypot(d.dx - d.tx, d.dy - d.ty)
    dst = meta.get("dst", float("nan"))
    ht = meta.get("ht", float("nan"))
    foot = in_frame(*project(d, PITCH_FOR_GEO, 0.0))
    gap, n_long = longest_gap(d.tt, foot)
    # time since the last FOLLOW_TARGET that reached PX4
    last, ages = d.tt.iloc[0], []
    for t, n in zip(d.tt, d.ft_delivered):
        if n > 0:
            last = t
        ages.append(t - last)
    ages = np.array(ages)
    return {"mesafe_ort_m": hd.mean(), "mesafe_hatasi_rms_m": float(np.sqrt(np.mean((hd - dst) ** 2))),
            "mesafe_max_m": hd.max(), "mesafe_min_m": hd.min(), "yukseklik_ort_m": (d.dz + BASE_LINK_Z_IN_MODEL).mean(),
            "hedef_ht_m": ht, "hedef_dst_m": dst, "ayak_kadrajda_yuzde": foot.mean() * 100,
            "en_uzun_kayip_s": gap, "kayip_3s_ustu": n_long,
            "ft_yok_3s_ustu_yuzde": float(np.mean(ages > PX4_STALE_S) * 100), "ft_bosluk_max_s": float(ages.max()),
            "sure_s": d.tt.iloc[-1]}


def plot_tracking(runs, metas, out, tag):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for n, d in runs.items():
        hd = np.hypot(d.dx - d.tx, d.dy - d.ty)
        axes[0].plot(d.tt, hd, lw=1, label=n)
    axes[0].set_xlabel("zaman (s)")
    axes[0].set_ylabel("hedef–drone yatay mesafe (m)")
    axes[0].set_title("Takip mesafesi")
    axes[0].legend(fontsize=7)
    ref = next((n for n in ("ht8_dst8", "acik_ht8_dst8", "gecikme0_kayip0") if n in runs), next(iter(runs)))
    d = runs[ref]
    axes[1].plot(d.tx, d.ty, "r-", lw=2.5, label="hedef (parkur)")
    axes[1].plot(d.dx, d.dy, "b-", lw=1.2, label=f"drone ({ref})")
    for k in range(0, len(d), 100):  # every 5 s: drone -> target line
        axes[1].plot([d.dx[k], d.tx[k]], [d.dy[k], d.ty[k]], color="gray", lw=0.6)
        axes[1].annotate(f"{d.tt[k]:.0f}s", (d.tx[k], d.ty[k]), fontsize=6, color="darkred")
    axes[1].set_aspect("equal")
    axes[1].set_xlabel("doğu (m)")
    axes[1].set_ylabel("kuzey (m)")
    axes[1].set_title("Üstten görünüş")
    axes[1].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(out / f"takip_{tag}.png", dpi=130)
    plt.close(fig)


def fmt_table(df, floatfmt=1):
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(f"{v:.{floatfmt}f}" if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(lines)


def analyse(directory):
    global PITCH_FOR_GEO
    out = Path(directory)
    runs, meta = load(out)
    if not runs:
        print(f"{out}: CSV yok")
        return
    if meta:
        PITCH_FOR_GEO = float(next(iter(meta.values())).get("egim", PITCH_FOR_GEO))
    report = [f"# {out.name}\n", f"Kamera eğimi (uçuşta): {PITCH_FOR_GEO:g}°\n"]
    result = {"egim": PITCH_FOR_GEO}

    vis = visibility_table(runs)
    vis.to_csv(out / "kadraj_tablosu.csv", index=False)
    plot_visibility(vis, out)
    best = vis.loc[vis.groupby("senaryo").ayak_kadrajda.idxmax()]
    report.append("## Her geometri için en iyi kamera eğimi (ayak noktası kadrajda)\n")
    report.append(fmt_table(best[["senaryo", "egim", "ayak_kadrajda", "tum_vucut", "en_uzun_kayip_s",
                                  "ortalama_bakis_acisi", "bakis_acisi_min", "bakis_acisi_max"]]))
    piv = vis.pivot(index="senaryo", columns="egim", values="ayak_kadrajda")
    report.append("\n## Ayak noktası kadrajda (%), satır = geometri, sütun = eğim\n")
    report.append(fmt_table(piv.reset_index(), 0))
    gpiv = vis.pivot(index="senaryo", columns="egim", values="gimbal_ayak_kadrajda")
    report.append("\n## Gimbal ile (roll/pitch dengeli) ayak noktası kadrajda (%)\n")
    report.append(fmt_table(gpiv.reset_index(), 0))
    result["kadraj"] = vis.to_dict(orient="records")
    first = sorted(runs, key=lambda n: (abs(scenario_key(n)[0] - 8) + abs(scenario_key(n)[-1] - 8), n))[0]
    plot_pixel_timeline(runs[first], first, out)

    geo = {n: s for n, d in runs.items() if (s := geolocation_stats(d)) is not None}
    if geo:
        result["geolocation"] = geo
        report.append("\n## Geolocation (kameradan hedef konumu)\n")
        report.append(fmt_table(pd.DataFrame([{"senaryo": n, **s} for n, s in geo.items()]), 2))
        plot_geolocation(runs, out)

    trk = {n: tracking_stats(d, meta.get(n, {})) for n, d in runs.items()}
    for n in trk:
        m = meta.get(n, {})
        trk[n].update(ft_gecikme_s=m.get("ft_delay", 0.0), ft_kayip=m.get("ft_loss", 0.0),
                      ft_patlama=m.get("ft_burst", 1.0), kaynak=m.get("kaynak", ""))
    result["takip"] = trk
    report.append(f"\n## Takip (kamera eğimi {PITCH_FOR_GEO:g}° ile görünürlük)\n")
    report.append(fmt_table(pd.DataFrame([{"senaryo": n, **{k: v for k, v in s.items()}} for n, s in trk.items()]), 2))
    plot_tracking(runs, meta, out, out.name)

    (out / "ozet.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    (out / "analiz.json").write_text(json.dumps(result, indent=1, ensure_ascii=False, default=float))
    print("\n".join(report))


if __name__ == "__main__":
    for arg in sys.argv[1:] or ["sonuclar"]:
        analyse(arg)
