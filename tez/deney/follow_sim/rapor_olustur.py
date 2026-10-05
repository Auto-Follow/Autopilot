#!/usr/bin/env python3
"""Builds the PDF report of the camera tilt / geolocation / Wi-Fi experiments from sonuclar/*/analiz.json.

Needs reportlab (not in the project venv):  python3 -m venv --system-site-packages /tmp/pdfenv &&
/tmp/pdfenv/bin/pip install reportlab && /tmp/pdfenv/bin/python rapor_olustur.py <output.pdf>
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,  # noqa: E402
                                Table, TableStyle)

HERE = Path(__file__).resolve().parent
RES = HERE / "sonuclar"
FIG = RES / "rapor_sekilleri"

pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DejaVuMono", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))

BODY = ParagraphStyle("body", fontName="DejaVu", fontSize=9.5, leading=13.5, alignment=TA_LEFT, spaceAfter=5)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8, leading=10.5, textColor=colors.HexColor("#444444"))
CELL = ParagraphStyle("cell", parent=BODY, fontSize=7.8, leading=9.5, spaceAfter=0)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="DejaVu-Bold")
H1 = ParagraphStyle("h1", parent=BODY, fontName="DejaVu-Bold", fontSize=16, leading=20, spaceAfter=8,
                    textColor=colors.HexColor("#1f3b63"))
H2 = ParagraphStyle("h2", parent=BODY, fontName="DejaVu-Bold", fontSize=12.5, leading=16, spaceBefore=10,
                    spaceAfter=6, textColor=colors.HexColor("#1f3b63"))
H3 = ParagraphStyle("h3", parent=BODY, fontName="DejaVu-Bold", fontSize=10.5, leading=14, spaceBefore=6, spaceAfter=4)
BOX = ParagraphStyle("box", parent=BODY, backColor=colors.HexColor("#eef4fb"), borderColor=colors.HexColor("#9db7d9"),
                     borderWidth=0.6, borderPadding=6, spaceBefore=4, spaceAfter=10)
PAGE_W = A4[0] - 3.6 * cm


def load(name):
    return json.loads((RES / name / "analiz.json").read_text())


def P(text, style=BODY):
    return Paragraph(text, style)


def bullets(items, style=BODY):
    return [Paragraph(f"•&nbsp;&nbsp;{t}", ParagraphStyle("b", parent=style, leftIndent=12, firstLineIndent=-9))
            for t in items]


def table(rows, widths=None, header=True, highlight=None):
    data = [[Paragraph(str(c), CELLB if (header and i == 0) else CELL) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b0b7c0")),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe7f1")))
    for (r, c, color) in highlight or []:
        style.append(("BACKGROUND", (c, r), (c, r), colors.HexColor(color)))
    t.setStyle(TableStyle(style))
    return t


def image(path, width=PAGE_W, caption=None):
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(str(path)).getSize()
    parts = [Image(str(path), width=width, height=width * ih / iw)]
    if caption:
        parts.append(Paragraph(caption, SMALL))
    return KeepTogether(parts)


def label(name):
    """ht8_dst8 -> 8 m / 8 m"""
    name = name.replace("acik_", "").replace("kapali_", "")
    if name.startswith("ht"):
        h, d = name[2:].split("_dst")
        return f"{h} m / {d} m"
    return name


def heat(v, lo=60, hi=85):
    return "#c8ecc9" if v >= hi else "#fff1b8" if v >= lo else "#f6c9c4"


# ----------------------------------------------------------------------------------------------- figures
def make_latency_figure(trk):
    names = sorted(trk, key=lambda n: (trk[n]["ft_gecikme_s"], trk[n]["ft_kayip"], trk[n]["ft_patlama"]))
    labels = []
    for n in names:
        s = trk[n]
        lab = f"{s['ft_gecikme_s'] * 1000:.0f} ms"
        if s["ft_kayip"]:
            lab += f" + %{s['ft_kayip'] * 100:.0f}" + (" patl." if s["ft_patlama"] > 1 else "")
        labels.append(lab)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    rms = [trk[n]["mesafe_hatasi_rms_m"] for n in names]
    vis = [trk[n]["ayak_kadrajda_yuzde"] for n in names]
    col = ["#d9534f" if trk[n]["kayip_3s_ustu"] else "#4a7ebb" for n in names]
    axes[0].bar(range(len(names)), rms, color=col)
    axes[0].set_xticks(range(len(names)), labels, fontsize=8, rotation=35, ha="right")
    axes[0].set_ylabel("takip mesafesi hatası RMS (m)")
    axes[0].set_title("FOLLOW_TARGET gecikme / kayıp → takip hatası")
    axes[1].bar(range(len(names)), vis, color=col)
    axes[1].set_xticks(range(len(names)), labels, fontsize=8, rotation=35, ha="right")
    axes[1].set_ylabel("hedef kadrajda (% süre)")
    axes[1].set_ylim(0, 100)
    axes[1].set_title("Kırmızı: hedef 3 s'den uzun kayboldu, takip koptu")
    fig.tight_layout()
    out = FIG / "gecikme_ozet.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def make_video_figure():
    files = [("gecikme0_kayip0.png", "Kayıp yok"), ("gecikme0_kayip3.png", "%3 paket kaybı"),
             ("gecikme0_kayip10.png", "%10 paket kaybı"), ("gecikme300_kayip3.png", "300 ms gecikme + %3 kayıp")]
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    for ax, (f, t) in zip(axes.ravel(), files):
        ax.imshow(plt.imread(RES / "video" / f))
        ax.set_title(t, fontsize=11)
        ax.axis("off")
    fig.tight_layout()
    out = FIG / "video_kayip.png"
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return out


def make_gimbal_figure(kad):
    names = ["ht3_dst8", "ht5_dst8", "ht8_dst8", "ht12_dst8", "ht8_dst12", "ht12_dst12"]
    fig, axes = plt.subplots(2, 3, figsize=(12, 5.5), sharex=True, sharey=True)
    for ax, n in zip(axes.ravel(), names):
        rows = sorted([r for r in kad if r["senaryo"] == n], key=lambda r: r["egim"])
        ax.plot([r["egim"] for r in rows], [r["ayak_kadrajda"] for r in rows], "o-", label="sabit montaj", ms=3)
        ax.plot([r["egim"] for r in rows], [r["gimbal_ayak_kadrajda"] for r in rows], "s--", label="gimbal (2 eksen)",
                ms=3)
        ax.set_title(f"yükseklik / mesafe = {label(n)}", fontsize=9)
        ax.grid(alpha=0.3)
        ax.set_ylim(0, 102)
    for ax in axes[1]:
        ax.set_xlabel("kamera eğimi (°)")
    for ax in axes[:, 0]:
        ax.set_ylabel("kadrajda (%)")
    axes[0, 0].legend(fontsize=8)
    fig.tight_layout()
    out = FIG / "gimbal.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


# ----------------------------------------------------------------------------------------------- report
def build(out_pdf):
    FIG.mkdir(parents=True, exist_ok=True)
    kam, geo, gec = load("kamera_egim40"), load("geolocation_egim45"), load("gecikme_egim45")
    budget = json.loads((RES / "hata_butcesi.json").read_text())
    video = json.loads((RES / "video" / "video_olcum.json").read_text())
    s = []

    s.append(P("Auto-Follow — Kamera Açısı, Geolocation ve Wi-Fi Benzetimi", H1))
    s.append(P("Simülasyon raporu · 01.10.2026 · PX4 v1.17 SITL + Gazebo Harmonic, x500 + Camera Module 3 modeli "
               "(66° × 40°, 2304 × 1296) · Hazırlayan: Ahmet (Claude Code ile)", SMALL))
    s.append(Spacer(1, 6))
    s.append(P("Özet ve öneriler", H2))
    s.append(P(
        "<b>1) Kamera aşağı eğik takılmalı.</b> Düz kamera PX4'ün varsayılan takibinde (8 m geride, 8 m yukarıda) "
        "hedefi zamanın sadece %2'sinde görüyor. <b>45° eğim</b> 8 m / 8 m'de %90, 40–45° eğim 5–12 m yükseklikte "
        "%83–94 görünürlük veriyor. Kalan kaybın tamamı drone'un hızlanırken burnunu eğmesinden: <b>2 eksenli gimbal</b> "
        "ile aynı uçuşlarda görünürlük <b>%99–100</b>.<br/>"
        "<b>2) Kameradan konum hesabı (geolocation) çalışıyor.</b> Ölçülen yatay hata ortanca <b>0.4–0.6 m</b>, %95'lik "
        "dilim <b>0.7–1.1 m</b>. Baskın kaynak tespit değil, drone'un yön (yaw) tahmini: gerçek pozla hata 0.23 m'ye iniyor. "
        "<b>Kapalı döngüde</b> (FOLLOW_TARGET sadece kameradan, GPS'siz, hızsız) drone hedefi gerçek GPS kadar iyi takip etti "
        "(mesafe hatası RMS 1.27 m'ye karşı 1.33 m).<br/>"
        "<b>3) Gecikmeye dayanıklı, keskin dönüşte kırılgan.</b> FOLLOW_TARGET'a 1 s gecikme bile takibi koparmadı; "
        "%30 bağımsız kayıp neredeyse etkisiz. Ama hedef 180° dönüp drone'un altından geçerken kamera onu 2.2 s kaybediyor "
        "(PX4'ün 3 s tahmin sınırına çok yakın); bu anda <b>patlamalı kayıp veya %60 kayıp</b> olunca takip tamamen koptu. "
        "Video tarafında <b>%3 paket kaybı</b> görüntüyü belirgin bozuyor.<br/>"
        "<b>4) Vision Pi'de (drone üstünde) çalışmalı.</b> O zaman FOLLOW_TARGET Wi-Fi'dan değil Pi → Pixhawk seri "
        "hattından gider; Wi-Fi sadece operatörün videosunu taşır ve Wi-Fi kopması takibi bozmaz.", BOX))
    s.append(P("Ekibe karar önerileri", H3))
    s += bullets([
        "Kamera montajı: sabit montajsa <b>40–45° aşağı</b>; mümkünse <b>2 eksenli (pitch/roll) gimbal</b>.",
        "Takip geometrisi: <b>FLW_TGT_HT = 8 m, FLW_TGT_DST = 8 m</b> (PX4 varsayılanı) bu kamerayla uyumlu; "
        "yükseklik ve kamera eğimi birlikte seçilmeli (bakış açısı ≈ atan(yükseklik / mesafe) ≈ eğim).",
        "Hedef kaybı için PX4'te özel davranış yok (3 s tahmin, sonra bekle). Pi tarafında <b>hız tahmini (Kalman)</b> "
        "gönderilmeli ve <b>kayıpta arama davranışı</b> (son yöne dön / yüksel) tasarlanmalı.",
        "Pusula kalibrasyonu ve yön doğruluğu geolocation için en kritik kalem; kamera montaj açısı da ölçülmeli.",
        "Video: Pi hotspot + H.264 RTP (QGC 5600) uygun; kayıp için kısa anahtar kare aralığı / intra-refresh denenmeli.",
    ])

    # ---------------------------------------------------------------- 1. setup
    s.append(P("1. Ne yapıldı (simülasyona eklenenler)", H2))
    s.append(table([
        ["Eklenen", "Ne işe yarar"],
        ["baslat.sh --egim N", "Kamerası N° aşağı eğik x500 ile simülasyon. PX4 reposuna dokunmaz: üretilen model + dünya, "
                               "PX4 dünyadaki drone'a bağlanır (PX4_GZ_MODEL_NAME)."],
        ["geolocation.py", "Piksel (u, v) → kamera ışını → PX4 EKF duruşu/konumu (kare zamanına interpole) → düz zemin "
                           "kesişimi → enlem/boylam. Sadece numpy; Pi'de aynen kullanılabilir."],
        ["Panel: konum kaynağı", "FOLLOW_TARGET 'gerçek konum' (GPS'li hedef) veya 'kameradan hesap' (Vision) ile; "
                                 "hesaplanan konum ve gerçeğe göre hatası canlı."],
        ["Panel: Wi-Fi benzetimi", "FOLLOW_TARGET yoluna gecikme + kayıp (bağımsız / patlamalı); video RTP paketlerine "
                                   "gecikme + kayıp (GStreamer netsim)."],
        ["deney.py / analiz.py", "Ekransız, tekrarlanabilir deneyler ve grafikler. Test parkuru: 20 m yürü, 90° dön, 20 m, "
                                 "5 s dur, 20 m koş (3 m/s), 180° dön, 20 m, R = 10 m yarım daire, 5 s dur (~85 s)."],
        ["hata_butcesi.py", "Gerçek donanım hata seviyeleri için geolocation hata bütçesi (Monte Carlo)."],
    ], widths=[4.2 * cm, PAGE_W - 4.2 * cm]))
    s.append(P("Kadraj analizi, kaydedilen gerçek drone pozundan <b>her kamera eğimi için ayrı</b> hesaplanır: bir uçuş "
               "0–70° arası bütün eğimleri karşılaştırır. Tespit (kırmızı renk eşiği) ve geolocation ise uçuştaki gerçek "
               "Gazebo görüntüsüyle çalışır. Kutusu görüntü kenarına değen tespitler konum hesabına alınmaz (kesik kutunun "
               "alt ortası ayak noktası değildir: testte bu kareler ortalama 123 px yanlıştı).", SMALL))

    # ---------------------------------------------------------------- 2. camera
    s.append(PageBreak())
    s.append(P("2. Deney 1 — Kamera eğimi ve takip geometrisi", H2))
    s.append(P("8 yükseklik/mesafe çifti, her biri test parkurunda Follow Me (FOLLOW_TARGET gerçek konum, hızsız — "
               "Vision gibi). Değer: hedefin ayak noktasının kadrajda olduğu süre yüzdesi (kenardan 20 px pay)."))
    s.append(image(RES / "kamera_egim40" / "kadraj_isi_haritasi.png"))
    kad = kam["kadraj"]
    names = ["ht3_dst8", "ht5_dst8", "ht8_dst8", "ht12_dst8", "ht5_dst5", "ht8_dst5", "ht8_dst12", "ht12_dst12"]
    rows = [["Yükseklik / mesafe", "En iyi eğim", "Kadrajda", "Tüm vücut", "En uzun kayıp", "Bakış açısı (2–98%)",
             "40°", "45°", "Gimbal (en iyi)"]]
    hl = []
    for i, n in enumerate(names, 1):
        rs = [r for r in kad if r["senaryo"] == n]
        best = max(rs, key=lambda r: r["ayak_kadrajda"])
        g = max(rs, key=lambda r: r["gimbal_ayak_kadrajda"])
        at = {r["egim"]: r for r in rs}
        rows.append([label(n), f"{best['egim']}°", f"%{best['ayak_kadrajda']:.0f}", f"%{best['tum_vucut']:.0f}",
                     f"{best['en_uzun_kayip_s']:.1f} s",
                     f"{best['ortalama_bakis_acisi']:.0f}° ({best['bakis_acisi_min']:.0f}–{best['bakis_acisi_max']:.0f}°)",
                     f"%{at[40]['ayak_kadrajda']:.0f}", f"%{at[45]['ayak_kadrajda']:.0f}",
                     f"%{g['gimbal_ayak_kadrajda']:.0f} ({g['egim']}°)"])
        hl += [(i, 6, heat(at[40]["ayak_kadrajda"])), (i, 7, heat(at[45]["ayak_kadrajda"]))]
    s.append(table(rows, widths=[2.6 * cm, 1.6 * cm, 1.5 * cm, 1.5 * cm, 1.8 * cm, 3.0 * cm, 1.1 * cm, 1.1 * cm,
                                 PAGE_W - 14.2 * cm], highlight=hl))
    s.append(Spacer(1, 6))
    s.append(P("Okuma:", H3))
    s += bullets([
        "Düz kamera (0°) sadece 3 m yükseklikte işe yarıyor (o da %24). PX4 varsayılanı 8 m / 8 m'de %2.",
        "En iyi eğim ≈ ortalama bakış açısı = atan(yükseklik / mesafe). Tek sabit eğim seçilecekse "
        "<b>40–45°</b>: 5–12 m yükseklik ve 8–12 m mesafede %78–94.",
        "Kayıpların hepsi dikey (hedef görüntünün altından/üstünden çıkıyor), yandan çıkış yok: PX4 yaw'ı hedefe "
        "çeviriyor. Kayıplar tam olarak hedefin hızlandığı, koşmaya başladığı ve 180° döndüğü anlarda.",
        "Tüm vücut (ayak + baş) için kriter daha sıkı; yakın mesafede (5 m) baş sık sık kadraj dışı.",
    ])
    s.append(image(RES / "kamera_egim40" / "piksel_zaman_ht8_dst8.png",
                   caption="8 m / 8 m: hedefin ayak noktasının dikey piksel konumu (yeşil bant = kadraj). 0° ve 20° "
                           "eğimde hedef neredeyse hep görüntünün altında; 40° eğimde sadece manevralarda dışarı taşıyor."))
    s.append(image(make_gimbal_figure(kad), caption="Sabit montaj ile 2 eksenli gimbal karşılaştırması (aynı uçuşlar, "
                                                    "gimbal yaw'ı drone'a bağlı, roll/pitch'i dengeliyor)."))
    s.append(image(RES / "kamera_egim40" / "takip_kamera_egim40.png",
                   caption="Sol: hedef–drone mesafesi. Koşu (t ≈ 35 s) mesafeyi +5 m açıyor (hız gönderilmediği için "
                           "drone geride kalıyor); 180° dönüşte (t ≈ 42 s) hedef drone'un altına giriyor. Sağ: 8 m / 8 m "
                           "uçuşunun üstten görünüşü; dönüşlerde drone hedefin arkasına geçmek için yay çiziyor."))

    # ---------------------------------------------------------------- 3. geolocation
    s.append(PageBreak())
    s.append(P("3. Deney 2 — Geolocation (kameradan hedef konumu)", H2))
    s.append(P("Kamera 45° eğik. <b>Açık döngü</b>: drone gerçek konumu takip eder, kamera hesabı sadece ölçülür. "
               "<b>Kapalı döngü</b>: FOLLOW_TARGET sadece kameradan hesaplanan konumla (hızsız), hedef görünmüyorsa hiç "
               "gönderilmez — gerçek Vision sistemi gibi. Hata, kare anındaki gerçek hedef konumuna göre yatay mesafedir."))
    rows = [["Uçuş", "Yük. / mes.", "Fix sayısı", "Hata medyan", "Hata %95", "Gerçek pozla medyan", "EKF yön hatası",
             "Bakış açısı"]]
    for n in ["acik_ht5_dst8", "acik_ht8_dst8", "acik_ht12_dst8", "kapali_ht8_dst8", "kapali_ht5_dst8"]:
        g = geo["geolocation"][n]
        rows.append(["açık" if n.startswith("acik") else "kapalı", label(n), str(g["n"]), f"{g['medyan_m']:.2f} m",
                     f"{g['p95_m']:.2f} m", f"{g['gercek_poz_ile_medyan_m']:.2f} m",
                     f"{g['ekf_yon_hatasi_ort_derece']:+.1f}° ± {g['ekf_yon_hatasi_std_derece']:.1f}°",
                     f"{g['ortalama_bakis_acisi']:.0f}°"])
    s.append(table(rows, widths=[1.4 * cm, 2.0 * cm, 1.7 * cm, 2.0 * cm, 1.8 * cm, 2.8 * cm, 3.0 * cm,
                                 PAGE_W - 14.7 * cm]))
    s.append(Spacer(1, 6))
    s += bullets([
        "Hata ortanca 0.4–0.6 m. <b>Gerçek (Gazebo) pozla aynı pikselden hesap 0.23 m</b>: farkın kaynağı drone'un "
        "kendi yön tahmini (SITL'de EKF yaw'ı 1–3° sapıyor). Saçılım grafiğindeki halka, drone döndükçe dönen bu sabit "
        "yan kaymanın imzası.",
        "Kalan 0.23 m: tespit kutusunun alt kenarı (hedefin kameraya yakın ayak kenarı), zaman eşleme ve kare çözünürlüğü.",
        "Yükseklik arttıkça (dik bakış) hata azalıyor: 5 m'de 0.62, 12 m'de 0.42 m — hata bütçesiyle uyumlu.",
        "Pikselin zamanı = kamera karesinin zamanı; EKF pozu o ana interpole ediliyor. SITL'de Gazebo zamanı = PX4 "
        "zamanı (ölçüldü: 3.293 s / 3.284 s). Gerçek sistemde picamera2 zaman damgası ile MAVLink zamanı "
        "(TIMESYNC / SYSTEM_TIME) eşlenmeli.",
    ])
    s.append(image(RES / "geolocation_egim45" / "geolocation_hata.png"))
    t = geo["takip"]
    s.append(P("Kapalı döngü: drone sadece kamerayla takip ediyor", H3))
    rows = [["Uçuş", "Konum kaynağı", "Mesafe ort.", "Mesafe hatası RMS", "Min / max mesafe", "Kadrajda",
             "En uzun kayıp"]]
    for n in ["acik_ht8_dst8", "kapali_ht8_dst8", "acik_ht5_dst8", "kapali_ht5_dst8"]:
        x = t[n]
        rows.append([label(n), "gerçek konum" if x["kaynak"] == "gercek" else "<b>kamera</b>",
                     f"{x['mesafe_ort_m']:.1f} m", f"{x['mesafe_hatasi_rms_m']:.2f} m",
                     f"{x['mesafe_min_m']:.1f} / {x['mesafe_max_m']:.1f} m", f"%{x['ayak_kadrajda_yuzde']:.0f}",
                     f"{x['en_uzun_kayip_s']:.1f} s"])
    s.append(table(rows, widths=[2.2 * cm, 2.6 * cm, 2.0 * cm, 2.9 * cm, 2.8 * cm, 1.8 * cm, PAGE_W - 14.3 * cm],
                   highlight=[(4, 5, "#f6c9c4"), (4, 6, "#f6c9c4"), (2, 3, "#c8ecc9")]))
    s.append(Spacer(1, 4))
    s += bullets([
        "<b>8 m / 8 m, kamera 45°:</b> sadece kamerayla takip gerçek konumla takip kadar iyi; en uzun kayıp 2.1 s "
        "(PX4 3 s tahmin ediyor), takip hiç kopmadı.",
        "<b>5 m / 8 m, kamera 45°:</b> geometri bu eğime uymuyor (en iyi eğim 35°). 180° dönüşte hedef kadrajdan "
        "çıktı, 3 s sonra PX4 durdu, hedef 28 m uzaklaştı: 20.6 s kayıp. <b>Kamera eğimi ile takip yüksekliği birlikte "
        "seçilmeli</b> ve hedef kaybında bir arama davranışı gerekli.",
    ])

    budget_block = [P("Gerçek donanım için hata bütçesi (Monte Carlo)", H3)]
    budget_block.append(P("Kamera hedefe ortalanmış; her sütunda tek hata kaynağı (1σ), son sütunda hepsi birlikte. Değerler: "
               "medyan / %95 yatay hata (m). Varsayımlar gerçek ölçümlerle değiştirilmeli (hata_butcesi.py).", SMALL))
    keys = [k for k in budget[0] if k not in ("yukseklik", "mesafe", "bakis_acisi")]
    rows = [["Yük. / mes.", "Bakış"] + keys]
    for r in budget:
        rows.append([f"{r['yukseklik']} / {r['mesafe']} m", f"{r['bakis_acisi']:.0f}°"] +
                    [f"{r[k][0]:.2f} / {r[k][1]:.2f}" if r[k] else "—" for k in keys])
    w0 = 1.9 * cm
    budget_block.append(table(rows, widths=[w0, 1.2 * cm] + [(PAGE_W - w0 - 1.2 * cm) / len(keys)] * len(keys)))
    s.append(KeepTogether(budget_block))
    s += bullets([
        "En büyük kalemler <b>yükseklik hatası</b> ve <b>zeminin düz olmaması</b>; sığ bakışta (3 m / 8 m) "
        "%95 hata 3.3 m'ye çıkıyor, dik bakışta (8 m / 5 m) 0.9 m. Dik bakmak geolocation için de iyi.",
        "Piksel hatası (5 px) önemsiz: 1774 px odak uzaklığında 5 px ≈ 0.16°.",
        "Drone'un GPS hatası tabloda yok: <b>takip için</b> büyük ölçüde sıfırlanır (PX4 hedefi ve kendini aynı "
        "GPS/EKF ile görür); <b>hedef koordinatını raporlarken</b> (arama-kurtarma) doğrudan eklenir.",
    ], SMALL)

    # ---------------------------------------------------------------- 4. latency
    s.append(PageBreak())
    s.append(P("4. Deney 3 — Gecikme ve kayıp (Wi-Fi benzetimi)", H2))
    s.append(P("8 m / 8 m, kamera 45°, <b>kapalı döngü</b> (FOLLOW_TARGET kameradan). Gecikme/kayıp FOLLOW_TARGET "
               "yoluna eklendi. Bu yol, Vision Pi'de çalışırsa <b>işlem gecikmesini</b> (kamera → tespit → hesap), tespit "
               "yerde yapılırsa <b>Wi-Fi + işlem</b> gecikmesini temsil eder. Patlamalı kayıp: kayıplar ortalama 20 mesajlık "
               "(2 s) kesintiler halinde."))
    rows = [["Gecikme", "Kayıp", "Mesafe hatası RMS", "Min / max mesafe", "Kadrajda", "En uzun kayıp", "Sonuç"]]
    hl = []
    order = sorted(gec["takip"], key=lambda n: (gec["takip"][n]["ft_gecikme_s"], gec["takip"][n]["ft_kayip"],
                                                gec["takip"][n]["ft_patlama"]))
    for i, n in enumerate(order, 1):
        x = gec["takip"][n]
        broke = x["kayip_3s_ustu"] > 0
        rows.append([f"{x['ft_gecikme_s'] * 1000:.0f} ms",
                     f"%{x['ft_kayip'] * 100:.0f}" + (" patlamalı" if x["ft_patlama"] > 1 else ""),
                     f"{x['mesafe_hatasi_rms_m']:.2f} m", f"{x['mesafe_min_m']:.1f} / {x['mesafe_max_m']:.1f} m",
                     f"%{x['ayak_kadrajda_yuzde']:.0f}", f"{x['en_uzun_kayip_s']:.1f} s",
                     "TAKİP KOPTU" if broke else "takip sürdü"])
        hl.append((i, 6, "#f6c9c4" if broke else "#c8ecc9"))
    s.append(table(rows, widths=[1.8 * cm, 2.4 * cm, 2.8 * cm, 2.8 * cm, 1.7 * cm, 2.2 * cm, PAGE_W - 13.7 * cm],
                   highlight=hl))
    s.append(Spacer(1, 6))
    s.append(image(make_latency_figure(gec["takip"])))
    s += bullets([
        "<b>Gecikme:</b> 200 ms → 1 s arasında takip bozulmuyor, sadece gevşiyor (RMS 1.3 → 2.4 m, 180° dönüşte drone "
        "hedefe 2.2 m'ye kadar yaklaşıyor). Pi 5 üzerinde tespit + hesap için 100–300 ms makul bir hedef.",
        "<b>Bağımsız %30 kayıp</b> etkisiz (10 Hz'de 3 s içinde yeterli mesaj geliyor).",
        "<b>Patlamalı %30 veya %60 kayıp</b>: kesinti 180° dönüşe denk gelince hedef drone'un altından/arkasından "
        "kadrajdan çıkıyor; yeni tespit gelmediği için PX4 3 s sonra duruyor ve hedef bir daha görülmüyor (45 s kayıp, "
        "30 m uzaklaşma). Zayıf nokta ortalama kayıp değil, <b>keskin dönüş anındaki kesinti</b>.",
        "Çözüm önerileri: Pi'de hedef için <b>Kalman filtresi</b> (konum + hız) ve FOLLOW_TARGET'a hız alanını doldurmak "
        "(PX4 kayıpta son hızla ilerler); kayıpta <b>son görülen yöne yaw + yükselme</b> ile arama; gimbal; dönüşte daha "
        "büyük takip mesafesi.",
    ])

    s.append(P("Video (Pi → dizüstü Wi-Fi, H.264 RTP)", H3))
    rows = [["Gecikme", "Paket kaybı", "Alınan kare hızı"]] + [
        [f"{v['gecikme_ms']} ms", f"%{v['kayip'] * 100:g}", f"{v['alinan_fps']} fps"] for v in video]
    s.append(table(rows, widths=[3 * cm, 3 * cm, 3.5 * cm]))
    s.append(Spacer(1, 4))
    s.append(image(make_video_figure(), width=PAGE_W * 0.92,
                   caption="Alıcıda (QGC ile aynı yayın) yakalanan kareler. Kod çözücü kare hızını korur ama kayıp "
                           "paketlerin yerini eski bloklarla doldurur; bozulma bir sonraki anahtar kareye (1 s) kadar sürer."))
    s += bullets([
        "Kare hızı her durumda 15 fps; kayıp <b>görüntü kalitesinde</b> görülüyor: %3'te belirgin bloklar, %10'da "
        "görüntü kullanılmaz. 300 ms gecikme görüntüyü bozmaz, sadece geç gösterir.",
        "Öneriler: Wi-Fi'da UDP kaybını düşük tutmak (5 GHz, harici anten, 100 m sınırı), anahtar kare aralığını "
        "kısaltmak (ör. 0.5 s) veya x264 <i>intra-refresh</i>, gerekirse bit hızını düşürmek. Bunlar simülasyonda "
        "<font face='DejaVuMono'>goruntu_yayini.py --keyframe</font> ile denenebilir.",
        "Tespit Pi'de yapılırsa video bozulması takibi etkilemez (tespit sıkıştırılmamış görüntüde çalışır).",
    ])

    # ---------------------------------------------------------------- 5. architecture + limits
    s.append(P("5. Arkadaşın sorusu: “Raspberry Pi'yi sunucu olarak mı kuruyoruz?”", H2))
    s.append(P("Evet, iki anlamda: (1) <b>Ağ</b>: Pi kendi Wi-Fi ağını yayınlar (hotspot / erişim noktası), dizüstü "
               "bu ağa bağlanır, ayrı modem gerekmez. (2) <b>Video</b>: Pi kamerayı H.264'e çevirip dizüstünün IP'sine "
               "UDP/RTP ile sürekli yollar (port 5600, QGC gösterir); klasik istemci–sunucu bağlantısı yoktur. "
               "Takip komutu (FOLLOW_TARGET) ise Wi-Fi'dan değil, Pi → Pixhawk seri hattından gider. Açık soru: hotspot "
               "Pi'de mi olsun, yerde küçük bir router mı (menzil ve anten açısından router daha güçlü olabilir)."))
    s.append(P("6. Sınırlamalar", H2))
    s += bullets([
        "Simülasyon: düz zemin, rüzgâr yok, ideal kamera (distorsiyon yok, fx = 1774 px; gerçek değer kalibrasyonla "
        "bulunmalı — datasheet'ten ≈ 1693 px), basit renk eşiği tespiti (gerçek Vision algoritması değil).",
        "Hedef kinematik ve tek kişi; kalabalık, örtme (ağaç, araç), ışık değişimi yok.",
        "SITL sensör gürültüsü gerçek Pixhawk 6C'den farklı; özellikle yön hatası sahada ölçülmeli.",
        "Gecikme benzetiminde FOLLOW_TARGET 50 ms adımlarla bırakılıyor (20 Hz döngü).",
    ])
    s.append(P("7. Sonraki adımlar", H2))
    s += bullets([
        "Ekip kararı: kamera eğimi (40–45°) veya gimbal; takip yüksekliği/mesafesi.",
        "Pi tarafı: tespit → geolocation.py → Kalman → FOLLOW_TARGET (konum + hız) zinciri; Pi ↔ Pixhawk arayüzü (ICD).",
        "Kamera kalibrasyonu (fx, fy, cx, cy, k1..k3) ve montaj açısının ölçümü; simülasyondaki kamerayı güncellemek.",
        "Hedef kaybı davranışı (arama) ve dönüşte geometri ayarı için simülasyon denemeleri.",
        "Sahada: Wi-Fi menzil ve paket kaybı ölçümü, Pi 5'te tespit + kodlama işlemci yükü.",
    ])
    s.append(Spacer(1, 6))
    s.append(P("Tüm kod ve veriler: <font face='DejaVuMono'>~/follow_sim</font> (WSL). Deneyleri tekrar çalıştırmak için "
               "README.md 'Deneyler' bölümü. Grafikler <font face='DejaVuMono'>~/follow_sim/sonuclar/</font> altında.", SMALL))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("DejaVu", 7.5)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawString(1.8 * cm, 1.1 * cm, "Auto-Follow · kamera açısı / geolocation / Wi-Fi simülasyonu")
        canvas.drawRightString(A4[0] - 1.8 * cm, 1.1 * cm, f"Sayfa {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(out_pdf), pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.6 * cm,
                            bottomMargin=1.7 * cm, title="Auto-Follow — Kamera Açısı, Geolocation ve Wi-Fi Benzetimi",
                            author="Ahmet (Claude Code)")
    doc.build(s, onFirstPage=footer, onLaterPages=footer)
    print(f"Rapor: {out_pdf}")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else RES / "Kamera_Geolocation_WiFi_Raporu.pdf")
