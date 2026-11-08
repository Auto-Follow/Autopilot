# M15 shape-spec: 1. tur soruların cevapları (çalışma notu)

- Tarih: 2026-11-08
- Durum: **Shape-spec sürüyor.** `requirements.md` henüz yazılmadı. Kullanıcı, `write-spec` aşamasına geçilmeden önce bazı maddelerin ayrıntılı konuşulmasını istedi.
- Etiketler:
  - **Karar:** Kullanıcı açıkça seçti.
  - **Karar (öneri kabul):** Kullanıcı "senin önerin neyse o" ya da "önerilen gibi" dedi; aşağıdaki öneri kabul edildi.
  - **Açık:** Ayrıntılı konuşulacak ya da netleşmesi gerekiyor.
  - **Teyit bekliyor:** Cevap birden fazla şekilde okunabiliyor.

## Cevaplar

| # | Konu | Kullanıcının cevabı | Kayıt |
|---|---|---|---|
| 1 | m15 ile m16 sınırı | 1-a | **Karar:** Spec issue #6'yı izler: iskelet + ilk guidance + basit güvenli davranış + SITL testi. Roadmap'teki m15 tanımıyla (yalnızca iskelet derlenir) fark spec'e not olarak yazılır. "m16'ya kalanlar" listesi tutulur. |
| 2 | PX4 entegrasyon yaklaşımı | 2-a | **Karar:** External mode modülü (`mc_nn_control` kalıbı). Modül `trajectory_setpoint` yayınlar, PX4'ün `mc_pos_control` → `mc_att_control` → `mc_rate_control` → `control_allocator` zinciri kullanılır. |
| 3 | Kodun yeri | 3-a | **Karar:** `src/modules/<ad>/` + `boards/px4/sitl/default.px4board` ve `boards/px4/fmu-v6c/default.px4board` dosyalarına `CONFIG_MODULES_<AD>=y`. **Yapılacak:** Bu yolların `tez/pin/allowed-paths.txt`'e eklenmesi için repo sorumlusunun (Hüseyin) onayı gerekir. Ekleme ayrı ve açık bir PR ile yapılır; ajan listeye kendisi eklemez. 3.1 (fmu-v6c'ye de eklensin mi) cevaplanmadı → **Açık**. |
| 4 | Modülün iç yapısı | "senin önerin neyse" | **Karar (öneri kabul):** 4.1 iş kuyruğu `nav_and_controllers` (`mc_nn_control.cpp:65`). 4.2 sabit hızlı çevrim `ScheduleOnInterval` (önerilen 50 Hz; değer spec'te). Gerekçe: veri gelmese de çevrim döner, zaman aşımı yakalanır. 4.3 guidance hesabı donanımdan bağımsız ayrı bir sınıfta. |
| 5 | Girdi mesajı | 5-a | **Karar (Varsayım olarak):** MAVLink `DEBUG_VECT` → uORB `debug_vect`. ICD (m3–5) yazılana kadar "Varsayımlar" başlığı altında kalır. Bilinen sınırlamalar: sıra no yok; `timestamp` varış anı (`mavlink_receiver.cpp:2804`); ortak topic, name filtresi gerekir; işleyici `CONSTRAINED_FLASH` altında derleme dışı kalır (m14 riski). |
| 6 | Guidance yasası | "detaylı konuşacağız" | **Açık.** Seçenekler: a) hız tabanlı P, b) konum tabanlı, c) PN/pure pursuit. Bunlara ek olarak 6.1 kestirim ve 6.2 varsayılan değerler. |
| 7 | Setpoint tipi | 7-a, mutlak yaw | **Karar:** `trajectory_setpoint`, `velocity[0..1]` + `position[2]` + `yaw` (mutlak); diğer alanlar NaN. Not: Kesin alan dağılımı 6. maddedeki yasaya bağlı. |
| 8 | Geçersiz/eski veri | "önerilen gibi" | **Karar (öneri kabul):** 8.1 kontroller: `PX4_ISFINITE`, birim norm toleransı, `name` eşleşmesi, yaş < zaman aşımı, en küçük aşağı açı, en büyük menzil, yerel konum geçerli. Geçersiz örnek atılır, `perf_counter` ile sayılır, hız sınırlı loglanır. DEBUG_VECT'te sıra no olmadığı için "tekrar/eski ölçüm" yakalanamaz; bu, "bilinen eksik" olarak yazılır. 8.2 tepki: **(a)** modül aktif olarak hover yayınlar (mevcut konum + hız 0 + son yaw); Hold isteği m16'ya. Standart (`error-handling.md:4`) ile kaynak (`MulticopterPositionControl.cpp:438, 443-449`) arasındaki çelişki spec'e not olarak yazılır. 8.3 zaman aşımı parametre olur (önerilen aralık 0.5–1.0 s, varsayılan değer **Açık**). 8.4 veri geri gelirse takibe otomatik dönülür. **Teyit bekliyor:** Öneride 8.2 için "(a) ya da (b)" yazıyordu; (a) olarak kaydedildi. |
| 9 | Mod kaydı ve arming | "arm edili değilken de masa testleri için bu moda geçebilmem lazım" | **Gereksinim:** Araç disarm durumdayken bu moda geçilebilmeli (masa/bench testi). Kaynak bulgusu ve kalan alt sorular aşağıda. 9.1, 9.3, 9.4 ve 9.5 → **Açık**. |
| 10 | Test | "hiç anlamadım" | **Açık:** Kullanıcıya sade dille yeniden anlatılacak. |
| 11 | Sentetik vektörü gönderen kod | "Karar bende değil, Vision tarafındaki arkadaşta. Tüm repoları tara, bana dön." | **Açık:** Tarama sonucu aşağıda. Karar Vision tarafıyla (Yusuf Ortatepe) ve m06 sorumlusuyla (Ahmet Kazalcı) birlikte verilecek. |
| 12 | Adlar | "Süreçte karar verelim, her ad gerektiğinde sor." | **Karar (süreç):** Her ad, gerektiği anda kullanıcıya PX4 kurallarıyla (büyük harf, ≤16 karakter, çakışma yok) birlikte sorulur. Önceden toplu ad verilmez. Eski taslak adlar (`tez_follow`, `TEZ_FOL_*`, `TEZ_LOS`) geçersiz. |
| 13 | Varsayımlar | "a parametresi olsun" | **Teyit bekliyor.** İki şekilde okunabilir: (i) V4 yükseklik kaynağı = (a) `-vehicle_local_position.z`, V5 hedef noktası için hedef yüksekliği **parametresi** olsun; (ii) V4 için (a) seçildi ve bir parametreyle düzeltilebilsin (ör. zemin ofseti). V1, V2, V3 ve V6 için ayrıca itiraz gelmedi; teyit edilecek. |
| 14 | Kapsam dışı ve ürün planı | "detaylı konuşalım" | **Açık.** 14.1 kapsam dışı listesi, 14.2 tech-stack güncellemesi, 14.3 masaüstündeki guidance dosyası, 14.4 eski taslak spec'ler. |

