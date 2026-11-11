# Görev listesi: AUTO FOLLOW (M15), body FRD LOS'tan PX4 setpoint'ine takip modu

- **Görev:** https://github.com/Auto-Follow/Auto-Follow/issues/6 · yol haritası m15 · son teslim **2026-11-15**
- **Repo / dal:** Autopilot (PX4 v1.17.0, kilitli) · `ozellik/m15-takip-kodu` · spec klasörü `agent-os/specs/2026-11-08-m15-takip-kodu/`
- **Kaynaklar:** `spec.md` (ana belge, 2026-11-10 son hali), `planning/requirements.md` (§3.12 testler, §3.14 write-spec kararları), `log-sozlugu.md` (bütün adlar), `planning/visuals/01-ust-seviye-akis.md`, `planning/visuals/02-px4-detayli-akis.md`. Gerekçeler: `planning/karar-gunlugu.md` (KG, son kayıt geçerli).
- **Bu liste yeni karar içermez.** Adlar yalnızca `spec.md` ve `log-sozlugu.md`'den alındı. Bu dosyalarda olmayan bir ad gerekirse **"(ad kullanıcıya sorulacak)"**, kaynakta kanıtlanamayan bir şey **"(doğrulanacak)"** diye işaretlendi.
- Görev grupları `spec.md` "Uygulama sırası" (Karar 14.5) ile birebir aynıdır; başa takım işleri için **Görev grubu 0** eklendi.

## Genel bakış

Toplam: 7 görev grubu (0–6), 89 alt görev (0: 6 · 1: 14 · 2: 23, geri dönüş 2.LF dahil · 3: 6 · 4: 14 · 5: 14, 2026-11-11 eklenen 5.A–5.C dahil · 6: 12). 2026-11-10: log mesajı Grup 6'dan Grup 2'ye taşındı (kullanıcı "1-a").

| Grup | Ne | Kim | Bağımlılık |
|---|---|---|---|
| 0 | Ön koşullar: Hüseyin onayı (7 kilitli yol), Vision ile `AF_LOS` anlaşması, açık adlar | Kullanıcı / ekip (kod yok) | Yok |
| 1 | İskelet: mod kaydı, arming check, açılışta başlatma, 50 Hz çevrim, parametreler, iki derleme ve flash kaydı | PX4 C++ | 0 (onay gelmeden `verify-pin` kırmızı kalır) |
| 2 | Guidance + alpha-beta + log mesajı: doğrulama, geometri, filtre, yasa ve sınırlar, yaw/irtifa, setpoint, `auto_follow_status` | PX4 C++ | 1 (log yolları Grup 0 onayına bağlı) |
| 3 | Kısa birim testi `AutoFollowGuidanceTest.cpp` | PX4 C++ (GoogleTest) | 2 |
| 4 | SITL: test göndericisi, ön kontroller, S1a, S1b, S2, S3, S4 (yalnız KAYIP_BEKLE), S5 | Python + SITL | 3 |
| 5 | Hold geçişi ve S4'ün tamamı | PX4 C++ + SITL | 4 |
| 6 | Analiz script'i, S6–S7 (kapalı çevrim), kapanış | Python + SITL | 5 |

## Bütün gruplar için geçerli kurallar

Bunlar her grupta ayrıca görev olarak da yazıldı; burada nedenleri toplu duruyor.

- **Kilitli yollar:** Ajan `tez/pin/allowed-paths.txt`'i **asla düzenlemez** (spec "Kilitli yollar ve flash"). PX4 ağacında yalnızca spec'teki 7 yol değişir. Başka bir PX4 dosyasına dokunmak gerekirse **durulur ve kullanıcıya / Hüseyin'e sorulur**.
- **`verify_pin` beklentisi:** Hüseyin'in onayı gelip liste ayrı bir PR'la güncellenene kadar `tez/pin/verify_pin.sh --worktree` 7 yolu "izinsiz" diye gösterecektir (spec:314, "Kilit listesi onayı gelmeden `verify-pin` kırmızı kalır"). Kontrol şudur: **listede bu 7 yoldan başka yol çıkmamalı.** Başka yol çıkarsa commit atılmaz, kullanıcıya bildirilir.
- **Flash:** Pixhawk 6C ~%98 dolu (~40 KB boş, `../agent-os/product/tech-stack.md:43`). Kod küçük tutulur: `double` yok, dinamik bellek (`new`, `malloc`, büyüyen `std::vector`) yok, büyük tablo yok (`../agent-os/standards/px4/modules.md:10`, `../agent-os/standards/global/error-handling.md:7`). Kod değiştiren her grupta `make px4_fmu-v6c_default` çıktısındaki flash kullanımı spec'e ve rapora yazılır. **`region FLASH overflowed` görülürse durulur, Hüseyin'e ve kullanıcıya haber verilir; başka modül kapatılarak yer açılmaz** (o iş m14). Spec'teki önceden kararlaştırılmış geri dönüş (Karar 13: `AF_GND_OFS` çıkarılır) kullanıcıyla birlikte değerlendirilir.
- **Commit:** Her grup sonunda, kontroller geçince, yalnızca o grubun dosyaları **adıyla** eklenir (`git add -A` / `git add .` yok). Mesaj: `2026-11-08-m15-takip-kodu: Görev grubu <N> — <ne yapıldı>`. **Push, amend, rebase, `reset --hard` yok.** Commit'ten önce dal kontrol edilir (`ozellik/m15-takip-kodu` olmalı, `main` değil) ve `git rev-parse --show-toplevel` ile Autopilot reposunda olunduğu doğrulanır.
- **Doküman koddan geri kalmaz** (spec Bölüm 12): her grup sonunda
  - `rapor.md` güncellenir ("Belge geçmişi"ne yeni sürüm satırı),
  - spec klasörüne kod okumadan anlaşılacak bir **görev grubu notu** yazılır: ne yapıldı, neden (spec bölümü / karar numarası), nasıl test edildi, hangi sorunlar çıktı ve nasıl çözüldü. Notlar **`implementation/`** klasörüne, grubun içeriğini anlatan adlarla yazılır (Karar 2026-11-10; SITL sonuç kayıtları da aynı notlara girer): `grup-0-on-kosullar.md`, `grup-1-iskelet-mod-kaydi.md`, `grup-2-guidance-filtre-log.md`, `grup-3-birim-testi.md`, `grup-4-sitl-acik-cevrim.md`, `grup-5-hold-gecisi.md`, `grup-6-kapali-cevrim-analiz.md`.
  - Yeni bir ad (değişken dışında, kullanıcının göreceği her şey) gerekiyorsa `log-sozlugu.md` **kodla aynı commit'te** güncellenir (Karar C3).
  - İş sırasında yeni bir karar gerekirse kullanıcıya seçenek + kanıt + öneri olarak sunulur; cevap `planning/karar-gunlugu.md` ve `planning/requirements.md`'ye yazılır.
- **Kod biçimi:** PX4 stili (`../agent-os/standards/global/coding-style.md`): tab girinti, 140 karakter, `make check_format` / `make format`. Python script'leri: `ruff format` + `ruff check` (ruff 0.16.9, `tez/env/analiz-requirements.txt:18`), tip ipuçları, herkese açık fonksiyonlarda docstring. Not: makinede astyle 3.1 kurulu ama `tez/env/VERSIONS.md`'de yazılı değil; `make check_format` kullanmadan önce kullanıcıya sorulur (çatı kural 4) **(doğrulanacak)**.
- **Yetişmeyen işler** `planning/requirements.md` §1.3 "m16'ya kalanlar" listesine yazılır.

---

## Görev listesi

### Takım işleri

#### Görev grubu 0: Ön koşullar (kod yok; kullanıcı ve ekip)

**Bağımlılık:** Yok. Diğer grupların başlamasını engellemez; ama onay gelmeden `verify-pin` kırmızı kalır ve Grup 6'nın log mesajı yolu bu onaya bağlıdır.

- **Ne:** Kilitli yolların onayı, Vision ile girdi mesajının anlaşması ve uygulama sırasında gerekecek ama henüz verilmemiş adların sorulması.
- **Neden:** PX4 v1.17.0 kilitli; izin listesine ekleme yalnızca repo sorumlusunun onayıyla, ayrı ve açık bir PR'la yapılır (çatı `CLAUDE.md` kural 1, `Autopilot/CLAUDE.md`, spec "Kilitli yollar ve flash", A7). Girdi biçimi bir varsayımdır (V2, A5).
- **Nasıl kontrol edilir:** Hüseyin'in cevabı ve Vision'ın cevabı `planning/karar-gunlugu.md`'ye yazılmış olur.

