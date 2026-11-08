# Spec Requirements: FC'ye Özel Akış Şemaları (Vision/Pi Tarafı Çıkarılmış)

## Initial Description

> tamam şimdi iki adet akış şemasını değiştirmeden sadece vision tarafından yazılanları
>   kaldır sadece benim yapacağım bana ne gelip ta pwm e nasıl gidiyor ya benim kısmın yani
>   benim çalışma alanım sadece fc kısmı o yüzden o tarafları kaldırılaım ona göre düzeleme yapalım

(Kaynak: `planning/raw-idea.md`, 2026-10-18.)

Bağlam: Bu spec, önceki spec'in (`agent-os/specs/2026-10-15-m15-target-follow-flight-mode/`) ürettiği iki Mermaid akış şemasından türer: `diagrams/01-ust-seviye-akis.md` (Şema 1, üst seviye) ve `diagrams/02-px4-detayli-akis.md` (Şema 2, PX4 v1.17.0 detaylı, A–D blokları). Kullanıcının çalışma alanı yalnızca uçuş kontrolcüsüdür (FC). Vision / Raspberry Pi tarafı şemalardan çıkarılacak. Şemalar FC'ye gelen girdiyle başlayıp PWM çıkışına kadar gidecek.

## Requirements Discussion

### First Round Questions

**Q1:** Konum: Yeni şemalar bu spec'e yazılır: `diagrams/01-ust-seviye-akis-fc.md` ve `02-px4-detayli-akis-fc.md`. Eski spec'teki şemalara dokunulmaz. Doğru mu?
**Answer:** Eskileri kalmasın onları güncelle
**Yorum (orkestratör):** Ayrı `-fc` kopyası oluşturulmaz. Teslimat, önceki spec'teki iki şema dosyasının yerinde güncellenmesidir: `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/diagrams/01-ust-seviye-akis.md` ve `.../diagrams/02-px4-detayli-akis.md`. Kullanıcı yalnızca bu iki dosyanın değiştirilmesine izin verdi. Önceki spec klasörünün geri kalanı (`spec.md`, `tasks.md`, `planning/`, `implementation/` raporları, `orchestration.yml`) değişmez. Bu yeni spec klasörü, değişikliğin planlamasını, `spec.md` ve `tasks.md` dosyalarını tutar.

**Q2:** Giriş noktası: Pi kutusu (kamera, tespit, piksel → kamera → body LOS) ve Pi'den çıkan oklar tamamen kalkar. Şemanın başında tek bir girdi kutusu olur: "Body FRD LOS (montaj açısı dahil, birim vektör), MAVLink ile TELEM2'den gelir (ICD TBD)". Şema 2'de FC'nin mesajı alan tarafı aynen kalır: TELEM2 `/dev/ttyS3`, `MAV_1_CONFIG=102`, SITL UDP 14580, `handle_message_debug_vect` → `debug_vect`, ICD TBD kutusu ve iki notu. Pi'nin gönderen tarafı silinir: `/dev/ttyAMA0`, pymavlink ile gönderme, `udp:127.0.0.1:14540`. FC'nin beklediği alanlar giriş kutusuna taşınır: `name` en fazla 9 karakter, x/y/z = LOS_body, "FC montaj açısını bilmez". Doğru mu?
**Answer:** tamam
**Yorum (orkestratör):** Giriş noktası onaylandı. FC'nin alış tarafı kalır, Pi'nin gönderen tarafı silinir.

