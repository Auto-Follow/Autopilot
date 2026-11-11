#!/usr/bin/env python3
"""AUTO FOLLOW (M15) log analizi: ULog'dan senaryo ölçülerini çıkarır.

Script bir PX4 ULog dosyasını (pyulog 1.2.4) okur, logdaki her AUTO FOLLOW
bölümünü (modun açıldığı andan kapandığı ana kadar) kendisi bulur ve her bölüm
için spec Bölüm 11 tablosunun "Ölçüm" sütunundaki ölçüleri hesaplar: mesafe
hatası, oturma süresi, aşma, salınım, kırpma, burun hatası, hız isteği,
filtrenin girdisi ve çıktısı, durum geçiş süreleri, Hold süresi, atılan mesaj
sayaçları ve gecikme. Alan adları log sözlüğüyle aynıdır (log-sozlugu.md).

Kullanım:
    tez/analiz/af_log_analiz.py LOG.ulg
    tez/analiz/af_log_analiz.py LOG.ulg --aralik 60 120
    tez/analiz/af_log_analiz.py LOG.ulg --grafik ~/grafikler --csv sonuc.csv

Seçenekler:
    --aralik BAS BIT  Yalnızca bu zaman aralığına bak [s, PX4 açılışından beri].
    --grafik KLASOR   Her bölüm için PNG grafikleri bu klasöre yazar.
    --csv DOSYA       Bütün ölçüleri bir CSV dosyasına yazar.

Rehber (her ölçünün anlamı, iyi/kötü örnekler, grafiklerin okunuşu):
tez/analiz/BENIOKU.md
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from pyulog import ULog

# --- Ölçü ayarları -----------------------------------------------------------

# Mesafe hatası bu bandın içine girip çıkmazsa "oturdu" [m] (karar 2026-11-11)
OTURMA_BANDI_M = 0.3
# Burun hatası (gerçek yön − hedef yönü) bu bandın içine girip çıkmazsa "hedefte" [deg]
BURUN_BANDI_DERECE = 2.0
# Salınım sayımında hatanın işaret değiştirdiği sayılan en küçük genlik [m]
ISARET_ESIGI_M = 0.1
SON_PENCERE_S = 5.0  # "son değer" ortalamaları için bölüm sonundaki pencere
HIZ_PENCERESI_S = 1.0  # ölçümlerden türetilen hedef hızı için zaman farkı
KIRPMA_PAYI = 1e-3  # [m/s] yasa çıkışı AF_VEL_MAX'ı bundan fazla geçerse kırpma sayılır

KONULAR = [
    "auto_follow_status",
    "vehicle_status",
    "vehicle_local_position",
    "vehicle_command",
]

PARAMETRELER = [
    "AF_K_DIST",
    "AF_K_FF",
    "AF_VEL_MAX",
    "AF_ACC_MAX",
    "AF_ALPHA",
    "AF_BETA",
    "AF_TRK_ANG",
    "AF_TGT_HGT",
    "AF_DATA_TOUT",
    "AF_LOST_T",
    "AF_YAWRATE_MAX",
    "AF_YAW_MIN_D",
]

DURUMLAR = {0: "PASIF", 1: "TAKIP", 2: "KAYIP_BEKLE", 3: "HOLD_ISTENDI"}
STATE_TAKIP = 1
STATE_KAYIP_BEKLE = 2
STATE_HOLD_ISTENDI = 3
NAV_STATE_HOLD = 4  # NAVIGATION_STATE_AUTO_LOITER (VehicleStatus.msg:40)
VEHICLE_CMD_SET_NAV_STATE = 100001  # VehicleCommand.msg:114

MOD_ADLARI = {
    0: "Manual",
    1: "Altitude",
    2: "Position",
    3: "Mission",
    4: "Hold",
    5: "RTL",
    6: "Position Slow",
    10: "Acro",
    12: "Descend",
    13: "Termination",
    14: "Offboard",
    15: "Stabilized",
    17: "Takeoff",
    18: "Land",
    19: "Follow Me (PX4'ün, AUTO FOLLOW değil)",
    20: "Precision Land",
    21: "Orbit",
}

SAYACLAR = [
    "accept_count",
    "no_target_count",
    "reject_name_count",
    "reject_nonfinite_count",
    "reject_norm_count",
    "reject_seq_count",
    "reject_age_count",
    "reject_position_count",
    "reject_depression_count",
    "reject_range_count",
]

Dizi = np.ndarray


@dataclass
class Olcu:
    """Tablodaki tek bir satır."""

    grup: str
    ad: str
    deger: float | str  # tam sayılar (int) ondalıksız yazılır
    birim: str = ""
    aciklama: str = ""


@dataclass
class Bolum:
    """Bir AUTO FOLLOW bölümü: auto_follow_status örneklerinin [i0, i1] aralığı."""

    no: int
    i0: int
    i1: int
    bas: float
    bit: float
    basi_kesik: bool = False  # mod, log ya da --aralik başlamadan önce açıktı
    sonu_kesik: bool = False  # mod, log ya da --aralik bittiğinde hâlâ açıktı


@dataclass
class LogVerisi:
    """ULog'dan okunan konular ve parametreler (zaman: PX4 açılışından beri saniye)."""

    yol: Path
    konular: dict[str, dict[str, Dizi]]
    ilk_parametreler: dict[str, float]
    degisen_parametreler: list[tuple[float, str, float]]
    bas: float
    bit: float
    mesajlar: list[tuple[float, str]] = field(default_factory=list)

    def zaman(self, konu: str) -> Dizi:
        """Konunun zaman damgaları [s]."""
        return self.konular[konu]["timestamp"] * 1e-6

    def parametre(self, ad: str, t: float) -> float:
        """Parametrenin t anındaki değeri (log başındaki değer + t'ye kadarki değişiklikler)."""
        deger = self.ilk_parametreler.get(ad, math.nan)
        for zaman, degisen_ad, yeni in self.degisen_parametreler:
            if degisen_ad == ad and zaman <= t:
                deger = yeni
        return float(deger)


