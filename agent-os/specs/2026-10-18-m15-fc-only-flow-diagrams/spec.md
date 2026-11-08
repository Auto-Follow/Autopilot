# Specification: FC'ye Özel Akış Şemaları (Vision/Pi Tarafı Çıkarılmış)

## Goal
Önceki spec'in iki Mermaid akış şemasını yerinde güncelleyerek yalnızca uçuş kontrolcüsünü (FC) göstermek. Akış, FC'ye MAVLink ile gelen body FRD LOS mesajıyla başlar ve MAIN çıkışından ESC'ye giden PWM sinyaliyle biter. Vision / Raspberry Pi tarafı şemalardan tamamen çıkarılır.

## User Stories
- FC tarafından sorumlu tez öğrencisi olarak, şemalarda yalnızca kendi çalışma alanımı (FC'ye ne geliyor, PWM'e nasıl gidiyor) görmek istiyorum. Böylece Vision ekibinin işi benim şemalarımı kalabalıklaştırmaz.
- Danışmanıma anlatan biri olarak, Şema 1'in sade ama önceki sürümden daha detaylı olmasını istiyorum. Kontrol adımları ve karar noktaları teknik terime boğulmadan görünmeli.
- Modülü yazacak geliştirici olarak, Şema 2 (B)'de `actuator_motors`'tan MAIN PWM çıkışına kadar olan zinciri v1.17.0 kaynağına göre doğrulanmış adlarla görmek istiyorum.

## Specific Requirements

**Teslimat, konum ve kapsam sınırı**
- Yeni şema dosyası oluşturulmaz, `-fc` kopyası yapılmaz. Şu iki dosya yerinde güncellenir:
  - `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/diagrams/01-ust-seviye-akis.md`
  - `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/diagrams/02-px4-detayli-akis.md`
- Önceki spec klasöründeki diğer dosyalar (`spec.md`, `tasks.md`, `planning/`, `implementation/`, `orchestration.yml`) kullanıcı kararıyla değişmez. Bu dosyalar Pi bloklarını ve 5 adımlı (D) akışını anlatmaya devam eder. Bu tutarsızlık bilinçlidir.
- Her iki şema dosyasının başına (başlığın hemen altına) kısa bir not eklenir. Not, şemanın FC'ye özel olarak güncellendiğini söyler ve `agent-os/specs/2026-10-18-m15-fc-only-flow-diagrams/` klasörünü gösterir. Notta önceki spec metinlerinin Pi'yi ve 5 adımı anlatmaya devam ettiği de belirtilir.
- Metinler Türkçe, teknik terimler İngilizce yazılır. Önceki spec'in Mermaid kuralları aynen geçerlidir: tırnaklı etiketler, ASCII ve blok harfiyle başlayan id'ler, `#quot;` / `#60;` / `#62;`, blok başına `classDef` paleti, "(doğrulanacak)" / "(öneri)" / TBD etiketleri.
- (A) ve (C) blokları, mevcut TBD'ler, notlar, kaynak satırları, renkler ve şekiller değişmez. Yalnızca Pi'ye atıf yapan ifadeler düzeltilir ve aşağıda listelenen eklemeler yapılır.
- Branch `yusuf/agent-os-denemeleri-ve-sema-olusturma` olarak kalır, commit atılmaz. Repoda yalnızca bu spec klasörü ve iki şema dosyası değişir.

**Şema 1: Pi'nin kaldırılması ve FC giriş kutusu**
- `piBox` subgraph'ı (`piImg`, `piDetect`, `piCamLos`, `piBodyLos`), bunlara ait oklar, `class` satırlarındaki referanslar ve `style piBox` satırı silinir.
- Giriş paragrafındaki "Raspberry Pi kamera görüntüsünde..." anlatımı FC'nin bakış açısından yeniden yazılır. Paragraf şöyle başlar: FC'ye MAVLink ile body FRD LOS gelir (montaj açısı dahil), FC bunu PWM'e kadar işler.
- `icdMsg` bir girdi paralelkenarına dönüşür: "Body FRD LOS (montaj açısı dahil), MAVLink ile gelir (ICD TBD)". Kesik çizgili TBD vurgusu korunur. Gerekirse paralelkenar şekli `tbd` stiliyle birleştirilir.
- Üslup korunur: paralelkenar = girdi, yuvarlak köşeli kutu = işlem, kesik çizgi = TBD. Siyah-beyaz kutular ve mavi oklar (`#4472c4`) aynı kalır. ECEF/WGS84 kutusu eklenmez.
- Yan girdiler korunur: "UAV Roll / Pitch / Yaw", "İrtifa (baro / EKF) — TBD", "UAV yerel NED konumu", "Pilot / QGC mod seçimi".

