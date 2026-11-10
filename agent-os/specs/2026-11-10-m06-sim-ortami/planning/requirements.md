# Spec Gereksinimleri: m06 Simülasyon Ortamı

- Yol haritası maddesi: m06 (madde 6: Simülasyon kamera ve hareketli insan hedefi kurulumu)
- İlgili issue: Auto-Follow/Auto-Follow#7 (son teslim 15.11.2026)
- Dal: `ozellik/m06-sim-ortami` · PR başlığı: `[M06] Simülasyon ortamı`
- Not: Yol haritasında madde 6 için "Çatı spec, Autopilot uygulama" yazar; issue #7 spec'i `Autopilot/agent-os/specs/` altına istediği için burada tutulur.

## İlk Açıklama

"m06: Simülasyon ortamı (issue #7). tez/sim'deki mevcut çalışmanın (F0/F1) üstüne, gerçek uçuşa olabildiğince yakın, tam bir simülasyon ortamı: Gazebo kamera → model → PX4 → simülasyon döngüsü, kamera ve gecikme gerçekçiliği, dron ve dünya gerçekçiliği, QGC'ye video, senaryo ve ölçüm altyapısı. Kapsam listesi: ~/Desktop/Follow/devir.md. Blok diyagram: ~/Desktop/Follow/3_m06_Simulasyon/. Yaklaşma mesafesi: ~/Desktop/Follow/2_Raporlarim/Kamera_ve_Takip_Ayarlari_Raporu.pdf"

Issue #7'nin "bitti" ölçütü:
- Spec klasöründe blok diyagram (`planning/visuals/`, elle çizim olabilir), yaklaşma mesafesi dokümanı, kamera parametreleri ve insan hedefinin nasıl hareket ettiği bulunur.
- SITL'de Gazebo kamera görüntüsü laptop'ta okunur, model bu görüntü üzerinde çalışır ve hareket eden bir insan hedefi vardır.
- Yalnızca Gazebo Harmonic (`gz_*`) kullanılır.
- Model → PX4 oku için geçici çözüm kullanılır ve "Varsayımlar" başlığı altında yazılır.
- `.pt` dosyaları repoya girmez; model repo dışındaki bir klasörden okunur.

## Gereksinim Tartışması

### Birinci Tur Sorular

**S1:** Teslim ve aşamalar (15.11). Kapsam küçültülmeden aşamalara bölünür. Önerim tek spec, iki fazdı. Faz A 15.11'e kadar ilk PR olur: issue'daki "bitti" listesi (belgeler, kamera okunur, model çalışır, insan hareket eder, Model→PX4 geçici çözümle çalışır). Faz B 15.11'den sonra aynı spec'e bağlı ikinci PR olur (kamera kusurları, rüzgâr/GPS, eğimli zemin, Wi-Fi benzetimi, ek ölçümler). Bu bölme uygun mu?
**Cevap:** Evet: tek spec, Faz A (15.11, ilk PR) ve Faz B (sonra).

**S2:** Hangi model kullanılacak, m06 ile m08 sınırı ne olacak? Önerim: m06'da Yusuf Ortatepe'nin `model-training` dalındaki v0.2 `.pt` modeli laptop CPU'sunda çalışır. Kıyas için stok COCO YOLOv8s seçilebilir. Asıl ve Hailo ile tutarlı hal m08'de Vision'ın işidir. Hüseyin cevap verdi mi?
**Cevap:** Evet: Ortatepe'nin v0.2 `.pt` modeli laptop CPU'sunda çalışır; stok COCO YOLOv8s kıyas için seçilebilir; asıl ve Hailo ile tutarlı hal m08'dedir. Hüseyin'e geri bildirim mesajının gönderilip gönderilmediği cevaplanmadı. Hüseyin'e bağlı kararlar "onay bekliyor" olarak kaydedilir.

**S3:** `.pt` nerede durur, paketler nasıl sabitlenir? Önerim:
- Model repo dışında durur, yolu `--model <yol>` ile verilir ve sha256 özeti spec'e yazılır.
- `ultralytics` ve `torch` (CPU) sabit sürümle bir requirements dosyasına ve `tez/env/VERSIONS.md`'ye yazılır.
- AGPL-3.0 notu eklenir.
- Çatıdaki `tech-stack.md` ve `docs/02-...` ayrı bir çatı PR'ında güncellenir.
**Cevap:** Evet. Kullanıcı model klasörünün yerini belirtmedi. Varsayılan olarak repo dışında `~/auto-follow-modeller/` önerilir; `--model <yol>` ile değiştirilebilir.

