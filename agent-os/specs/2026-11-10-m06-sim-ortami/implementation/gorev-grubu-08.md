# Görev Grubu 8 — Kare kaydı ve MP4 video (kamera + kuşbakışı harita)

- Tarih: 13.11.2026 · dal `ozellik/m06-sim-ortami` · taban commit `33d8ec8842` (Görev grubu 7)
- Aynı oturumda iki iş: **A** bu belge (`tasks.md` 8.0–8.6 + kullanıcının 13.11 isteği: kuşbakışına 7. gruptaki
  açıklayıcı animasyonun öğeleri) ve **B** `tasks.md` 9.8'in öne alınması (`gorev-grubu-09-on-followme-ayar.md`). İki
  ayrı commit: A'nın yaması `~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev8_is_A.patch` (aşağıda "Commit ayrımı").
- Koşular `33d8ec8842` + çalışma ağacı (A + B) ile; B yalnız ölçüt ekler, videoyu değiştirmez.
- Durum: **uygulandı ve test edildi**, commit'lenmedi.

## Kısaca

Her koşu artık kendi `kosu.mp4`'ünü üretiyor (`senaryo.py` ve `toplu.py` dahil; `--videosuz` hariç): solda dronun
kamerası (hakemin kutuları, PX4'ün o anda elindeki model kutusu, "HEDEF YOK"), sağda kuşbakışı harita (kişi, dron,
kameranın yerde gördüğü alan, 3 m ve kameranın yakın görüş sınırı halkaları, dronun olması gereken yer, PX4'e giden
konumlar ve `follow_me`'de PX4'ün kendi kestirimi, varsaydığı rota, dronu gönderdiği yer), altta ne olduğunu söyleyen
ve sorun anında kırmızıya dönen bir durum satırı. 2000×720, 15 kare/s, H.264 / yuv420p, VLC 3.0.20'de açılıyor. Kareler
koşu sırasında ayrı bir süreçte yalnız diske yazılıyor, video koşudan sonra çevrimdışı birleştiriliyor. Video, dron
modunu seçtiği andan senaryo sonuna kadardır: kişinin durduğu "takip başı"nı (stok Follow Me'nin salınımı) da gösterir.

### Ne yapıldı

| Alt görev | Dosya | Özet |
|---|---|---|
| 8.1 | `testler/test_video.py` (yeni, 10 test), `testler/test_goruntu_yayini.py` (yeni, 3 test), `test_hedef.py`, `test_toplu.py` | 2000×720 birleşim ve çift boyut; kutuların 2304×1296 → 1280×720 ölçekle yerinde çizilmesi; PX4'ün o anda elindeki model sonucu (gönderim / çıkış / hazır anı); kameranın yerdeki izdüşümü (yakın ve uzak kenar elle hesaplanan değerle, ufka bakan ışınların kesilmesi); kuşbakışında kuzey yukarı, doğu sağ, ölçek çubuğu; durum satırı ve kırmızı/turuncu durumlar; taklit ffmpeg ile komut (`rawvideo`, `bgr24`, `2000x720`, `15`, `libx264`, `yuv420p`, `veryfast`, `crf 23`, `+faststart`) ve borudan giden baytlar (BGR sırası); küçük bir koşu klasöründen bütün video (kare sayısı = hakemin kaydının 1/15 s'leri, `kareler/`'in silinmesi / saklanması, kamera karesi yokken yer tutucu); kare–ızgara eşlemesi ve eksik kare; `onizleme.py`'nin MP4'ü. Kayıt: 15 fps ızgarası (her ikinci kare, kaybolan kare, pencere), JPEG (1280×720, renk sırası, geçici adla yazma), dolu kuyrukta kare düşürme ve sayma. `--kareleri-sakla` artık bağlı, `henuz_bagli_degil` boş; `toplu.html` her koşunun `kosu.mp4`'ünü bağlar |
| 8.2 | `tez/env/VERSIONS.md` | ffmpeg 7:6.1.1-3ubuntu5 (libavcodec60 aynı, libx264-164 2:0.164.3108+git31e19f9-1), VLC 3.0.20-3build6 (`dpkg-query -W`); kullanılmadan önce yazıldı |
| 8.3 | `araclar/goruntu_yayini.py` (yeni) | `FrameRecorder` (ana süreç tarafı: başlat, `begin`/`end` ile pencere, `stop` ile defter), `recorder_process` ("spawn" süreç: `subscribe_raw`, `nice 5`, OpenCV tek iş parçacığı), `FrameSink` (geri çağırma yalnız başlığı okur ve seçer; yazıcı iş parçacığı çözer, küçültür, JPEG yazar; dolu kuyrukta düşürür ve sayar), `GridPicker`, `write_jpeg`. QGC RTP kısmı 11. grupta |
| 8.4 | `araclar/video.py` (yeni) | `make(klasör)`: koşu klasörünün dosyalarından `kosu.mp4`; `Run`/`load` (dosyalar, ULog'dan PX4'ün Follow Target iç durumu), `moment` (bir anın her şeyi), `draw_camera`, `draw_map`, `status`, `Encoder` (ffmpeg borusu), `frames_by_slot`/`timeline`; komut satırı `video.py <klasör>`. `onizleme.py`'deki kutu çizimi (`draw_referee`) ve ffmpeg çağrısı (`Encoder`) burada ortak |
| 8.5 | `araclar/senaryo.py`, `rapor.py`, `hedef.py`, `toplu.py`, `onizleme.py`, `ruff.toml` | `senaryo.py`: kaydedici simden önce açılır, `_Recording` hakemin kaydıyla kare kaydını birlikte açıp kapatır, video `rapor.write`'ın `video` kancasıyla yapılır, `kareler/` sonra silinir (`--kareleri-sakla` ile kalır), günlüğe kaydedicinin defteri ve video satırı; `rapor.write`: kanca, `ozet.json` → `video`, raporun başında video satırı; `hedef.py`: ara hata ve `not_in_effect` satırı silindi; `toplu.py`: `kosu.mp4` bağlantısı; `onizleme.py`: WebM → MP4; `ruff.toml`: `goruntu_yayini`, `video` |
| belge | `spec.md`, `tasks.md`, `README.md`, `kabul-kosulari.md`, bu dosya | spec 9. madde (pencere, kaydedici, çevrimdışı birleştirme, kuşbakışı öğeleri), Dosya Planı, alan tablosu, Test Planı, sürüm TBD'si; tasks 8.x; README "Video (`kosu.mp4`)", çıktılar tablosu, önizleme, dosyalar |

### Kararlar ve gerekçeler

1. **Video hakemin kaydını kapsar (mod seçimi → senaryo sonu), yalnız ölçüt penceresini değil.** Spec "kayıt
   penceresi" diyordu; kodda "kayıt" (`Recorder.start`) dronun modunu seçtiği andır, ölçüt penceresi ise
   `zamanlama.baslama_s`'den başlar. Kullanıcının giderilmesini istediği salınım çoğunlukla kişi dururken, yani "takip
   başı"nda oluyor (stok Follow Me'nin ilk dönüşü, sahte hızlar); yalnız 60–89 s'yi gösteren bir video bunu
   göstermezdi. Takip başı ölçütleri de (yörünge dönüşü, PX4'ün rota varsayımı, 9.8 ön işinin sahte hızı) zaten bu
   aralığa bakıyor. ffprobe süresi `ozet.json` → `olcutler.kayit_suresi_s` (hakemin ilk–son satırı) ile karşılaştırılır.
   Spec 9. madde ve Test Planı 5. koşul buna göre güncellendi.
2. **Koşu sırasında yalnız kare yazılır, video koşudan sonra ve yalnız dosyalardan yapılır.** Böylece video koşunun
   zamanlamasına girmez (kare kaydının bedeli aşağıda ölçüldü), her takip kaynağı (stok Follow Me, `tez_los` + m15'in
   modu) aynı videoyu aynı yoldan alır ve saklanan karelerle (`--kareleri-sakla`) aynı video `video.py <klasör>` ile
   yeniden yapılabilir (ör. video kodu değişince). `rapor.write`'a bir kanca eklendi: video `ozet.json` ve CSV'ler
   yazıldıktan sonra yapılır, sonucu `ozet.json` → `video`'ya ve raporun başındaki satıra girer.
3. **Kaydedici ayrı bir süreç ve simin önüne geçmez.** Model süreci gibi "spawn" ile ve simden önce açılır (gz-transport
   ve JPEG işi ana süreçten uzak). OpenCV varsayılanda her küçültmeyi bütün çekirdeklere (16) yayıyordu; ölçünce tek
   adımlı kutu süzgeci (2304×1296 → 1280×720) tek çekirdekte 16 ms sürüyordu. Kaydedici OpenCV'yi tek iş parçacığında
   çalıştırır, küçültmeyi iki adımda yapar (tam yarıya kutu süzgeci: OpenCV'nin hızlı tam sayı yolu, örtüşme yok;
   sonra 1280×720'ye çift doğrusal): 3.4 ms. Süreç `nice 5` ile çalışır: işlemci dar gelirse kare düşen kaydedici olur,
   yavaşlayan sim değil. Düşen kare sayılır ve videoda o 1/15 s için önceki kare gösterilir.
4. **Kare seçimi: her 1/15 s'lik ızgara anına en çok 20 ms uzaklıktaki kare.** Kamera kareleri 4 ms'lik fizik adımı
   yüzünden 32 / 36 ms arayla geliyor. "Her dilimin ilk karesi" kuralı 100 / 32 / 68 ms'lik düzensiz aralıklar verirdi;
   ızgaraya en yakın kare kuralı tam olarak her ikinci kareyi seçer (testli). Kaybolan bir karenin yeri boş kalır,
   sonraki kareler kaymaz.
5. **"PX4'ün elindeki model sonucu" gönderim anına göre.** Sol panelde kırmızı kutular, o anda PX4'e gitmiş en yeni
   sonuçtur (gönderim anı; reddedilmişse gecikme hattından çıkışı; hakem kaynağında model sonucu PX4'e gitmez, hazır
   olduğu an). Bu kutu birkaç kare eskidir: kişinin gerisinde kalması gecikmeyi gözle gösterir.
6. **Kuşbakışında ölçek video boyunca sabit, merkez yumuşak izler.** Ölçek dron ile kişiyi sığdıracak kadardır (mesafenin
   p98'inin yarısı + 7 m, 11–26 m arası); merkez ikisinin ortasını 1.5 s'lik zaman sabitiyle izler. Değişen bir ölçek
   halkaları ve mesafeyi gözle karşılaştırmayı zorlaştırırdı.
7. **Yazılar PIL ve matplotlib'in DejaVu Sans'ıyla, şekiller OpenCV ile.** OpenCV'nin yazı tipleri Türkçe harfleri
   (ı, ş, ğ) çizemiyor; yazı tipi sabit sürümlü matplotlib'in içinden alınıyor, sistem yazı tipine bağlı değil.
   Şekiller kenar yumuşatmalı (`LINE_AA`, 1/16 piksel).
8. **Durum satırının renkleri.** Kırmızı: kilit kaybı / kilit yok, PX4'e "hedef yok" gidiyor, dron 3 m ya da kameranın
   yakın görüş sınırı içinde, kişi kadraj dışında, PX4 kestirimi bayat (kullanıcının istediği). Turuncu: dron kişinin
   yanında/önünde (köşede aşma), model bu karede kişiyi bulamadı. Yoksa PX4'ün kişinin hızı kestirimi ve rotası; bu
   satır İş B'nin anlattığı mekanizmayı videoda doğrudan gösterir ("hedefin hızı 1.3 m/s (≥ 1 m/s: rota güncellenir)"
   yazarken kişi duruyor).
9. **Video yapılamazsa koşu kalmaz.** Hata `ozet.json` → `video.hata` ve olaylara yazılır; ölçütler etkilenmez.
10. **`onizleme.py` MP4'e geçti.** Aynı `video.Encoder` ve aynı hakem kutusu çizimi (`video.draw_referee`); yarım
    çözünürlük, 10 kare/s.

### Test sonuçları ve doğrulama (8.6)

| Kontrol | Sonuç |
|---|---|
| `$P -m pytest tez/sim/testler/test_video.py tez/sim/testler/test_goruntu_yayini.py -q` | **13 geçti** (10 + 3) |
| `$P -m pytest tez/sim/testler -q` | **225 geçti** (7. grupta 211; A: +13, B: +1), 1 uyarı (önceden de vardı, protobuf). `torch`/`ultralytics`, ffmpeg, Gazebo gerekmez |
| `ruff format` + `ruff check` (`tez/sim/ruff.toml`, ruff 0.16.9) | temiz |
| `tez/pin/verify_pin.sh --worktree` | **KILIT SAGLAM (v1.17.0)** |
| `senaryo.py --senaryo takip_yuruyen --ekransiz --kareleri-sakla` (`sonuclar/gorev8_takip_yuruyen`) | GEÇTİ; `ffprobe`: **h264, yuv420p, 2000×720**, süre **65.87 s** (hakemin kaydı `kayit_suresi_s` 65.84 s, fark 0.03 s); 988 kare, kamera karesi olmayan an 0, kaydedici 0 kare düşürdü; video 26 s'de birleşti. Saklanan karelerle `video.py tez/sim/sonuclar/gorev8_takip_yuruyen` son kodla yeniden yaptı (28 s, aynı süre) |
| `senaryo.py --senaryo kalabalik_park --ekransiz` (`sonuclar/gorev8_kalabalik_park`) | GEÇTİ; h264, yuv420p, 2000×720, **63.67 s** (kayıt 63.66 s); 955 kare, eksik 0, düşen 0; 32 s'de birleşti, `kareler/` silindi |
| `toplu.py --senaryo takip_yuruyen --tekrar 3` (`sonuclar/gorev9on_RS0.1_model_x3`, İş B'nin varsayılan grubu) | 3/3 GEÇTİ; her koşunun `kosu.mp4`'ü h264 / yuv420p / 2000×720, süreler 65.73 / 64.73 / 65.13 s (kayıt 65.77 / 64.71 / 65.11 s); `kareler/` silindi; `toplu.html` üçünü de bağlıyor. Bu oturumun videolu 32 koşusunun hiçbirinde eksik ya da düşen kare yok; video süresi ile kayıt süresi arasındaki fark en çok 0.06 s |
| VLC 3.0.20 (`cvlc --intf dummy --play-and-exit --run-time 4`) | açtı, oynattı, temiz çıktı (uçbirimdeki VDPAU ve "Timestamp conversion failed" satırları VLC'nin kendisinden) |
| `tez/sim/araclar/f0_kabul.sh` | **GEÇTİ** (1 dk 9 s) |
| `tez/sim/araclar/f1_kabul.sh` (`--modelsiz`, `yok`; F1 artık video da üretiyor) | **GEÇTİ**: hedef doğrulama farkı en çok 0.13 / 0.13 m (sınır 0.30), iki koşu arası 0.000 m; videolar 952 kare, eksik 0 |

Her koşudan önce `pgrep -x px4` / `pgrep -f "^gz sim"` boştu; sonunda açık PX4, Gazebo, kaydedici, ffmpeg ya da yardımcı
süreç kalmadı.

### Kare kaydının RTF'e etkisi (ölçüm)

`takip_yuruyen`, model v0.2, 4 çekirdek, aynı kod; videolu ve `--videosuz` koşular **sırayla dönüşümlü** ve ben hiçbir
şey çalıştırmazken (`sonuclar/gorev8_rtf_{video,videosuz}_{1,2,3}`):

| | koşu 1 | koşu 2 | koşu 3 | ort. |
|---|---|---|---|---|
| RTF, videolu (kare kaydı açık) | 0.790 | 0.781 | 0.792 | **0.788** |
| RTF, `--videosuz` | 0.831 | 0.849 | 0.829 | **0.836** |
| `model_ms` ort., videolu / videosuz | 106.8 / 101.8 | 106.6 / 99.7 | 107.9 / 95.6 | **107.1 / 99.0** |
| İşlenen kare [1/sim-s], videolu / videosuz | 11.6 / 11.6 | 11.8 / 11.6 | 11.5 / 12.4 | 11.6 / 11.9 |

- **Kare kaydı RTF'i ≈ 0.05 düşürüyor (%6), modelin kare süresini ≈ %8 uzatıyor.** Fark küçük ama tutarlı: üç videolu
  koşunun üçü de üç videosuz koşunun altında. Kaydedici hiç kare düşürmedi; kare başına çözme + küçültme + JPEG + yazma
  ort. 9.2–9.5 ms (tek çekirdek, `nice 5`).
- **Kaynağı ayrılamadı:** kameraya bütün 9 MB'lık kareleri alan ama işlemeyen pasif bir abone (scratchpad) ile 2
  videosuz koşu 0.783 ve 0.872 verdi; bu oturumdaki videosuz koşuların kendi yayılımı (0.78–0.91) kadar. Yani payın ne
  kadarının üçüncü bir aboneliğin (Gazebo'nun kareyi bir sürece daha göndermesi, Python'a 30 Hz × 9 MB kopya) ne
  kadarının JPEG işinin olduğu 2 koşuyla söylenemiyor.
- Bağlam: bugün model genel olarak yavaştı (kare başına ≈ 100 ms; 7. grupta 82–86 ms) ve RTF videosuz da 0.83 civarındaydı
  (7. grupta 0.97). Sim zamanıyla ölçülen her şey RTF'den bağımsızdır; RTF düşünce model sim saatine göre biraz hızlı
  görünür.
- **Ne yapılabilir (karar bekliyor, bu grupta uygulanmadı):** (1) RTF'in önemli olduğu ölçüm koşularında `--videosuz`
  (bedel 0); (2) kare kaydını model sürecinin zaten aldığı karelerden yapmak (aynı abonelik; ama spec ayrı bir yayın
  süreci öngörüyor ve 11. grubun QGC yayını da o süreçte olacak); (3) 3'ten fazla koşuyla payı abonelik / işleme diye
  ayırmak.

### Karşılaşılan sorunlar

- **İlk koşunun RTF'i 0.83 çıktı (7. grupta model koşuları 0.97).** Sebebi videoyu sandım ve önce kaydedicinin bedelini
  ölçtüm: OpenCV kaydedici süreçte varsayılanda 16 iş parçacığı kullanıyordu ve tek adımlı kutu süzgeci tek çekirdekte
  16 ms sürüyordu; kaydedici tek iş parçacığına, iki adımlı küçültmeye (3.4 ms) ve `nice 5`'e alındı (karar 3). Ama
  aynı oturumdaki videosuz koşular da 0.82–0.91 verdi: bugün model daha yavaştı (kare başına ort. 100 ms; 7. grupta
  82–86 ms). Asıl ölçüm yukarıdaki dönüşümlü 3 + 3 koşudur: kaydın payı ≈ 0.05.
- **Benim işlerim ölçümü kirletti:** OpenCV hız ölçümlerini bir videosuz koşu sırasında yaptım (RTF 0.79, ölçüme
  girmedi); bir videolu grubun iki koşusu sırasında da Python ile ULog okudum (0.74, 0.82; boştayken 0.90). RTF
  karşılaştırması bu yüzden ayrı bir dönüşümlü dizide, ben boştayken tekrarlandı.
- **Ad gölgelemesi (koşmadan yakalandı):** `senaryo.run` içinde kaydedicinin defterine `frame_books` adını verdim; aynı
  adlı modül fonksiyonunu (model sürecinin kare defteri) gölgeleyecekti. Koşudan önce fark edilip `video_books` yapıldı.
- **Kendi testimde kuyruk boyu:** `FrameSink` testinde bütün kareler aynı anda verildiği için 6'lık kuyruk iki kare
  düşürdü (gerçekte kareler 33 ms arayla gelir). Test, ilk kısımda kuyruğu 16 yapacak şekilde düzeltildi; düşürme ayrı
  bir kısımda, takılı bir yazıcıyla sınanıyor.
- **`dunya` modülü `ruff.toml`'un `known-first-party` listesinde yok** (önceden de yoktu; `rapor.py` de onu üçüncü taraf
  gibi sıralıyor). `video.py` de ruff'ın sıralamasına uyuyor; listeye eklemek başka dosyaların sıralamasını da
  değiştireceği için bu grupta yapılmadı.

### Kalan sim-gerçek farkları (video için)

- **Video bir değerlendirme aracıdır, Pi'nin gördüğü görüntü değildir.** Sol panel Gazebo kamerasının kendi karesidir
  (1280×720'ye küçültülüp JPEG kalite 90 ile saklanır); gerçek Camera Module 3'ün gürültüsü, bulanıklığı, rolling
  shutter'ı, pozlaması yok (Faz B, `kusurlar.py`). Gazebo gölgeleri var, gerçek güneşin yönü ve sertliği farklı olur.
- **Hakem kusursuzdur:** mavi kutu, kuşbakışındaki kişi, dronun yeri ve "olması gereken yer" Gazebo'nun gerçek
  konumlarıdır. Gerçek uçuşta bunların yerini RTK GPS'li bir hedef ya da yer kamerası tutmalı (m17/m25); uçuş videosunda
  yalnız Pi'nin kendi kutusu ve telemetri olur.
- **PX4'ün iç durumu ULog'dan gelir:** gerçek araçta da `follow_target*` konuları ancak kaydedici bunları alırsa
  görünür (spec "Açık Konular": gerçek araçta `follow_target*` kaydı). Simde kaydedici yeniden başlatıldığı için ilk
  ≈ 3 s'de (mod seçimi → kaydedicinin yeniden başlaması) mor işaretler yoktur.
- **Kuşbakışındaki kameranın izdüşümü düz zemin içindir** (`z = 0`); eğimli arazide (kampüs, %3–7) gerçekte kayar.
- **Video sim zamanındadır:** RTF < 1 iken koşu duvar saatinde daha uzun sürer, video yine sim saniyesiyle oynar (15
  kare/sim-s). Gerçek uçuş videosu duvar saatindedir.
- QGC'ye canlı görüntü henüz yok (11. grup); kayıt ve canlı yayın aynı süreçte birleşecek.

### Açık kararlar ve bekleyenler

- **Video penceresi:** spec "kayıt penceresi" diyordu; video hakemin kaydını (takip başı + kayıt penceresi) kapsıyor
  (karar 1). **Karar (13.11, kullanıcı; 9. grupta spec'e yazıldı):** böyle kalır, takip moduna geçişten koşu sonuna.
- **Kare kaydının RTF payı (≈ 0.05):** azaltmak istenirse seçenekler yukarıda ("Ne yapılabilir"). **Karar (13.11,
  kullanıcı):** 11. grupta QGC yayınıyla birlikte ele alınır (`tasks.md` 11.6); o zamana kadar RTF'in önemli olduğu
  ölçümlerde `--videosuz`.
- **`dunya` modülünün `ruff.toml`'daki yeri** (önceden de eksikti; ayrı küçük bir iş).

### Commit ayrımı (A ve B aynı dosyalara dokundu)

A'nın dosyaları yalnız A'nındır: `tez/sim/araclar/video.py`, `goruntu_yayini.py`, `senaryo.py`, `hedef.py`,
`onizleme.py`, `tez/sim/testler/test_video.py`, `test_goruntu_yayini.py`, `test_hedef.py`, `test_toplu.py`,
`tez/sim/ruff.toml`, `tez/env/VERSIONS.md`, bu dosya. B'nin yalnız: `tez/sim/araclar/olcum.py`,
`tez/sim/testler/test_olcum.py`, `implementation/gorev-grubu-09-on-followme-ayar.md`. Ortak dosyalar:

| Dosya | A'nın kısmı | B'nin kısmı |
|---|---|---|
| `tez/sim/araclar/rapor.py` | `write`'ın `video` kancası, raporun başındaki video satırı, `Callable` içe aktarması | `PERCENT_KEYS`'teki `px4_kestirim_hizi_baslangic_1mps_orani`, "Takip başı: hedef dururken konum titreşimi ve PX4'ün sahte hızı" ölçüt grubu |
| `tez/sim/araclar/toplu.py` | `VIDEO` sabiti, `toplu.html`'deki `kosu.mp4` bağlantısı, belge metni | `MAIN_KEYS`'e eklenen 5 anahtar |
| `tez/sim/README.md` | durum, ara durum, çıktılar tablosu (`kosu.mp4`, `rapor.html`), "Video (`kosu.mp4`)" bölümü, önizleme, dosyalar | "Ölçütler" tablosundaki sahte hız satırı ve stok Follow Me ayarları paragrafı |
| `spec.md` | 9. madde (pencere, kaydedici, çevrimdışı birleştirme, kuşbakışı), ara durum satırı, Dosya Planı, alan tablosu, Test Planı, sürüm TBD'si | "Ölçüt Tanımları"nın girişi ve 2 yeni satırı, "PX4 stok Follow Target davranışı"nın 9.8 paragrafı, "Açık Konular"daki 9.8 maddesi |
| `tasks.md` | 8.0–8.6 | 9.8 |
| `implementation/kabul-kosulari.md` | "8" satırları | "8 + 9.8 (ön)" ve "9.8 (ön)" satırları |

A'nın tam hâli yama olarak: `~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev8_is_A.patch` (HEAD `33d8ec8842`'ye karşı;
`git apply --cached` ile önce A commit'lenir, kalan değişiklikler B'dir). Yama, HEAD'in paylaşımlı bir klonunda
(kullanıcının reposuna ve index'ine dokunmadan) uygulanıp denendi: **224 test geçti** (7. grubun 211'i + A'nın 13'ü; ortak dosyalarda B'nin kısımları geri alınmış hâlde), ruff temiz; klona yalnız git'e girmeyen insan modeli (`kur.sh`'ın indirdiği `models/insan/meshes`) bağlandı.

### Görseller (repo dışı)

`~/Desktop/Follow/3_m06_Simulasyon/Deneme/`:

| Dosya | Ne |
|---|---|
| `gorev8_takip_yuruyen_kosu.mp4` | `takip_yuruyen`'in `kosu.mp4`'ü (`sonuclar/gorev8_takip_yuruyen`, model, stok Follow Me, 65.9 s; kareler saklandığı için son video koduyla `video.py` ile yeniden yapıldı) |
| `gorev8_kalabalik_park_kosu.mp4` | `kalabalik_park`'ın `kosu.mp4`'ü (`sonuclar/gorev8_kalabalik_park`, `yok`: dron Hold'da, beş kişi, 63.7 s) |
| `gorev8_takip_yuruyen_kare.png` | 36.2 s: kişi duruyor, PX4 "hedefin hızı 1.2 m/s (≥ 1 m/s: rota güncellenir)" diyor, dron kişinin etrafında dönüyor; PX4'teki model kutusu (kırmızı, 164 ms eski) hakem kutusunun (mavi) gerisinde |
| `gorev8_kalabalik_park_kare.png` | 66.0 s: hedef (mavi) ve dört kişi (turuncu), modelin seçtiği kutu (kalın kırmızı), çam ağacı; sağda ağaç taçları ve kişilerin izleri |
| `gorev8_is_A.patch` | İş A'nın yaması (commit ayrımı için) |

---


## Kendin dene

Bu bölümdeki her şey bilgisayarında hazır: paketler kurulu, model dosyası yerinde, PX4 derli.

**Başlamadan:** Terminal açmak için **Ctrl+Alt+T**'ye bas. Aşağıdaki gri kutulardaki satırları **tek tek** kopyala,
terminale **Ctrl+Shift+V** ile yapıştır (terminalde Ctrl+V çalışmaz) ve **Enter**'a bas. Her satır tek başına
çalışır (değişken yok; yeni bir terminalde de olur). Bir komutu yarıda kesmek için **Ctrl+C**.

### 1. Videoyu izle

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev8_takip_yuruyen_kosu.mp4 2>/dev/null
```

Solda dronun kamerası, sağda kuşbakışı harita (kuzey yukarı). Bak:

- **Sol üst:** sim zamanı, PX4 modu ("Follow Target"), uçtan uca gecikme; altında "PX4'teki son model sonucu: … ms
  önceki kare". **Mavi kutu** hakemin (doğru cevap) kutusu, **kalın kırmızı kutu** modelin PX4'e giden kutusu ve
  güveni. Kişi yürürken kırmızı kutu mavinin biraz gerisinde kalır: modelin gecikmesi gözle görünür.
- Model kişiyi bulamayınca kırmızı kutu kaybolur, sol üstte "bu karede hedef bulunamadı", 10 karede bir **kilit kaybı**
  olur ve büyük kırmızı **HEDEF YOK** çıkar.
- **Sağda:** mavi nokta kişi (ok: yürüdüğü yön), turuncu üçgen dron (sivri ucu burnu), çizgiler son 10 s. Açık mavi
  alan kameranın yerde gördüğü yer. Kişinin çevresinde **kırmızı kesikli halka 3 m**, **gri kesikli halka** kameranın
  yakın görüş sınırı (dron bunun içine girerse kişinin ayakları kadrajdan çıkar). **Yeşil yıldız** dronun olması
  gereken yer (yürüyen kişinin 8 m arkası). **Mor noktalar** son 3 s'de PX4'e gönderilen kişi konumları: kişi
  dururken bile bir yerde durmazlar. **Mor kare** PX4'ün "kişi burada" dediği yer, **mor ok** PX4'ün kişinin gittiğini
  sandığı yön, **mor halka** PX4'ün dronu şu an gönderdiği yer, **mor ×** hedeflediği yer.
- **Altta durum satırı:** kişi duruyor mu yürüyor mu, dron–kişi mesafesi; kırmızı satır bir sorun (kilit kaybı, hedef
  yok, dron çok yakın, kişi kadraj dışında). Kişi dururken bile "PX4: hedefin hızı 1.3 m/s (≥ 1 m/s: rota güncellenir)"
  yazdığı anlara bak: mor ok döner, dron kişinin etrafında döner. Salınımın sebebi bu (İş B).

VLC kısayolları: **Boşluk** duraklat/sürdür, **E** bir kare ileri, **Shift+→ / Shift+←** 3 s ileri/geri, **[** / **]**
yavaşlat/hızlandır, **F** tam ekran. Uçbirime düşen "Timestamp conversion failed" satırları VLC'nin kendisinden gelir.

Kalabalık park (dron 10 m'de Hold'da bekler, beş kişi, ağaçlar):

```bash
vlc ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev8_kalabalik_park_kosu.mp4 2>/dev/null
```

Bak: turuncu kutular diğer insanlar; kırmızı kalın kutu başka birine atlarsa (yanlış kişi) haritada da görünür; kişi
çamın arkasına girince mavi kutu küçülür ya da kaybolur, harita kişiyi göstermeye devam eder.

Videolardan birer kare:

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev8_takip_yuruyen_kare.png
```

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev8_kalabalik_park_kare.png
```

### 2. Kendin koştur (pencere yok, ~3 dakika)

Önce açık bir sim olmadığından emin ol (iki satır da bir şey yazmamalı):

```bash
pgrep -x px4
```

```bash
pgrep -f "^gz sim"
```

Tek koşu; sonunda video birleşir (yarım dakika kadar):

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz
```

Sona doğru "Video kareleri: … yazıldı (… düştü)" ve "Video: …/kosu.mp4 (… kare, … s)" satırları çıkar; en son satır
"SONUÇ: GEÇTİ". Klasörün adı "Rapor:" satırında yazar (ör. `tez/sim/sonuclar/20261113_041500_takip_yuruyen`). En son
koşunun videosunu açmak için:

```bash
vlc "$(ls -td ~/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/*_takip_yuruyen | head -1)/kosu.mp4" 2>/dev/null
```

Raporun en üstünde videonun satırı var:

```bash
firefox "$(ls -td ~/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/*_takip_yuruyen | head -1)/rapor.html"
```

Videonun kontrolü (beklenen: `h264,2000,720,yuv420p` ve 60–70 arası bir süre):

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,pix_fmt -of csv=p=0 "$(ls -td ~/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/*_takip_yuruyen | head -1)/kosu.mp4"
```

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 "$(ls -td ~/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/*_takip_yuruyen | head -1)/kosu.mp4"
```

Kareleri saklayıp videoyu yeniden yapmak (ör. video kodu değişince): koşuya `--kareleri-sakla` ekle, sonra

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/video.py tez/sim/sonuclar/gorev8_takip_yuruyen
```

Üç koşu ve hepsinin videosu (`toplu.html` her koşunun `kosu.mp4`'ünü bağlar; ~8 dakika):

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot && ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/toplu.py --senaryo takip_yuruyen --tekrar 3
```

```bash
firefox ~/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev9on_RS0.1_model_x3/toplu.html
```

### 3. Kontroller

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

Beklenen: `225 passed`; `KILIT SAGLAM (v1.17.0)`; F0 (~1 dakika) ve F1 (~5 dakika) sonunda `SONUÇ: GEÇTİ`.

### Bir şey ters giderse

| Mesaj | Ne yapmalı |
|---|---|
| `Zaten çalışan bir PX4 veya Gazebo var` | Açık simi kendi terminalinde Ctrl+C ile kapat ya da bitmesini bekle |
| Raporda "Video yapılamadı: …" | Koşunun sonucu etkilenmez; `sim.log` ve koşunun günlüğüne bak. Kareler saklandıysa `video.py <klasör>` ile yeniden dene |
| "Video kareleri: … N düştü" | İşlemci dar geldi; videoda o anlarda önceki kare görünür (sol üstte "bu an için kamera karesi yok") |
| VLC açılmıyor | `ffprobe` satırını çalıştır; `h264,2000,720,yuv420p` görüyorsan dosya sağlamdır |
