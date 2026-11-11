# Görev grubu 4: SITL ön kontroller, test göndericisi, S1a–S5 (açık çevrim)

- **Tarih:** 2026-11-10/11 · **Dal:** `ozellik/m15-takip-kodu` · **Görev listesi:** `../tasks.md` Grup 4 (4.1–4.14)
- **Durum:** Bitti. Test göndericisi `tez/sitl/af_los_gonder.py` yazıldı; ön kontroller (QGC ekranı hariç) ve S1a, S1b, S2, S3, S4 (yalnız KAYIP_BEKLE kısmı), S5 Gazebo Harmonic'te koşuldu ve ULog'dan sayıyla ölçüldü. **Modül kodunda hata bulunmadı, `src/modules/auto_follow/` değişmedi.** Spec'in söylemediği 6 gözlem ve 4 açık soru Bölüm 8–9'da.
- Bu not kod okumadan anlaşılacak şekilde yazıldı. Adların anlamı `../log-sozlugu.md`'de. Bütün uygulama kararları ayrıca `../rapor.md` §5.1'de.

## 1. Ne yapıldı?

1. **Test göndericisi** (`tez/sitl/af_los_gonder.py`, izinli yol `tez/*`): Pi'nin göndereceği `AF_LOS` mesajını SITL'e taklit eden Python script'i. Açık çevrimde sabit bir yön, kapalı çevrimde yerde hayali bir hedefe göre gerçek yön gönderir; S4 ve S5 için zaman çizelgeli "kesme" ve "bozma" kipleri vardır.
2. **Ön kontroller:** modun açılışta kaydolması, mod numarası, arm/geçiş kuralları (C1, A14), giriş/çıkışta setpoint, RC anahtarı, RC çubuğuyla Position'a geçiş (A2), MAVLink 2.
3. **Senaryolar S1a, S1b, S2, S3, S4 (KAYIP_BEKLE kısmı), S5:** her biri ayrı bir SITL oturumunda; her oturumun ULog'u `~/Desktop/AUTO-FOLLOW LOG/`'a özgün adıyla kopyalandı.

| Dosya | Ne | Yeni mi? |
|---|---|---|
| `tez/sitl/af_los_gonder.py` | Test göndericisi | Yeni (çalıştırılabilir) |
| `agent-os/specs/2026-11-08-m15-takip-kodu/implementation/grup-4-sitl-acik-cevrim.md` | Bu not | Yeni |
| `rapor.md`, `log-sozlugu.md`, `spec.md`, `tasks.md` | Sonuçlar, kararlar, sözlük satırları | Değişti |

`tez/pin/allowed-paths.txt`'e ve PX4 dosyalarına dokunulmadı. Hiçbir `.ulg` dosyası repoya girmedi.

## 2. Test göndericisi `tez/sitl/af_los_gonder.py`

**Ne gönderir:** MAVLink 2 `DEBUG_FLOAT_ARRAY`, `name = "AF_LOS"`, `data[0..2]` LOS (body FRD), `data[3]` yaş [ms], `data[4]` sıra no (her gönderilen mesajda +1), `data[5]` hedef var (1) / yok (0) (spec Bölüm 2). MAVLink 2, `pymavlink` içe aktarılmadan önce `MAVLINK20=1` ile açılır (`data` bir MAVLink 2 ek alanıdır).

**Seçenekler** (kullanıcının geçici kararı, 2026-11-10; Vision'ın geri bildirimine göre değişebilir, bu yüzden varsayılanlar dosyanın başında sabit olarak toplandı):

| Seçenek | Varsayılan | Anlamı |
|---|---|---|
| `--cevrim acik\|kapali` | `acik` | Açık: sabit LOS. Kapalı: yerde hayali hedef, drone'un konumu ve tutumu MAVLink'ten okunur |
| `--los X Y Z` | `0.8 0 0.6` | Açık çevrim LOS (spec Bölüm 3 örneği = S1b). Birim vektöre çevrilmeden aynen gönderilir |
| `--senaryo <kes\|hedef-yok\|yanlis-ad\|nan\|norm\|sira\|eski\|ufuk\|uzak>` | yok | Zaman çizelgeli kesme/bozma (aşağıda) |
| `--hiz` | 20 Hz | Gönderim hızı |
| `--yas` | 50 ms | `data[3]` |
| `--baglanti` | **`udpin:0.0.0.0:14540`** | pymavlink bağlantı adresi (aşağıdaki düzeltmeye bakın) |

**Bağlantı adresi düzeltmesi (kullanıcıya bildirilecek):** Kararda varsayılan `udpout:127.0.0.1:14540` yazıyordu. PX4 SITL'in onboard kanalı UDP **14580'i dinler, 14540'a gönderir** (`ROMFS/px4fmu_common/init.d-posix/px4-rc.mavlink:4-5, 26`; konsolda `mode: Onboard ... on udp port 14580 remote port 14540`). `udpout:127.0.0.1:14540` ile mesajlar PX4'ün dinlemediği porta giderdi. İki doğru seçenek vardı: (a) `udpin:0.0.0.0:14540` (script 14540'ı dinler, PX4'ün ilk paketinden sonra cevabı aynı porttan yollar) · (b) `udpout:127.0.0.1:14580`. **(a) seçildi:** PX4 ilk paketi gönderenin adresini "ortak" olarak hatırlıyor ve değiştirmiyor (`mavlink_receiver.cpp:3203-3218`); (b)'de script her yeniden başlatıldığında rastgele yeni bir porttan gönderir ve PX4 konum akışını eski porta yollamaya devam eder, kapalı çevrim konumu alamaz. (a)'da port hep 14540 kalır. Seçenek adı aynı, yalnızca değer değişti.

**Senaryo zaman çizelgeleri** (t = script başladıktan sonra geçen süre; değerler dosyanın başındaki sabitlerde):

| Senaryo | t < 10 s | Ne yapar | Ne sınar |
|---|---|---|---|
| `kes` | normal | 10–11 s gönderim yok (1,0 s) · 20–23 s gönderim yok (3,0 s) · sonra normal | S4-b: 0,5 s'de KAYIP_BEKLE, 1,0 s'de dönüş → takip sürer · S4-a: 0,5 s'de KAYIP_BEKLE, 1,5 s'de HOLD_ISTENDI · veri dönünce HOLD_ISTENDI'den çıkılmaz |
| `hedef-yok` | normal | 10–10,5 s `data[5] = 0` · 20–23 s `data[5] = 0` · sonra normal | S4-c: hemen KAYIP_BEKLE; kısa olanda dönüş, uzun olanda 1,0 s sonra HOLD_ISTENDI |
| `yanlis-ad`, `nan`, `norm`, `sira`, `eski`, `ufuk`, `uzak` | normal | 10–20 s her 5. mesaj bozuk (araya karışık) · 20–23 s bütün mesajlar bozuk · sonra normal | S5: atılır, sayaç artar, drone etkilenmez · uzun bozuk veri → hedef kaybı yolu |

Bozuk değerler: `yanlis-ad` ad `AF_TEST` · `nan` sırayla LOS x = NaN ve yaş = +sonsuz · `norm` LOS 0,7 katı (uzunluk 0,7) · `sira` sırayla son geçerli sıra no'nun tekrarı ve 10 geri; hepsi bozukken hep aynı sıra no · `eski` yaş 600 ms · `ufuk` burnun 5° altı · `uzak` burnun 11° altı (10 m'de ~46 m > 40 m).

