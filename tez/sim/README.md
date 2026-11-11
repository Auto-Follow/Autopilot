# Auto-Follow simülasyon ortamı (`tez/sim`)

Görüntü işleme (Vision) ve kontrol (PX4 içindeki tez modu) ekiplerinin kodlarını gerçek uçuştan önce Gazebo'da
**ölçerek** denemesi için ortak ortam. Tasarım: "Auto-Follow Simülasyon ve Test Ortamı — Tasarım Önerisi" belgesi.

> **Durum: F1 (hakem çekirdeği) + gerçekçi dünya, m06 Görev grupları 1–4.** Tez dronu + düz alan ve dokulu
> çayır (patika, ağaçlar) + stok PX4 (airframe 4001, gerçek dronun ayarlarıyla) + insan gibi yürüyen hedef ve başka
> insanlar, YAML senaryo, kare kare doğru cevap (görünürlük ve kutu dahil), dron kamerasında koşan insan algılama
> modeli (v0.2, CPU; `algilama.csv`), ULog ve otomatik HTML rapor.
> m06'nın devamı (`TEZ_LOS`, Follow Me, MP4): `agent-os/specs/2026-11-10-m06-sim-ortami/`.

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
koşu simülasyon açılmadan durur ve hangi grupta bağlanacağını söyler (ör. `takip.kaynak: follow_me (--takip): Görev
grubu 6'da bağlanacak`); hiçbir ayar sessizce yok sayılmaz. Bugün bağlı olanlar: `takip.kaynak: yok`, algılama
(`algilama.*`, `--model`, `--imgsz`, `--conf`, `--sinif`, `--modelsiz`), `kusurlar` (Faz A: boş), `--videosuz`,
`takip.px4_parametreleri` ve `--param`. Varsayılanı henüz etkin olmayan ayarlar (TEZ_LOS, MP4) `ozet.json` →
`ayarlar.henuz_bagli_degil`'de listelenir.

