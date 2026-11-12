# Son doğrulama raporu: AUTO FOLLOW (M15)

- **Spec:** `2026-11-08-m15-takip-kodu` · issue Auto-Follow/Auto-Follow#6 · yol haritası m15 (m13, m16'ya da değiyor)
- **Tarih:** 2026-11-12
- **Doğrulayan:** implementation-verifier (Claude)
- **Repo / dal / commit:** Autopilot · `ozellik/m15-takip-kodu` · doğrulanan kod `8a0f27a86d` (2026-11-12 22:31)
- **Genel durum:** **Geçti, notlarla.** Kod, testler, derlemeler ve SITL kanıtları tamam ve birbiriyle tutarlı. Açık kalanlar kod dışı: repo sorumlusu onayı (bu olmadan CI'daki `verify-pin` kırmızı kalır), Vision'ın cevapları, kamera eğimi. Ayrıca dokümanlarda birkaç eskimiş cümle bulundu; hiçbiri koddaki bir değeri yanlış göstermiyor (Bölüm 5).

> Bu doğrulamada kod değiştirilmedi, karar verilmedi, `tez/pin/allowed-paths.txt`'e dokunulmadı, SITL yeniden çalıştırılmadı, masaüstündeki loglar yalnızca okundu. `tasks.md`'de tek bir işaret düzeltildi (Bölüm 1).

---

## Özet (sade dille)

AUTO FOLLOW modu PX4'e eklenmiş, iki hedefte de (bilgisayardaki simülasyon ve Pixhawk 6C) uyarısız derleniyor ve Pixhawk'ın belleğine sığıyor: **1 937 316 B, %98,54**. Bu, beklenen sayının tam kendisi. Kısa birim testinin **12 testinin 12'si geçti**. PX4'ün bütün test takımı da çalıştırıldı: hata yok. Python script'leri biçim ve kod kontrolünden temiz geçti.

Kilit kontrolü beklendiği gibi kırmızı. Gösterdiği 15 dosyanın hepsi, onay bekleyen 7 yolun içinde. Bunların dışında değişmiş bir PX4 dosyası yok.

Kodla dokümanlar arasında karşılaştırılanlar: 17 parametre (adı, varsayılanı, birimi, aralığı), 39 log alanı ve 14 sabit. Spec, sözlük ve kod bunların hepsinde aynı.

Dokümanlarda geçen 29 ULog'un 29'u da `~/Desktop/AUTO-FOLLOW LOG/` klasöründe duruyor. İki log analiz script'iyle yeniden ölçüldü ve notlardaki sayılar aynen çıktı.

---

## 1. Görev listesi (`tasks.md`) durumu

**Durum:** Grup 1–6 tamam. Grup 0'ın açık maddeleri beklenen dış işler.

| Grup | Ne | Durum |
|---|---|---|
| 0 | Ön koşullar (kod yok) | 0.5 bitti (bu doğrulamada işaretlendi). 0.0, 0.1, 0.2, 0.3, 0.4 ve 0.6 açık; nedenleri aşağıda |
| 1 | İskelet, mod kaydı, arming check, açılışta başlatma | 1.0–1.14 hepsi `[x]` |
| 2 | Doğrulama, geometri, filtre, guidance, setpoint, log mesajı | 2.0–2.17 ve 2.L1–2.L6 `[x]`. 2.LF açık; bu beklenen durum, aşağıda |
| 3 | Kısa birim testi | 3.0–3.6 `[x]` |
| 4 | SITL ön kontroller, S1a–S5 | 4.0–4.14 `[x]` |
| 5 | Hold geçişi, S4 tam, yaw sınırı, sıra no kuralı | 5.0–5.11 ve 5.A–5.C `[x]` |
| 6 | Analiz script'i, S6–S7, T1–T2, kapanış | 6.0, 6.5, 6.8–6.18, 6.T1 ve 6.T2 `[x]`. 6.1–6.4, 6.6 ve 6.7 numaralı madde yok; log mesajı Grup 2'ye taşınınca numaralar boş kaldı |

**Bu doğrulamada yapılan tek düzeltme:** **0.5** `[x]` yapıldı. Bu madde, kaynaklarda olmayan adların ve değerlerin kullanıcıya sorulmasını istiyordu. Hepsi sorulmuş ve karar günlüğüne yazılmış:

- test göndericisinin seçenek adları ve 20 Hz / 50 ms değerleri: `planning/karar-gunlugu.md`, "Düzeltme turu sonrası (2026-11-10)", geçici karar;
- analiz script'inin kullanım biçimi: "Görev grubu 6 öncesi sorular", soru 1;
- grup notlarının yeri: tasks'ta "karar verildi" diye yazıyor.

**Açık kalanlar ve neden açık oldukları (hepsi beklenen):**

| Madde | Neden açık |
|---|---|
| 0.1 7 yol talebi | Talebi ajan değil kullanıcı iletir. `implementation/grup-0-on-kosullar.md`'de durum yalnızca "Bekliyor" yazıyor; talebin Hüseyin'e **gerçekten gönderilip gönderilmediği** kayıtlı değil. Kullanıcıya sorulmalı |
| 0.2 Hüseyin'in cevabı | Cevap henüz yok |
| 0.3 Vision ile `AF_LOS` anlaşması | 9 soru 2026-11-10'da soruldu, cevap yok (grup-0 notu) |
| 0.4 Kamera eğimi (Ahmet, m06) | Bekleniyor. SITL'de `AF_TRK_ANG` = 30° |
| 0.6 Ön koşul cevaplarının commit'i | 0.2, 0.3 ve 0.4'ün cevaplarına bağlı |
| 0.0 | Alt maddeleri bitmediği için açık |
| 2.LF Geri dönüş | Yalnızca Hüseyin log yollarını reddederse yapılacak. Ret olmadığı için yapılmaması doğru |

---

## 2. Kabul kriterleri (spec "Kabul kriterleri", issue #6 kriterleri 1–6)

| # | Kriter | Sonuç | Kanıt |
|---|---|---|---|
| 1 | Spec klasöründe şemalar var | **Karşılandı** | `planning/visuals/01-ust-seviye-akis.md`, `02-px4-detayli-akis.md` (5 Mermaid şeması). Not: `02`'de birkaç eski ifade kaldı (Bölüm 5, madde 10) |
| 2 | PX4'te neyin nereye bağlandığı ve neden yazılmış | **Karşılandı** | `spec.md` Bölüm 1–9 (PX4 kaynağına `dosya:satır` gösterimleriyle), `rapor.md` §4.1–4.10, §7 |
| 3 | Her senaryo için "ne verildi, drone ne yaptı, ULog adı" yazılmış | **Karşılandı** (iki küçük boşluk var, sağdaki sütunda) | Ön kontroller ve S1a–S5: `implementation/grup-4-sitl-acik-cevrim.md`. S4 tam, Hold sonrası yeniden giriş, donmuş Pi, S2 (60°/s): `grup-5-hold-gecisi.md` Bölüm 4. S6, S7, T1, T1b, T2, T2b, tarama ve S6 tekrarı: `grup-6-kapali-cevrim-analiz.md`. Hepsi `rapor.md` §4.9'da da var. 29 ULog'un hepsi klasörde (Bölüm 4). Boşluklar: QGC ekranındaki kontroller kullanıcıya kaldı. Hold reddi yolu SITL'de üretilemedi, yalnızca birim testinde sınandı |
| 4 | Kod `make px4_sitl` ile derleniyor | **Karşılandı** | Bugün derlendi (çıkış 0, uyarı 0). `auto_follow` nesneleri silinip yeniden derlendi (Bölüm 3) |
| 5 | CI'da `verify-pin`, `derleme-sitl`, `derleme-fmu-v6c` yeşil | **Karşılanmadı (henüz doğrulanamaz)** | Push ve PR yok, yani CI hiç çalışmadı. `verify-pin` kırmızı olacak: yerelde CI'ın kullandığı biçimde (`verify_pin.sh`, bayraksız) de 15 dosya, 7 yol. Hüseyin'in izin listesi PR'ı birleşince yeşile döner. İki derleme yerelde geçtiği için `derleme-sitl` ve `derleme-fmu-v6c`'nin yeşil olması bekleniyor ama CI'da görülmedi |
| 6 | PX4'e eklenen yeni dosyaların yolları PR açıklamasında | **Karşılandı (taslakta)** | `implementation/pr-aciklamasi-taslak.md`, "PX4'e eklenen / değişen dosyalar": 10 yeni dosya, 5 değişen dosya ve tez araçları. `git diff main...HEAD` ile birebir aynı. PR henüz açılmadı |

**Spec'in kendi kararlarından gelen kriterler:**

| Kriter | Sonuç | Kanıt |
|---|---|---|
| Modül 6C'ye giriyor, flash spec'te | **Karşılandı** | `boards/px4/fmu-v6c/default.px4board` satırı. Spec "Kilitli yollar ve flash" tablosu son satırı 1 937 316 B. Bugünkü derleme aynı sayıyı verdi |
| Her SITL ULog'u klasörde, adı spec klasöründe | **Karşılandı** | 29/29 (Bölüm 4) |
| `log-sozlugu.md` kodla aynı, `AUTO_FOLLOW_TARGET` uyarısı içinde | **Karşılandı** (belge geçmişi eksik) | Bütün adlar, tipler, sabitler ve parametreler kodla aynı. Uyarı en üstte. Sürüm satırı ve tablo biçimiyle ilgili küçük eksikler Bölüm 5'te |
| `rapor.md` ve grup notları güncel | **Büyük ölçüde** | Son kararlar (`AF_BETA` 0,10, S6 tekrarı) rapor §4.6, §4.9, §4.10 ve belge geçmişi sürüm 14'te yazılı. Birkaç eski cümle var (Bölüm 5) |
| PR açıklamasında `Closes Auto-Follow/Auto-Follow#6` | **Karşılandı (taslakta)** | Taslağın sonunda. Kapsam (m15 mü, m16'yı da kapatıyor mu) Hüseyin'le netleşecek |

---

## 3. Test, derleme, flash, ruff ve kilit sonuçları

| Kontrol | Komut | Sonuç |
|---|---|---|
| Birim testi | `make tests TESTFILTER=AutoFollowGuidance` | **Geçti.** ctest: 1/1 (`unit-AutoFollowGuidance`). Test dosyası ayrıca doğrudan çalıştırıldı: **12 testin 12'si geçti** (GeometrySpecExample, LawSpecExampleMovesAway, LawClippedToVelMaxS1a, AccelerationLimitPerCycle, CorruptInputRejected, DataTimeoutThenHold, NoTargetImmediatelyLost, RestartedSenderAcceptedAfterTimeout, FilterRestartsAfterLongGap, FrozenSenderNeverAccepted, YawRateLimitPerCycle, HoldRequestRetries) |
| PX4'ün bütün test takımı (gerileme kontrolü) | `build/px4_sitl_test` içinde `ctest` | **149 test: 148 geçti, 0 kaldı, 1 çalıştırılmadı** (`antlr4_tests_NOT_BUILT`: dışarıdan indirilen antlr kütüphanesinin derlenmemiş test yer tutucusu, `_deps/antlr_cpp-build`; bizim işle ilgisi yok). Not: ilk denemede testler paralel (`-j4`) koşuldu ve 25 `sitl-*` / `posix_*` testi "PX4 server already running for instance 0" diyerek düştü. Bu testler aynı anda tek bir PX4 örneği ister. Düşen 25 test sırayla yeniden koşuldu ve 24'ü geçti; kalan tek test yukarıdaki antlr yer tutucusu |
| SITL derlemesi | `make px4_sitl` | **Geçti**, çıkış 0, uyarı 0 (`AutoFollow.cpp` ve `AutoFollowGuidance.cpp` yeniden derlendi) |
| Pixhawk 6C derlemesi | `make px4_fmu-v6c_default` | **Geçti**, çıkış 0, uyarı 0 |
| **6C flash** | çıktıdaki satır | **`FLASH: 1937316 B 1920 KB 98.54%`**, boş 28 764 B. Beklenenle aynı (1 937 316 B, %98,54). `region FLASH overflowed` yok. Modül yokken 1 926 408 B → **+10 908 B** |
| Python biçimi | `ruff format --check tez/sitl/af_los_gonder.py tez/analiz/af_log_analiz.py` (ruff 0.16.9) | **Temiz**: "2 files already formatted" |
| Python kod kontrolü | `ruff check` (aynı iki dosya) | **Temiz**: "All checks passed!" |
| Kilit (çalışma ağacı) | `tez/pin/verify_pin.sh --worktree` | **Beklenen kırmızı.** "15 PX4 dosyası izinsiz değişmiş". Hepsi 7 yolun içinde: `src/modules/auto_follow/` (10 dosya), iki kart dosyası, `msg/AutoFollowStatus.msg`, `msg/CMakeLists.txt`, `src/modules/logger/logged_topics.cpp`, `ROMFS/px4fmu_common/init.d/rc.mc_apps`. Taban v1.17.0 OK, `.gitmodules` OK, 29 submodule OK |
| Kilit (CI'ın biçimi) | `tez/pin/verify_pin.sh` | Aynı sonuç: 15 dosya, 7 yol |
| **7 yolun dışında değişen PX4 dosyası** | `git diff --name-only main...HEAD` | **Yok.** Geri kalan değişiklikler `agent-os/` ve `tez/` altında; ikisi de izinli yol |
| `allowed-paths.txt` | `git diff main...HEAD -- tez/pin/allowed-paths.txt` | **Değişmemiş** |
| Kodda `double` ve dinamik bellek | `grep` | `double` yok. Tek `new` / `delete`, PX4'ün her modülde kullandığı başlatma kalıbı (`AutoFollow.cpp:665, 679`, `task_spawn`; açılışta bir kez). Büyüyen bellek ya da `malloc` yok |
| `make check_format` | — | Çalıştırılmadı. astyle'ın sürümü `VERSIONS.md`'de yazılı değil (çatı kural 4); grup notları da aynısını yazıyor. Kod elle PX4 stiline uydurulmuş. CI bu kontrolü istemiyor |

---

## 4. SITL kanıtları

**Klasör kontrolü** (`~/Desktop/AUTO-FOLLOW LOG/`, yalnızca listelendi). Dokümanlarda geçen 29 ULog adının **hepsi** klasörde:

- Grup 4: `20_48_09`, `20_52_31`, `20_55_24`, `20_56_47`, `20_58_51`, `21_00_19`, `21_01_32`, `21_02_55`, `21_05_34`, `21_10_47`
- Grup 5: `19_09_04`, `19_10_27`, `19_13_40`, `19_15_43`, `19_18_27`, `19_20_46`, `19_22_03`, `19_23_53`, `19_25_29`
- Grup 6: `21_08_57`, `21_14_07`, `21_18_29`, `21_22_13`, `21_24_40`, `21_26_42`
- Tarama ve S6 tekrarı: `18_56_51`, `19_02_38`, `19_06_16`, `19_26_43`

Repoda hiçbir `.ulg`, CSV ya da grafik dosyası yok.

**Analiz script'iyle örnek kontrol** (`tez/analiz/af_log_analiz.py`; çıktılar yalnızca geçici klasöre yazıldı, masaüstünde bir şey değişmedi):

| Log | Ölçü | Notta yazan | Bugün ölçülen |
|---|---|---|---|
| `19_18_27.ulg` (S4 tam) | Son geçerli mesaj → Hold (`nav_state = 4`) | 1,528 s | **1,528 s** |
| `19_18_27.ulg` | İlk "hedef yok" → Hold | 1,036 s | **1,036 s** |
| `19_18_27.ulg` | Hedefsiz giriş → Hold | 1,524 s | **1,524 s** |
| `19_18_27.ulg` | Hold isteği → Hold, istek sayısı | 20–24 ms, 1 | **0,020 / 0,020 / 0,024 s, 1** |
| `19_26_43.ulg` (S6 tekrarı, `AF_BETA` 0,10) | Oturma süresi 10 / 15 / 20 / 25 / 30 m | 4,94 / 1,68 / 4,32 / 6,80 / 9,18 s | **4,94 / 1,68 / 4,32 / 6,80 / 9,18 s** |
| `19_26_43.ulg` | Logdaki `AF_BETA` | 0,10 | **0.1** |

Sayılar notlarla aynı. Bu doğrulamanın sonunda arkada px4 ya da gz süreci kalmadı (`pgrep` boş).

---

## 5. Kod ↔ doküman uyuşmazlıkları

### 5.1 Kodla karşılaştırma: değerler aynı

| Konu | Kod | `spec.md` | `log-sozlugu.md` | Sonuç |
|---|---|---|---|---|
| Parametre sayısı | `module.yaml`: 17 (`AF_ENABLE` yalnızca `rc.mc_apps`'te okunur; modülde 16 `DEFINE_PARAMETERS`) | Bölüm 10: 17 | Bölüm 3: 17 | Aynı |
| Varsayılanlar ve aralıklar | `AF_BETA` **0.10**, `AF_YAWRATE_MAX` **60** (5–200 deg/s), `AF_K_FF` 0, `AF_ALPHA` 0.5, `AF_TRK_ANG` 30, `AF_DATA_TOUT` 0.5, `AF_LOST_T` 1.0, `AF_MAX_RNG` 40, … | Aynı | Aynı | 17'sinde de ad, varsayılan, birim ve min–max aynı |
| Log mesajı | `msg/AutoFollowStatus.msg`: **39 alan**, 4 `STATE_*` (0–3), 10 `CHECK_*` (0–9) | Bölüm 9 tablosu: aynı 39 alan, aynı tipler | Bölüm 4–6: aynı | Aynı |
| Mod adı, girdi adı, çevrim | `MODE_NAME = "AUTO FOLLOW"`, `INPUT_NAME = "AF_LOS"`, 20 ms (50 Hz), `nav_and_controllers` | Aynı | Aynı | Aynı |
| Arming check ve kontrol bayrakları | `can_arm_and_run = !(landed && !mode_active)`, `mode_req_prevent_arming = true`, `flag_control_auto_enabled = true` | A1, A2, A14, C1 | — | Aynı |
| Hold isteği | `VEHICLE_CMD_SET_NAV_STATE`, `param1 = AUTO_LOITER`, 1 s arayla en fazla 3, uyarı metni `AUTO FOLLOW: Hold rejected, holding position` | Bölüm 7 | Bölüm 1, 4.7 | Aynı |
| Kilitli yollardaki satırlar | `rc.mc_apps` (`if param compare -s AF_ENABLE 1`), `add_topic("auto_follow_status")`, `AutoFollowStatus.msg` satırı, iki kart satırı | "Kilitli yollar" tablosu | Bölüm 7 | Aynı |

### 5.2 Anlamca fark (kodda değil, metinde)

1. **LOS hangi andaki tutumla çevriliyor?** `spec.md` Bölüm 3 ve Varsayım V3 (ayrıca `tasks.md` 2.4) "varış anındaki `vehicle_attitude.q`" diyor. Kod ise mesajın işlendiği çevrimdeki en son tutumu kullanıyor (`AutoFollow.cpp:293`). Bu an varıştan en fazla ~20 ms sonra. Fark grup-2 notu (satır 146) ve `rapor.md` §5.1 K2.7'de bilerek verilmiş bir kod içi karar olarak yazılı, ama spec metni güncellenmemiş.

### 5.3 Dokümanlarda eskimiş ya da çelişkili yerler (hepsi küçük; düzeltilmedi, karar kullanıcının)

1. **`log-sozlugu.md`**
   - Başlıkta "Sürüm: 8" yazıyor ve belge geçmişinde `AF_BETA` 0.17 → 0.10 değişikliği için satır yok. Tablodaki değer güncel.
   - §4.3'te `latency` satırı "Bütün sayaçlar…" paragrafının altında kalmış. Markdown'da tablodan kopuyor ve düz metin gibi görünüyor.
   - §4'ün girişindeki "mod açıkken görülecek değerler Grup 4'te SITL'de doğrulanacak" cümlesi eskidi; bu değerler doğrulandı.
2. **`tez/analiz/BENIOKU.md:266`** filtreyi anlatırken "`AF_BETA` (0,17)" diyor; yeni varsayılan 0,10. (Satır 217'deki örnek çıktı eski bir logdan alındığı için 0.17 göstermesi doğru.)
3. **`tasks.md`** (madde metinleri tarihsel; yalnızca işaretlere dokunuldu)
   - 1.6 ve Grup 1 kabul kriteri "16 parametre" ve `AF_BETA` 0.17 diyor; şimdi 17 parametre, 0.10.
   - "Genel bakış" Grup 6 için 12 alt görev diyor; listede 14 madde var.
   - Grup 3 kabul kriterinde "test sayısı ~8'i geçmiyor" yazıyor; şimdi 12. Fazlası kullanıcı kararlarıyla Grup 2'nin düzeltme turunda ve Grup 5'te eklendi.
   - 1.4'teki "visuals:114 hâlâ auto = false yazıyor" notu eskidi; şema güncellenmiş.
   - Grup 6 "Sonuç" satırı flash için 1 937 260 B ve "`AF_ALPHA`/`AF_BETA` değiştirilmedi" diyor; sonraki 0.10 kararı ve 1 937 316 B bu satırda yok.
4. **`implementation/grup-6-kapali-cevrim-analiz.md`**
   - Baştaki "Durum" satırı ve §12'nin girişi varsayılan kararını "bekleniyor" diye yazıyor. §12.7 de "`module.yaml` değişmedi" diyor.
   - §7.3 ve §11 flash için 1 937 260 B diyor.
   - §12.8 (karar) §12.7'den önce geliyor.
   - Kararın kendisi §12.8'de doğru yazılı.
5. **`rapor.md` §11** aynı bölümde birbirini tutmayan cümleler içeriyor. Bir yerde "(2) … varsayılan kararı bekleniyor" ve "(1) ve (4) cevap bekliyor" yazıyor. Hemen altında dört sorunun cevaplandığı ve `AF_BETA` kararının verildiği yazıyor.
6. **`rapor.md` §1 Özet** hâlâ gelecek zamanla yazılmış ("yazılacak", "engellenecek"). İş bitti.
7. **`spec.md`**
   - Bölüm 11'deki "Grup 6 sonuçları" maddesinde S6 tekrarı (`19_26_43.ulg`) ve tarama logları (`18_56_51`, `19_02_38`, `19_06_16`) yok; bunlar rapor §4.9'da ve grup-6 notunda var.
   - "Visual Design" bölümü "kilit listesi onayı (6 yol)" diyor; doğrusu 7.
8. **`implementation/pr-aciklamasi-taslak.md`**, "Taslakla ilgili notlar" kısmı: "Flash sayısı Grup 5 sorusu 3-b'den sonraki son ölçümdür; Grup 6'da PX4 kodu değişmedi" cümlesi eskidi. PR metnindeki sayı (1 937 316 B) doğru.
9. **`planning/karar-gunlugu.md`**'deki "Görev grubu 6 sonrası sorular (2026-11-12, cevap bekliyor)" başlığının cevapları bir sonraki başlıkta. "Son kayıt geçerli" kuralına uygun; yalnızca bilgi.
10. **`planning/visuals/02-px4-detayli-akis.md:551`** "Açık: spec A2 (SITL'de doğrulanacak)" diyor; A2 karara bağlandı ve Grup 4'te doğrulandı.

---

## 6. Açık konular ve dış bağımlılıklar

| Konu | Kim | Durum | Etkisi |
|---|---|---|---|
| **7 kilitli yolun izin listesine eklenmesi** (`tasks.md` 0.1 tablosu) | Kullanıcı → Hüseyin | Bekliyor. Talebin gönderildiği kayıtlı değil | Onay ve Hüseyin'in ayrı PR'ı olmadan CI'daki `verify-pin` kırmızı; issue kriteri 5 karşılanamaz |
| **Vision'a sorulan 9 soru** (hız, yaş, yaşın ölçüldüğü yer, yerleşim, eksenler ve işaretler (V1/V6), "hedef yok" davranışı, sıra no, hedef seçimi, seri port ve baud) | Kullanıcı → Yusuf Ortatepe | Cevap yok (2026-11-10'dan beri) | Yerleşim ya da eksenler farklı çıkarsa PX4 kodu değişir ve S1–S3 yeniden koşulur (grup-0 notunda tablo var) |
| **Kamera eğimi → `AF_TRK_ANG`** | Ahmet (m06) | Bekliyor | SITL'de 30°. Gerçek değer istenen mesafeyi değiştirir |
| **Gerçek uçuştan önce `COM_LOW_BAT_ACT` = 3** | Takım / Hüseyin | Bekliyor (grup-0 0.5 satırı) | PX4 varsayılanı 0 = yalnızca uyarı. Hold üç kez reddedilir ve pilot devralmazsa drone batarya bitene kadar bekleyebilir. T1'de 3 ile RTL ve Land görüldü |
| **Hold reddinin gerçek testi** | Kullanıcı / m16 | SITL'de üretilemedi (Hold küresel konum ister; GPS gidince yerel konum da gidiyor). Yalnızca birim testinde sınandı | Karar: m16'ya ya da gerçek uçuştan önce GPS'li bir yer testine |
| **EKF yön sıfırlamasında yaw kaydırma ve filtre sıfırlama** | m16 / gerçek uçuş | SITL'de bu sıfırlama hiç olmadı | Kod var, birim testi yok, sahada görülmedi |
| **QGC'de bakılacaklar** | Kullanıcı | HEADLESS çalışıldığı için bakılmadı | Mod listesinde `AUTO FOLLOW`. Yerde arm'lıyken geçiş reddinin ve bu modda arm reddinin QGC'deki metni (PX4 "External 1" diyor). Hold'a geçişin QGC'de görünüşü |
| `tech-stack.md:44` "entegrasyon yaklaşımı: external mode" | Hüseyin | PR taslağında not olarak var | Ürün planını yalnızca repo sorumlusu günceller |
| `AF_K_FF` gerçek uçuşta | Kullanıcı / m13 | Varsayılan 0. SITL'de 1,0 / β 0,10 sakin çıktı | Gerçek kameranın gecikmesiyle titreşim sınırı değişebilir |
| Burnun dönüşte 5–7° aşması, gecikme telafisi | m13 / m16 | "Şimdilik böyle kalsın" kararı | `requirements.md` §1.3'te |

---

## 7. Roadmap güncellemesi (yalnızca öneri; ürün planına dokunulmadı)

`../agent-os/product/roadmap.md` yalnızca okundu. İşaretlemeyi repo sorumlusu PR birleştikten sonra yapar. Issue #6 [M15] olarak açıldı, ama iş m16'nın doğrulama tanımına da değiyor. Kapsam Hüseyin'le netleşecek.

- [ ] **15. PX4 entegrasyon yaklaşımının seçimi**: önerilen durum **tamamlandı**; repo sorumlusu birleştirmeden sonra işaretler. Gerekçe: yaklaşım (external mode) seçenekleriyle ve gerekçesiyle belgelendi (spec Bölüm 1, rapor §4.2, karar 2-a). Maddenin doğrulama ölçütü olan "en küçük iskelet SITL ve 6C'de derlenir" sağlandı, iskeletin ötesinde tam mod da derleniyor.
- [ ] **16. PX4 özel takip modu (SITL)**: önerilen durum **büyük ölçüde tamamlandı, CI koşulu bekliyor**. Sağlananlar: veri doğrulama (9 kontrol), sentetik hedef vektörüyle mod seçimi ve takip (S1–S7), veri kesilince tanımlı davranış (S4, loglardan ölçüldü). Kalan: "CI'daki derleme ve kilit kontrolleri geçer" koşulu Hüseyin'in izin listesi PR'ına bağlı. Bu yüzden ancak o PR birleşip CI yeşil olunca işaretlenmeli.
- Kısmen değen maddeler (önerilmez, bilgi):
  - **13 (kontrol algoritması)**: ilk hız tabanlı yasa yazıldı; nihai yasa ve ince ayar m13'te.
  - **17 (test ve ölçüm altyapısı)**: `af_log_analiz.py` var, ama başarı kriterleri (m01) henüz tanımlı değil.

---

## 8. PR öncesi yapılacaklar

1. **Hüseyin'e 7 yol talebi.** Gönderilmediyse gönderilmeli; cevabı karar günlüğüne yazılmalı. İzin listesine ekleme Hüseyin'in açacağı ayrı PR'dır (ajan listeye dokunmaz).
2. **Bölüm 5.2 ve 5.3'teki doküman düzeltmeleri.** Hangilerinin yapılacağına kullanıcı karar verir. Hepsi metin işi, kod değişmez. Öncelikliler: sözlüğün belge geçmişi ve `latency` satırı, `BENIOKU.md:266`, `rapor.md` §11'deki çelişki, spec'teki V3 cümlesi.
3. **Kapsam ve kapanış.** PR taslağındaki `Closes Auto-Follow/Auto-Follow#6` ve m15 / m16 sınırı Hüseyin'le netleşmeli.
4. **Dalda eski taslak spec klasörleri de var.** `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/` ve `2026-10-18-m15-fc-only-flow-diagrams/` bu dalın commit'lerinde. İçlerinde 86 KB'lık bir fotoğraf var (`planning/visuals/WhatsApp Image 2026-09-26 at 00.07.13.jpeg`, adında boşluk var). Kural 9'a aykırı değil, ama PR'a gireceği bilinmeli.
5. **QGC kontrolleri** (Bölüm 6) PR'dan önce ya da hemen sonra yapılabilir. PR'ı engellemez.
6. PR açılınca CI'daki `derleme-fmu-v6c` flash satırı bu rapordaki 1 937 316 B ile karşılaştırılmalı.
7. Push ve PR yalnızca kullanıcı isteyince açılır. Bu doğrulamada push ve PR yapılmadı.

---

## Ek: bu doğrulamada çalıştırılan komutlar

- `make tests TESTFILTER=AutoFollowGuidance` · `build/px4_sitl_test/unit-AutoFollowGuidance` · `ctest` (bütün takım; ilk paralel denemede düşen 25 test `ctest --rerun-failed` ile sırayla yeniden koşuldu)
- `make px4_sitl` · `make px4_fmu-v6c_default` (iki kez; ikincisinde `auto_follow` nesne dosyaları silinip yeniden derlendi, uyarı kontrolü için)
- `.venv-tez/bin/ruff format --check …` · `ruff check …`
- `tez/pin/verify_pin.sh --worktree` · `tez/pin/verify_pin.sh`
- `af_log_analiz.py` iki logda (`19_18_27.ulg`, `19_26_43.ulg`), çıktılar yalnızca geçici klasörde

---

## Ek: doğrulamadan sonra yapılanlar (2026-11-12)

Bu rapor yazıldığı andaki durumu anlatır. Sonrasında kullanıcının kararlarıyla:
- Bölüm "Bulunan uyuşmazlıklar"daki **metin eksiklerinin hepsi düzeltildi** (yalnızca doküman; kod değişmedi).
- **`AF_ENABLE` varsayılanı 0 → 1** (`module.yaml`; kullanıcı kararı, rapor §5.1 G6.19). C++ ve `rc.mc_apps` aynı. İki derleme uyarısız; 6C flash **1 937 348 B (%98,54)**, +32 B; birim testi 12/12.
- Hüseyin: kullanıcı konuştu, push/PR yapılınca 7 yolu onaylayacak.
- Eski taslak spec klasörleri ve fotoğraf kullanıcı kararıyla PR'da kalır (PR taslağına not düşüldü).