**Şema 1: daha detaylı FC akışı (sade dil)**
- Akış mevcut sürümden belirgin biçimde daha detaylı olur. Kullanıcı mevcut sürümü "çok basit" buldu. Yaklaşık 25–30 node hedeflenir.
- Eklenecek sade adımlar ve karar noktaları:
  - pilot / QGC ile moda giriş, mod anahtarıyla çıkış
  - "Mod aktif mi?" kararı (hayır → hesap yapılmaz)
  - "Gelen mesaj geçerli mi?" kararı (ad, sayı, birim vektör, tazelik sade dille, hayır → örnek atılır)
  - "Hedef görünüyor mu?" kararı (hayır → yerinde bekle, süre dolunca Hold)
- Ana zincir sade dille ve sırayla şöyle ilerler:
  - LOS'u yere göre yöne çevirme (NED)
  - aşağı açı ve eğik mesafe
  - hedefin yerel NED konumu
  - hedef kestirimi (konum/hız)
- Guidance parçalara ayrılır: istenen konum / takip mesafesi, istenen hız, yaw hedefe bakar, hız ve irtifa sınırları.
- Kontrol zinciri: konum kontrolü → tutum kontrolü → açısal hız kontrolü → motor karıştırma → PWM → ESC → motorlar → araç hedefi takip eder.
- Karar noktaları eşkenar dörtgenle çizilir. Lejant satırına "eşkenar dörtgen = karar" eklenir, gerekiyorsa `decision` `classDef` tanımı da eklenir (siyah-beyaz).
- PX4 topic adı, parametre adı ve ağır teknik terim kullanılmaz. Bu ayrıntılar yalnızca Şema 2'de yer alır. Guidance yasası ayrıntısı için `/home/yusuf/Desktop/guidance-yasalari.md` atfı korunur.
- Yeni her Şema 1 kutusu, Şema 2 (B)'deki bir node'a eşlenebilir olmalıdır (önceki K7-1 terim tutarlılığı kuralı).

**Şema 2: giriş metni, lejant ve açık konular tablosu**
- Giriş paragrafındaki "Pi'den gelen body FRD LOS" ifadesi şöyle yazılır: "FC'ye MAVLink ile gelen body FRD LOS". Paragrafa, zincirin MAIN PWM çıkışına kadar gösterildiği eklenir.
- Lejant katman tablosundan "Pi (Vision) | `Raspberry Pi (Vision)` | B" satırı silinir. Diğer satırlar değişmez.
- TBD #1 (ICD) kalır ve "FC'nin beklediği hedef LOS mesajı" olarak yeniden yazılır. "Pi → FC" ifadesi kaldırılır, kalan içerik (`DEBUG_VECT` aday, gösterim, hız, gecikme, zaman damgası, "hedef yok" sinyali) aynı kalır.
- Yeni satır #8 eklenir: "SITL'de LOS girdisi | Test sırasında FC'ye gelecek LOS mesajının SITL'de nasıl üretileceği. Sahte Pi adımı kullanıcı kararıyla silindi, ileride eklenebilir | D".
- TBD tablosu ↔ `tbd` node eşleme kuralı korunur. Uygulamadan sonra tabloda 8 satır, şemada da 8 `tbd` node'u bulunur.

**Şema 2 (B): Pi bloğunun kaldırılması ve FC giriş kutusu**
- `bPi` subgraph'ı (`bPiLos`, `bPiSend`, `bPiPort`) ve okları (`bPiLos→bPiSend`, `bPiSend→bPiPort`, `bPiSend-.-bIcd`, `bPiPort→bLinkHw`, `bPiPort→bLinkSitl`) silinir. `class` satırlarındaki referanslar da temizlenir.
- Yeni bir giriş paralelkenarı (`input`, örneğin `bLosIn`) eklenir: "Body FRD LOS (montaj açısı dahil), MAVLink ile TELEM2'den gelir (ICD TBD)".
- Giriş kutusu, FC'nin beklediği alanları listeler:
  - `DEBUG_VECT` aday
  - `name` en fazla 9 karakter (ör. "TEZ_LOS", öneri)
  - x/y/z = LOS_body birim vektör
  - FC montaj açısını bilmez
  - `time_usec` FC'de kullanılmaz
