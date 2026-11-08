# Specification: Hedef Takip Uçuş Modu (Target Follow Flight Mode) — Akış Şemaları

## Goal
Pi'den gelen body FRD LOS ile bir insanı düz dünya kabulüyle takip eden, FC içinde çalışan ve QGC/RC ile seçilebilen bir PX4 v1.17.0 external uçuş modunun (`tez_follow`) tasarımını iki Mermaid akış şemasıyla belgelemek. Bu spec'in teslimatı yalnızca bu iki şemadır; modül kodu sonraki spec'te yazılır.

## User Stories
- Tez öğrencisi olarak, yaptığım işi referans görseldeki gibi sade tek sayfalık bir akışla anlatmak istiyorum ki danışmanım ve ekip arkadaşlarım zinciri tek bakışta anlasın.
- Modülü yazacak geliştirici olarak, PX4 v1.17.0'a özel ve doğrulanmış topic/parametre/dosya adlarıyla detaylı bir akış istiyorum ki kodlamaya doğrudan bu şemadan başlayabileyim.
- Pilot olarak, modu QGC'den veya RC mod anahtarından seçip yine mod anahtarıyla çıkmak istiyorum. Stick hareketi modu değiştirmemeli ve hedef kaybolursa araç güvenli şekilde Hold'a geçmeli.

## Specific Requirements

**Teslimat biçimi ve konumu**
- İki dosya create-tasks/implement-tasks adımlarında üretilir:
  - `diagrams/01-ust-seviye-akis.md`
  - `diagrams/02-px4-detayli-akis.md`