# --- Okuma ve bölümler -------------------------------------------------------


def log_oku(yol: Path) -> LogVerisi:
    """ULog'u okur; yalnızca gereken konuları ve parametreleri alır."""
    ulog = ULog(str(yol), KONULAR)
    konular = {ds.name: ds.data for ds in ulog.data_list if ds.multi_id == 0}
    if "auto_follow_status" not in konular:
        raise ValueError(
            "logda auto_follow_status yok (AUTO FOLLOW modülü çalışmamış ya da "
            "log bu modül eklenmeden önce alınmış)"
        )
    degisen = [(t * 1e-6, ad, float(v)) for t, ad, v in ulog.changed_parameters]
    mesajlar = [(m.timestamp * 1e-6, m.message) for m in ulog.logged_messages]
    return LogVerisi(
        yol=yol,
        konular=konular,
        ilk_parametreler={k: float(v) for k, v in ulog.initial_parameters.items()},
        degisen_parametreler=degisen,
        bas=ulog.start_timestamp * 1e-6,
        bit=ulog.last_timestamp * 1e-6,
        mesajlar=mesajlar,
    )


def bolumleri_bul(log: LogVerisi, aralik: tuple[float, float] | None) -> list[Bolum]:
    """mode_active = 1 olan ardışık örnek gruplarını (bölümleri) bulur."""
    af = log.konular["auto_follow_status"]
    t = log.zaman("auto_follow_status")
    aktif = af["mode_active"].astype(bool)
    if aralik is not None:
        aktif = aktif & (t >= aralik[0]) & (t <= aralik[1])
    if not aktif.any():
        return []
    fark = np.diff(aktif.astype(int))
    baslar = list(np.nonzero(fark == 1)[0] + 1)
    bitler = list(np.nonzero(fark == -1)[0])
    if aktif[0]:
        baslar.insert(0, 0)
    if aktif[-1]:
        bitler.append(len(aktif) - 1)
    tum_aktif = af["mode_active"].astype(bool)
    bolumler = []
    for no, (i0, i1) in enumerate(zip(baslar, bitler), start=1):
        basi = i0 == 0 or bool(tum_aktif[i0 - 1])
        sonu = i1 == len(t) - 1 or bool(tum_aktif[i1 + 1])
        bolumler.append(
            Bolum(no, int(i0), int(i1), float(t[i0]), float(t[i1]), basi, sonu)
        )
    return bolumler


# --- Yardımcı hesaplar --------------------------------------------------------


def sar(aci: Dizi) -> Dizi:
    """Açıyı (-pi, pi] aralığına sarar [rad]."""
    return np.angle(np.exp(1j * aci))


def ara_deger(t: Dizi, t_kaynak: Dizi, deger: Dizi) -> Dizi:
    """Bir konunun değerini başka zamanlara doğrusal ara değerle taşır."""
    return np.interp(t, t_kaynak, deger)


def isaret_degisimi(x: Dizi, esik: float) -> int:
    """x'in +esik üstünden -esik altına (ya da tersi) geçiş sayısı."""
    sayi = 0
    onceki = 0
    for v in x:
        if v > esik:
            isaret = 1
        elif v < -esik:
            isaret = -1
        else:
            continue
        if onceki != 0 and isaret != onceki:
            sayi += 1
        onceki = isaret
    return sayi


def istatistik(x: Dizi) -> tuple[float, float, float, float]:
    """Sonlu değerlerin ortalaması, std'si, en küçüğü ve en büyüğü (yoksa NaN)."""
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return (math.nan, math.nan, math.nan, math.nan)
    return (float(x.mean()), float(x.std()), float(x.min()), float(x.max()))


def ortalama(x: Dizi) -> float:
    """Sonlu değerlerin ortalaması (yoksa NaN)."""
    return istatistik(x)[0]


def en_buyuk_mutlak(x: Dizi) -> float:
    """Sonlu değerlerin en büyük mutlak değeri (yoksa NaN)."""
    x = x[np.isfinite(x)]
    return float(np.abs(x).max()) if len(x) else math.nan


def mod_adi(nav_state: int, mod_no: int) -> str:
    """nav_state numarasının okunur adı."""
    if nav_state == mod_no and mod_no != 0:
        return "AUTO FOLLOW"
    if 23 <= nav_state <= 30:
        return f"External {nav_state - 22}"
    return MOD_ADLARI.get(nav_state, f"nav_state {nav_state}")


def sayac_artis(af: dict[str, Dizi], ad: str, b: Bolum) -> int:
    """Sayaç alanının bölüm boyunca artışı (girişten önceki çevrime göre)."""
    x = af[ad].astype(np.int64)
    once = x[b.i0 - 1] if b.i0 > 0 else x[b.i0]
    return int(x[b.i1] - once)


# --- Ölçüler ------------------------------------------------------------------


@dataclass
class BolumVerisi:
    """Bir bölümün ölçülerde ve grafiklerde ortak kullanılan dizileri."""

    t: Dizi
    durum: Dizi
    takip: Dizi
    hata: Dizi
    istenen: Dizi
    yaw_cmd: Dizi
    gercek_yon: Dizi
    hedef_yonu: Dizi
    yasa: Dizi
    komut: Dizi
    hedef_hiz: Dizi
    olcum: Dizi
    kestirim: Dizi
    guncellendi: Dizi
    drone_xy: Dizi
    drone_hiz: Dizi
    vel_max: float


