# Task Group 6: Çapraz Tutarlılık, Kapsam ve Sözdizimi Kontrolü

Tarih: 2026-10-18. Branch `yusuf/agent-os-denemeleri-ve-sema-olusturma`, commit atılmadı.

`S=/tmp/claude-1000/-home-yusuf-Desktop-Projects-Auto-Follow-Autopilot/4b91b3e4-86c9-4515-ad60-66129800d8c8/scratchpad`

## 1. Özet

- İki şema birlikte gözden geçirildi. Spec'in istediği bütün değişiklikler yerinde, kapsam dışı bir değişiklik yok.
- Bu grupta yalnızca Şema 1'de iki küçük metin düzeltmesi yapıldı (bkz. bölüm 2). Şema 2'ye bu grupta dokunulmadı.
- Task Group 6 kontrolleri: **114 PASS, 0 FAIL**. Beş Mermaid bloğunun hepsi MPE ile `PARSE OK`, headless Chrome ile `syntax-error-markers=0`.
- Grup 1–5 kontrolleri yeniden çalıştırıldı. Kalan FAIL'lerin hepsi, sonraki grupların değişikliğinden önce alınmış ara kopyalarla yapılan zaman sıralı karşılaştırmalardır. Gerçek hata değildirler (bkz. bölüm 4.2).
- Kullanıcı kararı gereken dört konu var (bkz. bölüm 9). En önemlisi ground truth (insan konumu) kaydının şemadan düşmesi.

## 2. Bu grupta yapılan düzeltmeler

Yalnızca `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/diagrams/01-ust-seviye-akis.md` değişti.

| Satır | Önce | Sonra | Gerekçe |
|---|---|---|---|
| 3 (başlık notu) | "... metinleri Pi'yi ve Şema 2 (D) bloğunun 5 adımlı eski akışını anlatmaya devam eder." | "... metinleri Pi'yi ve Şema 2'nin 5 adımlı (D) akışını anlatmaya devam eder." | İki dosyanın notu aynı kalıba getirildi. Şema 2'deki not "5 adımlı (D) akışını" der. Şema 1'de yalnızca "Şema 2'nin" eki kaldı, çünkü Şema 1'de (D) bloğu yok. |
| 5 (giriş paragrafı) | "FC'ye MAVLink ile body FRD LOS gelir (kamera montaj açısı dahil), ..." | "FC'ye MAVLink ile body FRD LOS gelir (montaj açısı dahil), ..." | Spec, paragrafın bu cümleyle birebir başlamasını istiyor. 6.6 kapsam listesi "kamera"yı Vision tarafı terimi sayıyor. `icdMsg` ve `bLosIn` etiketleri de "(montaj açısı dahil)" diyor. |

Düzeltmeden sonra iki dosyanın tüm blokları yeniden parse ve render edildi. Grup 5 kontrolleri tekrar çalıştırıldı ve hepsi geçti.

## 3. Şemalarda neler değişti (Grup 2–6 toplamı)

### Şema 1 (`01-ust-seviye-akis.md`)

- Pi kutusu (`piBox` ve dört node) silindi. Başlığın altına bu spec'e atıf yapan not eklendi.
- Giriş paragrafı FC'nin bakış açısından yeniden yazıldı. Lejanta "eşkenar dörtgen = karar" eklendi. Eşleme tablosuna atıf eklendi.
- `icdMsg` artık girdi paralelkenarıdır ("Body FRD LOS (montaj açısı dahil), MAVLink ile gelir (ICD TBD)"). Kesik çizgili `tbd` stili korundu.
- Akış 16 node'dan 30 node'a çıktı (hedef 25–30). Moda giriş ve mod anahtarıyla çıkış eklendi. Üç karar eklendi: "Mod aktif mi?", "Gelen mesaj geçerli mi?" ve "Hedef görünüyor mu?". Bunların "hayır" dalları "Hesap yapılmaz", "Örnek atılır" ve "Yerinde bekle → Süre dolunca Hold" kutularına gider.
- Ana zincir sade dille ilerler: LOS'u NED'e çevirme → aşağı açı ve eğik mesafe → hedefin yerel NED konumu → hedef kestirimi. Guidance alt kutusunda dört parça var. "PX4 kontrolcüleri" alt kutusunda konum, tutum ve açısal hız kontrolü ile motor karıştırma var. Zincir PWM → ESC → Motorlar → Araç hedefi takip eder şeklinde biter.
- Renkler, `linkStyle default` (`#4472c4`) ve mevcut `classDef`'ler değişmedi. Siyah-beyaz bir `classDef decision` eklendi.

