# Auto-Follow simülasyon ortamı (`tez/sim`)

Görüntü işleme (Vision) ve kontrol (PX4 içindeki tez modu) ekiplerinin kodlarını gerçek uçuştan önce Gazebo'da
**ölçerek** denemesi için ortak ortam. Tasarım: "Auto-Follow Simülasyon ve Test Ortamı — Tasarım Önerisi" belgesi.

> **Durum: F1 (hakem çekirdeği) + gerçekçi dünya, m06 Görev grupları 1–8.** Tez dronu + düz alan ve dokulu
> çayır (patika, ağaçlar) + stok PX4 (airframe 4001, gerçek dronun ayarlarıyla) + insan gibi yürüyen hedef ve başka
> insanlar, YAML senaryo, kare kare doğru cevap (görünürlük ve kutu dahil), dron kamerasında koşan insan algılama
> modeli (v0.2, CPU; `algilama.csv`), geçici hedef seçimi ve PX4'e `TEZ_LOS` (`DEBUG_VECT`) akışı, düz zemin konum
> hesabı ve stok Follow Me ile kapalı döngü (`FOLLOW_TARGET`), adıyla seçilen takip modu (`yok` → Hold, `follow_me` →
> Follow Target, `tez_los` → `--mod-adi`), ULog, spec'teki bütün ölçütler, kontroller ve uyarılarla HTML rapor, aynı
> senaryonun N koşusu ve dağılımı (`toplu.py`), her koşunun VLC'de açılan videosu (`kosu.mp4`: dron kamerası +
> kuşbakışı harita), ağaç dışı bir PX4 modülünü (ör. m15'in takip modu) derleyip başlatarak aynı senaryo, ölçüt ve
> videoyla denemek (Görev grubu 10; aşağıda "C. Kendi PX4 modülünü takmak"), dron kamerasını kutularla birlikte
> QGroundControl'e canlı yayınlamak (Görev grubu 11; aşağıda "Canlı video (QGC)"). m06'nın devamı:
> `agent-os/specs/2026-11-10-m06-sim-ortami/`.

> **Ekip için kısa özet** (kamera ve montaj, eksenler, PX4'e giden mesajlar, kendi modunu takmak, model ölçümleri,
> karar bekleyenler): [`agent-os/specs/2026-11-10-m06-sim-ortami/EKIP_ICIN_OZET.md`](../../agent-os/specs/2026-11-10-m06-sim-ortami/EKIP_ICIN_OZET.md).
> Kamera değerlerini kopyalamak için tek dosya: [`kamera_montaji.yaml`](kamera_montaji.yaml).

PX4 kaynağı, ROMFS ve submodule'ler **değişmez** (`tez/pin/verify_pin.sh --worktree` → "KILIT SAGLAM"); dron, dünya
ve başlangıç parametreleri `tez/sim/` altında durur.

## PX4 tarafı: (b) yolu

- `calistir.sh` PX4'ü stok `4001_gz_x500` airframe'iyle açar (`PX4_SYS_AUTOSTART=4001`) ve dünyada zaten duran
  `x500_tez_0` dronuna bağlar (`PX4_GZ_MODEL_NAME=x500_tez_0`). `PX4_SIM_MODEL=x500_tez` yalnız bilgi amaçlıdır; tek
  başına verilirse rcS `<no>_x500_tez` adlı bir airframe arar ve "Unknown model" diyerek çıkar.
- Gerçek dronun ayarları her açılışta yüklenir. Sıra (aynı parametre birden çok yerdeyse **sonuncu kazanır**):
  `tez/sim/parametreler/gercek_dron.params` (4019 kazançları + 22.08 davranış ayarları) → `sim.params`
  (`SDLOG_PROFILE 163`: `debug_vect` ULog'a girer) → `calistir.sh --param AD=DEĞER` (birden çok verilebilir).
- Yöntem: stok posix rcS'teki `PX4_PARAM_<AD>=<değer>` döngüsü. rcS bunları `param reset_all`'dan sonra, airframe
  dosyasından önce `param set` ile yazar; airframe'in `param set-default` satırları onları ezmez. Dikkat: PX4
  `param set` değer o anki değere eşitse hiçbir şey yazmaz; böyle bir değeri sonradan bir `set-default` satırı
  değiştirebilir. F0 testi bu yüzden her değeri PX4'ten geri okur.
- Dosya biçimi: her satırda `AD DEĞER  # kaynak` (ad büyük harf, en fazla 16 karakter; değer sayı; kaynak yorumu
  zorunlu). Hatalı satır, dosya adı, satır numarası ve parametre adıyla bildirilir ve sim hiç açılmaz.
- Hangi 22.08 parametrelerinin neden alındığı: spec "Başlangıç parametreleri" ve
  `implementation/gorev-grubu-01.md`. Her açılışta `parameters*.bson` silinir; koşular birbirinin parametresini
  devralmaz.
- **Manyetometre:** dronun pusulası PX4'ün kendi `sensor_mag_sim`'idir (`sim.params` `SENS_EN_MAGSIM 1`): PX4'ün dünya
  manyetik modeli (WMM) alanını dronun gerçek konumu ve duruşuyla üretir; EKF'nin beklediği alanla aynıdır. Gazebo'nun
  manyetometre sistemi `server.config`'te yüklenmez: Gazebo Harmonic'in alanı PX4'e doğu bileşeni aynalanmış ulaşıyor
  (sapma −2.57°, beklenen +3.41°) ve EKF yaw'ını 6° kaydırıyordu (m06 Görev grubu 7, iş A;
  `testler/test_manyetometre.py`). Açılışta birkaç saniye "Found 0 compass" uyarısı görülür (`sensor_mag_sim` ilk GPS
  yer gerçeğini bekler); sonra kaybolur.

## Kurulum (bir kere)

Ön koşul: [`TEZ_README.md`](../../TEZ_README.md) kurulumu tamam, `make px4_sitl` çalışıyor.

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot
tez/sim/derle.sh            # ilk sefer birkaç dakika; çıktı build/px4_sitl_tez
tez/sim/kur.sh              # insan modeli, zemin dokuları ve ağaçları indirir (~20 MB, sha256 kontrollü), dünyaları
                            # üretir (ilk sefer ~3 dakika); git'e girmez. Tekrar çalıştırınca sadece eksik/değişeni yapar
```

`derle.sh` stok `px4_sitl_default` yapılandırmasını (+ Gazebo eklentileri) ayrı bir klasöre derler; ekibin normal
`build/px4_sitl_default` derlemesine dokunmaz. Ağaç dışı bir PX4 modülüyle derlemek için `derle.sh --harici <klasör>`
(aşağıda "C"). `build/px4_sitl_tez` başka bir harici klasörle (ya da harici modülle) yapılandırılmışsa `derle.sh`
CMake'i kendiliğinden yeniden yapılandırır: bayraksız `derle.sh` her zaman stok SITL'e döner.

## Çalıştırma

```bash
tez/sim/calistir.sh                          # Gazebo penceresi + bu terminalde PX4 kabuğu (pxh>)
tez/sim/calistir.sh --ekransiz               # pencere yok (otomatik testler için)
tez/sim/calistir.sh --param FLW_TGT_DST=10   # parametre dosyalarından sonra bir parametre daha (sonuncu kazanır)
tez/sim/calistir.sh --px4-baslat "tez_auto_follow start"   # PX4 açılınca bir PX4 komutu (birden çok; "C" bölümü)
```

AMD hibrit GPU'lu laptopta Gazebo penceresini açmadan önce `export DRI_PRIME=1`.

- QGroundControl'ü açın; kendiliğinden bağlanır (UDP 14550).
- Kalkış: QGC'de **Takeoff** (10 m'ye kalkar; yükseklik `MIS_TAKEOFF_ALT`).
- Kalkıştan sonra PX4 **Hold**'a geçer ve yerinde bekler. Stok **Follow Target** (Follow Me) modu da listededir.
- Kapatma: `pxh>` içinde `shutdown` veya Ctrl+C. Gazebo da kapanır.
- Her açılış temiz parametrelerle başlar (ekip standardı: testler birbirinin parametresini devralmaz).

Kamera: Camera Module 3 Standard (yatay 66°, 2304×1296, 30 fps), gövdenin altında ön kızaklardaki tutucuda
(X500 V2 "Depth Camera Mount" yeri), **35° aşağı** (simin varsayılan montajı, `kamera.NOMINAL_TILT_DEG`; Görev
Grubu 17'nin kamera eğimi taramasıyla 14.11'de seçildi, öncesinde 45°; gerçek montaj henüz yapılmadı, takılınca açısı
araçta ölçülür), Gazebo konusu `/x500_tez/kamera/image` (+ `/x500_tez/kamera/camera_info`).

## F0 kabul testi

```bash
tez/sim/araclar/f0_kabul.sh              # simi kendisi açar (pencere yok), ~1.5 dakika, sonunda "SONUÇ: GEÇTİ"
tez/sim/araclar/f0_kabul.sh --acik-sim   # zaten açık bir sim üzerinde (ör. Gazebo + QGC penceresiyle izlemek için)
```

Kontrol ettikleri: kamera çözünürlüğü, hızı (sim saniyesi başına kare) ve odak uzaklığı; `SYS_AUTOSTART` 4001;
iki `.params` dosyasındaki her parametrenin PX4'te aynı değerde olması (`PARAM_REQUEST_READ`); "Hold" ve "Follow
Target" modlarının QGC listesinde olması; 10 m kalkış; Hold'da 15 s konum tutma (sapma < 0.5 m); iniş ve disarm; PX4
ve Gazebo'nun temiz kapanması. Log: `build/px4_sitl_tez/tez_kabul/sim.log`.

## Senaryolar (F1)

Senaryo, hedefin yolunu ve dronun ne yapacağını anlatan bir YAML dosyasıdır (`tez/sim/senaryolar/`). Koşturmak:

```bash
P=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python
$P tez/sim/araclar/senaryo.py --senaryo yuruyen_insan              # Gazebo penceresiyle (~3 dakika)
$P tez/sim/araclar/senaryo.py --senaryo yuruyen_insan --ekransiz   # pencere yok
$P tez/sim/araclar/senaryo.py --senaryo yuruyen_insan --dogrula    # + tepe kamerasıyla hedef konumu kontrolü
$P tez/sim/araclar/senaryo.py --senaryo yuruyen_insan --param FLW_TGT_DST=10   # bir PX4 parametresi daha
$P tez/sim/araclar/senaryo.py --help                               # bütün bayraklar
```

Bayraklar senaryodaki değeri ezer: `--model`, `--imgsz`, `--conf`, `--sinif`, `--modelsiz` (algılama), `--takip`,
`--mod-adi`, `--los`, `--param AD=DEĞER` ve `--px4-baslat KOMUT` (ikisi de birden çok verilebilir), `--gecikme-ms`,
`--qgc`, `--videosuz`, `--kareleri-sakla`. Koşunun geçerli ayarlarının hepsi `ozet.json` → `ayarlar`'a yazılır.

**Ara durum (m06 sürerken):** m06'nın sonraki görev gruplarında bağlanacak bir ayar varsayılan dışında verilirse
koşu simülasyon açılmadan durur ve hangi grupta bağlanacağını söyler (ör. `gecikme.ek_ms: 200.0 (--gecikme-ms):
Görev grubu 12'de bağlanacak`); hiçbir ayar sessizce yok sayılmaz. Bugün bağlı olanlar: `takip.kaynak: yok`,
`follow_me` ve `tez_los` (`--mod-adi`), `takip.los: model | hakem` (`--los`), algılama (`algilama.*`, `--model`,
`--imgsz`, `--conf`, `--sinif`, `--modelsiz`), `kusurlar` (Faz A: boş), `video.mp4` / `--videosuz`,
`--kareleri-sakla`, `takip.px4_parametreleri` ve `--param`, `takip.px4_baslat` ve `--px4-baslat` (10. grup),
`video.qgc` / `--qgc` (11. grup). `ozet.json` → `ayarlar.henuz_bagli_degil` 8. gruptan beri boştur.

**Mod her zaman adıyla seçilir** (`yok` → "Hold", `follow_me` → "Follow Target", `tez_los` → `takip.mod_adi` /
`--mod-adi`); numarası koda
gömülmez, koşuda PX4'ün `AVAILABLE_MODES` listesinden okunur. PX4'ün sunmadığı bir ad simülasyon açılmadan, PX4
v1.17.0'ın seçilebilir modlarını listeleyen bir hatayla reddedilir (harici bir modun adı ise PX4 açılıp modül
başladıktan sonra, kalkıştan önce PX4'ün listesinde aranır; "C" bölümü). Örnek duman testi: `--takip tez_los
--mod-adi "Hold"`. Ekipten gelen bilgi (09.11, Yusuf Algan; kesinleşmiş değil, m15/m16 spec'inde kesinleşecek):
m15'in modu QGC'de **"AUTO FOLLOW"** adıyla görünecek, parametreleri `AF_` önekli olacak; modül takılınca
`--takip tez_los --mod-adi "AUTO FOLLOW" --px4-baslat "<başlatma komutu>"`.

Senaryo yöneticisi mod adını ve model dosyasını (sha256) kontrol eder, modeli kendi sürecinde yükler, dünyayı (temel
dünya + hedef) yazar, Gazebo ve PX4'ü açar, dronu kaldırır ve takip kaynağının moduna adıyla alır, hedef yürürken
doğru cevabı kaydeder ve `TEZ_LOS` gönderir, kayıt bitince modeli ve `TEZ_LOS` akışını kapatır, iner, kapatır ve
raporu yazar. Çıktı `tez/sim/sonuclar/<tarih>_<ad>/` (git'e girmez):

| Dosya | İçerik |
|---|---|
| `kosu.mp4` | **Koşunun videosu** (VLC; aşağıda "Video"): solda dron kamerası, hakemin ve modelin kutuları; sağda kuşbakışı harita; 2000×720, 15 kare/s, mod seçiminden senaryo sonuna. `--videosuz` ile yapılmaz |
| `rapor.html` | Sonuç (GEÇTİ / KALDI / TAMAMLANMADI); en üstte videonun satırı; "Kontroller ve uyarılar" (model görüntüde çalışıyor, 3 m uyarısı, kameranın yakın sınırı, mod, RTF); gruplu ölçümler (takip: mesafe ve kadraj, arkada kalma ve yörünge, konum ve FOLLOW_TARGET, PX4 kestirimi; (a) model, (b) LOS, (c) zaman); takip zaman çizelgesi, PX4 Follow Target (rota ve yörünge açısı), üstten harita, mesafe ve kamera görüntüsü grafikleri; mod zaman çizelgesi (ULog); ayarlar (model sha256, PX4 parametreleri) |
| `dogru_cevap.csv` | **Dron kamerasının her karesi için bir satır** (~30 Hz, karenin sim zamanıyla): dron konumu ve duruşu (roll/pitch/yaw, PX4 yönleriyle), kamera konumu, hedef konumu/hızı, hedefin o karedeki pikseli (ayak, merkez, baş) ve kadrajda olup olmadığı, kameradan hedefe menzil ve **doğru görüş vektörü** (aşağıda) |
| `ozet.json` | Ölçütler ve sonuç (makineyle okunur); `ayarlar`: koşunun geçerli ayarları (senaryo + komut satırı) ve her başlangıç parametresinin istenen değeri, kaynağı ve PX4'ten geri okunan değeri; kameranın kalibrasyonu ve gövdeye montajı (ofset, C_cb) |
| `algilama.csv` | **Modelin işlediği her kare için bir satır**: `t_us` (= `round(t*1e6)`, `dogru_cevap.csv` ile birleştirme anahtarı), `t` (yakalama, sim s), `sira`, `onceki_atlanan`, duvar saatinde `varis`/`basla`/`bitis`/`alinma` ve sim saniyesinde `*_sim`, `ulasma_ms`, `bekleme_ms`, `cozme_ms`, `kusur_ms`, `model_ms`, `islem_ms`, `teslim_ms`, `kutu_sayisi`; hedef seçimi (`secim`, `kilitsiz_neden`, `kilit_no`, `ardisik_kacirma`, `secilen_kutu`, `secilen_u0…v1`, `secilen_guven`, `kilit_iou`, kapı `kapi_u/v/px`, `merkez_mesafe_px`), `los_i_x/y/z` (seçilen kutunun LOS'u, gövde FRD), giden `tez_los_x/y/z` (boş = NaN = hedef yok), `tez_los_sonuc`, `hazir`/`serbest`/`gonderim` (+ `*_sim`), `takip_ms`, `ek_gecikme_ms`, `uctan_uca_ms` (yakalama → gönderim, sim ms); seçilen kutunun düz zemin konumu: `konum` (`hesaplandi`, `kutu_yok`, `kenar`, `poz_yok`, `referans_yok`, `ufka_yakin`, `kamera_yok`), `ayak_u/v`, `isin_asagi`, kare anının EKF pozu (`ekf_n/e/d`, `ekf_roll/pitch/yaw_deg`, `poz_once_ms`/`poz_sonra_ms`), `konum_n/e/d`, `konum_lat/lon/alt`, `konum_menzil_m`, `konum_yatay_m`, dünyada `konum_x/y`, `gercek_x/y`, `konum_hatasi_m`; `follow_me`'de `ft_sonuc`, `ft_gonderim_sim`, `ft_uctan_uca_ms` |
| `tez_los.csv` | **Her `TEZ_LOS` denemesi bir satır** (kaynak `model` ya da `hakem`): `t_us`, `t`, `kaynak`, `hedef` (1 = yön, 0 = NaN), `x y z`, `time_usec`, `sonuc` (`gonderildi`, `gecersiz`, `baglanti_yok`, `ayni_kare`, `eski_kare`, `hiz_siniri`), zamanlar ve `uctan_uca_ms` |
| `follow_target.csv` | `follow_me`: **her FOLLOW_TARGET denemesi bir satır** (kaynak `model` ya da `hakem`): `t_us`, `t`, `kaynak`, `lat lon alt` (giden), dünyada `x y`, `gercek_x/y` (hedefin o karedeki gerçek yeri, değerlendirme), `hata_m`, `hata_gonderimde_m`, `sonuc`, zamanlar ve `uctan_uca_ms` |
| `kutular.csv` | Modelin bulduğu bütün kutular (`t_us`, `t`, `sira`, sıra no, `u0 v0 u1 v1` piksel kenarı, `guven`, `sinif`) |
| `ucus.ulg` | PX4 uçuş kaydı (PlotJuggler / pyulog). `follow_me`'de kaydedici FOLLOW_TARGET başlayınca bir kez yeniden başlatılır (aşağıda): `ucus.ulg` o andan inişe kadardır, öncesi `ucus_once.ulg` |
| `dunya.sdf`, `senaryo.yaml`, `sim.log` | Koşunun girdileri ve logu |

**Model koşuda nasıl çalışır:** Model ayrı bir süreçtedir (`algilama.ModelProcess`) ve Gazebo kare yayınlamaya
başladığı andan kayıt bitene kadar kamerayı okur. Sim gerçek zamanda akar, Gazebo modeli beklemez: model meşgulken
gelen kare bekleyen karenin yerine geçer ve `atlanan` sayılır; model boşalınca yalnız en yeni kareyi alır, kuyruk
büyümez. `ozet.json`'da `kare_defteri` (gelen = işlenen + atlanan + bekleyen) ve `olcutler`'de kayıt penceresinin
sayıları (`uretilen`, `islenen`, `atlanan_kare_orani`, `islenen_kare_hizi_hz`, `model_ms_*`, `ulasma_ms_*`,
`bekleme_ms_ort`, `rtf_ort`, `algilama_orani` …) yazılır; raporun "Kontroller"i modelin görüntüde gerçekten
çalıştığını (en az bir karede hedefle IoU ≥ 0.5) söyler. RTF 0.9'un altına düşerse olaylarda
uyarı çıkar. `--modelsiz` ile model süreci hiç açılmaz (F1 böyle koşar).

**Hedef seçimi ve `TEZ_LOS` (geçici; asıl çözüm m10/m11, biçim ortak ICD'ye kadar varsayım):** Her işlenen karede
takip iş parçacığı (`araclar/takip.py`) hedefin kutusunu seçer. İlk kilit hakemden gelir (operatörün hedefi
seçmesinin yerine): hakemin hedef kutusuyla IoU'su en yüksek kutu (en az 0.3). Sonra merkezi bir önceki seçime en
yakın kutu izlenir; en çok önceki kutunun köşegeninin 1.5 katı uzaktaki bir kutu kabul edilir. 10 işlenen karede
eşleşme olmazsa kilit düşer ve hakemle yeniden kilitlenilir (sayılır). Seçilen kutunun merkezi `kamera.py` zinciriyle
(camera_info iç parametreleri, koşunun montajı: varsayılan 35°) gövde FRD birim vektörüne (LOS i) çevrilir ve PX4'e
`DEBUG_VECT` adı `TEZ_LOS` olarak gönderilir: işlenen kare başına bir mesaj, `time_usec` = karenin yakalama anı,
kutu yoksa `x = y = z = NaN` (hedef yok; eski veri tekrarlanmaz). `--los hakem` ile model yerine hakemin `los_govde`'si
(LOS ii) her kamera karesinde gider ("mükemmel algılayıcı"). Gönderim kuralları: aynı kare iki kez gitmez, kareler
yalnız ileri gider, en çok bir mesaj / kamera karesi (≤ 30 Hz), sonlu olmayan ya da birim olmayan vektör gönderilmez
ve sayılır. Akış `yok` dahil her takip kaynağında vardır (algılama kapalı ve `yok` iken LOS yoktur, F1 böyle koşar);
PX4'le bağlantı kurulunca başlar, kayıt bitince kapanır. Kayıt penceresinin sayıları `ozet.json` → `olcutler`'de
(`tez_los_*`, `uctan_uca_ms_*`, `yeniden_kilit_sayisi`, `secim_dogru_orani`, `los_aci_hatasi_*_deg`, ULog'dan
`tez_los_px4_sayisi`), bütün koşununki `ozet.json` → `tez_los`'ta.

**Konum hesabı ve stok Follow Me (`follow_me`; geçici, asıl çözüm m10, biçim ortak ICD'ye kadar varsayım):** Her
işlenen karede seçilen kutunun alt ortası (ayak noktası) `kamera.py` zinciriyle (camera_info, koşunun montajı) ve
**karenin yakalandığı andaki EKF pozuyla** (PX4'ün `ATTITUDE_QUATERNION` 50 Hz + `LOCAL_POSITION_NED` 30 Hz akışı,
pymavlink `message_hooks` ile toplanır, kare anına ara değerlenir) bir ışına çevrilir ve ev noktasının 0.227 m
altındaki düz zeminle kesiştirilir (`araclar/konumlama.py`). Nokta PX4'ün kendi izdüşümüyle `GPS_GLOBAL_ORIGIN`'e göre
enlem/boylama çevrilir (PX4 kökeni yalnız değişince gönderdiği için bağlantıda ve kalkıştan sonra istenir) ve
`FOLLOW_TARGET` olarak gider: hız NaN (0 gönderilse PX4 hedefi "duruyor" sayardı), `alt`
zeminin AMSL'si, en çok her üçüncü kamera karesinde (≈ 10 Hz). Kutu sol/sağ/alt kenara 8 px'ten yakınsa, ışın ufkun
14.5°'den az altındaysa (`u_D < 0.25`) ya da kare anını 0.15 s içinde kapsayan poz yoksa konum yoktur ve FOLLOW_TARGET
gitmez. `--los hakem` ile kişinin gerçek konumu gider, yalnız göründüğü karelerde ("mükemmel algılayıcı"). Dron
kalkıştan sonra "Follow Target"e alınır; `FLW_TGT_HT` senaryoda yoksa `drone.yukseklik_m`, `FLW_TGT_DST`
`gercek_dron.params`'tan (8 m). PX4 v1.17.0 konumu en sık 500 ms'de bir kaynaştırır; FOLLOW_TARGET kesilince 3 s son
hızla öngörür, sonra son konumda durur ve dron onun 8 m gerisinde havada bekler (mod değişmez, failsafe yok).

PX4'ün kaydedicisi `follow_target`, `follow_target_estimator`, `follow_target_status` konularını ancak kendisi
başlarken varlarsa kaydeder; bu konular ilk FOLLOW_TARGET ve Follow Target moduyla doğar (gerçek araçta da). Bu yüzden
`follow_me` koşusunda kaydedici, FOLLOW_TARGET akmaya başlayınca ve kayıt penceresinden önce bir kez yeniden başlatılır
(uçuşa etkisi yok). Rapor PX4'ün hedef kestirimini gerçek konumla karşılaştırır (`px4_kestirim_hatasi_*`). Kayıt
penceresinin sayıları `ozet.json` → `olcutler`'de (`follow_target_*`, `geolocation_hatasi_*`, `konum_hatasi_*`,
`konum_hatasi_gercek_pozla_*`, `ekf_yaw_hatasi_*`, `yatay_mesafe_hatasi_ort_m`, `px4_kestirim_*`), bütün koşununki
`ozet.json` → `follow_target`'ta.

```bash
$P tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz              # model kutusundan, kapalı döngü
$P tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz --los hakem  # mükemmel algılayıcıyla
$P tez/sim/araclar/senaryo.py --senaryo kalabalik_park --ekransiz --takip follow_me --param FLW_TGT_DST=10
```

### Ölçütler, rapor ve çok koşu

Her koşunun ölçütleri `araclar/olcum.py`'de hesaplanır ve `ozet.json` → `olcutler`'e yazılır: spec "Ölçüt
Tanımları"ndaki **bütün anahtarlar her koşuda vardır**, uygulanmayan `null` olur (ör. `yok`'ta `geolocation_hatasi_*`).
Yalnız kayıt penceresi sayılır; "takip başı" ölçütleri mod seçiminden hedefin yürümeye başlamasına kadardır. Takip
için öne çıkanlar:

| Anahtar | Ne |
|---|---|
| `en_az_yatay_mesafe_m`, `yakin_mesafe_3m_suresi_s`, `yakin_mesafe_3m_olay_sayisi` | Dron–hedef yatay mesafenin en azı; 3 m'nin altında kalınan süre ve kaç kez. Her olay raporda **uyarı**dır (başarı eşiği değil; kesin eşiği m01 belirler) |
| `kadraj_yakin_sinir_m`, `kadraj_yakin_sinir_alti_s` | Kameranın (koşunun eğimiyle) yerde gördüğü en yakın nokta (35° / 9 m'de ≈ 6.6 m, 45° / 8 m'de ≈ 3.9 m) ve dronun bundan yakın kaldığı süre: o sırada kişinin ayakları kadrajın altındadır |
| `hedef_kadrajda_orani`, `ayak_kadrajda_orani` | Hakeme göre kişinin tamamı (ayak + baş) / ayakları görüntüde |
| `arkada_kalma_hatasi_{ort,p95,maks}_deg`, `arkada_kalma_hatasi_90_ustu_s` | Kişi yürürken dronun "arkasında" olmaktan sapması (0° arkasında, 90° yanında, 180° önünde); 90°'yi aştığı süre (köşede aşma) |
| `baslangic_yorunge_donusu_deg`, `yuruyus_basi_yorunge_donusu_deg` | Dronun kişi etrafında döndüğü toplam açı: kişi dururken ve yürümeye başladığı ilk 10 s |
| `px4_rota_kuzey_varsayimi_s`, `px4_rota_hatasi_*`, `px4_yorunge_donusu_*` | `follow_me`: PX4'ün kendi Follow Target görevinin iç durumu (ULog `follow_target_status`): rotayı kuzey varsaydığı süre, rota hatası, yörünge hedefinin dönüşü |
| `follow_target_titresim_baslangic_m`, `px4_kestirim_hizi_baslangic_*`, `px4_rota_degisimi_baslangic_sayisi` | `follow_me`, takip başı (kişi dururken): PX4'e giden konumun titreşimi; PX4'ün hedef kestiricisinin bundan ürettiği **sahte hız** (ULog `follow_target_estimator.vel_est`) ve 1 m/s'yi (rota güncelleme eşiği) aştığı süre; PX4'ün rotasının kaç kez değiştiği. Stok Follow Me'nin duran kişi etrafında salınmasının sebebi |
| `mesafe_{4m_alti,6m_alti,6_10m,10m_ustu}_orani` | Kaydın tamamında (videonun gösterdiği aralık: mod seçimi → son) dron–kişi mesafesinin 4 m altında, 6 m altında, 6–10 m arasında, 10 m üstünde geçen payı |
| `yakin_gecis_6m_olay_sayisi`, `yakin_gecis_<sebep>_sayisi` | Kayıtta dronun kişiye 6 m'den yakın geçtiği aralıklar ve sebepleri (`ozet.json` → `yakin_gecis.olaylar`: başlangıç/bitiş, en az mesafe, sebep, etkenler ve en az mesafe anında "8 m'den neden yakın" ayrıştırması). Sebepler: takip başı yörünge dönüşü, kilit kaybı / bayat kestirim, köşe / yön değişimi, kişi durdu ya da hızlandı, konum kayması, diğer. Rapor ve `toplu.html`'de tablo, raporda zaman çizelgesi, videoda durum satırı |
| `kose_px4_yetisme_{ort,maks}_s`, `kose_arkada_kalma_maks_deg`, `kose_<i>_*` | Kişinin yolunun köşeleri (hakemden bulunan bacak başları): PX4'ün varsaydığı rotanın yeni yöne (30° içine) yetişme süresi ve köşeden sonra dronun aşması (arkada kalma açısı hatası, > 90°) |
| `mod_korunma_orani` | İstenen modda geçen süre (ULog `vehicle_status`) |
| `ekf_yaw_hatasi_ulog_*`, `mag_sapma_olculen_deg` | EKF yaw − gerçek yaw (ULog, her örnek) ve manyetometrenin ölçtüğü alanın sapması (PX4 WMM'i +3.41°) |

Stok Follow Me'nin takip başında hedefin etrafında dönmesi ve köşede hedefi aşması **PX4'ün kendi davranışıdır**
(gerçek dronda da olur; spec "PX4 stok Follow Target davranışı"); ölçütler bunu sayıya döker.
Stok ayarlarla ne kadar düzeldiği (9.8 ön işi ve 9. grup, her ayar 3 koşu): `FLW_TGT_RS 0.3` duran kişideki salınımı
her koşuda gideriyor (sahte hız 0.53 → 0.14 m/s; 0.2 üç koşunun ikisinde gidermedi), bedeli köşelerde PX4'ün yeni yöne
0.5–1 s geç yetişmesi ve köşede daha yakın geçiş; 0.5 ve üstünde PX4 köşelere yetişemiyor. **Kullanıcı kararı (13.11):
Follow Me senaryoları (`takip_yuruyen`, `takip_yuruyen_45_10m`, `takip_yuruyen_45_8m`) `FLW_TGT_RS 0.3` ile koşar** (senaryonun
`takip.px4_parametreleri`'nde; sim seçimidir, gerçek dronun parametre dosyasında 0.1'dir ve `gercek_dron.params`
değişmedi). PX4'ün varsayılanıyla koşmak: `--param FLW_TGT_RS=0.1`. Ayrıntı:
`agent-os/specs/2026-11-10-m06-sim-ortami/implementation/gorev-grubu-09.md` (ve `-09-on-followme-ayar.md`).

Dronun kişiye neden zaman zaman 8 m'den çok yaklaştığı (9. grup): PX4 dronu kişinin kendisine değil, kestirimini kendi
süzgecinden geçirdiği bir noktaya göre koyar; kişi aniden durunca ya da dönünce bu nokta eski hızla kişiyi geçer
(stok modda en az mesafe koruması yoktur). Her koşunun `rapor.html`'inde "Yakın geçişler" tablosu bunu geçiş geçiş
paylara ayırır.

Aynı senaryoyu birkaç kez koşup dağılımını almak (m06 kararı: her senaryo 3 kez):

```bash
$P tez/sim/araclar/toplu.py --senaryo takip_yuruyen --tekrar 3                  # ~6.5 dakika, pencere yok
$P tez/sim/araclar/toplu.py --senaryo kalabalik_park --tekrar 3 -- --los hakem  # -- sonrası her koşuda senaryo.py'ye
$P tez/sim/araclar/toplu.py --ozet tez/sim/sonuclar/A tez/sim/sonuclar/B        # var olan koşuları özetle
```

Çıktı `tez/sim/sonuclar/<tarih>_<ad>_x<N>/`: her koşunun klasörü (`kosu_<i>/`, kendi `rapor.html`'iyle), `toplu.html`
(ana ölçütler: koşu koşu, ortalama, en az, en çok; nokta grafiği), `toplu.json`, `toplu.csv`. Başlayamayan bir koşu
(ör. PX4'ten heartbeat gelmedi) altyapı hatası sayılır, en çok 2 kez yeniden denenir ve "Denemeler"de listelenir.

Hazır senaryolar: `yuruyen_insan` (düz bacaklar, bekleme, koşu), `kivrimli_yuruyus` (kıvrımlı yol, yavaş yürüme,
kısa koşu, sert geri dönüş) — ikisi düz alanda — ve `kalabalik_park` (çayırda hedef + dört kişi: patikada yürüyen,
çapraz koşan, duran, hedefle aynı kıyafetli; hedef bir süre çamın arkasında kalır; dron 9 m'de bekler, hedef yolunun
her yerinde kadrajdadır). `takip_yuruyen`: `yuruyen_insan`'ın yolu 2.9 m doğuya kaydırılmış (kişi dronun 12.9 m
önünde başlar), dron **9 m'den stok Follow Me ile 12.9 m geriden** izler, kamera varsayılan 35° (takip kaynağı
`follow_me`; karar 14.11: kamera eğimi taramasında kuralın üçer koşusunda takip yolunda ve kıvrımlı yolda kapıyı
geçen tek ayar, ek koşularla 10 koşunun 9'unda; Görev Grubu 17 belgesi bölüm 18). **45° montajla karşılaştırma** (eğim dosyada yazılı, varsayılan değişse de 45°'de
kalır; yol `yuruyen_insan`'ınki): `takip_yuruyen_45_10m` (14.11'e kadarki `takip_yuruyen`, 10 m / 10 m; takip yolunda
11 koşuda 8'inde kişi izlendi, kıvrımlı yolda 0/6) ve `takip_yuruyen_45_8m` (eski adı `takip_yuruyen_8m`, 8 m / 8 m,
6–9. grupların `takip_yuruyen`'i; köşede dron kişiye 0.5–2 m yaklaşıyor). Gerçek uçuşta hangi ayarın kullanılacağı ekip
kararıdır (gerçek dronun parametre dosyasında 8/8; önerilen ayar ve ilk uçuşta doğrulama planı Görev Grubu 17
belgesinin 19. bölümünde, doğrulanmadı). Yeni senaryo yazmak için birini kopyalayın. Alanlar:

- `dunya`: `duz_alan` (tek renk düz alan, hızlı) veya `cayir` (aşağıda "Dünyalar")
- `drone.yukseklik_m`
- `takip` (varsayılan `{kaynak: yok}`; eski `drone.mod` alanı kaldırıldı):
  - `kaynak`: `yok` (dron PX4 "Hold"da bekler, açık döngü), `follow_me` (stok Follow Me, "Follow Target"; hedefin
    konumu model kutusundan, `FOLLOW_TARGET`) veya
    `tez_los` (adı `mod_adi`'de verilen harici mod; orada `mod_adi` zorunlu). Mod her zaman adıyla seçilir.
  - `los`: PX4'e `TEZ_LOS` olarak giden görüş vektörünün kaynağı: `model` (model kutusu, LOS i, varsayılan) veya
    `hakem` (doğru cevap `los_govde`, LOS ii, her kamera karesinde). Algılama kapalıyken `model` olamaz;
    `follow_me`/`tez_los` o zaman `hakem` ister.
  - `px4_baslat`: PX4 açıldıktan sonra, kalkıştan önce çalışacak PX4 komutları (liste, ör. `[tez_auto_follow start]`;
    `--px4-baslat` sona eklenir). Verilirse koşu "harici modlu"dur: sonunda `sim.log`'da "unresponsive" aranır
    ("C" bölümü)
  - `px4_parametreleri`: `{AD: sayı}`; parametre dosyalarından sonra, `--param`'dan önce yüklenir, aynı ad ve sayı
    kuralı (`MIS_TAKEOFF_ALT` yazılmaz, onu `drone.yukseklik_m` verir). Koşuda her başlangıç parametresi PX4'ten geri
    okunur; PX4 istenen değeri tutmuyorsa koşu kalkıştan önce durur.
- `algilama` (varsayılan açık): `etkin`, `model` (yol), `imgsz` (varsayılanı `.pt`'deki), `conf` (0.25), `sinif`
  (ad ya da numara; varsayılan adı `person` olan), `cekirdek` (4)
- `gecikme` (hepsi 0): `ek_ms`, `titresim_ms`, `saat_ofset_ms`, `saat_kayma_ppm`
- `kamera` (varsayılan `{egim_deg: 35}`): `egim_deg` kameranın burnun altındaki eğimi, 0–60° (komut satırında
  `--kamera-egim`). Varsayılan tek bir yerden gelir (`araclar/kamera.py` → `NOMINAL_TILT_DEG`; `models/x500_tez` de
  35°, test ikisini karşılaştırır); varsayılanla uçan senaryo bu alanı yazmaz. Başka bir eğimde koşu klasörüne modelin
  eğimli bir kopyası yazılır (`x500_tez_egim<eğim>/`, git dışında), LOS (i), düz zemin konum hesabı, kameranın yakın
  görüş sınırı ve video aynı eğimi kullanır; Gazebo'nun bildirdiği eğim koşu sonunda senaryonunkiyle karşılaştırılır
  (`ozet.json` → `ayarlar.kamera`, `kamera_montaji.egim_deg`). 14.11'den önceki koşuların hepsi 45° ile uçtu; videoları
  yeniden çizilirken eğim Gazebo'nun kaydettiği montajdan alınır (`video.run_tilt_deg`). Gerçek araçta eğim bir montaj
  parçasıdır (henüz yapılmadı).
- `kusurlar` (varsayılan `{}`, kapalı): Faz A'da kamera kusurları kapalıdır, kare modele değişmeden gider. Ayrılmış
  alanlar (`gurultu`, `bulaniklik`, `rolling_shutter`, `pozlama`) yazılırsa "Faz B'de uygulanacak" hatası verilir
- `video`: `mp4` (true), `qgc` (false)
- `hedef.baslangic: [x, y]` ve `hedef.yol`: sırayla `{nokta: [x, y], hiz_mps: v}` (v > 2 m/s koşu) veya `{dur_s: s}`
- `hedef.davranis` (isteğe bağlı): hedef **insan gibi** hareket eder (`araclar/yuruyus.py`): ilk adımda yürüme hızına
  çıkar (yürürken 2 m/s², koşarken 2.5 m/s²), köşeleri yayla döner (yarıçap v²/1.5 m/s²; 1.4 m/s'de ~1.3 m),
  135°'den keskin dönüşte ve beklemeden sonra yeni yöne kalkarken 0.3 m'lik dar bir yayda **adım atarak** döner
  (yerinde dönmez: insan modelinde dönüş animasyonu yok, yerinde dönüş süzülme gibi görünür), hızı (%5) ve çizgisi
  (~8 cm) hafifçe dalgalanır. Alanlar: `dogal` (false = eski ideal hareket), `tohum` (aynı tohum = aynı yürüyüş),
  `hiz_dalgalanma`, `yol_sapmasi_m`. Bu sınırlar yetişkinler için tipik değerlerdir; gerçek hedeflerle ölçülene kadar
  varsayımdır.
- `hedef.kiyafet` (isteğe bağlı): `{ust: renk, alt: renk, ten: ton}`; renkler `yesil` (modelin kendi kazağı), `kot`
  (kendi pantolonu), `kirmizi`, `turuncu`, `sari`, `mavi`, `lacivert`, `mor`, `beyaz`, `gri`, `siyah`, `kahverengi`,
  `bej`, `haki`; ten `acik`, `orta` (modelin kendisi), `esmer`, `koyu`. Varsayılan: yeşil kazak, kot, orta.
- `diger_insanlar` (isteğe bağlı): hedef olmayan insanlar listesi; her biri hedefle aynı alanları alır (`baslangic`,
  `yol`, `davranis`, `kiyafet`) ve `gecikme_s` (hedefin başlamasından kaç saniye sonra yola çıkar). Görüntü işleme
  için karıştırma testi: hedefle aynı kıyafeti verin.
- `zamanlama.baslama_s`: hedefin yürümeye başladığı simülasyon zamanı (dron o ana kadar hazır olmalı; ~30 s sürer)
- `basari`: eşikler — `kadrajda_kalma_min`, `gorunur_kalma_min`, `en_uzun_kayip_max_s`, `yatay_mesafe_max_m`. Boşsa
  sadece ölçülür.

Bir insanın yolu dünyadaki bir ağaç gövdesinden geçerse senaryo reddedilir (Gazebo insanları ağaçla çarpıştırmaz).

Koordinatlar Gazebo dünyasına göredir: **x doğu, y kuzey [m]**; dron (0, 0)'dan doğuya bakarak kalkar. Yanlış yazılan
bir alan, hangi alan olduğu söylenerek reddedilir.

Görüş vektörü (LOS) sütunları, ekibin "Pikselden Vektöre Dönüşüm" belgesindeki zincirle aynı eksenlerdedir
(`araclar/kamera.py`, testleri belgenin örnek sayılarını kullanır):

| Sütun | Eksenler |
|---|---|
| `los_kamera_x/y/z` | kamera optik eksenleri: x sağ, y aşağı, z ileri (görüntü işlemenin ürettiği vektör) |
| `los_govde_x/y/z` | gövde FRD: x burun, y sağ, z aşağı (kameradan hedefe, gövde eksenlerinde) |
| `los_ned_x/y/z` | NED: kuzey, doğu, aşağı |
| `sapma_yatay_deg`, `sapma_dikey_deg` | burundan sapma: sağa ve aşağı pozitif |

Görüş vektörü hedefin gövde merkezine (yerden 0.9 m) göredir. Gazebo dünya koordinatları (`dron_x`, `hedef_x`...)
ise x doğu, y kuzey, z yukarı.

**Görünürlük ve kutular:** `kadrajda` sadece geometridir (gövde merkezi görüntünün içinde mi); ağaç arkasındaki hedef
de "kadrajda" sayılır. Dronda, kameranın yanında aynı açıda yarım çözünürlüklü bir **segmentasyon kamerası** vardır
(gerçek bir algılayıcı değil, sadece hakem için; her insan ayrı etiketli). Ondan her kare için:

| Sütun | Anlam |
|---|---|
| `gorunur` | hedefin en az 40 pikseli gerçekten görünüyor (örtülü veya çok küçük değil) |
| `hedef_piksel` | hedefin görünen piksel sayısı (dron kamerası pikseli) |
| `hedef_kutu_u0/v0/u1/v1` | hedefin görüntüdeki kutusu (bbox), piksel kenarları; görünmüyorsa boş — görüntü ekibi için etiket |
| `insanN_x/y`, `insanN_u/v`, `insanN_kadrajda` | N. diğer insanın konumu, gövde merkezinin pikseli, kadrajda mı |
| `insanN_piksel`, `insanN_kutu_*` | N. diğer insanın görünen pikselleri ve kutusu |
| `kadrajdaki_diger_insan` | o karede kadrajdaki diğer insan sayısı |

Rapor bunlardan "gerçekten göründüğü süre" ve "kadrajda ama örtülü" oranlarını verir.

**Canlı hakem akışı ve Gazebo'nun büyüyen başlığı:** Gazebo 8'in segmentasyon kamerası (gz-sensors 8.2.2) her
yayımladığı karenin başlığına bir `frame_id` girdisi daha ekler ve hiç temizlemez (kare başına ≈ 51 bayt). Bu yüzden
hakemin segmentasyon karesi protobuf modülüyle değil ham baytından okunur (`kayit.read_image`: damga, boyut, pikseller;
başlık girdileri çözülmeden atlanır); `dogrulama.py` ve `onizleme.py` de öyle. Eskiden kare saf Python protobuf ile
baştan sona çözülüyordu ve ≈ 70 s kayıttan sonra hakem geride kalıyor, kilit düşünce yeniden kilit olamıyordu
(Görev Grubu 17 belgesi, bölüm 16). Her koşuda `ozet.json` → `tez_los.hakem_akisi`: hakem karesinin yakalamadan sonra
ne kadar geç hazır olduğu (`gecikme_ms_p50/p95/maks`, 100 ms'den geç kare `gec_kare`), hakemi bulamayan kilitsiz model
karesi (`hakem_yok_kare`; kayıttan önce hakem yoktur) ve bunlardan hakemin karesi sonradan gelenler
(`hakem_sonradan_gelen_kare`: hakem eksik değil geç). Sonradan gelen 5'ten fazlaysa raporda olay olarak yazılır.

### Kamera eğimi × yükseklik × mesafe taraması (`tarama.py`)

Bir takip senaryosunu kamera eğimi, yükseklik ve geride durma mesafesinin bir ızgarasında koşar (Görev Grubu 17'nin
öne alınmış hâli; sonuçlar ve karar kuralı
`agent-os/specs/2026-11-10-m06-sim-ortami/implementation/gorev-grubu-17-on-kamera-acisi.md`). Her bileşimin
senaryosu temel senaryonun yolunun doğuya kaydırılmış hâlidir (kişi dronun tam `d` önünde başlar); mesafe
`d = h / tan(eğim)` × çarpanlar ve ek mesafeler; kişinin düz uçuşta kadraja sığmadığı bileşim koşulmaz.

```bash
$P tez/sim/araclar/tarama.py plan --cikti tez/sim/sonuclar/T --egim 30 35 40 45 --yukseklik 8 10 12 15 --carpan 0.8 1 1.25 --ek-mesafe 8
$P tez/sim/araclar/tarama.py plan --cikti tez/sim/sonuclar/T --egim 30 35 40 45 --yukseklik 4 5 6 7 --ek-mesafe 8 --ekle
$P tez/sim/araclar/tarama.py kos --cikti tez/sim/sonuclar/T --asama asama1 --tekrar 1 -- --videosuz   # yarıda kalırsa aynı komut kaldığı yerden sürer
$P tez/sim/araclar/tarama.py ozet --cikti tez/sim/sonuclar/T --asama asama1                          # kapılar, puanlar, aşama 2 adayları
$P tez/sim/araclar/tarama.py kos --cikti tez/sim/sonuclar/T --asama asama2 --tekrar 3 --sadece e45_h10_d10.0 e30_h8_d13.9
$P tez/sim/araclar/tarama.py kos --cikti tez/sim/sonuclar/T --asama asama2_hakem --tekrar 3 --sadece e45_h10_d10.0 -- --los hakem
$P tez/sim/araclar/tarama.py plan --cikti tez/sim/sonuclar/T --temel kivrimli_yuruyus --egim 45 --yukseklik 10 --ekle   # aynı ayar başka yolda
$P tez/sim/araclar/tarama.py kos --cikti tez/sim/sonuclar/T --asama asama2_kivrimli --tekrar 3 --sadece kivrimli_yuruyus_e45_h10_d10.0
```

Çıktı: `T/plan.json` ve `T/senaryolar/` (bileşimlerin senaryoları), `T/<aşama>/<bileşim>/` (`toplu.py` klasörü),
`T/<aşama>/durum.json` (biten bileşimler), `T/<aşama>/ozet.csv` ve `ozet.json` (her bileşimin ölçütleri, kapıları,
grup puanları, sırası; geometrik paylar: kameranın yakın/uzak sınırı, yaklaşma payı, kişinin mesafesinde görüş
genişliği; ölçülen köşe ve duruş yaklaşması, kişinin kadrajdan hangi kenardan çıktığı).

**Sonuç (14.11):** 30–45° × 4–15 m (100 bileşim), adaylar iki yolda 3'er koşu: simin varsayılanı **35° · 9 m /
12.9 m** oldu (takip yolunda ve kıvrımlı yolun 164° geri dönüşünde kapıyı üçer koşunun hepsinde geçen tek ayar; 37.5° aynı
yükseklik ve mesafede takip yolunda eşit, kıvrımlı yolda 6 koşunun 5'inde kişiyi kaybetti; 35° 1'inde). Hiçbir 45°
ayarı geçmedi.
Gerçek uçuş için öneri ve ilk uçuşta doğrulama planı (doğrulanmadı): belgenin 19. bölümü.

### Video (`kosu.mp4`)

Her koşu kendi videosunu üretir (toplu koşular dahil; `toplu.html` her koşunun `kosu.mp4`'ünü bağlar):

```bash
vlc tez/sim/sonuclar/<klasör>/kosu.mp4 2>/dev/null
```

- **Sol (1280×720), dron kamerası:** mavi kutu hakemin hedef kutusu, turuncu diğer insanlar; kırmızı kutular o anda
  **PX4'ün elindeki** model sonucu (kalın: seçilen kutu ve güveni). Model sonucu birkaç kare eskidir, bu yüzden kişinin
  biraz gerisinde kalır: gecikme gözle görülür. Üstte sim zamanı, PX4 modu, uçtan uca gecikme ve modelin durumu;
  son giden `TEZ_LOS` "hedef yok" ise büyük kırmızı **HEDEF YOK**.
- **Sağ (720×720), kuşbakışı (kuzey yukarı):** mavi nokta kişi (ok: yürüdüğü yön), turuncu üçgen dron (sivri ucu
  burnu) ve son 10 s'lik izleri; açık mavi alan kameranın yerde gördüğü yer; kişinin çevresinde kırmızı kesikli 3 m
  halkası ve gri kesikli kameranın yakın görüş sınırı (dron bunun içine girerse kişinin ayakları kadrajdan çıkar); yeşil
  yıldız dronun olması gereken yer (yürüyen kişinin `FLW_TGT_DST` gerisi); mor noktalar son 3 s'de gönderilen
  `FOLLOW_TARGET` konumları (titreşimleri görünür); `follow_me`'de PX4'ün kendi iç durumu (ULog): dolu mor kare
  kestiricinin kişi kestirimi, içi boş mor kare görevin **süzülmüş hedefi** (dron bunun `FLW_TGT_DST` gerisine konur;
  kişi durunca ya da dönünce kişiyi metrelerce geçer: yakın geçişlerin asıl sebebi), mor ok varsaydığı rota, mor halka
  dronu şu an gönderdiği yer (PX4'ün kendi ayar noktası, `trajectory_setpoint`), mor × hedeflediği yer. Ölçek çubuğu,
  kuzey oku, dron–kişi mesafesi.
- **Altta durum satırı:** ne olduğu (takip başı / kişi yürüyor / koşuyor, mesafe, arkada kalma açısı hatası);
  **kırmızı**: **"YANLIŞ KİŞİ"** (PX4'e giden seçilen kutu hakeme göre hedefte değil başka bir kişide; aynı kıyafetli
  kişiyse "hedefle aynı kıyafetli" de yazar; `yanlis_kisi_orani` ile aynı kural, `olcum.wrong_person`), kilit kaybı,
  "hedef yok", dron 3 m ya da kameranın yakın sınırı içinde, kişi kadraj dışında; turuncu:
  dron kişinin yanında/önünde (köşede aşma); dron kişiye 6 m'den yakınken o geçişin sebebi ("6 m'den yakın geçiş:
  köşe / yön değişimi" gibi; `ozet.json` → `yakin_gecis`); yoksa PX4'ün kişinin hızı kestirimi ("≥ 1 m/s: rota
  güncellenir") ve varsaydığı rota.
- Video hakemin kaydını kapsar: dron modunu seçtiği andan senaryo sonuna (kişi dururken geçen "takip başı" da dahil).
  Kareler koşu sırasında ayrı bir süreçte yalnız diske yazılır (`goruntu_yayini.py`: 15 kare/sim-s, 1280×720 JPEG,
  `kareler/`); video koşu bittikten sonra çevrimdışı birleştirilir (`video.py`, ffmpeg: H.264, yuv420p) ve kareler
  silinir. `--kareleri-sakla` ile kalırlar; o zaman video aynı klasörden yeniden yapılabilir:
  `$P tez/sim/araclar/video.py tez/sim/sonuclar/<klasör>`.
- VLC'nin uçbirime yazdığı "Timestamp conversion failed" satırları VLC 3.0.20'nin kendisinden gelir; video sağlamdır.

### Canlı video (QGC)

Dron kamerasının görüntüsü, kutular çizili olarak QGroundControl'e canlı gider (H.264 RTP, UDP 5600; m06 Görev
grubu 11). Paketler: `tez/env/VERSIONS.md` → "Canlı video paketleri".

```bash
$P tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --qgc             # senaryo koşusu + canlı yayın (Gazebo penceresiyle)
$P tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz --qgc  # pencere yok, yayın yine gider
$P tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --qgc --videosuz  # yalnız yayın, kosu.mp4 yok
```

- **QGC 5.1.4'te:** sol üstteki QGC simgesi → **Uygulama Ayarları** (Application Settings) → **Video** →
  **Kaynak** (Video Source): **UDP h.264 Video Stream**; altında çıkan port / adres alanı **5600** olmalı (QGC'nin
  varsayılanı; yeni sürümlerde alanın adı "UDP URL", değeri `0.0.0.0:5600`). Sonra uçuş ekranına dönün (sol üstteki
  QGC simgesi → Fly); görüntü sol alttaki küçük pencerede, tıklayınca büyür. Ayar kalıcıdır.
- **QGC'siz:** `ffplay -protocol_whitelist file,udp,rtp -fflags nobuffer -flags low_delay -i tez/sim/araclar/yayin.sdp`
  (ffmpeg paketinin ffplay'i, `VERSIONS.md`) ya da
  `gst-launch-1.0 udpsrc port=5600 caps="application/x-rtp,media=video,encoding-name=H264,payload=96" ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false`.
  **VLC bu yayını açamaz:** Ubuntu'nun VLC 3.0.20 paketi live555'siz derlenmiş, SDP'den RTP alamıyor ("A description
  in SDP format is required"). UDP 5600'ü aynı anda tek bir program dinleyebilir: QGC açıkken ffplay görüntü almaz.
  Pencere açılmadan ~1 s siyah / bozuk görünebilir (ilk anahtar kare 1 s'de bir gelir).
- **Görüntüde:** üstte "CANLI · t = … s (sim)" ve modelin durumu ("model: … ms önceki kare, … kutu, hedef
  izleniyor"); **mavi kutu** hakemin hedef kutusu, **kırmızı kutular** modelin kutuları (kalın: seçilen, yanında
  güveni); PX4'e "hedef yok" gidiyorsa büyük kırmızı **HEDEF YOK**. Kutular modelin işlediği daha eski kareye aittir
  (≈ 0.1 s): kişinin biraz gerisinde kalırlar, `kosu.mp4`'teki gibi. 1 s'den eski kutu çizilmez ("kutu bilgisi eski").
- **Nasıl çalışır:** `kosu.mp4`'ün karelerini yazan süreç (`goruntu_yayini.py`) aynı kareleri yayına da verir:
  her kare bir kez okunur ve küçültülür; yayın simin başından sonuna (kalkış dahil) gider, kayıt yalnız hakemin
  kayıt penceresindedir. Model açıkken bu süreç kameraya ayrıca abone olmaz: kareleri model sürecinin zaten aldığı
  mesajlardan paylaşılan bellekle alır (ikinci bir 9 MB × 30 Hz abonelik RTF'i ≈ 0.06 düşürüyordu; modelsiz koşuda ve
  modelin kapandığı inişte kendi aboneliği). Kaydın ve yayının ölçülebilir bir RTF payı kalmadı. Ana süreç işlenen her model karesinin kutularını, seçilen kutuyu ve o karenin hakem kutusunu
  `127.0.0.1:5610`'a UDP JSON olarak gönderir. Hat: `appsrc` → `queue leaky=downstream max-size-buffers=2` →
  `videoconvert` (I420) → `x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000 key-int-max=15 threads=1`
  (constrained-baseline) → `rtph264pay config-interval=1 pt=96 mtu=1400` → `udpsink 127.0.0.1:5600`. Yayının
  defteri (gönderilen kare, hızı, kutulu kare, kutu mesajları, gecikme, sürecin CPU'su) `ozet.json` → `yayin`.
- **Tek başına (elle uçuş):** açık bir sim (`tez/sim/calistir.sh`) + QGC ile elle uçarken, ikinci bir terminalde
  `$P tez/sim/araclar/goruntu_yayini.py --qgc --model ~/auto-follow-modeller/person_detection_model_v0.2.pt`.
  Model kendi sürecinde kendi kutularını bulur; hakem kutusu, hedef seçimi ve PX4'e giden bir şey (LOS) yoktur.
  `--model` olmadan kutusuz görüntü. Durdurmak için Ctrl+C. Senaryo koşusuyla aynı anda çalıştırılmaz (UDP 5610).
- Yayının sime bedeli ve gecikmesi: `agent-os/specs/2026-11-10-m06-sim-ortami/implementation/gorev-grubu-11.md`.

Doğru cevap hakkında: Gazebo Harmonic insan (actor) konumunu yayınlamaz; hedefin konumu senaryodaki yoldan
hesaplanır. `--dogrula` bunu tepe segmentasyon kamerasıyla kontrol eder (zemin dokusu, gölge ve diğer insanlar
karışmaz; ağaç altında kalan anlar sayılmaz); yürürken gövde merkezi yolun 0.05–0.19 m önündedir. Ayrıntı:
`models/insan/KAYNAK.md`.

## Önizleme (PX4'süz)

Bir dünyaya veya senaryoya dron kamerasının gözünden bakmak için (kamera sabit, dron yerde durur):

```bash
$P tez/sim/araclar/onizleme.py --dunya cayir                                  # (0, 0, 10 m)'den varsayılan montaj açısıyla
$P tez/sim/araclar/onizleme.py --senaryo kalabalik_park --video 58:88 --etiket   # MP4 + hakemin kutuları
$P tez/sim/araclar/onizleme.py --dunya cayir --kamera 5,0,12,25,40            # x,y,z,eğim,yön (derece)
```

Çıktı `tez/sim/sonuclar/<tarih>_onizleme_<ad>/` (video H.264 MP4, VLC ile açılır; kutular `kosu.mp4`'teki gibi).

## Model (PX4'süz deneme)

Simdeki insan algılayıcı Yusuf Ortatepe'nin v0.2 modelidir (Ultralytics YOLOv8s, laptop CPU'sunda). Bir kez kurulur:

```bash
$P -m pip install -r tez/env/model-requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
mkdir -p ~/auto-follow-modeller && git -C <Vision klasörü> show ebff718:models/person_detection_model_v0.2.pt \
  > ~/auto-follow-modeller/person_detection_model_v0.2.pt     # model dosyası repoya girmez (kural 9)
sha256sum ~/auto-follow-modeller/person_detection_model_v0.2.pt   # tez/sim/modeller.yaml'daki özetle aynı olmalı
```

Modeli bir resimde ya da bir senaryonun Gazebo karelerinde denemek için (kırmızı: model, mavi/turuncu: hakem):

```bash
$P tez/sim/araclar/model_dene.py --senaryo kalabalik_park --zaman 62,66,73,78   # ~1.5 dk; kareler + *_model.jpg
$P tez/sim/araclar/model_dene.py --kare resim.jpg                              # herhangi bir PNG/JPG
```

Sürümler ve AGPL-3.0 notu: `tez/env/VERSIONS.md`. Senaryo koşusunda model kendiliğinden çalışır (yukarıda "Model
koşuda nasıl çalışır"); kapatmak için `--modelsiz`.

## Dünyalar

| Dünya | Ne |
|---|---|
| `duz_alan` | 500 m × 500 m tek renk düz çim. Hızlı; kabul testleri bunu kullanır |
| `cayir` | Gerçek fotoğraf dokulu zemin (iki tür çim, aşınmış yamalar, ağaç altında yaprak), toprak patikalar, tek ağaçlar ve ağaç kümeleri (meşe, çam; çarpışma şekilli: dron çarparsa düşer) |

Dokulu bir dünya `worlds/<ad>.yaml` ile tarif edilir, `kur.sh` (`araclar/dunya.py`) zemini ve ağaçları
`models/<ad>_cevre/`'ye üretir; `worlds/<ad>.sdf` onu `model://<ad>_cevre` ile içerir. Merkezdeki alan (varsayılan
120 m) tekrarsız ~1.2 cm/piksel dokuyla pişirilir (10 m'den kameranın yerde ayırt ettiği kadar); dışı daha basit.
Alanlar: `tohum`, `alan: {merkez, boyut_m}`, `yollar: [{noktalar, genislik_m}]`, `agaclar: [{tur: mese|cam, konum,
olcek}]`, `agac_gruplari: [{merkez, yaricap_m, sayi, turler}]`. Dosyayı değiştirince `kur.sh`'ı tekrar çalıştırın.
Varlıkların kaynağı ve lisansı (hepsi CC0): `models/dokular/KAYNAK.md`.

F1 kabul testi (senaryoyu modelsiz, `--modelsiz`, iki kez koşar, ~4 dakika; `araclar/f1_testi.py`):

```bash
tez/sim/araclar/f1_kabul.sh       # her koşuda hedef farkı ≤ 0.3 m, iki koşu aynı (≤ 0.15 m)
```

## C. Kendi PX4 modülünü takmak

Kılavuzun A (kurulum) ve B (çalıştırma) adımları yukarıdaki "Kurulum", "Çalıştırma" ve "Senaryolar" bölümlerindedir.
Bu bölüm, ağaç dışı bir PX4 modülünü (ör. m15'in takip modu) **PX4 dosyası değiştirmeden** sime takıp aynı senaryo,
ölçüt ve videoyla denemeyi anlatır (m06 Görev grubu 10; spec "Takım Arkadaşı Kılavuzu" C1–C8). Modülün,
parametrelerin ve modun adını modülü yazan kişi kendi spec'inde belirler. Ekipten gelen bilgi (09.11, Yusuf Algan;
kesinleşmiş değil, m15/m16 spec'inde kesinleşecek): mod adı **"AUTO FOLLOW"**, parametre öneki `AF_`.

1. **Modülü koy.** Kendi dalında `tez/px4/src/modules/<ad>/` altına (ya da repo dışında bir klasöre; `--harici` ile
   verilir). Örnek: eski iskelet modül `tez_auto_follow`, dalın `c4b4abf342` commit'inde (repoda değil; açmak için
   aşağıdaki "İskelet modülle deneme"). Gereken üç kural (iskelet bunlara uyar):
   - `tez/px4/src/CMakeLists.txt` modül listesini **`PARENT_SCOPE`** ile tanımlar:
     `set(config_module_list_external modules/<ad> PARENT_SCOPE)`. PX4 listeyi üst kapsamda okur
     (`CMakeLists.txt`, `add_subdirectory(<klasör>/src)`); `PARENT_SCOPE` yoksa modül sessizce derlenmez
     (`derle.sh` bunun için uyarır).
   - Modül `px4_add_module(MODULE modules__<ad> MAIN <ad> SRCS ... [MODULE_CONFIG module.yaml])` ile eklenir;
     PX4 kütüphanelerine **`DEPENDS` yazılmaz**: harici modüller PX4'ün kendi kütüphanelerinden önce yapılandırılır
     (`px4_work_queue` vb. zaten `px4` ikilisine bağlanır).
   - Ağaç içi bir modül (`src/modules/...` + `.px4board`) istiyorsan kilit listesi PR'ı gerekir; repo sorumlusuna sor.
     m06 kilit listesine yol eklemez.
2. **Modu kaydet.** Modül kendini commander'a harici mod olarak kaydeder (`mc_nn_control` ile aynı yol):
   `register_ext_component_request` (`register_mode` + `register_arming_check`; ad en çok **24 karakter**:
   `char[25] name`), sonra her `arming_check_request`'e `arming_check_reply` ile cevap verir. Commander 300 ms'de
   bir sorar, 50 ms içinde cevap bekler; art arda 3 (kayıttan hemen sonra 10) cevapsız istekte modu "unresponsive"
   sayar ve mod çalışamaz olur (`externalChecks.hpp`/`.cpp`). İskelet döngüsünü 10 ms'de bir çalıştırır. Mod QGC'nin
   listesinde ve `AVAILABLE_MODES`'ta bu adla görünür (ULog'da yalnız yuva numarası, `nav_state` 23 = "External 1";
   rapor ve video koşunun seçtiği adı yazar).
