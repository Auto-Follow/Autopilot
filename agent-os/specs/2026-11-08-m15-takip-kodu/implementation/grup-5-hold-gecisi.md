# Görev grubu 5: Hold geçişi, S4'ün tamamı, yaw hız sınırı, sıra no inceltmesi

- **Tarih:** 2026-11-11 · **Dal:** `ozellik/m15-takip-kodu` · **Görev listesi:** `../tasks.md` Grup 5 (5.1–5.3, 5.A, 5.B, 5.C, 5.4–5.11)
- **Durum:** Bitti. Modül artık hedef kaybında süre dolunca PX4'ten **Hold** istiyor; S4'ün dört varyantı Hold dahil, Hold'dan sonra yeniden giriş (RC anahtarı ve komutla), donmuş Pi ve S2 (yaw hızı) Gazebo'da uçuldu ve ULog'dan sayıyla ölçüldü. Bütün beklenen değerler görüldü. Kullanıcıya 3 soru ve 2 bilgi notu var (Bölüm 8).
- Bu not kod okumadan anlaşılacak şekilde yazıldı. Adların anlamı `../log-sozlugu.md`'de. Bu grubun uygulama kararları ayrıca `../rapor.md` §5.1'de (G5.1–G5.12).

## 1. Ne yapıldı?

