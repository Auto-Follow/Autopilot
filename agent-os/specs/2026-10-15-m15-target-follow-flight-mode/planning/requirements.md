# Spec Requirements: Hedef Takip Uçuş Modu (Target Follow Flight Mode)

## Initial Description

> senden istediğim şuan vision ve autopilot repolarını oku analiz et analizini yaptıktan sonra benim görevim doğrultusundan senden iki adet çıktı isticem
>
> ben ne yapıyorum
>
> vision tarafında model tabanlı görüntü işleme ile bir insana detec ediliyor bu hedef bilgisi piksel kamera frame body frame adımlarından sonra bana body frame olarka geliyor ve ben bunu arth frame çeviriyorum daha sonrasında bu hedefi takip ediyorum sadece (dünya düz kabulu ile) ben burada tüm kontrolcüyü yazamak hedefim değil zaten bunu yapmamak için px4 kullanıyorum benim amacım burada istenen durumu guidanceyi yazmak ve bunun doğrultusunda px4 yönledirmek ama bunu fc tarafında yapmak isitiyorum yani bir uçuş modu olucak bu QGC ekranında veya pilot stickle başlatabilecek bu modu şimdi bu anlatığım çok ama çok üst pencereden benim yapamam gerekn bunun doğrultusunda iki adet akış şeması isitiyorum ilki sana atacağım görseldeki gibi üst penceren benim yaptığımı anlatan akış şeması (attığım görsek tamamen referans amaçlı o şekilde basit anlatım diline sahip olması amaçlı) diğeri tamamne bu anlatıklarımda px4 özelinde nasıl yapılcağı çok detaylı anlatan bir akış şeması isitiyorum

(Kaynak: `planning/raw-idea.md`, 2026-10-15. Referans görsel: `planning/visuals/WhatsApp Image 2026-09-26 at 00.07.13.jpeg`)

## Requirements Discussion

### First Round Questions

**Q1:** Bu spec'in çıktısının şimdilik sadece iki akış şeması (tasarım dokümanı) olduğunu, kodlamanın sonraki bir spec'te yapılacağını varsayıyorum. İki şema da spec klasöründe Mermaid (markdown içinde) olacak; metinler Türkçe, teknik terimler İngilizce. Şema 1 referans görseldeki gibi sade ve kutulu (girdiler paralelkenar, işlemler kutu). Şema 2 PX4'e özel ve çok detaylı (modül, uORB topic, commander, QGC/RC, kontrolcü zinciri, failsafe). Doğru mu, yoksa draw.io/PNG gibi başka format mı?
**Answer:** tamam

**Q2:** Pi şu adımları yapar: piksel → kamera frame LOS → gövde (body FRD) frame LOS. FC'ye birim LOS vektörü (veya iki açı) gelir, mesafe gelmez. FC şunları yapar: body → vehicle-carried NED (`vehicle_attitude` ile), down angle ve slant distance (düz dünya + irtifa), hedefin yerel NED konumu, guidance. Düz dünya kabulüyle ECEF ve WGS84 adımları atlanır; WGS84 sadece loglama/QGC gösterimi için opsiyoneldir. Doğru mu, yoksa body → NED dönüşümünü de Pi mi yapsın?
**Answer:** tamam

**Q3:** Kameranın X500'e sabit (gimbalsız), aşağı doğru sabit açıyla monte edildiğini varsayıyorum; montaj açıları ve ötelemesi parametre/config olur. Gimbal var mı? Düz dünya hesabındaki irtifa için EKF yerel konumundan kalkış noktasına göre yükseklik (`vehicle_local_position.z`) öneriyorum. Araçta lidar/rangefinder var mı?
**Answer:** kamerada gimbal yok başka bir arkadaş bu görev için kamerayı kaç derece ile monte ediceğini gazeboda bizim kameraayı kullanrak hesaplıyor onun çıktısına göre bir açı belirlenecek ve sabit kalıcak ama zaten bu bilg dahil edilerek hesaplanmış bir body frame gelmiş olucak bana diğer sorduğunda araçta irtifa bilgisi sadece barodan gelicek o yüzden deiğin mantıklı olabilir onu konuşalım