**Q3:** PWM'e kadar uzatma: Zincir `actuator_motors`'tan sonra şöyle uzatılır: mixer_module (FunctionMotors) → çıkış sınırlama (`PWM_MAIN_MIN/MAX/DIS/FAIL`, 1000–2000 µs) → px4io (IO işlemcisi) → MAIN 1–4'te PWM 400 Hz (`PWM_MAIN_TIMx`) → ESC → motorlar. Yanına `actuator_outputs` topic'i eklenir. Motor ataması `PWM_MAIN_FUNC1..4 = 101..104` (Motor 1..4). 4019 airframe bunu ayarlamıyor, QGC Actuators'da elle yapılıyor. ESC'ler MAIN çıkışlarına PWM ile mi bağlı, yoksa AUX çıkışlarına DShot ile mi? Bilinmiyorsa iki dal da "TBD" olarak gösterilsin mi? SITL dalı (`gz_bridge`, `SIM_GZ_EC_FUNCx`) kalsın mı?
**Answer:** maın portuna bağlı
**Yorum (orkestratör):** ESC'ler MAIN portunda, PWM ile bağlı. Yalnızca MAIN dalı çizilir, AUX/DShot dalı çizilmez. Zincir: `actuator_motors` → mixer_module FunctionMotors → çıkış sınırları (`PWM_MAIN_MIN/MAX/DIS/FAIL`) → px4io (IO işlemcisi, `/dev/ttyS4`) → MAIN 1–4 PWM 400 Hz (`PWM_MAIN_TIMx`) → ESC → motorlar. Yanında `actuator_outputs` ve `PWM_MAIN_FUNC1..4 = 101..104` (QGC Actuators'da ayarlanır) gösterilir. SITL sorusu cevaplanmadı. (D) doğrulaması Gazebo SITL kullandığı için SITL çıkış yolu (`gz_bridge`, `SIM_GZ_EC_FUNCx`, PWM değil motor hızı) tam bir dal olarak değil, kısa bir yan not olarak kalır. "V6C10/V6C11 sürümlerinde IO yok" maddesi "(doğrulanacak)" notu olarak kalır.

**Q4:** Şema 1: Pi kutusu kalkınca yalnızca FC kutusu kalır, aynı sade üslup sürer. "PX4 kontrolcüleri"nden sonra iki kutu eklenir: "Motor karıştırma (control allocation)" ve "PWM → ESC → motorlar". Parametre adları yalnızca Şema 2'de olur. Doğru mu?
**Answer:** doğru ancak şema 1 i biraz daha detaylandır basit olsun dedim ama buda çok basit oldu bunu zayen bende yapardım biraz daha detaylındıt (çok teknik detaya terimlere girme ama bu kadarda çok az detaylı olmasın)
**Yorum (orkestratör):** Şema 1 yalnızca FC'yi gösterir ve referans görselin üslubunu korur. Ancak mevcut sürümden belirgin biçimde daha detaylı olur, çünkü kullanıcı mevcut sürümü fazla basit buldu. Sade dille anlamlı ara adımlar ve karar noktaları eklenir:
- mesaj kontrolü / doğrulama
- mod aktif mi kontrolü
- hedef kaybı kontrolü → yerinde bekleme / Hold
- guidance'ın parçaları: istenen konum / takip mesafesi, istenen hız, yaw hedefe bakar, sınırlar
- konum → tutum → açısal hız kontrolü
- motor karıştırma
- PWM → ESC → motorlar
- pilot / QGC ile moda giriş ve çıkış

Ağır teknik terim, PX4 topic adı ve parametre adı kullanılmaz. Orta yol: daha çok adım ve karar noktası, sade ifade. Topic ve parametre adları yalnızca Şema 2'de olur.

**Q5:** (D) doğrulama, Adım 3 "Sahte Pi": Bu adım FC'yi test etmek için kullanıcının yazacağı bir araç. Kaldırmak yerine adı "SITL LOS test vericisi (pymavlink)" yapılsın, Pi/Vision'a ait ifadeler silinsin ("Pi 5 /dev/ttyAMA0 ↔ TELEM2", "Vision kodu ICD'ye göre", donanım listesindeki "Raspberry Pi 5"). Yoksa tamamen mi kalksın?
**Answer:** şöyle benim daha o konuda kararım yok o yüzden sil sonrasında belki ekleriz
**Yorum (orkestratör):**
- **Adım 3 tamamen silinir:** "Adım 3 sahte Pi (pymavlink)" adımı, subgraph'ı (`dStep3`) ve başlığı, `dFakePi`, `dTruth`, `dPiQ`, `dPiFix` node'ları. Kullanıcının bu konuda kararı yok, ileride eklenebilir.
- **Kalan adımlar yeniden numaralanır.** Bu adıma bağlı her geri dönüş oku ve kapı düzeltilir.
- **Senaryolar nötr yazılır:** `dSc4` "sahte Pi göndermeyi keser" ve `dSc5` "ikinci gönderici" ifadeleri Pi ya da test aracı adı geçmeden yeniden yazılır (ör. "LOS mesajı kesilir", "ikinci kaynaktan DEBUG_VECT").
- **Yeni açık konu (TBD):** LOS girdisinin SITL'de nasıl üretileceği.
- **Diğer Pi/Vision ifadeleri silinir:** `dHwCfg`, `dFlight`, senaryo tablosu ve notlardaki Pi/Vision ifadeleri (pymavlink sürümü vb.).
- **Kalanlar:** `dRcSim`, `dQgc`, `dFailNote` ve `dUnitFn` içindeki "ICD doğrulama".

