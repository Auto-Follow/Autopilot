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
> kuşbakışı harita). m06'nın devamı (harici modül, QGC yayını): `agent-os/specs/2026-11-10-m06-sim-ortami/`.

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
`build/px4_sitl_default` derlemesine dokunmaz. Eski bir `build/px4_sitl_tez` harici modülle yapılandırılmışsa
`derle.sh` CMake'i kendiliğinden yeniden yapılandırır.

## Çalıştırma

```bash
tez/sim/calistir.sh                          # Gazebo penceresi + bu terminalde PX4 kabuğu (pxh>)
tez/sim/calistir.sh --ekransiz               # pencere yok (otomatik testler için)
tez/sim/calistir.sh --param FLW_TGT_DST=10   # parametre dosyalarından sonra bir parametre daha (sonuncu kazanır)
```

AMD hibrit GPU'lu laptopta Gazebo penceresini açmadan önce `export DRI_PRIME=1`.

- QGroundControl'ü açın; kendiliğinden bağlanır (UDP 14550).
- Kalkış: QGC'de **Takeoff** (10 m'ye kalkar; yükseklik `MIS_TAKEOFF_ALT`).
- Kalkıştan sonra PX4 **Hold**'a geçer ve yerinde bekler. Stok **Follow Target** (Follow Me) modu da listededir.
- Kapatma: `pxh>` içinde `shutdown` veya Ctrl+C. Gazebo da kapanır.
- Her açılış temiz parametrelerle başlar (ekip standardı: testler birbirinin parametresini devralmaz).

Kamera: Camera Module 3 Standard (yatay 66°, 2304×1296, 30 fps), gövdenin altında ön kızaklardaki tutucuda
(X500 V2 "Depth Camera Mount" yeri), 45° aşağı, Gazebo konusu
`/x500_tez/kamera/image` (+ `/x500_tez/kamera/camera_info`).

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
koşu simülasyon açılmadan durur ve hangi grupta bağlanacağını söyler (ör. `video.qgc: true (--qgc): Görev grubu
11'de bağlanacak`); hiçbir ayar sessizce yok sayılmaz. Bugün bağlı olanlar: `takip.kaynak: yok`, `follow_me` ve
`tez_los` (`--mod-adi`), `takip.los: model | hakem` (`--los`), algılama (`algilama.*`, `--model`, `--imgsz`, `--conf`,
`--sinif`, `--modelsiz`), `kusurlar` (Faz A: boş), `video.mp4` / `--videosuz`, `--kareleri-sakla`,
`takip.px4_parametreleri` ve `--param`. `ozet.json` → `ayarlar.henuz_bagli_degil` 8. gruptan beri boştur.

**Mod her zaman adıyla seçilir** (`yok` → "Hold", `follow_me` → "Follow Target", `tez_los` → `takip.mod_adi` /
`--mod-adi`); numarası koda
gömülmez, koşuda PX4'ün `AVAILABLE_MODES` listesinden okunur. PX4'ün sunmadığı bir ad simülasyon açılmadan, PX4
v1.17.0'ın seçilebilir modlarını listeleyen bir hatayla reddedilir (harici bir modun adı ise PX4 açılıp modül
başladıktan sonra aranır; 10. grup). Örnek duman testi: `--takip tez_los --mod-adi "Hold"`.

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
(camera_info iç parametreleri, nominal 45° montaj) gövde FRD birim vektörüne (LOS i) çevrilir ve PX4'e
`DEBUG_VECT` adı `TEZ_LOS` olarak gönderilir: işlenen kare başına bir mesaj, `time_usec` = karenin yakalama anı,
kutu yoksa `x = y = z = NaN` (hedef yok; eski veri tekrarlanmaz). `--los hakem` ile model yerine hakemin `los_govde`'si
(LOS ii) her kamera karesinde gider ("mükemmel algılayıcı"). Gönderim kuralları: aynı kare iki kez gitmez, kareler
yalnız ileri gider, en çok bir mesaj / kamera karesi (≤ 30 Hz), sonlu olmayan ya da birim olmayan vektör gönderilmez
ve sayılır. Akış `yok` dahil her takip kaynağında vardır (algılama kapalı ve `yok` iken LOS yoktur, F1 böyle koşar);
PX4'le bağlantı kurulunca başlar, kayıt bitince kapanır. Kayıt penceresinin sayıları `ozet.json` → `olcutler`'de
(`tez_los_*`, `uctan_uca_ms_*`, `yeniden_kilit_sayisi`, `secim_dogru_orani`, `los_aci_hatasi_*_deg`, ULog'dan
`tez_los_px4_sayisi`), bütün koşununki `ozet.json` → `tez_los`'ta.