**Q4:** Pi → Pixhawk mesajı (ICD) için v1.17.0'da kullanılabilecek seçenekler: (a) `DEBUG_VECT` (isim + gövde FRD birim LOS; en basit, ancak zaman damgası FC'ye varışta basılır), (b) `LANDING_TARGET` (zaman senkronlu ama v1.17.0 body frame'i reddediyor, açı modu `irlock_report` ile çakışıyor), (c) `FOLLOW_TARGET` (lat/lon; geo-referanslamayı Pi'ye taşır). (a) ile başlamayı, "hedef yok" durumunu zaman aşımıyla anlamayı, 10–30 Hz ve < 150 ms gecikme bütçesini öneriyorum. Confidence gönderilsin mi?
**Answer:** bunu tek başıma karak veremem burayı not al konuşalım

**Q5:** Mod mimarisi için önerim: FC içinde çalışan yeni modül `src/modules/tez_follow`, kendini uORB üzerinden "external mode" olarak kaydeder (upstream `mc_nn_control` emsali). QGC'de kendi adıyla görünür, RC switch'e `COM_FLTMODEx = External Mode N` ile atanır, `trajectory_setpoint` yayınlar, PX4 kontrolcüleri uçurur. Gerekenler: `allowed-paths.txt`'ye `src/modules/tez_*` ve iki `.px4board` dosyası eklenir. Alternatifler: (b) mevcut Follow Me (`FlightTaskAutoFollowTarget`), (c) yeni FlightTask + yeni `nav_state` (kilitli dosyaları değiştirir). (a) onaylanıyor mu?
**Answer:** mevcut follow me kullanmak istemiyorum guidanci ben yazıcam

**Q6:** Guidance yasası önerisi: sabit irtifa (moda girişteki irtifa veya `TEZ_FOL_ALT`), LOS doğrultusunda sabit yatay takip mesafesi (örn. 5 m, parametre), yaw hep hedefe bakar. Çıkış `trajectory_setpoint` içinde NED hız + yaw; P yasası + hedef hızı ileri beslemesi + parametreli saturation; hedef hızı FC'de alfa-beta/low-pass ile kestirilir. Uygun mu, yoksa `goto_setpoint` mı? Kafanda belirli bir yasa (PN, pure pursuit vb.) var mı?
**Answer:** bende şuan böyle düşüyonüyorum ancak buradaki çeşitli yasaların anlatımını yaptığın bir .md yaz ve masaüstüne kaydet (repodan bağımsız)

**Q7:** Mod sadece havadayken aktif edilebilir, bu modda arm edilemez. Hedef kaybolursa (`TEZ_FOL_TOUT` ≈ 1 s) araç yerinde asılı kalır, yaw son bilinen yönde tutulur; ≈ 5–10 s sonra Hold'a geçilir. Pilot stick oynatırsa Position'a dönülür (`COM_RC_OVERRIDE`). Diğer failsafe'ler PX4 varsayılanında kalır, `defer_failsafes` kullanılmaz. Min irtifa, max hız ve max yaw hızı parametrelerle sınırlanır. Doğru mu?
**Answer:** buda hold da bekleme olayı okey ama pilot stickle başka uçuş moduna geçip devam etsin stick oynatması ile mod değiştirmesin

**Q8:** Kapsam dışı: Vision algılama modeli ve kamera kalibrasyonu, çoklu hedef seçimi / re-ID, gimbal kontrolü, ROS 2 / uXRCE-DDS, ECEF/WGS84 dönüşümleri, engelden kaçınma, düz olmayan arazi, mod içinde otomatik kalkış/iniş, gerçek kod. Şema 2'nin sonuna doğrulama akışı (Gazebo Harmonic SITL → ULog/pyulog → gerçek uçuş) eklenir. Doğru mu?
**Answer:** evet

**Q9 (mevcut kod / görsel):** Referans alınacak mevcut kod, prototip (MATLAB/Python) veya guidance denklemi var mı? Ek görsel (kamera montajı, takip geometrisi) var mı?
**Answer:** hayır yok şuan

