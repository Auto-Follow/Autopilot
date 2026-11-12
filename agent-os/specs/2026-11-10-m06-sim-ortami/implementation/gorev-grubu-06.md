# Görev Grubu 6 — Düz zemin konum hesabı, `FOLLOW_TARGET` ve stok Follow Me ile kapalı döngü

- Tarih: 12.11.2026 · dal `ozellik/m06-sim-ortami` · taban commit `cba2f344eb` (Görev grubu 5); bütün koşular
  `cba2f344eb` + çalışma ağacı üstünde
- Durum: **uygulandı ve test edildi**, commit'lenmedi.
- Kısaca: Döngü kapandı. Model kişiyi dronun kamerasında buluyor; seçilen kutunun alt ortası (ayak noktası), karenin
  çekildiği andaki EKF pozuyla düz zemine izdüşürülüyor; bulunan yer enlem/boylam olarak PX4'e `FOLLOW_TARGET`
  gidiyor ve stok **Follow Me** ("Follow Target") dronu kişinin 8 m gerisinde, 8 m yükseklikte tutuyor. Mod her koşuda
  kayıt boyunca "Follow Target"te kaldı. `takip_yuruyen`'de "mükemmel algılayıcı" (hakem) kaynağıyla yatay mesafe ort.
  **7.59 m**; model kaynağıyla üç ölçüm koşusunun ikisinde dron kişiyi sonuna kadar izledi (ort. **7.38 / 7.54 m**),
  birinde kişi köşede koşmaya başlayınca kaybetti. Gönderilen konumun hatası ort. **0.49–1.12 m**; bunun yalnız
  0.21–0.27 m'si kutunun kendisinden, gerisi koşudan koşuya değişen EKF yaw kaymasından (−2.4°…+8.5°).
- Önemli bulgular: (1) Model kişiyi göremeyince PX4 son hızla 3 s öngörmeye devam ediyor; hedef köşede geri
  dönerken dron kişinin **0.76 m** yakınına (tepesine) kadar geldi. (2) Seçim tek bir karede başka bir kişiye
  atlayınca o tek `FOLLOW_TARGET`, PX4'ün kestiricisinde 6–10 m/s'lik sahte bir hıza dönüşüyor; `kalabalik_park`'ta dron
  hedeften 35 m uzaklaşıp hayalet bir noktanın gerisinde asılı kaldı. (3) PX4 v1.17.0'ın kaydedicisi `follow_target*`
  konularını stok ayarla hiç yazmıyor (gerçek araçta da).
- `FOLLOW_TARGET` kullanımı ve düz zemin hesabı ortak ICD (m05) yazılmadığı için **varsayımdır** (spec "Varsayımlar"
  5–6); kesinleşmiş değildir.

## Ne yapıldı

