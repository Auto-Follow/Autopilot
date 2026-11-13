# Görev Grubu 9 — 15.11 en az demo, `FLW_TGT_RS` kararı, yakın geçişlerin açıklaması ve 10 m / 10 m denemesi

- Tarih: 13.11.2026 · dal `ozellik/m06-sim-ortami` · taban commit `c557f3954e` (9.8 ön işi) + çalışma ağacı
- Kapsam: `tasks.md` 9.0–9.7; kullanıcının 13.11 kararları (1: `FLW_TGT_RS`, 2: video penceresi, 3: kare kaydının RTF
  payı, 4: köşe ölçütlerinin `olcum.py`'ye taşınması) ve sorusu ("dron genel olarak hedefe çok yakın, neden böyle, biz
  kaç metre mesafede kullanıyoruz?").
- Durum: **uygulandı, test edildi, koşuldu**; commit'lenmedi (commit'i kullanıcı atar; RS varsayılanı ayrı commit,
  bölüm 10).

## Kısaca

- **Demo (15.11) listesinin bütün maddeleri sağlandı** (bölüm 5, madde madde sayılarıyla): `takip_yuruyen` v0.2 (CPU) +
  stok Follow Me ile kapalı döngüde 3/3 GEÇTİ, `kalabalik_park` (`yok`) 3/3 GEÇTİ ve model ölçütleri (karıştırma,
  örtülme) çıktı, altı koşunun hepsi `rapor.html` + `ozet.json` + VLC'de açılan `kosu.mp4` üretti, `TEZ_LOS` ULog'da
  gönderilenle birebir; `verify_pin` KİLİT SAĞLAM; F0 ve F1 GEÇTİ; 234 birim testi geçti. Görsel kontrol (9.5) Ahmet'te
  (bölüm 6'da zamanlı izleme listesi).
- **`FLW_TGT_RS` 0.3 seçildi** (karar 1, bölüm 2): duran kişideki salınımı ölçülen her koşuda gideren tek aday (0.2 üç
  koşunun ikisinde gidermedi); bedeli köşede biraz daha yakın geçiş. Follow Me senaryolarına yorumuyla yazıldı,
  `gercek_dron.params` değişmedi (gerçek dronda 0.1).
- **"Dron neden bu kadar yakın?"** (bölüm 3): biz 8 m kullanıyoruz ve dron kaydın %84'inde kişiden 6–10 m
  uzakta, ortalama 8.2 m (6 model koşusu, RS 0.3; mükemmel algılayıcıyla 7.2 m). Ama her koşuda iki an var: **kişi aniden durunca** dron ≈ 5.5–5.9 m'ye, **kişi koşudan sonra
  dönünce** 0.45–2 m'ye geliyor. Sebep PX4'ün stok Follow Me'si: dronu kişiye değil, kişinin "süzülmüş" bir kopyasına göre
  koyuyor ve bu kopya kişi durunca/dönünce eski hızla kişiyi metrelerce geçiyor; kişiye yaklaşmamak için bir kuralı yok.
  ULog'la her geçiş paylara ayrıldı. Modelin konum kayması dronu yaklaştırmıyor, tersine biraz uzaklaştırıyor.
- **Köşedeki yakın geçiş takibi bitiriyor:** dron kişinin üstüne gelince kişi kameranın görüş alanından çıkıyor, model
  onu bulamıyor ve stok Follow Me onu bir daha bulamıyor (demo koşularının 3/3'ünde ≈ 81 s'den sonra kestirim bayat,
  dron koşu sonuna kadar bayat noktanın gerisinde bekliyor). Bu bir sim hatası değil, stok modun davranışı.
- **10 m / 10 m denendi** (bölüm 4): en az mesafe 2.99–5.10 m (8/8'de 0.45–1.94), kaydın 6 m altındaki payı %2.9 (%7.5), kişinin tamamı kadrajda %93 (%59), köşeden sonra kişi hiç kaybedilmedi (8/8'de 3/3); bedeli kilit kaybı daha sık (4.3 / 2.3) ve çekim daha uzaktan. Varsayılan 8/8 kaldı; karar kullanıcıda.
- Kullanıcının dört kararı uygulandı (bölüm 1); köşe ölçütleri artık `olcum.py`'de (testli), raporda, `toplu.html`'de.
- Bulunan iki hata testle düzeltildi: videoda "PX4'ün dronu gönderdiği yer" yanlış noktadan çiziliyordu (köşede
  metrelerce kayık); bacak bulma, hakemde bir NaN yaw'dan sonra bütün rotayı kaybederdi.

## 1. Kullanıcı kararları (13.11) ve uygulanışı

| Karar | Uygulanışı |
|---|---|
| 1. `FLW_TGT_RS`: "0.2 veya 0.3 daha iyi olur" | 0.2 3 + 3 koşu (model, hakem), 0.3 son kodla yeniden 3 + 3; aynı ölçütlerle karşılaştırıldı (bölüm 2); **0.3** `takip_yuruyen.yaml` → `takip.px4_parametreleri`'ne yorumuyla (sim seçimi, gerçek dronda 0.1, gerekçe, ölçüm); yeni `takip_yuruyen_10m.yaml` da 0.3. `gercek_dron.params` değişmedi; F0 / F1 Follow Me kullanmaz (ikisi de yeniden geçti). Test: `test_hedef.py` (değer, kaynak, PX4'ün 0.1–1.0 kısması, gerçek dron dosyasında yok) |
| 2. Video penceresi takip moduna geçişten koşu sonuna | Kod değişmedi (8. gruptaki gibi); spec 9. maddeye karar olarak yazıldı, 8. grup belgesinin açık kararı kapandı |
| 3. Kare kaydının RTF payı (≈ 0.05) 11. grupta | `tasks.md` 11.6 eklendi; spec 9. maddeye yazıldı. Bu gruptaki karşılaştırmalar her grupta aynı video ayarıyla (hepsi videolu) koşuldu |
| 4. Köşe ölçütleri `olcum.py`'ye | `olcum.legs` (bacaklar hakemden bulunur; 9.8'in betiğinde köşe anları elle yazılıydı), `olcum.corner_metrics` (PX4'ün yeni yöne yetişmesi, aşma); `kose_*` `ozet.json`'da, raporda tablo, `toplu.html`'de köşe köşe tablo; testli (`test_yakin_gecis.py`). Eski betikle aynı koşuda aynı sayılar çıktı (2.58 / 1.81 / 1.69 s) |

Ek olarak kullanıcının sorusu için yeni ölçütler: 6 m altı geçişler, sebepleri ve ayrıştırması (`olcum.near_passes`,
`olcum.decompose`, `olcum.Px4Follow`), mesafenin dağılımı; raporda "Yakın geçişler" tablosu ve zaman çizelgesi,
`toplu.html`'de her koşunun geçişleri, videonun durum satırında geçişin sebebi.

## 2. `FLW_TGT_RS`: 0.2 mi, 0.3 mü? (karar 1) — **0.3 seçildi**

**Nasıl ölçüldü:** `takip_yuruyen` (8 m / 8 m, v0.2 CPU'da, 4 çekirdek), `toplu.py --tekrar 3 -- --param FLW_TGT_RS=0.2`
ve `=0.3`, ayrıca ikisi de `--los hakem` ile (mükemmel algılayıcı: konum gürültüsü yok, yalnız PX4'ün kendi bedeli
görünür). 12 koşu bu oturumda, aynı son kodla, sırayla (04:53–05:24), hepsi videolu (karar 3: gruplar arasında aynı
video ayarı). 9.8 ön işinin RS 0.1 ve RS 0.3 koşuları yeni köşe / yakın geçiş ölçütleriyle klasörlerindeki dosyalardan
yeniden ölçüldü (diğer ölçütleri kendi `ozet.json`'larından). Her hücre: **ortalama** (en az–en çok), 3 koşu.

| Ölçüt | RS 0.1 (9.8) | **RS 0.2** | **RS 0.3** | RS 0.3 (9.8) | hakem RS 0.1 (9.8) | **hakem RS 0.2** | **hakem RS 0.3** |
|---|---|---|---|---|---|---|---|
| *Duran kişide salınım (küçük iyi)* | | | | | | | |
| Duran kişi etrafında dönüş [°] | 482 (191–652) | **301** (198–367) | **203** (201–205) | 187 (183–189) | 194 (193–195) | **194** (194–195) | **194** (194–195) |
| PX4'ün sahte hızı, ort. [m/s] | 0.53 (0.24–0.71) | **0.30** (0.19–0.41) | **0.14** (0.12–0.15) | 0.15 (0.14–0.16) | 0 | **0** | **0** |
| Sahte hız ≥ 1 m/s [%] | 17 (2–26) | **3** (0–4) | **0** (0–0) | 1 (0–1) | 0 | **0** | **0** |
| PX4'ün rotası değişti [kez] | 15 (2–23) | **4** (0–7) | **0** (0–0) | 1 (1–2) | 0 | **0** | **0** |
| *Köşe bedeli (küçük iyi)* | | | | | | | |
| Köşe 1 (60.3 s, yürüyüş başı → doğu): PX4 yetişme [s] | 1.5 | **1.9** (1.7–2.2) | **2.6** (2.4–2.9) | 2.4 | 1.6 | **1.7** (1.6–1.8) | **1.9** (1.8–2.1) |
| Köşe 2 (73.0 s, kuzeye koşu): PX4 yetişme [s] | 1.6 | **2.1** (2.0–2.1; 1 koşuda yetişemedi) | **2.0** (1.8–2.1) | 1.9 | 1.2 | **1.5** (1.3–1.6) | **1.7** (1.5–1.8) |
| Köşe 3 (77.6 s, batıya dönüş): PX4 yetişme [s] | 1.0 (1 koşuda yetişemedi) | **2.3** (2 koşuda yetişemedi) | **1.7** (1.6–1.9) | 1.7 | 1.7 | **1.3** (1.2–1.5) | **2.3** (2.0–2.6; 1 koşuda yetişemedi) |
| Köşeden sonra arkada kalma, en çok [°] | 138 | **108** (95–131) | **145** (138–156) | 154 | 126 | **132** (131–135) | **139** (134–143) |
| En az yatay mesafe [m] | 1.95 (1.68–2.46) | **4.87** (3.68–6.01) | **1.49** (1.21–2.03) | 1.16 (0.66–1.56) | 3.22 (2.93–3.46) | **2.53** (2.49–2.61) | **1.98** (1.87–2.06) |
| 3 m altı [s] | 1.0 | **0.0** | **1.2** (1.0–1.4) | 1.3 | 0.1 | **0.7** (0.7–0.8) | **1.1** (1.1–1.1) |
| *Takip* | | | | | | | |
| PX4 kestirimi bayat [s] | 3.9 (0–9.0) | **8.1** (3.2–12.6) | **6.1** (2.6–8.0) | 5.3 (0–8.0) | 0 | **0** | **2.7** (0–8.2) |
| Kişinin tamamı kadrajda [%] | 55 (38–86) | **55** (50–65) | **67** (62–76) | 69 (57–88) | 91 | **91** (90–92) | **78** (59–89) |
| PX4 rota hatası, ort. [°] | 39 | **57** (33–93) | **34** (32–38) | 34 | 23 | **24** (23–26) | **33** (31–37) |
| RTF | 0.82 | **0.78** (0.76–0.80) | **0.83** (0.79–0.90) | 0.84 | 0.86 | **0.84** (0.80–0.91) | **0.80** (0.80–0.81) |

Bütün tablo ve şekil: `~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9_RS_0.2_0.3_karsilastirma.png`.

**Seçim (kullanıcının kuralıyla: önce duran kişideki salınımı gidermeli, sonra en az mesafe / köşe bedeli küçük olan):**

1. **Salınımı gideren yalnız 0.3.** 0.3: üç koşunun üçünde duran kişi etrafında 201–205° (hakemde 194–195°: kalan tek
   dönüş PX4'ün başlangıçtaki "kuzey" varsayımı), PX4'ün rotası hiç değişmedi, sahte hız 1 m/s'yi hiç aşmadı; 9.8'deki
   3 koşuda da aynı (183–189°): 6/6. 0.2: üç koşunun yalnız birinde (198°); diğer ikisinde 339° ve 367° (rota 5 ve 7
   kez değişti). 0.2, 0.1'in salınımını yarıya indiriyor ama gidermiyor.
2. **Bedel 0.2'de daha küçük.** Mükemmel algılayıcıyla (PX4'ün kendi bedeli): köşede en az mesafe 2.53 m (0.3'te 1.98,
   0.1'de 3.22), 3 m altı 0.7 s (1.1), PX4'ün yeni yöne yetişmesi köşe başına 0.2–1.0 s daha erken. Model kutusuyla
   0.2'nin en az mesafesi 4.87 m görünüyor ama yanıltıcı: iki koşuda PX4 kişiyi kaybetti (biri kuzey koşusunu hiç
   görmedi, rotası 91°'de kaldı; diğerinde köşede kuzeye öngörmeye devam etti; kestirim 8–13 s bayat), dron uzak kaldığı
   için yakın geçmedi. 9.8'deki RS 0.5 / 0.8 gibi: "güvenli" görünmesi takip etmemesinden.
3. **Karar: 0.3.** Bedeli (köşede ≈ 0.5 m daha yakın geçiş, PX4'ün yeni yöne biraz daha geç yetişmesi) her koşuda
   ölçülüyor (köşe ve yakın geçiş ölçütleri) ve bölüm 3 bunun neden olduğunu gösteriyor. 0.2'nin daha çok koşuyla
   (ör. 6) yeniden ölçülmesi istenirse komut "Kendin dene" 7'de; 3 koşunun ikisinde salınım olduğu için seçim
   değişmeyecek gibi görünüyor ama kesin değil.

**Uygulandı:** `tez/sim/senaryolar/takip_yuruyen.yaml` → `takip.px4_parametreleri: FLW_TGT_RS: 0.3` (yorumu: sim seçimi,
kullanıcı kararı, gerçek dronda 0.1, gerekçe, ölçüm belgesi); `takip_yuruyen_10m.yaml` de 0.3. `gercek_dron.params`
değişmedi. Bu değişiklik ayrı commit'lenebilsin diye ayrı yama: bölüm 10. PX4'ün varsayılanıyla koşmak için
`--param FLW_TGT_RS=0.1`.

## 3. "Dron genel olarak hedefe çok yakın, neden? Biz kaç metre kullanıyoruz?"

### Kısa cevap

**Biz 8 m kullanıyoruz:** dron 8 m yükseklikte uçar ve kişinin 8 m gerisinde durmaya çalışır (`FLW_TGT_HT 8`,
`FLW_TGT_DST 8`; kamera raporunun stad ayarı, 45° kamera). Seçilen ayarla (RS 0.3) 6 model koşusunda dron kaydın
(mod seçimi → senaryo sonu, videonun gösterdiği aralık) **%84'ünde kişiden 6–10 m uzakta**, ortalama **8.2 m**;
%6.6'sında 6 m'den, %2.9'unda 4 m'den yakın, %9'unda 10 m'den uzak.

**Yaklaşmalar rastgele değil, her koşuda aynı iki anda:**

| An | Ne oluyor | Dron kişiye ne kadar yaklaşıyor (6 model koşusu) | Mükemmel algılayıcıyla (3 koşu) |
|---|---|---|---|
| ≈ 71 s (ve ≈ 86 s) | Kişi doğu yürüyüşünün (ya da yolun) sonunda **aniden duruyor** | 6 kez, 5.48–5.91 m (ort. 5.69) | 5 kez, 5.38–5.98 m |
| ≈ 78–80 s | Kişi 3 m/s **koşudan sonra yavaşlayıp batıya dönüyor** | 6 kez, **0.45–2.03 m** (ort. 1.29) | 3 kez, 1.87–2.06 m |

Bu oturumun bütün koşularında (15 koşu: RS 0.2 / 0.3, model / hakem, demo) 31 geçişin 17'si durma, 14'ü köşe; **takip
başında hiç 6 m altı yok** (takip başında en az 6.8–7.1 m; 9.8'in RS 0.1 koşularında bile en az 6.07 m), **konum
kayması ya da kilit kaybı hiçbir geçişin kök sebebi değil**. 9.8'in RS 0.1 koşularında (6 koşu, 11 geçiş) ayrıca 2
"kilit kaybı / bayat kestirim" (model kişiyi koşunun sonunda kaybetti, PX4 3 s eski hızla öngörüp durdu; dron kişiyi
1.71 m'ye kadar geçti) ve 1 "diğer" (düz yürüyüşte PX4 kişinin hızını 1.88 m/s sandı, gerçek 1.40) var.

### Neden? (PX4 kodu ve ULog)

Kaynak: `src/modules/flight_mode_manager/tasks/AutoFollowTarget/` (yalnız okundu).

1. **PX4 dronu kişinin kendisine değil, kendi "süzülmüş hedef"ine göre yerleştirir.** Kestirici (`TargetEstimator`)
   FOLLOW_TARGET'lardan bir kestirim (E) yapar; Follow Target görevi bunu bir de kendi ikinci derece süzgecinden geçirir
   (`FlightTaskAutoFollowTarget.cpp:136–139`, `SecondOrderReferenceModel`, doğal frekans 1 rad/s, sönüm 0.71,
   `.hpp:82–85`) ve dronun hedef konumunu bu süzülmüş hedefin (F) `FLW_TGT_DST` gerisine koyar (`.cpp:344`,
   `calculateDesiredDronePosition(target_position_filtered, ...)`). Süzgeç kestirimin hızını da girdi olarak alır
   (`update(dt, pos_est, vel_est)`; ivme = ωn²(konum − F) + 2ζωn(hız − F'nin hızı),
   `second_order_reference_model.hpp`): kişi yürürken F gecikmesiz izler, ama kişi **aniden durunca ya da dönünce F'nin
   kendi hızı sürer ve kişiyi geçer**.
2. **Dronun hız ayar noktası kişinin (süzülmüş) hızını ileri besler** (`.cpp:364`, `_velocity_setpoint.xy() =
   orbit_tangential_velocity + target_velocity_filtered.xy()`): kişi durunca dron bir süre daha aynı hızla gelir; konum
   kontrolcüsü onu ancak sonra ayar noktasına çeker (ayrıştırmada "dron" payı).
3. **Kestirici son ölçümden sonra hız ve ivmeyle öngörür** (`TargetEstimator::prediction_update`); konum en sık 500
   ms'de bir kaynaşır. Kişi koşudan yürüyüşe geçip dönünce kestirim de eski yöne doğru ileri gider ("PX4 öngörüsü"
   payı); model kişiyi kaçırırsa (kilit kaybı) bu öngörü 3 s sürer, sonra kestirim "bayat" olur ve son noktada durur.
4. **Yön (rota) değişimini yörünge açısı sınırlı hızla izler** (en çok 2 m/s² / 4 m/s³ / `FLW_TGT_MAX_VEL`, `.hpp:99–102`)
   ve rota yalnız kişinin hızı ≥ 1 m/s iken güncellenir (`.hpp:94`): köşede dron bir süre eski "arka"da kalır.
5. **PX4 v1.17.0'ın stok Follow Target'ında en az mesafe koruması yoktur**: kodda dron–kişi mesafesine bakan bir sınır
   yalnız yaw için var (1 m'den yakında yaw güncellenmez, `MINIMUM_DISTANCE_TO_TARGET_FOR_YAW_CONTROL`); konum ayar
   noktası her zaman F + `FLW_TGT_DST`'tir. F kişiyi ne kadar geçerse dron o kadar yakına gelir.
6. **Geri besleme:** dron kişiye kameranın yakın görüş sınırından (8 m'de ≈ 3.9 m) daha çok yaklaşınca kişinin ayakları
   kadrajın altından çıkar, model kutusu kesilir ya da kenara değer (konum hesaplanmaz), FOLLOW_TARGET durur ve
   kestirici eski yönde öngörmeye devam eder (3. madde). Bu yüzden yakın geçişlerin çoğunda en az mesafe anında bir
   ölçüm boşluğu da vardır; boşluk geçişin sebebi değil, çoğu zaman sonucudur (ayrıştırmanın "öngörü" ve "ölçümün yaşı"
   payları ne kadar katkı yaptığını söyler).

### Ayrıştırma: her geçişte "8 m'den neden yakın?" (ULog)

**Olay ve sebep sınıfları** (kod: `olcum.near_passes`, testli):

- **Olay:** kayıt (video) penceresinde (mod seçimi → senaryo sonu) dron–kişi yatay mesafesinin 6 m'nin altında kaldığı
  her ayrı aralık: başlangıç, bitiş, süre, en az mesafe ve anı.
- **Sebep:** aşağıdaki kurallardan sırayla **ilk tutan** (kural sırası bilerek böyle: önce "PX4 hiç bilmiyordu" gibi kök
  sebepler, sonra kişinin hareketi):

| Sınıf | Kural | Ne demek |
|---|---|---|
| takip başı yörünge dönüşü | En az mesafe anı kişi yürümeye başlamadan önce | Stok modun "kuzey" varsayımı ve sahte hızla duran kişinin etrafında dönerken |
| kilit kaybı / bayat kestirim | Yaklaşmanın başında PX4'ün en yeni ölçümü ≥ 1.5 s eski (3 kaynaşma aralığı) ya da kestirimi bayat (3 s ölçüm yok) | PX4 kişiyi görmeden, son hızıyla öngörerek uçuyordu |
| köşe / yön değişimi | ≥ 45° dönen bir bacak yaklaşmadan en çok 6 s önce ya da yaklaşma sırasında başladı | Kişi yön değiştirdi, PX4 eski yönde gitmeye devam etti |
| kişi durdu ya da hızlandı | En az mesafe anından önceki 4 s'de kişinin hızı ≥ 1 m/s değişti (durdu, yürümeye ya da koşmaya başladı) | PX4'ün süzgeci ve öngörüsü eski hızla kişiyi geçti |
| konum kayması | Ayrıştırmada en büyük pay gönderilen konumun hatası ve ≥ 0.5 m | Model kutusundan bulunan konum kişiden kayık, dronu kişiye doğru çekti |
| diğer | Hiçbiri | Ayrıştırmanın en büyük payı söyler |

- **Etkenler:** tutan bütün kurallar ayrıca listelenir (ör. bir köşede kişi aynı anda yavaşladıysa "köşe" + "kişi durdu
  ya da hızlandı"); **ölçüm boşluğu** etkeni: yaklaşmadan 3 s önceden en az mesafe anına kadar ≥ 1 s'lik bir FOLLOW_TARGET
  boşluğu ya da kilit kaybı (yaklaşmanın sonucu da olabilir: dron yakınken kişinin ayakları kadrajın altındadır).
- **Ayrıştırma:** en az mesafe anında "8 m'den ne kadar, neden yakın" (yukarıdaki tablo).

En az mesafe anında, n = PX4'ün dronu hedefinden istediği yön (yörünge açısı hedefi, `follow_target_status`) olmak
üzere:

FLW_TGT_DST − (dron − kişi)·n = **dron** + **PX4 süzgeci** + **PX4 öngörüsü** + **konum hatası** + **ölçümün yaşı**

| Pay | Ne | Nereden |
|---|---|---|
| dron | Dron ayar noktasının (P) gerisinde, kişiye doğru (ataleti, hız ileri beslemesi, konum kontrolcüsü) | hakem (dronun gerçek yeri), ULog `trajectory_setpoint` |
| PX4 süzgeci | Görevin süzülmüş hedefi (F) kestirimi (E) geçti | `follow_target_status.desired_position_raw` − `FLW_TGT_DST`·(rota + izleme açısı) = F; `follow_target_estimator` = E |
| PX4 öngörüsü | Kestirim (E) son FOLLOW_TARGET'ı (S) geçti: kestiricinin hız ve ivmeyle öngörüsü | `follow_target_estimator`, `follow_target.csv` |
| konum hatası | Gönderilen konum (S) − kişinin karenin anındaki gerçek yeri | `follow_target.csv` (model kutusunun alt ortası → düz zemin) |
| ölçümün yaşı | Kişi karenin anından beri yürüdü | hakem |

Toplam bire bir tutar (P − F = `FLW_TGT_DST`·n olduğu için); ULog konuları farklı anlarda örneklendiği için kalan
≈ ±0.02 m. Kod: `olcum.decompose`, `olcum.Px4Follow`; testli (`test_yakin_gecis.py`).

Ortalamalar (her hücre metre; + dronu kişiye yaklaştırdı, − uzaklaştırdı; toplam = 8 m − dronun PX4'ün istediği yöndeki
mesafesi):

| | Geçiş | En az mesafe | Toplam | Dron (ataleti) | PX4 süzgeci | PX4 öngörüsü | Konum hatası | Ölçümün yaşı |
|---|---|---|---|---|---|---|---|---|
| Model, RS 0.3 (6 koşu) | durma ×6 | 5.48–5.91 | +2.32 | +0.49 | **+1.65** | +0.23 | −0.04 | 0.00 |
| | köşe ×6 | 0.45–2.03 | +6.76 | +1.46 | +2.41 | **+2.85** | −0.13 | +0.15 |
| Hakem, RS 0.3 (3 koşu) | durma ×5 | 5.38–5.98 | +2.49 | +0.38 | **+1.41** | +0.71 | 0 | 0 |
| | köşe ×3 | 1.87–2.06 | +6.10 | +1.25 | +1.89 | **+2.85** | 0 | +0.10 |

Okuma:

- **Kişi durunca** dronu yaklaştıran asıl şey PX4'ün süzülmüş hedefinin kişiyi ≈ 1.4–1.7 m geçmesi; dronun ataleti
  ≈ 0.4–0.5 m ekliyor. Model ile mükemmel algılayıcıda aynı: bu, stok modun kendisi.
- **Köşede** üç pay da büyük: PX4'ün kestiricisi kişinin 3 m/s'lik koşusunu öğrenmiş, kişi yavaşlayıp dönünce kestirim
  kuzeye ≈ 2.9 m ileri gidiyor (öngörü), görevin süzgeci bunun üstüne ≈ 1.9–2.4 m ekliyor, dron da kuzeye giderken
  ataletiyle ≈ 1.3–1.5 m daha geliyor. Toplam ≈ 6–7 m: dron 8 m yerine 1–2 m'ye geliyor.
- **Konum kayması** (modelin konumu kişiden drona doğru ≈ 0.4–0.5 m kayık) payı hep ≈ 0 ya da eksi: kayma dronu
  uzaklaştırıyor, çünkü PX4 dronu gönderilen noktanın 8 m gerisine koyuyor ve nokta drona doğru kayık.
- **Ölçüm boşluğu** köşe geçişlerinin 13/14'ünde etken olarak görünüyor, ama mükemmel algılayıcıda da (3/3) var: dron
  kameranın yakın sınırına (8 m'de ≈ 3.9 m) girince kişi kadrajın altından çıkıyor ve FOLLOW_TARGET kesiliyor. Boşluk
  yaklaşmanın çoğunlukla sonucu; payı "öngörü" ve "ölçümün yaşı"nda.

### Ortalama neden 8 m değil?

Kullanıcının gördüğü 7.4–8.5 m'lik ortalamalar (her 0.5 s'de ayrıştırma, fazlara göre ortanca, RS 0.3, 3'er koşu):

| Faz | Hakem: mesafe | Hakem: en büyük pay | Model: mesafe | Model: en büyük pay |
|---|---|---|---|---|
| Takip başı (kişi duruyor, 25–60 s) | 8.01 m | – | 8.47 m | konum hatası −0.37 m (uzaklaştırıyor) |
| Kişi yürüyor | 7.81 m | süzgeç +0.28, öngörü +0.16 | 8.59 m | konum −0.18, ölçümün yaşı −0.12 |
| Kişi durduktan sonra (3 s'lik duruş, yolun sonu) | **6.16 m** | süzgeç +1.11, öngörü +0.55 | 8.54 m | (kişi kaybedilmiş, dron geride) |

- **Mükemmel algılayıcıyla ortalama ≈ 7.2–7.6 m:** yürürken dron ≈ 7.8 m'de, ama kişi durduktan sonra PX4'ün süzgeci ve
  öngörüsü kişiyi geçtiği için dron ≈ 6.2 m'de kalıyor (süzgeç birkaç saniyede geri çekiliyor) ve ortalamayı aşağı
  çekiyor.
- **Modelle ortalama ≈ 7.9–8.6 m:** konum kayması dronu ≈ 0.2–0.4 m uzaklaştırıyor, modelin ≈ 0.14 s'lik gecikmesi
  (kişi kareden beri yürüdü) ≈ 0.1 m; köşeden sonra kişi kaybedilince dron bayat noktanın gerisinde 9–11 m'de kalıyor
  (kaydın %9'u > 10 m).

### Köşedeki yakın geçişten sonra takip bitiyor

Köşede dron kişinin üstüne / önüne geçince kişi kameranın görüş alanından çıkıyor (45° kamera yalnız önü görür), model
onu bulamıyor ve PX4'e konum gitmiyor. Stok Follow Me'nin bir arama davranışı yok: kestirici 3 s eski hızla öngörüyor,
sonra "bayat" olup son noktada kalıyor ve dron onun 8 m gerisinde koşu sonuna kadar bekliyor (kişi kadrajda %0).

| Grup | Köşeden sonra kişi kaybedildi | Son FOLLOW_TARGET | Kestirim bayat |
|---|---|---|---|
| Demo `takip_yuruyen` (RS 0.3) | 3/3 | 78.0–78.3 s | 81.3–81.6 s → son |
| RS 0.3 karşılaştırma | 2/3 | 78.4 s | 81.6–81.8 s → son (3. koşu 84 s'de yeniden buldu) |
| RS 0.2 karşılaştırma | 2/3 (birinde kuzey koşusunda) | 73.8 / 77.9 s | 77.0 / 81.1 s → son |
| RS 0.1 (9.8) | 2/3 | 77.3 / 83.8 s | 80.6 / 87.0 s → son |

Bu, yakın geçişin bir sonucu (geri besleme) ve stok modun bilinen bir eksiği ("PX4 v1.17.0'da hedef kaybı için failsafe
yok", spec "PX4 tarafı"). m15'in modu için önemli bir ölçüt: kişi kadrajdan çıkınca ne yapıyor.

### Öneriler (ayrı ayrı: m06'da yapılabilecekler ve takım arkadaşlarının işi)

**m06'da (sim tarafı; ölçer ve takılabilir kalır):**

1. **10 m / 10 m ayarı** (kamera raporunun çim alan ayarı): 3 koşuyla ölçüldü (bölüm 4). Varsayılan 8/8 kaldı; karar
   kullanıcıda.
2. **`FLW_TGT_RS`** (karar 1): 0.3 seçildi (bölüm 2). Duran kişideki salınımı gideriyor, ama köşedeki yakın geçişi
   biraz artırıyor; bu bir ayar, güvenlik çözümü değil.
3. **Ölçüm her koşuda**: 6 m altı geçişler, sebepleri, "neden 8 m'den yakın" ayrıştırması, mesafe dağılımı ve köşeler
   artık her `ozet.json`'da, raporda, `toplu.html`'de ve videonun durum satırında. m15'in modu takıldığında aynı
   sayılar onun için de çıkar (ayrıştırma PX4'ün Follow Target konularına bağlı olduğu için yalnız stok modda; m15'in
   modu kendi iç durumunu kaydederse eklenebilir).
4. **m01'e (Hüseyin) öneri:** başarı ölçütlerine "en az yatay mesafe" ve "6 m altı süre payı" girsin (3 m uyarısı
   zaten var); eşiği m01 belirler.

**Takım arkadaşlarının işi (m06 bunları yapmadı, yalnız ölçtü):**

- **m15 (Yusuf Kurt), kendi takip modu:** (a) **en az mesafe koruması**: dron–kişi yatay mesafesi bir eşiğin altına
  inince ayar noktasını kişiden uzaklaştırmak ya da kişiye doğru hız bileşenini kesmek (stok modda yok); (b) kişinin
  durduğunu / döndüğünü hızlı anlamak ve o anda kişinin hızını dronun hızına ileri beslememek (stok modda yakın
  geçişin en büyük iki payı süzgeç ve hız ileri beslemesi); (c) ölçüm kesilince eski yönde öngörüyü sınırlamak
  (bayat kestirimde dron hayali noktanın 8 m gerisinde asılı kalır). Karşılaştırma tabanı: bu belgedeki tablolar.
- **m11 (Yusuf Ortatepe), hedef seçimi ve süzgeç:** PX4'e süzülmüş konumla birlikte **süzülmüş hız** göndermek
  (9.8 ön işi: PX4 hızı %83 ağırlıkla alır, duran kişide sahte hız RS'den bağımsız kalkar) ve durma / dönme anını hızlı
  yakalayan bir hız kestirimi; ölçüm boşluğunda "hedef yok" (kişi dronun altına girince model onu kaybediyor).
- **m09 / gerçek uçuş:** gerçek araçta da aynı mekanizma çalışır; ilk uçuşlarda kişi aniden durduğunda ve döndüğünde
  dronun yaklaşması özellikle izlenmeli (uçuş planı, m22/m25).

## 4. 10 m / 10 m denemesi (kamera raporunun çim alan ayarı) — **karar kullanıcıda, varsayılan 8/8 kaldı**

Yeni senaryo `takip_yuruyen_10m`: aynı yol ve zamanlama, `drone.yukseklik_m: 10` (Follow Me yüksekliği de 10 m),
`FLW_TGT_DST 10`, `FLW_TGT_RS 0.3`. Kameranın yakın sınırı kendiliğinden 4.9 m oldu (`kadraj_yakin_sinir_m`, kamera
yüksekliğinden; 8 m'de 4.0 m). 3 koşu (`sonuclar/gorev9_takip_yuruyen_10m_x3`), 8/8 demo grubuyla aynı kod ve RS.

| Ölçüt (3'er koşu, ortalama (en az–en çok)) | 8 m / 8 m (varsayılan) | 10 m / 10 m |
|---|---|---|
| Yatay mesafe, ort. [m] | 7.91 (7.77–8.10) | 9.30 (9.16–9.38) |
| En az yatay mesafe [m] | **1.09** (0.45–1.94) | **3.95** (2.99–5.10) |
| Mesafenin `FLW_TGT_DST`'den farkı, ort. [m] | 1.56 | 1.41 |
| Kayıtta < 4 m / < 6 m [%] | 3.1 / 7.5 | **0.9 / 2.9** |
| 6 m altı geçiş [kez] | 2 (durma + köşe) | **1** (yalnız köşe; durmada en az > 6 m) |
| 3 m altı [s] | 1.4 | **0.0** (bir koşuda 0.1) |
| Kameranın yakın sınırı / altında [s] | 3.97 m / 1.9 | 4.91 m / 1.0 |
| Kişinin tamamı kadrajda [%] | 59 (57–60) | **93** (87–96) |
| En uzun kadraj dışı [s] | 11.0 | **1.1** |
| Köşeden sonra kişi kaybedildi | 3/3 | **0/3** (son FOLLOW_TARGET 89–91 s) |
| PX4 kestirim hatası, ort. [m] | 3.72 | **0.94** |
| Algılama oranı [%] | 60 (58–63) | 58 (55–62) |
| Kilit kaybı | 2.3 | **4.3** (4–5) |
| Kutunun konum hatası, ort. [m] | 0.27 | 0.30 |
| Duran kişi etrafında dönüş [°] | 198 | 215 (salınım yok) |
| Köşe: PX4 yetişme ort. [s] / arkada kalma en çok [°] | 2.3 / 147 | 2.2 / 152 |
| Köşe geçişinin ayrıştırması (toplam / dron / süzgeç / öngörü / konum) [m] | +7.0 / +1.3 / +2.1 / +3.5 / −0.1 | +6.1 / +1.6 / +2.6 / +1.9 / −0.2 |
| RTF | 0.83 | 0.92 |

Şekil: `gorev9_10m_8m_karsilastirma.png`, zaman çizelgesi `gorev9_yakin_gecis_cizelgesi_10m.png`.

**Okuma:**

- **PX4'ün aşması aynı kaldı, payı küçüldü:** köşede PX4'ün hedefi kişiyi yine ≈ 6 m geçiyor (ayrıştırma toplamı
  +6.1 / +7.0 m; mekanizma aynı), ama dron 10 m geride durduğu için kişiye en çok ≈ 3–5 m yaklaşıyor (8/8'de 0.5–2 m).
  Kişi dururken PX4'ün aşması (≈ 2.3 m) 10 m'de 6 m'nin altına inmiyor.
- **Asıl fark kadraj:** 10 m'de kişi köşede kameranın görüş alanında kalıyor (kişinin tamamı kadrajda %93, en uzun
  kayıp 1.1 s), PX4 kişiyi kaybetmiyor (kestirim hatası 0.94 m). 8/8'de üç koşunun üçünde köşeden sonra kişi kayboluyor.
- **Bedeli:** kişi görüntüde küçük (yeni simde baş–ayak ≈ 168 px, segmentasyon kutusu ≈ 180 px; 8/8'de ≈ 215 / 220 px), model onu aynı oranda buluyor
  ama kilit daha sık düşüyor (4.3 / 2.3), takip başında model duran kişiyi 3–10 s bulamadığı anlar oldu (kestirim
  takip başında 1–10 s bayat; kişi durduğu için dron yerinde bekledi). Dron başların ≈ 8 m üstünde (8/8'de ≈ 6 m),
  kişi 10 m geride: çekim daha uzaktan.
- **Sınırlar:** 3 koşu; yol aynı (bir keskin köşe, bir duruş); Hailo'da (m08) ve gerçek CM3'te 10 m'deki kişi boyunun
  algılamaya etkisi ölçülmedi; kamera raporunun 10/10'u "çim alanın açık kısmı" içindir (stad ayarı 8/8).

**Öneri (karar kullanıcının):** stok Follow Me ile sim koşularında 10/10, 8/8'den belirgin olarak daha güvenli ve kişiyi
kaybetmiyor; m06'nın Follow Me senaryosunun varsayılanını 10/10 yapmak düşünülebilir (tek satır: `takip_yuruyen.yaml`
`yukseklik_m: 10`, `FLW_TGT_DST: 10`; ya da `takip_yuruyen_10m`'i demo senaryosu yapmak). Bu, yakın geçişin sebebini
gidermez, yalnız payını büyütür: asıl çözüm m15'in en az mesafe korumasıdır (bölüm 3, Öneriler). Gerçek uçuş ayarı
(22.08: 8/8) ayrı karardır (m22/m25).

## 5. "En az demo (15.11)" listesi, madde madde

Koşular: `toplu.py --senaryo takip_yuruyen --tekrar 3` (`sonuclar/gorev9_takip_yuruyen_x3`, senaryonun yeni varsayılanı
RS 0.3 ile, `--param` yok) ve `toplu.py --senaryo kalabalik_park --tekrar 3` (`sonuclar/gorev9_kalabalik_park_x3`);
13.11, 05:25–05:41, son kodla, videolu. Koşu koşu sayılar `kabul-kosulari.md`'de.

| Madde (spec) | Sağlandı mı? | Sayılar |
|---|---|---|
| 1. `takip_yuruyen` v0.2 modeliyle (CPU) ve stok Follow Me ile kapalı döngüde uçar | **Evet, 3/3 GEÇTİ** | Model `person_detection_model_v0.2.pt` (sha256 `c5f6838b…`, `modeller.yaml` ile aynı), CPU 4 çekirdek, `imgsz` 640; mod "Follow Target" 25.5–25.9 s'den 90.6–90.8 s'ye kadar (ULog `nav_state` 19, kayıt penceresinde **%100**); FOLLOW_TARGET pencerede 80–95 (2.7–3.2 /sim-s), PX4'ün ULog'unda `follow_target` 35–38; `FLW_TGT_RS` 0.3 PX4'ten geri okundu; kişi dururken salınım yok (dönüş 196–202°, sahte hız 0.07–0.15 m/s); yatay mesafe ort. 7.87 / 7.77 / 8.10 m; konum hatası 0.24–0.31 m; LOS açı hatası 0.30–0.35°; uçtan uca 142–165 ms; RTF 0.90 / 0.78 / 0.80. **Sınır (açıkça):** üç koşunun üçünde de köşedeki yakın geçişten (en az 0.89 / 1.94 / 0.45 m) sonra kişi kadrajdan çıktı ve stok Follow Me onu bir daha bulamadı (≈ 81.4 s'den sonra kestirim bayat; bölüm 3) |
| 2. `kalabalik_park` `yok` ile koşar ve model ölçütleri çıkar (karıştırma, örtülme) | **Evet, 3/3 GEÇTİ** | Dron 10 m'de Hold (mod %100); hedef görünürken algılama %70.8 / 72.2 / 72.0 (IoU ort. 0.81–0.82); seçim doğru %65 / 61 / 66; **karıştırma:** yanlış kişi %6.4 / 11.7 / 7.6, bunun aynı kıyafetlisi %4.9 / 0 / 4.6 (hepsi 79–84 s'de, bölüm 6); yanlış pozitif 0–0.003 kutu/kare; kilit kaybı 1 / 2 / 1; **örtülme:** hedef 70.2–75.7 s çamın arkasında (kadrajda ama görünmüyor %19.4 / 19.2 / 19.9), gerçekten görünür %80.5; konum hatası 0.15–0.20 m; LOS açı hatası 0.21–0.26°; `model_ms` 96–103; RTF 0.73 / 0.72 / 0.76 (uyarı raporda) |
| 3. İki koşu da `rapor.html`, `ozet.json` ve VLC'de açılan `kosu.mp4` üretir; `TEZ_LOS` ULog'da görünür | **Evet, 6/6** | Her koşu klasöründe üçü de var; `ffprobe`: h264, yuv420p, 2000×720; süreler kayıt süresinin (`kayit_suresi_s`) ±0.06 s içinde; eksik kare 0, kaydedicinin düşürdüğü 0; VLC 3.0.20 açtı (`cvlc --play-and-exit` iki demo videosunu oynattı, çıkış 0; VLC 3.0.20). `TEZ_LOS` ULog'da / gönderilen: 281/281, 356/356, 345/345 (takip), 390/390, 383/383, 393/393 (kalabalık): **%100** |
| 4. `verify_pin.sh --worktree` geçer | **Evet** | "KILIT SAGLAM (v1.17.0)" (bölüm 7) |
| 5. Bu belgedeki belgeler hazırdır | **Evet** | Spec: "Yaklaşma mesafesi" (9. grubun kapalı döngü ölçümü eklendi), "Kamera parametreleri" (RTF, kişi boyu), "İnsan hedefi" (senaryolar, köşe anları), "Varsayımlar" (konum kaymasının etkisi), "PX4 stok Follow Target davranışı" (6. madde ve RS kararı), "Ölçüt Tanımları", "Açık Konular"; README; bu belge, `kabul-kosulari.md`, `tasks.md` |

**Görsel kontrol (9.5) Ahmet'in işi:** listesi ve dakika:saniyeleri bölüm 6'da; spec'in "Görsel kontrol" maddeleri orada
tek tek. 9.5'in `tasks.md`'deki kutusu bu yüzden açık bırakıldı.

## 6. Görsel kontrol (9.5) — Ahmet'in izleme listesi

Videolar (VLC'de **Ctrl+T** ile dakika:saniyeye gidilir; komutlar "Kendin dene" 3'te):

- `gorev9_takip_yuruyen_kosu.mp4` = `gorev9_takip_yuruyen_x3/kosu_1` (en temsili koşu: ölçütleri üçünün ortalamasına en
  yakın), 63.5 s, video 0:00 = sim 25.9 s.
- `gorev9_kalabalik_park_kosu.mp4` = `gorev9_kalabalik_park_x3/kosu_3`, video 0:00 = sim 26.7 s.
- `gorev9_en_yakin_gecis.mp4`: en yakın geçişin (`gorev9_takip_yuruyen_x3/kosu_3`, 79.3 s, 0.45 m) ±5 s'lik kesiti.

**`takip_yuruyen` (dron 8 m'den stok Follow Me ile, RS 0.3):**

| Video | Sim | Ne olur | Neye bak (spec "Görsel kontrol") |
|---|---|---|---|
| 0:00–0:34 | 25.9–60 s | Takip başı: kişi duruyor | Dron kişinin etrafında **yalnız bir kez** döner (kuzeyden güneye, ≈ 196°; PX4'ün başlangıçtaki "kuzey" varsayımı). Mor ok (PX4'ün sandığı rota) sabit kalır, durum satırı "PX4: hedefin hızı 0.0–0.2 m/s" (RS 0.3: salınım yok; 9.8'deki `gorev9on_RS_0.1_kosu.mp4` ile karşılaştır) |
| 0:34–0:44 | 60–70 s | Kişi doğuya yürür | **Model kutusu hedefin üstünde, gecikmesi görülür:** kalın kırmızı kutu mavi hakem kutusunun biraz gerisinde (sol üstte "… ms önceki kare", uçtan uca ≈ 140–165 ms). **Hakem kutusu hedefle çakışır.** **Dron hedefi 8 m geriden izler:** turuncu üçgen yeşil yıldıza (8 m arkası) yakın, mesafe 7.5–8.5 m. **Üstten görünüm kamera görüntüsüyle tutarlı:** kişi açık mavi alanın (kameranın gördüğü yer) içinde |
| 0:44.8–0:46.3 | 70.7–72.2 s | Kişi durur | Durum satırı turuncu "6 m'den yakın geçiş: kişi durdu ya da hızlandı"; içi boş mor kare (PX4'ün süzülmüş hedefi) kişinin ≈ 1.5 m doğusuna geçer, dron 5.6 m'ye gelir (0:45.5) |
| 0:47.1 | 73.0 s | Köşe 2: kişi kuzeye koşmaya başlar | Mor ok kuzeye döner (≈ 2 s sonra) |
| 0:51.6–0:56.0 | 77.6–81.9 s | Köşe 3: kişi yavaşlayıp batıya döner | İçi boş mor kare kuzeye doğru kişiyi metrelerce geçer; dron kişinin üstüne gelir (**0:53.5, 0.89 m**), durum satırı kırmızı "dron hedefe 3 m'den yakın · 6 m'den yakın geçiş: köşe / yön değişimi"; solda kişi kadrajın altından çıkar, **HEDEF YOK** |
| 0:55.5–son | 81.4–89.4 s | PX4 kişiyi kaybetti | "PX4 kestirimi bayat"; dron bayat noktanın gerisinde bekler, kişi kadrajda yok (bölüm 3: stok modun davranışı) |

**`kalabalik_park` (dron 10 m'de Hold, beş kişi):**

| Video | Sim | Ne olur | Neye bak |
|---|---|---|---|
| 0:00–0:33 | 26.7–60 s | Kişiler bekliyor, kilit | Mavi kutu hedefte, turuncu kutular diğerlerinde |
| 0:43.5–0:49.0 | 70.2–75.7 s | **Örtülme:** hedef çamın arkasında | Mavi kutu küçülür / kaybolur, haritada kişi görünmeye devam eder |
| 0:53.8–0:55.1 | 80.6–81.9 s | **Yanlış kişi** | Kalın kırmızı kutu (PX4'teki model sonucu) turuncu "insan3" kutusunun (sarı üst) üstünde |
| 0:55.2–0:56.5 | 81.9–83.2 s | **Yanlış kişi, aynı kıyafetli** | Kalın kırmızı kutu turuncu "insan4" kutusunun (hedefle aynı mavi üst / siyah alt) üstünde; mavi hakem kutusu başka yerde (ör. 0:55.9, sim 82.7 s: kırmızı 0.79 insan4'te, hedef insan3'ün arkasında; kare gözle doğrulandı) |

**Yanlış kişiye geçişler: videoda ve `yanlis_kisi_orani`'nda aynı anlar** (`ozet.json` → `olcutler.yanlis_kisi_orani`
= yanlış kişideki işlenmiş kare / işlenmiş kare; aynı kurala göre koşu klasöründen kare kare çıkarıldı, sayılar
`ozet.json` ile birebir aynı; videoda kırmızı kutu karenin gönderildiği anda, yani ≈ 0.13 s sonra görünür):

| Koşu | `yanlis_kisi_orani` | Video (sim) | Kim |
|---|---|---|---|
| `kosu_1` | 0.064 (25 / 390 kare) | 0:53.9–0:54.2 (80.7–81.0 s), 0:54.9 (81.7 s) | insan3 (başka kıyafet) |
| | | 0:55.0–0:56.4 (81.7–83.1 s), 19 kare | insan4 (**aynı kıyafet**) |
| `kosu_2` | 0.117 (45 / 383) | 0:52.4–0:54.2 (79.1–80.8 s), 24 kare | insan3 |
| | | 0:55.1–0:57.4 (81.7–84.0 s), 21 kare | insan3 |
| `kosu_3` | 0.076 (30 / 393) | 0:53.8–0:55.1 (80.6–81.9 s), 12 kare | insan3 |
| | | 0:55.2–0:56.5 (81.9–83.2 s), 18 kare | insan4 (**aynı kıyafet**) |

Bütün yanlış kişi anları hedefin çamın arkasından çıkıp geri döndüğü 79–84 s'de: hedef, sarı giysili kişinin (insan3,
20 s bekleyip yavaşça yürür) yanından geçerken ve aynı kıyafetli kişi (insan4) yolunu keserken.

**`gorev9_en_yakin_gecis.mp4`** (sim 74.3–84.3 s, 10 s): 0:05'te en yakın an (0.45 m). İçi boş mor kare (süzülmüş hedef)
ile kişi (mavi nokta) arasındaki mesafeye ve dronun kişinin üstünden geçişine bak.

Gösterilen bir sorun düzeltilirse aynı sahne yeniden koşularak doğrulanır (`toplu.py --senaryo takip_yuruyen --tekrar 3`).

## 7. Testler ve doğrulama (9.1, 9.7)

| Kontrol | Sonuç |
|---|---|
| Önce testler (yeni kod ve iki hata için) | `test_yakin_gecis.py` (yeni, 5 test: bacaklar ve köşeler, PX4'ün köşeye yetişmesi ve aşma, 6 m altı geçişlerin sebebi ve mesafe payları, ayrıştırmanın beş payı, ULog → dünya dönüşümü); `test_olcum.py` (`measure`'ın yeni bölümleri, günlük satırı), `test_rapor.py` +1 (yakın geçiş ve köşe tabloları, kontrol satırı, grafik), `test_toplu.py` +1 (köşe tablosu, koşuların geçişleri), `test_video.py` +1 ve 1 genişletme (ayar noktası halkası: 8. grubun hatası; durum satırında geçişin sebebi), `test_hedef.py` +1 ve 1 değişiklik (RS kararı: ayrı yama). Hepsi önce kırmızı görüldü, sonra kod yazıldı; NaN yaw hatasının testi eski kodla kalıyordu (bir NaN'dan sonra bütün rota NaN) |
| `$P -m pytest tez/sim/testler -q` | **234 geçti** (önce 225; +9), 1 uyarı (önceden de vardı, protobuf). Gazebo, PX4, `torch` gerekmez |
| `ruff format` + `ruff check` (`tez/sim/ruff.toml`, ruff 0.16.9) | temiz (yeni modül yok; `known-first-party` değişmedi) |
| `tez/pin/verify_pin.sh --worktree` | **KILIT SAGLAM (v1.17.0)** (son kontrol 13.11 06:26, bütün değişikliklerden sonra) |
| `tez/sim/araclar/f0_kabul.sh` | **GEÇTİ** (1 dk 9 s): 21/21 başlangıç parametresi PX4'te, kamera 2304×1296 30.3 kare/sim-s fx 1773.9, "Hold" + "Follow Target" listede, Hold'da 15 s sapma yatay 0.07 / dikey 0.08 m, temiz kapanış |
| `tez/sim/araclar/f1_kabul.sh` (`--modelsiz`, `yok`) | **GEÇTİ** (4 dk 37 s): hedef doğrulama farkı en çok 0.13 / 0.13 m (sınır 0.30), iki koşu arası 0.000 m (sınır 0.15), RTF 0.94 / 0.94; iki koşu da `kosu.mp4` üretti |
| Demo koşuları | `takip_yuruyen` ×3 ve `kalabalik_park` ×3: 6/6 GEÇTİ (bölüm 5); ayrıca RS 0.2 / 0.3 × model / hakem 12/12 ve 10/10 ×3 GEÇTİ; 21 koşunun hiçbiri yeniden denenmedi |
| Videolar (`ffprobe`) | 21 koşunun 21'i h264 / yuv420p / 2000×720, süre kayıt süresinin ±0.06 s içinde, eksik kare 0, kaydedicinin düşürdüğü 0 |
| `git status --short` | `sonuclar/`, `.pt`, `.ulg`, `.mp4` görünmüyor; yalnız bölüm 10'daki dosyalar |
| Süreçler | Her zincirden önce `pgrep -x px4` / `pgrep -f "^gz sim"` boştu; sonunda açık PX4, Gazebo, ffmpeg ya da yardımcı süreç kalmadı |

## 8. Karşılaşılan sorunlar

- **Videoda "PX4'ün dronu gönderdiği yer" yanlış noktadan çiziliyordu (8. gruptan kalan hata, test önce yazıldı):**
  mor halka ve mor ×, kestiricinin konumu (E) + `FLW_TGT_DST` olarak çiziliyordu. PX4 ise dronu görevin süzülmüş hedefine
  (F) göre koyuyor ve köşede F, E'den 1.5–3 m ileride: halka tam yakın geçiş anlarında metrelerce yanlış yerdeydi.
  Düzeltme: halka PX4'ün kendi ayar noktası (`trajectory_setpoint`), × `desired_position_raw`, F içi boş mor kare olarak
  ayrıca çiziliyor (`video.px4_marks`, `test_video.py`). Videolu bütün 9. grup koşuları düzeltilmiş kodla yapıldı.
- **Bacak bulma, hakemde bir NaN yaw'dan sonra bütün rotayı kaybederdi** (kod incelemesinde bulundu, koşularda NaN
  olmadı): `np.unwrap` NaN'ı sonraki bütün örneklere taşıyor. Önce test (`test_yakin_gecis.py`, eski kodla kalıyordu:
  bir NaN'dan sonra rota hep NaN), sonra NaN'ı bir önceki yaw'la doldurma.
- **9.8 belgesinde köşe anları yanlış yazılmıştı** (≈ 71.6 / ≈ 75 s; hakemden 73.0 / 77.6 s). Betik gecikmeleri doğru
  anlardan hesaplamıştı: aynı koşuda yeni kod aynı sayıları verdi (2.58 / 1.81 / 1.69 s). Belge düzeltildi.
- **Spec'te 8/8'de kişinin görüntüdeki boyu ≈ 195 px yazıyordu** (kamera raporu, eski sim); yeni simde hakemden ölçülen
  baş–ayak ≈ 215 px, segmentasyon kutusu ≈ 228 px (kişi yürürken ortanca). Spec güncellendi.
- **Video efsanesine "süzülmüş hedefi" eklenince son öğe sağ kenardan taşıyordu**; FOLLOW_TARGET öğesi bir üst satıra
  alındı (iki satır 668 ve 635 px, 720'ye sığıyor).
- **Kendi hatalarım (koşmadan, testle yakalandı):** `toplu._html` içinde yerel `runs` (HTML metni) yeni parametreyi
  gölgeliyordu; bir testin beklediği metin ("köşe") günlükte "Köşeler" olarak yazıyordu (test düzeltildi).
- **Bu oturumun RTF'i 0.76–0.90** (videolu, model 4 çekirdek): 7. gruptan (0.95–0.98) düşük, 9.8 ön işiyle aynı. Bütün
  gruplar aynı oturumda ve aynı video ayarıyla koşuldu; sim zamanıyla ölçülen her şey RTF'den bağımsızdır.

## 9. Kalan sim-gerçek farkları

- **Yaklaşmaların mekanizması PX4'ün kendisi** (süzülmüş hedef, hız ileri beslemesi, öngörü, en az mesafe korumasının
  olmaması): gerçek dronda da aynısı olur. Büyüklükleri ise sime bağlı: kişinin yolu (3 m/s koşudan sonra keskin dönüş,
  2 m/s²'lik duruş; gerçek bir insan dronu görünce farklı davranabilir), simdeki X500'ün kütlesi ve kazançları (gerçek
  araç ölçülene kadar standart X500; ataletin payı ≈ 0.5–1.5 m), rüzgâr yok.
- **`FLW_TGT_RS 0.3` bir sim seçimidir.** Gerçek araçta GPS (M8N) ve pusula gürültüsü simdekinden büyük; sahte hız ve
  doğru RS farklı çıkabilir. Gerçek dronun parametre dosyasında 0.1 kaldı; uçuşta denenecekse ayrı karar (m25).
- **Köşeden sonra kişinin kaybı** kameranın 45° sabit montajına ve modelin kişiyi dronun hemen altında bulamamasına bağlı;
  gerçek CM3'ün görüş açısı ve gimbal olmaması simle aynı. Gerçek modelde (Hailo, m08) kaçırma oranı farklı olabilir.
- **Ayrıştırma ULog'a dayanır:** gerçek araçta da `follow_target*` konuları ancak kaydedici onları alırsa var (spec "Açık
  Konular"); `trajectory_setpoint` ve `vehicle_local_position` stok kayıtta var.
- **Model laptop CPU'sunda** (v0.2; kare başına ≈ 100 ms, sonuç kareden ≈ 140 sim-ms sonra) ve RTF 0.8 civarında: gerçek
  zamanda gecikme ve kaçırma biraz daha kötü olur.
- **Hakem kusursuz:** "mükemmel algılayıcı" koşuları PX4'ün kendi bedelinin alt sınırıdır; gerçekte konum gürültüsü ekler.

## 10. Dosyalar ve commit ayrımı

**A. RS varsayılanı (karar 1; ayrı commit):** yama `~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9_RS_varsayilan.patch`
(temiz HEAD `c557f3954e`'nin ayrı bir klonunda uygulandı: 226 test geçti (HEAD'in 225'i + yeni RS testi), ruff temiz).

| Dosya | Değişiklik |
|---|---|
| `tez/sim/senaryolar/takip_yuruyen.yaml` | `takip.px4_parametreleri`'ne `FLW_TGT_RS: 0.3` ve yorumu (sim seçimi, karar, gerçek dronda 0.1, gerekçe, ölçüm belgesi) |
| `tez/sim/testler/test_hedef.py` | `takip_yuruyen`'in başlangıç parametresi listesinde `FLW_TGT_RS 0.3`; yeni `test_follow_me_scenario_uses_the_chosen_flw_tgt_rs` (değer, kaynak, PX4'ün 0.1–1.0 kısması, `gercek_dron.params`'ta yok) |

**B. Görev grubu 9 (geri kalan her şey):**

| Dosya | Değişiklik |
|---|---|
| `tez/sim/araclar/olcum.py` | `Px4Follow`, `legs`, `corner_metrics`, `near_passes`, `decompose`; `KEYS`'e 20 anahtar; `measure` → `koseler`, `yakin_gecis` bölümleri; ULog konularına `trajectory_setpoint`, `vehicle_local_position` |
| `tez/sim/araclar/rapor.py` | Sebep ve pay metinleri, renkleri; iki yeni ölçüt grubu; "yakin_gecis" kontrolü; "Yakın geçişler" ve "Köşeler" tabloları; "Yakın geçişler ve sebepleri" grafiği |
| `tez/sim/araclar/toplu.py` | Ana tabloya yeni anahtarlar; köşe tablosu; koşuların yakın geçişleri |
| `tez/sim/araclar/video.py` | `px4_marks` (halka: ayar noktası, ×: `desired_position_raw`, içi boş kare: süzülmüş hedef); `Px4Timeline` `olcum.Px4Follow`'dan; durum satırında geçişin sebebi; efsane |
| `tez/sim/araclar/senaryo.py` | Günlüğe yakın geçiş ve köşe satırları |
| `tez/sim/senaryolar/takip_yuruyen_10m.yaml` | Yeni: 10 m / 10 m (RS 0.3 dahil; A reddedilirse bu satır da silinir) |
| `tez/sim/testler/test_yakin_gecis.py` | Yeni (5 test) |
| `tez/sim/testler/test_olcum.py`, `test_rapor.py`, `test_toplu.py`, `test_video.py` | Bölüm 7 |
| `tez/sim/README.md` | Ölçüt tablosu, RS kararı ve yakın geçiş paragrafı, 10 m senaryosu, video açıklaması |
| `agent-os/specs/2026-11-10-m06-sim-ortami/spec.md` | Karar 2 ve 3 (9. madde), "Ölçüt Tanımları" (4 satır, giriş), "PX4 stok Follow Target davranışı" (6. madde, RS kararı), Follow Me ayarları, "Kamera parametreleri" (RTF, kişi boyu), "İnsan hedefi" (senaryolar, köşe anları), "Varsayımlar" 5, "Yaklaşma mesafesi" (9. grubun ölçümü), Dosya Planı, Test Planı, "Açık Konular" |
| `agent-os/specs/2026-11-10-m06-sim-ortami/tasks.md` | 9.x, 11.6 (RTF payı) |
| `implementation/gorev-grubu-09.md` (yeni), `kabul-kosulari.md`, `gorev-grubu-08.md` (açık kararlar kapandı), `gorev-grubu-09-on-followme-ayar.md` (köşe anları düzeltildi, ölçütlerin taşındığı) | Belgeler |

İki commit hangi sırayla atılırsa atılsın testler geçer: A'sız B'de `test_hedef.py` eski listeyi (RS'siz) bekler ve
`takip_yuruyen.yaml` RS'sizdir; A'da ikisi birlikte değişir (doğrulandı: temiz HEAD'in ayrı bir klonunda yalnız B → 233 test, ruff temiz; RS yaması B'nin üstüne de uygulanıyor; çalışma ağacında A + B → 234).

## 11. Görseller ve betikler (repo dışı)

`~/Desktop/Follow/3_m06_Simulasyon/Deneme/`:

| Dosya | Ne |
|---|---|
| `gorev9_takip_yuruyen_kosu.mp4` | Demo `takip_yuruyen` (en temsili koşu, `gorev9_takip_yuruyen_x3/kosu_1`) |
| `gorev9_kalabalik_park_kosu.mp4` | Demo `kalabalik_park` (en temsili koşu, `gorev9_kalabalik_park_x3/kosu_3`) |
| `gorev9_takip_yuruyen_10m_kosu.mp4` | 10 m / 10 m (en temsili koşu, `gorev9_takip_yuruyen_10m_x3/kosu_2`) |
| `gorev9_en_yakin_gecis.mp4` | En yakın geçişin ±5 s'si (`gorev9_takip_yuruyen_x3/kosu_3`, sim 74.3–84.3 s, 0.45 m) |
| `gorev9_yakin_gecis_cizelgesi.png` | Demo koşularının mesafe eğrisi, renkli sebep bantları, köşeler ve her geçişin ayrıştırması |
| `gorev9_yakin_gecis_cizelgesi_10m.png` | Aynısı 10 m / 10 m |
| `gorev9_RS_0.2_0.3_karsilastirma.png` | RS 0.2 / 0.3 (ve 9.8'in 0.1 / 0.3'ü), model ve hakem, 24 ölçüt |
| `gorev9_10m_8m_karsilastirma.png` | 8/8 ile 10/10, 21 ölçüt |
| `gorev9_toplu_takip_yuruyen_ekran.png`, `gorev9_toplu_kalabalik_park_ekran.png` | `toplu.html` ekran görüntüleri (ana tablo, köşeler, yakın geçişler) |
| `gorev9_RS_varsayilan.patch` | Karar 1'in yaması (bölüm 10 A) |
| `gorev9_betikler/` | Bu belgenin tablolarını, şekillerini ve kesitlerini üreten betikler (repoya girmedi): `ortak.py`, `karsilastir.py`, `yakin_cizelge.py`, `sebep_dagilimi.py`, `ortalama.py` (fazlara göre ayrıştırma), `yanlis_kisi.py`, `temsili.py`, `satirlar.py` (kabul tablosu satırları), `gorseller.sh`, `video_kontrol.sh`, `yama_dogrula.sh` |

Koşu klasörleri (`tez/sim/sonuclar/`, git dışında): `gorev9_RS0.2_model_x3`, `gorev9_RS0.3_model_x3`, `gorev9_RS0.2_hakem_x3`,
`gorev9_RS0.3_hakem_x3`, `gorev9_takip_yuruyen_x3`, `gorev9_kalabalik_park_x3`, `gorev9_takip_yuruyen_10m_x3`; her birinde
`toplu.html` (her koşunun `rapor.html` ve `kosu.mp4` bağlantısıyla); `gorev9_f0.log`, `gorev9_f1.log`.

## 12. Açık kararlar ve bekleyenler

- **Görsel kontrol (9.5):** Ahmet'te; izleme listesi bölüm 6, komutlar "Kendin dene" 3.
- **10 m / 10 m varsayılan olsun mu?** (bölüm 4): sim koşularında belirgin olarak daha güvenli ve kişiyi kaybetmiyor;
  bedeli kilit kaybı ve çekim uzaklığı. Karar kullanıcıda; m06'da tek satırlık iş.
- **RS 0.2 daha çok koşuyla ölçülsün mü?** 3 koşunun ikisinde salınım vardı; seçim 0.3 (bölüm 2). İstenirse 3 koşu daha.
- **Takım arkadaşlarına öneriler** (bölüm 3, "Öneriler"): m15 en az mesafe koruması ve kişi kadrajdan çıkınca davranış;
  m11 süzülmüş hız ve durma/dönme anının hızlı kestirimi; m01'e en az mesafe / 6 m altı payı ölçütü. Kime iletileceği
  kullanıcının ve Hüseyin'in kararı.
- **`FLW_TGT_MAX_VEL`** için daha çok koşuyla ayrı karşılaştırma (9.8'den açık; bu grupta yapılmadı).
- **Videoda yanlış kişi işareti (öneri, yapılmadı):** durum satırı seçilen kutunun başka bir kişide olduğunu (hakeme
  göre) şimdilik söylemiyor; kutular videoda görünüyor ve anlar bölüm 6'da listeli. İstenirse `video.py`'ye küçük bir
  ek (testli); mevcut videolar ancak yeniden koşulunca değişir (kareler saklanmadı).
- **Kare kaydının RTF payı:** 11. grupta (karar 3, `tasks.md` 11.6).

---

## Kendin dene

Bu bölümdeki her şey bilgisayarında hazır: koşular yapıldı; videolar, resimler ve betikler
`~/Desktop/Follow/3_m06_Simulasyon/Deneme/` klasöründe (`gorev9_` ile başlayanlar).

**Başlamadan:** Terminal açmak için **Ctrl+Alt+T**. Aşağıdaki gri kutulardaki satırları **tek tek** kopyala, terminale
**Ctrl+Shift+V** ile yapıştır ve **Enter**'a bas. Her satır tek başına çalışır (değişken yok; yeni bir terminalde de
olur). Bir komutu yarıda kesmek için **Ctrl+C**. VLC kısayolları: **Boşluk** duraklat/sürdür, **Ctrl+T** belirli bir
zamana git (dakika:saniye yaz), **E** bir kare ileri, **Shift+→ / Shift+←** 3 s ileri/geri, **[** / **]**
yavaşlat/hızlandır, **F** tam ekran. Uçbirime düşen "Timestamp conversion failed" satırları VLC'nin kendisinden gelir.

### 1. "Dron neden bu kadar yakın?" tek resimde

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9_yakin_gecis_cizelgesi.png
```

Üç demo koşusu üst üste: siyah çizgi dron–kişi mesafesi (gri çizgi 8 m, kırmızı kesikli 6 m, noktalı 4 m). **Sarı
bant** "kişi durdu" (≈ 71 s), **turuncu bant** "köşe / yön değişimi" (≈ 78–80 s); bantın içindeki sayı en az mesafe.
Dikey kesikli çizgiler köşeler (kişinin yeni yönü). En alttaki çubuklar her geçişte "8 m'den neden yakın": turuncu
dronun ataleti, koyu mor PX4'ün süzülmüş hedefinin kişiyi geçmesi, açık mor PX4'ün eski hızla öngörmesi, taralı mavi
konum hatası (eksi: dronu uzaklaştırıyor), gri ölçümün yaşı; siyah çizgi toplam.

### 2. En yakın geçişi videoda izle (10 s'lik kesit)

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9_en_yakin_gecis.mp4 2>/dev/null
```

**[** ile yavaşlat. Sağdaki haritada **içi boş mor kare** PX4'ün "kişi burada" diyip dronu ona göre konumladığı nokta
(süzülmüş hedef), **mavi nokta** kişinin gerçek yeri. Kişi batıya dönerken içi boş mor kare kuzeye gitmeye devam eder,
dron (turuncu üçgen) onun 8 m gerisine, yani kişinin tam üstüne gelir. Altta durum satırı kırmızıya döner.

### 3. Demo videoları ve görsel kontrol (9.5, senin işin)

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9_takip_yuruyen_kosu.mp4 2>/dev/null
```

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9_kalabalik_park_kosu.mp4 2>/dev/null
```

Neye hangi dakikada bakacağın: bu belgenin **bölüm 6**'sındaki iki tablo. Kısaca:
`takip_yuruyen`: 0:00–0:34 dron duran kişinin etrafında yalnız bir kez döner; 0:34–0:44 kırmızı model kutusu mavi
hakem kutusunun biraz gerisinde (gecikme), dron yeşil yıldızın (8 m arkası) yanında; 0:45.5 kişi durunca 5.6 m;
0:53.5 köşede 0.89 m; 0:55.5'ten sonra PX4 kişiyi kaybeder. `kalabalik_park`: 0:43.5–0:49.0 hedef çamın arkasında;
0:53.8–0:56.5 kalın kırmızı kutu başka birinin turuncu kutusunda (yanlış kişi).

Videolarda gördüğün bir sorunu bana dakika:saniyesiyle yaz; düzeltmeyi aynı sahnede yeniden koşarak doğrularım.

### 4. FLW_TGT_RS 0.2 / 0.3 karşılaştırması

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9_RS_0.2_0.3_karsilastirma.png
```

Her küçük grafik bir ölçüt; mavi model kutusuyla, yeşil mükemmel algılayıcıyla (hakem); noktalar koşular, çubuk
ortalama. İlk satır kişi dururken salınım (küçük iyi): RS 0.3'ün üç noktası hakem kadar düşük, RS 0.2'nin ikisi yüksek.
Sonraki satırlar köşelerin ve yakın geçişin bedeli.

```bash
firefox ~/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev9_RS0.2_model_x3/toplu.html
```

```bash
firefox ~/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev9_RS0.3_model_x3/toplu.html
```

### 5. 10 m / 10 m denemesi

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9_10m_8m_karsilastirma.png
```

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9_takip_yuruyen_10m_kosu.mp4 2>/dev/null
```

Videoda köşeye (≈ 0:52–0:56) bak: içi boş mor kare yine kişiyi kuzeye doğru geçer, ama dron 10 m geride olduğu için kişinin üstüne gelmez (en az ≈ 5 m) ve kişi solda kadrajda kalır; koşu sonuna kadar takip sürer. Durum satırında kişi dururken (≈ 0:45) 6 m uyarısı çıkmaz. Zaman çizelgesi:

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9_yakin_gecis_cizelgesi_10m.png
```

### 6. Toplu sayfalar ve raporlar

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9_toplu_takip_yuruyen_ekran.png
```

```bash
firefox ~/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev9_takip_yuruyen_x3/toplu.html
```

```bash
firefox ~/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev9_kalabalik_park_x3/toplu.html
```

```bash
firefox ~/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev9_takip_yuruyen_x3/kosu_1/rapor.html
```

`toplu.html`'de yeni bölümler: "Köşeler (PX4'ün yeni yöne yetişmesi ve aşma)" ve "Yakın geçişler (< 6 m)" (her koşunun
geçişleri; "Ayrıştırmalarıyla" açılır). `rapor.html`'de "Kontroller"de 6 m satırı, "Yakın geçişler" ve "Köşeler"
tabloları, "Yakın geçişler ve sebepleri" grafiği.

### 7. Kendin koştur (pencere yok)

Önce açık bir sim olmadığından emin ol (iki satır da bir şey yazmamalı):

```bash
pgrep -x px4
```

```bash
pgrep -f "^gz sim"
```

Demo (`takip_yuruyen`, RS 0.3 senaryodan, 3 koşu, ~8 dakika; sonuç klasörü en son satırda yazar):

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/toplu.py --senaryo takip_yuruyen --tekrar 3
```

Kalabalık park (3 koşu, ~9 dakika):

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/toplu.py --senaryo kalabalik_park --tekrar 3
```

10 m / 10 m (3 koşu, ~8 dakika):

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/toplu.py --senaryo takip_yuruyen_10m --tekrar 3
```

PX4'ün varsayılan `FLW_TGT_RS 0.1`'iyle karşılaştırmak (ya da 0.2'yi daha çok koşuyla ölçmek: `0.1` yerine `0.2`):

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/toplu.py --senaryo takip_yuruyen --tekrar 3 -- --param FLW_TGT_RS=0.1
```

Bir koşunun yakın geçişlerini ve köşelerini metin olarak görmek (koşunun günlüğü; kendi koşunda klasör adını değiştir):

```bash
grep -E "yakın geçiş|Köşeler" ~/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev9_takip_yuruyen_x3/kosu_1.log
```

### 8. Kontroller

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python -m pytest tez/sim/testler -q
```

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && tez/pin/verify_pin.sh --worktree
```

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && tez/sim/araclar/f0_kabul.sh
```

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && tez/sim/araclar/f1_kabul.sh
```

Beklenen: `234 passed`; `KILIT SAGLAM (v1.17.0)`; F0 (~1 dakika) ve F1 (~5 dakika) sonunda `SONUÇ: GEÇTİ`.