### Existing Code to Reference

Kullanıcı kendi kodunu veya prototipini vermedi ("hayır yok şuan"). Aşağıdakiler repo analizinde araştırmacının bulduğu PX4 v1.17.0 referanslarıdır; spec yazarı bunları kullanmalıdır.

**Similar Features Identified:**
- Feature: FC içinden external mode kaydı (uORB) - Path: `src/modules/mc_nn_control/mc_nn_control.cpp`
  - Kullandığı akış: `register_ext_component_request` → `register_ext_component_reply` → `config_control_setpoints` (vehicle_control_mode) → `arming_check_request` / `arming_check_reply` → `unregister_ext_component`
- Feature: Mod yönetimi (commander) - Path: `src/modules/commander/ModeManagement.cpp`, `src/modules/commander/module.yaml` (`COM_MODE${i}_HASH`, `COM_FLTMODE${i}` = 100..107 External Mode 1..8)
- Feature: Stick override mantığı - Path: `src/modules/commander/Commander.cpp` (~2936–2970), `src/modules/commander/commander_params.c` (`COM_RC_OVERRIDE`, `COM_RCL_EXCEPT`)
- Feature: External modda FlightTask'ın devre dışı kalması - Path: `src/modules/flight_mode_manager/FlightModeManager.cpp` (~140)
- Feature: Setpoint tüketicileri - Path: `src/modules/mc_pos_control/MulticopterPositionControl.cpp`, `src/modules/mc_pos_control/GotoControl/`
- Feature: Modül iskeleti - Path: `src/examples/work_item`
- Feature: MAVLink alıcı (ICD adayları) - Path: `src/modules/mavlink/mavlink_receiver.cpp` (`handle_message_debug_vect`, `handle_message_landing_target`, `handle_message_follow_target`)
- Sadece guidance fikri için okunabilir, kullanılmayacak: `src/modules/flight_mode_manager/tasks/AutoFollowTarget/` (Follow Me + `follow_target_estimator`). Kullanıcı mevcut Follow Me'yi kullanmayı reddetti.
- Components to potentially reuse: uORB topic'leri `trajectory_setpoint`, `goto_setpoint`, `vehicle_attitude`, `vehicle_local_position`, `vehicle_status`, `debug_vect`, `config_control_setpoints`, `mode_completed`
- Backend logic to reference: `mc_nn_control` kayıt/arming-check deseni; `Commander.cpp` stick override koşulları

## Follow-up Questions

Ek soru sorulmadı. Orkestratör kullanıcı cevaplarını şöyle yorumladı ve bu yorum kayda geçti:

1. Çıktılar spec klasöründe iki Mermaid akış şemasıdır. Metinler Türkçe, teknik terimler İngilizce. Şema 1 referans görsel gibi sadedir, Şema 2 PX4'e özel ve detaylıdır.
2. İş bölümü onaylandı.
   - Pi: piksel → kamera LOS → body FRD LOS.
   - FC: body → NED, düz dünya altında down angle / slant range, hedefin yerel NED konumu, guidance.
   - ECEF/WGS84 atlanır (WGS84 yalnızca loglama/QGC için opsiyonel).