**S4:** Kod nerede yaşar? Önerim: m06'nın kamera okuyucusu ve model çalıştırıcısı Autopilot `tez/sim/` altında olur ve Vision'a `../` ile bağlanmaz (kural 7). Arayüz basit tutulur (kare girer, kutu listesi çıkar), böylece Vision kodu sonradan takılabilir.
**Cevap:** Evet: kod Autopilot `tez/sim/` altında olur; arayüz basittir (kare girer, kutu listesi çıkar), böylece Vision kodu sonradan yerine takılabilir.

**S5:** Geçici Model→PX4 oku nasıl olacak (Varsayımlar)? Önerim: iki kaynak senaryoda seçilir.
- (i) Model kutusundan: `kamera.py` zinciriyle gövde FRD yön vektörü hesaplanır.
- (ii) Hakemin doğru cevabından: `kayit.py`'nin `los_govde` değeri kullanılır.
Mesaj `DEBUG_VECT`, adı `TEZ_LOS`, 30 Hz, SITL'de UDP 14540 olur.
**Cevap:** Evet: iki LOS kaynağı senaryo başına seçilir: (i) model kutusundan `kamera.py` ile, (ii) doğru cevap `los_govde`. Mesaj `DEBUG_VECT` "TEZ_LOS", 30 Hz; "Varsayımlar" altında yazılır.

**S6:** Döngü m06'da kapansın mı? Önerim: evet, stok PX4 Follow Me kullanılır. Model kutusundan düz zemin geolocation ile `FOLLOW_TARGET` gönderilir, ayarlar `FLW_TGT_HT 8` / `FLW_TGT_DST 8` olur. Diğer seçenek açık döngü, yani yalnız veri akışıdır.
**Cevap:** İKİSİ BİRDEN olsun, çalışma anında kullanıcı seçsin:
- Stok PX4 Follow Me ile kapalı döngü: `FOLLOW_TARGET` model kutusundan, düz zemin geolocation ile hesaplanır; `FLW_TGT_HT 8` / `FLW_TGT_DST 8`.
- Açık döngü / yalnız veri modu.

Kullanıcı şunu özellikle vurguladı: Yusuf Kurt'un PX4 takip modu (m15) **kolayca takılabilmeli, entegre edilebilmeli ve test edilebilmeli**. Bu yüzden birinci sınıf gereksinimdir:
- Bir "takip kaynağı / kontrolcü" seçimi olur. Örnekler: `follow_me` | `tez_los` + adıyla harici özel moda geçiş | `yok` (açık döngü).
- Bir takım arkadaşının kendi PX4 modülünü simin kullandığı SITL derlemesine nasıl ekleyeceği ve ona karşı nasıl senaryo koşturacağı adım adım belgelenir.
- Her kontrolcü için aynı ölçütler ve aynı video üretilir; böylece kontrolcüler karşılaştırılabilir.

**S7:** ROMFS ve iskelet PX4 modülü ne olacak? Önerim:
- (b) yolu: PX4 dosyalarına dokunulmaz; stok 4001 + `PX4_SIM_MODEL=x500_tez` + 4019 kazançları ve parametreler başlangıçta yüklenir; 3 ROMFS dosyası geri alınır.
- "Tez Auto Follow" iskelet modülü m06 PR'ına girmez.
Hüseyin cevap verdi mi?
**Cevap:** Kullanıcı kararı bıraktı: "diğer takım arkadaşlarının simi kendi bilgisayarlarında en kolay çalıştırabileceği yolu seç". Karar (orkestratör): **(b)**.
- PX4/ROMFS dosyası değişmez. Stok 4001 airframe + `PX4_SIM_MODEL=x500_tez` + gerçek dronun ayarları (4019 kazançları + 22.08 parametreleri) başlangıçta yüklenir.
- 3 ROMFS dosyası geri alınır, böylece `verify_pin.sh --worktree` geçer.
- "Tez Auto Follow" iskelet modülü m06 PR'ına girmez.
- F0 kabul testi ve README güncellenir.
- Ek gereksinim: bir takım arkadaşı repoyu klonlayıp kurulum/derleme/çalıştırma betiklerini çalıştırarak simi ayağa kaldırabilmelidir. Kurulum adımları belgelenir, AMD için `DRI_PRIME` notu da eklenir.
- Hüseyin'in bu konudaki onayı: onay bekliyor.