**Hedefsiz moda giriş (S4-d)** için script hiç çalıştırılmaz (ayrı bir seçenek gerekmedi).

**Kapalı çevrim:** script başlarken drone'un konumunu ve burun yönünü okur, hayali hedefi **burnun 20 m önüne, yere** koyar; bakılan nokta `AF_TGT_HGT` = 1,0 m yükseklikte. Her mesajda drone'dan bu noktaya NED yönü hesaplanır ve `ATTITUDE` (roll, pitch, yaw) ile gövde eksenine (FRD) çevrilir. Konum ya da tutum 0,5 s'den eskiyse mesaj gönderilmez. **S6/S7 için hedefin yeri, hızı ve yolu kullanıcıya henüz sorulmadı;** şimdilik hedef duruyor (`HEDEF_ILERI_M = 20`, `HEDEF_HIZ_NED = (0, 0)` sabitleri; yeni komut satırı seçeneği eklenmedi).

**Kontroller:** `ruff format` ve `ruff check` (ruff 0.16.9, `/home/yusuf/Desktop/Projects/Auto-Follow/.venv-tez/bin/ruff`) temiz. Ruff 0.16.9'un varsayılan kuralları `#!` satırı olan dosyanın çalıştırılabilir olmasını istiyor (EXE001); dosya çalıştırılabilir yapıldı. Tip ipuçları ve herkese açık fonksiyonlarda docstring var. Dönüşüm fonksiyonu elle denendi: drone 10 m'de, düz, hedef 12 m kuzeyde → (0,8; 0; 0,6); burun doğuda → (0; −0,8; 0,6); burun 10° yukarıda → aşağı bakış 46,9° (beklenen 36,9 + 10). SITL'de kapalı çevrimde FC'nin bulduğu hedef konumu script'in koyduğu noktayla aynı çıktı (Bölüm 4.3): iki tarafın eksen anlaşması tutarlı.

**Kullanılan Python:** `/home/yusuf/Desktop/Projects/Auto-Follow/.venv-tez/bin/python` (3.12.3). pymavlink **2.4.50** ve pyulog **1.2.4** sabit sürümlerdeki gibi, ama ikisi de sanal ortamın içinden değil `~/.local/lib/python3.12/site-packages/`'tan geliyor (Grup 2'deki bulguyla aynı).

## 3. Test oturumlarının düzeni (4.2)

Her oturum:

