# Görev Grubu 4 — Kare okuyucu, kusur aşaması, model süreci ve `algilama.csv`

- Tarih: 11.11.2026 · dal `ozellik/m06-sim-ortami` · taban commit `4955aeebef` (Görev grubu 3); çalışırken dala
  `f27712003b` ve `8586dcad7a` (tasks.md takvim notu) geldi, SITL koşuları `8586dcad7a` üstünde yapıldı
- Durum: **uygulandı ve test edildi**, commit'lenmedi.
- Kısaca: v0.2 modeli artık senaryo koşusunda, PX4 ve Gazebo açıkken dronun kamerasında canlı çalışıyor. Model ayrı
  bir süreçte, her zaman yalnız en yeni kareyi alıyor; yetişemediği kareler atlanıyor ve tek tek defterde. Kayıt
  penceresinde kare başına `model_ms` ≈ 85 ms, saniyede ≈ 14 kare işleniyor, karelerin ≈ %54'ü atlanıyor. Model
  açıkken Gazebo'nun gerçek zaman oranı 1.00'dan **0.83'e** düşüyor (uyarı çıkıyor; aşağıda "Açık kararlar").

## Ne yapıldı

| Alt görev | Dosya | Özet |
|---|---|---|
| 4.1 | `testler/test_kusurlar.py` (yeni, 2 test), `testler/test_goruntu.py` (yeni, 3 test), `testler/test_algilama.py` (+3 test) | Boş ayarda kare bit bit aynı; Faz B alanı ve bilinmeyen alan reddi (senaryo yüklenirken de); en yeni kare + atlanan kare defteri (sınırlı liste dahil); mesaj çözme; sim ↔ duvar saati ve RTF; Gazebo'nun yayın zamanıyla eşleme; taklit ultralytics sonucundan `Kutu` (kırpma, piksel kenarı, boş kutu), IoU; bir karenin kusur aşaması + sahte algılayıcıdan geçişi; `algilama.csv`/`kutular.csv` satırları ve pencere sayıları |
| 4.1 | `testler/test_hedef.py`, `testler/conftest.py` | Ara durum testi güncellendi (algılama ayarları artık bağlı, `henuz_bagli_degil` = `{takip.los: 5, video.mp4: 8}`); `kusurlar` hatalarına 2 durum; conftest saf Python protobuf'u araçlarla aynı seçer |
| 4.2 | `araclar/goruntu.py` (yeni) | `LatestFrame` (tek yuva, `put`/`take`, defter), `stamp` (başlıktan sim zamanı), `decode` (kopyasız, salt okunur RGB), `FrameReader` (`subscribe_raw`), `clock_pair` + `SimClock` (`/world/<dünya>/clock`, 100 Hz'e kısılmış; `to_sim`, `wall_at`, `rtf`, `rtf_min`) |
| 4.3 | `araclar/kusurlar.py` (yeni) | `check` (alan denetimi), `KameraKusurlari.uygula(kare, t)` (Faz A: aynı dizi), `kusur_ms` |
| 4.4 | `araclar/algilama.py` | `boxes_of` (ultralytics sonucu → `Kutu`), `to_boxes` boş kutuyu atar, `iou`; `ModelSettings`, `FrameResult`, `process` (çözme → kusur → algılayıcı, her adım zamanlı), `model_process` (spawn edilen süreç), `ModelProcess` (ana süreç tarafı: başlat/bekle, sonuç iş parçacığı, durdur), `ModelError`; `DetectionLog` (`algilama.csv`, `kutular.csv`, pencere sayıları + geçici IoU kontrolü) |
| 4.5 | `araclar/senaryo.py`, `araclar/rapor.py`, `araclar/hedef.py` | `check_model` (sim açılmadan sha256 + paket kontrolü), `start_model`, `frame_books`; model süreci simden önce açılır, kayıt bitince kapanır; ilerleme satırları; RTF + 0.9 uyarısı; `ozet.json` → `olcutler` (+ yeni anahtarlar), `kare_defteri`, `ayarlar.algilama.{model, model_dosyasi, model_bilgisi}`; `rapor.html`'de yeni satırlar. `hedef.py`: `kusurlar` yüklenirken denetlenir; `algilama.*`/`kusurlar` ara hataları ve `henuz_bagli_degil["algilama.etkin"]` silindi |
| 4.6 | `araclar/f1_testi.py`, `araclar/f1_kabul.sh`, `ruff.toml` | F1 `--modelsiz` koşar; `known-first-party`'ye `goruntu`, `kusurlar` (`algilama` zaten vardı) |
| belge | `tez/sim/README.md`, `spec.md`, `tasks.md`, `implementation/kabul-kosulari.md` | README: yeni çıktılar ve "Model koşuda nasıl çalışır"; spec: sapmalar, ölçülen sayılar, açık karar; tasks: 4.x işaretlendi, 5.5'e not |

## Kararlar ve gerekçeler

1. **Tek yuva, kuyruk yok.** `LatestFrame` yalnız en yeni kareyi tutar; model meşgulken gelen kare bekleyenin yerine
   geçer ve `atlanan` sayılır. Model bir kareyi en fazla bir kez alır. Böylece bellekte en çok bir bekleyen kare
   olur ve eski kare hiç işlenmez (spec 2). Geri çağırma yalnız ham bayt, `time.monotonic()` ve sayaç saklar.
2. **Atlanan karelerin de sim zamanı bilinir (spec'e eklendi).** Yerine yenisi gelen karenin yalnız ilk 256 baytı
   (protobuf başlığı: damga + çerçeve adı, ≈ 60 bayt) tutulur ve model kareyi alırken çözülür. Kare verisi yine yalnız
   işlenen karede çözülür. Gerekçe: kayıt penceresindeki sayılar tahminsiz çıkar ve hakemin kamera kare sayısıyla
   (`camera_info`) birebir karşılaştırılabilir (`okuyucuya_ulasmayan`, ölçülen 0). Liste de sınırlıdır (900 kare);
   taşan kısım sayılır (`listesiz_atlanan`, ölçülen 0).
3. **Saat eşlemesi Gazebo'nun yayın zamanıyla (uygulamada bulunan hata).** İlk ölçüm koşusunda `ulasma_ms`
   ortalaması **−5 ms** çıktı (kare, çekilmeden önce varmış gibi). Sebep: saat mesajının geri çağırması ana süreçte
   çalışıyor ve ana süreç meşgul (hakemin 2.2 MB'lık segmentasyon karelerini saf Python'la çözmesi, MAVLink); geri
   çağırma onlarca ms geç çalışınca "şu sim zamanı şu duvar anında" eşlemesi kayıyordu. Gazebo her saat mesajına
   yayınladığı andaki sistem saatini (`Clock.system`) yazıyor; boştaki bir süreçte alış − `system` farkı 0.09–0.31 ms
   ölçüldü. Eşleme artık bu alanla yapılıyor (`goruntu.clock_pair`, testli); alan yoksa alış anına düşülür. Düzeltmeden
   sonra `ulasma_ms` 31 ms.
4. **Model süreci simden önce açılır, kayıt bitince kapanır.** `check_model` (sha256, `modeller.yaml`, ultralytics
   kurulu mu) → model süreci ("spawn") açılır ve model yüklenene kadar beklenir → ancak sonra çıktı klasörü yazılır ve
   Gazebo/PX4 açılır. Model bir ayarı reddederse (`--sinif kedi`, `--imgsz 650`) koşu 3 s içinde, hiçbir şey açılmadan
   ve klasör oluşmadan çıkış kodu 2 ile durur. Model Gazebo kare yayınlamaya başladığı andan kayıt bitene kadar çalışır
   (gerçek araçta da model hep açıktır; kalkışta CPU yükü gerçekçi). Kayıt bitince kapanır, iniş modelsiz yapılır.
   `algilama.csv` bu yüzden model sürecinin bütün ömrünü kapsar (t ≈ 0.008 s'den itibaren); ölçütler yalnız kayıt
   penceresinden hesaplanır. Dosyalar ilk sonuçla açılır.
5. **`model_ms` algılayıcının `algila()` çağrısının çevresinden ölçülür** (renk çevirme ve kutu dönüşümü dahil),
   `YoloAlgilayici.last_model_ms` değil. Böylece Vision'ın takacağı başka bir `Algilayici` da aynı ölçümü alır
   (`model_dene.py` ile aynı). Ayrıca `cozme_ms` (mesaj çözme, ort. 1.4 ms; spec'in tahmini ~14 ms'ti) ve `kusur_ms`
   (0.007 ms) ayrı yazılır; `islem_ms` = bitiş − başlama.
6. **Defter iki katmanlı.** (a) `kare_defteri` (model sürecinin bütün ömrü): okuyucuya gelen = işlenen + atlanan +
   bekleyen; işlenenlerin hepsi ana sürece ve `algilama.csv`'ye ulaştı mı (`tutarli`). Tutmazsa olaylara yazılır.
   (b) Kayıt penceresi: `uretilen` (okuyucuya ulaşan), `islenen`, `atlanan`, `atlanan_kare_orani = 1 − islenen/uretilen`,
   `kamera_karesi` (hakemin sayısı), `okuyucuya_ulasmayan`. FIFO'nun büyümediği `teslim_ms` ile görülür (ort. 10 ms).
7. **`kusurlar` senaryo yüklenirken denetlenir** (`hedef._defects` → `kusurlar.check`). Faz B alanı geçici bir "Görev
   grubu N" hatası değil, kalıcı bir Faz A kuralıdır; ara durum satırı silindi.
8. **`to_boxes` düzeltmesi:** kırpıldıktan sonra hiç piksel kapsamayan kutu atılır (görüntünün tamamen dışındaki
   kutu). Ultralytics kutuları zaten kırptığı için pratikte olmaz, ama kural `u0 ≤ u < u1` ile tutarlı. Ultralytics
   sonucunun açılması `boxes_of`'a ayrıldı (taklit sonuçla test edilebilsin diye); `to_boxes` 1 boyutlu girdiyi de
   düzleştiriyor.
9. **Ctrl+C:** terminaldeki Ctrl+C bütün süreç grubuna gider. Model süreci SIGINT'i yok sayar; ana süreç onu `stop`
   olayıyla durdurur ve defter yine gelir. Denendi (aşağıda).
10. **RTF:** `rtf_ort` (kayıt penceresi) ve `rtf_min_5s`, saat eşlemesinden; 0.9 altında olaylara uyarı. Uyarı sonucu
    değiştirmez (spec: yalnız ölçülür). Varsayılan 4 çekirdek değiştirilmedi (spec'teki değer); karar açık.
11. **Geçici IoU kontrolü** `DetectionLog.metrics`'te (`iou05_kare_sayisi`, `hedef_gorunur_islenen`, `iou_max`); 7.
    grupta `olcum.py`'ye taşınır. Hiç eşleşme yoksa olaylara yazılır.
12. **`algilama.csv`'de seçim/LOS/konum sütunları yok:** 5–6. gruplar ekler; boş sütun bırakmak kafa karıştırırdı.
13. **conftest:** testlerde `gz.msgs10` saf Python protobuf ile açılsın diye `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION`
    araçlardaki gibi ayarlandı (aksi hâlde C uzantısı açılıp iki ek uyarı veriyordu).

## Test sonuçları

| Kontrol | Sonuç |
|---|---|
| `$P -m pytest tez/sim/testler/test_kusurlar.py tez/sim/testler/test_algilama.py tez/sim/testler/test_goruntu.py -q` | **14 geçti** |
| `$P -m pytest tez/sim/testler -q` | **142 geçti** (önceki 132 + 8 yeni test + `test_hedef`'te 2 yeni durum), 1 uyarı (önceden de vardı, protobuf) |
| `ruff format` + `ruff check` (`tez/sim/ruff.toml`, ruff 0.16.9) | temiz |
| `tez/pin/verify_pin.sh --worktree` | **KILIT SAGLAM (v1.17.0)** |
| Duman (Gazebo'suz, scratchpad): gz-transport'a 30 Hz'de gerçek bir Gazebo karesi yayınlayan betik + `ModelProcess` | 300 kare: 135 işlendi, 165 atlandı, 0 bekleyen (defter tutarlı); çıkış kodu 0; geçici ultralytics klasörü silindi; `model_ms` 73 ms |
| `tez/sim/araclar/f1_kabul.sh` (`--modelsiz`) | **GEÇTİ** (3 dk 41 s), iki kez (ilk kod ve son kod); son: RTF 1.000 / 0.999 |
| `senaryo.py --senaryo kalabalik_park --ekransiz` | **GEÇTİ** (2 dk 6 s) + RTF uyarısı; sayılar aşağıda |
| Hata yolları (sim açılmadan) | `--sinif kedi`, `--imgsz 650` → "Model hatası, simülasyon açılmadı" (2.75 s); eksik model, Faz B kusuru → "Senaryo hatası" (< 1 s); hepsi çıkış kodu 2, geride süreç yok |
| Ctrl+C (koşu ortasında süreç grubuna SIGINT) | Rapor yazıldı (TAMAMLANMADI, "Kullanıcı durdurdu"), defter tutarlı, geride süreç yok |

Her koşudan önce `pgrep -x px4` / `pgrep -f "^gz sim"` ile kontrol edildi (çalışan sim yoktu); her koşudan sonra
PX4, Gazebo ya da model süreci kalmadı.

## Sayılar (`kalabalik_park`, 4.7'deki komut, kayıt penceresi 60–89.2 s)

| Ölçüt | Değer |
|---|---|
| `model_ms` | ort. **85 ms**, p95 90, en çok 97 (Gazebo kapalıyken 3. grupta 56–66 ms) |
| İşlenen kare hızı | **13.9 kare/sim-s** (kamera 30.3 kare/sim-s) |
| Atlanan kare oranı | **%54** (886 kareden 406 işlendi, 480 atlandı); kameranın ürettiği 886 karenin hepsi okuyucuya ulaştı |
| Gecikmeler | kare okuyucuya ulaşma 31 ms (p95 35), modeli bekleme 19 ms, çözme 1.4 ms, sonuç kareden ≈ 122 sim-ms sonra hazır (p95 141); sonuç ana sürece FIFO'da 10 ms'de (en çok 78) geçti |
| RTF | **0.831** (en yavaş 5 s'lik dilim 0.819); aynı senaryo modelsiz 1.00 |
| Geçici IoU kontrolü | hedefin göründüğü 330 işlenmiş karenin **234'ünde** bir model kutusu hedefle IoU ≥ 0.5; en iyi IoU **0.94** |
| Kare defteri (model süreci boyunca) | 2708 kare = 1178 işlenen + 1529 atlanan + 1 bekleyen; 1178 sonuç ana sürece ve `algilama.csv`'ye ulaştı |

### RTF neden düştü (karşılaştırma koşuları, hepsi `kalabalik_park`)

| Koşu | RTF ort. (en düşük 5 s) | `model_ms` | İşlenen kare/sim-s | Atlanan |
|---|---|---|---|---|
| Modelsiz (F1 senaryosu, `yuruyen_insan`) | 1.000 (0.999) | — | — | — |
| Modelsiz + kameraya pasif abone (9 MB × 30 Hz alır, işlemez) | **1.000** (1.000) | — | — | — |
| Model, 4 çekirdek (varsayılan) | **0.831–0.843** (0.819–0.831) | 85 | 13.7–13.9 | %54–55 |
| Model, 2 çekirdek | **0.933** (0.929) | 135 | 7.8 | %74 |
| Model, 4 çekirdek + gösterim kayıtçısı (yalnız video için) | 0.815 (0.792) | 91 | 13.3 | %56 |

Sonuç: kamera görüntüsünün aktarımı RTF'yi düşürmüyor; düşüşün sebebi modelin hesap yükü. RTF < 1 iken sim dünyası
duvar saatinden yavaş aktığı için model sim saatine göre olduğundan hızlı görünür (85 ms duvar ≈ 71 sim-ms). Spec'teki
uyarı tam bu durum için var ve çalışıyor.

## Görseller (repo dışı)

`~/Desktop/Follow/3_m06_Simulasyon/Deneme/`:

| Dosya | Ne |
|---|---|
| `gorev4_kalabalik_park_yavas_x3.mp4` | **Ana video** (36 s): 62–74 s arasındaki her kamera karesi, 3 kat yavaş (10 kare/s). İşlenen kareler kırmızı model kutuları ve süreleriyle; atlananlar karartılmış, "ATLANDI"; mavi/turuncu hakem kutuları; altta son 1.5 s'nin zaman şeridi (yeşil: işlenen kare, gri: atlanan, kırmızı çubuk: modelin meşgul olduğu süre) |
| `gorev4_kalabalik_park_gercek_hiz.mp4` | Aynı video gerçek hızda (12 s, 30 kare/s) |
| `gorev4_kalabalik_park_islenen_tum_t62.04.jpg` | İşlenen kare: 4 kişinin 4'ü bulundu, hedefin IoU'su 0.85 |
| `gorev4_kalabalik_park_atlanan_t62.08.jpg` | Hemen sonraki kare atlandı (model meşguldü) |
| `gorev4_kalabalik_park_hedef_kacti_t64.22.jpg` | Model hedefi kaçırdı (IoU 0.00), diğer üç kişiyi buldu |
| `gorev4_kalabalik_park_hedef_agac_arkasi_t70.23.jpg` | Hedef çamın arkasında (hakemde görünmüyor); model diğer 4 kişiyi buldu |

Bu video ve kareler ölçüm koşusundan değil, ayrı bir gösterim koşusundan (yukarıdaki son satır) gelir: koşunun yanında
çalışan bir kayıtçı (scratchpad betiği, repoya girmedi) 62–74 s arasındaki kamera karelerini yarım çözünürlükte tuttu;
kareler aynı sim zamanına sahip `algilama.csv` / `kutular.csv` / `dogru_cevap.csv` satırlarıyla birleştirildi. Kamera
mesajı bütün abonelere aynı gider, yani model bu kareleri tam olarak böyle gördü. MP4'ü ffmpeg 6.1.1 (sistem) üretti;
ffmpeg'in sürüm sabitlemesi 8. grubun işidir, burada yalnız bu gösterim için kullanıldı, repo kodu kullanmıyor.

## Karşılaşılan sorunlar

- **Negatif `ulasma_ms`:** karar 3. İlk ölçüm koşusunun (`ulasma_ms` −5 ms) sayıları bu yüzden tabloya girmedi.
- **RTF 0.83:** karar 10, açık karar aşağıda.
- **Ctrl+C koşusunda yanıltıcı olay:** pencere (60 s) başlamadan durdurulunca olaylara "IoU kontrolü: hiçbir karede…"
  yazıldı. Artık pencerede işlenmiş kare yoksa "Kayıt penceresinde işlenmiş kare yok" yazılıyor.
- **Hata yolunda boş dosyalar:** model ayarı reddedildiğinde çıktı klasöründe boş CSV'ler ve dünya dosyası kalıyordu;
  model süreci artık klasöre bir şey yazılmadan önce açılıyor ve CSV'ler ilk sonuçla oluşuyor.
- **Ana süreçte GIL çekişmesi:** sonuç FIFO'dan ana sürece ort. 10 ms'de, en çok ≈ 80 ms'de geçiyor. Sebep ana
  süreçteki hakemin segmentasyon çözümü (saf Python protobuf, 30 Hz). 4. grupta yalnız ölçülüyor; 5. grupta bu süre
  gönderim gecikmesine girer (tasks.md 5.5'e not edildi).
- **Test betiği hatası (benim):** Ctrl+C denemesinde `setsid` kendini çatalladığı için süreç grubu ilk denemede
  okunamadı; koşu arka planda sürdü, sonra aynı koşunun grubuna SIGINT gönderilerek deneme tamamlandı. Kullanıcının bir
  süreci etkilenmedi.

## Açık kararlar ve bekleyenler

- **Model çekirdek sayısı ve RTF (kullanıcı/Hüseyin):** 4 çekirdekte RTF 0.83 (< 0.9 uyarısı), 2 çekirdekte 0.93 ama
  model 135 ms ve 7.8 kare/s. Seçenekler: 4'te kalıp uyarıyla yaşamak; 2–3 çekirdek; Gazebo'nun yükünü azaltmak (ör.
  hakemin segmentasyon kamerasını yalnız kayıtta açmak zaten yapılıyor, render ayarları). Varsayılan spec'teki 4 kaldı.
  Spec "Açık Konular"a yazıldı.
- **`imgsz` (Ortatepe/Hüseyin):** 3. gruptaki gözlem sürüyor: 640'ta hedefin göründüğü karelerin ≈ %71'inde
  (234/330) IoU ≥ 0.5; kaçırmalar videoda görülüyor (ör. 64.2 s).
- **CSV'yi açmak için LibreOffice kurulu değil:** "Kendin dene"de terminal ve VS Code yolu yazıldı; Calc istenirse
  `sudo apt install libreoffice-calc` (proje aracı değil, kişisel görüntüleyici; kurmak kullanıcının kararı).

## Sonraki gruplar için notlar

- **5. grup:** `ModelProcess(settings, on_result)` sonuçları sırayla tek bir iş parçacığında verir; seçim/LOS/gönderim
  `on_result`'ın içine (ya da `DetectionLog.add`'in yanına) gelir. `DetectionLog.ROW_COLUMNS`'a sütun eklenir.
  `SimClock.to_sim(monotonic)` gönderim anını sim saatine çevirir (`uctan_uca_ms`).
- **7. grup:** `DetectionLog.metrics` (zaman ve kare sayıları, geçici IoU) `olcum.py`'ye taşınır; `rtf_ort` zaten
  `ozet.json`'da. `rapor.write(more_metrics, sections)` yeni bölümler için kullanılabilir.
- **8. grup:** `gorev4_video.py`'deki zaman şeridi fikri (işlenen/atlanan kareler, modelin meşgul olduğu süre) MP4'ün
  sol paneline eklenebilir; betik scratchpad'deydi, tasarım bu belgede.
- **12. grup:** `FrameResult.basla/bitis` ve `SimClock` gecikme hattının girişidir.

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

Bir şey yazmaz; bu normal. `P`, ekibin Python'unun kısaltmasıdır.

### 2. Hazır videoyu izle

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev4_kalabalik_park_yavas_x3.mp4
```

VLC'de dronun kamerası açılır (10 m yükseklik, 45° aşağı, dron yerinde bekliyor), 3 kat yavaş:
- Sol üstte yeşil **"İŞLENDİ"**: model bu kareye baktı. Kırmızı kutular modelin bulduğu insanlar (altında güveni).
  Hemen altında o karenin süreleri: `model_ms` (modelin düşünme süresi), bekleme, ulaşma ve hedefin IoU'su (1'e yakın
  = model hedefi doğru yerde buldu).
- Karartılmış ve gri **"ATLANDI"**: model o sırada önceki kareyle meşguldü; bu kareye hiç bakmadı. Yaklaşık her
  iki kareden biri böyle.
- **Mavi kutu:** simin bildiği gerçek hedef (hakem). **Turuncu:** diğer insanlar.
- Alttaki şerit son 1.5 saniyeyi gösterir: yeşil çizgi işlenen kare, gri atlanan kare, kırmızı çubuk modelin meşgul
  olduğu süre. Model boşalır boşalmaz yalnız **en yeni** kareyi alır; eski kareler birikmez.

Gerçek hızda görmek için aynı komutta dosya adını `gorev4_kalabalik_park_gercek_hiz.mp4` yap. Duraklatmak için
**Boşluk**, kare kare ilerlemek için **E** tuşu.

Fotoğraflar:

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev4_kalabalik_park_hedef_kacti_t64.22.jpg
```

Bu karede model hedefi (mavi kutu) kaçırıyor ama diğer üç kişiyi buluyor. Aynı klasördeki diğer `gorev4_*.jpg`'ler:
hepsinin bulunduğu kare, atlanan kare, hedefin ağaç arkasında olduğu kare.

### 3. Kendin koştur (pencere yok, ~2 dakika)

Önce açık bir sim olmadığından emin ol (iki satır da bir şey yazmamalı; yazıyorsa o simi kendi terminalinde Ctrl+C
ile kapat ya da bitmesini bekle):

```bash
pgrep -x px4
pgrep -f "^gz sim"
```

Sonra:

```bash
$P tez/sim/araclar/senaryo.py --senaryo kalabalik_park --ekransiz
```

Şuna benzer satırlar görürsün:

```text
[20:27:04] Model süreci açılıyor: person_detection_model_v0.2.pt, CPU, 4 çekirdek (indirme ve analitik kapalı)...
[20:27:07] Model hazır: sınıf 0 (Person), imgsz 640 (adım 32), conf 0.25, ilk çağrı 1122 ms; kamera kusurları kapalı
[20:27:18] PX4 ve Gazebo hazır
[20:27:23] Kalkış: 10 m
[20:27:40] Kayıt başladı; hedef 60 s'de yürümeye başlayacak, senaryo 89 s'de bitecek
[20:28:17]   t = 60 s: model 776 kare işledi; son 10 s'de 13.3 kare/s, %56 kare atlandı; son kare 4 kutu, model_ms 88 ms
...
[20:29:09] RTF (kayıt penceresi): ort. 0.831, en düşük 0.819 (5 s'lik)
[20:29:09] Model: kayıt penceresinde 406 kare işlendi (13.9 kare/sim-s), 480 kare atlandı (%54; ...); model_ms ort. 85 ms ...
[20:29:09] IoU kontrolü (geçici): 234 işlenmiş karede bir model kutusu hedefin hakem kutusuyla IoU >= 0.5 (en iyi 0.94; ...)
[20:29:10] SONUÇ: GEÇTİ
```

`RTF 0.83` şu demek: model açıkken simülasyon gerçek zamandan %17 yavaş aktı (model işlemciyi Gazebo'yla paylaşıyor).
Rapordaki olaylarda bunun için bir uyarı görürsün; beklenen bir durum.

**Gazebo penceresini de görmek istersen** (dron havada bekler, insanlar yürür; pencere ek yük getirir, RTF biraz daha
düşebilir):

```bash
export DRI_PRIME=1
$P tez/sim/araclar/senaryo.py --senaryo kalabalik_park
```

`export DRI_PRIME=1` Gazebo'nun ayrık ekran kartını (AMD) kullanmasını sağlar; aynı terminalde bir kez yeterli.
Pencere koşu bitince kendisi kapanır; erken kapatmak istersen terminalde Ctrl+C (rapor yine yazılır).

### 4. Çıktıları aç

En yeni koşunun klasörünü bir değişkene al:

```bash
K=$(ls -dt tez/sim/sonuclar/*_kalabalik_park | head -1); echo $K
```

- **Rapor** (tarayıcıda; "Ölçümler" tablosunun sonunda model satırları, "Olaylar"da RTF uyarısı):

  ```bash
  firefox "$K/rapor.html"
  ```

- **`ozet.json`** (Firefox bunu açılır kapanır bir ağaç olarak gösterir; `olcutler`, `kare_defteri` ve
  `ayarlar` → `algilama`'ya tıkla):

  ```bash
  firefox "$K/ozet.json"
  ```

- **`algilama.csv`** (modelin işlediği her kare bir satır). LibreOffice bu bilgisayarda kurulu değil; şu an çalışan
  iki yol:

  ```bash
  column -s, -t "$K/algilama.csv" | less -S
  ```

  Tablo terminalde açılır; ok tuşlarıyla gez, **q** ile çık. Ya da VS Code'da düz metin olarak: `code "$K/algilama.csv"`.
  Önemli sütunlar: `t` (karenin sim zamanı, s), `onceki_atlanan` (bu kareden önce kaç kare atlandı), `model_ms`,
  `bekleme_ms`, `ulasma_ms`, `kutu_sayisi`. Modelin bulduğu kutular `kutular.csv`'de (aynı `t_us` anahtarıyla).
  Tablo programında açmak istersen önce `sudo apt install libreoffice-calc` (isteğe bağlı, kişisel araç), sonra
  `libreoffice --calc "$K/algilama.csv"`; açılan pencerede ayırıcı "Virgül" seçili olsun.

Sonuç klasörleri git'e girmez (`tez/sim/sonuclar/` yok sayılır).

### 5. Ayarlarla oyna

Komutun sonuna ekle (hepsini birden de):

| Ekle | Ne olur |
|---|---|
| `--modelsiz` | Model hiç açılmaz; RTF'nin 1.00'a döndüğünü görürsün |
| `--conf 0.5` | Yalnız güveni 0.5'ten büyük kutular sayılır |
| `--imgsz 960` | Model resmi daha büyük görür: küçük insanları daha iyi bulur ama yavaşlar, daha çok kare atlanır |
| `--sinif kedi` | Hata denemesi: Gazebo açılmadan, 3 saniyede "modelin sınıfları: 0: Person" der |

### 6. Kontroller

```bash
$P -m pytest tez/sim/testler -q
tez/sim/araclar/f1_kabul.sh
```

Beklenen: `142 passed`; F1 (~4 dakika, modelsiz) sonunda `SONUÇ: GEÇTİ`.

### Bir şey ters giderse

| Mesaj | Ne yapmalı |
|---|---|
| `Zaten çalışan bir PX4 veya Gazebo var` | Açık simi kendi terminalinde Ctrl+C ile kapat ya da bitmesini bekle, sonra tekrar dene |
| `Model hatası, simülasyon açılmadı: ...` | Mesajdaki ayarı düzelt (`--sinif`, `--imgsz` 32'nin katı olmalı) |
| `Senaryo hatası: Model dosyası yok: ...` | Mesajdaki "Almak için" komutunu çalıştır (`<Vision klasörü>` = `~/Desktop/Projects/Auto-Follow/Vision`) |
| `Senaryo hatası: kusurlar.<alan>: Faz B'de uygulanacak` | Senaryodaki `kusurlar:` alanını sil ya da `kusurlar: {}` yaz |
| Raporda `RTF ... (< 0.9)` uyarısı | Beklenen (model işlemciyi paylaşıyor); `--modelsiz` ile karşılaştırabilirsin |
