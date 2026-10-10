# Auto-Follow simülasyon ortamı (`tez/sim`)

Görüntü işleme (Vision) ve kontrol (PX4 içindeki tez modu) ekiplerinin kodlarını gerçek uçuştan önce Gazebo'da
**ölçerek** denemesi için ortak ortam. Tasarım: "Auto-Follow Simülasyon ve Test Ortamı — Tasarım Önerisi" belgesi.

> **Durum: F0 (iskelet).** Tez dronu + düz alan dünyası + PX4'te görünen boş "Tez Auto Follow" modu.
> Hedef (yürüyen insan), senaryolar, hakem ve rapor sonraki aşamalarda (F1–F4) gelecek.

PX4 kaynağı değişmez. Tez modu `tez/px4/` altında **harici modül** olarak derlenir; dron ve dünya `tez/sim/` altında
durur. PX4 tarafında sadece kilit listesinde izinli iki dosya eklenir: airframe `4030_gz_x500_tez` (+ `.post`).

## Kurulum (bir kere)

Ön koşul: [`TEZ_README.md`](../../TEZ_README.md) kurulumu tamam, `make px4_sitl` çalışıyor.

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot
tez/sim/derle.sh            # ilk sefer birkaç dakika; çıktı build/px4_sitl_tez
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
tez/sim/araclar/f0_kabul.sh       # pencere açmaz, ~2 dakika, sonunda "SONUÇ: GEÇTİ"
```

Kontrol ettikleri: kamera çözünürlüğü, hızı ve odak uzaklığı; modun QGC listesinde olması; yerde arm reddi;
10 m kalkış; tez moduna geçiş ve 15 s konum tutma (sapma < 0.5 m); iniş ve disarm; PX4 ve Gazebo'nun temiz
kapanması. Loglar: `build/px4_sitl_tez/tez_kabul/`.

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
| `tez/sim/araclar/` | Kabul testleri |
| `tez/px4/src/modules/tez_auto_follow/` | Tez uçuş modu (iskelet) |
| `ROMFS/.../airframes/4030_gz_x500_tez(.post)` | SITL airframe: x500 + gerçek X500 V2 (4019) açısal hız kazançları; modu başlatır |

Python araçları: `ruff format tez/sim && ruff check tez/sim` (`tez/sim/ruff.toml`).
