#!/usr/bin/env python3
"""Geçici test göndericisi: Raspberry Pi'nin AF_LOS mesajını SITL'e taklit eder.

Bu script M15 (AUTO FOLLOW) SITL testleri içindir; Pi'deki gerçek gönderici
değildir (o Vision reposunda yazılacak). Pi'nin göndereceği "hedef drone'a göre
şu yönde" bilgisini MAVLink 2 DEBUG_FLOAT_ARRAY mesajı olarak PX4'e yollar.

Mesaj (spec Bölüm 2, Varsayım V2):
    name    = "AF_LOS"
    data[0..2] = LOS birim vektörü x, y, z (body FRD: x ileri, y sağ, z aşağı)
    data[3]    = yaş [ms] (görüntünün çekiminden gönderime geçen süre)
    data[4]    = sıra no (her mesajda 1 artar)
    data[5]    = hedef var (1) / yok (0)

Kullanım (SITL açıkken, ayrı bir terminalde):
    python3 tez/sitl/af_los_gonder.py                      # açık çevrim, LOS (0.8, 0, 0.6)
    python3 tez/sitl/af_los_gonder.py --los 0.951 0 0.309  # S1a "hedef uzakta"
    python3 tez/sitl/af_los_gonder.py --senaryo kes        # S4: gönderimi kes / geri başlat
    python3 tez/sitl/af_los_gonder.py --senaryo nan        # S5: araya NaN/Inf karıştır
    python3 tez/sitl/af_los_gonder.py --cevrim kapali      # kapalı çevrim: hayali yer hedefi
    python3 tez/sitl/af_los_gonder.py --cevrim kapali --hedef-mesafe 25 --hedef-aci 30
                                                           # S6: hedef 25 m uzakta, burnun 30 derece sağında

Seçenekler:
    --cevrim acik|kapali  acik: sabit LOS gönderir (varsayılan).
                          kapali: başlangıçta yerde hayali bir hedef noktası
                          seçer, drone'un konumunu ve tutumunu MAVLink'ten
                          okuyup gerçek body FRD LOS'u hesaplar.
    --hedef-mesafe METRE  Kapalı çevrimde hedefin başlangıçtaki yatay uzaklığı
                          (varsayılan 20 m). Açık çevrimde kullanılmaz.
    --hedef-aci DERECE    Kapalı çevrimde hedefin başlangıçta burna göre yönü
                          (varsayılan 0 = tam önde, pozitif = sağ, negatif = sol).
                          Açık çevrimde kullanılmaz.
    --los X Y Z           Açık çevrimde gönderilecek LOS (birim vektöre
                          çevrilmeden aynen gönderilir).
    --senaryo AD          Zaman çizelgeli bozma/kesme senaryosu (aşağıda).
    --hiz HZ              Gönderim hızı [Hz].
    --yas MS              data[3]'e yazılan yaş [ms].
    --baglanti URL        pymavlink bağlantı adresi.

Senaryolar (süreler dosyanın başındaki sabitlerde; t = script başlangıcından
beri geçen süre, SENARYO_BASLA_S öncesi hep normal gönderim):
    kes        t=10 s'de 1.0 s gönderim yok (KAYIP_BEKLE'den takibe dönüş),
               t=20 s'de 3.0 s gönderim yok (KAYIP_BEKLE -> HOLD_ISTENDI),
               sonra yine normal.
    hedef-yok  t=10 s'de 0.5 s data[5]=0, t=20 s'de 3.0 s data[5]=0, sonra normal.
    yanlis-ad  nan  norm  sira  eski  ufuk  uzak
               t=10-20 s arası her BOZUK_ARALIK'ıncı mesaj bozuk (araya
               karışık), t=20-23 s arası bütün mesajlar bozuk, sonra normal.
               yanlis-ad: ad "AF_TEST" · nan: LOS x NaN / yaş +Inf (sırayla) ·
               norm: LOS 0.7 kat · sira: aynı sıra no / 10 geri (sırayla;
               hepsi bozukken hep aynı sıra no) · eski: yaş 600 ms ·
               ufuk: aşağı bakış 5 derece · uzak: aşağı bakış 11 derece
               (10 m irtifada ~46 m > AF_MAX_RNG 40 m).
    Hedefsiz moda giriş (S4-d) için script hiç çalıştırılmaz.

Kapalı çevrimde hedefin yolu (dosyadaki HEDEF_YOL sabiti):
    ()       hedef durur (S6, varsayılan).
    L_YOLU   S7 (karar 2026-11-11): YURUME_BASLA_S anından sonra 1.4 m/s ile
             20 s drone'dan uzaklaşma yönünde düz, sonra 90 derece sağa dönüp
             20 s düz; sonra durur. "Uzaklaşma yönü" = başlangıçta drone'dan
             hedefe bakan yatay yön. Açmak için HEDEF_YOL = L_YOLU yapılır
             (komut satırı seçeneği yok; adı kullanıcıya sorulacak).

Bağlantı: PX4 SITL'in "API/Offboard" (onboard) MAVLink kanalı UDP 14580'i
dinler ve 14540'a gönderir (ROMFS/px4fmu_common/init.d-posix/px4-rc.mavlink:4-5,
26). Script bu yüzden 14540'ı dinler (udpin) ve PX4'e cevabı oradan yollar.
Pi'de bu adres seri port olur (ör. /dev/ttyAMA0); bu script yalnızca SITL içindir.

Durdurmak için Ctrl+C. Değerler geçicidir (kullanıcı kararı 2026-11-10):
Vision ekibinin geri bildirimine göre değişebilir, bu yüzden hepsi aşağıda
sabit olarak toplandı.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import time
from dataclasses import dataclass

os.environ["MAVLINK20"] = "1"  # data alanı MAVLink 2 ek alanıdır (common.xml:7630-7631)

from pymavlink import mavutil  # MAVLINK20 içe aktarmadan önce kurulmalı

# --- Değiştirilmesi kolay varsayılanlar -------------------------------------

VARSAYILAN_HIZ_HZ = 20.0  # Pi 10-30 Hz bekleniyor (V2)
VARSAYILAN_YAS_MS = 50.0
VARSAYILAN_BAGLANTI = "udpin:0.0.0.0:14540"
VARSAYILAN_LOS = (0.8, 0.0, 0.6)  # spec Bölüm 3 örneği (S1b)

MESAJ_ADI = "AF_LOS"
VERI_UZUNLUGU = 58  # DEBUG_FLOAT_ARRAY data[] uzunluğu
KAYNAK_SISTEM = 1  # Pi, Pixhawk ile aynı sistemin parçası
KAYNAK_BILESEN = 191  # MAV_COMP_ID_ONBOARD_COMPUTER

# Kapalı çevrim: yerde hayali hedef (S6 ve S7 kararları 2026-11-11).
AF_TGT_HGT_M = 1.0  # hedefin bakılan noktasının yerden yüksekliği (AF_TGT_HGT)
AF_GND_OFS_M = 0.0  # hedef zemininin kalkış yerine göre yüksekliği (AF_GND_OFS)
VARSAYILAN_HEDEF_MESAFE_M = 20.0  # --hedef-mesafe: başlangıçta hedefe yatay uzaklık
VARSAYILAN_HEDEF_ACI_DERECE = 0.0  # --hedef-aci: burna göre yön, pozitif = sağ
KONUM_ESKI_S = 0.5  # drone konumu bu süredir gelmediyse mesaj gönderilmez

# Hedefin yolu: (süre [s], yön [derece], hız [m/s]) bacakları. Yön, başlangıçta
# drone'dan hedefe bakan yatay yöne göredir: 0 = drone'dan uzaklaşma yönü,
# pozitif = sağa dönüş. Boş = hedef durur (S6). Yürüme YURUME_BASLA_S anında
# başlar (önce drone duran hedefin istenen mesafesine otursun diye); son
# bacaktan sonra hedef durur.
YURUME_HIZI_M_S = 1.4  # S7 (karar 2026-11-11)
L_YOLU = ((20.0, 0.0, YURUME_HIZI_M_S), (20.0, 90.0, YURUME_HIZI_M_S))  # S7
HEDEF_YOL: tuple[tuple[float, float, float], ...] = ()  # S7 için L_YOLU

# Senaryo zaman çizelgesi [s] (script başlangıcından)
SENARYO_BASLA_S = 10.0
YURUME_BASLA_S = SENARYO_BASLA_S  # kapalı çevrimde hedefin yürümeye başladığı an
KISA_KESINTI_S = 1.0  # kes: AF_DATA_TOUT (0.5) < bu < AF_DATA_TOUT + AF_LOST_T (1.5)
KISA_HEDEF_YOK_S = 0.5  # hedef-yok: kısa "hedef yok"
UZUN_BASLA_S = 20.0
UZUN_SURE_S = 3.0  # > 1.5 s: HOLD_ISTENDI'ye kadar
BOZUK_ARALIK = 5  # araya karışık bozuk mesaj: her 5. mesaj

BOZUK_AD = "AF_TEST"
ESKI_YAS_MS = 600.0  # > AF_DATA_TOUT (500 ms)
NORM_KATSAYI = 0.7  # |LOS| = 0.7, AF_NORM_TOL 0.1 dışında
SIRA_GERI = 10
UFUK_ACI_DERECE = 5.0  # < AF_MIN_DEP (10)
UZAK_ACI_DERECE = 11.0  # h = 9 m'de d = 9 / tan(11) = 46 m > AF_MAX_RNG (40)

SENARYOLAR = (
    "kes",
    "hedef-yok",
    "yanlis-ad",
    "nan",
    "norm",
    "sira",
    "eski",
    "ufuk",
    "uzak",
)
BOZMA_SENARYOLARI = ("yanlis-ad", "nan", "norm", "sira", "eski", "ufuk", "uzak")

Vektor = tuple[float, float, float]


@dataclass
class Mesaj:
    """Gönderilecek tek bir AF_LOS mesajının içeriği."""

    ad: str
    los: Vektor
    yas_ms: float
    sira: float
    hedef: float


@dataclass
class DroneDurumu:
    """MAVLink'ten okunan son drone konumu (NED) ve tutumu (rad)."""

    x: float = math.nan
    y: float = math.nan
    z: float = math.nan
    roll: float = math.nan
    pitch: float = math.nan
    yaw: float = math.nan
    konum_zamani: float = 0.0
    tutum_zamani: float = 0.0

    def hazir(self, simdi: float) -> bool:
        """Konum ve tutum son KONUM_ESKI_S içinde geldiyse True."""
        return (
            simdi - self.konum_zamani < KONUM_ESKI_S
            and simdi - self.tutum_zamani < KONUM_ESKI_S
        )