def bolum_verisi(log: LogVerisi, b: Bolum) -> BolumVerisi:
    """Bölümün dizilerini hazırlar (drone konumu ve yönü auto_follow_status zamanlarına taşınır)."""
    af = log.konular["auto_follow_status"]
    sl = slice(b.i0, b.i1 + 1)
    t = log.zaman("auto_follow_status")[sl]
    lp = log.konular["vehicle_local_position"]
    t_lp = log.zaman("vehicle_local_position")
    yon = sar(ara_deger(t, t_lp, np.unwrap(lp["heading"])))
    dx = ara_deger(t, t_lp, lp["x"])
    dy = ara_deger(t, t_lp, lp["y"])
    vx = ara_deger(t, t_lp, lp["vx"])
    vy = ara_deger(t, t_lp, lp["vy"])
    est = np.stack([af["target_est_ned[0]"][sl], af["target_est_ned[1]"][sl]], 1)
    durum = af["state"][sl].astype(int)
    hata = af["range_est"][sl] - af["range_desired"][sl]
    return BolumVerisi(
        t=t,
        durum=durum,
        takip=(durum == STATE_TAKIP) & np.isfinite(hata),
        hata=hata,
        istenen=af["range_desired"][sl],
        yaw_cmd=af["yaw_cmd"][sl],
        gercek_yon=yon,
        hedef_yonu=np.arctan2(est[:, 1] - dy, est[:, 0] - dx),
        yasa=np.stack([af["vel_cmd_law[0]"][sl], af["vel_cmd_law[1]"][sl]], 1),
        komut=np.stack([af["vel_cmd[0]"][sl], af["vel_cmd[1]"][sl]], 1),
        hedef_hiz=np.stack(
            [af["target_vel_ned[0]"][sl], af["target_vel_ned[1]"][sl]], 1
        ),
        olcum=np.stack([af["target_meas_ned[0]"][sl], af["target_meas_ned[1]"][sl]], 1),
        kestirim=est,
        guncellendi=af["filter_updated"][sl].astype(bool),
        drone_xy=np.stack([dx, dy], 1),
        drone_hiz=np.hypot(vx, vy),
        vel_max=log.parametre("AF_VEL_MAX", b.bas),
    )


def cikis_bul(log: LogVerisi, b: Bolum, mod_no: int) -> tuple[float, int] | None:
    """Bölümden sonra PX4'ün geçtiği mod: (zaman, nav_state); log mod açıkken bittiyse None."""
    vs = log.konular["vehicle_status"]
    t_vs = log.zaman("vehicle_status")
    nav = vs["nav_state"].astype(int)
    aday = np.nonzero((t_vs > b.bit - 0.05) & (nav != mod_no))[0]
    if len(aday) == 0:
        return None
    return float(t_vs[aday[0]]), int(nav[aday[0]])


def kabul_varislari(log: LogVerisi) -> tuple[Dizi, Dizi]:
    """Kabul edilen ve "hedef yok" mesajlarının Pixhawk'a varış anları [s]."""
    af = log.konular["auto_follow_status"]
    varis = af["los_timestamp"] * 1e-6
    kabul = np.nonzero(np.diff(af["accept_count"].astype(np.int64)) > 0)[0] + 1
    hedef_yok = np.nonzero(np.diff(af["no_target_count"].astype(np.int64)) > 0)[0] + 1
    return varis[kabul], varis[hedef_yok]


def durum_gecisleri(log: LogVerisi, b: Bolum, bv: BolumVerisi) -> list[Olcu]:
    """Bölüm içindeki durum geçişleri ve her geçişin nedenine göre süresi."""
    kabul, hedef_yok = kabul_varislari(log)
    satirlar = [
        Olcu(
            "Durum",
            "Girişteki durum",
            DURUMLAR.get(int(bv.durum[0]), str(bv.durum[0])),
            "",
            f"t = {bv.t[0]:.3f} s",
        )
    ]
    degisim = np.nonzero(np.diff(bv.durum) != 0)[0] + 1
    kayip_bas = bv.t[0] if bv.durum[0] == STATE_KAYIP_BEKLE else math.nan
    for k, i in enumerate(degisim, start=1):
        eski, yeni, tk = int(bv.durum[i - 1]), int(bv.durum[i]), float(bv.t[i])
        ad = f"Geçiş {k}: {DURUMLAR.get(eski, eski)} → {DURUMLAR.get(yeni, yeni)}"
        aciklama = f"t = {tk:.3f} s"
        sure: float | str = "—"
        if yeni == STATE_KAYIP_BEKLE:
            kayip_bas = tk
            once = kabul[kabul <= tk]
            son_gecerli = float(once[-1]) if len(once) else math.nan
            yok = hedef_yok[(hedef_yok > son_gecerli) & (hedef_yok <= tk)]
            if len(yok):
                sure = tk - float(yok[0])
                aciklama += "; neden: 'hedef yok'; süre ilk 'hedef yok' mesajından"
            else:
                sure = tk - max(son_gecerli, b.bas)
                aciklama += "; neden: geçerli veri yok; süre son geçerli mesajdan (ya da girişten)"
        elif yeni == STATE_HOLD_ISTENDI:
            sure = tk - kayip_bas
            aciklama += "; süre KAYIP_BEKLE'nin başından"
        elif yeni == STATE_TAKIP and eski == STATE_KAYIP_BEKLE:
            sure = tk - kayip_bas
            aciklama += "; geçerli veri geri geldi; süre KAYIP_BEKLE'de geçen"
        satirlar.append(Olcu("Durum", ad, sure, "s", aciklama))
    return satirlar