- [ ] 0.0 Ön koşulları tamamla
  - [ ] 0.1 Hüseyin'e **tek talep** olarak şu **7 yolun** `tez/pin/allowed-paths.txt`'e eklenmesi iletilir (kullanıcı iletir; ajan listeyi düzenlemez). Tablo `spec.md` "Kilitli yollar ve flash"tan aynen:

    | Yol | Neden |
    |---|---|
    | `src/modules/auto_follow/` | Yeni modül (`AutoFollow.cpp/.hpp`, `AutoFollowGuidance.cpp/.hpp`, `AlphaBetaFilter.hpp`, `AutoFollowGuidanceTest.cpp`, `CMakeLists.txt`, `Kconfig`, `module.yaml`) |
    | `boards/px4/sitl/default.px4board` | `CONFIG_MODULES_AUTO_FOLLOW=y` |
    | `boards/px4/fmu-v6c/default.px4board` | `CONFIG_MODULES_AUTO_FOLLOW=y` |
    | `msg/AutoFollowStatus.msg` | Log mesajı |
    | `msg/CMakeLists.txt` | Mesaj listesine bir satır (`msg_files`, `msg/CMakeLists.txt:39`) |
    | `src/modules/logger/logged_topics.cpp` | `auto_follow_status`'u her zaman kaydeden `add_topic` satırı |
    | `ROMFS/px4fmu_common/init.d/rc.mc_apps` | Açılışta `auto_follow start` satırı (Karar B2-b) |

    Talepte iki geri dönüş de yazılır: log yolları (`msg/AutoFollowStatus.msg`, `msg/CMakeLists.txt`, `logged_topics.cpp`) reddedilirse `debug_array` + sözlük; `rc.mc_apps` reddedilirse A8-(a): SITL'de `pxh>`'tan `auto_follow start`, 6C'de SD karttaki `etc/extras.txt`.
  - [ ] 0.2 Hüseyin'in cevabı karar günlüğüne yazılır. Onay gelince listeye ekleme **Hüseyin'in açacağı ayrı PR**'dır; bu dal o PR'ı beklemeden çalışmaya devam eder.
  - [ ] 0.3 Vision (Yusuf Ortatepe) ile `AF_LOS` anlaşması (A5, V2, V6): yerleşim `data[0..2]` LOS x/y/z (body FRD), `data[3]` yaş [ms], `data[4]` sıra no, `data[5]` hedef var (1) / yok (0); `name = "AF_LOS"`; sıra no float geldiği için 2²⁴ sınırı (spec:136); eksen yönleri ve işaretleri m10 ile (V6, **Açık**). MAVLink 2 Vision tarafından doğrulandı (B1), yeniden sorulmaz.
  - [ ] 0.4 Ahmet Kazalcı'dan kamera eğimi (A6): gelene kadar SITL'de `AF_TRK_ANG` = 30°. Gelmezse iş durmaz.
  - [ ] 0.5 Uygulamada gerekecek, kaynaklarda olmayan şu adlar ve değerler kullanıcıya **tek tek** sorulur ve karar günlüğüne yazılır:
    - ~~görev grubu notlarının yeri~~ → karar verildi (yukarıdaki "Bütün gruplar için geçerli kurallar"),
    - `tez/sitl/af_los_gonder.py` ve `tez/analiz/af_log_analiz.py`'nin komut satırı seçeneklerinin adları **(ad kullanıcıya sorulacak)** (ilgili grupta da sorulabilir),
    - açık çevrim testlerde script'in gönderim hızı (Pi 10–30 Hz bekleniyor, V2) ve gönderilecek yaş değeri **(değer kullanıcıya sorulacak)**.
  - [ ] 0.6 Cevaplar `planning/karar-gunlugu.md`'ye (ve karar niteliğindeyse `planning/requirements.md`'ye) yazılır; değişen dosyalar adıyla commit edilir: `2026-11-08-m15-takip-kodu: Görev grubu 0 — ön koşul cevapları`.

**Kabul kriterleri:**
- Talep Hüseyin'e 7 yol olarak iletildi; cevap (ya da "beklemede") karar günlüğünde.
- `tez/pin/allowed-paths.txt` bu dalda **değişmedi**.
- Vision'a yerleşim soruldu; cevap ya da "beklemede" karar günlüğünde.

---

### PX4 modülü

#### Görev grubu 1: İskelet (mod kaydı, arming check, açılışta başlatma, 50 Hz, parametreler)

**Bağımlılık:** Grup 0'daki talep iletilmiş olmalı (onay beklenmez; `verify-pin` kırmızı kalır).

- **Ne:** `src/modules/auto_follow/` klasöründe, kendini PX4'e **external mode** olarak kaydettiren, açılışta (yalnızca `AF_ENABLE` = 1 ise) başlayan, 50 Hz dönen ve bütün `AF_*` parametrelerini tanımlayan en küçük modül. Henüz guidance yok.
- **Neden:** Spec Bölüm 1 (Karar 2-a, 3-a, 3.1-ii), B2-b, A13, A14, C1, A1, A2; Bölüm 10 (parametreler). Kayıt yalnızca disarm iken kabul edildiği için modül arm'dan önce başlamalıdır.
- **Nasıl kontrol edilir:** `make px4_sitl` ve `make px4_fmu-v6c_default` derlenir, 6C flash kullanımı yazılır; kısa bir SITL açılışında modülün başladığı ve modun kaydolduğu görülür.