| Alt görev | Dosya | Özet |
|---|---|---|
| 6.1 | `testler/test_konumlama.py` (yeni, 5 test fonksiyonu, 12 durum) | Bilinen pozdan zemin noktası → piksel → kutu → konum, < 1 cm (4 duruş × 2 kamera, biri bozulmalı; PX4 izdüşümüyle enlem/boylam gidiş-dönüşü dahil); `u_D` eşiğinin iki yanı (0.24 ret, 0.26 kabul); sol/sağ/alt kenar reddi ve üst kenarın kabulü (8 px sınırının iki yanı); poz geçmişinin kare anını 0.15 s içinde kapsaması, nlerp/doğrusal ara değer, `poz_yok` ve `referans_yok`; PX4 `MapProjection` ve Gazebo WGS84 (gz-math 7.7.0'ın LOCAL2 değerleriyle) dönüşümleri |
| 6.1 | `testler/test_mesajlar.py` (+4) | `FOLLOW_TARGET` paketleme/çözme (1e7 tamsayı, yuvarlama, NaN hız, `est_capabilities=1`, `alt`) ve geçersiz konumun reddi; akış kuralları (her üçüncü kamera karesi, aynı / eski kare, bağlantı yok, geçersiz); poz kancası (yalnız otopilotun mesajları, köken, ev); EKF kökeninin istenmesi (`wait_references`) |
| 6.1 | `testler/test_takip.py` (+3), `test_hedef.py` (+1, 1 güncellendi), `test_rapor.py` (+1) | Takip iş parçacığı: model kutusundan `FOLLOW_TARGET`, `algilama.csv` konum sütunları, `follow_target.csv`; hakem kaynağında gerçek konum yalnız görünürken; kaydedicinin bir kez yeniden başlatılması; `FLW_TGT_HT` kuralı; ara durum testinde `follow_me` artık bağlı; ULog'daki `follow_target` sayımı ve PX4 kestiriminin hatası, bayat süre |
| 6.2 | `araclar/konumlama.py` (yeni) | `PoseHistory` (EKF pozu, köken, ev; kilitli), `Locator` (ayak noktası → ışın → zemin → enlem/boylam, ret nedenleri), `MapProjection` (PX4 lib/geo'nun aynısı), `WorldGeo` + `world_geo` (Gazebo dünyasının WGS84 kökeni; değerlendirme), `true_pose_hit` (aynı ışın dronun gerçek pozuyla; değerlendirme), nominal montaj sabitleri |
| 6.3 | `araclar/px4_baglanti.py` | `FrameStream` (TEZ_LOS ve FOLLOW_TARGET'ın ortak akış kuralları), `LosSender` ona taşındı, `FollowTargetSender` (≥ 96 ms), `check_follow_target`, `follow_target_message`, `pose_hook` (`message_hooks`), `Vehicle.poses`, `Vehicle.request_message` / `wait_references` (EKF kökeni ve ev noktası istenir), `Vehicle.send_follow_target`, akış hızları `ATTITUDE_QUATERNION` 50 Hz / `LOCAL_POSITION_NED` 30 Hz |
| 6.4 | `araclar/takip.py` | Her işlenen karede konum (`Locator`) ve `algilama.csv`'de 29 yeni sütun; `follow_me`'de `FOLLOW_TARGET` (model: kutunun konumu; hakem: gerçek konum, yalnız görünürken) aynı gecikme hattından; `follow_target.csv`; özet (`ozet.json` → `follow_target`) ve geçici ölçütler (`geolocation_hatasi_*`, `konum_hatasi_*`, `konum_hatasi_gercek_pozla_*`, `ekf_yaw_hatasi_*`, `ekf_yatay_konum_hatasi_*`, `follow_target_*`) |
| 6.4 | `araclar/hedef.py`, `senaryo.py`, `simulasyon.py`, `rapor.py` | `follow_me` ara hatası kaldırıldı; `FLW_TGT_HT` kuralı; Tracker'a konum/dünya/gerçek bağlandı; `yatay_mesafe_hatasi_ort_m`; PX4 kaydedicisinin `follow_me`'de bir kez yeniden başlatılması (`Simulation.restart_logger`, `ulogs()`, `ucus_once.ulg`); `rapor.follow_target_in_ulog` / `ulog_follow_target` ve rapor etiketleri |
| belge | `tez/sim/README.md`, `senaryolar/takip_yuruyen.yaml`, `ruff.toml`, `spec.md`, `tasks.md`, `implementation/kabul-kosulari.md`, `gorev-grubu-05.md` | README: "Konum hesabı ve stok Follow Me", yeni çıktılar ve sütunlar; ruff: `konumlama`; spec: uygulama notları, Varsayımlar 3/5/6, ölçüt tablosu, Test Planı notu, Açık Konular; tasks: 6.x işaretlendi, 12. gruba 12.4 (yeniden kilit bekleme süresi); 5. grubun üç açık kararı karara bağlandı |

## Kararlar ve gerekçeler

1. **Konum her takip kaynağında hesaplanır**, `FOLLOW_TARGET` yalnız `follow_me`'de gider. Böylece `yok` ve `tez_los`
   koşuları da (m10'un dönüşümünü ve m15'in modunu deneyenler için) aynı konum ölçütlerini verir.
2. **Ayak noktası kutunun alt ortası** `((u0 + u1) / 2, v1)`. Kişi ayakta olduğu için kutunun alt kenarı kameraya en
   yakın ayaktır (≈ 25 cm öne kayık; ölçütlerde görünür). **Kenar kuralı sol, sağ, alt** kenar için: başı üstten
   kesik bir kişinin ayakları yerindedir; spec'in gerekçesi ("ayak görünmüyor olabilir") alt kenara aittir.
   Koşularda `kenar` reddi 0–1 kare.
3. **Zemin: ev noktasının 0.227 m altı.** x500'ün iniş ayaklarının altı modelden okundu (`base_link_collision_3/4`,
   z −0.2195 m, 0.015 m kalınlık). EKF'nin konumu `base_link`'tir (IMU ve GPS orada). Gerçek araçta ölçülür.
4. **`alt` = zeminin AMSL'si** (köken − zemin D), spec'teki "ev noktasının AMSL'si"nden 0.227 m aşağıda: kişinin
   ayakları oradadır. `FLW_TGT_ALT_M 0` iken kontrolü etkilemez.
5. **PX4'ün kendi izdüşümü** (lib/geo `MapProjection`, 6371 km küre): PX4'ün hedef kestiricisi enlem/boylamı aynı
   izdüşüm ve aynı EKF kökeniyle NED'e geri çevirir; böylece gidiş-dönüşe yalnız mesajın 1e-7° tamsayıları eklenir.
   WGS84 kullanılsaydı 30 m'de doğu yönünde ≈ 9 cm'lik bir ölçek farkı eklenirdi (küre ile elipsoidin bu enlemdeki
   yarıçap farkı %0.3).
6. **Gerçek konum için Gazebo'nun dönüşümü** (değerlendirme ve hakem kaynağı): dünyanın `spherical_coordinates`'ı,
   WGS84, ENU. gz-math'in `LOCAL` çerçevesi x/y'yi ters çevirir (sınandı: +10 m doğu batıya düşüyordu); doğrusu
   `LOCAL2`'dir. Kodda kendi ECEF dönüşümümüz var (yeni paket yok); test, gz-math 7.7.0'ın `LOCAL2` değerlerini
   1e-12° ile tutturur. Koşuda EKF'nin yatay konumu bu dönüşümle Gazebo'nun gerçek konumundan ort. 0.17–0.25 m farklı
   çıktı; çerçeveler tutarlı.
7. **EKF kökeni istenir.** PX4 `GPS_GLOBAL_ORIGIN`'i yalnız köken kurulunca/değişince ya da istenince gönderir
   (`streams/GPS_GLOBAL_ORIGIN.hpp`, `_force_next_send`). Bağlantımız kökenden sonra kurulursa mesaj hiç gelmez: ilk
   D gösterim koşusunda böyle oldu (bütün kareler `referans_yok`, hiç `FOLLOW_TARGET` gitmedi; A, B, E, D2'de köken
   bağlantıdan sonra kurulduğu için gelmişti, yani bir yarıştı). Artık bağlantı kurulunca ve kalkıştan sonra
   `MAV_CMD_REQUEST_MESSAGE` ile istenir (`Vehicle.wait_references`: köken ve ev noktası gelene kadar saniyede bir,
   en çok 10 s; gelmezse olay yazılır). Pi'nin kodu da bunu yapmalı.
8. **Poz geçmişi `message_hooks` ile.** Ana iş parçacığının `recv_match` döngüleri okumaya devam eder, her ayrıştırılan
   mesaj kancadan geçer; ikinci bir okuyucu yok, kanca hiç istisna fırlatmaz. Akış hızları PX4'ün onboard bağlantı
   hızlarına çekildi (`ATTITUDE_QUATERNION` 50 Hz, `LOCAL_POSITION_NED` 30 Hz; önceden 10 Hz'e kısılıyordu): Pi'nin
   TELEM2'de onboard modunda alacağı budur (bant genişliği m04'te ölçülmeli). Ölçülen: kareden sonraki ilk örnek ort.
   16 ms, en çok 36 ms sonra geldi; `poz_yok` hiç olmadı.
9. **"En çok 10 Hz" = kare zamanları en az 96 ms arayla.** 30 Hz kameranın kareleri 32, 32, 32, 36 ms arayla gelir;
   üçüncü kare 96 ya da 100 ms sonradır. 100 ms'lik bir sınır her dördüncü kareyi (7.6 Hz) verirdi. PX4 zaten en sık
   500 ms'de bir kaynaştırır. Ölçülen: hakem kaynağında 9.7, model kaynağında 5.1 mesaj/sim-s (işlenen kare ≈ 12.7/s,
   bunların bir kısmı konumsuz).
10. **`FOLLOW_TARGET` karenin `TEZ_LOS`'unun arkasından aynı gecikme hattından** gider (12. grupta eklenecek yapay
   gecikme ikisine birden uygulanır; gerçekte de ikisi aynı seri hattan gider). İki akış `px4_baglanti.FrameStream`'in
   aynı kurallarını kullanır.
