# AUTO FOLLOW (M15) sözlüğü: bizim verdiğimiz bütün adlar

> **Sürüm:** 1 (write-spec turu), 2026-11-10 · **Durum:** kod henüz yazılmadı. Adlar **karar**; davranış ve değerler `spec.md`'den alındı. Kod yazıldıkça bu dosya **aynı commit'te** güncellenir ve "koddan doğrulandı" diye işaretlenir.
>
> **Kapsam (Karar C3, 2026-11-10):** Yalnızca log alanları değil, M15'te bizim ad verdiğimiz her şey: mod, modül ve komutları, dosyalar, girdi mesajı, parametreler, log mesajı ve alanları, durumlar, doğrulama sonuçları, script'ler. Kullanıcı: "Bizim yazdığımız, isimlerini verdiğimiz her şeyi detaylı kaydet."

> ⚠️ **AUTO_FOLLOW_TARGET bizimle ilgili değildir.** PX4'ün kendi `AUTO_FOLLOW_TARGET` modu (GPS tabanlı Follow Me, `nav_state` = **19**, `msg/versioned/VehicleStatus.msg:55`; kod `FlightTaskAutoFollowTarget`, parametreler `FLW_TGT_*`) bizim **AUTO FOLLOW** modumuzla **ilgili değildir**. Bizimki dış modlara ayrılmış **23–30** aralığından bir numara alır; hangisi olduğu `auto_follow_status.mode_nav_state` alanında yazar. Bazı log araçları 19'u "Auto Follow" diye gösterebilir. Bizim kodda hiçbir şeye `AutoFollowTarget` / `follow_target` adı verilmez. RC anahtarı (`COM_FLTMODEx`) bizim mod numarasıyla ayarlanır; QGC listesinde "Follow Me" ile "AUTO FOLLOW"u karıştırmayın.

**Nasıl okunur?** Logu (PlotJuggler, Flight Review ya da `tez/analiz/af_log_analiz.py`) açınca bizim alanlar `auto_follow_status.<alan>` diye görünür, ör. `auto_follow_status.state`. Aşağıdaki tablolarda her alanın ne demek olduğu, birimi, frame'i ve hangi durumda ne değer aldığı yazar.

