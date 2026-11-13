# Görev Grubu 9 (ön iş, `tasks.md` 9.8) — Stok Follow Me ayar karşılaştırması ve "sahte hız"

- Tarih: 13.11.2026 · dal `ozellik/m06-sim-ortami` · taban commit `33d8ec8842` (Görev grubu 7) + çalışma ağacı
- 9. grubun geri kalanından önce yapıldı (kullanıcı isteği). Aynı oturumda 8. grup (video) da yapıldı; iki ayrı commit
  (`gorev-grubu-08.md`, "Commit ayrımı"). Bu iş yalnız ölçüt ekler; **m06'nın varsayılan parametreleri değişmedi.**
- Durum: **ölçüldü ve belgelendi**, commit'lenmedi. Karar kullanıcının.

## Kullanıcının sorusu

"Model kişiyi her karede biraz farklı yerde buluyor, PX4 bunu 'kişi 1 m/s'den hızlı gidiyor' sanıyor ve dron
salınıyor. Bunu nasıl giderebiliriz?" Asıl çözümler takım arkadaşlarının işi: Pi tarafında konum süzgeci (m11,
Ortatepe) ve kendi takip modu (m15, Kurt); m06'ya konum süzgeci eklenmedi. Bu belge m06'nın kendi kapsamındaki ilk
adımı yapar: (1) mekanizmayı sayıyla açıklar, (2) PX4'ün kendi ayarlarıyla ne kadar düzeldiğini ölçer, (3) m11 ve
m15'e karşılaştırma tabanı olacak sayıları verir.

## Kısaca

- **Neden salınıyor (ölçüldü):** kişi dururken modelin kutusundan bulunan konum kareden kareye yalnız 7 cm oynuyor, ama
  ortalama 0.5 m **drona doğru** kayık ve bu kayma dronun baktığı yönle birlikte dönüyor (std 0.7 m); model kişiyi
  sürenin üçte biri kadar da bulamıyor. PX4'ün hedef kestiricisi bunu ortalama 0.57 m/s'lik **sahte hıza** çeviriyor;
  sahte hız zamanın %17'sinde 1 m/s'yi aşıyor, her aşışta PX4 kişinin "rotasını" değiştiriyor ve dronu kişinin yeni
  "arkasına" gönderiyor (takip başında 14.5 kez). Dron dönünce kayma da dönüyor: geri besleme. Sonuç: dron duran kişinin
  etrafında ortalama 530° dönüyor. Mükemmel algılayıcıyla (gürültüsüz konum) sahte hız 0, dönüş 194° (yalnız PX4'ün
  başlangıçtaki "kuzey" varsayımından).
- **PX4 ayarıyla ne kadar düzeliyor (her ayar 3 koşu):** `FLW_TGT_RS 0.3` salınımı gideriyor (dönüş 183–189°, sahte hız
  0.15 m/s, 1 m/s'yi aşan süre %0–1); yürüyüşte rota hatası değişmiyor. Bedeli köşelerde: PX4'ün rotası her köşeye 0.5–0.9 s
  geç yetişiyor, dron kişiye daha yakın geçiyor (en az 0.66–1.56 m; mükemmel algılayıcıyla 3.2 → 2.2 m). RS 0.5 ve 0.8
  salınımı tamamen kaldırıyor ama PX4 köşelere yetişemiyor (rota hatası 83° / 120°, kişi kadrajdan çıkıyor).
  `FLW_TGT_MAX_VEL` kestiriciye girmez: 3'te salınım sürüyor ama kişi kadrajda daha çok kalıyor (%89–92); 8'de üç koşuda
  da duran kişide sakin (kapalı döngünün etkisi), ama bir koşuda dron kişinin tam üstünden geçti.
- **Öneri:** stok Follow Me kullanılacaksa `FLW_TGT_RS 0.3` (bedeliyle birlikte); MAX_VEL için öneri yok. Karar
  kullanıcının; m06'nın varsayılanları değişmedi. Asıl çözüm Pi tarafında süzülmüş konum ve **süzülmüş hız**
  göndermek (m11): PX4 kodu, gelen hızı her 100–200 ms'de %83 ağırlıkla aldığı için duran kişide sahte hızın RS'den
  bağımsız olarak kalkacağını gösteriyor (denenmedi; bölüm 6).

## 1. Sayıyla: kişi dururken ne oluyor?

"Takip başı": dron Follow Target'ta, kişi henüz yürümüyor (mod seçimi ≈ 25 s → 60 s, ≈ 35 s). `takip_yuruyen`, 8 m /
45°, v0.2 modeli CPU'da, varsayılan `FLW_TGT_RS 0.1`. Model kaynağında 6 koşu var (9.8'in 3 koşusu + aynı ayarla 3
videosuz koşu, 8. grubun RTF karşılaştırması için); hakem 3 koşu. Sayılar `olcum.follow_start_metrics`'in yeni
ölçütleri (bütün koşularda `ozet.json` → `olcutler`; tanımlar spec "Ölçüt Tanımları").

