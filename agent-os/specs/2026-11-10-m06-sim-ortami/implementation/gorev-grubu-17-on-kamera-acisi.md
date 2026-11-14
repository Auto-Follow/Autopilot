# Görev Grubu 17 (öne alındı) — Modelle kamera eğimi (30–45°) × yükseklik × mesafe taraması

- Dal `ozellik/m06-sim-ortami` · taban commit `b5ee6160fe` + çalışma ağacı · `tasks.md` Görev Grubu 17 (genişletildi ve
  öne alındı)
- Kullanıcının isteği: "Önceki senaryolarda 30 dereceden 45 dereceye kadar olan açılarda farklı mesafe uzaklıklarında
  birçok simülasyon koşturup denemeler yapmıştım. Şimdi bu modelle birlikte kameranın 30–45 derece ve farklı mesafe
  uzaklıkları için denemeler yapıp hangi seçeneklerin benim için daha iyi olacağına karar ver."
- Ek istekler (14.11): düşük yükseklik bandı 4–7 m (30° / 4 m / 8 m dahil); modelin hangi koşullarda iyi algıladığı.
- Durum: **uygulandı, test edildi, koşuldu**; commit'lenmedi (commit'i kullanıcı atar; iş A ayrı commit, bölüm 13).
  Bölüm 1–3 koşulardan önce yazıldı (13.11.2026 13:26), sonuçlar koşulardan sonra eklendi.
- 14.11 ekleri: İş 1 (canlı hakem akışı düzeltmesi, ayrı commit, bölüm 16), İş 2 (37.5° ve genişletilmiş tarama, son
  karar ve gerçek uçuş önerisi, bölüm 17–19), İş 3 (seçilen ayar simin varsayılanı, bölüm 20), İş 4 (alçak + uzak
  takip denemesi, bölüm 21). 17.1, 17.5 ve 21.1'in tasarımları koşulardan önce yazıldı.

## Kısaca

- **Ne yapıldı:** kamera eğimi bir senaryo ayarı oldu (`kamera.egim_deg` / `--kamera-egim`; Gazebo modeli, LOS, konum,
  yakın sınır, video ve hakem aynı eğimle; varsayılan 13.11'de 45° kaldı, 14.11'de 35° oldu: bölüm 20). `takip_yuruyen` yolunda stok Follow Me ve v0.2
  (CPU) ile **81 bileşim** (30/35/40/45° × 4–15 m × 4 mesafe kuralı, 1'er koşu) ve **8 bileşim × 3 koşu** (videolu),
  ayrıca en iyi adaylar ve 45° 10/10 için mükemmel algılayıcı ve kıvrımlı yol 3'er koşu: **129** tarama
  koşusu, karar kuralı koşulardan önce yazıldı.
- **Sonuç:** 12 m ve üstünde model kişiyi bulamıyor (15 m'de %0, 12 m'de ort. %9); 4–7 m'de buluyor (%70–88) ama köşede
  dron kişinin üstüne geliyor. Kapıyı (köşede ≥ 3 m, kişi sonuna kadar izlendi) 3 koşunun 3'ünde geçenler: 35° 7/10,
  30° 6/10.4, 35° 8/11.4, 40° 12/11.4; **hiçbir 45° ayarı geçmedi** (8/8: 7 koşuda 1 izlendi, 10/10: 8 koşuda 7).
- **Neden:** köşede stok Follow Me dronu ≈ **6.2 m** yaklaştırıyor ve bu **mesafeyle ölçeklenmiyor**; kişi, bu yaklaşma
  kameranın yakın sınırına kadarki payı (≈ 0.52 × geride durma) aşınca kadrajın altından / yanından kaçıyor. 30–40°'de
  9 m ve üstünde geride duran 32 koşunun hepsi kişiyi köşeden sonra da izledi.
- **Kullanıcının 30° sorusu:** evet, düşük açı "yaklaşınca kaçırma"yı azaltıyor; ama mekanizma açı değil, aynı
  yükseklikte daha uzakta durabilmek (aynı mesafede pay eğimden bağımsız). Bedeli ufkun yakınlığı, konumun zemin ve GPS
  yüksekliğine duyarlılığı, başlara yakınlık. Piksel boyu kaybı belirlemiyor.
- **13.11'deki önerim (14.11'de bölüm 18'in son kararı yerini aldı):** kamera **35°**, **8 m yükseklik / 11.4 m geride** (geride durma ≈ 1.43 × yükseklik): **iki yolda da 3/3 geçen tek ayar** (köşede en az
  5.2–5.5 m, kıvrımlı yolun 164° dönüşünde 6.0–8.1 m), model %73–77, PX4'ün Follow Me alt sınırında (8 m). Kuralın birincisi aynı montajda 7 m / 10 m (köşede 3.7–4.2
  m, 7 m; kıvrımlı yolda 1/3, bir kaybı belirsiz). İkinci seçenek **30° · 6 m / 10.4 m** (model %83 ama 6 m ve ufuk payı 9.9°). 45°'de kalınacaksa **10 m / 10 m**.
  Bedeli: yeni montaj parçası, konum 1.43 kat duyarlı, ufuk payı 14.9°, dron 11.4 m geride. Karar kullanıcının.
- **Model hangi koşulda iyi buluyor** (133 koşu, 103 897 kişi-kare, lojistik model; ilişki, nedensellik değil):
  belirleyen **piksel boyu**: kişi 150–180 px'te %61, 120–150 px'te %25, 120 px'in altında %3 (640 girişte ≈ 33 px'ten
  küçük). Yandan görünen (olasılık oranı 0.10), kısmen örtülü (0.15), kutusu başka biriyle örtüşen (0.08) ve kenarda
  kesik (0.41) kişi daha az bulunuyor; aynı boyda 30° 45°'ten iyi (1.64). Işık, bulanıklık, gürültü ve insan
  çeşitliliği simde ölçülemedi; Ortatepe'ye 8 öneri (bölüm 9).
- **Modelsiz raporla fark:** raporun "15 m'de bile rahat tespit" ve "8 m geride her eğimde başarılı" sonuçları modelle
  geçerli değil; geometri (yer şeridi, ufuk, konum duyarlılığı) aynı.
- **Canlı hakem hatası (İş 1, bölüm 16):** "≈ 7 s duran" hakem, Gazebo'nun segmentasyon karesinin başlığı her karede
  büyüdüğü için ≈ 70 s kayıttan sonra geride kalıyordu; düzeltildi (kare ham okunuyor). Kıvrımlı yol yeniden koşuldu:
  35° 7/10 ve 30° 6/10.4 artık 2/3 (belirsiz kayıplar hataymış), **35° 8/11.4 de 2/3** (bu kez gerçek bir kayıp); iki
  günde 5/6, 3/6, 3/6.
