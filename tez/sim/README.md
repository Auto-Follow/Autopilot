# Auto-Follow simülasyon ortamı (`tez/sim`)

Görüntü işleme (Vision) ve kontrol (PX4 içindeki tez modu) ekiplerinin kodlarını gerçek uçuştan önce Gazebo'da
**ölçerek** denemesi için ortak ortam. Tasarım: "Auto-Follow Simülasyon ve Test Ortamı — Tasarım Önerisi" belgesi.

> **Durum: F1 (hakem çekirdeği).** Tez dronu + düz alan + PX4'te görünen "Tez Auto Follow" modu (iskelet: yerinde
> bekler) + yürüyen insan hedefi, YAML senaryo, doğru cevap kaydı, ULog ve otomatik HTML rapor.
> Sıradaki: F2 (kontrol ekibi için "mükemmel algılayıcı"), F3 (görüntü ekibi için kamera ve etiketli kareler).

PX4 kaynağı değişmez. Tez modu `tez/px4/` altında **harici modül** olarak derlenir; dron ve dünya `tez/sim/` altında
durur. PX4 tarafında sadece kilit listesinde izinli iki dosya eklenir: airframe `4030_gz_x500_tez` (+ `.post`).

## Kurulum (bir kere)

Ön koşul: [`TEZ_README.md`](../../TEZ_README.md) kurulumu tamam, `make px4_sitl` çalışıyor.

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot
tez/sim/derle.sh            # ilk sefer birkaç dakika; çıktı build/px4_sitl_tez
tez/sim/kur.sh              # insan hedef modelini indirir (~11 MB, sha256 kontrollü; git'e girmez)
```

`derle.sh` ayrı bir klasöre derler; ekibin normal `build/px4_sitl_default` derlemesine dokunmaz.
Tez modunun kodunu değiştirdikten sonra yine `tez/sim/derle.sh` (sadece değişen dosyalar derlenir).

## Çalıştırma

```bash
tez/sim/calistir.sh               # Gazebo penceresi + bu terminalde PX4 kabuğu (pxh>)
tez/sim/calistir.sh --ekransiz    # pencere yok (otomatik testler için)
```

- QGroundControl'ü açın; kendiliğinden bağlanır (UDP 14550).
- Kalkış: QGC'de **Takeoff** (10 m'ye kalkar; yükseklik `MIS_TAKEOFF_ALT`).
- Havadayken uçuş modu listesinden **Tez Auto Follow** seçin. Şu anki iskelet seçildiği yerde havada bekler.
- Tez modunda yerde arm edilemez (PX4 Follow Me gibi): önce başka modla kalkın.
- Kapatma: `pxh>` içinde `shutdown` veya Ctrl+C. Gazebo da kapanır.
- Her açılış temiz parametrelerle başlar (ekip standardı: testler birbirinin parametresini devralmaz).

Kamera: Camera Module 3 Standard (yatay 66°, 2304×1296, 30 fps), gövdenin altında ön kızaklardaki tutucuda
(X500 V2 "Depth Camera Mount" yeri), 45° aşağı, Gazebo konusu
`/x500_tez/kamera/image` (+ `/x500_tez/kamera/camera_info`).

## F0 kabul testi

```bash
tez/sim/araclar/f0_kabul.sh              # simi kendisi açar (pencere yok), ~1.5 dakika, sonunda "SONUÇ: GEÇTİ"
tez/sim/araclar/f0_kabul.sh --acik-sim   # zaten açık bir sim üzerinde (ör. Gazebo + QGC penceresiyle izlemek için)
```

Kontrol ettikleri: kamera çözünürlüğü, hızı (sim saniyesi başına kare) ve odak uzaklığı; modun QGC listesinde
olması; yerde arm reddi; 10 m kalkış; tez moduna geçiş ve 15 s konum tutma (sapma < 0.5 m); iniş ve disarm; PX4 ve
Gazebo'nun temiz kapanması; modun hiç "unresponsive" işaretlenmemesi. Log: `build/px4_sitl_tez/tez_kabul/sim.log`.

## Senaryolar (F1)

Senaryo, hedefin yolunu ve dronun ne yapacağını anlatan bir YAML dosyasıdır (`tez/sim/senaryolar/`). Koşturmak:

```bash
P=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python
$P tez/sim/araclar/senaryo.py --senaryo yuruyen_insan              # Gazebo penceresiyle (~3 dakika)
$P tez/sim/araclar/senaryo.py --senaryo yuruyen_insan --ekransiz   # pencere yok
$P tez/sim/araclar/senaryo.py --senaryo yuruyen_insan --dogrula    # + tepe kamerasıyla hedef konumu kontrolü
```

Senaryo yöneticisi dünyayı (temel dünya + hedef) yazar, Gazebo ve PX4'ü açar, dronu kaldırır ve senaryonun moduna
alır, hedef yürürken doğru cevabı kaydeder, iner, kapatır ve raporu yazar. Çıktı `tez/sim/sonuclar/<tarih>_<ad>/`
(git'e girmez):

| Dosya | İçerik |
|---|---|
| `rapor.html` | Sonuç (GEÇTİ / KALDI / TAMAMLANMADI), ölçütler, üstten harita, mesafe ve kamera görüntüsü grafikleri |
| `dogru_cevap.csv` | **Dron kamerasının her karesi için bir satır** (~30 Hz, karenin sim zamanıyla): dron konumu ve duruşu (roll/pitch/yaw, PX4 yönleriyle), kamera konumu, hedef konumu/hızı, hedefin o karedeki pikseli (ayak, merkez, baş) ve kadrajda olup olmadığı, kameradan hedefe menzil ve **doğru görüş vektörü** (aşağıda) |
| `ozet.json` | Ölçütler ve sonuç (makineyle okunur); kameranın kalibrasyonu ve gövdeye montajı (ofset, C_cb) |
| `ucus.ulg` | PX4 uçuş kaydı (PlotJuggler / pyulog) |
| `dunya.sdf`, `senaryo.yaml`, `sim.log` | Koşunun girdileri ve logu |

Yeni senaryo yazmak için `senaryolar/yuruyen_insan.yaml`'ı kopyalayın. Alanlar:

- `drone.yukseklik_m`, `drone.mod` (`tez` veya `bekle` = PX4 Hold)
- `hedef.baslangic: [x, y]` ve `hedef.yol`: sırayla `{nokta: [x, y], hiz_mps: v}` (v > 2 m/s koşu) veya `{dur_s: s}`
- `zamanlama.baslama_s`: hedefin yürümeye başladığı simülasyon zamanı (dron o ana kadar hazır olmalı; ~30 s sürer)
- `basari`: eşikler — `kadrajda_kalma_min`, `en_uzun_kayip_max_s`, `yatay_mesafe_max_m`. Boşsa sadece ölçülür.

Koordinatlar Gazebo dünyasına göredir: **x doğu, y kuzey [m]**; dron (0, 0)'dan doğuya bakarak kalkar. Yanlış yazılan
bir alan, hangi alan olduğu söylenerek reddedilir.

Görüş vektörü (LOS) sütunları, ekibin "Pikselden Vektöre Dönüşüm" belgesindeki zincirle aynı eksenlerdedir
(`araclar/kamera.py`, testleri belgenin örnek sayılarını kullanır):

| Sütun | Eksenler |
|---|---|
| `los_kamera_x/y/z` | kamera optik eksenleri: x sağ, y aşağı, z ileri (görüntü işlemenin ürettiği vektör) |
| `los_govde_x/y/z` | gövde FRD: x burun, y sağ, z aşağı (kameradan hedefe, gövde eksenlerinde) |
| `los_ned_x/y/z` | NED: kuzey, doğu, aşağı |
| `sapma_yatay_deg`, `sapma_dikey_deg` | burundan sapma: sağa ve aşağı pozitif |

Görüş vektörü hedefin gövde merkezine (yerden 0.9 m) göredir. Gazebo dünya koordinatları (`dron_x`, `hedef_x`...)
ise x doğu, y kuzey, z yukarı.

Doğru cevap hakkında: Gazebo Harmonic insan (actor) konumunu yayınlamaz; hedefin konumu senaryodaki yoldan
hesaplanır. `--dogrula` bunu tepe kamerasıyla kontrol eder (gölgeler kapanır); yürürken gövde merkezi yolun
0.05–0.19 m önündedir. Ayrıntı: `models/insan/KAYNAK.md`.

F1 kabul testi (senaryoyu iki kez koşar, ~6 dakika; `araclar/f1_testi.py`):

```bash
tez/sim/araclar/f1_kabul.sh       # her koşuda hedef farkı ≤ 0.3 m, iki koşu aynı (≤ 0.15 m)
```

## Kontrol ekibi: modu nereye yazıyorum?

`tez/px4/src/modules/tez_auto_follow/TezAutoFollow.cpp`

- Mod kaydı, kalkış öncesi kontrollere cevap ve modun aktif olup olmadığı hazır; dokunmanız gerekmez.
- Takip mantığı `update_setpoint()` içine yazılır: her 10 ms'de bir `trajectory_setpoint` (NED konum, hız, yaw)
  yayınlanır, PX4'ün konum kontrolcüsü onu izler.
- Yeni parametreler `TEZ_` ön ekiyle (`standards/px4/uorb-params.md`).
- Gerçek kart için de derlenir: `make px4_fmu-v6c_default EXTERNAL_MODULES_LOCATION=$PWD/tez/px4`
  (gerçek araçta modül SD karttaki `etc/extras.txt` içine `tez_auto_follow start` yazılarak başlatılır).

## Dosyalar

| Yol | Ne |
|---|---|
| `tez/sim/derle.sh` | PX4 SITL + tez modülleri → `build/px4_sitl_tez` |
| `tez/sim/calistir.sh` | Gazebo + PX4'ü başlatır |
| `tez/sim/models/x500_tez/` | X500 (PX4 `x500` modeli) + gövde altında 45° Camera Module 3 (tutucu ölçüleri yaklaşık) |
| `tez/sim/worlds/duz_alan.sdf` | 500 m × 500 m düz çim alan; dron dünyanın içinde (`x500_tez_0`) |
| `tez/sim/server.config` | Gazebo sistemleri (PX4'ünkinin GStreamer kamerasız hali) |
| `tez/sim/kur.sh` | Git'e girmeyen dosyaları indirir (insan modeli) |
| `tez/sim/models/insan/` | İnsan hedef (Gazebo Fuel Mingfei/actor, CC BY 4.0; kaynak: `KAYNAK.md`) |
| `tez/sim/senaryolar/` | Senaryo dosyaları (YAML) |
| `tez/sim/araclar/senaryo.py` | Senaryo yöneticisi; `hedef.py` (yol, doğru cevap, dünya), `kayit.py` (kare kare kayıt), `kamera.py` (kamera modeli, eksen dönüşümleri), `dogrulama.py` (tepe kamerası), `rapor.py` (rapor), `simulasyon.py` (simi açar/kapatır), `px4_baglanti.py` (MAVLink) |
| `tez/sim/araclar/f0_kabul.sh`, `f1_kabul.sh` | Kabul testleri (`f0_testi.py`, `f1_testi.py`) |
| `tez/sim/testler/` | Donanımsız birim testleri (pytest) |
| `tez/px4/src/modules/tez_auto_follow/` | Tez uçuş modu (iskelet) |
| `ROMFS/.../airframes/4030_gz_x500_tez(.post)` | SITL airframe: x500 + gerçek X500 V2 (4019) açısal hız kazançları; modu başlatır |

Python araçları:

```bash
P=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python
$P -m pytest tez/sim/testler                     # birim testleri, simsiz, ~1 s
../Vision/.venv/bin/ruff format --config tez/sim/ruff.toml tez/sim && ../Vision/.venv/bin/ruff check --config tez/sim/ruff.toml tez/sim
```
