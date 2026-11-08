# Task Group 7: Son Gözden Geçirme (Çapraz Tutarlılık, Sözdizimi ve Kapsam)

Bu rapor iki şemanın son gözden geçirmesidir. Spec ile PX4 v1.17.0 kaynağı arasındaki tüm farkları (F1–F36), kalan "(doğrulanacak)" maddeleri, açık konuları (TBD) ve sizin karar vermeniz gereken noktaları tek yerde toplar.

- Kaynak: branch `yusuf/agent-os-denemeleri-ve-sema-olusturma`, commit `503566a6bc`. Satır numaraları bu commit içindir.
- Değişen dosyalar yalnızca spec klasöründedir. Commit atılmadı, branch değişmedi.
- Konum notu: tasks.md'nin genel kuralı spec klasörüne iki şema dışında dosya eklenmemesini söyler. Bu rapor, Task Group 1 envanteri gibi orkestratörün isteğiyle `implementation/` altına yazıldı.

## 1. İki şemanın kısa özeti

**Şema 1 (`diagrams/01-ust-seviye-akis.md`):** Referans görselin üslubunda tek sayfalık sade akış (16 node). Pi tarafı kamera görüntüsünden body FRD LOS üretir. "Pi → FC hedef LOS mesajı (ICD TBD)" iki tarafı bağlar. FC tarafı LOS'u vehicle-carried NED'e çevirir, düz dünya kabulüyle down angle ve slant range hesaplar, hedefin yerel NED konumunu bulur, hedefi kestirir, guidance ile hız ve yaw üretir. Bu isteği PX4 kontrolcüleri uygular. ECEF/WGS84 yoktur.

**Şema 2 (`diagrams/02-px4-detayli-akis.md`):** PX4 v1.17.0'a özel dört blok:

| Blok | İçerik | Node / kenar |
|---|---|---|
| (A) | Derleme ön koşulu, başlatma noktaları, `mc_nn_control` desenindeki kayıt, kontrol modu yapılandırması, arming check döngüsü, kayıt silme | 47 / 56 |
| (B) | Her `Run()` çevrimi: `debug_vect` → mod kapısı → giriş hazırlığı → konum geçerliliği → dört adımlı girdi doğrulama → geolocation → kestirim → guidance → saturation → `trajectory_setpoint` → kontrolcü zinciri → motorlar | 56 / 72 |
| (C) | QGC ve RC ile moda giriş, giriş koşulları, stick override, çıkış, hedef kaybı (Hold isteği), güvenli taraf, PX4 varsayılan failsafe'leri ve RTL fallback'i | 61 / 73 |
| (D) | Doğrulama: GoogleTest → Gazebo Harmonic SITL → sahte Pi → S1–S7 senaryoları → ULog + pyulog metrikleri → gerçek uçuş kapısı | 49 / 63 |

## 2. Task Group 7'de yapılan değişiklikler

Tüm değişiklikler küçüktür ve kaynağa dayanır.

1. **(B)/(C) hedef kaybı boşluğu kapatıldı (öneri).** Önceden (B)'de `bAccept` ölçüm zamanını `u_D` kontrolünden önce yeniliyordu. Bu yüzden `u_D` geçersiz ölçümler `TEZ_FOL_TOUT` sayacını sıfırlıyor, araç güvenli tarafta süresiz kalabiliyordu. Şimdi:
   - `bAccept` yalnızca `LOS_body`'yi saklar. Sayaç burada yenilenmez.
   - `bUdQ` "evet" kenarı: "son geçerli ölçüm zamanı güncellenir (öneri)". "hayır" kenarı: "zaman güncellenmez (öneri)".
   - `bAgeQ` ve `cAgeQ` aynı metne getirildi: "Son geçerli ölçüm (dört adım + u_D) TEZ_FOL_TOUT (öneri) içinde mi?".
   - `cBackQ`: "Yeni geçerli ölçüm geldi mi? ((B) dört adımlı girdi doğrulama + u_D)".
   - S5 senaryosuna (`dSc5`) "u_D geçersizliği TEZ_FOL_TOUT (öneri)'dan uzun sürerse hedef kaybı" eklendi.
   - (B) notlarına kuralı açıklayan bir madde eklendi.
