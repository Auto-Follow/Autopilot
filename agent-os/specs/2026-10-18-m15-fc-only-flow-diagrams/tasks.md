# Task Breakdown: FC'ye Özel Akış Şemaları (Vision/Pi Tarafı Çıkarılmış)

## Overview
Total Tasks: 53 alt görev, 7 task group

Bu spec'in teslimatı, önceki spec'teki **iki Mermaid şema dosyasının yerinde güncellenmesidir** (kod yok, yeni şema dosyası yok, `-fc` kopyası yok):
- `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/diagrams/01-ust-seviye-akis.md` (Şema 1)
- `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/diagrams/02-px4-detayli-akis.md` (Şema 2, A–D blokları)

Akış, FC'ye MAVLink ile gelen body FRD LOS mesajıyla başlar ve MAIN çıkışından ESC'ye giden PWM sinyaliyle biter. Vision / Raspberry Pi tarafı şemalardan çıkarılır.

Bu spec'te "test", kod testi değildir. Her task group başında şemaya yönelik 2–8 **doğrulama kontrolü** tanımlanır ve grubun sonunda yalnızca o kontroller çalıştırılır. Kontroller grep, node/kenar sayımı, baseline ile blok karşılaştırması ve Mermaid parse/render kontrolüdür.

**Genel kurallar (tüm gruplar için geçerli):**
- Repoda yalnızca iki şema dosyası ve bu spec klasörü (`agent-os/specs/2026-10-18-m15-fc-only-flow-diagrams/`) değişir. Önceki spec'in `spec.md`, `tasks.md`, `planning/`, `implementation/` ve `orchestration.yml` dosyalarına **dokunulmaz**. Bu dosyalar Pi bloklarını ve 5 adımlı (D) akışını anlatmaya devam eder, bu tutarsızlık bilinçlidir.
- Upstream PX4 dosyaları, `build/` ve Vision reposu salt okunurdur. Branch `yusuf/agent-os-denemeleri-ve-sema-olusturma` kalır, branch değiştirilmez, commit atılmaz.
- Metinler Türkçe, teknik terimler İngilizce yazılır.
- Önceki spec'in Mermaid kuralları aynen geçerlidir (`2026-10-15-m15-target-follow-flight-mode/tasks.md` "Genel kurallar"):
  - Özel karakterli her etiket `"..."` ile tırnaklanır. Etiket içinde `"` için `#quot;`, `<` / `>` için `#60;` / `#62;` kullanılır.
  - Node id'leri ASCII, benzersizdir ve Şema 2'de blok harfiyle başlar (`b...`, `d...`). `end` gibi Mermaid anahtar kelimeleri id olarak kullanılmaz.
  - Her Şema 2 bloğu kendi `classDef` paletini içerir (`input`, `process`, `decision`, `tbd`, `note`, `warn`, `ref`) ve `linkStyle default` kullanır. İndeksli `linkStyle` eklenmez.
  - Kaynakta doğrulanamayan veya donanıma bağlı maddeler "(doğrulanacak)", projeye özel adlar "(öneri)", açık konular `tbd` sınıflı "TBD" node'larıyla gösterilir.
- (A) ve (C) blokları, mevcut TBD'ler, notlar, kaynak satırları, renkler ve şekiller değişmez. Yalnızca Pi'ye atıf yapan ifadeler düzeltilir ve spec'te listelenen eklemeler yapılır.
- Önceki spec klasörü git'te izlenmediği için (`?? agent-os/specs/`) `git diff` baseline vermez. Karşılaştırmalar Task Group 1'de alınan scratch kopyalarına göre yapılır.
- Çalışma notları ve geçici dosyalar scratch alanında tutulur. Spec klasörüne `tasks.md` ve gerekirse `implementation/` raporları dışında dosya eklenmez.

**Doğrulama araçları (kurulum yok, hepsi bu makinede mevcut):**

`S=/tmp/claude-1000/-home-yusuf-Desktop-Projects-Auto-Follow-Autopilot/4b91b3e4-86c9-4515-ad60-66129800d8c8/scratchpad`

- **Yapısal denetim:** `python3 -I $S/mmd_check.py <dosya.md> [blok_indeksi]`. Şema 1'de denetleyicinin bilmediği geçerli sözdizimi (`direction TB`, `style`, subgraph'a giden kenar) yanlış pozitif verir. Önceki spec'te de böyleydi, bunlar MPE parse sonucuyla teyit edilir.
- **MPE Mermaid parse (node/kenar/subgraph dökümü):** `ELECTRON_RUN_AS_NODE=1 /usr/share/code/code $S/mmd/inspect.js ~/.vscode/extensions/shd101wyy.markdown-preview-enhanced-0.8.40/crossnote/dependencies/mermaid/mermaid.min.js <dosya.md>`. Her blok için `PARSE OK`, node sayısı, node şekli/sınıfı, subgraph üyeleri ve kenarlar listelenir. Çıkış kodu 0 olmalıdır.
- **Headless Chrome render:** `python3 -I $S/gen_render.py <dosya.md> $S/render.html $S/<çıktı>.html [blok_indeksi]` ile render sayfası üretilir, ardından önceki spec'teki yöntemle `google-chrome --headless` (`--allow-file-access-from-files`, `--user-data-dir=$S/chrome-profile`, `--dump-dom file://$S/<çıktı>.html`) çalıştırılır. Her blok için `OK` ve `syntax-error-markers=0` beklenir.

## Task List

### Hazırlık ve Kaynak Doğrulama

#### Task Group 1: Baseline Kopyaları ve PWM Zinciri Kaynak Doğrulaması
**Dependencies:** None

