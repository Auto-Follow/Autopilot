# Görev Grubu 11 — QGC'ye canlı video (H.264 RTP, UDP 5600) ve kayıt + yayının RTF payı

- Tarih: 14.11.2026 · dal `ozellik/m06-sim-ortami` · taban commit `ec23a1599b` + çalışma ağacı
- Kapsam: `tasks.md` 11.0–11.7 (11.6: kullanıcının 13.11 kararı, `gorev-grubu-08.md` "Ne yapılabilir")
- Durum: **uygulandı, test edildi, koşuldu**; commit'i ana oturum atar. QGC'deki görsel kontrol Ahmet'te: QGC bu grupta
  açılmadı, yayın bir GStreamer alıcısıyla, `gst-launch-1.0` ile ve ffmpeg + `yayin.sdp` ile ölçülerek doğrulandı.

## Kısaca

- `senaryo.py --qgc` (senaryoda `video: {qgc: true}`) dron kamerasını **kutular çizili** olarak QGroundControl'e
  canlı gönderir: H.264 RTP, `udp://127.0.0.1:5600`, 1280×720, 15 kare/sim-s, simin başından sonuna. QGC 5.1.4:
  Uygulama Ayarları → Video → "UDP h.264 Video Stream", port 5600.
- Kutular: işlenen her model karesinin kutuları (kırmızı, seçilen kalın + güveni) ve **o karenin** hakem kutusu (mavi),
  "HEDEF YOK"; ana süreç bunları `127.0.0.1:5610`'a tek JSON datagramıyla gönderir (iki taraflı doğrulama).