**S8:** Kamera gerçekçiliği ve gecikme nasıl olacak? Önerim: Python'da ayarlanabilir bir "kamera kusurları" aşaması olur: (a) gürültü düzeltmesi, (b) hareket bulanıklığı, (c) rolling shutter, (d) pozlama/parlaklık, (e) yakalama→PX4 gecikmesi ve saat kayması. Model yetişemezse sim gerçek zamanda akar ve kareler atlanır. Faz önerisi: (e) Faz A, (a)–(d) Faz B.
**Cevap:** Kullanıcı: "bilmiyorum". Karar (orkestratör):
- **Faz A:** Gecikme zinciri (yakalama→PX4 gecikmesi, saat kayması). CPU'daki model yetişemediğinde kare atlanır, sim gerçek zamanda akar; bunlar ölçülür. "Kamera kusurları" aşamasının altyapısı Faz A'da kurulur ama kusurlar varsayılan olarak KAPALIDIR.
- **Faz B:** Gürültü düzeltmesinin ayarı, hareket bulanıklığı, rolling shutter, pozlama.

**S9:** Dron ve dünya gerçekçiliği hangi fazda olacak? Önerim: Faz A'da gerçek dron parametreleri. Faz B'de rüzgâr, GPS gürültüsü, eğimli zemin ve lidar, insan çeşitliliği. Kütle m21'de.
**Cevap:** Faz B'deki dron/dünya maddeleri (rüzgâr, GPS gürültüsü, eğimli zemin + lidar, insan çeşitliliği) şimdilik gerekmiyor, "belki ileride". Faz A'da yalnızca gerçek dron parametreleri yapılır. Diğerleri taahhüt edilmiş Faz B olarak değil, "sonraya / şimdilik kapsam dışı (belki ileride)" olarak listelenir.

**S10:** QGC'ye video olacak mı? Önerim: deney dalındaki `goruntu_yayini.py` yeniden yazılır. Model ve hakem kutuları çizilir, H.264 RTP UDP 5600 ile 1280×720, 15 fps yayınlanır. Faz A'da olur; Wi-Fi benzetimi Faz B'de.
**Cevap:** "Olabilir". QGC videosu Faz A'da yapılır: yeniden yazılmış `goruntu_yayini.py`, model ve doğru cevap kutuları, H.264 RTP UDP 5600, 1280×720, 15 fps. Wi-Fi gecikme/kayıp benzetimi sonraya kalır.

**S11:** Senaryo, ölçüm ve video çıktısı ne olacak? Önerim: `senaryo.py` ve `rapor.html` genişler. Her koşu şunları üretir: (a) model ölçütleri (IoU, kaçırma, yanlış kişi), (b) LOS açı hatası, (c) kare başına süre ve gecikme, (d) takip ölçütleri, (e) WebM video. Eşikler boş kalır.
**Cevap:** Uygun. Video biçimi değişiyor: kullanıcı VLC'de açılan normal bir video dosyası istiyor (VLC 3.0.20 ve ffmpeg 6.1.1 kurulu); Firefox/WebM gerekmez. Çıktı **MP4 (H.264)** olur: dron kamerası + model ve doğru cevap kutuları + yan yana üstten görünüm. Eşikler boş kalır, yalnızca ölçülür.

**S12:** Spec'e hangi belgeler girecek? Önerim:
- 45° raporunun içeriği spec'e Türkçe metin olarak taşınır, PDF de kopyalanır.
- Kamera parametreleri 22.10 ölçümlerinden alınır.
- İnsan hareketi README'den alınır.
- 8/8, 10/10 ve 15/12 yeni simde gerçek modelle yeniden ölçülür.
**Cevap:** Uygun: 45° raporunun içeriği spec'e taşınır ve PDF spec klasörüne kopyalanır; kamera parametreleri 22.10 ölçümlerinden, insan hareketi README'den alınır. 8/8, 10/10 ve 15/12 yeni simde gerçek modelle yeniden ölçülecek, ama sonra (döngü kapandıktan sonra). Kullanıcı sonraki fazları isteğe bağlı saydığı için bu iş **Faz B** olarak işaretlenir.

**S13:** Kapsam dışı neler? Önerim: PX4 özel takip modu (m15), asıl piksel→gövde dönüşümü (m10), Hailo ve model seçimi (m07/m08), model eğitimi (Aşama 8), Qt operatör arayüzü, gerçek uçuş ve CM3 kalibrasyonu (m09), ROS 2 ve Gazebo Classic.
**Cevap:** Tamam, kapsam dışı listesi kabul edildi.

### Mevcut Koddan Yararlanma

Kullanıcı ek kod göstermedi. Önerilen kaynakları kabul etti.

**Benzer özellikler:**
- Özellik: F0/F1 simülasyon ortamı. Yol: `Autopilot/tez/sim/`
  - Model `models/x500_tez/` (CM3 66°, 2304×1296, 30 fps, gövde altı 45°, hakem segmentasyon kamerası)
  - İnsan `models/insan/` (Mingfei actor, `walk_tez`/`run_tez`)
  - Dünyalar `worlds/duz_alan`, `worlds/cayir`; senaryolar `senaryolar/*.yaml`
  - Araçlar:
    - `araclar/senaryo.py`, `hedef.py`, `yuruyus.py`, `kayit.py` (kare başına doğru cevap, `los_govde`, görünürlük, kutular)
    - `kamera.py` (kamera modeli ve eksen zinciri), `rapor.py`, `onizleme.py`, `simulasyon.py`, `px4_baglanti.py` (UDP 14540, GCS gibi)
    - `f0_kabul.sh`, `f1_kabul.sh`
  - 76 pytest testi `testler/`