- Giriş kutusundan iki ok çıkar: biri `bLinkHw`'ye ("MAVLink DEBUG_VECT (seri, TELEM2)"), diğeri `bLinkSitl`'e ("MAVLink DEBUG_VECT (UDP, SITL)"). Giriş kutusu `bIcd`'ye noktalı çizgiyle bağlanır.
- `bLink` subgraph'ı aynen kalır: `bLinkHw`, `bLinkSitl` (local 14580 / remote 14540 PX4 tarafı ayarıdır, kalır), `bRecv`, `bIcd`, `bTsNote`, `bQueueNote`.
- Bu subgraph'taki Pi'ye atıflar nötr yazılır:
  - `bIcd` başlığı "TBD: ICD (FC'nin beklediği hedef LOS mesajı)" olur.
  - `bTsNote`'taki "görüntü yakalama anı" ifadesi "LOS ölçüm anı" gibi nötr bir ifadeye çevrilir. Anlam değişmez.
- Giriş metnindeki "Pi'den gelen LOS örneği" ifadesi "FC'ye gelen LOS örneği" olur. "Pi ve FC portları karıştırılmaz" maddesi yalnızca FC portunu anlatacak şekilde yeniden yazılır: "FC tarafı TELEM2 = `/dev/ttyS3`".

**Şema 2 (B): kontrolcü zincirinin MAIN PWM'e kadar uzatılması**
- Mevcut `bEsc` node'u ayrıntılı bir zincirle değiştirilir: `bAlloc` -- `actuator_motors` --> mixer_module `MixingOutput` / FunctionMotors (`THR_MDL_FAC`, varsayılan 0; [0,1] → [-1,1]).
- Çıkış sınırlama (`output_limit`) adımları:
  - armed değilse disarmed değeri kullanılır
  - normalde `PWM_MAIN_MIN`..`PWM_MAIN_MAX` (1000–2000 µs) arasına ölçeklenir
  - kill/lockdown durumunda `PWM_MAIN_DIS` (1000) kullanılır
  - termination durumunda `PWM_MAIN_FAIL` kullanılır (varsayılan -1: fonksiyonun varsayılan failsafe değeri, doğrulanacak)
- Ardından zincir şöyle ilerler:
  - px4io sürücüsü (`updateOutputs` → `PX4IO_PAGE_DIRECT_PWM`)
  - seri hat `/dev/ttyS4` (1.5 Mbps) → IO işlemcisi
  - MAIN 1–4 PWM 400 Hz (`PWM_MAIN_TIMx`, varsayılan 400)
  - ESC → motorlar → "araç hedefi takip eder"
- Yan çıkış: mixer_module, `actuator_outputs` topic'ini sürücü çağrısından sonra yayınlar (`note` ile ULog bağlantısı).
- Motor ataması notu: `PWM_MAIN_FUNC1..4 = 101..104` (Motor 1..4). Varsayılan 0 (Disabled). 4019_x500_v2 airframe bu ataması yapmaz, atama QGC Actuators sekmesinde elle yapılır. MAIN 1–4 ↔ motor sırası "(doğrulanacak)" etiketi alır.
- Yalnızca MAIN dalı çizilir. AUX / `pwm_out` / `dshot` dalı çizilmez. ESC'ler kullanıcı bilgisine göre MAIN portuna PWM ile bağlıdır.
- SITL yan notu (dal değil, `note`): `gz_bridge` aynı `MixingOutput`'u kullanır. Ayarlar `SIM_GZ_EC_FUNC1..4 = 101..104`, MIN 150 / MAX 1000. Çıkış PWM değil motor hızıdır.
- "(doğrulanacak)" notu: V6C10/V6C11 donanım sürümlerinde PX4IO yoktur. Kullanıcının kartında IO olduğu varsayılır.
- Yeni node'lar `bCtl` subgraph'ı ("FlightModeManager ve kontrolcüler") içinde veya hemen altındaki ayrı bir subgraph'ta (ör. "Çıkış: mixer_module ve px4io") yer alır. Mevcut palet kullanılır (`process`, `note`, `warn`).