1. `build/px4_sitl_default/rootfs/parameters*.bson` silindi (yalnızca "yeniden başlatmada aynı numara" kontrolünde bilerek silinmedi).
2. `PX4_PARAM_AF_ENABLE=1 HEADLESS=1 make px4_sitl gz_x500` arka planda; girdisi `sleep infinity |` ile beklemede tutuldu (Grup 2'deki 240 MB konsol sorunu yaşanmadı). Konsol komutları `build/px4_sitl_default/bin/px4-*` istemcileriyle verildi.
3. `AF_K_FF` = 0,0000 her oturumda `param show` ile görüldü; `AF_LOST_T` = 1,0, `AF_DATA_TOUT` = 0,5, `MC_YAWRATE_MAX` = 200 (varsayılanlar).
4. **Kalkış Position modunda** (sapma yok): geçici bir "pilot" script'i (yalnızca scratchpad'de, repoda değil) GCS gibi bağlandı (PX4'ün GCS kanalı 18570 ↔ 14550), 1 Hz GCS heartbeat'i ve 25 Hz **MAVLink `MANUAL_CONTROL`** (sanal joystick; SITL'de `COM_RC_IN_MODE` = 1, `init.d-posix/rcS:170`) gönderdi. Gaz kolu aşağıda arm, gaz %60 yukarıda tırmanış, ~9,4 m'de orta konum; irtifa 9,88–9,94 m'de sabitlendi. Sonra havada AUTO FOLLOW'a geçildi.
5. **Mod değişimi:** MAVLink `MAV_CMD_DO_SET_MODE`, `param1 = 1` (özel mod), `param2 = 4` (AUTO), `param3 = 11` (`PX4_CUSTOM_SUB_MODE_EXTERNAL1`, `px4_custom_mode.h:69`); Position'a dönüş `4 → 3, 0`. Bu QGC'nin mod seçerken yaptığının aynısıdır. Bir oturumda ayrıca RC anahtarıyla (Bölüm 4.1).
6. Oturum sonunda `px4-logger stop`, sonra px4 ve gz süreçleri PID ile kapatıldı (`px4-shutdown` takılması, Grup 1). Son kontrolde hiç px4/gz süreci kalmadı. Log özgün adıyla kopyalandı, parametre dosyası yine silindi.
7. Ölçüm: pyulog 1.2.4'ün Python arayüzüyle (`pyulog.ULog`) geçici analiz script'leri (scratchpad). Kalıcı analiz script'i `tez/analiz/af_log_analiz.py` Grup 6'nın işi; bu notta hesapların ne olduğu yazılı.

**Logların adı ve yeri:** PX4 logu açılış anının **UTC** saatiyle adlandırır (yerel saat UTC+3). Klasör: `/home/yusuf/Desktop/AUTO-FOLLOW LOG/` (SITL'de `rootfs/log/2026-11-10/` altındaydılar). Notta "t" = PX4 açılışından beri geçen süre (ULog zamanı).

| ULog | Oturum |
|---|---|
| `20_48_09.ulg` | Ön kontroller 1: disarm iken geçiş, bu modda arm reddi, yerde arm'lıyken geçiş reddi, havada giriş/çıkış, çubukla Position, kısa kapalı çevrim, MAVLink 2 |
| `20_52_31.ulg` | Ön kontroller 2: parametreler silinmeden yeniden açılış (aynı numara). RC denemesi bu oturumda yapılamadı (Bölüm 7, sorun 3) |
| `20_55_24.ulg` | Ön kontroller 3: RC anahtarıyla giriş/çıkış, RC çubuğuyla Position, arm reddinin nedeni |
| `20_56_47.ulg` | S1a |
| `20_58_51.ulg` | S1b |
| `21_00_19.ulg` | S2 |
| `21_01_32.ulg` | S3 |
| `21_02_55.ulg` | S4 (a, b, c, d) |
| `21_05_34.ulg` | S5 (7 bozma türü) |
| `21_10_47.ulg` | S5 ek: `ufuk` ve `uzak`, temel LOS 30° ile (Bölüm 5.6) |

## 4. Ön kontroller (4.3, 4.4)

### 4.1 Sonuçlar

| Kontrol | Ne yapıldı | Görülen / ölçülen | Sonuç |
|---|---|---|---|
| Modül açılışta kendiliğinden başladı (B2) | 10 oturumun hepsi `PX4_PARAM_AF_ENABLE=1` ile | Her açılışta konsolda `mode 'AUTO FOLLOW' registered: nav_state 23` (açılıştan ~4,8 s sonra) | Geçti |
| `mode_nav_state` 23–30 | `auto_follow status`, `commander status`, log | 23; `commander status`: `External Mode 1: nav_state: 23, name: AUTO FOLLOW`; logda `mode_nav_state` hep 23 | Geçti |
| `can_set_nav_states_mask`'ta bit | `vehicle_status` (log) | Kayıttan önce 8 308 095 (bit 23 = 0), sonra 16 696 703 (bit 23 = 1) | Geçti |
| Yeniden başlatmada aynı numara | Parametre dosyası silinmeden yeniden açılış (`20_52_31.ulg`) | Yine 23; `COM_MODE0_HASH` = −1849044625 kaydedilmiş | Geçti |
| Disarm iken moda geçiş kabul (C1) | Yerde, disarm, `DO_SET_MODE` (`20_48_09.ulg` t = 15,62) | Kabul, `nav_state` 23 | Geçti |
| Bu modda arm reddedilir (C1) | AUTO FOLLOW'da disarm, arm komutu (t = 17,14) | ACK `TEMPORARILY_REJECTED`; STATUSTEXT `Arming denied: Resolve system health failures first`; `health_report.can_arm_mode_flags`'te bit 23 = 0, `failsafe_flags.mode_req_prevent_arming`'de bit 23 = 1 (`20_55_24.ulg` oturumu); 3 s sonra Position'da arm kabul edildi | Geçti (mesaj genel; bkz. 8.6) |
| Yerde arm'lıyken moda geçiş engellenir (B4, A14) | Position'da yerde arm (t = 20,19), sonra `DO_SET_MODE` AUTO FOLLOW (t = 21,20) | Commander ACK `TEMPORARILY_REJECTED` (t = 21,208); STATUSTEXT **`Switching to External 1 is currently not available`**; log olayı `Switching to mode 'External 1' is currently not possible`; `nav_state` Position'da kaldı | Geçti (metindeki ad "External 1"; bkz. 8.6) |
| Girişte ilk çevrimde setpoint | Havada 3 giriş (`20_48_09.ulg`) | Modun açık göründüğü **ilk** çevrimde `vel_cmd` dolu (setpoint o çevrimde yayınlandı). Logger'ın girişten sonraki ilk `trajectory_setpoint` örneği iki girişte tam bu çevrimin örneği (t = 56,976 ve 68,176, `auto_follow_status`'la aynı an ve aynı hız) | Geçti |
| Çıkışta setpoint durur | 3 çıkış | Çıkıştan sonraki ilk `trajectory_setpoint` örneği Position'ın (FlightTask); mod açıkken loglanan 219 örneğin hepsi bizim; üç ön kontrol logunda mod kapalıyken bizim imzalı (ivme NaN, dikey hız NaN, `position[2]` dolu) **0** örnek | Geçti |
| QGC ile giriş/çıkış | QGC'nin gönderdiği komut (`DO_SET_MODE`) script'ten gönderildi | Yukarıdaki gibi | Geçti (komut düzeyinde) |
| RC anahtarıyla giriş/çıkış | `RC_CHANNELS_OVERRIDE` ile 8 kanal; `COM_RC_IN_MODE` = 0, `RC_CHAN_CNT` = 8, `RC_MAP_ROLL/PITCH/THROTTLE/YAW` = 1/2/3/4, `RC_MAP_FLTMODE` = 5, `COM_FLTMODE1` = 2 (Position), `COM_FLTMODE6` = **100** (External Mode 1) (`20_55_24.ulg`) | Anahtar 6. konum → AUTO FOLLOW (t = 42,98), 1. konum → Position (47,72), yine 6. konum → AUTO FOLLOW (51,72) | Geçti |
| RC çubuğu → Position (A2) | AUTO FOLLOW'da roll çubuğu %60 (joystick, `20_48_09.ulg`) ve RC kanal 1 = 1800 (`20_55_24.ulg`) | İkisinde de `Pilot took over using sticks`, Position'a geçiş (t = 61,0 ve 56,69) | Geçti |
| HEARTBEAT `base_mode` yan etkisi (A2) | Pilot script'inin aldığı HEARTBEAT | AUTO FOLLOW'da 157 = arm + özel mod + STABILIZE + GUIDED + **AUTO**; Position'da 209 = arm + özel mod + STABILIZE + **MANUAL_INPUT** (`HEARTBEAT.hpp:98-100`) | Görüldü |
| MAVLink 2 (4.4) | Gönderici çalışırken `listener debug_array` | `data: [0.80000, 0.00000, 0.60000, 50.00000, 23.00000, 1.00000, 0, …]`, `name: "AF_LOS"`; bütün oturumlarda `los_frd` sıfır değil | Geçti |
| QGC mod listesinde `AUTO FOLLOW` | — | HEADLESS çalışıldı, QGC açılmadı | **Kullanıcı kontrol edecek** |
| Hold'dan sonra anahtar aç-kapa ile yeniden giriş | — | Hold isteği henüz yok | Grup 5'te |

### 4.2 RC anahtarı ve çubuğu SITL'de nasıl verildi? (tasks 4.3 "(doğrulanacak)")

- **Çubuk:** MAVLink `MANUAL_CONTROL` (sanal joystick) yeterli; SITL'de `COM_RC_IN_MODE` = 1 zaten bunu kullanıyor. `COM_RC_OVERRIDE` = 1 (otomatik modlar, varsayılan), `COM_RC_STICK_OV` = %30.
- **Anahtar:** joystick'in mod anahtarı yok; PX4 mod anahtarını yalnızca RC kaynağından okur (`ManualControl.cpp:170-172`). Bu yüzden `RC_CHANNELS_OVERRIDE` (MAVLink'ten gelen RC) kullanıldı; `COM_RC_IN_MODE` 0'a alındı ve RC kanal eşlemeleri yukarıdaki gibi verildi. **`COM_FLTMODEx` değeri 23 değil 100'dür** ("External Mode 1", `ManualControl.cpp:595`); sözlükteki "mod numarasıyla ayarlanır" cümlesi buna göre düzeltildi.

### 4.3 Kapalı çevrim kısa kontrol (4.1, "yalnızca çalıştığı görülür")

`20_48_09.ulg`, t = 68,2–98,2 s. Hayali hedef burnun 20 m önünde. Mesafe hatası (`range_est − range_desired`) +4,47 m'den başladı, **4,5 s'de 0,3 m'nin altına indi**, aşım −0,04 m; son 10 s'de ortalama −0,006 m (std 0,02 m). Yaw hatası 0,1°'nin altında. FC'nin kestirdiği hedef konumu (−1,69; 7,27) script'in koyduğu noktayla aynı. Kapalı çevrim çalışıyor; ayrıntılı ölçüm S6'da (Grup 6).

## 5. Senaryolar (4.5–4.10)

Bütün senaryolarda `AF_K_FF` = 0, `AF_LOST_T` = 1,0 s, diğer `AF_*` varsayılan. İrtifa 10 m değil **9,88–9,94 m** oldu (elle kalkış), bu yüzden beklenen değerler ölçülen yükseklik farkıyla (h ≈ 8,92 m) yeniden hesaplandı: `range_desired` = h / tan 30° ≈ 15,46 m (spec 15,6 m, h = 9,0 ile).

**Önemli not (bütün açık çevrim senaryoları):** Açık çevrimde LOS gövdeye sabittir. Drone eğildikçe (hızlanırken, frenlerken) aynı gövde yönü dünyada başka bir açıya denk gelir; FC bunu doğru şekilde tutumla çevirir (spec Bölüm 3) ve ölçülen mesafe değişir. Bu yüzden spec'in beklediği sayılar **drone düzken** (moda girişin ilk çevrimi) birebir görülür; uçarken eğim yüzünden kayar. Bu, test yönteminin doğası (B3'ün benzeri), kod hatası değil. Ayrıntı Bölüm 8.1.