- Özellik: WSL dönemi Follow Me denemesi. Dal: `origin/deney/ai-follow-sim`, yol `tez/deney/follow_sim/`. Bu dal yalnızca okunarak kaynak alınır; kod doğrudan taşınmaz, spec'e göre yeniden yazılır.
  - `video/goruntu_yayini.py`:
    - Gazebo karesine `subscribe_raw` ile abone olur ve yalnız yayınlanacak kareyi çözer.
    - GStreamer hattı: appsrc → leaky queue → x264enc zerolatency → rtph264pay → netsim → multiudpsink.
    - Kutu ve ayak noktası çizer.
  - `video/video_izleyici.py`, `video/video.sdp`, `video/wifi_olcum.py`
  - `geolocation.py`: düz zemin; kare anına interpole edilen EKF pozu; görüntü kenarına değen kutu reddedilir.
  - `follow_core.py`:
    - FOLLOW_TARGET gönderimi (bilinmeyen hız için 0 değil NaN)
    - `TargetKalman`, `DistanceBand`
    - `LinkImpairment` (Gilbert-Elliott)
  - `deney.py` / `analiz.py`: test parkuru deseni.
  - Alınmayacaklar:
    - Kırmızı renk eşikli dedektör
    - `mono_cam_cm3` modeli, `renkli_duz` dünyası, Tk paneli
    - `kur.sh`'ın kilitli `Tools/simulation/gz` altına symlink kurması
    - `px4_hook.post`'un build klasörüne yazması
    - Sabit kodlu `x500_mono_cam_0` konu adı
    - Sabitlenmemiş `reportlab`
- Model: Vision `origin/model-training` dalı, `models/person_detection_model_v0.2.pt` (Ultralytics YOLO, ~22 MB, AGPL-3.0). Repo dışındaki klasöre kopyalanarak kullanılır.
- Gerçek dron ayarları: `~/Desktop/Follow/4_Ucus/Drone parametreleri/22.08.2026.params`, ayrıca 4019 (`x500_v2`) kazançları. Bunlar şu an `ROMFS/.../4030_gz_x500_tez` içinde `param set-default` olarak duruyor.

### Takip Soruları

Sorulmadı. Cevaplar yeterince açıktı; belirsiz kalan noktalar aşağıda "Açık konular" altında kayıtlıdır.

## Görseller

### Sağlanan dosyalar
- `planning/visuals/blok_diyagram_elle.jpeg` (kaynak: `~/Desktop/Follow/3_m06_Simulasyon/WhatsApp Image 2026-10-23 at 22.25.30.jpeg`): Kâğıda elle çizilmiş dört kutu. Akış: "Gazebodaki kamera" → "Model" → "PX4" → "Simülasyon". Model'den PX4'e kıvrık bir ok, PX4'ten Simülasyon'a düz bir ok var. Simülasyon → Kamera dönüş oku çizilmemiş; issue #7'deki mermaid diyagramında kesikli ok olarak var (döngü örtük).

### Görsel çıkarımlar
- Ana veri akışı tek yönlü bir döngüdür: Gazebo kamerası → algılama modeli → PX4 → simülasyon (dronun hareketi kamerayı değiştirir).
- Doğruluk düzeyi: düşük (kavramsal el çizimi). Arayüz tasarımı değil, mimarinin üst seviye akışıdır.
- Gereksinim: spec'e el çiziminin yanında **ayrıntılı dijital bir blok diyagram** eklenir. Bu diyagram `planning/visuals/` altında ya da spec içinde (ör. mermaid) olur. İçeriği:
  - Gazebo kamera konusu
  - Kamera kusurları aşaması
  - Model (kare → kutu listesi)
  - LOS / FOLLOW_TARGET üretimi
  - MAVLink
  - PX4 (takip kaynağı seçimi)
  - gz_bridge / Gazebo
  - Hakem (doğru cevap), QGC video yayını
  - Simülasyon → kamera dönüş oku
- Referans videolar (`~/Desktop/Follow/3_m06_Simulasyon/Videolar/`, 11.10 tarihli 11 dosya: insan yürüyüşü yandan/yakın, eski/yeni insan sahneleri, `dunya_kalabalik_park(_etiketli).webm`) F1'in mevcut görsel durumunu gösterir. Yalnızca referans olarak anılır, repoya kopyalanmaz (kural 9).