11. **`FLW_TGT_HT` kuralı:** senaryo ya da `--param` vermezse `drone.yukseklik_m`, kaynak
    `drone.yukseklik_m (follow_me)` ile senaryo katmanının başına eklenir (dosyaların 8 m'sinden sonra). Kamera raporuna
    göre yükseklik ile mesafe birlikte değişmelidir; 10 m'lik `kalabalik_park`'ta `FLW_TGT_HT` 10 oldu.
12. **Hakem kaynağı (mükemmel algılayıcı):** `FOLLOW_TARGET` hedefin gerçek konumu (kişinin üzerinde kusursuz bir GPS
    gibi), yalnız hakemin `gorunur` dediği karelerde; konumun hatası tanım gereği 0, gönderildiği andaki gerçek konuma
    göre ort. 0.07 m (hedef bu arada yürüdü).
13. **PX4 kaydedicisi yeniden başlatılır** (`follow_me`'de, kayıt penceresinden önce, ilk üç `FOLLOW_TARGET`'tan
    sonra): aşağıda "Karşılaşılan sorunlar". Uçuşa etkisi yok; ULog iki dosya olur.
14. **Değerlendirme ayrıştırması:** her konum için dronun gerçek pozu ve Gazebo'nun montajıyla da aynı ışın
    kesiştirilir (`konum_hatasi_gercek_pozla_*`). Fark EKF'den gelir (duruş, yaw, konum, zaman). B'de kutunun payı
    0.26 m, EKF pozuyla 0.48 m: farkın çoğu EKF yaw kaymasıdır (49–54 s'de +6.2° → 1.3 m).

## PX4 v1.17.0 Follow Target'ın davranışı (kaynaktan okundu, koşularda görüldü)

- **Alım:** `mavlink_receiver` yalnız `lat, lon, alt, vel`'i alır; `est_capabilities`, `timestamp` ve diğerleri
  kullanılmaz. `follow_target.timestamp` mesajın varış anıdır.
- **Kestirici** (`TargetEstimator`, alfa-beta-gama, `FLW_TGT_RS` 0.1): konumu en sık 500 ms'de bir kaynaştırır; hız
  NaN olduğu için hızı ardışık konumlardan çıkarır. Bu yüzden konumdaki bir sıçrama doğrudan hıza dönüşür: tek bir
  yanlış kişiye ait konum (7–11 m sıçrama) 6–10 m/s'lik hız verdi.
- **Mesaj kesilince:** kestirici son hızla **3 s öngörmeye devam eder**, sonra `stale` olur, hız/ivme sıfırlanır, son
  konum tutulur. `valid` kaldığı için görev o noktanın `FLW_TGT_DST` gerisinde havada bekler; mod değişmez, hedef kaybı
  için failsafe yoktur. Görevdeki 1.5 s'lik zaman aşımı kestiricinin kendi yayınına aittir (spec "Varsayımlar" 3
  düzeltildi).
- **Moda girince:** yörünge açısı 0'dan (hedefin kuzeyi) başlar, hedefin rotası + `FLW_TGT_FA` (180°) yönüne döner
  (açısal ivme/hız sınırlı); rota yalnız kestirilen hız ≥ 1 m/s iken güncellenir. Kişi dururken konum titreşimi (±0.5–1 m)
  kestiricide ≈ 1 m/s'lik hızlar üretip rotayı oynatıyor; dron duran kişinin etrafında dolanıyor (E'de 28–46 s, A ve
  B'de 26–60 s arasında görüldü). Yaw hep hedefe bakar, kamera dronla döner.
- **Kayıt:** `follow_target` (500 ms), `follow_target_estimator` (200 ms), `follow_target_status` (400 ms) isteğe
  bağlı konulardır; aşağıya bakın.

## Test sonuçları

| Kontrol | Sonuç |
|---|---|
| `$P -m pytest tez/sim/testler/test_konumlama.py tez/sim/testler/test_mesajlar.py -q` | **21 geçti** |
| `$P -m pytest tez/sim/testler -q` | **184 geçti** (önceki 163 + 21), 1 uyarı (önceden de vardı, protobuf) |
| Aynı testler `torch`/`ultralytics` olmadan | testler bu paketleri içe aktarmaz (5. gruptaki düzen değişmedi) |
| `ruff format` + `ruff check` (`tez/sim/ruff.toml`, ruff 0.16.9) | temiz |
| `tez/pin/verify_pin.sh --worktree` | **KILIT SAGLAM (v1.17.0)** |
| `senaryo.py --senaryo takip_yuruyen --ekransiz --los hakem` (A) | **GEÇTİ**, sayılar aşağıda |
| `senaryo.py --senaryo takip_yuruyen --ekransiz` (B, model v0.2, CPU; son kodla B2 ve B3) | **GEÇTİ** (üçü de; eşik yok), sayılar aşağıda |
| Kayıt boyunca mod | A, B, B2, B3, D, D2: `vehicle_status.nav_state` 19 (Follow Target) kalkıştan ≈ 25 s sonra → 90.7–91.0 s, sonra Land (18); "senaryo modundan çıktı" olayı hiçbirinde yok |
| ULog'da `follow_target` | A 58, B 57, B2 33, B3 53 kayıt (pencerede, kaydedici 500 ms'de bir yazar); `follow_target_estimator` ve `follow_target_status` da var |
| pyulog satırı (tasks.md 5.7) | `debug_vect` pencerede: A 890 = gönderilen 890; B 373 = 373; B2 346 / 347; B3 352 = 352 |
| Ek: `kalabalik_park --takip follow_me --param FLW_TGT_DST=10` (E, kayıp davranışı) | **GEÇTİ** (eşik yok); dron hedeften uzaklaştı, aşağıda |

Her koşudan önce `pgrep -x px4` / `pgrep -f "^gz sim"` boştu; sonra da açık PX4, Gazebo ya da model süreci kalmadı.