Senaryo yöneticisi model dosyasını (sha256) kontrol eder ve modeli kendi sürecinde yükler, dünyayı (temel dünya +
hedef) yazar, Gazebo ve PX4'ü açar, dronu kaldırır ve takip kaynağının moduna alır, hedef yürürken doğru cevabı
kaydeder, kayıt bitince modeli kapatır, iner, kapatır ve raporu yazar. Çıktı `tez/sim/sonuclar/<tarih>_<ad>/`
(git'e girmez):

| Dosya | İçerik |
|---|---|
| `rapor.html` | Sonuç (GEÇTİ / KALDI / TAMAMLANMADI), ölçütler, üstten harita, mesafe ve kamera görüntüsü grafikleri |
| `dogru_cevap.csv` | **Dron kamerasının her karesi için bir satır** (~30 Hz, karenin sim zamanıyla): dron konumu ve duruşu (roll/pitch/yaw, PX4 yönleriyle), kamera konumu, hedef konumu/hızı, hedefin o karedeki pikseli (ayak, merkez, baş) ve kadrajda olup olmadığı, kameradan hedefe menzil ve **doğru görüş vektörü** (aşağıda) |
| `ozet.json` | Ölçütler ve sonuç (makineyle okunur); `ayarlar`: koşunun geçerli ayarları (senaryo + komut satırı) ve her başlangıç parametresinin istenen değeri, kaynağı ve PX4'ten geri okunan değeri; kameranın kalibrasyonu ve gövdeye montajı (ofset, C_cb) |
| `algilama.csv` | **Modelin işlediği her kare için bir satır**: `t_us` (= `round(t*1e6)`, `dogru_cevap.csv` ile birleştirme anahtarı), `t` (yakalama, sim s), `sira`, `onceki_atlanan`, duvar saatinde `varis`/`basla`/`bitis`/`alinma` ve sim saniyesinde `*_sim`, `ulasma_ms`, `bekleme_ms`, `cozme_ms`, `kusur_ms`, `model_ms`, `islem_ms`, `teslim_ms`, `kutu_sayisi`. LibreOffice Calc'ta açılır |
| `kutular.csv` | Modelin bulduğu bütün kutular (`t_us`, `t`, `sira`, sıra no, `u0 v0 u1 v1` piksel kenarı, `guven`, `sinif`) |
| `ucus.ulg` | PX4 uçuş kaydı (PlotJuggler / pyulog) |
| `dunya.sdf`, `senaryo.yaml`, `sim.log` | Koşunun girdileri ve logu |

**Model koşuda nasıl çalışır:** Model ayrı bir süreçtedir (`algilama.ModelProcess`) ve Gazebo kare yayınlamaya
başladığı andan kayıt bitene kadar kamerayı okur. Sim gerçek zamanda akar, Gazebo modeli beklemez: model meşgulken
gelen kare bekleyen karenin yerine geçer ve `atlanan` sayılır; model boşalınca yalnız en yeni kareyi alır, kuyruk
büyümez. `ozet.json`'da `kare_defteri` (gelen = işlenen + atlanan + bekleyen) ve `olcutler`'de kayıt penceresinin
sayıları (`uretilen`, `islenen`, `atlanan_kare_orani`, `islenen_kare_hizi_hz`, `model_ms_*`, `ulasma_ms_*`,
`bekleme_ms_ort`, `rtf_ort`, geçici IoU kontrolü `iou05_kare_sayisi`) yazılır. RTF 0.9'un altına düşerse olaylarda
uyarı çıkar. `--modelsiz` ile model süreci hiç açılmaz (F1 böyle koşar).

Hazır senaryolar: `yuruyen_insan` (düz bacaklar, bekleme, koşu), `kivrimli_yuruyus` (kıvrımlı yol, yavaş yürüme,
kısa koşu, sert geri dönüş) — ikisi düz alanda — ve `kalabalik_park` (çayırda hedef + dört kişi: patikada yürüyen,
çapraz koşan, duran, hedefle aynı kıyafetli; hedef bir süre çamın arkasında kalır). `takip_yuruyen`:
`yuruyen_insan`'ın yolu, dron 8 m'den stok Follow Me ile 8 m geriden izler (takip kaynağı `follow_me`, m06'nın 6.
görev grubunda bağlanır). Yeni senaryo yazmak için birini kopyalayın. Alanlar:

- `dunya`: `duz_alan` (tek renk düz alan, hızlı) veya `cayir` (aşağıda "Dünyalar")
- `drone.yukseklik_m`
- `takip` (varsayılan `{kaynak: yok}`; eski `drone.mod` alanı kaldırıldı):
  - `kaynak`: `yok` (dron PX4 "Hold"da bekler, açık döngü), `follow_me` (stok Follow Me, "Follow Target") veya
    `tez_los` (adı `mod_adi`'de verilen harici mod; orada `mod_adi` zorunlu). Mod her zaman adıyla seçilir.
  - `los`: PX4'e `TEZ_LOS` olarak giden görüş vektörünün kaynağı: `model` (model kutusu, varsayılan) veya `hakem`
    (doğru cevap). Algılama kapalıyken `model` olamaz; `follow_me`/`tez_los` o zaman `hakem` ister.
  - `px4_baslat`: PX4 açıldıktan sonra çalışacak komutlar (liste)
  - `px4_parametreleri`: `{AD: sayı}`; parametre dosyalarından sonra, `--param`'dan önce yüklenir, aynı ad ve sayı
    kuralı (`MIS_TAKEOFF_ALT` yazılmaz, onu `drone.yukseklik_m` verir). Koşuda her başlangıç parametresi PX4'ten geri
    okunur; PX4 istenen değeri tutmuyorsa koşu kalkıştan önce durur.
- `algilama` (varsayılan açık): `etkin`, `model` (yol), `imgsz` (varsayılanı `.pt`'deki), `conf` (0.25), `sinif`
  (ad ya da numara; varsayılan adı `person` olan), `cekirdek` (4)
- `gecikme` (hepsi 0): `ek_ms`, `titresim_ms`, `saat_ofset_ms`, `saat_kayma_ppm`
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

Doğru cevap hakkında: Gazebo Harmonic insan (actor) konumunu yayınlamaz; hedefin konumu senaryodaki yoldan
hesaplanır. `--dogrula` bunu tepe segmentasyon kamerasıyla kontrol eder (zemin dokusu, gölge ve diğer insanlar
karışmaz; ağaç altında kalan anlar sayılmaz); yürürken gövde merkezi yolun 0.05–0.19 m önündedir. Ayrıntı:
`models/insan/KAYNAK.md`.

## Önizleme (PX4'süz)

Bir dünyaya veya senaryoya dron kamerasının gözünden bakmak için (kamera sabit, dron yerde durur):

```bash
$P tez/sim/araclar/onizleme.py --dunya cayir                                  # (0, 0, 10 m)'den 45° fotoğraf
$P tez/sim/araclar/onizleme.py --senaryo kalabalik_park --video 58:88 --etiket   # WebM + hakemin kutuları
$P tez/sim/araclar/onizleme.py --dunya cayir --kamera 5,0,12,25,40            # x,y,z,eğim,yön (derece)
```

Çıktı `tez/sim/sonuclar/<tarih>_onizleme_<ad>/` (videoyu Firefox ile açın).

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
| `tez/sim/models/x500_tez/` | X500 (PX4 `x500` modeli) + gövde altında 45° Camera Module 3 (tutucu ölçüleri yaklaşık) + hakem için segmentasyon kamerası |
| `tez/sim/worlds/duz_alan.sdf` | 500 m × 500 m düz çim alan; dron dünyanın içinde (`x500_tez_0`) |
| `tez/sim/worlds/cayir.sdf`, `cayir.yaml` | Dokulu çayır: zemin ve ağaçlar `cayir.yaml`'dan üretilir (`araclar/dunya.py`) |
| `tez/sim/server.config` | Gazebo sistemleri (PX4'ünkinin GStreamer kamerasız hali) |
| `tez/sim/kur.sh` | Git'e girmeyen dosyaları indirir (insan modeli, dokular, ağaçlar) ve dünyaları üretir |
| `tez/sim/models/dokular/KAYNAK.md` | Zemin dokuları ve ağaçların kaynağı ve lisansı |
| `tez/sim/models/insan/` | İnsan hedef (Gazebo Fuel Mingfei/actor, CC BY 4.0; kayma düzeltmeleri ve Gazebo hatası önlemi: `KAYNAK.md`) |
| `tez/sim/senaryolar/` | Senaryo dosyaları (YAML) |
| `tez/sim/modeller.yaml` | Bilinen model dosyaları (ad, sha256, boyut, kaynak); dosyalar repo dışında, `~/auto-follow-modeller/` |
| `tez/env/model-requirements.txt` | Model paketleri (ultralytics, CPU torch/torchvision) ve bağımlılıkları, sabit sürümle |
| `tez/sim/araclar/senaryo.py` | Senaryo yöneticisi; `hedef.py` (yol, doğru cevap, dünya), `kayit.py` (kare kare kayıt), `kamera.py` (kamera modeli, eksen dönüşümleri), `dogrulama.py` (tepe kamerası), `rapor.py` (rapor), `simulasyon.py` (simi açar/kapatır), `parametreler.py` (başlangıç parametreleri), `px4_baglanti.py` (MAVLink), `dunya.py` (dokulu dünya üretici), `onizleme.py` (PX4'süz fotoğraf/video), `algilama.py` (algılayıcı arayüzü, model dosyası, YOLO, model süreci, `algilama.csv`), `goruntu.py` (kare okuyucu: yalnız en yeni kare, atlanan kareler, sim ↔ duvar saati), `kusurlar.py` (kamera kusurları aşaması, Faz A'da kapalı), `model_dene.py` (modeli resimde/senaryoda dener) |
| `tez/sim/araclar/f0_kabul.sh`, `f1_kabul.sh` | Kabul testleri (`f0_testi.py`, `f1_testi.py`) |
| `tez/sim/testler/` | Donanımsız birim testleri (pytest) |

Python araçları:

```bash
P=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python
$P -m pytest tez/sim/testler                     # birim testleri, simsiz, ~1 s
$P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim   # ruff 0.16.9
```