**Şema 2 (B): Şema 1 eşleme tablosu, notlar ve kaynak satırları**
- Eşleme tablosundan Pi satırları (`bPiLos`, `bPiSend`) silinir. Bunların yerine "Body FRD LOS, MAVLink ile gelir (ICD TBD)" → yeni giriş kutusu, `bIcd`, MAVLink katmanı satırı eklenir.
- Yeni Şema 1 kutuları (B) node'larına eşlenir:
  - mesaj kontrolü → `bVecQ`, `bChkName`..`bChkFresh`, `bDrop`
  - mod aktif mi → `bGate`
  - hedef görünüyor mu → `bAgeQ`, `bLostRef`
  - guidance parçaları → `bGuid`, `bSat`, `bTraj`
  - konum / tutum / açısal hız kontrolü → `bPos`, `bAtt`, `bRate`
  - motor karıştırma → `bAlloc` ve mixer node'u
  - PWM → ESC → motorlar → yeni çıkış node'ları
- (B) notlarındaki "Pi tarafı `/dev/ttyAMA0` ve `udp:127.0.0.1:14540`: `agent-os/standards/python/companion.md:8`" cümlesi silinir.
- Mevcut "Kontrolcü zinciri" notundaki "(pwm_out, dshot ve gz_bridge `MixingOutput` kullanır)" ifadesi korunur. PWM zinciri için ayrı bir not maddesi eklenir.
- Yeni not maddesinin kaynak satırları:
  - mixer: `src/lib/mixer_module/mixer_module.cpp:440-575`, `:666-675`, `:117-131`, `:690-706`
  - FunctionMotors: `src/lib/mixer_module/functions/FunctionMotors.hpp:52-118`
  - motor fonksiyonları ve `THR_MDL_FAC`: `output_functions.yaml`, `motor_params.c:57`
  - px4io: `src/drivers/px4io/px4io.cpp:363-378`, `src/drivers/px4io/module.yaml`
  - kart: `boards/px4/fmu-v6c/src/board_config.h:59-72`, `:149-150`, `boards/px4/fmu-v6c/default.px4board:32`
  - başlatma: `ROMFS/px4fmu_common/init.d/rcS:414`, `ROMFS/px4fmu_common/init.d/airframes/4019_x500_v2`
  - parametre varsayılanları: `build/px4_fmu-v6c_default/parameters.xml` (`PWM_MAIN_FUNC1`, `PWM_MAIN_TIM0..2`, `PWM_MAIN_DIS1`, `PWM_MAIN_MIN1`, `PWM_MAIN_MAX1`, `PWM_MAIN_FAIL1`)
  - SITL: `ROMFS/px4fmu_common/init.d-posix/airframes/4001_gz_x500:35-48`
- Uygulama sırasında her kaynak satırı v1.17.0 kaynağına karşı grep ile yeniden doğrulanır. `build/` altındaki satır numaraları derlemeye bağlı olduğu için "(build çıktısı)" olarak işaretlenir.

**Şema 2 (D): sahte Pi adımının silinmesi ve yeniden numaralandırma**
- Silinecekler:
  - `dStep3` subgraph'ı ve başlığı
  - `dFakePi`, `dTruth`, `dPiQ`, `dPiFix` node'ları
  - ilgili oklar: `dBootQ→dFakePi`, `dTruth-.->dFakePi`, `dFakePi→dPiQ`, `dPiQ→dPiFix`, `dPiQ→dPick`, `dPiFix→dFakePi`
- `dRcSim`, `dQgc` ve `dFailNote` korunur ve `dScn` subgraph'ına (SITL senaryoları) taşınır. `dRcSim→dPick`, `dQgc→dPick` ve `dRcSim-.-dFailNote` bağlantıları kalır.
- `dBootQ`'nun "evet" kenarı doğrudan `dPick`'e bağlanır.
- Yeni bir `tbd` node'u (ör. `dLosTbd`) `dPick`'e noktalı çizgiyle bağlanır: "TBD: SITL'de LOS girdisinin nasıl üretileceği". Node, S2, S4 ve S5'in bu girdiye ihtiyaç duyduğunu belirtir.
- Adımlar yeniden numaralanır: Adım 1 GoogleTest → Adım 2 Gazebo Harmonic SITL → Adım 3 ULog + pyulog metrikleri (eski 4) → Adım 4 gerçek uçuş (eski 5). Subgraph id'leri başlıkla uyumlu olacak şekilde `dStep3` / `dStep4` olarak yeniden adlandırılır.
- Numara geçen her yer güncellenir:
  - giriş metnindeki "Sıra" maddesi
  - `dScn` başlığı ("Adım 2–4" → "Adım 2–3")
  - `dMetrics` ve `dFlight` etiketleri
  - senaryo tablosundaki "Adım 5" satırı ("Adım 4" olur)
  - "Başarısızlık" maddesi ve geri dönüş okları