## Sayılar (`takip_yuruyen`, kayıt penceresi 60–89.9 s)

A ve B köken düzeltmesinden (karar 7) önceki kodla, B2 ve B3 son kodla koşuldu; dördünde de köken geldi, yani sayılar
karşılaştırılabilir. Model kaynağı aynı senaryoda koşudan koşuya belirgin değişiyor (aşağıda neden).

| | A: `--los hakem` | B: model | B2: model (son kod) | B3: model (son kod) |
|---|---|---|---|---|
| Sonuç | sonuna kadar izledi | izledi | **75–78 s'de kaybetti** | izledi |
| Dron–hedef yatay mesafe ort. / en az / en çok [m] | 7.59 / 2.94 / 9.31 | 7.38 / **0.76** / 10.11 | 11.06 / 1.42 / 19.41 | 7.54 / 2.71 / 10.32 |
| \|mesafe − 8 m\| ort. [m] | 0.89 | 1.25 | 4.05 | 1.24 |
| Dron yüksekliği ort. [m] (`FLW_TGT_HT` 8) | 7.97 | 8.03 | 8.05 | 8.02 |
| Hedef kadrajda / görünür / en uzun kayıp | %93 / %96 / 1.3 s | %86 / %89 / 1.8 s | %42 / %47 / 9.0 s | %82 / %89 / 1.4 s |
| Gönderilen `FOLLOW_TARGET` (hız); konumsuz işlenmiş kare | 285 (9.7/s); 0 | 150 (5.1/s); 130 | 71 (2.4/s); 243 | 133 (4.5/s); 146 |
| `FOLLOW_TARGET` uçtan uca ort. / p95 [ms] | 68 / 114 | 137 / 181 | 136 / 176 | 140 / 178 |
| Gönderilen konumun hatası ort. / p50 / p95 / en çok [m] | 0 (gönderimde 0.07) | **0.49** / 0.47 / 0.92 / 1.59 | 0.66 / 0.65 / 1.54 / 1.58 | 1.12 / 1.03 / 2.25 / 2.38 |
| Kutunun konum hatası (hedefken) EKF pozuyla / gerçek pozla, ort. [m] | 0.25 / 0.21 | 0.48 / 0.26 | 0.47 / 0.27 | 1.13 / **0.25** |
| EKF yaw − gerçek yaw ort. / en çok \|·\| | +0.14° / 3.2° | −2.35° / 3.8° | +2.45° / 5.1° | **+8.51° / 15.9°** |
| EKF yatay konum − gerçek ort. [m] | 0.17 | 0.25 | 0.29 | 0.20 |
| PX4'ün hedef kestirimi − gerçek ort. / p95 / en çok [m] | 0.25 / 0.77 / 1.56 | 0.66 / 1.58 / 3.63 | 7.64 / 20.4 / 20.4 | 1.26 / 2.43 / 3.13 |
| PX4 kestiriminin bayat süresi (pencerede) | 0 s | 0 s | 8.6 s | 0.2 s |
| ULog'da `follow_target` (pencerede, 500 ms'de bir) | 58 | 57 | 33 | 53 |
| `TEZ_LOS` gönderilen = ULog | 890 = 890 | 373 = 373 | 347 / 346 | 352 = 352 |
| Görünürken kutusuz işlenmiş kare | %34 | %26 | %28 | %29 |
| Kilit kaybı / yeniden kilit (pencerede) | 3 / 3 | 3 / 3 | 4 / 3 | 6 / 6 |
| En büyük eğim (ULog) | 42° | 32° | 37° | 43° |
| RTF | 0.89 | 0.93 | 0.94 | 0.91 |
| Mod (`vehicle_status.nav_state`) | 19 (Follow Target) 28.6 → 90.8 s | 26.7 → 90.8 s | 25.8 → 90.8 s | 24.5 → 90.7 s |

Gösterim koşuları (kayıtçıların yüküyle, ölçüm değil): D (model + dış kamera, RTF 0.74) sonuna kadar izledi, mesafe ort.
8.59 m (5.96–12.85), gönderilen konumun hatası ort. 0.50 m, EKF yaw +3.2°; D2 (hakem, RTF 0.85) ort. 7.59 m (3.20–9.36).