- [x] 1.0 Değişiklik öncesi baseline'ı al ve (B) PWM zincirinde geçecek her adı v1.17.0 kaynağına karşı doğrula
  - [x] 1.1 2–6 doğrulama kontrolü tanımla
    - K1: `$S/baseline-fc/` altında iki şema dosyasının değişiklik öncesi kopyası var ve repo dosyalarıyla birebir aynı (`cmp`).
    - K2: Spec'teki "Yeni not maddesinin kaynak satırları" listesindeki her dosya yolu repoda mevcut (`build/px4_fmu-v6c_default/parameters.xml` dahil).
    - K3: Listelenen her satır aralığı spec'te yazan içeriği gösteriyor (grep / `sed -n` ile):
      - `mixer_module.cpp`: `update` / `limitAndUpdateOutputs` / `output_limit_calc_single`, `actuator_outputs` yayını, `<prefix>_FUNCn/DISn/MINn/MAXn/FAILn`
      - `FunctionMotors.hpp`: `actuator_motors` aboneliği, `THR_MDL_FAC`, [0,1] → [-1,1]
      - `px4io.cpp`: `updateOutputs` → `PX4IO_PAGE_DIRECT_PWM`
      - `board_config.h`: `/dev/ttyS4` (1.5 Mbps), V6C10/V6C11 "NO PX4IO"
    - K4: Parametre varsayılanları `parameters.xml` ile aynı: `PWM_MAIN_FUNC1` = 0, `PWM_MAIN_TIM0..2` = 400, `PWM_MAIN_DIS1` = 1000, `PWM_MAIN_MIN1` = 1000, `PWM_MAIN_MAX1` = 2000, `PWM_MAIN_FAIL1` = -1. `THR_MDL_FAC` = 0 (`motor_params.c:57`). Motor1..4 = 101..104 (`output_functions.yaml`).
    - K5: `4019_x500_v2` içinde `PWM_MAIN_FUNC` veya `PWM_*_FUNC` ataması yok. `4001_gz_x500:35-48` içinde `SIM_GZ_EC_FUNC1..4 = 101..104`, MIN 150, MAX 1000 var. `rcS:414` `px4io start` satırı.
  - [x] 1.2 Baseline kopyalarını al
    - `01-ust-seviye-akis.md` ve `02-px4-detayli-akis.md` dosyalarını `$S/baseline-fc/` altına `cp` ile (`-p` olmadan) kopyala. Kopyanın değişiklik zamanı 6.8'deki `find -newer` kontrolünün referansıdır.
    - Baseline üzerinde MPE parse çalıştır ve node/kenar sayılarını not et. Mevcut `tbd` node sayısı 7 olmalı (`aPre`, `bIcd`, `bAltTbd`, `bGuidTbd`, `bSpTbd`, `cTimeTbd`, `dPerson`).
  - [x] 1.3 mixer_module ve FunctionMotors satırlarını doğrula
    - `src/lib/mixer_module/mixer_module.cpp:440-575`, `:666-675`, `:117-131`, `:690-706`
    - `src/lib/mixer_module/functions/FunctionMotors.hpp:52-118`
    - `src/lib/mixer_module/output_functions.yaml` (Motor1..12 = 101..112), `src/lib/mixer_module/motor_params.c:57`
    - `actuator_outputs`'un sürücü `updateOutputs` çağrısından **sonra** yayınlandığını teyit et
    - `output_limit` dallarını teyit et: armed değil → disarmed, normal → MIN..MAX, kill/lockdown → DIS, termination → FAIL
  - [x] 1.4 px4io, kart ve başlatma satırlarını doğrula
    - `src/drivers/px4io/px4io.cpp:363-378`, `src/drivers/px4io/module.yaml` (`PWM_MAIN` öneki, PWM 50/100/200/400 Hz veya OneShot, DShot yok, varsayılan 400)
    - `boards/px4/fmu-v6c/src/board_config.h:59-72`, `:149-150`, `boards/px4/fmu-v6c/default.px4board:32` (`CONFIG_DRIVERS_PX4IO=y`)
    - `ROMFS/px4fmu_common/init.d/rcS:414`, `ROMFS/px4fmu_common/init.d/airframes/4019_x500_v2`
  - [x] 1.5 Parametre ve SITL satırlarını doğrula
    - `build/px4_fmu-v6c_default/parameters.xml` içindeki `PWM_MAIN_FUNC1`, `PWM_MAIN_TIM0..2`, `PWM_MAIN_DIS1`, `PWM_MAIN_MIN1`, `PWM_MAIN_MAX1`, `PWM_MAIN_FAIL1` girdileri. Bu satır numaraları derlemeye bağlıdır, şemaya "(build çıktısı)" etiketiyle yazılacak.
    - `ROMFS/px4fmu_common/init.d-posix/airframes/4001_gz_x500:35-48`, `src/modules/simulation/gz_bridge/module.yaml` (`SIM_GZ_EC` öneki)
  - [x] 1.6 Sonuçları sınıflandır
    - Her ad şu etiketlerden birini alır: doğrulandı / "(doğrulanacak)" / "(build çıktısı)"
    - Kalıcı olarak "(doğrulanacak)" kalacaklar: IO'suz V6C10/V6C11 sürümleri (kullanıcının kartında IO olduğu varsayılır), MAIN 1–4 ↔ motor sırası, QGC Actuators ataması, `PWM_MAIN_FAIL` = -1 anlamı (fonksiyonun varsayılan failsafe değeri)
    - Spec'teki bir satır numarası kaynakla uyuşmazsa şemaya kaynaktaki doğru satır yazılır ve fark Task Group 6 raporunda kullanıcıya bildirilir. Bulunamayan ad uydurulmaz.
    - Notlar scratch alanında tutulur (ör. `$S/pwm-envanter.txt`). `implementation/1-ad-envanteri.md` değiştirilmez.
  - [x] 1.7 Grup 1 kontrollerini çalıştır
    - YALNIZCA 1.1'deki K1–K5 kontrollerini çalıştır

**Acceptance Criteria:**
- 1.1'deki kontroller geçer. Geçmeyen her ad bir kaynak düzeltmesine veya "(doğrulanacak)" etiketine bağlanmıştır.
- İki şema dosyasının baseline kopyası scratch alanındadır.
- Repoda hiçbir dosya değişmemiştir.

### Şema 2

#### Task Group 2: Şema 2 Ortak Bölümler ve (B) Giriş Tarafı
**Dependencies:** Task Group 1

