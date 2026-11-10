# Görev grubu 2: Doğrulama, geometri, alpha-beta, guidance, setpoint, log mesajı

- **Tarih:** 2026-11-10 · **Dal:** `ozellik/m15-takip-kodu` · **Görev listesi:** `../tasks.md` Grup 2 (2.1–2.16, log mesajı 2.L1–2.L6; geri dönüş 2.LF yapılmadı, gerekmedi)
- **Durum:** Bitti. İki derleme geçti, kısa SITL kontrolü geçti. `verify-pin` CI'da Hüseyin'in izin listesi PR'ı gelene kadar kırmızı kalır (beklenen). Uçuş davranışı (moda girip takip etmek) bu grupta **denenmedi**; o Grup 4'ün işi.
- Bu not kod okumadan anlaşılacak şekilde yazıldı. Adların anlamı `../log-sozlugu.md`'de.

## 1. Ne yapıldı?

Grup 1'deki iskelete modun asıl işi eklendi. Modül artık her 20 ms'de şunları yapar:

1. Pi'den gelen `AF_LOS` mesajını okur ve **9 kontrolden** geçirir. Geçemeyen mesaj atılır ve nedeniyle sayılır.
2. Geçen mesajdan hedefin yerdeki yerini bulur (düz zemin kabulü).
3. Bu yeri **alpha-beta filtresiyle** yumuşatır; hedefin hızını da kestirir.
4. Mod açıksa hız kuralını (guidance) çalıştırır, hızı sınırlar, burnu hedefe çevirir ve PX4'e `trajectory_setpoint` gönderir.
5. Hedef kaybolursa yerinde bekler (KAYIP_BEKLE), süre dolunca HOLD_ISTENDI durumuna geçer. **PX4'ten Hold'u isteyen komut Grup 5'te yazılacak**; şimdilik drone HOLD_ISTENDI'de yerinde beklemeye devam eder ve `hold_request_count` 0 kalır.
6. Her çevrimde, mod kapalıyken de, **`auto_follow_status`** log mesajını yayınlar; bu mesaj her logda kendiliğinden kaydedilir.

### Dosyalar

| Dosya | Ne | Yeni mi? |
|---|---|---|
| `src/modules/auto_follow/AutoFollowGuidance.hpp`, `.cpp` | Saf hesaplar: 9 kontrolün ilk 7'si, geometri (kontrol 8–9), hız kuralı, hız kırpma, ivme sınırı, durum makinesi, süreler | Yeni |
| `src/modules/auto_follow/AlphaBetaFilter.hpp` | Alpha-beta filtresi (yatay x, y) | Yeni |
| `src/modules/auto_follow/AutoFollow.hpp`, `.cpp` | Modül: girdiyi okur, hesapları çağırır, setpoint ve log mesajını yayınlar, `auto_follow status` çıktısı | Değişti |
| `src/modules/auto_follow/CMakeLists.txt` | `AutoFollowGuidance` kütüphanesi (`px4_add_library`), modül ona bağlı | Değişti |
| `msg/AutoFollowStatus.msg` | Log mesajı: 39 alan, `STATE_*` ve `CHECK_*` sabitleri | Yeni |
| `msg/CMakeLists.txt` | Mesaj listesine bir satır (`AutoFollowStatus.msg`, alfabetik yerine) | Bir satır |
| `src/modules/logger/logged_topics.cpp` | `add_default_topics` içine `add_topic("auto_follow_status");` (aralıksız; alfabetik yerine) | Bir satır |

Hepsi Hüseyin'e iletilecek 7 yolun içinde. `tez/pin/allowed-paths.txt`'e dokunulmadı. `AutoFollowGuidanceTest.cpp` Grup 3'te yazılacak.

## 2. Neden böyle? (spec bölümü / karar)