- Uygulamadan sonra her karar node'unun "hayır" kenarı geçerli bir düzeltme veya geri dönüş hedefine gider. Silinen node'a giden kenar kalmaz. Kullanılmayan id ve `class` referansı da kalmaz.

**Şema 2 (D): Pi/Vision ifadelerinin nötrlenmesi**
- `dSc4`'teki "sahte Pi göndermeyi keser" ifadesi "LOS mesajı kesilir" olur. `dSc5`'teki "yanlış name'li DEBUG_VECT (ikinci gönderici)" ifadesi "ikinci kaynaktan yanlış name'li DEBUG_VECT" olur. Pi ya da test aracı adı geçmez.
- `dHwCfg` içinden "Pi 5 /dev/ttyAMA0 ↔ TELEM2, Vision kodu ICD'ye göre (ICD TBD)" satırı silinir. TELEM2, `extras.txt` ve SDLOG satırları kalır.
- `dFlight` içinden "+ Raspberry Pi 5" silinir. Etiket "X500 V2 + Pixhawk 6C" olur.
- Senaryo tablosunun gerçek uçuş satırındaki "Pi bağlantısı" yerine FC tarafı madde yazılır: "TELEM2'den LOS alımı (`debug_vect`)".
- (D) notlarındaki "Sahte Pi ve pilot simülasyonu" maddesi "Pilot simülasyonu" olur. Sahte Pi'ye ait onboard UDP atfı (`px4-rc.mavlink:4-5`, `:26`) çıkarılır. GCS, `RC_CHANNELS_OVERRIDE`, `COM_RC_IN_MODE` ve `RC_MAP_*` atıfları kalır.
- `dRcSim` pilot simülasyonu için pymavlink `RC_CHANNELS_OVERRIDE` kullanmaya devam eder. Bu kullanım Pi'ye ait değildir. "Sürümler" notundaki `pymavlink 2.4.50` satırı bu kullanım için korunur. Yalnızca sahte Pi'ye ait pymavlink ifadeleri silinir.
- `dUnitFn` içindeki "ICD doğrulama" (FC tarafı girdi doğrulaması) ve "Saat ve ground truth" not maddesi korunur. Ground truth, takip mesafesi metriği için hâlâ gereklidir.

**Doğrulama ve masaüstü çıktıları**
- Grep kontrolü yapılır: iki şema dosyasında `Raspberry`, `Vision`, `ttyAMA0`, `Sahte Pi`, `sahte Pi`, `bPi`, `piBox`, `dFakePi`, `dPiQ` geçmemeli. Tek istisna, dosya başındaki bu spec'e atıf notudur. `pymavlink` yalnızca `dRcSim`, (D) "Pilot simülasyonu" notu ve "Sürümler" satırında kalır.
- Her Mermaid bloğu önceki spec'in yöntemiyle (MPE Mermaid parse ve headless Chrome render) hatasız parse edilir ve render edilir.
- TBD tablosu (8 satır) ↔ `tbd` node sayısı (8) eşleşir. Şema 1 kutuları ↔ (B) eşleme tablosu eksiksizdir.
- Uygulamadan sonra masaüstündeki güncel sürümlerin üzerine yazılır. Eski sürüm ve `-fc` kopyası tutulmaz. Güncellenecek dosyalar (`/home/yusuf/Desktop/hedef-takip-ciktilari/` altında):
  - `01-ust-seviye-akis.md`
  - `01-ust-seviye-akis.pdf`
  - `02-px4-detayli-akis.md`
  - `02-px4-detayli-akis.pdf`
- PDF dönüşümünü uygulamadan sonra orkestratör, önceki PDF yöntemiyle yapar. Masaüstündeki `1-ad-envanteri.*`, `7-son-gozden-gecirme.*` ve `referans-gorsel.jpeg` dosyalarına dokunulmaz.
- Masaüstü `.md` kopyaları, önceki seferdeki gibi repo dosyasının birebir kopyasıdır. Şema 1'deki göreli referans görsel bağlantısı masaüstünde çözülmez. Bu durum önceki kopyada da vardı ve bu spec'te değiştirilmez.

## Visual Design