**Konum hatasının parçaları:** dronun gerçek pozuyla kutunun kendi payı dört koşuda da **0.21–0.27 m** (ayağın ≈ 25 cm
önü, kutu kenarlarının oynaması). Üstüne EKF eklenir; en büyük parça EKF yaw kaymasıdır ve koşudan koşuya
−2.4°…+8.5° (B3'te anlık 15.9°) değişti: 11 m menzilde 1° ≈ 0.19 m. B3'ün 1.13 m'lik hatasının ≈ 0.9 m'si yaw'dandır.
Gönderim anına kadar hedefin yürüdüğü yol (1.4 m/s × 0.14 s ≈ 0.2 m) yöne göre eklenir ya da çıkar. PX4'ün kestirimi
bunun üstüne 500 ms'lik kaynaştırmayı ve kayıpta öngörüyü ekler.

**Neden koşudan koşuya farklı?** Hedef 60 s'ye kadar duruyor. Konumdaki ±0.5–1 m titreşim PX4'ün kestiricisinde
≈ 1 m/s'lik sahte hızlar üretiyor ve hedefin "rotası" bunlarla oynuyor; yörünge açısı da kuzeyden başlayıp bu rotaya
göre döndüğü için hedef yürümeye başladığında dronun nerede olduğu rastlantısal: B'de hedefin batısında (arkasında), B2'de
kuzeydoğusundaydı. B2'de hedef doğuya yürüyünce dron 135° dolanmak zorunda kaldı; eğim ±20–25°'ye çıktı ve kişi 45°
kameranın ±20° dikey görüşünden defalarca çıktı (65, 71, 74 s). Kişi köşede koşmaya başlayınca (≈ 75 s) kilit düştü,
PX4 kuzeye 3 m/s ile öngördü, kestirim bayatladı ve dron 14–19 m uzakta bekledi. Bu, kamera raporundaki "kişi birden
koşunca görüntünün üstünden çıkar" gözleminin model ve stok Follow Me ile tekrarıdır.

## Hedef kaybolunca dron ne yapıyor? (gözlendi)

- **Kısa kayıp (< 3 s), B, 77–79 s:** hedef kuzeye koşudan batıya dönüp yürürken model kişiyi ≈ 2 s göremedi. PX4
  kişinin hâlâ kuzeye koştuğunu varsayıp öngördü (kestirim hatası 3.6 m'ye çıktı); dron öngörülen noktanın gerisine
  giderken gerçek kişinin üstünden geçti: yatay mesafe **0.76 m** (8 m yükseklikte, kişinin ≈ 6 m üstünde). Hakem
  kaynağında aynı yerde en az 2.94 m. Gerçekte de stok Follow Me'nin, görüntüye dayalı bir hedefle yaşayacağı durum.
- **Uzun kayıp, E (`kalabalik_park`, 10 m / 10 m, model):** hedef 60 s'ye kadar (7, −1)'de duruyor. 44.2 s'de seçim tek
  bir karede yandaki sarılı kişiye (9, 6), 48.2 s'de patikadaki kişiye (−2, −7) atladı (199 konumun 2'si). İkisi de
  `FOLLOW_TARGET` olarak gitti; PX4'ün kestiricisi bunları 6–10 m/s'lik hızlara çevirip 3 s öngördü, dron hedeften
  uzaklaştı, kişi kadrajdan çıktı, kilit düştü ve geri gelmedi (hakem yeniden kilit için hedefin kadrajda görünmesini
  bekler). 51 s'den sonra kestirim bayat: dron, hayalet noktanın 10 m gerisinde, hedeften ≈ 35 m uzakta havada bekledi;
  mod "Follow Target"te kaldı, PX4 hiçbir uyarı vermedi. Gerçekte operatörün müdahalesi gerekirdi.
- Sonuç: kayıp anında güvenli davranış (m01 başarı ölçütleri, m11 geçersiz veri yönetimi, m15 modu) için iki somut
  ihtiyaç ölçüldü: yere izdüşürülmüş konumda sıçrama süzgeci (insan en çok 6 m/s) ve kayıpta öngörünün sınırlanması.
  m06'nın geçici seçimi bunu yapmaz (spec: asıl çözüm m11).

## Görseller (repo dışı)

`~/Desktop/Follow/3_m06_Simulasyon/Deneme/`:

| Dosya | Ne |
|---|---|
| `gorev6_model_yavas_x3.mp4` | **Ana video** (3 dk 16 s, 10 kare/s = 3 kat yavaş; gösterim koşusu D, model v0.2). Solda dronun kamerası: mavi kutu ve mavi halka = hakemin gerçek hedefi ve gerçek ayak noktası; kırmızı = PX4'ün o anda elindeki son model sonucu (kalın = seçilen kutu, kırmızı × = kutunun alt ortası, yani yere izdüşürülen nokta); sol üstte PX4 modu (ULog'dan), "HEDEF YOK", kilit olayları. Sağda kuşbakışı harita (kuzey yukarı, 5 m ölçek): turuncu = dronun gerçek izi ve burnu, mavi = hedefin gerçek izi ve 8 m halkası, açık kırmızı noktalar = kutulardan hesaplanan bütün konumlar, kırmızı × = PX4'e giden son 3 s'lik FOLLOW_TARGET'lar, mor kare = PX4'ün kendi hedef kestirimi ("bayat" yazısı 3 s mesaj gelmeyince), gri çokgen = kameranın yerde gördüğü alan. Altta: yatay mesafe ve yükseklik, o karenin konum hatası, gönderilen FOLLOW_TARGET sayısı ve son 1 s'deki hızı, son gönderilenin gecikmesi ve hatası, PX4 kestiriminin hatası; sağ altta son 20 s'nin mesafe (beyaz) ve konum hatası (kırmızı) eğrisi |
| `gorev6_model_gercek_hiz.mp4` | Aynısı gerçek hızda (65 s, 30 kare/s) |
| `gorev6_model_dis_kamera_gercek_hiz.mp4` | **Dış (takip) kamerası** (73 s, 15 kare/s): aynı koşuda dronun 10 m arkasından ve 3 m üstünden bakan bir kamera (scratchpad'de dünyaya eklenen statik bir kamera, her adımda `set_pose` ile dronun arkasına taşındı). Dron üstte küçük, yürüyen kişi aşağıda; dronun kişiyi nasıl izlediği, durunca etrafında nasıl dolandığı görülür |
| `gorev6_hakem_yavas_x3.mp4`, `gorev6_hakem_gercek_hiz.mp4` | Karşılaştırma: aynı senaryo "mükemmel algılayıcı" (`--los hakem`, gösterim koşusu D2) ile. Bu koşu köken düzeltmesinden önceydi: model kutularının konumu `referans_yok` (soldaki konum hatası "–"); hakemin FOLLOW_TARGET'ı etkilenmedi |
| `gorev6_model_ilk_follow_target_t25.58.jpg`, `..._yurume_basliyor_t62.01.jpg`, `..._en_yakin_6.0m_t86.23.jpg`, `..._en_buyuk_konum_hatasi_0.97m_t72.93.jpg`, `..._kilit_kaybi_t74.94.jpg`, `..._son_t89.76.jpg` | D'den anlar: ilk FOLLOW_TARGET; yürüyüşün başı; en yakın geçiş; en büyük konum hatası; kilit kaybı (kişi kadrajda yok, PX4 kestirimi 3 m geride) |
| `gorev6_hakem_*.jpg` | D2'den aynı anlar |
| `gorev6_B_model_mesafe_ve_konum_hatasi.png` | Ölçüm koşusu B: üstte dron–hedef yatay mesafe (gri: hedef kadraj dışında; 78.8 s'deki 0.76 m'lik düşüş), ortada konum hataları (model kutusu, giden FOLLOW_TARGET, PX4'ün kestirimi), altta kilit durumu, FOLLOW_TARGET'lar ve PX4'ün "bayat" anları |
| `gorev6_B2_model_son_mesafe_ve_konum_hatasi.png`, `gorev6_B2_kayip_haritasi.png` | Ölçüm koşusu B2: kişi köşede koşarken kayıp; haritada PX4'ün kestirimi kuzeye kaçıp bayatlıyor, dron 14–19 m uzakta kalıyor |
| `gorev6_B3_model_son_mesafe_ve_konum_hatasi.png` | Ölçüm koşusu B3: izledi; konum hatası EKF yaw kaymasıyla (+8.5°) daha büyük |
| `gorev6_E_kayip_haritasi.png` | `kalabalik_park` (E): iki yanlış kişi konumu (büyük ×), PX4 kestiriminin güneybatıya kaçışı, dronun 35 m uzakta asılı kalması |
| `gorev6_model_mesafe_ve_konum_hatasi.png`, `gorev6_hakem_mesafe_ve_konum_hatasi.png` | D ve D2'nin aynı grafiği |

Videolar ve fotoğraflar ölçüm koşularından değil, iki gösterim koşusundan (D, D2) gelir: koşunun yanında çalışan bir
kayıtçı (scratchpad, repoya girmedi) 24–96 s arasındaki her kamera karesini 1280×720 JPEG yazdı; D'de ayrıca dış kamera
vardı (RTF 0.74). Kayıp anı (B2, E) video olarak kaydedilmedi, haritalarda görülür. MP4: ffmpeg 6.1.1 (sistem),
`libx264`, `yuv420p`, `+faststart`, 2000×930 (ffmpeg'in sürüm sabitlemesi 8. grubun işi; repo kodu kullanmıyor).

## Karşılaşılan sorunlar

- **`follow_target` ULog'da yoktu (ilk A koşusu):** PX4 v1.17.0'ın kaydedicisi isteğe bağlı konulara yalnız kendisi
  başlarken varlarsa abone olur (`LoggedTopics::add_topic` → `orb_exists`); `follow_target*` konuları ilk
  `FOLLOW_TARGET` ve Follow Target moduyla doğar. Gerçek araçta da aynıdır. Seçenekler: (a) SD karttaki / rootfs'teki
  `etc/logging/logger_topics.txt` (dosya varsa **profili tümüyle değiştirir**, bütün listeyi elle tutmak gerekir),
  (b) kaydediciyi konular doğduktan sonra yeniden başlatmak. Simde (b) seçildi: uçuşa etkisi yok, profil aynı kalır;
  ULog `ucus_once.ulg` + `ucus.ulg` olur. Gerçek araç için karar açık.
- **Model, görünen kişiyi sık kaçırıyor:** kayıt penceresinde hedef açıkça görünürken (≈ 8500 px) işlenen karelerin
  A'da %34'ünde (118 / 345), B'de %26'sında (90 / 341), B2'de %28'inde, B3'te %29'unda hiç kutu yok; kapı sorunu değil (ilk A denemesinde kaçırılan
  237 karenin hepsinde kutu sayısı 0'dı). 8 m / 45°'den kişi 640 girişte ≈ 54 px; v0.2 bu açıyla eğitilmemiş olabilir (m08,
  Ortatepe'ye soru listesinde).
- **Kendi betiklerimin hataları (repo kodu değil):** gösterim sarmalayıcısında `if __name__ == "__main__"` yoktu;
  model süreci "spawn" ile açılırken dosyayı yeniden içe aktarıp çıktı (D'nin ilk denemesi 2 s'de, sim açılmadan
  durdu). Ardından betik, kare bekleyen iki kayıtçımı bekledi; onları durdurdum (ikisi de benim süreçlerimdi).
- **EKF kökeni gelmedi (D'nin ikinci denemesi):** karar 7. Düzeltmeden sonra B, son kodla yinelendi (B2).
- Çalışma arada kullanım sınırı yüzünden kesildi; A ve B koşuları o sırada tamamlanmıştı (klasörler ve günlükler
  kontrol edildi), yeniden koşmaya gerek olmadı.

## Kalan sim-gerçek farkları

- **Zaman eşlemesi:** simde kare zamanı doğrudan PX4 zamanıdır (gz_bridge PX4 saatini her adımda Gazebo'ya eşler).
  Pi'de kamera saati ile PX4 saati TIMESYNC ile eşlenmeli (m04); 10 ms'lik bir hata 60°/s dönüşte 0.6°, 11 m'de 0.12 m.
- **Düz zemin:** `duz_alan` ve `cayir` düzdür; kampüsteki çim %3–7 eğimli (kamera raporu: 1 m yükseklik farkı 45°'de
  ≈ 1 m konum hatası). Zemin yüksekliği ev noktasından alınır.
- **GPS:** simde gürültüsüz (navsat sensöründe gürültü yok); EKF'nin yatay konumu yine 0.17–0.25 m kayık. Gerçek M8N
  metre düzeyinde gürültülüdür ve hedefin konumu ile dronun konumu aynı EKF'den geldiği için çoğu birbirini götürür,
  ama yükseklik hatası (`EKF2_HGT_REF 1`, GPS) doğrudan konuma geçer.
- **EKF yaw:** koşudan koşuya −2.4°…+8.5° ortalama, anlık 15.9°; simdeki manyetik alanın (`<magnetic_field>`)
  konumun WMM değeriyle uyuşmamasından (spec "Varsayımlar" 6). Konum hatasının en büyük parçası budur. Gerçekte
  kalibrasyona ve motor girişimine bağlıdır; simdeki değer gerçeği temsil etmez.
- **Montaj ve kamera:** nominal 45° ve nominal ofset kullanılıyor, simde gerçek montaj da nominal (Gazebo'dan okunan
  hata 0.03°); kamera bozulmasız. Gerçekte montaj açısı ölçülmeli (1° = 8 m'de ≈ 0.3 m).
- **Bağlantı:** UDP 127.0.0.1, kayıpsız. Gerçekte TELEM2 seri hattında `ATTITUDE_QUATERNION` 50 Hz +
  `LOCAL_POSITION_NED` 30 Hz + `FOLLOW_TARGET` 10 Hz + `TEZ_LOS` 30 Hz'in sığıp sığmadığı ölçülmeli (m04).
- **Operatör:** ilk kilit ve yeniden kilit hakemden, tepki süresi 0 (12. grupta ayarlanabilir olacak). Gerçekte
  operatör QGC'de tıklar; E'deki gibi hedef kadrajdan çıkınca operatör de bir şey yapamaz, dronu elle geri getirir.
- **Model:** laptop CPU'sunda v0.2; Hailo'daki davranış başka (m08). RTF 0.89–0.93.
- **Kaydedici:** simde `follow_me`'de yeniden başlatılıyor; gerçek araçta bu konular kayda girmez (karar açık).

## Açık kararlar ve bekleyenler

- **Gerçek araçta `follow_target*` konularının kaydı (Hüseyin / Kurt, m17/m22/m25):** SD karta tam bir
  `logger_topics.txt` mı, uçuşta kaydediciyi yeniden başlatmak mı, yoksa kaydı olmadan mı uçulacak?
- **Yanlış kişiye atlama ve sıçrama süzgeci (kullanıcı / Ortatepe, m11; Kurt, m15):** m06'nın geçici seçimi tek bir
  yanlış konumu da PX4'e gönderiyor (E). m06'ya geçici bir "yer düzleminde en çok 6 m/s" süzgeci eklensin mi, yoksa
  stok davranış olduğu gibi ölçülüp m11'e mi bırakılsın? (Şimdilik ölçülüyor, eklenmedi.)
- **Güvenlik (m01):** stok Follow Me hedef geri dönerken dronu kişinin 0.76 m yakınına (tepesine) getirdi. Başarı
  ölçütlerinde "en az yatay mesafe" için bir eşik gerekebilir.
- **Simdeki manyetik alan (kullanıcı / Hüseyin):** EKF yaw kayması koşudan koşuya −2.4°…+8.5° ve konum hatasının
  çoğunu oluşturuyor (B3: 1.13 m'nin ≈ 0.9 m'si). Dünyaların `<magnetic_field>`'ını konumun WMM değerine eşitlemek bu
  sim yapıntısını kaldırırdı; bütün koşuları ve F0/F1'i etkilediği için ayrı bir karar (şimdilik ölçülüp raporlanıyor).
- **Koşu sayısı:** model kaynağı koşudan koşuya çok değişiyor (3 ölçüm koşusundan 1'inde kayıp). Tek koşuyla sonuç
  söylenemez; 7. ve 9. grupta en az 3–5 koşu ve dağılım raporlanmalı (kabul koşulları buna göre yazılabilir).
- 5. gruptan süren `imgsz` kararı (m08) ve modelin bu açıdaki kaçırma oranı (%26–34).

## Sonraki gruplar için notlar

- **7. grup:** `takip.Tracker._position_metrics` ve `_follow_metrics` (`geolocation_hatasi_*`, `konum_hatasi_*`,
  `konum_hatasi_gercek_pozla_*`, `ekf_*`, `follow_target_*`) ile `senaryo.tracking_results`'taki
  `yatay_mesafe_hatasi_ort_m` `olcum.py`'ye taşınır; `rapor.ulog_follow_target` hazır. `mod_korunma_orani` için
  `ucus_once.ulg` + `ucus.ulg` birlikte okunmalı (mod 28 s'de, kaydedici ≈ 27–29 s'de yeniden başlıyor).
- **8. grup:** sağ panel için `algilama.csv`'de `konum_x/y`, `follow_target.csv`'de giden noktalar (`x y`), ULog'da PX4'ün
  kestirimi (`follow_target_estimator.lat_est/lon_est`) hazır. Bu gruptaki gösterim betiğinin düzeni aşağıda.
- **10. grup:** harici bir mod `FOLLOW_TARGET` isterse aynı akış kullanılabilir (spec "Varsayımlar" 8).
- **12. grup:** gecikme hattı `FOLLOW_TARGET`'ı da taşıyor; yeni alt madde 12.4 (yeniden kilit bekleme süresi).

---

## Kendin dene

Bu bölümdeki her şey bilgisayarında hazır: paketler kurulu, model dosyası yerinde, PX4 derli.

**Başlamadan:** Terminal açmak için **Ctrl+Alt+T**'ye bas. Aşağıdaki gri kutulardaki komutları kopyala, terminale
**Ctrl+Shift+V** ile yapıştır (terminalde Ctrl+V çalışmaz) ve **Enter**'a bas. Bir komutu yarıda kesmek için
**Ctrl+C**.

### 1. Hazırlık (her yeni terminalde bir kez)

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot
P=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python
```

Bir şey yazmaz; bu normal.

### 2. Hazır videoları izle

Önce dışarıdan bak (dron yürüyen kişiyi 8 m geriden, 8 m yüksekten izliyor):

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev6_model_dis_kamera_gercek_hiz.mp4
```

Sonra ana video (3 kat yavaş):

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev6_model_yavas_x3.mp4
```

- **Sol:** dronun kamerası. Mavi kutu = kişinin gerçek yeri (hakem). Kırmızı kalın kutu = modelin bulduğu ve takip için
  seçilen kutu; kırmızı **×** onun alt ortası: program bu noktayı (ayak) yere izdüşürüp kişinin konumunu buluyor. Mavi
  halka gerçek ayak noktası; × ile ne kadar yakınsa konum o kadar doğru. Kırmızı kutu kişinin biraz gerisinde kalıyorsa
  sebebi ≈ 0.14 s'lik gecikmedir.
- **Sağ (kuşbakışı):** turuncu çizgi dronun gittiği yol, mavi çizgi kişinin yolu, kesikli mavi halka kişinin etrafındaki
  8 m. Kırmızı **×**'ler PX4'e giden `FOLLOW_TARGET` konumları, **mor kare** PX4'ün "kişi burada" dediği yer. Dron, mor
  karenin 8 m gerisinde durmaya çalışır.
- **Alt:** yatay mesafe (ayar 8 m), yükseklik, o karenin konum hatası (metre), kaç `FOLLOW_TARGET` gittiği ve hızı.

Videoda şunlara bak: ~25 s'de ilk `FOLLOW_TARGET` (yeşil şerit) ve dronun hedefin etrafında dönmeye başlaması (kişi
dururken PX4 onun hangi yöne baktığını bilmiyor); 60 s'de kişi doğuya yürüyor, dron arkasına geçiyor; ~75 s'de kişi
kuzeye koşarken kadrajdan çıkıyor, "KİLİT KAYBI" ve "HEDEF YOK", mor kare kişinin önüne kaçıyor; kişi tekrar görününce
yeniden kilit.

VLC kısayolları: **Boşluk** duraklat/sürdür, **E** bir kare ileri, **Shift+→ / Shift+←** 3 s ileri/geri,
**]** / **[** hızlandır/yavaşlat, **F** tam ekran. Gerçek hız için dosya adını `gorev6_model_gercek_hiz.mp4` yap;
"mükemmel algılayıcı" ile karşılaştırma için `gorev6_hakem_yavas_x3.mp4`.

### 3. Fotoğraflar ve grafikler

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev6_B_model_mesafe_ve_konum_hatasi.png
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev6_B2_kayip_haritasi.png
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev6_E_kayip_haritasi.png
```

- Birinci grafik: üstte dron–hedef mesafesi (8 m civarı; 78.8 s'de 0.76 m'ye düşüş: kişi köşede dönerken model onu ≈ 2 s
  göremedi, PX4 kişinin hâlâ kuzeye koştuğunu varsaydı ve dron kişinin tepesinden geçti). Ortada konum hataları.
- İkinci: aynı senaryonun başka bir koşusu (B2); bu kez kişi koşarken kayboldu, dron uzakta kaldı.
- Üçüncü: kalabalık parkta seçim iki kez başka kişiye atladı (büyük ×), PX4 bunu hıza çevirdi, dron 35 m uzaklaştı ve
  orada asılı kaldı. Gerçek uçuşta operatörün dronu elle geri alması gerekirdi.

### 4. Kendin koştur (pencere yok, ~2 dakika)

Önce açık bir sim olmadığından emin ol (iki satır da bir şey yazmamalı):

```bash
pgrep -x px4
pgrep -f "^gz sim"
```

Model kutusuyla Follow Me:

```bash
$P tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz
```

Sonda şuna benzer satırlar görürsün (sayılar her koşuda biraz farklıdır, bazen dron kişiyi kaybeder):

```text
[05:55:31] FOLLOW_TARGET (model): kayıt penceresinde 133 gönderildi (4.5 mesaj/sim-s), konumsuz kare 146; gönderilen konumun hatası ort. 1.12 m ...
[05:55:31] PX4: ULog'da 53 follow_target (kaydedici 500 ms'de bir); hedef kestirimi gerçek konumdan ort. 1.26 m ...
[05:55:31] Follow Me: dron-hedef yatay mesafe ort. 7.54 m (en az 2.71, en çok 10.32; FLW_TGT_DST 8); ...
[05:55:31] Konum (model kutusu, düz zemin): ... kutu hedefken hata ort. 1.13 m ..., gerçek pozla 0.25 m; EKF yaw hatası ort. +8.51° ...
[05:55:32] SONUÇ: GEÇTİ
```

"Mükemmel algılayıcı" ile (kişinin gerçek konumu gider; karşılaştırma için):

```bash
$P tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz --los hakem
```

Hedef kaybı denemesi (kalabalık park, 10 m yükseklik / 10 m mesafe):

```bash
$P tez/sim/araclar/senaryo.py --senaryo kalabalik_park --ekransiz --takip follow_me --param FLW_TGT_DST=10
```

### 5. Gazebo penceresinde izle (isteğe bağlı)

Ekran kartını seçmek için önce (AMD hibrit GPU):

```bash
export DRI_PRIME=1
$P tez/sim/araclar/senaryo.py --senaryo takip_yuruyen
```

Gazebo penceresi açılır. Sol taraftaki varlık listesinde (Entity Tree) `x500_tez_0`'a sağ tıklayıp **Follow**'u seçersen
kamera dronu izler; fare tekerleğiyle yakınlaş. Kişi 60. saniyede yürümeye başlar. Pencere kapanınca rapor yazılır.

### 6. Çıktıları aç

```bash
K=$(ls -dt tez/sim/sonuclar/*_takip_yuruyen | head -1); echo $K
firefox "$K/rapor.html"                         # "Ölçümler"de FOLLOW_TARGET, konum hatası, PX4 kestirimi satırları
column -s, -t "$K/follow_target.csv" | less -S  # her FOLLOW_TARGET: lat lon, gerçek yer, hata_m, sonuc; q ile çık
```

`algilama.csv`'de yeni sütunlar: `konum` (`hesaplandi`, `kutu_yok`, `kenar`, `poz_yok`, `referans_yok`,
`ufka_yakin`), `ayak_u/v` (kutunun alt ortası), `ekf_yaw_deg` (o anki EKF yönü), `konum_x/y` (bulunan yer, dünyada),
`gercek_x/y`, `konum_hatasi_m`, `ft_sonuc` (`gonderildi`, `hiz_siniri`, `konum_yok`).

PX4'ün kaydında `follow_target` ve kestirici var mı:

```bash
$P -c "import sys;from pyulog import ULog;u=ULog(sys.argv[1],['follow_target','follow_target_estimator','debug_vect']);print({d.name:len(d.data['timestamp']) for d in u.data_list})" "$K/ucus.ulg"
```

`ucus.ulg` kaydedicinin yeniden başladığı andan (≈ 27 s) inişe kadardır; öncesi `ucus_once.ulg`'dadır.

### 7. Kontroller

```bash
$P -m pytest tez/sim/testler -q
tez/pin/verify_pin.sh --worktree
tez/sim/araclar/f1_kabul.sh
```

Beklenen: `184 passed`; `KILIT SAGLAM (v1.17.0)`; F1 (~4 dakika, modelsiz) sonunda `SONUÇ: GEÇTİ`.

### Bir şey ters giderse

| Mesaj | Ne yapmalı |
|---|---|
| `Zaten çalışan bir PX4 veya Gazebo var` | Açık simi kendi terminalinde Ctrl+C ile kapat ya da bitmesini bekle |
| `FOLLOW_TARGET: kayıt penceresinde hiç gönderilmedi` | `ozet.json` → `follow_target.konum`'a bak: hep `referans_yok` ise EKF kökeni gelmemiştir (olaylarda "EKF kökeni ... alınamadı" yazar), hep `kutu_yok` ise model kişiyi bulamamıştır |
| Dron kişiden uzakta kaldı (`yatay_mesafe` büyük) | Hata değil, ölçülen bir sonuç: PX4 kişiyi kaybetmiş ve son tahminin gerisinde bekliyor; grafiklerde mor çizgiye bak |
| Raporda `RTF ... (< 0.9)` uyarısı | Beklenen (model işlemciyi paylaşıyor); tarayıcı gibi ağır programları kapatmak biraz yardımcı olur |