### Şema 2 (`02-px4-detayli-akis.md`)

- **Ortak:** Başlık notu eklendi. Giriş paragrafı "FC'ye MAVLink ile gelen body FRD LOS" diye değişti ve "MAIN PWM çıkışına kadar" ifadesi eklendi. Lejanttan "Pi (Vision)" satırı silindi. TBD #1 "FC'nin beklediği hedef LOS mesajı" olarak yeniden yazıldı. TBD #8 eklendi.
- **(B) giriş:** `bPi` subgraph'ı ve okları silindi. Yeni girdi paralelkenarı `bLosIn` beş alanı listeler. `bLinkHw` ve `bLinkSitl`'e etiketli oklarla, `bIcd`'ye noktalı çizgiyle bağlanır. `bIcd` başlığı ve `bTsNote` nötr yazıldı. Giriş metni ve port maddesi düzeltildi. (B) notlarından Pi cümlesi silindi.
- **(B) çıkış:** `bEsc` silindi. `bCtl` içinde yeni `bOut` subgraph'ı ("Çıkış: mixer_module ve px4io") var. Zincir şöyle ilerler: `bAlloc` -- `actuator_motors` --> `bMix` → `bLimQ` (dört durum: kill/lockdown, termination, armed değil, normal) → `bLimDis` / `bLimFail` / `bLimOn` → `bIoDrv` → `/dev/ttyS4` → `bIoMcu` → `bMainPwm` → `bOutEsc` → `bMotors` → `bFollow`. Dört `note` eklendi: motor ataması, SITL `gz_bridge`, V6C10/V6C11 ve `actuator_outputs` → ULog. (B) notlarına "PWM zinciri" maddesi eklendi. "Kontrolcü zinciri" maddesi değişmedi.
- **(B) eşleme tablosu:** 32 satır. Şema 1'in 30 kutusu ve 2 alt kutusu birebir aynı etiketlerle yazıldı. Pi satırları ve `bEsc` kaldırıldı. Moda giriş, mod anahtarıyla çıkış, yerinde bekleme ve Hold satırları (C) bloğuna yazılı atıf verir.
- **(D):** Sahte Pi adımı (`dStep3`, `dFakePi`, `dTruth`, `dPiQ`, `dPiFix`) silindi. `dRcSim`, `dQgc` ve `dFailNote` `dScn`'ye taşındı. `dBootQ` "evet" kenarı artık `dPick`'e gider. `dLosTbd` eklendi. Adımlar 1–4 olarak yeniden numaralandı. Senaryo, donanım ve not ifadeleri nötr yazıldı.
- **Değişmeyenler:** (A) ve (C) blokları ile notları, "Şekiller ve renkler" ve "Ad etiketleri" tabloları, TBD #2–#7 ve render edilmeyen yorum bloğu baseline ile byte düzeyinde aynıdır.

## 4. Kontrol sonuçları

### 4.1 Task Group 6 (6.2–6.7)

Betik `$S/tg6/tg6_checks.py`, çıktısı `$S/tg6/tg6_checks.out`. Parse ve render betiği `$S/tg6/parse_render.sh`, çıktısı `$S/tg6/post-parse-render.out`. Sonuç: **114 PASS, 0 FAIL**.

