# m06 Simülasyon Ortamı — Ekip (ve ekibin Claude'u) için özet

> **Bu dosya kimin için:** Auto-Follow ekibindeki herkesin ve onların Claude / Agent OS oturumlarının, m06
> simülasyonunu ve ondan çıkan kararları tek yerden öğrenmesi için. Claude'a şöyle söyleyebilirsiniz:
> *"Autopilot reposundaki `agent-os/specs/2026-11-10-m06-sim-ortami/EKIP_ICIN_OZET.md` dosyasını oku; m06 simülasyonu
> ve kararları buradadır."* Ayrıntı gerekirse aynı klasördeki `spec.md`, `tasks.md` ve `implementation/` belgeleri.
>
> Sahibi: Ahmet (m06, issue #7). Son güncelleme: 15.11.2026. Dal: `ozellik/m06-sim-ortami` (Autopilot).
> Buradaki frame/mesaj tanımları **varsayımdır**; ortak spec'ler (yol haritası m03 frame, m04 haberleşme, m05 ICD)
> yazılınca onlara göre güncellenir.

## 1. Sim ne yapıyor? (bir paragraf)

Gazebo Harmonic + PX4 SITL v1.17.0 (stok kod, PX4 dosyası değişmedi) üzerinde, gerçek dronumuza benzeyen bir X500
(`x500_tez`) ve yürüyen insanlar var. Dronun kamerası (Camera Module 3 benzeri) görüntüyü laptoptaki insan algılama
modeline (Ortatepe v0.2, YOLOv8s tabanlı, CPU) veriyor; seçilen kişinin yönü (`TEZ_LOS`) ve yerdeki konumu
(`FOLLOW_TARGET`) PX4'e gidiyor; PX4'ün takip modu dronu hareket ettiriyor; döngü kapalı. Simülasyon kişinin gerçek
yerini her karede bildiği için ("hakem") modelin, hedef seçiminin ve uçuşun doğruluğu sayıyla ölçülüyor. Her koşu bir
video (`kosu.mp4`: kamera + kuşbakışı harita), bir rapor (`rapor.html`) ve ~100 ölçütlük `ozet.json` üretiyor;
`--qgc` ile dron kamerası, modelin ve hakemin kutuları çizili olarak QGroundControl'e canlı da gidiyor.

## 2. Kamera ve montaj (kesinleşen sim varsayılanı, gerçek için öneri)

**Değerler için tek dosya: `tez/sim/kamera_montaji.yaml`** (sim'in kullandığı değerlerle testle eşleşir).

| | Değer |
|---|---|
| Kamera | Raspberry Pi Camera Module 3 **Standard**; simde yatay FOV 66.0° (1.151917 rad), düşey 40.1°, 2304×1296, 30 fps, bozulmasız |
| Montaj | gövdeye sabit (gimbal yok), **35° aşağı** (14.11.2026 kararı; öncesinde 45°), base_link'e göre FLU (0.151, 0, −0.035) m = FRD (0.151, 0, 0.035) m |
| Gerçek montaj | **henüz yapılmadı.** Öneri 35° (+1° içinde); takılınca açı araçta ±0.5° ölçülüp Pi'ye verilmeli. Öneri: 30–40° arasında 2.5° adımlı ayarlanabilir parça (model değişince en iyi açı değişebilir) |
| Uçuş önerisi (doğrulanmamış) | **9 m yükseklik, kişinin 12.9 m gerisi** (≈ 1.43 × yükseklik = yükseklik / tan 35°). **Yedek: 8 m / 12.9 m** (aynı montaj; gerçek kamera ya da Hailo kişiyi 9 m'de zor bulursa). Stok Follow Me ile 11.4 m'nin altına inilmemeli |

Neden 35°: ~180 koşuluk modelli tarama (30–45°, 4–15 m, farklı mesafeler; her aday iki yolda 3–6 koşu). 45°'de dron
köşelerde kişiye çok yaklaşıp kadrajdan çıkarıyor; 37.5° ani geri dönüşte kişiyi 6 koşunun 5'inde kaybetti; 12–15 m'de
v0.2 kişiyi neredeyse hiç bulamıyor. Alçak + uzak takip (30–32.5°, 6–7 m, 12.9 m) köşede yaklaşmayı çözüyor ama
kalabalıkta yanlış kişiye geçme %70–77'ye çıkıyor (35°/9 m'de %16) ve dron hızlanırken kişi görüntünün üstünden
çıkabiliyor; ilk uçuşlar için önerilmiyor. Belge: `implementation/gorev-grubu-17-on-kamera-acisi.md` (bölüm 17–21).

## 3. Eksenler (varsayım; m03 yazılınca güncellenir)

- Kamera: OpenCV optik frame — x sağ, y aşağı, z ileri; piksel orijini sol üst (u sağa, v aşağı).
- Gövde: PX4 FRD — x burun, y sağ kanat, z aşağı.
- Gazebo: dünya ENU, modeller FLU; FLU → FRD = diag(1, −1, −1).
- Eğim 0 iken optik → gövde: optik z → x, optik x → y, optik y → z; sonra burun aşağı `egim` kadar döndürülür.
- Kod: `tez/sim/araclar/kamera.py` (`Camera.pixel_to_los`, `camera_to_body`). Ortatepe'nin m10 requirements'ındaki kurallar bunlarla aynı.

## 4. PX4'e giden mesajlar (varsayım; m05 ICD yazılınca güncellenir)

| Mesaj | İçerik | Sıklık | "Hedef yok" |
|---|---|---|---|
| `DEBUG_VECT`, `name = "TEZ_LOS"` | x, y, z = kameradan hedefe **gövde FRD birim vektör** (kutu merkezi; attitude kullanılmaz). Normu 1'den 1e-3'ten fazla sapan ya da sonlu olmayan vektör gönderilmez | işlenen kare başına bir, ≤ 30 Hz, aynı kare iki kez gitmez | x = y = z = NaN |
| `FOLLOW_TARGET` | kişinin ayak noktasının düz zemin varsayımıyla enlem/boylamı (1e7 tamsayı), `alt` = zemin AMSL, hızlar NaN | ≤ 10 Hz | gönderilmez |

PX4 v1.17.0 notları (kaynaktan doğrulandı): `debug_vect` uORB'a `time_usec`'i taşımaz → alıcı **varış zamanıyla** zaman
aşımı yapmalı ve `name == "TEZ_LOS"` ile süzmeli. `FOLLOW_TARGET`'ta `est_capabilities` okunmaz; bilinmeyen hız 0 değil
NaN gönderilmeli. PX4 `FOLLOW_TARGET`'ı en çok 500 ms'de bir füzyonlar. MAVLink: sim yer istasyonu gibi UDP 14540'ta,
QGC 14550'de. Kod: `tez/sim/araclar/px4_baglanti.py` (`send_los`, `send_follow_target`).

## 5. Takip modu ve kendi modunu takmak (m15 — Yusuf Kurt / Yusuf Algan)

- Sim modu **adıyla** seçer (`AVAILABLE_MODES`); numara koda gömülü değil. Ekipten gelen bilgi (09.11, kesin değil;
  m15/m16 spec'inde kesinleşecek): mod adı **"AUTO FOLLOW"**, parametreler **`AF_XXX`**. Hazır olunca:
  `senaryo.py --senaryo takip_yuruyen --takip tez_los --mod-adi "AUTO FOLLOW" --px4-baslat "<başlatma komutu>"`
  (başlatma komutu henüz bilinmiyor). Başlatma komutu olmadan stok olmayan bir ad sim açılmadan PX4'ün mod listesiyle
  reddedilir; komutla verilirse ad PX4 açılınca, kalkıştan önce PX4'ün listesinde aranır.
- Ağaç dışı modülü takmak (m06 görev grubu 10, PX4 dosyası değişmez): `tez/sim/derle.sh --harici <klasör>` (içinde
  `src/CMakeLists.txt`, `config_module_list_external ... PARENT_SCOPE`; modülde `DEPENDS` yok), sonra
  `senaryo.py ... --takip tez_los --mod-adi "<ad>" --px4-baslat "<modül> start" --los hakem`. Mod kendini
  `register_ext_component_request` ile kaydeder (ad ≤ 24 karakter) ve her arming check isteğine cevap verir; koşu
  sonunda `sim.log`'da "unresponsive" aranır. Adım adım: `tez/sim/README.md` → "C. Kendi PX4 modülünü takmak";
  iskelet modül (`c4b4abf342`) ile denendi: `implementation/gorev-grubu-10.md`. İşin sonunda bayraksız
  `tez/sim/derle.sh` yine stok SITL'dir.
- **Stok Follow Me ölçümleri = m15 için gereksinim listesi** (spec "PX4 stok Follow Target davranışı"):
  - Mod açılınca hedefin kuzeye gittiğini varsayar (`FlightTaskAutoFollowTarget.hpp:284`), hedef ≥ 1 m/s olmadan rotayı
    güncellemez (`.cpp:191`) → başta gereksiz yörünge dönüşü.
  - Model konumundaki sıçramaları hız sanıp duran kişinin etrafında salınır; simde `FLW_TGT_RS 0.3` ile bastırıldı
    (gerçek dronda 0.1; bedeli köşede 0.5–0.9 s geç dönüş).
  - Kişi durunca/dönünce kestirim kişiyi geçer; dron ortalama **≈ 6.2 m** yaklaşır (mesafeden bağımsız). Stok modda en az
    mesafe koruması yok → **m15'te olmalı.**
  - Kestirim 3 s güncellenmezse dron son noktada havada bekler; mod değişmez, uyarı yok → kişi kaybında tanımlı davranış gerekli.
  - Gerçek uçuşta `follow_target*` konuları ULog'a girmiyor (kaydedici açılışında yoklar) — açık konu.

## 6. Model ve görüntü işleme için ölçülenler (m08/m10/m11 — Yusuf Ortatepe)

- Model: `person_detection_model_v0.2.pt` (sha256 `c5f6838be50c2c09ca788e97381b68567f0df3f20e430905142ce88f8abaa440`),
  imgsz 640, conf 0.25, laptop CPU ≈ 85–100 ms/kare; kameradan PX4'e uçtan uca ≈ 120 ms. Repoda değil; yolu `--model`.
- Bulma oranı kişinin görüntüdeki boyuna bağlı (~104 000 kare): 150–180 px **%61**, 120–150 px **%25**, < 120 px **%3**.
  Daha zor: yandan görünen kişi, kısmen örtülen, başka biriyle yan yana (kutu birleşiyor), kadraj kenarında kesik.
  Aynı boyda 30° bakış 45°'ten iyi. Kalabalıkta 35°'de yanlış kişiye geçme %16 (45°'de %6–12).
- **Stok COCO `yolov8s.pt` ile kıyas (15.11, `kalabalik_park` × 3):** simdeki insanlarda stok model v0.2'den belirgin
  iyi: bulma %79 / %64, doğru kişi %74 / %49, yanlış kişi %4.5 / %16; süre benzer (92 / 88 ms). Yalnız sim insanında
  ölçüldü (v0.2 gerçek görüntüyle eğitildi); gerçek CM3 görüntüsünde aynı kıyas yapılmalı. `takip_yuruyen` × 3'te
  (stok Follow Me) fark daha büyük: bulma %96 / %62, kilit kaybı 1.3 / 4, köşede PX4 0.5–0.8 s daha erken yetişiyor;
  izlendi 3/3 ve mesafe aynı, konum hatası 0.44 / 0.36 m. Ayrıntı `implementation/gorev-grubu-13.md` 7.
- Veri toplama / eğitim önerileri: 30–40° yukarıdan bakış, kişi 120–200 px, yandan görünüm, yan yana duran kişiler;
  simin segmentasyon kamerası otomatik etiketli sentetik veri üretebilir (gerçek veriyle karıştırılarak; istenirse m06 aracı yazar).
- m11 için: kişi bulunamayan kareler %27–47; konum titreşimi PX4'te sahte hız üretiyor; PX4'e süzülmüş hız gönderilirse
  salınımın kalkması bekleniyor (PX4 kodundan çıkarım, denenmedi).
- Ayrıntı: `implementation/gorev-grubu-17-on-kamera-acisi.md` ("Model hangi koşullarda iyi algılıyor", Ortatepe'ye öneriler).

## 7. Simi çalıştırmak (Autopilot kökünden)

Kurulum adım adım (apt paketleri, venv, model dosyası, AMD `DRI_PRIME=1`): `tez/sim/README.md` → "A. Kurulum".

```bash
tez/sim/derle.sh && tez/sim/kur.sh                     # bir kere; kur.sh sonda model klasörünü denetler (indirmez)
tez/sim/araclar/f0_kabul.sh && tez/sim/araclar/f1_kabul.sh && tez/sim/araclar/m06_kabul.sh   # kabul testleri, ~11 dk
P=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python
$P tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz          # tek koşu (~3 dk)
$P tez/sim/araclar/toplu.py --senaryo takip_yuruyen --tekrar 3            # aynı senaryo 3 kez, dağılım
$P tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz --los hakem   # "mükemmel algılayıcı" ile karşılaştırma
```

Önemli bayraklar: `--takip yok|tez_los|follow_me`, `--mod-adi`, `--model`, `--imgsz`, `--conf`, `--modelsiz`,
`--videosuz`, `--kareleri-sakla`, `--qgc`, `--cikti`. Kendi modunla kabul testi (m06 Görev grubu 13): `tez/sim/araclar/m06_kabul.sh --mod-adi
"<ad>" --px4-baslat "<modül> start"` (isteğe bağlı 3. koşu, aynı yedi koşul). Gecikme ve hedef kaybı denemeleri için (m06 görev grubu 12):
`--gecikme-ms 200` (PX4'e giden her şey 200 **sim** ms geç; titreşim ve `TEZ_LOS` saat ofseti/kayması senaryonun
`gecikme` bloğunda), `--yeniden-kilit-bekleme-s 1.5` (kilit düşünce operatör 1.5 s sonra yeniden seçer); koşuları yan
yana koymak: `$P tez/sim/araclar/karsilastir.py <klasör A> <klasör B> [--html dosya.html]`.

**QGC'de canlı görüntü** (m06 görev grubu 11): koşuya `--qgc` ekle; QGC 5.1.4 → Uygulama Ayarları → Video → "UDP h.264
Video Stream", port 5600 (H.264 RTP, 1280×720, 15 kare/sim-s). Görüntüde modelin kutuları (kırmızı, seçilen kalın) ve
hakemin hedef kutusu (mavi); kutular modelin işlediği ≈ 0.1–0.2 s önceki kareye ait. Elle uçarken (açık sim + QGC)
kendi modeliyle: `$P tez/sim/araclar/goruntu_yayini.py --qgc --model <dosya.pt>` (hakem ve LOS yok). QGC'siz:
`ffplay -protocol_whitelist file,udp,rtp -i tez/sim/araclar/yayin.sdp` (Ubuntu'nun VLC'si bu yayını açamaz).
Ayrıntı: `tez/sim/README.md` → "Canlı video (QGC)". Senaryolar `tez/sim/senaryolar/` (`takip_yuruyen` = 35° montaj, 9 m /
12.9 m; `takip_yuruyen_45_10m`, `takip_yuruyen_45_8m` = eski 45° karşılaştırma; `kalabalik_park`, `kivrimli_yuruyus`,
`yuruyen_insan`). Çıktılar `tez/sim/sonuclar/<klasör>/` (git'e girmez). Aynı anda tek sim çalışır.

## 8. Kurallar ve sınırlar

- PX4/ROMFS/submodule değişmez (`tez/pin/verify_pin.sh --worktree` → "KILIT SAGLAM"); başlangıç parametreleri
  `tez/sim/parametreler/` ve senaryolardan `PX4_PARAM_*` ile.
- Model, video, ULog repoya girmez. Yeni paketler sabit sürümüyle `tez/env/VERSIONS.md`'de (ultralytics, torch, ffmpeg).
- Simin gerçeği temsil etmediği yanlar: rüzgâr yok; GPS/baro yüksekliği kusursuz; zemin düz; kamera kusursuz (pozlama,
  bulanıklık, gürültü yok — Faz B); tek insan modeli, tek ışık; model laptop CPU'sunda (Hailo değil); RTF ≈ 0.85–0.95
  (sim gerçek zamandan yavaş; sebebi modelin işlemci yükü, video kaydının ve canlı yayının ölçülebilir payı yok);
  canlı yayın aynı makinede, ağ kaybı ve gecikmesi yok (Wi-Fi benzetimi Faz B).

## 9. Karar bekleyenler

Kamera montaj açısı (öneri 35°) · m01'e "en az yatay mesafe" ölçütü (öneri ≥ 3 m) · gerçek uçuşta `follow_target`
kaydı · ortak model saklama yeri · `TEZ_LOS` biçiminin m05'te kesinleşmesi · yer istasyonunda görüntü/takip gösterim
yöntemi (öneri: önce QGC video + videoya çizili kutular, simde `--qgc` ile hazır; gerekirse PySide6 uygulaması; QGC'yi
kaynaktan özelleştirmek en son).