def aci_los(derece: float) -> Vektor:
    """Burun yönünde, verilen aşağı bakış açısıyla bir body FRD LOS döndürür."""
    r = math.radians(derece)
    return (math.cos(r), 0.0, math.sin(r))


def ned_to_frd(v: Vektor, roll: float, pitch: float, yaw: float) -> Vektor:
    """NED vektörünü drone gövde eksenine (FRD) çevirir: R(roll, pitch, yaw)^T * v."""
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    # R = Rz(yaw) * Ry(pitch) * Rx(roll), gövde -> NED; satırlar R'nin sütunları (R^T)
    r11, r12, r13 = cp * cy, sr * sp * cy - cr * sy, cr * sp * cy + sr * sy
    r21, r22, r23 = cp * sy, sr * sp * sy + cr * cy, cr * sp * sy - sr * cy
    r31, r32, r33 = -sp, sr * cp, cr * cp
    x, y, z = v
    return (
        r11 * x + r21 * y + r31 * z,
        r12 * x + r22 * y + r32 * z,
        r13 * x + r23 * y + r33 * z,
    )


def kapali_cevrim_los(drone: DroneDurumu, hedef_xy: tuple[float, float]) -> Vektor:
    """Drone'dan hayali hedefin bakılan noktasına body FRD birim LOS hesaplar."""
    hedef_z = -(AF_GND_OFS_M + AF_TGT_HGT_M)  # NED z, aşağı pozitif
    fark = (hedef_xy[0] - drone.x, hedef_xy[1] - drone.y, hedef_z - drone.z)
    uzunluk = math.sqrt(sum(c * c for c in fark))
    if uzunluk <= 0.0:
        return (0.0, 0.0, 1.0)
    birim = (fark[0] / uzunluk, fark[1] / uzunluk, fark[2] / uzunluk)
    return ned_to_frd(birim, drone.roll, drone.pitch, drone.yaw)