### 5.1 S1a Hedef uzakta — `20_56_47.ulg` — **Geçti**

- **Verilen:** `--los 0.951 0 0.309` (aşağı bakış ~18°), 12 s AUTO FOLLOW.
- **Drone ne yaptı:** burnunun yönünde ileri hızlandı ve 2 m/s'de sabit uçtu; irtifa ve burun yönü sabit kaldı.

| Ölçüm | Beklenen | Ölçülen |
|---|---|---|
| Girişte (düz) aşağı bakış `depression` | ~18° | 17,8° |
| Girişte `range_meas` | 27,7 m (h = 9,0) / 27,8 m (h = 8,925) | 27,81 m |
| `range_desired` | 15,46 m | 15,44–15,49 m |
| Girişte kural `vel_cmd_law` | ≈ +6,0 m/s ileri | +6,17 m/s ileri (yan bileşen 0,00) |
| `vel_cmd` en büyük | 2,0 m/s | 2,000 m/s; 601 örneğin 565'inde kural > 2 m/s (kırpıldı) |
| İvme: `vel_cmd`'nin çevrimden çevrime değişimi | ≤ 3 m/s² | en çok 3,000 m/s² |
| Drone hızı (son 5 s, `vehicle_local_position`) | 2 m/s ileri | 2,04 m/s ileri, yan 0,004 m/s; drone'un ölçülen ivmesi en çok 1,55 m/s² |
| `trajectory_setpoint` | hız, sabit irtifa, yaw; konum/ivme NaN | yatay hız ≤ 2,000; `position[2]` −9,926 sabit; yatay konum ve ivme hep NaN |
| İrtifa / `alt_hold_z` | sabit | 9,91–9,94 m / −9,926 |
| `yaw_cmd − burun yönü` | ~0 | ortalama 0,0°, en çok 0,3° |

Not: hızlanırken burun 9,3°'ye kadar aşağı eğildi, gövdeye sabit LOS daha dik göründü, `range_meas` 17,3 m'ye indi ve kural kısa süre 0,7 m/s'ye düştü; 2 m/s'ye %95 ulaşma 1,14 s sürdü (yalnız ivme sınırıyla 0,67 s olurdu). Sabit uçuşta (eğim −1,3°) aşağı bakış 19,3°, `range_meas` 25,5 m, kural 5,0 m/s → yine 2 m/s'de kırpıldı.

### 5.2 S1b Hedef yakında — `20_58_51.ulg` — **Geçti** (salınım gözlemi var)

- **Verilen:** `--los 0.8 0 0.6` (aşağı bakış ~36,9°), 12 s.
- **Drone ne yaptı:** hedeften uzaklaşarak geri uçtu; hız ve eğim düzenli olarak salındı (aşağıda).