| Takip başında | Model kutusu (6 koşu) ort. (en az–en çok) | Mükemmel algılayıcı, `--los hakem` (3 koşu) |
|---|---|---|
| Gönderilen FOLLOW_TARGET sıklığı | 5.6 /s (4.3–6.7) | 9.9 /s |
| Model kişiyi bulamadığı boşluklar (> 0.5 s) | 7–12 kez, en uzunu 1.8–3.4 s, sürenin %27–47'si | yok |
| Gönderilen konumun titreşimi (hatanın yatay std'si) | **0.69 m** (0.51–0.90) | 0 |
| Ardışık iki konumun farkı (ortanca) | **0.07 m** (0.04–0.09) | 0 |
| Hatanın drona doğru bileşeni (ort.) | **+0.48 m** (+0.34…+0.59) | 0 |
| PX4 sahte hızı (`vel_est`) ort. / p95 / en çok | **0.57 / 1.50 / 2.26 m/s** (ort. 0.24–0.79) | 0 |
| Sahte hızın ≥ 1 m/s olduğu süre | **%17** (%2–29) | %0 |
| PX4'ün varsaydığı rota değişti | **14.5 kez** (2–23) | 0 (34 s "kuzey" kaldı) |
| Dronun duran kişi etrafında döndüğü açı | **530°** (191–672) | 194° (193–195) |

**Ne oluyor (sahte hız şekli, `gorev9on_sahte_hiz.png`):**

1. Konum kareden kareye çok az oynuyor (7 cm); asıl hata **yavaş değişen, dronun baktığı yöne bağlı bir kayma**:
   ortalama 0.5 m drona doğru (kutunun alt kenarı kameraya yakın ayaktır; bacak açıklığı ve gölgenin payı da olabilir),
   std 0.7 m. Dron kişinin etrafında döndükçe "drona doğru" yönü de döner; PX4'e kişi dronla birlikte hareket ediyormuş
   gibi gelir. Model kişiyi sürenin üçte biri kadar bulamıyor; boşluktan sonraki ilk konum ayrıca bir sıçramadır.
2. PX4'ün `TargetEstimator`'ı konumu en sık 500 ms'de bir kaynaştırır ve her kaynaşmada konum farkının bir payını hıza
   ekler (aşağıda 2). Birkaç saniyede 1 m'lik bir kayma ve boşluk sonrası sıçramalar böylece 1 m/s'yi aşan sahte hızlara
   dönüşür (6 koşuda sürenin %2–29'u).
3. Görev, kişinin rotasını yalnız hız ≥ 1 m/s iken günceller; her güncellemede yörünge açısı hedefi "rota + 180°"ye
   kayar ve dron yeni "arka"ya doğru döner. Dron dönünce bakış yönü, dolayısıyla kayma da döner: **geri besleme**.
4. Koşudan koşuya fark büyük: 6 koşudan biri (191°) neredeyse hakem kadar sakin, diğerleri 503–672°. Döngü bir kez
   başlarsa kendini besliyor, başlamazsa sakin kalıyor. Bu yüzden sonuçlar aralıklarıyla veriliyor.
5. Hakemde konum gürültüsüz: sahte hız 0, rota 34 s "kuzey" kalıyor, tek dönüş PX4'ün başlangıçtaki "kuzey"
   varsayımından (mod açılınca dron kişinin batısından güneyine gidiyor, ≈ 194°; spec "PX4 stok Follow Target
   davranışı" 1).

## 2. PX4 kodundan: sahte hız nasıl doğuyor? (yalnız okundu)

1. **Konum en sık 500 ms'de bir kaynaşır** (`MINIMUM_TIME_BETWEEN_POS_FUSIONS_MS 500`, `measurement_can_be_fused`).
   Aradaki FOLLOW_TARGET'lar yalnız "bayat" sayacını sıfırlar. Simde 5.6 mesaj/s gidiyor, PX4 bunların en çok 2'sini kullanıyor.
2. **Her kaynaşmada hız, konum farkıyla birlikte değişir:** `vel += H_p / dt · (ölçülen − kestirilen konum)`,
   `acc += 2 K_p / dt² · (aynı fark)`, `dt` ≈ 0.5 s. Kazançlar `FLW_TGT_RS`'den gelir (`update_filter_gains`):
   `β = RS^(1/3)`, `G_p = 1 − β³ = 1 − RS`, `H_p = 1.5 (1 − β)² (1 + β)`, `K_p = 0.5 (1 − β)³`; RS önce 0.1–1.0'a
   kısılır.

   | `FLW_TGT_RS` | β | G_p (konum) | H_p | H_p / 0.5 s (hıza giden pay) | 2 K_p / (0.5 s)² |
   |---|---|---|---|---|---|
   | 0.1 (varsayılan, en tepkisel uç) | 0.464 | 0.90 | 0.63 | **1.26 /s** | 0.62 /s² |
   | 0.3 | 0.669 | 0.70 | 0.27 | 0.55 /s | 0.14 /s² |
   | 0.5 | 0.794 | 0.50 | 0.11 | 0.23 /s | 0.035 /s² |
   | 0.8 | 0.928 | 0.20 | 0.015 | 0.03 /s | 0.0015 /s² |
   | 1.0 | 1 | 0 | 0 | 0 (kestirici donar) | 0 |

   Yani RS 0.1'de konumdaki 0.5 m'lik bir sıçrama hıza tek kaynaşmada ≈ 0.63 m/s olarak eklenir (ve ivme terimiyle
   sonraki yarım saniyede biraz daha büyür). **Küçük RS = tepkisel, gürültüyü daha az bastırır** (parametre açıklaması:
   "lower values increase the responsiveness to changing position, but also ignore less noise"). 0.05 yazılsa da PX4
   0.1 gibi davranır; 9.8'deki eski aday bu yüzden geçersizdi.
3. **Rota yalnız iki hız birden ≥ 1 m/s iken güncellenir** (`FlightTaskAutoFollowTarget.cpp` `updateTargetOrientation`):
   kestiricinin süzülmemiş hızı (`vel_est`) ve görevin kendi ikinci derece süzgecinden geçen hız (doğal frekans 1 rad/s,
   sönüm 0.71). Sahte hız 1 m/s'yi kısa süre aşsa bile süzgeçli hız da aşmadıkça rota değişmez; aşınca rota sahte hızın
   yönüne döner, yörünge açısı hedefi "rota + 180°"ye kayar ve dron kişinin etrafında döner.
4. **Kestirici her mod seçiminde sıfırdan başlar** (`FlightTaskAutoFollowTarget()` kurucusunda `_target_estimator.Start()`),
   ilk FOLLOW_TARGET'ta hızı 0 kabul eder.
5. **`FLW_TGT_MAX_VEL`** yalnız yörünge açısının en büyük hızını sınırlar (`setMaxVel(MAX_VEL / FLW_TGT_DST)`; 8 m'de
   5 m/s → 0.625 rad/s, 3 m/s → 0.375 rad/s, 8 m/s → 1.0 rad/s). İvme (2 m/s² → 0.25 rad/s²) ve sarsıntı (4 m/s³) sınırı
   sabittir; 8 m/s'lik hıza 180°'lik bir dönüşte bile çoğu zaman ulaşılmaz. Sahte hızı değiştirmez, yalnız dronun ona ne
   kadar hızlı uyduğunu değiştirir.

## 3. Açık döngü: aynı konumlar, farklı `FLW_TGT_RS`

PX4'ün `TargetEstimator`'ı, görevin ikinci derece süzgeci ve rota kuralı Python'da satır satır yeniden yazıldı
(scratchpad, `kestirici_tekrar.py`; repoya girmedi). Doğrulama: `gorev8_takip_yuruyen`'in kayıtlı FOLLOW_TARGET'ları
RS 0.1 ile verilince PX4'ün ULog'daki `vel_est`'iyle **RMS fark 0.014 m/s, korelasyon 1.000**. Sonra aynı girdi farklı
RS ile tekrar oynatıldı. Bu açık döngüdür: gerçekte RS değişince dron başka yerde olur ve girdi (bakış yönüne bağlı
kayma) de değişir; yalnız süzgecin kendi etkisini gösterir.

| Aynı girdi | RS 0.1 | RS 0.3 | RS 0.5 | RS 0.8 |
|---|---|---|---|---|
| Kişi dururken sahte hız ort. (model koşusu `RS0.1_model_x3/kosu_3`) | 0.69 m/s | 0.39 m/s | 0.21 m/s | 0.05 m/s |
| … ≥ 1 m/s olduğu süre | %25 | **%0** | %0 | %0 |
| Kişi yürürken (≥ 1 m/s) PX4 rotasının hatası ort., gürültüsüz girdi (hakem `RS0.1_hakem_x3/kosu_1`) | 22° | 30° | 39° | 86° |
| … aynısı, model girdisi (`kosu_3`) | 54° | 45° | 67° | 72° |

Okuma: RS 0.3 aynı girdide sahte hızı yarıya indiriyor ve 1 m/s eşiğini hiç geçirmiyor; temiz girdide rotayı 8°
daha geç izliyor, gürültülü girdide ise rota hatası küçülüyor bile (gürültü daha az rota oynatıyor). RS 0.5'te
gecikme belirginleşiyor, 0.8'de PX4 köşelere yetişemiyor.

## 4. Kapalı döngü: her ayar 3 koşu

`toplu.py --senaryo takip_yuruyen --tekrar 3 -- --param AD=DEĞER` (`--los hakem` ile ayrıca). Model v0.2, CPU, 4
çekirdek; bütün gruplar aynı oturumda, aynı kodla (13.11, 02:11–03:30). Her hücre: **ortalama** (en az–en çok); "köşe"
satırları bu belge için koşu klasörlerinden hesaplandı (aşağıda), geri kalanı `ozet.json`'daki ölçütler. "RS 0.3 +
MAX_VEL 3" 9.8'in aday listesinde yoktu: ayrı ayrı sonuçlar bu birleşimi düşündürdüğü için, öneri ölçülmeden
yazılmasın diye eklendi (3 koşu).

| Ölçüt | RS 0.1 (varsayılan) | RS 0.3 | RS 0.5 | RS 0.8 | MAX_VEL 3 | MAX_VEL 8 | RS 0.3 + MAX_VEL 3 | hakem RS 0.1 | hakem RS 0.3 |
|---|---|---|---|---|---|---|---|---|---|
| Takip başı: dronun duran kişi etrafında döndüğü açı [°] | **482** (191–652) | **187** (183–189) | **207** (202–209) | **194** (193–197) | **445** (380–545) | **190** (184–196) | **194** (183–208) | **194** (193–195) | **195** (193–197) |
| Takip başı: PX4'ün sahte hızı, ort. [m/s] | **0.53** (0.24–0.71) | **0.15** (0.14–0.16) | **0.12** (0.10–0.14) | **0.03** (0.01–0.04) | **0.51** (0.26–0.79) | **0.21** (0.19–0.23) | **0.13** (0.12–0.14) | **0.00** (0.00–0.00) | **0.00** (0.00–0.00) |
| Takip başı: PX4'ün sahte hızı, p95 [m/s] | **1.23** (0.87–1.44) | **0.53** (0.48–0.62) | **0.32** (0.28–0.39) | **0.07** (0.04–0.09) | **1.39** (0.94–1.82) | **0.63** (0.51–0.82) | **0.42** (0.41–0.45) | **0.00** (0.00–0.00) | **0.00** (0.00–0.00) |
| Takip başı: sahte hız ≥ 1 m/s [%] | **17** (2–26) | **1** (0–1) | **0** (0–0) | **0** (0–0) | **14** (4–26) | **2** (2–4) | **1** (0–2) | **0** (0–0) | **0** (0–0) |
| Takip başı: PX4 rotası değişti [kez] | **15** (2–23) | **1** (1–2) | **0** (0–0) | **0** (0–0) | **12** (3–24) | **2** (1–2) | **1** (0–2) | **0** (0–0) | **0** (0–0) |
| Takip başı: gönderilen konumun titreşimi (std) [m] | **0.64** (0.51–0.74) | **0.48** (0.45–0.49) | **0.57** (0.54–0.60) | **0.49** (0.22–0.63) | **0.65** (0.61–0.69) | **0.50** (0.47–0.55) | **0.49** (0.45–0.55) | **0.00** (0.00–0.00) | **0.00** (0.00–0.00) |
| Yürüyüşün ilk 10 s'si: yörünge dönüşü [°] | **148** (90–222) | **84** (81–87) | **96** (94–97) | **47** (46–48) | **124** (87–172) | **95** (89–100) | **87** (80–92) | **97** (97–97) | **97** (97–97) |
| PX4 rotayı kuzey varsaydı [s] | **1.3** (0.8–2.0) | **1.6** (0.8–2.4) | **36.9** (36.0–37.6) | **42.0** (41.6–42.8) | **0.9** (0.8–1.2) | **1.7** (0.8–2.4) | **12.5** (1.2–35.2) | **34.1** (34.0–34.4) | **34.5** (34.4–34.8) |
| PX4 rota hatası ort. [°] (kişi ≥ 1 m/s) | **39** (29–56) | **34** (33–35) | **83** (51–100) | **120** (119–121) | **29** (24–32) | **34** (24–42) | **34** (29–38) | **23** (22–24) | **29** (28–29) |
| Köşe: PX4 rotasının yürüyüş başına yetişmesi (30° içine) [s] | **1.5** (1.5–1.6) | **2.4** (2.1–2.7) | **3.7** (3.5–3.9) | **9.5** (9.1–10.3) | **1.5** (1.0–1.9) | **1.7** (1.5–1.9) | **2.2** (1.8–2.9) | **1.6** (1.5–1.7) | **1.9** (1.8–2.0) |
| Köşe: kuzeye koşuya yetişmesi [s] | **1.4** (1.1–2.0) | **1.9** (1.8–2.1) | **2.3** (2.3–2.3) | – | **1.6** (1.5–1.8) | **2.7** (1.4–3.9) | **2.0** (1.8–2.1) | **1.2** (1.2–1.3) | **1.7** (1.6–1.9) |
| Köşe: batıya dönüşe yetişmesi [s] | **1.0** (1.0–1.0) | **1.7** (1.6–1.8) | – | – | **1.1** (1.0–1.3) | **1.7** (0.9–2.6) | **2.9** (2.0–3.9) | **1.7** (1.2–1.9) | **1.6** (1.5–1.7) |
| Arkada kalma hatası ort. [°] | **78** (44–139) | **53** (52–55) | **67** (57–72) | **67** (63–74) | **69** (64–72) | **43** (35–49) | **57** (50–67) | **49** (48–50) | **51** (50–52) |
| Arkada kalma hatası p95 [°] | **125** (98–178) | **142** (138–144) | **116** (111–121) | **100** (86–126) | **138** (123–148) | **85** (76–100) | **130** (125–139) | **103** (101–104) | **114** (110–120) |
| Dron yanında/önünde (> 90°) [s] | **7.9** (2.2–19.3) | **4.0** (3.5–4.3) | **4.2** (3.2–4.8) | **2.3** (0.7–5.6) | **4.6** (3.4–5.5) | **0.4** (0.0–1.2) | **2.6** (2.2–3.3) | **1.5** (1.4–1.6) | **2.0** (1.8–2.1) |
| Köşe (batı): arkada kalma hatası en çok [°] | **138** (114–179) | **154** (149–157) | **130** (129–132) | **111** (98–133) | **151** (143–159) | **92** (80–115) | **140** (137–144) | **126** (124–128) | **135** (131–140) |
| PX4 kestirim hatası ort. [m] | **3.46** (0.55–7.10) | **2.21** (0.67–3.16) | **5.39** (3.96–6.18) | **7.51** (6.08–8.32) | **0.69** (0.68–0.70) | **2.53** (0.55–5.88) | **2.23** (0.76–4.10) | **0.27** (0.25–0.30) | **0.53** (0.51–0.54) |
| En az yatay mesafe [m] | **1.95** (1.68–2.46) | **1.16** (0.66–1.56) | **4.42** (4.02–4.62) | **6.12** (5.60–6.94) | **2.49** (2.02–2.98) | **3.06** (0.02–5.12) | **2.61** (1.75–3.12) | **3.22** (2.93–3.46) | **2.19** (2.03–2.39) |
| 3 m altı [s] | **1.0** (0.7–1.2) | **1.3** (1.1–1.4) | **0.0** (0.0–0.0) | **0.0** (0.0–0.0) | **0.7** (0.2–1.2) | **0.4** (0.0–1.1) | **0.6** (0.0–1.4) | **0.1** (0.0–0.3) | **0.9** (0.8–1.0) |
| Kameranın yakın sınırı altı [s] | **1.9** (1.3–2.7) | **1.7** (1.6–1.8) | **0.0** (0.0–0.0) | **0.0** (0.0–0.0) | **1.6** (1.3–1.9) | **0.5** (0.0–1.6) | **1.7** (1.4–2.2) | **1.0** (0.8–1.1) | **1.5** (1.4–1.5) |
| Kişinin tamamı kadrajda [%] | **55** (38–86) | **69** (57–88) | **52** (48–58) | **53** (52–54) | **90** (89–92) | **66** (52–89) | **76** (60–91) | **91** (90–92) | **87** (86–87) |
| Kilit kaybı | **6** (3–11) | **2** (1–2) | **2** (1–3) | **2** (2–2) | **3** (2–3) | **4** (2–6) | **4** (2–6) | **3** (1–4) | **3** (2–3) |
| PX4 kestirimi bayat [s] | **3.9** (0.0–9.0) | **5.3** (0.0–8.0) | **10.7** (7.6–12.4) | **12.1** (11.2–13.0) | **0.0** (0.0–0.0) | **3.0** (0.0–8.2) | **2.9** (0.0–7.8) | **0.0** (0.0–0.0) | **0.0** (0.0–0.0) |
| Yatay mesafe ort. [m] | **8.39** (7.77–9.30) | **8.04** (7.47–8.37) | **7.55** (7.43–7.69) | **9.28** (8.75–9.56) | **7.57** (7.50–7.70) | **8.47** (7.93–8.76) | **7.59** (7.43–7.83) | **7.60** (7.49–7.68) | **7.12** (7.05–7.17) |
| RTF | **0.82** (0.74–0.90) | **0.84** (0.82–0.88) | **0.82** (0.82–0.83) | **0.82** (0.82–0.83) | **0.83** (0.82–0.84) | **0.83** (0.83–0.83) | **0.79** (0.78–0.80) | **0.86** (0.82–0.92) | **0.82** (0.79–0.85) |

"Köşe" ölçütleri (`dogru_cevap.csv` + ULog `follow_target_status`): kişinin gerçek rotası yeni yöne (±20°) geldiği
andan PX4'ün varsaydığı rotanın o yönün 30° içine girmesine kadar geçen süre (yürüyüş başı: doğu, 60.3 s; kuzeye koşu
73.0 s; batıya dönüş 77.6 s; bu anlar ilk yazımda yanlışlıkla ≈ 71.6 / ≈ 75 s yazılmıştı, gecikmeler betiğin hakemden
bulduğu doğru anlarla hesaplanmıştı: 9. grupta `olcum.py`'ye taşınan kodla aynı sayılar çıktı); "yetişmedi": koşu
bitene kadar girmedi. 9. grupta bu ölçütler `olcum.py`'ye taşındı (`kose_*`, karar 4, 13.11). "Köşe (batı) en çok": batıya dönüşten sonraki 6
s'de arkada kalma açısı hatasının en büyüğü.

**Okuma (salınım ↔ tepkisellik, ikisi birlikte):**

- **RS 0.3, kullanıcının sorununu gideriyor.** Duran kişide dönüş 183–189° (hakemde 193–197°; kalan tek dönüş PX4'ün
  "kuzey" varsayımı), sahte hız ort. 0.15 m/s, ≥ 1 m/s yalnız %0–1, rota 1–2 kez değişti (varsayılanda 2–23 kez).
  Gönderilen konumun titreşimi de azaldı (0.48 / 0.64 m): dron dönmeyince bakış yönü ve kayma sabit kalıyor; geri
  besleme kırılıyor. Yürüyüşte PX4'ün rota hatası değişmedi (34° / 39°), kişinin tamamı kadrajda biraz daha çok (%69 /
  %55), kilit kaybı daha az (2 / 6).
  **Bedeli köşelerde:** PX4'ün rotası her köşeye 0.5–0.9 s daha geç yetişiyor (yürüyüş başı 2.4 / 1.5 s, kuzey 1.9 /
  1.4 s, batı 1.7 / 1.0 s); batı dönüşünde arkada kalma hatası en çok 154° / 138°, p95 142° / 125°; en az mesafe 0.66–1.56
  m (varsayılanın bu 3 koşusunda 1.68–2.46 m, 6 koşusunda 0.51–5.60 m), 3 m altı 1.3 / 1.0 s. Mükemmel algılayıcıyla aynı
  karşılaştırma ayarın gürültüden bağımsız bedelini verir: PX4 rota hatası 23° → 29°, kestirim hatası 0.27 → 0.53 m,
  en az mesafe 3.2 → 2.2 m (3 m altı 0.1 → 0.9 s), kişinin tamamı kadrajda %91 → %87.
- **RS 0.5 ve 0.8: salınım tamamen gidiyor, takip bozuluyor.** Rota takip başında hiç değişmedi (PX4 rotayı kişi
  yürüyene kadar 36–43 s "kuzey" sandı, hakemdeki gibi). Ama yürüyüşte PX4 geride: rota hatası 83° / 120°, kestirim
  hatası 5.4 / 7.5 m, kestirim 11–12 s bayat (kişi kadrajdan çıkıyor, FOLLOW_TARGET kesiliyor), kişinin tamamı kadrajda
  %52–53; PX4'ün rotası batı dönüşüne RS 0.5'te de, 0.8'de de hiç yetişmedi (0.8'de kuzey koşusuna da). Dron geride kaldığı için en az mesafe
  4–7 m (yakın geçiş yok): "güvenli" görünmesi takip etmemesindendir.
