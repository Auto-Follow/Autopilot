# Görev Grubu 5 — Hedef seçimi, LOS (i)/(ii), `TEZ_LOS` ve adla mod seçimi

- Tarih: 12.11.2026 · dal `ozellik/m06-sim-ortami` · taban commit `c55d9ca1ab` (Görev grubu 4); bütün koşular
  `c55d9ca1ab` + çalışma ağacı üstünde
- Durum: **uygulandı ve test edildi**, commit'lenmedi.
- Kısaca: Model artık her işlenen karede takip edilecek kişinin kutusunu seçiyor, kutunun yönünü (LOS) dronun gövde
  eksenlerinde hesaplıyor ve PX4'e `DEBUG_VECT` adı `TEZ_LOS` olarak gönderiyor; kutu yoksa "hedef yok" (NaN) gidiyor.
  İstenirse model yerine hakemin doğru cevabı (LOS ii) her kamera karesinde gidiyor. PX4 gönderilenlerin
  %99.8–100'ünü ULog'a yazdı. Takip modu yalnız adıyla seçiliyor (`yok` → "Hold", `tez_los` → `--mod-adi`); PX4'ün
  sunmadığı bir ad simülasyon açılmadan reddediliyor. Kalabalık parkta model kaynağında yakalamadan gönderime ort.
  ≈ 124–130 ms geçiyor; model yönü ile doğru yön arasındaki açı ort. ≈ 0.2°.
- `TEZ_LOS` biçimi ortak ICD (m05) yazılmadığı için **varsayımdır** (spec "Varsayımlar" 1); kesinleşmiş değildir.

## Ne yapıldı