**Frame'ler:** **body FRD** = drone'a bağlı (x ileri, y sağ, z aşağı) · **NED** = dünyaya bağlı (x kuzey, y doğu, z aşağı; orijin kalkış yeri, PX4'ün yerel konumu).

---

## 1. Mod ve modül

| Ad | Ne | Nerede görülür | Not |
|---|---|---|---|
| `AUTO FOLLOW` | Uçuş modunun kayıt adı | QGC mod listesi, RC anahtarı ayarı | Ad **değişmemeli**: PX4 modun yerini adın hash'iyle hatırlar (`COM_MODE${i}_HASH`, `src/modules/commander/module.yaml:5-16`). PX4 modu 23–30 aralığından bir `nav_state`'e atar. |
| `auto_follow` | PX4 modülü ve konsol komutu | `pxh>` (SITL) / NSH (6C) konsolu, `top`, `work_queue status` | Komutlar: `auto_follow start` (başlat ve modu kaydet), `auto_follow stop` (durdur, kaydı sil), `auto_follow status` (durum yazdır). Açılışta `rc.mc_apps` satırıyla kendiliğinden başlar (Karar B2-b; satırın koşulu açık, `spec.md` A13). |
| `CONFIG_MODULES_AUTO_FOLLOW` | Modülü firmware'e katan ayar | `boards/px4/sitl/default.px4board`, `boards/px4/fmu-v6c/default.px4board` | `=y` olunca modül derlenir. |
| `src/modules/auto_follow/` | Modülün klasörü | Repo | İçindeki dosyalar Bölüm 7'de. |

## 2. Girdi mesajı (Pi → Pixhawk)

Pi, MAVLink `DEBUG_FLOAT_ARRAY` mesajını **MAVLink 2** ile gönderir (veri kısmı MAVLink 2'nin ek alanı; MAVLink 1 ile gelirse değerler 0 olur). PX4 bunu uORB `debug_array`'e çevirir. **Varsayım** (ICD yazılınca kesinleşir).

| Ad | Ne | Birim / frame | Not |
|---|---|---|---|
| `AF_LOS` | Mesajın `name` alanı | — | En fazla 9 karakter. Bu adı taşımayan `debug_array` örnekleri yok sayılır (`CHECK_NAME`). |
| `data[0]`, `data[1]`, `data[2]` | Hedef yönü: LOS birim vektörünün x, y, z bileşenleri | body FRD | Uzunluğu 1 olmalı (tolerans `AF_NORM_TOL`). z > 0 = hedef aşağıda. |
| `data[3]` | Yaş: görüntünün çekildiği andan gönderime kadar geçen süre | ms | Pixhawk gerçek yaşı `(şimdi − varış) + data[3]` diye hesaplar. |
| `data[4]` | Sıra numarası | — | Her mesajda artar. Float olarak gelir; 2²⁴'e kadar (30 Hz'de ~155 saat) kesin. |
| `data[5]` | Hedef var (1) / yok (0) | — | 0 bozuk veri sayılmaz; KAYIP_BEKLE'yi hemen başlatır. |

Logda bu ham değerler `auto_follow_status`'un `los_*` alanlarına kopyalanmış olarak görülür (Bölüm 4.2). Ham `debug_array` yalnızca PX4'ün debug log profili açıksa loglanır; gerek yoktur.

## 3. Parametreler (`AF_*`, QGC → Parameters)

Hepsi QGC'den değiştirilir, derleme gerekmez. Açılar QGC'de **derece** girilir, kod içinde radyana çevrilir. Min–max dışındaki değer QGC'de girilemez.

| Ad | Ne işe yarar | Varsayılan | Birim | Min–max | Ne zaman değiştirilir? |
|---|---|---|---|---|---|
| `AF_TRK_ANG` | Takip açısı: hedefe bu aşağı bakış açısıyla bakılacak mesafede durulur. İstenen mesafe = yükseklik farkı / tan(`AF_TRK_ANG`) | 30 | deg | 5–85 | Kamera eğimi (m06) bilinince ona eşitlenir. Büyük açı = daha yakın takip. |
| `AF_K_DIST` | Mesafe kazancı K: 1 m mesafe hatası için kaç m/s hız istenir | 0.5 | 1/s | 0–2 | Mesafe yavaş toplanıyorsa artır, salınım varsa azalt. |
| `AF_K_FF` | Hedef hızı katsayısı c: filtrenin bulduğu hedef hızının ne kadarı hız isteğine eklenir (0 = kapalı) | 0 | — | 0–1.5 | Açık çevrim testlerde **0**. Yürüyen hedefte (kapalı çevrim) geride kalınıyorsa açılır. |
| `AF_VEL_MAX` | En büyük yatay hız isteği | 2 | m/s | 0.1–5 | İlk uçuşlarda düşük tutulur. |
| `AF_ACC_MAX` | Hız isteğinin değişim sınırı (ivme) | 3 | m/s² | 0.5–5 | Sert eğilme görülürse azaltılır. 3 = PX4'ün otomatik modlarındaki değer. |
| `AF_ALPHA` | Alpha-beta filtresinin konum katsayısı: büyük = ölçüme hızlı uyar ama gürültülü | 0.5 | — | 0–1 | SITL'de log analizine göre ayarlanır. |
| `AF_BETA` | Alpha-beta filtresinin hız katsayısı: büyük = hız kestirimi hızlı ama gürültülü | 0.17 | — | 0–1 | `AF_ALPHA` ile birlikte; başlangıç β ≈ α²/(2−α) (Benedict–Bordner). |
| `AF_DATA_TOUT` | Veri zaman aşımı: bu süre geçerli veri gelmezse KAYIP_BEKLE. Yaşı bundan büyük mesaj da atılır | 0.5 | s | 0.1–5 | Pi'nin gönderim hızına göre. |
| `AF_LOST_T` | KAYIP_BEKLE'de bu süre dolarsa Hold istenir | 1.0 | s | 0–30 | İlk uçuşlarda kısa. Güven arttıkça uzatılır (kısa kayıplarda takip kesilmesin). |
| `AF_YAW_MIN_D` | Hedefe yatay mesafe bunun altındaysa burun çevrilmez (son yaw tutulur) | 1 | m | 0–10 | Hedef tam altındayken burun sağa sola savrulmasın diye. |
| `AF_TGT_HGT` | Hedefte bakılan noktanın yerden yüksekliği (insanın gövdesi) | 1.0 | m | 0–2.5 | Model insanın neresini işaretliyorsa ona göre. |
| `AF_GND_OFS` | Hedefin durduğu zeminin kalkış yerine göre yüksekliği | 0 | m | −20–20 | Kalkış yeri ile takip alanı farklı yükseklikteyse. Flash'a sığmazsa çıkarılacak ilk parametre. |
| `AF_NORM_TOL` | LOS uzunluğunun 1'den en fazla ne kadar sapabileceği | 0.1 | — | 0.01–0.5 | — |
| `AF_MIN_DEP` | En küçük aşağı bakış açısı; daha sığ bakışlar atılır (mesafe hatası çok büyür) | 10 | deg | 1–60 | — |
| `AF_MAX_RNG` | En büyük kabul edilen yatay mesafe | 40 | m | 1–200 | — |

## 4. Log mesajı `auto_follow_status`

- **Mesaj dosyası:** `msg/AutoFollowStatus.msg` → uORB topic `auto_follow_status`.
- **Ne zaman yayınlanır:** Modül çalıştığı sürece her çevrimde, **saniyede 50 kez**; mod kapalıyken (PASIF) de. Böylece masa testinde de, modu açmadan önceki anlar da logda görünür.
- **Kaydı:** PX4'ün varsayılan log listesine eklenir (`src/modules/logger/logged_topics.cpp`); her logda her zaman vardır, ayar açmak gerekmez. Log ancak PX4 log alırken tutulur (`SDLOG_MODE`; gerçek kartta varsayılan yalnız arm iken).
- **Geri dönüş:** Hüseyin `msg/` ve `logged_topics.cpp` yollarını onaylamazsa bu mesaj olmaz; aynı değerler `debug_array`'e konur ve logda `data[0]`, `data[1]`… diye görünür. O durumda bu bölüme "`data[i]` ↔ alan" eşleme tablosu eklenir.
- "Hangi durumda ne değer" sütunu `spec.md`'nin tanımladığı kadarını yazar; boş kalanlar kod yazılınca doldurulur.

### 4.1 Durum ve mod

| Alan | Tip | Birim | Anlam | Hangi durumda ne değer |
|---|---|---|---|---|
| `timestamp` | uint64 | µs | Mesajın yayın anı (PX4 saati, açılıştan beri) | Her mesajda |
| `mode_nav_state` | uint8 | — | PX4'ün AUTO FOLLOW'a verdiği mod numarası | 23–30. Kayıt henüz yoksa 0. **19 değildir** (⚠️ yukarıdaki uyarı) |
| `mode_active` | bool | — | PX4'ün şu anki modu AUTO FOLLOW mu | `vehicle_status.nav_state == mode_nav_state` ise 1 |
| `state` | uint8 | — | Modun iç durumu | Bkz. Bölüm 5 (`STATE_*`) |

### 4.2 Pi'den gelen ham veri (son `AF_LOS` mesajı)

| Alan | Tip | Birim | Anlam | Hangi durumda ne değer |
|---|---|---|---|---|
| `los_timestamp` | uint64 | µs | Son `AF_LOS` mesajının Pixhawk'a **varış** anı | Mesaj hiç gelmediyse 0 |
| `los_frd` | float32[3] | — (body FRD) | Ham LOS x, y, z (`data[0..2]`) | Doğrulamadan geçmese de son gelen değer yazılır |
| `los_age` | float32 | ms | Pi'nin bildirdiği yaş (`data[3]`) | Aynı |
| `los_seq` | uint32 | — | Sıra numarası (`data[4]`) | Aynı |
| `los_target` | bool | — | Hedef var bayrağı (`data[5]`) | 0 gelince KAYIP_BEKLE hemen başlar |

### 4.3 Doğrulama ve sayaçlar

| Alan | Tip | Birim | Anlam | Hangi durumda ne değer |
|---|---|---|---|---|
| `check_result` | uint8 | — | Son mesajın doğrulama sonucu | Bkz. Bölüm 6 (`CHECK_*`) |
| `accept_count` | uint32 | adet | Kabul edilen mesaj sayısı (açılıştan beri) | Sürekli artar |
| `reject_name_count` | uint32 | adet | Adı `AF_LOS` olmadığı için atılan | `CHECK_NAME` |
| `reject_nonfinite_count` | uint32 | adet | NaN / sonsuz değer içerdiği için atılan | `CHECK_NONFINITE` |
| `reject_norm_count` | uint32 | adet | LOS uzunluğu 1'den çok saptığı için atılan | `CHECK_NORM` |
| `reject_seq_count` | uint32 | adet | Sıra no artmadığı için (tekrar / geri) atılan | `CHECK_SEQ` |
| `reject_age_count` | uint32 | adet | Gerçek yaş `AF_DATA_TOUT`'tan büyük olduğu için atılan | `CHECK_AGE` |
| `reject_position_count` | uint32 | adet | Drone'un kendi yerel konumu geçersiz olduğu için atılan | `CHECK_POSITION` (ör. masada GPS yok) |
| `reject_depression_count` | uint32 | adet | Aşağı bakış açısı `AF_MIN_DEP`'ten küçük olduğu için atılan | `CHECK_DEPRESSION` |
| `reject_range_count` | uint32 | adet | Yükseklik farkı ≤ 0 ya da mesafe `AF_MAX_RNG`'den büyük olduğu için atılan | `CHECK_RANGE` |
| `no_target_count` | uint32 | adet | "Hedef yok" bayrağıyla gelen mesaj sayısı | `CHECK_NO_TARGET` (bozuk veri değil) |
| `latency` | float32 | ms | Kullanılan ölçümün toplam gecikmesi = (işlem anı − varış) + yaş | Gecikme telafisi gerekip gerekmediği buna bakılarak karar verilecek (m13/m16) |

### 4.4 Geometri (yönden hedefin yerine)

| Alan | Tip | Birim | Anlam | Hangi durumda ne değer |
|---|---|---|---|---|
| `los_ned` | float32[3] | — (NED) | Dünyaya çevrilmiş LOS (varış anındaki drone tutumuyla) | — |
| `depression` | float32 | rad | Aşağı bakış açısı δ = asin(`los_ned` z) | Örnek: LOS (0.8, 0, 0.6), düz uçuş → 0.644 rad (36.9°) |
| `height_diff` | float32 | m | Yükseklik farkı h = drone yüksekliği − `AF_GND_OFS` − `AF_TGT_HGT` | Örnek: 10 m irtifa → 9.0 m |
| `range_meas` | float32 | m | Bu ölçümden çıkan yatay mesafe d = h / tan(δ) | Örnek → 12.0 m |

### 4.5 Alpha-beta filtresi (girdi ve çıktı)

| Alan | Tip | Birim | Anlam | Hangi durumda ne değer |
|---|---|---|---|---|
| `target_meas_ned` | float32[2] | m (NED x, y) | **Filtre girdisi:** bu ölçümden bulunan hedef konumu | — |
| `target_est_ned` | float32[2] | m (NED x, y) | **Filtre çıktısı:** kestirilen hedef konumu | İlk ölçümde ölçüme eşit; EKF reset'te sıfırlanır |
| `target_vel_ned` | float32[2] | m/s (NED x, y) | **Filtre çıktısı:** kestirilen hedef hızı | İlk ölçümde 0. Açık çevrimde drone'un kendi hızına yakın çıkar (hedef drone'la "kayar"); bu yüzden orada `AF_K_FF` = 0 |
| `filter_updated` | bool | — | Bu çevrimde yeni ölçümle düzeltme yapıldı mı | Yeni kabul edilmiş ölçüm yoksa 0 (yalnızca tahmin) |