| Ne | Neden | Kaynak |
|---|---|---|
| Hesaplar ayrı kütüphanede, uORB ve parametre okumadan, zamanı argüman alarak | Birim testiyle (Grup 3) drone'suz sınanabilsin | "İç düzen" kararı, spec Bölüm 11, tasks 2.1 |
| 9 kontrol spec'teki sırayla, ilk geçilemeyen sonucu belirler | — | spec Bölüm 2, tasks 2.3 |
| "Hedef yok" (bayrak 0) atılan mesaj sayılmaz, ayrı sayılır, uyarı basılmaz | Bozuk veri değil | spec Bölüm 2 |
| LOS, PX4'ün tutum bilgisiyle dünyaya çevrilir; mesafe düz zemin kabulüyle | — | spec Bölüm 3, V3, V4, V5 |
| Filtre yatayda; tahmin her çevrim, düzeltme yalnız kabul edilen mesajda; Δt çekim anlarından; ilk mesajda hız 0; EKF sıfırlamasında filtre sıfırlanır | — | spec Bölüm 4, C2 |
| Sıra: kural → `AF_VEL_MAX` kırpması → `AF_ACC_MAX` ivme sınırı; ivme sınırı moda girişteki hızdan başlar | Geçişte sıçrama olmasın | spec Bölüm 5, C2 |
| İvme sınırı vektörün **büyüklüğüne** uygulanır (PX4'ün `SlewRate`'i kullanılmadı) | `SlewRate` her ekseni ayrı sınırlar; çapraz giderken değişim √2 kat olur. Spec "komut her çevrimde en fazla `AF_ACC_MAX · Δt` değişir" diyor; bunu her yönde sağlamak için küçük bir yardımcı fonksiyon yazıldı | spec "Existing Code" (öneri), tasks 2.6 |
| Yaw = hedefe bakış; hedef `AF_YAW_MIN_D`'den yakınsa son yaw; irtifa moda girişteki | — | spec Bölüm 6 |
| Durum makinesi ve hedefsiz girişte `max(son geçerli, giriş)` | — | spec Bölüm 7, A3 |
| Mod açıkken her çevrimde setpoint, kapalıyken hiç | Yayın kesilince PX4 son isteği uygulamaya devam eder; bu yüzden modül susmaz, aktif olarak hover ister (çatı standardındaki "setpoint üretmeyi bırak" kuralıyla çelişki notu, `error-handling.md:4` ↔ `MulticopterPositionControl.cpp:438`) | spec Bölüm 8 |
| Yerel konum geçersizken yatay konum NaN, yatay hız 0 | Tutma noktası anlamsız; asıl tepkiyi PX4'ün konum gereksinimi verir | spec Bölüm 8, A10 |
| Kendi log mesajımız, varsayılan listede, aralıksız, PASIF'te de | Kullanıcı ayar açmadan her logda olsun; masa testinde de görülsün | spec Bölüm 9, L2-b, C2 |
| Log mesajı Grup 2'de | S1–S5 ölçümleri ilk seferde tam alınsın | Karar 2026-11-10 ("1-a") |

## 3. Nasıl çalışıyor? (bir çevrim, sırayla)

Her 20 ms'de, Grup 1'deki kayıt ve arming check adımlarından sonra:

1. **Zaman ve araç durumu.** Bir önceki çevrimden beri geçen süre (Δt) ölçülür. PX4'ün yerel konumu ve tutumu okunur. EKF konumu sıfırladıysa (sıfırlama sayaçları değiştiyse) filtre unutulur; bir sonraki kabul edilen mesaj onu yeniden kurar.
2. **Filtre tahmini.** Filtre kurulmuşsa kestirilen hedef konumu, kestirilen hızla Δt kadar ilerletilir. Bu, mod kapalıyken de yapılır.
3. **Yeni `AF_LOS` mesajı varsa:**
   - Kontroller sırayla: (1) ad `AF_LOS` mı · (2) altı sayı geçerli mi (NaN/sonsuz değil) · (3) LOS'un uzunluğu 1'e `AF_NORM_TOL` kadar yakın mı · (4) sıra no bir öncekinden büyük mü · (5) gerçek yaş = (şimdi − varış) + Pi'nin yazdığı yaş, `AF_DATA_TOUT`'tan küçük mü · (6) hedef bayrağı 1 mi · (7) drone'un yerel konumu geçerli mi.
   - Ham değerler (LOS, yaş, sıra no, bayrak, varış anı) log mesajının `los_*` alanlarına yazılır; mesaj kontrollerden geçmese de. **İstisna:** adı `AF_LOS` olmayan mesaj başka bir programındır; yalnızca sayılır, `los_*` alanlarına yazılmaz (bkz. Bölüm 7, soru 1).
   - İlk 7 kontrol geçtiyse **geometri:** LOS dünyaya çevrilir (`los_ned`), aşağı bakış açısı bulunur (`depression`); (8) bu açı `AF_MIN_DEP`'ten küçükse atılır. Yükseklik farkı h = drone yüksekliği − `AF_GND_OFS` − `AF_TGT_HGT` (`height_diff`), yatay mesafe d = h / tan(açı) (`range_meas`); (9) h ≤ 0 ya da d, 0 ile `AF_MAX_RNG` arasında değilse atılır. Geçerse hedefin yeri = drone konumu + d × yatay yön (`target_meas_ned`).
   - 9 kontrolü geçen mesaj **filtreyi düzeltir** (`filter_updated` = 1): ilk mesajda filtre bu konuma ve hız 0'a kurulur; sonrakilerde fark `AF_ALPHA` oranında konuma, `AF_BETA / Δt` oranında hıza eklenir. Buradaki Δt, iki mesajın tahmini çekim anı (varış − yaş) arasındaki süredir. Mesajın varış anı "son geçerli mesaj" olarak saklanır; toplam gecikme `latency` alanına yazılır.
   - Sonuç `check_result`'a yazılır, ilgili sayaç bir artar. Atılan mesaj için konsola **en fazla saniyede bir** uyarı basılır (`input sample rejected: CHECK_...`).
4. **Durum makinesi** (bkz. Bölüm 4).
5. **Mod açıksa setpoint:**
   - Moda girişin ilk çevriminde: o anki irtifa saklanır (`alt_hold_z`), ivme sınırlayıcı drone'un o anki yatay hızından başlar, yaw başlangıcı drone'un o anki yönüdür.
   - **TAKIP:** kestirilen hedefe yatay mesafe (`range_est`), istenen mesafe = son kabul edilen mesajın h'si / tan(`AF_TRK_ANG`) (`range_desired`); kural `AF_K_FF × hedef hızı + AF_K_DIST × (range_est − range_desired) × hedefe yön` (`vel_cmd_law`); önce `AF_VEL_MAX`'a kırpılır, sonra bir çevrimde en fazla `AF_ACC_MAX × Δt` değişir (`vel_cmd`). Yaw hedefe bakar; hedef `AF_YAW_MIN_D`'den yakınsa son yaw tutulur (`yaw_frozen` = 1). PX4'e: yatay hız = `vel_cmd`, irtifa = `alt_hold_z`, yaw = `yaw_cmd`.
   - **KAYIP_BEKLE ve HOLD_ISTENDI:** kayıp anındaki yatay konum tutulur, yatay hız 0, irtifa `alt_hold_z`, son yaw. Hız komutu 0'a çekilir; takip geri gelince ivme sınırı 0'dan başlar.
   - **Yerel konum geçersizse** (her durumda): yatay konum NaN, yatay hız 0.
   - Kullanılmayan bütün alanlar NaN. Her eksende bir değer sonlu kalır, x ve y aynı türde; PX4'ün geçerlilik kuralı sağlanır (`PositionControl.cpp:224-250`).
6. **Mod kapalıysa (PASIF):** setpoint yayınlanmaz; guidance alanları (`vel_cmd_law`, `vel_cmd`, `range_est`, `range_desired`, `yaw_cmd`, `alt_hold_z`) NaN yazılır. Doğrulama, geometri ve filtre yine çalışır.
7. **Log mesajı** her çevrimde yayınlanır.

