# Task Group 1: PX4 v1.17.0 Ad Envanteri ve Doğrulama

Bu dosya, Şema 1 ve Şema 2'de (Task Group 2–7) kullanılacak her adın PX4 v1.17.0 kaynağına karşı doğrulama sonucudur. Sonraki gruplar adları **buradan** alır.

- Kaynak: `/home/yusuf/Desktop/Projects/Auto-Follow/Autopilot`, branch `yusuf/agent-os-denemeleri-ve-sema-olusturma`, commit `503566a6bc` (`git describe`: `tez-base-1.17.0-14-g503566a6bc`). Tüm yollar repo köküne göredir. Satır numaraları bu commit içindir.
- Konum notu: tasks.md envanterin scratch alanında tutulmasını söylüyor. Orkestratör, sonraki grupların görebilmesi için bu dosyanın Agent OS implementation-report klasörüne yazılmasını istedi. Dosya spec klasörü içindedir, upstream dosyası değişmedi.
- Yalnızca okuma yapıldı. Hiçbir PX4 dosyası değiştirilmedi.

## Etiketler

| Etiket | Anlamı | Şemada |
|---|---|---|
| doğrulandı | Ad (ve varsa değer) kaynakta birebir bulundu | Etiketsiz yazılır |
| (doğrulanacak) | Ad kaynakta var ama davranış yalnızca SITL/donanımda kanıtlanabilir, ya da ad kaynakta yok/kesin değil | `(doğrulanacak)` eki |
| (öneri) | Kaynakta yok, bu proje için önerilen ad (`TEZ_FOL_*`, `tez_follow`, `CONFIG_MODULES_TEZ_FOLLOW`, `*_gz_x500_tez*`) | `(öneri)` eki |
| TBD | Ekipçe karar verilecek açık konu | `classDef tbd` node |
| planlanan | Upstream'de olmayan, izinli/izin bekleyen yol | `(öneri)` ile birlikte |

## 1.1 Doğrulama kontrolleri (K1–K5)

Kontroller grep tabanlıdır, kabukta tek komut olarak çalıştırıldı. Spec klasörüne script eklenmedi.

- **K1:** Her uORB topic için `msg/` veya `msg/versioned/` altında `.msg` var, ya da bir `.msg` içindeki `# TOPICS` satırında geçiyor.
- **K2:** Şemada kullanılacak her alan ilgili `.msg` içinde birebir mevcut (tip dahil: `char[25] name`, `char[10] name`).
- **K3:** Her PX4 parametresi `module.yaml` veya `*_params.c` içinde tanımlı. `TEZ_FOL_*` kaynakta **olmamalı** (öneri olduğu teyit edilir).
- **K4:** Her dosya yolu repoda mevcut. Planlanan yollar (`src/modules/tez_follow`, `*_gz_x500_tez*`) **yok** olmalı. `tez/pin/allowed-paths.txt` içinde `src/modules/tez_*` ve `.px4board` **olmamalı**.
- **K5:** Her enum/sabit değeri kaynaktaki değerle aynı.

## 1.2 uORB topic'leri ve alanları

### Topic → mesaj dosyası (K1)

| Topic | Durum | Kaynak | Not |
|---|---|---|---|
| `register_ext_component_request` | doğrulandı | `msg/versioned/RegisterExtComponentRequest.msg` | `ORB_QUEUE_LENGTH = 2` (:24) |
| `register_ext_component_reply` | doğrulandı | `msg/versioned/RegisterExtComponentReply.msg` | `ORB_QUEUE_LENGTH = 2` (:15) |
| `unregister_ext_component` | doğrulandı | `msg/versioned/UnregisterExtComponent.msg` | |
| `arming_check_request` | doğrulandı | `msg/versioned/ArmingCheckRequest.msg` | |
| `arming_check_reply` | doğrulandı | `msg/versioned/ArmingCheckReply.msg` | `ORB_QUEUE_LENGTH = 4` (:43) |
| `config_control_setpoints` | doğrulandı | `msg/versioned/VehicleControlMode.msg:24` (`# TOPICS vehicle_control_mode config_control_setpoints`) | Tip `vehicle_control_mode_s` |
| `vehicle_control_mode` | doğrulandı | `msg/versioned/VehicleControlMode.msg` | |
| `debug_vect` | doğrulandı | `msg/DebugVect.msg` | versioned değil |
| `trajectory_setpoint` | doğrulandı | `msg/versioned/TrajectorySetpoint.msg` | |
| `goto_setpoint` | doğrulandı | `msg/versioned/GotoSetpoint.msg` | Alternatif setpoint (TBD) |
| `vehicle_attitude` | doğrulandı | `msg/versioned/VehicleAttitude.msg:14` | |
| `vehicle_local_position` | doğrulandı | `msg/versioned/VehicleLocalPosition.msg:87` | |
| `vehicle_status` | doğrulandı | `msg/versioned/VehicleStatus.msg` | |
| `vehicle_land_detected` | doğrulandı | `msg/versioned/VehicleLandDetected.msg` | |
| `vehicle_command` | doğrulandı | `msg/versioned/VehicleCommand.msg:200` | |
| `vehicle_attitude_setpoint` | doğrulandı | `msg/versioned/VehicleAttitudeSetpoint.msg` | |
| `vehicle_rates_setpoint` | doğrulandı | `msg/versioned/VehicleRatesSetpoint.msg` | |
| `vehicle_torque_setpoint` | doğrulandı | `msg/VehicleTorqueSetpoint.msg` | |
| `vehicle_thrust_setpoint` | doğrulandı | `msg/VehicleThrustSetpoint.msg` | |
| `actuator_motors` | doğrulandı | `msg/versioned/ActuatorMotors.msg` | |
| `mode_completed` | doğrulandı | `msg/versioned/ModeCompleted.msg` | Şemada zorunlu değil |

### Alanlar (K2)