def hedef_baslangici(
    drone: DroneDurumu, mesafe_m: float, aci_derece: float
) -> tuple[tuple[float, float], float]:
    """Hayali hedefin başlangıç konumu (NED x, y) ve drone'dan ona bakan yön [rad]."""
    yon = drone.yaw + math.radians(aci_derece)
    return (drone.x + mesafe_m * math.cos(yon), drone.y + mesafe_m * math.sin(yon)), yon


def hedef_konumu(
    baslangic: tuple[float, float],
    yon0: float,
    yol: tuple[tuple[float, float, float], ...],
    t: float,
) -> tuple[tuple[float, float], int]:
    """t anında hedefin NED x, y konumu ve yürüdüğü bacak (0 = duruyor / henüz başlamadı).

    t: script başlangıcından beri geçen süre [s]; yürüme YURUME_BASLA_S'de başlar.
    """
    x, y = baslangic
    kalan = t - YURUME_BASLA_S
    bacak = 0
    for no, (sure, yon_derece, hiz) in enumerate(yol, start=1):
        if kalan <= 0.0:
            break
        adim = min(kalan, sure)
        yon = yon0 + math.radians(yon_derece)
        x += hiz * adim * math.cos(yon)
        y += hiz * adim * math.sin(yon)
        if kalan < sure:
            bacak = no
        kalan -= adim
    return (x, y), bacak