**`agent-os/specs/2026-10-15-m15-target-follow-flight-mode/planning/visuals/WhatsApp Image 2026-09-26 at 00.07.13.jpeg`** (bu spec'in `planning/visuals/` klasörü boş, üslup referansı önceki spec'teki bu görseldir)
- Yalnızca şekil dili alınır, görsel birebir kopyalanmaz.
- Girdiler paralelkenar, işlemler yuvarlak köşeli kutu olarak çizilir.
- Tek sütunlu ana zincir yukarıdan aşağı akar. Yan girdiler ana zincire yatay okla bağlanır.
- Kutular siyah-beyazdır, oklar mavidir.
- Bu spec'te karar noktaları için eşkenar dörtgen eklenir ve lejantta gösterilir.
- Düşük ayrıntılı bir üslup örneğidir. Şema 1 bundan daha çok adım içerir, ama aynı sadelikte kalır.

## Existing Code to Leverage

**Mevcut iki şema dosyası (güncellenecek)**
- Önceki spec'teki `diagrams/01-ust-seviye-akis.md` ve `diagrams/02-px4-detayli-akis.md` dosyaları temel alınır. Yalnızca bu spec'te listelenen değişiklikler yapılır.
- Şema 2'deki `classDef` paleti (`input`, `process`, `decision`, `tbd`, `note`, `warn`, `ref`), `linkStyle default`, lejant tabloları ve blok başına "notlar ve kaynak satırları" düzeni korunur.

**Önceki spec'in yazım kuralları ve kontrolleri**
- `tasks.md` "Genel kurallar" bölümü (tırnaklama, ASCII id, kaçış dizileri, etiketler) aynen uygulanır.
- `implementation/7-son-gozden-gecirme.md` K7-1 (terim tutarlılığı), K7-2 (TBD tablosu ↔ `tbd` node), K7-8 (repo yolları mevcut), K7-9 (MPE parse) ve K7-10 (branch / `git status`) kontrolleri bu değişiklik için tekrar kullanılır.

**PX4 v1.17.0 çıkış zinciri kaynağı**
- `src/lib/mixer_module/` (`MixingOutput`, `FunctionMotors`, `output_limit`, `actuator_outputs` yayını) motor karıştırmadan sonraki ölçekleme ve sınırlama adımlarının kaynağıdır.
- `src/drivers/px4io/` ve `boards/px4/fmu-v6c/` kaynakları `PWM_MAIN` öneki, 400 Hz varsayılanı, DShot olmaması, `/dev/ttyS4` IO hattı ve IO'suz V6C10/V6C11 sürümleri için kullanılır.

**Ad envanteri**
- `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/implementation/1-ad-envanteri.md` mevcut (B) adlarının kaynağı olarak okunur, değiştirilmez. Yeni PWM adları bu spec'te kaynak satırlarıyla doğrulanır.

**Önceki PDF ve render yöntemi**
- Önceki spec'te masaüstü PDF'lerini üreten yöntem (MPE Mermaid ve headless Chrome), orkestratör tarafından aynı şekilde tekrar kullanılır.

## Out of Scope
- Vision / Raspberry Pi tarafının tamamı: kamera, insan tespiti, piksel → kamera → body LOS, Pi'de gönderim, Pi seri portu, Pi'den pymavlink ile gönderim.
- Önceki spec'te iki şema dosyası dışındaki her dosyanın değiştirilmesi (`spec.md`, `tasks.md`, `planning/`, `implementation/`, `orchestration.yml`).
- AUX çıkışları, `pwm_out` ve DShot çıkış dalı.
- SITL çıkış yolunun (`gz_bridge`) tam bir dal olarak çizilmesi. Bu yol yalnızca yan nottur.
- (A) ve (C) bloklarında, mevcut TBD'lerde, notlarda, kaynak satırlarında, renklerde ve şekillerde Pi'ye atıf düzeltmesi dışında değişiklik.
- SITL LOS test vericisi (eski "sahte Pi" adımı). Kullanıcının kararı yok, yalnızca TBD olarak işaretlenir.
- `tez_follow` kodu, `module.yaml`, GoogleTest ve SITL testleri (sonraki spec).
- Masaüstündeki `1-ad-envanteri.*`, `7-son-gozden-gecirme.*` ve `referans-gorsel.jpeg` dosyalarının güncellenmesi.
- Branch değişikliği, commit, Vision reposunda değişiklik, upstream PX4 dosyalarında değişiklik.