- [x] 1.0 İskeleti tamamla
  - [x] 1.1 Modül dosyaları oluşturulur: `AutoFollow.cpp`, `AutoFollow.hpp`, `CMakeLists.txt` (`MODULE_CONFIG module.yaml`), `Kconfig` (`CONFIG_MODULES_AUTO_FOLLOW`), `module.yaml`. Yazım deseni `ModuleBase` + `ModuleParams` + `px4::ScheduledWorkItem` (`src/examples/work_item/WorkItemExample.hpp:55`). `print_usage()` modülün ne yaptığını ve `start` / `stop` / `status` komutlarını anlatır (`../agent-os/standards/px4/modules.md`).
  - [x] 1.2 İş kuyruğu `nav_and_controllers` (`mc_nn_control.cpp:65`); `ScheduleOnInterval` ile **sabit 50 Hz** (20 ms; parametre değil, Karar). Döngü süresi için `perf_counter` (`WorkItemExample.hpp:86-87`).
  - [x] 1.3 `Run()` sırası `mc_nn_control` kalıbıyla (`mc_nn_control.cpp:436-477`): çıkış kontrolü → kayıt isteği → cevabın beklenmesi → arming check isteğine cevap → `nav_state == mode_nav_state` kapısı. Kayıt isteği adı **`AUTO FOLLOW`** (`RegisterExtComponentRequest`, ad `char[25]`, `msg/versioned/RegisterExtComponentRequest.msg:8`; kayıt `mc_nn_control.cpp:132-143`, cevap `:198-212`). `auto_follow stop` kaydı siler (`:146-155`).
  - [x] 1.4 Kayıt cevabı gelince kontrol modu yapılandırılır (`config_control_setpoints`, `mc_nn_control.cpp:158-172`). Bayraklar (A1, C1; `msg/versioned/VehicleControlMode.msg:8-19`): position, velocity, altitude, climb_rate, acceleration, attitude, rates, allocation, termination = **true**; manual, offboard = **false**; **`flag_control_auto_enabled = true`** (Karar A2: pilot çubuğu oynatınca Position'a geçilir, `Commander.cpp:2939-2960`). Not: `planning/visuals/02-px4-detayli-akis.md:114` hâlâ eski "auto = false" yazıyor; geçerli olan spec A2'dir.
  - [x] 1.5 Arming check cevabı (`mc_nn_control.cpp:175-195`; `msg/versioned/ArmingCheckReply.msg:31-41`):
    - `mode_req_angular_velocity`, `mode_req_attitude`, `mode_req_local_alt`, `mode_req_local_position` = true; `mode_req_global_position`, `mode_req_home_position`, `mode_req_mission`, `mode_req_manual_control` = false (A1).
    - **`mode_req_prevent_arming = true`** (C1: bu modda arm yasak; disarm iken moda geçiş serbest, `UserModeIntention.cpp:54-55`, `modeCheck.cpp:196-205`).
    - **`can_arm_and_run = !(vehicle_land_detected.landed && !mode_active)`** (Karar A14-a; `msg/VehicleLandDetected.msg:8`). Bunun için `vehicle_land_detected` ve `vehicle_status` okunur. Mod aktifken her zaman `true` kalır: `false` olursa PX4 Hold'a değil RTL'e düşer (`failsafe.cpp:698-702`, Karar 5-a).
  - [x] 1.6 `module.yaml`'a **16 parametrenin hepsi** `description`, `type`, `default`, `min`, `max`, `unit`, `decimal` ile yazılır (`../agent-os/standards/px4/uorb-params.md:10`). Değerler spec Bölüm 10 tablosundan aynen: `AF_ENABLE` (0, 0–1, değişince reboot), `AF_TRK_ANG` (30 deg, 5–85), `AF_K_DIST` (0.5 1/s, 0–2), `AF_K_FF` (0, 0–1.5), `AF_VEL_MAX` (2 m/s, 0.1–5), `AF_ACC_MAX` (3 m/s², 0.5–5), `AF_ALPHA` (0.5, 0–1), `AF_BETA` (0.17, 0–1), `AF_DATA_TOUT` (0.5 s, 0.1–5), `AF_LOST_T` (1.0 s, 0–30), `AF_YAW_MIN_D` (1 m, 0–10), `AF_TGT_HGT` (1.0 m, 0–2.5), `AF_GND_OFS` (0 m, −20–20), `AF_NORM_TOL` (0.1, 0.01–0.5), `AF_MIN_DEP` (10 deg, 1–60), `AF_MAX_RNG` (40 m, 1–200). Açılar QGC'de derece, kodda radyana çevrilir. Kodda `DEFINE_PARAMETERS`, `parameter_update` aboneliğiyle güncelleme.
  - [x] 1.7 `ROMFS/px4fmu_common/init.d/rc.mc_apps`'e başlatma satırı, `MC_NN_EN` kalıbıyla (`rc.mc_apps:40-43`): `if param compare -s AF_ENABLE 1` → `auto_follow start` (Karar B2-b, A13-b). Başka satıra dokunulmaz.
  - [x] 1.8 `CONFIG_MODULES_AUTO_FOLLOW=y` hem `boards/px4/sitl/default.px4board` hem `boards/px4/fmu-v6c/default.px4board`'a eklenir (Karar 3.1-ii).
  - [x] 1.9 Derleme: `make px4_sitl` uyarısız biter; `make px4_fmu-v6c_default` biter ve çıktıdaki **FLASH kullanımı** (kullanılan / toplam / yüzde) not edilir. `region FLASH overflowed` → durulur, Hüseyin'e ve kullanıcıya haber verilir, başka modül kapatılmaz.
  - [x] 1.10 Kısa SITL duman kontrolü (ayrıntılı ön kontroller Grup 4'te): parametre dosyası sıfırlanır (`build/px4_sitl_default/rootfs/parameters*.bson`), `PX4_PARAM_AF_ENABLE=1 HEADLESS=1 make px4_sitl gz_x500`; `pxh>`'ta `auto_follow status` modülün çalıştığını ve kayıt numarasını (23–30) gösterir; `work_queue status`'ta `nav_and_controllers` altında görünür. Ardından `PX4_PARAM_AF_ENABLE` verilmeden açılır: modül **başlamaz** (A13, varsayılan 0). Araç bu testte arm edilmez.
  - [x] 1.11 `tez/pin/verify_pin.sh --worktree`: yalnızca Grup 0'daki 7 yoldan bu grupta değişenler görünür; başka yol çıkmaz.
  - [x] 1.12 `log-sozlugu.md`'de bu grupta koda giren adlar (mod, modül ve komutları, `CONFIG_MODULES_AUTO_FOLLOW`, parametreler, `rc.mc_apps` satırı) "koddan doğrulandı" diye işaretlenir; fark varsa sözlük düzeltilir.
  - [x] 1.13 Flash kullanımı `spec.md` "Kilitli yollar ve flash" bölümüne ve `rapor.md`'ye yazılır; `rapor.md` "Belge geçmişi"ne yeni sürüm satırı; görev grubu notu (ne, neden, nasıl test edildi, sorunlar).
  - [x] 1.14 Commit (yalnızca bu grubun dosyaları, adıyla): `2026-11-08-m15-takip-kodu: Görev grubu 1 — iskelet, mod kaydı, arming check, açılışta başlatma`.

**Kabul kriterleri:**
- `make px4_sitl` ve `make px4_fmu-v6c_default` derleniyor; 6C flash kullanımı spec'te ve raporda yazılı.
- `AF_ENABLE` = 1 iken modül açılışta başlıyor ve mod 23–30 aralığından bir `nav_state` alıyor (`msg/versioned/VehicleStatus.msg:59-66`); `AF_ENABLE` = 0 iken başlamıyor.
- Arming check cevabı A1, C1, A14 ile birebir (`ArmingCheckReply.msg:31-41`, `mc_nn_control.cpp:185-193`); kontrol bayraklarında `flag_control_auto_enabled = true` (A2).
- `module.yaml`'da 16 parametre, spec Bölüm 10 değerleriyle, hepsinde min/max.
- Kodda `double` ve dinamik bellek yok.
- `verify_pin` yalnızca onay bekleyen yolları gösteriyor.

#### Görev grubu 2: Guidance + alpha-beta + log mesajı (doğrulama, geometri, filtre, yasa, yaw/irtifa, setpoint, `auto_follow_status`)

**Bağımlılık:** Grup 1. Log mesajı yolları Grup 0.2'deki onaya bağlı (onay beklenirken kod yazılır, `verify-pin` kırmızı kalır).

- **Ne:** `AutoFollowGuidance.cpp/.hpp` (ayrı kütüphane, adı `AutoFollowGuidance`) ve `AlphaBetaFilter.hpp`; modülün her çevrimde `debug_array`'i okuyup doğrulaması, hedefin yerini bulması, filtrelemesi, hız/yaw/irtifa isteğini hesaplaması ve mod aktifken `trajectory_setpoint` yayınlaması. Durum makinesi (PASIF / TAKIP / KAYIP_BEKLE / HOLD_ISTENDI) de burada yazılır; **Hold komutunun gönderilmesi Grup 5'tedir.**
- **Neden:** Spec Bölüm 2–8; Karar 6-a, 6.1, 6.3, 6.4, 7-a, C2, A3; "İç düzen" kararı (öneri kabul, 2026-11-10): doğrulama ve durum makinesi **zamanı argüman alan saf fonksiyonlar** olarak `AutoFollowGuidance` içinde, ki birim testiyle sınanabilsin.
- **Nasıl kontrol edilir:** İki derleme ve flash kaydı; hesapların doğruluğu Grup 3'te birim testiyle, uçuş davranışı Grup 4'te SITL'de.

- [x] 2.0 Guidance ve filtreyi tamamla
  - [x] 2.1 Kütüphane düzeni `mc_pos_control/PositionControl/` deseniyle: `px4_add_library` ile `AutoFollowGuidance` kütüphanesi, modül ona bağlanır (`PositionControl/CMakeLists.txt`). Kütüphane uORB ve parametre okumaz; değerleri argüman olarak alır.
  - [x] 2.2 Girdi okuma (spec Bölüm 2): her yeni `debug_array` örneği (`mavlink_receiver.cpp:2815-2832`; `timestamp` = FC'ye varış anı, `:2822`). Ham değerler (LOS, yaş, sıra no, bayrak, varış anı) doğrulamadan önce saklanır ve log mesajına kopyalanır (2.L4).
  - [x] 2.3 Doğrulama, **bu sırayla**, ilk geçilemeyen kontrol sonucu belirler (sonuç adları `log-sozlugu.md` Bölüm 6):
    1. ad `AF_LOS` mı → `CHECK_NAME` (ad en fazla 9 karakter, son bayt NUL; `DebugArray.msg:4`, `mavlink_receiver.cpp:2825`),
    2. altı değer sonlu mu (`PX4_ISFINITE`) → `CHECK_NONFINITE`,
    3. `| |LOS| − 1 | ≤ AF_NORM_TOL` → `CHECK_NORM`,
    4. sıra no öncekinden büyük mü → `CHECK_SEQ`,
    5. gerçek yaş `(şimdi − varış) + data[3]` < `AF_DATA_TOUT` → `CHECK_AGE`,
    6. hedef bayrağı 1 mi → `CHECK_NO_TARGET` (bozuk veri değil; sayılır ve KAYIP_BEKLE'yi hemen başlatır),
    7. yerel konum geçerli mi (`xy_valid`, `z_valid`, `VehicleLocalPosition.msg:9-10`) → `CHECK_POSITION`,
    8. aşağı bakış açısı ≥ `AF_MIN_DEP` → `CHECK_DEPRESSION` (geometri adımında),
    9. `0 < yatay mesafe ≤ AF_MAX_RNG` (ve `h > 0`) → `CHECK_RANGE` (geometri adımında).

    Geçen örnek `CHECK_OK`. Geçmeyen örnek atılır, nedene göre sayılır (`perf_counter` PC_COUNT, `perf_counter.h:49`, ve iç sayaçlar), **hız sınırlı** `PX4_WARN` ile yazılır, guidance'a asla girmez (`validation.md:7`, `error-handling.md:8`). Her çevrimde log basılmaz. *(Grup 2: sayaçlar log mesajında ve `auto_follow status`'ta; `perf_counter` adları kaynaklarda olmadığı için eklenmedi, kullanıcıya soruldu — `implementation/grup-2-guidance-filtre-log.md` Bölüm 7, soru 2. → Karar 2026-11-10, 2-a: `perf` sayacı eklenmez, spec cümlesi düzeltildi.)*
  - [x] 2.4 Geometri (spec Bölüm 3): `LOS_NED = R(q) · LOS_FRD`, `q` varış anındaki `vehicle_attitude.q` (V3; `matrix::Quatf::rotateVector`, `Quaternion.hpp:487`); `δ = asin(LOS_NED.z)`; `h = −vehicle_local_position.z − AF_GND_OFS − AF_TGT_HGT` (V4, V5); `d = h / tan(δ)`; `hedef_NED_xy = drone_xy + d · (LOS_NED_xy / |LOS_NED_xy|)`. Küresel koordinat yok. Tümü `float`.
  - [x] 2.5 `AlphaBetaFilter.hpp` (spec Bölüm 4, C2): yatayda (x, y); tahmin `x̂ ← x̂ + v̂·Δt` her 50 Hz çevrimde; düzeltme yalnızca kabul edilen ölçümde: `r = ölçüm − x̂`, `x̂ ← x̂ + α·r`, `v̂ ← v̂ + (β/Δt)·r` (`AF_ALPHA`, `AF_BETA`); Δt ölçümlerin tahmini çekim anları (`varış − yaş`) arasından; ilk ölçümde konum ölçüme, hız 0'a kurulur; EKF reset sayaçları (`VehicleLocalPosition.msg:21, 23`) değişirse filtre sıfırlanır. PX4'ün `TargetEstimator`'ı kullanılmaz.
  - [x] 2.6 Guidance yasası (spec Bölüm 5): `d_ist = h / tan(AF_TRK_ANG)`; `v_yasa = AF_K_FF · v̂_hedef + AF_K_DIST · (d_kest − d_ist) · û` (filtre çıktısıyla); sıra **yasa → kırpma (`|v| ≤ AF_VEL_MAX`) → ivme sınırı (çevrim başına en fazla `AF_ACC_MAX · Δt`)**. Moda girişte ivme sınırlayıcı drone'un o anki yatay hızından başlar. İvme sınırı için `SlewRate` (`SlewRate.hpp:79-87`) eksen bazlıdır; vektör büyüklüğüyle sınır gerekirse küçük bir yardımcı fonksiyon yazılır (spec "öneri"; fonksiyon adı sözlüğe girmez, kod içi addır).
  - [x] 2.7 Yaw ve irtifa (spec Bölüm 6): `yaw = atan2(Δy, Δx)` (drone → kestirilen hedef; `matrix::wrap_pi`, `helper_functions.hpp:98`); `d_kest < AF_YAW_MIN_D` ise son yaw tutulur; moda girişteki `vehicle_local_position.z` saklanır ve `position[2]` olarak tutulur. Yaw hız sınırı PX4'ündür (`MC_YAWRATE_MAX`, `mc_att_control_params.c:147`) **(doğrulanacak)**.
  - [x] 2.8 Durum makinesi (spec Bölüm 7, saf fonksiyon, zaman argümanla): durumlar `STATE_PASIF`, `STATE_TAKIP`, `STATE_KAYIP_BEKLE`, `STATE_HOLD_ISTENDI`. Geçişler: TAKIP → KAYIP_BEKLE (`AF_DATA_TOUT` boyunca geçerli veri yok **ya da** bayrak 0); KAYIP_BEKLE → TAKIP (`AF_LOST_T` dolmadan geçerli veri); KAYIP_BEKLE → HOLD_ISTENDI (`AF_LOST_T` doldu); herhangi biri → PASIF (`nav_state` artık bizim mod değil). Hedefsiz girişte (A3): zaman referansı `max(son geçerli mesaj, giriş anı)`, durum KAYIP_BEKLE, Hold zamanı giriş + `AF_DATA_TOUT` + `AF_LOST_T`. "Son geçerli" = 9 kontrolün hepsini geçen örnek. Hold'dan sonra takibe kendiliğinden dönülmez.
  - [x] 2.9 `trajectory_setpoint` (spec Bölüm 8), yalnızca mod aktifken, **her çevrimde**, `timestamp = hrt_absolute_time()`; kullanılmayan alanlar NaN (`TrajectorySetpoint.msg:11-17`):
    - TAKIP: `velocity[0..1] = v`, `position[2] = giriş irtifası`, `yaw = mutlak yaw`;
    - KAYIP_BEKLE / HOLD_ISTENDI: `position[0..2] = tutulan konum` (kayıp anındaki konum, giriş irtifası), `velocity[0..1] = 0`, `yaw = son yaw`;
    - moda girişte ilk çevrimde yayın yapılır (`MulticopterPositionControl.cpp:443-449`);
    - mod aktif değilken (PASIF) yayın yok; veri yine işlenir.

    Modül sorun anında susmaz, aktif hover yayınlar (standartla çelişki notu, `error-handling.md:4` ↔ `MulticopterPositionControl.cpp:438`; spec Bölüm 8 gerekçesi grup notuna da yazılır).
  - [x] 2.10 Yerel konum geçersizken (spec Bölüm 8, C2, A10): `position[0..1]` NaN, `velocity[0..1] = 0`; asıl tepki PX4'ün `mode_req_local_position` fallback'idir.
  - [x] 2.11 `auto_follow status` anlamlı durum basar: mod numarası, mod aktif mi, iç durum, son doğrulama sonucu ve nedene göre sayaçlar (konsoldan hızlı kontrol için).
  - **Log mesajı (Karar 2026-11-10, kullanıcı "1-a": Grup 6'dan buraya taşındı).** Neden: S1–S5 ölçümleri `auto_follow_status` alanlarına dayanıyor; mesaj erken gelirse açık çevrim testleri ilk seferde tam ölçülür ve tekrar koşulmaz. Log yolları Hüseyin'in onayına bağlı: onay → 2.L1–2.L6; ret → 2.LF.
  - [x] 2.L1 `msg/AutoFollowStatus.msg`: alanlar spec Bölüm 9 tablosundan **aynen** (ad, tip, birim yorumda; önek yok, C3): `timestamp`, `mode_nav_state`, `mode_active`, `state`, `los_timestamp`, `los_frd`, `los_age`, `los_seq`, `los_target`, `check_result`, `accept_count`, `reject_name_count`, `reject_nonfinite_count`, `reject_norm_count`, `reject_seq_count`, `reject_age_count`, `reject_position_count`, `reject_depression_count`, `reject_range_count`, `no_target_count`, `latency`, `los_ned`, `depression`, `height_diff`, `range_meas`, `target_meas_ned`, `target_est_ned`, `target_vel_ned`, `filter_updated`, `range_est`, `range_desired`, `vel_cmd_law`, `vel_cmd`, `yaw_cmd`, `yaw_frozen`, `alt_hold_z`, `time_since_valid`, `lost_time`, `hold_request_count`. Sabitler: `STATE_PASIF=0`, `STATE_TAKIP=1`, `STATE_KAYIP_BEKLE=2`, `STATE_HOLD_ISTENDI=3`; `CHECK_OK=0`, `CHECK_NAME`, `CHECK_NONFINITE`, `CHECK_NORM`, `CHECK_SEQ`, `CHECK_AGE`, `CHECK_NO_TARGET`, `CHECK_POSITION`, `CHECK_DEPRESSION`, `CHECK_RANGE` (sayısal değerler sözlükte "taslak 0–9", kodla kesinleşir).
  - [x] 2.L2 `msg/CMakeLists.txt`'e mesaj listesine bir satır (`msg_files`, `msg/CMakeLists.txt:39`).
  - [x] 2.L3 `src/modules/logger/logged_topics.cpp`'de varsayılan listeye (`add_default_topics`, `:46`) **aralıksız** bir `add_topic` satırı (her yayın, 50 Hz; C2). `logger_topics.txt` kullanılmaz (`logged_topics.cpp:531-540`). `SDLOG_MODE` değiştirilmez (Karar L3, A5).
  - [x] 2.L4 Modül mesajı **her çevrimde** doldurur ve yayınlar, mod kapalıyken (PASIF) de; `timestamp = hrt_absolute_time()`. Ham girdi doğrulamadan geçmese de `los_*` alanlarına yazılır; `mode_nav_state` kayıt yoksa 0.
  - [x] 2.L5 `log-sozlugu.md` **aynı commit'te**: her alan "koddan doğrulandı"; `CHECK_*` ve `STATE_*` sayısal değerleri koddakiyle eşitlenir; "hangi durumda ne değer" sütunundaki boşluklar doldurulur; `AUTO_FOLLOW_TARGET` uyarısı yerinde kalır; belge geçmişine yeni sürüm.
  - [x] 2.L6 Kısa doğrulama: yeni bir SITL logunda (kısa bir SITL açılışı, araç arm edilmeden) `auto_follow_status` alanlarının kendi adlarıyla göründüğü ve PASIF'te de yazıldığı görülür; `pxh>`'ta `listener auto_follow_status`.
  - [ ] 2.LF **Geri dönüş (yalnızca Hüseyin `msg/` ve `logged_topics.cpp` yollarını reddederse):** 2.L1–2.L3 yapılmaz; aynı değerler PX4'ün hazır `debug_array` mesajına konur ve `log-sozlugu.md` Bölüm 4'e "`data[i]` ↔ alan" eşleme tablosu eklenir; `af_log_analiz.py` adları bu tablodan verir. Bu yolda bilinen sorunlar **(doğrulanacak)** ve kullanıcıya sunulur:
    - `debug_array` girdiyle **aynı topic** ve kuyruğu tektir (spec Bölüm 2): modülün 50 Hz yayını gelen `AF_LOS` örneklerini ezebilir ve kendi mesajımız `CHECK_NAME` sayacını artırır;
    - ham `debug_array` yalnızca logger'ın debug profili açıkken loglanır (`logged_topics.cpp:289-294`);
    - durum mesajının `name` alanı **(ad kullanıcıya sorulacak)**; uint64 zaman alanları float32'ye sığmaz, 58 sayılık sınır.
  - [x] 2.12 Derleme: `make px4_sitl` ve `make px4_fmu-v6c_default`; flash kullanımı ve Grup 1'e göre artış not edilir. Taşma → durulur, Hüseyin'e ve kullanıcıya haber.
  - [x] 2.13 `tez/pin/verify_pin.sh --worktree`: yalnızca 7 yoldan değişenler.
  - [x] 2.14 `log-sozlugu.md`: durumlar ve `CHECK_*` sonuçlarının koddaki karşılığı "koddan doğrulandı" diye işaretlenir; "hangi durumda ne değer" sütununda kodla netleşenler doldurulur (aynı commit).
  - [x] 2.15 `rapor.md` (§4.5 "Her döngüde ne oluyor?" gerçekleşen hâliyle, flash satırı, belge geçmişi) ve görev grubu notu.
  - [x] 2.16 Commit: `2026-11-08-m15-takip-kodu: Görev grubu 2 — doğrulama, geometri, alpha-beta, guidance, setpoint, log mesajı`.
  - [x] 2.17 Düzeltme turu (Grup 2 sonrası kararlar, 2026-11-10): `AF_DATA_TOUT` boyunca geçerli veri yoksa filtre sıfırlanır (Karar 3); EKF konum sıfırlamasında tutulan nokta `delta_xy` / `delta_z` kadar kaydırılır (Karar 4); sıra no hafızası `AF_DATA_TOUT` sonra unutulur (Karar 5b-a); spec'teki `perf` cümlesi düzeltildi (Karar 2-a); 1-a, 5a, 6 kod değişikliği yok. 2 birim testi eklendi (toplam 9). Ayrıntı `implementation/grup-2-guidance-filtre-log.md` Bölüm 10.

**Kabul kriterleri:**
- Doğrulama sırası spec Bölüm 2'deki 9 adımla birebir; atılan örnek guidance'a girmiyor.
- Setpoint karışımı her durumda `PositionControl.cpp:224-250` kuralına uyuyor (her eksende konum/hız/ivmeden biri sonlu, x–y çiftleri birlikte).
- Mod aktif değilken `trajectory_setpoint` yayınlanmıyor; aktifken her çevrimde yayınlanıyor.
- İki derleme geçiyor; flash kaydı güncel. `double`, dinamik bellek yok.
- `auto_follow_status` her logda, her çevrimde (PASIF'te de), alanlar spec Bölüm 9 tablosundaki adlarla; `log-sozlugu.md` aynı commit'te güncel, `AUTO_FOLLOW_TARGET` uyarısı içinde.

#### Görev grubu 3: Kısa birim testi (`AutoFollowGuidanceTest.cpp`)

**Bağımlılık:** Grup 2.

- **Ne:** Bilgisayarda, drone'suz, saniyeler içinde biten **kısa** GoogleTest dosyası. Süre kısıtlı; yalnızca temel hesaplar (Karar 10.1).
- **Neden:** Spec Bölüm 11; `../agent-os/standards/testing/test-writing.md:6-10` (nominal, sınır, NaN/Inf, zaman aşımı).
- **Nasıl kontrol edilir:** `make tests TESTFILTER=AutoFollowGuidance` yeşil (`Makefile:406-407`). CI'da çalışmaz, yerelde koşulur; firmware'e girmez, flash'ı etkilemez.

- [x] 3.0 Birim testini tamamla
  - [x] 3.1 `AutoFollowGuidanceTest.cpp`, `px4_add_unit_gtest(SRC AutoFollowGuidanceTest.cpp LINKLIBS AutoFollowGuidance)` ile (`cmake/px4_add_gtest.cmake:40`). En fazla ~8 test:
    1. **Geometri:** drone 10 m, düz, burun kuzey, LOS (0.8, 0, 0.6), `AF_TGT_HGT` 1.0, `AF_GND_OFS` 0 → δ ≈ 36.9°, h = 9.0 m, **d = 12.0 m** (spec Bölüm 3 örneği).
    2. **Yasa:** aynı örnek, `AF_TRK_ANG` 30° → `d_ist` ≈ 15.6 m, `v` ≈ **−1.8 m/s** (hedeften uzaklaşma), kırpma yok.
    3. **Kırpma:** S1a geometrisi (LOS (0.951, 0, 0.309)) → yasa ≈ +6.0 m/s, çıkış `AF_VEL_MAX` = 2 m/s.
    4. **İvme sınırı:** bir çevrimde komut değişimi ≤ `AF_ACC_MAX · Δt`.
    5. **Bozuk veri:** NaN/Inf → `CHECK_NONFINITE`; norm dışı → `CHECK_NORM`; tekrar/geri sıra no → `CHECK_SEQ`; yanlış ad → `CHECK_NAME`.
    6. **Zaman aşımı:** son geçerli örnekten 0.5 s sonra KAYIP_BEKLE; +1.0 s sonra HOLD_ISTENDI.
    7. **Hedef yok:** bayrak 0 → hemen KAYIP_BEKLE.
  - [x] 3.2 `make tests TESTFILTER=AutoFollowGuidance` çalıştırılır; **yalnızca bu testler** koşulur, hepsi geçer. Hata çıkarsa düzeltme Grup 2 koduna yapılır ve hatanın nedeni grup notuna yazılır.
  - [x] 3.3 `make px4_sitl` hâlâ derleniyor (test dosyası firmware'i değiştirmez; 6C derlemesi bu grupta gerekmez, kod değişmediyse).
  - [x] 3.4 `tez/pin/verify_pin.sh --worktree`: yalnızca 7 yoldan değişenler.
  - [x] 3.5 `rapor.md` (§4.9 birim testi sonuçları, belge geçmişi) ve görev grubu notu: hangi testler, sonuçlar, çıkan sorunlar.
  - [x] 3.6 Commit: `2026-11-08-m15-takip-kodu: Görev grubu 3 — kısa birim testi`.

**Kabul kriterleri:**
- `make tests TESTFILTER=AutoFollowGuidance` yeşil; test sayısı ~8'i geçmiyor.
- Sayısal örnekler spec'le aynı: 12.0 m, −1.8 m/s, 2 m/s kırpma.
- Durum geçişleri 0.5 s, +1.0 s ve "hedef yok" için sınanmış.

---

### SITL testleri

#### Görev grubu 4: SITL ön kontroller + S1a, S1b, S2, S3, S4 (yalnız KAYIP_BEKLE), S5

**Bağımlılık:** Grup 3.

- **Ne:** Geçici test göndericisi `tez/sitl/af_los_gonder.py`'nin yazılması (açık ve kapalı çevrim) ve Gazebo Harmonic'te açık çevrim senaryoları. S4'ün Hold kısmı Grup 5'ten sonra (Karar A4).
- **Neden:** Spec Bölüm 11 (Karar 10.2, A1, A2, A12, B3); issue #6 kabul kriteri 3 ("ne verildi, drone ne yaptı, ULog adı").
- **Nasıl kontrol edilir:** Her senaryonun ULog'u `~/Desktop/AUTO-FOLLOW LOG/`'a kopyalanmış ve kaydı yazılmış; değerlendirme pyulog 1.2.4 ile (`tez/env/requirements-lock.txt:27`); göz kararı test sayılmaz.
- **Ölçüm kaynağı:** Log mesajı Grup 2'de geldiği için (Karar 2026-11-10, 1-a) S1–S5 ölçümleri spec Bölüm 11 tablosundaki `auto_follow_status` alanlarıyla yapılır (`range_meas`, `range_desired`, `vel_cmd_law`, `vel_cmd`, `yaw_cmd`, `yaw_frozen`, `state`, `time_since_valid`, `check_result`, `reject_*_count`…), ayrıca varsayılan loglanan PX4 topic'leriyle (`trajectory_setpoint`, `vehicle_status`, `vehicle_local_position`, `vehicle_attitude`; `logged_topics.cpp:131-150`).

- [x] 4.0 Açık çevrim SITL testlerini tamamla
  - [x] 4.1 `tez/sitl/af_los_gonder.py` (izinli yol; pymavlink 2.4.50, `tez/env/requirements-lock.txt:25`): Pi'nin `AF_LOS` mesajını spec Bölüm 2 yerleşimiyle `DEBUG_FLOAT_ARRAY` olarak **MAVLink 2** ile gönderir (`data` bir MAVLink 2 ek alanıdır, `common.xml:7630-7631`). SITL onboard bağlantısı UDP 14540/14580 (`px4-rc.mavlink:4-5, 26`). Sıra no her mesajda artar.
    - **Açık çevrim:** sabit LOS gönderir.
    - **Kapalı çevrim:** yerde hayali bir hedef tutar (duran ya da yürüyen), drone'un konumunu ve tutumunu MAVLink'ten okur, gerçek body FRD LOS'u hesaplar (hedefin bakılan noktası `AF_TGT_HGT` yüksekliğinde). Bu kip Grup 6'da (S6–S7) kullanılır, burada yalnızca çalıştığı görülür.
    - **Senaryo kipleri:** gönderimi kesme ve geri başlatma, `data[5] = 0`, hiç göndermeden başlama (S4); yanlış ad, NaN/Inf, norm dışı, tekrar/geri sıra no, yaş > 0.5 s, ufka yakın (δ < 10°), menzil > 40 m (S5).
    - Komut satırı seçeneklerinin adları **(ad kullanıcıya sorulacak)**; gönderim hızı ve yaş değeri **(değer kullanıcıya sorulacak)** (Grup 0.5).
    - `ruff format` + `ruff check`, tip ipuçları, docstring.
  - [x] 4.2 Her test oturumunun sabit adımları (her senaryo için tekrarlanır):
    1. Parametre dosyası sıfırlanır: `build/px4_sitl_default/rootfs/parameters*.bson` silinir (`test-writing.md:13-15`).
    2. `PX4_PARAM_AF_ENABLE=1 HEADLESS=1 make px4_sitl gz_x500` (HEADLESS mümkün değilse arayüzlü; nedeni nota yazılır).
    3. Açık çevrim senaryolarında `AF_K_FF` = 0 olduğu kontrol edilir (varsayılan; spec Bölüm 5).
    4. Drone **Position** modunda arm edilir ve 10 m'ye kaldırılır (AUTO FOLLOW'da kalkış yok ve arm yasak, C1/B4), sonra havada AUTO FOLLOW'a alınır.
    5. Test sonunda ULog (`build/px4_sitl_default/rootfs/log/<tarih>/<saat>.ulg`) **`~/Desktop/AUTO-FOLLOW LOG/`**'a kopyalanır (`SDLOG_DIRS_MAX` = 7, `init.d-posix/rcS:183`; loglar repoya girmez).
    6. Kayıt: **ne verildi, drone ne yaptı, ULog adı**, kullanılan `AF_*` değerleri (özellikle `AF_LOST_T`).
  - [x] 4.3 **Ön kontroller** (spec Bölüm 11, oturum başında): modül açılışta kendiliğinden başladı (B2) · QGC listesinde `AUTO FOLLOW`, `mode_nav_state` 23–30, `can_set_nav_states_mask`'ta bit (`VehicleStatus.msg:72`), yeniden başlatmada aynı numara · disarm iken moda geçiş kabul, bu modda arm reddedilir (C1) · yerde arm'lıyken moda geçiş engellenir ve QGC'de "Switching to … is currently not available" görülür (B4, A14; `Commander.cpp:2620-2638`) · QGC ve RC anahtarıyla giriş/çıkış; girişte ilk çevrimde setpoint, çıkışta setpoint durur · RC çubuğu oynayınca Position'a geçiş (A2; HEARTBEAT `base_mode` yan etkisi, `HEARTBEAT.hpp:98-100`). SITL'de RC anahtarı ve çubuğun nasıl verileceği **(doğrulanacak)**. "Hold'dan sonra anahtar aç-kapa ile yeniden giriş" Grup 5'te.
  - [x] 4.4 MAVLink 2 kontrolü: `pxh>`'ta `listener debug_array` ile gelen `data` değerlerinin sıfır olmadığı görülür (spec Bölüm 2 notu, B1).
  - [x] 4.5 **S1a Hedef uzakta:** LOS (0.951, 0, 0.309), δ ≈ 18° → d ≈ 27.7 m > 15.6 m → **ileri**; yasa ≈ +6.0 m/s, çıkış 2 m/s'de kırpılır, ivme ≤ 3 m/s². Ölçüm: `trajectory_setpoint` hız yönü ve büyüklüğü, `vehicle_local_position` hız.
  - [x] 4.6 **S1b Hedef yakında:** LOS (0.8, 0, 0.6), δ ≈ 36.9° → d = 12.0 m < 15.6 m → **geri** ~1.8 m/s, kırpma yok. Ölçüm aynı.
  - [x] 4.7 **S2 Hedef sağda:** LOS (0, 0.8, 0.6) → burun sağa döner; sabit body LOS yüzünden dönüş sürer (beklenen, B3). Yalnızca dönüş yönü kontrol edilir; yaw doğruluğu S6'da. Ölçüm: `trajectory_setpoint.yaw`, `vehicle_attitude` yönü.
  - [x] 4.8 **S3 Hedef neredeyse tam altta:** LOS (0.174, 0, 0.985), δ = 80° → d ≈ 1.6 m → geri; yasa ≈ −7.0 m/s, 2 m/s'de kırpılır; d > `AF_YAW_MIN_D` (1 m) olduğundan yaw donmaz. Ölçüm: `trajectory_setpoint` hız ve yaw.
  - [x] 4.9 **S4 (yalnız KAYIP_BEKLE kısmı, Karar A4):** (a) gönderim kesilir → 0.5 s sonra hover; (b) 1.0 s dolmadan gönderim geri gelir → takip kendiliğinden sürer; (c) `data[5] = 0` → hemen hover; (d) hedefsiz moda giriş → girişte hover. Bu grupta Hold komutu henüz olmadığından durum HOLD_ISTENDI'de kalır ve drone hover sürdürür; bu beklenen davranıştır ve kayda öyle yazılır. Ölçüm: `trajectory_setpoint` (hız 0, konum tutma), `auto_follow status` durumu.
  - [x] 4.10 **S5 Girdi doğrulama:** yanlış ad, NaN/Inf, norm dışı, tekrar/geri sıra no, yaş > 0.5 s, ufka yakın (δ < 10°), menzil > 40 m → her biri atılır, ilgili sayaç artar (`auto_follow status` ve `perf` çıktısı), drone etkilenmez (`trajectory_setpoint` hızı değişmez). Uzun süren bozuk veri hedef kaybı yoluna girer.
  - [x] 4.11 Değerlendirme: her ULog pyulog 1.2.4'ün kendi komutlarıyla (ör. `ulog2csv`) okunur; `auto_follow_status` alanları da dahil; senaryo başına sayısal sonuç (hız, yön, süre) kayda yazılır. Kesin başarı eşikleri m01'e aittir; şimdilik beklenen değerle karşılaştırma yazılır.
  - [x] 4.12 `tez/pin/verify_pin.sh --worktree`; `make tests TESTFILTER=AutoFollowGuidance` hâlâ yeşil. SITL'de kod hatası bulunup düzeltildiyse iki derleme ve flash kaydı tekrarlanır.
  - [x] 4.13 Sonuç kayıtları (`implementation/grup-4-sitl-acik-cevrim.md`), `rapor.md` (§4.9 test sonuçları tablosu, belge geçmişi) ve görev grubu notu (çıkan sorunlar ve çözümleri dahil).
  - [x] 4.14 Commit: `2026-11-08-m15-takip-kodu: Görev grubu 4 — test göndericisi, ön kontroller, S1–S5`.
  - Sonuç (2026-11-11): ön kontroller (QGC ekranı hariç, kullanıcı bakacak), S1a, S1b, S2, S3, S4 (KAYIP_BEKLE kısmı), S5 koşuldu ve ölçüldü; modül kodu değişmedi. Test göndericisinin bağlantı varsayılanı `udpin:0.0.0.0:14540` (PX4 14580'i dinler, 14540'a gönderir). Ayrıntı ve 5 açık soru: `implementation/grup-4-sitl-acik-cevrim.md`.

**Kabul kriterleri:**
- Ön kontrollerin hepsi (Hold'dan sonra yeniden giriş hariç) yapıldı ve sonucu yazıldı.
- S1a, S1b, S2, S3, S4 (KAYIP_BEKLE kısmı), S5 için **ne verildi, drone ne yaptı, ULog adı** yazılı; her ULog `~/Desktop/AUTO-FOLLOW LOG/`'da.
- Açık çevrim testlerde `AF_K_FF` = 0.
- Hiçbir log, video ya da `.ulg` dosyası repoya girmedi (çatı kural 9).

---

### Hold geçişi

#### Görev grubu 5: Hold geçişi (`VEHICLE_CMD_SET_NAV_STATE`) ve S4'ün tamamı

**Bağımlılık:** Grup 4.

- **Ne:** KAYIP_BEKLE'de `AF_LOST_T` dolunca PX4'ten Hold istenmesi; reddedilirse tekrar; ardından S4'ün dört varyantının Hold dahil tam testi.
- **Neden:** Spec Bölüm 7 (hedef kaybı D, kullanıcı "önemli" dedi; C2: Hold reddinde 1 s arayla en fazla 3 tekrar; A4).
- **Nasıl kontrol edilir:** S4'te son geçerli örnekten `nav_state = 4`'e kadar geçen süre ULog'dan ölçülür.

- [x] 5.0 Hold geçişini tamamla
  - [x] 5.1 HOLD_ISTENDI'ye geçişte `vehicle_command` yayınlanır: `command = VEHICLE_CMD_SET_NAV_STATE` (`msg/versioned/VehicleCommand.msg:114`), `param1 = NAVIGATION_STATE_AUTO_LOITER` (`VehicleStatus.msg:40`), hedef sistem/bileşen `vehicle_status.system_id/component_id` (`VehicleStatus.msg:118-119`; süzgeç `Commander.cpp:746-747`; işleme `:936-944`). `source_component < 1000` olmalı ki istek "User" sayılsın (`Commander.cpp:1559-1562`) **(doğrulanacak)**.
  - [x] 5.2 `vehicle_command_ack` izlenir; `TEMPORARILY_REJECTED` gelirse hover sürer ve istek **1 s arayla en fazla 3 kez** tekrarlanır (C2). Gönderilen istek sayısı `hold_request_count` alanına yazılır. **3 denemeden sonra da reddedilirse (Karar 2026-11-10, kullanıcı "tamam"):** drone yerinde beklemeye (hover) devam eder, durum HOLD_ISTENDI'de kalır; QGC'ye uyarı düşer (`mavlink_log_critical`, bir kez) ve logda görünür (`hold_request_count` = 3, `state` = HOLD_ISTENDI); pilot RC ile devralır. Modül kendi başına RTL, iniş ya da başka bir mod istemez.
  - [x] 5.3 PX4 Hold'a geçince (`nav_state` artık bizim mod değil) durum PASIF olur, setpoint durur; takibe **kendiliğinden dönülmez** (C reddedildi).
  - [x] 5.A **EKF yön sıfırlamasında tutulan yaw kaydırılır** (Karar D5-a, 2026-11-10): `vehicle_local_position.heading_reset_counter` değişince tutulan/komut edilen yaw (`_yaw_cmd`) `delta_heading` kadar kaydırılır (PX4 kalıbı `MulticopterPositionControl.cpp:709-711`; konum kaydırmasının, karar 4, yanına).
  - [x] 5.B **Sıra no "önceki numara" yalnızca tam sessizlikte unutulur** (Karar 1a, 2026-11-11; 5b-a'nın inceltilmesi): önceki numara, `AF_DATA_TOUT` boyunca **hiç `AF_LOS` adlı mesaj gelmezse** (1. kontrolü geçen mesaj; sonraki kontrollerde atılsa bile sessizliği bozar) unutulur. Donmuş Pi aynı mesajı tekrarlarsa hepsi `CHECK_SEQ` ile atılır → 0.5 s'de KAYIP_BEKLE, 1.5 s'de Hold. Birim testine bu durum eklenir. SITL: `--senaryo sira` uzun bölümünde Hold görülür.
  - [x] 5.C **Yaw hız sınırı parametresi `AF_YAWRATE_MAX`** (Karar 2026-11-11; ad ve değer kullanıcının): varsayılan **60°/s**, aralık **5–200°/s**, QGC grubu `AUTO FOLLOW`, İngilizce açıklama. Her çevrimde komut edilen yaw en fazla `AF_YAWRATE_MAX × dt` kadar değişir (açı farkı ±π'ye sarılarak). Yeni log alanı yok (`yaw_cmd` sınırlanmış değeri gösterir). Kanıt: PX4 otomatik modlarında `MPC_YAWRAUTO_MAX` = 60°/s (`multicopter_autonomous_params.c:148`, `FlightTaskAuto.cpp:306-307`); bizim modda yalnızca `MC_YAWRATE_MAX` = 200°/s (`mc_att_control_params.c:147`). Birim testi; SITL'de S2 tekrarlanır (beklenen ≈ 60°/s).
  - [x] 5.4 Derleme: `make px4_sitl` ve `make px4_fmu-v6c_default`, flash kaydı; `make tests TESTFILTER=AutoFollowGuidance` yeşil.
  - [x] 5.5 **S4 tam** (Grup 4.2 oturum adımlarıyla, `AF_LOST_T` = 1.0 s; kullanılan değer kayda yazılır):
    - gönderim kesilir → 0.5 s sonra KAYIP_BEKLE (hover), +1.0 s sonra `nav_state = 4` (toplam ≈ 1.5 s);
    - 1.0 s dolmadan geri gelir → takip kendiliğinden sürer, Hold yok;
    - `data[5] = 0` → hemen KAYIP_BEKLE, 1.0 s sonra Hold;
    - hedefsiz moda giriş → girişten 1.5 s sonra Hold.

    Ölçüm: son geçerli örnek ↔ `vehicle_status.nav_state = 4` arası süre, `vehicle_command` (istek anı), `trajectory_setpoint`. Hold'un kaynağının "User" görünüp görünmediği not edilir (5.1 doğrulaması).
  - [x] 5.6 Kalan ön kontrol: Hold'dan sonra RC anahtarını başka konuma alıp geri getirerek ve QGC'den tek tıkla yeniden giriş; anahtarı yerinde bırakmanın yetmediği görülür (`ManualControl.cpp:176-177`).
  - [x] 5.7 Her ULog `~/Desktop/AUTO-FOLLOW LOG/`'a kopyalanır; **ne verildi, drone ne yaptı, ULog adı** yazılır; parametre dosyası her testten önce/sonra sıfırlanır.
  - [x] 5.8 `tez/pin/verify_pin.sh --worktree`: yalnızca 7 yoldan değişenler.
  - [x] 5.9 `log-sozlugu.md`: `STATE_HOLD_ISTENDI` ve `hold_request_count` satırları kodla doğrulanır; **`AF_YAWRATE_MAX` satırı eklenir**; sıra no kuralının (5.B) anlatımı güncellenir; `spec.md` parametre tablosu ve Bölüm 2 (kontrol 4) aynı şekilde güncellenir (aynı commit).
  - [x] 5.10 `rapor.md` (§4.7 güvenlik davranışları gerçekleşen hâliyle, S4 sonuçları, flash, belge geçmişi) ve görev grubu notu.
  - [x] 5.11 Commit: `2026-11-08-m15-takip-kodu: Görev grubu 5 — Hold geçişi, S4 tam, yaw sınırı, sıra no inceltmesi`.
  - Sonuç (2026-11-11): Hold isteği, tekrar ve QGC uyarısı (geçici metin), yön sıfırlamasında yaw kaydırma, sıra no kuralı 1a ve `AF_YAWRATE_MAX` yazıldı; birim testi 12/12; 6C flash 1 937 252 B (%98,53, +992 B). SITL (son kodla): S4 tam — son geçerliden Hold'a 1,528 s, "hedef yok"tan 1,036 s, hedefsiz girişten 1,524 s, kısa kesintide Hold yok, Hold'dan sonra kendiliğinden dönüş yok (`19_18_27.ulg`); Hold sonrası RC anahtarı aç-kapa ve QGC ile yeniden giriş, anahtarı yerinde bırakmak yetmedi (`19_22_03.ulg`); donmuş Pi 1,540 s'de Hold (`19_20_46.ulg`); S2 60°/s (`19_25_29.ulg`); masada hedefsiz giriş (`19_23_53.ulg`). İstek "User" sayılıyor (5.1 doğrulandı). Ret yolu SITL'de üretilemedi, birim testinde sınandı. 3 soru: `implementation/grup-5-hold-gecisi.md` Bölüm 8.

**Kabul kriterleri:**
- Veri kesilince son geçerli örnekten ≈ 1.5 s sonra `nav_state = 4`; bayrak 0'da 1.0 s; hedefsiz girişte girişten 1.5 s.
- Hold'dan sonra mod kendiliğinden geri açılmıyor; anahtar aç-kapa ve QGC ile yeniden giriliyor.
- İki derleme geçiyor, flash kaydı güncel; S4 ULog adları yazılı.

---

### Loglama, analiz ve kapalı çevrim

#### Görev grubu 6: Analiz script'i, kapalı çevrim S6–S7 ve kapanış

**Bağımlılık:** Grup 5. (Log mesajı Grup 2'de yazıldı.)

- **Ne:** Sözlüğün son kez kodla eşitlenmesi, ULog'dan senaryo ölçümlerini çıkaran `tez/analiz/af_log_analiz.py`, kapalı çevrim S6 ve S7, PR hazırlığı.
- **Neden:** Spec Bölüm 9 (Karar L2-b, L1, L3, L4, Karar 4, C3), Bölüm 11 (S6, S7, değerlendirme), Bölüm 12; kullanıcının vurgusu: filtrenin girdisi ve çıktısı loga yazılıp analiz edilir.
- **Nasıl kontrol edilir:** Yeni bir SITL logunda alanlar `auto_follow_status.<alan>` adıyla görünür; analiz script'i S6–S7 ölçümlerini sayıyla çıkarır.

- [ ] 6.0 Loglama, analiz ve kapalı çevrim testlerini tamamla
  - [ ] 6.5 Kod değiştiyse derleme: `make px4_sitl` ve `make px4_fmu-v6c_default`, flash kaydı; `make tests TESTFILTER=AutoFollowGuidance` yeşil. `log-sozlugu.md` son hâliyle kodla karşılaştırılır (aynı commit).
  - [ ] 6.8 `tez/analiz/af_log_analiz.py` (izinli yol; pyulog 1.2.4, `tez/env/requirements-lock.txt:27`): ULog'u okur ve spec Bölüm 11 tablosunun "Ölçüm" sütunundaki değerleri senaryo başına çıkarır (ör. `range_est − range_desired`, `yaw_cmd − yön`, `vel_cmd`, `target_vel_ned`, son geçerli örnek → `nav_state = 4` süresi, `reject_*_count`). Alan adlarını sözlükle aynı kullanır. Komut satırı seçeneklerinin adları ve çıktı biçimi **(ad kullanıcıya sorulacak)**. `ruff format` + `ruff check`, tip ipuçları, docstring.
  - [ ] 6.9 **S6 Duran hayali insan** (kapalı çevrim, `AF_K_FF` = 0): beklenen `range_est → range_desired` (15.6 m), burun hedefte, salınım yok. Hedefin yerdeki başlangıç konumu **(değer kullanıcıya sorulacak)**. Ölçüm: `range_est − range_desired`, `yaw_cmd − yön`, `vel_cmd` (analiz script'iyle).
  - [ ] 6.10 **S7 Yürüyen hayali insan** (kapalı çevrim, `AF_K_FF > 0`): beklenen: geride kalmadan takip, mesafe hatası S6'ya yakın. `AF_K_FF` değeri, hedefin hızı ve yolu **(değer kullanıcıya sorulacak)**. Ölçüm: `target_vel_ned`, `range_est − range_desired`, `vel_cmd`. Filtre girdisi (`target_meas_ned`) ve çıktısı (`target_est_ned`, `target_vel_ned`) ayrıca karşılaştırılır (kullanıcının vurgusu). `AF_ALPHA` / `AF_BETA` ayarı gerekirse yapılan her değişiklik ve gerekçesi kayda yazılır.
  - [ ] 6.11 S6 ve S7 için oturum adımları Grup 4.2 ile aynı (parametre sıfırlama, `PX4_PARAM_AF_ENABLE=1`, `HEADLESS=1`, Position'da kalkış, ULog kopyası, **ne verildi, drone ne yaptı, ULog adı**).
  - [ ] 6.12 `latency` değerleri kayda yazılır; gecikme telafisi gerekip gerekmediği için veri olarak m13/m16'ya not düşülür (V3, spec Bölüm 9).
  - [ ] 6.13 S1–S5 yeniden koşulmaz: log mesajı Grup 2'de geldiği için ölçümleri Grup 4'te alındı (Karar 1-a). Yalnızca Grup 5–6'da kod değiştiyse etkilenen senaryo kısa tekrarlanır ve kayda yazılır.
  - [ ] 6.14 `tez/pin/verify_pin.sh --worktree`: yalnızca 7 yoldan değişenler.
  - [ ] 6.15 `planning/requirements.md` §1.3 "m16'ya kalanlar" yetişmeyenlerle güncellenir.
  - [ ] 6.16 `rapor.md` (§4.8 loglama gerçekleşen hâliyle, S6–S7 sonuçları, son flash, belge geçmişi) ve görev grubu notu.
  - [ ] 6.17 Commit: `2026-11-08-m15-takip-kodu: Görev grubu 6 — analiz script'i, S6–S7, kapanış`.
  - [ ] 6.18 PR açıklaması taslağı hazırlanır (**push ve PR yalnızca kullanıcı isteyince**): başlık `[M15] ...`; PX4'e eklenen yeni dosya yolları (kabul kriteri 6); 6C flash kullanımı; `../agent-os/product/tech-stack.md:44` için "karar: external mode, güncellenmeli" notu; `Closes Auto-Follow/Auto-Follow#6`. Zorunlu CI: `verify-pin`, `derleme-sitl`, `derleme-fmu-v6c`; `verify-pin` Hüseyin'in izin listesi PR'ı birleşmeden yeşil olmaz.

**Kabul kriterleri:**
- `log-sozlugu.md` son kodla aynı.
- S6 ve S7 için **ne verildi, drone ne yaptı, ULog adı** ve `af_log_analiz.py` ile çıkarılmış sayısal sonuçlar yazılı; ULog'lar `~/Desktop/AUTO-FOLLOW LOG/`'da.
- Son 6C flash kullanımı spec'te, raporda ve PR taslağında.
- Issue #6 kabul kriterleri 1–6 (`spec.md` "Kabul kriterleri") karşılanmış ya da karşılanmayan madde ve nedeni raporda yazılı.

---

## Uygulama sırası

1. Görev grubu 0: Ön koşullar (kullanıcı ve ekip; diğer grupları engellemez)
2. Görev grubu 1: İskelet
3. Görev grubu 2: Guidance + alpha-beta + log mesajı
4. Görev grubu 3: Kısa birim testi
5. Görev grubu 4: SITL ön kontroller + S1–S5 (S4 yalnız KAYIP_BEKLE)
6. Görev grubu 5: Hold geçişi + S4 tam
7. Görev grubu 6: Analiz script'i, S6–S7, kapanış

Süre yetmezse sıra korunur ve kalanlar `planning/requirements.md` §1.3'e yazılır. Teslim 2026-11-15.

## Kapsam dışı (spec "Out of Scope")

- Hold'dan sonra takibe kendiliğinden dönüş (seçenek C) ve ayrıntılı failsafe / mod çıkış akışının tamamı → m16
- **RC kaybı ve modül donması SITL testleri → m16 adayı** (A1)
- Nihai guidance yasası, ince ayar ve gecikme telafisi (gerekirse) → m13 / m16
- Pi tarafı, ICD, kalıcı yön göndericisi → Vision (m3–5, m12)
- Gerçekçi simülasyon, kamera ve hareketli insan modeli / dünyası → m06
- Gerçek uçuş → m22, m25
- Flash'ta yer açma, modül kapatma → m14
- Yeni MAVLink mesajı / dialect
- Ekip için "her özelleştirme loga girer + log sözlüğü" standardı → ayrı m00 (çatı profili)
- Çatı dosyalarının (`agent-os/product/`, standartlar) güncellenmesi → repo sorumlusu
- **Geliştirmeye açık (kullanıcının notu, A3):** dışarıda, arm etmeden, GPS fix'liyken yapılacak yer testleri (geometri ve guidance çıktıları görülebilir) sonra eklenebilir; kullanıcı düşünecek. Bu listede görev olarak yer almaz.
- Uygulama sırasında yetişmeyen adımlar → "m16'ya kalanlar" listesi (`planning/requirements.md` §1.3)