- **MAX_VEL 3: sahte hızı değiştirmiyor, kamerayı rahatlatıyor.** Kestiriciye dokunmadığı için salınım varsayılan
  kadar (445°, ≥ 1 m/s %14). Dron daha yavaş döndüğü için kişi kadrajda kalıyor: kişinin tamamı kadrajda %89–92 (en iyi),
  PX4 kestirim hatası 0.68–0.70 m, kestirim hiç bayat değil, rota hatası 29°. Bedeli: dron "arka"ya geç varıyor
  (arkada kalma ort. 69°, p95 138°).
- **MAX_VEL 8:** üç koşuda da duran kişide sakin (184–196°) ve arkada kalma en iyi (ort. 43°, > 90° 0–1.2 s). Ama bir
  koşuda dron kişinin tam üstünden geçti (en az 0.02 m) ve o koşuda kestirim 5.9 m saptı. Sahte hızı azaltan ayarın
  kendisi değil (MAX_VEL kestiriciye girmez), kapalı döngü: dron ilk dönüşünü hızlı bitirip durunca bakış yönü ve kayma
  da duruyor. 3 koşu bunu kesinleştirmeye yetmez; yakın geçiş riski nedeniyle önerilmez.
- **RS 0.3 + MAX_VEL 3 (ek):** duran kişide RS 0.3 kadar sakin (183–208°, sahte hız 0.13 m/s), yakın geçiş RS 0.3'ten
  iyi (en az 1.75–3.12 m, 3 m altı 0.56 s), dron yanında/önünde daha az (2.6 / 4.0 s); ama kadraj ve kestirim koşudan
  koşuya çok değişti (kişinin tamamı kadrajda %60–91, bir koşuda kestirim 7.8 s bayat ve 4.1 m hatalı). MAX_VEL 3'ün
  tek başına verdiği istikrarlı kadraj (%89–92) birleşimde görülmedi.