**Q6:** Geri kalan her şey değişmeden kopyalanır: (A) ve (C) blokları, TBD'ler, notlar, kaynak satırları, renkler ve şekiller. Yalnızca Pi'ye atıf yapan cümleler düzeltilir: "Pi'den gelen", lejanttaki "Pi (Vision)" katmanı, Şema 1 eşleme tablosundaki Pi satırları. TBD #1 (ICD), "FC'nin beklediği mesaj" diye yeniden yazılarak kalır. Kapsam dışı: Vision tarafının tamamı, kod yazımı ve önceki spec'te değişiklik. Başka çıkarılacak veya eklenecek bir şey var mı?
**Answer:** yok bu madde okey
**Yorum (orkestratör):** (A), (C), TBD'ler, notlar, kaynak satırları, renkler ve şekiller değişmez. Yalnızca Pi'ye atıf yapan cümleler düzeltilir: lejanttaki "Pi (Vision)" katman satırı, Şema 1 eşleme tablosundaki Pi satırları ve "Pi'den gelen" ifadesi. TBD #1 (ICD) "FC'nin beklediği mesaj" olarak yeniden yazılır. Eklenecek bir şey yok. Not: "önceki spec'te değişiklik yok" maddesi Q1 cevabıyla daralır. Yalnızca iki şema dosyası değişir.

**Q7:** Çıktı: Önceki gibi .md ve PDF'ler masaüstüne kopyalansın mı? Ayrı bir alt klasöre mi (`/home/yusuf/Desktop/hedef-takip-ciktilari/fc/`), yoksa aynı klasöre `-fc` ekiyle mi?
**Answer:** kopyalansın ancak masaüstündeki şemaları güncelle direkt eskisi kalmasın
**Yorum (orkestratör):** `/home/yusuf/Desktop/hedef-takip-ciktilari/` içindeki mevcut dosyaların üzerine güncel sürümler yazılır: `01-ust-seviye-akis.md`/`.pdf` ve `02-px4-detayli-akis.md`/`.pdf`. Eski sürüm tutulmaz, `-fc` kopyası oluşturulmaz. PDF dönüşümünü, uygulamadan sonra orkestratör yapar.

**Mevcut kod / görsel sorusu:** Önceki iki şemanın yanında örnek alınacak başka bir şema, doküman veya kod var mı? Çizim, taslak veya ekran görüntüsü var mı?
**Answer:** Ayrıca belirtilmedi. Referans yalnızca önceki iki şema ve önceki spec'teki referans görseldir.

### Existing Code to Reference