| Ölçüm | Beklenen | Ölçülen |
|---|---|---|
| Girişte `depression` | 36,9° | 36,8° |
| Girişte `range_meas` | 12,0 m (h = 9,0) / 11,9 m (h = 8,92) | 11,93 m |
| `range_desired` | 15,45 m | 15,43–15,47 m |
| Girişte kural | ≈ −1,8 m/s (geri) | −1,76 m/s geri (yan 0,00) |
| Kırpma | yok | `vel_cmd` en çok 1,97 m/s (hiç 2'ye ulaşmadı); kuralın 601 örneğinden 17'si salınım tepelerinde 2,03'e kadar çıktı |
| İvme sınırı | ≤ 3 m/s² | en çok 3,000 m/s² |
| Drone hızı (son 5 s) | ~1,8 m/s geri | 1,53 m/s geri (yan 0,001) |
| İrtifa, yaw | sabit | 9,91–9,93 m; `yaw_cmd − burun` ≤ 0,2° |

**Salınım:** geri uçarken burun yukarı eğilir (ortalama +1,2°), sabit gövde LOS'u daha sığ görünür, ölçülen mesafe büyür, kural küçülür; hız azalınca eğim düzelir ve döngü tekrarlar. Eğim −0,6° ile +2,7°, hız komutu −1,3 ile −1,9 m/s arasında **~0,6 s periyotla sürekli** salındı. Ortalama eğimle hesap: aşağı bakış 35,7° → d = 12,43 m → kural −1,51 m/s; ölçülen ortalama hızla (1,53) uyumlu. Açık çevrime özgü (Bölüm 8.1).

### 5.3 S2 Hedef sağda — `21_00_19.ulg` — **Geçti** (yön)

- **Verilen:** `--los 0 0.8 0.6` (hedef sağda, 12 m), 12 s.
- **Drone ne yaptı:** yerinde sağa (saat yönünde, yukarıdan bakınca) döndü ve dönmeyi sürdürdü; yatay hızı küçük kaldı (son 5 s 0,19 m/s).

| Ölçüm | Beklenen | Ölçülen |
|---|---|---|
| `yaw_cmd − burun yönü` | ~+90° (sağ) | +81…+90°, ortalama +85° |
| Dönüş yönü | sağa (yaw artar) | burun yönü 12 s'de **+2 312°** arttı (~6,4 tur) |
| Dönüş hızı | PX4'ün sınırı (`MC_YAWRATE_MAX`, doğrulanacaktı) | ortalama 192°/s, en çok 206°/s; `MC_YAWRATE_MAX` = 200°/s → **sınır PX4'ün `MC_YAWRATE_MAX`'ı** (spec Bölüm 6'daki "(doğrulanacak)" doğrulandı) |
| İrtifa | sabit | 9,85–9,95 m |

Not: filtrenin hedef hızı (`target_vel_ned`) ~46 m/s çıktı: gövdeye bağlı hayali hedef drone'un çevresinde 12 m yarıçapla dönüyor. `AF_K_FF` = 0 olduğu için etkisi yok.

### 5.4 S3 Hedef neredeyse tam altta — `21_01_32.ulg` — **Geçti** (dönme gözlemi var)

- **Verilen:** `--los 0.174 0 0.985` (aşağı bakış ~80°), 12 s.
- **Drone ne yaptı:** önce geri uçtu; ~2,5 s sonra burnu dönmeye başladı ve drone 1,8 m/s ile daire çizerek dönmeyi sürdürdü.

| Ölçüm | Beklenen | Ölçülen |
|---|---|---|
| Girişte `depression` | 80° | 79,8° |
| Girişte `range_meas` | ≈ 1,6 m | 1,61 m |
| Girişte kural | ≈ −7,0 m/s (geri) | −6,93 m/s geri |
| `vel_cmd` | 2 m/s'de kırpılır | en çok 2,000 m/s; 602 örneğin hepsinde kural > 2 |
| `yaw_frozen` | 0 (d > `AF_YAW_MIN_D` = 1 m) | hiç 1 olmadı; `range_est` 1,61–3,94 m |
| İvme sınırı | ≤ 3 m/s² | en çok 3,000 m/s² |

**Dönme:** geri uçarken burun +9°'ye kadar yukarı eğildi, hedef 3,7 m öne kaydı. Hedef gövdeye bağlı ve yakın olduğu için burnun en küçük dönüşü hedefi de döndürüyor; yaw isteği burnun ~24–40° önünde kaldı ve drone ortalama 65°/s ile döndü (12 s'de 781°). Spec'in S3 için beklediği üç şey (geri, 2 m/s kırpma, yaw donmaz) sağlandı; dönme beklenmiyordu (Bölüm 8.2).

### 5.5 S4 Hedef kaybı, yalnız KAYIP_BEKLE kısmı — `21_02_55.ulg` — **Geçti**

Bu grupta Hold isteği yok (Grup 5): süre dolunca durum HOLD_ISTENDI olur ve drone yerinde beklemeyi sürdürür; `hold_request_count` 0. Beklenen davranış budur. Temel LOS S1b'ninki (drone ~1,5 m/s geri uçarken kayıp başlar, böylece duruş görülür). Süreler mesajın **varış** anından ölçüldü.

| Varyant | Verilen | Ölçülen | Beklenen | Sonuç |
|---|---|---|---|---|
| (b) kısa kesinti | `--senaryo kes`, 1,0 s gönderim yok | son mesaj t = 44,684 → KAYIP_BEKLE 45,196 (**+0,512 s**) · gönderim 45,736'da döndü → TAKIP 45,756 (bir çevrim sonra) | 0,5 s'de bekleme, 1,0 s dolmadan dönünce takip sürer | Geçti |
| (a) uzun kesinti | aynı script, 3,0 s gönderim yok | son mesaj 54,684 → KAYIP_BEKLE 55,196 (**+0,512 s**) → HOLD_ISTENDI 56,196 (**+1,512 s**, `lost_time` 1,012) · veri 57,736'da döndü → **HOLD_ISTENDI'de kaldı** (mod kapanana kadar, 61,98) | 0,5 s + 1,0 s; Hold'dan sonra takibe kendiliğinden dönülmez | Geçti |
| (c) hedef yok | `--senaryo hedef-yok`: 0,5 s, sonra 3,0 s `data[5] = 0` | ilk "hedef yok" 76,736 → KAYIP_BEKLE 76,756 (**bir çevrim**) · bayrak 1'e döndü → TAKIP 77,256 · uzun: 86,736 → KAYIP_BEKLE 86,756 → HOLD_ISTENDI 87,736 (**+1,000 s**) · sonra gelen geçerli veri durumu değiştirmedi | hemen bekleme, 1,0 s sonra Hold | Geçti |
| (d) hedefsiz giriş | script çalışmıyor (son mesaj 3,6 s önce) | giriş 101,116 → aynı çevrimde KAYIP_BEKLE → HOLD_ISTENDI 102,616 (**girişten 1,500 s**); `time_since_valid` girişte 0'dan saydı (A3) · 5 s sonra script başladı → HOLD_ISTENDI'de kaldı | girişten 1,5 s sonra Hold | Geçti |