- **Son karar (İş 2, bölüm 17–18): kamera 35°, 9 m yükseklik, 12.9 m geride** (geride durma = yükseklik / tan 35° ≈
  1.43 × yükseklik). 37.5° ve 9 m eklenmiş taramada (19 yeni bileşim, 9 aday iki yolda 3'er koşu) takip yolunda 3/3
  geçen beş ayarın kıvrımlı yolda da 3/3 geçen tek ayarı (son seçimin 3. adımı). Kuralın puanla birincisi 37.5° ·
  9/12.9: takip yolunda 35°'yle pratikte eşit, kıvrımlı yolda kişiyi 6 koşunun 5'inde kaybetti (35° 1'inde). Hiçbir
  45° ayarı geçmedi.
- **Gerçek uçuş önerisi (bölüm 19, doğrulanmamış, ilk uçuşta doğrulanacak):** montaj 35° (hedef 35°, en çok +1°;
  32.5°'ye kadar yatık olabilir), 9 m (8–9 m), 12.9 m geride (8 m'de 11.4 m); açı araçta ±0.5° ile ölçülüp Pi'ye
  girilir; adım adım doğrulama planı bölüm 19'da.
- **Simin varsayılanı (İş 3, bölüm 20):** `kamera.NOMINAL_TILT_DEG` 35° ve `models/x500_tez` (tek kaynak, testli),
  `takip_yuruyen` 9 m / 12.9 m, `kalabalik_park` 9 m; 45° senaryoları `takip_yuruyen_45_10m` / `takip_yuruyen_45_8m`;
  `gercek_dron.params` değişmedi. F0 ve F1 yeni varsayılanla GEÇTİ; `takip_yuruyen` ×3: kişi 3/3 izlendi, en az
  6.63 (5.68–7.12) m; `kalabalik_park` ×3: hedef %99 (98–100) kadrajda, ama yanlış kişiye
  geçme %16 (12–19) (45° / 10 m'de %6–12). 281 test.
- **Alçak + uzak takip denemesi (İş 4, bölüm 21, 14.11 akşam):** kullanıcının fikri (açıyı azalt, alçal, daha geride
  dur; kişi görüntünün ortasının üstünde): 30° 6/12.9, 30° 7/12.9, 32.5° 7/12.9, 35° 8/12.9 iki yolda 3'er koşu +
  kalabalık park 3'er koşu (36 koşu, 1 sa 36 dk). Takip yolunda dördü de 3/3 (köşede 6.7–7.9 m), kıvrımlı yolda 30° 6 m
  dışındakiler 3/3; kuralın sim seçimi **30° 7/12.9** (bulma %73–76, kişi 200 px). Ama sorun alttan üste taşındı:
  hızlanırken burun 12–18° aşağı eğilince kişi görüntünün üstünden çıkıyor (6 m'de kayba kadar); kalabalıkta alçak
  bakışta kişiler üst üste biniyor, yanlış kişi %39–77 (35° 9 m'de %16). Önceden yazılan şart sağlanmadı: **gerçek
  uçuş başlangıcı 35° 9/12.9 kalıyor; yedek 35° 8/12.9** (aynı montaj; 13.11'in yedeği 8/11.4 yerine; doğrulanmamış).
  Varsayılanlar değişmedi.

## 1. Ne yapıldı (kod)

- **Kamera eğimi tek bir ayar** (`kamera.egim_deg`, komut satırında `--kamera-egim`; varsayılan ve gerçek montaj 45°,
  `kamera.NOMINAL_TILT_DEG`). Aralık 0–60° (kamera raporunun taradığı aralık). Bir koşunun eğimi şunlara gider:
  - **Gazebo modeli:** eğim `models/x500_tez`'inkinden (45°) farklıysa koşu klasörüne modelin bir kopyası yazılır
    (`<koşu>/x500_tez_egim30/model.sdf`, yalnız `camera_link`'in pitch'i değişir; kamera ve hakemin segmentasyon
    kamerası birlikte döner) ve dünya bu kopyayı mutlak yoluyla ekler (SDFormat çözüyor). `models/x500_tez/model.sdf`
    hiç değişmez (13.11'de 45°, 14.11'den beri 35°: bölüm 20). Kopya `sonuclar/` altında, git dışında.
  - **LOS (i)** (`takip.Tracker(mount=...)`), **düz zemin konum hesabı** (`konumlama.Locator(mount=...)`), **kameranın
    yakın / uzak görüş sınırı** (`olcum.frame_limits(..., tilt_deg)`: ölçüt, rapor grafiği, videonun halkası),
    **video** (`ozet.json` → `ayarlar.kamera.egim_deg`'den; kuşbakışındaki izdüşüm zaten Gazebo'nun montajından).
  - **Hakem** montajı Gazebo'dan okur (`kayit.Recorder.camera_dcm`); görünürlüğü ve `los_govde` eğimli modelle
    kendiliğinden tutarlıdır. Koşu sonunda Gazebo'nun bildirdiği eğim senaryonunkiyle karşılaştırılır (en çok 0.05°
    fark; değilse olay ve "TAMAMLANMADI"); `ozet.json` → `kamera_montaji.egim_deg`, `ayarlar.kamera.{egim_deg,
    gazebo_modeli}`.
  - İlk deneme (30°, `takip_yuruyen` 8/8, videosuz): Gazebo'nun bildirdiği eğim 30.00001°, koşu 117 s, RTF 0.98,
    yakın sınır 7.04 m (45°'de 8 m'de 3.97 m).
- **Tarama sürücüsü** `araclar/tarama.py` (repo içinde, testli): `plan` (ızgara, her bileşimin senaryosu), `kos`
  (her bileşim `toplu.py` ile; `durum.json`'a biteni yazar, yarıda kesilirse biteni tekrarlamaz), `ozet` (kapılar,
  puanlar, aşama 2 adayları; `ozet.csv`, `ozet.json`).

## 2. Tarama tasarımı (koşulardan önce yazıldı)

**Senaryo:** `takip_yuruyen`'in yolu (`duz_alan`, ağaçsız): kişi 60. s'de doğuya 1.4 m/s yürür, 3 s durur (ani duruş),
kuzeye 3 m/s koşar (köşe + koşu), batıya yürür (köşe). Stok Follow Me, v0.2 CPU'da, `FLW_TGT_RS 0.3` (karar 1, 13.11),
LOS kaynağı model. Her bileşimin senaryosu bu yolun **doğuya kaydırılmış** hâlidir: kişi dronun tam `d` önünde başlar
(kalkışta görüntünün ortasında; yol biçimi ve zamanlaması aynı). Böylece 30° / 15 m / 26 m gibi uzak bir ayarda da kişi
ilk karede görünür ve kilitlenir; kaydırma olmasa kişi kadrajın altında kalırdı.

**Izgara:**

| Bant | Eğim [°] | Yükseklik [m] | Geride durma | Koşu |
|---|---|---|---|---|
| Ana | 30, 35, 40, 45 | 8, 10, 12, 15 | merkez mesafesi `d = h / tan(eğim)` × 0.8, 1.0, 1.25 + raporun 8 m'si | 1 (aşama 1) |
| Düşük (ek istek) | 30, 35, 40, 45 | 4, 5, 6, 7 | merkez mesafesi + raporun 8 m'si | 1 (aşama 1) |

- **Merkez mesafesi:** kamera raporunun kuralının genelleşmesi (45°'de yükseklik = geride durma): optik eksen yere
  kişinin ayaklarının yanında değer. Çarpanlar raporun 45° için denediği aralığı verir (8 m'de 6.4 / 8 / 10 m ≈ raporun
  6.5–10 m'si; 10 m'de 8 / 10 / 12.5 m ≈ 8–12 m; 15 m'de 12 / 15 / 18.8 m, raporun 15/12'si dahil). Raporun "her eğim
  için en alçak başarılı ayar" tablosu hep 8 m geride uçtuğu için 8 m de eklendi.
- **Düşey FOV kontrolü:** kişinin ayakları ve başı (yerden 0 ve 1.75 m) düz uçuşta görüntünün içinde, kenarlardan en az
  2° içeride olmalı (simde düşey yarı açı 20.07°); sığmayan bileşim koşulmaz, planda nedeniyle listelenir
  (`tarama.view`). Ana bantta 6 (ör. 30° / 15 m / 8 m: ayaklar 62.7° aşağıda, görüntü 50.1°'de biter), düşük bantta 3
  (45° / 4 m / 8 m dahil: baş görüntünün üstünden çıkar) bileşim atlandı. Ana bant **55**, düşük bant **26** bileşim, toplam **81** (planlamadan sonra düzeltildi: önce 55 + 29 = 84 yazılmıştı;
  düşük bantta merkez mesafesi 8 m'ye 0.75 m'den yakın olan 3 ek mesafe yinelenen sayıldı).
- Yakın iki mesafe (aynı eğim ve yükseklikte 0.75 m'den yakın) iki kez koşulmaz (6 yinelenen: ana bantta 3, düşük
  bantta 3; ör. 45° / 8 m'de merkez 8.0 m = raporun 8 m'si).
- **PX4 sınırları:** `FLW_TGT_DST` en az 1 m (en çok 100 m, `FOLLOW_DISTANCE_MAX`); `FLW_TGT_HT`'nin `@min 8.0`'ı
  yalnız üst veridir, `FlightTaskAutoFollowTarget.cpp:84` değeri kısmadan kullanır (koordinatörün notu). Düşük bantta
  değerin gerçekten uygulandığı geri okuma (`PARAM_REQUEST_READ`, her koşuda) ve ULog'daki yükseklikle (dron yüksekliği
  ortalaması) doğrulanır; uygulanmıyorsa durulur.
- **Düşük bant yalnız `duz_alan`'da** (ağaçsız; `cayir`'de ağaçlar ≈ 11 m, çarpma riski). `takip_yuruyen`'in yolu zaten
  `duz_alan`'da.

**İki aşama:**

1. Her bileşim 1 koşu, `--videosuz` (RTF korunur): 81 koşu.
2. Adaylar (aşağıdaki kurala göre en çok 6) + 45° 8/8 ve 10/10 başvuruları 3'er koşu, **videolu**; en iyi 1–2 aday
   için ayrıca `--los hakem` (mükemmel algılayıcı) 3'er koşu ve `kivrimli_yuruyus` yolu (kıvrılarak yürüme, duruş,
   yavaş yürüme, kısa koşu, sert dönüş) 3'er koşu (+ karşılaştırma için 45° 10/10).

**Bütçe:** ilk deneme koşusu 117 s (videosuz); aşama 1 ≈ 81 × 2 dk ≈ 2.7 saat (ana bant ≈ 1.9 saat, düşük bant
≈ 1 saat: koordinatörün izin verdiği +1 saat); aşama 2 ≈ 24 videolu koşu × ≈ 3 dk + hakem 6 + kıvrımlı 9 ≈ 2 saat.
Toplam ≈ 4.8 saat + A doğrulaması, F0 / F1. Izgara daraltılmadı.

**Gerçekleşen (13.11):** aşama 1 81 koşu, 13:28–16:17 (önceki ajan 62'sini koştu, 15:32'de durduruldu; kalan 19'u bu işte 15:38–16:17), ≈ 2.0 dk / koşu; iş A'nın iki doğrulama koşusu + F0 + F1 16:17–16:28; aşama 2 24 koşu 16:28–17:27; mükemmel algılayıcı 12 koşu 17:27–17:57; kıvrımlı yol 12 koşu 17:57–18:28 (≈ 2.4–2.6 dk / koşu, videolu). Toplam 129 tarama koşusu (+ 1 altyapı yeniden denemesi) ve 4 doğrulama koşusu; bu işin sim süresi ≈ 2 saat 50 dakika (15:38–18:28).

## 3. Ölçütler ve karar kuralı (koşulardan önce yazıldı)

Kural `tarama.py`'de kodlu ve testlidir (`test_tarama.py`); sonuç bu kurala göre verilir, sonradan değiştirilmez.
Değiştirilirse ayrı bölümde gerekçesiyle yazılır ve eski kuralın sonucu da gösterilir.

**Adım 1 — kapılar (her koşuda sağlanmalı; aşama 1'de 1 koşu, aşama 2'de 3/3):**

| Kapı | Ölçüt | Gerekçe |
|---|---|---|
| Güvenlik | `en_az_yatay_mesafe_m` ≥ 3 m | Karar 3 (12.11): 3 m uyarısı. Koordinatörün kuralı: aşama 2'ye yalnız güvenlik ölçütlerini geçen aday olur |
| Takip başarısı | Kişi koşu sonunda kaybedilmemiş: son giden `FOLLOW_TARGET` ile koşu sonu arası ≤ 3 s (PX4'ün kestirimi 3 s sonra bayat olur; 9. gruptaki "köşeden sonra kişi kaybedildi, stok mod bir daha bulamadı") | Kamera raporunun "başarı" tanımı (dron kişiyi kendi kamerasıyla sonuna kadar izledi) |
| Geçerlilik | Koşu "TAMAMLANMADI" değil | Altyapı hatası sonuç sayılmaz |

**Adım 2 — grup puanları (kapıyı geçenler arasında):** her ölçüt kapıyı geçen bileşimlerin en iyisi 1, en kötüsü 0
olacak şekilde doğrusal ölçeklenir (min–maks; birimleri farklı ölçütler karşılaştırılabilir olsun, "ne kadar iyi"
korunsun diye sıra yerine), grubun puanı ölçütlerinin ortalamasıdır:

| Grup | Ölçütler (↑ büyük iyi, ↓ küçük iyi) |
|---|---|
| Güvenlik | en az yatay mesafe ↑, kaydın 6 m altı payı ↓, 4 m altı payı ↓ |
| Takip sürekliliği | kişi sonda kaybedildi ↓, kilit kaybı ↓, en uzun kadraj dışı ↓, kişinin tamamı kadrajda ↑, gerçekten görünür ↑ |
| Algılama | modelin bulma oranı ↑ (IoU ≥ 0.5), kişinin hakem kutusu boyu [px] ↑ (v0.2, `imgsz` 640'ta modele × 640/2304 girer) |
| Konum hatası | model kutusunun düz zemin konum hatası ort. ↓, p95 ↓ |
| Salınım / arkada kalma | arkada kalma açısı hatası ort. ↓, bağıl mesafe hatası \|d − FLW_TGT_DST\| / FLW_TGT_DST ↓, takip başında yörünge dönüşü ↓ |
| Köşede yetişme | PX4'ün köşede yeni yöne yetişme süresi ↓, yetişemediği köşe ↓, köşeden sonra arkada kalma en çok ↓ |
| Geometri (sim dışı, ölçülmez; eğim, yükseklik ve mesafeden çıkar) | ufuk payı (ufkun kadraja girmesi için burnun kalkması gereken açı, eğim − 20.07°) ↑, zemin duyarlılığı (zemin ya da GPS yüksekliği 1 m yanlışsa konum kayması, d / h) ↓, başların üstündeki yükseklik (h − 1.75 m) ↑ |

**Toplam puan** = 7 grubun ortalaması (eşit ağırlık). Gerekçe: m01'in başarı eşikleri ve öncelikleri henüz yok;
hiçbir grubu ötekinden önemli saymak için ölçülmüş bir dayanak yok. Geometri grubu ayrıca var çünkü kamera raporunda
30° ile 45° arasındaki asıl farkı geometri yaptı (konum hassasiyeti, ufuk) ve sim bunları ölçemez (zemin düz, GPS
yüksekliği kusursuz, otomatik pozlama yok). Ayrıca **sim puanı** (geometrisiz 6 grubun ortalaması) yan yana
gösterilir ve iki duyarlılık denemesi yapılır (güvenlik ×2, algılama ×2): önerilen ayar bunlarla değişiyorsa yazılır.
**Tek sayıya indirgenmez:** sonuç tablosunda her grubun puanı ve ham değerler (artı/eksi) yan yana durur.

**Adım 3 — aşama 2 adayları (aşama 1'den):** kapıyı geçenler arasında her eğimin en iyisi (en çok 4), sonra sıradaki
en iyiler, toplam 6; ayrıca 45° 8/8 ve 10/10 başvuruları (kapıdan geçmeseler de). Bir eğimde kapıyı geçen yoksa o eğim
aday çıkarmaz, bu açıkça yazılır.

**Adım 4 — öneri (aşama 2'den):** 3/3 koşuda kapıyı geçenler arasında toplam puanı en yüksek olan; ikinci seçenek,
farklı bir eğimdeki (yoksa farklı yükseklikteki) en iyi aday. Bedeli: önerilenin eksi olduğu gruplar. Karar
kullanıcınındır; varsayılan 45° montaj ve senaryo varsayılanları bu işte değişmez.

**Rapordaki modelsiz sonuçlarla karşılaştırma:** raporun "her eğim için en alçak başarılı ayar"ı (30°: 4/8, 35–40°:
6/8, 45°: 8/8), 45° çalışan aralıkları (8 m'de 6.5–10, 10 m'de 8–12), başarı 3/3 ve "kişi zamanın %91–96'sında
kadrajda, en uzun kayıp < 2 s" sayıları aynı tanımlarla (kadrajda kalma, en uzun kadraj dışı, kişinin piksel boyu)
yan yana konur.

## 4. Aşama 1 sonuçları (81 bileşim × 1 koşu, videosuz)

Koşular 13.11, 13:28–16:17 (15:32'de önceki ajan durdurulunca `e35_h4_d5.7` yarıda kaldı; 15:38'de aynı komutla
kaldığı yerden sürdü, biten 62 bileşim tekrarlanmadı, yarım klasör `e35_h4_d5.7_yarim_153924` olarak ayrıldı). 81/81
koşu GEÇTİ (koşu sonucu, kapı değil); bir koşu PX4'ten heartbeat gelmediği için başlayamadı ve `toplu.py` onu yeniden
denedi (bilinen seyrek açılış hatası, `e45_h7_d8.0/kosu_1_deneme1`; sonuç sayılmadı). Koşu başına ≈ 2.0 dk, RTF ort.
0.965 (en düşük 0.896). Klasör: `tez/sim/sonuclar/gorev10on_tarama/asama1/` (`ozet.csv`, `ozet.json`).

**`FLW_TGT_HT` < 8 gerçekten uygulandı** (`yukseklik_kontrol.csv`, repo dışı betik `yukseklik_kontrol.py`): düşük
bandın 26 koşusunun hepsinde PX4'ten kalkıştan önce geri okunan değer istenenle aynı, PX4'ün kendi ULog'undaki
yükseklik (ev noktasına göre, 60–90 s) istenenden en çok 0.15 m farklı; Gazebo'nun ölçtüğü dron yüksekliği de öyle.
PX4'ün `@min 8.0`'ı yalnız üst veri (QGC uyarır), kod değeri kısmıyor.

**Kapı:** 81 bileşimin **23**'ü geçti. Geçemeyenlerin 27'si yalnız "kişi sonda kaybedildi", 5'i yalnız "3 m'den
yakın" (kişi sonuna kadar izlendi ama köşede 3 m'nin altına inildi: 35° 8/9.1, 45° 8/10, **45° 10/10** (2.17 m), 40°
4/4.8, 40° 7/8.3), 26'sı ikisi birden.

| | 30° | 35° | 40° | 45° |
|---|---|---|---|---|
| Kapıyı geçen | 7/20 | 6/21 | 7/20 | **3/20** |

| Yükseklik [m] | 4 | 5 | 6 | 7 | 8 | 10 | 12 | 15 |
|---|---|---|---|---|---|---|---|---|
| Kapıyı geçen | 0/6 | 0/6 | 2/7 | 2/7 | 7/14 | 9/14 | 3/14 | 0/13 |
| Modelin bulma oranı, ort. (en az–en çok) [%] | 82 (77–88) | 75 (69–79) | 75 (70–81) | 73 (68–79) | 66 (45–76) | 39 (0–57) | 9 (0–35) | 0 (0–1) |
| Kişinin hakem kutusu, ortanca [px] | 396 | 324 | 281 | 243 | 206 | 159 | 124 | 95 |
| Kişi nerede kaybedildi (koşu sayısı) | köşe 4, koşu 1, izlendi 1 | köşe 5, koşu 1 | köşe 5, izlendi 2 | köşe 3, durma 1, izlendi 3 | izlendi 9, köşe 2, durma 2, koşu 1 | izlendi 10, durma 2, koşu 1, hiç 1 | hiç 10, durma 1, izlendi 3 | hiç 13 |

("Kişi nerede kaybedildi": son giden `FOLLOW_TARGET`'ın zamanı yolun köşelerine göre: "hiç" = model kişiyi
neredeyse hiç bulamadı (bulma < %5), "durma" = doğuya yürüyüş ya da duruş, "koşu" = kuzeye ani koşu, "köşe" = batıya
dönüşten sonra, "izlendi" = sonuna kadar; repo dışı `yaklasma_analizi.py`.)

**Üç bölge açıkça ayrılıyor:**

1. **12 m ve üstü: model kişiyi bulamıyor.** Kişi 15 m'de ≈ 95 px, 12 m'de ≈ 124 px; v0.2 640 piksellik girişte bunu
   ≈ 26–34 px görüyor ve bulma oranı %0–35'e düşüyor. Kamera raporunun "15 m'de bile kişi 100 pikselden büyük; tespit için
   rahat bir boyut" cümlesi kırmızı kutu içindi; **bu modelle doğru değil**. 12 m'de yalnız kişi drona yakınken (kısa
   eğik mesafe: 40° 12/11.4, 45° 12/12) bulma %32–35 ve kapıdan geçti; kilit 7–9 kez düştü.
2. **4–7 m: model iyi buluyor (%70–88), ama köşede dron kişinin üstüne geliyor.** 26 bileşimin 17'sinde kişi
   batıya dönüşten sonra kaybedildi; yalnız merkez mesafesinin uzun olduğu 30° 6/10.4, 30° 7/12.1, 35° 7/10 ve kısa bir
   koşuda 40° 6/8 geçti. **Kullanıcının örneği 30° 4 m / 8 m geçmedi** (en az 0.06 m, kişi köşeden sonra kaybedildi).
3. **8–10 m: ikisinin dengesi.** Model ortalama %66 (8 m) ve %39 (10 m) buluyor, kişi çoğunlukla sonuna kadar izleniyor; geçmeyenler geride durma
   mesafesi kısa olanlar (8 m ve altı) ve 10 m'de kişinin uzakta kaldığı (17–18 m) bileşimler.

**Raporun 8 m'si:** 19 bileşimin yalnız biri (40° 6/8, kısa köşe yaklaşmasıyla tek koşu) geçti. Kamera raporunda her
eğimin "en alçak başarılı ayarı" 8 m gerideydi; modelle ve bu yolla 8 m geride durma köşede yetmiyor (bölüm 8).

Isı haritaları: `~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_isi_<ölçüt>.png` (14 ölçüt; her biri dört panel:
merkez mesafesinin 0.8 / 1 / 1.25 katı ve raporun 8 m'si; satır yükseklik, sütun eğim, ✗ kapıdan geçmedi).

**Aşama 2 adayları (kural, adım 3; aşama 1'in tek koşusundan):**

| Sıra | Bileşim | Neden | Toplam | Sim puanı | En az [m] | Bulma [%] | Kutu [px] | Yaklaşma payı [m] |
|---|---|---|---|---|---|---|---|---|
| 1 | 40° · 6 m / 8 m | 40° için en iyi | 0.66 | 0.70 | 4.14 | 71 | 290 | 4.3 |
| 2 | 35° · 7 m / 10 m | 35° için en iyi | 0.63 | 0.67 | 3.94 | 79 | 236 | 4.8 |
| 3 | 40° · 12 m / 11.4 m | sıradaki en iyi | 0.63 | 0.58 | 8.03 | 32 | 142 | 4.2 |
| 4 | 35° · 8 m / 11.4 m | sıradaki en iyi | 0.63 | 0.66 | 4.91 | 76 | 206 | 5.5 |
| 6 | 30° · 6 m / 10.4 m | 30° için en iyi | 0.62 | 0.71 | 4.79 | 80 | 250 | 5.1 |
| 10 | 45° · 12 m / 12 m | 45° için en iyi | 0.60 | 0.53 | 7.40 | 35 | 144 | 6.2 |
| – | 45° · 8 m / 8 m | başvuru (kapıdan geçmedi) | 0.52 | 0.48 | 2.19 | 61 | 218 | 4.0 |
| – | 45° · 10 m / 10 m | başvuru (kapıdan geçmedi: 2.17 m) | 0.53 | 0.47 | 2.17 | 46 | 174 | 5.1 |

Tek koşu gürültülü: 40° 6/8 köşede yalnız 3.9 m yaklaştı (aşama 1'in tipik değeri ≈ 6 m; yaklaşma payı 4.3 m), 45° 10/10
9. grubun üç koşusunda kapıdan geçmişti (2.99–5.10 m), burada 2.17 m. Aşama 2'nin 3'er koşusu bunun için.

## 5. Aşama 2 sonuçları (8 bileşim × 3 koşu, videolu)

Koşular 13.11, 16:28–17:27 (24 koşu, hepsi GEÇTİ; koşu başına ≈ 2.4 dk; RTF ort. 0.92, en düşük 0.89). Klasör:
`tez/sim/sonuclar/gorev10on_tarama/asama2/` (`ozet.csv`, `ozet.json`; her bileşimde `toplu.html`, her koşuda `kosu.mp4`
ve `rapor.html`). Değerler 3 koşunun ortalaması (en az–en çok).

| Bileşim | En az mesafe [m] | < 6 m [%] | Kişi kaybı | Kadrajda [%] | Görünür [%] | En uzun kayıp [s] | Bulma [%] | Kutu [px] | Kilit kaybı | Konum hatası [m] | Arkada kalma [°] | Köşede yetişme [s] | Köşe yaklaşması [m] | Yaklaşma payı [m] | d / h | Ufuk payı [°] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 35° · 7 m / 10 m | 3.9 (3.7–4.2) | 3 (2–3) | 0/3 | 95 (93–95) | 97 (96–97) | 1.2 (1.1–1.2) | 77 (74–79) | 237 (236–238) | 1.0 (1.0–1.0) | 0.34 (0.32–0.38) | 61 (57–65) | 1.9 (1.8–1.9) | 6.1 (5.8–6.3) | 4.8 | 1.43 | 14.9 |
| 30° · 6 m / 10.4 m | 4.2 (3.8–4.4) | 2 (2–3) | 0/3 | 92 (91–93) | 98 (97–98) | 0.9 (0.9–1.1) | 83 (82–86) | 252 (252–252) | 1.0 (1.0–1.0) | 0.36 (0.34–0.39) | 68 (62–76) | 1.9 (1.8–2.0) | 6.2 (6.0–6.6) | 5.1 | 1.73 | 9.9 |
| 35° · 8 m / 11.4 m | 5.3 (5.2–5.5) | 1 (1–2) | 0/3 | 94 (93–95) | 97 (97–98) | 1.0 (0.9–1.0) | 73 (72–74) | 204 (202–206) | 2.3 (2.0–3.0) | 0.43 (0.41–0.44) | 71 (62–80) | 2.0 (1.8–2.1) | 6.1 (5.9–6.2) | 5.5 | 1.43 | 14.9 |
| 40° · 12 m / 11.4 m | 7.0 (5.6–7.9) | 0 (0–1) | 0/3 | 89 (87–91) | 93 (90–96) | 1.1 (1.0–1.4) | 30 (29–31) | 142 (140–146) | 8.0 (8.0–8.0) | 0.38 (0.29–0.45) | 77 (70–84) | 5.1 (4.6–6.1) | 4.4 (3.5–5.8) | 4.2 | 0.95 | 19.9 |
| 45° · 8 m / 8 m | 1.0 (0.7–1.4) | 6 (5–7) | 2/3 | 63 (56–75) | 68 (62–80) | 8.6 (3.6–11.1) | 64 (62–66) | 223 (220–226) | 2.3 (2.0–3.0) | 0.28 (0.22–0.35) | 54 (49–61) | 2.0 (1.9–2.1) | 7.0 (6.6–7.3) | 4.0 | 1.00 | 24.9 |
| 45° · 10 m / 10 m | 3.4 (3.0–3.8) | 3 (3–4) | 1/3 | 84 (68–94) | 87 (70–96) | 3.5 (1.3–7.8) | 54 (47–59) | 176 (172–178) | 4.0 (3.0–5.0) | 0.39 (0.27–0.59) | 66 (64–68) | 2.6 (2.4–2.9) | 6.6 (6.2–7.0) | 5.1 | 1.00 | 24.9 |
| 45° · 12 m / 12 m | 5.8 (3.4–8.4) | 2 (0–4) | 1/3 | 73 (60–92) | 81 (63–93) | 4.6 (1.2–7.6) | 23 (13–38) | 138 (134–144) | 5.0 (4.0–6.0) | 0.63 (0.55–0.78) | 63 (55–71) | 2.1 (0.0–4.2) | 6.2 (3.6–8.6) | 6.2 | 1.00 | 24.9 |
| 40° · 6 m / 8 m | 1.2 (1.0–1.5) | 9 (6–11) | 3/3 | 54 (52–55) | 63 (63–64) | 10.9 (10.7–11.0) | 71 (70–73) | 278 (276–280) | 1.7 (1.0–2.0) | 0.23 (0.23–0.24) | 53 (51–58) | 2.0 (1.9–2.0) | 6.8 (6.5–7.0) | 4.3 | 1.33 | 19.9 |

**Kapı (3/3 koşuda ≥ 3 m ve kişi sonuna kadar izlendi):** 35° 7/10, 30° 6/10.4, 35° 8/11.4, 40° 12/11.4 geçti.
**Hiçbir 45° ayarı geçmedi:** 8/8'de üç koşunun ikisinde kişi köşeden sonra kaybedildi, üçünde de dron 1.4 m'den
yakına geldi; 10/10'da bir koşuda kişi köşeden hemen sonra (78.5 s) kaybedildi (köşe yaklaşması 7.0 m, yaklaşma payı
5.1 m; kişi kadrajın yanından 6.8 s, altından 2.9 s çıktı) ve en az mesafe 2.96–3.82 m; 12/12'de bir koşuda kaybedildi
(model kişiyi %13 buldu). Aşama 1'de geçen 40° 6/8 (tek koşuda köşe yaklaşması 3.9 m'de kalmıştı) üç koşunun üçünde
kişiyi kaybetti ve 1.5 m'den yakına geldi: yaklaşma payı (4.3 m) ölçülen köşe yaklaşmasından (≈ 6.2 m) küçük; tek koşu
şanslıydı.

**45° 10/10'un bütün koşuları** (9. grup 3, aşama 1 1, iş A 1, aşama 2 3 = 8 koşu): kişi 8 koşunun 7'sinde sonuna kadar
izlendi, 5'inde dron 3 m'nin dışında kaldı (en az 2.17–6.39 m); model %46–62 buldu. 45° 8/8 (9. grup 3, aşama 1 1,
aşama 2 3 = 7 koşu): 1/7 izlendi, hiçbirinde ≥ 3 m (0.45–2.19 m).

Kişi nerede kaybedildi (aşama 2, 24 koşu): 17'si sonuna kadar izlendi, 7'si batıya dönüşten (köşe) sonra kaybedildi
(40° 6/8 3, 45° 8/8 2, 45° 10/10 1, 45° 12/12 1).

Görsel: `~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_aday_karsilastirma.png` (her ölçüt için 3 koşu nokta,
ortalama çubuk; grup puanları; toplam ve sıra).

### Mükemmel algılayıcı (`--los hakem`) ve kıvrımlı yol (13.11, 17:27–18:28; 24 koşu, hepsi GEÇTİ)

Kuralın ilk ikisi (35° 7/10, 30° 6/10.4), önerdiğim 35° 8/11.4 (bölüm 6) ve 45° 10/10 başvurusu, 3'er koşu, videolu.
Klasörler `asama2_hakem/`, `asama2_kivrimli/`.

**Mükemmel algılayıcı** (`takip_yuruyen` yolu; PX4'e modelin kutusu yerine hedefin gerçek konumu gider, yalnız hedef
görünürken; model yine çalışır ve ölçülür):

| Bileşim (3 koşu) | Kapı | En az mesafe [m] | < 6 m [%] | Kişi kaybı | Kadrajda [%] | Görünür [%] | En uzun kayıp [s] | Bulma [%] | Kilit kaybı | Konum hatası [m] | Arkada kalma [°] | Köşede yetişme [s] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 30° · 6 m / 10.4 m | geçti | 4.4 (4.3–4.5) | 2 (2–2) | 0/3 | 94 (94–95) | 97 (97–97) | 1.1 (1.1–1.2) | 83 (82–84) | 1.0 (1.0–1.0) | 0.40 (0.37–0.43) | 59 (59–60) | 1.7 (1.6–1.7) |
| 35° · 7 m / 10 m | geçti | 3.9 (3.9–4.0) | 3 (3–3) | 0/3 | 95 (94–96) | 97 (97–97) | 1.1 (1.1–1.2) | 76 (76–76) | 1.3 (1.0–2.0) | 0.33 (0.30–0.35) | 57 (56–59) | 1.7 (1.7–1.9) |
| 35° · 8 m / 11.4 m | geçti | 5.2 (5.2–5.3) | 2 (1–2) | 0/3 | 96 (96–96) | 97 (97–97) | 1.1 (1.1–1.1) | 76 (76–76) | 2.0 (1.0–3.0) | 0.37 (0.36–0.37) | 66 (64–67) | 1.8 (1.7–1.8) |
| 45° · 10 m / 10 m | geçti | 3.9 (3.7–4.0) | 3 (3–3) | 0/3 | 96 (95–96) | 96 (96–97) | 1.2 (1.1–1.3) | 64 (62–66) | 4.3 (3.0–6.0) | 0.31 (0.29–0.34) | 58 (57–59) | 1.7 (1.7–1.8) |

- Dördü de 3/3 kapıyı geçti; **45° 10/10 da** (en az 3.7–4.0 m, kişi hiç kaybedilmedi). Yani 45° 10/10'un model
  koşularındaki kaybı (8 koşuda 1) köşede modelin kişiyi geç bulmasından (o koşuda bulma %47).
- Köşedeki en az mesafe hakemle de modelle de aynı: 35° 8/11.4'te 5.2 / 5.3 m, 35° 7/10'da 3.9 / 3.9 m, 30° 6/10.4'te
  4.4 / 4.2 m. **Köşe yaklaşması PX4'ün kendi davranışı**, modelin konum gürültüsü değil.

**Kıvrımlı yol** (`kivrimli_yuruyus`, aynı kaydırma kuralıyla: kişi kıvrılarak kuzeydoğuya yürür, 4 s durur, yavaş
yürür, 3.5 m/s kısa koşu, sonra 88 s'de **164°'lik sert geri dönüşle** drona doğru yürür; model):

| Bileşim (3 koşu) | Kapı | En az mesafe [m] | < 6 m [%] | Kişi kaybı | Kadrajda [%] | Görünür [%] | En uzun kayıp [s] | Bulma [%] | Kilit kaybı | Konum hatası [m] | Arkada kalma [°] | Köşede yetişme [s] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kıvrımlı yol, 30° · 6 m / 10.4 m | kişi sonda kaybedildi (2/3 koşu) | 4.5 (3.0–6.6) | 5 (0–8) | 2/3 | 87 (74–99) | 93 (82–100) | 2.4 (0.0–6.0) | 84 (83–85) | 0.7 (0.0–1.0) | 0.40 (0.36–0.42) | 52 (45–57) | 1.6 (1.5–1.7) |
| kıvrımlı yol, 35° · 7 m / 10 m | kişi sonda kaybedildi (2/3 koşu) | 6.0 (5.4–6.3) | 1 (0–2) | 2/3 | 85 (67–97) | 91 (75–100) | 3.3 (0.3–8.8) | 81 (80–84) | 1.3 (0.0–3.0) | 0.32 (0.30–0.36) | 44 (44–46) | 1.7 (1.6–1.8) |
| kıvrımlı yol, 35° · 8 m / 11.4 m | geçti | 7.0 (6.0–8.1) | 0 (0–1) | 0/3 | 97 (95–98) | 100 (100–100) | 0.1 (0.0–0.3) | 77 (75–78) | 1.0 (0.0–2.0) | 0.42 (0.42–0.42) | 54 (51–58) | 1.7 (1.6–1.8) |
| kıvrımlı yol, 45° · 10 m / 10 m | kişi sonda kaybedildi (3/3 koşu) | 5.2 (4.5–5.7) | 3 (2–5) | 3/3 | 71 (69–73) | 77 (74–80) | 8.3 (7.5–8.7) | 67 (62–70) | 2.7 (2.0–3.0) | 0.55 (0.30–0.72) | 50 (48–53) | 2.2 (1.9–2.5) |

- **Yalnız 35° 8/11.4 3/3 geçti** (kişi 3/3 sonuna kadar izlendi, en az 6.0–8.1 m, kişinin tamamı %97 kadrajda, en uzun
  kayıp 0.1 s). 35° 7/10 ve 30° 6/10.4 üç koşunun ikisinde, 45° 10/10 üçünde de kişiyi kaybetti.
- Bütün kayıplar sert geri dönüşte (88 s): kişi geri dönüp drona doğru yürüyor, PX4 dronu kişinin yeni "arkasına"
  döndürene kadar kişi kameranın yakın sınırının içine giriyor ve kadrajın **altından** çıkıyor (kaybedilen koşularda
  alttan 2–10 s, yandan ≤ 1.7 s). Yaklaşma payı en büyük olan 35° 8/11.4 (5.5 m; diğerleri 4.8–5.1 m) kişiyi tuttu.
- 45° 10/10'da model kişiyi %62–70 buldu; kişi alttan çıkınca yeniden bulunamadı ve PX4'ün kestirimi bayatladı.
- **Belirsiz iki kayıp (sim sorunu, bölüm 12):** 35° 7/10'un 2. ve 30° 6/10.4'ün 1. koşusunda kilit düştükten sonra kişi
  kadrajda (%92 / %74) ve model onu buluyorken yeniden kilit ≈ 7 s denenemedi: hakemin canlı satırı gelmedi
  (`hakem_yok`; satırlar sonradan `dogru_cevap.csv`'de var). Gerçekte operatör ya da m11 hedefi yeniden seçerdi. Bu iki
  koşu izlenmiş sayılırsa 35° 7/10 ve 30° 6/10.4 kıvrımlı yolda 2/3 olur; **35° 8/11.4 yine iki yolda da 3/3 geçen tek
  ayar** kalır.
  **Sonra (İş 1, bölüm 16):** kök neden bulundu ve düzeltildi; iki kayıp hakem hatasıydı. Düzeltilmiş kodla yeniden koşuda
  35° 7/10 ve 30° 6/10.4 2/3, 35° 8/11.4 de 2/3 (bir gerçek kayıp); iki günün altı koşusunda 3/6, 3/6, 5/6.

Görseller: `gorev10on_hakem_karsilastirma.png`, `gorev10on_kivrimli_karsilastirma.png`.

## 6. Karar kuralının sonucu ve öneri

**Kuralın sonucu (bölüm 3, adım 4; değiştirilmeden uygulandı).** Grup puanları kapıdan 3/3 geçen dört bileşim arasında
ölçeklendi (en iyi 1, en kötü 0; `+` ≥ 0.67, `−` ≤ 0.33, `○` arası):

| Sıra | Bileşim (3 koşu) | Kapı | Güv. | Sür. | Alg. | Konum | Salın. | Köşe | Geo. | Toplam | Sim |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 35° · 7 m / 10 m | geçti | − 0.00 | ○ 0.56 | + 0.88 | + 0.97 | + 0.68 | + 1.00 | ○ 0.35 | 0.63 | 0.68 |
| 2 | 30° · 6 m / 10.4 m | geçti | − 0.21 | + 0.70 | + 1.00 | + 0.90 | ○ 0.45 | ○ 0.66 | − 0.00 | 0.56 | 0.65 |
| 3 | 35° · 8 m / 11.4 m | geçti | ○ 0.66 | + 0.68 | + 0.69 | − 0.00 | ○ 0.45 | + 0.72 | ○ 0.41 | 0.51 | 0.53 |
| 4 | 40° · 12 m / 11.4 m | geçti | + 1.00 | − 0.04 | − 0.00 | + 0.72 | ○ 0.33 | − 0.11 | + 1.00 | 0.46 | 0.37 |
| ✗ | 45° · 8 m / 8 m | en az yatay mesafe 0.69 m < 3 m; kişi sonda kaybedildi (2/3 koşu) | − 0.00 | − 0.16 | + 0.68 | + 1.00 | ○ 0.33 | ○ 0.65 | + 0.76 | 0.51 | 0.47 |
| ✗ | 45° · 10 m / 10 m | en az yatay mesafe 2.96 m < 3 m; kişi sonda kaybedildi (1/3 koşu) | − 0.00 | − 0.11 | ○ 0.38 | + 0.70 | − 0.24 | + 0.92 | + 0.87 | 0.46 | 0.39 |
| ✗ | 45° · 12 m / 12 m | kişi sonda kaybedildi (1/3 koşu) | ○ 0.33 | − 0.09 | − 0.00 | − 0.00 | ○ 0.53 | ○ 0.65 | + 0.98 | 0.37 | 0.27 |
| ✗ | 40° · 6 m / 8 m | en az yatay mesafe 0.97 m < 3 m; kişi sonda kaybedildi (3/3 koşu) | − 0.00 | − 0.18 | + 0.89 | + 1.00 | ○ 0.67 | ○ 0.66 | ○ 0.50 | 0.56 | 0.57 |

- **Kuralın önerisi: 35° · 7 m / 10 m** (toplam 0.63; dört duyarlılık denemesinin dördünde de birinci: sim puanı,
  güvenlik ×2, algılama ×2). **İkinci seçenek** (kural: farklı bir eğimdeki en iyi): **30° · 6 m / 10.4 m** (0.56).
- Duyarlılık: sim puanında ve algılama ×2'de sıra aynı (35° 7/10 > 30° 6/10.4 > 35° 8/11.4 > 40° 12/11.4); güvenlik ×2'de
  35° 8/11.4 ikinciliğe çıkıyor, 30° 6/10.4 sonuncu oluyor.

**Kuralın bir zayıflığı (koşulardan sonra görüldü, kural değiştirilmedi):** min–maks ölçekleme farkın büyüklüğüne
bakmıyor. 35° 8/11.4'ün konum grubu 0.00 çünkü konum hatası 0.43 m, diğerlerininki 0.34–0.38 m (0.05–0.09 m'lik, gerçek
uçuşta zemin ve GPS hatasının yanında önemsiz bir fark); buna karşılık güvenlikte köşedeki en az mesafe 5.3 m'ye karşı
35° 7/10'da 3.9 m (1.4 m'lik, 3 m uyarısına göre önemli bir fark) yalnız 0.66 puan getiriyor.

**Artı / eksi (ham değerlerle, kapıdan geçenler ve 45° başvurusu):**

| | 35° · 8 m / 11.4 m | 35° · 7 m / 10 m (kuralın birincisi) | 30° · 6 m / 10.4 m (kuralın ikincisi) | 45° · 10 m / 10 m (bugünkü montaj) |
|---|---|---|---|---|
| Köşede en az mesafe (3 koşu) | **+ 5.2–5.5 m** | ○ 3.7–4.2 m | ○ 3.8–4.4 m | − 2.96–3.82 m (8 koşuda 2.17–6.39) |
| Kişi sonuna kadar izlendi | + 3/3 | + 3/3 | + 3/3 | − 2/3 (8 koşuda 7/8) |
| **Kıvrımlı yol (164° geri dönüş): kişi izlendi / en az mesafe** | **+ 3/3 / 6.0–8.1 m** | − 1/3 (belirsiz kayıp sayılmazsa 2/3) / 5.4–6.3 m | − 1/3 (2/3) / 3.0–6.6 m | − 0/3 / 4.5–5.7 m |
| Mükemmel algılayıcıyla (`takip_yuruyen`): izlendi / en az mesafe | + 3/3 / 5.2–5.3 m | + 3/3 / 3.9–4.0 m | + 3/3 / 4.3–4.5 m | + 3/3 / 3.7–4.0 m |
| Kişinin tamamı kadrajda / en uzun kayıp | + %94 / 1.0 s | + %95 / 1.2 s | + %92 / 0.9 s | ○ %84 / 3.5 s |
| Modelin bulma oranı / kişi boyu | ○ %73 / 204 px | + %77 / 237 px | **+ %83 / 252 px** | − %54 / 176 px |
| Kilit kaybı | ○ 2.3 | + 1.0 | + 1.0 | − 4.0 |
| Konum hatası (sim) | ○ 0.43 m | + 0.34 m | + 0.36 m | ○ 0.39 m |
| Köşede PX4'ün yetişmesi / arkada kalma | + 2.0 s / ○ 71° | + 1.9 s / + 61° | + 1.9 s / ○ 68° | ○ 2.6 s / ○ 66° |
| Yükseklik (PX4 Follow Me'nin önerdiği alt sınır 8 m) | **+ 8 m** | − 7 m | − 6 m | + 10 m |
| Başların üstünde | ○ 6.25 m | − 5.25 m | − 4.25 m | + 8.25 m |
| Ufuk payı (burun ne kadar kalkınca ufuk kadraja girer) | ○ 14.9° | ○ 14.9° | − 9.9° | + 24.9° |
| Zemin / GPS yüksekliği 1 m hatalıysa konum kayması | ○ 1.43 m | ○ 1.43 m | − 1.73 m | + 1.0 m |
| Dron kişinin gerisinde / gereken boş alan | ○ 11.4 m | ○ 10 m | ○ 10.4 m | ○ 10 m |
| Donanım | − yeni montaj parçası (35°) | − yeni montaj parçası (35°) | − yeni montaj parçası (30°) | + değişiklik yok |

**Önerim: kamera 35° aşağı, 8 m yükseklik / 11.4 m geride** (`FLW_TGT_HT 8`, `FLW_TGT_DST 11.4`; kural: geride durma ≈
1.43 × yükseklik, kişi görüntünün ortasında). Kuralın birincisiyle (35° 7/10) **aynı montaj**; aradaki fark iki
parametre, sahada değiştirilebilir. Gerekçe:

0. **İki yolda da 3/3 geçen tek ayar:** kıvrımlı yolun 164°'lik sert geri dönüşünde kişiyi üç koşunun üçünde tuttu (en az 6.0–8.1 m); kuralın birincisi (35° 7/10) ve ikincisi (30° 6/10.4) orada üç koşunun ikisinde (birer kaybı sim sorunuyla karışık, onlar sayılmasa da birer kayıp kalıyor), 45° 10/10 üçünde kişiyi kaybetti (bölüm 5).
1. Kapıyı 3/3 geçen dört ayardan köşede kişiye en az yaklaşan ikincisi (5.2–5.5 m; yalnız modelin %30 bulduğu 40°
   12/11.4 daha uzak), kişiyi her koşuda sonuna kadar izliyor, kişi %94 kadrajda, en uzun kayıp 1 s.
2. PX4'ün Follow Me için önerdiği en düşük yükseklikte (8 m; `FLW_TGT_HT` `@min 8.0`) ve kamera raporunun "en alçak
   rahat ayar"ında; 7 m ve 6 m bu alt sınırın altında (QGC uyarır) ve başlara 1–2 m daha yakın.
3. Algılamanın bedeli küçük: model %73 (35° 7/10'da %77), kişi 204 px (8/8'deki 220 px'e yakın), kilit kaybı 2.3.
4. Köşedeki ≈ 6.2 m'lik mutlak yaklaşmaya karşı yaklaşma payı 5.5 m: dört geçenin en büyüğü (bölüm 8).

**Bedeli:** (a) yeni bir montaj parçası ve açının araçta ölçülüp yazılıma girilmesi; (b) konum hesabı zemin eğimine ve
GPS yükseklik hatasına 45°'den 1.43 kat duyarlı (1 m hata → 1.43 m kayma; kampüsteki %3–7 eğim); (c) ufuk payı 14.9°
(frende burun 6–11° kalkıyor: 4–9° pay kalıyor, sert frende ya da rüzgârda gökyüzü kadrajın üstüne yaklaşır, otomatik
pozlama etkisi simde yok); (d) dron kişinin 11.4 m gerisinde: daha geniş boş alan ve 13.4 m'lik açık görüş hattı;
(e) kişi 45° 8/8'e göre biraz küçük (204 / 220 px) ve kilit biraz daha sık düşüyor (2.3 / 1.0, 35° 7/10'a göre).

**İkinci seçenek: 30° · 6 m / 10.4 m** (farklı eğimdeki en iyi; kuralın da ikincisi): en iyi algılama (%83, 252 px) ve
en kısa kayıp; ama kıvrımlı yolda üç koşunun ikisinde kişiyi kaybetti; ama 6 m'de (başların 4.25 m üstü, PX4'ün alt sınırının 2 m altı), ufuk payı yalnız 9.9° (frende her
seferinde ufuk kadraja girebilir) ve konum hatası 1.73 kat duyarlı. Alan boş, düz ve insansızsa düşünülebilir.

**45°'de kalınacaksa (montaj değişmeden): 10 m / 10 m** (iş A'nın yeni `takip_yuruyen`'i): 8 koşuda 7/8 izlendi, 5/8'de
≥ 3 m; stok Follow Me ile hiçbir 45° ayarı 3/3 kapıyı geçmedi. 8/8 bu yolda önerilmez (7 koşuda 1/7 izlendi). Kalıcı
çözüm m15'in en az mesafe koruması (dron köşede kişiye ≈ 6 m'den fazla yaklaşmasın): o zaman 45° 10/10'un köşedeki
sorunu da büyük ölçüde kalkar; bu, yeni montajdan önce denenmeye değer.

**Karar kullanıcının ve ekibin:** varsayılan montaj (45°, `models/x500_tez`), `takip_yuruyen` (iş A: 10/10) ve gerçek
dronun parametreleri bu işte (13.11) değişmedi; 14.11'de son karar (bölüm 18) simin varsayılanı oldu (bölüm 20). Öneri stok Follow Me ve v0.2 ile, tek yolda (+ kıvrımlı yol, bölüm 5) ve
simde ölçüldü; gerçek uçuştan önce bölüm 10'daki farklar okunmalı.

## 7. Kamera raporunun modelsiz sonuçlarıyla yan yana: ne değişti, neden?

Rapor (23–24.10, `planning/kaynaklar/Kamera_ve_Takip_Ayarlari_Raporu.pdf`): eski WSL simi, hedef kırmızı bir kutu (renk
eşikli algılama: her boyutta kusursuz), kamera gövde hizasında, stok Follow Me (`FLW_TGT_RS` varsayılan 0.1), yol "yürü,
dön, dur, birden koş, aniden geri dön"; başarı = dron kişiyi yalnız kendi kamerasıyla sonuna kadar izledi (3 denemenin
3'ü). Bu tarama: yeni sim (insan modeli, kamera gerçek montaj yerinde), **v0.2 modeli** (CPU, 640 giriş), stok Follow Me
`FLW_TGT_RS 0.3`, `takip_yuruyen` yolu (60 s'de doğuya yürü, 3 s dur, kuzeye 3 m/s koş, 90° dönüp batıya yürü). Raporla
aynı tanımı kullanmak için "kişi sonuna kadar izlendi" ayrıca gösterildi (kapı buna ≥ 3 m'yi de ekliyor).

| Raporun bulgusu | Bu taramada (modelle) | Neden farklı |
|---|---|---|
| "15 m'de bile kişi 100 pikselden büyük; tespit için rahat" | 15 m'de kişi ≈ 95 px, **model %0–1 buluyor**; 12 m'de ≈ 124 px, %0–35 (ort. 9) | Kırmızı kutu her boyutta bulunur; v0.2 kişiyi 640 piksellik girişte görüyor (2304 px'lik kare 3.6 kat küçülüyor, kişi ≈ 26–34 px) ve ≈ 150 px'in altında hızla kaçırıyor (bölüm 9) |
| Her eğimin en alçak başarılı ayarı 8 m geride: 30° 4/8, 35–40° 6/8, 45° 8/8 (3/3) | 8 m geride: 19 bileşimin yalnız biri kapıdan geçti (40° 6/8, tek koşu; aşama 2'de 0/3); **30° 4/8 kişiyi köşeden sonra kaybetti** (en az 0.06 m); "yalnız izlendi" tanımıyla da 8 m geride 30° / 35° / 45°'de izlenen yok, 40°'ta 6 m | Köşede stok Follow Me ≈ 6.2 m yaklaşıyor (bölüm 8); 8 m geride yaklaşma payı 0.7–5.0 m (yükseklik arttıkça küçülür), kişi kadrajın altından çıkıyor. Rapor bunu görmemiş: kusursuz algılayıcıda konum gürültüsü yok, `FLW_TGT_RS` 0.1 daha tepkisel (9. grup: RS 0.3'ün bedeli köşede ≈ 0.5 m daha yakın geçiş) |
| 45° çalışan aralıklar: 8 m'de 6.5–10, 10 m'de 8–12 m geride; 6/8 0/3 | 8 m yükseklikte: 6.4 m geride kayıp (0.42 m); **8 m geride 7 koşunun 1'inde izlendi, hiçbirinde ≥ 3 m değil** (0.45–2.19 m); 10 m geride izlendi ama 1.29 m. 10 m yükseklikte: 8 m geride kayıp (0.73 m); **10/10 8 koşunun 7'sinde izlendi, 5'inde ≥ 3 m** (2.17–6.39 m); 12.5 m geride geçti (5.47 m). 12/10 (9.6) ve 15/12: model kişiyi bulamadı, kayıp. 6/8: kayıp (1.54 m), raporla aynı | Aynı: aşma ≈ 6 m'lik mutlak bir mesafe, kısa geride durma onu karşılamıyor |
| Kişi zamanın %91–96'sında kadrajda, en uzun kayıp < 2 s | Kapıdan geçen 23 bileşimde kişi (gövde merkezi) %78–98 kadrajda, en uzun kadraj dışı 0.4–3.2 s | Yakın: kişiyi izleyen ayarlarda kadraj davranışı rapordakine benziyor |
| Kişinin boyu: 8/8 ≈ 195 px, 10/10 ≈ 155, 15/12 ≈ 115, 30° 4/8 ≈ 310 | 215 / 168 / ≈ 108 / ≈ 355 px (baş–ayak, ortanca) | Yeni simde kamera gerçek montaj yerinde ve kişi 1.75 m'lik insan modeli; birkaç santimlik yer farkı ve kutu / insan farkı |
| Alçak uçuşta en iyi sonuç 30° (12/12) | Alçakta (4–7 m) model iyi buluyor (%70–88) ama köşede dron kişinin üstüne geliyor; yalnız merkez mesafesi uzun olan 30° 6/10.4, 30° 7/12.1, 35° 7/10 kapıdan geçti | 30°'nin artısı korunuyor ama 8 m geride değil, kişiyi görüntünün ortasında tutan uzun mesafede (d ≈ 1.7 h) |
| 45° seçimi: konum doğruluğu, ufuk, güvenli yükseklik | Geometri değişmedi (bölüm 8 ve 10); sim zemini düz ve GPS yüksekliği kusursuz olduğu için konum farkını ölçemiyor (kapıdan geçenlerde modelin konum hatası ort. 30°'de 0.54 m, 35° 0.46, 40° 0.38, 45° 0.47 m: eğimden çok mesafeyle büyüyor; gerçekte zemin eğimi ve GPS yüksekliği hatası 30°'de 1.7 kat büyür) | Raporun 45° gerekçeleri sim dışı etkenlere dayanıyor; bu tarama onları ne doğruladı ne çürüttü |

**Özet:** Raporun geometrisi (yer şeridi, ufuk, konum duyarlılığı) yeni simde de aynı. Değişen iki şey var: (1) **model
küçük kişiyi bulamıyor**, bu yüzden 45°'nin "yükseğe çık, aynı montaj" artısı 12 m'nin üstünde geçersiz; (2) **köşede
stok Follow Me ≈ 6 m yaklaşıyor**, bu yüzden 8 m geride durma (raporun bütün eğimler için "en alçak başarılı ayar"ı) bu
yolda yetmiyor. İkisi birlikte, takip için gereken mesafeyi alçakta veren düşük eğimleri öne çıkarıyor.

## 8. Kullanıcının sorusu: "30°'de dron daha uzaktan takip ettiği için, yaklaşınca kadrajdan kaçırma sorunu artıya dönebilir mi?"

**Kısa cevap: evet, ama artıyı açının kendisi değil, aynı yükseklikte daha uzakta durabilmek veriyor.** Kişiyi
kaçırmayı belirleyen, köşede dronun yaklaştığı miktar ile **yaklaşma payı** (kişi ile kameranın yakın görüş sınırı
arası) arasındaki fark; yaklaşma ≈ 6 m'lik **mutlak** bir mesafe, pay ise geride durma mesafesiyle (d) büyüyor. 30°
aynı yükseklikte dronu 1.73 kat uzağa koyduğu için payı büyütüyor; aynı d'de ise açı payı değiştirmiyor. Piksel boyu
kaybı belirlemiyor.

**1. Geometri (düz uçuş, simdeki CM3: düşey ±20.07°, yatay ±33°; `tarama.margins`, testli).** Kullanıcının ön hesabı
doğru: yaklaşma payı 45° 8/8 4.3 m, 45° 10/10 5.4, 30° 4/8 4.7, 30° 6/10.4 5.4, 30° 8/13.9 7.2; kişinin mesafesindeki
yatay görüş genişliği 14.7, 18.4, 11.6, 15.6, 20.8 m (kameranın base_link'in 0.151 m önünde ve yerden h + 0.19 m
yüksekte olduğu hesaba katılınca paylar ≈ 0.3 m küçük: 4.0, 5.1, 4.3, 5.1, 6.9 m; genişlikler aynı).

| Ayar | Yakın sınır [m] | Uzak sınır [m] | Yaklaşma payı [m] | Geri kalma payı [m] | Genişlik [m] | Eğik mesafe [m] | Bakış [°] |
|---|---|---|---|---|---|---|---|
| 45° 8/8 | 4.0 | 17.8 | 4.0 | 9.8 | 14.7 | 10.7 | 42.9 |
| 45° 10/10 | 4.9 | 22.1 | 5.1 | 12.1 | 18.4 | 13.5 | 43.3 |
| 30° 4/8 | 3.7 | 24.1 | 4.3 | 16.1 | 11.6 | 8.5 | 22.8 |
| 30° 6/10.4 | 5.3 | 35.5 | 5.1 | 25.1 | 15.5 | 11.5 | 27.3 |
| 30° 8/13.9 | 7.0 | 46.9 | 6.9 | 33.0 | 20.8 | 15.6 | 27.9 |

Kişi görüntünün ortasındaysa (d = h / tan eğim) pay ≈ d · (1 − tan eğim / tan(eğim + 20.07°)): 30°'de 0.517 d, 35°'de
0.511 d, 40°'ta 0.517 d, 45°'de 0.535 d. **Aynı d'de dört eğimin payı neredeyse aynı**; fark, aynı d için gereken
yükseklikte: d = 9.1 m için 30°'de h = 5.3 m, 35°'de 6.4, 40°'ta 7.6, 45°'de 9.1 m. Eğik mesafe d / cos(eğim): 30°'de
1.15 d, 45°'de 1.41 d (aynı d'de kişi 30°'de ≈ %18 daha yakın, yani daha büyük görünür).

**2. Köşede dron kaç metre yaklaşıyor ve bu mesafeyle ölçekleniyor mu? (ölçüldü)** Kişi 3 m/s koşudan sonra 90°
dönüyor; köşeye kadar izlenen 76 model koşusunda (aşama 1 + aşama 2 + 9. grup) dronun `FLW_TGT_DST`'ye göre yaklaşması:

- d ≥ 7 m (70 koşu): **ort. 6.2 m (sd 1.2; %10–90: 4.6–7.6 m)**, d ile doğrusal eğim −0.10 ± 0.06 m/m, R² 0.05:
  **mutlak bir metre, mesafeyle ölçeklenmiyor.** 9. grupta 8/8'de ölçülen ≈ 6–7.5 m'lik yaklaşma ve ULog
  ayrıştırmasındaki ≈ 6–7 m'lik aşma (PX4'ün süzülmüş hedefi + öngörü + dronun ataleti) bununla aynı.
- d < 7 m'de yaklaşma daha küçük (2–4 m) çünkü dron kişiden daha fazla yaklaşamıyor (üstüne geliyor).
- Kişi aniden durunca: ort. 2.3 m (87 koşu; d ile zayıf eğim −0.20 m/m), çoğunlukla zararsız.
- Bu yaklaşma **stok Follow Me'nin** davranışıdır (spec "PX4 stok Follow Target davranışı" 6); m15 en az mesafe
  koruması getirirse küçülür, ama geometri (pay) aynı kalır.

**3. Kişiyi kaçırmayı ne belirliyor? (ölçüldü)** Aşama 1, aşama 2 ve 9. grubun model koşularında köşeden sonra
kaybedilen 28 koşu ile sonuna kadar izlenen 48 koşu, tek tek etkenlerle ne kadar ayrılıyor (AUC: 0.5 ayırmaz, 1.0 tam ayırır;
`yaklasma_analizi.json`):

| Etken | AUC |
|---|---|
| Kişinin kadrajın **altından** çıktığı süre (büyük = kayıp) | **0.97** |
| Geride durma mesafesi d (küçük = kayıp) | **0.93** |
| Kişinin mesafesinde yatay görüş genişliği (küçük = kayıp; d ile birlikte büyür) | **0.92** |
| Köşe yaklaşması − yaklaşma payı (pay aşımı; büyük = kayıp) | 0.88 |
| Yaklaşma payı (küçük = kayıp) | 0.83 |
| Kişinin kadrajın yanından çıktığı süre | 0.77 |
| Pay aşımı, dronun anlık burun açısıyla | 0.73 |
| **Kişinin piksel boyu (küçük = kayıp)** | **0.14** (ters: kaybedilenler daha büyük görünüyordu, çünkü daha yakındılar) |

- **30–40°'de d ≥ 9 m olan 32 koşunun 32'si köşeden sonra da izlendi;** 30–40°'de kaybedilen en uzak ayar d = 8.7 m.
  45°'de d ≥ 9 m'de 14 koşunun 12'si izlendi; iki kayıp (10/10 ve 12/12'de birer) ikisi de hem köşe yaklaşmasının
  ortalamanın üstünde olduğu (7.0 / 8.6 m) hem de modelin kişiyi zayıf bulduğu (%47 / %13) koşular: 45°'de aynı d için
  dron yüksekte, kişi küçük, kadraja geri dönünce model onu geç buluyor.
- Kaybedilen koşularda kişi kadrajın altında ort. 5.3 s, yanında 4.2 s, üstünde 1.3 s kaldı; izlenenlerde 1.1 / 0.4 /
  0.8 s. Kaçış önce **alttan** (dron kişinin üstüne geliyor, ayaklar yakın sınırın içinde), sonra **yandan** (dron
  aşınca kişi görüntünün kenarına kayıyor). Kısa süre yakın sınırın içine girip (pay aşımı 0–3 m) kişiyi tutan
  koşular da var: kısa bir dalış affediliyor, derin ya da uzun olanı değil (`gorev10on_yaklasma_payi.png`).
- Yaklaşma payı (0.83) d'den (0.93) biraz daha az ayırıyor: aynı d'de yüksek uçan dronun yakın sınırı büyük ama
  kişinin gövdesi ve başı (yerden 0.9 / 1.75 m) daha uzun süre görüntüde kalıyor; pay ayak noktasının ölçüsüdür.

**4. Sonuç: düşük açının artısı ve eksisi, sayılarla.**

| | 30° (aynı yükseklikte) | 45° |
|---|---|---|
| Köşe kaybından korunmak için gereken d (ölçülen eşik ≈ 9 m) | h ≥ 5.3 m | h ≥ 9.1 m |
| O yükseklikte kişinin boyu / modelin bulma oranı (aşama 1) | 6 m'de ≈ 280 px, %75 | 10 m'de ≈ 160 px, %39 |
| Yaklaşma payı (merkez) | 0.52 d | 0.53 d |
| Aynı h'de d / pay | 1.73 h / ≈ 0.89 h | 1.0 h / ≈ 0.53 h |
| Ufuk payı (burnun ne kadar kalkınca ufuk kadraja girer) | **9.9°** (frende 6–11° kalkıyor) | 24.9° |
| Zemin 1 m yüksek / GPS yüksekliği 1 m yanlışsa konum kayması | **1.73 m** | 1.0 m |
| Başların üstünde (d = 9.1 için) | 3.6 m | 7.4 m |

- **Artı (ölçüldü):** 30–35°, köşedeki ≈ 6 m'lik mutlak yaklaşmayı karşılayacak d'yi alçakta veriyor; alçakta kişi
  büyük, model %70–80 buluyor. 45°'de aynı d için 9–12 m'ye çıkmak gerekiyor ve orada model kişiyi %40'ın altında
  buluyor (12 m'de %9). Yani 30°'nin "uzaktan takip" artısı gerçek, ama **mekanizması açı değil yükseklik–mesafe
  oranı**.
- **Eksi (ölçülmedi, geometri):** ufuk 30°'de çok yakın (sert frende, rüzgârda gökyüzü kadraja girer, otomatik pozlama
  kişiyi karartır); konum hesabı zemine ve GPS yüksekliğine 1.7 kat duyarlı; aynı d'de dron başlara daha yakın;
  dronla kişi arasında daha uzun, açık bir görüş hattı ve daha büyük boş alan gerekir. Aşama 2'nin sonuçları ve
  öneri bölüm 6'da.

## 9. Kullanıcının ek isteği: "Model hangi koşullarda iyi algılıyor?"

**Veri:** taramanın bütün koşuları (aşama 1, aşama 2, mükemmel algılayıcı ve kıvrımlı yol koşuları; model hepsinde
çalışıyor) ve kalabalık park koşuları (9. grubun 3'ü ve iş A'nınki). Her işlenmiş model karesinde, hakem kutusu
görünür (≥ 40 px) olan **her kişi** için (hedef ve kalabalıktaki diğer kişiler) "bulundu" = hakem kutusuyla IoU ≥ 0.5
olan bir model kutusu var mı (ölçüt `algilama_orani` ile aynı kural) ve bulunan kutunun güveni. Her kişi-kareye o anın
koşulları yazıldı: kişinin piksel boyu (baş–ayak izdüşümü), eğik mesafe, bakış açısı, kutunun görüntüdeki yeri ve
kenarda kesik olup olmadığı, kişinin hızı (duruyor < 0.1 / yürüyor < 2 / koşuyor m/s), kameraya dönüklüğü (yürüyüş
yönüne göre önden / yandan / arkadan), örtülme (hakem kutusu boyu / beklenen boy: açık ≥ 0.85, kısmi ≥ 0.4, çoğu gizli),
yakında başka kişi (hakem kutuları örtüşüyor), dronun |pitch|'i ve dönme hızı, dünya, kamera eğimi. Repo dışı betik
`algilama_kosullari.py`; veri `tez/sim/sonuclar/gorev10on_tarama/algilama_kareleri.csv.gz`, sonuç `algilama_kosullari.json`.

**Yöntem ve sınırı:** tek tek oranlar (koşu kümelerinin std'siyle) ve çok değişkenli lojistik model (numpy IRLS; bütün
etkenler birlikte; ayrıca yalnız tarama koşularıyla, kalabalık parkın karıştırıcı etkisi olmadan). **Bunlar ilişkidir,
nedensellik değil:** etkenler birbirine bağlı (eğik mesafe ile piksel boyu r = -0.77; kalabalık park hep 45° ve 10 m
hover, önden görünüş çoğunlukla orada; dronun dönmesi takip başındaki yörünge dönüşünde, kişi dururken). Ardışık kareler
bağımsız değil: %95 aralıklar gerçekte daha geniştir; koşular arası std tek tek oranlarda gösterildi.

Veri: 103897 kişi-kare, 133 koşu; genel bulma oranı %53. Korelasyon: eğik mesafe–piksel boyu r = -0.77, bakış açısı–piksel boyu r = -0.07.

**Tek tek (ham oranlar; etkenler birbirine karışır):**

| Koşul | Sınıf: bulma oranı % (kişi-kare, koşu) |
|---|---|
| Kişinin piksel boyu (baş–ayak) [px] | (0, 60]: **0** (1, 1); (60, 90]: **0** (2395, 14); (90, 120]: **3** (10256, 38); (120, 150]: **25** (13477, 51); (150, 180]: **61** (26284, 65); (180, 210]: **57** (12277, 66); (210, 250]: **67** (21379, 60); (250, 300]: **77** (9352, 63); (300, 2000]: **79** (8476, 37) |
| Eğik mesafe [m] | (0, 8]: **88** (5490, 43); (8, 10]: **73** (11218, 70); (10, 12]: **71** (22327, 90); (12, 14]: **52** (21499, 86); (14, 17]: **47** (17171, 61); (17, 20]: **46** (8902, 37); (20, 25]: **30** (9279, 28); (25, 30]: **0** (3921, 20); (30, 60]: **0** (4090, 17) |
| Bakış açısı (ufkun altında) [°] | (0, 20]: **5** (1167, 12); (20, 25]: **31** (6791, 48); (25, 30]: **60** (20515, 82); (30, 35]: **56** (26172, 102); (35, 40]: **54** (16064, 118); (40, 45]: **48** (20138, 120); (45, 50]: **56** (5887, 113); (50, 55]: **68** (5096, 94); (55, 90]: **32** (2067, 63) |
| Kişinin hareketi | duruyor: **55** (71468, 133); yürüyor: **50** (28550, 133); koşuyor: **37** (3879, 128) |
| Kameraya göre dönüklük | arkadan: **69** (30310, 133); yandan: **39** (62192, 133); önden: **84** (11395, 85) |
| Örtülme | açık: **54** (99357, 133); kısmi: **45** (2863, 125); çoğu gizli: **6** (1677, 120) |
| Yakında başka kişi (kutular örtüşüyor) | kutular örtüşüyor: **62** (385, 4); yalnız: **53** (103512, 133) |
| Görüntü kenarında kesik | kenarda kesik: **41** (6565, 125); tamamı kadrajda: **54** (97332, 133) |
| Görüntüde düşey yer | üst: **54** (35326, 132); orta: **49** (56684, 133); alt: **66** (11887, 125) |
| Görüntüde yatay yer | sol: **57** (11377, 123); orta: **53** (83349, 133); sağ: **44** (9171, 125) |
| Dronun |pitch|'i | < 3°: **48** (76405, 133); 3–7°: **67** (12284, 121); 7–12°: **69** (8196, 121); > 12°: **58** (7012, 121) |
| Dronun dönmesi | dron dönüyor (> 15°/s): **67** (18216, 121); dönmüyor: **50** (85681, 133) |
| Dünya | cayir: **91** (12467, 4); duz_alan: **48** (91430, 129) |
| Kamera eğimi | 30.0: **54** (21319, 29); 35.0: **53** (28563, 39); 40.0: **41** (17807, 26); 45.0: **57** (36208, 39) |
| Kim | aynı kıyafetli: **99** (3019, 4); diğer kişi: **88** (6494, 4); hedef: **49** (94384, 133) |

**Çok değişkenli lojistik model, bütün koşular** (n = 103897, açıklanan sapma payı %42):

| Etken (karşılaştırılan) | Olasılık oranı | %95 aralık (kareler bağımsız sayılarak) |
|---|---|---|
| boy < 120 px (150–180 px'e göre) | 0.01 | 0.01–0.01 |
| boy 120–150 px (150–180 px'e göre) | 0.37 | 0.35–0.40 |
| boy 180–210 px (150–180 px'e göre) | 2.52 | 2.37–2.68 |
| boy 210–250 px (150–180 px'e göre) | 4.35 | 4.12–4.59 |
| boy > 250 px (150–180 px'e göre) | 11.80 | 11.07–12.57 |
| bakış açısı +1 sd | 1.10 | 1.07–1.13 |
| görüntü merkezinden uzaklık +1 sd | 0.78 | 0.76–0.81 |
| dronun |pitch|'i +1 sd | 1.34 | 1.30–1.38 |
| kenarda kesik | 0.41 | 0.37–0.47 |
| kısmi örtülü (açık'e göre) | 0.15 | 0.13–0.18 |
| çoğu gizli (açık'e göre) | 0.01 | 0.00–0.01 |
| yürüyor (duruyor'e göre) | 0.71 | 0.68–0.74 |
| koşuyor (duruyor'e göre) | 0.95 | 0.87–1.05 |
| önden görünüyor (arkadan'e göre) | 2.02 | 1.78–2.28 |
| yandan görünüyor (arkadan'e göre) | 0.10 | 0.09–0.10 |
| kutusu başka bir kişininkiyle örtüşüyor | 0.08 | 0.06–0.10 |
| dron dönüyor (> 15°/s) | 1.65 | 1.55–1.77 |
| çayır / kalabalık park (düz alan (tarama)'e göre) | 9.26 | 8.25–10.38 |
| kamera 30° (45°'e göre) | 1.64 | 1.53–1.75 |
| kamera 35° (45°'e göre) | 1.09 | 1.03–1.15 |
| kamera 40° (45°'e göre) | 0.88 | 0.84–0.93 |

Etkenlerin ağırlığı (modelden çıkarınca artan sapma; diğerleri varken açıkladığı): kişinin piksel boyu (sınıf) 35431; dönüklük (önden / yandan) 10943; örtülme (kısmi / çoğu gizli) 2768; dünya: çayır (kalabalık park senaryosu) 1625; dronun eğikliği |pitch| 417; kamera eğimi (30/35/40, 45'e göre) 392; yakında başka kişi 340; görüntüde merkezden uzaklık 296; hareket (yürüyor / koşuyor) 248; dronun dönmesi 229; kenarda kesik 199; bakış açısı (aşağı) 48.

**Çok değişkenli lojistik model, yalnız tarama koşuları (düz alan, hedef)** (n = 91430, açıklanan sapma payı %39):

| Etken (karşılaştırılan) | Olasılık oranı | %95 aralık (kareler bağımsız sayılarak) |
|---|---|---|
| boy < 120 px (150–180 px'e göre) | 0.01 | 0.01–0.01 |
| boy 120–150 px (150–180 px'e göre) | 0.36 | 0.33–0.38 |
| boy 180–210 px (150–180 px'e göre) | 2.44 | 2.30–2.60 |
| boy 210–250 px (150–180 px'e göre) | 4.24 | 4.02–4.47 |
| boy > 250 px (150–180 px'e göre) | 11.38 | 10.68–12.13 |
| bakış açısı +1 sd | 1.09 | 1.06–1.12 |
| görüntü merkezinden uzaklık +1 sd | 0.80 | 0.78–0.82 |
| dronun |pitch|'i +1 sd | 1.32 | 1.28–1.36 |
| kenarda kesik | 0.41 | 0.36–0.47 |
| kısmi örtülü (açık'e göre) | 0.17 | 0.15–0.20 |
| çoğu gizli (açık'e göre) | 0.01 | 0.00–0.01 |
| yürüyor (duruyor'e göre) | 0.86 | 0.82–0.90 |
| koşuyor (duruyor'e göre) | 0.96 | 0.86–1.06 |
| önden görünüyor (arkadan'e göre) | 0.59 | 0.49–0.69 |
| yandan görünüyor (arkadan'e göre) | 0.09 | 0.09–0.10 |
| dron dönüyor (> 15°/s) | 1.64 | 1.54–1.75 |
| kamera 30° (45°'e göre) | 1.64 | 1.53–1.75 |
| kamera 35° (45°'e göre) | 1.09 | 1.03–1.15 |
| kamera 40° (45°'e göre) | 0.89 | 0.85–0.95 |

Etkenlerin ağırlığı (modelden çıkarınca artan sapma; diğerleri varken açıkladığı): kişinin piksel boyu (sınıf) 34114; dönüklük (önden / yandan) 9832; örtülme (kısmi / çoğu gizli) 2401; kamera eğimi (30/35/40, 45'e göre) 368; dronun eğikliği |pitch| 354; görüntüde merkezden uzaklık 262; dronun dönmesi 221; kenarda kesik 183; hareket (yürüyor / koşuyor) 44; bakış açısı (aşağı) 34.

**Aynı piksel boyunda eğim (yalnız tarama, hedef; bulma % (kişi-kare)):**

| Boy [px] | 30° | 35° | 40° | 45° |
|---|---|---|---|---|
| (0, 60] | – | – | – | – |
| (60, 90] | 0 (1452) | 0 (727) | 0 (170) | 7 (46) |
| (90, 120] | 1 (2924) | 1 (2436) | 3 (2121) | 6 (2775) |
| (120, 150] | 20 (1712) | 17 (1846) | 21 (4520) | 19 (4263) |
| (150, 180] | 43 (1738) | 33 (2481) | 32 (2664) | 40 (8070) |
| (180, 210] | 61 (1667) | 58 (7861) | 46 (1280) | 52 (1469) |
| (210, 250] | 76 (6598) | 69 (9143) | 61 (1599) | 52 (4039) |
| (250, 300] | 84 (3444) | 74 (1486) | 71 (3025) | 72 (1397) |
| (300, 2000] | 83 (1784) | 78 (2583) | 74 (2428) | 82 (1681) |

**Okuma (son veriyle):**

1. **Piksel boyu açık ara baskın etken** (lojistik modelde açıkladığı sapma diğer bütün etkenlerin toplamından büyük).
   Kişinin baş–ayak boyu 150–180 px aralığında bulma %61; 120–150 px'te %25, 90–120 px'te %3,
   90 px'in altında %0. 640 piksellik girişte bu, kişinin modele ≈ 33–42 px'ten küçük girmesi demek. 250 px'in üstünde
   %77 ve daha yukarı. Eğik mesafe piksel boyuyla aynı bilgiyi taşıyor (r = -0.77); 25 m'nin ötesinde bulma
   %0. Bu, taramadaki "12 m ve üstünde model kişiyi bulamıyor" sonucunun nedeni.
2. **Kameraya dönüklük ikinci etken:** kişi kameraya **yandan** görünürken (yürüme yönü bakış doğrultusuna dik) bulma
   belirgin düşük (olasılık oranı arkadan görünüşe göre 0.10 (0.09–0.10), yalnız taramada 0.09 (0.09–0.10)). Taramada yandan görünüş
   çoğunlukla takip başındaki yörünge dönüşünde ve köşede (dron kişinin yanına geçince) oluyor; bu anlar dronun
   dönmesi, kişinin kenarda olması ve durmasıyla iç içe. **Önden** görünüş kalabalık parkta çok iyi (%84 ham), ama
   taramada arkadan görünüşten iyi değil (0.59 (0.49–0.69)): ilişki tutarsız, bu yüzden "önden iyi" denemez.
3. **Örtülme:** kısmi örtülü kişide olasılık oranı 0.15 (0.13–0.18), çoğu gizlide 0.01 (0.00–0.01) (ağaç arkası; hakem kutusu yalnız
   görünen pikselleri kapsadığı için IoU ≥ 0.5'i tutturmak da zorlaşıyor).
4. **Yakında başka kişi (kutu birleşmesi):** kalabalıkta iki kişinin hakem kutuları örtüştüğünde bulma olasılığı belirgin
   düşüyor (olasılık oranı 0.08 (0.06–0.10); ham oran yüksek görünüyor çünkü bu anlar yalnız kalabalık parkta ve orada kişiler
   büyük ve yakın). Model iki kişiyi tek kutuda birleştiriyor ya da kutuyu kaydırıyor; `yanlis_kisi_orani`'ndaki
   karışmalar da bu anlarda (iş A'nın koşusunda 80.6–83.2 s).
5. **Görüntüdeki yer:** kenarda kesik kişide olasılık oranı 0.41 (0.37–0.47); merkezden uzaklaştıkça hafif düşüş (0.78 (0.76–0.81)/sd).
6. **Hareket:** yürüyen ve koşan kişi, piksel boyu ve diğerleri hesaba katılınca duran kişiden çok farklı değil
   (taramada yürüyor 0.86 (0.82–0.90), koşuyor 0.96 (0.86–1.06)). Simde hareket bulanıklığı yok: gerçek kamerada koşan kişi ve dönen
   dronda bu farklı olabilir.
7. **Dronun eğikliği ve dönmesi:** ikisi de olasılık oranında > 1 çıkıyor (1.34 (1.30–1.38)/sd, 1.65 (1.55–1.77)); bu bir neden
   olarak okunmamalı: dronun eğildiği ve döndüğü anlar takip başındaki yörünge dönüşü ve köşeler, kişinin konumu ve
   görünüşü bu anlarda farklı (karıştırıcı). Simde bulanıklık olmadığı için dronun hareketinin görüntüye zararı da
   ölçülemiyor.
8. **Kamera eğimi, aynı piksel boyunda:** yalnız tarama koşularında, aynı boy aralığında 30° 45°'ten belirgin iyi
   (180–300 px'te 30° %61–84, 45° %52–72; tablo); lojistik modelde (boy, dönüklük, örtülme, yer … sabitken)
   45°'e göre 30° 1.64 (1.53–1.75), 35° 1.09 (1.03–1.15), 40° 0.89 (0.85–0.95). Düşük eğimin algılamaya iki katkısı var: aynı mesafede kişiyi
   daha yakından göstermesi (eğik mesafe d / cos eğim → daha büyük piksel boyu) ve 30°'de aynı boyda da daha iyi
   bulması (kişi daha yandan görünüyor, gövdesi görüntüde daha uzun; v0.2'nin eğitim verisi muhtemelen çoğunlukla yere
   yakın çekilmiş fotoğraflar, Ortatepe'nin teyidi bekleniyor). 35–40°'ta ikinci katkı küçük ya da yok.
9. **Dünya / kişi:** kalabalık parktaki (çayır) kişiler ham oranda çok daha iyi bulunuyor (%91; düz alan %48)
   ama bu, kişilerin orada yakın (7–17 m) ve büyük olmasından; model düzeltilince de büyük bir pay kalıyor (9.26 (8.25–10.38)),
   arka plan (çim + patika) mı, yoksa senaryonun başka bir farkı mı, ayırt edilemiyor.

**Simin ölçemediği koşullar ("ölçülemedi"):** ışık ve gölge (Gazebo'da tek, sabit güneş; gün saati, bulut, ters ışık
yok), hareket bulanıklığı ve rolling shutter (Faz B, Görev Grubu 15), kamera gürültüsü (SDF'teki gürültü ≈ 1/5 uygulanıyor,
etkisiz), otomatik pozlama (gökyüzü kadraja girince yerin kararması), lens bozulması (ideal iğne delik), **kıyafet ve
insan çeşitliliği** (tek actor modeli: aynı beden, kel, yalınayak; yalnız kıyafet rengi değişiyor), poz çeşitliliği
(yalnız yürüme / koşma / durma animasyonu; eğilen, oturan, kol sallayan yok), arka plan çeşitliliği (iki dünya: tek renk
düz alan ve çayır), hava (yağmur, toz), Hailo'nun nicemlemesi ve giriş boyutu. Bu sonuçlar bu koşulların hiçbirini
kapsamaz.

**Ortatepe (m08 / m10) için veri toplama ve eğitim önerileri** (öneri; karar ve yöntem Ortatepe'nin):

1. **Küçük kişi en büyük açık.** v0.2 kişi 150 px'in altına inince hızla kaçırıyor (640 girişte ≈ 40 px). Uçuşta
   toplanacak veri setine bilerek uzak / yüksek kareler girsin: dron 8–15 m yükseklikte, kişi 10–25 m eğik mesafede,
   görüntüde 60–200 px. Etiketleme kuralında (m27) "çok küçük kişi" etiketlensin, atılmasın.
2. **Giriş boyutu:** aynı kareler `imgsz` 1280'de kaçırılan kişileri buluyordu ama CPU'da 4–8 kat yavaş (3. grup gözlemi,
   spec "`imgsz` seçimi"). Hailo'da (m07/m08) 640'tan büyük giriş ya da kişinin çevresini kırpıp (ROI / tile) ikinci kez
   çalıştırmak, FPS bedeliyle birlikte ölçülsün. Takipte kişinin yeri bilindiği için kırpma doğal bir seçenek.
3. **Eğik açı ve yandan görünüş:** eğitim verisinin çoğu yere paralel çekilmiş fotoğrafsa (COCO benzeri), 25–45° aşağı
   bakan kameradan, özellikle kişinin **yandan** göründüğü kareler (dron kişinin yanına geçtiğinde, köşelerde) eklensin.
   Ortatepe'nin veri setinde eğik / üstten görüntü olup olmadığı hâlâ bilinmiyor (spec "Açık Konular").
4. **Kalabalık ve örtülme:** yan yana yürüyen, birbirini kısmen örten kişiler ve ağaç / direk arkasında kısmen görünen
   kişi örnekleri; NMS'in IoU eşiği (eğitimde 0.7) birleşen kutular için ayrıca denensin. m11'in hedef seçimi için de
   aynı anlar kritik (iş A'nın videosunda 0:56–0:59).
5. **Görüntü kenarı:** kenarda kesik kişiler (kutu kenara değiyor) daha az bulunuyor; kenarda kesik örnekler eklensin
   ve etiketleme kuralı kesik kişiyi nasıl kutulayacağını söylesin.
6. **Simin veremedikleri gerçek uçuşta toplanmalı:** farklı ışık (sabah / öğle / akşam, gölge, ters ışık), hareket
   bulanıklığı (koşan kişi, dönen dron), otomatik pozlama (gökyüzü kadrajdayken), farklı kıyafet, beden, saç, şapka,
   çanta, bisiklet / scooter ile hareket eden kişi, çim / beton / toprak zemin. Simdeki tek actor bunların hiçbirini
   temsil etmiyor.
7. **Güven eşiği:** bulunan kutuların güveni küçük kişide düşük (120 px'in altında ortanca 0.45–0.47, üstünde
   0.69–0.80; `gorev10on_algilama_kosullari_guven.png`); `conf` 0.25 varsayılanı küçük kişide sınırda. Eşik, gerçek uçuş verisinde precision–recall eğrisiyle seçilsin (simdeki yanlış
   pozitif kare başına ≈ 0 olduğu için sim burada yol gösteremez).
8. **Ölçüm:** bu analizin betiği (`algilama_kosullari.py`) Vision'ın modeli takıldığında aynı koşullarla yeniden
   çalıştırılabilir (sim koşu klasörlerini okur); v0.2 ile karşılaştırma tabanı bu bölümdeki tablolardır.

## 10. Gerçeklik: simin söylemediği şeyler (öneriyi okurken)

**Eğimi değiştirmek bir yazılım ayarı değil, montaj parçasıdır.** Simde `--kamera-egim 30` modelin bir kopyasını
döndürür; gerçek araçta X500 V2'nin "Depth Camera Mount" yerindeki tutucunun (CM3 kartının oturduğu parça) başka bir
açıyla yeniden yapılması ya da ayarlanabilir bir tutucu demektir. Ayarlanabilir tutucu titreşimle kayabilir; sabit
parça her açı için ayrı basılır. Hangi açıda olursa olsun **açı araçta ölçülüp yazılıma girilmelidir** (kamera raporu:
1°'lik montaj hatası 8 m'de ≈ 0.3 m konum hatası; simde montaj tam bilinir). Bu iş (13.11) varsayılanı değiştirmedi; 14.11'de bölüm 20 değiştirdi. 13.11'de: model
dosyası, `takip_yuruyen` ve gerçek montaj 45°'de kalır; öneri kullanıcının ve ekibin kararıdır.

**Kamera:** simdeki kamera CM3 Standard'ın veri sayfası değerleridir (66° yatay; 16:9'dan düşey 40.1°, veri sayfasında
41°), bozulmasız ideal iğne delik. Gerçek lensin odak uzaklığı veri sayfasında %5 belirsiz (m09 kalibrasyonu);
düşey yarı açı 1° farklı çıkarsa yakın sınır ve "yaklaşma payı" 45° / 10 m'de ≈ 0.2 m, 30° / 8 m'de ≈ 0.25 m kayar. Simde
gürültü, hareket bulanıklığı, rolling shutter ve otomatik pozlama yok (Faz B, Görev Grubu 15): düşük eğimde ufuk
kadraja daha çabuk girer (ufuk payı 30°'de 9.9°, 45°'de 24.9°) ve parlak gökyüzü gerçek kamerada yerdeki kişiyi
karartır; sim bunu ölçemez.

**Model:** v0.2 laptop CPU'sunda, Gazebo'nun tek insan modelinde (aynı beden, kel, yalınayak; kıyafet rengi değişir)
çalıştı. Hailo'ya dönüştürülmüş model (m07/m08) farklı `imgsz`, nicemleme ve eşikle başka bir bulma oranı verir;
"hangi koşulda iyi algılıyor" bölümündeki eğilimler (yandan görünüş, örtülme, piksel boyu) yön gösterir, sayılar
Hailo'ya taşınmaz.

**Rüzgâr ve dronun eğilmesi:** simde rüzgâr yok. Gerçekte dron rüzgâra karşı burnunu eğer ve kamera da onunla döner:
düşük eğimde ufuk payı küçük olduğu için sert frende ya da rüzgârda kişi görüntünün üstüne, ufuk görüntünün içine
kayar; yüksek eğimde aynı açı kişiyi görüntünün altına iter ve yaklaşma payını yer. Ağustos uçuşlarında burun
çoğunlukla 11–18°, en çok 26° eğildi (kamera raporu).

**Konum hesabı (zemin düz kabul edilir):** kampüsteki çim alan %3–7 eğimli ve yükseklik GPS'ten tutuluyor
(`EKF2_HGT_REF 1`, GPS yükseklik hatası yarım metreyi bulur). İkisi de konumu `d / h` katıyla kaydırır: 45°'de ≈ 1,
30°'de ≈ 1.7 (geometri grubundaki "zemin duyarlılığı"). Simde zemin düz ve dronun yüksekliği kusursuz; bu fark
sim sonuçlarında görünmez, geometri grubuna bu yüzden konuldu.

**Yükseklik kuralları ve alan:** insanların yakınında ve üstünde uçuşla ilgili sınırlar için **SHGM kurallarına
bakılmalı** (bu belge yasal bir sayı vermez); kampüste uçuş izni ve alanın sınırları ayrıca belirlenir. Düşük eğim
aynı yükseklikte dronu kişinin daha gerisine koyar (30°'de `d ≈ 1.7 h`: 8 m'de 13.9 m, 15 m'de 26 m): alan daha
büyük ve dronla kişi arasındaki görüş hattı ağaç, direk, bina gibi engellerden daha uzun süre açık olmalı;
Wi-Fi / telemetri menzili de uzar.

**Aday ayarların sahadaki karşılığı** (düz uçuş; `tarama.margins` / `geometry`):

| Ayar | Dron kişinin gerisinde [m] | Kamera yerde görür (dronun önünde) [m] | Dron–kişi görüş hattı [m] | Başların üstünde [m] | Ufuk payı [°] | Zemin / GPS yüksekliği 1 m hatalıysa konum kayması [m] |
|---|---|---|---|---|---|---|
| 45° · 8 m / 8 m | 8 | 4.0–18 | 10.7 | 6.25 | 24.9 | 1.00 |
| 45° · 10 m / 10 m | 10 | 4.9–22 | 13.5 | 8.25 | 24.9 | 1.00 |
| 45° · 12 m / 12 m | 12 | 5.8–26 | 16.4 | 10.25 | 24.9 | 1.00 |
| 40° · 12 m / 11.4 m | 11.4 | 7.2–34 | 15.9 | 10.25 | 19.9 | 0.95 |
| 35° · 8 m / 11.4 m | 11.4 | 5.9–31 | 13.4 | 6.25 | 14.9 | 1.43 |
| 35° · 7 m / 10 m | 10 | 5.2–27 | 11.7 | 5.25 | 14.9 | 1.43 |
| 30° · 6 m / 10.4 m | 10.4 | 5.3–36 | 11.5 | 4.25 | 9.9 | 1.73 |
| 30° · 8 m / 13.9 m | 13.9 | 7.0–47 | 15.6 | 6.25 | 9.9 | 1.74 |

Kişinin yürüyeceği alanın her yönünde en az "dron kişinin gerisinde" kadar boş, engelsiz ve insansız pay gerekir (dron
kişinin arkasında; köşede yanına ve önüne geçebilir, 9. grup); stadın ya da çim alanın kenarına yakın yürüyüşte dron
alanın dışına taşar. Ufuk payı, burnun ne kadar kalkınca görüntünün üst kenarının ufka değdiğidir (Ağustos uçuşlarında
frende burun 6–11° kalktı).

**Stok Follow Me:** bütün sonuçlar PX4 v1.17.0'ın stok Follow Target'ıyla. Köşedeki yaklaşmanın büyüklüğü bu modun
süzgecinden ve öngörüsünden geliyor (9. grup); m15'in kendi modu en az mesafe koruması getirirse yaklaşma miktarı
değişir, ama kameranın yakın görüş sınırı ve yaklaşma payı aynı kalır.

### Düşük yüksekliğin (4–7 m) gerçek dünyadaki bedeli

- **PX4'ün önerdiği alt sınır 8 m:** `FLW_TGT_HT`'nin üst verisi `@min 8.0` (kod kısmıyor, bu taramada geri okuma ve
  ULog yüksekliğiyle uygulandığı doğrulandı); PX4'ün kendisi Follow Me için 8 m'nin altını önermiyor.
- **İnsanlara yakınlık:** 4 m'de dron başların ≈ 2.25 m üstündedir; bir hata, rüzgâr ya da GPS yükseklik kayması
  dronu kişinin boyuna indirebilir. İnsanların yakınında uçuş için SHGM kurallarına bakılmalı.
- **Engeller:** ağaçlar (çayırdaki ≈ 11 m), aydınlatma direkleri, bina saçakları; düşük bant bu yüzden yalnız
  ağaçsız `duz_alan`'da koşuldu.
- **Rotor rüzgârı ve gürültü:** alçakta kişinin üstüne inen hava akımı ve gürültü rahatsız eder; kum/yaprak kaldırır.
- **Yerde görülen alan küçülür:** yakın sınır ile uzak sınır yükseklikle orantılı olduğu için alçakta görüntünün
  kapladığı şerit kısalır ve daralır; kişi köşede ya da dron hızlanınca kadrajdan daha çabuk çıkar (sonuçlarda
  "yaklaşma payı" ve "genişlik" sütunları).
- **Kazanç:** kişi görüntüde büyür (piksel boyu), bakış daha yandan olur; model bunu her zaman daha iyi bulmuyor
  ("Model hangi koşullarda iyi algılıyor").

## 11. Testler ve doğrulama

Önce testler yazıldı (donanımsız, simsiz). B'nin testleri: `test_kamera_egimi.py` (8 test, parametreli 21 durum) ve
`test_tarama.py` (11 test); `test_hedef.py`'de `ayarlar.kamera`. Toplam: temiz HEAD 234 → iş A 238 → A + B **270**.

| Test | Ne sınanır |
|---|---|
| `test_a_known_pose_goes_pixel_to_ground_and_back_with_the_scenario_tilt` (30/35/40/45° × burun ±) | Bilinen poz → piksel (eğimli kamera) → kutu → düz zemin konumu < 1 cm; aynı kutu 45° varsayılarak hesaplansa metrelerce hata (eğimin gerçekten kullanıldığının kanıtı) |
| `test_the_near_and_far_ground_limits_follow_the_tilt` | `olcum.frame_limits(..., tilt)`: h / tan(eğim ± düşey FOV/2) + 0.151 m; varsayılan 45° |
| `test_tracker_sends_the_los_of_its_mount` | LOS (i) koşunun montajıyla (`Tracker(mount=...)`), 45°'yle değil |
| `test_the_scenario_tilt_is_checked_and_the_command_line_replaces_it` | `kamera.egim_deg` varsayılan 45 (`kamera.NOMINAL_TILT_DEG`), 0–60 dışı ve bilinmeyen alan reddi (alan adıyla), `--kamera-egim` senaryoyu ezer, `ayarlar.kamera` |
| `test_the_gazebo_model_of_a_run_has_the_scenario_tilt` | 45°'de dünya `models/x500_tez`'i olduğu gibi ekler; başka eğimde koşu klasörüne yalnız `camera_link` pitch'i değişmiş kopya yazılır ve dünya onu mutlak yoluyla ekler; asıl model dosyası değişmez ve 45°'dir |
| `test_the_tilt_gazebo_reports_is_read_back_from_the_mount` | `kamera.tilt_of_mount`: Gazebo'nun bildirdiği montajdan eğim (koşu sonunda senaryoyla ≤ 0.05° karşılaştırılır) |
| `test_a_model_without_the_expected_camera_pose_is_refused` | Model dosyasının pozu bulunamazsa eğimli kopya yapılmaz (koşu açılmadan hata) |
| `test_the_video_draws_the_near_limit_of_the_runs_tilt` | Video eğimi `ozet.json` → `ayarlar.kamera`'dan (komut satırı dahil), yoksa senaryo kopyasından alır |
| `test_tarama.py` (11) | Merkez mesafesi ve kadraj kontrolü; kullanıcının beş ayarının geometrisi (pay, genişlik; bölüm 8); plan (yineleme, atlananın nedeni); ikinci bant; **başka bir yolun aynı ayarları** (aşama 2'de bulunan hata, bölüm 12); kaydırılmış yol ve takip bloğu; yarıda kalan taramanın sürmesi; köşe / duruş yaklaşması ve kadrajdan çıkış kenarı; kayıp ve piksel boyu (hiç `FOLLOW_TARGET` gitmeyen koşu dahil); kapılar, puanlar, sıra; aşama 2 adayları |

**Uçtan uca eğim doğrulaması (aşama 1'in 81 koşusu):** Gazebo'nun koşu sonunda bildirdiği eğim senaryonunkiyle en çok
1.7·10⁻⁵° farklı (hiçbir koşuda "Kamera eğimi" olayı yok); LOS (i) ile hakemin LOS (ii)'si arasındaki açı ort. 30°'de
0.39°, 35°'de 0.40°, 40°'ta 0.27°, 45°'de 0.28° (takip tarafı 45° varsaysaydı ≈ 15° olurdu); model kutusunun gerçek
pozla konum payı 0.23–0.26 m, eğimden bağımsız. Yani Gazebo modeli, LOS, konum hesabı ve hakem aynı eğimle çalışıyor.

## 12. Karşılaşılan sorunlar

- **Önceki ajan durduruldu (aşama 1, 62/81):** `e35_h4_d5.7` yarıda kaldı; aynı `tarama.py kos` komutu `durum.json`'dan
  bitenleri atlayıp kaldığı yerden sürdü, yarım klasör `_yarim_153924` olarak ayrıldı ve özetlere girmedi.
- **Kapının uygulamasında hata (aşama 1 sürerken, aday seçiminden önce bulundu; önce test):** modelin kişiyi hiç
  bulamadığı koşularda (ör. 30° / 15 m / 26 m: kişi ≈ 80 px, model girişinde ≈ 23 px) hiç `FOLLOW_TARGET` gitmediği
  için `follow_target.csv` hiç açılmıyor (dosya ilk denemeyle açılır); "kişi sonda kaybedildi" NaN kalıyor ve kapıdan
  geçiyordu. Önceden yazılan kurala göre ("son giden FOLLOW_TARGET ile koşu sonu arası ≤ 3 s") bu koşular kaybedilmiş
  sayılır; kural değişmedi, uygulaması düzeldi (`test_tarama.py`, `tarama.run_numbers`).
- **`plan --ekle` başka bir yolu yineleme sayıyordu (aşama 2'den önce bulundu; önce test):** `kivrimli_yuruyus`
  bileşimini aynı eğim, yükseklik ve mesafedeki `takip_yuruyen` bileşiminin yinelemesi sayıp planlamazdı. Bileşimler
  artık `temel` alanını taşıyor, yineleme yalnız aynı yolunkiler arasında aranıyor; alansız eski plan kayıtları planın
  ilk yolu sayılıyor (`test_another_base_path_joins_the_plan_at_the_same_settings`).
- **Canlı hakem akışı nadiren ≈ 7 s duruyor (kök nedeni İş 1'de bulundu ve düzeltildi, bölüm 16):** kilit düşünce yeniden kilit, o model
  karesinin hakem satırını canlı akıştan (`kayit.Recorder` → `takip.Tracker.on_referee`) arıyor. Hakem satırı normalde
  model sonucundan önce hazır (mükemmel algılayıcı koşularında `kaynak_ms` p50 46 ms, en çok 129 ms; model sonucu ≈ 140 ms),
  ama 152 koşunun 3'ünde (kıvrımlı yolda 35° 7/10 koşu 2 ve 30° 6/10.4 koşu 1, 9. grubun `gorev9_RS0.3_model_x3/kosu_2`'si)
  ≈ 7 s boyunca hiçbir model karesi için satır bulunamadı (`kilitsiz_neden` = `hakem_yok`), oysa satırlar `dogru_cevap.csv`'ye
  yazılmış ve hedef görünür; 61 koşuda daha tek tük (1–10) kare böyle (zararsız: bir sonraki karede yeniden denenir).
  Hakemin eksik kare sayacı (`hakem_eksik_kare`) bu koşularda 0, olaylarda hata yok. Etkisi: bu iki kıvrımlı koşunun
  "kişi kaybedildi" sonucu belirsiz (bölüm 5); takip yolunun kayıplarında kişi zaten kadraj dışındaydı ya da model onu
  bulamıyordu (`hedef_gorunmuyor` / `kutu_eslesmedi`), etkilenmedi. Tarama koşuları aynı kodla yapıldı; düzeltme ayrı bir
  iş (testli, m06) olarak önerildi, bu işte kod değişmedi.
- **Belgedeki bileşim sayısı yanlıştı:** planlamadan önce 55 + 29 = 84 yazılmıştı, plan 81 (düşük bantta 3 yineleme);
  bölüm 2 düzeltildi.
- **Seyrek açılış hatası** (bilinen, 7. grup): PX4'ten heartbeat gelmedi; `toplu.py` koşuyu yeniden denedi (aşama 1'de
  1 kez). Repo dışı yükseklik kontrolü bu denemeyi de sayıyordu; ayrıldı.
- **A ile B aynı satırın yanına alan ekliyordu** (`video.py` `Run`): A'nın yaması B'li çalışma ağacına uygulanmıyordu;
  B'nin `tilt_deg` alanı başka bir yere alındı, iki yama da temiz uygulanıyor.

## 13. Dosyalar ve A / B ayrımı

**İş A** (ayrı commit, yama `~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_is_A.patch`): `takip_yuruyen` 10/10,
`takip_yuruyen_8m`, videoda "YANLIŞ KİŞİ". Dosyaları ve doğrulaması `gorev-grubu-09.md` bölüm 13'te.

**İş B** (bu belge; çalışma ağacında A'nın üstünde):

| Dosya | Değişiklik |
|---|---|
| `tez/sim/araclar/hedef.py` | `kamera.egim_deg` alanı (`CameraMount`, 0–60°, varsayılan `kamera.NOMINAL_TILT_DEG`), `--kamera-egim` (`CommandLine.camera_tilt_deg`), `ayarlar.kamera`; modelin eğimli kopyası (`model_tilt_deg`, `tilted_model_sdf`, `camera_model`) ve dünyanın onu eklemesi (`write_world`) |
| `tez/sim/araclar/kamera.py` | `NOMINAL_TILT_DEG = 45`, `tilt_of_mount` |
| `tez/sim/araclar/takip.py`, `konumlama.py` | `Tracker(mount=...)`, `Locator(mount=...)` (koşunun eğimi); `konumlama.MOUNT_PITCH_DOWN` `kamera.NOMINAL_TILT_DEG`'den |
| `tez/sim/araclar/olcum.py` | `frame_limits(..., tilt_deg)`, `tracking_metrics(..., tilt_deg)`, `RunData.camera_tilt_deg` |
| `tez/sim/araclar/rapor.py`, `video.py` | Yakın / uzak sınır koşunun eğimiyle |
| `tez/sim/araclar/senaryo.py` | `--kamera-egim`; montaj LOS (i) ve konuma; `ayarlar.kamera.gazebo_modeli`; koşu sonunda Gazebo'nun eğimiyle karşılaştırma (`kamera_montaji.egim_deg`) |
| `tez/sim/araclar/tarama.py` | Yeni: tarama sürücüsü (plan / kos / ozet), karar kuralı, geometrik paylar |
| `tez/sim/ruff.toml` | `known-first-party`'ye `tarama` |
| `tez/sim/testler/test_kamera_egimi.py`, `test_tarama.py` | Yeni (bölüm 11) |
| `tez/sim/testler/test_hedef.py` | `ayarlar`'da `kamera` bloğu |
| `tez/sim/README.md` | `kamera` alanı, tarama bölümü, model dosyası notu |
| `agent-os/specs/2026-11-10-m06-sim-ortami/spec.md` | Senaryo alanları (`kamera.egim_deg`), Dosya Planı (`tarama.py`), Test Planı, "Kamera parametreleri" (eğim ayarı), "Yaklaşma mesafesi" (modelle tarama ve öneri), Faz B (17 öne alındı) |
| `agent-os/specs/2026-11-10-m06-sim-ortami/tasks.md` | Görev Grubu 17 (genişletildi, öne alındı) |
| `implementation/gorev-grubu-17-on-kamera-acisi.md` (yeni), `kabul-kosulari.md` | Bu belge; tarama satırları |

Ortak dosyalarda (`video.py`, `olcum.py`, `test_hedef.py`, README, spec, tasks, `kabul-kosulari.md`) A ve B ayrı
parçalardadır: A'nın yaması temiz HEAD'e ve B'li çalışma ağacına uygulanır (`git apply -R --check` ile çalışma
ağacının A'yı birebir içerdiği doğrulandı). Repoya video, ULog, model ya da sonuç klasörü girmez (`tez/sim/sonuclar/`
git dışında).

**İş 1** (hakem akışı düzeltmesi, ayrı commit): dosyaları bölüm 16.6, yama
`~/Desktop/Follow/3_m06_Simulasyon/Deneme/hakem_akisi_duzeltme.patch` (temiz HEAD `b6b299aff9`'a uygulanır).

**İş 2 + İş 3** (37.5° ve genişletilmiş tarama, son karar, gerçek uçuş önerisi, simin yeni varsayılanı; İş 1'in
üstünde, ayrı commit; yama `~/Desktop/Follow/3_m06_Simulasyon/Deneme/kamera_varsayilan_is2_is3.patch`, temiz HEAD +
İş 1'e uygulanır):

| Dosya | Değişiklik |
|---|---|
| `tez/sim/araclar/kamera.py` | `NOMINAL_TILT_DEG = 35.0` (simin varsayılan montajı; kaynak bu belge) |
| `tez/sim/models/x500_tez/model.sdf` | `camera_link` pitch 0.610865 (35°); yorumda karar 14.11, bu belge, gerçek montajın henüz yapılmadığı |
| `tez/sim/araclar/video.py` | `run_tilt_deg`: eski koşuların eğimi Gazebo'nun kaydettiği montajdan |
| `tez/sim/araclar/tarama.py` | `approach_numbers`'ın varsayılan eğimi `kamera.NOMINAL_TILT_DEG` (sabit 45 yerine) |
| `tez/sim/araclar/hedef.py`, `konumlama.py`, `takip.py`, `senaryo.py`, `olcum.py` | Açıklama ve iletilerde "gerçek montaj 45°" yerine simin varsayılanı (davranış `kamera.NOMINAL_TILT_DEG`'den, değişmedi) |
| `tez/sim/araclar/onizleme.py`, `model_dene.py` | Serbest kameranın varsayılan eğimi `kamera.NOMINAL_TILT_DEG` |
| `tez/sim/senaryolar/takip_yuruyen.yaml` | 9 m / 12.9 m, kamera varsayılan, yol 2.9 m doğuya kaydırıldı, yorumlar |
| `tez/sim/senaryolar/takip_yuruyen_45_10m.yaml`, `takip_yuruyen_45_8m.yaml` | Yeni: 45° montaj karşılaştırması (`takip_yuruyen_8m.yaml` kaldırıldı) |
| `tez/sim/senaryolar/kalabalik_park.yaml`, `yuruyen_insan.yaml` | 9 m (kalabalık park); yorumlar |
| `tez/sim/testler/test_varsayilan_montaj.py` | Yeni (5 test, 6 durum; bölüm 20) |
| `tez/sim/testler/test_kamera_egimi.py`, `test_hedef.py`, `test_takip.py`, `test_video.py`, `test_konumlama.py`, `test_olcum.py` | Varsayılanı 45° kabul eden yerler (bölüm 20) |
| `tez/sim/README.md` | Kamera, senaryolar, `kamera` alanı, taramanın sonucu, ekipten gelen "AUTO FOLLOW" bilgisi |
| `agent-os/specs/2026-11-10-m06-sim-ortami/spec.md` | Yaklaşma mesafesi (son karar, gerçek uçuş önerisi, ilk uçuş), Kamera parametreleri, senaryo alanları, senaryolar, Dosya / Test Planı, Varsayımlar, Faz B, Açık Konular; "AUTO FOLLOW" / `AF_` (ekipten gelen bilgi) |
| `agent-os/specs/2026-11-10-m06-sim-ortami/tasks.md` | 17.10–17.12; dış kişiler tablosu ve Grup 10'da "AUTO FOLLOW" / `AF_` |
| `implementation/gorev-grubu-17-on-kamera-acisi.md` | Bölüm 17–20, Kısaca, 13–15, Kendin dene |
| `implementation/gorev-grubu-09.md` | Bölüm 14 (yeni varsayılanla demo koşuları) |
| `implementation/kabul-kosulari.md` | Aşama 3, kıvrımlı yol, ek koşular, F0 / F1, demo koşuları |

## 14. Görseller, videolar ve betikler (repo dışı)

`~/Desktop/Follow/3_m06_Simulasyon/` altında; özet PDF: `Kamera_Acisi_ve_Mesafe_Modelli_Tarama.pdf` (HTML → headless
Chrome). `Deneme/` altında `gorev10on_` ile başlayanlar:

| Dosya | Ne |
|---|---|
| `gorev10on_isi_<ölçüt>.png` (14) | Aşama 1 ısı haritaları: eğim × yükseklik, dört mesafe kuralı (`toplam`, `sim_puani`, `en_az_yatay_mesafe_m`, `mesafe_6m_alti_orani`, `kisi_sonda_kayip`, `hedef_kadrajda_orani`, `gorunur_kalma`, `en_uzun_kayip_s`, `algilama_orani`, `kisi_kutu_boyu_px`, `kilit_kaybi_sayisi`, `konum_hatasi_ort_m`, `arkada_kalma_hatasi_ort_deg`, `kose_px4_yetisme_ort_s`) |
| `gorev10on_aday_karsilastirma.png` | Aşama 2: 8 bileşim, her ölçütte 3 koşu (nokta) ve ortalama; grup puanları; toplam ve sıra |
| `gorev10on_hakem_karsilastirma.png`, `gorev10on_kivrimli_karsilastirma.png` | Mükemmel algılayıcı ve kıvrımlı yol, 4 bileşim × 3 koşu |
| `gorev10on_rapor_karsilastirma.png` | Kamera raporunun modelsiz sonuçlarıyla yan yana (en alçak başarılı ayar, kadrajda kalma, piksel boyu) |
| `gorev10on_gorus_alani_30_45.png` | 30° ile 45°'nin gördüğü alan: aynı yükseklikte, aynı mesafede ve üstten; köşede 6.2 m yaklaşınca kişinin yeri |
| `gorev10on_yaklasma_payi.png` | Kullanıcının beş ayarı ve aşama 2 adayları: yerde görülen şerit, yaklaşma payı, her koşunun köşe yaklaşması (ok) |
| `gorev10on_yaklasma_ve_kacirma.png` | Köşe ve duruş yaklaşmasının mesafeyle ilişkisi; kaybı ne belirliyor (pay aşımı, genişlik, piksel boyu; AUC) |
| `gorev10on_yaklasma_cizelgesi.png` | Dört koşunun mesafe–zaman çizgisi, yakın sınır ve kişinin kadrajdan çıktığı kenar |
| `gorev10on_algilama_kosullari_*.png` (5) | Modelin bulma oranı ve güveni: tek tek koşullar, görüntüdeki yer ve boy × bakış, lojistik model, güven dağılımı, aynı boyda eğim |
| `gorev10on_yanlis_kisi_karesi.png` (+ `.json`) | İş A: videoda "YANLIŞ KİŞİ" uyarısının göründüğü kare |
| `gorev10on_onerilen_35_8m_11.4m_kosu.mp4` | Önerilen ayar, aşama 2'nin en temsili koşusu (`asama2/e35_h8_d11.4/kosu_2`) |
| `gorev10on_kural_birincisi_35_7m_10m_kosu.mp4` | Kuralın birincisi (`asama2/e35_h7_d10.0/kosu_1`) |
| `gorev10on_45_10m_10m_kosu.mp4`, `gorev10on_45_10m_10m_kayip_kosu.mp4` | 45° 10/10: temsili koşu (`kosu_2`) ve kişinin kaybedildiği koşu (`kosu_3`) |
| `gorev10on_A_kalabalik_park_kosu.mp4`, `gorev10on_A_takip_yuruyen_10m_kosu.mp4` | İş A'nın doğrulama koşuları |
| `gorev10on_is_A.patch` | İş A'nın yaması (ayrı commit) |
| `gorev10on_betikler/` | Bu belgenin tablolarını ve görsellerini üreten betikler (repoya girmedi): `tarama_grafikleri.py` (ısı, adaylar, rapor, görüş alanı, çizelge), `yaklasma_analizi.py`, `algilama_kosullari.py` + `algilama_tablolari.py`, `karar_tablosu.py`, `satirlar_tarama.py` (kabul satırları), `temsili_video.py`, `kivrimli_plan.py`, `yukseklik_kontrol.py`, `yanlis_kisi_kare.py`, `yama_dogrula.sh`, `metin.py` + `pdf_olustur.py` |

**14.11 (İş 1–3), `gorev17b_` ile başlayanlar:**

| Dosya | Ne |
|---|---|
| `gorev17b_kisaca.png` | PDF'in 1 sayfalık "Kısaca"sının görseli: seçilen ayarın yandan görünüşü; her ayarın iki yolda denemelerin kaçında kapıyı geçtiği (düzeltmeden sonraki bütün koşular) |
| `gorev17b_karsilastirma.png` | Aşama 2 (14.11): 35°, 37.5°, montaj toleransı (32.5°) ve rakipler iki yolda, 8 ölçüt (nokta = koşu, boş kare = ek koşu, ✗ = o yolda kapıdan geçmedi) |
| `gorev17b_isi_<ölçüt>.png` (14) | Aşama 1 + ekleri (37.5° ve 9 m dahil) ısı haritaları |
| `gorev17b_hakem_akisi_once_sonra.png` | İş 1: canlı hakem akışı önce / sonra (bölüm 16) |
| `gorev17b_secilen_35_9m_12.9m_takip_yolu_kosu.mp4`, `gorev17b_secilen_35_9m_12.9m_kivrimli_yol_kosu.mp4` | Seçilen ayar: takip yolu (`asama3/e35_h9_d12.9/kosu_1`, köşe ≈ 0:50) ve kıvrımlı yol (`asama3_kivrimli/kivrimli_yuruyus_e35_h9_d12.9/kosu_3`, 164° geri dönüş ≈ 1:01) |
| `gorev17b_37.5_9m_12.9m_kivrimli_kayip_kosu.mp4` | 37.5° · 9/12.9, kıvrımlı yolda kişinin kaybedildiği koşu (`asama3_kivrimli/kivrimli_yuruyus_e37.5_h9_d12.9/kosu_1`, ≈ 1:00) |
| `gorev17b_varsayilan_takip_yuruyen_kosu.mp4`, `gorev17b_varsayilan_kalabalik_park_kosu.mp4` | İş 3: yeni varsayılanla demo koşuları (temsili birer koşu, bölüm 20) |
| `hakem_akisi_duzeltme.patch` | İş 1'in yaması (temiz HEAD'e) |
| `kamera_varsayilan_is2_is3.patch` | İş 2 + İş 3'ün yaması (temiz HEAD + İş 1'e) |
| `gorev17b_betikler/` | `karar_tablolari.py` (bölüm 17.3–18'in tabloları), `sonuc_yaz.py` (17.5'in önceden yazılan okuması; tolerans cümlesi sonra elle yazıldı), `zamanlama.py` / `fren.py` (kayıp anı ve burun kalkışı), `ozetle.py` / `detay.py`, `park_geo.py` (kalabalık parkta hedefin kadrajda kalması), `duyarlilik_geometri.py` (±2.5° geometri), `kisaca_gorsel2.py`, `karsilastirma2.py`, `satirlar2.py` (kabul satırları), `pdf_olustur17b.py` + `kisaca.md` + `kavramlar.md`; İş 1'in betikleri (bölüm 16.6) |

Koşu klasörleri (`tez/sim/sonuclar/`, git dışında): `gorev10on_tarama/` (`plan.json`, `senaryolar/`, `asama1/`,
`asama2/`, `asama2_hakem/`, `asama2_kivrimli/`, her aşamada `durum.json`, `ozet.csv`, `ozet.json`; `algilama_kareleri.csv.gz`,
`algilama_kosullari.json`, `algilama_tablolari.md`, `yaklasma_analizi.json`, `karar_tablosu.md`,
`rapor_karsilastirma.json`, `yukseklik_kontrol.csv`), `gorev10on_A_takip_yuruyen/`, `gorev10on_A_kalabalik_park/`,
`gorev10on_f0.log`, `gorev10on_f1.log`, `gorev10on_zincir.log`. 14.11: `gorev10on_tarama/asama1b/`, `asama3/`,
`asama3_kivrimli/`, `asama3_duyarlilik/`, `asama3_duyarlilik_kivrimli/`, `asama3_kivrimli_ek/` (+ `zincir3.log`,
`karar17b.json`), `gorev17b_teshis/` (İş 1), `gorev17_varsayilan_takip_yuruyen_x3/`, `gorev17_varsayilan_kalabalik_park_x3/`,
`gorev17_varsayilan_f0.log`, `gorev17_varsayilan_f1.log`, `gorev17_varsayilan_zincir.log` (İş 3).

## 15. Açık kararlar ve bekleyenler

- ~~**Kamera eğimi ve uçuş ayarı (kullanıcı / ekip):** öneri 35° · 8 m / 11.4 m (bölüm 6).~~ **Sim için karar verildi
  (14.11, bölüm 18):** 35° · 9 m / 12.9 m, simin varsayılanı oldu (bölüm 20). **Gerçek uçuş için açık (ekip, m22/m25):**
  önerilen aynı ayar doğrulanmadı (bölüm 19); montaj parçası yapılınca açı araçta ölçülüp Pi'ye girilir ve ilk saha
  uçuşunda bölüm 19'daki plana göre doğrulanır.
- **m15'e (Kurt) öneri:** köşedeki ≈ 6.2 m'lik yaklaşma stok Follow Me'nin; kendi modunda en az mesafe koruması olursa
  45° 10/10 dahil bütün ayarlarda pay sorunu küçülür. m15 takılınca aynı tarama (`tarama.py`) onunla tekrarlanabilir.
- **m08 / m10'a (Ortatepe) öneriler:** bölüm 9 (küçük kişi, giriş boyutu, yandan görünüş, kalabalık, kenar, gerçek uçuş
  verisi). Hailo'daki model başka bir bulma oranı verir; tarama o modelle tekrarlanmalı.
- **m01'e (Hüseyin):** başarı ölçütlerine "köşede en az yatay mesafe" ve "kişi sonuna kadar izlendi" (bu taramanın kapısı)
  önerilebilir; eşikleri m01 belirler.
- **Simin ölçemedikleri** (bölüm 10): rüzgâr, gerçek CM3 lensi (m09), otomatik pozlama ve bulanıklık (Görev Grubu 15),
  zemin eğimi ve GPS yükseklik hatası, insan çeşitliliği. Öneri bunlar ölçülünce yeniden değerlendirilmeli.
- **m06'nın kendi açık hatası (kapandı, İş 1):** canlı hakem akışının "durması" Gazebo'nun büyüyen segmentasyon
  başlığından; düzeltildi ve kıvrımlı yolun 35° 7/10, 30° 6/10.4, 35° 8/11.4 koşuları yeniden koşuldu (bölüm 16).
- **Yasal sınırlar:** insanların yakınında ve üstünde uçuş için SHGM kurallarına bakılmalı; bu belge yasal bir sayı
  vermez.

## 16. Canlı hakem akışının "durması": kök neden ve düzeltme (İş 1)

**Kısaca:** Hata simin kendi hatasıydı, gerçek sistemde karşılığı yok (hakem yalnız simde var). Gazebo'nun
segmentasyon kamerası (gz-sensors 8.2.2) her yayımladığı karenin başlığına bir `frame_id` girdisi daha ekliyor ve hiç
temizlemiyor. Ana süreç bu kareyi saf Python protobuf ile baştan sona çözdüğü için kare başına iş koşu boyunca
doğrusal büyüdü, Python'un tam çöp toplaması (GC) sıklaştı ve ≈ 70 s kayıttan sonra gz-transport iş parçacığı 30 Hz'e
yetişemedi: hakemin satırları modelin sonucundan sonra gelmeye başladı ve kilit düşünce yeniden kilit hiç olamadı.
"≈ 7 s duruyor" gözlemi aslında **son kilit kaybından kaydın sonuna kadar** olan süreydi. Düzeltme: segmentasyon
karesi ham baytından okunuyor, başlığın girdileri çözülmeden atlanıyor (önce hatayı yakalayan test). Düzeltmeden sonra
hakem karesi kayıt boyunca yakalamadan ≈ 36 ms sonra hazır, büyümüyor.

### 16.1 Etkilenen koşular (yeniden sayıldı)

- Belgede "152 koşunun 3'ü" yazıyordu. Bütün model koşuları (194) yeniden tarandı (repo dışı `engellenen_kilit.py`):
  kayıt içinde hakemi bulamayan (`hakem_yok`) kilitsiz kare **122 koşuda** var ve bu 1051 karenin 1046'sı kaydın
  **ikinci yarısında**. Ama hakem zamanında gelseydi kilidin olacağı kare (kişi görünür ve bir model kutusu hakemin
  kutusuyla IoU ≥ 0.3, yani `LOCK_MIN_IOU`) yalnız **8 koşuda** var; çoğunda 1 kare.
- **Sonucu değiştiren:** kıvrımlı yol 35° 7/10 koşu 2 (89.9 s'den sonra 64 kare) ve 30° 6/10.4 koşu 1 (91.1 s'den
  sonra 45 kare). İkisinde de kişi kadrajdaydı, model onu buluyordu, ama yeniden kilit yapılamadı ve kişi "sonda
  kaybedildi" sayıldı. 30° 6/10.4 koşu 3'te 1 kare (90.7 s) ve aşama 1'in 45° 12/8'inde 1 kare: tek kare, kişi zaten
  kaybediliyordu.
- **Değiştirmeyen:** 9. grubun `gorev9_RS0.3_model_x3/kosu_2`'si (belgede üçüncü örnekti): `hakem_yok` var ama o anda
  modelin hiç kutusu yok (0 kutu); hakem zamanında gelseydi de kilit olmazdı.
- Üç örnekte de "durma" son kilit kaybından kaydın sonuna kadar sürüyor (89.5–97.4 s, 91.0–97.4 s, 83.2–89.4 s). Kilitli
  olunduğu sürece hakeme bakılmadığı için gecikme daha önce başlamıştı ama görünmüyordu.

### 16.2 Kanıt (ölçüm sırasıyla)

1. **Hakem kaynaklı 31 koşu** (`tez_los.csv` → `kaynak_ms`: hakem karesinin yakalamadan kaç ms sonra hazır olduğu):
   her koşuda kayıt boyunca büyüyor, ilk 15 s'de ortanca ≈ 40 ms, son 15 s'de 70–80 ms; **9 koşuda** son saniyelerde
   120–1141 ms (en kötüsü aşama 2 hakem 30° 6/10.4 koşu 1). Modelsiz hakem koşusunda (`gorev5_C2`) 17 → 26 ms.
   Model sonucu yakalamadan ≈ 120–150 ms sonra hazır (`hazir_sim`); hakem bundan geç kalınca kilitsiz her kare
   `hakem_yok` oluyor.
2. **Suçlu olmayanlar:** ana sürecin sim saati (`SimClock`, aynı gz-transport iş parçacığında) geride kalmıyor (model
   sonucunun `hazir_sim − t`'si 117 → 158 ms, artıda); MAVLink poz akışı zamanında (`poz_yok` 0); Tracker'ın hakem
   kuyruğu ≤ 7 ms; hakemin yarım-kare birleştirmesi hiç kare düşürmedi (`hakem_eksik_kare` 0).
3. **Ölçümlü koşu 1** (`sonuclar/gorev17b_teshis/once_1`, e30 · 6 m / 10.4 m, takip yolu, model, videolu; geri
   çağrılara zaman ölçerleri, GIL sondası, iş parçacığı başına CPU, GC olayları): gz-transport iş parçacığının CPU'su
   kayıt boyunca **doğrusal 0.15 → 0.87 çekirdek**; tam (2. kuşak) GC 33. s'de başlıyor, 45 s'den sonra ≈ 0.3 s'de
   bir, her biri 70–84 ms (toplam 122 kez, 9.1 s, GIL tutularak); GIL sondasının %95'i 0.3 → 6.5 ms. Geri çağrıların
   kendi gövdeleri ise sabit süreli (poz 0.1 ms, segmentasyon 3–4 ms): büyüyen iş geri çağrıdan önce.
4. **Ölçümlü koşu 2** (`once_2`, videosuz; mesaj başına ham boy, çözme süresi, iş parçacığı CPU'su, yığın örnekleri):
   segmentasyon mesajı 2 242 985 → 2 339 631 bayt (görüntü 2 239 488 bayt sabit, **kare başına ≈ 51 bayt**); saf
   Python ile çözme **0.95 → 19.4 ms**, kare başına CPU **3.5 → 30.8 ms** (kamera 33 ms'de bir kare gönderir);
   yığın örneklerinin çoğu protobuf'un tekrarlı alan çözücüsünde (`DecodeRepeatedField` → `containers.add`, dizgi
   çözme). Poz ve `camera_info` mesajları sabit (0.3 / 0.2 ms). Videosuz da aynı: video kaydedicisi sebep değil.
5. **Gazebo'nun kendisi** (`seg_baslik.py`; Gazebo sunucusu PX4'süz, aynı dünya, 40 s, ham yakalama;
   `sonuclar/gorev17b_teshis/seg_baslik.txt`): `labels_map` ve `colored_map` başlığında 36.5 s'de **1107 özdeş
   `frame_id` girdisi** (kare başına +1); RGB kamerada hep 2 girdi (`frame_id`, `seq`). Sensör yalnız abonesi varken
   yayımladığı için büyüme hakemin kayıt başındaki aboneliğiyle başlıyor.

**Zincir:** Gazebo segmentasyon karesinin başlığını büyütür → araçlar `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`
(saf Python protobuf) ile her kareyi baştan sona çözer, kare başına binlerce kısa ömürlü Python nesnesi → Python'un tam
çöp toplaması GIL'i tutarak 0.3 s'de bir → ana süreçteki tek gz-transport iş parçacığı ≈ 70 s kayıttan sonra 30 Hz'e
yetişemez, mesajlar birikir → hakemin satırı modelin sonucundan sonra gelir → kilit düşmüşse her model karesi
`hakem_yok`, yeniden kilit olmaz. Kıvrımlı yolun kaydı (≈ 73 s) takip yolununkinden (≈ 65 s) uzun olduğu için sonucu
değiştiren kayıplar hep orada çıktı.

### 16.3 Önce test, sonra düzeltme

`testler/test_hakem_akisi.py` (5 test, donanımsız, simsiz):

| Test | Ne sınanır |
|---|---|
| `test_a_segmentation_frame_is_read_from_its_raw_bytes` | Ham bayttan okunan damga, boyut ve pikseller protobuf'un çözdüğüyle aynı: 1, 0, 2200 girdili başlık, damgası girdilerden sonra yazılmış kare, başlıksız kare |
| `test_a_broken_frame_is_refused_with_a_reason` | Kesik kare ve tutmayan boyut nedeniyle reddedilir |
| `test_reading_a_frame_does_not_slow_down_as_gazebos_header_grows` | **Hatayı yakalayan test:** 20 000 girdili kare (≈ 11 dk Gazebo) 5 ms altında ve ilk kare kadar hızlı okunur |
| `test_the_recorder_takes_the_referees_frames_raw_and_joins_them` | Recorder segmentasyona yalnız kayıtta ve ham abone olur; büyümüş başlıklı kare de birleşik hakem karesine (görünen piksel, kutu) dönüşür |
| `test_the_referees_lateness_is_measured_in_every_tracking_source` | Hakemin gecikmesi ve "hakemi sonradan gelen" kilitsiz model kareleri her takip kaynağında sayılır |

**Kırmızı:** eski davranış (karenin protobuf ile baştan sona çözülmesi) aynı arayüzün arkasındayken zaman testi
başarısız oldu: 20 000 girdili kare **108.5 ms** (sınır 5 ms). **Yeşil:** düzeltmeden sonra 5/5; bütün testler 270 → 275.

**Düzeltme (`kayit.py`):**
- `read_image(raw)` protobuf modülü olmadan ham baytlardan yalnız gerekenleri okur: başlığın damgası, genişlik, yükseklik
  ve pikseller (kopyasız `memoryview`). Gazebo (C++) damgayı başlığın girdilerinden önce yazar; okuyucu damgayı bulunca
  başlığın geri kalanını uzunluğuyla atlar, girdilere hiç bakmaz. `label_channel` etiket kanalını verir.
- `Recorder` segmentasyona `subscribe_raw` ile abone olur (yalnız kayıtta, eskisi gibi); okunamayan kare koşunun
  hatalarına yazılır (olmadı). Testler için `node` parametresi.
- Aynı sensörü dinleyen `dogrulama.py` (tepe kamerası, F1) ve `onizleme.py` (`--etiket`) de ham okur.
- **Görünürlük:** `takip.Tracker` her koşuda `ozet.json` → `tez_los.hakem_akisi`'ni yazar: hakemin gecikmesi
  (`gecikme_ms_p50/p95/maks`, 100 ms'den geç kare `gec_kare`), hakemi bulamayan kilitsiz model karesi
  (`hakem_yok_kare`) ve bunlardan hakemin karesi sonradan gelenler (`hakem_sonradan_gelen_kare`: hakem eksik değil
  geç). `senaryo.py` bunu günlüğe yazar; sonradan gelen 5'ten fazlaysa raporda olay olur. Bu sayılar o zaman olsaydı
  hata ilk koşuda görünürdü.
- **Değişmeyenler:** Gazebo düzeltilmedi (sürümler kilitli, `apt-mark hold`); başlık büyümeye devam ediyor, ama artık
  kimse onu çözmüyor (11 dakikalık bir koşuda mesaj ≈ 1 MB büyür, aktarım için önemsiz). Araçların saf Python
  protobuf seçimi değişmedi: bu bilgisayarda sistemin protobuf'u (4.21.12, C++) Gazebo mesajlarını açıyor ama seçim
  `~/.local`'daki protobuf 7.x yüzünden yapılmıştı ve takım arkadaşlarının ortamı farklı olabilir; ham okuma
  ortamdan bağımsız. Hedef seçiminin kuralı (yeniden kilit hakemden) değişmedi.

### 16.4 Doğrulama

**Ölçümlü koşu 3** (`sonuclar/gorev17b_teshis/sonra_1`; ölçümlü koşu 1'in aynısı, düzeltilmiş kodla):

| | Önce (`once_1`) | Sonra (`sonra_1`) |
|---|---|---|
| gz-transport iş parçacığının CPU'su (kayıt boyunca) | 0.15 → 0.87 çekirdek, doğrusal büyüyor | ≈ 0.19 çekirdek, sabit |
| Tam (2. kuşak) GC | 122 kez, toplam 9.1 s (her biri 70–84 ms) | 1 kez, 34 ms |
| Kısa GC (0. / 1. kuşak) | 16 717 / 1 519 | 368 / 33 |
| GIL sondası, %95 | 0.3 → 6.5 ms | ≈ 0.5 ms, sabit |
| Hakem karesi hazır (yakalamadan sonra), ortanca / %95 / en çok | 35 / 40 / 47 ms (bu koşu 89 s'de bitti, iş parçacığı henüz 1 çekirdeğe ulaşmadı) | 36 / 42 / 46 ms, kayıt boyunca sabit |
| `ozet.json` → `hakem_akisi` (yeni) | – | 1935 kare, p50 44 / p95 49 / en çok 203 ms, 1 kare > 100 ms; hakemi sonradan gelen kilitsiz kare 1 (kaydın ilk karesi) |
| RTF (kayıt penceresi) | 0.918 | 0.932 |

**Kıvrımlı yolun yeniden koşuları** (`sonuclar/gorev10on_tarama/asama3_kivrimli/`, düzeltilmiş kod, videolu, 3'er koşu, 13.11 22:25–22:48;
13.11'deki aşama 2 kıvrımlı koşularıyla aynı senaryolar):

| Bileşim (kıvrımlı yol, 3 koşu) | 13.11, düzeltmeden önce: kişi izlendi / en az mesafe / engellenen kilit karesi | düzeltmeden sonra (13.11, 22:25–22:48): kişi izlendi / en az mesafe / hakem %95, en çok / engellenen | Düzeltmeden sonraki kaybın nedeni |
|---|---|---|---|
| 35° · 7 m / 10 m | 1/3 / 5.4–6.4 m / 64 kare (koşu 2) | **2/3** / 4.0–5.7 m / 42–49 ms, ≤ 210 ms / 0 | koşu 2: 164° dönüşte kişi kadrajın altından çıktı (son kayıptan sonra %83 alttan), `hedef_gorunmuyor` |
| 30° · 6 m / 10.4 m | 1/3 / 3.0–6.6 m / 45 kare (koşu 1) + 1 (koşu 3) | **2/3** / 5.5–6.5 m / 49 ms, ≤ 208 ms / 0 | koşu 3: kişi kadrajın altından çıktı (%86) |
| 35° · 8 m / 11.4 m | 3/3 / 6.0–8.1 m / 1 kare (koşu 2, sonuç değişmedi) | **2/3** / 6.0–7.5 m / 49 ms, ≤ 205 ms / 0 | koşu 2: dönüşten sonra kişi kadrajın yanından çıktı (%100 yandan) |

- Düzeltmeden sonra 9 koşunun hiçbirinde kayıt içinde hakemi bulamayan kilitsiz kare yok (yalnız kaydın ilk karesi,
  hakem zaten o an başlıyor); engellenen kilit 0; hakem %95'i 42–49 ms, en çok 205–210 ms (her koşuda en çok 1 kare
  > 100 ms). RTF 0.91–0.97 (13.11'de 0.86–0.96).
- **Belirsiz iki kayıp hataymış:** 35° 7/10 ve 30° 6/10.4 artık üç koşunun ikisinde kişiyi izliyor (13.11'de birinde).
  Kalan kayıplar gerçek: hakem zamanında, kişi kadrajdan çıkmış, model kutusu yok.
- **35° 8/11.4 bu kez üç koşunun birinde kişiyi kaybetti** (164° dönüşten sonra yandan). İki günün altı koşusunda: 35°
  8/11.4 **5/6**, 35° 7/10 3/6, 30° 6/10.4 3/6. Sıralama aynı kaldı ama 13.11'deki "kıvrımlı yolda 3/3 geçen tek
  ayar" sonucu yeniden koşuda tutmadı: kıvrımlı yolun sert geri dönüşü bu ayarların hepsi için sınırda. Bu, İş 2'nin
  son seçiminde (bölüm 18) bütün koşularla birlikte değerlendirildi.

### 16.5 Gerçekte karşılığı var mı?

- **Bu hata simde kalır.** Hakem (segmentasyon kamerası ve yeniden kilitte operatörün yerine geçmesi) yalnız simde var;
  Gazebo'nun başlık hatası gerçek kamerada yok. Gerçek sistemde yeniden kilidi m11'in kendi kuralı ya da QGC'deki
  operatör yapar.
- **Benzeri gerçekte de olabilir (ayrım):** bu bir görüntü akışı *kesilmesi* değil, *geride kalmasıydı*: mesajlar
  geliyordu ama giderek eskiyordu. Pi'deki Python süreci de kareleri bir geri çağrıda işliyorsa, kare başına iş zamanla
  büyürse (birikmiş durum, büyüyen mesaj) ya da çöp toplama / başka bir iş parçacığı GIL'i tutarsa kareler aynı biçimde
  giderek geç işlenir. Bunu yakalayacak olan, ICD'nin (m05) zaman damgası, Pi'nin kare yaşı kontrolü ("eski veriyi
  tekrar gönderme", hata yönetimi standardı) ve PX4 tarafının zaman aşımıdır. Vision için öneri (Ortatepe / m10–m12,
  karar onların): kare başına işlem süresini ve kare yaşını koşu boyunca logla; bu bölümdeki gibi bir "sabit mi,
  büyüyor mu" grafiği ilk uzun bench denemesinde bakılacak ilk şey olsun.
- Gerçek operatörün yeniden kilidi (QGC videosu üzerinden) Wi-Fi gecikmesiyle gecikebilir: o, Görev Grubu 16'nın (Wi-Fi
  benzetimi) konusu.

### 16.6 Dosyalar (İş 1, ayrı commit)

| Dosya | Değişiklik |
|---|---|
| `tez/sim/araclar/kayit.py` | `ImageFrame`, `read_image`, `label_channel` (ham okuma); `Recorder` segmentasyonu `subscribe_raw` ile dinler, `node` parametresi; modül metni |
| `tez/sim/araclar/takip.py` | `REFEREE_LATE_MS`, `referee_stream`; Tracker hakemin gecikmesini ve hakemi sonradan gelen kilitsiz kareleri sayar (`summary()["hakem_akisi"]`) |
| `tez/sim/araclar/senaryo.py` | Hakem akışı günlük satırı ve olayı (`REFEREE_LATE_EVENT_FRAMES`) |
| `tez/sim/araclar/dogrulama.py`, `onizleme.py` | Segmentasyon karesi ham okunur |
| `tez/sim/testler/test_hakem_akisi.py` | Yeni (5 test) |
| `tez/sim/README.md` | "Canlı hakem akışı ve Gazebo'nun büyüyen başlığı" |
| `agent-os/specs/2026-11-10-m06-sim-ortami/spec.md` | "Kamera parametreleri" → Konular satırı; Test Planı (`test_hakem_akisi.py`) |
| `agent-os/specs/2026-11-10-m06-sim-ortami/tasks.md` | 17.9 |
| `implementation/gorev-grubu-17-on-kamera-acisi.md` | Bu bölüm; bölüm 5, 12 ve 15'teki açık hata notları |
| `implementation/kabul-kosulari.md` | Ölçümlü koşular ve kıvrımlı yolun yeniden koşuları |

Yama: `~/Desktop/Follow/3_m06_Simulasyon/Deneme/hakem_akisi_duzeltme.patch` (temiz HEAD `b6b299aff9`'a uygulanır).
Temiz HEAD'in ayrı, paylaşımlı bir klonunda (kullanıcının deposu ve index'i değişmedi) `git apply` ile uygulandı: 275 test geçti (HEAD'in 270'i + 5 yeni), `ruff format --check` ve `ruff check` temiz; insan modelinin mesh'leri (`kur.sh` ile indirilen, git dışı) klona bağlantıyla verildi.

Görsel: `~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17b_hakem_akisi_once_sonra.png` (A: Gazebo'nun başlığı, B: kare
başına iş, C: gz-transport iş parçacığının CPU'su, D: tam GC, E: hakemin gecikmesi, F: kıvrımlı yolda engellenen
yeniden kilitler). Betikler `~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17b_betikler/` (`olcumlu_kosu*.py`,
`teshis_coz*.py`, `seg_baslik.py`, `engellenen_kilit.py`, `hakem_akisi_grafik.py`).

## 17. 37.5° denemesi ve genişletilmiş tarama (İş 2, 14.11)

**Kullanıcının isteği (14.11):** "En uygun hangisiyse, hangi seçeneği öneriyorsan o olsun; benim tahminimce 37.5° (30 ile
45'in ortası) en iyi sonucu verebilir gibi geliyor. Montajı henüz yapmadık." Ek kararlar (koordinatör üzerinden,
14.11): 37.5° yalnız 8 m'de değil, alçak ve yüksek yüksekliklerde ve farklı mesafelerde karşılaştırmalı denensin;
35° ve 40°'ye de 9 m eklensin; amaç yalnız simin varsayılanı değil, **gerçek uçuş için de bir değer**; sonuçlar
toplantıda ekip arkadaşlarına anlatılacak.

### 17.1 Tasarım (sonuçlar görülmeden yazıldı)

Bütün yeni koşular **İş 1'in düzeltmesinden sonraki kodla** (bölüm 16). Karar kuralı ve kapılar bölüm 3'tekinin
aynısı, `tarama.py`'de değişmedi. Izgara 13.11 22:23'te `plan.json`'a eklendi, 1. aşama ekleri 22:48'de başladı; bu
metin 22:55'te, hiçbir sonuç görülmeden yazıldı.

**Aşama 1 ekleri** (`asama1b`, 1'er koşu, videosuz, `takip_yuruyen` yolu, durum dosyasıyla; 19 bileşim, hepsi
kadraja sığıyor):

| Eğim | Yükseklik [m] | Geride durma | Bileşim |
|---|---|---|---|
| 37.5° | 6, 7, 8, 9, 10, 12 | merkez `h / tan 37.5° = 1.303 h` (7.8, 9.1, 10.4, 11.7, 13.0, 15.6 m) ve uzak `≈ 1.43 h` (önceki önerinin kuralı: 8.6, 10.0, 11.4, 12.9, 14.3, 17.2 m) | 12 |
| 35°, 40° | 9 (ızgarada yoktu) | aşama 1'in ana bandı gibi: merkezin 0.8 / 1 / 1.25 katı ve 8 m (35°: 10.3, 12.9, 16.1, 8 m; 40°: 8.6, 10.7, 13.4 m; 40°'nin 8 m'si 8.6'ya yakın, yinelenen) | 7 |

**Aday seçimi (kural, adım 2–3):** eski aşama 1 (81 bileşim, 13.11, düzeltmeden önce, videosuz) ile yeni 19 bileşim
birlikte sıralanır (min–maks ölçekleme hepsi üzerinden; repo dışı `adaylar.py`). Hata eski aşama 1'in tek koşularını
yalnız birer karede etkiledi (bölüm 16.1, sonucu değiştirmedi), bu yüzden ön seçim için birleştirmek kabul edildi;
asıl karşılaştırma aşama 2'de, aynı kodla. Adaylar 35° / 37.5° / 40°'den: her eğimin kapıyı geçen en iyisi, sonra
sıradaki en iyiler, **4 aday**.

**Aşama 2** (`asama3` = takip yolu, `asama3_kivrimli` = kıvrımlı yol; 3'er koşu, videolu, iki yolda da):
4 aday + önceki öneri **35° 8/11.4** + kuralın 13.11'deki birincisi ve ikincisi (**35° 7/10**, **30° 6/10.4**;
"en yakın rakipler") + **45° 10/10** başvurusu (bugünkü montaj). Bileşimler çakışırsa bir kez. Kuralın 4. adımı
(öneri) takip yolundaki havuzda uygulanır (13.11'deki gibi); kıvrımlı yol ek kapıdır. Bütçe: ≈ 8 bileşim × 2 yol × 3
koşu × 2.5 dk ≈ 2 saat (İş 1'in 9 kıvrımlı yeniden koşusu bunun içinde).

**Montaj açısının duyarlılığı** (`asama3_duyarlilik`): seçilen ayarın yüksekliği ve mesafesinde eğim ±2.5° (montaj
yanlış takılırsa), 3'er koşu, takip yolu ve kıvrımlı yol; aşama 2'de zaten koşulmuş komşu varsa tekrarlanmaz. Kuralın
havuzuna girmez (montaj hatasıdır, seçenek değildir).

**Son seçim** (kullanıcı seçimi bize bıraktı): (1) kural: kapıyı takip yolunda 3/3 geçenler arasında toplam puan;
(2) güvenlik: köşede en az mesafe ve 6 m altı pay; (3) **iki yolda 3/3** (kıvrımlı yolun kapısı da); (4) algılama
(bulma oranı, kişi boyu). Kuralın birincisiyle seçilen farklıysa gerekçesi sayılarla yazılır (13.11'deki gibi).

**Hiçbir ayar kıvrımlı yolda 3/3 geçmezse** (İş 1'in yeniden koşularında 35° 8/11.4, 35° 7/10, 30° 6/10.4 2/3 kaldı;
bu not 1. aşama eklerinin sonuçları görülmeden yazıldı): (3) yerine iki yolun bütün koşularında (13.11'in koşuları da
dahil, eskiler düzeltmeden önce olduğu için ayrı gösterilerek) kişinin sonuna kadar izlendiği koşu oranı ve köşe /
geri dönüşte kalan yaklaşma payı kullanılır; 3/3 kapısının hiçbir ayarda sağlanmadığı açıkça yazılır.

### 17.2 Aşama 1 ekleri: sonuçlar (19 bileşim × 1 koşu, videosuz)

Koşular 13.11, 22:48–23:28 (19/19 GEÇTİ, RTF 0.95–1.00; düzeltilmiş kod). Klasör
`sonuclar/gorev10on_tarama/asama1b/`; eski aşama 1 ile birleşik sıralama `asama1_birlesik.json` (100 bileşim, 36'sı
kapıdan geçti).

| Bileşim | Kapı | Sıra (birleşik) | Toplam | En az [m] | Kişi sonda | Bulma [%] | Kutu [px] | Köşe yaklaşması [m] | Yaklaşma payı [m] | Kadrajda [%] |
|---|---|---|---|---|---|---|---|---|---|---|
| 35° · 9 m / 8 m | kişi sonda kaybedildi | ✗ | 0.42 | 3.01 | kayıp | 57 | 192 | 5.0 | 1.4 | 30 |
| 35° · 9 m / 10.3 m | geçti | 25 | 0.58 | 3.99 | izlendi | 61 | 190 | 6.3 | 3.7 | 87 |
| 35° · 9 m / 12.9 m | geçti | 4 | 0.64 | 6.61 | izlendi | 64 | 182 | 6.3 | 6.3 | 95 |
| 35° · 9 m / 16.1 m | geçti | 32 | 0.51 | 10.80 | izlendi | 44 | 154 | 5.3 | 9.5 | 79 |
| 37.5° · 6 m / 7.8 m | 1.10 m < 3 m; kişi sonda kaybedildi | ✗ | 0.56 | 1.10 | kayıp | 73 | 276 | 6.7 | 3.7 | 58 |
| 37.5° · 6 m / 8.6 m | 2.07 m < 3 m | ✗ | 0.57 | 2.07 | izlendi | 70 | 266 | 6.5 | 4.5 | 72 |
| **37.5° · 7 m / 9.1 m** | geçti | **1** | 0.72 | 5.51 | izlendi | 75 | 246 | 3.6 | 4.4 | 92 |
| 37.5° · 7 m / 10 m | geçti | 12 | 0.62 | 4.33 | izlendi | 75 | 234 | 5.7 | 5.3 | 89 |
| **37.5° · 8 m / 10.4 m** | geçti | **2** | 0.70 | 4.64 | izlendi | 72 | 214 | 5.8 | 5.0 | 94 |
| 37.5° · 8 m / 11.4 m | geçti | 10 | 0.62 | 5.24 | izlendi | 69 | 204 | 6.2 | 6.0 | 91 |
| 37.5° · 9 m / 11.7 m | geçti | 7 | 0.63 | 5.58 | izlendi | 66 | 188 | 6.1 | 5.7 | 96 |
| 37.5° · 9 m / 12.9 m | geçti | 5 | 0.63 | 7.13 | izlendi | 61 | 180 | 5.8 | 6.9 | 94 |
| 37.5° · 10 m / 13 m | geçti | 16 | 0.60 | 6.95 | izlendi | 53 | 168 | 6.1 | 6.4 | 96 |
| 37.5° · 10 m / 14.3 m | geçti | 27 | 0.57 | 8.02 | izlendi | 47 | 158 | 6.3 | 7.7 | 93 |
| 37.5° · 12 m / 15.6 m | kişi sonda kaybedildi | ✗ | 0.47 | 16.24 | kayıp | 0 | 124 | – | 7.7 | 93 |
| 37.5° · 12 m / 17.2 m | kişi sonda kaybedildi | ✗ | 0.57 | 18.55 | kayıp | 0 | 114 | – | 9.3 | 100 |
| 40° · 9 m / 8.6 m | 2.05 m < 3 m; kişi sonda kaybedildi | ✗ | 0.47 | 2.05 | kayıp | 49 | 190 | 6.5 | 3.2 | 60 |
| 40° · 9 m / 10.7 m | geçti | 14 | 0.62 | 4.74 | izlendi | 63 | 192 | 6.0 | 5.3 | 96 |
| 40° · 9 m / 13.4 m | geçti | 17 | 0.60 | 9.10 | izlendi | 60 | 180 | 4.3 | 8.0 | 83 |

- **37.5°: 7–10 m'nin sekiz bileşiminin hepsi kapıyı geçti;** 6 m'de köşede dron kişinin üstüne geliyor (1.1 / 2.1 m),
  12 m'de model kişiyi hiç bulamıyor (%0, kişi ≈ 114–124 px). Algılama yükseklikle düşüyor: 7 m %75, 8 m %69–72, 9 m
  %61–66, 10 m %47–53. Bu tablo 13.11'deki 30–45° bulgusunun aynısı; 37.5° farklı bir davranış göstermiyor, 35° ile
  40°'ın arasında duruyor.
- Kapıyı geçme oranı eğime göre: 30° 7/20, 35° 9/25, **37.5° 8/12**, 40° 9/23, 45° 3/20. 37.5°'nin oranı yüksek
  görünüyor ama ızgarası farklı: yalnız merkez ve 1.43 h mesafeleri (kötü bilinen 0.8 × merkez ve 8 m yok), 4–5 m yok.
  Aynı mesafe kurallarında (merkez, 7–10 m) 35° 4/4, 37.5° 4/4, 40° 3/4.
- 9 m satırı (35°, 40°) 8 m ile 10 m'nin arasına oturuyor: 35° 9/12.9 (merkez) birleşik sıralamada 4., 40° 9/10.7 14.

**Aday seçimi (kural, adım 3, 35° / 37.5° / 40°, 4 aday):** 37.5° 7/9.1 (birleşik 1.; 37.5° için en iyi), 40° 6/8 (3.;
40° için en iyi), 35° 9/12.9 (4.; 35° için en iyi), 37.5° 8/10.4 (2.; sıradaki en iyi).
**Bir sapma (gerekçeli):** 40° 6/8 13.11'de aşama 2'de zaten 3 koşu uçtu ve üçünde de kapıdan kaldı (en az 0.97–1.50 m,
kişi 3/3 kaybedildi); o koşularda hakem hatasının engellediği kilit yok (bölüm 16.1), yani kayıp hatadan değil
geometriden. Aynı sonucu yeniden ölçmek için 6 koşu harcanmadı; yerine sıradaki en iyi **37.5° 9/12.9** (5.) alındı.
40° 6/8 tabloda 13.11'in sonucuyla durur.

**Aşama 2'nin havuzu (9 bileşim, iki yol, 3'er koşu, videolu):** adaylar 37.5° 7/9.1, 37.5° 8/10.4, 37.5° 9/12.9,
35° 9/12.9; **37.5° 8/11.4** (kullanıcının doğrudan sorusu: önerilen ayarla aynı mesafe; birleşik 10.); önceki öneri
35° 8/11.4; en yakın rakipler 35° 7/10, 30° 6/10.4; başvuru 45° 10/10. Koşular 23:28'de başladı.

### 17.3 Aşama 2, takip yolu (`asama3`): sonuçlar ve kuralın sırası

Koşular 13.11 23:28 – 14.11 00:34 (9 bileşim × 3 koşu, videolu, hepsi GEÇTİ; RTF 0.85–1.00). Değerler 3 koşunun
ortalaması (en az–en çok). Klasör `sonuclar/gorev10on_tarama/asama3/` (`ozet.csv`, `ozet.json`; her bileşimde
`toplu.html`, her koşuda `kosu.mp4` ve `rapor.html`).

| Bileşim (3 koşu) | Kapı | En az mesafe [m] | < 6 m [%] | Kişi kaybı | Kadrajda [%] | En uzun kayıp [s] | Bulma [%] | Kutu [px] | Kilit kaybı | Konum hatası [m] | Köşe yaklaşması [m] | Yaklaşma payı [m] | Kadraj dışı alttan / yandan [s] | RTF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 30° · 6 m / 10.4 m | geçti | 4.1 (3.6–4.5) | 2.6 (2.2–3.3) | 0/3 | 93 (91–96) | 0.9 (0.8–1.0) | 84 (82–86) | 248 (244–250) | 1.0 (1.0–1.0) | 0.41 (0.30–0.50) | 6.3 (5.9–6.8) | 5.1 | 0.9 (0.8–1.0) / 0.1 (0.0–0.4) | 0.89 (0.89–0.90) |
| 35° · 7 m / 10 m | en az yatay mesafe 1.60 m < 3 m; kişi sonda kaybedildi (1/3 koşu) | 3.3 (1.6–4.2) | 3.3 (2.7–4.4) | 1/3 | 84 (64–94) | 3.5 (0.9–8.5) | 76 (74–77) | 235 (232–238) | 1.7 (1.0–3.0) | 0.32 (0.23–0.37) | 6.7 (5.8–8.4) | 4.8 | 3.2 (0.9–7.7) / 0.9 (0.0–2.7) | 0.92 (0.85–0.97) |
| 35° · 8 m / 11.4 m | geçti | 5.2 (4.9–5.6) | 1.8 (1.3–2.1) | 0/3 | 94 (94–95) | 0.9 (0.8–1.1) | 71 (67–75) | 207 (206–208) | 1.7 (1.0–2.0) | 0.36 (0.34–0.37) | 6.2 (5.8–6.5) | 5.5 | 0.9 (0.8–1.1) / 0.0 (0.0–0.0) | 0.92 (0.89–0.95) |
| 35° · 9 m / 12.9 m | geçti | 6.2 (5.8–7.0) | 0.4 (0.0–0.7) | 0/3 | 95 (95–95) | 1.1 (0.8–1.3) | 62 (62–64) | 179 (178–180) | 3.3 (2.0–4.0) | 0.41 (0.35–0.46) | 6.7 (5.9–7.1) | 6.3 | 1.1 (0.8–1.3) / 0.0 (0.0–0.0) | 0.93 (0.89–0.99) |
| 37.5° · 7 m / 9.1 m | en az yatay mesafe 1.96 m < 3 m; kişi sonda kaybedildi (1/3 koşu) | 2.6 (2.0–3.0) | 3.5 (3.4–3.8) | 1/3 | 75 (61–88) | 3.9 (1.3–9.1) | 68 (62–73) | 239 (234–244) | 2.3 (1.0–4.0) | 0.29 (0.26–0.35) | 6.5 (6.1–7.1) | 4.4 | 1.8 (1.3–2.2) / 3.8 (0.0–9.3) | 0.92 (0.91–0.93) |
| 37.5° · 8 m / 10.4 m | en az yatay mesafe 2.89 m < 3 m | 3.7 (2.9–4.2) | 3.2 (2.7–3.8) | 0/3 | 94 (92–95) | 1.2 (1.0–1.4) | 69 (65–72) | 215 (214–216) | 3.0 (1.0–4.0) | 0.28 (0.25–0.33) | 6.7 (6.2–7.5) | 5.0 | 1.2 (1.0–1.4) / 0.2 (0.0–0.5) | 0.97 (0.92–1.00) |
| 37.5° · 8 m / 11.4 m | geçti | 4.9 (3.7–5.6) | 2.0 (1.1–3.4) | 0/3 | 91 (91–92) | 0.9 (0.7–1.2) | 69 (67–71) | 205 (204–206) | 2.3 (1.0–3.0) | 0.38 (0.35–0.39) | 6.5 (5.8–7.7) | 6.0 | 0.9 (0.7–1.2) / 0.0 (0.0–0.0) | 0.96 (0.90–1.00) |
| 37.5° · 9 m / 12.9 m | geçti | 6.7 (6.4–6.8) | 0.0 (0.0–0.0) | 0/3 | 91 (90–92) | 0.8 (0.8–0.9) | 62 (59–65) | 181 (180–182) | 4.0 (3.0–5.0) | 0.37 (0.35–0.40) | 6.2 (6.1–6.5) | 6.9 | 0.8 (0.8–0.9) / 0.0 (0.0–0.0) | 0.92 (0.88–0.96) |
| 45° · 10 m / 10 m | en az yatay mesafe 2.22 m < 3 m; kişi sonda kaybedildi (2/3 koşu) | 3.1 (2.2–3.8) | 3.9 (2.9–4.8) | 2/3 | 75 (64–92) | 3.7 (1.2–8.2) | 39 (35–48) | 173 (168–180) | 5.7 (4.0–7.0) | 0.29 (0.21–0.38) | 6.9 (6.2–7.8) | 5.1 | 3.1 (1.2–5.8) / 2.1 (0.0–3.9) | 0.95 (0.87–1.00) |

- **Kapıyı 3/3 geçen beş ayar:** 30° 6/10.4, 35° 8/11.4, **35° 9/12.9**, 37.5° 8/11.4, **37.5° 9/12.9**. Geçmeyenler:
  37.5° 7/9.1 (köşede 1.96 m, bir koşuda kişi kaybedildi), 35° 7/10 (1.60 m, bir kayıp; 13.11'de 3/3 geçmişti),
  37.5° 8/10.4 (2.89 m, kişi hep izlendi), 45° 10/10 (2.22 m, iki kayıp).
- **37.5°'de mesafe belirleyici:** merkez mesafesiyle (d = h / tan 37.5° = 1.30 h: 9.1 ve 10.4 m) uçan iki ayar köşede
  yaklaşma payını aştı (pay 4.4 / 5.0 m, köşe yaklaşması 6.5 / 6.7 m) ve kapıdan kaldı; 1.43 h'de (11.4 ve 12.9 m)
  ikisi de geçti. 13.11'deki bulgunun aynısı: köşede stok Follow Me ≈ 6.2 m yaklaşıyor ve bu mesafeyle ölçeklenmiyor
  (bölüm 8), kişiyi tutan açı değil geride durma mesafesi.
- Model 9 m'de kişiyi %62 buluyor (kutu ≈ 180 px), 8 m'de %69–71 (≈ 206 px), 6 m'de %84 (248 px): aşama 1'deki
  "yükseldikçe algılama düşer" eğilimi.

**Kuralın sonucu** (bölüm 3, değişmeden; grup puanları kapıyı 3/3 geçen beş ayar arasında ölçeklendi; `+` ≥ 0.67,
`−` ≤ 0.33):

| Sıra | Bileşim | Kapı (takip yolu) | Güv. | Sür. | Alg. | Konum | Salın. | Köşe | Geo. | Toplam | Sim | Kıvrımlı yol: kapı / izlendi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 37.5° · 9 m / 12.9 m | geçti | + 1.00 | ○ 0.40 | − 0.01 | ○ 0.62 | ○ 0.43 | ○ 0.33 | + 0.99 | 0.54 | 0.46 | ✗ / 1/3 |
| 2 | 35° · 8 m / 11.4 m | geçti | ○ 0.58 | ○ 0.64 | ○ 0.41 | + 0.94 | − 0.17 | − 0.26 | + 0.78 | 0.54 | 0.50 | ✗ / 2/3 |
| 3 | 37.5° · 8 m / 11.4 m | geçti | − 0.21 | ○ 0.39 | ○ 0.35 | + 0.69 | ○ 0.40 | ○ 0.47 | + 0.89 | 0.48 | 0.42 | ✗ / 2/3 |
| 4 | 30° · 6 m / 10.4 m | geçti | − 0.00 | ○ 0.62 | + 1.00 | ○ 0.50 | ○ 0.67 | ○ 0.33 | − 0.00 | 0.45 | 0.52 | ✗ / 2/3 |
| 5 | 35° · 9 m / 12.9 m | geçti | + 0.89 | − 0.24 | − 0.00 | − 0.04 | ○ 0.42 | − 0.19 | + 0.88 | 0.38 | 0.30 | geçti / 3/3 |
| ✗ | 37.5° · 7 m / 9.1 m | en az yatay mesafe 1.96 m < 3 m; kişi sonda kaybedildi (1/3 koşu) | − 0.00 | − 0.11 | ○ 0.58 | + 1.00 | ○ 0.37 | ○ 0.56 | + 0.78 | 0.49 | 0.44 | ✗ / 0/3 |
| ✗ | 35° · 7 m / 10 m | en az yatay mesafe 1.60 m < 3 m; kişi sonda kaybedildi (1/3 koşu) | − 0.00 | − 0.16 | + 0.72 | + 1.00 | ○ 0.49 | − 0.29 | ○ 0.66 | 0.47 | 0.44 | ✗ / 2/3 |
| ✗ | 37.5° · 8 m / 10.4 m | en az yatay mesafe 2.89 m < 3 m | − 0.00 | − 0.20 | ○ 0.42 | + 1.00 | ○ 0.34 | − 0.30 | + 0.89 | 0.45 | 0.38 | ✗ / 0/3 |
| ✗ | 45° · 10 m / 10 m | en az yatay mesafe 2.22 m < 3 m; kişi sonda kaybedildi (2/3 koşu) | − 0.00 | − 0.00 | − 0.00 | + 1.00 | ○ 0.42 | ○ 0.33 | + 1.00 | 0.39 | 0.29 | ✗ / 0/3 |

Duyarlılık (kuralın kendi denemeleri, bölüm 3):

- eşit: 37.5° · 9 m / 12.9 m (0.54) > 35° · 8 m / 11.4 m (0.54) > 37.5° · 8 m / 11.4 m (0.48) > 30° · 6 m / 10.4 m (0.45) > 35° · 9 m / 12.9 m (0.38)
- güvenlik ×2: 37.5° · 9 m / 12.9 m (0.60) > 35° · 8 m / 11.4 m (0.54) > 37.5° · 8 m / 11.4 m (0.45) > 35° · 9 m / 12.9 m (0.45) > 30° · 6 m / 10.4 m (0.39)
- algılama ×2: 35° · 8 m / 11.4 m (0.52) > 30° · 6 m / 10.4 m (0.51) > 37.5° · 9 m / 12.9 m (0.47) > 37.5° · 8 m / 11.4 m (0.47) > 35° · 9 m / 12.9 m (0.34)
- sim puanı (geometrisiz): 30° · 6 m / 10.4 m (0.52) > 35° · 8 m / 11.4 m (0.50) > 37.5° · 9 m / 12.9 m (0.46) > 37.5° · 8 m / 11.4 m (0.42) > 35° · 9 m / 12.9 m (0.30)

- Kuralın birincisi **37.5° 9/12.9** (0.540), ikincisi 35° 8/11.4 (0.539): fark 0.001, yani berabere. Duyarlılık
  denemelerinde sıra değişiyor (güvenlik ×2'de 37.5° 9/12.9, algılama ×2'de 35° 8/11.4, sim puanında 30° 6/10.4
  önde). Kural bu beş ayarı birbirinden sağlam biçimde ayırmıyor; son seçimin 2–4. adımları (17.1) bunun için.
- **35° 9/12.9 beşinci (0.38)** ama ham değerleri 37.5° 9/12.9'unkine çok yakın (aynı yükseklik ve mesafe): ayrıntı
  bölüm 18'de.

### 17.4 Aşama 2, kıvrımlı yol (`asama3_kivrimli`): ek kapı

Koşular 13.11 22:25–22:48 (İş 1'in üç yeniden koşusu, bölüm 16.4) ve 14.11 00:34–01:30 (altı bileşim). 45° 10/10'un
koşusu 01:14'te önceki ajan durdurulunca yarıda kaldı; `tarama.py kos` aynı komutla 01:22'de baştan koştu, yarım klasör
`kivrimli_yuruyus_e45_h10_d10.0_yarim_012231` olarak ayrıldı ve özetlere girmedi. 27 koşu, hepsi GEÇTİ (koşu sonucu).

| Bileşim (3 koşu) | Kapı | En az mesafe [m] | < 6 m [%] | Kişi kaybı | Kadrajda [%] | En uzun kayıp [s] | Bulma [%] | Kutu [px] | Kilit kaybı | Konum hatası [m] | Köşe yaklaşması [m] | Yaklaşma payı [m] | Kadraj dışı alttan / yandan [s] | RTF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 30° · 6 m / 10.4 m | kişi sonda kaybedildi (1/3 koşu) | 6.1 (5.5–6.5) | 0.5 (0.0–1.5) | 1/3 | 87 (66–97) | 3.4 (0.0–10.3) | 85 (82–88) | 248 (240–252) | 0.7 (0.0–2.0) | 0.32 (0.26–0.36) | 4.2 (3.7–4.9) | 5.1 | 3.0 (0.0–9.1) / 0.4 (0.0–1.3) | 0.92 (0.91–0.92) |
| 35° · 7 m / 10 m | kişi sonda kaybedildi (1/3 koşu) | 4.9 (4.0–5.7) | 3.0 (1.3–4.7) | 1/3 | 83 (69–97) | 3.5 (0.0–8.8) | 82 (76–86) | 235 (232–238) | 2.3 (0.0–5.0) | 0.44 (0.41–0.47) | 5.0 (4.3–6.0) | 4.8 | 3.1 (0.0–8.0) / 1.7 (0.0–3.4) | 0.97 (0.92–1.00) |
| 35° · 8 m / 11.4 m | kişi sonda kaybedildi (1/3 koşu) | 6.7 (6.0–7.5) | 0.3 (0.0–1.0) | 1/3 | 89 (74–99) | 2.6 (0.0–7.3) | 75 (70–79) | 201 (198–202) | 1.3 (0.0–3.0) | 0.40 (0.38–0.42) | 4.7 (3.9–5.4) | 5.5 | 0.7 (0.0–1.8) / 2.0 (0.0–6.0) | 0.91 (0.89–0.92) |
| 35° · 9 m / 12.9 m | geçti | 8.1 (8.0–8.3) | 0.0 (0.0–0.0) | 0/3 | 98 (97–100) | 0.0 (0.0–0.0) | 68 (66–69) | 178 (178–178) | 2.3 (2.0–3.0) | 0.45 (0.44–0.45) | 4.8 (4.6–4.9) | 6.3 | 0.0 (0.0–0.0) / 0.0 (0.0–0.0) | 0.93 (0.88–1.00) |
| 37.5° · 7 m / 9.1 m | kişi sonda kaybedildi (3/3 koşu) | 5.5 (5.4–5.7) | 2.8 (2.0–4.2) | 3/3 | 71 (68–74) | 8.8 (8.0–9.3) | 82 (78–85) | 240 (236–244) | 1.0 (1.0–1.0) | 0.29 (0.27–0.33) | 3.6 (3.4–3.7) | 4.4 | 7.3 (6.0–8.3) / 1.6 (1.0–2.1) | 0.90 (0.89–0.91) |
| 37.5° · 8 m / 10.4 m | kişi sonda kaybedildi (3/3 koşu) | 6.1 (4.8–7.1) | 1.2 (0.0–3.5) | 3/3 | 74 (73–75) | 7.5 (7.3–7.9) | 73 (69–80) | 208 (208–208) | 2.0 (1.0–3.0) | 0.31 (0.28–0.34) | 4.2 (3.2–5.6) | 5.0 | 4.8 (4.3–5.4) / 3.4 (2.8–3.7) | 0.93 (0.89–0.99) |
| 37.5° · 8 m / 11.4 m | kişi sonda kaybedildi (1/3 koşu) | 6.3 (5.8–6.9) | 0.4 (0.0–1.3) | 1/3 | 86 (67–96) | 2.8 (0.0–8.5) | 74 (72–76) | 203 (198–206) | 2.0 (0.0–5.0) | 0.40 (0.33–0.44) | 5.1 (4.5–5.6) | 6.0 | 2.6 (0.0–7.9) / 0.4 (0.0–1.3) | 0.91 (0.90–0.91) |
| 37.5° · 9 m / 12.9 m | kişi sonda kaybedildi (2/3 koşu) | 6.8 (5.7–7.4) | 0.4 (0.0–1.1) | 2/3 | 81 (70–95) | 5.0 (0.0–7.8) | 67 (65–69) | 178 (176–180) | 3.0 (1.0–4.0) | 0.36 (0.30–0.42) | 6.1 (5.5–7.2) | 6.9 | 4.6 (0.0–7.5) / 0.9 (0.0–1.7) | 0.92 (0.91–0.92) |
| 45° · 10 m / 10 m | kişi sonda kaybedildi (3/3 koşu) | 4.9 (3.5–5.9) | 3.2 (1.7–4.3) | 3/3 | 72 (71–74) | 8.8 (8.2–9.7) | 68 (64–71) | 179 (178–180) | 3.3 (3.0–4.0) | 0.35 (0.26–0.49) | 5.1 (4.1–6.5) | 5.1 | 8.5 (8.3–8.8) / 0.2 (0.0–0.5) | 0.94 (0.91–0.99) |

- **Yalnız 35° 9/12.9 3/3 geçti:** kişi üç koşuda da sonuna kadar izlendi ve **kadrajdan hiç çıkmadı** (en uzun kayıp
  0 s, kişinin tamamı %98 kadrajda), en az mesafe 8.0–8.3 m. Aynı yükseklik ve mesafede **37.5° 9/12.9 üç koşunun
  ikisinde kişiyi kaybetti** (kadrajın altından 6.3–7.5 s).
- 35° 8/11.4, 37.5° 8/11.4, 30° 6/10.4 ve 35° 7/10 üç koşunun ikisinde; 37.5° 7/9.1, 37.5° 8/10.4 ve 45° 10/10 hiçbirinde
  kişiyi tutamadı.
- **Kayıplar hep 164° geri dönüşte:** kişi geri dönüp drona doğru yürürken, dron kişinin yeni arkasına dönene kadar kişi
  kadrajın altından çıkıyor (87–91 s; son `FOLLOW_TARGET` 85.9–88.5 s). Kaybedilen 15 koşunun hepsinde dron bundan
  sonra burnunu 10.6–18.8° kaldırdı (izlenen 12 koşuda en çok 3.7–8.9°); bu büyük kalkış çoğu koşuda kişi kadrajdan
  **çıktıktan sonra** (PX4'ün kestirimi bayatlayınca dron frenliyor): kaybın nedeni değil, izi gibi görünüyor; bu veriyle
  ayrılamıyor (repo dışı `zamanlama.py`, `fren.py`). m15 için not: geri dönüşte dronun kişiye doğru
  ilerlemeyi sürdürmesi kişiyi kadrajın altına itiyor; en az mesafe koruması ve geri dönüşün hızlı kestirimi (m11) bunu
  küçültür.
### 17.5 Ek koşular: montaj toleransı ve kıvrımlı yolun gürültüsü (14.11, 01:35'te, sonuçlar görülmeden yazıldı)

Aşama 2'nin iki yolu bitince (45° 10/10'un kıvrımlı koşusu yarıda kesilmişti, 01:23'te yeniden koşuldu) kuralın
sırasıyla (17.1, "Son seçim") seçilen ayar **35° · 9 m / 12.9 m** çıktı: takip yolunda 3/3 kapıyı geçen beş ayarın
kıvrımlı yolda da 3/3 geçen tek ayarı (bölüm 18). Seçim bu üç koşuyla verilir ve değişmez. İki ek koşu dizisi
seçimi değiştirmek için değil, sağlamlığını ölçmek için:

1. **Montaj toleransı** (17.1'deki `asama3_duyarlilik`): seçilen yükseklik ve mesafede eğim ±2.5°. 37.5° · 9/12.9
   aşama 2'de iki yolda zaten koşuldu (tekrarlanmaz); **32.5° · 9/12.9** iki yolda 3'er koşu (`asama3_duyarlilik`,
   `asama3_duyarlilik_kivrimli`).
2. **Kıvrımlı yolun gürültüsü:** üç koşuluk kapı gürültülü (35° 8/11.4 13.11'de 3/3, düzeltmeden sonra 2/3). Seçimi
   belirleyen iki komşu, **35° 9/12.9** ve **37.5° 9/12.9** (kuralın puanla birincisi), kıvrımlı yolda 3'er koşu daha
   (`asama3_kivrimli_ek`).

**Önceden yazılan okuma:**
- Kıvrımlı yolda 6 koşunun toplamında 37.5° 9/12.9, 35° 9/12.9 kadar ya da daha çok koşuda kişiyi sonuna kadar
  izlerse: "kıvrımlı yolda iki açı arasında fark bulunamadı" yazılır, gerçek uçuş önerisinde açı **35–37.5°** aralığı
  olur; simin varsayılanı kuralın sonucu (35°) kalır. 35° daha çok koşuda izlerse gerçek uçuş önerisi 35°'dir ve
  toleransın dik (büyük açı) tarafı daha dar yazılır.
- Tolerans: 32.5° ve 37.5° iki yolun bütün koşularında kapıyı (≥ 3 m ve kişi sonuna kadar izlendi) geçerse "±2.5°'lik
  montaj hatası simde sonucu değiştirmedi"; geçmezse hangi tarafta, hangi yolda ve kişinin kadrajın neresinden
  çıktığı yazılır.
- Hepsi aynı kodla (İş 1'in düzeltmesinden sonraki çalışma ağacı, varsayılanlar henüz değişmeden), videolu.

**Sonuçlar** (14.11, 01:31–02:02; 12 koşu, hepsi GEÇTİ; aynı kod, videolu):

Montaj toleransı, takip yolu (`asama3_duyarlilik`):

| Bileşim (3 koşu) | Kapı | En az mesafe [m] | < 6 m [%] | Kişi kaybı | Kadrajda [%] | En uzun kayıp [s] | Bulma [%] | Kutu [px] | Kilit kaybı | Konum hatası [m] | Köşe yaklaşması [m] | Yaklaşma payı [m] | Kadraj dışı alttan / yandan [s] | RTF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 32.5° · 9 m / 12.9 m | geçti | 6.5 (5.4–7.4) | 0.5 (0.0–1.5) | 0/3 | 95 (95–96) | 1.2 (1.1–1.4) | 61 (59–66) | 179 (178–180) | 4.0 (3.0–5.0) | 0.39 (0.34–0.41) | 6.4 (5.5–7.5) | 5.7 | 1.2 (1.1–1.4) / 0.0 (0.0–0.0) | 0.94 (0.91–1.00) |

Montaj toleransı, kıvrımlı yol (`asama3_duyarlilik_kivrimli`):

| Bileşim (3 koşu) | Kapı | En az mesafe [m] | < 6 m [%] | Kişi kaybı | Kadrajda [%] | En uzun kayıp [s] | Bulma [%] | Kutu [px] | Kilit kaybı | Konum hatası [m] | Köşe yaklaşması [m] | Yaklaşma payı [m] | Kadraj dışı alttan / yandan [s] | RTF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 32.5° · 9 m / 12.9 m | kişi sonda kaybedildi (1/3 koşu) | 7.5 (5.5–9.0) | 1.0 (0.0–2.9) | 1/3 | 92 (78–99) | 2.2 (0.0–6.0) | 70 (69–72) | 177 (176–178) | 3.0 (2.0–4.0) | 0.36 (0.25–0.48) | 5.4 (3.9–7.4) | 5.7 | 2.4 (0.0–7.0) / 0.2 (0.0–0.3) | 0.92 (0.91–0.92) |

Kıvrımlı yol, ek 3'er koşu (`asama3_kivrimli_ek`):

| Bileşim (3 koşu) | Kapı | En az mesafe [m] | < 6 m [%] | Kişi kaybı | Kadrajda [%] | En uzun kayıp [s] | Bulma [%] | Kutu [px] | Kilit kaybı | Konum hatası [m] | Köşe yaklaşması [m] | Yaklaşma payı [m] | Kadraj dışı alttan / yandan [s] | RTF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 35° · 9 m / 12.9 m | kişi sonda kaybedildi (1/3 koşu) | 7.1 (5.4–8.2) | 0.7 (0.0–2.2) | 1/3 | 90 (72–99) | 2.8 (0.0–8.4) | 71 (70–71) | 176 (172–178) | 3.0 (3.0–3.0) | 0.45 (0.37–0.50) | 5.8 (4.7–7.5) | 6.3 | 2.6 (0.0–7.8) / 0.0 (0.0–0.1) | 1.00 (1.00–1.00) |
| 37.5° · 9 m / 12.9 m | kişi sonda kaybedildi (3/3 koşu) | 7.2 (6.2–7.9) | 0.0 (0.0–0.0) | 3/3 | 71 (70–73) | 7.7 (6.8–8.5) | 62 (59–66) | 175 (172–176) | 4.7 (3.0–6.0) | 0.34 (0.30–0.38) | 5.7 (5.0–6.7) | 6.9 | 5.9 (2.4–7.9) / 2.5 (0.6–5.6) | 0.91 (0.90–0.92) |

**Okuma (önceden yazılan kurala göre):** kıvrımlı yolda 6 koşunun toplamında 35° 5/6, 37.5° 1/6 koşuda kişiyi sonuna kadar izledi. 35° daha çok koşuda izlediği için gerçek uçuş önerisi **35°**'dir ve toleransın dik (büyük açı) tarafı daha dar yazılır.

**Tolerans:** ±2.5°'lik montaj hatası **takip yolunda sonucu değiştirmedi** (32.5° 3/3, 37.5° 4/4 koşuda kapı). Kıvrımlı yolun 164° geri dönüşünde iki taraf farklı: **32.5° 3 koşunun 2'sinde** kişiyi tuttu (kayıpta kişi kadrajın altından çıktı, 7.0 s), 35°'nin 6'da 5'ine yakın; **37.5° 6 koşunun yalnız 1'inde** tuttu (5 kayıp: dördünde kişi kadrajın altından 6.3–7.9 s, birinde yandan 5.6 s). Yani yatık tarafa (32.5°) 2.5°'lik sapma simde belirgin bir fark yaratmadı, dik tarafa (37.5°) sapma ani geri dönüşü belirgin kötüleştirdi. 6'ya 6 koşuda 5/6 ile 1/6 tek başına kesin bir kanıt değil (iki yönlü Fisher kesin testi p ≈ 0.08), ama yön iki ayrı dizide aynı (ilk 3 koşuda 3/3 ile 1/3, ek 3 koşuda 2/3 ile 0/3).

**İki yolun ve iki günün bütün koşularında** (düzeltmeden sonra): 35° · 9/12.9 10 koşunun 9'unda, 37.5° · 9/12.9 10'un 5'inde, 32.5° · 9/12.9 6'nın 5'inde kapıyı geçti (tablo bölüm 18'in sonunda). Seçim (bölüm 18) değişmedi: kural ilk üç koşuyla uygulandı (17.1, 17.5).

## 18. Son karar (İş 2, 14.11): kamera 35°, 9 m yükseklik, 12.9 m geride

**Kısaca:** Seçilen ayar **kamera 35° aşağı, dron 9 m yükseklikte, kişinin 12.9 m gerisinde** (`FLW_TGT_HT 9`,
`FLW_TGT_DST 12.9`; geride durma = yükseklik / tan 35° ≈ 1.43 × yükseklik: kişi düz uçuşta görüntünün ortasında).
Koşulardan önce yazılan son seçim sırasıyla (17.1) verildi: takip yolunda kapıyı 3/3 geçen beş ayarın kıvrımlı yolda
da 3/3 geçen tek ayarı. Kuralın puanla birincisi 37.5° · 9/12.9 (aynı yükseklik ve mesafe); takip yolunda ikisi
pratikte eşit, kıvrımlı yolda 37.5° kişiyi kaybetti. Simin varsayılanı bu ayar oldu (bölüm 20); gerçek uçuş önerisi
bölüm 19'da (doğrulanmadı).

**Son seçimin dört adımı (17.1'deki sırayla, sonuçlar görülmeden yazıldı):**

| Adım | Ölçüt | 37.5° · 9/12.9 | 35° · 8/11.4 | 37.5° · 8/11.4 | 30° · 6/10.4 | **35° · 9/12.9** |
|---|---|---|---|---|---|---|
| 1 | Kural (takip yolu, toplam puan; sıra) | **0.540 (1)** | 0.539 (2) | 0.485 (3) | 0.445 (4) | 0.383 (5) |
| 2 | Güvenlik: köşede en az mesafe [m] / kaydın 6 m altı [%] | **6.4–6.8 / 0.0** | 4.9–5.6 / 1.8 | 3.7–5.6 / 2.0 | 3.6–4.5 / 2.6 | 5.8–7.0 / 0.4 |
| 3 | İki yolda 3/3 (kıvrımlı yolun kapısı) | ✗ (kıvrımlı 1/3) | ✗ (2/3) | ✗ (2/3) | ✗ (2/3) | **✓ (3/3)** |
| 4 | Algılama: bulma [%] / kutu [px] (takip yolu) | 62 / 181 | 71 / 207 | 69 / 205 | **84 / 248** | 62 / 179 |

Adım 3'ü yalnız 35° · 9/12.9 sağladı; adım 2'de ikinci, adım 4'te sonuncu (37.5° 9/12.9 ile eşit). 13.11'deki gibi
(bölüm 6) "iki yolda 3/3" kuralın puanından önce geldi; kural koşulardan önce böyle yazılmıştı.

**Kuralın birincisinden (37.5° · 9/12.9) neden ayrıldı, sayılarla:**

| Takip yolu, 3 koşu (ort.) | 37.5° · 9/12.9 | 35° · 9/12.9 | Fark | Puan farkı (min–maks, 5 ayar arasında) |
|---|---|---|---|---|
| Köşede en az mesafe | 6.66 m | 6.24 m | 0.4 m | güvenlik 1.00 / 0.89 |
| Kişinin tamamı kadrajda | %91.4 | **%94.8** | 3.4 puan 35° lehine | (süreklilik içinde) 0 / 1 |
| En uzun kayıp | 0.84 s | 1.11 s | 0.28 s | 1 / 0 |
| Kilit kaybı | 4.0 | **3.3** | 0.7 35° lehine | 0 / 0.22 |
| Gerçekten görünür | %97.8 | %96.8 | 1 puan | 1 / 0 → süreklilik 0.40 / 0.24 |
| Modelin bulma oranı / kişinin kutusu | %62.4 / 181 px | %62.5 / 179 px | yok | algılama 0.01 / 0.00 |
| Konum hatası ort. / p95 | 0.37 / 0.84 m | 0.41 / 0.96 m | 4 / 12 cm | konum 0.62 / 0.04 |
| Köşede yetişme / köşeden sonra arkada kalma | 2.3 s / 156° | 2.2 s / 161° | 0.1 s / 5° | köşe 0.33 / 0.19 |
| Ufuk payı (geometri) | 17.4° | 14.9° | 2.5° | geometri 0.99 / 0.88 |

- Takip yolunda iki ayar pratikte aynı: farklar birkaç santim, saniyenin onda biri ve 1–3 puan, yönleri karışık.
  0.54 / 0.38'lik puan farkını bu küçük farkları tam puana çeviren min–maks ölçekleme yapıyor (13.11'de görülen
  zayıflık, bölüm 6): 4 cm'lik konum farkı 0.62 / 0.04, 0.28 s'lik en uzun kayıp farkı 1 / 0 oluyor.
- **Kıvrımlı yolda:** 35° üç koşunun üçünde kişiyi tuttu (kişi kadrajdan hiç çıkmadı, en az 8.0–8.3 m), 37.5° ikisinde
  kaybetti (164° geri dönüşte kadrajın altından, 6.3–7.5 s). **Ek koşular (17.5) farkı doğruladı:** 3'er koşu daha,
  toplam 6 koşuda 35° 5, 37.5° yalnız 1 koşuda kişiyi tuttu; 37.5°'nin bütün kayıpları kadrajın altından.
- **Kayıp anı:** kişi drona doğru dönüp yürürken kişi 7–9.5 m uzakta görüntünün altından çıkıyor; kayıp koşularında
  dron bu sırada ya da hemen sonra burnunu 13–18° kaldırarak frenliyor (kamera onunla yukarı döner), 35°'nin izlenen
  koşularında burun en çok 4–7° kalktı. Frenin kaybın nedeni mi sonucu mu olduğu ayrılamıyor (17.4). 37.5°'de
  sert frenin neden daha sık olduğu bu veriyle ayrılamıyor (kıvrımlı yolda 37.5°'de modelin bulma oranı biraz düşük ve
  kilit daha sık düşüyor: %62–67 / 3.0–4.7 kez, 35°'de %68–71 / 2.3–3.0; PX4'ün kestirimi bu yüzden geri dönüşü geç ve
  sert yakalıyor olabilir, bu bir tahmindir).
- 37.5°'nin geometrik artıları gerçek: ufuk payı 2.5° daha büyük (17.4° / 14.9°: sert frende ya da rüzgârda gökyüzü
  kadraja daha geç girer), yaklaşma payı 0.6 m daha büyük (6.9 / 6.3 m; kişi görüntü merkezinin 4.5° üstünde, 35°'de 2.0°
  üstünde). Simde bunlar kıvrımlı yolda kişiyi tutmaya dönüşmedi.
- **Kullanıcının tahmini ("37.5°, 30 ile 45'in ortası, en iyi olabilir"):** takip yolunda doğru çıktı (kuralın
  birincisi; 7–10 m'deki sekiz 37.5° bileşiminin hepsi aşama 1'de kapıyı geçti, aşama 2'de 1.43 h'dekiler 3/3); son
  seçimi kıvrımlı yolun sert geri dönüşü belirledi ve orada 37.5° 6 koşunun 5'inde kişiyi kaybetti (35° 1'inde).
  Simde 37.5° köşe ve düz yürüyüşte iyi, ani geri dönüşte zayıf.

**İkinci seçenek** (kural: farklı bir yükseklikteki en iyi): **35° · 8 m / 11.4 m** (13.11'in önerisi; aynı montaj,
yalnız iki parametre farklı): takip yolunda iki günde 7/7, kıvrımlı yolda 5/6 (düzeltmeden sonra 2/3); algılama daha iyi
(%71 / 207 px), köşede 1 m daha yakın (4.9–5.6 m); 8 m PX4'ün Follow Me için önerdiği alt sınır.

**Seçilenin bedeli:** algılama beşin en zayıfı (%62, kişi ≈ 179 px; model 640'lık girişte ≈ 50 px görüyor) ve kilit
daha sık düşüyor (3.3; 35° 8/11.4'te 1.7); dron kişinin 12.9 m gerisinde (görüş hattı 15.2 m, daha büyük boş alan);
konum hesabı zemin / GPS yüksekliği hatasına 1.43 kat duyarlı (45°'de 1.0); ufuk payı 14.9° (45°'de 24.9°); yeni
montaj parçası.

**45° · 10/10 (14.11'e kadarki varsayılan, başvuru):** düzeltmeden sonra iki yolun 6 koşusunun 1'inde kapıyı geçti
(takip yolu 1/3, kıvrımlı yol 0/3); bütün koşularında 13'te 3. Stok Follow Me ile hiçbir 45° ayarı seçilebilir değil.

**Bir ayarın bütün koşuları** (düzeltmeden önceki 13.11 koşuları ayrı; kapı = koşuda ≥ 3 m ve kişi sonuna kadar izlendi; repo dışı `karar_tablolari.py`):

| Ayar | Takip yolu, 13.11 (düzeltmeden önce) | Takip yolu, düzeltmeden sonra | Kıvrımlı yol, 13.11 | Kıvrımlı yol, düzeltmeden sonra | Kapı, düzeltmeden sonra | Kapı, hepsi |
|---|---|---|---|---|---|---|
| 30° · 6 m / 10.4 m | 4/4 (izlendi 4; en az 3.8–4.8 m) | 3/3 (izlendi 3; en az 3.6–4.5 m) | 1/3 (izlendi 1; en az 3.0–6.6 m) | 2/3 (izlendi 2; en az 5.5–6.5 m) | **5/6** | 10/13 |
| 32.5° · 9 m / 12.9 m | – | 3/3 (izlendi 3; en az 5.4–7.4 m) | – | 2/3 (izlendi 2; en az 5.5–9.0 m) | **5/6** | 5/6 |
| 35° · 7 m / 10 m | 4/4 (izlendi 4; en az 3.7–4.2 m) | 2/3 (izlendi 2; en az 1.6–4.2 m) | 1/3 (izlendi 1; en az 5.4–6.3 m) | 2/3 (izlendi 2; en az 4.0–5.7 m) | **4/6** | 9/13 |
| 35° · 8 m / 11.4 m | 4/4 (izlendi 4; en az 4.9–5.5 m) | 3/3 (izlendi 3; en az 4.9–5.6 m) | 3/3 (izlendi 3; en az 6.0–8.1 m) | 2/3 (izlendi 2; en az 6.0–7.5 m) | **5/6** | 12/13 |
| 35° · 9 m / 12.9 m | – | 4/4 (izlendi 4; en az 5.8–7.0 m) | – | 5/6 (izlendi 5; en az 5.4–8.3 m) | **9/10** | 9/10 |
| 37.5° · 7 m / 9.1 m | – | 1/4 (izlendi 3; en az 2.0–5.5 m) | – | 0/3 (izlendi 0; en az 5.4–5.7 m) | **1/7** | 1/7 |
| 37.5° · 8 m / 10.4 m | – | 3/4 (izlendi 4; en az 2.9–4.6 m) | – | 0/3 (izlendi 0; en az 4.8–7.1 m) | **3/7** | 3/7 |
| 37.5° · 8 m / 11.4 m | – | 4/4 (izlendi 4; en az 3.7–5.6 m) | – | 2/3 (izlendi 2; en az 5.8–6.9 m) | **6/7** | 6/7 |
| 37.5° · 9 m / 12.9 m | – | 4/4 (izlendi 4; en az 6.4–7.1 m) | – | 1/6 (izlendi 1; en az 5.7–7.9 m) | **5/10** | 5/10 |
| 45° · 10 m / 10 m | 2/4 (izlendi 3; en az 2.2–3.8 m) | 1/3 (izlendi 1; en az 2.2–3.8 m) | 0/3 (izlendi 0; en az 4.5–5.7 m) | 0/3 (izlendi 0; en az 3.5–5.9 m) | **1/6** | 3/13 |

**Ek koşular (17.5):** kıvrımlı yolda 3'er koşu daha: 35° toplam 5/6, 37.5° 1/6 (ek üç koşuda 2/3 ile 0/3); montaj toleransı 32.5° takip yolunda 3/3, kıvrımlı yolda 2/3. 35° kıvrımlı yolda belirgin daha sık tuttu (p ≈ 0.08, yön iki ayrı dizide aynı); gerçek uçuş önerisi 35° ve dik tarafa tolerans dar (bölüm 19). Seçim kuralla ilk üç koşudan verildi ve değişmedi.

## 19. Gerçek uçuş için önerilen ayar (doğrulanmamış; ilk saha uçuşunda doğrulanacak)

Kullanıcı (14.11): "Yalnız simin varsayılanı değil, gerçek hayat için de bir değer belirlemeye çalışıyoruz." Aşağıdaki
değerler **simde ölçülenlere dayanan bir öneridir; gerçek araçta hiçbiri ölçülmedi** ve montaj henüz yapılmadı. Sim
v0.2 modelini laptop işlemcisinde, PX4'ün stok Follow Me moduyla, rüzgârsız düz zeminde çalıştırdı; bu üçü gerçek
uçuşta farklı olacak (aşağıda).

> **Güncelleme (14.11 akşam, kullanıcı onayı):** yedek ayar 8 m / 11.4 m yerine **35° · 8 m / 12.9 m** (bölüm 21:
> iki yolda 6/6, köşede en az 6.8–8.4 m, kişi ≈ 190 px; 8/11.4 kıvrımlı yolda 3 koşunun 1'inde kişiyi kaybetti).
> Başlangıç ayarı değişmedi: 35° · 9 m / 12.9 m. Aşağıdaki tabloda "8 m'de 11.4 m" geçen yerler bu güncellemeden önceki
> haliyle bırakıldı.

| | Öneri | Aralık / tolerans | Simdeki dayanak |
|---|---|---|---|
| Montaj açısı (burnun altında) | **35°** | **hedef 35°, en çok +1°**: yatık tarafa 32.5°'ye kadar simde sorun yok (takip 3/3, kıvrımlı 2/3); dik tarafa 37.5° ani geri dönüşte kişiyi 6 koşunun 5'inde kaybettirdi; arası ölçülmedi | 35° · 9/12.9: düzeltmeden sonraki 10 koşunun 9'unda kapı (takip yolu 4/4, kıvrımlı 5/6); 37.5° · 9/12.9: 5/10 (kıvrımlı 1/6); 32.5° · 9/12.9: 5/6. Aynı 35° montajda 8 m / 11.4 m iki günde 12/13 |
| Uçuş yüksekliği (`FLW_TGT_HT`; m15'te `AF_` önekli yükseklik parametresi) | **9 m** | **8–9 m** | 35° montajda 8 m (11.4 m geride) iki günde 13 koşunun 12'sinde, 9 m (12.9 m) 10 koşunun 9'unda kapıyı geçti. 10 m'de model kişiyi %47–53, 12 m'de %0 buluyor (37.5°, aşama 1 ekleri; kişi ≈ 120 px'in altına iniyor). 8 m PX4'ün Follow Me için önerdiği alt sınır; altında başlara yakınlık artıyor |
| Geride durma (`FLW_TGT_DST`; m15'te `AF_` önekli mesafe parametresi) | **12.9 m** | **yükseklik / tan(açı) ≈ 1.43 × yükseklik**: 8 m'de 11.4 m, 9 m'de 12.9 m. Stok Follow Me ile **11.4 m'nin altına inme** | Köşede stok Follow Me ort. 6.2 m yaklaşıyor ve bu mesafeyle küçülmüyor (bölüm 8); kişiyi tutan pay (yaklaşma payı ≈ 0.49 × geride durma) bunu karşılamalı. 37.5° 1.30 h'de (9.1 ve 10.4 m) köşede 3 m'nin altına indi; 1.43 h'de (11.4 ve 12.9 m) geçti. 1.43 oranı kişiyi düz uçuşta görüntünün ortasında tutar |
| Açı ölçümü | araç düz zeminde, eğim ölçer ya da dama tahtasıyla (m09), **±0.5°**; ölçülen değer Pi'ye girilir | — | Ölçülmeyen 1°'lik hata 9 m / 12.9 m'de konumu ≈ 0.47 m, 2.5°'lik hata ≈ 1.2 m kaydırır (`duyarlilik_geometri.py`) |

**Montaj açısı ±2.5° yanlış olursa (geometri, düz uçuş, 9 m / 12.9 m):**

| Montaj | Görüntünün alt kenarı yerde [m] | Yaklaşma payı [m] | Kişi (gövde merkezi) görüntüde | Ufuk payı [°] | Açı ölçülmezse konum kayması [m] |
|---|---|---|---|---|---|
| 32.5° (−2.5°) | 7.19 | 5.71 | merkezin 0.5° (17 px) altı | 12.4 | 1.17 |
| 34° (−1°) | 6.81 | 6.09 | merkezin 1.0° (30 px) üstü | 13.9 | 0.47 |
| **35°** | **6.57** | **6.33** | **merkezin 2.0° (61 px) üstü** | **14.9** | 0 |
| 36° (+1°) | 6.34 | 6.56 | merkezin 3.0° (92 px) üstü | 15.9 | 0.47 |
| 37.5° (+2.5°) | 5.99 | 6.91 | merkezin 4.5° (138 px) üstü | 17.4 | 1.17 |

**Tolerans:** ±2.5°'lik montaj hatası **takip yolunda sonucu değiştirmedi** (32.5° 3/3, 37.5° 4/4 koşuda kapı). Kıvrımlı yolun 164° geri dönüşünde iki taraf farklı: **32.5° 3 koşunun 2'sinde** kişiyi tuttu (kayıpta kişi kadrajın altından çıktı, 7.0 s), 35°'nin 6'da 5'ine yakın; **37.5° 6 koşunun yalnız 1'inde** tuttu (5 kayıp: dördünde kişi kadrajın altından 6.3–7.9 s, birinde yandan 5.6 s). Yani yatık tarafa (32.5°) 2.5°'lik sapma simde belirgin bir fark yaratmadı, dik tarafa (37.5°) sapma ani geri dönüşü belirgin kötüleştirdi. 6'ya 6 koşuda 5/6 ile 1/6 tek başına kesin bir kanıt değil (iki yönlü Fisher kesin testi p ≈ 0.08), ama yön iki ayrı dizide aynı (ilk 3 koşuda 3/3 ile 1/3, ek 3 koşuda 2/3 ile 0/3).

**Simin temsil etmediği yanlar (öneriyi gerçek uçuşta değiştirebilecekler):**
- **Rüzgâr ve dronun eğilmesi:** simde rüzgâr yok. Gerçekte dron rüzgâra karşı ve frende burnunu eğer, kamera onunla
  döner. 35°'de ufuk payı 14.9° (frende burun 6–11° kalkıyor: 4–9° pay kalıyor; Ağustos uçuşlarında burun 11–18°, en
  çok 26° eğildi, kamera raporu). Rüzgârlı günde gökyüzü kadraja girebilir (otomatik pozlama yerdeki kişiyi karartır)
  ya da kişi görüntünün altına kayar.
- **GPS / baro yükseklik:** gerçek araçta yükseklik GPS'ten (`EKF2_HGT_REF 1`), hata yarım metreyi bulur; konum hesabı
  1.43 katıyla kayar (≈ 0.7 m). Simde dronun yüksekliği kusursuz.
- **Zemin eğimi:** kampüsteki çim %3–7 eğimli; düz zemin varsayımı 12.9 m'de %5 eğimde ≈ 0.65 m'lik zemin farkını
  ≈ 0.9 m'lik konum kaymasına çevirir. Simde zemin düz.
- **Gerçek kamera:** CM3'ün görüş açısı veri sayfasında %5 belirsiz (m09 kalibrasyonu); düşey yarı açı 1° farklıysa
  yakın sınır ≈ 0.25 m kayar. Otomatik pozlama, hareket bulanıklığı, rolling shutter ve lens bozulması simde yok (Görev
  Grubu 15).
- **Hailo:** model Hailo'ya dönüştürülünce (m07/m08) giriş boyutu ve nicemleme başka bir bulma oranı verir. Simde v0.2
  9 m / 12.9 m'de kişiyi %62 buldu (kişi ≈ 179 px); Hailo'da daha kötüyse ilk ayar düğmesi 8 m / 11.4 m'dir
  (%71, 207 px).
- **Stok Follow Me yerine m15 ("AUTO FOLLOW"):** köşedeki 6.2 m'lik yaklaşma ve 164° geri dönüşteki kayıplar stok modun
  davranışı. Ekipten gelen bilgiye göre (09.11, Yusuf Algan; kesinleşmiş değil) m15'in modu QGC'de "AUTO FOLLOW" adıyla
  görünecek, parametreleri `AF_` önekli olacak. m15'in en az mesafe koruması olursa geride durma kısaltılabilir;
  öneri m15 takılınca aynı taramayla (`tarama.py`) yeniden ölçülmeli.
- **İnsan, ışık, arka plan:** simde tek insan modeli (aynı beden, kel, yalınayak), tek güneş, iki dünya (bölüm 9).
- **Yasal:** insanların yakınında ve üstünde uçuş için SHGM kurallarına bakılmalı; bu belge yasal bir sayı vermez.

**İlk saha uçuşunda adım adım doğrulama planı (öneri; uçuş güvenliği ve sırası ekip kararı, m22/m25):**
1. **Montaj:** 35°'lik parçayı tak; araç düz zemindeyken açıyı ölç (eğim ölçer ya da dama tahtası, ±0.5°). 32.5–37.5°
   dışında çıkarsa parçayı düzelt; ölçülen değeri Pi'nin yapılandırmasına yaz (Vision, m10).
2. **Yerde görüntü kontrolü:** kamerayı yerden bilinen bir h' yükseklikte tut, kişi 1.43 × h' önünde dursun; kişi
   görüntünün ortasına yakın görünmeli (simde 9 m / 12.9 m'de gövde merkezi merkezin ≈ 60 px üstünde).
3. **Takipsiz hover (Position modu), 9 m:** kişi dronun 12.9 m önünde durur, sonra yürür ve döner. Görüntüyü ve ULog'u
   kaydet; bak: kişi görüntünün neresinde, boyu kaç piksel (simde ≈ 180 px), model (Hailo) onu ne sıklıkla buluyor
   (simde %62), ufuk kadrajın üst kenarına ne kadar yakın, rüzgârda burun ne kadar eğiliyor.
4. **Takip, önce yavaş:** stok Follow Me ya da hazırsa m15 ("AUTO FOLLOW"); sırayla yavaş yürüyüş → duruş → 90° dönüş;
   en son kısa koşu ve geri dönüş. Her adımda bak: köşede dron kişiye en çok ne kadar yaklaştı (simde stok modla en az
   5.8–7.0 m; 3 m'nin altı = dur), kişi kadrajdan çıktı mı, kilit kaç kez düştü.
5. **Karşılaştır:** aynı ölçütler (kişinin kadrajda kalma oranı, en az mesafe, bulma oranı, kişinin boyu) sim
   değerleriyle; ULog ve Vision kayıtlarından (m17). Commit'ler `tez-ucus-N` tag'iyle işaretlenir.
6. **Ayar düğmeleri (montajı değiştirmeden):** kişi küçük, model bulamıyor → 8 m / 11.4 m; köşede çok yaklaşıyor →
   geride durmayı artır (ör. 9 m'de 14 m; kişi görüntünün üst yarısına kayar). Ufuk sık kadraja giriyorsa montajı
   dikleştirmek ufuk payını artırır (37.5°'de +2.5°) ama simde ani geri dönüşte kişiyi daha sık kaybettirdi (6 koşuda
   5): önce rüzgârsız bir günde tekrarla; gerekirse yeni parçayla 36–37°'yi dene ve geri dönüşü ayrıca sına.

## 20. Simin varsayılanı değişti (İş 3, 14.11): 35° · 9 m / 12.9 m

Kullanıcının isteği (14.11, koordinatör üzerinden): seçilen ayar simin varsayılanı olsun; 45° senaryoları
karşılaştırma için tutarlı adla kalsın; `kalabalik_park` yeni açıyla anlamlı mı bakılsın; `gercek_dron.params`'a
dokunulmasın.

**Ne değişti:**
- **Kamera eğimi tek kaynaktan:** `kamera.NOMINAL_TILT_DEG = 35.0` ve `models/x500_tez/model.sdf`'te `camera_link`
  pitch'i 0.610865 rad (35°; yorumda karar 14.11, bu belge, "gerçek montaj henüz yapılmadı, takılınca açısı araçta
  ölçülür"). Test ikisini karşılaştırır. Varsayılanla uçan senaryo (`kamera` bloğu yok) modeli olduğu gibi kullanır
  (kopya yazılmaz); LOS (i) (`takip.NOMINAL_MOUNT`), düz zemin konum (`konumlama.NOMINAL_MOUNT`), yakın / uzak sınır
  (`olcum.frame_limits`), rapor, video (`video.Run`) ve taramanın yaklaşma ölçütü (`tarama.approach_numbers`, önceden
  sabit 45 yazılıydı) aynı sabitten. Önizleme araçlarının serbest kamerası (`onizleme.py`, `model_dene.py`
  `--kamera`) da varsayılan olarak bu açıyla bakar. İletilerdeki "gerçek montaj 45°" ifadesi "varsayılan montaj" oldu.
- **Eski koşular eski montajlarıyla kalır:** 14.11'den önceki koşuların `ozet.json`'unda `ayarlar.kamera` yok ve senaryo
  kopyalarında `kamera` bloğu yok; video yeniden çizilirken bunlar artık 35° sayılırdı. `video.run_tilt_deg`: eğim
  `ayarlar.kamera`'dan, yoksa Gazebo'nun kaydettiği montajdan (`kamera_montaji.dcm_optik_govde`, eski koşularda 45°),
  ikisi de yoksa senaryodan.
- **`takip_yuruyen`:** 9 m / 12.9 m, kamera varsayılan (dosyada `kamera` bloğu yok: tek kaynak), `FLW_TGT_RS 0.3`
  kalır. Yol `yuruyen_insan`'ınki, 2.9 m doğuya kaydırılmış: kişi dronun 12.9 m önünde başlar. Bu, taramanın
  `e35_h9_d12.9` senaryosunun aynısıdır (yol, zamanlama, takip bloğu; test karşılaştırır), yani `takip_yuruyen`
  koşuları taramanın o bileşimine eklenebilir.
- **45° montaj senaryoları:** `takip_yuruyen_45_10m` (14.11'e kadarki `takip_yuruyen`, 10 m / 10 m) ve
  `takip_yuruyen_45_8m` (eski adı `takip_yuruyen_8m`, 8 m / 8 m); ikisinde de `kamera: {egim_deg: 45}` dosyada yazılı
  (varsayılan bir daha değişse de 45°'de kalırlar), yol `yuruyen_insan`'ınki (14.11'e kadarki koşularla aynı).
  `takip_yuruyen_8m.yaml` kaldırıldı; eski belgelerdeki adı geçmiş kaydıdır.
- **`kalabalik_park`:** 35° kamerayla 10 m'de hedef başta durduğu yerde (7, −1) görüntünün altında kalıyordu (60 s
  boyunca; hedef yolunun %27'si kadrajda). Yükseklik simin uçuş yüksekliğine, **9 m**'ye indi: hedef yolunun her
  yerinde kadrajda (en kötü anda alt kenarın 61 px üstünde); diğer kişiler 45° / 10 m'dekine yakın: çapraz koşan,
  duran ve aynı kıyafetli %97–98 (45°'de %98–100), patikada yürüyen %21 (45°'de %12; o zaten çoğunlukla kadraj dışında
  yürüyor). Hesap testli (`test_varsayilan_montaj.py`) ve repo dışı `park_geo.py`. Kişiler biraz daha yakın ve daha
  yandan görünür: sayılar 13.11'in 45° / 10 m koşularıyla doğrudan karşılaştırılmaz (aşağıda).
- **Dokunulmayanlar:** `gercek_dron.params` (gerçek dronun 22.08 parametreleri, 8/8), PX4 / ROMFS / submodule
  dosyaları, Vision. `yuruyen_insan` ve `kivrimli_yuruyus` (takipsiz, 10 m) varsayılan kamerayla uçar; kişi başta
  görüntünün alt yarısında (yorum güncellendi). F0 ve F1 `yuruyen_insan`'ı kullanır.

**Testler (önce yazıldı, kırmızı → yeşil):** `testler/test_varsayilan_montaj.py` (5 test, biri iki senaryo için: 6 durum): varsayılanın tek
kaynağı ve modelin eğimi; `takip_yuruyen`'in ayarı ve taramanın yoluyla aynılığı; 45° senaryolarının adı, dosyadaki
eğimi ve yolu (iki senaryo); `kalabalik_park`'ta hedefin bütün yolda kadrajda olması (10 m'de başta olmadığı da); eski
bir koşunun videosunun kaydedilen montajla çizilmesi. Kod değişmeden önce 5'i başarısızdı (eski koşu testi 45°
varsayılanla zaten geçiyordu; varsayılan değişince düzeltme olmadan başarısız olur). Varsayılanı 45° sayan eski testler
(davranışlarını değil, yalnız bu yerlerini) güncellendi: `test_kamera_egimi.py` (varsayılan 35°, modelin pitch'i
0.610865, varsayılan montajla açı farkı 35 − 30 = 5°), `test_hedef.py` (`takip_yuruyen` 9 m / 12.9 m ve kaydırılmış
yol, 45° senaryolarının adları), `test_takip.py` (hakemin kamera montajı modelinki, yani varsayılan), `test_video.py`
(yerdeki izdüşüm varsayılan eğimle), `test_konumlama.py` (bir pozdaki yer noktası 35° kadrajda kalsın diye 7 m yerine
10 m önde), `test_olcum.py` (45° / 8 m'lik örnek koşu eğimini açıkça veriyor). Değişiklik önce temiz HEAD + İş 1'in bir
klonunda denendi, sonra çalışma ağacına uygulandı. **281 test geçti** (275 + 6); `ruff format --check` ve `ruff check`
temiz; `verify_pin.sh --worktree` KILIT SAGLAM.

**Doğrulama koşuları (yeni varsayılanla, 14.11 02:03–02:24, aynı kod):**

| Koşu | Sonuç | Sayılar |
|---|---|---|
| `tez/sim/araclar/f0_kabul.sh` | GEÇTİ | 21/21 başlangıç parametresi PX4'te dosyadaki değerde; kamera 2304×1296, 30.3 kare/sim-s, fx 1773.9, RTF 1.00; `SYS_AUTOSTART` 4001; "Hold" + "Follow Target" listede; 10 m'ye kalkış; Hold'da 15 s, sapma yatay 0.06 / dikey 0.09 m |
| `tez/sim/araclar/f1_kabul.sh` (`yuruyen_insan` ×2, `--modelsiz`, `--dogrula`, `yok`) | GEÇTİ | hedef doğrulama farkı en çok 0.13 / 0.13 m (sınır 0.30); iki koşu arası 10 ortak anda 0.000 m (sınır 0.15); RTF 0.946 / 0.946; kameranın yakın görüş sınırı 7.3 m (35°, 10 m). Not: kişinin gövde merkezi kadrajda %100 / %81: kişi yürüyüşün son 6 s'sinde görüntünün sol kenarında (merkez +18 / −18 px) ve dronun Hold'daki yönü iki koşuda 0.9° farklı; F1'in kapılarını etkilemez (45°'de kişi bu bölümde zaten kadraj dışındaydı) |
| `toplu.py --senaryo takip_yuruyen --tekrar 3` (`sonuclar/gorev17_varsayilan_takip_yuruyen_x3`) | GEÇTİ 3 | PX4'ten geri okunan `FLW_TGT_HT` 9, `FLW_TGT_DST` 12.9, `FLW_TGT_RS` 0.3; kişi sonuna kadar izlendi **3/3**, kapı (≥ 3 m ve izlendi) 3/3; en az yatay mesafe 6.63 (5.68–7.12) m; yatay mesafe ort. 12.08 (11.58–12.35) m; kaydın 6 m altı %1 (0–2); kişinin tamamı kadrajda %95 (92–96); en uzun kayıp 0.54 (0.00–0.86) s; modelin bulma oranı %62 (58–65); kilit kaybı 4.00 (3.00–5.00); konum hatası 0.36 (0.30–0.39) m; dron yüksekliği 8.97 (8.93–9.00) m; yakın sınır 6.55 (6.53–6.58) m; RTF 0.95 (0.92–1.00) |
| `toplu.py --senaryo kalabalik_park --tekrar 3` (`sonuclar/gorev17_varsayilan_kalabalik_park_x3`) | GEÇTİ 3 | dron yüksekliği 8.95 (8.92–9.01) m; hedefin tamamı kadrajda %99 (98–100), gövde merkezi %100 (100–100); gerçekten görünür %89 (84–93); bulma %64 (61–66); seçim doğru %49 (46–53); yanlış kişi %16 (12–19) (aynı kıyafetli %5 (0–7)); kilit kaybı 1.67 (1.00–3.00); `model_ms` 87.95 (87.08–89.43); RTF 0.85 (0.85–0.86) |

Hepsinde model dosyası doğrudan `models/x500_tez/model.sdf` (kopya yok), Gazebo'nun bildirdiği eğim 34.99999°;
`TEZ_LOS` ULog / gönderilen 353/352, 312/312, 347/347, 388/388, 382/382, 378/378; hakem %95 ≤ 52 ms, hakemi sonradan gelen kilitsiz kare en çok 1 (kaydın ilk
karesi). Videolar h264 / yuv420p / 2000×720 (`ffprobe`).

**Okuma:**
- `takip_yuruyen` yeni varsayılanla taramanın `e35_h9_d12.9` bileşiminin aynısı ve sonuç da aynı çıktı (17.3'te en az
  6.2 (5.8–7.0) m, bulma %62, kadrajda %95, kişi 3/3 izlendi); takip yolunda bu ayar artık 7 koşunun 7'sinde kapıyı
  geçti. 14.11'e kadarki 45° 10/10 takip yolunda 11 koşuda 8'inde kişiyi izlemişti (en az 2.2–6.4 m).
- `kalabalik_park` (45° / 10 m'deki koşular, 9. grup ×3 + iş A: bulma %71–73, seçim doğru %61–66, yanlış kişi %6–12,
  aynı kıyafetli %0–8, görünür %80–81): 35° / 9 m'de hedef yine hep kadrajda ve ağacın arkasında daha az kalıyor
  (görünür %89), ama **yanlış kişiye geçme arttı** (%16; seçim doğru %49): daha yatık bakışta kişiler görüntüde daha
  çok üst üste biniyor. Karışma anları 78.7–85.5 s (çoğu `insan3`, sarı üstlü, hedefin yanında duran / yavaş yürüyen;
  bir kısmı `insan4`, hedefle aynı kıyafetli). Senaryo amacına (karıştırma ve örtülme ölçümü) hâlâ uygun, sayılar 45°
  koşularıyla doğrudan karşılaştırılmaz; m11 (hedef seçimi) ve Ortatepe için not: 35° montajda yakın duran kişilerin
  kutuları daha sık birleşiyor ya da karışıyor.

## 21. Alçak + uzak takip denemesi, 14.11 (İş 4)

**Kullanıcının fikri (14.11, koordinatör üzerinden):** kamera açısını azaltıp yüksekliği (dikey uzaklığı) azaltmak ve
yatay uzaklığı artırmak. Taramada geride durma ya kişiyi görüntünün ortasına koyan `h / tan(eğim)` ya da raporun
değerleriydi; "alçak + kişi görüntünün ortasının üstünde + daha geride" hiç denenmedi. Denenen alçak ayarlar (30°
6/10.4, 35° 7/10) kıvrımlı yolun geri dönüşünde kişiyi kaybetti; nedeni dronun kişiye yakın durması, yani yaklaşma
payının küçük olması (bölüm 8, 17.4).

### 21.1 Tasarım (sonuçlar görülmeden yazıldı, 14.11 17:35)

**Ayarlar** (montaj eğimi koşu başına `kamera.egim_deg`; varsayılan dosyalar değişmez). Geometri düz uçuşta,
`tarama.margins` / `geometry` ile (repo dışı `gorev17c_betikler/geometri.py`):

| Ayar | Neden | Yaklaşma payı [m] (kod / basit formül) | Geri kalma payı [m] | Kişinin gövde merkezi görüntüde | Ufuk payı [°] | Zemin duyarlılığı d / h | Başların üstü [m] |
|---|---|---|---|---|---|---|---|
| 30° · 6 m / 12.9 m | yeni: en alçak, en geride | 7.57 / 7.88 | 22.6 | merkezin 7.5° (232 px) üstü; ayak 127 px üstü | 9.9 | 2.15 | 4.25 |
| 30° · 7 m / 12.9 m | yeni | 6.73 / 7.04 | 28.3 | 3.7° (116 px) üstü | 9.9 | 1.84 | 5.25 |
| 32.5° · 7 m / 12.9 m | yeni (30° ile 35°'nin arası) | 7.24 / 7.54 | 19.9 | 6.2° (194 px) üstü | 12.4 | 1.84 | 5.25 |
| 35° · 8 m / 12.9 m | yeni: aynı mesafede 35° | 7.03 / 7.31 | 18.0 | 5.2° (162 px) üstü | 14.9 | 1.61 | 6.25 |
| 35° · 9 m / 12.9 m | başvuru (seçili ayar) | 6.33 / 6.61 | 21.7 | 2.0° (61 px) üstü | 14.9 | 1.43 | 7.25 |
| 35° · 8 m / 11.4 m | başvuru (ikinci seçenek) | 5.53 / 5.81 | 19.5 | 2.1° (63 px) üstü | 14.9 | 1.43 | 6.25 |

- **Geometrinin doğrulanması:** koordinatörün notundaki 7.9 / 7.2 / 6.6 m'nin 7.9 ve 6.6'sı basit formülün (`d − h /
  tan(eğim + 20.07°)`, kamera ofseti yok) değeri; kod kameranın base_link'in 0.151 m önünde ve yerden h + 0.19 m
  yüksekte olduğunu hesaba katar ve ≈ 0.3 m küçük verir. 32.5° 7/12.9'un basit formülü 7.54 m (7.2 kodun değeri).
  Notun "kişi 30° 6/12.9'da optik eksenin ≈ 5.1° üstünde (≈ 158 px)" sayısı ayak noktası, ofsetsiz; gövde merkezi
  (0.9 m; bölüm 19'daki tablo gibi) 7.5° / 232 px üstte. Belgede kodun değerleri kullanılır.
- Köşede stok Follow Me dronu ort. **6.2 m** (sd 1.2; %10–90: 4.6–7.6 m) yaklaştırıyor (bölüm 8). Dört yeni ayarın
  payı bu ortalamanın üstünde (6.7–7.6 m); 35° 9/12.9'unki 6.3, 35° 8/11.4'ünki 5.5 m.
- Kişi bütün ayarlarda kadraja sığar (`tarama.view`: ayak ve baş kenarlardan en az 2° içeride); baş üst kenarın 9.3°
  (30° 6/12.9) – 15.3° (35° 9/12.9) altında.

**Koşular** (aynı kod: HEAD `ad283dcc9d`, çalışma ağacı temiz; durum dosyalı `tarama.py kos`; videolu; v0.2 CPU'da,
stok Follow Me, `FLW_TGT_RS 0.3`, LOS kaynağı model):
- Her yeni ayar: `takip_yuruyen` yolu ×3 (`gorev10on_tarama/asama4`), `kivrimli_yuruyus` yolu ×3
  (`asama4_kivrimli`), `kalabalik_park` aynı eğim ve yükseklikte, Hold ×3 (`gorev17c_kalabalik/kalabalik`; repo
  dışı `kalabalik_plan.py` kalabalığın yolunu ve takip bloğunu değiştirmeden yalnız yüksekliği ve eğimi yazar).
- **Başvurular yeniden koşulmaz:** 35° 9/12.9 ve 35° 8/11.4'ün takip ve kıvrımlı yol koşuları `asama3` /
  `asama3_kivrimli`'de, hakem akışı düzeltmesinden sonraki kodla (bölüm 16–17). Kod o koşulardan sonra yalnız
  varsayılan eğimi 35° yaptı (bölüm 20); eğimi açıkça verilen koşular için uçuş aynı. Kalabalıkta 35° / 9 m
  `gorev17_varsayilan_kalabalik_park_x3` (bölüm 20); 35° / 8 m'yi yeni dizi koşar (kalabalık Hold'da yalnız eğim ve
  yüksekliğe bağlı: 35° 8/12.9'un ve 35° 8/11.4'ün ortak başvurusu).
- Kapı için başvuruların kuralın ilk üç koşusu kullanılır (17.5'teki gibi); 35° 9/12.9'un kıvrımlı yoldaki ek üç
  koşusu (`asama3_kivrimli_ek`) "bütün koşular" satırında ayrıca gösterilir.
- Planda üç bileşim fazladan yazıldı ve koşulmaz (`tarama.py plan --carpan 1`'in yan ürünü, merkez mesafeleri):
  `e32.5_h7_d11.0`, `kivrimli_yuruyus_e30_h7_d12.1`, `kivrimli_yuruyus_e32.5_h7_d11.0`.
- Bütçe: 36 koşu × ≈ 2.5 dk ≈ 1.5 saat (+ açılışlar); 2.5 saatlik bütçeye sığıyor, kalabalık 3'er koşu kalır.

**Düşük yükseklik kontrolleri:**
- `FLW_TGT_HT` < 8 (6–7 m) PX4'te yalnız üst veri sınırı: kalkıştan önce PX4'ten geri okunan değer ve ULog'daki
  yükseklik (60–90 s) istenenle karşılaştırılır (bölüm 4'teki yöntem).
- **Ağaç:** yol koşuları ağaçsız `duz_alan`'da. `kalabalik_park` `cayir`'de ve dron Hold'da (0, 0)'da bekler;
  kalkış yerinin 8 m çevresine ağaç konmaz (en yakın gövde 13.9 m): çarpma olamaz. Ağaç boyları 7.3–10.9 m (çam (13,
  5): 9.2 m, taç tabanı 1.2 m), yani 6–7 m'de dron ağaç tepelerinin altında. Hedefin yürüyüşünde kameradan gövde
  merkezine giden ışının bir ağaç tacından geçtiği pay kaba geometriyle (taç elipsoid, gerçek ağaçtan geniş; repo
  dışı `park_geo_c.py`) 9 m'de %39, 8 m'de %38, 7 m'de %38, 6 m'de %37: alçalmak bu senaryoda örtülmeyi büyütmüyor.
  Ölçülen değer hakemin "gerçekten görünür" oranı. Hedef bütün yeni ayarlarda yolunun %97–99'unda kadrajda (35° / 9
  m'de %100).

**Değerlendirme (17'deki kural aynen, `tarama.py`'de değişmedi):**
1. Kapı (her koşuda ≥ 3 m ve kişi sonuna kadar izlendi, geçerli koşu) takip yolunda 3/3; ek kapı kıvrımlı yolda 3/3.
2. Kuralın puanı (7 grup, min–maks, eşit ağırlık) takip yolunda kapıyı 3/3 geçenler arasında (yeni 4 + 2 başvuru);
   duyarlılık denemeleri aynı.
3. Son seçim sırası 17.1'deki gibi uygulanır: iki yolda 3/3 geçenler arasında kuralın puanı; sonra güvenlik (köşede en
   az mesafe, 6 m altı pay); sonra algılama. İki yolda 3/3 geçen yoksa 17.1'deki yedek kural (iki yolun bütün
   koşularında kişinin izlendiği koşu oranı ve kalan yaklaşma payı).
4. Ek sütunlar (puanlanmaz, kural değişmez): yaklaşma payı ve geri kalma payı (hesap ve ölçülen: köşe yaklaşmasından
   sonra kalan pay, `FLW_TGT_DST`'nin ötesine en çok geri kalma), kişinin görüntüdeki dikey yeri (hakem, gövde merkezi,
   ortadan piksel), piksel boyu ve bulma oranı, köşede en az yatay mesafe ve aynı andaki 3B mesafe (dron ile kişinin
   başı arası), kalabalıkta yanlış kişi oranı, konum hatası ve duyarlılığı (`d / h` ≈ 1 / tan(bakış)), ufuk payı.

**Gerçek uçuş önerisi için önceden yazılan okuma:**
- Yeni bir ayar, 35° 9/12.9'un yerine gerçek uçuş başlangıç ayarı olarak ancak üçü birlikte sağlanırsa önerilir:
  (a) iki yolda 3/3 kapı; (b) kalabalıkta yanlış kişi oranının ortalaması 35° / 9 m'nin en kötü koşusunu (%19)
  aşmıyor; (c) yükseklik 8 m'nin altındaysa (PX4'ün Follow Me için önerdiği alt sınır, başlara yakınlık, ağaç
  tepelerinin altı) ya da ufuk payı 35°'ninkinden küçükse, bu bedele karşı simde ölçülen kazanç (iki yolda daha çok
  izlenen koşu ya da köşe / geri dönüşte belirgin daha büyük kalan pay ya da daha iyi algılama) sayıyla
  gösterilebiliyor. Aksi hâlde 35° 9/12.9 başlangıç ayarı kalır; yeni ayar en çok yedek olur.
- 3 koşuluk kapı gürültülü (35° 8/11.4 kıvrımlı yolda iki günde 3/3 ve 2/3): 3/3 ile 2/3 arasındaki fark tek başına
  güçlü kanıt değil; sonuçlar koşu sayısıyla yazılır.
- Varsayılanlar (`kamera.NOMINAL_TILT_DEG`, `models/x500_tez`, `takip_yuruyen`, `kamera_montaji.yaml`) bu işte
  değişmez; karar kullanıcının.

### 21.2 Koşular ve düşük yükseklik doğrulaması

- 14.11, 17:34–19:10: 24 yol koşusu (4 ayar × 2 yol × 3) ve 12 kalabalık koşusu (4 eğim / yükseklik × 3), hepsi
  GEÇTİ (koşu sonucu, kapı değil); yeniden denenen koşu yok. Yol koşuları ≈ 2.5 dk (takip) / ≈ 2.6 dk (kıvrımlı),
  RTF ort. 0.90 (0.77–1.00); kalabalık ≈ 2.9 dk, RTF 0.76 (0.62–0.83). Gazebo'nun bildirdiği eğim her
  koşuda istenenle aynı (30.0 / 32.5 / 35.0°). Kod HEAD `ad283dcc9d`, çalışma ağacı temiz; bu iş kod değiştirmedi.
- **`FLW_TGT_HT` < 8 uygulandı:** 6 ve 7 m'lik 18 yol koşusunun hepsinde PX4'ten kalkıştan önce geri okunan değer
  istenenle aynı; PX4'ün ULog'undaki yükseklik (ev noktasına göre, 60–90 s) istenenden +0.02…+0.12 m, Gazebo'nun
  ölçtüğü dron yüksekliği de öyle; 8 m'lik 6 koşu da aynı.

**FLW_TGT_HT / yükseklik kontrolü (yeni koşular)**

| Koşu | İstenen yükseklik [m] | PX4'ten geri okunan `FLW_TGT_HT` | ULog yükseklik 60–90 s [m] | Gazebo [m] | Sonuç |
|---|---|---|---|---|---|
| gorev10on_tarama/asama4/e30_h6_d12.9/kosu_1 | 6.0 | 6.0 | 6.05 | 5.97 | GEÇTİ |
| gorev10on_tarama/asama4/e30_h6_d12.9/kosu_2 | 6.0 | 6.0 | 6.10 | 6.09 | GEÇTİ |
| gorev10on_tarama/asama4/e30_h6_d12.9/kosu_3 | 6.0 | 6.0 | 6.08 | 6.05 | GEÇTİ |
| gorev10on_tarama/asama4/e30_h7_d12.9/kosu_1 | 7.0 | 7.0 | 7.11 | 7.13 | GEÇTİ |
| gorev10on_tarama/asama4/e30_h7_d12.9/kosu_2 | 7.0 | 7.0 | 7.04 | 7.03 | GEÇTİ |
| gorev10on_tarama/asama4/e30_h7_d12.9/kosu_3 | 7.0 | 7.0 | 7.07 | 7.05 | GEÇTİ |
| gorev10on_tarama/asama4/e32.5_h7_d12.9/kosu_1 | 7.0 | 7.0 | 7.05 | 7.03 | GEÇTİ |
| gorev10on_tarama/asama4/e32.5_h7_d12.9/kosu_2 | 7.0 | 7.0 | 7.05 | 7.03 | GEÇTİ |
| gorev10on_tarama/asama4/e32.5_h7_d12.9/kosu_3 | 7.0 | 7.0 | 7.03 | 7.06 | GEÇTİ |
| gorev10on_tarama/asama4/e35_h8_d12.9/kosu_1 | 8.0 | 8.0 | 8.05 | 8.03 | GEÇTİ |
| gorev10on_tarama/asama4/e35_h8_d12.9/kosu_2 | 8.0 | 8.0 | 8.12 | 8.11 | GEÇTİ |
| gorev10on_tarama/asama4/e35_h8_d12.9/kosu_3 | 8.0 | 8.0 | 8.02 | 8.01 | GEÇTİ |
| gorev10on_tarama/asama4_kivrimli/kivrimli_yuruyus_e30_h6_d12.9/kosu_1 | 6.0 | 6.0 | 6.02 | 5.99 | GEÇTİ |
| gorev10on_tarama/asama4_kivrimli/kivrimli_yuruyus_e30_h6_d12.9/kosu_2 | 6.0 | 6.0 | 5.98 | 5.99 | GEÇTİ |
| gorev10on_tarama/asama4_kivrimli/kivrimli_yuruyus_e30_h6_d12.9/kosu_3 | 6.0 | 6.0 | 6.06 | 6.01 | GEÇTİ |
| gorev10on_tarama/asama4_kivrimli/kivrimli_yuruyus_e30_h7_d12.9/kosu_1 | 7.0 | 7.0 | 6.97 | 6.99 | GEÇTİ |
| gorev10on_tarama/asama4_kivrimli/kivrimli_yuruyus_e30_h7_d12.9/kosu_2 | 7.0 | 7.0 | 7.00 | 7.00 | GEÇTİ |
| gorev10on_tarama/asama4_kivrimli/kivrimli_yuruyus_e30_h7_d12.9/kosu_3 | 7.0 | 7.0 | 7.04 | 7.03 | GEÇTİ |
| gorev10on_tarama/asama4_kivrimli/kivrimli_yuruyus_e32.5_h7_d12.9/kosu_1 | 7.0 | 7.0 | 7.01 | 6.96 | GEÇTİ |
| gorev10on_tarama/asama4_kivrimli/kivrimli_yuruyus_e32.5_h7_d12.9/kosu_2 | 7.0 | 7.0 | 7.01 | 7.01 | GEÇTİ |
| gorev10on_tarama/asama4_kivrimli/kivrimli_yuruyus_e32.5_h7_d12.9/kosu_3 | 7.0 | 7.0 | 7.05 | 7.04 | GEÇTİ |
| gorev10on_tarama/asama4_kivrimli/kivrimli_yuruyus_e35_h8_d12.9/kosu_1 | 8.0 | 8.0 | 8.03 | 8.03 | GEÇTİ |
| gorev10on_tarama/asama4_kivrimli/kivrimli_yuruyus_e35_h8_d12.9/kosu_2 | 8.0 | 8.0 | 8.07 | 8.03 | GEÇTİ |
| gorev10on_tarama/asama4_kivrimli/kivrimli_yuruyus_e35_h8_d12.9/kosu_3 | 8.0 | 8.0 | 8.04 | 8.03 | GEÇTİ |
| gorev17c_kalabalik/kalabalik/kalabalik_park_e30_h6/kosu_1 | 6.0 | – (Hold) | 6.00 | 5.99 | GEÇTİ |
| gorev17c_kalabalik/kalabalik/kalabalik_park_e30_h6/kosu_2 | 6.0 | – (Hold) | 6.05 | 6.06 | GEÇTİ |
| gorev17c_kalabalik/kalabalik/kalabalik_park_e30_h6/kosu_3 | 6.0 | – (Hold) | 6.03 | 6.03 | GEÇTİ |
| gorev17c_kalabalik/kalabalik/kalabalik_park_e30_h7/kosu_1 | 7.0 | – (Hold) | 6.98 | 6.97 | GEÇTİ |
| gorev17c_kalabalik/kalabalik/kalabalik_park_e30_h7/kosu_2 | 7.0 | – (Hold) | 6.99 | 7.01 | GEÇTİ |
| gorev17c_kalabalik/kalabalik/kalabalik_park_e30_h7/kosu_3 | 7.0 | – (Hold) | 6.96 | 6.81 | GEÇTİ |
| gorev17c_kalabalik/kalabalik/kalabalik_park_e32.5_h7/kosu_1 | 7.0 | – (Hold) | 7.02 | 7.05 | GEÇTİ |
| gorev17c_kalabalik/kalabalik/kalabalik_park_e32.5_h7/kosu_2 | 7.0 | – (Hold) | 6.97 | 7.02 | GEÇTİ |
| gorev17c_kalabalik/kalabalik/kalabalik_park_e32.5_h7/kosu_3 | 7.0 | – (Hold) | 7.13 | 7.19 | GEÇTİ |
| gorev17c_kalabalik/kalabalik/kalabalik_park_e35_h8/kosu_1 | 8.0 | – (Hold) | 8.07 | 8.10 | GEÇTİ |
| gorev17c_kalabalik/kalabalik/kalabalik_park_e35_h8/kosu_2 | 8.0 | – (Hold) | 8.01 | 8.00 | GEÇTİ |
| gorev17c_kalabalik/kalabalik/kalabalik_park_e35_h8/kosu_3 | 8.0 | – (Hold) | 8.00 | 8.03 | GEÇTİ |

- Kalabalık koşularında (Hold, Follow Me yok) dron istenen yükseklikte: ULog'daki yükseklik istenenden (6 / 7 / 8 m)
  en çok 0.13 m farklı; ağaçla çarpma yok (21.5).

### 21.3 İki yolun sonucu ve kuralın sırası

**Kuralın sonucu (takip yolu havuzu: 4 yeni + 2 başvuru, ilk 3'er koşu)**

| Sıra | Ayar | Kapı (takip yolu) | Güv. | Sür. | Alg. | Konum | Salın. | Köşe | Geo. | Toplam | Sim | Kıvrımlı yol: kapı / izlendi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 35° · 8 m / 11.4 m | geçti | − 0.00 | + 0.70 | + 0.84 | + 1.00 | ○ 0.33 | ○ 0.45 | + 0.89 | 0.60 | 0.55 | ✗ / 2/3 |
| 2 | 30° · 7 m / 12.9 m | geçti | ○ 0.67 | + 0.71 | + 0.81 | ○ 0.49 | ○ 0.46 | ○ 0.52 | − 0.25 | 0.56 | 0.61 | geçti / 3/3 |
| 3 | 30° · 6 m / 12.9 m | geçti | ○ 0.64 | − 0.20 | + 0.99 | ○ 0.56 | ○ 0.56 | ○ 0.61 | − 0.00 | 0.51 | 0.60 | ✗ / 2/3 |
| 4 | 35° · 8 m / 12.9 m | geçti | ○ 0.63 | ○ 0.49 | ○ 0.34 | ○ 0.37 | ○ 0.59 | − 0.16 | + 0.80 | 0.49 | 0.43 | geçti / 3/3 |
| 5 | 35° · 9 m / 12.9 m | geçti | ○ 0.43 | ○ 0.40 | − 0.00 | ○ 0.60 | ○ 0.55 | − 0.30 | + 1.00 | 0.47 | 0.38 | geçti / 3/3 |
| 6 | 32.5° · 7 m / 12.9 m | geçti | ○ 0.65 | ○ 0.39 | + 0.82 | − 0.00 | − 0.23 | − 0.23 | ○ 0.42 | 0.39 | 0.39 | geçti / 3/3 |

Duyarlılık:

- eşit: 35° · 8 m / 11.4 m (0.60) > 30° · 7 m / 12.9 m (0.56) > 30° · 6 m / 12.9 m (0.51) > 35° · 8 m / 12.9 m (0.48) > 35° · 9 m / 12.9 m (0.47) > 32.5° · 7 m / 12.9 m (0.39)
- güvenlik ×2: 30° · 7 m / 12.9 m (0.57) > 35° · 8 m / 11.4 m (0.53) > 30° · 6 m / 12.9 m (0.53) > 35° · 8 m / 12.9 m (0.50) > 35° · 9 m / 12.9 m (0.46) > 32.5° · 7 m / 12.9 m (0.42)
- algılama ×2: 35° · 8 m / 11.4 m (0.63) > 30° · 7 m / 12.9 m (0.59) > 30° · 6 m / 12.9 m (0.57) > 35° · 8 m / 12.9 m (0.47) > 32.5° · 7 m / 12.9 m (0.45) > 35° · 9 m / 12.9 m (0.41)
- sim puanı (geometrisiz): 30° · 7 m / 12.9 m (0.61) > 30° · 6 m / 12.9 m (0.59) > 35° · 8 m / 11.4 m (0.56) > 35° · 8 m / 12.9 m (0.43) > 32.5° · 7 m / 12.9 m (0.39) > 35° · 9 m / 12.9 m (0.38)

**Bütün koşular (düzeltmeden sonra; kapı = ≥ 3 m ve kişi sonuna kadar izlendi)**

| Ayar | Takip yolu | Kıvrımlı yol | İki yol |
|---|---|---|---|
| 30° · 6 m / 12.9 m | 3/3 (izlendi 3) | 2/3 (izlendi 2) | **5/6** |
| 30° · 7 m / 12.9 m | 3/3 (izlendi 3) | 3/3 (izlendi 3) | **6/6** |
| 32.5° · 7 m / 12.9 m | 3/3 (izlendi 3) | 3/3 (izlendi 3) | **6/6** |
| 35° · 8 m / 12.9 m | 3/3 (izlendi 3) | 3/3 (izlendi 3) | **6/6** |
| 35° · 9 m / 12.9 m | 7/7 (izlendi 7) | 5/6 (izlendi 5) | **12/13** |
| 35° · 8 m / 11.4 m | 3/3 (izlendi 3) | 2/3 (izlendi 2) | **5/6** |

- **Takip yolunda dört yeni ayarın dördü de 3/3 geçti**, köşede en az 6.7–7.9 m (seçili 35° 9/12.9'da 5.8–7.0, 35°
  8/11.4'te 4.9–5.6 m) ve kaydın 6 m altında hiç kalmadı.
- **Kıvrımlı yolda (164° geri dönüş) 30° 7/12.9, 32.5° 7/12.9 ve 35° 8/12.9 3/3 geçti;** 30° 6/12.9 bir koşuda kişiyi
  kaybetti (2/3), 35° 8/11.4 yine bir koşuda kaybetti (2/3; düzeltmeden sonra iki yolun 6 koşusunda 5).
- **Kuralın son seçimi (önceden yazılan sırayla: iki yolda 3/3 geçenler arasında toplam puan): 30° · 7 m / 12.9 m**
  (0.56). Dört ağırlık denemesinin dördünde de iki yolda 3/3 geçenlerin birincisi; ikincisi hep 35° · 8 m / 12.9 m
  (0.49), seçili 35° 9/12.9 üçüncü (0.47), 32.5° 7/12.9 dördüncü (0.39). Havuzun puanla birincisi 35° 8/11.4 (0.60)
  kıvrımlı yolun kapısından kaldı. Puanlar bu altı ayarlık havuzda ölçeklendi; bölüm 17.3'ün puanlarıyla
  karşılaştırılmaz.
- Koşu sayısı küçük: üç koşuluk kapı gürültülü (35° 8/11.4 kıvrımlı yolda iki günde 3/3 ve 2/3). Yeni ayarların her
  birinde 6, seçili ayarda 13 koşu var; "iki yolda 3/3" yeni ayarlar arasında güçlü bir ayrım değil, puan ve ham
  değerler birlikte okunmalı.

### 21.4 Ne değişti: kişiyi kaçırma riski alttan üste taşındı

**Takip yolu (3'er koşu; ort. (en az–en çok))**

| Ayar | Kapı | En az yatay [m] | O anda 3B (kamera–baş) [m] | < 6 m [%] | Kişi kaybı | Kadrajda [%] | En uzun kayıp [s] | Bulma [%] | Kutu [px] | Kilit kaybı | Konum hatası ort / p95 [m] | Köşe yaklaşması [m] | Yaklaşma payı [m] | Kalan pay [m] | Gövde merkezi kadraj dışı alttan / yandan / üstten [s] | En çok geri kalma [m] | Kişinin yeri: ortadan yukarı [px] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 30° · 6 m / 12.9 m | geçti | 7.1 (6.7–7.5) | 8.4 (8.0–8.8) | 0.0 (0.0–0.0) | 0/3 | 80 (77–84) | 2.5 (2.1–3.0) | 73 (66–77) | 213 (210–216) | 1.7 (1.0–3.0) | 0.42 (0.40–0.46) / 0.95 (0.84–1.05) | 5.8 (5.4–6.2) | 7.6 | 1.8 (1.3–2.2) | 0.1 (0.0–0.3) / 0.0 (0.0–0.0) / 2.8 (2.1–4.2) | 2.0 (1.5–2.3) | 315 (292–338) |
| 30° · 7 m / 12.9 m | geçti | 7.3 (6.7–7.9) | 9.2 (8.7–9.6) | 0.0 (0.0–0.0) | 0/3 | 91 (87–93) | 1.2 (0.6–1.9) | 73 (72–75) | 200 (198–202) | 1.7 (1.0–2.0) | 0.46 (0.39–0.49) / 0.95 (0.79–1.09) | 5.6 (5.0–6.2) | 6.7 | 1.1 (0.5–1.7) | 0.4 (0.0–0.6) / 0.0 (0.0–0.0) / 1.1 (0.0–2.4) | 2.3 (1.7–2.7) | 184 (167–200) |
| 32.5° · 7 m / 12.9 m | geçti | 7.2 (7.1–7.3) | 9.1 (9.0–9.1) | 0.0 (0.0–0.0) | 0/3 | 88 (83–91) | 1.8 (1.4–2.3) | 72 (71–73) | 203 (202–204) | 1.7 (1.0–3.0) | 0.57 (0.51–0.63) / 1.12 (0.90–1.33) | 5.7 (5.6–5.8) | 7.2 | 1.6 (1.5–1.6) | 0.1 (0.0–0.2) / 0.0 (0.0–0.0) / 1.8 (1.4–2.3) | 1.9 (1.8–1.9) | 285 (277–294) |
| 35° · 8 m / 12.9 m | geçti | 7.1 (6.8–7.6) | 9.7 (9.4–10.1) | 0.0 (0.0–0.0) | 0/3 | 88 (85–92) | 1.5 (0.9–2.3) | 66 (64–68) | 191 (190–192) | 2.7 (2.0–3.0) | 0.47 (0.39–0.62) / 1.01 (0.80–1.20) | 5.8 (5.3–6.1) | 7.0 | 1.2 (0.9–1.7) | 0.5 (0.0–0.9) / 0.0 (0.0–0.0) / 1.5 (0.9–2.3) | 2.1 (1.8–2.4) | 260 (245–271) |
| 35° · 9 m / 12.9 m | geçti | 6.2 (5.8–7.0) | 9.8 (9.6–10.3) | 0.4 (0.0–0.7) | 0/3 | 95 (95–95) | 1.1 (0.8–1.3) | 62 (62–64) | 179 (178–180) | 3.3 (2.0–4.0) | 0.41 (0.35–0.46) / 0.96 (0.79–1.17) | 6.7 (5.9–7.1) | 6.3 | -0.3 (-0.7–0.4) | 1.1 (0.8–1.3) / 0.0 (0.0–0.0) / 0.0 (0.0–0.0) | 1.6 (1.4–1.9) | 167 (164–172) |
| 35° · 8 m / 11.4 m | geçti | 5.2 (4.9–5.6) | 8.3 (8.1–8.6) | 1.8 (1.3–2.1) | 0/3 | 94 (94–95) | 0.9 (0.8–1.1) | 71 (67–75) | 207 (206–208) | 1.7 (1.0–2.0) | 0.36 (0.34–0.37) / 0.73 (0.67–0.77) | 6.2 (5.8–6.5) | 5.5 | -0.7 (-1.0–-0.3) | 0.9 (0.8–1.1) / 0.0 (0.0–0.0) / 0.0 (0.0–0.0) | 1.4 (1.2–1.6) | 143 (121–171) |

**Kıvrımlı yol (3'er koşu; ort. (en az–en çok))**

| Ayar | Kapı | En az yatay [m] | O anda 3B (kamera–baş) [m] | < 6 m [%] | Kişi kaybı | Kadrajda [%] | En uzun kayıp [s] | Bulma [%] | Kutu [px] | Kilit kaybı | Konum hatası ort / p95 [m] | Köşe yaklaşması [m] | Yaklaşma payı [m] | Kalan pay [m] | Gövde merkezi kadraj dışı alttan / yandan / üstten [s] | En çok geri kalma [m] | Kişinin yeri: ortadan yukarı [px] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 30° · 6 m / 12.9 m | kişi sonda kaybedildi (1/3 koşu) | 7.5 (6.4–8.3) | 8.7 (7.8–9.4) | 0.0 (0.0–0.0) | 1/3 | 76 (64–84) | 4.0 (1.2–8.5) | 78 (76–79) | 211 (210–214) | 1.3 (1.0–2.0) | 0.43 (0.40–0.50) / 0.82 (0.70–1.06) | 5.4 (4.6–6.5) | 7.6 | 2.2 (1.1–3.0) | 2.5 (0.0–7.4) / 0.6 (0.0–1.9) / 2.2 (1.7–3.0) | 2.6 (2.4–2.9) | 317 (305–340) |
| 30° · 7 m / 12.9 m | geçti | 7.5 (7.3–7.8) | 9.3 (9.1–9.5) | 0.0 (0.0–0.0) | 0/3 | 93 (91–94) | 0.7 (0.5–1.0) | 76 (75–76) | 201 (200–202) | 1.0 (1.0–1.0) | 0.46 (0.41–0.49) / 0.97 (0.68–1.33) | 5.4 (5.1–5.6) | 6.7 | 1.3 (1.1–1.7) | 0.0 (0.0–0.0) / 0.2 (0.0–0.7) / 0.7 (0.5–1.0) | 2.5 (2.4–2.7) | 187 (175–196) |
| 32.5° · 7 m / 12.9 m | geçti | 6.7 (5.3–8.7) | 8.7 (7.6–10.2) | 0.8 (0.0–2.3) | 0/3 | 86 (83–92) | 1.6 (1.2–1.9) | 76 (74–78) | 203 (202–204) | 2.0 (1.0–3.0) | 0.44 (0.38–0.54) / 0.88 (0.74–0.98) | 6.2 (4.2–7.6) | 7.2 | 1.1 (-0.3–3.0) | 0.5 (0.0–1.0) / 0.0 (0.0–0.0) / 1.9 (1.2–2.4) | 2.7 (2.7–2.7) | 266 (252–284) |
| 35° · 8 m / 12.9 m | geçti | 7.9 (7.2–8.4) | 10.2 (9.6–10.6) | 0.0 (0.0–0.0) | 0/3 | 96 (91–99) | 0.6 (0.0–1.5) | 70 (67–74) | 190 (190–190) | 1.0 (1.0–1.0) | 0.48 (0.46–0.51) / 1.03 (0.99–1.07) | 5.0 (4.5–5.7) | 7.0 | 2.0 (1.3–2.5) | 0.0 (0.0–0.0) / 0.0 (0.0–0.0) / 0.7 (0.0–1.8) | 2.5 (2.4–2.6) | 249 (239–254) |
| 35° · 9 m / 12.9 m | geçti | 8.1 (8.0–8.3) | 11.0 (10.9–11.1) | 0.0 (0.0–0.0) | 0/3 | 98 (97–100) | 0.0 (0.0–0.0) | 68 (66–69) | 178 (178–178) | 2.3 (2.0–3.0) | 0.45 (0.44–0.45) / 1.08 (1.00–1.19) | 4.8 (4.6–4.9) | 6.3 | 1.5 (1.4–1.7) | 0.0 (0.0–0.0) / 0.0 (0.0–0.0) / 0.0 (0.0–0.0) | 2.5 (2.3–2.7) | 121 (118–122) |
| 35° · 8 m / 11.4 m | kişi sonda kaybedildi (1/3 koşu) | 6.7 (6.0–7.5) | 9.3 (8.8–9.8) | 0.3 (0.0–1.0) | 1/3 | 89 (74–99) | 2.6 (0.0–7.3) | 75 (70–79) | 201 (198–202) | 1.3 (0.0–3.0) | 0.40 (0.38–0.42) / 0.88 (0.63–1.08) | 4.7 (3.9–5.4) | 5.5 | 0.8 (0.1–1.6) | 0.7 (0.0–1.8) / 2.0 (0.0–6.0) / 0.2 (0.0–0.5) | 2.6 (2.4–2.7) | 128 (120–134) |

**Kişinin görüntüdeki yeri ve üst kenar (takip yolu; ort. (en az–en çok))**

| Ayar | Hesap, düz uçuş: gövde merkezi ortadan yukarı [px] | Ölçülen, havada (50–59 s) [px] | Ölçülen, yürürken (62–68 s) [px] | Yürürken burun aşağı [°] | Baş üst kenara en yakın [px] | Baş üst kenarın dışında [s] | Kıvrımlı: baş üst kenara en yakın [px] / dışında [s] |
|---|---|---|---|---|---|---|---|
| 30° · 6 m / 12.9 m | 232 | 260 (251–270) | 315 (292–338) | 2.3 (1.9–2.9) | -257 (-263–-253) | 5.3 (4.2–6.2) | -240 (-302–-163) / 5.7 (4.0–6.9) |
| 30° · 7 m / 12.9 m | 116 | 139 (135–144) | 184 (167–200) | 2.2 (1.8–3.1) | -185 (-269–-83) | 1.9 (1.1–3.2) | -159 (-180–-134) / 1.9 (1.3–2.8) |
| 32.5° · 7 m / 12.9 m | 194 | 218 (211–229) | 285 (277–294) | 2.9 (2.4–3.3) | -298 (-344–-252) | 2.9 (2.2–4.2) | -266 (-315–-191) / 4.0 (2.6–4.9) |
| 35° · 8 m / 12.9 m | 162 | 201 (192–209) | 260 (245–271) | 2.5 (1.6–3.8) | -183 (-209–-144) | 2.7 (1.5–3.9) | -116 (-228–-11) / 1.5 (0.4–3.0) |
| 35° · 9 m / 12.9 m | 61 | 80 (74–83) | 167 (164–172) | 3.0 (2.2–3.5) | -11 (-50–20) | 0.2 (0.0–0.5) | -9 (-27–19) / 0.3 (0.0–0.4) |
| 35° · 8 m / 11.4 m | 63 | 82 (70–92) | 143 (121–171) | 1.7 (1.4–1.8) | -55 (-70–-34) | 0.7 (0.6–0.7) | -62 (-127–-15) / 0.8 (0.5–1.3) |

- **Alt kenar (köşe ve geri dönüş) rahatladı.** Köşede ölçülen yaklaşma yeni ayarlarda 5.0–6.2 m (takip yolu
  ortalamaları 5.6–5.8 m; seçili ayarda 6.7 m): hesaplanan paydan sonra ortalama 1.1–2.2 m pay kalıyor (seçili ayarda takip
  yolunda −0.3 m, yani ayaklar kısa bir süre görüntünün altına iniyor). Kişinin gövde merkezi takip yolunda
  görüntünün altında yeni ayarlarda 0.1–0.5 s, başvurularda 0.9–1.1 s kaldı. 13.11'deki 70 koşunun köşe yaklaşması
  dağılımına göre (ort. 6.2 m, sd 1.2) payın aşılma olasılığı: 30° 6/12.9 %10, 32.5° 7/12.9 %16, 35° 8/12.9 %20, 30°
  7/12.9 %31, seçili 35° 9/12.9 %46, 35° 8/11.4 %83.
- **Üst kenar daraldı.** İleri uçarken dron burnunu 2–3° aşağı eğiyor ve kamera da onunla dönüyor: kişi yürürken
  havada asılı durduğundan 45–90 px daha yukarıda. Köşeden sonra stok Follow Me kişiye yetişmek için burnu **12–18°**
  aşağı eğerek hızlanıyor (bütün ayarlarda benzer; `analiz_17c.json` → `burun_asagi_maks_deg`). Kişi görüntünün ortasının
  üstüne konunca bu anlarda baş, hatta gövde üstten çıkıyor: takip yolunda başın üst kenarın dışında kaldığı süre yeni
  ayarlarda 1.9–5.3 s, seçili ayarda 0.2 s; gövde merkezi üstten 1.1–2.8 s (başvurularda 0). Model kesik kişiyi çoğu
  zaman yine buldu (kişinin tamamı kadrajda %80–91, seçili %95; kilit kaybı yine de daha az: 1.7–2.7, seçili 3.3).
- **Geri kalma payı (yerde) sınırlayıcı değil:** dron `FLW_TGT_DST`'nin ötesine en çok 1.4–2.7 m geri kaldı; yerdeki
  pay 18–28 m. Asıl sınır görüntünün üst kenarının açısı ve dronun burun eğimi.
- **Kullanıcının fikri aşırıya götürülünce (30° · 6 m / 12.9 m):** kişi düz uçuşta merkezin 232 px üstünde (yürürken
  ≈ 315 px), başı her koşuda 4–7 s üst kenarın dışında; kıvrımlı yolda bir koşuda 164° dönüşten hemen önceki kısa
  koşuda (burun −14°) kişi görüntünün **tamamen üstünden** çıktı, dönüşte alttan / yandan kaçtı ve stok mod onu bir
  daha bulamadı (`asama4_kivrimli/kivrimli_yuruyus_e30_h6_d12.9/kosu_2`, videoda ≈ 1:00). 35° ve 37.5°'nin
  kayıpları çoğunlukla alttandı (bölüm 17.4–18); 30° 6 m'de kayıp üstten başlıyor.
- **Algılama:** alçalınca kişi büyüyor ve daha yandan görünüyor; model 6 m'de %73–78, 7 m'de %72–76, 8 m / 12.9 m'de %66–70
  (seçili %62–68) buluyor; kişi 190–213 px (seçili 179 px). v0.2'nin çöktüğü 150 px'e pay 40–63 px (seçili 29 px).
- **Konum hatası (sim):** 0.42–0.57 m (seçili 0.41–0.45 m); simde zemin düz ve yükseklik kusursuz olduğu için fark
  küçük. Gerçekte zemin ya da GPS yüksekliği hatası `d / h` katıyla büyür: 30° 6/12.9 2.15, 7 m'liler 1.84, 35° 8/12.9
  1.61, seçili 1.43 (GPS yüksekliği 0.5 m yanlışsa 1.08 / 0.92 / 0.81 / 0.72 m).

### 21.5 Kalabalık park ve alçak uçuşta ağaçlar

**Kalabalık park (Hold, cayir; 3'er koşu)**

| Eğim / yükseklik | Yanlış kişi [%] | Aynı kıyafetli yanlış [%] | Seçim doğru [%] | Bulma [%] | Hedef kutusu [px] | Gerçekten görünür [%] | Hedef kadrajda [%] | Kilit kaybı | Dron yüksekliği [m] |
|---|---|---|---|---|---|---|---|---|---|
| 30° / 6 m | 77 (69–90) | 61 (41–74) | 16 (10–29) | 62 (56–67) | 215 (214–216) | 100 (100–100) | 95 (94–95) | 0.3 (0.0–1.0) | 6.03 (5.99–6.06) |
| 30° / 7 m | 70 (68–73) | 46 (34–68) | 28 (24–31) | 58 (57–59) | 211 (210–212) | 100 (100–100) | 99 (97–100) | 0.0 (0.0–0.0) | 6.93 (6.81–7.01) |
| 32.5° / 7 m | 73 (70–78) | 57 (34–68) | 25 (20–29) | 55 (52–58) | 207 (204–209) | 100 (100–100) | 96 (94–98) | 0.3 (0.0–1.0) | 7.09 (7.02–7.19) |
| 35° / 8 m | 39 (16–69) | 28 (6–69) | 33 (27–44) | 57 (56–57) | 198 (197–198) | 100 (99–100) | 98 (97–99) | 1.0 (0.0–2.0) | 8.04 (8.00–8.10) |
| 35° / 9 m | 16 (12–19) | 5 (0–7) | 49 (46–53) | 64 (61–66) | 192 (190–194) | 89 (84–93) | 99 (98–100) | 1.7 (1.0–3.0) | 8.95 (8.92–9.01) |

**Seçimin başka birine ilk geçtiği an** (repo dışı `gecis_17c.py`; aynı kural: seçilen kutu hakeme göre başka bir
kişinin üstünde):

| Eğim / yükseklik | Erken geçiş (yürüyüşün 3. saniyesi, hedefin ≈ 6 m gerisinde duran aynı kıyafetli `insan4`'e) | Diğer koşularda ilk geçiş | Geçiş sayısı (3 koşu) |
|---|---|---|---|
| 30° / 6 m | 3/3 koşu (62.9–63.0 s) | – | 3, 8, 4 |
| 30° / 7 m | 3/3 (63.1–63.5 s) | – | 10, 3, 10 |
| 32.5° / 7 m | 3/3 (62.9–63.3 s) | – | 9, 5, 5 |
| 35° / 8 m | 1/3 (63.5 s) | 78.0–78.9 s, sarı üstlü `insan3` (hedefin yanında duran) | 2, 5, 3 |
| 35° / 9 m (başvuru) | 0/3 | 78.7–79.0 s, `insan3` | 4, 2, 2 |

- **Mekanizma:** alçak ve yatık bakışta farklı derinlikteki kişiler görüntüde dikeyde sıkışıyor. Hedef drondan uzağa
  yürürken görüntüde yukarı, arkasında duran aynı kıyafetli kişinin kutusuna doğru kayıyor; model hedefi bir karede
  kaçırınca geçici seçim (`takip.Selection`: hakemle bir kez kilitlenir, sonra kapının içindeki en yakın kutuyu
  izler) öbür kutuya atlıyor ve kişi durduğu için orada kalıyor. 35° / 9 m'de aynı iki kişi görüntüde birbirinden
  uzak (kapının dışında). Görsel `gorev17c_kalabalik_gecis.png` (30° / 7 m, 62.5 s: seçim hedefte; 65.0 s: "YANLIŞ
  KİŞİ", `insan4`).
- **Sayının sınırı:** yanlış kişi oranı geçici seçim mantığına bağlı ve "yapışkan" (bir erken geçiş koşunun geri
  kalanını yanlış sayar); m11'in gerçek seçimi (görünüş, hareket) başka bir sayı verir. Ama aynı kıyafetli kişide
  görünüş yardım etmez ve kişilerin görüntüde üst üste binmesi bakış açısının kendisinden. **Önceden yazılan (b)
  şartı (ortalama ≤ %19) dört yeni ayarın hiçbirinde sağlanmadı (%39–77).**
- **Kullanıcının 8 m düşüncesine not:** kalabalık Hold'da yalnız eğim ve yüksekliğe bağlı; 35° / 8 m'nin %39'u
  (3 koşunun 1'inde erken geçiş) hem 35° 8/12.9'un hem 35° 8/11.4'ün bedeli. 3 koşu gürültülü (%16–69).
- **Örtülme:** hakemin "gerçekten görünür" ölçütü (hedefin en az 40 pikseli görünüyor) 9 m'de %89 (hedef çamın
  arkasında zamanın %11'inde tamamen gizli), 6–8 m'de %99–100: alçakta hedef çamın arkasından geçerken de bir kısmı
  hep göründü (nedeni ayrıştırılmadı; tahmin: yatık bakışta ağaç tacının altından bacaklar görünüyor). 21.1'deki kaba
  elipsoid tahmini (%37–39) mutlak değerde yanlış çıktı (taç gerçek ağaçtan geniş); yönü (alçalmak örtülmeyi
  büyütmüyor) doğru.
- **Ağaç ve çarpma:** Hold'da (0, 0)'da beklerken çarpma olamaz ve olmadı (dron 6.0 / 6.9 / 7.1 / 8.0 m'de sabit).
  Ama `cayir`'deki ağaçlar 7.3–10.9 m (dünya dosyası: meşe 6.5–10, çam 8–12 m): 6–7 m'de **takip eden** dron ağaç
  tepelerinin altında kalır ve stok Follow Me engel bilmez; kişi bir ağacın yanından geçerse dron ağaca çarpar. Yol
  koşuları ağaçsız `duz_alan`'da; ağaçlı alanda alçak takip denenmedi. Gerçekte 6–7 m'de takip ancak ağaçsız,
  direksiz, binasız bir alanda olur; 8–9 m de kampüsteki 8–12 m'lik ağaçların yanında güvenli değil (bölüm 10).

### 21.6 Tek tablo: 35° 9/12.9, 35° 8/11.4 ve yeni ayarlar

**Tek tablo (3'er koşu, ort. (en az–en çok); takip yolu / kıvrımlı yol)**

| Ayar | Kapı: takip / kıvrımlı (bütün koşular) | Köşede en az yatay [m] | Aynı anda 3B kamera–baş [m] | Yaklaşma payı hesap [m] / kalan (ölçülen) [m] | Geri kalma payı hesap [m] / en çok geri kalma [m] | Bulma [%] | Kişinin boyu [px] | Kişinin yeri ortadan yukarı: hesap / havada / yürürken [px] | Baş üst kenar dışında [s] | Kalabalıkta yanlış kişi [%] | Konum hatası sim [m] / duyarlılık d/h | Ufuk payı [°] | Başların üstü [m] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 30° · 6 m / 12.9 m | ✓ 3/3 / ✗ 2/3 (5/6) | 7.1 (6.7–7.5) / 7.5 (6.4–8.3) | 8.4 (8.0–8.8) / 8.7 (7.8–9.4) | 7.6 / 1.8 (1.3–2.2); 2.2 (1.1–3.0) | 22.6 / 2.0 (1.5–2.3) / 2.6 (2.4–2.9) | 73 (66–77) / 78 (76–79) | 213 (210–216) / 211 (210–214) | 232 / 260 (251–270) / 315 (292–338) | 5.3 (4.2–6.2) / 5.7 (4.0–6.9) | 77 (69–90) | 0.42 (0.40–0.46) / 0.43 (0.40–0.50) / 2.15 | 9.9 | 4.25 |
| 30° · 7 m / 12.9 m | ✓ 3/3 / ✓ 3/3 (6/6) | 7.3 (6.7–7.9) / 7.5 (7.3–7.8) | 9.2 (8.7–9.6) / 9.3 (9.1–9.5) | 6.7 / 1.1 (0.5–1.7); 1.3 (1.1–1.7) | 28.3 / 2.3 (1.7–2.7) / 2.5 (2.4–2.7) | 73 (72–75) / 76 (75–76) | 200 (198–202) / 201 (200–202) | 116 / 139 (135–144) / 184 (167–200) | 1.9 (1.1–3.2) / 1.9 (1.3–2.8) | 70 (68–73) | 0.46 (0.39–0.49) / 0.46 (0.41–0.49) / 1.84 | 9.9 | 5.25 |
| 32.5° · 7 m / 12.9 m | ✓ 3/3 / ✓ 3/3 (6/6) | 7.2 (7.1–7.3) / 6.7 (5.3–8.7) | 9.1 (9.0–9.1) / 8.7 (7.6–10.2) | 7.2 / 1.6 (1.5–1.6); 1.1 (-0.3–3.0) | 19.9 / 1.9 (1.8–1.9) / 2.7 (2.7–2.7) | 72 (71–73) / 76 (74–78) | 203 (202–204) / 203 (202–204) | 194 / 218 (211–229) / 285 (277–294) | 2.9 (2.2–4.2) / 4.0 (2.6–4.9) | 73 (70–78) | 0.57 (0.51–0.63) / 0.44 (0.38–0.54) / 1.84 | 12.4 | 5.25 |
| 35° · 8 m / 12.9 m | ✓ 3/3 / ✓ 3/3 (6/6) | 7.1 (6.8–7.6) / 7.9 (7.2–8.4) | 9.7 (9.4–10.1) / 10.2 (9.6–10.6) | 7.0 / 1.2 (0.9–1.7); 2.0 (1.3–2.5) | 18.0 / 2.1 (1.8–2.4) / 2.5 (2.4–2.6) | 66 (64–68) / 70 (67–74) | 191 (190–192) / 190 (190–190) | 162 / 201 (192–209) / 260 (245–271) | 2.7 (1.5–3.9) / 1.5 (0.4–3.0) | 39 (16–69) | 0.47 (0.39–0.62) / 0.48 (0.46–0.51) / 1.61 | 14.9 | 6.25 |
| 35° · 9 m / 12.9 m | ✓ 3/3 / ✓ 3/3 (12/13) | 6.2 (5.8–7.0) / 8.1 (8.0–8.3) | 9.8 (9.6–10.3) / 11.0 (10.9–11.1) | 6.3 / -0.3 (-0.7–0.4); 1.5 (1.4–1.7) | 21.7 / 1.6 (1.4–1.9) / 2.5 (2.3–2.7) | 62 (62–64) / 68 (66–69) | 179 (178–180) / 178 (178–178) | 61 / 80 (74–83) / 167 (164–172) | 0.2 (0.0–0.5) / 0.3 (0.0–0.4) | 16 (12–19) | 0.41 (0.35–0.46) / 0.45 (0.44–0.45) / 1.43 | 14.9 | 7.25 |
| 35° · 8 m / 11.4 m | ✓ 3/3 / ✗ 2/3 (5/6) | 5.2 (4.9–5.6) / 6.7 (6.0–7.5) | 8.3 (8.1–8.6) / 9.3 (8.8–9.8) | 5.5 / -0.7 (-1.0–-0.3); 0.8 (0.1–1.6) | 19.5 / 1.4 (1.2–1.6) / 2.6 (2.4–2.7) | 71 (67–75) / 75 (70–79) | 207 (206–208) / 201 (198–202) | 63 / 82 (70–92) / 143 (121–171) | 0.7 (0.6–0.7) / 0.8 (0.5–1.3) | 39 (16–69) | 0.36 (0.34–0.37) / 0.40 (0.38–0.42) / 1.43 | 14.9 | 6.25 |

- "Bütün koşular": düzeltmeden sonraki koşular (35° 9/12.9'da takip yolunda 7, kıvrımlı yolda 6 koşu; 35° 8/11.4'ün
  13.11'deki 7 koşusu dahil edilirse 12/13). Kalabalık: 35° 8/11.4 ile 35° 8/12.9 aynı koşular (35° / 8 m).
- Kişinin yeri: hesap düz uçuşta, dron tam `FLW_TGT_DST`'de; havada dron ≈ 0.3 m daha geride durduğu için ölçülen biraz
  daha yukarıda; yürürken burun 2–3° aşağı.

### 21.7 Okuma, kuralın sonucu ve gerçek uçuş önerisi

**Kuralın sonucu (sim, bölüm 3 ve 17.1'in sırası, değişmeden): 30° · 7 m / 12.9 m** — iki yolda 3/3 geçen dört
ayarın puanla birincisi; dört ağırlık denemesinde de. Simde yalnız yol koşularıyla bakılınca kullanıcının fikri
çalışıyor.

**Önceden yazılan gerçek uçuş okuması (21.1):**

| Şart | 30° · 6 m / 12.9 m | 30° · 7 m / 12.9 m | 32.5° · 7 m / 12.9 m | 35° · 8 m / 12.9 m |
|---|---|---|---|---|
| (a) iki yolda 3/3 | ✗ (kıvrımlı 2/3) | ✓ | ✓ | ✓ |
| (b) kalabalıkta yanlış kişi ort. ≤ %19 | ✗ %77 | ✗ %70 | ✗ %73 | ✗ %39 |
| (c) 8 m altı / ufuk payı küçük ise ölçülen kazanç | 6 m, 9.9° | 7 m, 9.9°; kazanç var (bulma +11 / +8 puan, kutu +21 px, takip yolunda köşede +1.1 m) | 7 m, 12.4°; kazanç var (bulma +10 / +8, +24 px) | gerekmez (8 m, 14.9°) |

**(b) hiçbirinde sağlanmadı: önceden yazıldığı gibi 35° · 9 m / 12.9 m başlangıç ayarı kalır; yeni ayarlar en çok
yedek.**

**Gerçek uçuş için öneri (doğrulanmamış; ilk saha uçuşunda doğrulanacak, bölüm 19'daki plan geçerli):**

1. **Başlangıç: kamera 35°, 9 m yükseklik, 12.9 m geride (değişmedi).** İki yolda düzeltmeden sonraki 13 koşunun
   12'si; kişi görüntünün ortasına yakın (havada 80 px, yürürken 167 px yukarıda), yani alt ve üst pay dengeli:
   rüzgârda ve frende burnun iki yöne eğilmesine karşı en sağlam yer. Kalabalıkta yanlış kişi en düşük (%16, hiçbir
   koşuda erken geçiş yok); başların 7.25 m üstü, ufuk payı 14.9°, konum duyarlılığı 1.43. **Bedeli:** algılama en
   zayıf (%62–68, kişi 179 px: v0.2'nin çöktüğü 150 px'e 29 px) ve köşede kalan pay en küçük (takip yolunda kişinin gövde
   merkezi 0.8–1.3 s görüntünün altında).
2. **Yedek: kamera 35°, 8 m yükseklik, 12.9 m geride.** Aynı montaj; sahada yalnız yükseklik 9 → 8 m (`FLW_TGT_DST`
   12.9 kalır). **Ne zaman:** gerçek kamera / Hailo kişiyi 9 m'de zayıf bulursa (bölüm 19 adım 3: takipsiz hover'da
   kişi ≈ 180 px'te model zorlanırsa). **Gerekçe:** iki yolda 6/6, köşede en az 6.8–8.4 m (yaklaşma payı 7.0 m),
   kişi 190 px (+12 px), bulma +4 / +2 puan, kilit kaybı daha az (2.7 / 1.0, 9 m'de 3.3 / 2.3); 8 m PX4'ün Follow Me
   için önerdiği alt sınır, ufuk payı aynı. **Bedeli:** kalabalıkta yanlış kişi %39 (3 koşunun 1'inde erken geçiş;
   kalabalık alanda kullanılmamalı ya da m11'in seçimi beklenmeli); kişi merkezin 162 px üstünde, hızlanırken baş
   1.5–2.7 s üstten çıkıyor (9 m'de 0.2–0.3 s; rüzgârlı günde daha sık olabilir); konum duyarlılığı 1.61.
   - **13.11'in yedeği 35° 8/11.4 yerine neden bu:** aynı yükseklik ve aynı kalabalık bedeli; ama 8/11.4 kıvrımlı yolda
     düzeltmeden sonra yine 3 koşunun 1'inde kişiyi kaybetti (5/6; 13.11 dahil 12/13), yaklaşma payı 5.5 m (takip
     yolunda kalan pay −0.7 m). 8/11.4'ün artısı biraz daha iyi algılama (%71–75, 207 px) ve kişinin merkezde durması
     (üst kenar 0.7–0.8 s). Kullanıcının "8 m / 11.4 m'ye geçme" düşüncesine cevap: 8 m'ye inilecekse simde 12.9 m
     geride kalmak daha sağlam; algılama farkı küçük (5 puan, 16 px).
3. **30° · 7 m / 12.9 m (kuralın sim seçimi) gerçek uçuş için önerilmez:** kalabalıkta 3 koşunun 3'ünde yürüyüşün 3.
   saniyesinde aynı kıyafetli kişiye geçti (%70); 7 m PX4'ün 8 m'sinin altında, başların 5.25 m üstünde, kampüs
   ağaçlarının altında; ufuk payı 9.9° (Ağustos uçuşlarında frende burun 6–11° kalktı: her sert frende ufuk kadraja
   girebilir, otomatik pozlama simde yok); konum 1.84 kat duyarlı (GPS yüksekliği 0.5 m yanlışsa 0.92 m); yeni bir 30°
   parça (bölüm 19'daki ayarlanabilir 30–40° parça olursa mümkün). Ne zaman düşünülür: m11'in seçimi kalabalıkta
   sağlamsa, alan ağaçsız ve boşsa ve 35°'de algılama yetmezse; ayrı bir uçuş denemesi olarak.
4. **30° · 6 m / 12.9 m ve 32.5° · 7 m / 12.9 m önerilmez:** 6 m'de kişi merkezin 232 px üstünde, baş her koşuda 4–7 s
   üstten dışarıda ve kıvrımlı yolda bir kayıp; 32.5° kişiyi 194 px yukarı koyuyor (baş 2.9–4.0 s dışarıda), kalabalıkta
   %73 ve konum hatası simde en büyük (0.57 m takip yolunda).

**Kullanıcının fikri üzerine, dürüst özet:** "Açıyı azalt, alçal, daha geride dur" simde köşe ve geri dönüşteki alt
kenar sorununu gerçekten çözüyor (kalan pay +1.1…+2.2 m, 7 ve 8 m'lik ayarlar iki yolda 6/6) ve kişiyi büyütüyor
(+12…+34 px, bulma +2…+11 puan). Ama sorunu iki yere taşıyor: (1) kişi merkezin üstünde durduğu için dron hızlanınca
görüntünün üstünden çıkıyor (6 m'de kayba kadar); (2) alçak bakışta kalabalıkta kişiler üst üste biniyor (yanlış
kişi %39–77). Sim dışı bedeller (8 m altı, ağaç tepelerinin altı, ufuk payı, konum duyarlılığı) de cabası. Bu
denemede yeni ayarlar 35° 9/12.9'u gerçek uçuş için geçmiyor; en yakını aynı montajdaki 35° 8/12.9 ve yedek olarak
önerildi. m15 en az mesafe koruması getirirse köşedeki 6.2 m'lik yaklaşma küçülür: yeni ayarların artısı (büyük alt
pay) azalır, bedeli kalır.

**Varsayılanlar değişmedi** (`kamera.NOMINAL_TILT_DEG` 35°, `models/x500_tez`, `takip_yuruyen` 9 m / 12.9 m,
`kamera_montaji.yaml`, `EKIP_ICIN_OZET.md`, bölüm 19). Yedeğin 8/11.4'ten 8/12.9'a geçmesi kullanıcı onaylarsa
bölüm 19, `kamera_montaji.yaml` (`ucus_onerisi`) ve `EKIP_ICIN_OZET.md`'ye işlenir.

**Açık konular ve sınırlar:** her yeni ayarda 6 yol koşusu ve 3 kalabalık koşusu (gürültülü; 3/3 ile 2/3 tek başına
kanıt değil); kalabalık sayısı geçici seçim mantığına bağlı; simde rüzgâr yok (burun eğilmesi yalnız hızlanma ve
frenden); stok Follow Me (m15 değil); v0.2 CPU'da (Hailo değil); tek kalabalık senaryosu (aynı kıyafetli kişi hedefin
6 m gerisinde: kötü durum).

### 21.8 Dosyalar, görseller, süre

- **Süre:** 14.11 17:34:37–19:10:44, 36 koşu, 1 saat 36 dakika sim (bütçe 2.5 saat; kalabalık 3'er koşu kaldı). Takip
  ≈ 2.5, kıvrımlı ≈ 2.6, kalabalık ≈ 2.9 dk / koşu; kalabalıkta RTF 0.62–0.83 (9 m'de 0.85). Kod değişmedi (test /
  ruff / pin gerekmedi).
- **Koşu klasörleri** (`tez/sim/sonuclar/`, git dışında): `gorev10on_tarama/asama4/`, `asama4_kivrimli/` (her birinde
  `durum.json`), `asama4.log`, `asama4_kivrimli.log`, `asama4.plan.log`, `plan.json`'a eklenen 11 bileşim (8'i koşuldu)
  ve `senaryolar/`, `analiz_17c.json`, `gecis_17c.json`; `gorev17c_kalabalik/` (`plan.json`, `senaryolar/`,
  `kalabalik/`, `kalabalik.log`).
- **Görseller ve videolar** (`~/Desktop/Follow/3_m06_Simulasyon/Deneme/`, `gorev17c_` ile başlayanlar):

| Dosya | Ne |
|---|---|
| `gorev17c_karsilastirma.png` | 6 ayar × (takip yolu, kıvrımlı yol, kalabalık), her nokta bir koşu: en az mesafe, kapı, kalan pay, bulma, kişi boyu, yanlış kişi, konum hatası, kişinin görüntüdeki yeri, başın üst kenar dışında kalması |
| `gorev17c_yan_gorunus.png` | Yan görünüş (dron, kamera konisi, kişi, köşede 6.2 m yaklaşınca kişi, yaklaşma payı) ve görüntüde kişinin yeri: düz uçuş, yaklaşınca, burun 10° aşağı; 30° 7/12.9, 35° 8/12.9, 35° 9/12.9, 35° 8/11.4 |
| `gorev17c_kalabalik_gecis.png` | 30° / 7 m kalabalık: 62.5 s seçim hedefte, 65.0 s aynı kıyafetli kişiye geçmiş |
| `gorev17c_30_7m_12.9m_takip_yolu_kosu.mp4`, `gorev17c_30_7m_12.9m_kivrimli_yol_kosu.mp4` | En iyi yeni ayar (kuralın seçimi), temsili koşular (`asama4/e30_h7_d12.9/kosu_3`, `asama4_kivrimli/kivrimli_yuruyus_e30_h7_d12.9/kosu_3`) |
| `gorev17c_35_8m_12.9m_takip_yolu_kosu.mp4`, `gorev17c_35_8m_12.9m_kivrimli_yol_kosu.mp4` | Önerilen yedek, temsili koşular (`kosu_1`'ler) |
| `gorev17c_30_6m_12.9m_kivrimli_kayip_kosu.mp4` | 30° 6/12.9, kişinin üstten çıkıp kaybedildiği koşu (`asama4_kivrimli/kivrimli_yuruyus_e30_h6_d12.9/kosu_2`) |
| `gorev17c_30_7m_kalabalik_park_kosu.mp4` | 30° / 7 m kalabalık, aynı kıyafetli kişiye geçiş (`gorev17c_kalabalik/kalabalik/kalabalik_park_e30_h7/kosu_2`) |

- **Betikler** (`gorev17c_betikler/`, repoya girmedi): `geometri.py`, `park_geo_c.py`, `kalabalik_plan.py`,
  `zincir_17c.sh`, `analiz_17c.py` (bu bölümün tabloları → `gorev17c_tablolar.md`), `gecis_17c.py`,
  `karsilastirma_17c.py`, `yan_gorunus_17c.py`, `videolar_17c.py`, `satirlar_17c.py` (kabul satırları),
  `pdf_olustur17c.py` + `kisaca17c.md` (PDF'in yeni bölümü).


---

## Kendin dene

Bu bölümdeki her şey bilgisayarında hazır: koşular yapıldı; özet PDF `~/Desktop/Follow/3_m06_Simulasyon/` altında,
görseller, videolar ve betikler `~/Desktop/Follow/3_m06_Simulasyon/Deneme/` altında (`gorev10on_` ile başlayanlar).

**Başlamadan:** Terminal açmak için **Ctrl+Alt+T**. Gri kutulardaki satırları **tek tek** kopyala, terminale
**Ctrl+Shift+V** ile yapıştır ve **Enter**'a bas. Her satır tek başına çalışır (değişken yok; yeni bir terminalde de
olur). Bir komutu yarıda kesmek için **Ctrl+C**. VLC kısayolları: **Boşluk** duraklat/sürdür, **Ctrl+T** belirli bir
zamana git (dakika:saniye), **E** bir kare ileri, **[** / **]** yavaşlat/hızlandır, **F** tam ekran.

### 1. Özet PDF (önce bunu oku)

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Kamera_Acisi_ve_Mesafe_Modelli_Tarama.pdf
```

### 2. Aşama 1: ısı haritaları (açı × yükseklik, her mesafe kuralı için)

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_isi_algilama_orani.png
```

Her küçük tablo bir mesafe kuralı (soldan: merkez mesafesinin 0.8 katı, merkez `h / tan(eğim)`, 1.25 katı, raporun
8 m'si); satırlar yükseklik (kalın çizginin altı 4–7 m bandı), sütunlar kamera eğimi. Yeşil iyi, kırmızı kötü; kırmızı
kesikli çerçeve ve ✗: kapıdan geçmedi. Burada 12–15 m satırlarının kırmızı olduğuna bak: model kişiyi bulamıyor.

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_isi_en_az_yatay_mesafe_m.png
```

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_isi_kisi_sonda_kayip.png
```

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_isi_toplam.png
```

### 3. Aşama 2: adaylar, 3'er koşu

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_aday_karsilastirma.png
```

Her küçük grafik bir ölçüt; noktalar 3 koşu, çubuk ortalama, renk eğim (kırmızı 30°, sarı 35°, yeşil 40°, lacivert
45°); ✗ üç koşudan birinde kapıdan geçmedi.

Kıvrımlı yol (164°'lik sert geri dönüş) ve mükemmel algılayıcı: aynı düzen; 13.11'de kıvrımlı yolda yalnız 35° 8/11.4
üç koşunun üçünde kişiyi tuttu (hakem düzeltmesinden sonra 2/3, bölüm 16.4).

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_kivrimli_karsilastirma.png
```

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_hakem_karsilastirma.png
```

### 4. Videolar: 13.11'in önerisi (35° · 8/11.4) ve 45° 10/10 (son karar ve yeni varsayılan: 11)

13.11'de önerilen 35° · 8 m / 11.4 m. **Ctrl+T** ile **0:53**'e git (kişi koşudan sonra batıya dönüyor): 0:55.5'te dron kişiye
5.5 m'ye kadar yaklaşıyor, kişi bir an kadrajın altına iniyor ve geri geliyor.

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_onerilen_35_8m_11.4m_kosu.mp4 2>/dev/null
```

45° · 10 m / 10 m, kişinin kaybedildiği koşu: **0:51**'den sonra dron 7 m yaklaşıyor (0:53.5'te 2.96 m), kişi önce
kadrajın altından sonra yanından çıkıyor ve stok Follow Me onu bir daha bulamıyor.

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_45_10m_10m_kayip_kosu.mp4 2>/dev/null
```

45° · 10 m / 10 m'nin temsili (kişiyi izlediği) koşusu ve kuralın birincisi 35° · 7 m / 10 m:

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_45_10m_10m_kosu.mp4 2>/dev/null
```

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_kural_birincisi_35_7m_10m_kosu.mp4 2>/dev/null
```

### 5. Senin sorun: "30°'de yaklaşınca kaçırma artıya döner mi?"

Kameranın gördüğü alan (aynı yükseklikte ve aynı mesafede 30° / 45°):

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_gorus_alani_30_45.png
```

Senin beş ayarın ve adayların yaklaşma payı; oklar her koşuda dronun köşede ne kadar yaklaştığı (kırmızı: yakın
sınırın içine girdi):

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_yaklasma_payi.png
```

Dört koşunun mesafe–zaman çizgisi (kırmızı bant: kişi kadrajın altında, turuncu: yanında):

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_yaklasma_cizelgesi.png
```

Köşe yaklaşması mesafeyle ölçekleniyor mu, kaybı ne belirliyor:

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_yaklasma_ve_kacirma.png
```

### 6. Kamera raporuyla (modelsiz) yan yana

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_rapor_karsilastirma.png
```

### 7. Model hangi koşullarda iyi algılıyor?

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_algilama_kosullari_tek_degisken.png
```

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_algilama_kosullari_lojistik.png
```

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_algilama_kosullari_boy_ve_egim.png
```

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_algilama_kosullari_goruntu_ve_boy.png
```

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev10on_algilama_kosullari_guven.png
```

### 8. 13.11'in önerisini kendin koştur (pencere yok, ≈ 3 dakika)

Taramanın 35° · 8 m / 11.4 m senaryosu (kamera 35°, dron 8 m'de, kişinin 11.4 m gerisinde); sonuç
`tez/sim/sonuclar/` altında tarihli bir klasörde (`kosu.mp4`, `rapor.html`):

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo tez/sim/sonuclar/gorev10on_tarama/senaryolar/e35_h8_d11.4.yaml --ekransiz
```

Herhangi bir senaryoyu başka bir kamera eğimiyle koşmak (örnek: `takip_yuruyen`, kamera 35°; dron yüksekliği ve
mesafesi senaryonunki kalır):

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --kamera-egim 35 --ekransiz
```

### 9. Kontroller

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python -m pytest tez/sim/testler -q
```

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && tez/pin/verify_pin.sh --worktree
```

Beklenen: `281 passed` (İş 1 tek başına temiz HEAD'de 275); `KILIT SAGLAM (v1.17.0)`.

### 10. Canlı hakem akışı: önce / sonra (İş 1, bölüm 16)

Altı panel: Gazebo'nun büyüyen başlığı, hakemin kare başına işi, gz-transport iş parçacığının CPU'su (önce kırmızı
çizgi 1 çekirdeğe doğru tırmanıyor, sonra yeşil düz), tam çöp toplama, hakemin gecikmesi, kıvrımlı yolda engellenen
yeniden kilitler:

```bash
xdg-open /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17b_hakem_akisi_once_sonra.png
```

Hatayı yakalayan testler (yaklaşık 1 saniye):

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python -m pytest tez/sim/testler/test_hakem_akisi.py -v
```

Bir koşunun hakem akışı sayıları (`gecikme_ms_p95` 50 ms civarı, `hakem_sonradan_gelen_kare` 1 olmalı):

```bash
grep -A 9 '"hakem_akisi"' /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev10on_tarama/asama3_kivrimli/kivrimli_yuruyus_e35_h8_d11.4/kosu_1/ozet.json
```

### 11. 37.5°, son karar ve yeni varsayılan (İş 2 ve İş 3, bölüm 17–20)

Önce güncellenmiş özet PDF'i aç; ilk sayfa ekip arkadaşların için 1 sayfalık, terimsiz "Kısaca":

```bash
xdg-open /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Kamera_Acisi_ve_Mesafe_Modelli_Tarama.pdf
```

Kısaca'nın görseli (solda seçilen ayarın yandan görünüşü, sağda her ayarın denemelerin kaçında kişiyi sonuna kadar
izleyip 3 m'den fazla yaklaşmadığı):

```bash
xdg-open /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17b_kisaca.png
```

35°, 37.5°, montaj toleransı (32.5°) ve rakipler, iki yolda koşu koşu (boş kareler: ek koşular):

```bash
xdg-open /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17b_karsilastirma.png
```

Seçilen ayar 35° · 9 m / 12.9 m, kıvrımlı yol: **Ctrl+T** ile **1:00**'a git; kişi 1:01'de neredeyse tam geri dönüp
(164°) drona doğru yürüyor, dron dönüp kişinin arkasına geçiyor ve kişi görüntüden hiç çıkmıyor.

```bash
vlc /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17b_secilen_35_9m_12.9m_kivrimli_yol_kosu.mp4 2>/dev/null
```

Aynı yükseklik ve mesafede 37.5°, kıvrımlı yolda kişinin kaybedildiği koşu: **Ctrl+T** ile **0:59**'a git; 1:00'da
kişi görüntünün altından çıkıyor ve stok Follow Me onu bir daha bulamıyor.

```bash
vlc /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17b_37.5_9m_12.9m_kivrimli_kayip_kosu.mp4 2>/dev/null
```

Seçilen ayar, takip yolu: **Ctrl+T** ile **0:49**'a git (kişi koşudan sonra batıya dönüyor). **0:51.4–0:52.7** (sim
78.8–80.1 s) kişi ~1.2 s **kadrajdan çıkıyor** ("HEDEF YOK", kilit kaybı) ve sonra geri geliyor: stok Follow Me köşede
kişiye 5.9 m'ye kadar yaklaşıyor (0:52.2, sim 79.6 s), bu kameranın yakın görüş sınırının (6.6 m) içinde, kişinin
ayakları kadrajın altında kalıyor. Takip yolunda bu ayarın üç koşusunun üçünde de köşede böyle bir çıkış var (en uzun
kayıp 0.8–1.3 s, en az mesafe 5.8–7.0 m); kişi her seferinde geri bulunuyor. "Hiç çıkmadı" yalnız kıvrımlı yol için
doğru (üç koşuda kayıp 0 s). (Düzeltme 14.11.2026: bu satır önce "kişi görüntüde kalıyor" diyordu; Ahmet VLC'de gördü,
17.8 kontrolü.)

```bash
vlc /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17b_secilen_35_9m_12.9m_takip_yolu_kosu.mp4 2>/dev/null
```

Yeni varsayılanla demo koşuları (İş 3, temsili birer koşu). `takip_yuruyen` (35° · 9 m / 12.9 m): **Ctrl+T** ile
**0:50**'e git, kişi batıya dönüyor:

```bash
vlc /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17b_varsayilan_takip_yuruyen_kosu.mp4 2>/dev/null
```

`kalabalik_park` (dron 9 m'de bekler, kamera 35°): **0:54–0:59** arasında model kutusu birkaç kez hedefin yanındaki
kişiye (sarı üstlü, sonra hedefle aynı kıyafetli) geçiyor; durum satırında kırmızı "YANLIŞ KİŞİ" yazar.

```bash
vlc /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17b_varsayilan_kalabalik_park_kosu.mp4 2>/dev/null
```

Yeni varsayılanı kendin koştur (pencere yok, ≈ 3 dakika; sonuç `tez/sim/sonuclar/` altında tarihli bir klasörde):

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz
```

Karşılaştırma için eski 45° montaj (10 m / 10 m):

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo takip_yuruyen_45_10m --ekransiz
```

Varsayılanın tek yerden geldiğini sınayan testler (yaklaşık 2 saniye) ve bütün testler:

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python -m pytest tez/sim/testler/test_varsayilan_montaj.py -v
```

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python -m pytest tez/sim/testler -q
```

Beklenen: `6 passed` (5 test, biri iki senaryo için) ve `281 passed`.

### 12. Alçak + uzak takip denemesi (İş 4, bölüm 21)

Önce PDF'in yeni bölümü ("Ek deneme (14.11 akşam)", Kısaca sayfasından hemen sonra):

```bash
xdg-open /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Kamera_Acisi_ve_Mesafe_Modelli_Tarama.pdf
```

Kişiyi görüntünün ortasının üstüne koymak ne demek (solda yan görünüş: köşede dron 6.2 m yaklaşınca kişi nerede;
sağda kameranın görüntüsünde kişi: düz uçuşta kırmızı, yaklaşınca turuncu, burun 10° aşağı eğilince mavi):

```bash
xdg-open /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17c_yan_gorunus.png
```

Altı ayar, her nokta bir koşu (iki yol + kalabalık; gri alan 35° 9/12.9 ve 35° 8/11.4):

```bash
xdg-open /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17c_karsilastirma.png
```

Kalabalıkta 30° / 7 m: solda 62.5 s'de seçim hedefte, sağda 65.0 s'de arkasındaki aynı kıyafetli kişiye geçmiş:

```bash
xdg-open /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17c_kalabalik_gecis.png
```

En iyi yeni ayar (kuralın sim seçimi) 30° · 7 m / 12.9 m, takip yolu: **Ctrl+T** ile **0:50**'ye git; 0:51'de kişi
batıya dönüyor, 0:56'da dron hızlanırken kişinin başı görüntünün üst kenarında kesiliyor ama model onu buluyor.

```bash
vlc /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17c_30_7m_12.9m_takip_yolu_kosu.mp4 2>/dev/null
```

Aynı ayar, kıvrımlı yol: **Ctrl+T** ile **1:00**'a git; 1:02'de kişi neredeyse tam geri dönüp (164°) drona doğru
yürüyor, kişi görüntüde kalıyor.

```bash
vlc /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17c_30_7m_12.9m_kivrimli_yol_kosu.mp4 2>/dev/null
```

Önerilen yedek 35° · 8 m / 12.9 m (aynı montaj, yalnız yükseklik 8 m): takip yolu köşe ≈ **0:52**, kıvrımlı yol geri
dönüş ≈ **1:01**.

```bash
vlc /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17c_35_8m_12.9m_takip_yolu_kosu.mp4 2>/dev/null
```

```bash
vlc /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17c_35_8m_12.9m_kivrimli_yol_kosu.mp4 2>/dev/null
```

Fikir aşırıya götürülünce, 30° · 6 m / 12.9 m: **Ctrl+T** ile **0:58**'e git; 1:00'da dron burnunu aşağı eğerek
hızlanırken kişi görüntünün tamamen üstünden çıkıyor ("HEDEF YOK"), 1:04'te geri dönüşte kayboluyor.

```bash
vlc /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17c_30_6m_12.9m_kivrimli_kayip_kosu.mp4 2>/dev/null
```

Kalabalıkta 30° / 7 m: **Ctrl+T** ile **0:38**'e git; 0:40 civarında durum satırında kırmızı "YANLIŞ KİŞİ (hedefle
aynı kıyafetli)" çıkıyor ve seçim koşunun çoğunda o kişide kalıyor.

```bash
vlc /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17c_30_7m_kalabalik_park_kosu.mp4 2>/dev/null
```

Bölümün bütün tabloları (betiğin çıktısı):

```bash
xdg-open /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17c_betikler/gorev17c_tablolar.md
```

Bir ayarı kendin koştur (pencere yok, ≈ 3 dakika; senaryo dosyası tarama klasöründe, git dışında):

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo tez/sim/sonuclar/gorev10on_tarama/senaryolar/e30_h7_d12.9.yaml --ekransiz
```

Tabloları koşulardan yeniden hesapla (≈ 10 saniye):

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python /home/ahmet/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev17c_betikler/analiz_17c.py
```
