# Spesifikasyon: m06 Simülasyon Ortamı

- Yol haritası maddesi: **m06** (madde 6: simülasyon kamera ve hareketli insan hedefi kurulumu) · issue Auto-Follow/Auto-Follow#7 (son teslim 15.11.2026)
- Dal `ozellik/m06-sim-ortami` · PR başlığı `[M06] Simülasyon ortamı` · gereksinimler: `planning/requirements.md`
- Tek spec, iki faz: **Faz A** 15.11'e kadar ilk PR (bu belgenin "Özel Gereksinimler" bölümünün tamamı), **Faz B** 15.11'den sonra aynı spec'e bağlı ikinci PR ("Faz B" bölümü).

## Amaç

`tez/sim` üzerindeki F0/F1 çalışmasının üstüne, el çizimindeki **Gazebo kamera → model → PX4 → simülasyon** döngüsünü kapatmak. Camera Module 3 benzeri kamera görüntüsü laptopta okunur. Yusuf Ortatepe'nin modeli CPU'da bu görüntüde çalışır. Geçici bir Model → PX4 okuyla (`TEZ_LOS` / `FOLLOW_TARGET`, bkz. "Varsayımlar") stok Follow Me ile ya da takılan bir harici modla takip yapılır. Her koşu aynı ölçütleri ve VLC'de açılan bir MP4 üretir. PX4 dosyalarına dokunulmaz.

## Kullanıcı Hikâyeleri

- Kontrol ekibinden biri (Yusuf Kurt, m15) olarak kendi PX4 takip modumu sime takıp aynı senaryo, aynı ölçütler ve aynı videoyla stok Follow Me'yle karşılaştırmak istiyorum; böylece modumu gerçek uçuştan önce ölçerek geliştirebilirim.
- Görüntü ekibinden biri (Yusuf Ortatepe) olarak modelimin Gazebo kamera görüntüsünde ne kadar iyi ve ne kadar hızlı çalıştığını (IoU, kaçırma, yanlış kişi, gecikme) hakeme göre ölçmek istiyorum; böylece m08'deki asıl çalışma için bir başlangıç noktam olur.
- Takım üyelerinden biri olarak repoyu klonlayıp birkaç betikle simi kendi bilgisayarımda ayağa kaldırmak ve sonucu VLC'de video olarak izlemek istiyorum; böylece kurulumla uğraşmadan test yapabilirim.

## Özel Gereksinimler

**1. PX4 tarafı: (b) yolu, yani stok 4001 + gerçek dron ayarları (PX4 dosyası değişmez)**
- ROMFS'teki 3 dosya v1.17.0 hâline döner (`4030_gz_x500_tez`, `4030_gz_x500_tez.post`, `airframes/CMakeLists.txt`). İskelet "Tez Auto Follow" modülü (`tez/px4/`) daldan çıkarılır. `tez/pin/verify_pin.sh --worktree` "KILIT SAGLAM" vermelidir; bugün bu dalda bu 3 dosya yüzünden "KILIT BOZULMUS" veriyor.
- `calistir.sh` PX4'ü şu ortam değişkenleriyle başlatır:
  - `PX4_SYS_AUTOSTART=4001`: stok `4001_gz_x500` airframe'i seçilir (rcS satır 41–44).
  - `PX4_GZ_MODEL_NAME=x500_tez_0`: PX4 dünyadaki drona bağlanır (`px4-rc.gzsim` 184–190).
  - `PX4_GZ_WORLD=<dünya>` ve `PX4_SIM_MODEL=x500_tez`: ikincisi yalnız bilgi amaçlıdır.
  - Not: Yalnız `PX4_SIM_MODEL=x500_tez` vermek yetmez. rcS bu durumda `<no>_x500_tez` adlı bir airframe dosyası arar ve "Unknown model" diyerek çıkar.
- **Parametre yükleme yöntemi:** v1.17.0 posix rcS'teki `PX4_PARAM_<AD>=<değer>` ortam değişkeni döngüsü kullanılır (rcS 129–136).
  - Döngü `param reset_all`'dan sonra, airframe dosyasından önce `param set` yapar. `param set` değeri kullanıcı katmanına yazar, `param set-default` yalnız varsayılanı değiştirir; bu yüzden airframe'in `param set-default` satırları bu değerleri ezmez.
  - İstisna (uygulamada bulundu, `param.cpp` `do_set`): `param set`, değer o anki değere eşitse hiçbir şey yazmaz. Varsayılana eşit bir değer kullanıcı katmanına girmez ve sonradan bir `set-default` satırı onu değiştirebilir (ör. `--param MPC_THR_HOVER=0.5` → 4001'in `0.60`'ı kazanır). Bu yüzden F0 her değeri PX4'ten geri okur; bugünkü dosyalarda 15/15 aynıdır.
  - Her açılışta `parameters*.bson` silinir; koşular birbirinin parametresini devralmaz. Çağıranın kabuğundan gelen `PX4_PARAM_*` değişkenleri `calistir.sh` tarafından silinir; tek yol `--param`'dır.
- **Elenen yollar ve nedenleri:**
  - Açılıştan sonra MAVLink `PARAM_SET`: kalkışla yarışır; bazı ayarlar modül başlarken okunur.
  - `px4 -s <betik>`: rcS'in kopyalanmasını ve veri klasörünün elle verilmesini gerektirir.
  - PATH üzerinden `px4-rc.*` dosyalarını gölgelemek: kırılgandır.
  - Hazır bir `parameters.bson`: ikili dosyadır ve derlemeye bağlıdır.