def hold_olculeri(
    log: LogVerisi, b: Bolum, cikis: tuple[float, int] | None
) -> list[Olcu]:
    """Çıkış Hold ise: son geçerli mesaj / ilk 'hedef yok' / giriş / istek → nav_state 4 süreleri."""
    af = log.konular["auto_follow_status"]
    satirlar = [
        Olcu(
            "Hold",
            "hold_request_count (en büyük)",
            int(af["hold_request_count"][b.i0 : b.i1 + 1].max()),
            "adet",
            "1 = tek istek, PX4 kabul etti; 3 = üç istek de kabul edilmedi",
        )
    ]
    if cikis is None or cikis[1] != NAV_STATE_HOLD:
        return satirlar
    t4 = cikis[0]
    data_tout = log.parametre("AF_DATA_TOUT", b.bas)
    kabul, hedef_yok = kabul_varislari(log)
    once = kabul[(kabul <= t4) & (kabul >= b.bas - data_tout)]
    if len(once):
        son_gecerli = float(once[-1])
        satirlar.append(
            Olcu(
                "Hold",
                "Son geçerli mesaj → nav_state = 4",
                t4 - son_gecerli,
                "s",
                f"son geçerli mesajın varışı t = {son_gecerli:.3f} s; beklenen ≈ AF_DATA_TOUT + AF_LOST_T",
            )
        )
        yok = hedef_yok[(hedef_yok > son_gecerli) & (hedef_yok <= t4)]
        if len(yok):
            satirlar.append(
                Olcu(
                    "Hold",
                    "İlk 'hedef yok' → nav_state = 4",
                    t4 - float(yok[0]),
                    "s",
                    "beklenen ≈ AF_LOST_T",
                )
            )
    else:
        satirlar.append(
            Olcu(
                "Hold",
                "Giriş → nav_state = 4 (hedefsiz giriş)",
                t4 - b.bas,
                "s",
                "girişte geçerli veri yoktu; beklenen ≈ AF_DATA_TOUT + AF_LOST_T",
            )
        )
    vc = log.konular.get("vehicle_command")
    if vc is not None:
        t_vc = log.zaman("vehicle_command")
        istek = t_vc[
            (vc["command"].astype(np.int64) == VEHICLE_CMD_SET_NAV_STATE)
            & (t_vc >= b.bas)
            & (t_vc <= t4)
        ]
        if len(istek):
            satirlar.append(
                Olcu(
                    "Hold",
                    "Hold isteği (vehicle_command) → nav_state = 4",
                    t4 - float(istek[-1]),
                    "s",
                    f"istek sayısı {len(istek)}",
                )
            )
    return satirlar


def mesafe_olculeri(bv: BolumVerisi) -> list[Olcu]:
    """range_est − range_desired: ortalama, std, son değer, oturma, aşma, salınım."""
    g = "Mesafe"
    if not bv.takip.any():
        return [Olcu(g, "Mesafe hatası", "—", "", "bu bölümde TAKIP yok")]
    te, e, rd = bv.t[bv.takip], bv.hata[bv.takip], bv.istenen[bv.takip]
    ort, std, _, _ = istatistik(e)
    son = te >= te[-1] - SON_PENCERE_S
    s_ort, s_std, _, _ = istatistik(e[son])
    satirlar = [
        Olcu(g, "range_desired ortalama", ortalama(rd), "m", "istenen mesafe"),
        Olcu(g, "Mesafe hatası ilk değer", float(e[0]), "m", f"t = {te[0]:.3f} s"),
        Olcu(g, "Mesafe hatası ortalama", ort, "m"),
        Olcu(g, "Mesafe hatası std", std, "m"),
        Olcu(g, "Mesafe hatası en büyük (mutlak)", en_buyuk_mutlak(e), "m"),
        Olcu(g, "Mesafe hatası son değer", float(e[-1]), "m", f"t = {te[-1]:.3f} s"),
        Olcu(
            g,
            f"Mesafe hatası son {SON_PENCERE_S:.0f} s ortalama",
            s_ort,
            "m",
            f"std {s_std:.3f} m",
        ),
    ]
    disari = np.nonzero(np.abs(e) >= OTURMA_BANDI_M)[0]
    if len(disari) == 0:
        oturma: float | str = 0.0
        oturma_not = "başından beri bantta"
    elif disari[-1] == len(e) - 1:
        oturma = "oturmadı"
        oturma_not = f"bölüm sonunda hata ±{OTURMA_BANDI_M} m dışında"
    else:
        oturma = float(te[disari[-1] + 1] - te[0])
        oturma_not = f"hatanın ±{OTURMA_BANDI_M} m bandına girip bir daha çıkmadığı an, TAKIP başından"
    satirlar.append(
        Olcu(
            g,
            f"Oturma süresi (hata ±{OTURMA_BANDI_M} m içinde)",
            oturma,
            "s",
            oturma_not,
        )
    )
    if abs(e[0]) >= OTURMA_BANDI_M:
        isaret = math.copysign(1.0, float(e[0]))
        asma = max(0.0, float(np.max(-isaret * e)))
        satirlar.append(
            Olcu(g, "Aşma", asma, "m", "hatanın ilk işaretinin tersine en fazla geçişi")
        )
    else:
        satirlar.append(Olcu(g, "Aşma", "—", "m", "başlangıçta zaten bantta"))
    satirlar.append(
        Olcu(
            g,
            "Salınım: işaret değişimi",
            isaret_degisimi(e, ISARET_ESIGI_M),
            "adet",
            f"hata +{ISARET_ESIGI_M} m ile −{ISARET_ESIGI_M} m arasında kaç kez yön değiştirdi",
        )
    )
    tepe = float(e[son].max() - e[son].min())
    satirlar.append(
        Olcu(
            g,
            f"Salınım: son {SON_PENCERE_S:.0f} s tepe-tepe",
            tepe,
            "m",
            "en büyük − en küçük hata",
        )
    )
    return satirlar