3. Gimbal yok. Kamera montaj açısı bir ekip arkadaşının Gazebo çalışmasıyla belirlenecek ve sabit kalacak. FC'ye gelen body-frame LOS bu montaj dönüşümünü zaten içerir, yani montaj açıları FC'nin işi değildir. Araçta irtifa kaynağı yalnızca barometredir. `vehicle_local_position.z` (baro füzyonlu, kalkışa göre yükseklik) geçici olarak kabul edildi; ancak bu bir **açık konu** (baro drift, zemin düzlemi kabulü, yerden yükseklik ile home'a göre yükseklik farkı).
4. ICD bir **açık konu** ve ekipçe karar verilecek. Şemalarda genel bir "Pi→FC hedef LOS mesajı (ICD TBD)" kutusu yer alır; `DEBUG_VECT` mevcut aday olarak not edilir.
5. Mevcut Follow Me kullanılmaz, guidance'ı kullanıcı yazar. Mimari: FC içinde `tez_follow` benzeri bir modül, `mc_nn_control` gibi uORB üzerinden external mode olarak kayıtlı (seçenek a). `allowed-paths.txt` ve `.px4board` değişiklikleri ayrı onay/PR gerektiren bir ön koşul olarak not edildi; henüz onaylanmadı.
6. Önerilen guidance yasası şimdilik çalışma temelidir, nihai yasa açıktır. Guidance yasalarını anlatan ayrı bir doküman orkestratör tarafından repo dışında yazılıyor: `/home/yusuf/Desktop/guidance-yasalari.md`.
7. Hedef kaybı davranışı kabul edildi: ~1 s sonra yerinde bekle ve yaw'ı tut, ~5–10 s sonra Hold. Stick hareketi modu **değiştirmemeli**. Pilot moddan RC mod anahtarı (veya QGC) ile çıkar. PX4 v1.17'nin stick override'ı external modlara nasıl uyguladığı doğrulama maddesi olarak kaydedildi.
8. Kapsam dışı listesi onaylandı. Şema 2'nin sonuna doğrulama akışı eklenir.
9. Mevcut kod/prototip veya ek görsel yok.

## Visual Assets

### Files Provided:
- `WhatsApp Image 2026-09-26 at 00.07.13.jpeg`: Beyaz zemin üzerinde siyah çerçeveli, mavi oklu, düşey ana zincirli bir akış şeması (Visio tarzı).
  - Girdiler paralelkenar:
    - "Target Location in Pixel Coordinate System"
    - "Camera Translation in X,Y,Z Directions w.r.t IMU in Body Coordinate System"
    - "Camera Tilt, Pan and Roll values w.r.t IMU in Body Coordinate System"
    - "UAV Roll", "UAV Pitch", "UAV Yaw"
    - "Altitude"
    - "UAV Location in WGS84 Coordinate System"
  - İşlemler yuvarlak köşeli kutu:
    - LOS Vector in Camera Coordinate System
    - → LOS Vector in Body Coordinate System
    - → LOS Vector in Vehicle Carried NED Coordinate System
    - → Down angle and Slant Distance Calculation
    - → Target Location in Vehicle Carried NED
    - → Target Location in ECEF
    - → Target Location in WGS84
  - Yan kol: UAV WGS84 → UAV ECEF → Altitude → Down angle/Slant Distance.

### Visual Insights:
- Tasarım dili: tek sütun ana akış. Yan girdiler, ilgili işlem kutusuna yatay oklarla bağlanır. Her kutuda kısa, isim cümlesi şeklinde etiket var. Şema 1 bu dili taklit edecek.
- Kullanıcının akışı referanstan iki noktada ayrılıyor:
  - (1) Piksel → kamera → body adımları Pi'de yapılıyor ve montaj açıları dahil edilmiş halde geliyor. Şema 1'de bu adımlar "Vision (Pi)" olarak gruplanmalı.
  - (2) Düz dünya kabulü var. ECEF/WGS84 adımları yerine "Target Location in Local NED" ile bitip **guidance → PX4 kontrolcüleri → araç** adımlarıyla devam edilmeli.
- İrtifa kaynağı referansta WGS84→ECEF'ten geliyor. Bu projede baro füzyonlu EKF yüksekliğinden gelecek (açık konu).
- Fidelity level: düşük-orta sadakatli referans diyagram (görsel dil/üslup rehberi; birebir içerik değil).

## Requirements Summary

### Functional Requirements

**Çıktılar (bu spec):**
- **Şema 1 (üst seviye, sade):** Referans görsel üslubunda Mermaid flowchart. Kullanıcının uçtan uca ne yaptığını anlatır, metinler Türkçe ve teknik terimler İngilizce. Zincir şöyle:
  - Pi'de (gruplanmış): hedef piksel → kamera LOS → body frame LOS (montaj açısı dahil).
  - Pi → FC mesajı (ICD TBD).
  - UAV roll/pitch/yaw ile vehicle-carried NED LOS.
  - İrtifa (baro/EKF) ile down angle ve slant distance (düz dünya).
  - Hedefin yerel NED konumu.
  - Guidance (istenen durum: hız/yaw setpoint).
  - PX4 kontrolcüleri.
  - Araç hedefi takip eder.
- **Şema 2 (PX4'e özel, çok detaylı):** Mermaid flowchart (gerekirse alt şemalara bölünmüş). Şunları kapsar:
  - Vision → MAVLink (TELEM2, `/dev/ttyAMA0`; SITL'de UDP) → `mavlink_receiver` → uORB (aday: `debug_vect`, ICD TBD).
  - `tez_follow` modülü (ScheduledWorkItem, `work_item` deseni):
    - Girdi doğrulama: `PX4_ISFINITE`, aralık, zaman damgası / zaman aşımı.
    - body → NED dönüşümü (`vehicle_attitude` quaternion).
    - Düz dünya kesişimi (`vehicle_local_position`, baro füzyonlu yükseklik).
    - Hedef NED konumu, hedef hızı filtresi.
    - Guidance yasası, saturation.
    - `trajectory_setpoint` yayını.
  - Mod kaydı:
    - `register_ext_component_request` / `reply` (commander `ModeManagement`).
    - `config_control_setpoints` bayrakları.
    - `arming_check_request` / `reply`.
    - `NAVIGATION_STATE_EXTERNALx`.
    - `COM_MODE_HASH`.
    - `unregister_ext_component`.
  - Mod seçimi:
    - QGC 5.1.4 mod listesi (AVAILABLE_MODES, `VEHICLE_CMD_DO_SET_MODE`).
    - RC mod anahtarı (`COM_FLTMODEx` = 100..107).
    - `vehicle_status.nav_state`.
  - Kontrolcü zinciri:
    - `FlightModeManager` external modda FlightTask'ı kapatır.
    - `mc_pos_control` → `vehicle_attitude_setpoint` → `mc_att_control` → `mc_rate_control` → `control_allocator` → motorlar.
  - Failsafe ve geçişler: hedef kaybı zaman aşımı → yerinde bekle → Hold; RC mod anahtarıyla çıkış; PX4 varsayılan failsafe'leri.
  - Parametreler (`TEZ_` önekli, `module.yaml`).
  - Loglama (ULog).
  - Sonda doğrulama akışı: GoogleTest → Gazebo Harmonic SITL → ULog/pyulog analizi → gerçek uçuş.

**Hedeflenen uçuş modunun davranışı (şemaların anlatacağı):**
- Mod FC içinde çalışır. QGC ekranından veya RC mod anahtarından seçilir.
- Mod yalnızca havadayken aktif edilir (Position modunda kalkış, sonra moda geçiş). Bu modda arm edilemez.
- FC'ye Pi'den body FRD frame'de LOS gelir. Bu LOS kamera montaj dönüşümünü zaten içerir; FC montaj açısı bilmez.
- FC işlem zinciri:
  - body → vehicle-carried NED (UAV roll/pitch/yaw).
  - Düz dünya kabulüyle down angle ve slant distance (irtifa: baro füzyonlu EKF yüksekliği; açık konu).
  - Hedefin yerel NED konumu (EKF orijinine göre).
  - Guidance.
- Guidance (çalışma temeli, nihai değil):
  - Sabit irtifa (moda giriş irtifası veya `TEZ_FOL_ALT`).
  - LOS doğrultusunda sabit yatay takip mesafesi (örn. 5 m, parametre).
  - Yaw hedefe bakar.
  - Çıkış: `trajectory_setpoint` içinde NED hız + yaw.
  - P yasası + hedef hızı ileri beslemesi (FC'de alfa-beta / low-pass kestirim).
  - Hız/yaw hızı parametrelerle saturation.
- Hedef kaybı:
  - Son geçerli mesajdan ~1 s sonra (`TEZ_FOL_TOUT`) araç yerinde asılı kalır ve yaw'ı tutar.
  - ~5–10 s içinde hedef dönmezse PX4 Hold moduna geçilir.
- Stick hareketi modu **değiştirmez**. Pilot moddan RC mod anahtarıyla (veya QGC'den) başka bir uçuş moduna geçerek çıkar.
- Batarya, RC/veri bağlantısı kaybı, geofence ve EKF failsafe'leri PX4 varsayılanında kalır. `defer_failsafes` kullanılmaz.
- Güvenlik sınırları parametrelidir: min irtifa, max yatay/dikey hız, max yaw hızı.

### Reusability Opportunities
- `mc_nn_control`: FC içi external mode kayıt/arming-check/kayıt silme deseni birebir model alınır.
- `src/examples/work_item`: modül iskeleti (ModuleBase + ModuleParams + ScheduledWorkItem).
- PX4'ün mevcut kontrolcü zinciri (`mc_pos_control` ve sonrası) olduğu gibi kullanılır. Kontrolcü yazılmaz, yalnızca guidance yazılır.
- `trajectory_setpoint` (veya alternatif olarak `goto_setpoint` + `GotoControl`) mevcut setpoint arayüzleridir.
- Mevcut MAVLink mesajları (`DEBUG_VECT` adayı); yeni MAVLink mesajı eklenmez.
- Mevcut Hold modu, hedef kaybı sonrası geri düşüş için kullanılır.
- `follow_target_estimator`: yalnızca fikir kaynağı (hedef hızı kestirimi); Follow Me kullanılmaz.

### Scope Boundaries
**In Scope:**
- İki Mermaid akış şeması (spec klasöründe): Şema 1 sade/üst seviye, Şema 2 PX4'e özel/detaylı.
- Şema 2'nin sonunda doğrulama akışı (GoogleTest → Gazebo Harmonic SITL → ULog/pyulog → gerçek uçuş).
- Açık konuların şemalarda "TBD" olarak açıkça gösterilmesi (ICD, irtifa kaynağı, nihai guidance yasası).

**Out of Scope:**
- Gerçek kod (modül implementasyonu sonraki spec'te)
- Mevcut PX4 Follow Me (`FlightTaskAutoFollowTarget`, `NAVIGATION_STATE_AUTO_FOLLOW_TARGET`) kullanımı
- Yeni FlightTask veya yeni `nav_state` eklemek (kilitli commander/msg/flight_mode_manager dosyaları)
- Vision tarafı: algılama modeli, kamera kalibrasyonu, piksel → body dönüşümünün implementasyonu
- Kamera montaj açısının belirlenmesi (ekip arkadaşının Gazebo çalışması)
- Birden fazla insan arasından hedef seçimi / yeniden tanıma (Pi tek hedef gönderir)
- Gimbal kontrolü (gimbal yok)
- ROS 2 / uXRCE-DDS, px4-ros2-interface-lib
- ECEF/WGS84 dönüşümleri (WGS84 yalnızca opsiyonel loglama/gösterim)
- Engelden kaçınma, düz olmayan arazi
- Mod içinde otomatik kalkış/iniş
- Yeni MAVLink mesajı/dialect, PX4 sürüm değişikliği
- Guidance yasalarını anlatan doküman bu spec'in parçası değil; repo dışında `/home/yusuf/Desktop/guidance-yasalari.md` olarak ayrıca yazılıyor.

### Technical Considerations

**Ortam ve kısıtlar:**
- PX4 v1.17.0 kalıcı olarak kilitli. Upstream dosyalar düzenlenmez, kendi dosyalar eklenir. `v*` tag açılmaz.
- Donanım: Holybro X500 V2, Pixhawk 6C (`px4_fmu-v6c_default`, `SYS_AUTOSTART=4019`), Raspberry Pi 5 (TELEM2 seri), QGC 5.1.4, Gazebo Harmonic.
- **Ön koşul (henüz onaylanmadı, ayrı PR):** `tez/pin/allowed-paths.txt` dosyasına şunlar eklenmeli:
  - `src/modules/tez_*`
  - `boards/px4/fmu-v6c/default.px4board`
  - `boards/px4/sitl/default.px4board`

  Ardından modül `CONFIG_MODULES_TEZ_FOLLOW=y` ile açılır.
- Mod kaydı ROS 2 olmadan, doğrudan uORB üzerinden yapılır (`mc_nn_control` emsali). `FlightModeManager` `NAVIGATION_STATE_EXTERNAL1..8` durumunda FlightTask'ı kapatır, bu yüzden setpoint'i modül yayınlar.
- Stick override (doğrulama maddesi, ön bulgu): v1.17.0 `Commander.cpp` stick override'ı yalnızca şu durumda uygular:
  - Modun `vehicle_control_mode` bayraklarında `flag_control_auto_enabled` veya `flag_control_offboard_enabled` true ise, ve
  - `COM_RC_OVERRIDE` ilgili biti açıksa.

  Bu nedenle mod `config_control_setpoints` içinde bu iki bayrağı false (ve `flag_control_manual_enabled` false) yayınlarsa stick hareketi modu değiştirmemeli. Bu, SITL'de doğrulanmalı. Ayrıca kontrol edilmesi gerekenler:
  - Failsafe framework içindeki override (`failsafe/framework.cpp`) davranışı
  - RC kaybında `COM_RCL_EXCEPT` bit 3 (External Mode) etkisi
- Kodlama standartları (sonraki spec için):
  - `TEZ_` önekli parametreler (≤16 karakter, `module.yaml`'da min/max/unit)
  - Dış veride `hrt_absolute_time()` ile zaman aşımı
  - `PX4_ISFINITE` doğrulaması, setpoint saturation
  - Dinamik bellek ve exception yok; `double` yoğun hesaptan kaçınma (6C FLASH/RAM)
  - `perf_counter`; `events` ile QGC bildirimleri
  - GoogleTest + SITL + pyulog testleri

**Açık konular (ekipçe karar verilecek):**
1. **ICD (Pi → FC mesajı):** Karara bağlanacaklar:
   - Mesaj tipi: `DEBUG_VECT` mevcut aday; `LANDING_TARGET` ve `FOLLOW_TARGET`'ın v1.17.0 kısıtları yukarıda.
   - LOS gösterimi: birim vektör veya iki açı.
   - Hız (öneri 10–30 Hz) ve gecikme bütçesi (öneri < 150 ms).
   - Zaman damgası / yakalama anı (`DEBUG_VECT`'te FC varış anı basılıyor; görüntü anındaki tutumla eşleştirme sorunu).
   - Confidence alanı ve "hedef yok" sinyali.

   Şemalarda "ICD TBD" olarak gösterilir.
2. **İrtifa kaynağı:** Araçta yalnızca barometre var. `vehicle_local_position.z` (baro füzyonlu, EKF orijinine/kalkışa göre) geçici kabul. Konuşulacaklar:
   - Baro drift'inin slant range hatasına etkisi
   - Hedefin kalkış zeminiyle aynı düzlemde olduğu kabulü
   - Yerden yükseklik ile home'a göre yükseklik farkı
   - İleride rangefinder ihtiyacı
3. **Nihai guidance yasası:** Yukarıdaki yasa çalışma temelidir. Alternatifler (pure pursuit, PN, sabit takip açısı vb.) `/home/yusuf/Desktop/guidance-yasalari.md` dokümanına göre değerlendirilecek. Setpoint tipi de bu kararla netleşir: `trajectory_setpoint` hız + yaw, veya `goto_setpoint`.
4. **Kamera montaj açısı:** Ekip arkadaşının Gazebo çalışmasıyla belirlenecek. FC'yi etkilemez (LOS dönüşümü Pi'de yapılır), ancak görüş alanı ve takip mesafesi/irtifa seçimini etkiler.
5. **Ön koşul onayı:** `allowed-paths.txt` + `.px4board` değişikliği için ekip onayı ve ayrı PR.
6. **Doğrulama maddesi:** External modda stick override'ın tetiklenmediği ve RC mod anahtarıyla çıkışın çalıştığı SITL'de doğrulanacak.
7. Zaman aşımı ve Hold'a geçiş süreleri (~1 s, ~5–10 s) parametre olarak kesinleşecek.