### 4.6 Guidance (karar ve PX4'e giden istek)

| Alan | Tip | Birim | Anlam | Hangi durumda ne değer |
|---|---|---|---|---|
| `range_est` | float32 | m | Kestirilen hedefe yatay mesafe | — |
| `range_desired` | float32 | m | İstenen mesafe = h / tan(`AF_TRK_ANG`) | Örnek: h = 9.0 m, 30° → 15.6 m |
| `vel_cmd_law` | float32[2] | m/s (NED x, y) | Kuralın istediği hız, sınırlardan **önce** | Örnek: (12.0 − 15.6) · 0.5 → 1.8 m/s geri |
| `vel_cmd` | float32[2] | m/s (NED x, y) | `AF_VEL_MAX` kırpması ve `AF_ACC_MAX` sınırından **sonra**, PX4'e giden hız | KAYIP_BEKLE ve HOLD_ISTENDI'de 0. Moda girişte drone'un o anki hızından başlar |
| `yaw_cmd` | float32 | rad (NED) | Burun yönü isteği (drone → kestirilen hedef) | KAYIP_BEKLE ve HOLD_ISTENDI'de son yaw |
| `yaw_frozen` | bool | — | Hedef `AF_YAW_MIN_D`'den yakın olduğu için yaw sabit mi | — |
| `alt_hold_z` | float32 | m (NED z, aşağı +) | Tutulan irtifa: moda girildiği andaki z | Örnek: 10 m irtifa → −10.0 |