def hiz_olculeri(log: LogVerisi, b: Bolum, bv: BolumVerisi) -> list[Olcu]:
    """vel_cmd_law / vel_cmd: kırpma süresi, büyüklük, değişim hızı; drone hızı."""
    g = "Hız"
    dt = float(np.median(np.diff(bv.t))) if len(bv.t) > 1 else 0.02
    yasa = np.hypot(bv.yasa[:, 0], bv.yasa[:, 1])
    komut = np.hypot(bv.komut[:, 0], bv.komut[:, 1])
    kirpma = bv.takip & np.isfinite(yasa) & (yasa > bv.vel_max + KIRPMA_PAYI)
    ardisik = bv.takip[1:] & bv.takip[:-1]
    degisim = np.linalg.norm(np.diff(bv.komut, axis=0), axis=1) / np.diff(bv.t)
    lp = log.konular["vehicle_local_position"]
    t_lp = log.zaman("vehicle_local_position")
    m = (t_lp >= b.bas) & (t_lp <= b.bit)
    drone = np.hypot(lp["vx"][m], lp["vy"][m])
    return [
        Olcu(
            g,
            "Kırpma süresi",
            float(kirpma.sum() * dt),
            "s",
            f"vel_cmd_law büyüklüğü > AF_VEL_MAX ({bv.vel_max:g} m/s) olan süre",
        ),
        Olcu(
            g,
            "vel_cmd_law büyüklüğü en büyük",
            en_buyuk_mutlak(yasa[bv.takip]),
            "m/s",
            "kırpma öncesi",
        ),
        Olcu(g, "vel_cmd büyüklüğü ortalama (TAKIP)", ortalama(komut[bv.takip]), "m/s"),
        Olcu(
            g,
            "vel_cmd büyüklüğü en büyük",
            en_buyuk_mutlak(komut),
            "m/s",
            "PX4'e giden",
        ),
        Olcu(
            g,
            "vel_cmd değişim hızı en büyük",
            en_buyuk_mutlak(degisim[ardisik]) if ardisik.any() else math.nan,
            "m/s²",
            f"TAKIP içinde; sınır AF_ACC_MAX = {log.parametre('AF_ACC_MAX', b.bas):g}",
        ),
        Olcu(
            g,
            "Drone yatay hızı ortalama",
            ortalama(drone),
            "m/s",
            "vehicle_local_position",
        ),
        Olcu(g, "Drone yatay hızı en büyük", en_buyuk_mutlak(drone), "m/s"),
    ]


def burun_olculeri(bv: BolumVerisi) -> list[Olcu]:
    """yaw_cmd − gerçek yön, yaw_cmd − hedef yönü, gerçek yön − hedef yönü [deg]."""
    g = "Burun"
    if not bv.takip.any():
        return [Olcu(g, "Burun hatası", "—", "", "bu bölümde TAKIP yok")]
    te = bv.t[bv.takip]
    son = te >= te[-1] - SON_PENCERE_S
    cifti = [
        (
            "yaw_cmd − gerçek yön",
            bv.yaw_cmd - bv.gercek_yon,
            "PX4 komutu ne kadar izliyor",
        ),
        (
            "yaw_cmd − hedef yönü",
            bv.yaw_cmd - bv.hedef_yonu,
            "AF_YAWRATE_MAX ve yaw donması etkisi",
        ),
        (
            "gerçek yön − hedef yönü",
            bv.gercek_yon - bv.hedef_yonu,
            "burun hedefe ne kadar bakıyor",
        ),
    ]
    satirlar = []
    for ad, fark, aciklama in cifti:
        f = np.degrees(sar(fark[bv.takip]))
        satirlar.append(Olcu(g, f"{ad} ortalama", ortalama(f), "deg", aciklama))
        satirlar.append(Olcu(g, f"{ad} en büyük (mutlak)", en_buyuk_mutlak(f), "deg"))
        satirlar.append(
            Olcu(g, f"{ad} son {SON_PENCERE_S:.0f} s ortalama", ortalama(f[son]), "deg")
        )
    burun_isaretli = np.degrees(sar(bv.gercek_yon - bv.hedef_yonu))[bv.takip]
    burun = np.abs(burun_isaretli)
    if burun[0] >= BURUN_BANDI_DERECE:
        isaret = math.copysign(1.0, float(burun_isaretli[0]))
        satirlar.append(
            Olcu(
                g,
                "Burun aşması",
                max(0.0, float(np.max(-isaret * burun_isaretli))),
                "deg",
                "gerçek yön − hedef yönü, ilk işaretin tersine en fazla geçiş",
            )
        )
    disari = np.nonzero(~(burun < BURUN_BANDI_DERECE))[0]
    if len(disari) == 0:
        oturma: float | str = 0.0
    elif disari[-1] == len(burun) - 1:
        oturma = "oturmadı"
    else:
        oturma = float(te[disari[-1] + 1] - te[0])
    satirlar.append(
        Olcu(
            g,
            f"Burun oturma süresi (gerçek yön − hedef yönü ±{BURUN_BANDI_DERECE:g} deg)",
            oturma,
            "s",
            "banda girip bir daha çıkmadığı an, TAKIP başından",
        )
    )
    return satirlar


def yaw_donmasi(log: LogVerisi, b: Bolum, bv: BolumVerisi) -> Olcu:
    """yaw_frozen = 1 olan süre."""
    af = log.konular["auto_follow_status"]
    dt = float(np.median(np.diff(bv.t))) if len(bv.t) > 1 else 0.02
    donuk = af["yaw_frozen"][b.i0 : b.i1 + 1].astype(bool)
    return Olcu(
        "Burun",
        "yaw_frozen süresi",
        float(donuk.sum() * dt),
        "s",
        f"hedef AF_YAW_MIN_D ({log.parametre('AF_YAW_MIN_D', b.bas):g} m) içinde",
    )


def turetilen_hiz(t: Dizi, olcum: Dizi) -> Dizi:
    """Ölçülen hedef konumlarından ~HIZ_PENCERESI_S önceki ölçüme göre hız [m/s]."""
    hiz = np.full_like(olcum, math.nan)
    for k in range(len(t)):
        j = np.searchsorted(t, t[k] - HIZ_PENCERESI_S, side="right") - 1
        if j >= 0 and t[k] - t[j] > 0.5 * HIZ_PENCERESI_S:
            hiz[k] = (olcum[k] - olcum[j]) / (t[k] - t[j])
    return hiz