| Alt görev | Dosya | Özet |
|---|---|---|
| 5.1 | `testler/test_takip.py` (yeni, 6 test fonksiyonu, 13 durum) | İlk kilit (en yüksek IoU, kilit yoksa nedeni); en yakın kutu ve kapı (1.5 köşegen, sınırın iki yanı); 10 işlenen karede kilit kaybı, sayaç sıfırlama, yeniden kilit; LOS (i) gidiş-dönüşü 4 poz × 2 kamera (biri bozulmalı) < 0.01°; takip iş parçacığının model ve hakem kaynakları (sahte saat ve sahte bağlantıyla: satırlar, `tez_los.csv`, `uctan_uca_ms`) |
| 5.1 | `testler/test_mesajlar.py` (yeni, 5 test) | `DEBUG_VECT` paketleme/çözme (ad, `time_usec`, birim vektör, NaN); geçersiz vektörün reddi; akış kuralları (bağlantı yok, aynı / eski kare, 30 ms sınırı, geçersiz); tek gönderim kilidi (4 iş parçacığı × 25 gönderim, çakışma yok); `AVAILABLE_MODES` adları (standart, seçilemeyen, harici) ve sim açılmadan ad denetimi; stok mod listesinin PX4 kaynağıyla (`ui.hpp`, `VehicleStatus.msg`) aynılığı |
| 5.1 | `testler/test_gecikme.py` (yeni, 1 test), `test_kayit.py` (+1), `test_rapor.py` (+1), `test_hedef.py` | Gecikme hattında sıra; hakemin satır + segmentasyon birleştirmesi; ULog'daki `TEZ_LOS` sayımı ve değerle eşleştirme; ara durum testi (`tez_los`, `--los hakem` artık bağlı, `henuz_bagli_degil` = `{video.mp4: 8}`) |
| 5.2 | `araclar/takip.py` (yeni) | `Selection` (geçici hedef seçimi), `Referee`, `los_of_box` (LOS i: kutu merkezi → `Camera.pixel_to_los` → `camera_to_body(45°)`), `angle_deg`, `Tracker` (takip iş parçacıkları, `tez_los.csv`, ölçüler), `ROW_COLUMNS` / `LOS_COLUMNS` |
| 5.2 | `araclar/kayit.py` | `FrameJoin` + `is_visible`; `Recorder(on_frame=...)`: hakemin karesi satırı ve segmentasyon karesi ikisi de gelince takip tarafına verilir (kayıt dışında satırsız); `join_dropped`, `errors` |
| 5.3 | `araclar/gecikme.py` (yeni) | `DelayLine`: sıra koruyan hat, öğe başına gecikme, `serbest` damgası; gecikme 0 ve bekleyen yokken çağıranın iş parçacığında |
| 5.4 | `araclar/px4_baglanti.py` | `serialize_sends` (tek gönderim kilidi), `check_los`, `los_message`, `Vehicle.send_los`, `LosSender` (akış kuralları ve sayaçlar), `mode_entry`, `STOCK_MODE_NAMES`, `STANDARD_MODE_NAMES`, `check_mode_name`; `modes()` standart modları adlandırır, seçilemeyenleri atlar |
| 5.5 | `araclar/senaryo.py`, `araclar/algilama.py`, `araclar/rapor.py` | Takip iş parçacıkları koşuya bağlandı (model sonucu → seçim → LOS → gecikme hattı → gönderim → `algilama.csv` satırı); `DetectionLog` ek sütun alır (`csv_cell` herkese açık); `TEZ_LOS` akışı PX4 bağlantısıyla başlar, kayıtla biter; ilerleme satırları, kilit olayları, `ozet.json` → `tez_los` ve `olcutler`; `rapor.ulog_tez_los` (ULog'daki `TEZ_LOS` sayısı, değerle eşleştirme, PX4 damgasıyla gecikme) ve rapor etiketleri |
| 5.6 | `senaryo.py`, `hedef.py`, `px4_baglanti.py` | `check_mode` (sim ve model açılmadan); koşuda ad PX4'ün listesinde aranır, liste `ayarlar.takip.px4_modlari`'ye yazılır; `hedef.unwired`'dan `tez_los` ve `los: hakem`, `not_in_effect`'ten `takip.los` silindi |
| 5.7 | — | Aşağıda "Test sonuçları" |
| belge | `tez/sim/README.md`, `tez/sim/ruff.toml`, `spec.md`, `tasks.md`, `implementation/kabul-kosulari.md` | README: durum, ara durum, adla mod, çıktılar (`algilama.csv` yeni sütunları, `tez_los.csv`), "Hedef seçimi ve TEZ_LOS"; ruff: `gecikme`, `takip`; spec: sapmalar ve ölçümler ("Uygulamada (5. grup)" notları, Varsayımlar 1, Ölçüt Tanımları, Açık Konular); tasks: 5.x işaretlendi, 6.3 / 7.3 / 12.2'ye notlar |

## Kararlar ve gerekçeler

1. **Takip iş parçacığı = modelin sonuç iş parçacığı.** 4. gruptaki `ModelProcess` her sonucu sırayla tek bir iş
   parçacığında veriyor; seçim, LOS ve gönderim orada yapılıyor (`Tracker.on_model`). Ayrı bir kuyruk + iş parçacığı
   GIL çekişmeli ana süreçte ölçülen yola bir geçiş daha eklerdi. Pi'de de algılama → karar → gönderim tek döngüdür.
   Hakemin kareleri ise gz-transport iş parçacığından gelir; orada iş yapılmaz, kuyruğa konup `tez-hakem-los` iş
   parçacığında işlenir (Gazebo geri çağırmaları kısa kalmalı).
2. **Satır gönderimden sonra yazılır** (spec: "Ardından satırı `algilama.csv`'ye yazar"). Gecikme hattı 12. grupta
   gecikme eklediğinde satır, mesaj hattan çıkınca hattın iş parçacığında yazılır; gönderim sütunları her zaman dolu
   olur. `kare_defteri` bunu da doğrular (işlenen = ana sürece ulaşan = `algilama.csv` satırı; her koşuda tutarlı).
3. **İlk kilit için en az IoU 0.3** ve hedefin `gorunur` olması. Spec yalnız "en yüksek IoU" diyor; eşiksiz, hedefle
   ilgisi olmayan bir kutuya (IoU 0.01) kilitlenilebilirdi. 0.3, ölçütlerin bir kutuyu bir insana ait saydığı eşik.
   Kilitliyken hakeme hiç bakılmaz; kapı son eşleşen kutuyla kurulur.
4. **Yeniden kilit bir sonraki işlenen karede** (operatör tepki süresi 0). Spec bunu belirtmiyor; en basit ve
   iyimser yorum. Açık karar olarak yazıldı (aşağıda).
5. **"En çok 30 Hz" yakalama zamanıyla**: iki gönderilen mesajın kare zamanları en az 30 ms ayrık olmalı, kare
   zamanı yalnız ileri gider, aynı kare ikinci kez gitmez. Simde kamera kareleri 32 / 36 ms arayla gelir (4 ms fizik
   adımı, 30.3 kare/sim-s); 33.3 ms'lik bir sınır geçerli hakem karelerinin ≈ %1'ini atardı. Gönderim (duvar)
   zamanına göre bir sınır da iş parçacığı titremesiyle iyi kareleri atardı (gönderimler bazen 1–2 ms arayla
   kümeleniyor, videodaki çift çizgiler). Hakem kaynağında 30.3 mesaj/sim-s ölçüldü, reddedilen 0.
6. **İki taraflı doğrulama** `LosSender`'da (akış kuralları) ve `Vehicle.send_los` / `los_message`'da (vektör):
   geçersiz vektör PX4'e hiç gitmez ve sayılır. Koşularda geçersiz 0 (beklenen: LOS birim vektörün dönmüş halidir).
7. **Tek gönderim kilidi:** pymavlink'in `MAVLink.send`'i bir kilitle sarıldı (`serialize_sends`); bütün `*_send`
   çağrıları ondan geçtiği için GCS heartbeat, komutlar, parametre okuma ve `TEZ_LOS` tek kilitten geçer. 6. grubun
   `FOLLOW_TARGET`'ı da kendiliğinden kilitli olur.
8. **Akış ne zaman var?** PX4 bağlantısı kurulunca başlar (önceki işlenmiş kareler `baglanti_yok`, koşu başına
   78–345), kayıt bitince model süreciyle birlikte kapanır. Kayıttan önce hakem yoktur: model kaynağında kilit
   yapılamaz, `hakem` kaynağında NaN gider; ikisi de "operatör henüz hedef seçmedi" durumudur. Kayıt sırasında modelin
   karesine hakemin yetişmediği yalnız 1 kare oldu (kayıt başlangıcı), yani model sonucu hakemi beklemeye gerek yok.
9. **Gönderim anı yazımdan hemen önce okunur** (uygulamada bulundu). İlk deneme A'da yazımdan sonra okunuyordu; PX4'ün
   kendi varış damgasıyla karşılaştırınca (değerle eşleştirerek) gönderim anı karelerin %7'sinde 10 ms'den, en çok
   71 ms geç çıktı: yazımdan sonra iş parçacığı GIL'i ve yüklü işlemcide sırasını bekliyor. Düzeltmeden sonra
   "PX4 varışı − gönderim" ort. −1.8…+1.1 ms, en az −11…−17 ms (PX4'ün saati Gazebo saatinden birkaç ms geride
   olabilir). Bu yüzden ULog'dan **PX4'ün damgasıyla uçtan uca gecikme** de çıkarılıyor (`uctan_uca_px4_ms_*`);
   iki ölçüm 1–2 ms içinde aynı.
10. **ULog sayımı 5. grupta öne alındı** (spec'te 7.3): 5.7'nin ±%5 koşulu her koşuda kendiliğinden denetlensin diye.
    Pencere PX4'ün varış damgasıyla; aşarsa olaylara yazılır. Yalnız `name == "TEZ_LOS"` sayılır.
11. **Mod adları:** PX4 `AVAILABLE_MODES`'ta standart modlara ad yazmıyor (Position, Return, Mission… boş geliyordu,
    hepsi `""` anahtarında birleşiyordu); onlara PX4'ün kendi adı verildi. Seçilemeyenler ("(Mode not available)" ×
    8, Termination) listeden çıktı. "Koşu başlamadan" denetimi için PX4'ün listesi ancak PX4 açılınca okunabildiğinden,
    PX4 v1.17.0'ın seçilebilir 17 stok mod adı bir sabit (`STOCK_MODE_NAMES`); test onu PX4 kaynağından türetip
    karşılaştırıyor, koşu da PX4'ün listesiyle karşılaştırıyor (fark olursa olay). Harici bir mod (m15) PX4 açılıp
    modül başlayınca kaydolur; `--px4-baslat` verilmişse ad koşuda, kalkıştan önce aranır (10. grup). Mod numarası
    hiçbir yerde yazılı değil; yalnız PX4'ün listesinden okunur.
