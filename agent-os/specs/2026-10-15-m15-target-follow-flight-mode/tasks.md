# Task Breakdown: Hedef Takip Uçuş Modu (Target Follow Flight Mode) — Akış Şemaları

## Overview
Total Tasks: 58 alt görev, 7 task group

Bu spec'in teslimatı **yalnızca iki Mermaid akış şeması**dır (kod yok):
- `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/diagrams/01-ust-seviye-akis.md` (Şema 1: sade, üst seviye)
- `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/diagrams/02-px4-detayli-akis.md` (Şema 2: PX4 v1.17.0'a özel, detaylı; A/B/C/D blokları)

Bu spec'te "test", kod testi değildir. Her task group'un başında şemaya yönelik 2–8 **doğrulama kontrolü** tanımlanır, sonunda yalnızca o kontroller çalıştırılır. Kontroller grep ile ad doğrulama, node/kenar sayımı ve Mermaid sözdizimi kontrolüdür. Modülün C++ kodu, `module.yaml`, `CMakeLists.txt` ve GoogleTest testleri sonraki spec'e aittir. Bu spec'te yazılmaz.

**Genel kurallar (tüm gruplar için geçerli):**
- Yalnızca spec klasörü içinde çalışılır. Upstream PX4 dosyası, `msg/`, `mavlink` submodule, `Tools/simulation/gz`, `boards/`, `tez/pin/allowed-paths.txt` **değiştirilmez**. Branch değiştirilmez, commit atılmaz.
- Metinler Türkçe, teknik terimler İngilizce yazılır.
- Parantez, eğik çizgi, iki nokta veya alt çizgi içeren her node etiketi `"..."` ile tırnaklanır. Node id'leri ASCII'dir (ör. `piCam`, `fcNedLos`). `end` gibi Mermaid anahtar kelimeleri id olarak kullanılmaz. Etiket içinde çift tırnak gerekiyorsa `#quot;` kullanılır.
- Kaynakta doğrulanamayan her ad "(doğrulanacak)" etiketi alır. Açık konular `classDef tbd` (kesik çizgi, ör. `stroke-dasharray: 5 5`) sınıflı "TBD" node'larıyla gösterilir. `TEZ_FOL_*` parametreleri kaynakta yoktur. Bunlar "(öneri)" olarak etiketlenir.
- Guidance yasasının ayrıntısı şemaya kopyalanmaz. Yalnızca `/home/yusuf/Desktop/guidance-yasalari.md` dokümanına atıf yapılır.
- Ad envanteri (Task Group 1) çalışma notu olarak scratch alanında tutulur. Spec klasörüne iki şema dosyası dışında yeni dosya eklenmez.

## Task List

### Kaynak Doğrulama

#### Task Group 1: PX4 v1.17.0 Ad Envanteri ve Doğrulama
**Dependencies:** None

- [x] 1.0 Şemalarda geçecek her adı v1.17.0 kaynağına karşı doğrula
  - [x] 1.1 2–8 doğrulama kontrolü tanımla
    - K1: Her uORB topic için `msg/` veya `msg/versioned/` altında `.msg` dosyası var, ya da bir `.msg` içindeki `# TOPICS` satırında geçiyor (ör. `config_control_setpoints` → `msg/versioned/VehicleControlMode.msg`).
    - K2: Şemada kullanılan her alan ilgili `.msg` dosyasında birebir mevcut.
    - K3: Her PX4 parametresi `module.yaml` veya `*_params.c` içinde tanımlı.
    - K4: Her dosya yolu repoda mevcut. Upstream'de olmayan yollar (`src/modules/tez_follow`, `*_gz_x500_tez.post`) "planlanan" olarak ayrılır.
    - K5: Her enum/sabit değeri (`NAVIGATION_STATE_EXTERNAL1..8` = 23..30, `VEHICLE_CMD_SET_NAV_STATE` = 100001 vb.) kaynaktaki değerle aynı.
    - Kontroller grep tabanlıdır ve kabukta çalıştırılır. Ayrı script dosyası spec klasörüne eklenmez.
  - [x] 1.2 uORB topic ve alanlarını doğrula
    - `register_ext_component_request`: `name` (char[25]), `request_id`, `px4_ros2_api_version`, `register_arming_check`, `register_mode`
    - `register_ext_component_reply`: `success`, `arming_check_id`, `mode_id`, `name`
    - `unregister_ext_component`: `arming_check_id`, `mode_id`
    - `arming_check_request` / `arming_check_reply`: `registration_id`, `can_arm_and_run`, `mode_req_attitude`, `mode_req_local_position`, `mode_req_local_alt`, `mode_req_angular_velocity`, `mode_req_prevent_arming`, `mode_req_manual_control`
    - `config_control_setpoints` (tip `vehicle_control_mode_s`): `source_id` ve spec'teki tüm `flag_*` alanları
    - `debug_vect` (`name` char[10], `x/y/z`), `trajectory_setpoint` (`position`, `velocity`, `yaw`, `yawspeed`, `timestamp`), `goto_setpoint`
    - `vehicle_attitude.q`, `vehicle_local_position` (`x/y/z`, `xy_valid`, `z_valid`, `heading`, `xy_reset_counter`, `z_reset_counter`), `vehicle_status.nav_state`, `vehicle_land_detected.landed`, `vehicle_command`
    - Kontrolcü zinciri topic'leri: `vehicle_attitude_setpoint`, `vehicle_rates_setpoint`, `vehicle_torque_setpoint`, `vehicle_thrust_setpoint`, `actuator_motors`
  - [x] 1.3 Commander ve mod yönetimi davranışını doğrula (değiştirmeden, yalnızca okuyarak)
    - `src/modules/commander/ModeManagement.cpp`: kayıt akışı, `COM_MODE%d_HASH`, "Not accepting registration requests while armed" mesajı, `updateControlMode`
    - `externalChecks.hpp/.cpp`: ~300 ms istek aralığı, 50 ms cevap süresi, 3 cevapsız istek → unresponsive
    - `failsafe/failsafe.cpp` `checkModeFallback`: RTL'e düşüş
    - `Commander.cpp` `manualControlCheck`: stick override koşulları; `VEHICLE_CMD_SET_NAV_STATE` işleyişi; `UserModeIntention::change`
    - `failsafe/framework.cpp` içindeki override davranışı (doğrulama maddesi olarak not edilir)
  - [x] 1.4 Kontrolcü ve MAVLink tarafını doğrula
    - `FlightModeManager.cpp` `start_flight_task`: `NAVIGATION_STATE_EXTERNAL1..8` → `FlightTaskIndex::None`
    - `MulticopterPositionControl.cpp`: `generateFailsafeSetpoint`, EKF reset düzeltmesi, `want_takeoff` koşulu
    - `mavlink_receiver.cpp` `handle_message_debug_vect` (timestamp'in `hrt_absolute_time()` ile basıldığı)
    - `streams/AVAILABLE_MODES.hpp`, `PX4_CUSTOM_MAIN_MODE_AUTO`, `PX4_CUSTOM_SUB_MODE_EXTERNAL1..8`, `VEHICLE_CMD_DO_SET_MODE`
  - [x] 1.5 Parametreleri ve sabitleri doğrula
    - `COM_FLTMODE1..6` (100..107 = External Mode 1..8), `COM_MODE${i}_HASH`, `COM_RC_OVERRIDE`, `COM_RC_STICK_OV`, `COM_RCL_EXCEPT` (bit 3), `NAV_RCL_ACT`
    - `MPC_XY_VEL_MAX`, `MPC_Z_VEL_MAX_UP`, `MPC_Z_VEL_MAX_DN`, tilt limiti parametresi
    - `MAV_1_CONFIG`, `MAV_1_MODE`
    - `NAVIGATION_STATE_AUTO_LOITER` değeri
  - [x] 1.6 Dosya yollarını ve derleme/başlatma bilgisini doğrula
    - `boards/px4/fmu-v6c/` içinde `CONFIG_BOARD_SERIAL_TEL2="/dev/ttyS3"`
    - `boards/px4/fmu-v6c/default.px4board`, `boards/px4/sitl/default.px4board`
    - `px4-rc.mavlink` onboard UDP portları (local 14580 / remote 14540)
    - `mc_nn_control` iş kuyruğu (`px4::wq_configurations::nav_and_controllers`?), `src/examples/work_item` iskeleti
    - SD kart `/fs/microsd/etc/extras.txt` başlatma noktası (rcS içinde), `ROMFS/px4fmu_common/init.d-posix/airframes/` deseni
    - `tez/pin/allowed-paths.txt` içinde `src/modules/tez_*` ve iki `.px4board` dosyasının henüz **olmadığını** teyit et (ön koşul TBD'dir)
    - `px4_add_unit_gtest` CMake fonksiyonunun varlığı
  - [x] 1.7 Envanteri sınıflandır
    - Her ad şu etiketlerden birini alır: doğrulandı / "(doğrulanacak)" / "(öneri)" (`TEZ_FOL_*`, `tez_follow`) / "TBD" (açık konu)
    - Spec'teki bir ad kaynakla çelişirse: şemaya kaynaktaki ad yazılır ve fark Task Group 7 raporunda kullanıcıya bildirilir. Kaynakta bulunamayan ad "(doğrulanacak)" ile işaretlenir, uydurulmaz.
    - Not: requirements.md'deki `/dev/ttyAMA0` Pi tarafı UART'tır. FC tarafında spec.md'deki `/dev/ttyS3` kullanılır. İkisi karıştırılmaz.
  - [x] 1.8 Grup 1 kontrollerini çalıştır
    - YALNIZCA 1.1'deki K1–K5 kontrollerini çalıştır
    - Tüm repoyu değil, sadece envanterdeki adları kapsa

**Acceptance Criteria:**
- 1.1'deki kontroller geçer. Geçmeyen her ad "(doğrulanacak)" etiketine veya kaynak düzeltmesine bağlanmıştır.
- Şemalarda kullanılacak her topic/alan/parametre/yol için bir sınıflandırma vardır.
- Repoda hiçbir dosya değişmemiştir (envanter scratch alanındadır).

### Şema 1

#### Task Group 2: Üst Seviye Akış (`diagrams/01-ust-seviye-akis.md`)
**Dependencies:** Task Group 1

- [x] 2.0 Referans görsel üslubunda sade üst seviye şemayı oluştur
  - [x] 2.1 2–6 doğrulama kontrolü tanımla
    - K1: Toplam node sayısı ~15–18 aralığında
    - K2: "ECEF" ve "WGS84" metni şemada geçmiyor
    - K3: `subgraph "Raspberry Pi (Vision)"` ve `subgraph "Pixhawk 6C / PX4 — Tez uçuş modu"` mevcut
    - K4: Dört yan girdi (`UAV Roll / Pitch / Yaw`, `İrtifa (baro / EKF)`, `UAV yerel NED konumu`, `Pilot / QGC mod seçimi`) paralelkenar (`[/"..."/]`) şeklinde
    - K5: ICD kutusu ve irtifa girdisi `tbd` sınıfında
    - K6: Mermaid sözdizimi kontrolü (bkz. 7.2)
  - [x] 2.2 Dosyayı oluştur ve başlığı yaz
    - Kısa Türkçe başlık ve 2–4 cümlelik açıklama: kim neyi yapar (Pi: algılama → body FRD LOS; FC: geolocation → guidance → PX4 kontrolcüleri), düz dünya kabulü
    - Referans görsele atıf: `../planning/visuals/WhatsApp Image 2026-09-26 at 00.07.13.jpeg` (yalnızca üslup rehberi, birebir kopya değil)
    - Tek ` ```mermaid ` bloğu, `flowchart TB`
  - [x] 2.3 Pi subgraph'ını çiz
    - Girdi (paralelkenar): "Kamera görüntüsü"
    - Zincir (yuvarlak köşeli kutu): "Model ile insan tespiti (piksel)" → "Kamera frame LOS" → "Body FRD LOS (montaj açısı dahil)"
    - Kamera montaj girdileri FC tarafına çizilmez (montaj Pi'de dahil edilir)
  - [x] 2.4 Ara kutuyu ekle
    - "Pi → FC hedef LOS mesajı (ICD TBD)", iki subgraph arasında, `tbd` sınıfı
  - [x] 2.5 FC subgraph ana zincirini çiz
    - "Body LOS → Vehicle-carried NED LOS" → "Aşağı açı (down angle) ve eğik mesafe (slant range)" → "Hedefin yerel NED konumu" → "Hedef kestirimi (konum/hız)" → "Guidance (istenen durum: hız + yaw)" → "PX4 kontrolcüleri" → "Araç hedefi takip eder"
  - [x] 2.6 Yan girdileri bağla (görseldeki gibi yatay oklar)
    - "UAV Roll / Pitch / Yaw" → Vehicle-carried NED LOS kutusu (tek kutu veya üç ayrı kutu, node bütçesine göre)
    - "İrtifa (baro / EKF)" (TBD) → down angle / slant range kutusu
    - "UAV yerel NED konumu" → hedefin yerel NED konumu kutusu
    - "Pilot / QGC mod seçimi" → FC subgraph'ı (modu başlatır)
    - Yan girdiler ana zincirin yanında kalacak şekilde yerleştirilir. Mermaid yerleşimi tam yatay olmazsa düşük-orta sadakat kabul edilir.
  - [x] 2.7 Görsel stili uygula
    - `classDef input` (paralelkenar, beyaz zemin, siyah çerçeve), `classDef process` (yuvarlak köşe, beyaz zemin, siyah çerçeve), `classDef tbd` (kesik çizgi)
    - `linkStyle default` ile mavi tek yönlü oklar
  - [x] 2.8 Grup 2 kontrollerini çalıştır
    - YALNIZCA 2.1'deki kontrolleri çalıştır

**Acceptance Criteria:**
- 2.1'deki kontroller geçer.
- Şema tek sayfada okunur, düşey ana zincir ve yan girdiler referans görselin şekil dilini taşır.
- Düz dünya kabulü korunur (ECEF/WGS84 yok). Açık konular (ICD, irtifa) TBD olarak görünür.

### Şema 2

#### Task Group 3: Şema 2 İskeleti ve (A) Başlatma, Mod Kaydı, Arming Check
**Dependencies:** Task Group 1

- [x] 3.0 `diagrams/02-px4-detayli-akis.md` dosyasını ve (A) bloğunu oluştur
  - [x] 3.1 2–8 doğrulama kontrolü tanımla
    - K1: Dosyada (A), (B), (C), (D) için ayrı başlık ve ayrı ` ```mermaid ` blokları var
    - K2: (A) bloğunda `register_ext_component_request`, `register_ext_component_reply`, `config_control_setpoints`, `arming_check_request`, `arming_check_reply`, `unregister_ext_component` kenar etiketi olarak geçiyor
    - K3: "Ön koşul onayı (allowed-paths ve `.px4board`)" TBD node'u mevcut
    - K4: "armed iken kayıt reddi" dalı ve "RTL'e düşer" uyarı notu mevcut
    - K5: Başlatma noktaları ve iş kuyruğu "(doğrulanacak)" etiketli
    - K6: (A) bloğu Mermaid sözdizimi kontrolü
  - [x] 3.2 Dosya başlığını ve ortak bölümleri yaz
    - Kısa Türkçe başlık, amaç, düz dünya kabulü, guidance dokümanı atfı (`/home/yusuf/Desktop/guidance-yasalari.md`)
    - Lejant: katmanlar (Pi (Vision), MAVLink, uORB, `tez_follow` modülü, commander, FlightModeManager ve kontrolcüler, QGC/RC, Doğrulama), TBD ve "(doğrulanacak)"/"(öneri)" etiketlerinin anlamı
    - Açık konular listesi: ICD, yükseklik kaynağı, nihai guidance yasası, setpoint tipi (`trajectory_setpoint` / `goto_setpoint`), ön koşul onayı, süre parametreleri
    - Her Mermaid bloğu kendi `classDef` tanımlarını içerir (bloklar arası paylaşılmaz)
  - [x] 3.3 (A) Derleme ön koşulunu çiz
    - TBD node: `tez/pin/allowed-paths.txt` onayı (`src/modules/tez_*` + iki `.px4board`, ayrı PR)
    - → `CONFIG_MODULES_TEZ_FOLLOW=y` (`boards/px4/fmu-v6c/default.px4board`, `boards/px4/sitl/default.px4board`)
  - [x] 3.4 Modül iskeletini ve başlatma noktasını çiz
    - `ModuleBase` + `ModuleParams` + `px4::ScheduledWorkItem` (`src/examples/work_item` deseni), `nav_and_controllers` kuyruğu (doğrulanacak), `ScheduleOnInterval` (~50 Hz önerisi)
    - SITL: `ROMFS/px4fmu_common/init.d-posix/airframes/<id>_gz_x500_tez.post` (doğrulanacak). Donanım: `/fs/microsd/etc/extras.txt` (doğrulanacak). Not: `rc.mc_apps` kilitli.
    - Modül boot'ta, disarm iken başlar
  - [x] 3.5 Kayıt akışını çiz (`mc_nn_control` deseni)
    - `tez_follow` → commander: `register_ext_component_request` (`name`, `request_id`, `px4_ros2_api_version=1`, `register_arming_check=true`, `register_mode=true`)
    - Karar: armed mı? Evet → kayıt reddi ("Not accepting registration requests while armed")
    - commander → `tez_follow`: `register_ext_component_reply` (`success`, `arming_check_id`, `mode_id` ∈ `NAVIGATION_STATE_EXTERNAL1..8` = 23..30)
    - Not: `COM_MODE${i}_HASH` (mod adının FNV-1a hash'i) → aynı ad hep aynı slot, mod adı sabit tutulur
  - [x] 3.6 Kontrol modu yapılandırmasını çiz
    - `config_control_setpoints` (`source_id = mode_id`) → commander `ModeManagement::updateControlMode` → mod aktifken `vehicle_control_mode`
    - true ve false bayrak listeleri tek node'da veya not olarak (spec'teki listeyle birebir)
    - Not: `mc_nn_control` pozisyon kontrolünü kapatır, `tez_follow` açık tutar
  - [x] 3.7 Arming check döngüsünü ve "yalnızca havada" koşulunu çiz
    - commander → `arming_check_request` (~300 ms) → modül her çevrimde kontrol eder → `arming_check_reply` (50 ms içinde)
    - Cevap alanları: `registration_id = arming_check_id`, `can_arm_and_run = !vehicle_land_detected.landed`, `mode_req_*` değerleri, `mode_req_prevent_arming=true`, `mode_req_manual_control=false`
    - Dal: 3 cevapsız istek → unresponsive
    - Uyarı notu: mod aktifken `can_arm_and_run=false` veya unresponsive → `Failsafe::checkModeFallback` **RTL** (Hold değil), bu yüzden hedef kaybında kullanılmaz
    - Not: external modda `mc_pos_control` `want_takeoff` üretmez → moda yerden kalkış yok
  - [x] 3.8 Kapanışı çiz
    - `should_exit` → `unregister_ext_component` (`arming_check_id`, `mode_id`)
  - [x] 3.9 Grup 3 kontrollerini çalıştır
    - YALNIZCA 3.1'deki kontrolleri çalıştır

**Acceptance Criteria:**
- 3.1'deki kontroller geçer.
- (A) bloğu `mc_nn_control` `Run()` sırasını izler: çıkış kontrolü → kayıt gönder → cevabı bekle → arming check cevabı.
- Tüm topic adları kenar etiketlerinde ve Task Group 1 envanteriyle birebir aynı.

#### Task Group 4: Şema 2 (B) Çevrim Başına Veri Akışı ve Kontrolcü Zinciri
**Dependencies:** Task Group 3

- [x] 4.0 (B) run loop bloğunu oluştur
  - [x] 4.1 2–8 doğrulama kontrolü tanımla
    - K1: Veri yolu topic düzeyinde izlenebilir: `debug_vect` → `tez_follow` → `trajectory_setpoint` → `vehicle_attitude_setpoint` → `vehicle_rates_setpoint` → `vehicle_torque_setpoint` / `vehicle_thrust_setpoint` → `actuator_motors` kenar etiketleri mevcut
    - K2: Girdi doğrulamanın dört adımı ve "at ve say" dalı mevcut
    - K3: Gate `vehicle_status.nav_state == mode_id` mevcut
    - K4: ICD, yükseklik kaynağı, nihai guidance yasası ve setpoint tipi TBD node'ları mevcut
    - K5: Guidance node'u yasa denklemi içermiyor, yalnızca dokümana atıf yapıyor
    - K6: `TEZ_FOL_*` parametreleri "(öneri)" etiketli
    - K7: (B) bloğu Mermaid sözdizimi kontrolü
  - [x] 4.2 Pi → FC iletişimini çiz
    - Pi subgraph → MAVLink subgraph: TELEM2 (`CONFIG_BOARD_SERIAL_TEL2="/dev/ttyS3"`, `MAV_1_CONFIG`/`MAV_1_MODE` onboard; doğrulanacak). SITL: UDP onboard (local 14580 / remote 14540)
    - `mavlink_receiver` → `handle_message_debug_vect` → uORB `debug_vect` (`name` char[10], `x/y/z`). Hepsi "ICD TBD".
    - Not: timestamp FC'ye varış anıdır (`hrt_absolute_time()`)
  - [x] 4.3 Girdi doğrulamayı çiz
    - Ardışık karar node'ları: `name` filtresi → `PX4_ISFINITE` → birim vektör normu → tazelik (`TEZ_FOL_TOUT`)
    - Herhangi biri geçmezse: örnek atılır ve sayılır
  - [x] 4.4 Durum girdilerini ve mod gate'ini çiz
    - Abonelikler: `vehicle_attitude.q` (FRD→NED), `vehicle_local_position` (`x/y/z`, `xy_valid`, `z_valid`, `heading`, `xy_reset_counter`, `z_reset_counter`), `vehicle_status.nav_state`, `vehicle_land_detected.landed`
    - Karar: `nav_state == mode_id`? Hayır → hesap yapılmaz, setpoint yayınlanmaz
  - [x] 4.5 Geolocation hesap zincirini çiz
    - `LOS_NED = R(q) · LOS_body` → karar `u_D > eşik` (LOS yere bakıyor mu)
    - h = yer düzlemine göre yükseklik, geçici `-vehicle_local_position.z` (baro füzyonlu) → yükseklik kaynağı TBD node'u
    - Slant range = h / u_D, down angle = asin(u_D) → hedef NED = UAV NED + range · LOS_NED
    - Geçersiz dalı (`u_D` geçersiz, `xy_valid`/`z_valid` false) (C) bloğundaki "güvenli taraf" davranışına referans verir
  - [x] 4.6 Kestirim, guidance ve saturation'ı çiz
    - Hedef kestirimi: alfa-beta / low-pass (konum + hız). Not: `follow_target_estimator` yalnızca fikir kaynağıdır, Follow Me kullanılmaz.
    - Guidance (çalışma temeli, TBD): sabit irtifa (`TEZ_FOL_ALT` veya giriş irtifası), sabit yatay mesafe, P + hedef hızı ileri beslemesi, yaw hedefe bakar. Ayrıntı için `guidance-yasalari.md` atfı.
    - Saturation: yatay/dikey hız, yaw hızı, min irtifa
  - [x] 4.7 Setpoint çıkışını çiz
    - `trajectory_setpoint` (NED): `velocity`, `position[2]` veya `velocity[2]`, `yaw`/`yawspeed`. Kontrol edilmeyen alanlar NaN, `timestamp = hrt_absolute_time()`
    - Not: moda girişte ilk çevrimde setpoint yayınlanmalı, aksi halde `mc_pos_control` `generateFailsafeSetpoint` üretir
    - TBD node: setpoint tipi (`trajectory_setpoint` / `goto_setpoint` + `GotoControl`)
  - [x] 4.8 Aşağı akış kontrolcü zincirini çiz
    - `FlightModeManager::start_flight_task` → `FlightTaskIndex::None` (`trajectory_setpoint`'i yalnızca `tez_follow` yayınlar)
    - `mc_pos_control` (`trajectory_setpoint` + `vehicle_local_position` + `vehicle_control_mode`) → `mc_att_control` → `mc_rate_control` → `control_allocator` → ESC/motorlar. Kenarlar topic adıyla etiketlenir.
    - Not: `MPC_XY_VEL_MAX`, `MPC_Z_VEL_MAX_UP/DN`, tilt limiti ikinci emniyet katmanıdır
  - [x] 4.9 Loglama ve parametre notlarını ekle
    - ULog: `debug_vect`, `trajectory_setpoint`, `vehicle_local_position`
    - Not: hedef NED konumu/durumu için yeni uORB mesajı gerekirse `msg/` kilitli → "(doğrulanacak / kullanıcıya sor)"
    - Parametre listesi (öneri, `module.yaml`, ≤16 karakter): `TEZ_FOL_TOUT`, `TEZ_FOL_HOLD_T`, `TEZ_FOL_ALT`, `TEZ_FOL_DIST`, `TEZ_FOL_KP`, `TEZ_FOL_VXY_MAX`, `TEZ_FOL_VZ_MAX`, `TEZ_FOL_YR_MAX`, `TEZ_FOL_MIN_ALT`. Kesin adlar sonraki spec'te belirlenir.
  - [x] 4.10 Grup 4 kontrollerini çalıştır
    - YALNIZCA 4.1'deki kontrolleri çalıştır

**Acceptance Criteria:**
- 4.1'deki kontroller geçer.
- Pi'den motora kadar veri yolu kenar etiketleriyle topic düzeyinde izlenebilir.
- Guidance yasası ayrıntısı şemada yoktur, yalnızca atıf vardır. Açık konular TBD olarak görünür.

#### Task Group 5: Şema 2 (C) Mod Seçimi, Çıkış, Hedef Kaybı ve Failsafe
**Dependencies:** Task Group 4

- [x] 5.0 (C) bloğunu oluştur
  - [x] 5.1 2–8 doğrulama kontrolü tanımla
    - K1: QGC yolu (`AVAILABLE_MODES` → `VEHICLE_CMD_DO_SET_MODE` → `NAVIGATION_STATE_EXTERNALx`) ve RC yolu (`COM_FLTMODE1..6 = 100..107`) mevcut
    - K2: Stick override karar node'u, üç koşulla birlikte "stick modu değiştirmez" sonucuna gidiyor ve "SITL doğrulama maddesi" olarak işaretli
    - K3: Hedef kaybı durum zinciri (takip → `TEZ_FOL_TOUT` → konum + yaw tut → `TEZ_FOL_HOLD_T` → Hold) ve "hedef geri gelirse takibe dön" dönüş oku mevcut
    - K4: `VEHICLE_CMD_SET_NAV_STATE` (100001, `param1 = NAVIGATION_STATE_AUTO_LOITER`) "(doğrulanacak)" etiketli
    - K5: "Süre parametreleri" TBD node'u mevcut. `config_overrides` / `defer_failsafes` kullanılmadığı notu mevcut.
    - K6: (C) bloğu Mermaid sözdizimi kontrolü
  - [x] 5.2 QGC 5.1.4 mod seçim yolunu çiz
    - `AVAILABLE_MODES` stream'i: mod adı `register_ext_component_reply.name` alanından gelir
    - HEARTBEAT custom mode = `PX4_CUSTOM_MAIN_MODE_AUTO` + `PX4_CUSTOM_SUB_MODE_EXTERNALx`
    - QGC → `VEHICLE_CMD_DO_SET_MODE` → commander → `NAVIGATION_STATE_EXTERNALx`
  - [x] 5.3 RC mod anahtarı yolunu çiz
    - `COM_FLTMODE1..6 = 100..107` (External Mode 1..8). Slot eşlemesi `COM_MODE${i}_HASH` ile kalıcı.
  - [x] 5.4 Moda giriş koşullarını çiz
    - Disarm: mod seçimine her zaman izin (`UserModeIntention::change`), arm `mode_req_prevent_arming` ile engellenir
    - Armed + yerde: `can_arm_and_run=false` → geçiş reddedilir
    - Armed + havada: geçiş kabul → `nav_state == mode_id` → (B) run loop aktif
  - [x] 5.5 Stick override kararını çiz
    - `Commander::manualControlCheck` koşulları: `flag_control_manual_enabled` false **ve** (`flag_control_auto_enabled` veya `flag_control_offboard_enabled` true) **ve** `COM_RC_OVERRIDE` biti açık
    - Bu modda iki bayrak false → stick modu değiştirmez (SITL doğrulama maddesi; `failsafe/framework.cpp` override davranışı da doğrulanacak)
  - [x] 5.6 Çıkışı çiz
    - Pilot RC mod anahtarı veya QGC ile başka moda geçer → modül `nav_state != mode_id` görür → setpoint üretmeyi bırakır
  - [x] 5.7 Hedef kaybı durum akışını çiz
    - `TEZ_FOL_TOUT` (~1 s) → son NED konum tutulur, son yaw korunur
    - `TEZ_FOL_HOLD_T` (~5–10 s) → `vehicle_command` `VEHICLE_CMD_SET_NAV_STATE` (100001, `param1 = NAVIGATION_STATE_AUTO_LOITER`) → Hold (doğrulanacak)
    - Hedef geri gelirse takibe dönülür (geri ok)
    - Not: Hold'da PX4 varsayılanı geçerlidir, `COM_RC_OVERRIDE` bit 0 açık olduğundan stick hareketi Position'a geçirir. Bu beklenen ve kabul edilen davranıştır.
  - [x] 5.8 Geçersiz durum dalını çiz
    - `xy_valid`/`z_valid` false, `u_D` geçersiz, EKF reset (`xy_reset_counter`/`z_reset_counter` değişimi) → güvenli taraf: konum tutar, yeni takip setpoint'i üretmez
  - [x] 5.9 PX4 varsayılan failsafe'lerini çiz
    - Batarya, RC kaybı (`NAV_RCL_ACT`; `COM_RCL_EXCEPT` bit 3 etkisi doğrulanacak), veri bağlantısı, geofence, EKF → PX4 varsayılanı
    - `config_overrides` / `defer_failsafes` kullanılmaz
    - Modül çökerse veya unresponsive olursa → commander RTL
  - [x] 5.10 Grup 5 kontrollerini çalıştır
    - YALNIZCA 5.1'deki kontrolleri çalıştır

**Acceptance Criteria:**
- 5.1'deki kontroller geçer.
- Pilot user story'si şemadan okunur: QGC/RC ile giriş, RC anahtarıyla çıkış, stick ile mod değişmez, hedef kaybında Hold.
- Hedef kaybı (modülün kendi Hold isteği) ile RTL fallback (unresponsive/çökme) açıkça ayrışır.

#### Task Group 6: Şema 2 (D) Doğrulama Akışı
**Dependencies:** Task Group 5

- [x] 6.0 (D) bloğunu oluştur
  - [x] 6.1 2–6 doğrulama kontrolü tanımla
    - K1: Beş adım sırayla mevcut: GoogleTest → Gazebo Harmonic SITL → sahte Pi (pymavlink) → ULog + pyulog metrikleri → gerçek uçuş
    - K2: Her adımda başarısızlık geri dönüş oku var
    - K3: "SITL parametre dosyasını sıfırla" adımı her SITL testinden önce yer alıyor
    - K4: "Gerçek uçuş yalnızca SITL geçtikten sonra" kapısı mevcut
    - K5: (D) bloğu Mermaid sözdizimi kontrolü
  - [x] 6.2 Adım 1: GoogleTest
    - `px4_add_unit_gtest`: düz dünya geolocation, guidance, ICD doğrulama saf fonksiyonları. Durumlar: nominal, sınır, NaN/Inf, zaman aşımı. Bu testler sonraki spec'te yazılır, şemada yalnızca adım olarak görünür.
  - [x] 6.3 Adım 2–3: SITL ve sahte Pi
    - `make px4_sitl gz_x500` / tez airframe, `HEADLESS=1`
    - Hareketli insan modeli: konumu TBD (`Tools/simulation/gz` kilitli)
    - Sahte Pi: pymavlink ile `DEBUG_VECT` gönderen script (ICD TBD)
    - Her testten önce SITL parametre dosyası (`build/px4_sitl_default/rootfs/parameters*.bson`) sıfırlanır
  - [x] 6.4 Adım 4: ULog + pyulog metrikleri
    - Takip mesafesi hatası, yaw hatası, hedef kaybında Hold'a geçiş süresi, stick hareketinde mod değişmediği, RC anahtarıyla çıkış
  - [x] 6.5 Adım 5: Gerçek uçuş
    - X500 V2 + Pixhawk 6C + Pi 5, yalnızca SITL metrikleri geçtikten sonra
  - [x] 6.6 Grup 6 kontrollerini çalıştır
    - YALNIZCA 6.1'deki kontrolleri çalıştır

**Acceptance Criteria:**
- 6.1'deki kontroller geçer.
- Akış `testing/test-writing.md` piramidiyle uyumludur (birim → SITL → gerçek uçuş). Göz kararı değerlendirme yoktur, metrikler pyulog ile ölçülür.

### Son Gözden Geçirme

#### Task Group 7: Çapraz Tutarlılık, Sözdizimi ve Kapsam Kontrolü
**Dependencies:** Task Groups 1-6

- [x] 7.0 İki şemayı birlikte gözden geçir ve kritik boşlukları kapat
  - [x] 7.1 Grup 1–6 kontrollerini gözden geçir
    - Toplam mevcut kontrol: yaklaşık 25–40
  - [x] 7.2 Mermaid sözdizimi doğrulaması
    - `mmdc` bu ortamda kurulu değil (node/npx de yok). Yeni araç kurmak `tez/env/VERSIONS.md` kaydı ve kullanıcı onayı gerektirir, bu yüzden **kurulmaz**. `mmdc` sonradan bulunursa her blok onunla render edilir.
    - Elle kontrol listesi: her blok ` ```mermaid ` + `flowchart` ile başlar; özel karakterli etiketler tırnaklı; tırnak içinde çıplak `"` yok; node id'leri ASCII ve benzersiz; `end`/`subgraph`/`class` anahtar kelimeleri id olarak kullanılmamış; her `subgraph` bir `end` ile kapanıyor; kenar etiketleri `-- "..." -->` veya `-->|"..."|` biçiminde; `classDef`/`class`/`linkStyle` satırları geçerli; `linkStyle` indeksleri kenar sayısını aşmıyor
  - [x] 7.3 Şema 1 ↔ Şema 2 terminoloji tutarlılığı
    - Aynı kavram iki şemada aynı adla geçer (ör. "Vehicle-carried NED LOS", "down angle", "slant range", "Hedefin yerel NED konumu")
    - Şema 1'deki her ana zincir adımının Şema 2 (B)'de karşılığı vardır
  - [x] 7.4 TBD ve etiket kapsamı
    - Şema 2'de altı TBD görünür: ICD, yükseklik kaynağı, nihai guidance yasası, setpoint tipi, ön koşul onayı, süre parametreleri
    - Task Group 1'de "(doğrulanacak)" sınıflanan her ad şemada bu etiketi taşır, "(öneri)" adlar öneri olarak işaretlidir
  - [x] 7.5 Kapsam kontrolü
    - Şemalarda yok: Follow Me (`FlightTaskAutoFollowTarget`, `NAVIGATION_STATE_AUTO_FOLLOW_TARGET`) kullanımı, yeni FlightTask/`nav_state`, yeni MAVLink veya uORB mesajı, ECEF/WGS84 dönüşümü, ROS 2/uXRCE-DDS, gimbal, çoklu hedef/re-ID, rangefinder, mod içinde otomatik kalkış/iniş, guidance yasası denklemlerinin kopyası
  - [x] 7.6 Gerekirse en fazla 10 ek kontrol yaz
    - Yalnızca kritik boşluklar için (ör. bir topic'in kenar etiketi eksik, bir user story şemadan izlenemiyor)
  - [x] 7.7 Repo hijyeni ve özellik kontrollerini çalıştır
    - YALNIZCA bu spec'in kontrollerini çalıştır (1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.6)
    - `git status`: yalnızca `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/` altında değişiklik var (`diagrams/` ve `tasks.md`). Branch `yusuf/agent-os-denemeleri-ve-sema-olusturma` kalır, commit atılmaz.
    - Kaynakla çelişen spec adları (bkz. 1.7) ve kalan "(doğrulanacak)" maddeleri kullanıcıya kısa listeyle raporlanır

**Acceptance Criteria:**
- Tüm özellik kontrolleri geçer (yaklaşık 25–50 kontrol).
- İki şema sözdizimsel olarak geçerli, birbirleriyle tutarlı ve spec'in in-scope / out-of-scope sınırlarına uygundur.
- Spec klasörü dışında hiçbir dosya değişmemiştir.

## Execution Order

Önerilen uygulama sırası:
1. Kaynak Doğrulama (Task Group 1): sonraki tüm grupların ad kaynağıdır
2. Şema 1 (Task Group 2): Task Group 1'den sonra, Task Group 3–6 ile paralel yürüyebilir
3. Şema 2 (A) iskelet ve mod kaydı (Task Group 3)
4. Şema 2 (B) run loop ve kontrolcü zinciri (Task Group 4)
5. Şema 2 (C) mod seçimi, çıkış ve failsafe (Task Group 5)
6. Şema 2 (D) doğrulama akışı (Task Group 6)
7. Çapraz tutarlılık, sözdizimi ve kapsam kontrolü (Task Group 7)