## Bulgu: 9. madde (disarm durumda moda geçiş)

- PX4 v1.17.0, araç **disarm durumdayken her mod değişikliğine izin veriyor**. Kaynakta "Always allow mode change while disarmed" yazıyor (`src/modules/commander/UserModeIntention.cpp:54-55`, `always_allow = force || !isArmed()`). Mod gereksinimleri (`canRun`) yalnızca araç arm iken kontrol ediliyor (`:58-59`).
- `mode_req_prevent_arming` moda **geçişi** engellemiyor, yalnızca **o moddayken arm etmeyi** engelliyor: "Mode not suitable for arming" (`src/modules/commander/HealthAndArmingChecks/checks/modeCheck.cpp:196-205`).
- Sonuç: Masa testinde disarm durumdayken moda geçmek 9.2'nin her iki seçeneğiyle de mümkün. 9.2 (a) seçilirse masada moda geçilir ama o moddayken arm edilemez; pervanesiz masa testi için sorun değil.
- Masa testi için ayrıca konuşulacak noktalar (**Açık**):
  - Kapalı ortamda GPS yoksa yerel konum geçersiz olur. 8.1'deki "yerel konum geçerli" kontrolü nedeniyle modül hover/bekleme durumunda kalır ve hedef konumunu hesaplamaz. Masada ne görülmek isteniyor: mesajın alınması ve doğrulanması mı, LOS → NED dönüşümü mü, setpoint hesabı mı?
  - Disarm durumdayken `mc_pos_control` motorlara bir şey göndermez; masada görülecek olan, modülün hesapladığı setpoint'tir.
  - Gerçek donanımda log varsayılan olarak yalnızca arm iken alınıyor: `SDLOG_MODE` = 0 "when armed until disarm" (`src/modules/logger/module.yaml:16-30`). Masa testinde log için 1 ya da 2 gerekir. SITL'de varsayılan 1 (`ROMFS/px4fmu_common/init.d-posix/rcS:180`).