## 4. Durum makinesi (zaman çizelgesi)

| Durumdan | Ne olunca | Duruma | Hold sayacı (`lost_time`) nereden başlar |
|---|---|---|---|
| herhangi | PX4'ün modu artık AUTO FOLLOW değil | PASIF | — |
| PASIF | moda girildi, son 0,5 s içinde geçerli mesaj var ve ondan sonra "hedef yok" gelmedi | TAKIP | — |
| PASIF | moda girildi, geçerli hedef yok | KAYIP_BEKLE | giriş + `AF_DATA_TOUT` (yani Hold girişten 1,5 s sonra, A3) |
| TAKIP | "hedef yok" mesajı geldi | KAYIP_BEKLE (hemen) | o mesajın varış anı (Hold 1,0 s sonra) |
| TAKIP | `max(son geçerli, giriş)`'ten beri `AF_DATA_TOUT` doldu | KAYIP_BEKLE | `max(son geçerli, giriş)` + `AF_DATA_TOUT` (Hold toplam 1,5 s) |
| KAYIP_BEKLE | yeni geçerli mesaj geldi | TAKIP | — |
| KAYIP_BEKLE | `lost_time` ≥ `AF_LOST_T` | HOLD_ISTENDI | — |
| HOLD_ISTENDI | — (kendiliğinden takibe dönülmez) | yalnızca PASIF'e | — |

- "Geçerli mesaj" = 9 kontrolün hepsini geçen mesaj. Zamanlar mesajın **varış** anına göredir.
- `time_since_valid` mod açıkken `max(son geçerli, giriş)`'ten beri geçen süredir; PASIF'te son geçerli mesajdan beri geçen süre, hiç geçerli mesaj gelmediyse NaN.
- `lost_time` yalnızca KAYIP_BEKLE ve HOLD_ISTENDI'de artar; TAKIP ve PASIF'te 0. Hedefsiz girişte ilk `AF_DATA_TOUT` (0,5 s) boyunca 0 kalır, sonra sayar: böylece "`lost_time` `AF_LOST_T`'yi geçince Hold" kuralı (sözlük) A3 ile birlikte her durumda doğru kalır.

## 5. Nasıl test edildi?

### 5.1 Derlemeler

| Derleme | Sonuç |
|---|---|
| `make px4_sitl_default` | Geçti. Modül ve kütüphane uyarısız (PX4 uyarıları hata sayar, `-Werror`; `-Wfloat-equal`, `-Wdouble-promotion`, `-Wshadow` dahil). |
| `make px4_fmu-v6c_default` | Geçti. `region FLASH overflowed` yok. Mesaj listesi değiştiği için yapılandırma yeniden çalıştı; Grup 1'deki iki eski uyarı (CMake `find_package` politikası, NuttX `ARCH_CHIP_UNSET`) yine göründü, ikisi de PX4 v1.17.0'ın kendi yapılandırmasından. |