## 5. Öneri (karar kullanıcının; m06'nın varsayılanları değişmedi)

- **Stok Follow Me kullanılacaksa `FLW_TGT_RS 0.3`.** Kullanıcının sorduğu salınımı (duran kişinin etrafında
  dönme) 6 koşunun 6'sında (RS 0.3'ün 3'ü + birleşimin 3'ü) gideriyor, yürüyüşte rota hatasını büyütmüyor. Bedeli
  köşelerde 0.5–0.9 s geç dönüş ve daha yakın geçiş (en az 0.66 m; mükemmel algılayıcıyla bile 3.2 m → 2.2 m): 3 m
  uyarısı ve kameranın yakın sınırı (≈ 4 m) içinde kalma (1.6–1.8 s) sürüyor. Gerçek uçuşta bu bir ayar önerisidir,
  güvenlik çözümü değildir.
- `FLW_TGT_MAX_VEL` için öneri yok: 3 koşu yetmedi (MAX_VEL 3 kadrajı iyileştirdi ama birleşimde bu tutmadı; MAX_VEL 8
  bir koşuda kişinin üstünden geçti). İsteniyorsa 3'ten fazla koşuyla ayrı bir karşılaştırma gerekir.
- `FLW_TGT_RS` ≥ 0.5 önerilmez (PX4 köşelere yetişemiyor, kişi kadrajdan çıkıyor).
- Asıl çözüm Pi tarafındadır: m11'in konum süzgeci ve PX4'e süzülmüş hız gönderilmesi (aşağıda 6), ya da m15'in kendi
  modu (stok modun "kuzey" varsayımı ve 1 m/s'lik rota kuralı onun elinde). RS 0.3 o zamana kadar yalnız duran kişideki
  salınımı giderir; köşe ve yakın geçiş sorunları sürer.
- m06'nın parametre dosyaları değişmedi; kullanıcı RS 0.3'ü seçerse tek satırlık iş: `tez/sim/parametreler/gercek_dron.params`
  ya da senaryonun `takip.px4_parametreleri`'ne `FLW_TGT_RS 0.3` (kaynağı bu belge). Gerçek dronun 22.08 parametrelerinde
  RS 0.1'dir.

## 6. m11 (Ortatepe) ve m15 (Kurt) için ölçülen sayılar

Hepsi `takip_yuruyen` (8 m / 45°, v0.2 CPU'da, stok Follow Me), "takip başı" = dron Follow Target'ta, kişi duruyor
(≈ 35 s); varsayılan `FLW_TGT_RS 0.1` için 6 koşu, diğerleri 3'er koşu (ortalama, en az–en çok).

**Konum (m11'in girdisi: model kutusunun alt ortasından düz zemin hesabı, `konumlama.py`):**

- Gönderim sıklığı 5.6 /s (4.3–6.7; hakemde 9.9 /s). PX4 bunların en çok 2'sini/s kaynaştırır (500 ms kuralı).
- Model kişiyi takip başında sık kaçırıyor: 0.5 s'den uzun 7–12 boşluk, en uzunu 1.8–3.4 s, sürenin %27–47'si. Boşluktan
  sonraki ilk konum PX4'te bir sıçrama olarak kaynaşır.
- Kişi dururken gönderilen konumun titreşimi (hatanın std'si) **0.69 m** (0.51–0.90); ardışık iki konumun farkı yalnız
  **0.07 m** (0.04–0.09). Sorun kareden kareye beyaz gürültü değil, **yavaş, bakış yönüne bağlı kayma**: hata ortalamada
  **0.48 m drona doğru** (+0.34…+0.59) ve dron döndükçe o da dönüyor (7. gruptaki zaman serisinde 0.5–1.5 m).
- Bu yüzden m11'in süzgecinde iki ayrı iş var: kareden kareye titreşim (≈ 0.1 m) kolay; bakış yönüne bağlı kayma
  (0.5–1.5 m, saniyeler içinde değişir) alçak geçiren bir süzgeçle tam gitmez. Kişinin durduğunu anlayan bir kural (hız
  ölü bölgesi, "duruyor" durumu) ya da kutunun alt kenarı yerine kişinin gövdesine dayanan bir konum gerekebilir.

**Stok Follow Me'nin buna tepkisi (m15'in karşılaştırma tabanı):**

- Sahte hız (kişi dururken `vel_est`): ort. **0.57 m/s** (0.24–0.79), p95 1.50 m/s, en çok 2.26 m/s; zamanın **%17**'sinde
  (%2–29) ≥ 1 m/s; PX4'ün rotası takip başında **14.5 kez** (2–23) değişti; dron duran kişinin etrafında **530°** (191–672)
  döndü. Hakemde: 0, 0, 194°.
- Hangi ayar ne kadar yardım etti (kapalı döngü, 3'er koşu): RS 0.3 sahte hızı 0.15 m/s'ye, ≥ 1 m/s'yi %1'e, rota
  değişimini ortalama 1.3 kereye, dönüşü 187°'ye indirdi; bedeli köşelerde 0.5–0.9 s gecikme ve daha yakın geçiş (en az 0.66–1.56 m).
  RS 0.5 / 0.8 sahte hızı 0.12 / 0.03 m/s'ye indirdi ama PX4 yürüyüşte 83° / 120° rota hatasıyla geride kaldı. MAX_VEL
  sahte hızı değiştirmedi (açık döngüde etkisi yok); kapalı döngüde MAX_VEL 3 kadrajı %90'a çıkardı, MAX_VEL 8 bir
  koşuda kişinin üstünden geçti. Tablo: bölüm 4.

**Pi tarafında hız kestirimi gönderilirse (PX4 kodundan beklenti, deneme yapılmadı):**

- PX4 v1.17.0 `est_capabilities`'i okumaz (`mavlink_receiver.cpp` `handle_message_follow_target` yalnız `lat`, `lon`,
  `alt`, `vel[3]`'ü `follow_target`'a yazar; `TargetEstimator` de bakmaz). "Hız bilinmiyor" için tek yol NaN'dır; 0
  gönderilirse PX4 kişinin durduğunu sanar (m06 NaN gönderir).
- Hız sonlu gelirse kestirici onu en sık 100 ms'de bir (değişmemişse 200 ms'de bir) kaynaştırır:
  `vel += G_v · (gelen hız − kestirilen hız)`, `G_v = 1 − (0.9 · RS^(1/3))²`: RS 0.1'de **0.83**, RS 0.3'te 0.64. Konum
  kaynaşmasının eklediği sahte hız aynı mesajda ya da 100–200 ms içinde %17'sine, iki hız kaynaşmasında %3'üne iner.
  Görevin 1 rad/s'lik süzgeci bu kadar kısa tepelere yetişmez, rota güncellenmez: **duran kişide salınım RS'den bağımsız
  olarak kalkmalı.**
- Şartlar: (1) gönderilen hız iyi süzülmüş olmalı: titreşen konumların ardışık farkı gibi gürültülü bir hız %83
  ağırlıkla doğrudan alınır ve durumu kötüleştirir; (2) kişi dururken ≈ 0, yürürken gerçek hız: yürürken 0 gönderen bir
  eşik PX4'ü geride bırakır; (3) NED, m/s; (4) köşelerdeki gecikme bu kez Pi'nin süzgecine geçer, RS yalnız konum
  tarafını belirler. Sim bunu ölçmeye hazır: hız alanı `px4_baglanti.Vehicle.send_follow_target`'ta; m11'in süzgeci takılınca
  aynı senaryo ve aynı ölçütlerle (`px4_kestirim_hizi_baslangic_*`, `baslangic_yorunge_donusu_deg`) denenir.

**m15 kendi modunu yazarken (gözlem, tasarım kararı değil):** stok modun salınımı iki kuraldan geliyor: (1) kişinin
rotası 1 m/s'lik bir eşikle, süzülmemiş ve süzülmüş iki hızın ikisi de geçince güncelleniyor; (2) mod açılınca rota
"kuzey" kabul ediliyor. Kişi dururken dronun yerini koruyan bir davranış ve kişinin hızına bir ölü bölge, ikisini
birlikte giderir. m06 aynı senaryo, aynı ölçütler ve aynı videoyla karşılaştırma imkânı verir (`--takip tez_los
--mod-adi "<ad>"`, 10. grup).

## 7. Kalan sim-gerçek farkları

- **Konum hatasının kaynağı simde yalnız model kutusu:** gz_bridge'in GPS gürültüsü küçük, rüzgâr yok, EKF yaw hatası
  7. gruptan beri ≈ 1°. Gerçekte M8N GPS (metre mertebesi, yavaş kayan), pusula ve gövde titreşimi eklenir; bakış
  yönüne bağlı kayma ve sahte hız büyüyebilir. `--los hakem` alt sınırdır (gürültüsüz konum).
- **Kişi kayıtlı bir yolu izler** (dur 60 s → doğu → 3 s dur → kuzeye koş → batı): köşe sonuçları bu yola bağlıdır.
  Gerçek bir insan dronun yaklaşmasına tepki verebilir, köşe sayısı ve keskinliği farklı olur.
- **Gölge ve görünüş:** Gazebo güneşinin gölgesi kutunun alt kenarını ve kaymayı etkiliyor olabilir (ölçülmedi);
  gerçek güneşin yönü, kişinin kıyafeti ve zemin farklı.
- **Model laptop CPU'sunda** (v0.2, bugün kare başına ort. 100 ms; 12.11'de 85 ms); Hailo'daki hız ve kaçırma başka
  olur (m08). Kaçırma ve gecikme sahte hızın bir parçası (boşluk sonrası sıçramalar).
- **RTF 0.79–0.92** (bütün gruplarda benzer, aşağıda 8): sim zamanında model biraz hızlı görünür; gerçek zamanda kare
  hızı ve gecikme biraz daha kötü olur.
- **3 koşu az:** varsayılan ayarın 6 koşusunda duran kişi etrafındaki dönüş 191–672° arasında değişti. RS 0.3'ün etkisi
  6/6 koşuda tutarlı; MAX_VEL için 3 koşu karar vermeye yetmedi.

## 8. Karşılaşılan sorunlar

- **9.8'deki 0.05 adayı geçersizdi:** PX4 `FLW_TGT_RS`'yi 0.1–1.0'a kısar (`update_filter_gains`); 0.05 ile 0.1 aynı
  koşu olurdu. Adaylar 0.1, 0.3, 0.5, 0.8 olarak düzeltildi (`tasks.md` 9.8).
- **Bugünkü RTF düşüktü** (koşularda 0.74–0.92, grup ortalamaları 0.79–0.86; 7. grupta 0.95–0.98): model kare başına
  ort. 100 ms sürdü (7. grupta 82–86 ms). Video kaydının payı ≈ 0.05 (8. grup belgesi, dönüşümlü ölçüm); bütün model
  gruplarında video açıktı, yani gruplar arasında fark yaratmaz. Gruplar aynı oturumda, aynı kodla koşuldu; 7. grupla
  sayılar birebir karşılaştırılmamalı.
- **Benim analiz işlerim iki koşunun RTF'ini düşürdü** (`gorev9on_RS0.1_model_x3` koşu 1: 0.74, koşu 2: 0.82; boştayken
  0.90): koşu sürerken Python ile ULog okumak bile simi yavaşlatıyor. Sonraki gruplarda koşu sırasında yalnız metin
  yazıldı. Bu iki koşu tabloda bırakıldı: sim zamanında ölçülen her şey (mesafe, açı, gecikme) RTF'den bağımsızdır;
  yalnız model sim saatine göre biraz hızlı görünür.