def senaryo_uygula(
    senaryo: str | None, t: float, sayac: int, normal: Mesaj, son_gecerli_sira: float
) -> Mesaj | None:
    """Zaman çizelgesine göre mesajı bozar ya da gönderimi keser (None = gönderme).

    t: script başlangıcından beri geçen süre [s]; sayac: gönderim denemesi sırası.
    son_gecerli_sira: bozulmamış son mesajın sıra no'su ("sira" senaryosu için).
    """
    if senaryo is None or t < SENARYO_BASLA_S:
        return normal

    uzun = UZUN_BASLA_S <= t < UZUN_BASLA_S + UZUN_SURE_S

    if senaryo == "kes":
        kisa = SENARYO_BASLA_S <= t < SENARYO_BASLA_S + KISA_KESINTI_S
        return None if (kisa or uzun) else normal

    if senaryo == "hedef-yok":
        kisa = SENARYO_BASLA_S <= t < SENARYO_BASLA_S + KISA_HEDEF_YOK_S
        if kisa or uzun:
            return Mesaj(normal.ad, normal.los, normal.yas_ms, normal.sira, 0.0)
        return normal

    araya = t < UZUN_BASLA_S and sayac % BOZUK_ARALIK == 0
    if not (araya or uzun):
        return normal

    if senaryo == "yanlis-ad":
        return Mesaj(BOZUK_AD, normal.los, normal.yas_ms, normal.sira, normal.hedef)
    if senaryo == "nan":
        if sayac % (2 * BOZUK_ARALIK) == 0:
            return Mesaj(
                normal.ad,
                (math.nan, normal.los[1], normal.los[2]),
                normal.yas_ms,
                normal.sira,
                normal.hedef,
            )
        return Mesaj(normal.ad, normal.los, math.inf, normal.sira, normal.hedef)
    if senaryo == "norm":
        los = tuple(NORM_KATSAYI * c for c in normal.los)
        return Mesaj(
            normal.ad,
            (los[0], los[1], los[2]),
            normal.yas_ms,
            normal.sira,
            normal.hedef,
        )
    if senaryo == "sira":
        if uzun or sayac % (2 * BOZUK_ARALIK) == 0:
            sira = son_gecerli_sira  # tekrar
        else:
            sira = son_gecerli_sira - SIRA_GERI  # geri
        return Mesaj(normal.ad, normal.los, normal.yas_ms, sira, normal.hedef)
    if senaryo == "eski":
        return Mesaj(normal.ad, normal.los, ESKI_YAS_MS, normal.sira, normal.hedef)
    if senaryo == "ufuk":
        return Mesaj(
            normal.ad,
            aci_los(UFUK_ACI_DERECE),
            normal.yas_ms,
            normal.sira,
            normal.hedef,
        )
    if senaryo == "uzak":
        return Mesaj(
            normal.ad,
            aci_los(UZAK_ACI_DERECE),
            normal.yas_ms,
            normal.sira,
            normal.hedef,
        )
    return normal


