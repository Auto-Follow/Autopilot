# Görev grubu 6: Analiz script'i, kapalı çevrim S6–S7, batarya ve GPS denemeleri, kapanış

- **Tarih:** 2026-11-11/12 · **Dal:** `ozellik/m15-takip-kodu` · **Görev listesi:** `../tasks.md` Grup 6 (6.5, 6.8–6.18, 6.T1, 6.T2)
- **Durum:** Bitti. Log analiz script'i `tez/analiz/af_log_analiz.py` ve rehberi `tez/analiz/BENIOKU.md` yazıldı; test göndericisine S6/S7 hedefi eklendi; S6 (5 başlangıç mesafesi), S7 (L yolu, `AF_K_FF` 0 ve 1,0), T1 (batarya failsafe'i) ve T2 (GPS arızası) Gazebo'da uçuldu ve script'le ölçüldü. **PX4 kodu bu grupta değişmedi.** Kullanıcıya 4 soru ve 3 bilgi notu var (Bölüm 10).
- Bu not kod okumadan anlaşılacak şekilde yazıldı. Adların anlamı `../log-sozlugu.md`'de, ölçülerin anlamı ve hesabı `tez/analiz/BENIOKU.md`'de. Bu grubun uygulama kararları ayrıca `../rapor.md` §5.1'de (G6.1–G6.12).

## 1. Ne yapıldı?

| # | Ne | Neden (kaynak) | Kullanıcı ne görür? |
|---|---|---|---|
| 6.8 | **Analiz script'i** `tez/analiz/af_log_analiz.py`: ULog'u okur, logdaki her AUTO FOLLOW **bölümünü** (mod açık kalma süresi) kendisi bulur, her bölüm için spec Bölüm 11'in "Ölçüm" sütunundaki bütün ölçüleri Türkçe başlıklı Markdown tabloyla basar; `--aralik`, `--grafik` (6 PNG), `--csv` | Spec Bölüm 9, 11; karar 2026-11-11 (kullanım biçimi kullanıcının) | Tek komutla oturma süresi, aşma, salınım, kırpma, burun hatası, filtre girdisi/çıktısı, Hold süreleri, sayaçlar, gecikme |
| 6.8 | **Rehber** `tez/analiz/BENIOKU.md`: kurulum, örnek komutlar, her ölçünün anlamı ve hesabı, iyi/kötü değer örnekleri, gerçek logdan örnek çıktı, grafiklerin ve filtre girdisi/çıktısının yorumu, sık hatalar | Karar 2026-11-11 ("benim anlamam için doküman hazırlanmalı", yer (a)) | PDF'i kullanıcı üretecek |
| 6.9 | Test göndericisine **`--hedef-mesafe METRE`** (varsayılan 20) ve **`--hedef-aci DERECE`** (varsayılan 0, pozitif = sağ); S6 koşuldu (10/15/20/25/30 m, 30° sağ) | Karar 2026-11-11 (adlar ve değerler kullanıcının) | Bölüm 4 |
| 6.10 | Göndericiye **S7 L yolu** (1,4 m/s, 20 s düz + 90° sağ + 20 s düz; `HEDEF_YOL` sabiti); S7 iki koşu (`AF_K_FF` 0 ve 1,0) | Karar 2026-11-11 | Bölüm 5 |
| 6.T1 | Batarya failsafe'i takip sırasında (`COM_LOW_BAT_ACT` = 3) | Karar 2026-11-11 ("SITL'de bunun testlerine devam") | Bölüm 6 |
| 6.T2 | GPS arızası takip sırasında (`failure gps off`) | Karar 2026-11-11 | Bölüm 6 |
| 6.5, 6.12–6.18 | Sözlüğün kodla son karşılaştırması, `latency`, S1–S5'in yeniden koşulmaması, `verify_pin`, `requirements.md` §1.3, `rapor.md`, PR açıklaması taslağı | tasks 6.x | Bölüm 7, 11 |

| Dosya | Ne değişti |
|---|---|
| `tez/analiz/af_log_analiz.py` | Yeni (çalıştırılabilir) |
| `tez/analiz/BENIOKU.md` | Yeni |
| `tez/sitl/af_los_gonder.py` | `--hedef-mesafe`, `--hedef-aci`, hedef yolu (`HEDEF_YOL`, `L_YOLU`, `YURUME_HIZI_M_S`, `YURUME_BASLA_S`); eski `HEDEF_ILERI_M` ve `HEDEF_HIZ_NED` sabitlerinin yerini aldı |
| `log-sozlugu.md`, `spec.md`, `rapor.md`, `tasks.md`, `planning/requirements.md`, bu not, `pr-aciklamasi-taslak.md` | Dokümanlar |

`tez/pin/allowed-paths.txt`'e dokunulmadı. PX4 dosyası değişmedi (`src/`, `msg/`, `boards/`, `ROMFS/` bu grupta hiç değişmedi). Hiçbir `.ulg`, PNG ya da CSV repoya girmedi; grafikler ve CSV'ler `~/m15-sitl-araclari/grup6/` altında. SITL test yardımcıları repoda değil (`~/m15-sitl-araclari/`, kullanıcı kararı U4.19).

## 2. Analiz script'i ve rehberi

**Nasıl çalışır (özet; ayrıntı rehberde):**

