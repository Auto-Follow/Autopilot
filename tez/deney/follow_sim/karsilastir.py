#!/usr/bin/env python3
"""Compact comparison of deney.py runs: one row per scenario, or (--tekrar) mean / worst over repeated runs.

  python3 karsilastir.py sonuclar/kalman_egim45
  python3 karsilastir.py --tekrar sonuclar/opt_egik_r1 sonuclar/opt_egik_r2
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


def longest_run(mask, t):
    best, start = 0.0, None
    for ti, m in zip(t, mask):
        if m and start is None:
            start = ti
        elif not m and start is not None:
            best, start = max(best, ti - start), None
    if start is not None:
        best = max(best, t[-1] - start)
    return best


def pitch_deg(d):
    w, x, y, z = d["qw"], d["qx"], d["qy"], d["qz"]
    return np.degrees(np.arcsin(np.clip(2 * (w * y - z * x), -1, 1)))


def summarize(csv, dst):
    d = pd.read_csv(csv)
    t = d["t"].to_numpy() - d["t"].iloc[0]
    dist = np.hypot(d["dx"] - d["tx"], d["dy"] - d["ty"]).to_numpy()
    seen = (d["det_seen"].fillna(0).astype(bool) & ~d["det_clip"].fillna(0).astype(bool)).to_numpy()
    dt = np.gradient(t)
    speed = np.hypot(np.gradient(d["dx"].to_numpy()) / dt, np.gradient(d["dy"].to_numpy()) / dt)
    pitch = np.abs(pitch_deg(d))
    err = d["fix_err"].dropna() if "fix_err" in d else pd.Series(dtype=float)
    banded = "band_dst" in d and d["band_dst"].notna().any()
    ref = d["band_dst"].to_numpy() if banded else np.full(len(d), dst)
    end_dist = dist[-int(5 / np.median(dt)):].mean()
    return {
        "kadrajda_%": 100 * seen.mean(),
        "en_uzun_kayip_s": longest_run(~seen, t),
        "mesafe_ort": dist.mean(),
        "mesafe_max": dist.max(),
        "hata_rms_m": float(np.sqrt(np.nanmean((dist - ref) ** 2))),
        "son_mesafe": end_dist,
        "koptu": "EVET" if end_dist > 2.5 * np.nanmean(ref) else "hayır",  # target lost and left behind
        "geo_medyan": err.median() if len(err) else math.nan,
        "geo_p95": err.quantile(0.95) if len(err) else math.nan,
        "hiz_p99": np.percentile(speed, 99),
        "egim_p95": np.percentile(pitch, 95),
        "egim_max": pitch.max(),
    }


def runs(folders):
    for folder in map(Path, folders):
        meta = json.loads((folder / "ozet.json").read_text())
        for sc in meta["senaryolar"]:
            csv = folder / f"{sc['name']}.csv"
            if csv.exists():
                yield folder, meta["egim"], sc, summarize(csv, sc["dst"])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("klasorler", nargs="+")
    p.add_argument("--tekrar", action="store_true", help="group same-named scenarios of several folders")
    args = p.parse_args()
    pd.set_option("display.width", 250)
    rows = [{"senaryo": sc["name"], "egim": egim, "ht": sc["ht"], "dst": sc["dst"], "tur": folder.name, **r}
            for folder, egim, sc, r in runs(args.klasorler)]
    df = pd.DataFrame(rows)
    if not args.tekrar:
        print(df.drop(columns=["tur"]).set_index("senaryo").round(2).to_string())
        return
    df["aci"] = np.degrees(np.arctan2(df["ht"], df["dst"])).round()
    df["koptu_n"] = (df["koptu"] == "EVET").astype(int)
    g = df.groupby(["egim", "senaryo", "aci"])
    out = pd.DataFrame({
        "tur": g.size(), "koptu": g["koptu_n"].sum(),
        "kadraj_ort": g["kadrajda_%"].mean(), "kadraj_min": g["kadrajda_%"].min(),
        "kayip_max_s": g["en_uzun_kayip_s"].max(), "rms_ort": g["hata_rms_m"].mean(),
        "geo_med": g["geo_medyan"].mean(), "geo_p95": g["geo_p95"].mean(), "egim_p95": g["egim_p95"].mean(),
    })
    print(out.round(2).to_string())


if __name__ == "__main__":
    main()