def gonder(baglanti: mavutil.mavfile, mesaj: Mesaj) -> None:
    """Mesajı MAVLink 2 DEBUG_FLOAT_ARRAY olarak gönderir."""
    veri = [0.0] * VERI_UZUNLUGU
    veri[0], veri[1], veri[2] = mesaj.los
    veri[3] = mesaj.yas_ms
    veri[4] = mesaj.sira
    veri[5] = mesaj.hedef
    zaman_us = int(time.time() * 1e6)
    baglanti.mav.debug_float_array_send(zaman_us, mesaj.ad.encode("ascii"), 0, veri)


def gelenleri_oku(baglanti: mavutil.mavfile, drone: DroneDurumu) -> None:
    """Bekleyen bütün MAVLink mesajlarını okur, drone konumunu ve tutumunu günceller."""
    while True:
        msg = baglanti.recv_match(
            type=["LOCAL_POSITION_NED", "ATTITUDE"], blocking=False
        )
        if msg is None:
            return
        simdi = time.monotonic()
        if msg.get_type() == "LOCAL_POSITION_NED":
            drone.x, drone.y, drone.z = msg.x, msg.y, msg.z
            drone.konum_zamani = simdi
        else:
            drone.roll, drone.pitch, drone.yaw = msg.roll, msg.pitch, msg.yaw
            drone.tutum_zamani = simdi


def argumanlari_oku(argv: list[str] | None = None) -> argparse.Namespace:
    """Komut satırı seçeneklerini okur."""
    p = argparse.ArgumentParser(description="AF_LOS test göndericisi (SITL, M15)")
    p.add_argument(
        "--cevrim",
        choices=("acik", "kapali"),
        default="acik",
        help="acik: sabit LOS; kapali: hayali yer hedefi",
    )
    p.add_argument(
        "--hedef-mesafe",
        type=float,
        default=VARSAYILAN_HEDEF_MESAFE_M,
        metavar="METRE",
        help="kapalı çevrim: hedefin başlangıçtaki yatay uzaklığı [m]",
    )
    p.add_argument(
        "--hedef-aci",
        type=float,
        default=VARSAYILAN_HEDEF_ACI_DERECE,
        metavar="DERECE",
        help="kapalı çevrim: hedefin burna göre yönü [derece], pozitif = sağ",
    )
    p.add_argument(
        "--los",
        nargs=3,
        type=float,
        metavar=("X", "Y", "Z"),
        default=list(VARSAYILAN_LOS),
        help="açık çevrim LOS (body FRD)",
    )
    p.add_argument(
        "--senaryo",
        choices=SENARYOLAR,
        default=None,
        help="zaman çizelgeli kesme/bozma senaryosu",
    )
    p.add_argument(
        "--hiz", type=float, default=VARSAYILAN_HIZ_HZ, help="gönderim hızı [Hz]"
    )
    p.add_argument(
        "--yas", type=float, default=VARSAYILAN_YAS_MS, help="data[3] yaşı [ms]"
    )
    p.add_argument(
        "--baglanti", default=VARSAYILAN_BAGLANTI, help="pymavlink bağlantı adresi"
    )
    args = p.parse_args(argv)
    if args.hiz <= 0.0:
        p.error("--hiz pozitif olmalı")
    if args.hedef_mesafe <= 0.0:
        p.error("--hedef-mesafe pozitif olmalı")
    return args