1. Logdan `auto_follow_status`, `vehicle_status`, `vehicle_local_position`, `vehicle_command` ve parametreler okunur (pyulog 1.2.4).
2. **Bölüm** = `auto_follow_status.mode_active` = 1 olan ardışık çevrimler. Çıkış modu `vehicle_status.nav_state`'ten (Position, Hold, RTL, Land…).
3. Her bölümün başında geçerli `AF_*` parametreleri yazılır (uçuş sırasında değişenler logdan okunur; S7'de `AF_K_FF` 0 → 1,0 doğru görüldü).
4. Ölçüler: durum süreleri ve geçişleri (nedenine göre süre), Hold süreleri (son geçerli mesaj / ilk "hedef yok" / giriş / istek → `nav_state = 4`), `hold_request_count`, mesafe hatası (ilk, ortalama, std, en büyük, son, son 5 s), oturma süresi (±0,3 m), aşma, salınım (işaret değişimi ±0,1 m, son 5 s tepe-tepe), kırpma süresi, `vel_cmd` büyüklüğü ve değişim hızı, drone hızı, üç burun hatası (`yaw_cmd` − gerçek yön, `yaw_cmd` − hedef yönü, gerçek yön − hedef yönü), burun aşması ve oturma süresi (±2°), `yaw_frozen` süresi, filtre ölçüm sayısı ve hızı, girdi–çıktı uzaklığı, `target_vel_ned`, ölçümlerden türetilen hız ve filtre hızıyla farkı, `latency`, 10 sayacın artışı, irtifa.
5. Ekranda Markdown tablo; `--grafik` ile her bölüm için `mesafe`, `burun`, `hiz`, `filtre`, `harita`, `durum` PNG'leri; `--csv` ile `bolum, grup, olcu, deger, birim, not` sütunlu dosya.

**Elle ölçümlerle tutarlılık (script'in doğrulaması):** Grup 4–5 notlarında elle (geçici script'lerle) ölçülen sayılar script'le aynı loglardan yeniden çıkarıldı:

| Log | Ölçü | Grup notundaki (elle) | Script | Uyum |
|---|---|---|---|---|
| `19_18_27.ulg` (S4 tam) | (b) son mesaj → KAYIP_BEKLE | +0,508 s | 0,508 s | Aynı |
| `19_18_27.ulg` | (b) KAYIP_BEKLE → TAKIP | 45,224 → 45,784 | 0,560 s (45,784'te) | Aynı |
| `19_18_27.ulg` | (a) son geçerli mesaj → `nav_state = 4` | 1,528 s (varış 54,716) | 1,528 s (varış 54,716) | Aynı |
| `19_18_27.ulg` | (a) KAYIP_BEKLE → HOLD_ISTENDI | +1,0 s (55,224 → 56,224) | 1,000 s | Aynı |
| `19_18_27.ulg` | (c) ilk "hedef yok" → KAYIP_BEKLE | bir çevrim (76,768 → 76,784) | 0,016 s | Aynı |
| `19_18_27.ulg` | (c) ilk "hedef yok" → `nav_state = 4` | 1,036 s | 1,036 s | Aynı |
| `19_18_27.ulg` | İstek → `nav_state = 4` | 20–24 ms | 0,020 s (bölüm 1, 2) | Aynı |
| `19_18_27.ulg` | `hold_request_count` | 1 | 1 | Aynı |
| `20_48_09.ulg` (kapalı çevrim kısa kontrol, `--aralik 68 99`) | Oturma süresi (±0,3 m) | 4,5 s | 4,500 s | Aynı |
| `20_48_09.ulg` | Aşma | 0,04 m | 0,04 m | Aynı |
| `20_48_09.ulg` | Son dönem hata | son 10 s −0,006 ± 0,02 m | son 5 s −0,01 ± 0,02 m | Uyumlu (pencere farklı) |
| `20_48_09.ulg` | Yaw hatası | < 0,1° (yaw_cmd − hedef) | `yaw_cmd` − hedef yönü en büyük 0,0° | Aynı |

Ayrıca Grup 5'in diğer logları da script'le yeniden ölçüldü ve notla aynı çıktı: S4 (d) hedefsiz giriş (`19_18_27.ulg` bölüm 3) giriş → `nav_state = 4` **1,524 s**; donmuş Pi (`19_20_46.ulg`) son geçerli mesaj → `nav_state = 4` **1,540 s**; Hold sonrası yeniden giriş (`19_22_03.ulg`) hedefsiz giriş → Hold **1,516 s**, gönderim kesilince **1,520 s**. Script'in çıktıları `~/m15-sitl-araclari/grup6/analiz_*.md` dosyalarında (repoda değil).

T1'de bir eksik bulunup düzeltildi: Hold'a PX4 kendi failsafe'iyle geçince (bizim modül istemeden) script ilk sürümde "son geçerli mesaj → Hold" süresini de yazıyordu (yanıltıcı). Artık bu süreler yalnızca bölümde modül HOLD_ISTENDI'ye girdiyse hesaplanıyor; yoksa "Hold'a geçişi kim yaptı: PX4 (AUTO FOLLOW istemedi)" yazılıyor. `hold_request_count` da yalnızca bölümün HOLD_ISTENDI çevrimlerinden okunuyor (alan mod kapanınca son değerini koruduğu için önceki bölümün değeri karışmasın). Düzeltmeden sonra Grup 5 logları yeniden denendi, sayılar değişmedi.

**Kontroller:** `ruff format` + `ruff check` (ruff 0.16.9) temiz; tip ipuçları ve herkese açık fonksiyonlarda docstring var. Rehberdeki örnek çıktı gerçek logdan (`21_08_57.ulg`, bölüm 3).

## 3. Test göndericisine eklenenler (6.9, 6.10)

| Ne | Değer | Anlamı |
|---|---|---|
| `--hedef-mesafe METRE` | varsayılan 20 | Kapalı çevrimde hedefin başlangıçtaki **yatay** uzaklığı (drone'un altındaki noktadan hedefin durduğu yere). Açık çevrimde kullanılmaz |
| `--hedef-aci DERECE` | varsayılan 0 | Hedefin başlangıçta burna göre yönü; pozitif = sağ (NED'de yaw + açı). Açık çevrimde kullanılmaz |
| Hedef yolu (`HEDEF_YOL`) | `()` = duruyor (S6, varsayılan) · `L_YOLU` = S7 | Bacak listesi: (süre, yön, hız). Yön, başlangıçta drone'dan hedefe bakan yatay yöne göre (0 = drone'dan uzaklaşma yönü, pozitif = sağa dönüş). S7: (20 s, 0°, 1,4 m/s), (20 s, +90°, 1,4 m/s); sonra durur |
| Yürüme başlangıcı (`YURUME_BASLA_S`) | gönderici başladıktan 10 s sonra (`SENARYO_BASLA_S` ile aynı) | Önce drone duran hedefin istenen mesafesine otursun, geride kalma ölçüsü yaklaşmayla karışmasın (kod içi, §5.1 G6.4) |

- Hedefin yeri zamanın fonksiyonu olarak hesaplanır (eskiden her mesajda hız × aralık ekleniyordu; drone konumu gelmediği çevrimlerde hedef ilerlemiyordu). Gönderici bacak değişimlerini ekrana yazar (`hedef bacak 1/2/0`).
- **S7'yi açmanın yolu:** komut satırı seçeneği eklenmedi (yeni ad uydurmamak için). Dosyadaki `HEDEF_YOL = ()` satırı `HEDEF_YOL = L_YOLU` yapılır. Testte dosya değiştirilmeden, `~/m15-sitl-araclari/af_los_gonder_L.py` sarmalayıcısıyla (sabiti değiştirip aynı `main()`'i çağırır) çalıştırıldı. Seçenek adı kullanıcıya sorulacak (Bölüm 10, soru 1).
- Elle denendi: `hedef_baslangici` (20 m, 30° → (17,32; 10,00)), `hedef_konumu` (L yolu: 20 s'de 14 m ilerde, 30 s'de köşede (28; 20), 50 s'de (28; 48), sonra sabit). SITL'de göndericinin yazdığı köşe noktaları: başlangıç (−37,07; 46,12) → köşe (−64,00; 53,78) → son (−71,66; 26,85): birinci bacak 164°, ikinci 254° yönünde (= +90°, sağa), her biri 28 m (1,4 × 20).
- `ruff format` + `ruff check` temiz.

## 4. S6: duran hayali insan — `21_08_57.ulg` — **Geçti**

**Oturum düzeni** Grup 4–5'teki gibi: parametre dosyası silindi, `PX4_PARAM_AF_ENABLE=1 HEADLESS=1 make px4_sitl gz_x500`, Position'da kalkış (simüle joystick), havada AUTO FOLLOW (`MAV_CMD_DO_SET_MODE` 1/4/11), oturum sonunda pilot kapanmadan `logger stop`, süreçler PID ile kapatıldı, log özgün adıyla kopyalandı, parametre dosyası yine silindi. `AF_K_FF` = 0, diğer `AF_*` varsayılan (`AF_YAWRATE_MAX` = 60, `AF_ALPHA` = 0,5, `AF_BETA` = 0,17; oturum başında `param show` ile görüldü). İrtifa 9,92–9,98 m (elle kalkış) → istenen mesafe **15,48 m** (spec'in 15,6 m'si h = 9,0 m ile; burada h ≈ 8,94 m).

**Verilen:** tek oturumda 5 giriş; her girişte gönderici yeniden başlatıldı: `--cevrim kapali --hedef-mesafe {10, 15, 20, 25, 30} --hedef-aci 30` (hedef burnun 30° sağında, yerde, bakılan nokta 1 m yükseklikte), 30 s AUTO FOLLOW, sonra Position. Ölçüm: `af_log_analiz.py 21_08_57.ulg --grafik ... --csv ...` (her mesafe bir bölüm).

**Drone ne yaptı:** her girişte burnunu 30° sağa, hedefe çevirdi ve aynı anda hedefe doğru yaklaştı (10 m'de geri çekildi), istenen 15,5 m'ye yerleşti ve orada kaldı; irtifa ve burun sabit, salınım yok.

| Başlangıç mesafesi | 10 m | 15 m | 20 m | 25 m | 30 m |
|---|---|---|---|---|---|
| Bölüm (t, s) | 1 (35,4–65,4) | 2 (72,0–102,0) | 3 (108,6–138,6) | 4 (145,2–175,2) | 5 (181,7–211,7) |
| İlk mesafe hatası | −5,47 m (geri) | −0,49 m | +4,52 m | +9,53 m | +14,48 m |
| **Oturma süresi** (±0,3 m) | 4,78 s | **1,64 s** | 4,40 s | 6,76 s | 9,22 s |
| **Aşma** | 0,03 m | 0,05 m | 0,04 m | 0,04 m | 0,01 m |
| **Salınım:** işaret değişimi / son 5 s tepe-tepe | 0 / 0,05 m | 0 / 0,07 m | 0 / 0,08 m | 0 / 0,05 m | 0 / 0,05 m |
| Son 5 s mesafe hatası | 0,00 m | +0,01 m | 0,00 m | −0,01 m | +0,03 m |
| **Kırpma süresi** (kural > 2 m/s) | 1,68 s | **0** | 1,20 s | 3,68 s | 6,06 s |
| Kuralın en büyük isteği | 2,73 m/s | 0,25 m/s | 2,26 m/s | 4,76 m/s | 7,24 m/s |
| **Burun oturma süresi** (±2°) | 2,62 s | 2,64 s | 2,52 s | 2,58 s | 2,60 s |
| **Burun aşması** | 5,5° | 7,5° | 6,9° | 6,8° | 6,9° |
| Son 5 s burun hatası (gerçek yön − hedef yönü) | 0,0° | 0,0° | 0,0° | 0,0° | 0,0° |
| Kestirilen hedef hızı en büyük (hedef duruyor) | 0,49 m/s | 0,39 m/s | 1,10 m/s | 1,59 m/s | 2,25 m/s |
| Kestirilen hedef hızı son 5 s | 0,01 m/s | 0,01 m/s | 0,00 m/s | 0,00 m/s | 0,00 m/s |
| `latency` ortalama (en küçük–en büyük) | 58 (54–70) ms | 58 (54–62) ms | 58 (54–62) ms | 58 (54–62) ms | 58 (54–62) ms |
| Kabul / atılan mesaj | 600 / 0 | 600 / 0 | 601 / 0 | 601 / 0 | 601 / 0 |

Beklenen (spec S6): `range_est → range_desired` (15,6 m; burada 15,48 m), burun hedefte, salınım yok. **Beşinde de sağlandı.** Hız isteği hiç 2,00 m/s'yi, değişim hızı hiç 3,00 m/s²'yi geçmedi; yaw hiç donmadı (hedef hep > 1 m uzakta); durum hep TAKIP.

**"En ideal başlangıç mesafesi" (kullanıcının sorusu) — sade anlatım:**

- **Drone her durumda aynı yere gidiyor.** Durduğu mesafeyi başlangıç değil, **irtifa ve takip açısı** belirliyor: istenen mesafe = (irtifa − hedefin bakılan noktasının yüksekliği) / tan(`AF_TRK_ANG`) = (9,94 − 1,0) / tan 30° ≈ **15,5 m**. Beş koşunun beşinde de drone 15,48 m'ye yerleşti, son 5 s hatası ±0,03 m. Başlangıç mesafesi yalnızca **oraya nasıl gittiğini** değiştiriyor.
- **En iyisi, istenen mesafeye en yakın başlamak (bu testte 15 m):** 1,6 s'de oturdu, hız sınırına hiç dayanmadı (kırpma 0), drone neredeyse hiç kımıldamadı (en çok 0,21 m/s). Kalan 1,6 s'nin çoğu burnun 30° dönüşünün yarattığı küçük kaymadır.
- **Uzaklaştıkça süre doğrusal uzuyor:** drone hedefe 2 m/s'den hızlı gidemediği için (`AF_VEL_MAX`) 20 m'de 4,4 s, 25 m'de 6,8 s, 30 m'de 9,2 s. Ama **kalite bozulmuyor**: aşma hep ≤ 0,05 m, salınım yok. Yani 30 m'den başlamak da güvenli, yalnızca daha uzun sürüyor.
- **Yakından (10 m) başlamak da sorun değil:** drone geri çekildi, 4,8 s'de oturdu (aynı büyüklükteki 20 m'lik ileri yaklaşmayla hemen hemen aynı: 4,4 s).
- **Pratik sonuç:** pilot AUTO FOLLOW'u açarken hedefe ~15 m (± birkaç metre) uzaklıkta olursa takip en sakin başlar. Bu bir parametre değildir; istenen mesafe irtifa ya da `AF_TRK_ANG` değişince değişir (ör. 20 m irtifada ≈ 33 m). Uzak başlangıçta oturma süresini kısaltmanın yolu `AF_VEL_MAX`'ı artırmaktır (ilk uçuşlarda önerilmez).
- **Burun:** 30°'lik dönüş 60°/s ile 0,5 s'de bitiyor ama drone 5,5–7,5° fazla dönüp geri geliyor ve ±2°'ye 2,5–2,6 s'de yerleşiyor. Bu, başlangıç mesafesinden bağımsız (beşinde de aynı). Neden ve seçenekler Bölüm 10, soru 3.

## 5. S7: yürüyen hayali insan (L yolu) — `21_14_07.ulg` — **Kısmen geçti** (`AF_K_FF` = 1,0'da titreşim, soru 2)

**Verilen:** tek oturumda iki giriş (62 s), aralarda Position. Gönderici `--cevrim kapali` (hedef burnun 20 m önü, `--hedef-mesafe`/`--hedef-aci` varsayılan), L yolu: hedef 10 s durur, sonra **1,4 m/s** ile 20 s drone'dan uzaklaşır, **90° sağa** dönüp 20 s yürür, durur. Bölüm 1: `AF_K_FF` = **0**; bölüm 2: `AF_K_FF` = **1,0** (`param set`, logda değişiklik kaydı var; script iki bölümü doğru parametreyle gösterdi). Diğer `AF_*` varsayılan; **`AF_ALPHA` / `AF_BETA` değiştirilmedi.** İrtifa 9,92–9,94 m, istenen mesafe 15,46 m. Yürüme başlangıcı logda ölçülen hedef yerinin kımıldamasından bulundu: bölüm 1'de t ≈ 45,9 s, bölüm 2'de t ≈ 115,0 s (girişten ~9 s sonra); bacak pencereleri buna göre (`--aralik`).

**Drone ne yaptı:** iki koşuda da önce 20 m'den 15,5 m'ye yaklaştı, hedef yürüyünce arkasından gitti, köşede sağa döndü ve hedefi izledi, hedef durunca yine 15,5 m'de durdu. `AF_K_FF` = 0'da hedefin ~2,8 m gerisinde kaldı; 1,0'da geride kalmadı ama hız kestirimi ve eğim titreşti.

| Ölçü | `AF_K_FF` = 0 (bölüm 1) | `AF_K_FF` = 1,0 (bölüm 2) | Beklenen |
|---|---|---|---|
| **Geride kalma: 1. bacak son 10 s mesafe hatası** (hedef uzaklaşıyor) | **+2,79 ± 0,02 m** | **+0,06 ± 0,06 m** | 0'da ≈ 1,4 / `AF_K_DIST` = **2,8 m**; 1,0'da ≈ 0 |
| 2. bacak son 10 s mesafe hatası (hedef sağa yürüyor) | +2,22 ± 0,22 m (artıyor, bacak sonunda 2,5 m) | +0,01 ± 0,07 m | 0'da < 2,8 (geometri, aşağıda); 1,0'da ≈ 0 |
| Yürüme başlarken en büyük hata | +2,80 m (geride kalmaya yerleşme) | +1,61 m (1–2 s'lik geçici) | — |
| Dönüşten sonraki 10 s | +0,70…+2,71 m | **−1,26**…+0,21 m (drone köşeyi kısa kesip hedefe yaklaştı) | — |
| Hedef durduktan sonra son 5 s hata | +0,06 m (tepe-tepe 0,05) | 0,00 m (**tepe-tepe 0,34 m**, 21 işaret değişimi bölüm boyunca) | ≈ 0, salınım yok |
| Oturma süresi (bölüm sonuna göre) | 52,1 s (hedef durduktan ~2,5 s sonra) | 31,6 s (dönüşten ~2,6 s sonra yerleşti) | — |
| Kırpma süresi | 1,18 s (yalnızca ilk yaklaşma) | 3,66 s | Yürürken kırpma yok |
| Drone hızı (1. bacak son 10 s) | 1,40 ± 0,01 m/s | 1,39 ± 0,02 m/s | 1,4 |
| **`target_vel_ned` (1. bacak son 10 s)** | **1,39 ± 0,04 m/s** | 1,39 ± **0,38** m/s (0,57–2,20; ~3 Hz) | 1,4 m/s, sakin |
| `target_vel_ned` (2. bacak son 10 s) | 1,39 ± 0,03 m/s | 1,43 ± 0,10 m/s | 1,4 |
| `target_vel_ned` hedef durunca (5–10 s sonra) | 0,01 m/s | **0,37 ± 0,21** m/s (~6 Hz) | 0 |
| Filtre hızı yürüme başında / dönüşte gerçek hıza yetişme | ~0,4 s / ~0,3 s | ~0,5 s / ~0,2 s | — |
| Girdi–çıktı uzaklığı ortalama (en büyük) | 0,01 (0,13) m | 0,05 (0,15) m | Küçük |
| Ölçümden türetilen hız ile filtre hızı farkı | 0,07 m/s | **0,35 m/s** | Küçük |
| Drone eğimi (pitch) std: 1. bacak / hedef durunca | 0,09° / 0,11° | **0,36° / 0,72°** | — |
| Burun: son 5 s gerçek yön − hedef yönü | 0,0° | 0,0° | 0 |
| `latency` ortalama (en küçük–en büyük) | 66 (62–70) ms | 66 (58–70) ms | — |
| Kabul / atılan mesaj | 1 241 / 0 | 1 241 / 0 | — |

**Yorum (sade):**

- **`AF_K_FF` = 0 (yalnız mesafe kuralı):** hedef 1,4 m/s ile uzaklaşırken drone ancak hatası kadar hız ister (0,5 × hata); 1,4 m/s'ye ulaşmak için 2,8 m hata gerekir. Ölçülen **2,79 m** spec'in beklediğiyle aynı. Hedef sağa dönünce drone ile hedef arasındaki doğru yavaş yavaş döner; drone o doğru boyunca gittiği için hedefin hızının yalnızca bir kısmı "uzaklaşma" olarak görünür, hata önce 0,7 m'ye iner, sonra doğru döndükçe 2,5 m'ye doğru yeniden büyür. Filtre hedefin hızını **1,39 m/s** ile doğru ve sakin buldu (std 0,03–0,04).
- **`AF_K_FF` = 1,0 (hedef hızı da eklenir):** drone **geride kalmadı** (1. bacakta +0,06 m, 2. bacakta +0,01 m); beklenen buydu. İki geçici etki var: yürüme başlarken filtre hızı öğrenene ve drone hızlanana kadar 1,6 m geride kaldı (2–3 s), köşede hız kestirimi eski yönde olduğu için drone köşeyi kısa kesip 1,26 m yaklaştı (3 s'de toparladı).
- **Ama hız kestirimi titreşiyor:** filtrenin hedef hızı 1,4 m/s civarında ±0,4 m/s (~3 Hz), hedef durduktan sonra da 0 yerine ~0,4 m/s civarında (~6 Hz) gidip geliyor; drone'un eğimi `AF_K_FF` = 0'a göre 4–7 kat fazla kıpırdıyor. Mesafe hatası yine küçük (±0,15 m), drone'un hızı sakin (std 0,02–0,07 m/s). **Olası neden (doğrulanacak):** S6'da da görülen "drone eğilirken ölçülen hedef yerinin kayması" (Bölüm 10, bilgi 2): gönderici yönü kendi aldığı tutumla, Pixhawk dünyaya kendi tutumuyla çeviriyor; aradaki küçük zaman farkı eğim değişirken hedefi birkaç desimetre kaydırıyor. `AF_K_FF` > 0 iken bu sahte hız drone'un isteğine giriyor, eğimi değiştiriyor, yeni sahte hız doğuruyor: kapalı bir döngü. Gerçek uçuşta kameranın gecikmesi (V3) aynı etkiyi yapabilir. **`AF_ALPHA` / `AF_BETA` değiştirilmedi** (karar: önce kullanıcıya sorulur) → soru 2.

**Filtre girdisi ↔ çıktısı (kullanıcının vurgusu):** `_filtre` grafiklerinde (`~/m15-sitl-araclari/grup6/grafik_S7/21_14_07_bolum{1,2}_filtre.png`) ölçüm noktaları (girdi) ile kestirim (çıktı) L yolunun iki bacağında üst üste; konum çıktısı ölçümü 1–5 cm içinde izliyor. Hız çıktısı `AF_K_FF` = 0'da gerçek yürüme hızını 0,3–0,5 s'de buluyor ve sakin; `AF_K_FF` = 1,0'da ortalaması doğru ama titreşimli. Yani **konum kestirimi iki koşuda da iyi, hız kestirimi yalnız kendi başına (`AF_K_FF` = 0) iyi**; hız guidance'a geri beslenince titreşim başlıyor.

## 6. T1 batarya failsafe'i ve T2 GPS arızası (kod yok)

### 6.1 T1: batarya — `21_18_29.ulg` (+ ek `21_22_13.ulg`) — **Görüldü** (beklenen davranış, araya PX4'ün 5 s'lik Hold'u giriyor)

**Verilen:** `COM_LOW_BAT_ACT` = **3** (kritikte RTL, acilde Land; `commander_params.c:285-293`), simüle batarya `SIM_BAT_DRAIN` = 60 s (varsayılan: %100'den 0'a 60 s'de, yalnızca arm iken; `BatterySimulator.cpp:85-101`), taban `SIM_BAT_MIN_PCT` (`battery_simulator_params.c:56, 71`). Eşikler varsayılan: düşük `BAT_LOW_THR` %15, kritik `BAT_CRIT_THR` %7, acil `BAT_EMERGEN_THR` %5; `COM_FAIL_ACT_T` = 5 s. Kalkış ve takip boyunca taban %50 (varsayılan; batarya kalkıştan ~30 s sonra %50'de durur). Kapalı çevrimde duran hedefe (20 m önde) takipteyken taban **%6**'ya indirildi (kritik geçilir, acil geçilmez); RTL görüldükten sonra taban **%0** (acil).

| Olay | T1 `21_18_29.ulg` (t, s) | T1b `21_22_13.ulg` (t, s) | Beklenen |
|---|---|---|---|
| AUTO FOLLOW'a giriş (TAKIP) | 35,616 | 35,572 | — |
| "Low battery" (%15, `battery_status.warning` = 1) | 69,644 | 69,608 | Yalnızca uyarı |
| **"Critical battery"** (%7, warning = 2) | **74,624** | **74,480** | RTL |
| PX4: "Failsafe activated: entering Hold for 5 seconds" → `nav_state = 4` (Hold) | 74,636 | 74,492 | (kararda yoktu; `COM_FAIL_ACT_T` = 5 s, `commander_params.c:296-311`) |
| **Modül PASIF** (`mode_active` = 0, `state` = 0) | 74,656 (bir çevrim sonra) | 74,512 (bir çevrim sonra) | PASIF |
| **RTL** (`nav_state = 5`), "RTL: start return at 11 m" | **79,640** (+5,0 s) | **79,496** (+5,0 s) | RTL |
| "RTL: land at destination" (drone eve yakındı, hemen inişe başladı) | 81,668 | 81,628 | — |
| **"Emergency battery level"** (%5, warning = 3) | 97,076 — **drone zaten inmişti** (iniş 95,432) | **83,036, havada (~8 m)** | Land |
| **Land** (`nav_state = 18`) | 97,088 (yerde) | **83,048** | Land |
| İniş / disarm | 95,432 / 97,436 | 95,420 / 97,424 | — |
| `hold_request_count` (bölüm) | 0 | 0 | Modül hiçbir mod istemez |

- **Drone ne yaptı:** takip ederken kritik seviyede durdu (Hold, 5 s), sonra eve döndü (RTL) ve inişe geçti; T1b'de acil seviye inerken geldi ve PX4 RTL'i Land'e çevirdi; iki koşuda da yere inip disarm oldu. **AUTO FOLLOW kritik seviyenin ilk çevriminde kapandı, modül hiçbir istek göndermedi** (Hold isteği yok, setpoint yayını durdu).
- **Kararda olmayan bir adım:** PX4 failsafe eylemini (RTL) hemen değil, **5 s Hold'dan sonra** yapıyor (`COM_FAIL_ACT_T` = 5 s; "kullanıcı fark etsin" diye; bu sürede pilot mod değiştirebilir, ama çubukla devralamaz, `commander_params.c:296-302`). Takip açısından fark yok: modül Hold'un ilk çevriminde PASIF oluyor. Bilgi 3.
- T1'de acil seviye drone indikten sonra geldiği için uçuşta Land görülemedi; bu yüzden aynı oturum T1b olarak, RTL başladıktan ~2 s sonra taban %0 yapılarak tekrarlandı (sapma 3).
- Script'te bu bölümün çıkışı "Hold (nav_state 4) · Hold'a geçişi kim yaptı: PX4 (AUTO FOLLOW istemedi)" olarak görünür; son 5 s mesafe hatası T1'de −0,01 m, T1b'de 0,00 m (takip kesilene kadar normal).

### 6.2 T2: GPS arızası — `21_24_40.ulg` — **Sınanamadı: Gazebo Harmonic SITL'de `failure gps off` çalışmıyor**

**Verilen:** `SYS_FAILURE_EN` = 1 (`system_params.c:303`), takipte (kapalı çevrim, duran hedef) `failure gps off` (`src/systemcmds/failure/failure.cpp:59, 79`), 30 s sonra `failure gps ok`.

**Ne oldu:** hiçbir şey. Komut "inject failure unit: gps (4), type: off (1)" yazdı, ardından **"Timeout waiting for ack"** (`failure.cpp:155`): komuta kimse cevap vermedi. `sensor_gps.fix_type` log boyunca 3 (3D fix) kaldı, EKF GPS'i kullanmayı sürdürdü (`estimator_status_flags.cs_gnss_pos` = 1), yerel ve küresel konum hep geçerli, `nav_state` 23'te, modül 30 s boyunca TAKIP'te, `hold_request_count` 0, uyarı yok. `failure gps ok` da aynı şekilde cevapsız.

**Neden (kaynakta görüldü):** PX4 v1.17.0'da GPS arıza enjeksiyonunu yalnızca eski MAVLink simülatör köprüsü işliyor (`src/modules/simulation/simulator_mavlink/SimulatorMavlink.cpp:1247-1270`, jMAVSim / Gazebo Classic için). Gazebo Harmonic'te GPS `gz_bridge`'den geliyor (`ROMFS/px4fmu_common/init.d-posix/px4-rc.gzsim:148`; `GZBridge.cpp:751-774`) ve o modül `VEHICLE_CMD_INJECT_FAILURE`'ı dinlemiyor. Commander'ın arıza enjeksiyonu yalnızca motorları kapsıyor (`failure_detector/FailureInjector.cpp:56-60`).

### 6.3 T2b (ek deneme): GPS kaybı, EKF'nin GPS kullanımı kapatılarak — `21_26_42.ulg` — **Görüldü**

T2 sonuçsuz kaldığı için, kilitli dosyaya dokunmadan, **EKF'nin GPS'i kullanması uçuşta bir parametreyle kapatıldı**: `EKF2_GPS_CTRL` 7 → **0** (EKF2 bu parametreyi uçuşta okur, `src/modules/ekf2/EKF2.hpp:516`). Bu, "GPS anteni gitti" durumuna yakındır (GPS verisi gelir ama EKF kullanmaz). **Sapma 4** (kullanıcıya soruldu, soru 4).

| Olay | t (s) | Girişten / GPS kesilmesinden |
|---|---|---|
| AUTO FOLLOW (TAKIP) | 35,260 | — |
| `EKF2_GPS_CTRL` = 0 → EKF GPS'i bıraktı (`cs_gnss_pos` 1 → 0) | 47,252 | 0 |
| EKF yatay konumu ve hızı geçersiz (`xy_valid`, `v_xy_valid` = 0; `EKF2_NOAID_TOUT` = 5 s'lik GPS'siz tahminden sonra) | **51,252** | +4,0 s |
| `mc_pos_control`: "invalid setpoints", "Failsafe: blind land" (`MulticopterPositionControl.cpp:643, 664`) | 51,252 | +4,0 s |
| Modül: ilk mesaj `CHECK_POSITION` ile atıldı | 51,300 | +4,05 s |
| PX4 failsafe: **Descend** (`nav_state = 12`; konumsuz iniş) — "Failsafe activated" | **51,368** | +4,1 s |
| **Modül PASIF** | 51,380 | bir çevrim sonra |
| İniş / disarm | ~66 / 68,420 | — |

- **Drone ne yaptı:** GPS bırakıldıktan 4 s sonra PX4 konumun geçersiz olduğunu gördü ve aynı anda AUTO FOLLOW'dan çıkarıp **Descend** ile olduğu yerde alçalarak indirdi. AUTO FOLLOW'un kendi hedef kaybı yolu hiç başlamadı: konum geçersiz olunca yalnızca 2 mesaj `CHECK_POSITION` ile atılabildi (KAYIP_BEKLE'ye 0,5 s gerekirdi), **Hold isteği yok** (`hold_request_count` 0).
- **Hold reddi yolu (Grup 5 bilgi 2) yine görülmedi:** bizim mod yerel konumu, Hold küresel konumu ister; GPS gidince EKF ikisini **aynı anda** geçersiz yaptı (`failsafe_flags.local_position_invalid` ve `global_position_invalid` ikisi de 51,356'da 1). Bu durumda PX4'ün kendi failsafe'i (bizim modun `mode_req_local_position` gereksinimi, spec A10) önce devreye giriyor. Ret yolu yalnızca birim testinde sınanmış olarak kalıyor (doğrulanacak).
- 51,252–51,368 arasındaki ~0,1 s'de `mc_pos_control` kendi acil inişini ("blind land") yaptı: modül o çevrimlerde yatay hız 0, konum NaN yayınlıyordu (spec Bölüm 8, A10: konum geçersizken asıl tepki PX4'ün). PX4 davranışı, kod hatası değil.

## 7. Diğer görevler

### 7.1 `latency` (6.12)

| Oturum | Ortalama | En küçük–en büyük |
|---|---|---|
| S6 (5 bölüm, `21_08_57.ulg`) | 58 ms | 54–70 ms |
| S7 (2 bölüm, `21_14_07.ulg`) | 66 ms | 58–70 ms |
| Grup 5 S4 (`19_18_27.ulg`, script'le) | 62 ms | 58–70 ms |

- `latency` = (Pixhawk'ın mesajı işlediği an − varış) + Pi'nin bildirdiği yaş. SITL'de yaş sabit **50 ms** (gönderici `--yas`, gerçek bir ölçüm değil), işlem payı **4–20 ms** (50 Hz çevrim; değerler SITL'in 4 ms'lik adımının katları). Yani SITL'deki sayının 50 ms'si varsayımdır; gerçek gecikme Pi'nin görüntü işleme süresine bağlı olacak.
- **m13/m16 için veri:** S6–S7'de tutum değişirken ölçülen hedef yerinde desimetre düzeyinde kayma ve `AF_K_FF` = 1,0'da hız kestiriminde titreşim görüldü (Bölüm 5). Gecikme telafisi (LOS'u görüntünün çekildiği andaki tutumla çevirmek, V3) bu etkiyi azaltabilir; gerçek gecikme Pi ile ölçülünce karar verilmeli. `requirements.md` §1.3'e yazıldı.

### 7.2 S1–S5 yeniden koşulmadı (6.13)

Grup 5'ten (son SITL koşuları `19_18_27`–`19_25_29`) sonra PX4 kodunda tek değişiklik soru 3-b'dir (EKF **yön** sıfırlamasında filtre sıfırlaması, bir satır); SITL'de yön sıfırlaması olmadığı için hiçbir senaryoyu etkilemez. Grup 6'da PX4 kodu değişmedi. Bu yüzden S1–S5 yeniden koşulmadı; S6–S7 son kodla koşuldu.

### 7.3 Sözlük ↔ kod (6.5)

PX4 kodu bu grupta değişmediği için derlemeler, flash kaydı ve birim testi tekrarlanmadı (6.5 "kod değiştiyse"); son değerler Grup 5'teki gibi: 6C flash **1 937 260 B (%98,53)**, birim testi 12/12. `log-sozlugu.md` son kodla karşılaştırıldı (script'le): `msg/AutoFollowStatus.msg`'deki 39 alanın, 4 `STATE_*` ve 10 `CHECK_*` sabitinin hepsi sözlükte, değerleri aynı; `module.yaml`'daki 17 parametrenin hepsi sözlükte, varsayılan/birim/aralık aynı. Sözlüğe bu grupta yalnızca göndericinin yeni seçenekleri, analiz script'i ve rehber satırları eklendi (sürüm 8).

## 8. Sapmalar (planlanandan farklı yapılanlar)

1. **S6 tek oturumda 5 bölüm, S7 tek oturumda 2 bölüm** (her koşu ayrı log yerine). Parametre dosyası her oturumdan önce ve sonra silindi; S7'de `AF_K_FF` bölümler arasında `param set` ile değişti (logda kayıtlı, script doğru gösteriyor). Analiz script'inin bölüm bulmasını da sınamış oldu.
2. **Analiz script'ine istenenlerin dışında üç ölçü eklendi:** "gerçek yön − hedef yönü" (burnun hedefe gerçekten bakıp bakmadığı; S6'nın "burun hedefte" beklentisinin doğrudan ölçüsü), "burun aşması" ve "burun oturma süresi" (±2°). S6'da burnun 5–7° aşması bunlarla görüldü.
3. **T1b ek oturumu:** T1'de acil seviye drone indikten sonra geldi; uçuşta Land'i görmek için tekrarlandı.
4. **T2b ek deneme (`EKF2_GPS_CTRL` = 0):** `failure gps off` Gazebo Harmonic'te desteklenmediği için. tasks'ta yoktu; yalnızca parametre, kod yok. Kullanıcıya soruldu (soru 4).
5. **S7'nin açılması:** komut satırı seçeneği yerine dosyadaki sabit (`HEDEF_YOL`) ve repo dışı bir sarmalayıcı (`~/m15-sitl-araclari/af_los_gonder_L.py`); ad uydurmamak için (soru 1).
6. **Yürüme başlangıcı** gönderici başladıktan 10 s sonra (kararda yoktu; kod içi, §5.1 G6.4).
7. Test yardımcıları (repo dışı, `~/m15-sitl-araclari/`): `pilot.py`'de `start_sender`'a `script` seçeneği; yeni `S6.py`, `S7.py`, `T1.py`, `T1b.py`, `T2.py`, `T2b.py`, `af_los_gonder_L.py`, `analiz_t.py`, `grup6/analiz_s7_ek.py`; `BENIOKU.md` güncellendi.

## 9. Çıkan sorunlar ve çözümleri

1. **Script'in ilk sürümünde Markdown tablo bozuluyordu:** ölçü adlarındaki `|vel_cmd|` gibi mutlak değer çizgileri tablo sütun ayracıyla karıştı. Adlar "büyüklüğü", "(mutlak)" diye yeniden yazıldı; hücrelerde kalabilecek `|` işaretleri kaçışla yazılıyor.
2. **"Salınım: oturduktan sonra tepe-tepe"** ilk sürümde oturma anından sonraki bütün hatayı içeriyordu ve bandın içindeki yaklaşma kuyruğunu da salınım sayıyordu (kapalı çevrim kısa kontrolde 0,34 m). Kararlı hâli ölçmesi için "son 5 s tepe-tepe" yapıldı (aynı logda 0,05–0,08 m).
3. **PX4'ün failsafe Hold'u script'te bizim Hold'umuz gibi ölçülüyordu** (Bölüm 2'nin sonu); düzeltildi.
4. **T2'de GPS arızası enjekte edilemedi** (Bölüm 6.2); T2b ile ek deneme.
5. SITL tuzakları (Grup 4–5 notları) bu grupta sorun çıkarmadı: stdin `sleep infinity |`, pilot kapanmadan `logger stop`, süreçler PID ile, `pgrep -f` kalıpları kendi komut satırımla aynı satırda kullanılmadı (kontrol `pgrep -x px4`). Her oturumdan sonra px4/gz yok ve parametre dosyası silinmiş.

## 10. Kullanıcıya sorulacaklar

**Soru 1 — S7 yolunu komut satırından açmak için bir seçenek eklensin mi? (ad sizin)** Şimdi S7, `tez/sitl/af_los_gonder.py`'de `HEDEF_YOL = ()` satırı `HEDEF_YOL = L_YOLU` yapılarak açılıyor (karar "sabitlerle, yeni komut satırı adı yok" diyordu; açma yolunu söylemiyordu).
- (a) Böyle kalsın (dosyadaki sabit). Artı: yeni ad yok, kod hazır. Eksi: S7'yi koşmak için dosyayı düzenlemek (ve geri almayı unutmamak) gerekiyor; testte repo dışı sarmalayıcı kullanıldı.
- (b) Yeni bir seçenek (ör. bir yol adı alan bir `--...` seçeneği); **adı ve biçimi sizin**. Artı: S7 tek komutla, dosya değişmeden tekrarlanır (m06'ya taşınırken de). Eksi: yeni bir ad, sözlüğe girer.
- **Öneri: (b)** (tekrarlanabilirlik), ad sizden.

**Soru 2 — `AF_K_FF` = 1,0'da hedef hızı kestirimindeki titreşim (S7, Bölüm 5).** Geride kalma kalktı (2,8 m → 0,06 m), ama filtrenin hedef hızı ±0,4 m/s (~3–6 Hz) titreşiyor, hedef durunca 0'a inmiyor (~0,4 m/s), drone'un eğimi 4–7 kat fazla kıpırdıyor; mesafe hatası yine küçük (±0,15 m). Kanıt: hız düzeltmesi `v̂ += (β/Δt)·r` (`src/modules/auto_follow/AlphaBetaFilter.hpp:84`; 20 Hz'de her ölçümde artığın 0,17 / 0,05 = 3,4 katı hıza ekleniyor); LOS dünyaya mesajın işlendiği andaki tutumla çevriliyor, gecikme telafisi yok (`AutoFollow.cpp:293`, V3); `AF_K_FF` = 0'da aynı yol sakin (std 0,03–0,04 m/s), S6'da duran hedefte drone hızlanırken 0,4–2,3 m/s sahte hız görüldü.
- (a) Böyle kalsın; `AF_K_FF` varsayılanı zaten 0, ilk uçuşlarda 0 kalır; ayar ve gecikme telafisi m13/m16'da. Artı: kod ve parametre değişmez. Eksi: yürüyen hedefte 2,8 m geride kalma sürer.
- (b) SITL'de `AF_BETA` (ve gerekirse `AF_ALPHA`) için kısa bir tarama yapılsın (ör. β 0,17 / 0,08 / 0,04, `AF_K_FF` = 1,0, aynı L yolu) ve sonuca göre varsayılan sizinle seçilsin. Artı: titreşim büyük olasılıkla azalır (β küçüldükçe hız kestirimi sakinleşir). Eksi: hız kestirimi yavaşlar (yürüme başında ve dönüşte geride kalma artar); zaman.
- (c) `AF_K_FF`'in 1,0 yerine daha küçük bir değerle (ör. 0,5) denenmesi. Artı: döngü kazancı yarıya iner. Eksi: geride kalma 1,4 m kalır.
- (d) Gecikme telafisi (LOS'u görüntünün çekildiği andaki tutumla çevirmek; tutum geçmişi tutmak gerekir). Artı: sahte hızın kaynağına iner. Eksi: kod ve flash (~%98,5 dolu); kapsam m13/m16.
- **Öneri: (a)**, m13 için (b) ve (d) not olarak (`requirements.md` §1.3'e yazıldı). İsterseniz (b) bu dalda kısa bir SITL taraması olarak yapılabilir; **`AF_ALPHA`/`AF_BETA` sizin onayınız olmadan değiştirilmedi.**

**Soru 3 — Burun 30°'lik dönüşte 5–7° fazla dönüp geri geliyor (S6).** Yerleşme 2,5–2,6 s; son hata 0,0°. Kanıt: modül yalnızca açı (`yaw`) veriyor, dönüş hızı (`yawspeed`) NaN (`AutoFollow.cpp:414`); açı isteği 60°/s ile rampalanıp birden duruyor ve PX4'ün tutum kontrolcüsü bunu aşmayla izliyor. PX4'ün otomatik modları açıyı yumuşatıp dönüş hızını da veriyor (`FlightTaskAuto.cpp:306-316`, `_heading_smoothing`).
- (a) Böyle kalsın (m13'e not). Artı: kod yok. Eksi: dönüşlerde ~1 s'lik 5–7° salınım (kamerada hedef biraz kayar).
- (b) `trajectory_setpoint.yawspeed`'e sınırlanmış açı değişim hızı da yazılsın (küçük kod; flash birkaç yüz bayt). Artı: aşma büyük olasılıkla azalır (doğrulanacak). Eksi: PX4 kodu değişir, yeniden derleme, flash, SITL.
- (c) `AF_YAWRATE_MAX` küçültülsün (QGC'den). Artı: kod yok. Eksi: hedefe dönüş yavaşlar.
- **Öneri: (a)** (m15 kapsamında yeterli; m13'te (b) değerlendirilsin).

**Soru 4 — T2 (GPS arızası): ek deneme kabul mü?** `failure gps off` Gazebo Harmonic SITL'de çalışmıyor (Bölüm 6.2, `SimulatorMavlink.cpp:1263` yalnızca eski simülatörlerde). Ek deneme `EKF2_GPS_CTRL` = 0 ile yapıldı (Bölüm 6.3): 4 s sonra PX4 Descend ile indirdi, modülün Hold yolu devreye girmedi.
- (a) T2 bu ek denemeyle tamam sayılsın. Artı: gerçek "GPS kaybı" sonucunu gösteriyor, kod yok. Eksi: GPS verisi gelmeye devam ediyor (yalnızca EKF kullanmıyor), anten kopmasıyla birebir aynı değil.
- (b) Başka bir simülatörde (`failure gps off`'u destekleyen SIH ya da jMAVSim) denensin. Artı: komutun kendisi sınanır. Eksi: yeni simülatör hedefi, sabit sürüm kaydı gerekir (çatı kural 4–5); m06'nın kapsamı.
- (c) m16'ya bırakılsın. 
- **Öneri: (a).**

**Bilgi 1 — S6 "en ideal başlangıç mesafesi":** istenen mesafeye en yakın başlangıç (bu testte 15 m; 10 m irtifada ≈ 15,5 m) en sakin başlangıçtır; drone her durumda aynı yere yerleşir (Bölüm 4).

**Bilgi 2 — Drone hızlanırken sahte hedef hızı:** duran hedefte bile filtrenin hedef hızı drone hızlanırken birkaç saniye 0,4–2,3 m/s'ye çıkıyor (S6). `AF_K_FF` = 0 iken etkisi yok. Gerçek uçuşta kamera gecikmesiyle benzeri beklenir (V3).

**Bilgi 3 — Batarya failsafe'inde 5 s'lik Hold:** `COM_LOW_BAT_ACT` = 3 ile kritik seviyede PX4 önce 5 s Hold'da bekliyor, sonra RTL (`COM_FAIL_ACT_T` = 5 s). AUTO FOLLOW kritik seviyenin ilk çevriminde kapanıyor. Gerçek uçuşta pilot bu 5 s içinde mod değiştirebilir.

## 11. Kontroller

| Kontrol | Sonuç |
|---|---|
| `ruff format` + `ruff check` (`tez/analiz/af_log_analiz.py`, `tez/sitl/af_los_gonder.py`; ruff 0.16.9) | Temiz |
| Analiz script'i Grup 4–5 loglarında | Elle ölçülen bütün sayılarla aynı (Bölüm 2) |
| PX4 kodu | Değişmedi → iki derleme ve birim testi tekrarlanmadı (6.5). `make px4_sitl` güncel; `make px4_fmu-v6c_default` güncel ve **FLASH 1 937 260 B / 1920 KB (%98,53)**, boş 28 820 B (Grup 5 sonuyla aynı) |
| `log-sozlugu.md` ↔ kod | 39 alan, 14 sabit, 17 parametre aynı (Bölüm 7.3) |
| `tez/pin/verify_pin.sh --worktree` | Beklenen kırmızı: yine **15 dosya, hepsi onay bekleyen 7 yolda**; yeni yol yok (`tez/analiz/`, `tez/sitl/` izinli `tez/*` içinde). `allowed-paths.txt`'e dokunulmadı |
| Loglar | 6 oturumun ULog'u `~/Desktop/AUTO-FOLLOW LOG/`'da özgün adlarıyla: `21_08_57.ulg` (S6), `21_14_07.ulg` (S7), `21_18_29.ulg` (T1), `21_22_13.ulg` (T1b), `21_24_40.ulg` (T2), `21_26_42.ulg` (T2b). Repoya log, grafik, CSV girmedi |
| Süreçler | Her oturumdan sonra ve en sonda px4/gz süreci yok (`pgrep -x px4`, `pgrep -f "[g]z sim"`), parametre dosyası silinmiş |