### Diğer kaynak belgeler (spec klasörüne kopyalandı)
- `planning/kaynaklar/Kamera_ve_Takip_Ayarlari_Raporu.pdf`: "Kamera Neden 45° Aşağı Bakmalı?" (8 sayfa, 23–24.10). Yaklaşma mesafesi belgesinin kaynağıdır. İçeriği spec'e Türkçe metin olarak da taşınacak.

## Gereksinimler Özeti

### İşlevsel Gereksinimler

**Faz A: 15.11.2026'ya kadar, ilk PR**

1. **Belgeler (spec içinde)**
   - El çizimi blok diyagram (mevcut) + ayrıntılı dijital blok diyagram.
   - **Yaklaşma mesafesi belgesi.** 45° raporunun içeriği Türkçe metin olarak verilir:
     - Kural "yükseklik ≈ geride durma"; stad 8/8, çim 10/10, ağaç üstü 15/12 m.
     - 8 m'de 6.5–10 m, 10 m'de 8–12 m geride çalışır; 6 m altı çalışmaz.
     - Dikey yarı açı 20.5°.
     - Gerekçeler ve "30° neden seçilmedi?" bölümü.
     - Not: sayılar eski WSL denemesinden, renkli hedefle elde edildi; gerçek modelle yeniden ölçüm Faz B'dedir.
   - **Kamera parametreleri:**
     - CM3 Standard (IMX708), yatay 66° × dikey 41°, 2304×1296 (2×2 birleştirilmiş), 30 fps.
     - Montaj: gövde altı ön, base_link'e göre (0.151, 0, −0.035) m, sabit 45° aşağı.
     - 22.10 ölçümleri: fx 1773.7±0.2 (tanımlı 1773.9), cx 1152.3, cy 647.3, k ≈ 0, RMS 0.04 px; solvePnP montaj hatası 1.9 mm / 0.03°.
     - Veri sayfası tutarsızlığı: 4.74 mm / 2.8 µm → fx 1693 (HFOV 68.5°), oysa 66° → fx 1774.
     - Gürültü sorunu: tanımlanan stddev'in ~1/5'i uygulanıyor.
     - Saatler: RTF 0.97, PX4–Gazebo farkı ±4 ms, kare Python'a ~20 ms'de ulaşıyor.
   - **İnsan hedefinin nasıl hareket ettiği:**
     - Model: Mingfei actor (CC BY 4.0), düzeltilmiş `walk_tez`/`run_tez`.
     - `yuruyus.py` kuralları:
       - İvme: yürürken 2 m/s², koşarken 2.5 m/s².
       - Köşelerde dönüş yarıçapı v²/1.5.
       - 135°'den keskin dönüşte ve beklemeden sonra kalkışta 0.3 m'lik yayda adım atarak döner.
       - Hız %5, çizgi ~8 cm dalgalanır.
     - Senaryo YAML alanları, `diger_insanlar`, kıyafetler.
     - Sınırlar: Gazebo actor konumu yayınlamaz, bu yüzden doğru cevap yoldan hesaplanır; ağaçla çarpışma yok; herkes aynı beden.
   - **"Varsayımlar" başlığı.** Ortak spec'ler m03/m04/m05 yazılmadığı için şunlar kesin değildir:
     - `TEZ_LOS` mesajı (`DEBUG_VECT`, 30 Hz, gövde FRD birim vektör, UDP 14540)
     - `FOLLOW_TARGET` kullanımı
     - Eksen ve frame kuralları
     - Düz zemin geolocation
     - Zaman damgası anlamı

2. **Gazebo kamerasından görüntü okuma (laptop)**
   - `x500_tez` kamerasının Gazebo konusu Python'da okunur. Kare sim zamanı damgasıyla alınır.
   - Kare okuyucu ile model arasında basit bir arayüz vardır: kare girer, kutu listesi çıkar. Vision'ın m08/m10 kodu sonradan yerine takılabilir.

3. **Modelin bu görüntüde çalışması**
   - Varsayılan model Yusuf Ortatepe'nin v0.2 `.pt`'si; çalıştırma laptop CPU'sunda (AMD, CUDA yok).
   - Kıyas için stok COCO YOLOv8s seçilebilir.
   - Model yolu `--model <yol>` ile verilir. Varsayılan klasör repo dışında `~/auto-follow-modeller/` (değiştirilebilir). Kullanılan dosyanın sha256 özeti spec'e yazılır.
   - Model üst verisi (YOLO türü, giriş boyutu, sınıflar) bilinmiyor. Bu yüzden:
     - Sınıf adları `.pt` dosyasından okunur.
     - `--imgsz`, `--conf`, `--sinif` ile değiştirilebilir.
   - Kare başına işlem süresi loglanır.