**Similar Features Identified:**
- Feature: Şema 1 (güncellenecek dosya) - Path: `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/diagrams/01-ust-seviye-akis.md`
- Feature: Şema 2, A–D blokları (güncellenecek dosya) - Path: `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/diagrams/02-px4-detayli-akis.md`
- Feature: Şema 1 üslup rehberi (referans görsel) - Path: `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/planning/visuals/WhatsApp Image 2026-09-26 at 00.07.13.jpeg` (masaüstü kopyası: `/home/yusuf/Desktop/hedef-takip-ciktilari/referans-gorsel.jpeg`)
- Feature: Önceki spec'in yazım kuralları ve kontrolleri - Path: `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/tasks.md` (genel kurallar: tırnaklı etiketler, ASCII id, `#quot;`/`#60;`/`#62;`, `classDef` paleti, "(doğrulanacak)" / "(öneri)" / TBD etiketleri), `implementation/7-son-gozden-gecirme.md` (K7-1..K7-10 kontrolleri, TBD tablosu ↔ `tbd` node eşlemesi)
- Components to potentially reuse: Şema 2'deki `classDef` paleti (`input`, `process`, `decision`, `tbd`, `note`, `warn`, `ref`), `linkStyle default`, lejant tabloları, blok başına "notlar ve kaynak satırları" listeleri.
- Backend logic to reference (PWM zinciri, PX4 v1.17.0 kaynağı):
  - `src/lib/mixer_module/mixer_module.cpp:440-575` (`update`, `limitAndUpdateOutputs`, `output_limit_calc_single`), `:666-675` (`actuator_outputs` yayını), `:117-131` (`<prefix>_FUNCn/DISn/MINn/CENTn/MAXn/FAILn`, `<prefix>_REV`)
  - `src/lib/mixer_module/functions/FunctionMotors.hpp:52-118` (`actuator_motors` aboneliği, `THR_MDL_FAC`, [0,1] → [-1,1] dönüşümü)
  - `src/lib/mixer_module/output_functions.yaml` (Motor1..12 = 101..112), `src/lib/mixer_module/motor_params.c:57` (`THR_MDL_FAC` varsayılanı 0)
  - `src/drivers/px4io/px4io.cpp:363-378` (`updateOutputs` → `PX4IO_PAGE_DIRECT_PWM`), `src/drivers/px4io/module.yaml` (`PWM_MAIN` öneki, protokol: PWM 50/100/200/400 Hz veya OneShot, DShot yok, varsayılan 400)
  - `boards/px4/fmu-v6c/src/board_config.h:59-72` (PX4IO seri hattı `/dev/ttyS4`, 1.5 Mbps), `:149-150` (V6C10/V6C11 "NO PX4IO")
  - `boards/px4/fmu-v6c/default.px4board:32` (`CONFIG_DRIVERS_PX4IO=y`), `Kconfig:81-84` (`CONFIG_BOARD_IO` = `px4_io-v2_default`), `src/lib/parameters/CMakeLists.txt:91-93` ve `Tools/module_config/generate_params.py:53-67` (IO'lu kartta FMU çıkışları `PWM_AUX` öneki alır)
  - `ROMFS/px4fmu_common/init.d/rcS:414` (`px4io start`), `:478-479` (`dshot start`, `pwm_out start`)
  - `ROMFS/px4fmu_common/init.d/airframes/4019_x500_v2` (yalnızca CA_ROTOR ve rate PID ayarları, `PWM_*_FUNCn` ayarı yok)
  - `build/px4_fmu-v6c_default/parameters.xml:2166` (`PWM_MAIN_FUNC1` varsayılanı 0), `:2783-2809` (`PWM_MAIN_TIM0..2` varsayılanı 400), `:2054` (`PWM_MAIN_DIS1` = 1000), `:2718` (`PWM_MAIN_MIN1` = 1000), `:2670` (`PWM_MAIN_MAX1` = 2000), `:2110` (`PWM_MAIN_FAIL1` = -1)
  - SITL yan notu: `ROMFS/px4fmu_common/init.d-posix/airframes/4001_gz_x500:35-48` (`SIM_GZ_EC_FUNC1..4 = 101..104`, MIN 150, MAX 1000), `src/modules/simulation/gz_bridge/module.yaml` (`SIM_GZ_EC` öneki)

### Follow-up Questions

Takip sorusu sorulmadı (orkestratör talimatı).

## Visual Assets

### Files Provided:
Bu spec'in `planning/visuals/` klasöründe dosya bulunmadı (bash kontrolü: "No visual files found").

### Visual Insights:
- Bu spec için yeni görsel verilmedi.
- Şema 1'in üslup rehberi önceki spec'teki referans görseldir. O görsel düşük ayrıntılı bir üslup örneğidir ve birebir kopyalanmaz, yalnızca şekil dili alınır (paralelkenar = girdi, kutu = işlem).
- Fidelity level: düşük ayrıntılı üslup referansı (önceki spec'ten).

## Requirements Summary

### Functional Requirements

**Genel**
- İki şema dosyası yerinde güncellenir. Yeni şema dosyası oluşturulmaz:
  - `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/diagrams/01-ust-seviye-akis.md`
  - `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/diagrams/02-px4-detayli-akis.md`
- Şemalar yalnızca FC'yi gösterir. Akış, FC'ye MAVLink ile gelen body FRD LOS mesajıyla başlar ve MAIN çıkışından ESC'ye giden PWM sinyaliyle biter.
- Vision / Raspberry Pi tarafına ait her node, subgraph, ok, not, tablo satırı ve cümle kaldırılır.
- Metinler Türkçe, teknik terimler İngilizce yazılır. Mermaid yazım kuralları önceki spec'tekiyle aynıdır.

**Şema 1 (üst seviye, FC'ye özel, daha detaylı)**
- Kaldırılanlar:
  - `piBox` subgraph'ı (`piImg`, `piDetect`, `piCamLos`, `piBodyLos`) ve bunlara ait oklar ve sınıf referansları.
  - Giriş paragrafındaki "Raspberry Pi kamera görüntüsünde..." anlatımı. Paragraf FC'nin bakış açısından yeniden yazılır.
- `icdMsg` bir girdi paralelkenarına dönüşür: "Body FRD LOS (montaj açısı dahil), MAVLink ile gelir (ICD TBD)" (kesik çizgili TBD vurgusu korunabilir).
- Referans görselin üslubu korunur: paralelkenar = girdi, yuvarlak köşeli kutu = işlem, kesik çizgi = TBD. Siyah-beyaz kutular ve mavi oklar aynı kalır.
- Mevcut sürümden belirgin biçimde daha detaylı olur. Sade dille ara adımlar ve karar noktaları eklenir:
  - pilot / QGC ile moda giriş ve çıkış
  - mod aktif mi kontrolü
  - gelen mesajın kontrolü / doğrulaması
  - hedef kaybı kontrolü → yerinde bekleme, süre dolunca Hold
  - LOS → NED çevirme, aşağı açı ve eğik mesafe, hedefin yerel NED konumu, hedef kestirimi
  - guidance'ın parçaları: istenen konum / takip mesafesi, istenen hız, yaw hedefe bakar, sınırlar
  - konum kontrolü → tutum kontrolü → açısal hız kontrolü
  - motor karıştırma
  - PWM → ESC → motorlar
- Karar noktaları eşkenar dörtgenle gösterilebilir. Lejant bu şekli de içerecek biçimde güncellenir.
- PX4 topic adı, parametre adı ve ağır teknik terim kullanılmaz. Bu ayrıntılar yalnızca Şema 2'dedir.
- Yan girdiler (tutum, irtifa (TBD), yerel konum) korunur.

**Şema 2, Lejant ve TBD tablosu**
- Lejant katman tablosundaki "Pi (Vision) | Raspberry Pi (Vision) | B" satırı kaldırılır.
- TBD #1 (ICD) kalır, ama "FC'nin beklediği hedef LOS mesajı" olarak yeniden yazılır.
- Yeni açık konu eklenir: "SITL'de LOS girdisinin nasıl üretileceği" (sahte Pi adımı silindiği için).
- Önceki spec'teki TBD tablosu ↔ `tbd` node eşleme kuralı korunur. Uygulamada, tablodaki her TBD satırının bir `tbd` node'una karşılık geldiği kontrol edilir.

**Şema 2, (A) bloğu**
- Değişmez.

**Şema 2, (B) bloğu**
- Giriş metnindeki "Pi'den gelen LOS örneği" ifadesi FC'nin bakış açısından yeniden yazılır.
- "Pi ve FC portları karıştırılmaz: Pi tarafı `/dev/ttyAMA0`..." maddesi kaldırılır ya da yalnızca FC portunu (TELEM2 = `/dev/ttyS3`) anlatacak biçimde yeniden yazılır.
- Şema 1 eşleme tablosu güncellenir:
  - Pi satırları (`bPiLos`, `bPiSend`) kaldırılır.
  - Yeni giriş kutusu ve yeni Şema 1 kutuları (doğrulama, mod kapısı, motor karıştırma, PWM vb.) (B) node'larına eşlenir.
- `bPi` subgraph'ı (`bPiLos`, `bPiSend`, `bPiPort`) ve okları (`bPiLos→bPiSend→bPiPort`, `bPiSend-.-bIcd`, `bPiPort→bLinkHw/bLinkSitl`) kaldırılır.
- Yeni giriş paralelkenarı eklenir: "Body FRD LOS (montaj açısı dahil), MAVLink ile TELEM2'den gelir (ICD TBD)". FC'nin beklediği alanlar burada yazar: `DEBUG_VECT` aday, `name` en fazla 9 karakter, x/y/z = LOS_body birim vektör, FC montaj açısını bilmez, `time_usec` FC'de kullanılmaz.
- Giriş kutusu `bLinkHw` (donanım, TELEM2) ve `bLinkSitl` (SITL, UDP local 14580) node'larına bağlanır.
- `bLink` subgraph'ı aynen kalır: `bLinkHw`, `bLinkSitl`, `bRecv`, `bIcd`, `bTsNote`, `bQueueNote`. İçlerindeki Pi'ye atıf yapan ifadeler nötr yazılır.
- (B) notlarındaki "Pi tarafı `/dev/ttyAMA0` ve `udp:127.0.0.1:14540`: `agent-os/standards/python/companion.md:8`" kısmı kaldırılır.
- Kontrolcü zinciri PWM'e kadar uzatılır. Mevcut `bEsc` node'u ("Çıkış sürücüsü... → ESC / motorlar") ayrıntılı zincirle değiştirilir:
  - `control_allocator` → `actuator_motors` → mixer_module `MixingOutput`: FunctionMotors (`THR_MDL_FAC`, varsayılan 0, [0,1] → [-1,1]) → armed değilse disarmed değeri → `output_limit`: `PWM_MAIN_MIN`..`PWM_MAIN_MAX` (1000–2000 µs) arası, kill/lockdown → `PWM_MAIN_DIS` (1000), termination → `PWM_MAIN_FAIL`.
  - px4io sürücüsü → seri hat `/dev/ttyS4` (1.5 Mbps, `PX4IO_PAGE_DIRECT_PWM`) → IO işlemcisi → MAIN 1–4 PWM 400 Hz (`PWM_MAIN_TIMx`) → ESC → motorlar (araç hedefi takip eder).
  - Yan çıkış olarak `actuator_outputs` topic'i gösterilir (ULog).
  - Motor ataması notu: `PWM_MAIN_FUNC1..4 = 101..104` (Motor 1..4). Varsayılan 0 (Disabled), 4019_x500_v2 airframe ayarlamaz, QGC Actuators sekmesinde elle yapılır.
  - Yalnızca MAIN dalı çizilir. AUX / `pwm_out` / `dshot` dalı çizilmez.
  - SITL yolu yalnızca kısa bir yan nottur: `gz_bridge` aynı `MixingOutput`'u kullanır, `SIM_GZ_EC_FUNC1..4 = 101..104`, MIN 150 / MAX 1000, PWM değil motor hızı.
  - "(doğrulanacak)" notu: V6C10/V6C11 donanım sürümlerinde PX4IO yoktur. Kullanıcının kartında IO olduğu varsayılır.
- (B) notları ve kaynak satırları listesine PWM zincirinin kaynak satırları eklenir (bkz. "Existing Code to Reference").

**Şema 2, (C) bloğu**
- Değişmez.

**Şema 2, (D) bloğu**
- "Adım 3: Sahte Pi (pymavlink)" adımı tamamen silinir: `dStep3` subgraph'ı ve başlığı, `dFakePi`, `dTruth`, `dPiQ`, `dPiFix`, ilgili oklar (`dBootQ → dFakePi`, `dTruth -.-> dFakePi`, `dFakePi → dPiQ`, `dPiQ → dPiFix/dPick`, `dPiFix → dFakePi`).
- `dRcSim`, `dQgc` ve `dFailNote` kalır. Silinen subgraph'ın dışına (ör. senaryo / SITL bölümüne) taşınırlar. `dRcSim → dPick` ve `dQgc → dPick` okları korunur.
- `dBootQ` "evet" kenarı doğrudan senaryo seçimine (`dPick`) bağlanır.
- Adımlar yeniden numaralanır: Adım 1 GoogleTest → Adım 2 Gazebo Harmonic SITL → Adım 3 ULog + pyulog metrikleri (eski Adım 4) → Adım 4 gerçek uçuş (eski Adım 5). Numara geçen her yer güncellenir:
  - giriş metnindeki "Sıra" maddesi
  - senaryo subgraph başlığı ("Adım 2–4" → "Adım 2–3")
  - `dStep4` / `dStep5` başlıkları
  - `dMetrics`, `dFlight` etiketleri
  - senaryo tablosundaki "Adım 5" satırı
  - "(doğrulanacak)" listesinde geçen adım numaraları
- Silinen adıma bağlı her geri dönüş oku ve kapı düzeltilir. Kapsamı oluşan boşluk, yeni TBD ("SITL'de LOS girdisinin nasıl üretileceği") ile işaretlenir.
- Senaryolar Pi ya da test aracı adı geçmeden yeniden yazılır:
  - `dSc4`: "sahte Pi göndermeyi keser" → ör. "LOS mesajı kesilir"
  - `dSc5`: "yanlış name'li DEBUG_VECT (ikinci gönderici)" → ör. "ikinci kaynaktan yanlış name'li DEBUG_VECT"
- Pi/Vision ifadeleri kaldırılır:
  - `dHwCfg`: "Pi 5 /dev/ttyAMA0 ↔ TELEM2, Vision kodu ICD'ye göre (ICD TBD)"
  - `dFlight`: "+ Raspberry Pi 5"
  - senaryo tablosunda "Pi bağlantısı"
  - (D) notlarında "Sahte Pi ve pilot simülasyonu" maddesi (yalnızca pilot simülasyonu kısmı kalır) ve sahte Pi'ye ait pymavlink ifadeleri
- `dUnitFn` içindeki "ICD doğrulama" kalır (FC tarafı girdi doğrulaması).

**Masaüstü çıktıları**
- `/home/yusuf/Desktop/hedef-takip-ciktilari/01-ust-seviye-akis.md` ve `02-px4-detayli-akis.md` güncel sürümlerle değiştirilir. `.pdf` dosyaları yeniden üretilip üzerine yazılır. Eski sürüm tutulmaz, `-fc` kopyası yoktur.
- PDF dönüşümünü uygulamadan sonra orkestratör yapar.
- Masaüstündeki diğer dosyalar (`1-ad-envanteri.*`, `7-son-gozden-gecirme.*`, `referans-gorsel.jpeg`) bu spec'in kapsamında değildir.

### Reusability Opportunities
- Önceki spec'teki Mermaid yazım kuralları, `classDef` paleti ve lejant tabloları aynen kullanılır.
- Önceki spec'in doğrulama yaklaşımı (grep ile ad kontrolü, node/kenar sayımı, MPE Mermaid parse + headless Chrome render, TBD tablosu ↔ `tbd` node eşlemesi) bu değişiklik için de kullanılabilir.
- Önceki PDF dönüşüm yöntemi masaüstü çıktıları için tekrar kullanılır (orkestratör).

### Scope Boundaries
**In Scope:**
- İki şema dosyasının yerinde güncellenmesi:
  - Vision/Pi içeriğinin kaldırılması
  - FC giriş kutusunun eklenmesi
  - (B) zincirinin MAIN PWM'e kadar uzatılması
  - Şema 1'in sade dille daha detaylı hale getirilmesi
  - (D)'deki sahte Pi adımının silinip adımların yeniden numaralanması
  - Pi'ye atıf yapan cümlelerin düzeltilmesi
  - yeni SITL LOS girdisi TBD'si
- Bu spec klasöründe planlama, `spec.md` ve `tasks.md`.
- Masaüstündeki `01-ust-seviye-akis` ve `02-px4-detayli-akis` .md/.pdf dosyalarının üzerine yazılması.

**Out of Scope:**
- Vision / Raspberry Pi tarafının tamamı: kamera, insan tespiti, piksel → kamera → body LOS, Pi'de gönderim, Pi seri portu, pymavlink ile gönderim.
- Önceki spec'te iki şema dışındaki her dosya (`spec.md`, `tasks.md`, `planning/`, `implementation/`, `orchestration.yml`).
- AUX / DShot çıkış dalı.
- SITL çıkış yolunun tam dal olarak çizilmesi (yalnızca yan not olarak kalır).
- (A) ve (C) bloklarında Pi'ye atıf dışındaki değişiklikler. Mevcut TBD'lerin, notların, kaynak satırlarının, renk ve şekillerin değiştirilmesi.
- `tez_follow` kodu, `module.yaml`, testler (sonraki spec).
- SITL LOS test vericisi (sahte Pi). Kullanıcının kararı yok, ileride eklenebilir.
- Branch değişikliği, commit, yeni spec klasörü ve iki şema dosyası dışında repo değişikliği, Vision reposunda değişiklik.

### Technical Considerations
- Branch `yusuf/agent-os-denemeleri-ve-sema-olusturma` olarak kalır, commit atılmaz.
- Repoda yalnızca bu spec klasörü ve iki şema dosyası değişir. Masaüstü dosyaları repo dışındadır ve kullanıcı izniyle güncellenir. Vision reposu salt okunurdur.
- Önceki spec'in `spec.md`, `tasks.md` ve `implementation/7-son-gozden-gecirme.md` dosyaları Pi bloklarını ve 5 adımlı (D) akışını anlatmaya devam eder. Bu dosyalar kullanıcı kararıyla değişmez, bu yüzden şemalarla aralarında bilinçli bir tutarsızlık oluşur. Şema dosyalarının başında bu spec'e (`agent-os/specs/2026-10-18-m15-fc-only-flow-diagrams/`) atıf verilebilir.
- Şema 1 referans görsel bağlantısı (`../planning/visuals/WhatsApp Image 2026-09-26 at 00.07.13.jpeg`) dosya yerinde kaldığı için geçerli kalır.
- PX4 v1.17.0 kaynağına göre doğrulananlar:
  - Pixhawk 6C build'inde PX4IO var. MAIN 1–8 px4io'dan (`PWM_MAIN_*`, DShot yok), AUX 1–8 FMU `pwm_out`/`dshot`'tan (`PWM_AUX_*`) gelir.
  - ESC'ler MAIN'de olduğu için ilgili parametreler `PWM_MAIN_FUNCn`, `PWM_MAIN_MINn/MAXn/DISn/FAILn`, `PWM_MAIN_TIM0..2` ve `PWM_MAIN_REV`'dir.
  - `actuator_outputs` mixer_module tarafından sürücü `updateOutputs` çağrısından sonra yayınlanır.
- Kaynakta doğrulanamayan veya donanıma bağlı maddeler "(doğrulanacak)" etiketi alır: IO'suz 6C sürümleri, MAIN 1–4 ↔ motor sırası, QGC Actuators ataması.
- (D)'de `dRcSim` pilot simülasyonu için pymavlink `RC_CHANNELS_OVERRIDE` kullanmaya devam eder. Bu Pi'ye ait değildir. (D) notlarındaki pymavlink sürüm satırı yalnızca bu kullanım için gerekiyorsa korunabilir. Uygulamada sahte Pi'ye ait pymavlink ifadeleri silinir, pilot simülasyonuna ait olanlar kalır.
- Şema 1 ile Şema 2 (B) arasındaki terim tutarlılığı (önceki K7-1 kontrolü) yeni Şema 1 kutuları için de korunur. (B)'deki eşleme tablosu buna göre güncellenir.