2. **Yedinci TBD tabloya eklendi.** Task Group 6, (D)'de "Hareketli insan modeli ve tez dünyasının konumu" TBD node'unu çizmişti, ama "Açık konular (TBD)" tablosunda altı satır vardı. Spec (D) bu konuyu zaten "Model konumu TBD" olarak verir. Bu yüzden tabloya 7. satır eklendi. Envanterdeki (`1-ad-envanteri.md`) TBD başlığı ve "Ek açık nokta" maddesi de yedi olarak güncellendi. Spec'in istediği altı TBD aynen duruyor (bkz. bölüm 6). tasks.md 7.4'teki "altı TBD" metni değiştirilmedi.
3. **RC kaybı gecikmesi (C)'ye eklendi (F35).** `cRclAct`: "COM_RC_LOSS_T (0.5 s) sonra COM_FAIL_ACT_T (5 s) Hold, ardından NAV_RCL_ACT (varsayılan 2 = Return). RC dönünce tez_follow'a otomatik dönülmez (SITL'de doğrulanacak)". Bu metin (D) S6 ile aynıdır. (C) notlarına kaynak satırları eklendi.
4. **Etiket tutarlılığı:** `cAgeQ → cLost` kenarı "hayır: TEZ_FOL_TOUT (öneri) aşıldı" oldu. `aStartSitl` içindeki `.post` yolu ve `dTarget` içindeki `gz_x500_tez` hedefi "(öneri)" aldı. Lejant bu adların öneri olduğunu söylüyordu.
5. **Fallback zinciri (F26):** (C)'deki `cRtl` ve (C) giriş metni "RTL çalışamazsa Land, sonra Descend, en sonda Terminate" oldu. Bu metin (D) S7 ve `framework.cpp:536-605` ile aynıdır.
6. **Kayıt başına sayaç (F36):** `dSession` ve (D) notu "oturum başına en fazla 3 geri dönüş" yerine "kayıt başına" diyor. `total_num_unresponsive` yeni kayıtta sıfırlanır (`externalChecks.cpp:70`).
7. **Kayıt silme alanları (F20):** `aUnreg` artık "name (kayıttaki adla birebir), arming_check_id, mode_id, mode_executor_id = -1" yazar. Kaynak satırları (A) notlarına eklendi.

## 3. Kontrol sonuçları

| Grup | Kontrol | Sonuç | Not |
|---|---|---|---|
| 1 | K1–K5 (envanter, 174 ad) | Task Group 1'de 174/174 | Bu grupta envanter yeniden taranmadı. Şemadaki adlar için iki kontrol yeniden çalıştırıldı (aşağıda G1) |
| 1 (tekrar) | G1-K1: kenar etiketindeki her topic `msg/` içinde. G1-K3: Şema 2'deki her parametre kaynakta tanımlı, `TEZ_FOL_*` tanımsız | 2/2 | 26 ad (3'ü topic değil, mesaj alanı: `xy_valid`, `z_valid`, `local_position_invalid`), 25 parametre |
| 2 | K1–K5 (Şema 1) | 5/5 | 16 node, ECEF/WGS84 yok, dört yan girdi paralelkenar, ICD ve irtifa `tbd` |
| 3 | K1–K5 ((A)) | 5/5 | |
| 4 | K1–K7 ((B)) | 33/33 | |
| 5 | K1–K5 ((C)) | 5/5 | |
| 6 | K1–K5 ((D)) | 26/26 | |
| 7 | 7.6: K7-1..K7-10 | 10/10 | Aşağıda |
| Sözdizimi (2.1 K6, 3.1 K6, 4.1 K7, 5.1 K6, 6.1 K5, 7.2) | MPE Mermaid parse + headless Chrome render | 5/5 blok | Tüm bloklarda `syntax-error-markers=0` |

Toplam: bu grupta 91 otomatik kontrol çalıştırıldı (2 + 5 + 5 + 33 + 5 + 26 + 10 + 5 sözdizimi bloğu) ve hepsi geçti. Ayrıca 7.2'deki elle kontrol listesi uygulandı. Envanterin 174 kontrolü Task Group 1'de geçmişti.