3. **Derle.** `tez/sim/derle.sh` `tez/px4/src/CMakeLists.txt`'i kendisi bulur; başka bir klasör için
   `tez/sim/derle.sh --harici <klasör>` (içinde `src/CMakeLists.txt` olan klasör, `src`'nin kendisi değil). Çıktı her
   zaman `build/px4_sitl_tez`; klasör CMake önbelleğindekinden farklıysa yeniden yapılandırılır. Bayraksız `derle.sh`
   (ve `tez/px4` yoksa) yeniden stok SITL'dir; derlemeden çıkan modülün `bin/px4-<ad>` bağlantısı silinir.
4. **Başlat.** `calistir.sh --px4-baslat "<ad> start"` (birden çok verilebilir, sırayla) ya da senaryoda
   `takip.px4_baslat: ["<ad> start"]` (`senaryo.py --px4-baslat` sona eklenir). Bu, eski airframe `.post`
   dosyasının yerini alır; PX4 dosyası gerekmez. `calistir.sh` önce komutun bu derlemede olduğunu denetler
   (`bin/px4-<ad>` yoksa sim açılmadan durur), PX4 açılınca `px4-logger status` başarılı olana kadar (en çok 90 s)
   bekler, sonra komutları `rootfs` içinde `bin/px4-<ad> <argümanlar>` ile çalıştırır; çıktıları ve çıkış kodları
   sim log'una yazılır (`PX4 başlatma komutu ...`). Başarısız bir komut kalanları durdurur ve koşu açılmaz.
5. **Girdiyi oku.** `debug_vect` uORB'una abone ol ve `name == "TEZ_LOS"` ile süz; x, y, z kameradan hedefe gövde FRD
   birim vektör, NaN = hedef yok. PX4 `debug_vect`'e `time_usec`'i taşımaz: zaman aşımını varış zamanına göre kendin
   uygula (spec "Varsayımlar"; biçim m05 ICD'ye kadar varsayım).
6. **Koştur.** Bir senaryoyu kopyala ve `takip: {kaynak: tez_los, mod_adi: "<ad>", px4_baslat: ["<ad> start"],
   px4_parametreleri: {...}}` yaz ya da komut satırından ver. Önce `--los hakem` (mükemmel algılayıcı), sonra
   `--los model`:

   ```bash
   $P tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz --takip tez_los --mod-adi "<ad>" \
       --px4-baslat "<ad> start" --los hakem
   ```

   Mod adı kalkıştan önce PX4'ün listesinde aranır (modül kaydını 10 s'ye kadar bekler); yoksa koşu PX4'ün
   modlarını listeleyerek durur. Koşu sonunda `sim.log`'da "unresponsive" aranır; bulunursa koşu "TAMAMLANMADI"
   olur (commander modu düşürmüş, ölçütler modu ölçmüyor). `ozet.json` → `harici_mod`: başlatma komutlarının çıkış
   kodları ve "unresponsive" satırları; `ayarlar.takip.px4_modlari`: PX4'ün koşudaki mod listesi.
7. **Karşılaştır.** Aynı senaryoyu `--takip follow_me` ile de koş; `ozet.json` / `rapor.html`'leri yan yana koy
   (`karsilastir.py` m06 Görev grubu 12'de gelecek).
8. **Gerçek kart.** `make px4_fmu-v6c_default EXTERNAL_MODULES_LOCATION=$PWD/tez/px4`. Flash ~%98 dolu (iskelet
   `c4b4abf342`'de +2.8 KB ölçülmüştü); taşarsa (`region FLASH overflowed`) repo sorumlusuna haber ver. Kartta
   başlatma (`etc/extras.txt`) m15/m16'nın işidir.

**İskelet modülle deneme** (mekanizmanın çalıştığını görmek için; iskelet seçildiği yerde konum tutar, hedefi
izlemez). Modül repoya konmaz, repo dışında bir klasöre açılır:

```bash
mkdir -p /tmp/iskelet && git archive c4b4abf342 tez/px4 | tar -x -C /tmp/iskelet
tez/sim/derle.sh --harici /tmp/iskelet/tez/px4
$P tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz --takip tez_los --mod-adi "Tez Auto Follow" \
    --px4-baslat "tez_auto_follow start" --los hakem
tez/sim/derle.sh            # sonra yeniden stok SITL (F0 / F1 / m06 kabul testleri stok derlemeyle koşar)
```

Elle (Gazebo penceresi + QGC): `tez/sim/derle.sh --harici ...` sonrası `tez/sim/calistir.sh --px4-baslat
"tez_auto_follow start"`; QGC'de Takeoff, sonra uçuş modu listesinden **Tez Auto Follow**. Ayrıntı ve ölçümler:
`agent-os/specs/2026-11-10-m06-sim-ortami/implementation/gorev-grubu-10.md`.

## Dosyalar

| Yol | Ne |
|---|---|
| `tez/sim/derle.sh` | Stok PX4 SITL + Gazebo eklentileri → `build/px4_sitl_tez`; `--harici <klasör>` ağaç dışı PX4 modülleriyle |
| `tez/sim/calistir.sh` | Gazebo + PX4'ü başlatır (stok 4001, başlangıç parametreleri; `--px4-baslat` PX4 açılınca komutlar) |
| `tez/sim/parametreler/gercek_dron.params`, `sim.params` | Başlangıç parametreleri (`AD DEĞER  # kaynak`); `araclar/parametreler.py` okur |
| `tez/sim/models/x500_tez/` | X500 (PX4 `x500` modeli) + gövde altında 35° Camera Module 3 (simin varsayılan montajı, `kamera.NOMINAL_TILT_DEG`; tutucu ölçüleri yaklaşık) + hakem için segmentasyon kamerası; başka bir eğim (`kamera.egim_deg`) koşu klasörüne kopyalanır, bu dosya değişmez |
| `tez/sim/worlds/duz_alan.sdf` | 500 m × 500 m düz çim alan; dron dünyanın içinde (`x500_tez_0`) |
| `tez/sim/worlds/cayir.sdf`, `cayir.yaml` | Dokulu çayır: zemin ve ağaçlar `cayir.yaml`'dan üretilir (`araclar/dunya.py`) |
| `tez/sim/server.config` | Gazebo sistemleri (PX4'ünkinin GStreamer kamerasız ve manyetometresiz hali) |
| `tez/sim/kur.sh` | Git'e girmeyen dosyaları indirir (insan modeli, dokular, ağaçlar) ve dünyaları üretir |
| `tez/sim/models/dokular/KAYNAK.md` | Zemin dokuları ve ağaçların kaynağı ve lisansı |
| `tez/sim/models/insan/` | İnsan hedef (Gazebo Fuel Mingfei/actor, CC BY 4.0; kayma düzeltmeleri ve Gazebo hatası önlemi: `KAYNAK.md`) |
| `tez/sim/senaryolar/` | Senaryo dosyaları (YAML) |
| `tez/sim/modeller.yaml` | Bilinen model dosyaları (ad, sha256, boyut, kaynak); dosyalar repo dışında, `~/auto-follow-modeller/` |
| `tez/env/model-requirements.txt` | Model paketleri (ultralytics, CPU torch/torchvision) ve bağımlılıkları, sabit sürümle |
| `tez/sim/araclar/senaryo.py` | Senaryo yöneticisi; `takip.py` (hedef seçimi, LOS i/ii, konum, takip iş parçacığı, `tez_los.csv`, `follow_target.csv`), `konumlama.py` (düz zemin konum hesabı, EKF poz geçmişi, PX4 ve Gazebo enlem/boylam dönüşümleri), `gecikme.py` (sıra koruyan gecikme hattı), `hedef.py` (yol, doğru cevap, dünya), `kayit.py` (kare kare kayıt, canlı hakem akışı), `kamera.py` (kamera modeli, eksen dönüşümleri), `dogrulama.py` (tepe kamerası), `rapor.py` (rapor: kontroller, gruplu ölçümler, grafikler), `olcum.py` (bütün ölçütler, ULog özeti), `toplu.py` (aynı senaryonun N koşusu ve dağılımı), `tarama.py` (kamera eğimi × yükseklik × mesafe taraması, karar kuralı), `simulasyon.py` (simi açar/kapatır), `parametreler.py` (başlangıç parametreleri), `px4_baglanti.py` (MAVLink: tek gönderim kilidi, `TEZ_LOS`, `FOLLOW_TARGET`, poz kancası, adla mod), `dunya.py` (dokulu dünya üretici), `onizleme.py` (PX4'süz fotoğraf/MP4), `goruntu_yayini.py` (videonun kamera karelerini koşu sırasında ayrı süreçte kaydeder; `--qgc`: QGC'ye canlı H.264 RTP, kutular UDP 5610'dan; tek başına `--qgc --model`), `yayin.sdp` (yayını QGC'siz ffplay'de açmak için), `video.py` (`kosu.mp4`: kamera + kuşbakışı, çevrimdışı), `algilama.py` (algılayıcı arayüzü, model dosyası, YOLO, model süreci, `algilama.csv`), `goruntu.py` (kare okuyucu: yalnız en yeni kare, atlanan kareler, sim ↔ duvar saati), `kusurlar.py` (kamera kusurları aşaması, Faz A'da kapalı), `model_dene.py` (modeli resimde/senaryoda dener) |
| `tez/sim/araclar/f0_kabul.sh`, `f1_kabul.sh` | Kabul testleri (`f0_testi.py`, `f1_testi.py`) |
| `tez/sim/testler/` | Donanımsız birim testleri (pytest) |

Python araçları:

```bash
P=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python
$P -m pytest tez/sim/testler                     # birim testleri, simsiz, ~1 s
$P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim   # ruff 0.16.9
```