- **Köşe ölçütleri repoda değil:** "PX4 rotasının köşeye yetişmesi" ve "batı dönüşünde en çok arkada kalma" bu belge için
  betikle koşu klasörlerinden hesaplandı (`gorev9on_betikler/is_b_analiz.py`; senaryoya özgü köşe anları). **9. grupta
  `olcum.py`'ye taşındı** (kullanıcı kararı 13.11; köşeler hakemden bulunur, `kose_*`, testli; `gorev-grubu-09.md`).

## 9. Görseller (repo dışı)

`~/Desktop/Follow/3_m06_Simulasyon/Deneme/`:

| Dosya | Ne |
|---|---|
| `gorev9on_sahte_hiz.png` | Salınımın mekanizması, 4 panel: (1) kişi dururken dronun kişi etrafındaki açısı (model / hakem), (2) gönderilen konumun hatası (drona doğru / yana bileşen; hakemde 0), (3) PX4'ün `vel_est`'i ve 1 m/s eşiği, rotanın değiştiği anlar (mor), (4) aynı konumlar farklı `FLW_TGT_RS` ile (açık döngü). Koşular `gorev9on_RS0.1_model_x3/kosu_3` ve `gorev9on_RS0.1_hakem_x3/kosu_1` |
| `gorev9on_followme_RS_karsilastirma.png` | 9 grup × 3 koşu, 22 ölçüt (nokta: koşu, çubuk: ortalama); bölüm 4'teki tablonun görseli |
| `gorev9on_RS_0.1_kosu.mp4` | Varsayılan ayarla bir koşunun videosu (`gorev9on_RS0.1_model_x3/kosu_3`: takip başında 652° dönüş, sahte hız ≥ 1 m/s %26) |
| `gorev9on_RS_0.3_kosu.mp4` | `FLW_TGT_RS 0.3` ile bir koşunun videosu (`gorev9on_RS0.3_model_x3/kosu_2`: 183°, %0); ikisi yan yana izlenir |
| `gorev9on_betikler/` | Bu belgenin şekillerini ve köşe ölçütlerini üreten betikler (repoya girmedi): `kestirici_tekrar.py` (PX4 `TargetEstimator` + görev süzgecinin Python kopyası), `is_b_analiz.py` (koşu başına ölçütler ve köşe gecikmesi), `is_b_sekiller.py` (tablo ve karşılaştırma şekli), `sahte_hiz_sekli.py`, `tekrar_yuruyus.py` (açık döngü rota hatası) |