### 4.7 Süreler

| Alan | Tip | Birim | Anlam | Hangi durumda ne değer |
|---|---|---|---|---|
| `time_since_valid` | float32 | s | Son geçerli mesajdan beri geçen süre | Moda hedefsiz girişte giriş anından sayılır. `AF_DATA_TOUT`'u geçince KAYIP_BEKLE |
| `lost_time` | float32 | s | KAYIP_BEKLE'de geçen süre | TAKIP'te 0. `AF_LOST_T`'yi geçince Hold istenir |
| `hold_request_count` | uint8 | adet | Gönderilen Hold isteği sayısı | Normalde 1. Hold reddedilirse 1 s arayla en fazla 3 |

## 5. Durumlar (`state` alanı)

| Değer | Ad | Ne demek | Drone ne yapar | Nasıl çıkılır |
|---|---|---|---|---|
| 0 | `STATE_PASIF` | Mod kapalı | AUTO FOLLOW hiçbir istek göndermez; gelen veri yine işlenir ve loglanır | Pilot AUTO FOLLOW'u açınca: geçerli hedef varsa TAKIP, yoksa KAYIP_BEKLE |
| 1 | `STATE_TAKIP` | Geçerli veri var | Hedefi takip eder: hız + sabit irtifa + burun hedefte | `AF_DATA_TOUT` (0.5 s) geçerli veri yoksa ya da Pi "hedef yok" derse → KAYIP_BEKLE · pilot başka moda geçerse → PASIF |
| 2 | `STATE_KAYIP_BEKLE` | Hedef kayıp, kısa bekleme | Yerinde bekler: kayıp anındaki konum, hız 0, son yaw, giriş irtifası | `AF_LOST_T` (1.0 s) dolmadan geçerli veri gelirse → TAKIP (kendiliğinden) · dolarsa → HOLD_ISTENDI · pilot başka moda geçerse → PASIF |
| 3 | `STATE_HOLD_ISTENDI` | PX4'ten Hold istendi | PX4 Hold moduna geçene kadar yerinde bekler | PX4 Hold'a geçince → PASIF. Takibe **kendiliğinden dönülmez**; pilot modu yeniden açar (RC anahtarını başka konuma alıp geri getirir ya da QGC'den seçer) |

**Zaman çizelgeleri:**
- Veri kesilirse: `son geçerli mesaj ──0.5 s──▶ KAYIP_BEKLE ──1.0 s──▶ Hold` (toplam 1.5 s).
- Pi "hedef yok" derse: `bayrak 0 ──▶ KAYIP_BEKLE (hemen) ──1.0 s──▶ Hold`.
- Hedef görünmezken moda girilirse: `giriş ──▶ KAYIP_BEKLE ──(girişten 1.5 s)──▶ Hold`.

## 6. Doğrulama sonuçları (`check_result` alanı)

Kontroller bu sırayla yapılır; ilk geçilemeyen kontrol sonucu belirler. Sayısal değerler (0–9) taslaktır, kodla kesinleşir.

| Değer | Ad | Ne demek | Sayaç |
|---|---|---|---|
| 0 | `CHECK_OK` | Mesaj kabul edildi, filtreye girdi | `accept_count` |
| 1 | `CHECK_NAME` | Mesajın adı `AF_LOS` değil (başka bir program da `debug_array` gönderiyor olabilir) | `reject_name_count` |
| 2 | `CHECK_NONFINITE` | Değerlerden biri NaN ya da sonsuz | `reject_nonfinite_count` |
| 3 | `CHECK_NORM` | LOS uzunluğu 1'den `AF_NORM_TOL`'den fazla sapıyor | `reject_norm_count` |
| 4 | `CHECK_SEQ` | Sıra no öncekinden büyük değil (tekrar ya da geri) | `reject_seq_count` |
| 5 | `CHECK_AGE` | Gerçek yaş `AF_DATA_TOUT`'tan büyük (görüntü çok eski) | `reject_age_count` |
| 6 | `CHECK_NO_TARGET` | Pi "hedef yok" dedi; bozuk veri değil, KAYIP_BEKLE başlar | `no_target_count` |
| 7 | `CHECK_POSITION` | Drone'un kendi yerel konumu geçersiz (ör. GPS yok, masa testi) | `reject_position_count` |
| 8 | `CHECK_DEPRESSION` | Aşağı bakış açısı `AF_MIN_DEP`'ten küçük (hedef ufka çok yakın ya da yukarıda) | `reject_depression_count` |
| 9 | `CHECK_RANGE` | Yükseklik farkı ≤ 0 ya da mesafe `AF_MAX_RNG`'den büyük | `reject_range_count` |

## 7. Dosyalar ve script'ler

| Ad | Ne | Kilit durumu |
|---|---|---|
| `src/modules/auto_follow/AutoFollow.cpp/.hpp` | Modülün ana kodu: PX4'e kayıt, 50 Hz çevrim, durum makinesi, setpoint ve log yayını | Kilitli, onay gerekli |
| `src/modules/auto_follow/AutoFollowGuidance.cpp/.hpp` | Hesaplar: doğrulama, geometri, guidance kuralı, sınırlar (ayrı kütüphane, birim testi için) | Kilitli, onay gerekli |
| `src/modules/auto_follow/AlphaBetaFilter.hpp` | Alpha-beta filtresi sınıfı | Kilitli, onay gerekli |
| `src/modules/auto_follow/AutoFollowGuidanceTest.cpp` | Kısa birim testi (`make tests TESTFILTER=AutoFollowGuidance`) | Kilitli, onay gerekli |
| `src/modules/auto_follow/CMakeLists.txt`, `Kconfig`, `module.yaml` | Derleme, açma ayarı, parametre tanımları | Kilitli, onay gerekli |
| `msg/AutoFollowStatus.msg` | Log mesajının tanımı (Bölüm 4) | Kilitli, onay gerekli |
| `ROMFS/px4fmu_common/init.d/rc.mc_apps` (satır) | Açılışta `auto_follow start` | Kilitli, onay gerekli (7. yol) |
| `tez/sitl/af_los_gonder.py` | Geçici test göndericisi: Pi gibi `AF_LOS` gönderir (açık / kapalı çevrim) | İzinli |
| `tez/analiz/af_log_analiz.py` | ULog'u pyulog 1.2.4 ile okuyup senaryo ölçümlerini çıkaran script | İzinli |
| `~/Desktop/AUTO-FOLLOW LOG/` | Her SITL testinden sonra ULog'un kopyalandığı klasör (repo dışı) | — |

## Belge geçmişi

| Sürüm | Tarih | Ne |
|---|---|---|
| 1 | 2026-11-10 | İlk sürüm (write-spec turu): bütün adlar, spec'teki tanımlarla; kod henüz yok |