**7.6 kontrolleri (en fazla 10):**

| # | Kontrol | Sonuç |
|---|---|---|
| K7-1 | Şema 1 ana zincir adları (Body FRD LOS, Vehicle-carried NED LOS, down angle / slant range, Hedefin yerel NED konumu, Hedef kestirimi, Guidance) (B)'de birebir geçiyor | PASS |
| K7-2 | "Açık konular" tablosunun her satırı bir `tbd` node'una karşılık geliyor (7 = 7) | PASS |
| K7-3 | `TEZ_FOL_*`, `CONFIG_MODULES_TEZ_FOLLOW`, `*gz_x500_tez*`, "Tez Follow" geçen her node ve kenar etiketi "öneri" taşıyor | PASS (önce 3 FAIL, düzeltildi) |
| K7-4 | Task Group 1'de "(doğrulanacak)" kalan maddeler şemada bu etiketi taşıyor | PASS |
| K7-5 | Kapsam dışı içerik yok (ECEF, WGS84, `NAVIGATION_STATE_AUTO_FOLLOW_TARGET`, ROS 2, uXRCE, gimbal, re-ID, rangefinder). `FlightTaskAutoFollowTarget` yalnızca "kullanılmaz" notunda | PASS |
| K7-6 | (B)'de `u_D` geçersiz ölçüm hedef kaybı sayacını yenilemiyor, (C) ile aynı kural | PASS (önce FAIL, düzeltildi) |
| K7-7 | (C) RC kaybı: `COM_FAIL_ACT_T` beklemesi, `NAV_RCL_ACT`, otomatik dönüş yok | PASS (önce FAIL, düzeltildi) |
| K7-8 | Şema 2 notlarında atıf yapılan 71 repo yolu mevcut (planlanan yollar ve glob'lar hariç) | PASS |
| K7-9 | Tüm bloklar MPE Mermaid ile parse ediliyor | PASS |
| K7-10 | Branch doğru, `git status` yalnızca `agent-os/specs/` altında | PASS |

**7.2 elle kontrol listesi:** `mmdc`, `node` ve `npx` kurulu değil, yeni araç kurulmadı. Bunun yerine VS Code'daki Markdown Preview Enhanced eklentisinin Mermaid paketiyle parse ve headless Chrome ile render yapıldı. Yapısal denetim (`mmd_check.py`) Şema 2'nin dört bloğunda 0 hata verdi. Şema 1'de verdiği 5 hata denetleyicinin bilmediği geçerli sözdizimidir (`direction TB`, `style`, subgraph'a giden kenar). Mermaid bunları kabul edip render ediyor. Her blok ` ```mermaid ` + `flowchart` ile başlıyor. Etiketler tırnaklı, node id'leri ASCII ve benzersiz, anahtar kelime id yok, her `subgraph` bir `end` ile kapanıyor. İndeksli `linkStyle` yok, yalnızca `linkStyle default` kullanılıyor.

**7.3 terminoloji:** Şema 1'deki FC zinciri ve yan girdiler (B)'de aynı adlarla geçiyor. (B)'nin başındaki eşleme tablosu her Şema 1 kutusunu bir (B) node'una bağlıyor. Şema 1'deki Pi içi adımlar ("Kamera görüntüsü", "Model ile insan tespiti", "Kamera frame LOS") (B)'de yok. Bu adımlar spec'te kapsam dışıdır (Vision tarafı), (B) "Body FRD LOS (montaj açısı dahil)" kutusuyla başlıyor. "İrtifa" (Şema 1) ve "Yükseklik kaynağı" (TBD) farklı adlarla geçiyor, ama ikisi de spec'teki adlardır.

## 4. Spec ↔ kaynak farkları (F1–F36)

"Şema" sütunu şemaların kaynağı izleyip izlemediğini gösterir. F1–F18 envanterden, F19 ve F21–F36 Task Group 3–6 notlarından gelir. F20'yi bu grup tanımladı.

| # | Fark (kısa) | Blok | Şema |
|---|---|---|---|
| F1 | `arming_check_reply.request_id` spec listesinde yok. Commander yalnızca eşleşen `request_id` ve son 300 ms içindeki cevabı kabul eder. Bu alanların hepsi `arming_check_reply`'dadır, istekte değil | A | Kaynağı izliyor (`aReplyBuild`) |
| F2 | "3 cevapsız istek": koşul `> 3`, yani unresponsive 4. ardışık cevapsız istekte olur. Kayıttan sonra ilk cevaba kadar sınır 10 | A | İzliyor (`aNoReply`, `aInitNote`) |
| F3 | `config_control_setpoints` "birebir" kullanılmaz. Commander `flag_armed` ve `flag_multicopter_position_control_enabled` alanlarını yeniden türetir (sonuç yine true) | A | İzliyor (`aUpdCtl`, `aNnDiff`) |
| F4 | Mod aktifken kayıt silinirse Hold. Çökme veya unresponsive durumunda RTL | A, C | İzliyor (`aHold`, `aFallback`, `cRtl`) |
| F5 | `generateFailsafeSetpoint` yalnızca pozisyon kontrolü yeni açıldıysa üretilir. Position/Hold'dan geçişte son FlightTask setpoint'i kullanılır | B | İzliyor (`bFirstWarn`) |
| F6 | `want_takeoff`'u mc_pos_control yalnızca offboard'da kendisi hesaplar. External modda son `vehicle_constraints` değeri kalır | A | İzliyor, sadeleştirilmiş (`aPosCtl`) |
| F7 | Stick override'ın ek koşulları: armed, `valid`, `sticks_moving`, rotary wing. Failsafe sırasında devralma `_failsafe_user_override_request` ile olur | C | İzliyor (`cOvQ`, `cOvNote`) |
| F8 | `debug_vect.name` en fazla 9 karakter. MAVLink `time_usec` taşınmaz, timestamp FC'ye varış anıdır | B | İzliyor (`bRecv`, `bPiSend`, `bTsNote`) |
| F9 | ULog `debug_vect`'i yalnızca `SDLOG_PROFILE` bit 5 açıkken kaydeder | B, D | İzliyor (`bLog`, `dLog`) |
| F10 | `mc_nn_control` bir `px4::WorkItem`'dır ve callback ile çalışır. `ScheduledWorkItem` + `ScheduleOnInterval` deseni `work_item` örneğinden gelir | A | İzliyor (`aSkelNote`) |
| F11 | Gerçek parametre adları `COM_MODE0_HASH..COM_MODE7_HASH` | A, C | İzliyor (`aHash`) |
| F12 | Tilt limitinin adı `MPC_TILTMAX_AIR` | B | İzliyor (`bLimNote`) |
| F13 | `COM_RCL_EXCEPT` bit 3 kodda doğrulandı (varsayılan 0, `NAV_RCL_ACT` uygulanır). Davranış SITL maddesi | C | İzliyor (`cRclQ`) |
| F14 | Armed iken kayıt reddi yalnızca `COM_MODE_ARM_CHK = 0` (varsayılan) iken olur | A | İzliyor (`aArmedQ`) |
| F15 | `VEHICLE_CMD_SET_NAV_STATE`: hedef filtresi, `source_component < 1000` → User, kaynak yorumu "Used from ROS". FC içi kullanımı doğrulanacak | C | İzliyor (`cSetNav`, `cHoldCmd`) |
| F16 | Pi tarafı `/dev/ttyAMA0`, FC tarafı TELEM2 = `/dev/ttyS3`. `MAV_1_CONFIG` varsayılan olarak kapalı, 102 yapılmalı | B, D | İzliyor (`bPiPort`, `bLinkHw`, `dHwCfg`) |
| F17 | Başlatma sırası uyumlu: `extras.txt` ve `.post` commander ve mavlink'ten sonra çalışır | A | İzliyor |
| F18 | SITL `.post` tek başına yetmez. Noktasız `<id>_gz_x500_tez` airframe dosyası ve `airframes/CMakeLists.txt` kaydı da gerekir | A | İzliyor (`aStartSitl`) |
| F19 | Armed iken `unregister_ext_component` işlenmez. Uçuşta durdurulan modül unresponsive olur ve RTL'e düşülür. Kayıt silinince Hold'a geçiş yalnızca disarm iken olur | A, C, D | İzliyor (`aUnregArmedQ`, `aUnregDefer`, `cUnresp`, S7) |
| F20 | Spec, `unregister_ext_component` alanı olarak yalnızca `arming_check_id` ve `mode_id` sayar. Kaynakta `name` kayıttaki adla birebir eşleşmezse mod silinmez (`ModeManagement.cpp:185-194`). `mode_executor_id` için -1 yazılmalı. `mc_nn_control` bu alanı 0 bırakır, ama 0 otopilot executor'ı olduğu için zararsızdır | A | İzliyor (bu grupta `aUnreg` güncellendi) |
| F21 | `trajectory_setpoint` geçerlilik kuralı: her eksende position, velocity veya acceleration'dan en az biri sonlu olmalı, x/y birlikte. Geçersizse 200 ms son geçerli setpoint, sonra `generateFailsafeSetpoint`. yaw NaN ise mevcut yaw tutulur | B, C | İzliyor (`bTrajNote`, `cSafeInvNote`) |
| F22 | mc_pos_control setpoint için tazelik zaman aşımı uygulamaz. Donan modülün son setpoint'i commander RTL'e geçene kadar (yaklaşık 4 × 300 ms + 50 ms) uygulanır | B, C, D | İzliyor (`bStaleWarn`, `cUnresp`, S7) |
| F23 | `debug_vect` tek instance'tır ve her MAVLink bağlantısından yazılır. Bu yüzden `name` filtresi zorunludur | B, D | İzliyor (`bQueueNote`, S5) |
| F24 | Spec hedef kaybını "TEZ_FOL_TOUT sonra" diye tanımlar. Şemadaki tetik bir yorumdur: "Son geçerli ölçüm (dört adım + u_D) TEZ_FOL_TOUT (öneri) içinde mi?". Bu grupta `u_D` koşulu eklendi | B, C | Yorum, onayınız gerekiyor |
| F25 | Yükseklik EKF orijinine göredir. Orijin her zaman kalkış zemini olmayabilir (spec: "yer düzlemine göre", requirements: "kalkışa göre") | B, C | İzliyor (`bAlt`, (C) metni), TBD 2'ye bağlı |
| F26 | Mod fallback zinciri RTL → Land → Descend → Terminate (hangisi çalışabiliyorsa) | C, D | İzliyor (bu grupta `cRtl`'ye Terminate eklendi) |
| F27 | Fallback, koşul düzelince kalkar (`WhenConditionClears`). Pilot devralmadıysa araç `tez_follow`'a otomatik döner | C, D | İzliyor (`cFsClear`, S7), doğrulanacak |
| F28 | RC mod anahtarı kenar tetiklidir. Hold veya failsafe sonrası moda yeniden girmek için anahtar başka slota alınıp geri getirilir | C, D | İzliyor (`cManCtl`, `cSlotNote`, S3) |
| F29 | Moda girişte red `canRun(mode_id)` ile olur. Yalnızca `can_arm_and_run` değil, mod responsive mi ve `mode_req_*` sağlanıyor mu da bakılır | C | İzliyor (`cCanRunQ`) |
| F30 | Modülün yayınlayacağı topic `config_overrides_request`'tir, `config_overrides` değil. tez_follow ikisini de kullanmaz | C | İzliyor (`cNoDefer`) |
| F31 | `make px4_sitl gz_x500_tez` hedefi oluşur, ama Gazebo modelini kilitli `Tools/simulation/gz/models` altında arar. Çözüm: `PX4_SYS_AUTOSTART=<id> make px4_sitl gz_x500` | D | İzliyor (`dSitl`, `dTarget`), doğrulanacak |
| F32 | ULog sınırları: `trajectory_setpoint` 5 Hz kaydedilir, `arming_check_reply` ve kayıt cevabı hiç kaydedilmez. SITL'de `SDLOG_PROFILE` 131'den 163'e çıkarılmalı | D | İzliyor (`dLog`, `dLogNote`) |
| F33 | Gazebo SITL'de `failure` komutu yalnızca motor arızası uygular. GPS ve RC arızası etkisizdir | D | İzliyor (`dFailNote`) |
| F34 | SITL'de RC anahtarı testi için `COM_RC_IN_MODE = 0`, `RC_MAP_*` ve `RC_CHANNELS_OVERRIDE` gerekir | D | İzliyor (`dRcSim`) |
| F35 | RC kaybı: `COM_RC_LOSS_T` sonra `COM_FAIL_ACT_T` (5 s) Hold, ardından Return. RC dönünce `tez_follow`'a otomatik dönülmez | C, D | İzliyor (S6, bu grupta `cRclAct` de güncellendi) |
| F36 | Parametre dosyası her testten önce ve sonra sıfırlanır. Unresponsive moddan geri dönüş kayıt başına en fazla 3 kez olur | D | İzliyor (`dReset`, `dSession`, bu grupta "kayıt başına" yapıldı) |

## 5. Kalan "(doğrulanacak)" maddeler

Bu adlar kaynakta var. Davranış ise yalnızca SITL'de veya donanımda kanıtlanabilir. Her biri (D)'de bir senaryoya bağlıdır.

| Madde | Şema node'u | Senaryo |
|---|---|---|
| SITL başlatma noktası `<id>_gz_x500_tez.post` ve airframe dosyası | `aStartSitl`, `dSitl`, `dTarget` | S1 |
| Donanım başlatma noktası `/fs/microsd/etc/extras.txt` | `aStartHw`, `dHwCfg` | Adım 5 |
| `nav_and_controllers` kuyruğunun 6C'deki yükü | `aSkel` | Adım 5 |
| Armed iken kayıt silme isteğinin işlenmemesi ve unresponsive yolu | `aUnregDefer`, `cUnresp` | S7 |
| TELEM2 bağlantısı (`MAV_1_CONFIG = 102`, `MAV_1_MODE = 2`) | `bLinkHw`, `dHwCfg` | Adım 5 |
| Hedef NED durumu için yeni uORB mesajı gerekip gerekmediği (`msg/` kilitli) | `bMsgNote` | Kullanıcıya sorulacak |
| QGC 5.1.4'ün mod adını göstermesi ve `MAV_CMD_DO_SET_MODE` göndermesi | `cQgcSel`, `dQgc` | S3 |
| External modda stick hareketinin modu değiştirmemesi | `cNoOv` | S3 |
| Failsafe sırasında `framework.cpp` devralma davranışı | `cOvNote` | S3, S7 |
| Modülden `VEHICLE_CMD_SET_NAV_STATE` (100001, `param1 = 4`) ile Hold | `cHoldCmd`, `dSc4` | S4 |
| RC kaybı: `COM_RCL_EXCEPT` bit 3, `COM_FAIL_ACT_T` beklemesi, `NAV_RCL_ACT` | `cRclAct`, `dSc6` | S6 |
| Fallback kalkınca `tez_follow`'a otomatik dönüş | `cFsClear` | S7 |
| `xy_valid` false iken commander fallback'i | `dSc5` | S5 |
| Mod geçişinde FlightTask ile `tez_follow` setpoint'inin üst üste binmesi | `dSc2` | S2 |
| SITL'de konum kaybının nasıl üretileceği | `dFailNote` | S5 |
| gz saati ile ground truth zaman eşleşmesi | `dTruth` | S2 |
| `logger_topics.txt`'nin profil setinin yerine geçmesi | `dLogNote` | Adım 4 |

## 6. Açık konular (TBD)

Şema 2'de yedi `tbd` node'u vardır. İlk altısı spec'in istediği listedir (tasks.md 7.4). Yedincisi spec (D)'deki "Model konumu TBD" maddesinden gelir.

| # | Konu | Node | Blok |
|---|---|---|---|
| 1 | ICD (Pi → FC hedef LOS mesajı, `DEBUG_VECT` aday) | `bIcd` | B |
| 2 | Yükseklik kaynağı (geçici `-vehicle_local_position.z`) | `bAltTbd` | B |
| 3 | Nihai guidance yasası | `bGuidTbd` | B |
| 4 | Setpoint tipi (`trajectory_setpoint` / `goto_setpoint` + `GotoControl`) | `bSpTbd` | B |
| 5 | Ön koşul onayı (`allowed-paths.txt` + iki `.px4board`, ayrı PR) | `aPre` | A |
| 6 | Süre parametreleri (`TEZ_FOL_TOUT`, `TEZ_FOL_HOLD_T`) | `cTimeTbd` | C |
| 7 | Hareketli insan modeli ve tez dünyasının konumu | `dPerson` | D |

Şema 1'de iki TBD vardır: ICD kutusu ve irtifa girdisi.

## 7. Kararınızı veya onayınızı bekleyen maddeler

1. **Hedef kaybı tetiği (F24, öneri):** "Son geçerli ölçüm (dört adım + `u_D`) `TEZ_FOL_TOUT` içinde mi?". Bu grupta `u_D` geçersiz ölçümlerin sayacı yenilememesi eklendi (bölüm 2, madde 1). Onaylıyor musunuz?
2. **Giriş hazırlığı (Task Group 4, öneri):** (B)'deki "Moda giriş ilk çevrimi mi?" kararı ve `bEntry`. Girişte irtifa saklanır ve ilk `trajectory_setpoint` aynı çevrimde yayınlanır.
3. **Konum geçerliliği önce kontrol edilir (Task Group 4):** `xy_valid`/`z_valid` ve reset sayaçları girdi doğrulamadan önce kontrol ediliyor.
4. **(C)'den `bTraj`'a noktalı bağlantılar (Task Group 4):** Hedef kaybı ve güvenli taraf setpoint'leri, (B)'deki aynı `trajectory_setpoint` çıkışından yayınlanıyor.
5. **Konum geçersizken yayınlanan setpoint ((C), öneri):** Yatay hız 0, `position[0..1]` NaN. Asıl tepkiyi commander'ın fallback'i verir.
6. **Fallback sonrası otomatik dönüş (F27):** Pilot devralmazsa araç RTL'den `tez_follow`'a kendiliğinden dönebilir. PX4 varsayılanıdır. Kabul ediyor musunuz, yoksa sonraki spec'te ek önlem mi istiyorsunuz?
7. **RC kaybı davranışı (F35):** Varsayılanda 5 s Hold sonra Return olur ve RC dönünce takibe dönülmez. `COM_RCL_EXCEPT` bit 3 set edilirse RC kaybı bu modda yok sayılır. Hangisini istiyorsunuz?
8. **Hold isteği reddedilirse (öneri):** Konum tutulur, Hold isteği sınırlı sayıda tekrarlanır (`cRetry`).
9. **Yeni uORB mesajı:** Hedef NED durumunu loglamak için yeni bir mesaj gerekirse `msg/` kilitli. Ne yapılacak?
10. **Yedi TBD:** Özellikle ICD (ekipçe), yükseklik kaynağı, ön koşul PR'ı ve insan modelinin konumu.
11. **Öneri adlar:** `tez_follow`, "Tez Follow" (`COM_MODEx_HASH` yüzünden sabit kalmalı), `TEZ_FOL_*`, `<id>`, ICD adı (ör. "TEZ_LOS", en fazla 9 karakter).

## 8. Not olarak bırakılanlar (düzeltilmedi)

- **Kozmetik:** GitHub'da `linkStyle default` ok rengi farklı görünebilir. (D)'deki senaryo dağılımında S7 sırası yerleşimde kayabilir. (B), (C) ve (D) uzun şemalardır. Mermaid sözdizimi geçerlidir, okunabilirlik için ileride bloklar bölünebilir.
- **Kapsam dışı uyumsuzluk:** `tez/env/VERSIONS.md:28`, pyulog 1.2.4'ün `analiz-requirements.txt` içinde olduğunu söylüyor. Ama bu sürüm `tez/env/requirements-lock.txt:27` içinde sabitlenmiş, `analiz-requirements.txt`'de pyulog yok. (D) notu doğru dosyaya (`requirements-lock.txt:27`) atıf yapar. `VERSIONS.md` değiştirilmedi.