4. **Gecikme zinciri ve kare atlama**
   - Sim gerçek zamanda akar. Model yetişemediğinde kareler atlanır.
   - Ayarlanabilir yakalama→PX4 gecikmesi ve saat kayması uygulanır.
   - İşlenen kare hızı ve uçtan uca gecikme ölçülür.

5. **Kamera kusurları aşaması (altyapı)**
   - Gazebo karesi ile model arasında, senaryodan ayarlanan bir aşama kurulur. Faz A'da bütün kusurlar varsayılan olarak **kapalıdır**.

6. **Hareketli insan hedefi**
   - Mevcut F1 hedefi, senaryoları ve dünyaları (`duz_alan`, `cayir`, `kalabalik_park` dahil) kullanılır.

7. **İki LOS kaynağı (senaryo başına seçilir)**
   - (i) Model kutusundan, `kamera.py` zinciriyle gövde FRD'de hesaplanan yön.
   - (ii) Hakemin doğru cevabı olan `los_govde`.
   - Seçilen kaynak `DEBUG_VECT` adı `TEZ_LOS` ile 30 Hz gönderilir (Varsayımlar).

8. **Takip kaynağı / kontrolcü seçimi (birinci sınıf gereksinim, çalışma anında seçilir)**
   - `follow_me`: Stok PX4 Follow Me ile kapalı döngü. `FOLLOW_TARGET` model kutusundan düz zemin geolocation ile hesaplanır. `FLW_TGT_HT 8`, `FLW_TGT_DST 8`.
   - `tez_los` + harici özel mod: `TEZ_LOS` yayınlanır ve PX4 adıyla verilen harici özel moda geçirilir. Yusuf Kurt'un m15 modu buraya takılır.
   - `yok`: Açık döngü / yalnız veri. Dron takip etmez; veri akışı, ölçüm ve kayıt yapılır.
   - **Takım arkadaşı entegrasyon kılavuzu.** Bir arkadaşın kendi PX4 modülünü simin kullandığı SITL derlemesine nasıl ekleyeceği, derleyeceği ve ona karşı bir senaryoyu nasıl koşturacağı adım adım yazılır.
   - Her kontrolcü için **aynı ölçütler ve aynı video** üretilir; kontrolcüler karşılaştırılabilir.