def main(argv: list[str] | None = None) -> int:
    """Göndericiyi çalıştırır; Ctrl+C ile durur."""
    args = argumanlari_oku(argv)
    baglanti = mavutil.mavlink_connection(
        args.baglanti, source_system=KAYNAK_SISTEM, source_component=KAYNAK_BILESEN
    )

    print(f"[af_los_gonder] {args.baglanti} bekleniyor (PX4 heartbeat)...", flush=True)
    if baglanti.wait_heartbeat(timeout=30) is None:
        print(
            "[af_los_gonder] HATA: 30 s içinde PX4'ten heartbeat gelmedi",
            file=sys.stderr,
        )
        return 1

    drone = DroneDurumu()
    hedef_xy: tuple[float, float] | None = None
    hedef_bas: tuple[float, float] = (math.nan, math.nan)
    hedef_yon0 = math.nan
    if args.cevrim == "kapali":
        bitis = time.monotonic() + 10.0
        while not drone.hazir(time.monotonic()):
            if time.monotonic() > bitis:
                print(
                    "[af_los_gonder] HATA: drone konumu/tutumu gelmiyor",
                    file=sys.stderr,
                )
                return 1
            gelenleri_oku(baglanti, drone)
            time.sleep(0.01)
        hedef_bas, hedef_yon0 = hedef_baslangici(
            drone, args.hedef_mesafe, args.hedef_aci
        )
        hedef_xy = hedef_bas
        print(
            f"[af_los_gonder] hayali hedef NED x={hedef_xy[0]:.2f} y={hedef_xy[1]:.2f} (yerde), "
            f"mesafe {args.hedef_mesafe:g} m, burna göre {args.hedef_aci:g} derece, "
            f"yol bacak sayısı {len(HEDEF_YOL)}",
            flush=True,
        )

    los_acik = (args.los[0], args.los[1], args.los[2])
    print(
        f"[af_los_gonder] başladı: cevrim={args.cevrim} senaryo={args.senaryo} hiz={args.hiz} Hz "
        f"yas={args.yas} ms" + (f" los={los_acik}" if args.cevrim == "acik" else ""),
        flush=True,
    )

    aralik = 1.0 / args.hiz
    baslangic = time.monotonic()
    sonraki = baslangic
    sira = 0.0
    son_gecerli_sira = 0.0
    sayac = 0
    gonderilen = 0
    onceki_kip = ""
    onceki_bacak = 0

    try:
        while True:
            simdi = time.monotonic()
            gelenleri_oku(baglanti, drone)
            if simdi < sonraki:
                time.sleep(min(sonraki - simdi, 0.005))
                continue
            sonraki += aralik
            t = simdi - baslangic
            sayac += 1

            if hedef_xy is not None:
                hedef_xy, bacak = hedef_konumu(hedef_bas, hedef_yon0, HEDEF_YOL, t)
                if bacak != onceki_bacak:
                    print(
                        f"[af_los_gonder] t={t:6.2f} s: hedef bacak {bacak} "
                        f"(0 = duruyor), NED x={hedef_xy[0]:.2f} y={hedef_xy[1]:.2f}",
                        flush=True,
                    )
                    onceki_bacak = bacak
                if not drone.hazir(simdi):
                    continue
                los = kapali_cevrim_los(drone, hedef_xy)
            else:
                los = los_acik

            normal = Mesaj(MESAJ_ADI, los, args.yas, sira + 1.0, 1.0)
            mesaj = senaryo_uygula(args.senaryo, t, sayac, normal, son_gecerli_sira)

            kip = (
                "kesik"
                if mesaj is None
                else ("normal" if mesaj is normal else "bozuk/ozel")
            )
            if kip != onceki_kip:
                print(f"[af_los_gonder] t={t:6.2f} s: {kip}", flush=True)
                onceki_kip = kip

            if mesaj is None:
                continue
            sira += 1.0  # sıra no her gönderilen mesajda artar
            if mesaj is normal:
                son_gecerli_sira = mesaj.sira
            gonder(baglanti, mesaj)
            gonderilen += 1
    except KeyboardInterrupt:
        pass

    print(
        f"[af_los_gonder] durdu: {gonderilen} mesaj gönderildi, son sıra no {sira:.0f}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