- **Parametre dosyaları:**
  - `tez/sim/parametreler/gercek_dron.params`: 4019 kazançları ve 22.08 dosyasından davranış parametreleri.
  - `tez/sim/parametreler/sim.params`: yalnız sim için. `SDLOG_PROFILE 163` sayesinde `debug_vect` ULog'a girer.
  - Biçim: her satırda `AD DEĞER  # kaynak`. Ad `^[A-Z0-9_]{1,16}$` kuralına uymalı, değer sayı olmalıdır (`nan`/`inf` değil). Kaynak yorumu zorunludur; aynı dosyada aynı ad iki kez yazılamaz. Hatalı satır, dosya adı, satır numarası ve adıyla reddedilir ve sim hiç açılmaz.
  - Ayrıştırıcı: `araclar/parametreler.py` (`calistir.sh` onu `TEZ_PYTHON` ya da ekip venv'iyle çağırır ve yazdığı `PX4_PARAM_*` satırlarını dışa aktarır).
- **Yükleme sırası** (aynı parametre birden fazla yerde varsa sonuncu kazanır): `gercek_dron.params` → `sim.params` → senaryodaki `takip.px4_parametreleri` → `--param AD=DEĞER`.
- **Seçim kuralı:**
  - Dahil: `MC_*`, `IMU_*_CUTOFF`, `MPC_*`, `FLW_TGT_*`, `EKF2_HGT_REF`, `EKF2_MAG_TYPE`.
  - Hariç: `CA_*` geometri (22.08'deki ±1 değerleri sim modeline uymaz), `MPC_THR_HOVER` (model fiziğine bağlı), `CAL_*`, `RC*`, `BAT*`, `SENS_*`, `MAV_*`, `SER_*`, failsafe ayarları, `MIS_TAKEOFF_ALT` (bunu senaryo verir).
  - Uygulamada 22.08 dosyası v1.17.0 varsayılanlarıyla betikle karşılaştırılır. Tablo "Faz A Dosya Planı"ndadır; karşılaştırmanın tamamı `implementation/gorev-grubu-01.md`'dedir.
- F0 kabul testi stok modlara ve parametre doğrulamasına uyarlanır (bkz. "Test Planı"). `tez/sim/README.md` (b) yoluna göre yeniden yazılır. Hüseyin'in onayı bekleniyor.

**2. Kare okuyucu ve kamera kusurları aşaması**
- `araclar/goruntu.py` `/x500_tez/kamera/image` konusuna `subscribe_raw` ile abone olur.
  - Geri çağırma yalnız ham baytı, varış anını (`time.monotonic`) ve sayacı saklar.
  - Protobuf yalnız işlenecek karede çözülür. 9 MB'lık bir kareyi saf Python protobuf ile çözmek ~14 ms sürer.
- Kare nesnesi şunları taşır:
  - RGB `uint8` dizi (1296×2304×3).
  - `t`: Gazebo başlık damgası. Bu sim zamanıdır ve SITL lockstep'te PX4 zamanıyla aynıdır.
  - `varis`: duvar saatiyle varış anı.
  - `sira`: kare sayacı.
- Okuyucu yalnız en yeni kareyi tutar. Model meşgulken gelen kare bir öncekinin üstüne yazılır ve `atlanan` olarak sayılır. Kuyruk büyümez, eski kare işlenmez.
- Sim gerçek zamanda akar. Gazebo Python'u beklemez; model yavaşsa sim yavaşlamaz, kareler atlanır.
- Gecikme ölçümü için sim saati ile duvar saati eşlenir. Eşleme `/world/<dünya>/clock` konusundan tutulur (abonelik ~100 Hz'e kısılır).
- `araclar/kusurlar.py` görüntü ile model arasında bir aşamadır: `KameraKusurlari.uygula(kare, t) -> kare`. Senaryonun `kusurlar:` alanından ayarlanır.
  - Faz A'da alan boştur, yani kusurlar kapalıdır ve kare bit bit değişmeden geçer.
  - Faz B alan adları ayrılmıştır: `gurultu`, `bulaniklik`, `rolling_shutter`, `pozlama`. Faz A'da biri açılırsa "Faz B'de uygulanacak" hatası verilir.
- Aşamanın süresi (`kusur_ms`) her karede loglanır. Faz B'de aynı kusurlar, aynı tohumla video karelerine de uygulanır.

**3. Model arayüzü ve v0.2'nin laptop CPU'sunda çalışması**
- Arayüz `araclar/algilama.py` içindedir: `Algilayici.algila(kare_rgb) -> list[Kutu]`.
  - `Kutu` alanları: `u0, v0, u1, v1, guven, sinif, sinif_adi`.
  - Kutular tam çözünürlükte, piksel kenarı olarak verilir (`u0 ≤ u < u1`), hakem kutularıyla aynı kural.
  - Vision'ın m08/m10 kodu bu arayüze uyan yeni bir sınıf olarak takılır. `../Vision` yoluna bağlanılmaz (kural 7).
- `YoloAlgilayici`:
  - Ultralytics'i `device=cpu` ile çalıştırır.
  - `torch.set_num_threads(cekirdek)` uygulanır. Varsayılan 4'tür; Gazebo ve PX4'e CPU kalsın diye.
  - Yalnız verilen dosyayı yükler. Otomatik model ve yazı tipi indirme ile analitik kapalıdır.
  - `ultralytics` modülü yalnız bu sınıf içinde içe aktarılır. Böylece birim testleri torch olmadan çalışır.
- Model dosyasının yolu şu öncelik sırasıyla belirlenir:
  1. `--model <yol>`
  2. Senaryodaki `algilama.model`
  3. `~/auto-follow-modeller/person_detection_model_v0.2.pt`

  Dosya yoksa sim açılmadan hata verilir ve dosyanın nereden alınacağı söylenir.
- Sınıf, imgsz ve conf:
  - Sınıf adları `.pt` içindeki `names` alanından okunur. Varsayılan sınıf, adı büyük/küçük harf ayırmadan `person` olandır (v0.2'de `{0: 'Person'}`, COCO'da `0: person`).
  - `--sinif ad|no` ile başka bir sınıf seçilebilir.
  - `--imgsz`: varsayılanı `.pt` içindeki eğitim değeridir.
  - `--conf`: varsayılanı 0.25'tir.
- Dosyanın sha256 özeti her koşuda hesaplanır ve `ozet.json`'a yazılır.
  - Özet, `tez/sim/modeller.yaml` içindeki bilinen özetle karşılaştırılır; farklıysa uyarı verilir.
  - v0.2 bilgileri "Belgeler > Model dosyası" bölümündedir.
  - Kıyas için stok COCO `yolov8s.pt` aynı klasöre elle konur ve `--model` ile seçilir. Onun sha256 özeti uygulamada yazılır.
- Model ayrı bir süreçte çalışır (`multiprocessing`, "spawn" başlatma).
  - Amaç: GIL çekişmesinden ve gz-transport'un fork sonrası sorunlarından kaçınmak.
  - Sonuçlar ana sürece FIFO kuyrukla gelir.
  - `--modelsiz` ya da `algilama.etkin: false` verilirse model süreci hiç başlatılmaz (F1 testi bunu kullanır).
- Kare başına `model_ms` (ön işleme + çıkarım + son işleme) loglanır.
- Lisans: Ultralytics AGPL-3.0'dır. Model yalnız yerel simde çalıştırılır, dağıtılmaz.

**4. Gecikme zinciri, kare atlama ve zaman ölçümü**
- İşlenen her kare için şu zaman damgaları tutulur:
  - `t`: yakalama anı (sim zamanı).
  - `varis`, `basla`, `bitis`, `serbest` (gecikme hattından çıkış), `gonderim`: duvar saati (`monotonic`).

  Duvar zamanları saat eşlemesiyle sim saniyesine de çevrilir.
- Bunlardan türetilenler:
  - `ulasma_ms` = varış − yakalama.
  - `bekleme_ms` = başlama − varış.
  - `model_ms`.
  - `ek_gecikme_ms`: yapay gecikme.
  - `uctan_uca_ms` = gönderim − yakalama, sim milisaniyesi olarak.
- Kare atlama iki sayaçla ölçülür: üretilen kare sayısı (`uretilen`, kamera karesi) ve işlenen kare sayısı (`islenen`).
  - `atlanan_kare_orani = 1 − islenen/uretilen`.
  - `islenen_kare_hizi_hz`: sim saniyesi başına işlenen kare.
- `araclar/gecikme.py`, yakalama → PX4 yoluna yapay bir gecikme hattı ekler: `ek_ms` + `titresim_ms` (düzgün dağılımlı, tohumlu). Sıra korunur; bir mesaj kendinden önceki mesajdan önce çıkmaz.
- Saat modeli: gönderilen `time_usec = t_kare + saat_ofset_ms + saat_kayma_ppm × geçen süre`.
  - PX4 v1.17.0 bu alanı `DEBUG_VECT` ve `FOLLOW_TARGET` için kullanmaz; uORB damgası mesajın varış anıdır.
  - Bu yüzden saat kaymasının stok PX4 tüketicileri üzerinde etkisi yoktur. Ortak ICD zaman damgalı bir mesaj seçerse anlam kazanır (bkz. "Varsayımlar").
- Gerçek zaman oranı (RTF) koşu boyunca ölçülür. 0.9'un altına düşerse raporda uyarı çıkar; model CPU'yu Gazebo'dan alıyor olabilir.
- Faz A varsayılanları: yapay gecikme ve saat ayarlarının hepsi 0'dır; yalnız doğal gecikme ölçülür.

**5. İki LOS kaynağı, hedef seçimi ve `TEZ_LOS` gönderimi**
- LOS kaynağı (i), `model`:
  1. Seçilen kutunun merkezi alınır.
  2. `kamera.Camera.pixel_to_los` ile optik eksenlerde yön bulunur. İç parametreler `camera_info`'dan gelir; bozulma da hesaba katılır.
  3. `kamera.camera_to_body(45°)` ile gövde FRD'ye çevrilir.

  Sonuç gövde FRD'de bir birim vektördür: kameradan hedefe, montaj açısı eklenmiş.
- LOS kaynağı (ii), `hakem`: o karenin `los_govde` değeri (`kayit.py`). Yalnız hedef `gorunur` iken ve her kamera karesinde (30 Hz) kullanılır. Hakemin canlı satırı, segmentasyon karesi geldikten sonra kullanılır; bundan doğan ek gecikme de ölçülür.
- Hedef seçimi geçicidir; m11'de asıl çözüm gelir.
  - İlk kilit: hedefin hakem kutusuyla IoU'su en yüksek kutu seçilir. Bu, operatörün hedefi seçmesinin yerini tutar.
  - Sonraki karelerde, merkezi önceki seçime en yakın kutu seçilir. Merkezler arası mesafe en fazla önceki kutunun köşegeninin 1.5 katı olabilir.
  - Kilit kaybı: 10 işlenen kare boyunca eşleşme olmazsa kilit düşer ve hakemle yeniden kilitlenilir. Bu sayılır (`yeniden_kilit_sayisi`).
- Mesaj `DEBUG_VECT` olarak gönderilir:
  - `name="TEZ_LOS"`.
  - `x, y, z`: birim LOS, gövde FRD.
  - `time_usec`: yakalama anı, saat modelinden geçirilmiş.

  İşlenen her kare için bir mesaj gider, en çok 30 Hz. Aynı kare iki kez gönderilmez.
- "Hedef yok": hedef seçilemeyen işlenmiş karede aynı yoldan `x=y=z=NaN` gönderilir. Eski veri tekrarlanmaz (hata yönetimi standardı).
- Göndermeden önce doğrulama yapılır: değerler sonlu olmalı ve `|norm − 1| < 1e-3` sağlanmalıdır. Bu sağlanmazsa mesaj gönderilmez ve sayılır (iki taraflı doğrulama).
- `TEZ_LOS` her takip kaynağında gönderilir, `yok` dahil. Böylece veri akışı her zaman vardır ve ULog'a girer.

**6. Takip kaynağı / kontrolcü seçimi (birinci sınıf gereksinim)**
- Takip kaynağı senaryoda `takip.kaynak`, komut satırında `--takip` ile seçilir: `yok`, `follow_me` ya da `tez_los`. Dron `drone.yukseklik_m`'ye kalktıktan sonra mod adıyla seçilir:

  | Takip kaynağı | Seçilen PX4 modu |
  |---|---|
  | `yok` | "Hold" |
  | `follow_me` | "Follow Target" |
  | `tez_los` | `takip.mod_adi` / `--mod-adi` |

  Mod adları PX4'ün `AVAILABLE_MODES` listesinden çözülür (`px4_baglanti.Vehicle.modes`). Ad listede yoksa koşu başlamadan, mevcut adları listeleyen bir hata verilir.
- `follow_me` için `araclar/konumlama.py` kutunun alt ortasını (ayak noktası) düz zemine izdüşürür.
  - Kare anındaki EKF pozu kullanılır: `ATTITUDE_QUATERNION` + `LOCAL_POSITION_NED`, `time_boot_ms` ile interpolasyon. SITL'de bu zaman sim zamanıyla ±4 ms içinde aynıdır.
  - NED konumu `GPS_GLOBAL_ORIGIN`'e göre enlem/boylama çevrilir.
  - Şu durumlarda konum hesaplanmaz (reddedilir):
    - Kutu görüntü kenarına 8 px'ten yakınsa (ayak görünmüyor olabilir).
    - Işının aşağı bileşeni `u_D < 0.25` ise (ufka yakın, uzak tespit).
    - Poz geçmişi kare anını 0.15 s içinde kapsamıyorsa.
- `FOLLOW_TARGET` işlenen kare başına en çok 10 Hz gönderilir.
  - Alanlar: `est_capabilities=1`; hız `NaN` (0 gönderilirse PX4 hedefi "duruyor" sayar); `alt` ev noktasının AMSL yüksekliği (`FLW_TGT_ALT_M 0` iken kullanılmaz).
  - PX4 konumu en sık 500 ms'de bir kaynaştırır ve 3 s mesaj gelmezse hedefi kayıp sayar.
  - LOS kaynağı `hakem` ise `FOLLOW_TARGET` hedefin gerçek konumundan, yalnız hedef görünürken gönderilir. Bu bir "mükemmel algılayıcı" referans koşusudur.
- Follow Me ayarları:
  - `FLW_TGT_HT` senaryoda verilmezse `drone.yukseklik_m` kullanılır.
  - `FLW_TGT_DST` parametre dosyasından gelir (8 m).
- `tez_los` kaynağında yalnız `TEZ_LOS` gönderilir. Takılan modül `--px4-baslat` ile başlatılır. Koşu sonunda `sim.log` içinde "unresponsive" aranır.
- Poz geçmişi pymavlink'in `message_hooks` kancasıyla toplanır; ana iş parçacığının `recv_match` döngüsü bozulmaz.
  - Bütün gönderimler tek bir kilitle yapılır; GCS heartbeat iş parçacığıyla çakışmaz.
  - `TEZ_MODE_NAME` sabiti kaldırılır.
- Her takip kaynağı aynı ölçütleri ve aynı MP4'ü üretir. `araclar/karsilastir.py` birden çok koşunun `ozet.json` dosyalarını tek tabloda yan yana koyar.

**7. Takım arkadaşı için kurulum ve PX4 modülü takma**
- `derle.sh --harici <klasör>` verilen klasörü `EXTERNAL_MODULES_LOCATION` olarak kullanır.
  - Bayrak verilmezse ve `tez/px4/src/CMakeLists.txt` varsa o klasör kullanılır. O da yoksa stok `px4_sitl_default` derlenir (+ `px4_gz_plugins`).
  - Çıktı her durumda `build/px4_sitl_tez`'dir.
  - Klasör önbellekteki değerden farklıysa CMake yeniden yapılandırılır.
- Ağaç içi modüller için de aynı `derle.sh` çalışır. Bunlar `src/modules/...` + `.px4board` ile eklenir ve kendi spec'leriyle birlikte bir kilit listesi PR'ı gerektirir. m06 kilit listesine yol eklemez.
- `calistir.sh --px4-baslat "<komut>"` (birden çok verilebilir) `.post` dosyasının yerini alır.
  - rcS'in bitmesi beklenir: `px4-logger status` başarılı olana kadar, en çok 90 s.
  - Sonra komutlar `rootfs` içinde `bin/px4-<komut>` istemcisiyle çalıştırılır; çıktıları sim log'una yazılır.
- Senaryodaki iki alan aynı işi `calistir.sh`'a devreder:
  - `takip.px4_baslat`: başlatma komutları.
  - `takip.px4_parametreleri`: modülün kendi parametreleri, başlangıçta yüklenir.

  Mod yalnız adıyla seçilir. Mod numarası (`nav_state` EXTERNALn, `custom_mode`) koda gömülmez.
- SITL'de `COM_MODE_ARM_CHK=1`'dir (stok `px4-rc.simulator`). Bu yüzden modül havadayken başlatılsa da kaydolabilir.
- `kur.sh` çalışmasının sonunda model klasörünü ve sha256 özetlerini kontrol eder ve sonucu yazar; model dosyası indirmez. Python betikleri yorumlayıcıyı `TEZ_PYTHON` ortam değişkeninden alır. Varsayılan, `VERSIONS.md`'deki ekip venv'idir.
- README'ye eklenecekler:
  - Ön koşullar.
  - AMD hibrit GPU için `DRI_PRIME=1` notu.
  - QGC AppImage için `libfuse2t64`.
  - Adım adım kılavuz (taslak: "Takım Arkadaşı Kılavuzu" bölümü).

**8. Senaryo dosyası ve komut satırı**
- `drone.mod` alanı kalkar, çünkü iskelet mod yok. Yerine `takip` bloğu gelir; ayrıca `algilama`, `gecikme`, `kusurlar` ve `video` blokları eklenir. Alan tablosu "Faz A Dosya Planı" bölümündedir.
- Mevcut 3 senaryo `takip: {kaynak: yok}` olarak güncellenir. Yeni `senaryolar/takip_yuruyen.yaml` eklenir: `yuruyen_insan` yolu, `follow_me`, 8 m yükseklik / 8 m geride, LOS kaynağı model.
- Yanlış alan adı ya da değer, hangi alan olduğu söylenerek reddedilir (`hedef._check_keys` deseni). Ayrıca:
  - `tez_los` için `mod_adi` zorunludur.
  - `algilama.etkin: false` iken `takip.los: model` reddedilir. `los` hiç verilmemişse ve algılama kapalıysa: `yok`
    kaynağında LOS yoktur (`ayarlar.takip.los: null`; F1 böyle koşar), `follow_me`/`tez_los` ise `los: hakem` ister.
  - `takip.px4_parametreleri` ve `--param`, `.params` dosyalarıyla aynı ad ve sayı kuralından geçer
    (`araclar/parametreler.py`). `MIS_TAKEOFF_ALT` reddedilir: kalkış yüksekliğini `drone.yukseklik_m` verir ve
    `px4_baglanti.takeoff` onu zaten yazar; aksi hâlde verilen değer sessizce ezilirdi.
- `senaryo.py`'ye eklenen bayraklar:
  - `--model`, `--imgsz`, `--conf`, `--sinif`, `--modelsiz`
  - `--takip`, `--mod-adi`, `--los`
  - `--param AD=DEĞER` ve `--px4-baslat KOMUT` (ikisi de birden çok verilebilir)
  - `--gecikme-ms`, `--qgc`, `--videosuz`, `--kareleri-sakla`
- Komut satırı YAML'daki değeri ezer. Koşuda geçerli olan ayarların hepsi `ozet.json` içindeki `ayarlar` alanına yazılır. Bunlara PX4'e yüklenen parametreler ve model özeti de dahildir.
  - Komut satırı değerleri doğrulamadan önce senaryonun bloklarına yerleşir (`hedef.load(ad, CommandLine)`); hata
    mesajı YAML alan adını ve bayrağı birlikte söyler. `--param` ve `--px4-baslat` senaryonun listesinin sonuna
    eklenir (yükleme sırası korunur). `--kareleri-sakla` yalnız komut satırındadır (`ayarlar.video.kareleri_sakla`).
  - `ayarlar.px4_parametreleri`: yüklenen her başlangıç parametresi (dosyalar + senaryo + `--param`) için istenen
    değer (`deger`), kaynağı (`kaynak`: dosya:satır # yorum, `takip.px4_parametreleri` ya da `--param`) ve koşuda
    kalkıştan önce PX4'ten geri okunan değer (`px4`, `PARAM_REQUEST_READ`). PX4 istenen değeri tutmuyorsa koşu
    kalkıştan önce durur ("TAMAMLANMADI"; 1. maddedeki `param set` istisnası). `takip.px4_parametreleri` ve
    `--param` bu yüzden 2. görev grubunda bağlandı; 10. grup yalnız `px4_baslat`'ı bağlar.
  - Ara durum (m06 sürerken, tasks.md 2.5): sonraki bir görev grubunda bağlanacak ayar varsayılan dışında verilirse
    `senaryo.py` simülasyonu açmadan "`<alan>`: Görev grubu N'de bağlanacak" hatasıyla durur (`hedef.check_wired`;
    `senaryo.run` de aynı kontrolü yapar). Varsayılanı henüz etkin olmayan ayarlar `ayarlar.henuz_bagli_degil`'de
    grup numarasıyla listelenir (ör. `{"algilama.etkin": 4, "takip.los": 5, "video.mp4": 8}`). Her grup kendi
    satırlarını `hedef.unwired` / `hedef.not_in_effect`'ten siler.
  - `ozet.json`'daki eski `takip_kaynagi` alanı `ayarlar.takip.kaynak`'a taşındı (`ayarlar.takip.mod`: seçilen PX4
    modunun adı).
- `calistir.sh`'a `--param` ve `--px4-baslat`, `derle.sh`'a `--harici` eklenir. Mevcut `--ekransiz`, `--dunya` (`calistir.sh`) ve `--temiz` (`derle.sh`) aynen kalır. `calistir.sh` her açılışta parametreleri zaten sıfırlar.

**9. Ölçütler, rapor ve MP4 video**
- Her koşu `tez/sim/sonuclar/<tarih>_<ad>/` altına şunları yazar (git'e girmez):
  - `algilama.csv`: işlenen kare başına zamanlar, seçilen kutu, LOS, durum ve konum hesabı.
  - `kutular.csv`: modelin bulduğu bütün kutular.
  - `dogru_cevap.csv`: mevcut hakem dosyası.
  - `ozet.json` ve `rapor.html`: yeni bölümlerle.
  - `kosu.mp4` ve `ucus.ulg`.
- Ölçüt tanımları "Ölçüt Tanımları" bölümündedir. Başarı eşikleri boş kalır, yalnız ölçülür; eşikleri m01 belirleyince eklenir.
- Video kareleri `goruntu_yayini.py` tarafından toplanır.
  - Kayıt penceresinde, sim zamanında 15 fps ızgarasına denk gelen kareler (her 2. kare) alınır.
  - Kareler 1280×720 JPEG (kalite 90) olarak `kareler/` klasörüne yazılır.
  - MP4 üretildikten sonra bu klasör silinir; `--kareleri-sakla` verilirse kalır.
- Koşu bitince `araclar/video.py` videoyu birleştirir: 2000×720, 15 fps.
  - **Sol (1280×720), dron kamerası:**
    - Hakemin kutuları: hedef mavi, diğer insanlar turuncu.
    - O anda PX4'ün elindeki son model sonucu: seçilen kutu kalın kırmızı ve güven değeriyle, diğerleri ince çizgiyle.
    - "HEDEF YOK" yazısı; sim zamanı, mod ve uçtan uca gecikme.
  - **Sağ (720×720), üstten görünüm:**
    - Dron, hedef, diğer insanlar, ağaçlar.
    - Kameranın zemindeki izdüşümü ve son 10 s'lik iz.
    - `follow_me`'de gönderilen `FOLLOW_TARGET` noktası.
    - Ölçek çubuğu ve yatay mesafe.
- Kodlama:
  - Kareler ham BGR olarak `ffmpeg`'e borudan verilir (`rawvideo`, `bgr24`).
  - `ffmpeg` ayarları: `libx264`, `-pix_fmt yuv420p`, `-preset veryfast`, `-crf 23`, `-movflags +faststart`. Video VLC 3.0.20'de açılır.
  - OpenCV `VideoWriter` kullanılmaz; pip'ten gelen OpenCV'de H.264 kodlayıcı yoktur.
  - `onizleme.py` de WebM yerine aynı kodlayıcıyla MP4 üretir.
- ULog özeti genişler: PX4'e ulaşan `TEZ_LOS` (`debug_vect`) sayısı ve hızı, `follow_target` sayısı ve `vehicle_status` mod zaman çizelgesi.

**10. QGC'ye canlı video**
- `araclar/goruntu_yayini.py` deney dalındaki dosyanın yeniden yazımıdır.
  - Kaynak `/x500_tez/kamera/image`'dır. Deney dalındaki sabit `x500_mono_cam_0` konu adı kullanılmaz.
  - Kareler `subscribe_raw` ile alınır ve 15 fps'e göre her 2. kare kullanılır.
  - Çıktı 1280×720'dir.
- Kutular iki şekilde gelir:
  - Senaryo koşusunda: ana süreç `127.0.0.1:5610` adresine UDP JSON gönderir (son model sonucu + o karenin hakem kutusu).
  - Tek başına çalışırken (açık sim + QGC ile elle uçuş): `--model` ile kendi algılayıcısını çalıştırır. Bu modda LOS gönderilmez ve hakem kutusu yoktur.
- GStreamer hattı, sırasıyla:
  1. `appsrc`: BGR, 1280×720, 15/1, canlı kaynak.
  2. `queue leaky=downstream max-size-buffers=2`.
  3. `videoconvert` → I420.
  4. `x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000 key-int-max=15`, `constrained-baseline` profili.
  5. `rtph264pay config-interval=1 pt=96 mtu=1400`.
  6. `udpsink host=127.0.0.1 port=5600 sync=false`.
- QGC 5.1.4 ayarı: Uygulama Ayarları → Video → kaynak "UDP h.264 Video Stream", port 5600. QGC'siz kontrol için `gst-launch-1.0` alıcı hattı ya da VLC ile `araclar/yayin.sdp` kullanılır.
- Yayın `--qgc` ile açılır. Ayrı bir süreçtir ve kuyruğu sızdırandır; model ve kayıt hattını yavaşlatmaz.
- apt paketleri ve sürümleri:
  - Gerekenler: `python3-gi`, `gir1.2-gstreamer-1.0`, `gir1.2-gst-plugins-base-1.0`, `gstreamer1.0-plugins-base`, `gstreamer1.0-plugins-good`, `gstreamer1.0-plugins-ugly` (x264enc), `gstreamer1.0-libav` (yalnız `gst-launch` ile izlemek için), `ffmpeg`.
  - Sürümler uygulamada `dpkg-query` ile okunup `VERSIONS.md`'ye yazılır (şimdilik TBD).
  - `gstreamer1.0-plugins-bad` (`netsim`) Faz B'de gerekir.
- Wi-Fi gecikme/kayıp benzetimi Faz A'da yoktur (Faz B).

## Görsel Tasarım

**`planning/visuals/blok_diyagram_elle.jpeg`** (el çizimi, 23.10)
- Dört kutu vardır: "Gazebodaki kamera" → "Model" → "PX4" → "Simülasyon".
- Model'den PX4'e kıvrık, PX4'ten Simülasyon'a düz bir ok çizilmiştir.
- Simülasyon'dan kameraya dönüş oku çizilmemiştir ama döngü örtüktür: dron hareket edince görüntü değişir. Dijital diyagramda bu ok kesikli çizilir.
- Kavramsal bir çizimdir, arayüz tasarımı değildir. Ayrıntılar dijital diyagramdadır.

**`planning/visuals/blok_diyagram_dijital.mmd`** (aşağıdaki Mermaid kaynağının aynısı)
- Gazebo tarafı: dünya ve actor'lar, `x500_tez` kamera konusu, hakem segmentasyon kamerası.
- Laptop tarafında akış sırasıyla:
  1. Kamera kusurları aşaması (varsayılan kapalı).
  2. Kare okuyucu.
  3. Model (`.pt`, CPU).
  4. Hedef seçimi.
  5. LOS kaynağı seçimi: (i) model kutusu → `kamera.py`, ya da (ii) `los_govde`.
  6. Düz zemin konum hesabı.
  7. Gecikme hattı.
- MAVLink UDP 14540 ve takip kaynağı anahtarı: `follow_me`, `tez_los` + harici mod ya da `yok`.
- PX4 SITL: stok 4001, `PX4_SIM_MODEL=x500_tez` ve başlangıç parametreleri. `gz_bridge` üzerinden dron Gazebo'da hareket eder; kesikli ok döngüyü kapatır.
- Çıktılar: QGC video (RTP 5600), kayıt, rapor ve MP4.

```mermaid
flowchart LR
  subgraph SG_GZ["Gazebo Harmonic, gz-sim 8.15.0 (tez/sim/worlds, tez/sim/models)"]
    direction TB
    DUNYA["Dünya: duz_alan / cayir<br/>insan actor'ları: hedef + diğer insanlar<br/>(yol: senaryo YAML + yuruyus.py)"]
    DRON["x500_tez_0<br/>PX4 x500 + Camera Module 3<br/>gövde altı ön, sabit 45° aşağı"]
    CAM["Kamera (imager)<br/>/x500_tez/kamera/image + camera_info<br/>2304×1296 RGB, 30 Hz, sim zamanı damgalı"]
    SEG["Segmentasyon kamerası (yalnız hakem)<br/>/x500_tez/kamera_seg, 1152×648"]
    POZ["/world/DUNYA/dynamic_pose/info<br/>/world/DUNYA/clock"]
  end

  subgraph SG_PY["Laptop: tez/sim/araclar (senaryo.py yönetir)"]
    direction TB
    OKU["goruntu.py: kare okuyucu<br/>subscribe_raw, yalnız en yeni kare<br/>model yetişemezse kare atlanır ve sayılır"]
    KUS["kusurlar.py: kamera kusurları<br/>Faz A: hepsi KAPALI, kare değişmeden geçer"]
    MOD["algilama.py: model, kare → kutu listesi<br/>Ultralytics .pt, laptop CPU, ayrı süreç<br/>~/auto-follow-modeller/"]
    SEC["takip.py: hedef seçimi (geçici)<br/>ilk kilit hakemden, sonra en yakın kutu"]
    HAK["kayit.py: hakem / doğru cevap<br/>los_govde, görünürlük, kutular"]
    LOSK{"LOS kaynağı<br/>senaryo: takip.los"}
    LOSI["(i) model: kutu merkezi<br/>kamera.py: piksel → optik → gövde FRD"]
    LOSII["(ii) hakem: los_govde"]
    KON["konumlama.py: düz zemin geolocation<br/>kutu alt ortası + kare anındaki EKF pozu"]
    GEC["gecikme.py: ek gecikme + titreşim<br/>saat ofseti / kayması, varsayılan 0"]
    PB["px4_baglanti.py: MAVLink<br/>udpin 127.0.0.1:14540, GCS gibi<br/>kalkış, modu adıyla seçer (AVAILABLE_MODES)"]
    TKK{"Takip kaynağı<br/>takip.kaynak / --takip"}
    YAY["goruntu_yayini.py<br/>1280×720, 15 fps, kutular çizilir"]
    RAP["rapor.py / olcum.py / video.py<br/>rapor.html, ozet.json, dogru_cevap.csv,<br/>algilama.csv, kosu.mp4 (H.264, yuv420p)"]
  end

  subgraph SG_PX4["PX4 SITL v1.17.0, build/px4_sitl_tez (PX4 dosyası değişmez)"]
    direction TB
    BAS["Başlangıç: stok rcS<br/>PX4_SYS_AUTOSTART=4001 (gz_x500)<br/>PX4_SIM_MODEL=x500_tez, PX4_GZ_MODEL_NAME=x500_tez_0<br/>PX4_PARAM_*: 4019 kazançları + 22.08 ayarları"]
    ALI["mavlink alıcısı, onboard 14580<br/>DEBUG_VECT → debug_vect<br/>FOLLOW_TARGET → follow_target"]
    FM["Follow Target<br/>stok Follow Me"]
    EXT["Harici mod, adıyla seçilir<br/>ör. m15 takip modu"]
    HOLD["Hold<br/>yok: açık döngü"]
    KTR["Konum / duruş / açısal hız kontrolcüleri"]
    GZB["gz_bridge"]
    GCSL["mavlink GCS bağlantısı 18570"]
    ULG["ULog<br/>SDLOG_PROFILE 163: debug_vect dahil"]
  end

  QGC["QGroundControl 5.1.4<br/>telemetri UDP 14550, video UDP 5600"]

  DUNYA --> CAM
  DUNYA --> SEG
  DRON --> CAM
  CAM --> OKU --> KUS --> MOD --> SEC
  SEG --> HAK
  POZ --> HAK
  HAK -.->|"ilk kilit"| SEC
  SEC --> LOSK
  LOSK -->|"model"| LOSI
  LOSK -->|"hakem"| LOSII
  HAK --> LOSII
  SEC --> KON
  LOSI -->|"TEZ_LOS, işlenen kare başına, en çok 30 Hz"| GEC
  LOSII -->|"TEZ_LOS, en çok 30 Hz"| GEC
  KON -->|"FOLLOW_TARGET, en çok 10 Hz, yalnız follow_me"| GEC
  GEC --> PB
  PB -->|"UDP 14540 ↔ 14580"| ALI
  PB -.->|"mod komutu"| TKK
  TKK -->|"follow_me"| FM
  TKK -->|"tez_los + mod adı"| EXT
  TKK -->|"yok"| HOLD
  ALI --> FM
  ALI --> EXT
  ALI --> ULG
  BAS -.->|"başlangıç parametreleri"| KTR
  FM --> KTR
  EXT --> KTR
  HOLD --> KTR
  KTR --> GZB
  GZB -->|"motor komutları"| DRON
  DRON -->|"IMU, GPS, baro, mag, saat"| GZB
  DRON -.->|"dron hareket eder → kamera görüntüsü değişir (döngü)"| CAM
  CAM --> YAY
  SEC -->|"kutular, UDP 5610"| YAY
  HAK -->|"hakem kutusu"| YAY
  YAY -->|"H.264 RTP UDP 5600, --qgc"| QGC
  GCSL -->|"UDP 14550"| QGC
  YAY -->|"15 fps kareler"| RAP
  HAK --> RAP
  SEC --> RAP
  ULG --> RAP
```

**Süreçler ve zamanlama (diyagramın arkasındaki düzen)**
- **Ana süreç** (`senaryo.py`):
  - Gazebo/PX4'ü açar ve kapatır.
  - MAVLink bağlantısını tutar (14540; poz geçmişi `message_hooks` ile).
  - Hakemi çalıştırır (`kayit.Recorder`).
  - Takip iş parçacığında model sonucunu alır, hedefi seçer, LOS'u ve konumu hesaplar, gecikme hattından geçirip gönderir. Ardından satırı `algilama.csv`'ye yazar.
- **Model süreci** ("spawn"): kare okuyucu + kusur aşaması + algılayıcı. Sonuçlar FIFO kuyrukla ana sürece gider.
- **Yayın süreci** (`goruntu_yayini.py`): MP4 karelerini her zaman yazar; `--qgc` verilmişse RTP de yayınlar.
- MP4 koşu bittikten sonra çevrimdışı birleştirilir. Böylece video, koşunun zamanlamasını etkilemez ve her kontrolcü için aynı yolla üretilir.

## Yararlanılacak Mevcut Kod

**`tez/sim/araclar/kayit.py` ve `kamera.py` (hakem ve eksen zinciri)**
- `kayit.py` kamera karesi başına doğru cevabı üretir: `los_govde` (kameradan hedefe, gövde FRD), `gorunur`, hedef ve diğer insanların segmentasyon kutuları. Bunlar LOS kaynağı (ii) ve model ölçütlerinin referansıdır.
- Satırlar `round(t*1e6)` anahtarıyla eşlenir. `algilama.csv` de aynı anahtarla birleştirilir: model karesi, kamera karesiyle aynı sim zamanını taşır.
- `kamera.py` Hüseyin'in "Pikselden Vektöre" zincirini uygular: `Camera.pixel_to_los`, `undistort`, `camera_to_body`, `body_to_ned`, `project`. LOS (i), konum hesabı ve üstten görünümdeki kamera izdüşümü bunu kullanır; dönüşüm kodu kopyalanmaz.
- `Recorder.camera_offset` ve `camera_dcm` montajı Gazebo'dan okur. Takip tarafı ise Pi'deki ölçülmüş montaj yerine nominal değerleri kullanır (45°; FRD (0.151, 0, +0.035) m). Böylece ileride bilerek montaj hatası eklenebilir.

**`tez/sim/araclar/px4_baglanti.py`, `simulasyon.py`, `calistir.sh`, `derle.sh`**
- `Vehicle` zaten 14540'a GCS gibi bağlanıyor: 4 MB alım tamponu, GCS heartbeat, `modes()` (AVAILABLE_MODES), `switch_mode()`, `takeoff()`, `land()`. Bunlara gönderim kilidi, `send_los`, `send_follow_target`, `get_param` ve `message_hooks` ile poz geçmişi eklenir.
- `simulasyon.Simulation` simi açıp kapatır ve sorunları toplar. Değişecekler:
  - Hazır satırı `"registered as"` yerine `"Startup script returned successfully"` olur.
  - Parametreler ve başlatma komutları `calistir.sh`'a aktarılır.
  - "unresponsive" kontrolü yalnız harici modlu koşularda yapılır.
- `calistir.sh` dünya seçimini, ekransız çalışmayı, temiz parametreleri ve PX4'ü kapatma yolunu koruyarak (b) değişkenlerini ekler. `derle.sh` ayrı derleme klasörü düzenini korur.

**`tez/sim/araclar/senaryo.py`, `hedef.py`, `rapor.py`, `onizleme.py`, `f0_testi.py`**
- `senaryo.run` akışı korunur ve genişletilir: dünya yazma, sim, kalkış, mod, kayıt, iniş, ULog, rapor. Model ve yayın süreçleri kayıt başlamadan açılır, kayıt bitince kapanır.
- `hedef.load` alan doğrulama deseni (`_check_keys`, `_number`) yeni bloklar için de kullanılır.
- `rapor.metrics`, `_visibility` ve `plot_map` korunur. Yeni ölçütler `olcum.py`'de hesaplanır, `rapor.write` onları ekler. MP4'teki üstten görünüm `plot_map` ile aynı renkleri kullanır.
- `onizleme.py`'nin kutu çizimi (`Frames.annotate`) ve ffmpeg çağrısı `video.py`'ye taşınıp ortak kullanılır.
- `f0_testi.py`'nin rapor ve "GEÇTİ/KALDI" düzeni `m06_testi.py` için şablon olur.

**Deney dalı `origin/deney/ai-follow-sim:tez/deney/follow_sim/` (yalnız okunur; kod kopyalanmaz, yeniden yazılır)**
- `video/goruntu_yayini.py`: `subscribe_raw` ile yalnız yayınlanacak kareyi çözme, GStreamer hattı (appsrc → leaky queue → x264enc zerolatency → rtph264pay), kutu ve ayak noktası çizimi.
- `geolocation.py`: düz zemin kesişimi (`pixel_to_ground`), NED ↔ enlem/boylam (eşdikdörtgensel), açı/yükseklik hatası duyarlılığı. Burada `kamera.py` zinciriyle yeniden yazılır.
- `follow_core.py`:
  - `FOLLOW_TARGET`'ta bilinmeyen hızın `NaN` olması.
  - Kare anındaki EKF pozunun kullanılması.
  - Kenara değen kutunun reddi.
  - Zemin = ev noktası D + gövde iniş yüksekliği.
  - Faz B için `LinkImpairment` (Gilbert-Elliott) deseni.
- Alınmayacaklar: kırmızı renk eşikli dedektör, `mono_cam_cm3` / `renkli_duz`, Tk paneli, kilitli `Tools/simulation/gz` altına symlink, `px4_hook.post`, sabitlenmemiş `reportlab`.

**PX4 tarafı kaynakları (kılavuz ve parametreler için)**
- `ROMFS/.../4030_gz_x500_tez` içindeki 7 kazanç satırı (4019'dan) `gercek_dron.params`'a taşınır, sonra dosya geri alınır.
- İskelet modülün notları kılavuza girer. Kaynak: `tez/px4/src/CMakeLists.txt`, `TezAutoFollow.cpp`, dalın `c4b4abf342` commit'i.
  - `config_module_list_external` `PARENT_SCOPE` ile tanımlanır.
  - PX4 kütüphanelerine `DEPENDS` yazılmaz.
  - `register_ext_component_request` + arming check cevabı; mod adı en fazla 24 karakter.
- `~/Desktop/Follow/4_Ucus/Drone parametreleri/22.08.2026.params` (v1.17.0, gerçek araç): parametre seçiminin kaynağıdır, repoya girmez.

## Kapsam Dışı

- PX4 özel takip modu (m15, Yusuf Kurt). m06 yalnız onu takmayı ve test etmeyi kolaylaştırır.
- Asıl piksel → gövde dönüşümü (m10), asıl hedef seçimi ve geçersiz veri yönetimi (m11). m06'dakiler geçicidir.
- Hailo, asıl model seçimi ve Hailo ile tutarlı sim algılaması (m07/m08). Model eğitimi, veri toplama ve etiketleme (Aşama 8).
- Qt operatör arayüzü; gerçek Pi video yayını ve yer istasyonunda gösterim (m20/m24, Vision).
- Gerçek uçuş, CM3 kalibrasyonu (m09) ve dronun gerçek kütlesi (m21; ölçülene kadar standart X500).
- Ortak ölçüm altyapısı (m17) ve ortak spec'ler (m03 frame'ler, m04 haberleşme, m05 ICD).
- PX4, ROMFS veya submodule dosyasında değişiklik, kilit listesine yol eklenmesi, yeni MAVLink mesajı ya da dialect.
- ROS 2 ve Gazebo Classic.
- Sonraya bırakılanlar (taahhüt yok, belki ileride): rüzgâr ve esintiler, gerçekçi GPS gürültüsü, %3–7 eğimli zemin + aşağı bakan mesafe sensörü, insan çeşitliliği.
- Başarı eşikleri (m01 sayıları belirleyince) ve sim testlerinin CI'ya eklenmesi.

## Faz A Dosya Planı, Senaryo Alanları ve Teslim Sırası

### Dosyalar

| Yol | Durum | İçerik |
|---|---|---|
| `ROMFS/px4fmu_common/init.d-posix/airframes/4030_gz_x500_tez`, `.post`, `airframes/CMakeLists.txt` | v1.17.0 hâline döner | (b) yolu; `verify_pin.sh --worktree` geçer |
| `tez/px4/` | daldan çıkar | İskelet modül m06 PR'ına girmez |
| `tez/sim/parametreler/gercek_dron.params`, `sim.params` | yeni | Başlangıç parametreleri (tablo aşağıda) |
| `tez/sim/calistir.sh` | değişir | `PX4_SYS_AUTOSTART=4001`, `PX4_GZ_MODEL_NAME`, `PX4_PARAM_*`; `--param`, `--px4-baslat` |
| `araclar/parametreler.py` | yeni | `.params` ayrıştırma, yükleme sırası, `PX4_PARAM_*` satırları; F0 için geri okunan değerin karşılaştırılması |
| `tez/sim/derle.sh` | değişir | `--harici`, değişince yeniden yapılandırma; `tez/px4` yoksa stok derleme |
| `tez/sim/kur.sh` | değişir | Sonda model klasörü ve sha256 kontrolü (indirmez) |
| `tez/sim/modeller.yaml` | yeni | Bilinen model dosyaları: ad, sha256, boyut, kaynak |
| `araclar/goruntu.py`, `kusurlar.py`, `algilama.py` | yeni | Kare okuyucu, kusur aşaması (Faz A kapalı), algılayıcı arayüzü + YOLO + model süreci |
| `araclar/takip.py`, `konumlama.py`, `gecikme.py` | yeni | Hedef seçimi, LOS (i)/(ii), gönderim döngüsü; düz zemin konum hesabı; gecikme hattı + saat modeli |
| `araclar/goruntu_yayini.py`, `yayin.sdp`, `video.py` | yeni | 15 fps kare kaydı + QGC RTP; MP4 birleştirme |
| `araclar/olcum.py`, `karsilastir.py` | yeni | Model/LOS/zaman/takip ölçütleri; koşuları yan yana koyma |
| `araclar/m06_testi.py`, `m06_kabul.sh` | yeni | m06 SITL kabul testi |
| `araclar/px4_baglanti.py`, `simulasyon.py` | değişir | 6. ve "Yararlanılacak Mevcut Kod" maddelerindeki değişiklikler |
| `araclar/senaryo.py`, `hedef.py`, `rapor.py`, `onizleme.py` | değişir | Yeni alanlar, bayraklar, süreçler, ölçütler, MP4 |
| `araclar/f0_testi.py`, `f1_testi.py` | değişir | Stok modlar + parametre doğrulaması; `--modelsiz` |
| `senaryolar/*.yaml`, `senaryolar/takip_yuruyen.yaml` | değişir / yeni | `drone.mod` → `takip`; Follow Me 8/8 senaryosu |
| `testler/test_*.py` | yeni | "Test Planı"ndaki birim testleri |
| `tez/sim/ruff.toml` | değişir | `known-first-party`'ye yeni modüller |
| `tez/sim/README.md` | değişir | (b) yolu, kurulum, kılavuz, AMD, QGC; `TEZ_` ön eki ve "kilit listesinde izinli iki dosya" ifadeleri düzeltilir |
| `tez/env/model-requirements.txt` | yeni | `ultralytics`, `torch`/`torchvision` (CPU) ve bütün bağımlılıklar sabit sürümle (TBD) |
| `tez/env/VERSIONS.md` | değişir | Model paketleri, video apt paketleri, `libfuse2t64`, AGPL notu, `DRI_PRIME` |

Sürüm sabitliği (kural 4) için:
- `ultralytics`, `torch` ve `torchvision` sürümleri uydurulmaz. Uygulamada Python 3.12 / x86_64 için kurulabilir olan CPU sürümü denenir ve temiz bir venv'den `pip freeze` ile alınır. `ultralytics`'in çektiği `opencv-python`, `analiz-requirements.txt`'teki 5.0.0.93 ile uyumlu olmalıdır.
- `.pt` dosyası Ultralytics 8.4.174 ile kaydedilmiş. Seçilecek sürüm bu dosyayı yükleyebilmelidir.
- Çatıdaki `agent-os/product/tech-stack.md` ve `docs/02-ortak-yazilim-surumleri.md` ayrı bir çatı PR'ında güncellenir (Hüseyin).

### Başlangıç parametreleri

| Parametre | Değer | Kaynak | v1.17.0 varsayılanı |
|---|---|---|---|
| `IMU_GYRO_CUTOFF` | 30 | 4019_x500_v2 + 22.08 | 40 |
| `MC_ROLLRATE_P`, `MC_PITCHRATE_P` | 0.14 | 4019 + 22.08 | 0.15 |
| `MC_ROLLRATE_I`, `MC_PITCHRATE_I` | 0.3 | 4019 + 22.08 | 0.2 |
| `MC_ROLLRATE_D`, `MC_PITCHRATE_D` | 0.004 | 4019 + 22.08 | 0.003 |
| `FLW_TGT_HT`, `FLW_TGT_DST` | 8, 8 | 22.08 (45° raporu, stad ayarı) | 8, 8 |
| `FLW_TGT_ALT_M` | 0 | 22.08 | 0 |
| `EKF2_HGT_REF` | 1 (GPS) | 22.08 | 1 |
| `EKF2_MAG_TYPE` | 0 | 22.08 | 0 |
| `MPC_YAWRAUTO_MAX`, `MPC_TILTMAX_AIR` | 60, 45 | 22.08 | 60, 45 |
| `SDLOG_PROFILE` (`sim.params`) | 163 | sim: 131 + 32 (DEBUG_TOPICS, `debug_vect` için) | SITL rcS: 131 |

Davranışı yalnız ilk 7 kazanç değiştirir. Gereksinimlerde sayılan 22.08 değerleri zaten v1.17.0 varsayılanlarıyla aynıdır; izlenebilirlik için yine açıkça yazılır.

Karşılaştırmanın sonucu (11.11, `implementation/gorev-grubu-01.md`): 22.08'deki 1109 parametreden "dahil" sınıfında olup stok 4001 SITL'in etkin varsayılanından (meta veri + açılıştaki `set-default` satırları) farklı olan **yalnız bu 7 kazanç**tır. `MC_AT_EN` (22.08: 1) meta varsayılandan farklıdır ama SITL rcS onu zaten 1 yapar. Tablo değişmedi.

### Senaryo alanları (Faz A, yeni)

Şema 2. görev grubunda tamamlandı (`araclar/hedef.py`): bütün alanlar okunur ve doğrulanır. Son sütundaki grup
gelene kadar o ayar varsayılan dışında verilirse koşu simülasyon açılmadan durur (8. madde, "Ara durum").

| Alan | Değerler, varsayılan | Not | Bağlandığı görev grubu |
|---|---|---|---|
| `takip.kaynak` | `yok` \| `follow_me` \| `tez_los`; `yok` | Mod: Hold / "Follow Target" / `mod_adi`; `--takip` | `yok`: 1 · `tez_los`: 5 · `follow_me`: 6 |
| `takip.mod_adi` | metin | `tez_los`'ta zorunlu; AVAILABLE_MODES'taki ad; `--mod-adi` | 5 |
| `takip.los` | `model` \| `hakem`; `model` (algılama kapalı + `yok`: LOS yok) | LOS kaynağı (i) / (ii); algılama kapalıyken `model` olamaz; `--los` | 5 |
| `takip.px4_baslat` | metin listesi; boş | PX4 açıldıktan sonraki komutlar; `--px4-baslat` sona eklenir | 10 |
| `takip.px4_parametreleri` | {AD: sayı}; boş | Dosyalardan sonra, `--param`'dan önce yüklenir; koşuda PX4'ten geri okunur; `MIS_TAKEOFF_ALT` yazılmaz | 2 |
| `algilama.etkin` | `true` | `false` / `--modelsiz`: model süreci yok | `false`: 2 (model zaten yok) · `true`: 4 |
| `algilama.model`, `imgsz`, `conf`, `sinif`, `cekirdek` | yol (`~` açılır); `.pt`'deki (tam sayı ≥ 32); 0.25 ((0, 1]); adı `person` olan (ad ya da numara ≥ 0); 4 (≥ 1) | Komut satırı ezer (`--model`, `--imgsz`, `--conf`, `--sinif`) | 4 |
| `gecikme.ek_ms`, `titresim_ms`, `saat_ofset_ms`, `saat_kayma_ppm` | hepsi 0 (ilk ikisi ≥ 0) | Yakalama → PX4 yolu; `--gecikme-ms` = `ek_ms` | 12 |
| `kusurlar` | `{}` | Faz A: kapalı; Faz B alanları ayrılmış; 2. grupta yalnız sözlük olduğu denetlenir | 4 |
| `video.mp4`, `video.qgc` | `true`, `false` | `--videosuz`, `--qgc`; `--kareleri-sakla` yalnız komut satırında | `mp4: false`: 2 (video zaten yok) · `mp4`, `--kareleri-sakla`: 8 · `qgc`: 11 |
| `drone.mod` | kaldırılır | Yerine `takip.kaynak` | 1 |

### Teslim sırası ve 15.11'deki en az demo

1. (b) yolu: ROMFS geri alma, `tez/px4` çıkarma, parametre dosyaları, `calistir.sh`/`simulasyon.py`, F0 uyarlaması, `verify_pin`.
2. Kare okuyucu, model süreci, `algilama.csv` ve kare atlama / gecikme ölçümü.
3. LOS (i)/(ii), hedef seçimi, `TEZ_LOS`; takip kaynakları `yok` / `follow_me` / `tez_los` (adla mod), konum hesabı, `FOLLOW_TARGET`.
4. Ölçütler, rapor ve MP4.
5. `derle.sh --harici`, `--px4-baslat`, README kılavuzu.
6. QGC yayını, yapay gecikme ve saat ayarları, `karsilastir.py`.
7. `m06_kabul.sh`, `VERSIONS.md` / `model-requirements.txt`, son README.

**En az demo (15.11):**
- `takip_yuruyen` senaryosu v0.2 modeliyle (CPU) ve stok Follow Me ile kapalı döngüde uçar.
- `kalabalik_park` senaryosu `yok` ile koşar ve model ölçütleri çıkar (karıştırma, örtülme).
- İki koşu da `rapor.html`, `ozet.json` ve VLC'de açılan `kosu.mp4` üretir; `TEZ_LOS` ULog'da görünür.
- `verify_pin.sh --worktree` geçer.
- Bu belgedeki belgeler hazırdır.

5–7. gruplar demoya yetişmezse 15.11'den sonra aynı PR'da, merge'den önce tamamlanır. Bunlar Faz A'dır, Faz B'ye kaymaz. Her görev grubu ayrı commit olur (`2026-11-10-m06-sim-ortami: Görev grubu N — ...`).

## Belgeler

### Yaklaşma mesafesi: kamera neden 45° aşağı bakar? (`planning/kaynaklar/Kamera_ve_Takip_Ayarlari_Raporu.pdf`, 23–24.10)

> **Kaynak notu:** Geniş taramadaki sayılar eski (WSL dönemi) simülasyondan gelir. O taramada hedef bir insan modeli değil kırmızı bir kutuydu, kamera gövde hizasındaydı ve takip PX4'ün hazır Follow Me moduyla yapıldı. Eğim aynı olduğu için görüş geometrisi değişmez; yalnız birkaç santimlik yer farkı vardır. Gerçek modelle, yeni simde ve kapalı döngüde yeniden ölçüm **Faz B**'dedir.

**Kural:** Kamera gövdenin altına sabit 45° aşağı bakacak şekilde takılır. Dron kaç metre yüksekte uçuyorsa takip ettiği kişinin yaklaşık o kadar gerisinde durur.

| Uçuş alanı | Yükseklik | Geride durma |
|---|---|---|
| Stad | 8 m | 8 m |
| Çim alanın açık kısmı | 10 m | 10 m |
| Ağaçların üstü | 15 m | 12 m |

Bu ayarların her biri, dronun kişiyi yalnız kendi kamerasıyla takip ettiği 3 denemenin 3'ünde başarılı oldu; kişi zamanın %91–96'sında görüntüdeydi.

**Kamera yerde neyi görür?**
- CM3 Standard yatayda 66°, dikeyde 41° görür; yani optik eksenin 20.5° yukarısını ve 20.5° aşağısını. Simde 66° ve 16:9'dan dikey ≈ 40.1° çıkar (bkz. kamera tablosu).
- Düz ileri bakan kamera simde kişiyi zamanın yalnız %2'sinde gördü. 45° aşağı bakan kamera kişiyi görüntünün ortasında tutar.
- Görüntü 2304×1296'dır. 15 m'de bile kişi 100 pikselden büyük görünür; bu, tespit için rahat bir boyuttur.

| Yükseklik | Yerde görülen şerit (dronun önünde) | Kişinin olduğu yerde görüntü genişliği | Kişinin görüntüdeki boyu |
|---|---|---|---|
| 8 m | 3.6 → 17.5 m | ≈ 15 m | ≈ 195 px |
| 10 m | 4.6 → 22 m | ≈ 18 m | ≈ 155 px |
| 15 m | 6.8 → 33 m | ≈ 28 m | ≈ 115 px |

**Neden tam 45°?**
1. Kural kolay: yükseklik = geride durma mesafesi. Sahada hesap yapmadan ayarlanır.
2. Denemelerde başarılı oldu: kurala uyan beş ayarın hepsi 3/3 başarılıydı. Kişi zamanın %91–96'sında görüntüdeydi, en uzun kayıp 2 s'nin altında kaldı.
3. İnsanların başına yakın uçmaz: 8 m'de dron başların ~6 m üstündedir. Daha küçük eğimler dronu 3–4 m'ye, yani başların yalnız 1–2 m üstüne indirir; kalabalıkta tehlikelidir.
4. Araya biri girince hedefi daha zor kaybeder: 45°'de bu ancak biri kişinin 1.8 m yakınına girerse olur. Bu mesafe 30°'de 3.5 m, 15°'de 4.6 m'dir.
5. Ağaçların üstüne çıkabilir: aynı montajla 15 m'den takip edilir. Stad ve çim alan için tek montaj yeter.

**Konum hesabı için de 45° iyidir.** Kamera mesafeyi ölçemez, yalnız yön verir. Mesafe yükseklik ve bakış açısından bir üçgenle bulunur. Kişinin 8 m gerisinde uçarken 1°'lik açı hatasının mesafede yaptığı hata (Δd = 2d / sin 2θ):

| Bakış açısı | 20° | 30° | 45° | 60° |
|---|---|---|---|---|
| Mesafe hatası | 0.43 m | 0.32 m | 0.28 m | 0.32 m |

- Sığ açı, el fenerini yere yatık tutmak gibidir: küçük bir oynama lekeyi çok uzağa kaydırır. Çok dik açıda ise aynı mesafede kalmak için dron çok yükselmek zorunda kalır. 45° ikisinin ortasıdır.
- Hesap zemini düz kabul eder. Kişinin bastığı yer kalkış noktasından 1 m yüksekse hesaplanan konum kayar: 45°'de (8/8) ≈ 1 m, 30°'de (4/8) ≈ 2 m, 15°'de (3/8) ≈ 2.7 m. Kampüsteki çim alan doğuya doğru %3–7 eğimlidir.

**45°'de dikkat edilecekler:**
- Yükseklik ile mesafe birlikte değişmelidir. Yalnız yükseklik değişirse kamera kişiye göre yanlış yöne bakar; 6 m yükseklik / 8 m geride ayarı her denemede başarısız oldu.
  - Çalışan aralıklar: 8 m yükseklikte 6.5–10 m geride, 10 m yükseklikte 8–12 m geride.
- 6 m'nin altına inilmez. 5 m'nin altında güvenli bir ayar yok, 6 m'de iyi çalışan bir mesafe bulunamadı. En düşük rahat ayar 8 m / 8 m'dir.
- Dron hızlanırken ve frenlerken burnunu eğer ve kamera da onunla döner. Ağustos uçuşlarında burun çoğunlukla 11–18°'ye kadar eğildi, en fazla 26°. Kameranın payı ±20.5° olduğundan kişi normal uçuşta kadrajda kalır; çok sert manevrada kısa süre dışarı çıkabilir.
  - Simdeki kopmalar tam bu anlarda oldu: kişi birden koşmaya başlayınca görüntünün üstünden, aniden geri dönünce altından çıktı. Doğru yükseklik/mesafe çifti bu kopmaları önledi.
- Kameranın açısı araç üzerinde ölçülür. 1°'lik montaj hatası 8 m'de ≈ 0.3 m konum hatası demektir; ölçülen açı yazılıma girilmelidir.

**Neden başka bir eğim değil?** Aşağıdaki yükseklik ve geride durma değerleri, denemelerde başarılı olan en alçak ayardır.

| Eğim | Dron nerede uçar | Artısı | Eksisi | Ne zaman seçilir? |
|---|---|---|---|---|
| 0–10° | 3 m, 12–15 m geride | — | Kişi uzakta ve küçük görünür, kolay saklanır | Seçilmez |
| 15–25° | 3 m, 8 m geride | En net görüntü | Yükselemez; 3 m kalabalıkta tehlikeli | Boş ve düz alanda hep alçak uçulacaksa |
| 30° | 4 m, 8 m geride | Alçak uçuşta en iyi sonuç | Kalabalıkta riskli, kişi daha kolay saklanır, eğimli zeminde daha çok yanılır | Alanda insan ve engel yoksa |
| 35–40° | 6 m, 8 m geride | 45°'ye en yakın, güvenilir | Ağaç üstünde 15–20 m geride durmalı | Ağaç üstüne hiç çıkılmayacaksa en iyi yedek |
| **45°** | **8 m, 8 m geride** | Kolay kural, güvenli yükseklik, tek montaj her alana uyar | En alçak rahat ayar 8 m | **Seçilen** |
| 50–55° | 10–12 m, 8 m geride | Ağaç üstünde iyi | Stadda bile yüksek; kişi küçük | Çoğunlukla ağaç/bina üstünden uçulacaksa |
| 60° | 10 m, 6 m geride | — | Bazı denemelerde takip koptu; kişi dronun altından geçer | Seçilmez |

**30° neden seçilmedi?** Alçak uçuşta en iyi sonucu 30° verdi. Güvenlik ve alandaki insanlar hiç hesaba katılmasa bile iki fark kalır: konum doğruluğu ve ufkun kadraja girmesi.

| | 45° | 30° |
|---|---|---|
| Önerilen ayar (yükseklik / geride) | 8 m / 8 m | 4 m / 8 m |
| Takip başarısı (sim, yalnız kamerayla) | Kurala uyan 5 ayarın hepsi 3/3 | 12/12, alçakta en iyi |
| Kişinin görüntüdeki boyu | ≈ 195 px | ≈ 310 px |
| Zemin 1 m yüksekse konum kayması | ≈ 1 m | ≈ 2 m |
| Yükseklik 0.5 m yanlış ölçülürse | ≈ 0.5 m | ≈ 1 m |
| Tüm hatalar birlikte, kötü durumda (eski sim) | 1.3 m | 2.0 m (en yakın denenen 5 m / 8 m) |
| Ufuk kadraja ne zaman girer? | Burun 24.5° kalkınca | Burun 9.5° kalkınca |
| 15 m'ye çıkmak gerekirse geride durma | 12–15 m | ≈ 26 m |
| Başların üstünde | ≈ 6 m | ≈ 2 m |
| Araya giren kişinin saklayabildiği şerit | 1.8 m | 3.5 m |

1. **Konum hesabı iki kat daha hassas.** 30°'de küçük hatalar konuma iki kat büyüyerek yansır.
   - Çim alan eğimlidir.
   - Yükseklik GPS'ten tutulur (`EKF2_HGT_REF = 1`) ve GPS yükseklik hatası yarım metreyi bulur. Bu, 4 m'de yüksekliğin %12'si, 8 m'de %6'sıdır.
   - Projenin amacı kişinin yerini de hesaplamaktır.
2. **Ufuk kadraja çabuk girer.** Görüntünün üst kenarı optik eksenin 20.5° yukarısıdır. 45°'de bu kenar ufkun 24.5° altında, 30°'de yalnız 9.5° altında kalır. Ağustos uçuşlarında frenlerken burun 6–11° kalktı; 30°'de her sert frende ufuk kadraja girer. Bunun iki sonucu olur:
   - Ufka yakın uzak bir kişi ya da yanlış tespit için mesafe hesabı çok büyük çıkar.
   - Parlak gökyüzü otomatik pozlamayı karartır, yerdeki kişi koyulaşır.
3. **Yükselmek gerekince dron çok uzaklaşır.** 30°'de geride durma mesafesi yüksekliğin ≈ 2 katıdır; 15 m'de 26 m eder.

30°'nin daha iyi olduğu yanlar da var: alçak uçuşta takip biraz daha başarılı, kişi daha büyük ve daha yandan görünür. Tespit modelleri genelde yandan çekilmiş fotoğraflarla eğitildiği için bu tespiti kolaylaştırabilir. **Sonuç:** Alan boş ve düz olsaydı, hep alçaktan uçulacak olsaydı ve konum gerekmeseydi 30° iyi olurdu. Bu projede konum doğruluğundaki iki katlık fark ve ufkun sık kadraja girmesi 45°'yi öne geçirir.

**Bu sonuçlara nasıl ulaşıldı?**
- **Geniş tarama** (PX4 + Gazebo, Ekim 2026):
  - Hedef her seferinde aynı zor yolu izledi: yürüdü, döndü, durdu, birden koşmaya başladı, aniden geri döndü.
  - 3–20 m arasında 81 yükseklik/mesafe çifti, 0–60° arasında 13 kamera eğimiyle denendi.
  - En iyi 48 ayar, dron kişiyi yalnız kendi kamerasıyla bulacak şekilde 3'er kez uçuruldu: 144 uçuş.
  - 45° için 15/12 ve 12/10 ayarları da 3'er kez uçuruldu. Hepsi başarılıydı, en uzun kayıp 1.8 s.
- **Yeni sim ortamında kontrol:**
  - Kamera gerçek montaj yerinde, 45°'de. Görüş açısı ve montaj dama tahtasıyla ölçüldü.
  - `kalabalik_park` senaryosunda dron 10 m'de beklerken, 7–17 m uzakta yürüyen kişi zamanın %100'ünde kadrajdaydı. Gerçekten göründüğü süre (ağaç arkası hariç) %81.5'ti.
- **Sınırlar:** rüzgâr ve engebeli zemin yoktu; hedef kırmızı kutuydu; takip stok Follow Me ile yapıldı; gerçek uçuşla henüz doğrulanmadı.

**Dron ayarları ve ilk gerçek uçuş**
- Follow Me'de `FLW_TGT_HT` = yükseklik, `FLW_TGT_DST` = geride durma. Ekibin kendi modunda da aynı çift kullanılacak. Raporda kontrol tarafının önerdiği adlar `TEZ_FOL_ALT` / `TEZ_FOL_DIST`'tir; adları m15'i yapan kişi belirler.
- İlk uçuş önerisi:
  1. Kamera açısını araç üzerinde ölç.
  2. Stadda 45° ve 8 m / 8 m ayarıyla uç.
  3. Önce yürüyen bir kişiyi, sonra koşma ve ani dönüşü takip et.
  4. Görüntüyü ve uçuş kaydını sakla; kişinin kadrajda kalma oranını simle karşılaştır.

**Yazılım ekipleri için notlar**
- Kontrol tarafı:
  - 45°'de `ALT ≈ DIST` birlikte değişmelidir.
  - Dron yatayken kadrajdaki bir kişinin yön vektörünün aşağı bileşeni `u_D` 0.41–0.91 arasındadır. Takip edilen kişide bu değer burun eğilse bile 0.55–0.7 civarındadır.
  - 0.2–0.3'lük bir alt eşik, ufka yakın uzak tespitleri takip edilen kişiyi atmadan ayıklar.
  - Montaj açısı Pi'de yöne eklenir; araçta ölçülen değer kullanılmalıdır.
- Görüntü tarafı:
  - Kişi 8/8'de ≈ 195 px, 15/12'de ≈ 115 px boyunda görünür.
  - Kutunun alt kenarı kameraya yakın ayaktır; simde bu ≈ 25 cm öne kaymış bir nokta demektir.
  - Odak uzaklığı veri sayfasında bile %5 belirsizdir. CM3, 2304×1296 modunda dama tahtasıyla kalibre edilmelidir.

### Kamera parametreleri

| Konu | Değer |
|---|---|
| Model | Sim `tez/sim/models/x500_tez` (PX4 `x500` + kamera). Özel model seçildi: hazır `gz_x500_mono_cam` gövde üstünde düz bakar, CM3 çözünürlüğünde değildir ve hakem kamerası yoktur. Kilitli submodule'deki model de değiştirilemez |
| Sensör | Raspberry Pi Camera Module 3 Standard (Sony IMX708) |
| Görüş açısı | Yatay 66° (SDF `horizontal_fov` 1.151917 rad). Dikey: veri sayfasında 41° (±20.5°), simde 66° ve 16:9'dan 40.1° (±20.07°) |
| Çözünürlük / hız | 2304×1296 (2×2 birleştirilmiş mod), `R8G8B8`, 30 fps (`update_rate 30`) |
| İç parametreler | Tanımlı `fx = fy = 1152 / tan 33° = 1773.9 px`, ideal `cx, cy = 1152, 648`. 22.10 dama tahtası ölçümü: fx 1773.7 ± 0.2, cx 1152.3, cy 647.3, k ≈ 0, RMS 0.04 px |
| Bozulma | Yok (ideal pinhole); gerçek kamera m09'da kalibre edilene kadar |
| Kırpma | near 0.1 m, far 500 m |
| Gürültü | SDF Gaussian stddev 0.007. Ölçülen: 0.007 → 0 DN (etkisiz); 0.1 → 4.6 DN (beklenen 25.5). Gazebo tanımlananın ≈ 1/5'ini uygular; düzeltmesi Faz B'de |
| Montaj | Gövde altı ön, X500 V2 "Depth Camera Mount" yeri. `camera_link` base_link'e göre (0.151, 0, −0.035) m FLU (= FRD (0.151, 0, +0.035)); sabit 45° aşağı (pitch 0.785398). solvePnP montaj hatası 1.9 mm / 0.03°; kadrajda dron parçası yok |
| Konular | `/x500_tez/kamera/image`, `/x500_tez/kamera/camera_info`. Hakem: `/x500_tez/kamera_seg/labels_map` (instance, 1152×648, aynı açı, etiket 3. kanalda) |
| Saatler | RTF 0.97; PX4–Gazebo farkı ±4 ms (lockstep); 30.3 kare/sim-s; kare aralığı 32/36 ms; kare Python'a ≈ 20 ms'de ulaşır |
| Veri sayfası tutarsızlığı | 4.74 mm / 2.8 µm (2×2 birleştirilmiş piksel) → fx 1693 (HFOV 68.5°); oysa 66° → fx 1774. Simde 66° kullanılır; gerçek değer m09'da ölçülür |
| Görüntüde kişi boyu | 8/8 ≈ 195 px · 10/10 ≈ 155 px · 15/12 ≈ 115 px |

### İnsan hedefinin nasıl hareket ettiği

- **Model:** Gazebo Fuel "actor" (yazar Mingfei, sürüm 1, CC BY 4.0; tezde kaynak gösterilir). `kur.sh` sha256 kontrolüyle indirir, repoya girmez.
  - `walk_tez` / `run_tez` kopyaları `animasyon.py` ile üretilir. Döngü ayakların yan yana geldiği andan başlar (kalça ilerlemesi: yürüme 0.37 m, koşu 0.24 m).
  - Kalça ilerlemesi 0.91 ile ölçeklenir. Böylece basan ayağın kayması 1.4 m/s'de 0.12 m/s'den 0.00 m/s'ye iner.
- **Yol** (senaryo YAML):
  - `hedef.baslangic: [x, y]` ve `hedef.yol` listesi: `{nokta: [x, y], hiz_mps: v}` ya da `{dur_s: s}`.
  - `v > 2 m/s` koşu animasyonunu seçer; izin verilen en büyük hız 6 m/s'dir.
  - Koordinatlar Gazebo dünyasında: x doğu, y kuzey [m]. Dron (0, 0)'dan doğuya bakarak kalkar.
  - `zamanlama.baslama_s`: hedefin yürümeye başladığı sim zamanı.
- **İnsan gibi hareket** (`yuruyus.py`, değerler koddan doğrulandı):
  - İvmelenme ve yavaşlama: yürürken 2.0, koşarken 2.5 m/s². İlk adımın sonunda yürüme hızına ulaşılır.
  - Köşeler yayla dönülür. Yarıçap = v² / a_yanal; a_yanal yürürken 1.5, koşarken 3.0 m/s². 1.4 m/s'de bu ≈ 1.3 m eder.
  - 135°'den keskin dönüşlerde, ilk kalkışta ve beklemeden sonra yeni yöne kalkarken 0.3 m yarıçaplı dar bir yayda adım atarak, en çok √(1.5·0.3) ≈ 0.67 m/s ile dönülür. İnsan yerinde dönmez; modelde dönüş animasyonu yoktur.
  - Hız %5 standart sapmayla dalgalanır (dalga boyu 4–12 m).
  - Yürüme çizgisi 8 cm standart sapmayla yana sapar (dalga boyu 8–20 m). Sapma senaryo noktalarına 2 m kala söner.
  - Hareket tohumludur (`tohum`): aynı tohum aynı yürüyüşü verir.
  - Alanlar: `davranis: {dogal, tohum, hiz_dalgalanma, yol_sapmasi_m}`. `dogal: false` eski ideal hareketi verir.
  - Yol 20 ms çözünürlükle planlanır. Actor ara noktaları 0.2 s arayla yazılır (Gazebo Catmull-Rom ile doldurur). Ölçülen fark 0.05–0.19 m'dir; gövde merkezi yolun biraz önündedir.
- **Görünüş ve kalabalık:**
  - `hedef.kiyafet: {ust, alt, ten}`.
  - Renkler: `yesil` (varsayılan), `kot`, `kirmizi`, `turuncu`, `sari`, `mavi`, `lacivert`, `mor`, `beyaz`, `gri`, `siyah`, `kahverengi`, `bej`, `haki`. Ten: `acik`, `orta`, `esmer`, `koyu`.
  - `diger_insanlar`: hedefle aynı alanları alır, ayrıca `gecikme_s`. Aynı kıyafet karıştırma testi içindir.
  - Segmentasyon etiketleri: hedef 1, diğerleri 11, 12, …
- **Doğru cevap:** hedefin gövde merkezi yerden 0.9 m, baş 1.75 m kabul edilir. Görünürlük eşiği 40 px'tir.
  - Gazebo Harmonic actor konumunu yayınlamaz; doğru cevap yoldan hesaplanır.
  - `senaryo.py --dogrula` bunu tepe segmentasyon kamerasıyla kontrol eder.
- **Sınırlar ve bilinen önlemler:**
  - Actor ağaçla çarpışmaz; ağaç gövdesinden geçen yol reddedilir.
  - Herkes aynı bedendedir (kel, yalınayak).
  - `loop=true` + sonda 100000 s "dur" parçası kullanılır, çünkü `loop=false` + kamera sunucuyu kilitler.
  - `interpolate_x` hatası için her yörüngeye aynı dosyanın farklı bir yazımı verilir.
  - Hız ve ivme sınırları, gerçek insanlarla ölçülene kadar varsayımdır.
- **Hazır senaryolar:**
  - `yuruyen_insan` ve `kivrimli_yuruyus`: `duz_alan` dünyasında.
  - `kalabalik_park`: `cayir` dünyasında hedef + 4 kişi (patikada yürüyen, çapraz koşan, durup yürüyen, aynı kıyafetli); hedef bir süre çamın arkasında kalır.
  - `takip_yuruyen` (yeni): Follow Me 8/8.

### Model dosyası (v0.2)

| Konu | Değer |
|---|---|
| Dosya | `person_detection_model_v0.2.pt` → `~/auto-follow-modeller/` (repoya girmez, kural 9) |
| Geçici kaynak | Vision `origin/model-training` dalı, commit `ebff718`, `models/`. Ortak depolama yeri kararı bekliyor |
| Boyut | 22 525 930 bayt |
| sha256 | `c5f6838be50c2c09ca788e97381b68567f0df3f20e430905142ce88f8abaa440` |
| Dosyadaki üst veri | Ultralytics `DetectionModel`; taban `yolov8s.pt`; görev `detect`; tek sınıf `{0: 'Person'}`; eğitim `imgsz` 640, 100 epoch, batch 32, doğrulama `iou` 0.7; kaydeden sürüm 8.4.174; tarih 2026-10-09; veri `/content/person-1/data.yaml`; lisans AGPL-3.0 |
| Okunma şekli | Dosya çalıştırılmadan, bayt taramasıyla okunan ön bilgidir; Ortatepe teyit edecek |

## Varsayımlar

> Ortak spec'ler (m03 frame/eksen, m04 haberleşme yöntemi, m05 ICD) henüz yazılmadı. Aşağıdakilerin **hiçbiri kesin değildir**; m06'nın çalışması için seçilmiş geçici kurallardır. Ortak spec'ler yazılınca bu bölüm ve kod onlara göre güncellenir.

1. **`TEZ_LOS` mesajı**
   - `DEBUG_VECT` kullanılır, `name = "TEZ_LOS"`. PX4 adı 9 karakterde keser; bu ad 7 karakterdir.
   - `x, y, z`: kameranın optik merkezinden hedefe birim yön vektörü, gövde FRD'de, montaj açısı eklenmiş. Hedef noktası kutu merkezidir (hakemde gövde merkezi).
   - İşlenen kare başına bir mesaj, en çok 30 Hz. SITL'de UDP 14540 (PX4 onboard 14580) üzerinden.
   - Alıcı `name` alanıyla süzmelidir: her bağlantıdan gelen `DEBUG_VECT` aynı uORB konusuna düşer.
2. **Zaman damgası anlamı**
   - Kare zamanı, Gazebo başlık damgasıdır (sim zamanı). SITL lockstep'te bu PX4 açılıştan beri geçen süreyle ±4 ms içinde aynıdır.
   - `DEBUG_VECT.time_usec` alanına yakalama anı yazılır. Ancak PX4 v1.17.0 bu alanı uORB'a taşımaz: `debug_vect.timestamp` mesajın varış anıdır.
   - Bu yüzden PX4 tarafı gecikmeyi mesajdan öğrenemez. Gecikme telafisi gerekiyorsa ICD'de zaman damgalı bir yol seçilmelidir (ör. TIMESYNC + zaman damgasını işleyen bir mesaj).
   - Saat ofseti ve kayması ayarları bu yüzden şimdilik yalnız gönderilen alanı ve Python tarafındaki kayıtları etkiler.
3. **"Hedef yok" sinyali**
   - Hedef seçilemeyen işlenmiş karede `TEZ_LOS = (NaN, NaN, NaN)` gönderilir.
   - Kare hiç işlenmezse mesaj gitmez. Alıcı kendi zaman aşımını uygular (`PX4_ISFINITE` + varış zamanı).
   - `FOLLOW_TARGET` hedef yokken gönderilmez. PX4 3 s sonra bağlantıyı kayıp sayar, 1.5 s güncelleme olmazsa kestirimini sıfırlar.
4. **Frame ve eksenler** (`kamera.py` ile aynı)
   - Optik: x sağ, y aşağı, z ileri.
   - Gövde FRD: x burun, y sağ, z aşağı.
   - NED: kuzey, doğu, aşağı.
   - Gazebo: dünya ENU, model FLU.
   - Montaj nominaldir: 45° aşağı, base_link'e göre FRD (0.151, 0, +0.035) m; yalpa/sapma montaj hatası yok. LOS'un çıkış noktası gövde orijini değil kameradır; 0.15 m'lik fark 10 m'de ≈ 0.8° eder.
5. **`FOLLOW_TARGET` kullanımı**
   - Stok Follow Me için Pi'nin hedef adına gönderdiği konum mesajıdır.
   - `lat/lon`, kutunun alt ortasından düz zemin hesabıyla bulunur. Ayak noktası ≈ 25 cm kameraya doğru kayıktır.
   - `est_capabilities = 1`, hız `NaN`, `alt` = ev noktası AMSL, en çok 10 Hz.
   - PX4 konumu en sık 500 ms'de bir kaynaştırır. `timestamp` alanını kullanmaz.
6. **Düz zemin konum hesabı**
   - Zemin düzlemi: D = ev noktasının D değeri + 0.227 m. Bu, base_link'in iniş takımına göre yüksekliğidir; gerçek araçta ölçülür.
   - Kare anındaki EKF pozu `time_boot_ms` ile interpole edilir.
   - Reddedilenler: `u_D < 0.25`, kenardan 8 px içindeki kutular.
   - Bilinen sapma: simde EKF yaw değeri −4…−6° sabit kaymalı ölçüldü (Gazebo manyetik sapması −2.61°, PX4 WMM +3.41°). Bu 8 m'de ≈ 0.6–0.8 m yanal konum hatası demektir ve raporda görünür.
7. **Hedef seçimi:** ilk kilit ve kilit kaybından sonraki yeniden kilit hakemden yapılır (operatörün QGC'de hedefi seçmesinin yerine). Arada en yakın kutu izlenir. Asıl çözüm m11'dedir.
8. **Kontrolcü arayüzü:** m15 modunun adı ("AUTO FOLLOW"?), modülün yeri ve parametre öneki belli değildir. Bu yüzden mod yalnız adıyla seçilir ve ad senaryodan verilir. Bunlar `tez_los` dışındaki bir girdiye geçerse (ör. `FOLLOW_TARGET` + harici mod) takip kaynağı listesi genişler.
9. **Model:** v0.2'nin laptop CPU'sundaki davranışı, Hailo'daki davranışın ölçüsü değildir (m08).

## Ölçüt Tanımları

Ölçütler yalnız kayıt penceresinde hesaplanır (`zamanlama.baslama_s` → senaryo sonu). Hakem kutusu, segmentasyon kamerasında görünen piksellerin kutusudur: örtülü kısım dahil değildir ve 2 px'e yuvarlanmıştır. Eşleşme eşikleri ölçütün tanımının parçasıdır, başarı eşiği değildir.

| Grup | `ozet.json` anahtarı | Tanım |
|---|---|---|
| (a) Model | `algilama_orani`, `kacirma_orani` | Hedefin `gorunur` olduğu işlenmiş karelerde, hedefin hakem kutusuyla IoU ≥ 0.5 olan en az bir kutu bulunan kare oranı; kaçırma = 1 − bu |
| | `iou_ort`, `iou_p50` | Bu karelerde en iyi eşleşen kutunun IoU'su |
| | `secim_dogru_orani` | Hedef görünürken seçilen kutunun hedefle IoU ≥ 0.5 olduğu oran |
| | `yanlis_kisi_orani`, `yanlis_kisi_ayni_kiyafet_orani` | Seçilen kutunun başka bir insanın hakem kutusuyla IoU'sunun ≥ 0.3 ve hedefinkinden büyük olduğu işlenmiş kare oranı; aynı kıyafetli kişiler ayrıca sayılır |
| | `yanlis_pozitif_kare_basi`, `yeniden_kilit_sayisi` | Hiçbir insanın kutusuyla IoU ≥ 0.3 olmayan kutu sayısı / işlenen kare; hakemle yeniden kilit sayısı |
| (b) LOS | `los_aci_hatasi_{ort,p50,p95,maks}_deg` | Gönderilen LOS ile aynı karenin `los_govde`'si arasındaki açı; yalnız seçilen kutu hedefken |
| | `los_sapma_farki_{yatay,dikey}_ort_deg` | `kamera.deviation` bileşenlerindeki ortalama fark; sistematik kaymayı gösterir |
| (c) Zaman | `model_ms_{ort,p95}`, `ulasma_ms_ort`, `bekleme_ms_ort` | 4. gereksinimdeki tanımlar |
| | `uctan_uca_ms_{ort,p50,p95,maks}` | Gönderim − yakalama, sim ms |
| | `islenen_kare_hizi_hz`, `atlanan_kare_orani`, `rtf_ort` | Sim saniyesi başına işlenen kare; 1 − işlenen/üretilen; ortalama RTF |
| | `tez_los_px4_sayisi`, `tez_los_px4_hizi_hz` | ULog'daki `debug_vect` (`TEZ_LOS`) kayıtları; gönderilen sayıyla karşılaştırılır |
| (d) Takip | `yatay_mesafe_{min,ort,max}_m`, `kadrajda_kalma`, `gorunur_kalma`, `en_uzun_kayip_s`, `dron_yukseklik_ort_m` | Mevcut F1 ölçütleri (`rapor.metrics`) |
| | `mod_korunma_orani` | İstenen modda geçen süre / kayıt penceresi |
| | `geolocation_hatasi_{ort,p95}_m` | `follow_me`: gönderilen hedef konumu ile kare anındaki gerçek konum arasındaki yatay fark |
| | `yatay_mesafe_hatasi_ort_m` | `follow_me`: \|yatay mesafe − `FLW_TGT_DST`\| |
| (e) Video | `kosu.mp4` | 9. gereksinim; her koşuda aynı düzen |

## Test Planı

**Birim testleri** (pytest, donanımsız ve simsiz; mevcut 76 test geçmeye devam eder; `ultralytics`/`torch` gerekmez)

| Dosya | Ne sınanır |
|---|---|
| `test_parametreler.py` | `.params` ayrıştırma (yorum, boş satır, ad kuralı, sayı), hatalı satırın reddi, `PX4_PARAM_*` listesinin üretimi, yükleme sırası |
| `test_algilama.py` | Sahte algılayıcı; sınıf adı çözümü (`Person`/`person` → 0, numara, yoksa hata); taklit Ultralytics sonucundan `Kutu`'ya dönüşüm ve kırpma |
| `test_takip.py` | İlk kilit, izleme, kapı, kilit kaybı (10 kare); LOS (i) gidiş-dönüş: bilinen poz ve hedef → `project` → piksel → LOS, `los_govde` ile açı farkı < 0.01° |
| `test_konumlama.py` | Bilinen pozda zemin noktası → piksel → konum, hata < 1 cm; `u_D` eşiği, kenar reddi, poz aralığı reddi; NED ↔ enlem/boylam gidiş-dönüş |
| `test_mesajlar.py` | `DEBUG_VECT` paketleme/çözme (ad, birim norm, NaN = hedef yok); `FOLLOW_TARGET` (1e7 tamsayı enlem/boylam, NaN hız, `est_capabilities`); doğrulamanın geçersiz vektörü durdurması |
| `test_gecikme.py` | Sıra korunması, ek gecikme, tohumlu titreşim, saat ofseti/kayması |
| `test_kusurlar.py` | Boş ayarda karenin bit bit aynı kalması; Faz B alanının ve bilinmeyen alanın reddi |
| `test_olcum.py` | IoU, kaçırma, yanlış kişi (aynı kıyafet dahil), yanlış pozitif, LOS açı hatası, gecikme istatistikleri, atlanan kare oranı (elle hazırlanmış tablolarla) |
| `test_video.py` | Tek karelik birleşim (2000×720, çift boyutlar, kutuların yeri); taklit `subprocess` ile ffmpeg komutunda `libx264`, `yuv420p`, `+faststart` |
| `test_hedef.py` (eklenir) | Yeni senaryo alanları; hatanın alan adıyla verilmesi; `tez_los`'ta `mod_adi` zorunluluğu |

**SITL kabul testleri** (pencere yok)
- `f0_kabul.sh` (güncellenir, ~2 dk):
  - Kamera çözünürlüğü, hızı ve fx.
  - `SYS_AUTOSTART == 4001`; iki parametre dosyasındaki her satır PX4'te aynı değerde (`PARAM_REQUEST_READ`).
  - "Hold" ve "Follow Target" AVAILABLE_MODES listesinde.
  - 10 m'ye kalkış; Hold'da 15 s konum tutma (sapma < 0.5 m); iniş ve disarm; temiz kapanış.
- `f1_kabul.sh` (`--modelsiz`, `takip.kaynak: yok`): iki koşunun hedef farkı ≤ 0.15 m olmaya devam eder.
- `m06_kabul.sh` (yeni, ~8–10 dk): koşu 1 `takip_yuruyen` (`follow_me`, model); koşu 2 `kalabalik_park` (`yok`, model). İsteğe bağlı koşu 3: `--mod-adi "<ad>" --px4-baslat "<komut>"`, takılmış bir modül varsa. Geçme koşulları işlevseldir, başarım eşiği değildir:
  1. `verify_pin.sh --worktree` geçer; parametreler F0'daki gibi doğrulanır.
  2. Model yüklenir ve sha256 yazılır. En az bir işlenmiş karede hedefle IoU ≥ 0.5 kutu bulunur; model gerçekten görüntüde çalışıyordur.
  3. ULog'da `TEZ_LOS` adlı `debug_vect` vardır; sayısı gönderilen mesaj sayısının ±%5'i içindedir.
  4. Koşu 1'de "Follow Target"e geçilir, kayıt boyunca mod korunur ve ULog `follow_target` kaydı içerir.
  5. `kosu.mp4`'ü `ffprobe` okur: h264, yuv420p, 2000×720; süre kayıt penceresinin ±1 s içindedir.
  6. `ozet.json`'da "Ölçüt Tanımları"ndaki bütün anahtarlar bulunur (değer NaN olabilir); `rapor.html` yazılır.
  7. Temiz kapanış; harici modlu koşuda "unresponsive" görülmez.

**Görsel kontrol** (Ahmet, VLC'de `kosu.mp4`):
- Model kutusu hedefin üstünde ve gecikmesi gözle görülebiliyor.
- Hakem kutusu hedefle çakışıyor.
- Üstten görünüm kamera görüntüsüyle tutarlı (izdüşüm, kişiler).
- `follow_me`'de dron hedefi 8 m geriden izliyor.
- Kalabalıkta yanlış kişiye geçişler videoda ve ölçütte aynı anda görülüyor.

Düzeltme, sorunun gösterildiği sahnede yeniden koşularak doğrulanır.

**Belgeleme ve kod kontrolleri**
- Her kabul koşusunun özet sayıları, commit'i ve karşılaşılan sorunlar spec klasöründeki `implementation/` altına yazılır; video ve ULog yazılmaz.
- `ruff format` + `ruff check` (`tez/sim/ruff.toml`).
- Commit/PR öncesi `verify_pin.sh --worktree`.

## Takım Arkadaşı Kılavuzu (README'ye girecek taslak)

**A. Kurulum (bir kez)**
1. `TEZ_README.md` kurulumunu yap: Ubuntu 24.04, PX4 bağımlılıkları, Gazebo Harmonic (`apt-mark hold`), `python3-gz-*`. Ardından `git submodule update --init --recursive` ve `tez/pin/verify_pin.sh --worktree` (sonuç "KILIT SAGLAM" olmalı).
2. `VERSIONS.md`'deki video apt paketlerini (sabit sürümleriyle) ve QGC AppImage için `libfuse2t64`'ü kur.
3. Laptop venv'ini `VERSIONS.md`'deki komutla oluştur ve kur: `analiz-requirements.txt` + `model-requirements.txt` (torch CPU dizini). Betikler başka bir yorumlayıcıyı `TEZ_PYTHON` ile kabul eder.
4. Model dosyasını `~/auto-follow-modeller/` altına koy ve `sha256sum` ile `tez/sim/modeller.yaml`'daki özete göre kontrol et. Ortak depolama yeri belli olana kadar kaynak, Vision `model-training` dalıdır.
5. `tez/sim/derle.sh` ve `tez/sim/kur.sh` çalıştır.
6. GPU ayarı:
   - AMD hibrit GPU: Gazebo'yu açmadan önce `export DRI_PRIME=1`. `glxinfo -B` çıktısında ayrık kart (ör. RX 6600M) görünmeli.
   - NVIDIA: `VERSIONS.md`'deki PRIME ayarları.
7. Doğrulama: `tez/sim/araclar/f0_kabul.sh` ve `m06_kabul.sh` → "SONUÇ: GEÇTİ".

**B. Çalıştırma**
- Senaryo koşusu: `senaryo.py --senaryo takip_yuruyen`. Ek seçenekler: `--takip`, `--los`, `--model`, `--qgc`.
- Sonuç `tez/sim/sonuclar/<tarih>_<ad>/` altındadır: `kosu.mp4`'ü VLC'de, `rapor.html`'i tarayıcıda aç.
- Elle uçuş: `calistir.sh` + QGC; görüntü için `goruntu_yayini.py --qgc --model <yol>`.

**C. Kendi PX4 modülünü takmak (ör. m15)**
1. Modülü kendi dalında `tez/px4/src/modules/<ad>/` altına koy. Adı ve parametre önekini kendi spec'in belirler.
   - `tez/px4/src/CMakeLists.txt`, `config_module_list_external`'ı `PARENT_SCOPE` ile tanımlar.
   - Modül `px4_add_module(... MODULE_CONFIG module.yaml)` ile eklenir; PX4 kütüphanelerine `DEPENDS` yazılmaz.
   - Örnek: iskelet modül (`c4b4abf342`). Ağaç içi bir modül istiyorsan kilit listesi PR'ı gerekir; repo sorumlusuna sor.
2. Modu kaydet: `register_ext_component_request` (ad en fazla 24 karakter) ve arming check cevabı. Mod QGC'de ve AVAILABLE_MODES'ta adıyla görünür.
3. Derle: `tez/sim/derle.sh` (`tez/px4`'ü kendisi bulur) ya da `--harici <klasör>`.
4. Başlat: `calistir.sh --px4-baslat "<ad> start"` ya da senaryodaki `takip.px4_baslat` alanı.
5. Girdiyi oku: `debug_vect` uORB'una abone ol ve `name == "TEZ_LOS"` ile süz. NaN = hedef yok. Zaman aşımını varış zamanına göre kendin uygula (bkz. "Varsayımlar").
6. Koştur: bir senaryoyu kopyala ve `takip: {kaynak: tez_los, mod_adi: "<ad>", px4_baslat: [...], px4_parametreleri: {...}}` yaz. Önce `--los hakem` (mükemmel algılayıcı), sonra `--los model` ile koş.
7. Karşılaştır: aynı senaryoyu `--takip follow_me` ile de koş, sonra `karsilastir.py sonuclar/A sonuclar/B`.
8. Gerçek kart: `make px4_fmu-v6c_default EXTERNAL_MODULES_LOCATION=$PWD/tez/px4`. Flash ~%98 dolu; taşarsa repo sorumlusuna haber ver. Kartta başlatma (`etc/extras.txt`) m15/m16'nın işidir.

## Faz B (15.11'den sonra, aynı spec'e bağlı ikinci PR)

**Kamera kusurlarının ayarı ve açılması** (`kusurlar.py`, ayrılmış alanlar)
- **Gürültü:** Gazebo tanımlananın ≈ 1/5'ini uygular. SDF gürültüsü kapatılır; Python'da sensöre benzer gürültü (okuma + atış gürültüsü) eklenir. Değerler CM3 kayıtlarıyla ayarlanır (m09 ile).
- **Hareket bulanıklığı:** pozlama süresi × açısal hızdan (Gazebo pozu) yönlü bir çekirdekle.
- **Rolling shutter:** satır okuma süresi × açısal hızla satırların kaydırılması. IMX708'in bu moddaki okuma süresi ölçülür ya da veri sayfasından alınır.
- **Pozlama/parlaklık:** otomatik pozlama; gökyüzü kadraja girince yerin kararması (45° raporundaki etki).
- **Kabul:** her kusur tek başına açılır ve birim testinden geçer; MP4'te kusurlu ve kusursuz görüntü yan yana karşılaştırılır; model ölçütlerine etkisi raporlanır.

**Wi-Fi gecikme/kayıp benzetimi** (yalnız video yolu; Vision uçakta çalıştığı için `TEZ_LOS` yolu etkilenmez)
- GStreamer `netsim` (`gstreamer1.0-plugins-bad`) ve Gilbert-Elliott kayıp modeli (deneydeki `LinkImpairment` deseni) kullanılır.
- Senaryo alanları: `video.wifi.{gecikme_ms, kayip, patlama}`.
- Ölçüm: QGC'de görüntü gecikmesi ve donma süreleri.

**Yaklaşma mesafelerinin yeniden ölçülmesi**
- Ayarlar 3'er koşu: 8/8, 10/10, 15/12; aralık sınırları (8 m'de 6.5 ve 10 m, 10 m'de 8 ve 12 m); olumsuz kontrol 6/8.
- Koşullar: gerçek model (v0.2 ya da m08'in modeli), kapalı döngü (`follow_me`; m15 hazırsa o da), raporun zor yolu (yürü, dön, dur, birden koş, geri dön), `duz_alan` ve `cayir`.
- Ölçütler: kadrajda kalma, gerçekten görünür kalma, en uzun kayıp, konum hatası.
- Sonuç bu belgedeki "Yaklaşma mesafesi" bölümüyle karşılaştırılır ve bölüm güncellenir.

## Açık Konular

- **Hüseyin'in onayını bekleyenler:**
  - (b) yolu ve iskelet modülün PR'dan çıkarılması.
  - m06/m08 sınırı.
  - Ortak model depolama yeri. Vision PR #5'teki `.pt` dosyaları kural 9'a aykırı.
  - Çatıdaki `tech-stack.md` / `docs/02` güncellemesi.
  - Gazebo standardındaki "NVIDIA'da çalışmalı" ifadesinin AMD (`DRI_PRIME=1`) için genişletilmesi. Bu, `agent-os-profilleri/` üzerinden yapılır.
  - Geri bildirim mesajının (`Huseyine_geri_bildirim.txt`) gönderilip gönderilmediği bilinmiyor.
- **Yusuf Ortatepe'den:** "Model dosyası" bölümündeki üst verinin teyidi; önerdiği `conf`/`iou`; eğitimde kullandığı `ultralytics`/`torch` sürümleri; veri setinde eğik açıdan (dron) görüntü olup olmadığı; v0.2'nin doğru seçim olup olmadığı. Soru listesi repo dışında (`~/Desktop/Follow/Yusuf_Ortatepe_model_sorulari.txt`).
- **Yusuf Kurt / Yusuf Algan'dan:** mod adı, modülün yeri (harici `tez/px4` mi, ağaç içi + kilit listesi mi), parametre öneki, `TEZ_LOS` biçiminin uygunluğu, `time_usec` ihtiyacı (PX4 bu alanı düşürüyor).
- **Ortak spec'ler** (m03/m04/m05) yazılınca "Varsayımlar" ve ilgili kod güncellenir: `TEZ_LOS` biçimi, frame, zaman damgası, "hedef yok".
- **Uygulamada sabitlenecek sürümler (TBD):** `ultralytics`, `torch`/`torchvision` (CPU) ve bağımlılıkları; GStreamer, `python3-gi` ve `ffmpeg` apt paketleri; COCO `yolov8s.pt`'nin sha256 özeti.