12. **LOS (i) ve (ii) her kaynakta karşılaştırılır.** `algilama.csv`'de seçilen kutunun LOS (i)'i her zaman var;
    `los_i_ii_fark_*` aynı karenin LOS (ii)'siyle (seçilen kutu hedefken, IoU ≥ 0.5). 7. grubun `los_aci_hatasi`'ı
    (gönderilen LOS'a göre) bunun üstüne kurulur.

## Test sonuçları

| Kontrol | Sonuç |
|---|---|
| `$P -m pytest tez/sim/testler/test_takip.py tez/sim/testler/test_mesajlar.py -q` | **18 geçti** |
| `$P -m pytest tez/sim/testler -q` | **163 geçti** (önceki 142 + 21), 1 uyarı (önceden de vardı, protobuf) |
| Aynı testler `torch`/`torchvision`/`ultralytics` içe aktarması engellenmiş hâlde (içe aktarma kancası) | **163 geçti** |
| `ruff format` + `ruff check` (`tez/sim/ruff.toml`, ruff 0.16.9) | temiz |
| `tez/pin/verify_pin.sh --worktree` | **KILIT SAGLAM (v1.17.0)**. Not: betik PX4 dosyalarını commit'lenmiş durumda (`HEAD`) karşılaştırıyor; bu grubun değişiklikleri yalnız `tez/` ve `agent-os/` altında (`git status`) |
| `senaryo.py --senaryo kalabalik_park --ekransiz` (A2) | **GEÇTİ**, sayılar aşağıda |
| `... --takip tez_los --mod-adi "Hold"` (B2) | **GEÇTİ**: mod adıyla seçildi, "unresponsive" yok |
| `... --takip tez_los --mod-adi "Yok Boyle Mod"` | 0.7 s, çıkış kodu 2, sim ve model açılmadan 17 adı listeleyen hata |
| pyulog satırı (tasks.md 5.7) | A2: `{'debug_vect': 1048}`, B2: `{'debug_vect': 1000}` (ULog'un açık olduğu bütün süre; B2'de gönderilen 1001) |
| ULog ±%5 (kayıt penceresi) | A2 410 / 411 (%99.8), B2 389 / 389, C1 885 / 885, C2 886 / 886, D 415 / 415 |
| Ek: `--los hakem` (C1, model açık) ve `--los hakem --modelsiz` (C2) | ikisi de **GEÇTİ** |
| `tez/sim/araclar/f1_kabul.sh` | **GEÇTİ** (3 dk 41 s; iki koşu arası 0.000 m) |
| `tez/sim/araclar/f0_kabul.sh` (mod listesi kodu değiştiği için) | **GEÇTİ** (1 dk 9 s) |

Her koşudan önce `pgrep -x px4` / `pgrep -f "^gz sim"` boştu; sonra da açık PX4, Gazebo ya da model süreci kalmadı.

## Sayılar (`kalabalik_park`, kayıt penceresi 60–89.2 s)

| | A2: `yok`, LOS model | B2: `tez_los` "Hold", LOS model | C1: `tez_los`, LOS hakem | C2: hakem, modelsiz |
|---|---|---|---|---|
| Gönderilen `TEZ_LOS` (NaN) | 411 (156) | 389 (150) | 885 (168) | 886 (167) |
| PX4 ULog'unda | 410 (%99.8) | 389 (%100) | 885 (%100) | 886 (%100) |
| Değerle eşleşen yönlü kayıt | 254 / 254 | 239 / 239 | 717 / 717 | 719 / 719 |
| Mesaj hızı [mesaj/sim-s] | 14.1 | 13.3 | 30.3 | 30.3 |
| Geçersiz / reddedilen | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| `uctan_uca_ms` ort. / p50 / p95 / en çok | 124 / 122 / 164 / 182 | 130 / 126 / 168 / 202 | 71 / 61 / 110 / 118 | 33 / 27 / 62 / 73 |
| PX4 damgasıyla uçtan uca ort. / p95 | 124 / 164 | 130 / 168 | 73 / 112 | 31 / 60 |
| PX4 varışı − gönderim ort. (en az) [ms] | −0.1 (−13.9) | −0.9 (−11.0) | +1.1 (−12.9) | −1.8 (−4.3) |
| Kilit / kayıp / yeniden (bütün koşu) | 2 / 1 / 1 | 2 / 1 / 1 | 2 / 1 / 1 | — |
| Seçili kare; hedef görünürken doğru kutu | %62; %66 | %62; %58 | %61; %73 | — |
| LOS (i)–(ii) ort. / p50 / p95 / en çok [°] | 0.22 / 0.20 / 0.41 / 0.68 | 0.21 / 0.20 / 0.42 / 0.51 | 0.26 / 0.18 / 0.56 / 1.83 | — |
| RTF | 0.816 | 0.838 | 0.831 | 1.000 |

**Uçtan uca gecikmenin bileşenleri (A2, model kaynağı, ortalama):** kare model sürecine ulaşma 30.6 sim-ms + modeli
bekleme 17.4 ms + çözme ve model 87.1 ms + FIFO'dan ana sürece geçiş 9.6 ms (en çok 82 ms) + seçim ve LOS 0.18 ms +
gecikme hattı 0.03 ms → 124 sim-ms. Duvar saatindeki parçalar RTF 0.82'de sim saatine göre kısalır; gerçek zamanda
akan bir simde (RTF 1) aynı iş ≈ 150 ms tutardı (aşağıda "Sim-gerçek farkları").

**Kilit olayları (A2):** 27.62 s ilk kilit (IoU 0.87; dron 25–28 s'de hazır, hakem kayıtla başlar) · 68.21 s kilit
kaybı: hedef çamın arkasına girdi, 10 işlenen karede kapıda kutu yok · 78.41 s yeniden kilit: hedef görünür olunca
ve model onu IoU ≥ 0.3'le bulunca. Arada 87 kare "hedef görünmüyor", 60 kare "kutu eşleşmedi" (model hedefi
kaçırdı). İlk deneme A'da bir de 0.2 s sonra yeniden kilit + 0.6 s sonra tekrar kayıp görüldü (kısmi örtülme).

**LOS (i)–(ii) farkı neden 0 değil?** Model kutusunun merkezi gövde merkezi değildir (kutu ayaktan başa; hakem
gövde merkezini, yerden 0.9 m, alır); kutu kenarları birkaç piksel oynar; örtülüyken ya da iki kişi tek kutuda
birleşince merkez kayar. En büyük fark (D, 1.71°) model kutusunun hedefi yanındaki sarı giysili kişiyle tek kutuda
birleştirdiği karede (JPG aşağıda). Montaj ve kamera parametreleri simde birebir doğru olduğu için bu fark yalnız
kutudan gelir; zincirin kendisi testte < 0.01° (bozulmalı kamerada da).

**İşlemci (B'de örneklendi, 100 = bir çekirdek):** model 406, Gazebo 178, `senaryo.py` 50 (hedef dururken) → 90
(hedef yürürken), PX4 22, tarayıcı (Chrome) 20. A2'de aynı desen (45 → 89). Ana süreçteki artışın nedeni bu grupta
ayrıştırılmadı: takip işi iki aşamada aynı (aynı kare ve mesaj hızı), hakemin segmentasyon maskesi kişi sayısıyla
yalnız ≈ 0.3 ms artıyor (ölçüldü). RTF 0.82–0.84 4. gruptakiyle aynı; ilk deneme A'daki 0.76 dış yükten (aynı kodla
B 0.839).

## Görseller (repo dışı)

`~/Desktop/Follow/3_m06_Simulasyon/Deneme/`:

| Dosya | Ne |
|---|---|
| `gorev5_kalabalik_park_yavas_x3.mp4` | **Ana video** (1 dk 45 s, 10 kare/s = 3 kat yavaş): önce ilk kilit (24–28 s), "zaman atlaması" kartı, sonra 58–90 s. Her kamera karesinde: mavi kutu + mavi artı = hakemin hedefi ve gövde merkezi (LOS ii'nin görüntüdeki izdüşümü), turuncu = diğer insanlar; kırmızı = PX4'ün o anda elindeki son model sonucu (kalın = seçilen kutu + güveni, kırmızı çarpı = LOS i'nin izdüşümü, ince = diğer kutular), sarı kesikli daire = kapı (1.5 köşegen). Alt panelde kilit durumu ("KİLİTLİ", "EŞLEŞME YOK 3/10", "KİLİT KAYBI", "KİLİT YOK: nedeni"), PX4'teki son `TEZ_LOS` (ya da NaN), o karenin `uctan_uca_ms`'i ve şu an kaç ms eski olduğu, LOS (i)–(ii) açısı (aynı karede ve gecikme dahil şimdiki hakeme göre). En altta son 3 s: kilit durumları, giden `TEZ_LOS`'lar (mavi hedefli, gri NaN) ve uçtan uca gecikme eğrisi. Kilit olaylarında üstte yeşil/kırmızı şerit |
| `gorev5_kalabalik_park_gercek_hiz.mp4` | Aynısı gerçek hızda (36 s, 30 kare/s) |
| `gorev5_kalabalik_park_ilk_kilit_t25.58.jpg` | İlk kilit: hakemin hedef kutusuyla en çok örtüşen kutu seçildi |
| `gorev5_kalabalik_park_kilit_kaybi_t69.37.jpg` | Kilit kaybı: hedef çamın arkasında, kapıda kutu yok, giden `TEZ_LOS` NaN |
| `gorev5_kalabalik_park_yeniden_kilit_t78.54.jpg` | Hedef ağacın arkasından çıktı, hakemle yeniden kilit (kilit 2) |
| `gorev5_kalabalik_park_los_farki_en_buyuk_t81.61.jpg` | LOS (i)–(ii) farkının en büyük olduğu an (1.71°): model kutusu hedefle sarılı kişiyi birleştirmiş |
| `gorev5_tez_los_ulog_karsilastirma.png` | B2: gönderilen `TEZ_LOS`'lar (`tez_los.csv`) ile PX4'ün ULog'a yazdıkları (`debug_vect`): zaman çizgisi, birikimli sayı (1001 / 1000, eşleşen 1000) ve x, y, z bileşenleri üst üste |

Video ve kareler ölçüm koşularından değil, ayrı bir gösterim koşusundan (D) gelir: koşunun yanında çalışan bir
kayıtçı (scratchpad betiği, repoya girmedi) 24–90 s arasındaki 2000 kamera karesini 1280×720 JPEG yazdı; kayıtçının
yüküyle RTF 0.773. Kareler aynı sim zamanlı `algilama.csv` / `kutular.csv` / `tez_los.csv` / `dogru_cevap.csv`
satırlarıyla birleştirildi. MP4: ffmpeg 6.1.1 (sistem), `libx264`, `yuv420p`, `+faststart` (4. gruptaki yol; ffmpeg'in
sürüm sabitlemesi 8. grubun işi, repo kodu kullanmıyor). Boyut 1280×1060 (görüntü + panel + şerit).

## Karşılaşılan sorunlar

- **Gönderim anı geç okunuyordu:** karar 9. İlk deneme A'nın uçtan uca sayıları tabloya girmedi.
- **Standart modların adı boş geliyordu:** karar 11. Eski `modes()` Position, Return… modlarını `""` adıyla tek
  anahtarda birleştiriyordu; F0 yalnız "Hold" / "Follow Target" aradığı için fark edilmemişti. F0 yeniden geçti.
- **Değerle eşleştirmede yuvarlama:** `tez_los.csv` 6 ondalık yazıyor, PX4 float32 tutuyor; tam eşitlik 1227'nin
  417'sini buldu, 2e-6 toleransla 1226'sını.
- **Kendi betiğimin hatası (repo kodu değil):** F0'ı koşu dizisinden sonra başlatacak bekleme döngüsü
  `pgrep -f "kosular.sh"` ile kendi komut satırını da eşledi ve hiç bitmedi; döngü durduruldu, F0 elle bir kez
  koşuldu (GEÇTİ). Bir de bir `rm` komutu güvenlik denetimine takıldı ve çalışmadı; silme yapılmadan yeni bir
  klasörle devam edildi. Kullanıcının hiçbir süreci ya da dosyası etkilenmedi.

## Kalan sim-gerçek farkları

- **RTF < 1:** model işlemciyi Gazebo'yla paylaşıyor, sim gerçek zamandan %16–18 yavaş akıyor; modelin ve iş
  parçacıklarının süreleri sim saatine göre kısalıyor. Gerçek zamanda model kaynağının uçtan uca gecikmesi ≈ 150 ms
  olurdu (124 / 0.82). Pi + Hailo'daki süreler bambaşka olacak (m08).
- **Hakem kaynağı (LOS ii) gerçek bir algılayıcı değildir:** yalnız Gazebo'nun bildiği konum ve segmentasyonla
  "mükemmel algılayıcı"dır; gecikmesi (33–71 ms) Python'daki hakemin gecikmesidir, bir modelin değil.
- **İlk kilit ve yeniden kilit hakemden:** gerçekte operatör QGC'de tıklar (tepki süresi ~1–2 s) ya da m11'in
  otomatik yeniden bulma yöntemi çalışır; simde tepki süresi 0.
- **Bağlantı:** sim UDP 127.0.0.1'de (kayıpsız, ≈ 0 ms); gerçekte Pi ↔ Pixhawk TELEM2 seri hat (m04): bant
  genişliği, tampon ve kayıp ayrı ölçülmeli. Simde PX4 gönderilenlerin %99.8–100'ünü yazdı.
- **Montaj:** takip tarafı nominal 45° ve nominal ofsetle hesaplıyor, simdeki montaj da nominal (Gazebo'dan okunan
  hata 0.03°). Gerçek araçta açı ölçülmeli; 1° montaj hatası doğrudan 1° LOS hatasıdır.
- **Kamera:** simde bozulma yok, iç parametreler kusursuz; gerçek CM3 kalibre edilmeli (m09). Zincir bozulmayı
  hesaba katıyor (testli).
- **`time_usec`:** gönderiliyor ama PX4 v1.17.0 uORB'a taşımıyor; PX4 tarafı gecikmeyi mesajdan öğrenemez
  (spec "Varsayımlar" 2). Pixhawk 6C'de `DEBUG_VECT` alıcısı derleniyor (kart dosyalarında `CONSTRAINED_FLASH` yok),
  donanımda denenmedi.
- **Gönderim anının ölçümü** yüklü bir laptopta ±10–17 ms titriyor; PX4 tarafı varış damgası bunu doğruluyor.

## Açık kararlar ve bekleyenler

- **Yeniden kilidin zamanı (kullanıcı / m11):** operatör tepki süresi 0 mı kalsın, bir `takip.*` alanı mı eklensin?
- **İlk kilidin en az IoU'su 0.3 (kullanıcı / m11):** spec'te sayı yoktu; ölçütlerle tutarlı olsun diye seçildi.
- **`TEZ_LOS` biçimi (Kurt / Algan, m05):** ad, gövde FRD birim vektör, NaN = hedef yok, `time_usec` = yakalama;
  PX4 `time_usec`'i düşürüyor. Takılan modun `name == "TEZ_LOS"` ile süzmesi ve zaman aşımını varış zamanına göre
  uygulaması gerekiyor (spec C5).
- 4. gruptan süren: model çekirdek sayısı ve RTF; `imgsz`.

## Sonraki gruplar için notlar

- **6. grup:** `Tracker.on_model` seçimi yapıyor (`Choice.box`); konum hesabı aynı yerde, aynı kutuyla yapılır ve
  `ROW_COLUMNS`'a sütun eklenir. `FOLLOW_TARGET` `self.m.mav` üstünden gönderilince tek kilitten geçer;
  `LosSender` benzeri bir 10 Hz kuralı yazılabilir. Poz geçmişi (`message_hooks`) ana döngüyü bozmamalı.
- **7. grup:** `takip.Tracker.metrics` ve `_selection_metrics` (`uctan_uca_ms_*`, `tez_los_*`, `yeniden_kilit_sayisi`,
  `secim_dogru_orani`, `los_i_ii_fark_*`) `olcum.py`'ye taşınır; `rapor.ulog_tez_los` hazır.
- **8. grup:** videonun sol paneli için `algilama.csv`'de seçilen kutu, kapı (`kapi_u/v/px`), `los_i_*`, giden
  vektör ve `gonderim_sim` hazır; "PX4'ün elindeki son sonuç" `gonderim_sim`'e göre seçilir. Bu gruptaki gösterim
  betiğinin düzeni yukarıda.
- **10. grup:** `check_mode_name` `--px4-baslat` verilince adı koşuya bırakır; koşudaki denetim ve
  `ayarlar.takip.px4_modlari` hazır.
- **12. grup:** `DelayLine.put(..., extra_ms)` öğe başına gecikme alıyor; titreşim ve `time_usec` için saat modeli
  `Tracker`'a eklenir.

---

## Kendin dene

Bu bölümdeki her şey bilgisayarında hazır: paketler kurulu, model dosyası yerinde, PX4 derli.

**Başlamadan:** Terminal açmak için **Ctrl+Alt+T**'ye bas. Aşağıdaki gri kutulardaki komutları kopyala, terminale
**Ctrl+Shift+V** ile yapıştır (terminalde Ctrl+V çalışmaz) ve **Enter**'a bas. Bir komutu yarıda kesmek için
**Ctrl+C**.

### 1. Hazırlık (her yeni terminalde bir kez)

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot
P=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python
```

Bir şey yazmaz; bu normal.

### 2. Hazır videoyu izle

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev5_kalabalik_park_yavas_x3.mp4
```

Dronun kamerası açılır (10 m yükseklik, 45° aşağı, dron yerinde bekliyor), 3 kat yavaş:
- **Mavi kutu ve mavi artı:** simin bildiği gerçek hedef ve gövdesinin ortası. Artı, "doğru yön"ün (LOS ii)
  görüntüdeki yeridir.
- **Kalın kırmızı kutu ve kırmızı çarpı:** modelin bulduğu kutulardan takip için seçilen ve onun yönü (LOS i).
  Çarpı artıya ne kadar yakınsa model yönü o kadar doğru. İnce kırmızılar modelin bulduğu diğer insanlar.
- **Sarı kesikli daire (kapı):** bir sonraki karede seçilen kutunun merkezi bu dairenin içinde olmalı. Dışındaysa
  "EŞLEŞME YOK"; 10 kez üst üste olursa **"KİLİT KAYBI"** (kırmızı şerit). Hedef tekrar görününce **"YENİDEN
  KİLİT"** (yeşil şerit).
- **Alt panel:** PX4'ün o anda elindeki son yön (`TEZ_LOS`, üç sayı; hedef yoksa `NaN`), o karenin yakalanmasından
  PX4'e gönderilmesine kadar geçen süre (uçtan uca, ≈ 120 ms) ve o kutunun şu an kaç ms eski olduğu. Kırmızı kutu
  insanın biraz gerisinde kalıyorsa sebebi bu gecikmedir.
- **En alt şerit (son 3 saniye):** yeşil = kilitli, sarı = bu karede eşleşme yok, kırmızı = kilit kaybı, gri = kilit
  yok; mavi çizgiler PX4'e giden yönler, gri çizgiler "hedef yok" mesajları; sarı eğri gecikme.

Videoda şunlara bak: ~25 s'de ilk kilit; 58 s'den sonra hedef yürüyor; ~66–69 s'de hedef çamın arkasına giriyor,
kutular kayboluyor, kilit düşüyor ve PX4'e "NaN" gidiyor; ~78 s'de hedef çıkınca yeniden kilit; ~81 s'de hedef sarılı
kişiyle yan yana gelince model ikisini tek kutuda birleştiriyor ve kırmızı çarpı artıdan ayrılıyor (1.7°).

VLC kısayolları: **Boşluk** duraklat/sürdür, **E** bir kare ileri, **Shift+→ / Shift+←** 3 s ileri/geri,
**]** / **[** hızlandır/yavaşlat, **F** tam ekran. Gerçek hız için dosya adını `gorev5_kalabalik_park_gercek_hiz.mp4`
yap.

Fotoğraflar ve grafik:

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev5_kalabalik_park_kilit_kaybi_t69.37.jpg
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev5_tez_los_ulog_karsilastirma.png
```

Grafikte üstte mavi/gri çizgiler bizim gönderdiğimiz, turuncu/gri çizgiler PX4'ün kaydına yazdığı mesajlardır; ortada
iki birikimli sayı neredeyse aynı çizgi (1001 gönderildi, 1000 kayıtlı); altta yön bileşenleri iki tarafta aynı.

### 3. Kendin koştur (pencere yok, ~2 dakika)

Önce açık bir sim olmadığından emin ol (iki satır da bir şey yazmamalı):

```bash
pgrep -x px4
pgrep -f "^gz sim"
```

Sonra (dron yerinde bekler, model yönü PX4'e gider):

```bash
$P tez/sim/araclar/senaryo.py --senaryo kalabalik_park --ekransiz
```

Sonda şuna benzer satırlar görürsün:

```text
[01:06:05] TEZ_LOS (model): kayıt penceresinde 411 gönderildi (156 hedef yok, 14.1 mesaj/sim-s), 0 geçersiz; uçtan uca ort. 124 ms (p50 122, p95 164, en çok 182); ...
[01:06:05] PX4'ün ULog'unda kayıt penceresinde 410 TEZ_LOS (debug_vect); yönlü olanlardan 254 gönderilenle eşleşti, PX4'ün varış damgasıyla uçtan uca ort. 124 ms ...
[01:06:05] Hedef seçimi: 2 kilit, 1 kilit kaybı, 1 yeniden kilit (bütün koşu); ... LOS (i)-(ii) farkı ort. 0.22°, p95 0.41°, en çok 0.68° (219 kare)
[01:06:06] SONUÇ: GEÇTİ
```

Takip modunu adıyla seçmek (duman testi; "Hold" stok bir moddur, dron yine yerinde bekler):

```bash
$P tez/sim/araclar/senaryo.py --senaryo kalabalik_park --ekransiz --takip tez_los --mod-adi "Hold"
```

Yanlış bir ad, simülasyon hiç açılmadan, 1 saniyeden kısa sürede PX4'ün mod adlarını listeleyerek reddedilir:

```bash
$P tez/sim/araclar/senaryo.py --senaryo kalabalik_park --ekransiz --takip tez_los --mod-adi "Yok Boyle Mod"
```

Model yerine "mükemmel algılayıcı" (hakem) yönünü göndermek (her kamera karesinde, saniyede ≈ 30 mesaj):

```bash
$P tez/sim/araclar/senaryo.py --senaryo kalabalik_park --ekransiz --los hakem
```

### 4. Çıktıları aç

```bash
K=$(ls -dt tez/sim/sonuclar/*_kalabalik_park | head -1); echo $K
firefox "$K/rapor.html"                   # "Ölçümler"de TEZ_LOS, gecikme, kilit ve LOS satırları; "Olaylar"da kilit anları
firefox "$K/ozet.json"                    # "tez_los" (bütün koşu) ve "olcutler"; ayarlar -> takip -> px4_modlari
column -s, -t "$K/tez_los.csv" | less -S  # her TEZ_LOS denemesi; q ile çık
```

`algilama.csv`'de önemli yeni sütunlar: `secim` (ilk_kilit, izleme, eslesmedi, kilit_kaybi, yeniden_kilit,
kilitsiz), `kilitsiz_neden`, `los_i_x/y/z` (modelin yönü), `tez_los_x/y/z` (PX4'e giden; boş = NaN), `uctan_uca_ms`.

PX4'ün kaydında kaç `TEZ_LOS` var (tasks.md'deki satır):

```bash
$P -c "import sys;from pyulog import ULog;u=ULog(sys.argv[1],['debug_vect']);print({d.name:len(d.data['timestamp']) for d in u.data_list})" "$K/ucus.ulg"
```

### 5. Kontroller

```bash
$P -m pytest tez/sim/testler -q
tez/sim/araclar/f1_kabul.sh
```

Beklenen: `163 passed`; F1 (~4 dakika, modelsiz) sonunda `SONUÇ: GEÇTİ`.

### Bir şey ters giderse

| Mesaj | Ne yapmalı |
|---|---|
| `Zaten çalışan bir PX4 veya Gazebo var` | Açık simi kendi terminalinde Ctrl+C ile kapat ya da bitmesini bekle |
| `takip.mod_adi: '...' PX4'ün seçilebilir modları arasında yok` | Listedeki adlardan birini aynen yaz (büyük/küçük harf ve boşluk dahil, ör. `"Hold"`) |
| `takip.mod_adi: takip.kaynak tez_los iken zorunlu` | `--takip tez_los`'un yanına `--mod-adi "Hold"` ekle |
| Raporda `RTF ... (< 0.9)` uyarısı | Beklenen (model işlemciyi paylaşıyor); tarayıcı gibi ağır programları kapatmak biraz yardımcı olur |
| Raporda `TEZ_LOS: PX4'ün ULog'unda ... kayıt, gönderilen ...` olayı | PX4'e ulaşan sayı %5'ten fazla farklı: `sim.log`'u ve bilgisayarın yükünü kontrol et |