| Topic.alan | Tip | Durum | Kaynak |
|---|---|---|---|
| `register_ext_component_request.request_id` | uint64 | doğrulandı | `RegisterExtComponentRequest.msg:7` |
| `register_ext_component_request.name` | char[25] | doğrulandı | `RegisterExtComponentRequest.msg:8` |
| `register_ext_component_request.px4_ros2_api_version` | uint16 | doğrulandı | `RegisterExtComponentRequest.msg:12` |
| `LATEST_PX4_ROS2_API_VERSION` | = 1 | doğrulandı | `RegisterExtComponentRequest.msg:10` |
| `register_ext_component_request.register_arming_check` | bool | doğrulandı | `RegisterExtComponentRequest.msg:15` |
| `register_ext_component_request.register_mode` | bool | doğrulandı | `RegisterExtComponentRequest.msg:16` (mod kaydı arming check kaydını da gerektirir) |
| `register_ext_component_reply.request_id` | uint64 | doğrulandı | `RegisterExtComponentReply.msg:5` |
| `register_ext_component_reply.name` | char[25] | doğrulandı | `RegisterExtComponentReply.msg:6` |
| `register_ext_component_reply.success` | bool | doğrulandı | `RegisterExtComponentReply.msg:10` |
| `register_ext_component_reply.arming_check_id` | int8 | doğrulandı | `RegisterExtComponentReply.msg:11` (-1 geçersiz) |
| `register_ext_component_reply.mode_id` | int8 | doğrulandı | `RegisterExtComponentReply.msg:12` (-1 geçersiz) |
| `unregister_ext_component.name` | char[25] | doğrulandı | `UnregisterExtComponent.msg:5` |
| `unregister_ext_component.arming_check_id` | int8 | doğrulandı | `UnregisterExtComponent.msg:7` |
| `unregister_ext_component.mode_id` | int8 | doğrulandı | `UnregisterExtComponent.msg:8` |
| `arming_check_request.request_id` | uint8 | doğrulandı | `ArmingCheckRequest.msg:14` |
| `arming_check_request.valid_registrations_mask` | uint32 | doğrulandı | `ArmingCheckRequest.msg:16` |
| `arming_check_reply.request_id` | uint8 | doğrulandı | `ArmingCheckReply.msg:14` (isteğin `request_id`'si geri yazılmalı, bkz. F1) |
| `arming_check_reply.registration_id` | uint8 | doğrulandı | `ArmingCheckReply.msg:15` |
| `arming_check_reply.can_arm_and_run` | bool | doğrulandı | `ArmingCheckReply.msg:24` |
| `arming_check_reply.mode_req_angular_velocity` | bool | doğrulandı | `ArmingCheckReply.msg:31` |
| `arming_check_reply.mode_req_attitude` | bool | doğrulandı | `ArmingCheckReply.msg:32` |
| `arming_check_reply.mode_req_local_alt` | bool | doğrulandı | `ArmingCheckReply.msg:33` |
| `arming_check_reply.mode_req_local_position` | bool | doğrulandı | `ArmingCheckReply.msg:34` |
| `arming_check_reply.mode_req_prevent_arming` | bool | doğrulandı | `ArmingCheckReply.msg:40` |
| `arming_check_reply.mode_req_manual_control` | bool | doğrulandı | `ArmingCheckReply.msg:41` |
| `config_control_setpoints.source_id` | uint8 | doğrulandı | `VehicleControlMode.msg:22` ("Mode ID (nav_state)") |
| `flag_armed` | bool | doğrulandı | `VehicleControlMode.msg:4` (commander üzerine yazar, F3) |
| `flag_multicopter_position_control_enabled` | bool | doğrulandı | `VehicleControlMode.msg:6` (commander yeniden türetir, F3) |
| `flag_control_manual_enabled` | bool | doğrulandı | `VehicleControlMode.msg:8` |
| `flag_control_auto_enabled` | bool | doğrulandı | `VehicleControlMode.msg:9` |
| `flag_control_offboard_enabled` | bool | doğrulandı | `VehicleControlMode.msg:10` |
| `flag_control_position_enabled` | bool | doğrulandı | `VehicleControlMode.msg:11` |
| `flag_control_velocity_enabled` | bool | doğrulandı | `VehicleControlMode.msg:12` |
| `flag_control_altitude_enabled` | bool | doğrulandı | `VehicleControlMode.msg:13` |
| `flag_control_climb_rate_enabled` | bool | doğrulandı | `VehicleControlMode.msg:14` |
| `flag_control_acceleration_enabled` | bool | doğrulandı | `VehicleControlMode.msg:15` |
| `flag_control_attitude_enabled` | bool | doğrulandı | `VehicleControlMode.msg:16` |
| `flag_control_rates_enabled` | bool | doğrulandı | `VehicleControlMode.msg:17` |
| `flag_control_allocation_enabled` | bool | doğrulandı | `VehicleControlMode.msg:18` |
| `flag_control_termination_enabled` | bool | doğrulandı | `VehicleControlMode.msg:19` |
| `debug_vect.timestamp` | uint64 | doğrulandı | `DebugVect.msg:1` |
| `debug_vect.name` | char[10] | doğrulandı | `DebugVect.msg:2` (kullanılabilir en fazla 9 karakter, F8) |
| `debug_vect.x` / `.y` / `.z` | float32 | doğrulandı | `DebugVect.msg:3-5` |
| `trajectory_setpoint.timestamp` | uint64 | doğrulandı | `TrajectorySetpoint.msg:8` |
| `trajectory_setpoint.position` | float32[3] | doğrulandı | `TrajectorySetpoint.msg:11` (NED, m) |
| `trajectory_setpoint.velocity` | float32[3] | doğrulandı | `TrajectorySetpoint.msg:12` (NED, m/s) |
| `trajectory_setpoint.acceleration` | float32[3] | doğrulandı | `TrajectorySetpoint.msg:13` (NaN bırakılır) |
| `trajectory_setpoint.yaw` | float32 | doğrulandı | `TrajectorySetpoint.msg:16` (rad) |
| `trajectory_setpoint.yawspeed` | float32 | doğrulandı | `TrajectorySetpoint.msg:17` (rad/s) |
| "NaN = kontrol edilmez" kuralı | | doğrulandı | `TrajectorySetpoint.msg:4` |
| `goto_setpoint.position` | float32[3] | doğrulandı | `GotoSetpoint.msg:13` |
| `goto_setpoint.flag_control_heading` / `heading` | bool / float32 | doğrulandı | `GotoSetpoint.msg:15-16` |
| `vehicle_attitude.q` | float32[4] | doğrulandı | `VehicleAttitude.msg:10` ("FRD body frame to the NED earth frame") |
| `vehicle_local_position.xy_valid` / `z_valid` | bool | doğrulandı | `VehicleLocalPosition.msg:9-10` |
| `vehicle_local_position.x` / `y` / `z` | float32 | doğrulandı | `VehicleLocalPosition.msg:15-17` (z: Down, negatif irtifa) |
| `vehicle_local_position.xy_reset_counter` | uint8 | doğrulandı | `VehicleLocalPosition.msg:21` |
| `vehicle_local_position.z_reset_counter` | uint8 | doğrulandı | `VehicleLocalPosition.msg:23` |
| `vehicle_local_position.heading` | float32 | doğrulandı | `VehicleLocalPosition.msg:42` |
| `vehicle_status.nav_state` | uint8 | doğrulandı | `VehicleStatus.msg:35` |
| `vehicle_land_detected.landed` | bool | doğrulandı | `VehicleLandDetected.msg:8` |
| `vehicle_command.param1` | float32 | doğrulandı | `VehicleCommand.msg:183` |
| `vehicle_command.command` | uint32 | doğrulandı | `VehicleCommand.msg:190` |
| `vehicle_command.target_system` / `target_component` | uint8 | doğrulandı | `VehicleCommand.msg:191-192` (bkz. F15) |
| `vehicle_command.source_component` | uint16 | doğrulandı | `VehicleCommand.msg:194` |

### Kontrolcü zinciri (yayıncı → topic → tüketici)

| Adım | Durum | Kaynak |
|---|---|---|
| `mc_pos_control` abone: `trajectory_setpoint`, `vehicle_local_position`, `vehicle_control_mode` | doğrulandı | `src/modules/mc_pos_control/MulticopterPositionControl.hpp:102,107,109` |
| `mc_pos_control` → `vehicle_attitude_setpoint` | doğrulandı | `MulticopterPositionControl.hpp:99` |
| `mc_att_control` abone `vehicle_attitude_setpoint` → yayın `vehicle_rates_setpoint` | doğrulandı | `src/modules/mc_att_control/mc_att_control.hpp:105,115` |
| `mc_rate_control` abone `vehicle_rates_setpoint` → yayın `vehicle_thrust_setpoint` + `vehicle_torque_setpoint` | doğrulandı | `src/modules/mc_rate_control/MulticopterRateControl.hpp:100,110,111` |
| `control_allocator` abone `vehicle_torque_setpoint` + `vehicle_thrust_setpoint` → yayın `actuator_motors` | doğrulandı | `src/modules/control_allocator/ControlAllocator.hpp:178,179,187` |

## 1.3 Commander ve mod yönetimi davranışı

| Ad / davranış | Durum | Kaynak | Not |
|---|---|---|---|
| `ModeManagement::checkNewRegistrations` (kayıt akışı) | doğrulandı | `src/modules/commander/ModeManagement.cpp:218-335` | `register_mode` için `register_arming_check` zorunlu (:244-246). Cevap `register_ext_component_reply` (:333) |
| `mode_id` atama (`Modes::addExternalMode`) | doğrulandı | `ModeManagement.cpp:95`, `:297-298` | `mode_id` ∈ `NAVIGATION_STATE_EXTERNAL1..8` (`ModeManagement.hpp:78-79`) |
| `COM_MODE%d_HASH` (FNV-1a) | doğrulandı | `ModeManagement.cpp:97` (`hash_32_fnv1a_const`), `:111`, `:168-172` | Aynı ad → aynı slot. İndeks 0..7 (F11) |
| "Not accepting registration requests while armed" | doğrulandı | `ModeManagement.cpp:378` | Yalnızca `armed && !COM_MODE_ARM_CHK` iken (`:371-373`, F14) |
| `ModeManagement::updateControlMode` | doğrulandı | `ModeManagement.cpp:521-536` | `Commander::updateControlMode` içinden çağrılır (`Commander.cpp:2606`) |
| `config_control_setpoints` işleme (`checkConfigControlSetpointUpdates`) | doğrulandı | `ModeManagement.cpp:582-602`, çağrı `:411` | `source_id` geçerli bir kayıtlı mod olmalı, yoksa "Control sp config request for invalid mode" |
| Commander bayrak üzerine yazma | doğrulandı | `src/modules/commander/Commander.cpp:2608-2615` | `flag_armed` ve `flag_multicopter_position_control_enabled` commander'da yeniden hesaplanır (F3) |
| `checkUnregistrations` | doğrulandı | `ModeManagement.cpp:337-364` | Aktif mod kaydı silinirse **Hold** (`AUTO_LOITER`) (:357-361, F4) |
| `UPDATE_INTERVAL = 300_ms` | doğrulandı | `src/modules/commander/HealthAndArmingChecks/checks/externalChecks.hpp:70` | `arming_check_request` periyodu, yayın `externalChecks.cpp:285-293` |
| `REQUEST_TIMEOUT = 50_ms` | doğrulandı | `externalChecks.hpp:69` | Cevap süresi, kontrol `externalChecks.cpp:256` |
| `NUM_NO_REPLY_UNTIL_UNRESPONSIVE = 3` | doğrulandı | `externalChecks.hpp:72` | Tetik `++num_no_response > 3` (`externalChecks.cpp:262-265`, F2). Kayıt sonrası ilk cevaba kadar 10 (`externalChecks.hpp:75`) |
| Cevap eşleşmesi `request_id` + 300 ms tazelik | doğrulandı | `externalChecks.cpp:233-235` | F1 |
| `can_arm_and_run=false` → `mode_req_other` | doğrulandı | `externalChecks.cpp:158-159`, unresponsive `:130-134` | Mod çalışamaz sayılır |
| `Failsafe::checkModeFallback` → RTL | doğrulandı | `src/modules/commander/failsafe/failsafe.cpp:659-704` (`action = Action::RTL;` :700) | Hold değil, RTL |
| `Commander::manualControlCheck` stick override | doğrulandı (kod) / (doğrulanacak) SITL | `Commander.cpp:2926-2972` | Koşullar `:2936-2955`, Position'a geçiş `:2960`. Ek koşullar F7 |
| `RcOverrideBits::AUTO_MODE_BIT` / `OFFBOARD_MODE_BIT` | doğrulandı | `src/modules/commander/Commander.hpp:211-213` | bit 0 / bit 1 |
| `failsafe/framework.cpp` override | doğrulandı (kod) / (doğrulanacak) SITL | `src/modules/commander/failsafe/framework.cpp:502-531` | Stick isteği yalnızca `_failsafe_user_override_request` ile gelir (`Commander.cpp:2357,2967`). Ek yol yok (F7) |
| `VEHICLE_CMD_DO_SET_MODE` işleme | doğrulandı | `Commander.cpp:800-930`, external eşleme `:863-865` | `PX4_CUSTOM_SUB_MODE_EXTERNALx` → `NAVIGATION_STATE_EXTERNALx` |
| `VEHICLE_CMD_SET_NAV_STATE` işleme | doğrulandı (kod) / (doğrulanacak) SITL | `Commander.cpp:936-946` | `param1` → nav_state (`+0.5f` yuvarlama). Yorum: "Used from ROS". Modül içinden kullanım SITL'de doğrulanacak (F15) |
| Komut hedef filtresi | doğrulandı | `Commander.cpp:746-749` | `target_system`/`target_component` eşleşmeli veya 0 |
| `getSourceFromCommand` | doğrulandı | `Commander.cpp:1559-1562` | `source_component < COMPONENT_MODE_EXECUTOR_START (1000)` → `ModeChangeSource::User` (`VehicleCommand.msg:198`) |
| `UserModeIntention::change` | doğrulandı | `src/modules/commander/UserModeIntention.cpp:44-92` | Disarm iken her zaman izin (`:55`), armed iken `canRun` (`:59`) |
| RC kaybı External Mode istisnası | doğrulandı (kod) / (doğrulanacak) SITL | `failsafe.cpp:479-492` | `COM_RCL_EXCEPT` bit 3 set değilse `NAV_RCL_ACT` uygulanır (F13) |
| `onDisarm` unresponsive mod → Hold | doğrulandı | `ModeManagement.cpp:487-489` | |

## 1.4 Kontrolcü ve MAVLink tarafı

| Ad / davranış | Durum | Kaynak | Not |
|---|---|---|---|
| `FlightModeManager::start_flight_task` → `FlightTaskIndex::None` (EXTERNAL1..8) | doğrulandı | `src/modules/flight_mode_manager/FlightModeManager.cpp:136-143` | |
| FMM `vehicle_constraints` yalnızca task aktifken yayınlanır | doğrulandı | `FlightModeManager.cpp:118-120`, `:338-364` | F6 |
| `MulticopterPositionControl::generateFailsafeSetpoint` | doğrulandı (koşullu) | `src/modules/mc_pos_control/MulticopterPositionControl.cpp:636-685`, çağrı `:442-449`, `:593` | Yalnızca pozisyon kontrolü yeni açıldıysa (F5) |
| `_time_position_control_enabled` (false→true geçişi) | doğrulandı | `MulticopterPositionControl.cpp:402-411` | F5 |
| EKF reset düzeltmesi `adjustSetpointForEKFResets` | doğrulandı | `MulticopterPositionControl.cpp:440`, `:687-730` | `xy_reset_counter`, `z_reset_counter`, `heading_reset_counter` |
| `want_takeoff` koşulu | doğrulandı | `MulticopterPositionControl.cpp:464-486` | Yalnızca `flag_control_offboard_enabled` iken mc_pos_control kendisi hesaplar (F6) |
| `goto_setpoint` yalnızca `trajectory_setpoint` güncellenmiyorsa | doğrulandı | `MulticopterPositionControl.cpp:429-436` | `GotoControl` (`src/modules/mc_pos_control/GotoControl/`) |
| `MavlinkReceiver::handle_message_debug_vect` | doğrulandı | `src/modules/mavlink/mavlink_receiver.cpp:2797-2812`, dispatch `:298-299` | `timestamp = hrt_absolute_time()` (:2804), `name[9]='\0'` (:2806), MAVLink `time_usec` atılır (F8) |
| MAVLink `DEBUG_VECT` (id 250) | doğrulandı | `src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml:6961-6968` | `name` char[10], `time_usec`, `x/y/z` |
| `streams/AVAILABLE_MODES.hpp` | doğrulandı | `src/modules/mavlink/streams/AVAILABLE_MODES.hpp:76`, `:93-118`, `:195-207` | Mod adı `register_ext_component_reply.name`'den önbelleğe alınır |
| `PX4_CUSTOM_MAIN_MODE_AUTO` | doğrulandı, = 4 | `src/modules/commander/px4_custom_mode.h:48` | enum `MANUAL = 1`'den sayılır |
| `PX4_CUSTOM_SUB_MODE_EXTERNAL1..8` | doğrulandı, = 11..18 | `px4_custom_mode.h:69-76` | `AUTO_READY = 1`'den sayılır |
| nav_state → custom mode eşlemesi | doğrulandı | `px4_custom_mode.h:195-197` (EXTERNAL1 örneği) | HEARTBEAT custom mode |
| `VEHICLE_CMD_DO_SET_MODE` | doğrulandı, = 176 | `msg/versioned/VehicleCommand.msg:35` | |
| `mc_nn_control` kayıt deseni | doğrulandı | `src/modules/mc_nn_control/mc_nn_control.cpp:132-143` (Register), `:146-155` (Unregister), `:158-172` (Configure), `:175-195` (ReplyToArmingCheck), `:198-212` (CheckModeRegistration) | |
| `mc_nn_control::Run()` sırası | doğrulandı | `mc_nn_control.cpp:436-477` | `should_exit` → kayıt gönder → cevabı bekle → arming check cevabı → `nav_state == _mode_id` |

## 1.5 Parametreler ve sabitler

| Ad | Durum | Kaynak | Değer / not |
|---|---|---|---|
| `COM_FLTMODE${i}` (`COM_FLTMODE1..6`) | doğrulandı | `src/modules/commander/module.yaml:18-60` | `instance_start: 1`, `num_instances: 6` |
| `COM_FLTMODE` 100..107 = External Mode 1..8 | doğrulandı | `module.yaml:42-49` | |
| `COM_MODE${i}_HASH` | doğrulandı | `module.yaml:5-16` | `num_instances: 8`, `volatile`, gerçek adlar `COM_MODE0_HASH..COM_MODE7_HASH` (F11) |
| `COM_RC_OVERRIDE` | doğrulandı | `src/modules/commander/commander_params.c:446` | Varsayılan 1. bit 0 auto, bit 1 offboard (:442-443) |
| `COM_RC_STICK_OV` | doğrulandı | `commander_params.c:461` | Varsayılan 30 % |
| `COM_RCL_EXCEPT` | doğrulandı | `commander_params.c:633` | Varsayılan 0. bit 3 = External Mode (:629) |
| `NAV_RCL_ACT` | doğrulandı | `commander_params.c:616` | Varsayılan 2 = Return |
| `COM_MODE_ARM_CHK` | doğrulandı | `commander_params.c:1048` | Varsayılan 0 (armed iken kayıt kapalı) |
| `MPC_XY_VEL_MAX` | doğrulandı | `src/modules/mc_pos_control/multicopter_position_control_limits_params.c:47` | 12 m/s |
| `MPC_Z_VEL_MAX_UP` | doğrulandı | `multicopter_position_control_limits_params.c:64` | 3 m/s |
| `MPC_Z_VEL_MAX_DN` | doğrulandı | `multicopter_position_control_limits_params.c:81` | 1.5 m/s |
| Tilt limiti: `MPC_TILTMAX_AIR` | doğrulandı | `multicopter_position_control_limits_params.c:96` | 45°. Spec "tilt" yerine bu ad yazılır |
| `MAV_${i}_CONFIG` → `MAV_1_CONFIG` | doğrulandı | `src/modules/mavlink/module.yaml:40-48` | Instance 1 = TELEM2 companion. Varsayılan boş (kapalı). TELEM 2 değeri 102 (`Tools/serial/generate_config.py:92-96`) |
| `MAV_${i}_MODE` → `MAV_1_MODE` | doğrulandı | `src/modules/mavlink/module.yaml:54-79` | Varsayılan `[0, 2, 0]` → `MAV_1_MODE = 2` (Onboard) |
| TELEM2 varsayılan baud | doğrulandı | `Tools/serial/generate_config.py:95` | 921600 |
| `SDLOG_PROFILE` | doğrulandı | `src/modules/logger/module.yaml:71-104` | bit 5 = Debug. Varsayılan 1, SITL 131 (`ROMFS/px4fmu_common/init.d-posix/rcS:182`) (F9) |
| `NAVIGATION_STATE_AUTO_LOITER` | doğrulandı, = 4 | `msg/versioned/VehicleStatus.msg:40` | Hold |
| `NAVIGATION_STATE_AUTO_FOLLOW_TARGET` | doğrulandı, = 19 | `VehicleStatus.msg:55` | Kapsam dışı, kullanılmaz |
| `NAVIGATION_STATE_EXTERNAL1..8` | doğrulandı, = 23..30 | `VehicleStatus.msg:59-66` | `NAVIGATION_STATE_MAX = 31` (:67) |
| `VEHICLE_CMD_SET_NAV_STATE` | doğrulandı, = 100001 | `msg/versioned/VehicleCommand.msg:114` | `param1 = nav_state` |
| `COMPONENT_MODE_EXECUTOR_START` | doğrulandı, = 1000 | `VehicleCommand.msg:198` | |
| `PX4_ISFINITE` | doğrulandı | `platforms/common/include/px4_platform_common/defines.h:58` | |

## 1.6 Dosya yolları, derleme ve başlatma

| Ad / yol | Durum | Kaynak | Not |
|---|---|---|---|
| `CONFIG_BOARD_SERIAL_TEL2="/dev/ttyS3"` | doğrulandı | `boards/px4/fmu-v6c/default.px4board:6` | FC tarafı. Pi tarafı `/dev/ttyAMA0` (Vision standardı), karıştırılmaz |
| `boards/px4/fmu-v6c/default.px4board` | doğrulandı | dosya mevcut | `CONFIG_MODULES_MC_NN_CONTROL` burada yok, `neural.px4board:65`'te var |
| `boards/px4/sitl/default.px4board` | doğrulandı | dosya mevcut | |
| SITL onboard UDP local 14580 / remote 14540 | doğrulandı | `ROMFS/px4fmu_common/init.d-posix/px4-rc.mavlink:4-5`, başlatma `:26` (`-m onboard`) | `+px4_instance` ofseti. Vision tarafı `udp:127.0.0.1:14540` ile uyumlu |
| `px4::wq_configurations::nav_and_controllers` | doğrulandı | `platforms/common/include/px4_platform_common/px4_work_queue/WorkQueueManager.hpp:71`, mc_nn_control kullanımı `mc_nn_control.cpp:65` | Spec'teki "(doğrulanacak)" kaldırılabilir |
| `src/examples/work_item` iskeleti | doğrulandı | `src/examples/work_item/WorkItemExample.hpp:55` (`ModuleBase` + `ModuleParams` + `px4::ScheduledWorkItem`) | Örnek `wq_configurations::test1` kullanır, `ScheduleOnInterval` yorumda (`WorkItemExample.cpp:38,57`) (F10) |
| `ScheduleOnInterval` | doğrulandı | `platforms/common/include/px4_platform_common/px4_work_queue/ScheduledWorkItem.hpp:62` | ~50 Hz değeri (öneri) |
| `/fs/microsd/etc/extras.txt` | doğrulandı (kod) / (doğrulanacak) donanım | `ROMFS/px4fmu_common/init.d/rcS:25`, kaynaklanma `:599-603` | commander (`:468-476`) ve `rc.serial` mavlink (`:508`) sonrası çalışır, disarm iken |
| `ROMFS/px4fmu_common/init.d-posix/airframes/` deseni | doğrulandı | 4001_gz_x500 vb. (`airframes/CMakeLists.txt:73-90`) | |
| `<id>_gz_x500_tez.post` | (doğrulanacak) / planlanan | `.post` mekanizması `ROMFS/px4fmu_common/init.d-posix/rcS:217-229`, `:362-363` | Yalnızca aynı ada sahip noktasız airframe (`<id>_gz_x500_tez`) `SYS_AUTOSTART` ile seçilirse kaynaklanır (F18). İzinli yol: `allowed-paths.txt:8-9` |
| `rc.mc_apps` (kilitli) | doğrulandı | `ROMFS/px4fmu_common/init.d/rc.mc_apps:40-42` | `mc_nn_control` `MC_NN_EN` ile buradan başlar. Tez modülü buraya eklenmez |
| `tez/pin/allowed-paths.txt`: `src/modules/tez_*` yok | doğrulandı (TBD ön koşul) | `tez/pin/allowed-paths.txt:1-14` | |
| `tez/pin/allowed-paths.txt`: iki `.px4board` yok | doğrulandı (TBD ön koşul) | aynı dosya | |
| `px4_add_unit_gtest` | doğrulandı | `cmake/px4_add_gtest.cmake:40` | Örnek kullanım `src/modules/commander/CMakeLists.txt` |
| `ULog` varsayılan topic'ler | doğrulandı | `src/modules/logger/logged_topics.cpp:131` (`trajectory_setpoint`), `:145` (`vehicle_local_position`), `:150` (`vehicle_status`), `:141` (`vehicle_control_mode`) | `debug_vect` yalnızca debug profilinde (`:289-294`, `:569-570`) (F9) |
| `follow_target_estimator` | doğrulandı (yalnızca fikir) | `src/modules/flight_mode_manager/tasks/AutoFollowTarget/follow_target_estimator/` | Kullanılmaz |
| `FlightTaskAutoFollowTarget` | doğrulandı (kapsam dışı) | `src/modules/flight_mode_manager/tasks/AutoFollowTarget/FlightTaskAutoFollowTarget.cpp` | Kullanılmaz |
| `/home/yusuf/Desktop/guidance-yasalari.md` | doğrulandı | dosya mevcut (repo dışı) | Yalnızca atıf |
| Pixhawk 6C airframe `SYS_AUTOSTART=4019` | doğrulandı | `ROMFS/px4fmu_common/init.d/airframes/4019_x500_v2` | SITL'de 4019 `4019_gz_x500_gimbal`dır, karıştırılmaz |

## 1.7 Sınıflandırma: öneri, planlanan ve TBD adlar

### (öneri) / planlanan

| Ad | Durum | Gerekçe |
|---|---|---|
| `tez_follow` (modül adı), `src/modules/tez_follow` | (öneri), planlanan | Kaynakta yok (K4). `allowed-paths.txt` onayı gerekir |
| `CONFIG_MODULES_TEZ_FOLLOW=y` | (öneri) | Kaynakta yok. Ad deseni `CONFIG_MODULES_MC_NN_CONTROL` (`boards/px4/fmu-v6c/neural.px4board:65`) ile tutarlı |
| `<id>_gz_x500_tez` / `<id>_gz_x500_tez.post` | (öneri), planlanan | Kaynakta yok. Yol izinli (`allowed-paths.txt:8`). `<id>` TBD |
| `TEZ_FOL_TOUT`, `TEZ_FOL_HOLD_T`, `TEZ_FOL_ALT`, `TEZ_FOL_DIST`, `TEZ_FOL_KP`, `TEZ_FOL_VXY_MAX`, `TEZ_FOL_VZ_MAX`, `TEZ_FOL_YR_MAX`, `TEZ_FOL_MIN_ALT` | (öneri) | Kaynakta yok (K3). Hepsi ≤16 karakter. Kesin adlar sonraki spec'te |
| Mod adı "Tez Follow" | (öneri) | `name` char[25] sınırına uyar. `COM_MODEx_HASH` nedeniyle sabit tutulmalı |
| `debug_vect.name` filtresi (ör. "TEZ_LOS") | (öneri), ICD TBD | En fazla 9 karakter (F8) |
| ~50 Hz `ScheduleOnInterval` | (öneri) | |

### TBD (açık konular: spec'teki altı + (D) bloğundan yedinci, Şema 2'de yedi node)

1. ICD (Pi → FC mesajı; `DEBUG_VECT` aday)
2. Yükseklik kaynağı (geçici `-vehicle_local_position.z`)
3. Nihai guidance yasası (`guidance-yasalari.md` atfı)
4. Setpoint tipi (`trajectory_setpoint` / `goto_setpoint` + `GotoControl`)
5. Ön koşul onayı (`allowed-paths.txt` + iki `.px4board`, ayrı PR)
6. Süre parametreleri (`TEZ_FOL_TOUT` ~1 s, `TEZ_FOL_HOLD_T` ~5–10 s)

7. Hareketli insan modeli ve tez dünyasının konumu (`Tools/simulation/gz` kilitli). Spec (D) bunu "Model konumu TBD" olarak verir. Task Group 6 (D) bloğunda TBD node'u olarak çizdi, Task Group 7 Açık konular tablosuna 7. satır olarak ekledi.

### Hâlâ "(doğrulanacak)" kalan maddeler

Bunlar kaynakta bulundu, ancak davranış yalnızca SITL veya donanımda kanıtlanabilir:

- External modda stick hareketinin modu değiştirmemesi (`Commander.cpp:2936-2955`, `framework.cpp:502-531`)
- Modülden `VEHICLE_CMD_SET_NAV_STATE` (100001, `param1 = 4`) ile Hold'a geçiş (`Commander.cpp:936-946`)
- `COM_RCL_EXCEPT` bit 3'ün RC kaybında etkisi (`failsafe.cpp:479-492`)
- Başlatma noktaları: SITL `<id>_gz_x500_tez.post` (airframe dosyası da gerekir), donanım `/fs/microsd/etc/extras.txt`
- `MAV_1_CONFIG = 102` / `MAV_1_MODE = 2` ile TELEM2 üzerinden Pi bağlantısı (donanım)
- Hedef NED durumu için yeni uORB mesajı gerekip gerekmediği (`msg/` kilitli, kullanıcıya sorulacak)

## Spec ile kaynak arasındaki farklar (Task Group 7 raporu için)

Şemaya kaynaktaki ad ve davranış yazılır. Aşağıdaki farklar kullanıcıya raporlanmalıdır.

- **F1. `arming_check_reply.request_id` eksik.** Spec'teki cevap alan listesinde `request_id` yok. Commander yalnızca `reply.request_id == _current_request_id` ve `reply.timestamp` son 300 ms içindeyse cevabı kabul eder (`externalChecks.cpp:233-235`). `mc_nn_control` bunu yazar (`mc_nn_control.cpp:180`). tasks.md 1.2'deki "`arming_check_request` / `arming_check_reply`: `registration_id`, `can_arm_and_run`, ..." gruplaması da hatalı: bu alanların hepsi `arming_check_reply`'dadır. `arming_check_request` yalnızca `request_id` ve `valid_registrations_mask` taşır.
- **F2. "3 cevapsız istek" eşiği.** Sabit `NUM_NO_REPLY_UNTIL_UNRESPONSIVE = 3`, ancak koşul `++num_no_response > 3`. Yani mod 4. ardışık cevapsız istekte unresponsive olur. Kayıttan sonra ilk cevaba kadar eşik 10'dur (`externalChecks.hpp:72-75`, `externalChecks.cpp:262-265`). Şemada "3 cevapsız istek sınırı (`NUM_NO_REPLY_UNTIL_UNRESPONSIVE`) aşılınca" yazılması önerilir.
- **F3. `config_control_setpoints` "birebir" kullanılmaz.** `Commander::updateControlMode` modülün yapılandırmasını alır, ama `flag_armed` ve `flag_multicopter_position_control_enabled` alanlarının üzerine yazar. İkincisini altitude/climb_rate/position/velocity/acceleration bayraklarından yeniden türetir (`Commander.cpp:2608-2615`). Spec'in true listesiyle sonuç yine true olur, yani davranış farkı yok. Spec'teki "mc_nn_control pozisyon kontrolünü kapatır" ifadesi kaynağa göre şöyle yazılmalı: "mc_nn_control config'inde `flag_multicopter_position_control_enabled=false` yazar" (`mc_nn_control.cpp:164`). Aynı config `flag_control_climb_rate_enabled=true` yazdığı için (`:168`) commander bu bayrağı yeniden true türetir.
- **F4. Kapanışta Hold, çökme/unresponsive'de RTL.** Mod aktifken `unregister_ext_component` gelirse commander **Hold**'a (`AUTO_LOITER`) geçer (`ModeManagement.cpp:357-361`). RTL yalnızca modül cevap vermezse/çökerse `checkModeFallback` ile olur (`failsafe.cpp:700`). (A) kapanış ve (C) failsafe bloklarında bu ayrım gösterilmeli.
- **F5. `generateFailsafeSetpoint` koşullu.** Failsafe setpoint yalnızca `flag_multicopter_position_control_enabled` false'tan true'ya geçtiğinde ve o andan sonra yeni `trajectory_setpoint` gelmediyse üretilir (`MulticopterPositionControl.cpp:402-406`, `:442-449`). Position/Hold'dan (bayrak zaten true) moda geçişte mc_pos_control, modül yayınlayana kadar FlightTask'ın **son `trajectory_setpoint`'ini** kullanmaya devam eder. Bunun için bir tazelik zaman aşımı yoktur. "İlk çevrimde setpoint yayınla" kuralı geçerli, hatta daha kritik. Şema notu: "aksi halde son FlightTask setpoint'i (pozisyon kontrolü yeni açıldıysa `generateFailsafeSetpoint`) kullanılır".
- **F6. `want_takeoff`.** mc_pos_control `want_takeoff`'u yalnızca `flag_control_offboard_enabled` iken kendisi hesaplar (`MulticopterPositionControl.cpp:464-486`). Diğer durumlarda `vehicle_constraints`'ten okur. FMM bunu yalnızca bir FlightTask aktifken yayınlar (`FlightModeManager.cpp:118-120`, `:364`). External modda son (eski) değer kalır. Spec'in sonucu ("moda yerden kalkış yok") geçerli, zaten arm `mode_req_prevent_arming` ile engellenir.
- **F7. Stick override'ın ek koşulları.** Spec'teki üç koşul doğru, ancak eksik. Ayrıca `isArmed()`, `manual_control_setpoint.valid`, `sticks_moving` ve `VEHICLE_TYPE_ROTARY_WING` gerekir (`Commander.cpp:2931-2942`). `framework.cpp` stick takeover'ı yalnızca bu yoldan gelen `_failsafe_user_override_request` ile alır (`Commander.cpp:2357`, `:2967`). Aktif bir failsafe sırasında kullanıcı **mod anahtarıyla** takeover yapabilir (`framework.cpp:504-509`). SITL doğrulama maddesi olarak kalır.
- **F8. `debug_vect.name` en fazla 9 karakter.** uORB alanı `char[10]`, ancak alıcı son baytı `'\0'` yapar (`mavlink_receiver.cpp:2806`). MAVLink `time_usec` alanı uORB'ye taşınmaz. Timestamp FC'ye varış anıdır (`:2804`).
- **F9. ULog `debug_vect`'i varsayılan olarak kaydetmez.** `debug_vect` yalnızca `SDLOG_PROFILE` bit 5 (Debug) açıksa kaydedilir (`logged_topics.cpp:289-294`, `:569-570`). Varsayılan donanımda 1, SITL'de 131'dir. İkisi de bit 5'i içermez. Şemada "ULog: `debug_vect` (`SDLOG_PROFILE` bit 5 gerekir)" yazılmalı. `trajectory_setpoint` ve `vehicle_local_position` varsayılan sette var.
- **F10. `mc_nn_control` ScheduledWorkItem değil.** `mc_nn_control` `px4::WorkItem`'dır ve `vehicle_angular_velocity` callback'iyle çalışır (`mc_nn_control.hpp:83-84`, `mc_nn_control.cpp:65`, `:79`). `ScheduledWorkItem` + `ScheduleOnInterval` deseni `src/examples/work_item`'dan gelir. O örnek de `wq_configurations::test1` ve callback kullanır, `ScheduleOnInterval` yorum satırındadır. Spec'in birleşik ifadesi (work_item iskeleti + mc_nn_control ile aynı kuyruk) kaynakla çelişmez. Şemada iki kaynak ayrı belirtilmeli.
- **F11. `COM_MODE${i}_HASH` indeksi 0'dan başlar.** Gerçek parametreler `COM_MODE0_HASH..COM_MODE7_HASH`'dir (`generate_params.py:104` varsayılan `instance_start: 0`, `ModeManagement.cpp:109-111`). `COM_FLTMODE` ise 1..6'dır. Şemada `COM_MODE${i}_HASH` biçimi kalabilir.
- **F12. Tilt limiti adı.** Spec "tilt limiti" diyor. Kaynaktaki ad `MPC_TILTMAX_AIR` (`multicopter_position_control_limits_params.c:96`).
- **F13. `COM_RCL_EXCEPT` bit 3 kodda doğrulandı.** Varsayılan 0 olduğu için external modda RC kaybı `NAV_RCL_ACT` (varsayılan 2 = Return) uygular (`failsafe.cpp:479-492`). Bit 3 set edilirse RC kaybı yok sayılır. Spec'teki "(doğrulanacak)" kod düzeyinde kaldırılabilir. Davranış SITL maddesi olarak kalır.
- **F14. Armed iken kayıt reddi parametreye bağlı.** Red yalnızca `COM_MODE_ARM_CHK = 0` (varsayılan) iken olur (`ModeManagement.cpp:371-373`, `commander_params.c:1048`).
- **F15. `VEHICLE_CMD_SET_NAV_STATE`'in modülden kullanımı.** Komut `target_system`/`target_component` alanları vehicle_status `system_id`/`component_id` ile eşleşmeli veya 0 olmalı (`Commander.cpp:746-749`). `source_component < 1000` ise kaynak `User` sayılır (`:1559-1562`). Commander yorumu "Used from ROS". FC içi modülden kullanımı SITL'de "(doğrulanacak)".
- **F16. `/dev/ttyAMA0` ve `/dev/ttyS3`.** requirements.md'deki `/dev/ttyAMA0` Pi tarafıdır. FC tarafı TELEM2 = `/dev/ttyS3`'tür. `MAV_1_CONFIG` varsayılan olarak kapalıdır ve 102 (TELEM 2) yapılmalıdır. `MAV_1_MODE` varsayılanı zaten 2'dir (Onboard).
- **F17. Başlatma sırası uyumlu.** Donanımda `extras.txt` (`rcS:599`), commander (`:468-476`) ve `rc.serial` mavlink (`:508`) sonrasında çalışır. SITL'de `.post`, `px4-rc.mavlink` sonrasında çalışır (`init.d-posix/rcS:359-363`). Böylece `AVAILABLE_MODES` stream'i kayıt cevabını görebilir ve modül disarm iken kaydolur.
- **F18. SITL `.post` tek başına yetmez.** posix `rcS`, `.post` dosyasını yalnızca `SYS_AUTOSTART` ile seçilen noktasız airframe dosyasının yanında arar (`init.d-posix/rcS:217-229`, `:362-363`). Bu yüzden `<id>_gz_x500_tez` airframe dosyası ve `airframes/CMakeLists.txt` kaydı da gerekir. İkisi de izinli yollarda (`allowed-paths.txt:8-9`).

## 1.8 Kontrol sonuçları

Kontroller envanterdeki adlarla sınırlı tutuldu, tüm repo taranmadı.

| Kontrol | Geçen | Kalan | Not |
|---|---|---|---|
| K1 topic → `.msg` | 21 | 0 | `config_control_setpoints` `# TOPICS` ile bulundu |
| K2 alanlar | 69 | 0 | `char[25]` ve `char[10]` tipleri dahil |
| K3 parametreler | 15 | 0 | `TEZ_FOL_*` kaynakta yok → (öneri) teyit edildi |
| K4 yollar | 34 | 0 | Planlanan yollar ve `allowed-paths.txt` eksikleri teyit edildi |
| K5 değerler | 35 | 0 | |
| **Toplam** | **174** | **0** | |

İlk çalıştırmada K1'de 13 yanlış FAIL çıktı. Neden kontrol komutundaki bir hataydı: `ls a b`, dosyalardan biri yoksa sıfırdan farklı kodla döner. Dosya varlığı `[ -e ]` ile ayrı ayrı test edilerek tekrar çalıştırıldı ve 21/21 geçti. Kaynakta eksik ad yoktur.