**Konum hesabı ve stok Follow Me (`follow_me`; geçici, asıl çözüm m10, biçim ortak ICD'ye kadar varsayım):** Her
işlenen karede seçilen kutunun alt ortası (ayak noktası) `kamera.py` zinciriyle (camera_info, nominal 45° montaj) ve
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
| `kadraj_yakin_sinir_m`, `kadraj_yakin_sinir_alti_s` | 45° kameranın yerde gördüğü en yakın nokta (8 m'de ≈ 3.9 m) ve dronun bundan yakın kaldığı süre: o sırada kişinin ayakları kadrajın altındadır |
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
Follow Me senaryoları (`takip_yuruyen`, `takip_yuruyen_8m`) `FLW_TGT_RS 0.3` ile koşar** (senaryonun
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
çapraz koşan, duran, hedefle aynı kıyafetli; hedef bir süre çamın arkasında kalır). `takip_yuruyen`:
`yuruyen_insan`'ın yolu, dron 10 m'den stok Follow Me ile 10 m geriden izler (takip kaynağı `follow_me`; kamera
raporunun "çim alan" ayarı; kullanıcı kararı 14.11: 9. grupta 8/8'den belirgin olarak güvenli, kişi köşeden sonra
kaybedilmedi). `takip_yuruyen_8m`: aynı yol, 8 m / 8 m (raporun stad ayarı, 6–9. grupların `takip_yuruyen`'i; köşede
dron kişiye 0.5–2 m yaklaşıyor). Gerçek uçuşta hangi ayarın kullanılacağı ekip kararıdır (gerçek dronun parametre
dosyasında 8/8). Yeni senaryo yazmak için birini kopyalayın. Alanlar:

- `dunya`: `duz_alan` (tek renk düz alan, hızlı) veya `cayir` (aşağıda "Dünyalar")
- `drone.yukseklik_m`
- `takip` (varsayılan `{kaynak: yok}`; eski `drone.mod` alanı kaldırıldı):
  - `kaynak`: `yok` (dron PX4 "Hold"da bekler, açık döngü), `follow_me` (stok Follow Me, "Follow Target"; hedefin
    konumu model kutusundan, `FOLLOW_TARGET`) veya
    `tez_los` (adı `mod_adi`'de verilen harici mod; orada `mod_adi` zorunlu). Mod her zaman adıyla seçilir.
  - `los`: PX4'e `TEZ_LOS` olarak giden görüş vektörünün kaynağı: `model` (model kutusu, LOS i, varsayılan) veya
    `hakem` (doğru cevap `los_govde`, LOS ii, her kamera karesinde). Algılama kapalıyken `model` olamaz;
    `follow_me`/`tez_los` o zaman `hakem` ister.
  - `px4_baslat`: PX4 açıldıktan sonra çalışacak komutlar (liste)
  - `px4_parametreleri`: `{AD: sayı}`; parametre dosyalarından sonra, `--param`'dan önce yüklenir, aynı ad ve sayı
    kuralı (`MIS_TAKEOFF_ALT` yazılmaz, onu `drone.yukseklik_m` verir). Koşuda her başlangıç parametresi PX4'ten geri
    okunur; PX4 istenen değeri tutmuyorsa koşu kalkıştan önce durur.
- `algilama` (varsayılan açık): `etkin`, `model` (yol), `imgsz` (varsayılanı `.pt`'deki), `conf` (0.25), `sinif`
  (ad ya da numara; varsayılan adı `person` olan), `cekirdek` (4)
- `gecikme` (hepsi 0): `ek_ms`, `titresim_ms`, `saat_ofset_ms`, `saat_kayma_ppm`
- `kamera` (varsayılan `{egim_deg: 45}`): `egim_deg` kameranın burnun altındaki eğimi, 0–60° (komut satırında
  `--kamera-egim`). Gerçek montaj ve `models/x500_tez` 45°'dir; başka bir eğimde koşu klasörüne modelin eğimli bir
  kopyası yazılır (`x500_tez_egim<eğim>/`, git dışında), LOS (i), düz zemin konum hesabı, kameranın yakın görüş
  sınırı ve video aynı eğimi kullanır; Gazebo'nun bildirdiği eğim koşu sonunda senaryonunkiyle karşılaştırılır
  (`ozet.json` → `ayarlar.kamera`, `kamera_montaji.egim_deg`). Gerçek araçta eğim bir montaj parçasıdır.
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

Doğru cevap hakkında: Gazebo Harmonic insan (actor) konumunu yayınlamaz; hedefin konumu senaryodaki yoldan
hesaplanır. `--dogrula` bunu tepe segmentasyon kamerasıyla kontrol eder (zemin dokusu, gölge ve diğer insanlar
karışmaz; ağaç altında kalan anlar sayılmaz); yürürken gövde merkezi yolun 0.05–0.19 m önündedir. Ayrıntı:
`models/insan/KAYNAK.md`.

## Önizleme (PX4'süz)

Bir dünyaya veya senaryoya dron kamerasının gözünden bakmak için (kamera sabit, dron yerde durur):

```bash
$P tez/sim/araclar/onizleme.py --dunya cayir                                  # (0, 0, 10 m)'den 45° fotoğraf
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

## Kontrol ekibi: kendi PX4 modunu takmak

Bu dalda tez PX4 modülü yok; sim stok PX4 ile çalışır. Ağaç dışı bir modülü (ör. m15 takip modu) sime takmak için
`derle.sh --harici <klasör>` ve `calistir.sh --px4-baslat "<komut>"` m06 Görev grubu 10'da gelir; adım adım kılavuz
spec'in "Takım Arkadaşı Kılavuzu" bölümündedir. Eski iskelet modül örnek olarak dalın `c4b4abf342` commit'inde
okunabilir (`tez/px4/src/...`). Modülün, parametrelerin ve modun adını modülü yazan kişi kendi spec'inde belirler.

## Dosyalar

| Yol | Ne |
|---|---|
| `tez/sim/derle.sh` | Stok PX4 SITL + Gazebo eklentileri → `build/px4_sitl_tez` |
| `tez/sim/calistir.sh` | Gazebo + PX4'ü başlatır (stok 4001, başlangıç parametreleri) |
| `tez/sim/parametreler/gercek_dron.params`, `sim.params` | Başlangıç parametreleri (`AD DEĞER  # kaynak`); `araclar/parametreler.py` okur |
| `tez/sim/models/x500_tez/` | X500 (PX4 `x500` modeli) + gövde altında 45° Camera Module 3 (tutucu ölçüleri yaklaşık) + hakem için segmentasyon kamerası; başka bir eğim (`kamera.egim_deg`) koşu klasörüne kopyalanır, bu dosya değişmez |
| `tez/sim/worlds/duz_alan.sdf` | 500 m × 500 m düz çim alan; dron dünyanın içinde (`x500_tez_0`) |
| `tez/sim/worlds/cayir.sdf`, `cayir.yaml` | Dokulu çayır: zemin ve ağaçlar `cayir.yaml`'dan üretilir (`araclar/dunya.py`) |
| `tez/sim/server.config` | Gazebo sistemleri (PX4'ünkinin GStreamer kamerasız ve manyetometresiz hali) |
| `tez/sim/kur.sh` | Git'e girmeyen dosyaları indirir (insan modeli, dokular, ağaçlar) ve dünyaları üretir |
| `tez/sim/models/dokular/KAYNAK.md` | Zemin dokuları ve ağaçların kaynağı ve lisansı |
| `tez/sim/models/insan/` | İnsan hedef (Gazebo Fuel Mingfei/actor, CC BY 4.0; kayma düzeltmeleri ve Gazebo hatası önlemi: `KAYNAK.md`) |
| `tez/sim/senaryolar/` | Senaryo dosyaları (YAML) |
| `tez/sim/modeller.yaml` | Bilinen model dosyaları (ad, sha256, boyut, kaynak); dosyalar repo dışında, `~/auto-follow-modeller/` |
| `tez/env/model-requirements.txt` | Model paketleri (ultralytics, CPU torch/torchvision) ve bağımlılıkları, sabit sürümle |
| `tez/sim/araclar/senaryo.py` | Senaryo yöneticisi; `takip.py` (hedef seçimi, LOS i/ii, konum, takip iş parçacığı, `tez_los.csv`, `follow_target.csv`), `konumlama.py` (düz zemin konum hesabı, EKF poz geçmişi, PX4 ve Gazebo enlem/boylam dönüşümleri), `gecikme.py` (sıra koruyan gecikme hattı), `hedef.py` (yol, doğru cevap, dünya), `kayit.py` (kare kare kayıt, canlı hakem akışı), `kamera.py` (kamera modeli, eksen dönüşümleri), `dogrulama.py` (tepe kamerası), `rapor.py` (rapor: kontroller, gruplu ölçümler, grafikler), `olcum.py` (bütün ölçütler, ULog özeti), `toplu.py` (aynı senaryonun N koşusu ve dağılımı), `tarama.py` (kamera eğimi × yükseklik × mesafe taraması, karar kuralı), `simulasyon.py` (simi açar/kapatır), `parametreler.py` (başlangıç parametreleri), `px4_baglanti.py` (MAVLink: tek gönderim kilidi, `TEZ_LOS`, `FOLLOW_TARGET`, poz kancası, adla mod), `dunya.py` (dokulu dünya üretici), `onizleme.py` (PX4'süz fotoğraf/MP4), `goruntu_yayini.py` (videonun kamera karelerini koşu sırasında ayrı süreçte kaydeder), `video.py` (`kosu.mp4`: kamera + kuşbakışı, çevrimdışı), `algilama.py` (algılayıcı arayüzü, model dosyası, YOLO, model süreci, `algilama.csv`), `goruntu.py` (kare okuyucu: yalnız en yeni kare, atlanan kareler, sim ↔ duvar saati), `kusurlar.py` (kamera kusurları aşaması, Faz A'da kapalı), `model_dene.py` (modeli resimde/senaryoda dener) |
| `tez/sim/araclar/f0_kabul.sh`, `f1_kabul.sh` | Kabul testleri (`f0_testi.py`, `f1_testi.py`) |
| `tez/sim/testler/` | Donanımsız birim testleri (pytest) |

Python araçları:

```bash
P=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python
$P -m pytest tez/sim/testler                     # birim testleri, simsiz, ~1 s
$P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim   # ruff 0.16.9
```