`astyle` / `make check_format` sürümü sabitlenmediği için çalıştırılmadı (çatı kural 4); biçim PX4 stiline elle uyduruldu (tab girinti, 140 karakter, tek satırlık `if`'lerde de süslü parantez).

### 5.2 Flash (Pixhawk 6C)

| Ölçüm | FLASH (kullanılan / toplam) | Yüzde | Boş kalan |
|---|---|---|---|
| Grup 1 sonu | 1 931 164 B / 1 966 080 B (1920 KB) | %98,22 | 34 916 B |
| **Grup 2 sonu** | **1 936 100 B / 1 966 080 B (1920 KB)** | **%98,48** | **29 980 B (~29 KB)** |
| Artış | **+4 936 B (~4,8 KB)** | +0,26 puan | |

- Nesne dosyaları (text): `AutoFollow.cpp` 7 087 B (Grup 1'de 4 058 B), `AutoFollowGuidance.cpp` 1 921 B. Geri kalanı log mesajının tanımı (logger'ın mesaj biçimi metni) ve topic listesi.
- RAM (AXI_SRAM, statik): 62 028 B, değişmedi. Modül nesnesi açılışta bir kez oluşturulur (Grup 1); log mesajı ve filtre bu nesnenin içinde, ~0,3 KB büyüdü.
- Kodda `double` yok, çevrim içinde bellek ayrılmıyor, büyük tablo yok.

### 5.3 Kısa SITL kontrolü (2.L6; Gazebo Harmonic, `gz_x500`, `HEADLESS=1`, araç arm edilmedi, mod açılmadı)

Önce ve sonra `build/px4_sitl_default/rootfs/parameters*.bson` silindi. `PX4_PARAM_AF_ENABLE=1 HEADLESS=1 make px4_sitl gz_x500` arka planda çalıştırıldı; komutlar PX4'ün konsol istemcisiyle verildi. Test sonunda `logger stop` ile log kapatıldı, süreçler PID ile durduruldu (Grup 1'deki `shutdown` takılması yüzünden), hiçbir px4/gz süreci kalmadığı kontrol edildi. Log hiçbir yere kopyalanmadı.