9. **PX4 tarafı: (b) yolu**
   - PX4 / ROMFS dosyası değişmez. Stok 4001 airframe + `PX4_SIM_MODEL=x500_tez` kullanılır.
   - Gerçek dronun ayarları başlangıçta yüklenir: 4019 kazançları + `22.08.2026.params`'tan ilgili parametreler (`FLW_TGT_HT 8`, `FLW_TGT_DST 8`, `FLW_TGT_ALT_M 0`, `EKF2_HGT_REF 1`, `EKF2_MAG_TYPE 0`, `MPC_YAWRAUTO_MAX 60`, `MPC_TILTMAX_AIR 45` vb.).
   - Daldaki 3 ROMFS dosyası geri alınır: `4030_gz_x500_tez`, `.post`, `airframes/CMakeLists.txt`. `verify_pin.sh --worktree` geçer.
   - "Tez Auto Follow" iskelet modülü (`tez/px4/`) m06 PR'ına girmez.
   - F0 kabul testi (mod kontrolü PX4'ün kendi modlarına uyarlanır) ve `tez/sim/README.md` güncellenir.
   - Hüseyin'in onayı: onay bekliyor.

10. **Takım arkadaşları için kolay kurulum**
    - Repoyu klonlayan biri kurulum → derleme → çalıştırma betikleriyle simi ayağa kaldırabilir.
    - Adımlar belgelenir: ön koşullar, `kur.sh`, model dosyasının yerleştirilmesi, AMD hibrit GPU için `DRI_PRIME=1` notu.

11. **QGC'ye video**
    - `goruntu_yayini.py` yeniden yazılır. Akış: Gazebo karesi (→ kusurlar) → model kutusu ve doğru cevap kutusu çizimi → H.264 RTP UDP 5600 → QGC.
    - Biçim 1280×720, 15 fps.

12. **Senaryo, ölçüm ve video çıktısı**
    - `senaryo.py` ve `rapor.html` genişler. Her koşuda otomatik olarak şunlar çıkar:
      - (a) Model ölçütleri (hakemin segmentasyon kutusuna göre): IoU, kaçırılan kareler, yanlış kişi seçimi (aynı kıyafetli kişi dahil).
      - (b) LOS açı hatası (model kaynaklı ile doğru cevap arasında).
      - (c) Kare başına işlem süresi ve uçtan uca gecikme.
      - (d) Takip ölçütleri: yatay mesafe, kadrajda kalma, en uzun kayıp.
      - (e) VLC'de açılan **MP4 (H.264)** video: dron kamerası + model ve doğru cevap kutuları + yan yana üstten görünüm.
    - Başarı eşikleri boş kalır; yalnızca ölçülür (m01 sayıları belirleyince eklenir).

**Faz B: 15.11'den sonra, aynı spec'e bağlı ikinci PR**
- Kamera kusurlarının ayarı ve açılması: gürültü düzeltmesi (Gazebo'nun ~1/5 uygulaması), hareket bulanıklığı, rolling shutter, pozlama/parlaklık.
- Wi-Fi gecikme/kayıp benzetimi (video yayını için).
- Yaklaşma mesafelerinin (8/8, 10/10, 15/12) yeni simde gerçek modelle, kapalı döngüde yeniden ölçülmesi.

**Sonraya / şimdilik kapsam dışı (belki ileride; taahhüt edilmedi)**
- Rüzgâr ve ani esintiler.
- Gerçekçi GPS gürültüsü (simde ~2 cm, gerçek M8N'de metre düzeyinde; PX4 kaynağına dokunmadan).
- Eğimli zemin (%3–7) ve aşağı bakan mesafe sensörü.
- İnsan çeşitliliği (boy, saç, ayakkabı).

### Yeniden Kullanım Fırsatları
- `tez/sim/araclar/kayit.py`: hakem doğru cevabı, `los_govde`, görünürlük ve segmentasyon kutuları. Model ölçütlerinin referansı ve LOS kaynağı (ii).
- `tez/sim/araclar/kamera.py`: piksel → kamera → gövde FRD → NED zinciri. LOS kaynağı (i) ve geolocation için.
- `tez/sim/araclar/px4_baglanti.py`: MAVLink bağlantısı (UDP 14540, GCS heartbeat). `DEBUG_VECT` / `FOLLOW_TARGET` gönderimi ve mod geçişi buna eklenir.
- `tez/sim/araclar/senaryo.py`, `rapor.py`, `simulasyon.py`, `onizleme.py`: senaryo yönetimi, rapor, sim aç/kapat, video üretimi.
- `tez/sim/araclar/f0_kabul.sh` / `f0_testi.py`: (b) yoluna ve stok modlara uyarlanacak.
- Deney dalı:
  - `goruntu_yayini.py`: kare alma deseni, GStreamer hattı, çizim.
  - `geolocation.py`: düz zemin, kare anına poz interpolasyonu, kenar kutusu reddi.
  - `follow_core.py`: FOLLOW_TARGET'ta NaN hız anlamı.
- 4030 airframe'deki 4019 kazanç listesi: (b) yolunda başlangıç parametrelerine taşınır.

### Kapsam Sınırları

**Kapsam içinde:**
- Faz A'daki 1–12 numaralı maddeler (belgeler; kamera okuma; model; gecikme ve kare atlama; kusur altyapısı; hareketli hedef; iki LOS kaynağı; takip kaynağı/kontrolcü seçimi ve entegrasyon kılavuzu; (b) yolu; kolay kurulum; QGC videosu; ölçüm ve MP4 video).
- Faz B: kamera kusurlarının ayarı ve açılması, Wi-Fi benzetimi, yaklaşma mesafelerinin yeniden ölçülmesi.

**Kapsam dışında:**
- PX4 özel takip modu (m15, Yusuf Kurt); m06 yalnızca onu takıp test etmeyi kolaylaştırır.
- Asıl pikselden gövde vektörüne dönüşüm (m10, Yusuf Ortatepe); m06'daki dönüşüm geçicidir.
- Hailo, asıl model seçimi ve Hailo ile tutarlı simülasyon algılaması (m07/m08).
- Model eğitimi, veri toplama ve etiketleme (Aşama 8).
- Qt operatör arayüzü.
- Gerçek uçuş, CM3 kalibrasyonu (m09).
- Gerçek Pi video yayını ve yer istasyonu gösterimi (m20/m24, Vision).
- Ortak ölçüm altyapısı (m17, çatı).
- Dronun gerçek kütlesi (m21; ölçülene kadar standart X500).
- ROS 2, Gazebo Classic.
- Rüzgâr, GPS gürültüsü, eğimli zemin + lidar, insan çeşitliliği (şimdilik; belki ileride).

### Teknik Hususlar
- **PX4 v1.17.0 kilitli.** (b) yolu sayesinde PX4 dosyası değişmez. Değişiklik yalnızca `tez/*` altında olur (`allowed-paths.txt`). `verify_pin.sh --worktree` geçmelidir.
- **Kural 7:** `tez/sim` çalışma anında Vision'a ya da çatıya `../` ile bağlanmaz. Model dosyası repo dışından yol argümanıyla okunur.
- **Kural 9:** `.pt`, video, `.ulg` repoya girmez. Sonuçlar `tez/sim/sonuclar/` altında git dışında kalır.
- **Kural 4, sürüm sabitliği:**
  - `ultralytics` ve `torch` (CPU sürümü) sabit sürümle bir requirements dosyasına (ör. `tez/env/` altında) ve `tez/env/VERSIONS.md`'ye yazılır.
  - Video için gereken GStreamer/x264 ve `python3-gi` apt paketleri de `VERSIONS.md`'ye yazılır.
  - Çatıdaki `agent-os/product/tech-stack.md` ve `docs/02-ortak-yazilim-surumleri.md` ayrı bir çatı PR'ında güncellenir (Hüseyin).
- **Lisans:** Ultralytics AGPL-3.0. Spec'e not düşülür; model yerel simde çalıştırılır, dağıtılmaz.
- **Donanım ve ortam:**
  - Laptop AMD hibrit GPU (RX 6600M): CUDA yok, model CPU'da çalışır; Gazebo için `DRI_PRIME=1`.
  - Python 3.12, venv `~/Desktop/Projects/Auto-Follow/.venv-tez`.
  - Gazebo Python bağları sistem paketinden gelir.
- **Gazebo:** Harmonic, gz-sim 8.15.0. `server.config` GStreamer kamerasız. Kamera konusu `/x500_tez/kamera/image`.
- **MAVLink ve PX4:**
  - Mesajlar yalnızca PX4 v1.17.0'ın desteklediği mesajlardır (`DEBUG_VECT`, `FOLLOW_TARGET`); yeni mesaj/dialect yok.
  - Araçlar 14540'a GCS gibi bağlanır. `DEBUG_VECT` her bağlantıdan aynı konuya düştüğü için `name` filtresi gerekir.
  - x500 GCS heartbeat olmadan arm etmez.
- **Çalışma süresi:** Sim gerçek zamanda koşar (lockstep, RTF ~0.97). Model gecikmesi ve kare atlaması ölçülüp raporlanır.
- **Önceki tuzaklar (devir.md §6):**
  - Actor `loop=true` olmalı.
  - `interpolate_x` her yörüngede ayrı dosya yolu ister.
  - Büyük görüntü alırken MAVLink UDP tamponu taşabilir; 4 MB tampon kullanılır.
  - Ortam değişkenleri: `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`, `GZ_IP=127.0.0.1`.
  - PX4 durdurma: `px4-shutdown`.
- **Testler:**
  - Donanımsız pytest: kusur aşaması, LOS/geolocation dönüşümleri, model arayüzü (taklit model ile), mesaj paketleme.
  - SITL kabul betikleri: F0 güncellenir, m06 için yeni kabul eklenir.
  - Değerlendirme ULog + doğru cevap CSV'sinden betikle yapılır. Kullanıcı ayrıca MP4 videoyla görsel kontrol yapar.
- **Kod stili:** `tez/sim/ruff.toml` ile ruff 0.16.9. Kod, değişken adları ve yorumlar İngilizce; belgeler Türkçe.
- **Commit:** Her görev grubu ayrı commit (`2026-11-10-m06-sim-ortami: ...`). Push ve PR kullanıcının onayıyla yapılır.

### Açık Konular (onay / bilgi bekleyen)
- **Hüseyin onayı bekleyenler:**
  - (b) yolu ve iskelet modülün çıkarılması.
  - m06/m08 sınırı.
  - Ortak model depolama yeri.
  - Çatı `tech-stack.md` / `docs/02` güncellemesi.
  - Geri bildirim mesajının gönderilip gönderilmediği bilinmiyor.
- **Model üst verisi:** YOLO türü, giriş boyutu ve sınıflar bilinmiyor. Kullanıcı Yusuf Ortatepe'ye soracak (soru listesi repo dışında: `~/Desktop/Follow/Yusuf_Ortatepe_model_sorulari.txt`). Bu yüzden uygulama sınıf adlarını `.pt`'den okur ve `--imgsz` / `--conf` / `--sinif` ile değiştirmeye izin verir.
- **Ortak spec'ler yazılınca güncellenecekler:** `TEZ_LOS` biçimi, frame/eksen, zaman damgası ve "hedef yok" sinyali. m03/m04/m05 yazılınca "Varsayımlar" bölümü güncellenir.
- **Kontrolcü entegrasyonu:** Yusuf Kurt / Yusuf Algan modunun adı ("AUTO FOLLOW") ve parametre ön eki (`AF_XXX`) kesin değil. Takip kaynağı seçimindeki harici mod adı bu yüzden yapılandırılabilir olmalıdır.