Koşu klasörleri (`tez/sim/sonuclar/`, git dışında): `gorev9on_RS0.1_model_x3`, `gorev8_rtf_videosuz_x3` (aynı ayar,
videosuz), `gorev9on_RS0.3_model_x3`, `gorev9on_RS0.5_model_x3`, `gorev9on_RS0.8_model_x3`, `gorev9on_MAXVEL3_model_x3`,
`gorev9on_MAXVEL8_model_x3`, `gorev9on_RS0.3_MAXVEL3_model_x3`, `gorev9on_RS0.1_hakem_x3`, `gorev9on_RS0.3_hakem_x3`;
her birinde `toplu.html` (her koşunun `rapor.html` ve `kosu.mp4` bağlantısıyla).

## Kendin dene

**Başlamadan:** Terminal için **Ctrl+Alt+T**. Satırları **tek tek** kopyala, **Ctrl+Shift+V** ile yapıştır, **Enter**.
Her satır tek başına çalışır (değişken yok).

### 1. Salınımın sebebi tek resimde

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9on_sahte_hiz.png
```

Yukarıdan aşağı:

1. Kişi duruyor ama dron onun etrafında dönüyor (turuncu: model kutusuyla; gri: mükemmel algılayıcıyla, yalnız bir kez
   döner).
2. Modelin kutusundan bulunan konum (PX4'e giden FOLLOW_TARGET) kişinin gerçek yerinden kayık: koyu mavi noktalar
   "drona doğru" kayma. Kareden kareye az oynar, ama dron döndükçe kayma da döner.
3. PX4 bu kaymayı "kişi hareket ediyor" diye hıza çeviriyor (mavi çizgi). Kırmızı kesikli çizgi 1 m/s: PX4 kişinin
   yönünü yalnız bu hızın üstünde günceller. Mor dikey çizgiler PX4'ün yönü değiştirdiği anlar; her biri dronu yeni bir
   "arka"ya gönderir. Gri çizgi (mükemmel algılayıcı) hep 0.
4. Aynı konumları PX4'ün kestiricisine farklı `FLW_TGT_RS` ile verince (bilgisayarda yeniden hesaplandı): değer
   büyüdükçe sahte hız küçülür.

### 2. Ayarların karşılaştırması

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9on_followme_RS_karsilastirma.png
```