def filtre_olculeri(log: LogVerisi, b: Bolum, bv: BolumVerisi) -> list[Olcu]:
    """Filtre girdisi (target_meas_ned) ↔ çıktısı (target_est_ned, target_vel_ned)."""
    g = "Filtre"
    af = log.konular["auto_follow_status"]
    gun = (
        bv.guncellendi
        & np.all(np.isfinite(bv.olcum), 1)
        & np.all(np.isfinite(bv.kestirim), 1)
    )
    satirlar = [Olcu(g, "Ölçüm sayısı (filter_updated = 1)", int(gun.sum()), "adet")]
    if not gun.any():
        return satirlar
    sure = bv.t[-1] - bv.t[0]
    satirlar.append(
        Olcu(g, "Ölçüm hızı", float(gun.sum() / sure) if sure > 0 else math.nan, "Hz")
    )
    fark = np.linalg.norm(bv.olcum[gun] - bv.kestirim[gun], axis=1)
    ort, std, _, mx = istatistik(fark)
    satirlar += [
        Olcu(
            g,
            "Girdi–çıktı uzaklığı ortalama",
            ort,
            "m",
            "target_meas_ned ile target_est_ned arası, düzeltmeden sonra",
        ),
        Olcu(g, "Girdi–çıktı uzaklığı std", std, "m"),
        Olcu(g, "Girdi–çıktı uzaklığı en büyük", mx, "m"),
    ]
    hiz = np.hypot(bv.hedef_hiz[:, 0], bv.hedef_hiz[:, 1])
    tak = bv.takip
    te = bv.t[tak] if tak.any() else bv.t
    son = (bv.t >= te[-1] - SON_PENCERE_S) & tak
    satirlar += [
        Olcu(
            g,
            "target_vel_ned büyüklüğü ortalama (TAKIP)",
            ortalama(hiz[tak]),
            "m/s",
            "kestirilen hedef hızı",
        ),
        Olcu(
            g,
            f"target_vel_ned büyüklüğü son {SON_PENCERE_S:.0f} s ortalama",
            ortalama(hiz[son]),
            "m/s",
        ),
        Olcu(g, "target_vel_ned büyüklüğü en büyük", en_buyuk_mutlak(hiz), "m/s"),
    ]
    turev = turetilen_hiz(bv.t[gun], bv.olcum[gun])
    gun_tak = tak[gun]
    v_est = bv.hedef_hiz[gun]
    hiz_farki = np.linalg.norm(turev - v_est, axis=1)
    satirlar += [
        Olcu(
            g,
            f"Ölçümlerden türetilen hız ortalama (TAKIP, {HIZ_PENCERESI_S:g} s pencere)",
            ortalama(np.hypot(turev[gun_tak, 0], turev[gun_tak, 1])),
            "m/s",
        ),
        Olcu(
            g,
            "Türetilen hız ile target_vel_ned farkı ortalama (TAKIP)",
            ortalama(hiz_farki[gun_tak]),
            "m/s",
            "filtrenin hız kestirimi ölçümlerle ne kadar uyumlu",
        ),
    ]
    lat = af["latency"][b.i0 : b.i1 + 1][bv.guncellendi]
    l_ort, _, l_min, l_max = istatistik(lat)
    satirlar += [
        Olcu("Girdi", "latency ortalama", l_ort, "ms", "kabul edilen mesajlar"),
        Olcu("Girdi", "latency en küçük", l_min, "ms"),
        Olcu("Girdi", "latency en büyük", l_max, "ms"),
    ]
    return satirlar


def girdi_olculeri(log: LogVerisi, b: Bolum) -> list[Olcu]:
    """Kabul / hedef yok / atılan mesaj sayaçlarının bölüm içindeki artışı."""
    af = log.konular["auto_follow_status"]
    return [
        Olcu("Girdi", f"{ad} artışı", sayac_artis(af, ad, b), "adet") for ad in SAYACLAR
    ]


def irtifa_olculeri(log: LogVerisi, b: Bolum) -> list[Olcu]:
    """Tutulan irtifa ve drone'un gerçek irtifası."""
    af = log.konular["auto_follow_status"]
    lp = log.konular["vehicle_local_position"]
    t_lp = log.zaman("vehicle_local_position")
    m = (t_lp >= b.bas) & (t_lp <= b.bit)
    _, _, z_min, z_max = istatistik(-lp["z"][m])
    return [
        Olcu(
            "İrtifa", "alt_hold_z", float(af["alt_hold_z"][b.i0]), "m", "NED z, aşağı +"
        ),
        Olcu("İrtifa", "Drone irtifası en küçük", z_min, "m"),
        Olcu("İrtifa", "Drone irtifası en büyük", z_max, "m"),
    ]


def bolum_olc(log: LogVerisi, b: Bolum) -> tuple[list[Olcu], BolumVerisi]:
    """Bir bölümün bütün ölçüleri."""
    af = log.konular["auto_follow_status"]
    mod_no = int(af["mode_nav_state"][b.i0])
    bv = bolum_verisi(log, b)
    cikis = None if b.sonu_kesik else cikis_bul(log, b, mod_no)
    if b.sonu_kesik:
        cikis_metni = "log ya da aralık bitti, mod hâlâ açıktı"
    elif cikis is None:
        cikis_metni = "—"
    else:
        cikis_metni = (
            f"{mod_adi(cikis[1], mod_no)} (nav_state {cikis[1]}, t = {cikis[0]:.3f} s)"
        )
    sure_durum = {
        ad: float((bv.durum == no).sum() * np.median(np.diff(bv.t)))
        if len(bv.t) > 1
        else 0.0
        for no, ad in DURUMLAR.items()
        if no != 0
    }
    olculer = [
        Olcu(
            "Genel",
            "Başlangıç",
            b.bas,
            "s",
            "PX4 açılışından beri"
            + (" (mod daha önce açılmıştı)" if b.basi_kesik else ""),
        ),
        Olcu("Genel", "Bitiş", b.bit, "s"),
        Olcu("Genel", "Süre", b.bit - b.bas, "s"),
        Olcu("Genel", "mode_nav_state", mod_no, "", "AUTO FOLLOW'un mod numarası"),
        Olcu("Genel", "Çıkış", cikis_metni, ""),
    ]
    olculer += [Olcu("Durum", f"{ad} süresi", s, "s") for ad, s in sure_durum.items()]
    olculer += durum_gecisleri(log, b, bv)
    olculer += hold_olculeri(log, b, cikis)
    olculer += mesafe_olculeri(bv)
    olculer += hiz_olculeri(log, b, bv)
    olculer += burun_olculeri(bv)
    olculer.append(yaw_donmasi(log, b, bv))
    olculer += filtre_olculeri(log, b, bv)
    olculer += girdi_olculeri(log, b)
    olculer += irtifa_olculeri(log, b)
    return olculer, bv