| Kontrol | Görülen | Sonuç |
|---|---|---|
| Modül başladı, mod kaydı | `mode 'AUTO FOLLOW' registered: nav_state 23` | Geçti |
| `listener auto_follow_status` (PASIF) | Bütün alanlar adlarıyla; `mode_nav_state` 23, `mode_active` False, `state` 0; mesaj gelmeden `los_timestamp` 0, geometri, filtre ve guidance alanları `nan`, `time_since_valid` `nan`, `lost_time` 0 | Geçti |
| Yayın hızı (`uorb top`) | `auto_follow_status` **50 Hz**, 1 abone (logger), boyut 176 B | Geçti |
| Geçerli biçimli 5 mesaj (`AF_LOS`, LOS (0,8; 0; 0,6), yaş 50 ms, sıra 1–5, bayrak 1) | Ham değerler `los_*`'ta; drone yerde olduğu için h = −0,99 m → `CHECK_RANGE`, `reject_range_count` 5. `depression` 0,6436 rad (36,9°, beklenen), `los_ned` drone'un yönüyle döndürülmüş (drone doğuya bakıyordu: (−0,086; 0,795; 0,600)) | Geçti (yerde beklenen sonuç) |
| Bozuk mesajlar: yanlış ad, NaN, norm 0,71, eski sıra no, yaş 900 ms, bayrak 0, ufka bakan LOS | Her biri kendi sayacında 1: `reject_name_count`, `reject_nonfinite_count`, `reject_norm_count`, `reject_seq_count`, `reject_age_count`, `no_target_count`, `reject_depression_count`; `auto_follow status` aynı sayıları gösterdi | Geçti |
| Uyarı hız sınırı | 0,1 s arayla gelen 7 bozuk mesajdan konsola yalnızca saniyede bir uyarı düştü | Geçti |
| ULog'da alanlar (pyulog 1.2.4) | `auto_follow_status` var; 39 alanın hepsi kendi adıyla (diziler `los_frd[0]` gibi açılınca 48 sütun); 96 s'de 4 809 örnek = **50,0 Hz**; kayıp (dropout) yok; `state` hep 0 (PASIF'te de yazıldı); `check_result` değerleri 0–9 arası beklenenler | Geçti |

- pyulog: `/home/yusuf/Desktop/Projects/Auto-Follow/.venv-tez/bin/python` ile çalıştırıldı; ama pyulog paketi (1.2.4) sanal ortamın içinde değil, kullanıcının `~/.local/lib/python3.12/site-packages/` klasöründen geliyor. Sürüm sabit listedekiyle aynı (`tez/env/requirements-lock.txt:27`).
- Test mesajları scratchpad'deki geçici bir pymavlink script'iyle MAVLink 2 olarak gönderildi (repoya girmedi; kalıcı gönderici Grup 4'teki `tez/sitl/af_los_gonder.py`).
- Not: SITL'de `trajectory_setpoint` mod kapalıyken de 50 Hz göründü; bu PX4'ün kendi FlightTask'ından (o an seçili mod). Bizim modül mod kapalıyken yayın yapmaz (kodda yayın yalnızca mod açıkken çağrılıyor); SITL'de ayrı ayrı görülmesi Grup 4'te.

### 5.4 Bu grupta denenmeyenler (Grup 3 ve 4'e kaldı)

- Moda girip takip etmek, hız/yaw/irtifa isteğinin değerleri, ivme sınırı, durum geçişleri: SITL'de Grup 4, sayısal olarak birim testinde Grup 3.
- Yerel konum geçersizken setpoint (A10), EKF sıfırlamasında filtrenin sıfırlanması.
- Yaw hız sınırının PX4'ün `MC_YAWRATE_MAX`'ı olduğu (doğrulanacak).

## 6. Kod içinde verilen küçük kararlar (yeni ad ya da kullanıcıya görünen davranış değil)

- **Kontroller "NaN geçemez" biçiminde yazıldı.** Örneğin tutum hiç gelmediyse LOS dönüşümü NaN çıkar ve mesaj kontrol 8'de atılır (tutum başlangıçta sıfır dörtlü (quaternion) tutulur ki yanlışlıkla "düz ve kuzeye bakıyor" sayılmasın).
- **LOS dönüşümden önce birim uzunluğa getirilir.** Uzunluk zaten `AF_NORM_TOL` içinde; böylece `asin` her zaman açıyı verir ve 1'den biraz uzun bir vektör NaN üretmez. Spec'teki örnek değerleri değiştirmez.
- **Mesafe formülü** `d = h × |LOS_NED yatay| / LOS_NED_z` olarak yazıldı; matematikçe `h / tan(δ)` ile aynıdır, ama hedef tam alttayken sıfıra bölme olmaz (d = 0 → kontrol 9'da atılır).
- **Bayrak kontrolü** "1 mi" sorusunu `|data[5] − 1| ≤ FLT_EPSILON` ile yapar (PX4 derleyici ayarı float eşitliğini uyarı/hata sayar).
- **Sıra no kontrolündeki "önceki":** 1–4. kontrolleri geçen son mesajın sıra numarası (yaş, bayrak, konum, açı ya da menzil yüzünden atılmış olsa da). Böylece masa testinde (konum geçersiz) tekrar eden mesaj yine `CHECK_SEQ` olarak görülür. İlk mesajda karşılaştırma yapılmaz. (Bölüm 7, soru 5.)
- **Filtrede Δt ≤ 0 ise** (çekim anları geri gittiyse) hız düzeltmesi yapılmaz, yalnızca konum düzeltilir; aksi halde `β/Δt` sonsuz olurdu.
- **İvme sınırının Δt'si** iki çevrim arasında gerçekten geçen süredir (yaklaşık 20 ms).
- **Tutum:** LOS, mesajın işlendiği çevrimdeki en son tutumla çevrilir; bu, varıştan en fazla bir çevrim (~20 ms) sonradır. V3 ("varış anındaki tutum, gecikme telafisi yok") bu küçük farkla uygulanmış olur.
- **Hedef tam drone'un üstündeyse** (kestirilen mesafe 0) hedefe yön tanımsızdır; kuralın mesafe kısmı 0 olur.
- **TAKIP'te filtre kurulu değilse** (EKF sıfırlaması hemen sonrası) yatay hız 0 istenir; bir sonraki kabul edilen mesajda filtre yeniden kurulur.
- **Moda girişte irtifa geçersizse** (`z_valid` yanlış; arm'lıyken PX4 buna izin vermez, yalnızca masada olabilir) `alt_hold_z` NaN olur ve setpoint geçerli kalsın diye dikey hız 0 istenir.
- **Uyarı sıklığı:** atılan mesaj için konsol uyarısı en fazla saniyede bir. "Hedef yok" için uyarı yok.
- **Konsol metinleri:** `auto_follow status` çıktısında yalnızca sözlükteki adlar kullanıldı (`STATE_*`, `CHECK_*`, sayaç adları).
- Şema `planning/visuals/02-px4-detayli-akis.md` (B) "konum geçerli mi?" kutusunu girdi kontrollerinden önce çiziyor; spec Bölüm 2'de konum 7. kontrol. **Spec'e uyuldu** (şemaya dokunulmadı).

## 7. Kullanıcıya sorulacaklar (bu grupta açık kalan)

Her biri için kod şu an "Şimdiki" sütunundaki gibi çalışıyor; cevaba göre küçük bir değişiklik olur.

1. **Yanlış adlı `debug_array` mesajı `los_*` alanlarına yazılsın mı?**
   - Kanıt: spec Bölüm 9 tablosu `los_timestamp`'i "Son `AF_LOS`'un FC'ye varış anı" diye tanımlıyor (`spec.md:108`); görev listesi ise "ham girdi doğrulamadan geçmese de `los_*` alanlarına yazılır" diyor (`tasks.md:161`).
   - a) **Yalnızca `AF_LOS` adlıları yaz (şimdiki).** Artı: `los_*` hep Pi'nin verisi; başka bir programın verisi Pi'ninkiyle karışmaz. Eksi: yanlış adlı mesajın içeriği logda görünmez (yalnızca `check_result` = `CHECK_NAME` ve sayaç).
   - b) Her `debug_array` mesajını yaz. Artı: S5'te yanlış adlı mesajın içeriği de görülür. Eksi: `los_timestamp` artık "son `AF_LOS`" değil; analizde Pi verisi ile yabancı veri ayırt edilemez.
   - Öneri: **a**.
2. **Nedene göre `perf` sayaçları.** Spec atılan mesajların `perf_counter` ile de sayılmasını istiyor (`spec.md:36`), ama sayaçların konsolda görünen adı verilmemiş. Şimdilik sayaçlar yalnızca log mesajında ve `auto_follow status` çıktısında.
   - a) **`perf` sayacı ekleme (şimdiki).** Artı: aynı bilgi zaten `auto_follow status` ve logda; flash ve RAM harcanmaz. Eksi: spec'teki "perf_counter" ifadesi karşılanmamış olur, spec'te bir cümle düzeltilir.
   - b) Tek sayaç, ör. `auto_follow: rejected` (ad sizin). Artı: `perf` çıktısında toplam görünür. Eksi: nedeni göstermez; ~100 B flash.
   - c) Her neden için bir sayaç (8 + 1 ad gerekir). Artı: `perf` çıktısında ayrıntı. Eksi: ~0,5 KB flash, 9 yeni ad; aynı bilgi zaten var.
   - Öneri: **a** (spec'teki ifade "log mesajındaki sayaçlar" diye düzeltilir).
3. **Uzun veri boşluğundan sonra filtre.** Spec filtrenin yalnızca EKF sıfırlamasında sıfırlanmasını söylüyor (`spec.md:53`). Şimdiki kodda veri uzun süre (ör. mod kapalıyken dakikalarca) gelmezse filtre son hızla hedefi ilerletmeye devam eder; veri geri gelince ilk birkaç mesajda kestirim yanlış olur (her mesajda hata yarıya iner, `AF_ALPHA` = 0,5).
   - a) Şimdiki gibi (spec'e harfiyen uygun). Eksi: boşluktan hemen sonra moda girilirse ilk ~0,1–0,2 s yanlış yöne hız istenebilir (ivme sınırlı).
   - b) **`AF_DATA_TOUT` boyunca geçerli mesaj gelmezse filtre de sıfırlansın;** bir sonraki geçerli mesaj onu yeniden kursun. Artı: eski kestirim hiç kullanılmaz; tek satır. Eksi: KAYIP_BEKLE'den kısa sürede dönüşte hedef hızı kestirimi sıfırdan başlar (açık çevrimde `AF_K_FF` = 0, etkisi yok).
   - Öneri: **b**. Karar verilirse spec Bölüm 4'e bir cümle eklenir.