- Tek başına mod (açık sim + QGC ile elle uçuş): `goruntu_yayini.py --qgc --model <dosya.pt>`; kendi model kutuları,
  hakem ve LOS yok; açık bir simde denendi (659 / 659 kare, 616'sında kutu).
- **Doğrulama koşusu** (`takip_yuruyen --ekransiz --qgc --cikti tez/sim/sonuclar/g11_qgc`, son kod): GEÇTİ; yayın
  **1583 kare gönderildi = alıcı 1583 kare aldı** (kayıp 0, 500 ms'den uzun boşluk 0), 15.0 kare/sim-s = 13.3 kare/s
  (RTF 0.86), kutu mesajı 948 gönderildi / 948 alındı, kutulu kare 1353 (kutusuzlar: modelin kapandığı inişteki
  ≈ 15 s); kaydedici 1343 kareyi model sürecinden aldı (0 ezildi); `kosu.mp4` h264 / yuv420p / 2000×720, 63.8 s.
- **11.6 (RTF payı):** ölçüm, kaydın payının çoğunun JPEG değil, kameraya **ikinci 9 MB × 30 Hz abonelik** olduğunu
  gösterdi (pasif bir abone tek başına ≈ 0.06). Kaydedici artık kareleri model sürecinin zaten aldığı mesajlardan
  paylaşılan bellekle alıyor, kareyi kopyasız okuyup tamponlara küçültüyor; yayının yazıları kendi kutularında
  çiziliyor, x264 tek iş parçacığında. Sonuç: video + `--qgc`'nin RTF payı **−0.114'ten +0.001 ± 0.027'ye**, yalnız
  videonun **−0.084'ten −0.027 ± 0.067'ye** (bir yavaş koşu; onsuz +0.002); kaydedici + yayın süreci 0.48 → 0.30
  çekirdek. Ölçümlerin gürültüsü içinde kayıt ve yayının payı kalmadı. **Kullanıcıya soru:** `--videosuz` kuralı
  kalksın mı (bölüm 9)?
- **VLC bu yayını açamıyor:** sabit sürümlü VLC 3.0.20-3build6 Ubuntu'da live555'siz derlenmiş (SDP'den RTP yok).
  QGC'siz izlemek için ffmpeg paketinin `ffplay`'i (`yayin.sdp` ile) ya da `gst-launch-1.0`; ikisi de denendi.
- 295 birim testi geçti (289 + 6), ruff temiz, **KILIT SAGLAM**, **F0 GEÇTİ** (stok derleme).

## 1. Ne yapıldı

| Alt görev | Dosya | Sonuç |
|---|---|---|
| 11.1 | `tez/sim/testler/test_goruntu_yayini.py` (+5 test), `test_video.py` (+1), `test_hedef.py` (güncellendi) | Bölüm 4 |
| 11.2 | `tez/env/VERSIONS.md` | GStreamer 1.24.2 paketleri, `python3-gi` 3.48.2-1, `libfuse2t64` 2.9.9-8.1build1 (`dpkg-query -W` ile okundu, kullanılmadan önce yazıldı); kurulum ve kontrol komutları ("Canlı video paketleri"); VLC satırına "canlı yayını açamaz" notu |
| 11.3 | `tez/sim/araclar/goruntu_yayini.py` | `pipeline_description`, `LiveStream` (appsrc → leaky queue → videoconvert → x264enc → rtph264pay → udpsink; defter: verilen, kutulu, kuyruk taşması, hız, gecikme), `gst()`; deney dalındaki sabit `x500_mono_cam_0` yok, konu `goruntu.CAMERA_TOPIC` |
| 11.4 | `goruntu_yayini.py`, `takip.py`, `video.py` | `BoxMessage` + `pack` / `unpack` / `check`, `BoxSender` (ana süreç), `BoxListener` (yayın süreci), `takip.Tracker(overlay=...)`; `video.draw_live` (kamera panelinin renkleri ve yardımcıları: `draw_model_boxes`, `draw_legend`); tek başına mod `main()` (`--qgc --model`), `standalone_message` |
| 11.5 | `tez/sim/araclar/yayin.sdp`, `senaryo.py`, `hedef.py` | SDP (H.264/90000, pt 96, port 5600); `--qgc` / `video.qgc` bağlandı (kayıtla aynı süreç; `--videosuz --qgc` yalnız yayın); 2. grubun `--qgc` ara hatası kaldırıldı; `ozet.json` → `yayin`; kaydedici/yayın açılamazsa "Video kaydı / canlı yayın açılamadı, simülasyon açılmadı" (çıkış 2) |
| 11.6 | `goruntu_yayini.py`, `goruntu.py`, `algilama.py`, `senaryo.py`, `video.py` | Bölüm 5: üç dönüşümlü seri (40 koşu); kare paylaşımı (`FrameShare` / `FrameTap` / `ShareReader`, `goruntu.FrameReader(also=...)`, `algilama.ModelProcess(tap=...)`), kopyasız okuma (`frame_pixels`), tamponlu küçültme (`Scaler`), etiketlerin kendi kutusunda çizimi (`video.render_labels`), `x264enc threads=1` |
| 11.7 | koşular | Bölüm 6 |
| belgeler | `spec.md`, `tasks.md`, `EKIP_ICIN_OZET.md`, `tez/sim/README.md`, `implementation/kabul-kosulari.md`, bu dosya | spec 4., 8., 9., 10. madde, alan tablosu, dosya planı, test planı, açık konular, "Saatler"; README "Canlı video (QGC)" |

## 2. Kararlar ve gerekçeler

1. **Kayıt ve yayın tek süreçte, tek işçide** (spec "Süreçler"). Izgaradaki (15 kare/sim-s) her kare bir kez okunur
   ve küçültülür; yayın kutular çizilmiş bir kopyasını alır, kayıt (pencerede) temizini JPEG yazar. Yayın simin
   başından sonuna gider (kalkış, iniş dahil: QGC'de uçuşun tamamı görünür); kayıt yalnız hakemin kayıt penceresinde.
2. **Yayın sızdırır, kayıt sızdırmaz.** Yalnız yayına giden bir kare başka bir karenin arkasında kuyruğa girmez;
   arkasında daha yeni bir kare bekleyen kare yayınlanmaz (yayın hep en yeniyi gösterir, gecikme birikmez); kodlayıcının
   önündeki `queue leaky=downstream max-size-buffers=2` da eski kareyi atar. Kayıt penceredeki her kareyi tutar (8.
   grubun 6 karelik kuyruğu).
3. **Kutular "o karenin" kutularıdır** (spec): model sonucu + aynı karenin hakem kutusu. Gösterilen kare daha yenidir
   (model ≈ 0.1 s sürer), kutular kişinin biraz gerisinde kalır; `kosu.mp4`'teki gibi gecikmeyi gözle gösterir. Üstte
   "model: … ms önceki kare". 1 s'den eski kutu çizilmez (model sustu: "kutu bilgisi eski"). "HEDEF YOK", o karenin
   `TEZ_LOS`'u "hedef yok" ise (model kaynağında seçili kutu yok, hakem kaynağında hedef görünmüyor).
4. **Kutu mesajı küçük ve doğrulanmış:** `{"v": 1, "t", "kutular": [[u0, v0, u1, v1, güven]…], "secilen", "secim",
   "hedef_yok", "hakem"}` (tam çözünürlükte piksel kenarları, 0.1 px'e yuvarlanmış). Gönderen ve alan aynı `check`'ten
   geçirir; geçersiz mesaj gönderilmez / çizilmez ve sayılır. Gönderim bloklamaz (takip iş parçacığı beklemez).
5. **Modelsiz koşu:** LOS hakemdense her hakem karesi kutusuz bir mesaj olur (yayında mavi kutu ve "HEDEF YOK"); model
   ve LOS yoksa yayında kutu yoktur ("kutu bilgisi yok").
6. **Tek başına mod MAVLink'siz:** `goruntu_yayini.py --qgc [--model]` kendi `algilama.ModelProcess`'ini açar; yalnız
   model kutuları çizilir (seçim yok, hakem yok). Süreç `pymavlink` / `px4_baglanti` içe aktarmaz (testli); LOS
   gönderemez. `--qgc` olmadan bir şey açmaz (çıkış 2): tek başına çalışmada bu aracın tek işi yayın.
7. **Hatta spec'e eklenenler:** `x264enc threads=1` (bölüm 5.3), `appsrc do-timestamp=true` (kare zamanı itildiği an:
   yayın duvar saatinde akar), `queue max-size-bytes=0 max-size-time=0` (yalnız 2 kare sınırı), `udpsink async=false`.
8. **Kareler model sürecinden** (11.6; bölüm 5): model açıkken kaydedici kameraya abone olmaz; model sürecinin kare
   okuyucusu ızgaradaki her mesajı 8 yuvalı bir paylaşılan bellek halkasına kopyalar (≈ 0.7 ms) ve kuyrukla bildirir;
   kaydedici kareyi halkadan kopyasız okur, küçültür, sonra yuvanın hâlâ o kareyi tuttuğunu denetler (seqlock: üzerine
   yazılan kare atılır ve sayılır, yırtık kare hiç kullanılmaz). Model yokken (`--modelsiz`), yuvaya sığmayan bir
   karede ve model kayıt bitince kapandıktan sonra (inişteki yayın) kaydedici kendi aboneliğine geçer. Kayıt ve yayın
   yine ayrı süreçtedir; model süreci yalnız bir kopya ve bir kuyruk mesajı ekler.
9. **VLC yerine ffplay:** sabit VLC'nin Ubuntu paketi live555'siz (bölüm 6.3). `yayin.sdp` aynen kalır (spec), ffplay
   onu açar; ffplay, zaten sabit olan ffmpeg 7:6.1.1-3ubuntu5 paketinin parçası (yeni paket yok). `senaryo.py` ve tek
   başına mod günlükte ffplay komutunu yazar.
10. **GStreamer'dan önce her şey yüklenir:** bir ölçüm betiğinde GStreamer iş parçacıkları çalışırken matplotlib'in ilk
    kez içe aktarılması süreci çökertti (segmentation fault, `faulthandler` ile görüldü; repo kodunda olmadı).
    `LiveStream` `video`'yu içe aktarır ve bir kez çizer, ancak sonra hattı başlatır.

## 3. Ölçülen yayın

| Ne | Değer | Nereden |
|---|---|---|
| Alınan / gönderilen kare | 1583 / 1583 (kayıp 0); tek başına modda 659 / 659 | alıcı (`alici.py`, scratchpad) ve `ozet.json` → `yayin.verilen` |
| Kare hızı | 15.0 kare/sim-s; duvar saatinde 13.3 kare/s (RTF 0.86), RTF 1'e yakınken 14.3–14.8 (3. seri) ve 15.0 (tek başına) | `yayin.hiz_sim_hz`, `hiz_duvar_hz`; alıcının aralığı p50 74 ms, p95 97 ms, en çok 290 ms, 500 ms'den uzun boşluk 0 |
| Kutulu kare | 1353 / 1583; kutusuzlar modelin kapandığı inişteki ≈ 15 s ("kutu bilgisi eski") | `yayin.kutulu` |
| Kutu mesajı | 948 gönderildi / 948 alındı, 0 geçersiz | `yayin.kutu_gonderimi`, `yayin.kutu_mesaji` |
| Kareyi alma → yayına itme | p50 12.9 ms, p95 17.5 ms (paylaşılan bellek dahil; 3. seride p50 11.3–11.8, p95 14.2–14.7) | `yayin.gecikme_ms_*` |
| İtme → alıcıda çözülmüş kare | p50 8.4 ms, p95 9.4 ms (x264 tek iş parçacığı + RTP + `avdec_h264`, aynı makine; çok iş parçacıklı x264'le 7.0 / 7.7 ms) | bench (`hat_gecikmesi.py`, scratchpad, 300 kare) |
| Kamera → kaydedici | ≈ 33 ms (`ulasma_ms`, model süreci; kareyi model süreci alıyor) | `ozet.json` |
| Yakalama → alıcıdaki kare (tahmin) | ≈ 33 + 13 + 8 ≈ **55 ms**; QGC'nin kendi tamponu ve ekranı buna eklenir, ölçülmedi | toplam |
| Kaydedici + yayın süreci işlemcisi | kayıt boyunca 0.29 çekirdek (kayıt + yayın; yalnız kayıt 0.11) | `video.kayit.surec` |

## 4. Testler

`tez/sim/testler/test_goruntu_yayini.py` (8. grupta 3 test; bu grupta +5, simsiz, donanımsız):

1. `test_boxes_reach_the_stream_on_udp_5610_and_bad_messages_are_refused`: mesajın gidiş-dönüşü ve JSON biçimi; beş
   geçersiz mesajın gönderilmemesi, yedi bozuk datagramın çözülmemesi (bozuk JSON, liste, fazla / eksik alan, NaN, 65
   kutu, 16 kB üstü); gerçek UDP soketiyle alınma ve sayaçlar; `Tracker`'ın mesajı (iki kutu, seçilen 1, aynı karenin
   hakem kutusu; sonraki boş karede "hedef yok"); modelsiz hakem kaynağında her hakem karesinin mesajı.
2. `test_live_stream_is_the_spec_pipeline_and_its_frames_arrive_with_the_boxes`: hattın öğeleri sırasıyla ve ayarları
   (spec + `threads=1`), `yayin.sdp`; gerçek hat boş bir porta: 15 kare itilir, H.264 RTP alıcısından (`udpsrc` →
   `rtph264depay` → `avdec_h264` → `appsink`) 1280×720 kare gelir, seçili kutunun sol kenarı kırmızı, hakem kutusu mavi
   doğru yerde, "HEDEF YOK" yok; defter 15 / 15 kutulu.
3. `test_standalone_stream_draws_its_own_model_boxes_and_sends_no_los`: tek başına mesaj yalnız model kutuları
   (seçimsiz, hakemsiz); ayrı bir yorumlayıcıda `goruntu_yayini` + `video` içe aktarılınca `pymavlink`, `px4_baglanti`,
   `takip`, `senaryo` yüklenmez; `--qgc`'siz çıkış kodu 2.
4. `test_one_worker_serves_the_stream_and_the_recording`: yayın pencere dışındakiler dahil her ızgara karesini alır,
   kayıt yalnız penceredekileri; her kare bir kez okunur; takılı bir yazıcı varken yayın yalnız en yeniyi gösterir,
   kayıt dördünü de yazar.
5. `test_the_recorder_takes_the_frames_the_model_process_receives` (11.6): ayrı bir "spawn" sürecinden paylaşılan
   belleğe yazılan ızgara kareleri bayt bayt aynı gelir; okuyucu geride kalınca üzerine yazılan iki yuva atılır,
   okunduktan sonra üzerine yazılan kare işçide kullanılmaz ("ezilen" sayılır); yuvaya sığmayan kare ve sürecin sonu
   görülür (kaydedici kendi aboneliğine geçer). Seqlock kontrolü kaldırılınca test kırmızı oluyor (denendi). Bu test
   paylaşım kodundan sonra yazıldı (ölçüm sonucuna göre eklenen iyileştirme); kırmızıya dönüşü elle doğrulandı.

`test_video.py` (+1) `test_labels_drawn_on_their_own_crop_are_the_whole_frame_pixels`: etiketin kendi kutusunda
çizimi bütün karede çizimle piksel piksel aynı (kesirli konum, çapanın sağ / altında başlayan kutu, kenara taşan
yazı); bölüm 7'deki alt piksel hatası geri konunca kırmızı (denendi). `test_hedef.py`: `--qgc` artık bağlı (komut
satırı, `--videosuz --qgc`, senaryodaki `video: {qgc: true}`), ara hata beklentisi çıktı.

| Kontrol | Sonuç |
|---|---|
| `pytest tez/sim/testler -q` | **295 passed** (önce 289), 1 uyarı (sistemdeki protobuf, eskiden beri); GStreamer gerektiren kısım GStreamer yoksa atlanır |
| `ruff format` + `ruff check` (`tez/sim/ruff.toml`) | 59 dosya değişmedi; All checks passed (yeni modül yok, `ruff.toml` değişmedi) |
| `tez/pin/verify_pin.sh --worktree` | **KILIT SAGLAM (v1.17.0)** |

## 5. 11.6: kare kaydının ve yayının RTF payı

### 5.1 Düzen

`takip_yuruyen` (model v0.2, CPU, 4 çekirdek, stok Follow Me), `--ekransiz`; koşullar **tur tur dönüşümlü**, ben
makinede bir şey çalıştırmazken (scratchpad `seri.sh`). RTF = `rtf_ort` (ölçüt penceresi, saat eşlemesi). Gün içinde
`--videosuz` RTF'i bile 0.81–1.00 arasında kaydığı için pay **tur içinde**, aynı turun `--videosuz` koşusuna göre
hesaplandı (ort ± örnek sapması, n = 4). "Kaydedici CPU'su": kaydedici + yayın sürecinin kayıt penceresindeki işlemci
zamanı / duvar zamanı (`ozet.json` → `video.kayit.surec.pencere_cekirdek`, bütün iş parçacıkları, GStreamer dahil).

### 5.2 Önce: kaydedici kendi aboneliğiyle (seri 1, 21:41–22:18, 16 koşu)

Çizim ve x264 iyileştirmeleri (5.3 a–b) bu seride vardı.

| Koşul | RTF tur 1–4 | ort. | tur içi fark | kaydedici CPU | işlenen kare/sim-s | `model_ms` |
|---|---|---|---|---|---|---|
| `--videosuz` | 1.000 · 0.990 · 0.868 · 0.953 | 0.953 | — | — | 11.4 | 91 |
| video | 0.902 · 0.885 · 0.828 · 0.858 | 0.868 | **−0.084 ± 0.030** | 0.31–0.35 | 11.3 | 102 |
| video + `--qgc` | 0.857 · 0.843 · 0.842 · 0.813 | 0.839 | **−0.114 ± 0.059** | 0.48–0.49 | 11.7 | 100 |
| `--videosuz` + kameraya pasif abone | 0.891 · 0.934 · 0.875 · 0.861 | 0.890 | **−0.062 ± 0.051** | (abone 0.17) | 11.5 | 96 |

Ayrıştırma: abonelik ≈ 0.06, JPEG işi ≈ 0.02, yayın ≈ 0.03; toplam ≈ 0.11. **Payın çoğu kameraya ikinci
aboneliğin kendisi** (Gazebo'nun kareyi bir sürece daha göndermesi + aboneye saniyede 270 MB): 8. grubun "kaynağı
ayrılamadı" dediği soru bu. (4. grupta modelsiz bir koşuda pasif abone RTF'i düşürmemişti: işlemci boşken bedava.)
Pasif abone `seri.sh`'ın scratchpad betiği `pasif_abone.py`'dir (`nice 5`, yalnız sayar).

### 5.3 İyileştirmeler (her biri ölçülerek)

| | Ne | Ölçüm |
|---|---|---|
| a | Yayının yazıları kendi kutularında (`video.render_labels`): bütün kare PIL'e ve geri kopyalanmıyor | `draw_live` 8.8 → 3.0 ms/kare; yayın (bench, 15 kare/s) 0.30 → 0.215 çekirdek; 1000 rastgele karede eski yolla piksel piksel aynı |
| b | `x264enc threads=1` | 0.215 → 0.17 çekirdek; kodlama gecikmesi p50 7.0 → 8.4 ms (+1.3 ms) |
| c | Kareler model sürecinden, paylaşılan bellekle (8. grubun 2. seçeneği) | seri 2 (aşağıda): yalnız videolu koşularda kaydedici 0.31–0.35 → 0.16–0.18; ama `--qgc`'li koşularda 0.48 → 0.55–0.61 ve kare başına yazma 9 → 19 ms |
| d | c'nin sorunu: işçi her karede 9 MB'ı halkadan kopyalayıp protobuf'la yeniden kopyalıyordu ve küçültme her karede 7.6 MB yeni dizi ayırıyordu; bench'te işçinin **çekirdek (sistem) zamanı** 20 s'de 0.36 s'den 2.99 s'ye çıkmıştı (sayfa hataları). Şimdi kare halkadan **kopyasız** okunur (`frame_pixels`), kareler arasında tutulan tamponlara küçültülür (`Scaler`, aynı pikseller), okunduktan sonra seqlock denetlenir | bench (sim yok, 30 Hz gerçek boyutlu kare, yayın + kayıt): kaydedici süreci 0.40 → **0.19** çekirdek, işçinin sistem zamanı 2.99 → 0.05 s, yazma 12 → 5 ms/kare, yayın gecikmesi p50 19 → 9 ms |
| — | Denenip geri alınan: `Gst.Buffer.new_wrapped`'a bellek görünümü vermek (bir kopya azalır sanıldı) | PyGObject onu öğe öğe çeviriyor: kare başına 80 ms, süreç 1 çekirdek. `tobytes()` yolu kaldı (kodda yorumla) |

Seri 2 (c, 22:27–22:55, 12 koşu): `--videosuz` 0.892 · 0.987 · 0.886 · 0.814 (0.895), video 0.859 · 0.980 · 0.826 ·
0.902 (0.892; fark −0.003 ± 0.064), `--qgc` 0.844 · 0.824 · 0.894 · 0.891 (0.863; fark −0.032 ± 0.102). Gürültülü bir
seri; asıl kanıt kaydedici CPU'su ve bench'ti (d'ye götürdü).

### 5.4 Sonra: son kod (seri 3, 23:06–23:34, 12 koşu)

| Koşul | RTF tur 1–4 | ort. | tur içi fark | kaydedici CPU | işlenen kare/sim-s | `model_ms` |
|---|---|---|---|---|---|---|
| `--videosuz` | 0.961 · 0.950 · 0.931 · 0.947 | 0.947 | — | — | 12.2 | 86 |
| video | 0.917 · 0.983 · 0.947 · 0.833 | 0.920 | −0.027 ± 0.067 (4. tur 0.833, en yavaş 5 s 0.761; onsuz +0.002) | 0.11 | 11.8 | 91 |
| video + `--qgc` | 0.978 · 0.980 · 0.910 · 0.923 | 0.948 | **+0.001 ± 0.027** | 0.29–0.31 | 11.6 | 90 |

Her koşu GEÇTİ; paylaşılan halkada ezilen kare 0, kuyruk dolu olduğu için düşen kare 0, yayında atlanan kare 0.

### 5.5 Sonuç ve karar

- **Toplam pay (kayıt + yayın):** önce −0.114 ± 0.059, şimdi +0.001 ± 0.027 (n = 4). Yalnız kayıt: −0.084 ± 0.030 →
  −0.027 ± 0.067. Bu ölçümlerin gürültüsü içinde (tur içi farkın standart hatası 0.015–0.035) **kayıt ve yayının
  ölçülebilir bir RTF payı kalmadı**; kalan payın üst sınırı kabaca 0.03–0.05 (2 standart hata). RTF'in 1'in altına
  düşmesinin kalan sebebi modelin işlemci yüküdür (`--videosuz` 0.89–0.95; 4. gruptan beri bilinen, karar 12.11:
  4 çekirdek kalır).
- **İşlemci (daha az gürültülü ölçü):** kaydedici + yayın süreci kayıt boyunca video 0.31–0.35 → 0.11, video +
  `--qgc` 0.48–0.49 → 0.29–0.31 çekirdek. Model süreci kopya başına ≈ 0.7 ms (15 kare/s: ≈ 0.01 çekirdek) ekler;
  `model_ms` ve işlenen kare hızı koşullar arasında değişmedi.
- **Seçenekler** (`gorev-grubu-08.md` "Ne yapılabilir"): (1) `--videosuz` → artık gerekmiyor; (2) kareleri model
  sürecinin aboneliğinden almak → **uygulandı**; (3) 3'ten fazla dönüşümlü koşuyla payı ayırmak → yapıldı (3 seri × 4
  tur, pasif aboneyle); "kaydı/yayını ayrı çekirdeğe almak" → uygulanmadı: payın çoğu iş değil abonelikti, Gazebo'nun
  iş parçacıkları sabitlenmeden bir çekirdeğe almak SMT kardeşiyle çakışmayı garanti etmez ve paylaşımdan sonra
  ölçülecek pay kalmadı.
- **Karar (kullanıcı kararı 15.11.2026, Ahmet):** 13.11'deki "RTF'in önemli olduğu ölçümlerde `--videosuz`" kuralı kalktı; ölçüm koşuları da
  videolu koşulur (her koşunun `kosu.mp4`'ü olur).

## 6. Koşular (11.7)

Ayrıntılı satırlar `kabul-kosulari.md`'de. Her koşudan önce `pgrep -x px4` / `pgrep -f "^gz sim"` boştu; sonunda açık
PX4, Gazebo, GStreamer, kaydedici ya da yardımcı süreç kalmadı; `~/.config/Ultralytics` oluşmadı. Seçenek adları
`senaryo.py --help` ve `goruntu_yayini.py --help` ile doğrulandı.

### 6.1 Doğrulama koşusu (son kod)

`senaryo.py --senaryo takip_yuruyen --ekransiz --qgc --cikti tez/sim/sonuclar/g11_qgc`, yanında UDP 5600'ü dinleyen
alıcı (scratchpad `alici.py`: `udpsrc` → `rtph264depay` → `avdec_h264` → `appsink`, 2 s'de bir kareyi JPG yazar).
**GEÇTİ**, 2 dk 30 s. Bölüm "Kısaca" ve 3'teki sayılar; ayrıca RTF 0.857 (en yavaş 5 s 0.812), işlenen 11.6 kare/sim-s,
`model_ms` 99, uçtan uca 139 ms, `TEZ_LOS` 340 gönderildi = ULog 340, yatay mesafe ort. 12.36 m (en az 7.58 m), video
957 kare 63.8 s (kayıt 63.85 s), raporda video ya da yayın olayı yok. Önceki iki doğrulama koşusu (`g11_qgc_ilk`: ilk
kod, kendi aboneliği; `g11_qgc_ara`: kopyalı paylaşım) da GEÇTİ (1588 / 1588 ve 1582 / 1582 kare).

### 6.2 Tek başına mod

Sim ekransız açıldı (`g11_qgc` koşusunun dünyası), dron bu deneme betiğinden MAVLink ile 9 m'ye kaldırıldı,
`goruntu_yayini.py --qgc --model ~/auto-follow-modeller/person_detection_model_v0.2.pt` alıcıyla 45 s çalıştı, SIGINT
ile durduruldu: model 3 s'de hazır, **659 kare gönderildi = alıcı 659** (15.0 kare/s), 616 karede kutu, çıkış kodu 0,
"Hakem ve hedef seçimi yok; PX4'e hiçbir şey gönderilmez" satırı; dron indi, sim kapandı.

### 6.3 QGC'siz alıcılar (sim yok; gerçek bir kare 15 kare/s ile 5600'e basıldı)

| Alıcı | Sonuç |
|---|---|
| `gst-launch-1.0 udpsrc port=5600 caps="application/x-rtp,media=video,encoding-name=H264,payload=96" ! rtph264depay ! avdec_h264 ! videoconvert ! ...` (README'deki caps, `autovideosink` yerine dosyaya) | 6 s'de 95 kare çözüldü |
| `ffmpeg -protocol_whitelist file,udp,rtp -fflags nobuffer -flags low_delay -i tez/sim/araclar/yayin.sdp` (ffplay'in aynı girişi) | 6 s'de 97 kare 1280×720 H.264; ilk kareler "non-existing PPS" uyarısı (akışın ortasından katılınca ilk anahtar kareye kadar, ≤ 1 s) |
| `cvlc tez/sim/araclar/yayin.sdp` (VLC 3.0.20-3build6) | **açamadı**: dosyayı MPEG-PS sanıp kapandı; VLC'nin yapılandırmasında `--disable-live555` |
| `cvlc rtp://@:5600` | **açamadı**: "A description in SDP format is required … dynamic RTP payload format (96)" |

### 6.4 F0

`tez/sim/araclar/f0_kabul.sh` (stok derleme, `EXTERNAL_MODULES_LOCATION` boş): **GEÇTİ** — kamera 2304×1296, 30.3
kare/sim-s, RTF 1.00, fx 1773.9; `SYS_AUTOSTART` 4001; 21/21 parametre; Hold + Follow Target; 10 m kalkış; Hold'da
15 s, en büyük sapma yatay 0.06 / dikey 0.11 m; iniş + disarm; temiz kapanış.

## 7. Karşılaşılan sorunlar

1. **Kapanış işareti "daha yeni kare" sanıldı:** işçi, arkasında kare bekliyorsa yayını atlıyordu; `close()`'un `None`'ı
   kuyruktayken son kare yayınlanmadı. Bekleyen kare sayısı ayrı tutuldu (test yakaladı).
2. **Testimdeki eskime sınırı:** 15 kareyi 1 s'ye yayınca sonuncusu kutudan 1.03 s sonraya düştü, "kutulu" 14 çıktı;
   test kareleri 0.57 s'ye sığacak biçimde düzeltildi (kod doğruydu).
3. **Kırpıntıda çizimde alt piksel kayması:** PIL yazıyı çapanın kesirli kısmından (`math.modf`) çiziyor; kırpıntıya
   göre konum negatif olunca kesir işaret değiştirip 300 karenin 79'unda pikseller farklı çıktı. Kırpıntı çapanın solundan
   / üstünden başlatıldı: 1000 / 1000 aynı; test eklendi.
4. **Paylaşım + yayın yavaşladı** (5.3 c–d): sayfa hatası; kopyasız okuma ve tamponlu küçültmeyle giderildi.
5. **`new_wrapped(memoryview)` 80 ms** (5.3): geri alındı.
6. **GStreamer + geç içe aktarılan matplotlib çökmesi** (karar 10): yalnız ölçüm betiğimde; `LiveStream` önce çizer.
7. **VLC açamıyor** (6.3, karar 9): görev metnindeki "VLC ile `yayin.sdp`" bu makinenin sabit VLC'siyle yapılamıyor;
   ffplay / `gst-launch-1.0` yazıldı.
8. Ruff'ın satır uzunluğu ve `Gst` adı (N806) uyarıları düzeltildi.

## 8. Kalan sim-gerçek farkları (yayın için)

- **Ağ yok:** yayın aynı makinede, kayıpsız ve gecikmesiz bir döngü arayüzünden gider. Gerçek uçuşta Pi → yer
  istasyonu kablosuzdur (yöntem m24'te seçilecek); gecikme, kayıp ve donma Faz B'nin Wi-Fi benzetimidir (16. grup).
- **Kodlayıcı laptop CPU'sunda:** Pi 5'in donanım H.264 kodlayıcısı yoktur, x264 orada da işlemcide çalışır ama Pi'nin
  işlemcisi ve Hailo'nun yükü başkadır; simdeki 0.17 çekirdek Pi için bir ölçü değildir.
- **Hakem kutusu yalnız simde:** gerçek yayında yalnız Pi'nin kutuları olur.
- **Kare zamanı:** yayın duvar saatindedir, RTF < 1 iken kişinin hareketi canlı görüntüde gerçekten yavaştır;
  `kosu.mp4` ise sim saatindedir.

## 9. Açık konular ve sorulacaklar

- ~~`--videosuz` kuralı kalksın mı?~~ Karar (kullanıcı kararı 15.11.2026, Ahmet): kalktı (bölüm 5.5).
- ~~QGC'siz izleme için VLC yerine ffplay uygun mu?~~ Karar (kullanıcı kararı 15.11.2026, Ahmet): uygun; ffplay (sabit ffmpeg paketinin parçası) ve gst-launch. VLC'nin canlı
  yayını açması için live555'li bir VLC gerekir; Ubuntu deposunda yok, önerilmez.
- **Görsel kontrol (Ahmet, QGC 5.1.4):** "Kendin dene" 2. QGC'nin video ayarındaki alanın adı (port mu "UDP URL" mi)
  bu grupta görülmedi; README iki adı da yazıyor.
- Tasarım notu: model süreci artık video karelerini paylaşılan belleğe de kopyalıyor (kare başına ≈ 0.7 ms, `model_ms`
  değişmedi). Spec'teki "yayın ayrı süreç" kuralı korunuyor; ölçüm sonucuna dayanan bir uygulama kararı. Onaylandı
  (kullanıcı kararı 15.11.2026, Ahmet).
- Wi-Fi benzetimi (`netsim`, Faz B, 16. grup) bu hatta `rtph264pay`'den sonra eklenecek.

## 10. Dosyalar (commit'e girecekler)

- `tez/sim/araclar/goruntu_yayini.py`
- `tez/sim/araclar/yayin.sdp` (yeni)
- `tez/sim/araclar/video.py`
- `tez/sim/araclar/takip.py`
- `tez/sim/araclar/senaryo.py`
- `tez/sim/araclar/hedef.py`
- `tez/sim/araclar/goruntu.py`
- `tez/sim/araclar/algilama.py`
- `tez/sim/testler/test_goruntu_yayini.py`
- `tez/sim/testler/test_video.py`
- `tez/sim/testler/test_hedef.py`
- `tez/sim/README.md`
- `tez/env/VERSIONS.md`
- `agent-os/specs/2026-11-10-m06-sim-ortami/spec.md`
- `agent-os/specs/2026-11-10-m06-sim-ortami/tasks.md`
- `agent-os/specs/2026-11-10-m06-sim-ortami/EKIP_ICIN_OZET.md`
- `agent-os/specs/2026-11-10-m06-sim-ortami/implementation/gorev-grubu-11.md` (yeni, bu dosya)
- `agent-os/specs/2026-11-10-m06-sim-ortami/implementation/kabul-kosulari.md`

`tez/sim/ruff.toml` değişmedi (yeni Python modülü yok). 11.6'nın paylaşım kısmı (`goruntu.py`, `algilama.py` ve
`goruntu_yayini.py`'deki `FrameShare` / `ShareReader` / `Scaler` / `frame_pixels`) aynı dosyalarda yayınla iç içe
olduğu için tek commit önerilir. Repo dışı: görseller (aşağıda), koşu klasörleri `tez/sim/sonuclar/g11_*` (git dışı),
ölçüm betikleri scratchpad'de.

### Görseller (repo dışı)

`/home/ahmet/Desktop/Follow/3_m06_Simulasyon/`:

| Dosya | Ne |
|---|---|
| `g11_qgc_yayin_karesi.jpg` | Doğrulama koşusunda UDP 5600'ü dinleyen alıcının çözdüğü kare (70.9 s): kalın kırmızı seçili kutu (0.67), mavi "hedef (hakem)" kutusu, "model: 196 ms önceki kare, 1 kutu, hedef izleniyor"; kişi yürüdüğü için kutular biraz geride |
| `g11_qgc_kosu.mp4` | Aynı koşunun `kosu.mp4`'ü (h264, 2000×720, 63.8 s) |
| `g11_tek_basina_yayin_karesi.jpg` | Tek başına modun karesi (65.5 s): yalnız ince kırmızı model kutusu, "tek başına, hedef seçimi yok" |

---

## 10. Ek düzeltme (15.11): Gazebo penceresi senaryodan açılmıyordu

- **Belirti (Ahmet):** `senaryo.py` pencereli koşulunca Gazebo penceresi hiç açılmıyordu; bir kez Ubuntu'nun "ruby3.2 has
  stopped unexpectedly" uyarısı çıktı (`/var/crash`: `gz sim -g`, signal 6). Koşunun kendisi etkilenmiyordu (sunucu ayrı
  süreç). Daha önce de olmuştu.
- **Neden:** `senaryo.py` OpenCV'yi (`cv2`) içe aktarıyor; opencv-python içe aktarılırken süreç ortamına kendi Qt
  eklentilerinin yolunu yazıyor (`QT_QPA_PLATFORM_PLUGIN_PATH`, `QT_QPA_FONTDIR`). Bu değişkenler `calistir.sh` üzerinden
  Gazebo penceresine geçiyor; pencere sistemin Qt5'i yerine uyumsuz eklentiyi yüklemeye çalışıp
  `QGuiApplicationPrivate::createPlatformIntegration` içinde duruyordu (abort). `calistir.sh` pencerenin çıktısını
  `/dev/null`'a attığı için hata görünmüyordu. Değişkenler elle verilerek aynı çökme yeniden üretildi; değişkenlersiz
  pencere aynı dünyayla 40 s hatasız çalıştı.
- **Düzeltme:** `calistir.sh` pencereyi `env -u QT_QPA_PLATFORM_PLUGIN_PATH -u QT_QPA_FONTDIR -u QT_PLUGIN_PATH` ile
  başlatır; dünya hazır olduğunda pencere süreci ölmüşse sim günlüğüne "UYARI: Gazebo penceresi açılamadı" ve nedenini
  görmek için komut yazılır. Test: `testler/test_calistir_pencere.py` (3 test; düzeltmesiz betikte 2'si kırmızı).
- **Doğrulama:** aynı komutla (`DRI_PRIME=1 ... senaryo.py --senaryo takip_yuruyen --qgc`) pencereli koşu
  (`sonuclar/pencere_duzeltme_dogrulama`): pencere açıldı (Ahmet ekranda gördü), koşu boyunca `gz sim -g` süreci canlı,
  uyarı yok, GEÇTİ. 298 test, ruff temiz, KILIT SAGLAM.

## 11. QGC'deki takılma denemesi (15.11, 11.7)

- Ahmet'in ilk QGC denemesinde (`g11_kendin_dene_qgc`, Gazebo penceresi açık) canlı görüntü bir kez belirgin takıldı.
  O koşunun kayıtlarında gönderen tarafta sorun yok: 1582 kare gönderildi, atlanan / taşan 0, yayına itme en çok
  33 ms; kamera kareleri düzenli (en uzun aralık 0.25 s, kaydın başında); RTF 0.87 (en düşük 5 s: 0.83).
- İşletim sisteminin UDP alım kaybı sayacı (`/proc/net/snmp` RcvbufErrors) açılıştan beri 20 813 idi; hangi
  programa ve ana ait olduğu bilinmiyor (11. grubun ölçüm denemelerinden olabilir).
- Tekrar: QGC 5.1.4, Low Latency Mode kapalı. `qgc_takilma_pencereli` (pencere açık, RTF 0.76) ve
  `qgc_takilma_ekransiz` (RTF 0.89): ikisi de GEÇTİ, 1598 / 1598 kare, takılma yok; sayaç iki koşu boyunca
  20 813'te kaldı (0 kayıp).
- Sonuç: kalıcı bir hata değil; tek seferlik bir yük ya da QGC'nin anlık meşguliyeti. Gazebo penceresi RTF'i
  belirgin düşürüyor (0.89 → 0.76); canlı görüntü duvar saatinde aktığı için o zaman hareket ağır çekim görünür.
  Ölçüm koşuları `--ekransiz` kalır. x264 `intra-refresh` ve Low Latency Mode Faz B'de, Wi-Fi grubunda (16)
  ölçülecek (tasks.md 16.0a).

## Kendin dene

**Başlamadan:** Terminal açmak için **Ctrl+Alt+T**. Aşağıdaki gri kutulardaki satırları **tek tek** kopyala, terminale
**Ctrl+Shift+V** ile yapıştır ve **Enter**'a bas. Her satır tek başına çalışır (değişken yok; yeni bir terminalde de
olur). Bir komutu yarıda kesmek için **Ctrl+C**.

### 1. Hazır görseller

```bash
xdg-open /home/ahmet/Desktop/Follow/3_m06_Simulasyon/g11_qgc_yayin_karesi.jpg
```

QGC'ye giden görüntü böyle görünür: üstte "CANLI · t = … s (sim)", **kalın kırmızı kutu** modelin seçtiği kişi (yanında
güveni), **mavi kutu** hakemin (doğru cevap) kutusu. Kutular modelin işlediği ≈ 0.1–0.2 s önceki kareye aittir; kişi
yürürken biraz geride kalırlar.

```bash
xdg-open /home/ahmet/Desktop/Follow/3_m06_Simulasyon/g11_tek_basina_yayin_karesi.jpg
```

```bash
vlc /home/ahmet/Desktop/Follow/3_m06_Simulasyon/g11_qgc_kosu.mp4 2>/dev/null
```

### 2. QGC'de canlı izle (asıl görsel kontrol, ~3 dakika)

**Terminal 1** — önce açık bir sim olmadığından emin ol (iki satır da bir şey yazmamalı):

```bash
pgrep -x px4
```

```bash
pgrep -f "^gz sim"
```

**Terminal 1** — QGC'yi aç (bu terminal QGC açık kaldıkça meşgul kalır):

```bash
/home/ahmet/Desktop/QGroundControl-v5.1.4-x86_64.AppImage
```

**QGC'de, bir kez:**
1. Sol üstteki **QGC simgesine** (Q harfi) tıkla → **Uygulama Ayarları** (Application Settings).
2. Soldaki listeden **Video**'yu seç.
3. **Kaynak** (Video Source) kutusundan **UDP h.264 Video Stream**'i seç.
4. Altında çıkan port / adres alanı **5600** olmalı (varsayılan; alanın adı "UDP URL" ise değeri `0.0.0.0:5600`).
   Değilse 5600 yaz.
5. Sol üstteki QGC simgesine tıklayıp **Fly** (uçuş ekranı) görünümüne dön. Ayar kalıcıdır.

**Terminal 2** (Ctrl+Alt+T ile yeni terminal) — senaryoyu Gazebo penceresiyle ve canlı yayınla koştur:

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && DRI_PRIME=1 /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --qgc --cikti tez/sim/sonuclar/g11_kendin_dene_qgc
```

Neye bakacaksın:
- Terminal 2'de "Canlı yayın hazır: H.264 RTP -> udp://127.0.0.1:5600" ve birkaç saniye sonra "PX4 ve Gazebo hazır"
  çıkar. QGC dronu kendiliğinden bulur (telemetri UDP 14550) ve görüntü **sol alttaki küçük pencerede** belirir;
  tıklayınca büyür. Önce dron yerdedir (çimen), sonra 9 m'ye kalkar.
- Sol üstte **"CANLI · t = … s (sim)"**: sim saati; QGC'nin uçuş modu yazısı ≈ 27. saniyede **Follow Target** olur.
- Kişi dronun ≈ 13 m önündedir: **kalın kırmızı kutu** (modelin seçtiği kişi, yanında güveni) ve **mavi kutu**
  ("hedef (hakem)", doğru cevap). Model bulamazsa kırmızı kutu kaybolur, ikinci satırda "bu karede hedef bulunamadı",
  ortada büyük kırmızı **HEDEF YOK** çıkabilir.
- 60. saniyede kişi yürümeye başlar: kutular kişinin biraz gerisinde kalır (modelin ≈ 0.1–0.2 s gecikmesi).
- Sonda dron iner: model kapandığı için ikinci satır "kutu bilgisi eski" olur; bu beklenen davranış.
- Koşu bitince Terminal 2'de "SONUÇ: GEÇTİ"; QGC'yi pencereden kapatabilirsin.

Görüntü gelmezse: QGC'nin Video ayarına tekrar bak (kaynak "UDP h.264 Video Stream", 5600); UDP 5600'ü aynı anda tek
bir program dinleyebilir (ffplay ya da başka bir QGC açık olmasın).

### 3. QGC'siz izle (ffplay)

**Terminal 1** — senaryoyu pencere olmadan koştur:

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz --qgc --cikti tez/sim/sonuclar/g11_kendin_dene_ffplay
```

**Terminal 2** — Terminal 1'de "Canlı yayın hazır" satırı çıktıktan sonra:

```bash
ffplay -protocol_whitelist file,udp,rtp -fflags nobuffer -flags low_delay -i /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/araclar/yayin.sdp
```

Bir pencere açılır (ilk saniye siyah ya da bozuk olabilir: ilk anahtar kare 1 s'de bir gelir). Kapatmak için pencerede
**q**. Not: **VLC bu yayını açamaz** (Ubuntu'nun VLC'si SDP'den RTP okuyamıyor); `vlc .../yayin.sdp` hemen kapanır.
Aynı işi GStreamer ile yapmak için (Terminal 2):

```bash
gst-launch-1.0 udpsrc port=5600 caps="application/x-rtp,media=video,encoding-name=H264,payload=96" ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false
```

### 4. Tek başına: elle uçarken modelin kutuları

**Terminal 1** — simi Gazebo penceresiyle aç (dünyada kişi dronun 12.9 m önünde durur, 60. saniyede yürür; bu terminal
`pxh>` olur):

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && DRI_PRIME=1 tez/sim/calistir.sh --dunya /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/g11_qgc/dunya.sdf
```

**Terminal 2** — QGC (2. adımdaki Video ayarı yapılmışsa yeniden gerekmez):

```bash
/home/ahmet/Desktop/QGroundControl-v5.1.4-x86_64.AppImage
```

**Terminal 3** — yayını kendi modeliyle başlat:

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/goruntu_yayini.py --qgc --model /home/ahmet/auto-follow-modeller/person_detection_model_v0.2.pt
```

QGC'de sol taraftaki **Takeoff** düğmesine bas ve kaydırarak onayla (10 m'ye kalkar). Kalkınca kişi görüntüye girer:
yalnız **ince kırmızı kutular** (modelin kutuları), sağ üstte "kırmızı: model kutuları (tek başına, hedef seçimi
yok)"; mavi hakem kutusu ve "HEDEF YOK" yoktur, PX4'e hiçbir şey gitmez. Terminal 3 10 saniyede bir "yayın: … kare"
yazar. Bitirmek için Terminal 3'te **Ctrl+C**, Terminal 1'deki `pxh>`'ye `shutdown` yaz (Gazebo da kapanır).

### 5. Kontroller

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python -m pytest tez/sim/testler -q
```

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && tez/pin/verify_pin.sh --worktree
```

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && tez/sim/araclar/f0_kabul.sh
```

Beklenen: `295 passed`; `KILIT SAGLAM (v1.17.0)`; F0 (~1 dakika) sonunda `SONUÇ: GEÇTİ`.

Bir koşunun yayın defteri (gönderilen kare, hız, kutu mesajları, gecikme):

```bash
grep -A 12 '"yayin"' /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/g11_qgc/ozet.json
```