# --- Çıktı --------------------------------------------------------------------

ONDALIK = {"s": 3, "m": 2, "m/s": 2, "m/s²": 2, "deg": 1, "ms": 1, "Hz": 1, "adet": 0}


def bicimle(deger: float | str, birim: str) -> str:
    """Sayıyı birimine uygun ondalıkla yazar; NaN '—' olur."""
    if isinstance(deger, str):
        return deger
    if isinstance(deger, int):
        return str(deger)
    if not math.isfinite(deger):
        return "—"
    ondalik = ONDALIK.get(birim, 3)
    return f"{round(deger, ondalik) + 0.0:.{ondalik}f}"  # + 0.0: "-0.0" yazılmasın


def tablo_yaz(olculer: list[Olcu]) -> str:
    """Ölçüleri Türkçe başlıklı Markdown tablo olarak döndürür."""
    satirlar = ["| Grup | Ölçü | Değer | Birim | Not |", "|---|---|---|---|---|"]
    for o in olculer:
        hucreler = [o.grup, o.ad, bicimle(o.deger, o.birim), o.birim, o.aciklama]
        satirlar.append(
            "| " + " | ".join(h.replace("|", "\\|") for h in hucreler) + " |"
        )
    return "\n".join(satirlar)


def parametre_satiri(log: LogVerisi, t: float) -> str:
    """Bölümün başında geçerli AF_* parametreleri."""
    return ", ".join(f"{ad} = {log.parametre(ad, t):g}" for ad in PARAMETRELER)


def csv_yaz(yol: Path, kayitlar: list[tuple[Bolum, list[Olcu]]]) -> None:
    """Bütün bölümlerin ölçülerini tek bir CSV dosyasına yazar (ondalık ayırıcı nokta)."""
    with yol.open("w", newline="", encoding="utf-8") as f:
        yazici = csv.writer(f)
        yazici.writerow(["bolum", "grup", "olcu", "deger", "birim", "not"])
        for b, olculer in kayitlar:
            for o in olculer:
                deger = (
                    o.deger if isinstance(o.deger, str) else bicimle(o.deger, o.birim)
                )
                yazici.writerow([b.no, o.grup, o.ad, deger, o.birim, o.aciklama])


# --- Grafikler ----------------------------------------------------------------