4. **EKF konumu sıfırlarsa tutulan nokta.** KAYIP_BEKLE'de tutulan yatay konum ve moda girişte saklanan irtifa, PX4'ün yerel koordinatlarındadır. EKF konumu sıçratırsa (ör. GPS düzeltmesi), PX4 kendi modlarında bu noktaları sıçrama kadar kaydırıyor; bizim kodda kaydırma yok, yani drone fiziksel olarak sıçrama kadar yer değiştirebilir. Spec bu durumu tanımlamıyor.
   - a) Şimdiki gibi (kaydırma yok).
   - b) **Sıfırlamada tutulan yatay konumu `delta_xy`, irtifayı `delta_z` kadar kaydır** (`VehicleLocalPosition.msg:20, 22`; PX4'ün kendi modlarının yaptığı). Artı: drone fiziksel olarak yerinde kalır. Eksi: birkaç satır kod (~100 B).
   - Öneri: **b**.
5. **Sıra no kontrolündeki "önceki"nin anlamı** (Bölüm 6'daki yorum): 1–4. kontrolleri geçen son mesaj mı (şimdiki), yoksa 9 kontrolün hepsini geçen son mesaj mı? Öneri: şimdiki; masada da tekrar eden mesaj `CHECK_SEQ` olarak görünür.
6. **Bilgi (onay rica edilir):** PASIF'te guidance alanları NaN; hiç geçerli mesaj gelmemişken PASIF'te `time_since_valid` NaN; hedefsiz girişte `lost_time` ilk 0,5 s 0 (Bölüm 4). Sözlüğe böyle yazıldı.

Grup 1'den kalan sorular (QGC parametre grubu adı, lisans başlığı, `module.yaml` dili) bu grupta değiştirilmedi.

## 8. Çıkan sorunlar ve çözümleri

1. **SITL konsol çıktısı çok hızlı büyüdü.** SITL arka planda, girdisi boş bir dosyaya bağlı çalıştırılınca `pxh>` istemi her an yeniden yazıldı; konsol çıktısı bir dakikada ~240 MB oldu. Kontroller hemen bitirildi, SITL durduruldu, geçici çıktı dosyası silindi. Grup 4 için not: SITL'in girdisi bekleyen bir kaynağa bağlanmalı (ör. `sleep infinity |` ile) ya da çıktı dosyaya yazılmamalı.
2. **Test script'i ilk denemede pymavlink'i bulamadı.** `python -I` kullanıcı paket klasörünü kapatıyor; pymavlink ve pyulog `.venv-tez` içinde değil, `~/.local` altında kurulu. `-I` olmadan çalıştırıldı. Grup 4 için not: `.venv-tez`'e sabit sürümleriyle kurulmaları gerekebilir (`tez/env/requirements-lock.txt`).
3. Derleme ilk denemede uyarısız geçti; kod hatası çıkmadı.

## 9. Sonraki grup için notlar

- Grup 3 (birim testi) için: `AutoFollowGuidance.hpp`'deki `check_input`, `compute_geometry`, `compute_guidance`, `constrain_length`, `limit_change`, `update_state`, `time_since_valid`, `lost_time` saf fonksiyonlardır; sonuç kodları `auto_follow_status_s::CHECK_*` / `STATE_*`. Test dosyası `CMakeLists.txt`'e `px4_add_unit_gtest(SRC AutoFollowGuidanceTest.cpp LINKLIBS AutoFollowGuidance)` satırıyla eklenir.
- Spec Bölüm 3 örneği (drone 10 m, LOS (0,8; 0; 0,6)) için beklenen: `depression` 0,6435 rad, h = 9,0 m, d = 12,0 m; Bölüm 5: `range_desired` 15,59 m, kural −1,8 m/s.
- Grup 5: Hold isteği HOLD_ISTENDI'ye geçişte gönderilecek; `hold_request_count` alanı hazır (şimdi hep 0).