- [x] 2.0 Şema 2'nin başlık, lejant ve TBD bölümlerini güncelle, (B)'deki Pi bloğunu FC giriş kutusuyla değiştir
  - [x] 2.1 2–8 doğrulama kontrolü tanımla
    - K1: Başlığın hemen altında bu spec'e (`agent-os/specs/2026-10-18-m15-fc-only-flow-diagrams/`) atıf yapan not var. Not, önceki spec metinlerinin Pi'yi ve 5 adımı anlatmaya devam ettiğini söylüyor.
    - K2: Lejant katman tablosunda "Pi (Vision)" satırı yok, diğer satırlar baseline ile birebir aynı.
    - K3: TBD tablosunda 8 satır var. #1 "FC'nin beklediği hedef LOS mesajı" olarak yazılmış ve "Pi → FC" içermiyor. #8 "SITL'de LOS girdisi" satırı (blok D) var. #2–#7 baseline ile birebir aynı.
    - K4: (B) bloğunda `bPi`, `bPiLos`, `bPiSend`, `bPiPort` id'leri ve bunlara giden kenarlar yok. `class` satırlarında bu id'lere referans yok.
    - K5: Yeni giriş paralelkenarı (`bLosIn`, `input` sınıfı) var. Beş alanı listeliyor ve `bLinkHw` / `bLinkSitl`'e iki etiketli ok ile, `bIcd`'ye noktalı çizgiyle bağlanıyor.
    - K6: `bLink` subgraph'ı altı node'u koruyor (`bLinkHw`, `bLinkSitl`, `bRecv`, `bIcd`, `bTsNote`, `bQueueNote`). `bIcd` başlığı "TBD: ICD (FC'nin beklediği hedef LOS mesajı)". `bTsNote` "görüntü yakalama" içermiyor.
    - K7: (B) giriş metninde "Pi'den gelen" yok. Port maddesi yalnızca "FC tarafı TELEM2 = `/dev/ttyS3`" diyor. (B) notlarında `ttyAMA0` ve `companion.md:8` yok.
    - K8: (B) bloğu MPE ile `PARSE OK`.
  - [x] 2.2 Dosya başı notunu ve giriş paragrafını güncelle
    - Başlığın hemen altına kısa not: şema FC'ye özel olarak güncellendi, bkz. `agent-os/specs/2026-10-18-m15-fc-only-flow-diagrams/`. Önceki spec'in `spec.md`, `tasks.md` ve `implementation/` metinleri Pi'yi ve 5 adımlı (D) akışını anlatmaya devam eder.
    - Giriş paragrafı: "Pi'den gelen body FRD LOS" → "FC'ye MAVLink ile gelen body FRD LOS". Zincirin MAIN PWM çıkışına kadar gösterildiğini ekle.
    - Düz dünya, guidance, ad kaynağı ve bloklar maddeleri ile render edilmeyen "Blok yazım kuralları" yorum bloğu değişmez
  - [x] 2.3 Lejantı ve açık konular tablosunu güncelle
    - Katman tablosundan "Pi (Vision) | `Raspberry Pi (Vision)` | B" satırını sil. Diğer satırlara dokunma.
    - TBD #1 (ICD): "Pi → FC hedef LOS mesajı" → "FC'nin beklediği hedef LOS mesajı". `DEBUG_VECT` aday, gösterim, hız, gecikme, zaman damgası ve "hedef yok" sinyali aynı kalır.
    - Yeni satır #8: "SITL'de LOS girdisi | Test sırasında FC'ye gelecek LOS mesajının SITL'de nasıl üretileceği. Sahte Pi adımı kullanıcı kararıyla silindi, ileride eklenebilir | D"
  - [x] 2.4 (B) giriş metnini güncelle
    - "Pi'den gelen LOS örneği" → "FC'ye gelen LOS örneği"
    - "Pi ve FC portları karıştırılmaz" maddesini yalnızca FC portunu anlatacak şekilde yeniden yaz: "FC tarafı TELEM2 = `/dev/ttyS3`"
    - Çevrim sırası ve "setpoint her çevrimde yayınlanır" maddeleri değişmez
    - Şema 1 eşleme tablosu bu grupta değişmez, Task Group 5'te güncellenir
  - [x] 2.5 `bPi` subgraph'ını ve oklarını sil
    - Silinecek node'lar: `bPiLos`, `bPiSend`, `bPiPort` ve `subgraph bPi ... end`
    - Silinecek oklar: `bPiLos --> bPiSend`, `bPiSend --> bPiPort`, `bPiSend -.- bIcd`, `bPiPort -- ... --> bLinkHw`, `bPiPort -- ... --> bLinkSitl`
    - `class` satırlarından `bPiLos` (`input`), `bPiSend` ve `bPiPort` (`process`) referanslarını temizle
  - [x] 2.6 FC giriş paralelkenarını ekle
    - `bLosIn[/"..."/]`, `input` sınıfı, `bLink` subgraph'ının üstünde
    - Etiket: "Body FRD LOS (montaj açısı dahil), MAVLink ile TELEM2'den gelir (ICD TBD)" ve FC'nin beklediği alanlar:
      - `DEBUG_VECT` aday
      - `name` en fazla 9 karakter (ör. #quot;TEZ_LOS#quot;, öneri)
      - x/y/z = LOS_body birim vektör
      - FC montaj açısını bilmez
      - `time_usec` FC'de kullanılmaz
    - Oklar: `bLosIn -- "MAVLink DEBUG_VECT (seri, TELEM2)" --> bLinkHw`, `bLosIn -- "MAVLink DEBUG_VECT (UDP, SITL)" --> bLinkSitl`, `bLosIn -.- bIcd`
  - [x] 2.7 `bLink` subgraph'ındaki Pi atıflarını nötrle
    - `bIcd` başlığı: "TBD: ICD (FC'nin beklediği hedef LOS mesajı)". Altındaki içerik satırları aynı kalır. `tbd` sınıfı korunur.
    - `bTsNote`: "görüntü yakalama anı" → "LOS ölçüm anı" gibi nötr ifade. "Görüntü anındaki tutum" ifadesi de aynı anlamla nötr yazılır ("ölçüm anındaki tutum").
    - `bLinkHw`, `bLinkSitl` (local 14580 / remote 14540 PX4 tarafı ayarıdır, kalır), `bRecv`, `bQueueNote` değişmez
  - [x] 2.8 (B) notlarındaki Pi cümlesini sil
    - "Donanım bağlantısı" maddesinden yalnızca "Pi tarafı `/dev/ttyAMA0` ve `udp:127.0.0.1:14540`: `agent-os/standards/python/companion.md:8`." cümlesini sil. Maddenin geri kalanı değişmez.
  - [x] 2.9 Grup 2 kontrollerini çalıştır
    - YALNIZCA 2.1'deki K1–K8 kontrollerini çalıştır (MPE parse yalnızca (B) bloğu için)

**Acceptance Criteria:**
- 2.1'deki kontroller geçer.
- (B) bloğu FC'ye gelen mesajla başlar. Pi'nin gönderen tarafı (port, pymavlink, `/dev/ttyAMA0`) şemada yoktur, FC'nin alan tarafı aynen durur.
- Başlık notu, lejant ve TBD tablosu spec'teki metinlerle uyumludur.

#### Task Group 3: Şema 2 (B) Kontrolcü Zincirinin MAIN PWM'e Kadar Uzatılması
**Dependencies:** Task Groups 1, 2

- [x] 3.0 `bEsc` node'unu `actuator_motors`'tan MAIN PWM → ESC → motorlar zinciriyle değiştir
  - [x] 3.1 2–8 doğrulama kontrolü tanımla
    - K1: `bEsc` id'si yok. `bAlloc -- "actuator_motors" -->` kenarı mixer node'una gidiyor.
    - K2: Zincir sırayla izlenebilir: mixer_module `MixingOutput` / FunctionMotors → `output_limit` → px4io sürücüsü → `/dev/ttyS4` → IO işlemcisi → MAIN 1–4 PWM 400 Hz → ESC → motorlar → "araç hedefi takip eder".
    - K3: `output_limit` dört durumu içeriyor: armed değil → disarmed, normal → `PWM_MAIN_MIN`..`PWM_MAIN_MAX` (1000–2000 µs), kill/lockdown → `PWM_MAIN_DIS` (1000), termination → `PWM_MAIN_FAIL` (-1, doğrulanacak).
    - K4: `actuator_outputs` yan çıkışı var ve bir `note` ile ULog'a bağlı.
    - K5: Motor ataması notu (`PWM_MAIN_FUNC1..4 = 101..104`, varsayılan 0, 4019 ayarlamaz, QGC Actuators, motor sırası "(doğrulanacak)") ve SITL `gz_bridge` notu (`SIM_GZ_EC_FUNC1..4`, MIN 150 / MAX 1000, PWM değil motor hızı) `note` sınıfında. SITL bir dal olarak çizilmemiş.
    - K6: V6C10/V6C11 "(doğrulanacak)" notu var. Şemada AUX, `pwm_out` veya `dshot` dalı yok. Mevcut "Kontrolcü zinciri" notundaki "(pwm_out, dshot ve gz_bridge `MixingOutput` kullanır)" ifadesi korunmuş.
    - K7: (B) notlarında PWM zinciri için yeni bir madde var. Task Group 1'de doğrulanan kaynak satırlarının hepsini içeriyor, `build/` satırları "(build çıktısı)" etiketli.
    - K8: (B) bloğu MPE ile `PARSE OK` ve headless Chrome render `syntax-error-markers=0`.
  - [x] 3.2 Çıkış subgraph'ını oluştur
    - `bCtl` ("FlightModeManager ve kontrolcüler") içinde veya hemen altında ayrı bir subgraph (ör. `bOut ["Çıkış: mixer_module ve px4io"]`)
    - Mevcut paleti kullan (`process`, `note`, `warn`). Yeni `classDef` ekleme.
  - [x] 3.3 mixer ve FunctionMotors node'unu ekle
    - `bAlloc -- "actuator_motors" --> bMix`. Etiket: mixer_module `MixingOutput` / FunctionMotors, `THR_MDL_FAC` (varsayılan 0), [0,1] → [-1,1]
    - Eski `bAlloc -- "actuator_motors" --> bEsc` kenarını ve `bEsc` node'unu, `class` satırındaki `bEsc` referansıyla birlikte kaldır
  - [x] 3.4 Çıkış sınırlama (`output_limit`) adımlarını ekle
    - Tek node veya kısa karar/işlem dizisi: armed değil → disarmed değeri. Normal → `PWM_MAIN_MIN`..`PWM_MAIN_MAX` (1000–2000 µs). Kill/lockdown → `PWM_MAIN_DIS` (1000). Termination → `PWM_MAIN_FAIL` (varsayılan -1: fonksiyonun varsayılan failsafe değeri, doğrulanacak).
    - Karar node'u kullanılırsa `decision` sınıfı alır ve her dalı etiketlidir
  - [x] 3.5 px4io ve MAIN çıkışını ekle
    - px4io sürücüsü: `updateOutputs` → `PX4IO_PAGE_DIRECT_PWM`
    - Seri hat `/dev/ttyS4` (1.5 Mbps) → IO işlemcisi
    - MAIN 1–4 PWM 400 Hz (`PWM_MAIN_TIMx`, varsayılan 400)
    - ESC → motorlar → "araç hedefi takip eder"
    - Yalnızca MAIN dalı. ESC'ler MAIN portuna PWM ile bağlıdır (kullanıcı bilgisi).
  - [x] 3.6 Yan çıkışı ve notları ekle
    - `actuator_outputs`: mixer_module tarafından sürücü çağrısından sonra yayınlanır. Mevcut ULog (`bLog`) notuna veya ayrı bir `note`'a noktalı bağlantı.
    - Motor ataması `note`: `PWM_MAIN_FUNC1..4 = 101..104` (Motor 1..4), varsayılan 0 (Disabled), 4019_x500_v2 airframe ayarlamaz, QGC Actuators sekmesinde elle yapılır, MAIN 1–4 ↔ motor sırası (doğrulanacak)
    - SITL yan `note`'u: `gz_bridge` aynı `MixingOutput`'u kullanır, `SIM_GZ_EC_FUNC1..4 = 101..104`, MIN 150 / MAX 1000, çıkış PWM değil motor hızıdır
    - "(doğrulanacak)" notu (`note` veya `warn`): V6C10/V6C11 donanım sürümlerinde PX4IO yoktur, kullanıcının kartında IO olduğu varsayılır
  - [x] 3.7 (B) notlarına PWM zinciri maddesini ekle
    - Mevcut "Kontrolcü zinciri" maddesi değişmez. Altına ayrı bir "PWM zinciri" maddesi eklenir.
    - Kaynak satırları (Task Group 1'de doğrulanmış hâliyle):
      - mixer: `src/lib/mixer_module/mixer_module.cpp:440-575`, `:666-675`, `:117-131`, `:690-706`
      - FunctionMotors: `src/lib/mixer_module/functions/FunctionMotors.hpp:52-118`
      - motor fonksiyonları ve `THR_MDL_FAC`: `src/lib/mixer_module/output_functions.yaml`, `src/lib/mixer_module/motor_params.c:57`
      - px4io: `src/drivers/px4io/px4io.cpp:363-378`, `src/drivers/px4io/module.yaml`
      - kart: `boards/px4/fmu-v6c/src/board_config.h:59-72`, `:149-150`, `boards/px4/fmu-v6c/default.px4board:32`
      - başlatma: `ROMFS/px4fmu_common/init.d/rcS:414`, `ROMFS/px4fmu_common/init.d/airframes/4019_x500_v2`
      - parametre varsayılanları: `build/px4_fmu-v6c_default/parameters.xml` (build çıktısı)
      - SITL: `ROMFS/px4fmu_common/init.d-posix/airframes/4001_gz_x500:35-48`
  - [x] 3.8 Grup 3 kontrollerini çalıştır
    - YALNIZCA 3.1'deki K1–K8 kontrollerini çalıştır (parse ve render yalnızca (B) bloğu için)

**Acceptance Criteria:**
- 3.1'deki kontroller geçer.
- `debug_vect`'ten MAIN PWM'e kadar veri yolu kenar etiketleriyle izlenebilir.
- Yeni PWM adlarının hepsi v1.17.0 kaynağına bağlıdır veya "(doğrulanacak)" / "(build çıktısı)" etiketlidir.

#### Task Group 4: Şema 2 (D) Sahte Pi Adımının Silinmesi, Yeniden Numaralandırma ve Nötrleme
**Dependencies:** Task Group 2 (TBD #8 satırı). Task Group 3 ile paralel yürüyebilir.

- [x] 4.0 (D) bloğunu FC'ye özel hâle getir
  - [x] 4.1 2–8 doğrulama kontrolü tanımla
    - K1: `dStep3` (eski "Sahte Pi"), `dFakePi`, `dTruth`, `dPiQ`, `dPiFix` id'leri ve bunlara giden/gelen kenarlar yok. `class` satırlarında bu id'lere referans yok.
    - K2: `dBootQ -- "evet" --> dPick` var. `dRcSim`, `dQgc`, `dFailNote` `dScn` subgraph'ının üyesi (MPE subgraph dökümü). `dRcSim → dPick`, `dQgc → dPick`, `dRcSim -.- dFailNote` kenarları var.
    - K3: `dLosTbd` (`tbd` sınıfı) var ve `dPick`'e noktalı çizgiyle bağlı. Etiket S2, S4 ve S5'i anıyor.
    - K4: Dört adım sırayla: Adım 1 GoogleTest → Adım 2 Gazebo Harmonic SITL → Adım 3 ULog + pyulog metrikleri → Adım 4 gerçek uçuş. Subgraph id'leri `dStep1`..`dStep4`, `dStep5` id'si yok. `dScn` başlığı "Adım 2–3". (D) bölümünde "Adım 5" geçmiyor.
    - K5: Her karar node'unun (`dUnitQ`, `dBootQ`, `dPick`, `dMetQ`, `dMoreQ`, `dRestart`, `dBenchQ`, `dFlightQ`) "hayır" (veya alternatif) kenarı var olan bir node'a gidiyor. Kenarı olmayan ya da hiçbir kenara bağlanmayan node yok.
    - K6: (D) bölümünde `Pi`, `Raspberry`, `Vision`, `ttyAMA0`, `Sahte Pi`, `sahte Pi`, `ikinci gönderici` geçmiyor. `pymavlink` yalnızca `dRcSim` ve "Sürümler" satırında geçiyor.
    - K7: `dUnitFn` içindeki "ICD doğrulama" ve "Saat ve ground truth" not maddesi korunmuş.
    - K8: (D) bloğu MPE ile `PARSE OK` ve headless Chrome render `syntax-error-markers=0`.
  - [x] 4.2 Sahte Pi adımını sil ve korunacak node'ları taşı
    - Sil: `subgraph dStep3 ["Adım 3: Sahte Pi (pymavlink)"] ... end`, `dFakePi`, `dTruth`, `dPiQ`, `dPiFix`
    - Sil: `dBootQ -- "evet" --> dFakePi`, `dTruth -. "LOS kaynağı" .-> dFakePi`, `dFakePi -- ... --> dPiQ`, `dPiQ -- "hayır" --> dPiFix`, `dPiFix -- "geri dön: Adım 3" --> dFakePi`, `dPiQ -- "evet" --> dPick`
    - `dRcSim`, `dQgc`, `dFailNote` node tanımlarını içerikleri değişmeden `dScn` subgraph'ına taşı. `dRcSim` pymavlink `RC_CHANNELS_OVERRIDE` kullanmaya devam eder (Pi'ye ait değildir).
    - Ekle: `dBootQ -- "evet" --> dPick`
    - `class` satırlarından `dFakePi`, `dTruth`, `dPiFix` (`process`) ve `dPiQ` (`decision`) referanslarını temizle
  - [x] 4.3 SITL LOS girdisi TBD node'unu ekle
    - `dLosTbd("TBD: SITL'de LOS girdisinin nasıl üretileceği<br/>S2, S4 ve S5 bu girdiye ihtiyaç duyar<br/>...")`, `tbd` sınıfı, `dScn` içinde
    - `dLosTbd -.- dPick`
    - TBD tablosundaki #8 satırıyla (Task Group 2) aynı konuyu anlatır
  - [x] 4.4 Adımları yeniden numaralandır
    - Subgraph'lar: eski `dStep4 ["Adım 4: ULog + pyulog metrikleri"]` → `dStep3 ["Adım 3: ULog + pyulog metrikleri"]`. Eski `dStep5 ["Adım 5: Gerçek uçuş"]` → `dStep4 ["Adım 4: Gerçek uçuş"]`.
    - Node etiketleri: `dMetrics` "Adım 4:" → "Adım 3:", `dFlight` "Adım 5:" → "Adım 4:"
    - `dScn` başlığı: "SITL senaryoları (Adım 2–4, ...)" → "(Adım 2–3, ...)"
    - Giriş metnindeki "Sıra" maddesi: dört adım. "Adım 2–4 her senaryo için..." ifadesi "Adım 2–3" olur.
    - Senaryo tablosundaki "Adım 5" satırı "Adım 4" olur
    - "Başarısızlık" maddesi, geri dönüş okları (`geri dön: Adım 1`, `evet: Adım 1'den` vb.) ve (D) notlarında geçen adım numaralarını tek tek kontrol et, eski numara kalmasın
  - [x] 4.5 Senaryo ve donanım etiketlerini nötrle
    - `dSc4`: "sahte Pi göndermeyi keser" → "LOS mesajı kesilir"
    - `dSc5`: "yanlış name'li DEBUG_VECT (ikinci gönderici)" → "ikinci kaynaktan yanlış name'li DEBUG_VECT"
    - `dHwCfg`: "Pi 5 /dev/ttyAMA0 ↔ TELEM2, Vision kodu ICD'ye göre (ICD TBD)" satırını sil. TELEM2, `extras.txt` ve SDLOG satırları kalır.
    - `dFlight`: "+ Raspberry Pi 5" sil. Etiket "X500 V2 + Pixhawk 6C" olur.
    - Senaryo tablosunun gerçek uçuş satırı: "Pi bağlantısı" → "TELEM2'den LOS alımı (`debug_vect`)"
    - Pi ya da test aracı adı geçmez
  - [x] 4.6 (D) notlarını güncelle
    - "Sahte Pi ve pilot simülasyonu" maddesi → "Pilot simülasyonu". Sahte Pi'ye ait onboard UDP atfı (`px4-rc.mavlink:4-5`, `:26`) çıkar. GCS bağlantısı, `RC_CHANNELS_OVERRIDE`, `COM_RC_IN_MODE` ve `RC_MAP_*` atıfları kalır.
    - "Sürümler" satırındaki `pymavlink 2.4.50` pilot simülasyonu için korunur
    - "Saat ve ground truth" maddesi korunur (takip mesafesi metriği için gerekli)
  - [x] 4.7 Grup 4 kontrollerini çalıştır
    - YALNIZCA 4.1'deki K1–K8 kontrollerini çalıştır (parse ve render yalnızca (D) bloğu için)

**Acceptance Criteria:**
- 4.1'deki kontroller geçer.
- (D) akışı dört adımlıdır ve her kapının başarısızlık dönüşü geçerli bir hedefe gider.
- SITL'de LOS üretimi boşluğu `dLosTbd` ile görünür. Pi ya da test aracı adı (D)'de geçmez.

### Şema 1

#### Task Group 5: Şema 1'in FC'ye Özel ve Daha Detaylı Hâle Getirilmesi, (B) Eşleme Tablosu
**Dependencies:** Task Groups 2, 3 (eşleme tablosu (B)'deki yeni giriş ve çıkış node id'lerine bağlıdır)

- [x] 5.0 Şema 1'i referans görselin üslubunda, sade dille ve daha detaylı olarak yeniden çiz, (B) eşleme tablosunu güncelle
  - [x] 5.1 2–8 doğrulama kontrolü tanımla
    - K1: `piBox`, `piImg`, `piDetect`, `piCamLos`, `piBodyLos`, `style piBox` yok. Giriş paragrafında "Raspberry" ve "Pi" geçmiyor (başlık altı not hariç).
    - K2: Toplam node sayısı 25–30 aralığında (MPE parse sayımı).
    - K3: Üç karar node'u eşkenar dörtgen (`{"..."}`) şeklinde: "Mod aktif mi?", "Gelen mesaj geçerli mi?", "Hedef görünüyor mu?". Her birinin "hayır" kenarı var ve doğru sonuca gidiyor (hesap yapılmaz / örnek atılır / yerinde bekle → süre dolunca Hold).
    - K4: `icdMsg` paralelkenar şeklinde, etiketi "Body FRD LOS (montaj açısı dahil), MAVLink ile gelir (ICD TBD)" ve kesik çizgili TBD vurgusunu taşıyor. Dört yan girdi ("UAV Roll / Pitch / Yaw", "İrtifa (baro / EKF) — TBD", "UAV yerel NED konumu", "Pilot / QGC mod seçimi") paralelkenar olarak duruyor.
    - K5: Ana zincir sırayla izlenebilir: NED'e çevirme → aşağı açı ve eğik mesafe → hedefin yerel NED konumu → hedef kestirimi → guidance parçaları → konum kontrolü → tutum kontrolü → açısal hız kontrolü → motor karıştırma → PWM → ESC → motorlar → araç hedefi takip eder. Moda giriş ve mod anahtarıyla çıkış var.
    - K6: PX4 topic/parametre adı yok (ör. `_setpoint`, `vehicle_`, `actuator_`, `PWM_MAIN`, `MPC_`, `TEZ_FOL_`, `debug_vect`, `DEBUG_VECT`, `nav_state`). "ECEF" ve "WGS84" yok. `guidance-yasalari.md` atfı ve referans görsel bağlantısı korunmuş.
    - K7: Lejantta "eşkenar dörtgen = karar" var. Kutular siyah-beyaz, `linkStyle default` `#4472c4`. `decision` `classDef` tanımlıysa siyah-beyaz.
    - K8: Her Şema 1 kutusu (B) eşleme tablosunun sol sütununda birebir geçiyor ve sağ sütundaki her id (B) bloğunda mevcut. Pi satırları (`bPiLos`, `bPiSend`) yok.
  - [x] 5.2 Başlık notunu ve giriş paragrafını yeniden yaz
    - Başlığın hemen altına Şema 2'deki gibi kısa not: FC'ye özel olarak güncellendi, bkz. `agent-os/specs/2026-10-18-m15-fc-only-flow-diagrams/`. Önceki spec metinleri Pi'yi ve 5 adımı anlatmaya devam eder.
    - Giriş paragrafı FC'nin bakış açısından: FC'ye MAVLink ile body FRD LOS gelir (montaj açısı dahil), FC bunu PWM'e kadar işler. Düz dünya kabulü cümlesi korunur.
    - Üslup rehberi, lejant ve guidance atfı maddeleri korunur. Lejant satırına "eşkenar dörtgen = karar" eklenir.
  - [x] 5.3 Pi kutusunu sil, FC giriş paralelkenarını kur
    - `piBox` subgraph'ı, dört node'u, oklarını, `class` satırlarındaki referansları ve `style piBox` satırını sil
    - `icdMsg[/"Body FRD LOS (montaj açısı dahil), MAVLink ile gelir (ICD TBD)"/]`. Paralelkenar şekli ile `tbd` stilini birleştir (ör. `class icdMsg tbd`, şekil paralelkenar kalır).
    - ECEF/WGS84 kutusu eklenmez
  - [x] 5.4 Mod girişi, çıkışı ve "Mod aktif mi?" kararını ekle
    - "Pilot / QGC mod seçimi" girdisi moda girişi başlatır
    - "Mod aktif mi?" eşkenar dörtgeni. Hayır → "hesap yapılmaz".
    - "Mod anahtarıyla çıkış" adımı (pilot RC mod anahtarı veya QGC ile başka moda geçer)
    - Sıra (B) çevrim sırasıyla uyumlu olmalı: önce mod kapısı, sonra mesaj kontrolü
  - [x] 5.5 "Gelen mesaj geçerli mi?" ve "Hedef görünüyor mu?" kararlarını ekle
    - Mesaj kontrolü sade dille: doğru ad, sayılar geçerli, birim vektör, mesaj taze. Hayır → "örnek atılır".
    - Hedef görünüyor mu: hayır → "yerinde bekle" → "süre dolunca Hold"
  - [x] 5.6 Ana hesap zincirini sade dille yaz
    - "LOS'u yere göre yöne çevir (NED)" (tutum yan girdisi buraya bağlanır)
    - "Aşağı açı ve eğik mesafe" (irtifa TBD yan girdisi buraya bağlanır)
    - "Hedefin yerel NED konumu" (UAV yerel NED konumu yan girdisi buraya bağlanır)
    - "Hedef kestirimi (konum/hız)"
    - Yan girdiler ana zincire yatay okla bağlanır. Mermaid yerleşimi tam yatay olmazsa düşük-orta sadakat kabul edilir.
  - [x] 5.7 Guidance parçalarını ve kontrol zincirini ekle
    - Guidance: "İstenen konum / takip mesafesi" → "İstenen hız" → "Yaw hedefe bakar" → "Hız ve irtifa sınırları"
    - Kontrol: "Konum kontrolü" → "Tutum kontrolü" → "Açısal hız kontrolü" → "Motor karıştırma" → "PWM" → "ESC" → "Motorlar" → "Araç hedefi takip eder"
    - Topic, parametre ve ağır teknik terim yok. Ayrıntılar yalnızca Şema 2'dedir.
  - [x] 5.8 Stili uygula ve node bütçesini kontrol et
    - Mevcut `classDef input` / `process` / `tbd` (siyah-beyaz, 1.5px) korunur. Gerekirse `classDef decision` (beyaz zemin, siyah çerçeve) eklenir.
    - `style fcBox` ve `linkStyle default stroke:#4472c4,stroke-width:1.5px` aynı kalır
    - Hedef 25–30 node. Aşılırsa birleştirilecek kutular sade dili bozmadan seçilir.
  - [x] 5.9 (B) "Şema 1 ile karşılık" tablosunu güncelle
    - Sil: `bPiLos` ve `bPiSend` satırları
    - Ekle: "Body FRD LOS (montaj açısı dahil), MAVLink ile gelir (ICD TBD)" → `bLosIn`, `bIcd`, MAVLink katmanı
    - Yeni eşlemeler:
      - mesaj kontrolü → `bVecQ`, `bChkName`..`bChkFresh`, `bDrop`
      - mod aktif mi → `bGate` (hesap yapılmaz → `bIdle`)
      - hedef görünüyor mu → `bAgeQ`, `bLostRef`
      - guidance parçaları → `bGuid`, `bSat`, `bTraj`
      - konum / tutum / açısal hız kontrolü → `bPos`, `bAtt`, `bRate`
      - motor karıştırma → `bAlloc` ve mixer node'u (`bMix`)
      - PWM → ESC → motorlar → Task Group 3'teki yeni çıkış node'ları
      - moda giriş / çıkış → (C) bloğuna atıf veya `bGate`
    - Sol sütun Şema 1 kutu etiketleriyle birebir aynı yazılır (K7-1 terim tutarlılığı)
  - [x] 5.10 Grup 5 kontrollerini çalıştır
    - YALNIZCA 5.1'deki K1–K8 kontrollerini çalıştır
    - Şema 1 için MPE parse ve headless Chrome render. `mmd_check.py`'nin `direction TB` / `style` / subgraph kenarı uyarıları yanlış pozitif kabul edilir.

**Acceptance Criteria:**
- 5.1'deki kontroller geçer.
- Şema 1 yalnızca FC'yi gösterir, önceki sürümden belirgin biçimde daha detaylıdır ama sade dilde kalır. Paralelkenar = girdi, yuvarlak köşeli kutu = işlem, eşkenar dörtgen = karar, kesik çizgi = TBD.
- Şema 1'in her kutusu (B) eşleme tablosu üzerinden bir (B) node'una bağlanır.

### Son Gözden Geçirme

#### Task Group 6: Çapraz Tutarlılık, Kapsam ve Sözdizimi Kontrolü
**Dependencies:** Task Groups 1-5

- [x] 6.0 İki şemayı birlikte gözden geçir ve kritik boşlukları kapat
  - [x] 6.1 Grup 1–5 kontrollerini gözden geçir
    - Toplam mevcut kontrol: yaklaşık 30–40
  - [x] 6.2 Grep kontrolü
    - İki şema dosyasında `Raspberry`, `Vision`, `ttyAMA0`, `Sahte Pi`, `sahte Pi`, `bPi`, `piBox`, `dFakePi`, `dPiQ` geçmez. Tek istisna dosya başındaki bu spec'e atıf notudur.
    - Ek: bütün kelime olarak `Pi` (`grep -nw Pi`) ve `udp:127.0.0.1:14540` yalnızca başlık notunda geçebilir
    - `pymavlink` yalnızca `dRcSim`, (D) "Pilot simülasyonu" notu ve "Sürümler" satırında kalır
  - [x] 6.3 Değişmeyen bölümlerin baseline ile karşılaştırılması
    - (A) ve (C) Mermaid blokları (blok indeksi 0 ve 2) ile "(A) notları" ve "(C) notları" bölümleri `$S/baseline-fc/02-px4-detayli-akis.md` ile byte düzeyinde aynı
    - Lejant tablolarındaki "Pi (Vision)" dışındaki satırlar ve TBD #2–#7 aynı
    - Baseline'a göre diff'te yalnızca spec'te listelenen değişiklikler görünür (`diff $S/baseline-fc/... <repo dosyası>` gözden geçirilir)
  - [x] 6.4 TBD ve eşleme tutarlılığı (K7-1, K7-2)
    - TBD tablosu 8 satır ↔ şemada 8 `tbd` node (`aPre`, `bIcd`, `bAltTbd`, `bGuidTbd`, `bSpTbd`, `cTimeTbd`, `dPerson`, `dLosTbd`). Her satır bir node'a karşılık gelir. Şema 1'deki `icdMsg` ve irtifa TBD'leri Şema 2 sayımına girmez.
    - Şema 1 kutuları ↔ (B) eşleme tablosu eksiksiz. Tablodaki her id (B) bloğunda var.
  - [x] 6.5 Repo yolları ve sözdizimi (K7-8, K7-9)
    - Şema 2 notlarına eklenen her repo yolu mevcut (`ls`). Planlanan yollar ve glob'lar hariç.
    - Dört Şema 2 bloğu ve Şema 1 bloğu MPE ile `PARSE OK`, headless Chrome ile `syntax-error-markers=0`
    - `mmd_check.py` Şema 2 bloklarında 0 hata. Şema 1'de yalnızca bilinen yanlış pozitifler.
    - Elle kontrol listesi: tırnak içinde çıplak `"` yok, id'ler ASCII ve benzersiz, her `subgraph` bir `end` ile kapanıyor, kullanılmayan id veya `class` referansı yok
  - [x] 6.6 Kapsam kontrolü
    - Şemalarda yok: Vision/Pi tarafı (kamera, tespit, piksel → kamera → body LOS, Pi'de gönderim), AUX / `pwm_out` / DShot dalı, `gz_bridge` tam dalı (yalnızca not), ECEF/WGS84, SITL LOS test vericisi (yalnızca TBD)
  - [x] 6.7 Gerekirse en fazla 10 ek kontrol yaz
    - Yalnızca kritik boşluklar için (ör. bir karar node'unun dalı etiketsiz, bir (B) kenarı silinen node'a gidiyor, bir user story şemadan izlenemiyor)
  - [x] 6.8 Repo hijyeni ve özellik kontrollerini çalıştır (K7-10)
    - YALNIZCA bu spec'in kontrollerini çalıştır (1.1, 2.1, 3.1, 4.1, 5.1, 6.2–6.7)
    - `git status` ve `git branch --show-current`: branch `yusuf/agent-os-denemeleri-ve-sema-olusturma`, değişiklik yalnızca `agent-os/specs/` altında. `find agent-os/specs/2026-10-15-m15-target-follow-flight-mode -newer $S/baseline-fc/02-px4-detayli-akis.md -type f` yalnızca iki şema dosyasını listeler (önceki spec'in diğer dosyaları değişmemiştir). Commit atılmaz.
    - Kaynakla uyuşmayan spec satırları (bkz. 1.6) ve kalan "(doğrulanacak)" maddeleri kullanıcıya kısa listeyle raporlanır
    - Rapor gerekiyorsa bu spec'in `implementation/` klasörüne yazılır

**Acceptance Criteria:**
- Tüm özellik kontrolleri geçer (yaklaşık 30–50 kontrol).
- İki şema sözdizimsel olarak geçerli, birbiriyle tutarlı ve spec'in in-scope / out-of-scope sınırlarına uygundur.
- Repoda yalnızca iki şema dosyası ve bu spec klasörü değişmiştir.

### Masaüstü Çıktıları

#### Task Group 7: Masaüstü .md Kopyaları ve PDF'ler (orkestratör yapar)
**Dependencies:** Task Group 6

- [x] 7.0 Masaüstündeki güncel sürümlerin üzerine yaz (uygulamadan sonra orkestratör tarafından yapılır)
  - [x] 7.1 2–4 doğrulama kontrolü tanımla
    - K1: `/home/yusuf/Desktop/hedef-takip-ciktilari/01-ust-seviye-akis.md` ve `02-px4-detayli-akis.md` repo dosyalarıyla birebir aynı (`cmp`)
    - K2: `01-ust-seviye-akis.pdf` ve `02-px4-detayli-akis.pdf` yeniden üretilmiş (değişiklik zamanı uygulamadan sonra), açılıyor ve Mermaid blokları hatasız render edilmiş görünüyor
    - K3: `1-ad-envanteri.*`, `7-son-gozden-gecirme.*` ve `referans-gorsel.jpeg` dosyalarının değişiklik zamanı değişmemiş. Klasörde `-fc` kopyası veya eski sürüm yedeği yok.
  - [x] 7.2 `.md` dosyalarını kopyala
    - İki repo dosyasını aynı adlarla üzerine yaz. Eski sürüm tutulmaz.
    - Şema 1'deki göreli referans görsel bağlantısı masaüstünde çözülmez. Bu durum önceki kopyada da vardı ve değiştirilmez.
  - [x] 7.3 PDF'leri yeniden üret
    - Orkestratör, önceki spec'teki PDF yöntemini (MPE Mermaid + headless Chrome) aynı şekilde kullanır
    - `01-ust-seviye-akis.pdf` ve `02-px4-detayli-akis.pdf` üzerine yazılır
  - [x] 7.4 Grup 7 kontrollerini çalıştır
    - YALNIZCA 7.1'deki K1–K3 kontrollerini çalıştır

**Acceptance Criteria:**
- Masaüstündeki dört dosya güncel sürümdür. Eski sürüm ve `-fc` kopyası yoktur.
- Masaüstündeki diğer dosyalara dokunulmamıştır.

## Execution Order

Önerilen uygulama sırası:
1. Baseline ve PWM kaynak doğrulaması (Task Group 1): sonraki tüm karşılaştırmaların ve yeni PWM adlarının kaynağıdır
2. Şema 2 ortak bölümler ve (B) giriş tarafı (Task Group 2)
3. Şema 2 (B) PWM zinciri (Task Group 3) ve Şema 2 (D) güncellemesi (Task Group 4): Task Group 2'den sonra paralel yürüyebilir
4. Şema 1 ve (B) eşleme tablosu (Task Group 5): (B)'deki yeni giriş ve çıkış id'leri kesinleştikten sonra
5. Çapraz tutarlılık, kapsam ve sözdizimi kontrolü (Task Group 6)
6. Masaüstü .md kopyaları ve PDF'ler (Task Group 7): uygulamadan sonra orkestratör yapar