- Her dosya kısa bir Türkçe başlık/açıklama ve bir veya birkaç ` ```mermaid ` `flowchart` bloğu içerir. Metinler Türkçe, teknik terimler İngilizce.
- Parantez, eğik çizgi, iki nokta veya alt çizgi içeren node etiketleri `"..."` ile tırnaklanır. Mermaid'i bozan karakterlerden kaçınılır. `mmdc` varsa doğrulanır, yoksa sözdizimi elle gözden geçirilir.
- Açık konular, görsel olarak ayrışan (ör. kesik çizgili `classDef tbd`) "TBD" node'larıyla gösterilir. Kaynakta doğrulanamayan her ad "(doğrulanacak)" olarak etiketlenir.
- Şemalardaki her uORB topic, alan, parametre ve dosya yolu bu repodaki v1.17.0 kaynağıyla birebir eşleşmelidir. Ad uydurulmaz.
- Guidance yasalarının ayrıntısı şemalara kopyalanmaz. Yalnızca repo dışı `/home/yusuf/Desktop/guidance-yasalari.md` dokümanına atıf yapılır.

**Şema 1 — Üst seviye akış (sade)**
- Referans görselin dili kullanılır: tek sütun ana zincir, girdiler paralelkenar (`[/ ... /]`), işlemler yuvarlak köşeli kutu, yan girdiler yatay okla bağlanır.
- `subgraph "Raspberry Pi (Vision)"` içeriği:
  - Girdi: Kamera görüntüsü
  - Zincir: Model ile insan tespiti (piksel) → Kamera frame LOS → Body FRD LOS (montaj açısı dahil)
- Ara kutu "Pi → FC hedef LOS mesajı (ICD TBD)", iki subgraph arasında yer alır.
- `subgraph "Pixhawk 6C / PX4 — Tez uçuş modu"` zinciri:
  - Body LOS → Vehicle-carried NED LOS
  - → Aşağı açı (down angle) ve eğik mesafe (slant range)
  - → Hedefin yerel NED konumu
  - → Hedef kestirimi (konum/hız)
  - → Guidance (istenen durum: hız + yaw)
  - → PX4 kontrolcüleri
  - → Araç hedefi takip eder
- Yan girdiler (paralelkenar):
  - "UAV Roll / Pitch / Yaw" (ayrı veya tek kutu)
  - "İrtifa (baro / EKF)" (TBD işaretli)
  - "UAV yerel NED konumu"
  - "Pilot / QGC mod seçimi". Bu girdi modu başlatır ve FC subgraph'ına bağlanır.
- ECEF/WGS84 kutuları yer almaz (düz dünya kabulü). Node sayısı referans görsel mertebesinde tutulur (~15–18).

**Şema 2 — Genel yapı ve katmanlar**
- Okunabilirlik için tek dosyada 3–4 ayrı Mermaid bloğu kullanılır:
  - (A) Başlatma ve mod kaydı yaşam döngüsü
  - (B) Çevrim başına veri akışı (run loop)
  - (C) Mod seçimi, çıkış ve failsafe
  - (D) Doğrulama akışı
- Katmanlar subgraph olarak ayrılır: Pi (Vision), MAVLink, uORB, `tez_follow` modülü, commander, FlightModeManager ve kontrolcüler, QGC/RC, Doğrulama.
- Kenar etiketleri uORB topic adını taşır (ör. `-- "trajectory_setpoint" -->`). Böylece veri yolu topic düzeyinde izlenebilir.
- Açık konular TBD node'u olarak görünür:
  - ICD
  - Yükseklik kaynağı
  - Nihai guidance yasası
  - Setpoint tipi (`trajectory_setpoint` / `goto_setpoint`)
  - Ön koşul onayı (allowed-paths ve `.px4board`)
  - Süre parametreleri

**Şema 2 (A) — Başlatma ve external mode kaydı (`mc_nn_control` deseni)**
- Derleme:
  - `src/modules/tez_*` ve iki `.px4board` dosyası için `tez/pin/allowed-paths.txt` onayı gerekir (TBD, ayrı PR).
  - Ardından `CONFIG_MODULES_TEZ_FOLLOW=y` (`boards/px4/fmu-v6c/default.px4board`, `boards/px4/sitl/default.px4board`) ayarlanır.
- Modül iskeleti `src/examples/work_item` desenindedir: `ModuleBase` + `ModuleParams` + `px4::ScheduledWorkItem`, `px4::wq_configurations::nav_and_controllers` (mc_nn_control ile aynı; doğrulanacak), `ScheduleOnInterval` (~50 Hz önerisi).
- Başlatma noktası: upstream `rc.mc_apps` kilitlidir.
  - SITL: `ROMFS/px4fmu_common/init.d-posix/airframes/<id>_gz_x500_tez.post` (izinli yol)
  - Donanım: SD kart `/fs/microsd/etc/extras.txt`

  Her ikisi de "(doğrulanacak)" olarak etiketlenir.
- Kayıt **disarm iken** yapılmalıdır. `ModeManagement` armed iken gelen kaydı reddeder ("Not accepting registration requests while armed"). Bu yüzden modül boot'ta başlar.
- Kayıt akışı:
  - Modül `register_ext_component_request` yayınlar: `name` (char[25], ör. "Tez Follow"), `request_id`, `px4_ros2_api_version=1`, `register_arming_check=true`, `register_mode=true`.
  - Commander `register_ext_component_reply` döndürür: `success`, `arming_check_id`, `mode_id`.
  - `mode_id`, `NAVIGATION_STATE_EXTERNAL1..8` (23..30) değerlerinden biridir.
- `COM_MODE${i}_HASH`: mod adının FNV-1a hash'i parametreye yazılır, aynı ad hep aynı slota düşer. Bu yüzden mod adı sabit tutulur.
- Kayıt sonrası modül `config_control_setpoints` (tip `vehicle_control_mode_s`, `source_id = mode_id`) yayınlar. Commander bunu mod aktifken `vehicle_control_mode` olarak birebir kullanır (`ModeManagement::updateControlMode`).
  - true: `flag_multicopter_position_control_enabled`, `flag_control_position/velocity/altitude/climb_rate/acceleration/attitude/rates/allocation_enabled`, `flag_control_termination_enabled`
  - false: `flag_control_manual_enabled`, `flag_control_auto_enabled`, `flag_control_offboard_enabled`

  mc_nn_control'den farkı: o modül pozisyon kontrolünü kapatır, bu modül açık tutar.
- Kapanışta (`should_exit`) `unregister_ext_component` yayınlanır (`arming_check_id`, `mode_id`).

**Şema 2 (A devam) — Arming check ve "yalnızca havada" koşulu**
- Commander her ~300 ms'de bir `arming_check_request` yayınlar. Cevap 50 ms içinde gelmelidir. Üç cevapsız istek modu "unresponsive" yapar (`externalChecks.hpp`). Bu yüzden istek her çevrimde kontrol edilir.
- `arming_check_reply` içeriği:
  - `registration_id = arming_check_id`
  - `can_arm_and_run = !vehicle_land_detected.landed`
  - `mode_req_attitude`, `mode_req_local_position`, `mode_req_local_alt`, `mode_req_angular_velocity` true
  - `mode_req_prevent_arming=true` (bu modda arm edilemez)
  - `mode_req_manual_control=false`
- Disarm iken mod seçimine her zaman izin verilir (`UserModeIntention::change`), ancak arm `mode_req_prevent_arming` ile engellenir. Armed ve yerde iken `can_arm_and_run=false` olduğundan geçiş reddedilir.
- Uyarı (şemada not olarak):
  - Mod aktifken `can_arm_and_run=false` olursa veya mod unresponsive olursa, `Failsafe::checkModeFallback` **RTL**'e düşer, Hold'a değil.
  - Bu yüzden hedef kaybı için bu mekanizma kullanılmaz.
- External modda `mc_pos_control` `want_takeoff` üretmez (offboard bayrağı yok). Bu da moda yerden kalkış yapılamayacağını teyit eder.

**Şema 2 (B) — Çevrim başına veri akışı**
- Pi → TELEM2 (Pixhawk 6C `CONFIG_BOARD_SERIAL_TEL2="/dev/ttyS3"`, `MAV_1_CONFIG`/`MAV_1_MODE` onboard; değerler doğrulanacak).
  - SITL'de UDP onboard bağlantısı kullanılır (`px4-rc.mavlink`: local 14580 / remote 14540).
- `mavlink_receiver` adımı: aday mesaj `DEBUG_VECT` → `handle_message_debug_vect` → uORB `debug_vect` (`name` char[10], `x/y/z`).
  - Timestamp, FC'ye varış anı olarak basılır (`hrt_absolute_time()`).
  - Tümü "ICD TBD".
- Girdi doğrulama (geçmeyen örnek atılır ve sayılır):
  - `name` filtresi
  - `PX4_ISFINITE`
  - Birim vektör normu
  - Tazelik (`TEZ_FOL_TOUT`)
- Durum girdileri:
  - `vehicle_attitude.q` (FRD→NED quaternion)
  - `vehicle_local_position`: `x/y/z`, `xy_valid`, `z_valid`, `heading`, `xy_reset_counter`, `z_reset_counter`
  - `vehicle_status.nav_state` (mod aktif mi: `nav_state == mode_id`)
  - `vehicle_land_detected.landed`
- Hesap zinciri:
  - LOS_NED = R(q) · LOS_body.
  - Kontrol: `u_D > eşik` (LOS yere bakıyor mu).
  - h = yer düzlemine göre yükseklik. Geçici olarak `-vehicle_local_position.z` kullanılır (baro füzyonlu, TBD).
  - Slant range = h / u_D. Down angle = asin(u_D).
  - Hedef NED = UAV NED + range · LOS_NED.
- Hedef kestirimi: alfa-beta / low-pass ile hedef konumu ve hızı hesaplanır. Bu sadece fikir kaynağıdır (`follow_target_estimator`), Follow Me kullanılmaz.
- Guidance (çalışma temeli, TBD; bkz. guidance-yasalari.md):
  - Sabit irtifa (`TEZ_FOL_ALT` veya giriş irtifası)
  - Sabit yatay mesafe
  - P + hedef hızı ileri beslemesi
  - Yaw hedefe bakar
- Sınırlar (saturation): yatay/dikey hız, yaw hızı, min irtifa.
- Çıkış `trajectory_setpoint` (NED): `velocity`, `position[2]` veya `velocity[2]`, `yaw`/`yawspeed`. Kontrol edilmeyen alanlar NaN, `timestamp = hrt_absolute_time()`.
- Moda girişte ilk çevrimde setpoint yayınlanmalıdır. Aksi halde `mc_pos_control` kendi failsafe setpoint'ini üretir (`generateFailsafeSetpoint`).

**Şema 2 (B devam) — Aşağı akış kontrolcü zinciri ve loglama**
- `FlightModeManager::start_flight_task` `NAVIGATION_STATE_EXTERNAL1..8` iken `FlightTaskIndex::None` seçer, yani `trajectory_setpoint`'i yalnızca `tez_follow` yayınlar.
- Zincir:
  1. `mc_pos_control` (`trajectory_setpoint` + `vehicle_local_position` + `vehicle_control_mode`) → `vehicle_attitude_setpoint`
  2. `mc_att_control` → `vehicle_rates_setpoint`
  3. `mc_rate_control` → `vehicle_torque_setpoint` + `vehicle_thrust_setpoint`
  4. `control_allocator` → `actuator_motors` → ESC/motorlar
- `mc_pos_control` limitleri (`MPC_XY_VEL_MAX`, `MPC_Z_VEL_MAX_UP/DN`, tilt) modülün kendi saturation'ının üstünde ikinci bir emniyet katmanıdır.
- Loglama: ULog `debug_vect`, `trajectory_setpoint`, `vehicle_local_position` kaydeder. Hedef NED konumu/durumu için yeni uORB mesajı gerekiyorsa `msg/` kilitlidir. Bu durum "(doğrulanacak / kullanıcıya sor)" olarak not edilir.
- Parametreler `TEZ_` önekli ve `module.yaml` içinde tanımlıdır (öneri, ≤16 karakter): `TEZ_FOL_TOUT`, `TEZ_FOL_HOLD_T`, `TEZ_FOL_ALT`, `TEZ_FOL_DIST`, `TEZ_FOL_KP`, `TEZ_FOL_VXY_MAX`, `TEZ_FOL_VZ_MAX`, `TEZ_FOL_YR_MAX`, `TEZ_FOL_MIN_ALT`. Kesin adlar sonraki spec'te belirlenir.

**Şema 2 (C) — Mod seçimi, çıkış, hedef kaybı ve failsafe**
- QGC 5.1.4 akışı:
  - `AVAILABLE_MODES` stream'i external mod adını `register_ext_component_reply.name` alanından gösterir.
  - HEARTBEAT custom mode = `PX4_CUSTOM_MAIN_MODE_AUTO` + `PX4_CUSTOM_SUB_MODE_EXTERNALx` olur.
  - QGC `VEHICLE_CMD_DO_SET_MODE` gönderir, commander bunu `NAVIGATION_STATE_EXTERNALx`'e çevirir.
- RC: `COM_FLTMODE1..6 = 100..107` (External Mode 1..8) mod anahtarı ile seçim yapılır. Slot eşlemesi `COM_MODE${i}_HASH` ile kalıcıdır.
- Stick override: `Commander::manualControlCheck` override'ı yalnızca şu koşullarda uygular:
  - `flag_control_manual_enabled` false ise, ve
  - `flag_control_auto_enabled` veya `flag_control_offboard_enabled` true ise, ve
  - `COM_RC_OVERRIDE` ilgili biti açıksa.

  Bu modda iki bayrak false olduğundan stick modu değiştirmez. Bu bir SITL doğrulama maddesidir.
- Çıkış: pilot RC mod anahtarıyla veya QGC'den başka bir moda geçer. Modül `nav_state != mode_id` gördüğünde setpoint üretmeyi bırakır.
- Hedef kaybı:
  - `TEZ_FOL_TOUT` (~1 s) sonra konum tutulur (son NED konum) ve son yaw korunur.
  - `TEZ_FOL_HOLD_T` (~5–10 s) sonra modül `vehicle_command` `VEHICLE_CMD_SET_NAV_STATE` (100001, `param1 = NAVIGATION_STATE_AUTO_LOITER`) ile Hold ister (doğrulanacak).
  - Hedef geri gelirse takibe dönülür.
- Hold (auto) moduna geçildikten sonra PX4 varsayılanı geçerlidir: `COM_RC_OVERRIDE` bit 0 açık olduğundan Hold'da stick hareketi Position'a geçirir. Bu beklenen ve kabul edilen davranıştır.
- Failsafe:
  - Batarya, RC kaybı (`NAV_RCL_ACT`; `COM_RCL_EXCEPT` bit 3 = External Mode etkisi doğrulanacak), veri bağlantısı, geofence ve EKF failsafe'leri PX4 varsayılanında kalır.
  - `config_overrides` / `defer_failsafes` kullanılmaz.
  - Modül çökerse veya unresponsive olursa commander RTL'e düşer.
- Geçersiz durumlarda (`xy_valid`/`z_valid` false, `u_D` geçersiz, EKF reset) modül güvenli tarafta kalır: konum tutar ve yeni setpoint üretmez.

**Şema 2 (D) — Doğrulama akışı**
- Adımlar sırayla:
  1. GoogleTest (`px4_add_unit_gtest`): düz dünya geolocation, guidance ve ICD doğrulama saf fonksiyonları. Test durumları: nominal, sınır, NaN/Inf, zaman aşımı.
  2. Gazebo Harmonic SITL (`make px4_sitl gz_x500` / tez airframe, `HEADLESS=1`): hareketli insan modeli kullanılır. Model konumu TBD, çünkü `Tools/simulation/gz` kilitli.
  3. Sahte Pi: pymavlink ile `DEBUG_VECT` gönderen script (ICD TBD).
  4. ULog + pyulog metrikleri: takip mesafesi hatası, yaw hatası, hedef kaybında Hold'a geçiş süresi, stick hareketinde mod değişmediği, RC anahtarıyla çıkış.
  5. Ancak SITL geçtikten sonra gerçek uçuş (X500 V2 + Pixhawk 6C + Pi 5).
- Her adımdan sonra başarısızlıkta geri dönüş oku gösterilir. SITL parametre dosyası her testten önce sıfırlanır.

## Visual Design

**`planning/visuals/WhatsApp Image 2026-09-26 at 00.07.13.jpeg`**
- Beyaz zemin, siyah çerçeveli kutular, tek yönlü mavi oklar. Visio tarzı düşey ana zincir.
- Girdiler paralelkenar: piksel konumu, kamera öteleme/açıları, UAV roll/pitch/yaw, altitude, UAV WGS84.
- İşlemler yuvarlak köşeli kutu, kısa isim cümleleri: "LOS Vector in Camera/Body/Vehicle Carried NED Coordinate System" → "Down angle and Slant Distance Calculation" → "Target Location in ...".
- Yan girdiler ana zincirdeki ilgili kutuya yatay okla bağlanır (roll/pitch/yaw → NED LOS kutusu, altitude → down angle kutusu).
- Bu projede iki fark var:
  - Kamera→body adımları Pi subgraph'ında toplanır ve kamera montaj girdileri FC'ye çizilmez (montaj Pi'de dahil edilir).
  - ECEF/WGS84 adımları yerine "hedef yerel NED → kestirim → guidance → PX4 kontrolcüleri → araç" ile biter.
- İrtifa girdisi WGS84→ECEF kolundan değil, "baro / EKF (TBD)" paralelkenarından gelir.
- Görsel birebir kopyalanmaz. Yalnızca sadelik ve şekil dili taklit edilir (düşük-orta sadakat).

## Existing Code to Leverage

**`src/modules/mc_nn_control/mc_nn_control.cpp` / `.hpp`**
- FC içi external mode kaydının birebir emsali:
  - `RegisterNeuralFlightMode` → `CheckModeRegistration`
  - `ConfigureNeuralFlightMode` (`config_control_setpoints`)
  - `ReplyToArmingCheck`
  - `UnregisterNeuralFlightMode`
- `Run()` sırası şemada aynen izlenir: çıkış kontrolü → kayıt gönder → cevabı bekle → arming check cevabı → `vehicle_status.nav_state == _mode_id` → mod aktifse hesap.
- Fark: tez_follow `flag_multicopter_position_control_enabled=true` kullanır ve `actuator_motors` değil `trajectory_setpoint` yayınlar.

**`src/modules/commander/` (ModeManagement, Commander, failsafe, HealthAndArmingChecks)**
- Değiştirilmez, yalnızca davranış kaynağıdır:
  - `ModeManagement.cpp`: kayıt, `COM_MODE%d_HASH`, armed iken kayıt reddi, `updateControlMode`
  - `externalChecks.hpp/.cpp`: 300 ms / 50 ms / 3 cevapsız → unresponsive
  - `failsafe/failsafe.cpp` `checkModeFallback`: koşul sağlanmazsa RTL
  - `Commander.cpp` `manualControlCheck`: stick override koşulları; `VEHICLE_CMD_SET_NAV_STATE` işleyişi
  - `commander_params.c`: `COM_RC_OVERRIDE`, `COM_RC_STICK_OV`, `COM_RCL_EXCEPT`

**`src/modules/flight_mode_manager/FlightModeManager.cpp` ve `src/modules/mc_pos_control/`**
- `start_flight_task` external nav_state'lerde FlightTask'ı kapatır.
- `MulticopterPositionControl.cpp`: setpoint yoksa failsafe setpoint'e geçer, EKF reset düzeltmesi yapar, takeoff state ve hız limitlerini uygular.
- `GotoControl/` modülü, `goto_setpoint` alternatifi seçilirse kullanılacak mevcut yumuşatıcıdır (TBD).

**`src/examples/work_item/` ve `src/modules/mavlink/`**
- `WorkItemExample` modül iskeleti, `Kconfig`, `CMakeLists.txt` deseni.
- `mavlink_receiver.cpp` `handle_message_debug_vect`: ICD adayının FC'deki giriş noktası.
- `streams/AVAILABLE_MODES.hpp`: external mod adının QGC'ye nasıl gittiğini gösterir.

**`src/modules/flight_mode_manager/tasks/AutoFollowTarget/` (yalnızca fikir)**
- `follow_target_estimator` hedef konum/hız kestirimi için fikir kaynağıdır. Kod ve mod kullanılmaz (kullanıcı Follow Me'yi reddetti).

## Out of Scope
- Modülün gerçek C++ kodu, `module.yaml`, `CMakeLists.txt`, testler (sonraki spec)
- Bu spec adımında Mermaid dosyalarının çizilmesi (create-tasks/implement-tasks adımında üretilecek)
- Mevcut Follow Me (`FlightTaskAutoFollowTarget`, `NAVIGATION_STATE_AUTO_FOLLOW_TARGET`) kullanımı; yeni FlightTask veya yeni `nav_state`
- Upstream PX4 dosyası, `msg/`, `mavlink` submodule veya `Tools/simulation/gz` değişikliği; yeni MAVLink mesajı
- Vision tarafı: algılama modeli, kamera kalibrasyonu, piksel→body dönüşümü, kamera montaj açısının belirlenmesi
- Çoklu hedef seçimi / re-ID, gimbal kontrolü
- ROS 2 / uXRCE-DDS / px4-ros2-interface-lib
- ECEF/WGS84 dönüşümleri (WGS84 yalnızca opsiyonel gösterim)
- Engelden kaçınma, düz olmayan arazi, rangefinder entegrasyonu
- Mod içinde otomatik kalkış/iniş, `defer_failsafes` veya PX4 failsafe davranışlarının değiştirilmesi