**Yerinde bekleme (hover) ölçümü** (`trajectory_setpoint` + `vehicle_local_position`):

| Bekleme | Süre | `trajectory_setpoint` | Drone |
|---|---|---|---|
| (b) kısa | 0,54 s | yatay hız 0, tutulan nokta sabit | 1,59 m/s'den 0,72'ye yavaşladı (takip döndü) |
| (a) uzun | 6,76 s | yatay hız 0, nokta sabit, `vel_cmd` 0 | 1,52 → 1 s'de 0,22 → 0,01 m/s; tutulan noktaya en çok 0,70 m uzaklaştı (fren), sonunda 0,04 m |
| (c) kısa | 0,48 s | aynı | 1,56 → 0,78 m/s |
| (c) uzun | 7,78 s | aynı | 1,52 → 0,23 → 0,02 m/s; en çok 0,68 m, sonunda 0,06 m |
| (d) | 9,52 s | aynı | zaten duruyordu; 0,04 m içinde |

İrtifa beklemelerde 9,89–9,94 m (`alt_hold_z` sabit). `auto_follow status` her varyantın sonunda `STATE_HOLD_ISTENDI` gösterdi.

Süre ayrıntısı: "+0,512 s" = 0,5 s + mesajın varışından sonraki 20 ms'lik çevrim sınırına kadar geçen 12 ms. Mesaj kaybı yok: bu oturumda gönderilen 1 281 mesajın 1 281'i FC'ye ulaştı ve işlendi.

### 5.6 S5 Girdi doğrulama — `21_05_34.ulg` (+ ek `21_10_47.ulg`)

Her tür ayrı bir girişte: 10 s normal → 10 s araya karışık (her 5. mesaj bozuk, 39–40 mesaj) → 3 s hepsi bozuk (60 mesaj) → normal. Temel LOS S1b'ninki (drone −1,4…−1,5 m/s geri uçarken; hız S1b'deki gibi ±0,3 m/s salınıyor).

| Tür | Araya karışık bölüm: atılan / doğru sayaç | `check_result` | Durum | `vel_cmd` ileri bileşeni (önce → araya karışık) | Hepsi bozukken (3 s) | Sonuç |
|---|---|---|---|---|---|---|
| `yanlis-ad` | 39 / yalnız `reject_name_count` (toplam 100) | 0, 1 | hep TAKIP | −1,45 ±0,27 → −1,51 ±0,29 | KAYIP_BEKLE +0,5 s, HOLD_ISTENDI +1,5 s | Geçti |
| `nan` | 39 / yalnız `reject_nonfinite_count` (100) | 0, 2 | hep TAKIP | −1,43 → −1,52 | +0,5 / +1,5 s | Geçti |
| `norm` | 39 / yalnız `reject_norm_count` (100) | 0, 3 | hep TAKIP | −1,43 → −1,53 | +0,5 / +1,5 s | Geçti |
| `sira` | 39 / yalnız `reject_seq_count` | 0, 4 | hep TAKIP | −1,44 → −1,50 | **Hold yoluna girmedi:** her 0,5 s'de bir mesaj kabul edildi (toplam `reject_seq_count` 94, 6 kabul), durum TAKIP ↔ KAYIP_BEKLE (KAYIP_BEKLE 20 ms) gidip geldi | Araya karışık bölüm geçti; uzun bölüm **beklenenden farklı** (Bölüm 8.3) |
| `eski` | 39 / yalnız `reject_age_count` (100) | 0, 5 | hep TAKIP | −1,42 → −1,51 | +0,5 / +1,5 s | Geçti |
| `ufuk` (5°) | 39 / yalnız `reject_depression_count` | 0, 8 | hep TAKIP | −1,42 → −1,48 | KAYIP_BEKLE +0,50 s, ama 0,26 s sonra **takibe döndü** (frenleyen drone burnunu eğince bazı mesajlar 10°'yi geçti) | Araya karışık bölüm geçti; uzun bölüm açık çevrim etkisi (8.4) |
| `uzak` (11°) | 29 atıldı (18 `CHECK_DEPRESSION`, 11 `CHECK_RANGE`), **10 kabul edildi** | 0, 8, 9 | hep TAKIP | −1,42 → **−1,15 ±0,48** (etkilendi) | kısa KAYIP_BEKLE, sonra takip | Açık çevrim etkisi (8.4); ek oturumla tekrarlandı ↓ |

Süreler son kabul edilen mesajdan (logda 0,48–0,50 s ve 1,48–1,50 s; fark, kabulün işlendiği çevrimle varış arasındaki ≤ 20 ms). Ölçü: "drone etkilenmez" için araya karışık bölümde `vel_cmd`'nin ortalaması S1b salınımının (±0,3 m/s) içinde, en çok 0,1 m/s kaydı (`uzak` hariç). Durum hiç TAKIP'ten çıkmadı.

**Ek oturum `21_10_47.ulg` (`--senaryo ufuk|uzak --los 0.866 0 0.5`):** temel LOS takip açısında (30°), yani istenen hız ~0. Amaç eğimi küçültmekti; ama burada da S1b'deki salınım ±3° eğimle sürdü (30°'de mesafe eğime daha da duyarlı).
- `ufuk`: araya karışık 39 / yalnız `reject_depression_count`, TAKIP; hepsi bozukken KAYIP_BEKLE **+0,50 s**, HOLD_ISTENDI **+1,50 s**. **Geçti.**
- `uzak`: 10 `CHECK_DEPRESSION`, 12 `CHECK_RANGE`, geri kalanı kabul; burun 1,7°'den fazla aşağı eğikken 11°'lik gövde yönü dünyada 12,7°'yi geçip mesafe 40 m'nin altına düştü. Hepsi bozukken kabul edilen mesaj (hedef 33–40 m önde) drone'u ileri götürdü, burun eğildi, sonraki mesajlar da kabul edildi: Hold yoluna girmedi.
- **Kontrolün kendisi doğru çalışıyor:** iki logda `ufuk`/`uzak` mesajlarının **400'ünün 400'ünde** sonuç, o anki dünya açısına ve mesafeye göre beklenenle aynı (aşağı bakış < 10° → `CHECK_DEPRESSION`; değilse mesafe > 40 m → `CHECK_RANGE`; değilse kabul). Yani menzil ve açı kontrolleri spec Bölüm 2–3'teki gibi dünya ekseninde, eşikte birebir çalışıyor; açık çevrimde gövdeye sabit yönle bu iki kontrolü drone'u eğmeden ayrı ayrı göstermek mümkün değil (8.4).