Her küçük grafik bir ölçüt; her sütun bir ayar; noktalar 3 koşu, çubuk ortalama. Soldan: RS 0.1 (varsayılan), 0.3,
0.5, 0.8, MV3 ve MV8 (`FLW_TGT_MAX_VEL` 3 ve 8), RS 0.3 + MV3 (ek birleşim), sonra mükemmel algılayıcıyla (hakem) RS
0.1 ve RS 0.3. İlk iki sıra kişi dururken olanlar (salınım; küçük daha iyi), sonraki üç sıra köşeler ve yürüyüş
(tepkiselliğin bedeli), son sıralar yakınlık ve kadraj. Kırmızı "yetişmedi": PX4'ün rotası o köşeye hiç yetişmedi.

### 3. Varsayılan ile önerilen ayarı yan yana izle

İki VLC penceresi açılır (ikisini ekranın iki yarısına sürükle):

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9on_RS_0.1_kosu.mp4 2>/dev/null &
```

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9on_RS_0.3_kosu.mp4 2>/dev/null &
```

Videonun ilk yarısında kişi duruyor (takip başı). Sağdaki haritada mor oka (PX4'ün sandığı yön) ve alttaki "PX4:
hedefin hızı … m/s" yazısına bak: varsayılanda hız sık sık 1 m/s'yi geçer, ok döner, dron kişinin etrafında döner;
önerilen ayarda ok sakin kalır. Sonra köşelere (kişi doğuya yürüyüp durur, kuzeye koşar, batıya döner) bak: önerilen
ayarda mor ok yeni yöne biraz daha geç döner (bedeli).

### 4. Toplu sayfalar (her ayarın 3 koşusu, her koşunun raporu ve videosu)

```bash
firefox ~/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev9on_RS0.1_model_x3/toplu.html
```

```bash
firefox ~/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev9on_RS0.3_model_x3/toplu.html
```

"Takip başı: hedef dururken konum titreşimi ve PX4'ün sahte hızı" satırları yeni ölçütlerdir (her koşunun
`rapor.html`'inde de ayrı bir tablo).

### 5. Kendin koştur (pencere yok, ~8 dakika)

Önce açık bir sim olmadığından emin ol (iki satır da bir şey yazmamalı):

```bash
pgrep -x px4
```

```bash
pgrep -f "^gz sim"
```

Bir ayarı 3 kez koşmak (ör. RS 0.5):

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/toplu.py --senaryo takip_yuruyen --tekrar 3 -- --param FLW_TGT_RS=0.5
```

Sonuç klasörü en son satırda yazar; içindeki `toplu.html`'i Firefox'ta aç. Mükemmel algılayıcıyla aynısı: komutun
sonuna ` --los hakem` ekle.