def grafik_ciz(klasor: Path, b: Bolum, bv: BolumVerisi, log: LogVerisi) -> list[Path]:
    """Bölümün PNG grafiklerini çizer; yazılan dosyaların yollarını döndürür."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    klasor.mkdir(parents=True, exist_ok=True)
    on_ek = f"{log.yol.stem}_bolum{b.no}"
    baslik = f"{log.yol.name}, bölüm {b.no} ({b.bas:.1f}–{b.bit:.1f} s)"
    t = bv.t
    tak = np.where(bv.takip, 1.0, math.nan)
    yazilan = []

    def kaydet(fig: matplotlib.figure.Figure, ad: str) -> None:
        fig.suptitle(baslik)
        fig.tight_layout()
        yol = klasor / f"{on_ek}_{ad}.png"
        fig.savefig(yol, dpi=110)
        plt.close(fig)
        yazilan.append(yol)

    af = log.konular["auto_follow_status"]
    sl = slice(b.i0, b.i1 + 1)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    ax1.plot(t, bv.hata * tak, label="range_est − range_desired")
    ax1.axhspan(
        -OTURMA_BANDI_M,
        OTURMA_BANDI_M,
        color="tab:green",
        alpha=0.15,
        label=f"±{OTURMA_BANDI_M} m",
    )
    ax1.axhline(0, color="k", lw=0.5)
    ax1.set_ylabel("mesafe hatası [m]")
    ax1.legend(loc="upper right")
    ax1.grid(True)
    ax2.plot(t, af["range_est"][sl], label="range_est (kestirilen)")
    ax2.plot(t, af["range_desired"][sl], label="range_desired (istenen)")
    ax2.plot(
        t, af["range_meas"][sl], ".", ms=2, alpha=0.4, label="range_meas (ölçülen)"
    )
    ax2.set_ylabel("yatay mesafe [m]")
    ax2.set_xlabel("t [s] (PX4 açılışından beri)")
    ax2.legend(loc="upper right")
    ax2.grid(True)
    kaydet(fig, "mesafe")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(
        t,
        np.degrees(sar(bv.yaw_cmd - bv.gercek_yon)) * tak,
        label="yaw_cmd − gerçek yön",
    )
    ax.plot(
        t,
        np.degrees(sar(bv.yaw_cmd - bv.hedef_yonu)) * tak,
        label="yaw_cmd − hedef yönü",
    )
    ax.plot(
        t,
        np.degrees(sar(bv.gercek_yon - bv.hedef_yonu)) * tak,
        label="gerçek yön − hedef yönü",
    )
    ax.axhline(0, color="k", lw=0.5)
    ax.set_ylabel("burun hatası [deg]")
    ax.set_xlabel("t [s]")
    ax.legend(loc="upper right")
    ax.grid(True)
    kaydet(fig, "burun")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(
        t,
        np.hypot(bv.yasa[:, 0], bv.yasa[:, 1]),
        label="|vel_cmd_law| (yasa, kırpma öncesi)",
    )
    ax.plot(
        t, np.hypot(bv.komut[:, 0], bv.komut[:, 1]), label="|vel_cmd| (PX4'e giden)"
    )
    ax.plot(t, bv.drone_hiz, label="drone yatay hızı")
    ax.plot(
        t,
        np.hypot(bv.hedef_hiz[:, 0], bv.hedef_hiz[:, 1]),
        label="|target_vel_ned| (hedef hızı)",
    )
    ax.axhline(
        bv.vel_max, color="r", ls="--", lw=1, label=f"AF_VEL_MAX = {bv.vel_max:g}"
    )
    ax.set_ylabel("hız [m/s]")
    ax.set_xlabel("t [s]")
    ax.legend(loc="upper right")
    ax.grid(True)
    kaydet(fig, "hiz")

    gun = bv.guncellendi
    fig, axs = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    for k, eksen in enumerate(("x (kuzey)", "y (doğu)")):
        axs[k].plot(
            t[gun], bv.olcum[gun, k], ".", ms=3, label="target_meas_ned (girdi)"
        )
        axs[k].plot(t, bv.kestirim[:, k], label="target_est_ned (çıktı)")
        axs[k].set_ylabel(f"hedef {eksen} [m]")
        axs[k].legend(loc="upper right")
        axs[k].grid(True)
    axs[2].plot(t, bv.hedef_hiz[:, 0], label="target_vel_ned x")
    axs[2].plot(t, bv.hedef_hiz[:, 1], label="target_vel_ned y")
    turev = turetilen_hiz(t[gun], bv.olcum[gun])
    axs[2].plot(
        t[gun],
        np.hypot(turev[:, 0], turev[:, 1]),
        ".",
        ms=2,
        alpha=0.5,
        label="ölçümden türetilen |hız|",
    )
    axs[2].plot(
        t,
        np.hypot(bv.hedef_hiz[:, 0], bv.hedef_hiz[:, 1]),
        "k",
        lw=1,
        label="|target_vel_ned|",
    )
    axs[2].set_ylabel("hedef hızı [m/s]")
    axs[2].set_xlabel("t [s]")
    axs[2].legend(loc="upper right")
    axs[2].grid(True)
    kaydet(fig, "filtre")

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.plot(bv.drone_xy[:, 1], bv.drone_xy[:, 0], label="drone")
    ax.plot(
        bv.olcum[gun, 1], bv.olcum[gun, 0], ".", ms=3, label="target_meas_ned (girdi)"
    )
    ax.plot(bv.kestirim[:, 1], bv.kestirim[:, 0], label="target_est_ned (çıktı)")
    ax.plot(bv.drone_xy[0, 1], bv.drone_xy[0, 0], "go", label="drone girişte")
    ax.set_xlabel("doğu [m]")
    ax.set_ylabel("kuzey [m]")
    ax.set_aspect("equal", adjustable="datalim")
    ax.legend(loc="best")
    ax.grid(True)
    kaydet(fig, "harita")

    fig, axs = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    axs[0].step(t, bv.durum, where="post")
    axs[0].set_yticks(list(DURUMLAR), list(DURUMLAR.values()))
    axs[0].set_ylabel("state")
    axs[0].grid(True)
    axs[1].step(t, af["check_result"][sl], where="post")
    axs[1].set_ylabel("check_result")
    axs[1].grid(True)
    axs[2].plot(t, af["time_since_valid"][sl], label="time_since_valid")
    axs[2].plot(t, af["lost_time"][sl], label="lost_time")
    axs[2].set_ylabel("süre [s]")
    axs[2].set_xlabel("t [s]")
    axs[2].legend(loc="upper right")
    axs[2].grid(True)
    kaydet(fig, "durum")
    return yazilan


# --- Ana akış -----------------------------------------------------------------


def argumanlari_oku(argv: list[str] | None = None) -> argparse.Namespace:
    """Komut satırı seçeneklerini okur."""
    p = argparse.ArgumentParser(
        description="AUTO FOLLOW (M15) log analizi: her AUTO FOLLOW bölümü için ölçüler"
    )
    p.add_argument("ulog", type=Path, help="ULog dosyası (.ulg)")
    p.add_argument(
        "--aralik",
        nargs=2,
        type=float,
        metavar=("BAS", "BIT"),
        help="yalnızca bu zaman aralığı [s, PX4 açılışından beri]",
    )
    p.add_argument(
        "--grafik",
        type=Path,
        metavar="KLASOR",
        help="PNG grafiklerin yazılacağı klasör",
    )
    p.add_argument(
        "--csv", type=Path, metavar="DOSYA", help="ölçülerin yazılacağı CSV dosyası"
    )
    args = p.parse_args(argv)
    if args.aralik is not None and not args.aralik[0] < args.aralik[1]:
        p.error("--aralik: BAS, BIT'ten küçük olmalı")
    return args


def main(argv: list[str] | None = None) -> int:
    """Logu okur, bölümleri bulur, ölçüleri basar; istenirse grafik ve CSV yazar."""
    args = argumanlari_oku(argv)
    try:
        log = log_oku(args.ulog)
    except (OSError, ValueError) as hata:
        print(f"HATA: {args.ulog}: {hata}", file=sys.stderr)
        return 1

    aralik = tuple(args.aralik) if args.aralik is not None else None
    bolumler = bolumleri_bul(log, aralik)
    print(f"# AUTO FOLLOW log analizi: {log.yol.name}\n")
    print(f"- Log: {log.bas:.1f}–{log.bit:.1f} s (PX4 açılışından beri)")
    if aralik is not None:
        print(f"- Aralık: {aralik[0]:g}–{aralik[1]:g} s")
    print(f"- Bulunan AUTO FOLLOW bölümü: {len(bolumler)}")
    if not bolumler:
        print(
            "\nBu logda (ya da aralıkta) AUTO FOLLOW hiç açılmamış (mode_active hep 0)."
        )
        return 0

    kayitlar = []
    for b in bolumler:
        olculer, bv = bolum_olc(log, b)
        kayitlar.append((b, olculer))
        print(f"\n## Bölüm {b.no}: {b.bas:.3f}–{b.bit:.3f} s ({b.bit - b.bas:.1f} s)\n")
        print(f"Parametreler (bölüm başında): {parametre_satiri(log, b.bas)}\n")
        print(tablo_yaz(olculer))
        if args.grafik is not None:
            yazilan = grafik_ciz(args.grafik, b, bv, log)
            print(f"\nGrafikler: {', '.join(str(y) for y in yazilan)}")

    if args.csv is not None:
        csv_yaz(args.csv, kayitlar)
        print(f"\nCSV: {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