| # | Ne | Neden (kaynak) | Kullanıcı ne görür? |
|---|---|---|---|
| 5.1–5.3 | **Hold isteği:** durum HOLD_ISTENDI olunca modül PX4'e "Hold moduna geç" komutu gönderir. PX4 kabul edince drone Hold'a geçer, modül PASIF olur ve setpoint göndermeyi bırakır; takibe **kendiliğinden dönmez**. PX4 reddederse drone yerinde beklemeye devam eder, istek **1 s arayla en fazla 3 kez** gönderilir; üçüncü de kabul edilmezse QGC'ye **bir kez** uyarı düşer, drone yine yerinde bekler, pilot devralır. Modül kendi başına RTL, iniş ya da başka bir mod istemez | spec Bölüm 7 (Karar D, C2), Karar 2026-11-10 ("tamam") | QGC'de mod "Hold" olur. Logda `hold_request_count` = 1, `vehicle_command` ve `vehicle_status.nav_state` = 4 |
| 5.A | **EKF yön sıfırlamasında tutulan yaw kaydırılır:** PX4'ün yön tahmini bir anda düzeltilirse (`heading_reset_counter` değişir), modülün tuttuğu yaw da aynı açı (`delta_heading`) kadar kaydırılır | Karar D5-a (2026-11-10); PX4 kalıbı `MulticopterPositionControl.cpp:709-711` | Drone gereksiz yere dönmez. Logda `yaw_cmd` sıçrama kadar değişir |
| 5.B | **Sıra no "önceki numara" yalnızca tam sessizlikte unutulur:** `AF_DATA_TOUT` (0,5 s) boyunca **hiç `AF_LOS` adlı mesaj gelmezse** unutulur (sonraki kontrollerde atılan mesaj da sessizliği bozar). Eskiden "sıra kontrolünü geçen mesaj gelmezse" unutuluyordu | Karar 1a (2026-11-11) | Donmuş Pi aynı mesajı tekrarlarsa hepsi atılır → 0,5 s'de yerinde bekleme, 1,5 s'de Hold. Yeniden başlayan Pi (sustuktan sonra 1'den sayar) yine kabul edilir |
| 5.C | **Yeni parametre `AF_YAWRATE_MAX`** (varsayılan 60°/s, 5–200°/s, QGC grubu `AUTO FOLLOW`): burun yönü isteği her çevrimde en fazla `AF_YAWRATE_MAX × geçen süre` kadar değişir, kısa yoldan (±180°'yi geçerek) | Karar 2026-11-11 ("AF_YAWRATE_MAX 60"); kanıt `MPC_YAWRAUTO_MAX` = 60°/s (`multicopter_autonomous_params.c:148`) | Drone en fazla 60°/s döner (önce PX4'ün 200°/s'si). Yeni log alanı yok; `yaw_cmd` sınırlanmış değeri gösterir |
| 5.4 | İki derleme, flash kaydı, birim testi | tasks 5.4 | Bölüm 7 |
| 5.5–5.7 | SITL: S4 tam, Hold sonrası yeniden giriş, donmuş Pi, S2 tekrarı, disarm iken hedefsiz giriş | tasks 5.5–5.7, 5.B, 5.C, Grup 4 notu 8.7 | Bölüm 4 |

| Dosya | Ne değişti |
|---|---|
| `src/modules/auto_follow/AutoFollow.cpp`, `AutoFollow.hpp` | Hold isteği (`vehicle_command` yayını, `vehicle_command_ack` okuma, tekrar, QGC uyarısı), yaw sınırının uygulanması, yön sıfırlamasında yaw kaydırma, sıra no zamanının ad kontrolüne bağlanması, `AF_YAWRATE_MAX` |
| `src/modules/auto_follow/AutoFollowGuidance.cpp`, `.hpp` | Yeni saf fonksiyonlar: `limit_yaw_change` (yaw sınırı), `hold_action` (Hold tekrar kuralı); `keep_previous_seq`'in açıklaması yeni kurala göre |
| `src/modules/auto_follow/AutoFollowGuidanceTest.cpp` | 3 yeni test (Bölüm 3) |
| `src/modules/auto_follow/module.yaml` | `AF_YAWRATE_MAX` |
| `log-sozlugu.md`, `spec.md`, `rapor.md`, `tasks.md`, bu not | Dokümanlar |

`tez/pin/allowed-paths.txt`'e dokunulmadı. Onay bekleyen 7 yol dışında PX4 dosyası değişmedi (`msg/`, `logged_topics.cpp`, `rc.mc_apps`, kart dosyaları bu grupta hiç değişmedi). Hiçbir `.ulg` dosyası repoya girmedi. SITL test yardımcıları repoda değil, `~/m15-sitl-araclari/`'da (kullanıcı kararı U4.19).

## 2. Nasıl çalışıyor? (sade anlatım)

### 2.1 Hold isteği

1. KAYIP_BEKLE'de `AF_LOST_T` dolunca durum HOLD_ISTENDI olur (Grup 2'den beri böyle). **O çevrimde** modül PX4'ün komut kanalına (`vehicle_command`) "mod numarası 4'e (Hold) geç" komutunu yazar (`VEHICLE_CMD_SET_NAV_STATE`, `param1` = 4). Komutun hedefi ve göndereni, PX4'ün kendi kimliği (`vehicle_status.system_id` / `component_id`, SITL'de 1/1). PX4'ün içindeki navigator modülü de komutlarını böyle gönderir (`navigator_main.cpp:1404-1409`).
2. PX4'ün commander'ı bu komutu, pilot QGC'den mod seçmiş gibi işler. **Doğrulandı (spec'teki "(doğrulanacak)"):** commander komutu gönderenin bileşen numarası 1000'den küçükse isteği "User" (kullanıcı) sayar (`Commander.cpp:1559-1562`; sınır `COMPONENT_MODE_EXECUTOR_START` = 1000, `VehicleCommand.msg:198`). Bizimki 1 olduğu için "User". "User" olmanın tek farkı, varsa bir mode executor'dan kontrolü almasıdır (`ModeManagement.cpp:424-429`); bizde executor yok, yani PX4 bu Hold'u pilotun Hold'undan ayırmaz. SITL'de logdaki `vehicle_command` kaydında gönderen 1/1, `from_external` = 0 görüldü.
3. Commander her komuta cevap verir (`vehicle_command_ack`; cevap komutu gönderene adreslenir, `Commander.cpp:2673-2680`). Bu komut için yalnızca iki cevap var: kabul (`ACCEPTED`) ya da şimdilik ret (`TEMPORARILY_REJECTED`) (`Commander.cpp:936-944`). Modül cevapları her çevrimde okur ve yalnızca kendi Hold komutuna gelen cevaba bakar.
4. **Kabul:** commander modu Hold'a çevirir; bir sonraki çevrimde modül "mod artık benim değil" görür ve PASIF olur, setpoint yayını durur. Pilot modu yeniden açmadıkça modül hiçbir şey istemez.
5. **Ret ya da cevap yok:** drone yerinde beklemeye devam eder (KAYIP_BEKLE'deki tutma noktası). Önceki istekten 1 s sonra istek yeniden gönderilir. En fazla **3 istek**. Üçüncüsü de reddedilirse (ya da 1 s içinde cevap gelmezse) QGC'ye **bir kez** kritik uyarı düşer (metin **geçici**, Bölüm 8 soru 1: `AUTO FOLLOW: Hold rejected, holding position`); aynı metin PX4 konsoluna ve ULog'un mesaj kısmına da yazılır. Durum HOLD_ISTENDI'de kalır, `hold_request_count` = 3; pilot RC ile devralır.
6. `hold_request_count` her HOLD_ISTENDI döneminin başında sıfırdan sayar; normal bir Hold'da 1 olur ve mod kapandıktan sonra da bir sonraki döneme kadar 1 görünür.

**Ne zaman reddedilir?** Hold, PX4'te çok kopterde küresel konum ve yerel konum ister (`mode_requirements.cpp:110-124`); bizim mod yalnızca yerel konum ister. Yani ör. GPS'in küresel konumu geçersizken ama yerel konum hâlâ geçerliyken ret mümkündür. Disarm iken PX4 her mod geçişine izin verir (`UserModeIntention.cpp:54-55`), yani masada ret olmaz.

### 2.2 Yaw hız sınırı (`AF_YAWRATE_MAX`)

Her çevrimde (50 Hz, ~20 ms) guidance "hedefe bakmak için burun şu açıda olmalı" der. Yeni kuralla komut edilen yaw bu açıya **en fazla 60°/s × 0,02 s = 1,2°** yaklaşır; fark ±180°'ye sarılarak kısa yol seçilir (ör. 179,5°'den −179°'ye 1,5°'lik yoldan, 358,5°'lik yoldan değil). Moda girişte başlangıç drone'un o anki yönüdür (Grup 2'den beri). KAYIP_BEKLE ve HOLD_ISTENDI'de yaw zaten sabit tutulur; sınır yalnızca TAKIP'te devrededir. Hedef `AF_YAW_MIN_D`'den yakınsa (yaw donuk) değişiklik zaten 0'dır.

PX4'ün kendi sınırı `MC_YAWRATE_MAX` (200°/s) yine geçerlidir; yani `AF_YAWRATE_MAX` 200'e yaklaştırılırsa asıl sınır o olur.

### 2.3 Sıra no kuralı (karar 1a)

"Önceki numara", adı `AF_LOS` olan bir mesaj geldikçe **canlı tutulur**. Ad kontrolünü geçen her mesaj (sonra NaN, norm, sıra, yaş vb. yüzünden atılsa bile) "Pi konuşuyor" sayılır. Yalnızca 0,5 s boyunca hiç `AF_LOS` gelmezse unutulur ve bir sonraki mesaj sıra karşılaştırmasına girmez.

- **Donmuş Pi** (işlem hattı takılır, son mesajı aynı sıra no ile tekrar tekrar yollar): mesajlar gelmeye devam ettiği için önceki numara unutulmaz, tekrarların hepsi `CHECK_SEQ` ile atılır → geçerli veri yok → 0,5 s'de KAYIP_BEKLE, 1,5 s'de Hold. Eski kuralda her 0,5 s'de bir mesaj kabul ediliyor ve Hold'a hiç gidilmiyordu (Grup 4, S5 `sira`).
- **Yeniden başlayan Pi:** yeniden başlarken saniyelerce susar, önceki numara unutulur, 1'den başlayan mesajlar kabul edilir.
- Değişmeyen: önceki numarayı değiştiren mesajlar yine 1–4. kontrolleri geçenlerdir (karar 5a).

### 2.4 EKF yön sıfırlaması (karar D5-a)

PX4'ün yön tahmini bazen bir anda düzeltilir (ör. pusula ya da GPS yön kaynağı değişince). PX4 bu sıçramayı `delta_heading` ile bildirir ve kendi setpoint'ini bir kez kaydırır (`MulticopterPositionControl.cpp:709-711`). Modül her çevrimde yeniden setpoint yayınladığı için kendi tuttuğu yaw'ı da aynı açı kadar kaydırır; yoksa bir sonraki çevrimde eski sayıyı yeniden ister ve drone gereksiz döner. Konum ve irtifa sıfırlamasındaki kaydırmanın (karar 4) yanına eklendi. **SITL'de denenmedi** (Gazebo'da kendiliğinden yön sıfırlaması olmadı); kalıp PX4'ünkiyle aynı **(doğrulanacak)**.

## 3. Birim testi (`make tests TESTFILTER=AutoFollowGuidance`)

**12 testin 12'si geçti** (önceki 9 + 3 yeni). Yeni testler:

| Test | Ne verildi | Beklenen | Sonuç |
|---|---|---|---|
| `FrozenSenderNeverAccepted` (5.B) | Donmuş Pi: aynı mesaj (sıra no 5) 3 s boyunca 20 Hz; sonra 0,5 s sessizlik ve sıra no 1 | Yalnızca ilk mesaj kabul, sonraki 59 tekrarın hepsi `CHECK_SEQ`; sessizlikten sonra sıra no 1 `CHECK_OK` | Geçti |
| `YawRateLimitPerCycle` (5.C) | 60°/s, bir çevrim 20 ms | sağdaki hedefe +1,2°, soldakine −1,2°; 179,5° → −179° kısa yoldan (−179,3°); küçük fark doğrudan; 50 çevrimde (1 s) 60°; önceki yaw yoksa hedef açı | Geçti |
| `HoldRequestRetries` (5.2) | Hold tekrar kuralı (`hold_action`) | ilk istek hemen; retten sonra 1 s dolmadan yeni istek yok, 1 s'de var; cevapsız istek de 1 s'de tekrar; 3. ret → uyarı bir kez, 4. istek yok; kabulden sonra hiçbir şey | Geçti |

Hold reddi SITL'de üretilemediği için (Bölüm 8, bilgi 2) ret yolu bu testle sınandı: tekrar kuralı modülden ayrı, zamanı argüman alan bir fonksiyona taşındı (spec Bölüm 11'deki "saf fonksiyon" ilkesi).

## 4. SITL sonuçları

**Oturum düzeni** Grup 4'teki gibi (`implementation/grup-4-sitl-acik-cevrim.md` Bölüm 3): her oturumdan önce ve sonra parametre dosyası silindi, `PX4_PARAM_AF_ENABLE=1 HEADLESS=1 make px4_sitl gz_x500`, Position'da kalkış (simüle joystick), havada AUTO FOLLOW (`MAV_CMD_DO_SET_MODE` 1/4/11, QGC'nin gönderdiği komut), oturum sonunda pilot kapanmadan `logger stop`, süreçler PID ile kapatıldı. `AF_K_FF` = 0, **`AF_LOST_T` = 1,0 s**, `AF_DATA_TOUT` = 0,5 s, **`AF_YAWRATE_MAX` = 60°/s** (varsayılanlar; her oturumun başında `param show` ile görüldü). İrtifa elle kalkış yüzünden 9,6–10,0 m. Araçlar: `~/m15-sitl-araclari/` (`run.sh`, `senaryo.py`, yeni `hold_yeniden_giris.py`, `hold_disarm.py`, `analiz_hold.py`, `analiz_s2.py`; `BENIOKU.md`).

Süreler mesajların Pixhawk'a **varış** anından ölçüldü; "t" = PX4 açılışından beri geçen süre (ULog zamanı). Loglar `~/Desktop/AUTO-FOLLOW LOG/`'da, özgün adlarıyla (PX4 UTC saatiyle adlandırır; tarih 2026-11-11).

**Son kodla koşulan oturumlar** (bu grubun sonuçları bunlardır):

| ULog | Oturum |
|---|---|
| `19_18_27.ulg` | S4 tam (a, b, c, d) |
| `19_20_46.ulg` | Donmuş Pi (`--senaryo sira`) → Hold |
| `19_22_03.ulg` | Hold'dan sonra yeniden giriş: RC anahtarı ve komut (5.6) |
| `19_23_53.ulg` | Disarm iken, yerde hedefsiz giriş (Grup 4 notu 8.7) |
| `19_25_29.ulg` | S2 tekrarı (yaw hızı) |

İlk koşular (`19_09_04.ulg` S2, `19_10_27.ulg` S4, `19_13_40.ulg` donmuş Pi, `19_15_43.ulg` yeniden giriş) Hold tekrar kuralı saf fonksiyona taşınmadan önceki kodla yapıldı; sonuçları son koşularla aynıydı (farklar 10–20 ms, çevrim sınırı). Taşımadan sonra Hold içeren üç oturum ve S2 son kodla yeniden koşuldu.

### 4.1 S4 tam — `19_18_27.ulg` — **Geçti**

Temel LOS S1b'ninki (drone ~1,5 m/s geri uçarken kayıp başlar). Script: `--senaryo kes` (10 s'de 1,0 s, 20 s'de 3,0 s gönderim yok), `--senaryo hedef-yok` (10 s'de 0,5 s, 20 s'de 3,0 s `data[5] = 0`), sonra script'siz giriş.

| Varyant | Ne verildi | Drone ne yaptı | Ölçülen | Beklenen | Sonuç |
|---|---|---|---|---|---|
| (a) uzun kesinti | Gönderim 3,0 s kesildi | Yavaşlayıp yerinde bekledi, sonra Hold'a geçti; veri dönünce Hold'da kaldı | Son geçerli mesaj t = 54,716 → KAYIP_BEKLE 55,224 (**+0,508 s**) → HOLD_ISTENDI ve Hold isteği 56,224 (**+1,508 s**) → PX4 kabul 56,232 → `nav_state = 4` **56,244 (+1,528 s)**. Veri 57,768'de döndü; Hold'da kaldı (Position'a script geçirene kadar, 61,812) | 0,5 s + 1,0 s ≈ 1,5 s; Hold'dan sonra takibe dönülmez | Geçti |
| (b) kısa kesinti | Gönderim 1,0 s kesildi | Yarım saniye yavaşladı, takibe kendiliğinden döndü | Son mesaj 44,716 → KAYIP_BEKLE 45,224 (+0,508 s) → veri 45,768'de döndü → TAKIP 45,784. Bu sürede Hold isteği **yok** | 1,0 s dolmadan dönünce takip sürer, Hold yok | Geçti |
| (c) hedef yok | `data[5] = 0`: kısa 0,5 s, uzun 3,0 s | Kısa olanda yarım saniye bekleyip takibe döndü; uzun olanda bekleyip Hold'a geçti | Kısa: ilk "hedef yok" 76,768 → KAYIP_BEKLE 76,784 (bir çevrim) → TAKIP 77,284. Uzun: ilk "hedef yok" 86,768 → KAYIP_BEKLE 86,784 → HOLD_ISTENDI ve istek 87,784 (**+1,016 s**) → `nav_state = 4` **87,804 (+1,036 s)** | hemen bekleme, 1,0 s sonra Hold | Geçti |
| (d) hedefsiz giriş | Script çalışmıyor (son mesaj 3,6 s önce) | Yerinde bekledi, Hold'a geçti; 4 s sonra veri başlayınca Hold'da kaldı | Giriş 100,944 → aynı çevrimde KAYIP_BEKLE → HOLD_ISTENDI ve istek 102,444 (**girişten 1,500 s**) → `nav_state = 4` **102,468 (+1,524 s)** | girişten 1,5 s sonra Hold | Geçti |

- **Hold isteği** (`vehicle_command`, her üç Hold'da): komut `SET_NAV_STATE` (100001), `param1` = 4, gönderen ve hedef 1/1, `from_external` = 0 → commander'a göre **"User"** (5.1 doğrulaması). PX4'ün cevabı (`vehicle_command_ack`) her seferinde **ACCEPTED** (sonuç 0), istekten 8–12 ms sonra. İstekten `nav_state = 4`'e **20–24 ms**. `hold_request_count` her Hold'da 1 (tekrar gerekmedi).
- **Hold'dan sonra:** modül bir çevrim sonra PASIF (`mode_active` = 0, `state` = 0); setpoint yayını durdu. Üç Hold'da da mod kendiliğinden geri açılmadı (sonraki mod değişikliği hep script'in Position komutu).
- **Bekleme kalitesi** (KAYIP_BEKLE, Hold'dan önce): `trajectory_setpoint` yatay hızı 0, tutulan nokta sabit; drone 1,48–1,51 m/s'den 1 s'de 0,21–0,24 m/s'ye yavaşladı, tutulan noktaya en çok 0,59–0,69 m uzaklaştı (fren payı); (d)'de zaten duruyordu (0,03 m).
- **Hold'da drone:** PX4'ün Hold'u geçiş anındaki yeri tuttu: başlangıçta 0,24–0,25 m/s, sonunda 0,02–0,03 m/s; giriş noktasına en çok 0,23–0,26 m ((d)'de 0,03 m); irtifa 9,91–9,95 m.
- "Son geçerli → `nav_state = 4`" süresinin 1,5 s'den fazlası = mesajın varışından sonraki çevrim sınırı (≤ 20 ms) + commander'ın işlemesi (~20 ms).

### 4.2 Hold'dan sonra yeniden giriş (5.6) — `19_22_03.ulg` — **Geçti**

RC anahtarı Grup 4'teki gibi verildi: `RC_CHANNELS_OVERRIDE`, `COM_RC_IN_MODE` = 0, `RC_CHAN_CNT` = 8, `RC_MAP_ROLL/PITCH/THROTTLE/YAW` = 1/2/3/4, `RC_MAP_FLTMODE` = 5, `COM_FLTMODE1` = 2 (Position), `COM_FLTMODE6` = 100 (AUTO FOLLOW). Kalkış RC ile Position'da.

| Adım | Ne verildi | Drone / PX4 ne yaptı | Ölçülen | Beklenen | Sonuç |
|---|---|---|---|---|---|
| 1 | Anahtar 6. konuma (t = 37,756), veri yok | AUTO FOLLOW (37,780), yerinde bekledi, Hold'a geçti | `nav_state = 4` **39,304** (girişten 1,516 s) | girişten 1,5 s sonra Hold | Geçti |
| 2 | Anahtar 6'da **bırakıldı**; geçerli veri başladı (ilk kabul 39,708) | Hold'da kaldı | 5,9 s boyunca Hold (anahtar 45,180'de değişene kadar) | Anahtarı yerinde bırakmak yetmez (`ManualControl.cpp:176-177`), kendiliğinden dönüş yok | Geçti |
| 3 | Anahtar 1. konuma (45,180) → Position (45,196); sonra yine 6'ya (47,668) | AUTO FOLLOW'a döndü ve takibe başladı | `nav_state = 23` 47,692; TAKIP 47,708 | aç-kapa ile yeniden giriş | Geçti |
| 4 | Gönderim durduruldu (son geçerli 51,608) | Bekledi, yine Hold | `nav_state = 4` **53,128** (+1,520 s) | 1,5 s | Geçti |
| 5 | Veri yeniden başladı, anahtar hâlâ 6'da; QGC'nin komutu (`DO_SET_MODE` 1/4/11) | Komutla AUTO FOLLOW'a döndü ve takibe başladı | Komuttan önce 4 s Hold'da (veri geçerliyken); `nav_state = 23` 57,148, TAKIP 57,168 | QGC'den tek tıkla yeniden giriş | Geçti |
| 6 | Anahtar 1. konuma (60,228) | Position | 60,244 | — | — |

### 4.3 Donmuş Pi (`--senaryo sira`) → Hold — `19_20_46.ulg` — **Geçti**

- **Verilen:** `--senaryo sira`: 10–20 s her 5. mesaj bozuk (sırayla son geçerli sıra no'nun tekrarı ve 10 geri), 20–23 s **bütün mesajlar aynı sıra no** (399; donmuş Pi), sonra normal.
- **Drone ne yaptı:** araya karışık bölümde takibi bozulmadan sürdürdü; donmuş bölümde yavaşlayıp bekledi ve Hold'a geçti.

| Bölüm | Ölçülen | Beklenen | Grup 4'te (eski kural) |
|---|---|---|---|
| Araya karışık (10–19 s) | 146 kabul, 37 `CHECK_SEQ`; durum hep TAKIP | atılır, sayaç artar, drone etkilenmez | aynı |
| Donmuş (20 s'den) | 30 mesajın **30'u** `CHECK_SEQ` (`los_seq` hep 399), kabul 0. Son geçerli 54,660 → KAYIP_BEKLE 55,176 (+0,516 s) → HOLD_ISTENDI ve istek 56,176 (+1,516 s) → ACCEPTED 56,188 → `nav_state = 4` **56,200 (+1,540 s)**; Hold'da kaldı (Position komutu 61,912) | 0,5 s'de bekleme, 1,5 s'de Hold (karar 1a) | Her 0,5 s'de bir mesaj kabul, TAKIP ↔ KAYIP_BEKLE, Hold yok |

### 4.4 S2 tekrarı (yaw hızı) — `19_25_29.ulg` — **Geçti**

- **Verilen:** `--los 0 0.8 0.6` (hedef sağda), 12 s, `AF_YAWRATE_MAX` = 60°/s.
- **Drone ne yaptı:** yerinde sağa döndü ve dönmeyi sürdürdü (açık çevrimde beklenen, B3), Grup 4'tekinden yaklaşık üç kat yavaş.

| Ölçüm | Beklenen | Ölçülen | Grup 4 (sınır yokken, `21_00_19.ulg`) |
|---|---|---|---|
| Komut edilen yaw'ın (`yaw_cmd`) değişim hızı | ≈ 60°/s | **her çevrimde 60,00°/s** (12,02 s'de 721,2°) | — |
| Drone'un dönüş hızı (girişten 2 s sonra) | ≈ 60°/s | ortalama **59,9°/s**, en çok 65,6°/s | ortalama 192°/s, en çok 206°/s |
| Burun yönünün komutun gerisinde kalması | — | ortalama 22°, en çok 28° | — |
| Dönüş yönü | sağa | sağa (+699,9°) | sağa |
| İrtifa | sabit | 9,94–9,96 m | — |

Not: drone'un yönü komutun ~22° gerisinden gelir; PX4'ün tutum kontrolcüsü yaw'ı birinci dereceden izler (60°/s'de ~0,37 s gecikme). Açık çevrimde hedef gövdeye bağlı olduğu için guidance'ın istediği açı komutun hep ~69° önünde kalır ve sınır her çevrimde devrededir. Kapalı çevrimde (S6) dönüş hedefe ulaşınca durur.

### 4.5 Disarm iken, yerde hedefsiz giriş — `19_23_53.ulg` — bilgi (Grup 4 notu 8.7)

- **Verilen:** yerde, disarm; AUTO FOLLOW komutu (t = 12,624), script yok. 3 s sonra arm komutu, 2 s sonra disarm.
- **PX4 ne yaptı:** KAYIP_BEKLE → HOLD_ISTENDI 14,136 (girişten 1,512 s) → Hold isteği → `nav_state = 4` 14,148. Disarm iken PX4 her geçişe izin verir (`UserModeIntention.cpp:54-55`). **Hold'da arm kabul edildi** (15,648): Hold, PX4'te arm'ı engelleyen modlardan değil (`mode_requirements.cpp:110-124`; engelleyenler ör. RTL, Land, Follow Me, `:141-202`). Drone yerde kaldı (`landed` log boyunca 1; PX4'ün Hold'u yerdeyken boşta bekler, `loiter.cpp:93-94`). Kullanıcı kararı U4.20 ("masa testinde hedefsiz girişte 1,5 s sonra Hold") ile uyumlu; yan etkisi Bölüm 8 soru 2'de.

## 5. Sapmalar (planlanandan farklı yapılanlar)

1. **Hold tekrar kuralı saf fonksiyona taşındı** (`hold_action`) ve birim testi eklendi. tasks 5.2'de birim testi istenmiyordu; ret yolu SITL'de üretilemediği için eklendi (Bölüm 3). Taşımadan sonra Hold içeren oturumlar yeniden koşuldu.
2. **Cevap gelmezse de tekrar:** tasks 5.2 "ret gelirse tekrar" diyor; kod, 1 s içinde cevap gelmezse de tekrarlıyor (G5.3). Commander her komuta cevap verdiği için pratikte fark yok; cevap kaybolursa drone sonsuza dek HOLD_ISTENDI'de beklemesin diye.
3. **Ek oturum:** disarm iken hedefsiz giriş (4.5), Grup 4 notunun "Grup 5'te bakılacak" maddesi için.
4. **Test yardımcılarında değişiklik** (repoda değil, `~/m15-sitl-araclari/`): `run.sh` artık var olan aynı adlı logun üstüne yazmıyor ve `AD.py` varsa onu çalıştırıyor; `senaryo.py`'ye `S5sira` eklendi; yeni `hold_yeniden_giris.py`, `hold_disarm.py`, `analiz_hold.py`, `analiz_s2.py`. `BENIOKU.md` güncellendi.

## 6. Çıkan sorunlar ve çözümleri

1. **Geri çıkarılan script'ler ilk çalıştırmada sorunsuz çalıştı** (`sitl.sh`, `pilot.py`, `senaryo.py`, `run.sh`, `analiz_s1.py`, `analiz_s4.py`, `ulog_load.py`); düzeltme gerekmedi. RC anahtarı kurulumu `onkontrol_rc.py`'deki sırayla yeni script'e alındı ve ilk denemede çalıştı.
2. **Üç oturumu tek komutla art arda koşarken kabuk öldürüldü** (çıkış kodu 144). `sitl.sh stop` süreçleri `pgrep -f "[g]z sim"` gibi kalıplarla buluyor; aynı komut satırında bu metni içeren bir kontrol (`pgrep -af "px4|gz sim"`) olduğu için kalıp benim kabuğumu da eşledi (Grup 1'deki sorun 15'in aynısı). İlk oturum (S4) bitmiş ve logu kopyalanmıştı; diğer ikisi ayrı ayrı koşuldu. Kontrol bundan sonra `sitl.sh status` ve `pgrep -x px4` ile yapıldı. Dosya ya da log kaybı yok.
3. **Hold reddi SITL'de üretilemedi.** Hold küresel konum ister, bizim mod yerel konum; Gazebo'da ikisini ayırmanın (küresel geçersiz, yerel geçerli) kilitli dosyaya dokunmadan basit bir yolu bulunmadı (GPS kesilince EKF ikisini birlikte bir süre tutar, sonra ikisini birlikte kaybeder; `COM_POS_FS_EPH` ikisini birlikte etkiler). Ret yolu birim testiyle sınandı (Bölüm 3); gerçek kartta ya da m16'da görülecek **(doğrulanacak)**.

## 7. Kontroller

| Kontrol | Sonuç |
|---|---|
| `make tests TESTFILTER=AutoFollowGuidance` | Geçti; test programı doğrudan: **12 testin 12'si** |
| `make px4_sitl` | Geçti, uyarı yok |
| `make px4_fmu-v6c_default` | Geçti, uyarı yok. **FLASH 1 937 252 B / 1920 KB (%98,53)**, boş 28 828 B; Grup 2 düzeltme turuna göre (1 936 260 B) **+992 B** |
| `tez/pin/verify_pin.sh --worktree` | Beklenen kırmızı: yine **15 dosya, hepsi onay bekleyen 7 yolda**; yeni yol yok. `allowed-paths.txt`'e dokunulmadı |
| Süreçler | Her oturumdan sonra ve en sonda px4/gz süreci yok (`sitl.sh status`, `pgrep -x px4`); parametre dosyası silinmiş |
| `make check_format` | Çalıştırılmadı (astyle `VERSIONS.md`'de yok, tasks "Bütün gruplar için" kuralı); kod PX4 stiline elle uyduruldu (tab, 140 karakter) |

## 8. Kullanıcıya sorulacaklar

**Soru 1 — Hold 3 kez kabul edilmezse QGC'ye düşen uyarının metni (geçici olarak yazıldı).** Karar "QGC'ye uyarı düşer" diyor, metni söylemiyor.
- (a) Şimdiki geçici metin: `AUTO FOLLOW: Hold rejected, holding position` (İngilizce, PX4'ün diğer mesajları gibi; QGC'de kritik uyarı + konsol + ULog mesajı). Artı: kısa, kod hazır. Eksi: Türkçe değil.
- (b) Başka bir metin (sizin vereceğiniz; metin en fazla 50 karakter, `MAVLINK_LOG_MAXLEN`, `src/lib/systemlib/mavlink_log.h:50`; şimdiki 44 karakter).
- (c) (a) + PX4'ün "event" (olay) sistemiyle de gönderilsin (commander'ın kendi mesajları böyle, ör. `Commander.cpp:2624-2632`). Artı: QGC'nin yeni sürümleri olay listesini daha iyi gösterir. Eksi: flash artar (~%98,5 dolu), olay tanımı gerekir.
- **Öneri: (a).**

**Soru 2 — Disarm iken hedefsiz girişte modül Hold'a geçiriyor; Hold'da arm serbest (4.5).** "Bu modda arm yasak" kuralı (C1) AUTO FOLLOW için geçerli; modül 1,5 s sonra Hold'a geçirince kullanıcı yerde arm edebiliyor (drone kalkmıyor, boşta bekliyor).
- (a) Böyle kalsın. Artı: U4.20 kararıyla aynı; PX4'ün Hold'u yerde kalkış yapmaz (`loiter.cpp:93-94`), yerde Hold'u pilot da seçebilir; kod değişmez. Eksi: masa testinde mod kendi kendine Hold'a döner.
- (b) Disarm iken Hold istenmesin (durum HOLD_ISTENDI'de kalır, mod AUTO FOLLOW'da kalır, arm yasağı sürer). Artı: masada mod değişmez. Eksi: masa testinde "Hold isteği"nin kendisi görülemez (A3 masada Hold isteğini gözlemeyi istiyor); küçük kod.
- (c) Yerdeyken (`landed`) Hold istenmesin. (b) ile benzer; arm'lı yerdeki durumu da kapsar.
- **Öneri: (a)** (A3 ve U4.20 ile tutarlı; risk yok).

**Soru 3 — EKF yön sıfırlamasında filtre de sıfırlansın mı?** Karar D5-a yalnızca tutulan yaw'ı kaydırıyor (uygulandı). Konum sıfırlamasında filtre zaten sıfırlanıyor (spec Bölüm 4, sayaçlar `VehicleLocalPosition.msg:21, 23`); yön sıfırlamasında sıfırlanmıyor. Yön sıçrayınca LOS'u dünyaya çeviren tutum da sıçrar, bir sonraki ölçülen hedef konumu kayar ve filtre bunu "hedef hareket etti" sanar (hız kestirimi bir an bozulur).
- (a) Böyle kalsın (spec'in yazdığı). Artı: kod değişmez; `AF_K_FF` = 0 iken hız kestirimi kullanılmıyor. Eksi: S7'de (`AF_K_FF` > 0) yön sıfırlaması olursa kısa bir hız sıçraması olabilir.
- (b) Yön sıfırlamasında filtre de sıfırlansın (bir satır; konum sıfırlamasıyla aynı davranış: sonraki ölçüm konumu kurar, hız 0'dan başlar). Artı: eski yönle hesaplanmış kestirim kullanılmaz. Eksi: sıfırlamadan sonra hedef hızı birkaç ölçüm boyunca 0'dan toplanır.
- **Öneri: (b)** (konum sıfırlamasıyla tutarlı; maliyet bir satır). Seçilmezse (a) kalır.

**Bilgi 1 — Yaw sınırının görünür etkisi:** 60°/s'de drone'un yönü komutun ~22° gerisinden gelir (PX4'ün tutum kontrolcüsü). Hedef 90° yandayken moda girilirse dönüş ~1,5 s sürer (önce ~0,5 s). Değer QGC'den değiştirilebilir.

**Bilgi 2 — Hold reddi yolu yalnızca birim testinde sınandı** (Bölüm 6 sorun 3). Gerçek uçuşta en olası nedeni GPS'in küresel konumunun bozulup yerel konumun sürmesi; böyle bir durumda drone AUTO FOLLOW'da yerinde bekler ve 3 istekten sonra QGC uyarısı düşer. İlk uçuş testlerinde pilot bunu bilmeli.

## 9. Sonraki grup için notlar

- Grup 6 (S6/S7): yaw artık 60°/s ile sınırlı; S6'da burnun hedefe dönüş süresi buna göre beklenmeli. `AF_YAW_MIN_D` (1 m) S6–S7'de bakılacak (U4.17).
- Grup 6 kalıcı analiz script'i (`tez/analiz/af_log_analiz.py`) için hazır ölçüler: `analiz_hold.py`'deki "son geçerli / ilk hedef-yok / giriş → istek → `nav_state = 4`" süreleri ve Hold'daki drone davranışı; `analiz_s2.py`'deki yaw komutu ve dönüş hızı.
- Soru 3 (b) seçilirse değişiklik bir satır; derleme ve birim testi tekrarlanır.
