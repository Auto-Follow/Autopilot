# Follow Me deneme simülasyonu (renkli düz dünya)

> **DENEME — tezde kullanılmayacak.** Bu klasör, yapay zekâ (Claude Code) ile kısa sürede ne kadar simülasyon
> yapılabileceğini görmek için WSL'de hazırlanmış bir denemedir (28.09–01.10.2026). Proje liderinin izniyle sadece
> `deney/ai-follow-sim` branch'inde durur; `main`'e alınmayacak. Tezin asıl simülasyon ve test arayüzü ekipçe ayrıca
> tasarlanacak. Sonuçlar (`sonuclar/`, 30 MB) repoya konmadı; özeti `Kamera_Geolocation_WiFi_Raporu.pdf`.

PX4 Follow Me modunun ([dokümandaki](https://docs.px4.io/v1.17/en/flight_modes_mc/follow_me) gibi) Gazebo'da
denenmesi: kırmızı hedef yürür, drone varsayılan parametrelerle (8 m geride, 8 m yukarıda, tam arkadan) takip eder,
kamera ışını / yükseklik / zemin kesişimleri sahnede çizilir.

## Kullanım

Bir kere (PX4 SITL derlenmiş olmalı; panel için `python3-tk`):

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot
tez/deney/follow_sim/kur.sh
```

Her seferinde:

```bash
tez/deney/follow_sim/baslat.sh             # düz kamera
tez/deney/follow_sim/baslat.sh --egim 40   # 40° aşağı bakan kamera
```

Açılanlar: renkli düz dünya, x500 + Camera Module 3 ayarlı kamera (`models/mono_cam_cm3`: 66°, 2304×1296),
Gazebo penceresi, kontrol paneli, işaretli kamera yayını (QGC UDP 5600 + ayrı pencere UDP 5601). QGroundControl aynı
makinede açılınca kendiliğinden bağlanır.

- Paneli açmadan: `FOLLOW_PANEL=0 tez/deney/follow_sim/baslat.sh`, video olmadan: `FOLLOW_VIDEO=0 ...`
- Geri almak: `tez/deney/follow_sim/kaldir.sh` (yeniden kurmak: `kur.sh`)
- Düz `make px4_sitl gz_x500_mono_cam` bu denemeden etkilenmez (kanca sadece `baslat.sh` ile çalışır).

`kur.sh` şunları yapar (PX4 reposunda takip edilen hiçbir dosya değişmez, `git status` temiz kalır):

| Ne | Nerede |
|---|---|
| Modeller ve dünya (symlink, `git status`'ta görünmez) | `Tools/simulation/gz/models`, `.../worlds` |
| PX4 kancası: panel + video (sadece `renkli_duz*` dünyalarında) | `build/px4_sitl_default/etc/init.d-posix/airframes/4010_gz_x500_mono_cam.post` |
| OpenCV'li Python ortamı | `tez/deney/follow_sim/.venv` (`requirements.txt`) |

WSL'de çalıştırılırsa QGC ve video Windows tarafına (varsayılan ağ geçidi) gönderilir; normal Linux'ta her şey
`127.0.0.1` üzerindendir. PX4 ROMFS'i yeniden ürettiğinde kanca silinir; `baslat.sh` her açılışta geri koyar.

## Uçuş

1. Panelde **1) Kalk** → drone 2.5 m'ye kalkar.
2. **2) Follow Me** → drone hedefin 8 m arkasına, 8 m yüksekliğe gider ve hedefe döner.
3. Hedef menüsünden yürüyüş seç (Gidip gel, Daire, Kare veya Klavye: I/K ileri-geri, J/L dön).
4. Kumanda çubukları (fare ile sürükle ya da klavye) Follow Me'de PX4'ün kendi RC ayarlarını değiştirir:
   - Sol çubuk ↑↓ (W/S) → takip yüksekliği
   - Sağ çubuk ↑↓ (ok tuşları) → takip mesafesi
   - Sağ çubuk ←→ → takip açısı

**"Hedef hızını gönder" kutucuğu:** İşaretliyken `FOLLOW_TARGET` hedefin gerçek hızını da taşır (telefon GPS'i gibi).
İşaret kaldırılınca hız `NaN` gönderilir ve PX4 hızı art arda gelen konumlardan kendisi kestirir; kamerayla konum
bulan Vision sistemi de böyle çalışacak. (`0` gönderilseydi PX4 bunu "hedef duruyor" ölçümü sayardı.)

**Vision modu kutucuğu:** İşaretliyken `FOLLOW_TARGET` sadece hedef kamerada görünürken gönderilir (videodaki
"HEDEF YOK" = PX4'e veri gitmiyor). Görünürlük, yayın programının tespitinden gelir (UDP 5610, panelde "kamera");
yayın kapalıysa kamera geometrisinden hesaplanır ("geometri"). "Hedef görünürlüğü" satırı kaybın süresini gösterir:
PX4 son mesajdan sonra 3 s hedefi son hızıyla tahmin eder, sonra drone son noktada bekler. Düz kamera 8 m'de hedefi
göremez; **"Takip yüksekliği 2.5 m"** düğmesi `FLW_TGT_HT`'yi buna uygun yapar ("Varsayılan FLW param." geri alır).

Panel kapanırsa kumanda sinyali kesilir ve PX4 güvenlik gereği **eve döner (RTL)**. PX4 kapanınca panel de kapanır.

**Kadraj notu:** Kamera düz (ufka) bakıyor, dikey görüş açısı ~40° (±20°). Varsayılan 8 m / 8 m'de hedef ufkun
45° altında kalır, yani görüntüde **görünmez**; panel "KADRAJ DIŞI" yazar, kırmızı nokta düzlemin altında kalır.
Hedefin görünmesi için takip açısı (atan(yükseklik / mesafe)) 20°'nin altında olmalı, ör. yükseklik ≈ 2.5 m.

## Yer istasyonu ve Wi-Fi menzili (seçenek A)

Sahnede drone'un kalkış noktasının 5 m gerisinde bir **yer istasyonu** (masa + dizüstü + Wi-Fi anteni) ve etrafında
**100 m'lik sarı menzil halkası** var. Panel "Yer istasyonu mesafesi (Wi-Fi)" satırında drone–yer istasyonu
mesafesini gösterir: yeşil < 80 m, sarı 80–100 m, kırmızı > 100 m (mesaj kutusuna uyarı da düşer).
Follow Me'de drone hedefin peşinden gittiği için önemli olan hedef–drone değil **drone–yer istasyonu** mesafesidir.
Bu bir planlama sınırıdır, radyo modeli değil: gerçek menzil sahada ölçülmeli. Konum/menzil `follow_core.py`
içindeki `GCS_POSITION`, `LINK_RANGE_M` ile dünyadaki `yer_istasyonu` / `menzil_halkasi` pozlarında aynı tutulmalı.

## Sahnedeki çizimler

| Renk | Anlamı |
|---|---|
| Mavi yarı saydam dikdörtgen | Görüntü düzlemi (kameranın 1.2 m önünde, dik; 66° × 40° görüş alanı) |
| Kırmızı küçük küre | Işının görüntü düzlemini (ya da uzantısını) deldiği nokta = hedefin piksel konumu (u, v) |
| Turuncu çizgi | Slant distance ışını (kamera → hedef) |
| Yeşil çizgi | Yükseklik h (kamera → zemin, dik) |
| Beyaz çizgi | Zemindeki yatay mesafe |
| Turuncu / yeşil küre | Zemin kesişimi (ışın) / Zemin kesişimi (yükseklik) |

Çizimlerin üzerinde yazı yoktur; sayısal değerler (h, θ, slant distance = h / cos θ, piksel (u, v), hedef GPS)
panelde canlı gösterilir.

## Canlı kamera (işaretli görüntü)

`renkli_duz` dünyasında Gazebo'nun ham kamera yayını kapalıdır. Onun yerine `video/goruntu_yayini.py`
(PX4 kancası otomatik başlatır) kamerayı okur, kırmızı hedefi bulur (prototip: renk eşiği), kutu + ayak noktası +
piksel (u, v) yazar ve H.264/RTP olarak iki yere yollar:

| Nereye | Port | Nasıl izlenir |
|---|---|---|
| QGroundControl | UDP 5600 | Application Settings → Video: `UDP h.264 Video Stream`, port 5600 |
| Ayrı video penceresi | UDP 5601 | Panelde **Kamera penceresi** ya da `tez/deney/follow_sim/.venv/bin/python tez/deney/follow_sim/video/video_izleyici.py` |

Video penceresi QGC'den bağımsızdır: QGC'de harita açıkken pencereyi ikinci monitöre sürükle, **F** tam ekran,
**Q** kapatır. VLC/ffplay ile izlemek için `video/video.sdp` dosyasını aç (başka makineye göndermek:
`FOLLOW_VIDEO_HOSTS=<ip>:5600,<ip>:5601`).

- Yayını kapatmak: `FOLLOW_VIDEO=0 tez/deney/follow_sim/baslat.sh`
- Ayarlar: `goruntu_yayini.py --help` (çözünürlük 1280×720, 15 fps, 2 Mbit/s varsayılan)
- Yayını 30 fps yapmak (kameranın kendi hızı): `FOLLOW_VIDEO_FPS=30 tez/deney/follow_sim/baslat.sh`
- WSL'de görüntü gelmezse Windows Güvenlik Duvarı'nda QGroundControl'e ağ izni ver.
- Gerçek drone'da aynı mantık: kaynak picamera2, tespit Vision algoritması; kodlama + gönderme aynı kalır.
  Raspberry Pi 5'te donanımsal H.264 kodlayıcı yok (x264 işlemcide çalışır), yayını küçük tut.
- Dünyadaki eklenti listesi PX4'ün `gz_bridge/server.config`'i ile aynı tutulmalı (sadece GstCameraSystem hariç).

## Eğik kamera (`baslat.sh --egim`)

```bash
tez/deney/follow_sim/baslat.sh --egim 40      # kamera 40° aşağı bakar
tez/deney/follow_sim/baslat.sh                # düz kamera (eğim 0)
```

PX4 reposuna dokunmaz: `models/x500_egik_kamera` (x500 + aşağı eğik `mono_cam_cm3`, eğim 0 da dahil) ve `worlds/renkli_duz_egik.sdf`
(renkli_duz + bu drone) üretilir, PX4 dünyadaki drone'a bağlanır (`PX4_GZ_MODEL_NAME=x500_mono_cam_0`). Eğim
`FOLLOW_CAMERA_PITCH_DEG` ile panele, geometri çizimine ve geolocation'a geçer.

## Geolocation (kameradan hedef konumu)

`geolocation.py` (sadece numpy, Pi'de aynen çalışır): piksel (u, v) → kamera ışını → drone duruşu (PX4 EKF,
`ATTITUDE_QUATERNION`) ve konumu (`LOCAL_POSITION_NED`) ile dünyaya → düz zeminle kesişim → enlem/boylam.

- Pikselin zamanı = kamera karesinin zamanı; EKF pozu o ana interpole edilir (SITL'de Gazebo zamanı = PX4 zamanı).
- Kutusu görüntü kenarına (alt/sol/sağ) değen tespitler kullanılmaz: kesik kutunun alt ortası ayak noktası değildir.
- Zemin düzlemi: EKF orijini drone yerdeyken alınır → zemin `BODY_HEIGHT_LANDED_M` (0.227 m) aşağıdadır.
- Panelde **Konum kaynağı**: "Gerçek konum" (GPS'li hedef) veya "Kameradan hesap" (FOLLOW_TARGET pikselden
  hesaplanan konumla, hızsız, sadece hedef görünürken). Hesaplanan konum ve gerçeğe göre hatası canlı gösterilir.

## Wi-Fi / gecikme benzetimi

| Yol | Ne benzetilir | Nasıl |
|---|---|---|
| FOLLOW_TARGET | Vision işlem gecikmesi, ya da tespit yerde yapılırsa Wi-Fi | `LinkImpairment`: sabit gecikme + kayıp (bağımsız ya da patlamalı, Gilbert-Elliott) |
| Video (RTP) | Pi → dizüstü Wi-Fi | `goruntu_yayini.py` içinde GStreamer `netsim`: gecikme + paket kaybı |

Panelde kaydırıcılarla ayarlanır. Not: Vision Pi'de (drone üstünde) çalışırsa FOLLOW_TARGET Wi-Fi'dan geçmez
(Pi → Pixhawk seri hat); Wi-Fi sadece operatörün videosunu etkiler. Video ölçümü: `video/wifi_olcum.py`.

## Deneyler (`deney.py`, `analiz.py`)

Ekransız, tekrarlanabilir ölçüm: PX4 + Gazebo'yu kendisi başlatır (senin terminalinde simülasyon açıksa başlamaz),
kalkar, Follow Me'ye geçer, her senaryoda hedef önce bekler (drone yerleşir), sonra **test parkurunu** yürür
(20 m yürü, 90° dön, 20 m, 5 s dur, 20 m koş 3 m/s, 180° dön, 20 m, R = 10 m yarım daire, 5 s dur).

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot/tez/deney/follow_sim
.venv/bin/python deney.py --deney kamera --egim 40        # 8 yükseklik/mesafe çifti
.venv/bin/python deney.py --deney geolocation --egim 40   # konum hatası, sonra kameradan kapalı döngü
.venv/bin/python deney.py --deney gecikme --egim 40       # FOLLOW_TARGET gecikme / kayıp
python3 analiz.py sonuclar/kamera_egim40                   # grafik + ozet.md
```

Kadraj analizi kayıtlı gerçek pozdan her eğim (0–70°) için ayrı hesaplanır; tek uçuş bütün eğimleri karşılaştırır.
Sonuçlar `sonuclar/` altında.

## Dosyalar

| Yol | İçerik |
|---|---|
| `kur.sh` / `kaldir.sh` | Bir kerelik kurulum / geri alma |
| `baslat.sh` | Simülasyonu başlatır, `--egim N` ile kamera N° aşağı |
| `geolocation.py` | Piksel → zemin → enlem/boylam (Pi'de de kullanılabilir) |
| `deney.py` / `analiz.py` | Ekransız deneyler / analiz ve grafikler |
| `video/wifi_olcum.py` | Video kaybı/gecikmesi ölçümü ve ekran görüntüleri |
| `sonuclar/` | Deney kayıtları, grafikler, özetler |
| `px4_hook.post` | PX4 kancası (QGC MAVLink bağlantısı + panel) |
| `follow_core.py` | MAVLink (FOLLOW_TARGET, MANUAL_CONTROL), hedef hareketi, geometri, Gazebo çizimleri |
| `follow_panel.py` | Tkinter kontrol paneli |
| `video/goruntu_yayini.py` | İşaretli kamera yayını (tespit + çizim + H.264 RTP) |
| `video/video_izleyici.py`, `video/video.sdp` | QGC'den bağımsız video penceresi / VLC-ffplay için SDP |
| `.venv/` | OpenCV'li Python ortamı (`--system-site-packages`) |
| `worlds/renkli_duz.sdf` | Renkli düz dünya (hedef dahil) |
| `models/hedef`, `models/renkli_zemin` | Hedef, zemin |
| `models/yer_istasyonu`, `models/menzil_halkasi` | Yer istasyonu ve 100 m Wi-Fi menzil halkası |
| `make_texture.py` | Zemin dokusunu yeniden üretir |

Kamera montajı `follow_core.py` içindeki `CAMERA_OFFSET` / `FOLLOW_CAMERA_PITCH_DEG` ile PX4'ün `x500_mono_cam` modeline
göre ayarlı; model değişirse bunları da güncelle.