## 6. Sapmalar (planlanandan farklı yapılanlar)

1. **Bağlantı varsayılanı** `udpout:127.0.0.1:14540` → `udpin:0.0.0.0:14540` (Bölüm 2; kullanıcıya bildirilecek).
2. **Kalkış:** Position modunda, simüle joystick (`MANUAL_CONTROL`) ile. Plandan sapma **yok**; Takeoff modu kullanılmadı. İrtifa 10 m yerine 9,88–9,94 m (elle kalkış), beklenen sayılar ölçülen h ile hesaplandı.
3. **QGC yerine** QGC'nin gönderdiği komut (`MAV_CMD_DO_SET_MODE`, 1/4/11) script'ten gönderildi. QGC ekranındaki liste ve mesaj kullanıcıya kaldı.
4. **RC anahtarı** için bir oturumda parametreler değiştirildi (`COM_RC_IN_MODE` 0, `RC_*`, `COM_FLTMODE1/6`); o oturum sonunda parametre dosyası silindi, diğer oturumları etkilemedi.
5. **Ek oturum S5b** (`ufuk`, `uzak`, temel LOS 30°): S5'teki `uzak` sonucu açık çevrim eğim etkisiyle karıştığı için.
6. **Ölçüm** kalıcı analiz script'iyle değil, pyulog 1.2.4'ün Python arayüzüyle geçici script'lerle yapıldı (kalıcı script Grup 6, `tez/analiz/af_log_analiz.py`). Test akışını yöneten "pilot" script'i de geçicidir, repoya girmedi (yalnızca `af_los_gonder.py` ve dokümanlar bu grubun dosyaları).
7. Senaryo süreleri: S1a–S3 12 s; S4/S5 her giriş 26,5 s.

## 7. Çıkan sorunlar ve çözümleri

