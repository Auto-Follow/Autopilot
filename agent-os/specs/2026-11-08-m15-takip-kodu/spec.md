# Specification: AUTO FOLLOW — Body FRD LOS'tan PX4 setpoint'ine takip modu (M15)

- **Görev:** https://github.com/Auto-Follow/Auto-Follow/issues/6 · yol haritası m15 (devamı m13, m16) · son teslim **2026-11-15**
- **Repo / dal:** Autopilot (PX4 v1.17.0, kilitli) · `ozellik/m15-takip-kodu` · spec klasörü `agent-os/specs/2026-11-08-m15-takip-kodu/`
- **Kaynaklar (bu spec yeni karar içermez):** `planning/requirements.md` (geçerli kararlar), `planning/karar-gunlugu.md` (KG; gerekçeler, son kayıt geçerli; write-spec turundaki cevaplar KG "Write-spec turu (2026-11-10)"), `rapor.md` (sade anlatım), `planning/visuals/`. Eski taslaklar `2026-10-15-m15-target-follow-flight-mode/` ve `2026-10-18-m15-fc-only-flow-diagrams/` **taslaktı, yerini bu spec aldı**; dosyalarına dokunulmaz.
- **Etiketler:** **Karar** = kullanıcı seçti · **Karar (öneri kabul)** = kullanıcı önerimizi kabul etti, sorun çıkarsa ilk bakılacak yer · **Varsayım** = ortak spec (m3–5) gelene kadar geçici · **Öneri — kullanıcı onayı bekliyor** = bu spec'te ilk kez önerilen, henüz onaylanmamış · **Açık** = karar yok · **(doğrulanacak)** = kaynakta kanıtlanamadı, SITL/donanımda görülecek.
- `dosya:satır` gösterimleri bu repodaki PX4 v1.17.0 içindir; çatı dosyaları `../agent-os/...` ile başlar.

## Goal

Raspberry Pi'nin gönderdiği "hedef drone'a göre şu yönde" bilgisinden (body FRD LOS birim vektörü + yaş + sıra no + hedef var/yok) yararlanarak, PX4'ün içinde **AUTO FOLLOW** adlı bir uçuş modu çalıştırmak: mod hedefin yerini düz zemin kabulüyle bulur, alpha-beta filtresiyle yumuşatır, hız tabanlı bir kuralla PX4'e `trajectory_setpoint` verir ve hedef kaybolunca önce yerinde bekleyip sonra Hold'a geçer. Kontrolcü yazılmaz; hızdan PWM'e kadar zincir PX4'ündür.

## User Stories

- Pilot olarak, QGC'den ya da RC anahtarından **AUTO FOLLOW** modunu seçmek istiyorum; böylece drone hedefi sabit irtifada, sabit açıyla ve kadrajın ortasında tutarak takip etsin.
- Güvenlikten sorumlu biri olarak, hedef ya da veri kaybolduğunda drone'un önce yerinde beklemesini, kısa süre sonra kendiliğinden **Hold**'a geçmesini ve pilot onayı olmadan takibe dönmemesini istiyorum.
- Kodu elle yazmayacak tez sahibi olarak, modun her iç durumunu (ham girdi, doğrulama, filtre girdisi/çıktısı, komutlar, durum) logda **kendi adlarıyla** görmek ve kod okumadan anlaşılacak dokümanlara sahip olmak istiyorum.

## Specific Requirements