| Kontrol | Sonuç |
|---|---|
| 6.2 Grep: `Raspberry`, `Vision`, `ttyAMA0`, `Sahte Pi`, `sahte Pi`, `bPi`, `piBox`, `dFakePi`, `dPiQ` (ek: `dTruth`, `dPiFix`, `udp:127.0.0.1:14540`, `ikinci gönderici`) | İki dosyada da yok. Başlık notunda da yok |
| 6.2 Bütün kelime `Pi` | İki dosyada da yalnızca 3. satırda (başlık notu) |
| 6.2 `pymavlink` | Yalnızca `dRcSim` ve "Sürümler" satırında var. "Pilot simülasyonu" notunda baseline'da da yoktu |
| 6.3 (A) ve (C) blokları ve notları, iki lejant tablosu, TBD #2–#7, yorum bloğu | Baseline ile byte düzeyinde aynı |
| 6.3 Katmanlar tablosu | Baseline'dan yalnızca "Pi (Vision)" satırı eksik |
| 6.3 Diff kapsamı | Değişen satırlar yalnızca spec'in değiştirdiği bölümlerde: başlık ve giriş, Katmanlar, TBD tablosu, (B) girişi ve eşleme tablosu, (B) bloğu, (B) notları (Donanım ve PWM zinciri), (D) girişi (Sıra ve Adım 4 satırı), (D) bloğu, (D) notları (Pilot simülasyonu) |
| 6.4 TBD tablosu ↔ `tbd` node (K7-2) | 8 satır ↔ 8 node: `aPre`, `bIcd`, `bAltTbd`, `bGuidTbd`, `bSpTbd`, `cTimeTbd`, `dPerson`, `dLosTbd`. Her satırın blok sütunu node'un bloğuyla uyuşuyor. #1 ↔ `bIcd` ve #8 ↔ `dLosTbd` aynı ifadeyi kullanıyor. Şema 1'deki `icdMsg` ve `inAlt` sayıma girmez |
| 6.4 Şema 1 ↔ (B) eşleme (K7-1) | Şema 1'in 30 kutu ve 2 alt kutu etiketinin her biri sol sütunda tam bir kez geçiyor. Sağ sütundaki her `b...` id'si (B) bloğunda var. Zincirin uç node'larının hepsi eşlenmiş |
| 6.5 Repo yolları (K7-8) | Şema 2 metnindeki 121 repo yolu mevcut. Bütün `yol:satır` ve devam eden `:satır` atıfları dosya uzunluğu içinde. Tek istisna önceden kalmadır (bkz. bölüm 9.4). Yeni PWM atıflarının içeriği ayrıca `sed -n` ile kontrol edildi |
| 6.5 MPE parse (K7-9) | Şema 1: 1 blok `PARSE OK`, 30 node / 31 kenar. Şema 2: (A) 47/56, (B) 68/88, (C) 61/73, (D) 46/59, hepsi `PARSE OK`. Çıkış kodu 0 |
| 6.5 Headless Chrome render | Beş blok `OK`, `syntax-error-markers=0` |
| 6.5 `mmd_check.py` | Şema 2'nin dört bloğunda 0 hata. Şema 1'de 6 bulgu var, hepsi bilinen yanlış pozitif (3 × `direction TB`, 3 × `style`) |
| 6.5 Elle kontrol listesi | Etiket içinde çıplak `"` yok. Id'ler ASCII, benzersiz ve blok harfiyle başlıyor. `subgraph`/`end` dengeli. İndeksli `linkStyle` yok. `class` satırları yalnızca tanımlı node'lara atıf yapıyor ve her node bir sınıf almış. Örtük node (silinmiş id'ye giden kenar) yok. Kenarsız node yok |
| 6.6 Kapsam | Hiçbir dosyada kamera, görüntü, tespit, piksel geçmiyor. Mermaid bloklarında AUX, `pwm_out` ve `dshot` yok. (B)'de `gz_bridge` yalnızca `bSitlNote` notunda geçiyor ve bu notun çıkan oku yok. Bloklarda ECEF/WGS84 yok, Şema 1'de hiç yok. SITL LOS vericisi yalnızca `dLosTbd` olarak var. Şema 1'de topic veya parametre adı yok |
| 6.7 Ek kontroller (E1–E8) | E1–E2: iki dosyadaki her karar node'unun en az iki dalı var ve dalların hepsi etiketli. E3: Şema 1'de `icdMsg`'den `fcFollow`'a düz oklarla üç karar üzerinden gidiliyor. E4: (B)'de `bLosIn`'den `bFollow`'a düz oklarla `actuator_motors`, mixer, px4io ve MAIN PWM üzerinden gidiliyor (üçüncü user story). E5: Şema 1'in yalnızca üç bilinçli bitişi var. E6: iki başlık notu uyumlu. E7: (D)'de yalnızca 1–4 numaralı adımlar geçiyor, "sahte" kelimesi yok. E8: "Saat ve ground truth" notu duruyor (boşluk için bkz. bölüm 8) |

### 4.2 Grup 1–5 kontrollerinin yeniden çalıştırılması (6.1, 6.8)

| Grup | Sonuç | Açıklama |
|---|---|---|
| TG1 K1–K5 (`$S/tg1_checks.sh`) | 106 PASS, 2 FAIL | FAIL: K1 `cmp` repo == baseline. Dosyalar bu spec'te bilerek değiştirildi, beklenen sonuç. K2–K5 (kaynak satırları ve parametre varsayılanları) geçti |
| TG2 K1–K8 (`$S/tg2_checks.py`) | 33 PASS, 1 FAIL | FAIL: "K7 notes otherwise unchanged". Nedeni TG3'ün eklediği "PWM zinciri" maddesi. O madde çıkarılınca (B) notları baseline ile birebir aynı |
| TG3 K1–K8 (`$S/tg3_checks.py`) | 28 PASS, 4 FAIL | K1–K8 içeriği geçti. FAIL'ler TG3 öncesi kopyaya göre kapsam kontrolleri. TG4 (D)'yi, TG5 eşleme tablosunu değiştirdi ve son `bEsc` satırını kaldırdı. Beklenen sonuç |
| TG4 K1–K8 (`$S/tg4/tg4_checks.py`) | 43 PASS, 1 FAIL | FAIL: TG4 öncesi kopyaya göre "(D) öncesi" kapsamı. Fark yalnızca TG5'in eşleme tablosu ve #8 ifadesi (elle diff ile teyit edildi) |
| TG5 K1–K8 (`$S/tg5/tg5_checks.py`) | 9/9 PASS | Bu gruptaki Şema 1 düzeltmesinden sonra da geçti |

Önceki spec'in `k7_check.py` betiği eski Şema 1 id'lerine (`fcGuidance` vb.) bağlı olduğu için çalışmadı. Kullanılan K7-1, K7-2, K7-8, K7-9 ve K7-10 kontrolleri `tg6_checks.py` içinde yeniden yazıldı. Yeniden çalıştırma çıktıları `$S/tg6/rerun-tg*.out` altındadır.

## 5. Spec'ten sapmalar

1. **TBD #8 ve `dLosTbd` ifadesi:** Spec ve `tasks.md` "Sahte Pi adımı kullanıcı kararıyla silindi" diyor. Şemada "Eski SITL LOS gönderim adımı kullanıcı kararıyla silindi, ileride eklenebilir" yazıyor. Bu orkestratör kararıdır, çünkü kullanıcı şemalarda Pi ifadesi kalmasını istemiyor. `spec.md` ve `tasks.md` eski metni alıntılamaya devam ediyor. Grep kontrolü yalnızca şema dosyalarına uygulanır.
2. **PWM zinciri kaynak aralıkları** (1.6 gereği bildirilir): Spec'teki aralıklar yanlış değil, TG1 hepsini doğruladı. TG3 bunları fonksiyon sınırlarına göre genişletti ve alt satırlarını yazdı.
   - `mixer_module.cpp:440-575` → `:421-576` (alt satırlar `:460-464`, `:491-495`, `:497-501`, `:505`, `:527-529`, `:535-576`)
   - `:666-675` → `:666-676`
   - `:690-706` → `:691-710`
   - `FunctionMotors.hpp:52-118` → `:52-120`
   - Ek atıflar: `output_limit_calc` `:578-663` (500 ms ramp ve OFF durumu), `px4io.cpp:227`, `manifest.c:89-100` ve `:108-109`, `px4iofirmware/registers.c:186-193`, `px4iofirmware/mixer.cpp:122-127` ve `:230-234`, `FunctionProviderBase.hpp:64`, `mixer_module.hpp:244`, `logged_topics.cpp:162`, gz_bridge `GZMixingInterfaceESC.*`
   - `parameters.xml` satırları "(build çıktısı)" etiketlidir
3. **(B)'de spec'te olmayan ama kaynakla doğrulanmış ayrıntılar:**
   - arm sonrası 500 ms ramp
   - fonksiyonu atanmamış kanala 0 yazılması
   - reversible olmayan motorda negatif değer → NAN
   - `PWM_MAIN_TIM0` (MAIN 1-2) ve `PWM_MAIN_TIM1` (MAIN 3-4) ayrımı
   - `PWM_MAIN_FAIL` = -1'in motorlarda disarmed değere düşmesi ("(doğrulanacak)" etiketiyle)
4. **Lejant ve `bOut`:** Yeni iç içe `bOut` subgraph'ı Katmanlar tablosuna eklenmedi. Gerekçe:
   - Tablo yalnızca üst katmanları listeler. (D)'deki iç içe `dStep1..4` ve `dScn` de tabloda yok.
   - `bOut`, tabloda bulunan "FlightModeManager ve kontrolcüler" katmanının içindedir.
   - Spec "Diğer satırlar değişmez" diyor.
   - Değişiklik gerekmedi.
5. **Şema 1 başlık notu ve giriş cümlesi:** Bu grupta spec metnine yaklaştırıldı (bölüm 2).

## 6. Kalan "(doğrulanacak)" maddeleri

**Bu spec'le gelen (PWM zinciri, (B)):**

- V6C10 / V6C11 donanım sürümlerinde PX4IO yoktur. Kullanıcının kartında IO olduğu varsayılır (`bIoNote`).
- MAIN 1–4 ↔ motor sırası (`bFuncNote`).
- `PWM_MAIN_FUNC1..4 = 101..104` atamasının QGC Actuators sekmesinde elle yapılması (`bFuncNote`).
- `PWM_MAIN_FAIL` = -1'in motorlarda disarmed değerine düşmesi (`bLimFail`). Kaynak bunu destekliyor, ama donanımda kanıtlanmadı.

**Önceki spec'ten kalan:** Şema 2'de "(doğrulanacak)" etiketi taşıyan 25 node var. Bunlardan 22'si önceki spec'ten kalır (yeni olanlar `bLimFail`, `bFuncNote`, `bIoNote`):

- (A): `aStartSitl`, `aStartHw`, `aSkel`, `aUnregDefer`
- (B): `bLinkHw`, `bMsgNote`
- (C): `cQgcSel`, `cOvNote`, `cRclAct`, `cUnresp`, `cFsClear`, `cHoldCmd`
- (D): `dSitl`, `dTarget`, `dQgc`, `dFailNote`, `dSc2`, `dSc4`, `dSc5`, `dSc6`, `dLogNote`, `dHwCfg`

Şema 1'de "(doğrulanacak)" yok.

## 7. Açık konular (TBD), 8 adet

| # | Konu | Node | Blok |
|---|---|---|---|
| 1 | ICD (FC'nin beklediği hedef LOS mesajı) | `bIcd` | B |
| 2 | Yükseklik kaynağı | `bAltTbd` | B |
| 3 | Nihai guidance yasası | `bGuidTbd` | B |
| 4 | Setpoint tipi | `bSpTbd` | B |
| 5 | Ön koşul onayı (`allowed-paths.txt`) | `aPre` | A |
| 6 | Süre parametreleri | `cTimeTbd` | C |
| 7 | Hareketli insan modeli ve tez dünyası | `dPerson` | D |
| 8 | SITL'de LOS girdisi (yeni) | `dLosTbd` | D |

Şema 1'deki `icdMsg` (ICD) ve `inAlt` (irtifa) kesik çizgili kutuları Şema 2'deki #1 ve #2'nin sade karşılıklarıdır.

## 8. Ground truth boşluğu

- Silinen `dTruth` node'u SITL'de ground truth kaydını anlatıyordu. Araç için `vehicle_local_position_groundtruth` ve `vehicle_attitude_groundtruth` kaydediliyordu. İnsan pozu Gazebo'dan ayrı bir script ile kaydediliyordu (öneri), ENU → NED dönüşümü ve saat eşleşmesi de bu node'daydı.
- `dMetrics` hâlâ insanın konumuna ihtiyaç duyar:
  - "takip mesafesi hatası: yatay mesafe (araç, insan)"
  - "yaw hatası: heading - hedefe kerteriz açısı"
- Şu anda bunu yalnızca (D) notlarındaki "Saat ve ground truth" maddesi karşılıyor (`GZBridge.cpp:331-346`, `logged_topics.cpp:230-242`). Bu madde PX4 saatini ve aracın ground truth topic'lerini anlatır. **İnsan pozunun nasıl kaydedileceği artık hiçbir node'da ve notta yazmıyor.**
- `tasks.md` yeni node istemediği için bu grupta node eklenmedi. Boşluk `dLosTbd` ile ilişkilidir, çünkü SITL'de LOS üretmek için de insan pozu gerekir. Karar için bkz. bölüm 9.1.

## 9. Kullanıcı kararı gereken konular

1. **İnsan pozu / ground truth kaydı (bölüm 8):** Üç seçenek var:
   - (a) (D)'de Adım 3'e veya `dLosTbd`'ye bağlı bir "insan pozu kaydı (öneri)" node'u ya da not maddesi eklenir.
   - (b) TBD #8'in kapsamı "SITL'de LOS girdisi ve insan pozu kaydı" olarak genişletilir.
   - (c) Konu sonraki spec'e (testler) bırakılır.
2. **Yeni "(doğrulanacak)" maddelerinin (D)'ye bağlanması:** (D) giriş metni "(A), (B) ve (C) bloklarında (doğrulanacak) kalan maddeler S1–S7 senaryolarına dağıtılmıştır" diyor. Bu spec'le (B)'ye gelen dört donanım maddesi hiçbir senaryoya, yer testine (`dBench`) veya "Adım 4" tablo satırına bağlanmadı: IO varlığı, MAIN 1–4 ↔ motor sırası, QGC Actuators ataması ve `PWM_MAIN_FAIL`. Spec (D) için bu değişikliği listelemediğinden 6.3 kapsamı gereği dokunulmadı. Öneri: `dBench` ve "Adım 4" satırına "QGC Actuators motor testi: MAIN 1–4 ↔ motor sırası ve yönü, PX4IO varlığı" eklenmesi.
3. **Şema 1'de "Yerinde bekle" sadeleştirmesi:** Şema 1'de "Yerinde bekle → Süre dolunca Hold" kolu kontrol zincirine bağlanmıyor. (B)'de ise tutma setpoint'i `bLostRef -.-> bTraj` ile kontrolcülere gider. Sade gösterim için kabul edilebilir. İstenirse "Yerinde bekle"den "Konum kontrolü"ne bir ok eklenebilir. Node sayısı değişmez.
4. **Önceden kalan küçük hata, (C) notları:** "RC yolu" maddesindeki `src/modules/commander/module.yaml:5-60` aralığı dosya uzunluğunu (52 satır) aşıyor. `COM_MODE${i}_HASH` `:5`'te, `COM_FLTMODE${i}` `:18`'de başlıyor, doğru aralık `:5-52` olmalı. Bu spec (C) bloğunun ve notlarının değişmemesini istediği için düzeltilmedi. Önceki spec'in metnidir.

## 10. Repo hijyeni (K7-10)

- `git branch --show-current`: `yusuf/agent-os-denemeleri-ve-sema-olusturma`. HEAD `503566a6bc`, commit atılmadı.
- `git status --short`: yalnızca `?? agent-os/specs/`. İzlenen dosyalarda değişiklik yok.
- `find agent-os/specs/2026-10-15-m15-target-follow-flight-mode -newer $S/baseline-fc/02-px4-detayli-akis.md -type f` (referans mtime 2026-10-18 15:40:41 +0300) yalnızca iki şema dosyasını listeliyor. Önceki spec'in diğer dosyaları değişmedi.
- Bu spec klasörüne yalnızca bu rapor eklendi ve `tasks.md` güncellendi.
- Masaüstü kopyaları ve PDF'ler Task Group 7'de orkestratör tarafından güncellenecek, bu grupta dokunulmadı.