## Bulgu: 11. madde (repo taraması, 2026-11-08, `git fetch` sonrası)

| Yer | Durum |
|---|---|
| `Vision` `main` (`64194c0`) | Kod yok. Yalnızca `src/vision/__init__.py` ve ortam testi var. `DEBUG_VECT` ya da başka bir MAVLink gönderici yok. |
| `Vision` `origin/model-training` | Yalnızca model ağırlıkları (`models/*.pt`, ~22 MB'lık 3 dosya). Açık PR: Vision #5 "base models added". Not: Kural 9'a göre model ağırlığı repoya girmemeli. Bu not repo sorumlusuna iletilebilir. |
| `Autopilot` `origin/deney/ai-follow-sim` (Ahmet Kazal, 2026-10-05) | "Deneme, tezde kullanılmayacak" (README). pymavlink ile **`FOLLOW_TARGET`** (lat/lon) gönderip PX4'ün kendi Follow Me modunu kullanıyor, `udpin:0.0.0.0:14540` (`follow_core.py:37,46`). Geolocation (`geolocation.py`), bağlantı gecikmesi/kayıp simülasyonu ve pyulog analizi var. `DEBUG_VECT` veya LOS gönderen bir kod yok. Fikir ve referans olarak kullanılabilir, kod doğrudan alınmaz. |
| Çatı repo (`docs`, `agent-os`) | Gönderici kodu yok. `docs/01-ekip-rehberi.md:513-521` görev dağılımı: m10 Yusuf Ortatepe (Vision, body frame), m06 Ahmet Kazalcı (Autopilot/Gazebo, simülasyon). "m10'un ürettiği body frame m15'in girdisi; m06 ikisini birleştirecek." |
| GitHub issue #7 (m06, Ahmet) | "Model → PX4 oku başka arkadaşlarının işine bağlı (m10, m15). Onlar hazır olana kadar geçici bir çözüm kullanabilirsin." Yani **SITL'de PX4'e veri gönderme işi m06 ile de kesişiyor.** |
| GitHub issue #8 (m10, Yusuf Ortatepe) | "Bu aşamada kod yazmak şart değil." Teslim 2026-11-08. Remote'ta henüz m10 dalı veya spec'i yok. |

**Sonuç:** Hiçbir repoda `DEBUG_VECT` (ya da LOS) gönderen bir kod yok. m10 ve m06'nın dalları da henüz remote'ta değil. Karar için konuşulacak kişiler: Yusuf Ortatepe (Vision, m10/m12) ve Ahmet Kazalcı (m06, SITL'de "Model → PX4" oku). M15'in SITL testi bu ikisini beklemeden yapılacaksa geçici bir test göndericisi gerekir (seçenekler 11a–d); hangisinin seçileceği kullanıcı onlarla konuştuktan sonra kararlaştırılır.

## Sonraki adım

Ayrıntılı konuşulacaklar: 6 (guidance yasası), 10 (testin sade anlatımı), 14 (kapsam ve ürün planı), 9'un alt soruları, 13'ün teyidi, 3.1 (fmu-v6c), 8.2 ve 8.3'ün teyidi. Bunlar netleşince spec-shaper `requirements.md` dosyasını yazar ve shape-spec tamamlanır. Bu dosya o zaman `requirements.md`'ye kaynak olur.