**1. Entegrasyon ve mod kaydı (Karar 2-a, 3-a, 3.1-ii; iç yapı Karar (öneri kabul))**
- Kod, kendini PX4'e **external mode** olarak kaydettiren bir modüldür; kalıp `mc_nn_control`'dür (kayıt `src/modules/mc_nn_control/mc_nn_control.cpp:132-143`, yapılandırma `:158-172`, arming check cevabı `:175-195`, kayıt cevabı `:198-212`, `Run()` sırası `:436-477`).
- Modül/komut `auto_follow`, klasör `src/modules/auto_follow/`, açma satırı `CONFIG_MODULES_AUTO_FOLLOW=y`; hem `boards/px4/sitl/default.px4board` hem `boards/px4/fmu-v6c/default.px4board`'a eklenir (6C'ye de girer).
- Kayıt adı (QGC/RC'de görünen) **`AUTO FOLLOW`**; ad sabit kalır, çünkü PX4 slotu adın hash'iyle hatırlar (`COM_MODE${i}_HASH`, `src/modules/commander/module.yaml:5-16`). PX4 modu 23–30 aralığından bir `nav_state`'e atar (`msg/versioned/VehicleStatus.msg:59-66`).
- Yazım deseni `ModuleBase` + `ModuleParams` + `px4::ScheduledWorkItem` (`src/examples/work_item/WorkItemExample.hpp:55`); iş kuyruğu `nav_and_controllers` (`mc_nn_control.cpp:65`); `ScheduleOnInterval` ile **sabit 50 Hz** (parametre değil, Karar). Gerekçe: veri kesilse de modül dönmeli ki kesintiyi fark etsin.
- Kayıt yalnızca araç **disarm** iken kabul edilir (`src/modules/commander/ModeManagement.cpp:371-378`, `COM_MODE_ARM_CHK` varsayılan 0, `commander_params.c:1048`); modül boot'ta, arm edilmeden başlatılmalıdır. **Karar (2026-11-10, B2-b):** `ROMFS/px4fmu_common/init.d/rc.mc_apps`'e bir başlatma satırı eklenir. Bu dosya her multikopter açılışında arm'dan önce çalışır (SITL `ROMFS/px4fmu_common/init.d-posix/rcS:289`, 6C `ROMFS/px4fmu_common/init.d/rcS:485` → `rc.vehicle_setup:20-24`); `mc_nn_control` da böyle başlar (`rc.mc_apps:40-43`). Yedinci kilitli yoldur, Hüseyin onayı gerekir. Satır `AF_ENABLE` parametresine bağlıdır (**Karar A13-b**, 2026-11-10): `if param compare -s AF_ENABLE 1` (`MC_NN_EN` kalıbı, `rc.mc_apps:40-43`). Varsayılan **0**: ilk yüklemede mod görünmez; kullanıcı 1 yapıp QGC'den reboot atar (güç kesmek gerekmez). SITL testlerinde `PX4_PARAM_AF_ENABLE=1` ile verilir.
- Not (Görev grubu 1'de bulundu): SITL `COM_MODE_ARM_CHK`'yı 1 yapar (`ROMFS/px4fmu_common/init.d-posix/px4-rc.simulator:8`); yani **SITL'de arm iken de kayıt kabul edilir**. "Kayıt yalnızca disarm iken" kuralı gerçek kartta (6C, varsayılan 0) geçerlidir. Ayrıca `auto_follow stop`, kayıt silme mesajından sonra PX4 modu listeden kaldırana kadar (en fazla 1 s) bekler; hemen kapanırsa mesaj PX4'e ulaşmıyor (`platforms/common/uORB/Publication.hpp:65-72`). Ayrıntı `implementation/grup-1-iskelet-mod-kaydi.md`.
- Arming check'e cevapta `can_arm_and_run = true` (Karar 5-a): mod aktifken `false` olursa PX4 Hold'a değil **RTL**'e düşer (`src/modules/commander/failsafe/failsafe.cpp:698-702`). Tek istisna adayı: yerde arm'lıyken moda geçişi engellemek (**Karar A14-a**: yalnızca drone yerdeyken, `vehicle_land_detected.landed`, ve mod aktif değilken `false`; PX4 geçişi kendisi reddeder). `mode_req_*` listesi ve kontrol bayrakları **Karar (öneri kabul, C1)**, A1. `mode_req_prevent_arming = true` **Karar** (C1: bu modda arm yasak, disarm iken moda geçiş serbest).
- Mod aktifken PX4 FlightTask çalıştırmaz (`src/modules/flight_mode_manager/FlightModeManager.cpp:139-144`); `trajectory_setpoint`'i yalnızca `auto_follow` yayınlar.
- Disarm araçta moda geçiş PX4'te zaten serbesttir (`src/modules/commander/UserModeIntention.cpp:54-55`); masa testi gereksinimi kod gerektirmez.

**2. Girdi ve doğrulama (Karar 2026-11-09 girdi mesajı; doğrulama Karar (öneri kabul); eşikler Karar)**
- Girdi MAVLink `DEBUG_FLOAT_ARRAY`, `name = "AF_LOS"`; PX4 bunu uORB `debug_array`'e çevirir (`src/modules/mavlink/mavlink_receiver.cpp:2815-2832`; tek yayıncı `mavlink_receiver.h:333`). PX4 MAVLink zaman alanını atar, `timestamp`'e **varış anını** yazar (`:2822`). Yerleşim (Varsayım V2): `data[0..2]` LOS x/y/z (body FRD), `data[3]` yaş [ms], `data[4]` sıra no, `data[5]` hedef var (1) / yok (0). Yeni MAVLink mesajı eklenmez.
- Her yeni `debug_array` örneğinde sırayla: (1) ad `AF_LOS` mı · (2) altı değer sonlu mu (`PX4_ISFINITE`) · (3) `| |LOS| − 1 | ≤ AF_NORM_TOL` · (4) sıra no öncekinden büyük mü · (5) gerçek yaş `(şimdi − varış) + data[3]` < `AF_DATA_TOUT` mı · (6) hedef bayrağı 1 mi · (7) drone yerel konumu geçerli mi (`xy_valid`, `z_valid`, `msg/versioned/VehicleLocalPosition.msg:9-10`) · (8) aşağı bakış açısı ≥ `AF_MIN_DEP` · (9) `0 < yatay mesafe ≤ AF_MAX_RNG`. (8) ve (9) geometri adımında (Bölüm 3) yapılır.
- Bayrak 0 (hedef yok) bozuk veri değildir: mesaj sayılır ve **KAYIP_BEKLE hemen başlar** (Bölüm 7).
- Geçmeyen örnek **atılır**, nedeniyle **sayılır** (`perf_counter` PC_COUNT, `src/lib/perf/perf_counter.h:49`, ve log mesajındaki sayaçlar), **hız sınırlı** `PX4_WARN` ile yazılır; guidance'a asla girmez (`../agent-os/standards/global/validation.md:7`, `error-handling.md:8`).
- `debug_array` ortak bir topic'tir ve kuyruğu tektir (`msg/DebugArray.msg` kuyruk sabiti tanımlamaz); başka yayıncılar olabileceği için ad süzgeci zorunludur. Ad en fazla 9 karakter (`DebugArray.msg:4`, son bayt NUL, `mavlink_receiver.cpp:2825`).
- `CONSTRAINED_FLASH` açılırsa `DEBUG_FLOAT_ARRAY` işleyicisi derlemeden çıkar (`mavlink_receiver.cpp:284-305`, `:2748-2833`): m14 yapılırken bilinmeli.
- Not (bu yazımda bulundu): MAVLink tanımında `data` alanı bir **extension** alanıdır (`src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml:7630-7631`); gönderen taraf **MAVLink 2** kullanmalıdır. Vision tarafı pymavlink'in MAVLink 2 kullandığını bildirdi (kullanıcı, 2026-11-10, B1); masa/SITL testinde `los_frd` alanlarının sıfır gelmediği kontrol edilir.

**3. Geometri ve mesafe (Karar 6 "ortak adım", 13-(iii), formül Karar 2026-11-09)**
- LOS, varış anındaki `vehicle_attitude.q` (FRD → NED, `msg/versioned/VehicleAttitude.msg:10`) ile NED'e çevrilir: `LOS_NED = R(q) · LOS_FRD` (V3; gecikme telafisi yok).
- Aşağı bakış açısı `δ = asin(LOS_NED.z)` (z aşağı pozitif).
- `yükseklik farkı h = −vehicle_local_position.z − AF_GND_OFS − AF_TGT_HGT` (`VehicleLocalPosition.msg:17`; zemin = kalkış düzlemi, V4).
- `yatay mesafe d = h / tan(δ)`; `hedef_NED_xy = drone_xy + d · (LOS_NED_xy / |LOS_NED_xy|)`. Küresel koordinat dönüşümü yok.
- Örnek (sayısal kontrol, birim testte de kullanılır): drone 10 m, düz, burun kuzey, LOS (0.8, 0, 0.6), `AF_TGT_HGT` 1.0, `AF_GND_OFS` 0 → δ ≈ 36.9°, h = 9.0 m, **d = 12.0 m**.
- `h ≤ 0` ya da `d` sınır dışıysa örnek atılır (neden: menzil). `AF_MIN_DEP` gerekçesi: 5 m irtifada 1° açı hatası 30°'de ~0.5 m, 10°'de ~3 m, 5°'de ~10 m mesafe hatası yapar (KG).

**4. Alpha-beta filtresi (Karar 6.1; kendi sınıfımız `AlphaBetaFilter.hpp`)**
- Girdi: ölçülen hedef NED konumu; çıktı: kestirilen hedef konumu ve **hedef hızı**. Katsayılar `AF_ALPHA`, `AF_BETA`.
- Adımlar: tahmin `x̂ ← x̂ + v̂·Δt`; yeni ölçümde artık `r = ölçüm − x̂`, düzeltme `x̂ ← x̂ + α·r`, `v̂ ← v̂ + (β/Δt)·r`.
- PX4'ün `TargetEstimator`'ı kullanılmaz: GPS'li `follow_target` topic'ine bağlı bir work item'dır (`src/modules/flight_mode_manager/tasks/AutoFollowTarget/follow_target_estimator/TargetEstimator.hpp:112, 210`); yalnızca fikir kaynağıdır.
- Karar (öneri kabul, C2): filtre yatayda (x, y) çalışır (hedef zeminde); tahmin her 50 Hz çevrimde, düzeltme yalnızca kabul edilen ölçümde yapılır; Δt ölçümlerin tahmini çekim anları (`varış − yaş`) arasından alınır; ilk ölçümde konum ölçüme, hız 0'a kurulur; EKF reset sayaçları (`VehicleLocalPosition.msg:21, 23`) değişirse filtre sıfırlanır.
- Kullanıcının vurgusu: filtrenin girdisi ve çıktısı loga yazılır ve analiz edilir (Bölüm 9).

**5. Guidance yasası ve sınırlar (Karar 6-a, 6.1b, 6.4 öneri kabul, 6.2 öneri kabul)**
- İstenen mesafe: `d_ist = h / tan(AF_TRK_ANG)` (aynı `h` ile). Örnek: h = 9.0 m, 30° → 15.6 m.
- Yasa (yatay, hedef yönünde): `v_yasa = AF_K_FF · v̂_hedef + AF_K_DIST · (d_kest − d_ist) · û`; `û` drone'dan kestirilen hedefe yatay birim yön, `d_kest` kestirilen hedefe yatay mesafe (Karar (öneri kabul, C2): guidance'ta filtre çıktısı kullanılır).
- Kırpma: `|v| ≤ AF_VEL_MAX`. İvme sınırı: komut her çevrimde en fazla `AF_ACC_MAX · Δt` değişir. Sıra: yasa → kırpma → ivme sınırı (Karar (öneri kabul, C2)).
- Örnek devamı: `d_kest − d_ist = 12.0 − 15.6 = −3.6 m` → `v = 0.5 · (−3.6) = −1.8 m/s`, yani hedeften uzaklaşarak geri (2 m/s sınırının altında).
- `AF_K_FF = 0` ilk testlerde: sabit yönle (açık çevrim) sanal hedef drone'la birlikte kayar ve `AF_K_FF > 0` drone'u `AF_VEL_MAX`'a kadar kaçırır (pozitif geri besleme). `AF_K_FF > 0` yalnızca kapalı çevrimde denenir.
- Karar (öneri kabul, C2): moda girişte ivme sınırlayıcı drone'un o anki yatay hızından başlatılır (geçişte sıçrama olmasın).
- Nihai yasa ve ince ayar m13'tür; bu spec ilk yasayı yazar.

**6. Yaw ve irtifa (Karar 7-a mutlak yaw, 6.3, 6.4)**
- Yaw mutlaktır: `yaw = atan2(Δy, Δx)` (drone → kestirilen hedef); hedef kadrajın ortasında kalır.
- `d_kest < AF_YAW_MIN_D` ise yaw değiştirilmez (son yaw tutulur).
- İrtifa: moda girildiği andaki `vehicle_local_position.z` saklanır ve `position[2]` olarak tutulur.
- Yaw hız sınırı parametresi kararlaştırılmadı; PX4'ün kendi sınırı geçerlidir (`MC_YAWRATE_MAX`, `src/modules/mc_att_control/mc_att_control_params.c:147`) (doğrulanacak).

**7. Durum makinesi ve hedef kaybı: D (Karar; kullanıcı "önemli" dedi; süreler Karar 2026-11-09)**
- Durumlar (adlar **Karar**, C3; ayrıntı `log-sozlugu.md`): **PASIF** (mod kapalı; setpoint yok, veri işlenebilir) · **TAKIP** (geçerli veri var, guidance çalışır) · **KAYIP_BEKLE** (hover: kayıp anındaki konum, hız 0, son yaw, giriş irtifası) · **HOLD_ISTENDI** (Hold istendi).
- Geçişler: TAKIP → KAYIP_BEKLE: `AF_DATA_TOUT` (0.5 s) boyunca geçerli veri yok **ya da** Pi `hedef yok` dedi · KAYIP_BEKLE → TAKIP: `AF_LOST_T` dolmadan geçerli veri geldi (takip kendiliğinden sürer) · KAYIP_BEKLE → HOLD_ISTENDI: `AF_LOST_T` (1.0 s) doldu · HOLD_ISTENDI/TAKIP/KAYIP_BEKLE → PASIF: `nav_state` artık bizim mod değil.
- Zaman çizelgesi:
  - Veri kesilirse: `son geçerli mesaj ──0.5 s──▶ KAYIP_BEKLE ──1.0 s──▶ Hold` (toplam 1.5 s).
  - Pi "hedef yok" derse: `bayrak = 0 ──▶ KAYIP_BEKLE (hemen) ──1.0 s──▶ Hold`.
  - Hedef görünmezken moda girilirse (Karar 5-a): 1.5 s içinde geçerli hedef gelmezse Hold. **Karar (A3, 2026-11-10):** zaman referansı `max(son geçerli mesaj, giriş anı)`; girişte geçerli veri yoksa durum KAYIP_BEKLE, Hold zamanı `giriş + AF_DATA_TOUT + AF_LOST_T` = giriş + 1.5 s.
- Hold isteği: `vehicle_command` ile `VEHICLE_CMD_SET_NAV_STATE` (`msg/versioned/VehicleCommand.msg:114`), `param1 = NAVIGATION_STATE_AUTO_LOITER` (`VehicleStatus.msg:40`), hedef sistem/bileşen `vehicle_status.system_id/component_id` (`VehicleStatus.msg:118-119`; süzgeç `Commander.cpp:746-747`); işleme `Commander.cpp:936-944`. `source_component < 1000` olmalı ki istek "User" sayılsın (`Commander.cpp:1559-1562`) (doğrulanacak).
- Hold'dan sonra takibe **kendiliğinden dönülmez** (C reddedildi). Pilot QGC'den tek tıkla ya da RC anahtarını başka konuma alıp geri getirerek döner; anahtarı yerinde bırakmak yetmez (`src/modules/manual_control/ManualControl.cpp:176-177`).
- Karar (öneri kabul, C2): Hold reddedilirse (`TEMPORARILY_REJECTED`) hover sürer, `vehicle_command_ack` izlenir, istek 1 s arayla en fazla 3 kez tekrarlanır.
- İlk uçuşlarda `AF_LOST_T` kısa tutulur (davranış pratikte B olur); her uçuşta kullanılan değer test planına yazılır.

**8. Setpoint çıkışı (Karar 7-a)**
- Mod aktifken **her çevrimde** `trajectory_setpoint` yayınlanır (`timestamp = hrt_absolute_time()`): TAKIP'te `velocity[0..1] = v`, `position[2] = giriş irtifası`, `yaw = mutlak yaw`; KAYIP_BEKLE/HOLD_ISTENDI'de `position[0..2] = tutulan konum`, `velocity[0..1] = 0`, `yaw = son yaw`. Kullanılmayan alanlar NaN (`msg/versioned/TrajectorySetpoint.msg:11-17`).
- Bu karışım PX4'te geçerlidir: her eksende konum/hız/ivmeden biri sonlu, x–y çiftleri birlikte (`src/modules/mc_pos_control/PositionControl/PositionControl.cpp:224-250`).
- Mod aktif değilken setpoint yayınlanmaz.
- Moda girişte ilk çevrimde setpoint yayınlanır; aksi halde `mc_pos_control` kendi yedek setpoint'ini üretir (`src/modules/mc_pos_control/MulticopterPositionControl.cpp:443-449`).
- **Standartla çelişki notu:** Çatı standardı hata anında "setpoint üretmeyi bırak" diyor (`../agent-os/standards/global/error-handling.md:4`). PX4'te ise yayın kesilince `mc_pos_control` **son isteği uygulamaya devam eder** (`trajectory_setpoint` yalnızca güncellenince okunur, `MulticopterPositionControl.cpp:438`; yedek setpoint yalnızca konum kontrolünün açıldığı ilk an için, `:443-449`). Bu yüzden modül susmaz, **aktif olarak hover** yayınlar. Standardın değişmesi ayrı bir iştir (çatı profili).
- Karar (öneri kabul, C2; eski taslaktan): yerel konum geçersizken tutma konumu anlamsızdır; bu durumda `position[0..1]` NaN, `velocity[0..1] = 0` yayınlanır, asıl tepkiyi PX4'ün `mode_req_local_position` fallback'i verir (A10).

**9. Loglama ve log sözlüğü (Karar L2-b, L1 güncel, L3, L4, Karar 4)**
- Kendi uORB mesajımız `msg/AutoFollowStatus.msg` → topic **`auto_follow_status`**; modül **her çevrimde** doldurup yayınlar. `src/modules/logger/logged_topics.cpp`'deki varsayılan listeye (`add_default_topics`, `:46`) bir `add_topic` satırıyla **her zaman** kaydedilir; kullanıcı ayar açmaz. Karar (öneri kabul, C2): aralık verilmez (her yayın, 50 Hz) ve mesaj PASIF'te de yayınlanır (masa testinde ham girdi görülsün).
- Debug biti gerekmez: ham girdi bu mesaja kopyalanır; ham `debug_array` yalnızca debug profilinde loglanır (`logged_topics.cpp:289-294`).
- **`logger_topics.txt` düzeltmesi:** SD karttaki `etc/logging/logger_topics.txt` varsa PX4 **yalnızca o dosyadakileri** loglar, varsayılan listeyi kapatır (`logged_topics.cpp:531-540`). Bu yüzden doğru yol `logged_topics.cpp`'ye satır eklemektir; o dosya kullanılmaz.
- Zaten varsayılan loglananlar: `trajectory_setpoint` (200 ms, `:131`), `vehicle_command`, `vehicle_control_mode`, `vehicle_local_position`, `vehicle_status` (`:131-150`), `actuator_motors` (`:214`).
- **Geri dönüş:** Hüseyin `msg/` ve `logged_topics.cpp` yollarını reddederse PX4'ün hazır `debug_array` mesajı + sözlük kullanılır; alanlar logda `data[i]` görünür, adlar sözlük ve analiz script'inden gelir.
- `SDLOG_MODE` varsayılan kalır (0 = yalnızca arm iken; `src/modules/logger/module.yaml:16-31`, değişiklik yeniden başlatma ister `:31`; SITL varsayılanı 1, `ROMFS/px4fmu_common/init.d-posix/rcS:180`). Masa testinde değeri kullanıcı kendisi seçip değiştirir (Karar A5, 2026-11-10: belgeler değer önermez; bilgi için 1 = açılıştan disarm'a, 2 = açılıştan kapanışa).
- **Sözlük** `log-sozlugu.md` (spec klasörü). Karar C3 (2026-11-10): kapsamı yalnız log alanları değil, **bizim verdiğimiz bütün adlar** (mod, modül ve komutları, dosyalar, girdi mesajı, parametreler, log mesajı ve alanları, durumlar, doğrulama sonuçları, script'ler). Her ad için anlam, birim, frame, hangi durumda ne değer aldığı; **kodla aynı commit'te** güncellenir. İlk sürümü write-spec turunda yazıldı. Sözlükte şu uyarı yer alır:
  > ⚠️ PX4'ün kendi `AUTO_FOLLOW_TARGET` modu (Follow Me, `nav_state` = 19, `msg/versioned/VehicleStatus.msg:55`; kod `FlightTaskAutoFollowTarget`, parametreler `FLW_TGT_*`) bizim **AUTO FOLLOW** ile **ilgili değildir**. Bizimki 23–30 aralığından numara alır; hangisi olduğu `auto_follow_status`'ta yazar. Bazı log araçları 19'u "Auto Follow" diye gösterebilir. Kodda hiçbir şeye `AutoFollowTarget` / `follow_target` adı verilmez; RC anahtarı (`COM_FLTMODEx`) bizim mod numarasıyla ayarlanır.
- **Log alanları — Karar (C3, 2026-11-10: adlar tablodaki gibi, önek yok)** (PX4 msg geleneği: alanlar küçük harf snake_case, birim yorumda; sabitler BÜYÜK_HARF):

| Alan | Tip | Birim | Anlam |
|---|---|---|---|
| `timestamp` | uint64 | us | Yayın anı |
| `mode_nav_state` | uint8 | — | AUTO FOLLOW'a atanan `nav_state` (23–30); kayıt yoksa 0 |
| `mode_active` | bool | — | `vehicle_status.nav_state == mode_nav_state` |
| `state` | uint8 | — | `STATE_PASIF=0`, `STATE_TAKIP=1`, `STATE_KAYIP_BEKLE=2`, `STATE_HOLD_ISTENDI=3` |
| `los_timestamp` | uint64 | us | Son `AF_LOS`'un FC'ye varış anı |
| `los_frd` | float32[3] | — | Ham LOS x/y/z, body FRD (`data[0..2]`) |
| `los_age` | float32 | ms | Pi'nin bildirdiği yaş (`data[3]`) |
| `los_seq` | uint32 | — | Sıra no (`data[4]`) |
| `los_target` | bool | — | Hedef var bayrağı (`data[5]`) |
| `check_result` | uint8 | — | Son örneğin doğrulama sonucu: `CHECK_OK=0`, `CHECK_NAME`, `CHECK_NONFINITE`, `CHECK_NORM`, `CHECK_SEQ`, `CHECK_AGE`, `CHECK_NO_TARGET`, `CHECK_POSITION`, `CHECK_DEPRESSION`, `CHECK_RANGE` |
| `accept_count` | uint32 | — | Kabul edilen örnek sayısı |
| `reject_name_count`, `reject_nonfinite_count`, `reject_norm_count`, `reject_seq_count`, `reject_age_count`, `reject_position_count`, `reject_depression_count`, `reject_range_count` | uint32 | — | Nedene göre atılan örnek sayaçları |
| `no_target_count` | uint32 | — | "Hedef yok" bayraklı örnek sayısı |
| `latency` | float32 | ms | Kullanılan ölçümün toplam gecikmesi = (işlem anı − varış) + yaş |
| `los_ned` | float32[3] | — | NED'e çevrilmiş LOS |
| `depression` | float32 | rad | Aşağı bakış açısı δ |
| `height_diff` | float32 | m | Yükseklik farkı h |
| `range_meas` | float32 | m | Ölçümden yatay mesafe d |
| `target_meas_ned` | float32[2] | m | Filtre girdisi: ölçülen hedef NED x, y |
| `target_est_ned` | float32[2] | m | Filtre çıktısı: kestirilen hedef NED x, y |
| `target_vel_ned` | float32[2] | m/s | Filtre çıktısı: kestirilen hedef hızı |
| `filter_updated` | bool | — | Bu çevrimde düzeltme yapıldı mı |
| `range_est` | float32 | m | Kestirilen hedefe yatay mesafe |
| `range_desired` | float32 | m | İstenen mesafe |
| `vel_cmd_law` | float32[2] | m/s | Yasa çıkışı (kırpma öncesi), NED |
| `vel_cmd` | float32[2] | m/s | Kırpma + ivme sınırı sonrası, `trajectory_setpoint`'e giden |
| `yaw_cmd` | float32 | rad | Yaw komutu |
| `yaw_frozen` | bool | — | `AF_YAW_MIN_D` nedeniyle yaw sabit |
| `alt_hold_z` | float32 | m | Tutulan irtifa (NED z) |
| `time_since_valid` | float32 | s | Son geçerli örnekten beri geçen süre |
| `lost_time` | float32 | s | KAYIP_BEKLE'de geçen süre |
| `hold_request_count` | uint8 | — | Gönderilen Hold isteği sayısı |

- Not: `data[4]` float olarak gelir; float32 tam sayıları 2²⁴'e kadar kesin taşır (30 Hz'de ~155 saat). Vision ile konuşulacak (A5).

**10. Parametreler (adlar Karar 2026-11-09; değerler Karar (öneri kabul))**
- `module.yaml`'da `description`, `type`, `default`, `min`, `max`, `unit`, `decimal` ile tanımlanır (`../agent-os/standards/px4/uorb-params.md:10`); kodda `DEFINE_PARAMETERS`, `parameter_update` ile güncellenir. Hepsi QGC'den değişir, derleme gerekmez. PX4 v1.17.0'da `AF_` önekli parametre yok (kaynakta tarandı). Çevrim hızı parametre değildir (50 Hz).
- Birim, min/max ve `AF_ALPHA`/`AF_BETA` varsayılanı **Karar (öneri kabul, C2)** (açılar kullanıcıya derece gösterilir, kodda radyana çevrilir).

| Parametre | Anlamı | Varsayılan | Birim | Min–max |
|---|---|---|---|---|
| `AF_ENABLE` | AUTO FOLLOW'u açılışta başlat (1) / başlatma (0); değişince reboot | 0 | — | 0–1 |
| `AF_TRK_ANG` | Takip açısı (kamera eğimi, m06'dan) | 30 (SITL) | deg | 5–85 |
| `AF_K_DIST` | Mesafe kazancı K | 0.5 | 1/s | 0–2 |
| `AF_K_FF` | Hedef hızı katsayısı c (0 = kapalı) | 0 | — | 0–1.5 |
| `AF_VEL_MAX` | En büyük yatay hız | 2 | m/s | 0.1–5 |
| `AF_ACC_MAX` | Hız komutu değişim sınırı (`MPC_ACC_HOR` varsayılanı, `src/modules/mc_pos_control/multicopter_autonomous_params.c:88`) | 3 | m/s² | 0.5–5 |
| `AF_ALPHA` | Filtre konum katsayısı | 0.5 (başlangıç; SITL'de ayarlanır) | — | 0–1 |
| `AF_BETA` | Filtre hız katsayısı | 0.17 (β ≈ α²/(2−α), Benedict–Bordner) | — | 0–1 |
| `AF_DATA_TOUT` | Veri zaman aşımı | 0.5 | s | 0.1–5 |
| `AF_LOST_T` | KAYIP_BEKLE'den Hold'a | 1.0 | s | 0–30 |
| `AF_YAW_MIN_D` | Bu yatay mesafenin altında yaw sabit | 1 | m | 0–10 |
| `AF_TGT_HGT` | Hedefin bakılan noktasının yüksekliği | 1.0 | m | 0–2.5 |
| `AF_GND_OFS` | Hedef zemininin kalkış yerine göre yüksekliği | 0 | m | −20–20 |
| `AF_NORM_TOL` | LOS uzunluk toleransı | 0.1 | — | 0.01–0.5 |
| `AF_MIN_DEP` | En küçük aşağı bakış açısı | 10 | deg | 1–60 |
| `AF_MAX_RNG` | En büyük menzil | 40 | m | 1–200 |

- Flash'a sığmazsa geri dönüş (Karar 13): `AF_GND_OFS` çıkarılır, yalnız `AF_TGT_HGT` kalır.

**11. Testler (Karar 10.1, 10.2, 10.3, L4)**
- **Birim testi (kısa):** `AutoFollowGuidanceTest.cpp`, GoogleTest `px4_add_unit_gtest` (`cmake/px4_add_gtest.cmake:40`), çalıştırma `make tests TESTFILTER=AutoFollowGuidance` (`Makefile:406-407`; CI'da çalışmaz, yerelde koşulur). Kapsam: mesafe/yön (Bölüm 3 örneği → 12.0 m), yasa ve sınırlar (örnek → −1.8 m/s, kırpma, ivme sınırı), bozuk veri (NaN/Inf, norm, sıra no, ad), zaman aşımı/durum geçişleri (0.5 s, +1.0 s, hedef yok). Karar (öneri kabul, 2026-11-10): doğrulama ve durum makinesi zamanı argüman alan saf fonksiyonlar olarak `AutoFollowGuidance` içinde tutulur ki testlenebilsin.
- **SITL:** Gazebo Harmonic, `make px4_sitl gz_x500` (mümkünse `HEADLESS=1`); her testten önce/sonra `build/px4_sitl_default/rootfs/parameters*.bson` sıfırlanır (`../agent-os/standards/testing/test-writing.md:13-15`). Drone **Position** modunda kalkar (AUTO FOLLOW'da kalkış yok ve arm yasak, C1/B4), sonra havada AUTO FOLLOW'a alınır.
- **Geçici gönderici** `tez/sitl/af_los_gonder.py` (pymavlink 2.4.50, `tez/env/requirements-lock.txt:25`; SITL onboard bağlantısı UDP 14540/14580, `ROMFS/px4fmu_common/init.d-posix/px4-rc.mavlink:4-5, 26`): Pi'nin `AF_LOS` mesajını Bölüm 2 yerleşimiyle taklit eder. **Açık çevrim** = sabit yön; **kapalı çevrim** = script yerde hayali bir hedef tutar, drone'un konumunu/tutumunu okur ve gerçek LOS'u hesaplar. Açık çevrimde `AF_K_FF = 0`.
- **Senaryolar — Karar (A1, A2, 2026-11-10):** kullanıcıyla konuşulan tablo (`rapor.md` §4.9) esastır; S1, açıya göre ikiye ayrıldı. Örnek değerler: irtifa 10 m, `AF_TGT_HGT` 1.0 → h = 9.0 m; `AF_TRK_ANG` 30° → istenen mesafe 15.6 m. S1–S5 açık çevrim, `AF_K_FF = 0`.

| # | Ne verilir | Beklenen sonuç | Ölçüm (pyulog) |
|---|---|---|---|
| S1a Hedef uzakta | Açık çevrim, sabit LOS (0.951, 0, 0.309): δ ≈ 18° < `AF_TRK_ANG` | d ≈ 27.7 m > 15.6 m → **ileri**; yasa ≈ +6.0 m/s ister, `AF_VEL_MAX` 2 m/s'de kırpılır; ivme ≤ 3 m/s² | `range_meas`, `range_desired`, `vel_cmd_law`, `vel_cmd`, `trajectory_setpoint` |
| S1b Hedef yakında | Açık çevrim, LOS (0.8, 0, 0.6): δ ≈ 36.9° > `AF_TRK_ANG` | d = 12.0 m < 15.6 m → **geri** ~1.8 m/s (kırpma yok) | Aynı |
| S2 Hedef sağda | Açık çevrim, LOS (0, 0.8, 0.6) | Burun sağa döner. Sabit body LOS yüzünden dönüş sürer (beklenen, B3); yaw doğruluğu S6'da ölçülür | `yaw_cmd`, `vehicle_attitude` yönü |
| S3 Hedef neredeyse tam altta | Açık çevrim, LOS (0.174, 0, 0.985): δ = 80° | d ≈ 1.6 m → geri; yasa ≈ −7.0 m/s ister, 2 m/s'de kırpılır; d > `AF_YAW_MIN_D` (1 m) olduğundan yaw donmaz | `vel_cmd_law`, `vel_cmd`, `yaw_frozen` |
| S4 Hedef kaybı | Gönderim kesilir · varyant: 1.0 s dolmadan geri gelir · varyant: `data[5] = 0` · varyant: hedefsiz moda giriş | 0.5 s sonra KAYIP_BEKLE (hover), +1.0 s sonra `nav_state = 4` (toplam ≈ 1.5 s) · takip kendiliğinden sürer · hemen KAYIP_BEKLE, 1.0 s sonra Hold · girişten 1.5 s sonra Hold. Hold kısmı iş sırasında 5. adımdan sonra koşulur (A4) | Son geçerli örnek → `nav_state = 4` süresi; `state`, `time_since_valid`, `lost_time` |
| S5 Girdi doğrulama | Yanlış ad, NaN/Inf, norm dışı, tekrar/geri sıra no, yaş > 0.5 s, ufka yakın (δ < 10°), menzil > 40 m | Atılır, ilgili `reject_*` sayacı artar, drone etkilenmez | `check_result`, `reject_*_count`, `vel_cmd` |
| S6 Duran hayali insan | Kapalı çevrim: script yerde duran bir hedef tutar ve gerçek LOS'u hesaplar | `range_est → range_desired` (15.6 m); burun hedefte; salınım yok | `range_est − range_desired`, `yaw_cmd − yön`, `vel_cmd` |
| S7 Yürüyen hayali insan | Kapalı çevrim, hedef yürür, `AF_K_FF > 0` | Geride kalmadan takip; mesafe hatası S6'ya yakın | `target_vel_ned`, `range_est − range_desired`, `vel_cmd` |

- **Ön kontroller** (her test oturumunun başında; SITL'de `PX4_PARAM_AF_ENABLE=1`; yeni senaryo değildir, eski taslaktaki "kayıt" ve "mod seçimi" başlıklarından): modül açılışta kendiliğinden başladı (B2) · QGC listesinde `AUTO FOLLOW`, `mode_nav_state` 23–30, `can_set_nav_states_mask`'ta bit (`VehicleStatus.msg:72`), yeniden başlatmada aynı numara · disarm iken moda geçiş kabul, bu modda arm reddedilir (C1) · yerde arm'lıyken moda geçiş engellenir (B4, yöntem A14) · QGC ve RC anahtarıyla giriş/çıkış; girişte ilk çevrimde setpoint, çıkışta setpoint durur · Hold'dan sonra anahtar aç-kapa ile yeniden giriş · RC çubuğu davranışı (A2).
- **SITL'siz test yalnızca birim testidir** (yukarıda). Açık çevrim testleri de SITL'dedir ama basittir: script sabit yön gönderir (B3).
- RC kaybı ve modül donması testleri bu spec'te yoktur (A1) → m16 adayı.
- Her senaryo için spec klasörüne yazılır: **ne verildi, drone ne yaptı, ULog adı**. Değerlendirme `tez/analiz/af_log_analiz.py` (pyulog 1.2.4, `tez/env/requirements-lock.txt:27`); göz kararı test sayılmaz. Kesin başarı eşikleri yol haritası m01'e aittir; şimdilik öneri.
- Her testten sonra ULog (`build/px4_sitl_default/rootfs/log/<tarih>/<saat>.ulg`) **`~/Desktop/AUTO-FOLLOW LOG/`** klasörüne kopyalanır (`SDLOG_DIRS_MAX` = 7, `ROMFS/px4fmu_common/init.d-posix/rcS:183`); loglar repoya girmez.
- m06 (gerçekçi simülasyon, Ahmet Kazalcı) hazır olunca testler oraya taşınır.

**12. Dokümantasyon (KG "Kullanıcının notu", Karar 14.3, L2)**
- Her görev grubunun sonunda spec klasörüne kod okumadan anlaşılacak dille: ne yapıldı, neden, nasıl test edildi, hangi sorunlar çıktı ve nasıl çözüldü.
- `rapor.md` her görev grubundan sonra güncellenir (yeni sürüm satırı "Belge geçmişi"ne).
- `log-sozlugu.md` bizim verdiğimiz bütün adları kapsar (C3), kodla **aynı commit'te** güncellenir ve `AUTO_FOLLOW_TARGET` uyarısını içerir.
- `planning/karar-gunlugu.md` iş boyunca güncel tutulur; her yeni karar oraya ve `requirements.md`'ye işlenir.
- Commit düzeni (çatı kural 10–11): görev grubu başına commit `2026-11-08-m15-takip-kodu: Görev grubu <N> — <ne>`; PR başlığı `[M15] ...`; PR açıklamasında yeni PX4 dosya yolları, 6C flash kullanımı, `tech-stack.md:44` için "karar: external mode, güncellenmeli" notu ve `Closes Auto-Follow/Auto-Follow#6`. Push kullanıcı istemeden yapılmaz.

## Varsayımlar

Ortak spec'ler (yol haritası 3, 4, 5) yazılmadığı için aşağıdakiler **kesin değildir** (`../agent-os/product/roadmap.md:69`); ortak spec yazılınca bu spec ona göre güncellenir.

| # | Varsayım | Durum |
|---|---|---|
| V1 | Girdi body FRD (x ileri, y sağ, z aşağı) LOS birim vektörüdür; kamera montaj açısı Pi tarafında uygulanmıştır, FC bilmez | 1. tur soru 13, itiraz yok |
| V2 | Taşıma MAVLink `DEBUG_FLOAT_ARRAY` (`AF_LOS`) → `debug_array`; yerleşim Bölüm 2; kesin biçim, frekans (Pi 10–30 Hz bekleniyor) ve zaman biçimi ICD'de | Karar 2026-11-09 |
| V3 | LOS → NED dönüşümünde **varış anındaki** tutum kullanılır; gecikme telafisi yok (gerekirse m13/m16, loglardaki gerçek gecikmeye göre) | 1. tur soru 13 |
| V4 | Drone yüksekliği `−vehicle_local_position.z`; zemin düz ve kalkış düzlemi | Karar 13-(iii) |
| V5 | Hedefin bakılan noktası `AF_TGT_HGT`, zemin farkı `AF_GND_OFS` | Karar 13-(iii) |
| V6 | LOS eksen yönleri ve işaretleri Yusuf Ortatepe'nin m10 çalışmasıyla eşlenecek | **Açık** |

## Visual Design

**`planning/visuals/01-ust-seviye-akis.md`**
- Üst seviye akış: mod seçimi → mod aktif mi → mesaj geçerli mi → LOS'u NED'e çevir → aşağı açı ve yatay mesafe → hedef NED konumu → alpha-beta → guidance (istenen mesafe, hız, yaw, sınırlar) → PX4 kontrolcüleri → PWM → ESC → motorlar.
- Kayıp dalı: `AF_DATA_TOUT` → yerinde bekle → `AF_LOST_T` → Hold.
- 2026-11-09'da kopyada güncellendi: kararlaşan TBD'ler kararla değişti, eski adlar (`tez_follow`, `TEZ_FOL_*`, `TEZ_LOS`) AUTO FOLLOW / `AF_*` oldu, masaüstü bağlantısı `../../rapor.md`'ye çevrildi. TBD kalan: ICD zaman biçimi.

**`planning/visuals/02-px4-detayli-akis.md`**
- (A) başlatma, mod kaydı, arming check · (B) çevrim başına veri akışı (`debug_array` → doğrulama → geometri → alpha-beta → guidance → `trajectory_setpoint` → PWM) · (C) mod seçimi, çıkış, hedef kaybı (D) ve failsafe · (D) doğrulama (GoogleTest → SITL S1–S7 → pyulog → gerçek uçuş).
- Aynı gün kopyada güncellendi. TBD kalanlar: kilit listesi onayı (6 yol), ICD zaman biçimi, hareketli insan modeli/dünyası (m06). Mod kaydı ayrıntıları ve başlatma noktası "(öneri, Açık)" olarak işaretli.
- Asıl şemalar eski klasörde (`2026-10-15-m15-target-follow-flight-mode/diagrams/`) değişmeden durur. PNG dönüşümü ertelendi (araç kurulmadan önce kullanıcıya sorulur).

## Existing Code to Leverage

**`src/modules/mc_nn_control/` — external mode kalıbı**
- Kayıt isteği (`RegisterExtComponentRequest`, ad `char[25]`, `msg/versioned/RegisterExtComponentRequest.msg:8`), cevabın beklenmesi, `config_control_setpoints` ile kontrol modu yapılandırması ve arming check cevabı: `mc_nn_control.cpp:132-212`.
- `Run()` sırası (çıkış → kayıt → cevap → arming check → `nav_state == mode_id` kapısı): `:436-477`. Kayıt silme `:146-155`.
- Fark: `mc_nn_control` konum kontrolünü kapatıp `actuator_motors` yayınlar (`:164`); `auto_follow` konum kontrolünü açık tutar ve `trajectory_setpoint` yayınlar.

**`src/examples/work_item/` ve `src/modules/internal_combustion_engine_control/` — modül iskeleti**
- `ModuleBase` + `ModuleParams` + `ScheduledWorkItem`, `perf_alloc` sayaçları (`WorkItemExample.hpp:55, 86-87`).
- `module.yaml` ile parametre ve `MODULE_CONFIG`, `DEPENDS SlewRate` örneği: `internal_combustion_engine_control/CMakeLists.txt`, `module.yaml`.

**`src/modules/mc_pos_control/PositionControl/` — saf hesap kütüphanesi + gtest deseni**
- `px4_add_library` + `px4_add_unit_gtest(SRC ...Test.cpp LINKLIBS ...)` (`PositionControl/CMakeLists.txt`). `AutoFollowGuidance` aynı şekilde ayrı bir kütüphane olur, modül ona bağlanır (kütüphane adı `AutoFollowGuidance`, Karar).

**Matematik yardımcıları**
- `matrix::Quatf::rotateVector` (FRD → NED, `src/lib/matrix/matrix/Quaternion.hpp:487`), `matrix::wrap_pi` (`src/lib/matrix/matrix/helper_functions.hpp:98`).
- İvme sınırı için `SlewRate::update` (`src/lib/slew_rate/SlewRate.hpp:79-87`); eksen bazlı sınırlar, vektör büyüklüğüyle sınır gerekirse küçük bir yardımcı yazılır (öneri).

**Commander arayüzleri ve fikir kaynakları**
- Hold isteği: `Commander.cpp:936-944`, hedef süzgeci `:746-747`, kaynak eşlemesi `:1559-1562`.
- `TargetEstimator` (`TargetEstimator.hpp:112, 210`, `FLW_TGT_RS` `follow_target_params.c:53`): yalnızca filtre fikri. Ahmet'in `origin/deney/ai-follow-sim` dalı (requirements §12): geolocation, gecikme/kayıp simülasyonu, pyulog analizi için fikir; kod alınmaz (bu yazımda dal içeriği doğrulanmadı).

## Kilitli yollar ve flash

- Şu an hiçbiri `tez/pin/allowed-paths.txt`'te değil (liste: `tez/*`, `.github/*`, `.gitmodules`, `TEZ_README.md`, `CLAUDE.md`, `agent-os/*`, `.claude/*`). **Tek talep** olarak repo sorumlusu **Hüseyin**'e iletilir:

| Yol | Neden |
|---|---|
| `src/modules/auto_follow/` | Yeni modül (`AutoFollow.cpp/.hpp`, `AutoFollowGuidance.cpp/.hpp`, `AlphaBetaFilter.hpp`, `AutoFollowGuidanceTest.cpp`, `CMakeLists.txt`, `Kconfig`, `module.yaml`) |
| `boards/px4/sitl/default.px4board` | `CONFIG_MODULES_AUTO_FOLLOW=y` |
| `boards/px4/fmu-v6c/default.px4board` | `CONFIG_MODULES_AUTO_FOLLOW=y` |
| `msg/AutoFollowStatus.msg` | Log mesajı |
| `msg/CMakeLists.txt` | Mesaj listesine bir satır (`msg_files`, `msg/CMakeLists.txt:39`) |
| `src/modules/logger/logged_topics.cpp` | `auto_follow_status`'u her zaman kaydeden `add_topic` satırı |
| `ROMFS/px4fmu_common/init.d/rc.mc_apps` | Açılışta `auto_follow start` satırı (Karar B2-b) |

- **Ajan `tez/pin/allowed-paths.txt`'i asla düzenlemez**; ekleme Hüseyin'in onayıyla ayrı, açık bir PR'dır. Log mesajı yolları (`msg/AutoFollowStatus.msg`, `msg/CMakeLists.txt`, `logged_topics.cpp`) reddedilirse `debug_array` + sözlük geri dönüşü uygulanır ve o üç yol gerekmez. `rc.mc_apps` reddedilirse geri dönüş A8-(a): SITL'de elle, 6C'de SD karttaki `etc/extras.txt`.
- Yedinci yol (`rc.mc_apps`) B2-b kararıyla talebe girdi; talep Hüseyin'e **yedi yol** olarak gider. Ajan listeye kendiliğinden eklemez.
- Commit/PR öncesi `tez/pin/verify_pin.sh --worktree`; zorunlu CI `verify-pin`, `derleme-sitl`, `derleme-fmu-v6c`.
- **Flash:** Pixhawk 6C ~%98 dolu (~40 KB boş; `../agent-os/product/tech-stack.md:43`). Kod küçük tutulur (`double`, dinamik bellek, büyük tablo yok; `../agent-os/standards/px4/modules.md:10`). `make px4_fmu-v6c_default` çıktısındaki flash kullanımı spec'e ve PR'a yazılır. `region FLASH overflowed` olursa **Hüseyin'e haber verilir; başka modül kapatılarak yer açılmaz** (o iş m14).
- **Flash ölçümleri** (`make px4_fmu-v6c_default`, FLASH bölgesi 1920 KB = 1 966 080 B; ayrıntı `implementation/` notlarında):

| Ne zaman | Kullanılan | Yüzde | Boş | Artış |
|---|---|---|---|---|
| Modül yokken (değişiklikten önce, 2026-11-10) | 1 926 408 B | %97,98 | 39 672 B | — |
| Görev grubu 1 sonu (iskelet + 16 parametre, 2026-11-10) | 1 931 164 B | %98,22 | 34 916 B | +4 756 B |
| Görev grubu 2 sonu (doğrulama, geometri, filtre, guidance, setpoint, `auto_follow_status`, 2026-11-10) | 1 936 100 B | %98,48 | 29 980 B | +4 936 B |

## Out of Scope

- Hold'dan sonra takibe kendiliğinden dönüş (seçenek C) ve ayrıntılı failsafe / mod çıkış akışının tamamı → m16
- RC kaybı ve modül donması SITL testleri → m16 adayı (A1)
- Nihai guidance yasası, ince ayar ve gecikme telafisi (gerekirse) → m13 / m16
- Pi tarafı, ICD, kalıcı yön göndericisi → Vision (m3–5, m12)
- Gerçekçi simülasyon, kamera ve hareketli insan modeli / dünyası → m06
- Gerçek uçuş → m22, m25
- Flash'ta yer açma, modül kapatma → m14
- Yeni MAVLink mesajı / dialect
- Ekip için "her özelleştirme loga girer + log sözlüğü" standardı → ayrı m00 (çatı profili)
- Çatı dosyalarının (`agent-os/product/`, standartlar) güncellenmesi → repo sorumlusu
- Uygulama sırasında yetişmeyen adımlar → "m16'ya kalanlar" listesi (`requirements.md` §1.3) güncellenir

## Açık konular

Her biri kullanıcıya seçenek + kanıt + öneri olarak sunuldu. 2026-11-10 itibarıyla A1–A4, A8–A10, A12–A14 karara bağlandı; açık kalanlar dış bağımlılıklar (A5 Vision, A6 m06, A7 Hüseyin, A11 kalıcı gönderici).

| # | Konu | Durum ve öneri |
|---|---|---|
| A1 | **Mod kaydı ayrıntıları** | **Karar (C1, 2026-11-10).** `mode_req_angular_velocity`, `mode_req_attitude`, `mode_req_local_alt`, `mode_req_local_position` = true; `mode_req_global_position`, `mode_req_home_position`, `mode_req_mission`, `mode_req_manual_control` = false (`msg/versioned/ArmingCheckReply.msg:31-41`, `mc_nn_control.cpp:185-193` ile aynı); kontrol bayrakları (`msg/versioned/VehicleControlMode.msg:8-19`): position, velocity, altitude, climb_rate, acceleration, attitude, rates, allocation, termination = true; manual, offboard = false; auto için A2 (öneri kabul). `mode_req_prevent_arming` = **true** (kullanıcı: "bu modda arm etmek yasak olsun ancak arm değilken bu moda geçebileyim"): disarm iken geçiş her zaman serbest (`UserModeIntention.cpp:54-55`), yasak yalnızca arm etmeyi durdurur (`HealthAndArmingChecks/checks/modeCheck.cpp:196-205`). Yerde arm'lıyken geçiş: A14. |
| A2 | **RC override** | **Karar (2026-11-10, b):** `flag_control_auto_enabled = true`; pilot çubuğu oynatınca Position'a geçilir (`Commander.cpp:2939-2960`; `COM_RC_OVERRIDE` varsayılan 1, `commander_params.c:430-446`). Kullanıcı: "evet, güvenlik amaçlı olsun." Yan etkileri SITL ön kontrollerinde doğrulanacak (HEARTBEAT `base_mode`, `streams/HEARTBEAT.hpp:98-100`). İlk uçuşta RC'de Position'a ayrılmış bir anahtar konumu yine olmalı. |
| A3 | **Masa testi (GPS yok)** | Kapalı ortamda yerel konum geçersiz → örnekler `CHECK_POSITION` ile atılır → mod aktifse 1.5 s sonra Hold istenir (disarm iken de). **Karar (2026-11-10):** masada gözlenecekler: mod kaydı ve QGC'de `AUTO FOLLOW`; disarm iken moda geçiş; `AF_LOS` alımı (`listener debug_array`, `listener auto_follow_status`: ham LOS, yaş, sıra no, bayrak, `check_result`, sayaçlar); durum geçişleri ve Hold isteği; `auto_follow status`. Geometri ve guidance SITL'de değerlendirilir. Log için kullanıcı `SDLOG_MODE`'u değiştirir ve kartı yeniden başlatır. **Geliştirmeye açık (kullanıcı notu):** dışarıda, arm etmeden, GPS fix'liyken yapılacak testler eklenebilir (geometri ve guidance çıktıları görülebilir); kullanıcı düşünecek. |
| A4 | **Log alan adları** | **Karar (C3, 2026-11-10):** Bölüm 9 tablosu, önek yok; durum adları PASIF / TAKIP / KAYIP_BEKLE / HOLD_ISTENDI. Bütün adlar `log-sozlugu.md`'de. |
| A5 | **Vision ile `AF_LOS` anlaşması** | MAVLink 2: Vision doğruladı (pymavlink MAVLink 2 kullanıyor, B1). Kalanlar Yusuf Ortatepe ile: yerleşim (`data[0..5]`), ad 9 karakter sınırı, sıra no float32 kesinliği, frekans 10–30 Hz, `array_id` kullanımı (öneri: 0, FC kontrol etmez). Eksenler m10 ile (V6). MAVLink tanımı mesaj için "üretimde kullanmayın" notu taşır (`common.xml:7626`); ICD'de değerlendirilir. |
| A6 | **Kamera eğimi → `AF_TRK_ANG`** | Ahmet'in m06 kamera montaj dokümanından; SITL için 30°. |
| A7 | **Kilit listesi talebi** | 7 yol (B2-b ile `rc.mc_apps` eklendi) tek talep olarak Hüseyin'e (bkz. "Kilitli yollar ve flash"). |
| A8 | **Modülün boot'ta başlatılması** | **Karar (B2-b, 2026-11-10):** `ROMFS/px4fmu_common/init.d/rc.mc_apps`'e satır (yedinci kilitli yol). Kanıt: kayıt yalnızca disarm iken kabul edilir (`ModeManagement.cpp:371-380`); `rc.mc_apps` her multikopter açılışında çalışır (SITL `init.d-posix/rcS:289`, 6C `init.d/rcS:485`, → `rc.vehicle_setup:20-24`). Hüseyin reddederse geri dönüş (a): SITL'de pxh'tan `auto_follow start`, 6C'de `/fs/microsd/etc/extras.txt` (`init.d/rcS:25, 599-603`). Satırın koşulu: A13. |
| A9 | **`AF_ALPHA` / `AF_BETA` varsayılanı ve tüm min/max/birimler** | **Karar (öneri kabul, C2):** Bölüm 10 tablosu. |
| A10 | **Hold reddi, hedefsiz giriş, konum geçersizken setpoint** | **Karar (A3, C2):** Bölüm 7–8. |
| A11 | **Kalıcı gönderici** | Vision (m12) ve m06 ile konuşulacak; geçiciyi biz yazıyoruz. |
| A12 | **S1–S7 tanım farkı** | **Karar (A1, A2, 2026-11-10):** konuşulan tablo (`rapor.md` §4.9) esas; S1 → S1a/S1b; eski "kayıt" ve "mod seçimi" başlıkları ön kontrol; RC kaybı ve modül sağlığı m16 adayı (Bölüm 11). |
| A13 | **`rc.mc_apps` satırının koşulu** | **Karar (b):** `if param compare -s AF_ENABLE 1` → `auto_follow start`. Ad `AF_ENABLE` ve varsayılan **0** kullanıcının seçimi. Değer değişince QGC'den reboot yeterli (açılış dosyaları her reboot'ta yeniden çalışır). SITL'de `PX4_PARAM_AF_ENABLE=1`. Parametre `auto_follow/module.yaml`'da tanımlanır, modül derlenince parametre tablosunda vardır. |
| A14 | **Yerde arm'lıyken moda geçişi engelleme (B4)** | **Karar (a):** arming check cevabında `can_arm_and_run = !(vehicle_land_detected.landed && !mode_active)` (`msg/VehicleLandDetected.msg:8`). PX4 arm'lı araçta geçişi reddeder (`UserModeIntention.cpp:58-59`, `externalChecks.cpp:158-160, 188-190`); QGC'de "Switching to … is currently not available" + uyarı sesi (`Commander.cpp:2620-2638`). Disarm iken geçiş serbest; mod aktifken koşul devreye girmez, RTL riski yok. SITL ön kontrolünde doğrulanır. |

## Kabul kriterleri

Issue #6 ("Bitti sayılması için"):
1. Spec klasöründe şemalar var (`planning/visuals/`).
2. PX4'te neyin nereye bağlandığı ve neden yazılmış (bu spec + `rapor.md`).
3. Test sonucu yazılmış: **ne verildi, drone ne yaptı, ULog adı** (her senaryo).
4. Kod `make px4_sitl` ile derleniyor.
5. CI'da `verify-pin`, `derleme-sitl`, `derleme-fmu-v6c` yeşil.
6. PX4'e eklenen yeni dosyaların yolları PR açıklamasında gösteriliyor.

Bu spec'in kararlarından:
- Modül 6C firmware'ine girer; `make px4_fmu-v6c_default` flash kullanımı spec'e yazılır.
- Her SITL testinin ULog'u `~/Desktop/AUTO-FOLLOW LOG/`'a kopyalanır, adı spec'e yazılır.
- `log-sozlugu.md` kodla aynı commit'te güncel; `AUTO_FOLLOW_TARGET` uyarısı içinde.
- `rapor.md` ve görev grubu notları güncel.
- PR açıklamasında `Closes Auto-Follow/Auto-Follow#6`.

## Uygulama sırası (Karar 14.5, öneri kabul)

1. **İskelet:** mod kaydı, arming check (yerde arm'lıyken geçiş engeli dahil, A14), açılışta başlatma satırı (`rc.mc_apps`), 50 Hz çevrim, parametreler; SITL ve 6C derlemesi, flash kullanımı kaydı. (Kilit listesi onayı gelmeden `verify-pin` kırmızı kalır.)
2. **Guidance + alpha-beta:** doğrulama, geometri, filtre, yasa, sınırlar, yaw/irtifa, setpoint. **Log mesajı da burada** (`auto_follow_status`, `log-sozlugu.md` aynı commit; Karar 2026-11-10, kullanıcı "1-a": S1–S5 ilk seferde tam ölçülsün).
3. **Kısa birim testi** (`AutoFollowGuidanceTest.cpp`).
4. **SITL ön kontroller + S1–S5** (S4'ün yalnız KAYIP_BEKLE kısmı; Hold kısmı 5. adımdan sonra — Karar A4).
5. **Hold geçişi** (`VEHICLE_CMD_SET_NAV_STATE`), S4'ün tamamı.
6. **S6–S7 + analiz script'i** (`af_log_analiz.py`), sözlüğün son eşitlemesi.

Her adımdan sonra kontroller geçince commit, görev grubu notu ve `rapor.md` güncellemesi. Yetişmeyenler "m16'ya kalanlar" listesine yazılır.