1. **Pilot script'i kapanınca drone RTL'e geçti** (ilk oturum, testler bittikten sonra). Joystick ve GCS bağlantısı kesilince PX4 "Manual control lost" → 5 s sonra RTL → iniş → disarm (Position modu RC ister). Log ölçülen kısımda etkilenmedi. Çözüm: sonraki oturumlarda pilot kapanmadan önce `logger stop`.
2. **Arm ve geçiş reddinde ACK okuması.** Yerde arm'lıyken AUTO FOLLOW isteğine PX4 **iki** ACK gönderdi: önce `ACCEPTED`, 4 ms sonra commander'ın asıl cevabı `TEMPORARILY_REJECTED` (`vehicle_command_ack`, t = 21,204 ve 21,208). Pilot script'i ilk ACK'i okuduğu için ekranda "kabul" yazdı; asıl sonuç logdan ve mod hiç değişmediğinden doğrulandı. İlk ACK'in kaynağı araştırılmadı (PX4 davranışı, bizim kodla ilgisi yok).
3. **RC ilk denemede çalışmadı** (`20_52_31.ulg`): `RC_CHAN_CNT` = 0 iken PX4 RC'yi "kalibre değil" sayıyor (`rc_update.cpp:152, 681`), arm reddedildi. `RC_CHAN_CNT` = 8 ile yeni oturumda (`20_55_24.ulg`) çalıştı.
4. `commander check` konsola yalnızca `Preflight check: FAILED` yazıyor; ret nedeni olaylarla (events) gidiyor. Neden `health_report` ve `failsafe_flags` topic'lerinden okundu.
5. Kapalı çevrim göndericisi, önceki gönderici durduktan 0,5 s geçmeden başlayınca ilk 6 mesajı `CHECK_SEQ` ile atıldı (sıra no 1'den başlıyor, önceki numara henüz unutulmadı). Karar 5b-a'nın beklenen davranışı; script'ler arasında ≥1 s beklenerek çözüldü.
6. Mod kapandıktan sonra (Position'da frenlerken burun kalkınca) açık çevrim mesajları `CHECK_DEPRESSION`/`CHECK_RANGE` ile atıldı. PASIF'te, etkisi yok.

## 8. Gözlemler (spec'in söylemediği; karar verilmedi, kullanıcıya sunulur)

1. **Açık çevrimde gövdeye sabit LOS ↔ eğim etkileşimi (S1a, S1b, S5).** Hız değişince eğim değişiyor, eğim ölçülen mesafeyi değiştiriyor, mesafe hızı değiştiriyor. S1b'de bu, ~0,6 s periyotlu sürekli bir salınım yaptı (hız −1,3…−1,9 m/s, eğim −0,6…+2,7°); S1a'da kırpma döngüyü kesti. Gerçek uçuşta kamera hedefin görüntüde eğimle kaydığını görür ve FC tutumla geri çevirir; etki yalnızca tutumun zamanlaması tutmazsa (V3: varış anındaki tutum, ~60 ms gecikme telafisiz) kalıntı olarak görülebilir. **m13 / V3 (gecikme telafisi) için not.**
2. **S3'te drone kendi etrafında dönmeye başladı** (ortalama 65°/s). Hedef 1,6–3,9 m yakında ve gövdeye bağlı; yaw isteği hedefi kovaladıkça hedef de dönüyor. Açık çevrime özgü, ama gerçek uçuşta da hedef neredeyse altındayken yaw çok duyarlı olacak (1 m yatay hata, 3 m'de ~18°). `AF_YAW_MIN_D` = 1 m bu durum için küçük olabilir. **Açık soru (9.2).**
3. **S5 `sira`, uzun bölüm:** sıra no sürekli aynı gelirse (ör. Pi'nin işlem hattı donup son mesajı tekrar tekrar yollarsa) Karar 5b-a gereği önceki numara 0,5 s sonra unutuluyor ve bir mesaj kabul ediliyor → her 0,5 s'de bir geçerli mesaj, durum TAKIP ↔ KAYIP_BEKLE; **Hold'a hiç gidilmiyor.** Spec S5 "uzun süren bozuk veri hedef kaybı yoluna girer" diyor; bu türde girmiyor. Kod spec'in Karar 5b-a cümlesine birebir uyuyor; iki spec cümlesi bu durumda çelişiyor. **Açık soru (9.1).**
4. **S5 `ufuk`/`uzak`:** açı ve menzil kontrolleri dünya ekseninde yapılıyor (spec Bölüm 3, doğru); açık çevrimde gövdeye sabit yön drone eğildikçe eşiği geçiyor. Kontrolün eşikte doğru karar verdiği 400 mesajda doğrulandı; "uzun bozuk veri → Hold" yolu bu iki türde açık çevrimde gösterilemedi (S5b'de `ufuk` gösterildi). Kapalı çevrimde (Grup 6) hedef uzağa konarak denenebilir.
5. **Yaw dönüş hızı:** sınır PX4'ün `MC_YAWRATE_MAX`'ı (200°/s); otomatik modların `MPC_YAWRAUTO_MAX`'ı bizim setpoint'imize uygulanmıyor (FlightTask çalışmıyor). Moda girişte hedef 90° yandaysa drone yarım saniyede döner. **Açık soru (9.3).**
6. **Mesajlarda mod adı:** yerde arm'lıyken geçiş reddinin STATUSTEXT'i `Switching to External 1 is currently not available` (PX4 dış modlara sabit ad veriyor, `mode_util::nav_state_names`); "AUTO FOLLOW" yazmıyor. Bu modda arm reddinin STATUSTEXT'i genel (`Resolve system health failures first`); asıl neden ("Mode not suitable for arming", `modeCheck.cpp:203`) olay (event) olarak gidiyor. QGC'nin bunları nasıl gösterdiği headless görülemedi; **kullanıcı QGC'de bakacak.**
7. Bilgi: AUTO FOLLOW'a **disarm iken** girilip hedef yoksa durum yerde KAYIP_BEKLE → 1,5 s sonra HOLD_ISTENDI oluyor ve modül disarm araca setpoint yayınlıyor (zararsız, motorlar kapalı). Grup 5'te Hold isteği eklenince bu durumda yerde de Hold istenecek; Grup 5'te bakılacak.

## 9. Kullanıcıya sorulacaklar

1. **`sira` uzun bölüm (8.3):** sıra no sürekli aynı gelirse ne olsun? (a) Şimdiki gibi (Karar 5b-a): her 0,5 s'de bir mesaj kabul, Hold yok · (b) önceki numara daha geç unutulsun (ör. `AF_DATA_TOUT + AF_LOST_T` = 1,5 s; o zaman donmuş Pi 1,5 s'de Hold'a gider, yeniden başlayan Pi 1,5 s sonra kabul edilir) · (c) aynı numara hiç kabul edilmesin, yalnız açıkça küçük numara (Pi yeniden başladı) unutmayı tetiklesin (yeni eşik gerekir). Öneri yok; karar sizin (güvenlik ↔ kullanılabilirlik).
2. **`AF_YAW_MIN_D` (8.2):** 1 m, hedef neredeyse altındayken yaw'ı sakin tutmaya yetmeyebilir. Şimdilik değiştirilmedi; kapalı çevrimde (S6) ya da gerçek uçuşta bakılsın mı?
3. **Yaw hız sınırı (8.5):** PX4'ün 200°/s'si kalsın mı, yoksa bir sınır mı konsun (yeni parametre ya da `MC_YAWRATE_MAX` düşürülmesi)? Spec'te "kararlaştırılmadı" yazıyor.
4. **Test göndericisi bağlantı adresi:** `udpin:0.0.0.0:14540` (Bölüm 2) uygun mu?
5. **Pilot / analiz script'i:** Bu gruptaki test akışını (kalkış, mod değişimi, log kopyalama) yöneten script geçici tutuldu. Tekrarlanabilirlik için `tez/sitl/` altına alınsın mı? Alınacaksa adı sizin.

**Cevaplar (2026-11-11):**
1. Kullanıcı "biraz aç" dedi; örnekli anlatım verildi. Öneri: "önceki numara" yalnızca `AF_DATA_TOUT` boyunca hiç `AF_LOS` mesajı gelmezse unutulsun. **Cevap bekleniyor.**
2. `AF_YAW_MIN_D` 1 m kalır, S6–S7'de bakılır (**"okey"**).
3. **Ayrı yaw hız sınırı parametresi Grup 5'te eklenir** (kullanıcı: "sen şimdiden ekle, parametre dursun"); adı ve varsayılanı soruldu.
4. `udpin:0.0.0.0:14540` onaylandı (**"okey"**).
5. Script'ler **repoya girmez, kullanıcının bilgisayarında kalıcı durur** ("ileride repoya almaya bakarız"). Geçici klasör bilgisayar yeniden açılınca silinmişti; script'ler bu grubun ajan kayıtlarından geri çıkarıldı (pilot, senaryo, ön kontrol, analiz script'leri, `sitl.sh`, `run.sh`). Kalıcı yeri soruldu.
6. Grup 5'ten sonra hedefsiz girişte 1,5 s'de Hold (**"okey"**).

## 10. Kontroller (4.12)

| Kontrol | Sonuç |
|---|---|
| `tez/pin/verify_pin.sh --worktree` | Beklenen kırmızı: yine 15 dosya, hepsi onay bekleyen 7 yolda; yeni yol yok (`tez/sitl/` izinli `tez/*` içinde). `allowed-paths.txt`'e dokunulmadı |
| `make tests TESTFILTER=AutoFollowGuidance` | Geçti; test programı doğrudan: **9 testin 9'u** |
| `ruff format` + `ruff check` (`tez/sitl/af_los_gonder.py`) | Temiz |
| Modül kodu | Değişmedi → iki derleme ve flash kaydı tekrarlanmadı (flash Grup 2 düzeltme turundaki gibi: 1 936 260 B, %98,48) |
| Süreçler | Test sonunda hiç px4/gz süreci yok |

## 11. Sonraki grup için notlar

- Grup 5 (Hold): S4'ün aynı script'le (`--senaryo kes`, `--senaryo hedef-yok`, script'siz giriş) tekrarlanması yeterli; ölçüm son geçerli mesaj → `nav_state = 4`. Disarm iken hedefsiz girişteki HOLD_ISTENDI'ye (8.7) dikkat.
- Grup 6 (S6/S7): `--cevrim kapali` çalışıyor; hedefin yeri, hızı ve yolu kullanıcıya sorulacak (şimdilik burnun 20 m önü, duruyor).
- Analiz script'i için hazır ölçüler: girişteki düz değerler, kırpma sayısı, `vel_cmd` değişim hızı, durum geçiş süreleri (varıştan), hover'da tutulan noktaya uzaklık, `ufuk`/`uzak` için eşik tutarlılığı.
