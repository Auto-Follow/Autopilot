# Görev Grubu 3 — Model ortamı: sürüm sabitleme, model dosyası, model yolu

- Tarih: 11.11.2026 · dal `ozellik/m06-sim-ortami` · taban commit `48aad9846f` (Görev grubu 2)
- Durum: **uygulandı ve test edildi**, commit'lenmedi.
- Kısaca: v0.2 modeli sabit sürümlü paketlerle (ultralytics 8.4.174, torch 2.14.1+cpu) laptop CPU'sunda yükleniyor,
  gerçek Gazebo karelerinde insanları buluyor ve kare başına ~60 ms sürüyor. Model senaryo koşusuna 4. grupta
  bağlanır; bu grupta denemek için `model_dene.py` var (aşağıda "Kendin dene").

## Ne yapıldı

| Alt görev | Dosya | Özet |
|---|---|---|
| 3.1 | `tez/sim/testler/test_algilama.py` (yeni) | 6 test: model yolu önceliği, eksik dosyanın nereden alınacağı, sha256 ve `modeller.yaml` karşılaştırması, `modeller.yaml` doğrulaması, sınıf çözümü, modülün torch'suz içe aktarılması |
| 3.2 | `tez/env/model-requirements.txt` (yeni) | Sürümler scratchpad'deki üç venv'de kurularak belirlendi (aşağıda); bütün bağımlılıklar sabit, PyTorch CPU dizini yorum olarak |
| 3.3 | `tez/env/VERSIONS.md` | 1. tabloya satır, "Sim model paketleri" bölümü (kurulum komutu, AGPL-3.0 notu, kapalı indirme/analitik), sürüm kontrolü satırları |
| 3.4 | ekip venv'i `~/Desktop/Projects/Auto-Follow/.venv-tez` | Kuruldu, `pip check` temiz; venv 1.1 GB → 2.1 GB |
| 3.5 | `~/auto-follow-modeller/person_detection_model_v0.2.pt` (repo dışı) | `git -C ../Vision show ebff718:models/person_detection_model_v0.2.pt` ile kopyalandı (yol commit içinde `ls-tree` ile doğrulandı), salt okunur (`chmod 444`); Vision reposu değişmedi |
| 3.6 | `tez/sim/modeller.yaml` (yeni) | v0.2 kaydı (ad, sha256, boyut, kaynak, alma komutu, açıklama); `yolov8s.pt` TBD (13. grup) |
| 3.7 | `tez/sim/araclar/algilama.py` (yeni) | `Kutu`, `Algilayici`, `model_path`, `load_catalog`, `file_sha256`, `inspect_model` (`ModelFile`), `resolve_class`, `to_boxes` |
| 3.8 | `algilama.py` | `YoloAlgilayici`: CPU, `cekirdek` iş parçacığı, `imgsz` varsayılanı `.pt`'den, `conf` 0.25; indirme, analitik, paket kurma ve `~/.config` yazımı kapalı |
| 3.9 | — | Doğrulama komutları ve duman testleri (aşağıda) |
| ek | `tez/sim/araclar/model_dene.py` (yeni), `testler/test_model_dene.py` (yeni, 2 test) | Kullanıcının modeli bir resimde ya da bir senaryonun Gazebo karelerinde (PX4'süz) denemesi için küçük araç; model ve hakem kutularını çizer, `model_ms` yazar |
| ek | `araclar/onizleme.py`, `araclar/hedef.py` | Kopyalamamak için: `onizleme.capture()` ve `people_of()` `main`'den ayrıldı (davranış aynı); `hedef._detection` → `hedef.read_detection` (herkese açık; `model_dene.py` bayraklarını aynı kurallarla doğrular) |
| ek | `tez/sim/.gitignore`, `tez/sim/ruff.toml`, `tez/sim/README.md` | `*.pt` (kural 9 güvenliği); `known-first-party`'ye `algilama`, `model_dene`, `onizleme`; README'ye kısa "Model (PX4'süz deneme)" bölümü ve dosya satırları |
| belge | `spec.md`, `tasks.md`, `implementation/kabul-kosulari.md` | Spec 3. madde, dosya planı, sürüm sabitliği, "Model dosyası" tablosu, açık konular; 3.x işaretlendi, 4.1/4.4'e not; iki duman koşusu tabloya |

## Seçilen sürümler

| Paket | Sürüm | Not |
|---|---|---|
| `ultralytics` | **8.4.174** | v0.2'yi kaydeden sürüm; ilk denenen, dosyayı yükledi (AGPL-3.0) |
| `torch` | **2.14.1+cpu** | PyTorch CPU dizini; torchvision 0.29'un derlendiği sürüm |
| `torchvision` | **0.29.2+cpu** | CPU dizinindeki en yeni torchvision |
| `opencv-python` | 5.0.0.93 (değişmedi) | `analiz-requirements.txt`; ultralytics `>=4.7.0, !=4.13.0.90` istiyor, 5.0 ile çalıştı |
| `ultralytics-thop` 2.2.5, `ultralytics-platform` 0.1.109, `nvidia-ml-py` 13.615.71, `polars` 2.1.0 + `polars-runtime-32` 2.1.0, `filelock` 4.2.10, `fsspec` 2026.9.0, `networkx` 3.7, `httpx` 0.28.1, `httpcore` 1.0.9, `h11` 0.16.0, `anyio` 4.16.0, `charset-normalizer` 3.5.2 | — | Ekip venv'ine yeni gelenler (pip'in çözdüğü) |
| `setuptools` | 80.10.2 | torch `>=77.0.3` istiyor; venv'de apt'nin 68.1.2'sinin önüne geçer |
| `typing_extensions` | 4.16.0 | anyio `>=4.16.0` istiyor; venv'de apt'nin 4.10.0'ının önüne geçer |
| pillow 10.2.0, PyYAML 6.0.1, requests 2.31.0, Jinja2 3.1.2, MarkupSafe 2.1.5, certifi 2023.11.17, idna 3.6, urllib3 2.0.7, pyparsing 3.1.1, python-dateutil 2.8.2, six 1.16.0 | Ubuntu 24.04 apt sürümleri | Ekip venv'inde zaten var (değişmez); sabitler yalnız sistem paketi görmeyen bir venv'de iş görür |

**Nasıl belirlendi (uydurulmadı):**

1. **Temiz venv** (scratchpad, Python 3.12.3): `pip install ultralytics==8.4.174 torch torchvision` PyTorch CPU dizini
   ve `requirements-lock.txt` + `analiz-requirements.txt` kısıtıyla (paylaşılan paketler ekiptekiyle aynı kalsın).
   pip **torch 2.15.0+cpu + torchvision 0.29.2+cpu** seçti: torchvision 0.29.2 yalnız `torch>=2.14.0` istiyor, CPU
   dizininde torch 2.15 için torchvision (0.30) henüz yok. NMS bu ikiliyle çalıştı ama resmî eşleşme torchvision
   0.29 ↔ torch 2.14 olduğu için **2.14.1+cpu** seçildi (ultralytics 8.4.174'ün kendi `export` ekstrası da bir
   platformda `torch<2.15.0` diyor).
2. **Ekip venv'inin aynası** (`--system-site-packages` + `analiz-requirements.txt`, böylece `~/.local` ve apt
   paketleri de görünür): aynı kurulum yalnız ekleme yaptı; apt'deki hiçbir dosya değişmedi ("Not uninstalling …
   outside environment"). Kapanış (bağımlılık ağacının tamamı) her paketin sürümü ve nereden geldiğiyle çıkarıldı;
   `model-requirements.txt` buradan yazıldı. Bu venv'de: `pip check` temiz, mevcut **124 test geçti**, v0.2
   ağ tamamen engelliyken yüklendi.
3. **Yalıtılmış venv** (sistem paketlerini görmez): `requirements-lock.txt` + `analiz-requirements.txt` +
   `model-requirements.txt` birlikte kuruldu, `pip check` temiz, v0.2 yüklendi; model kümesinin her paketi bir
   dosyada sabit. Dosyalarda olmayan dört paket (`pexpect`, `ptyprocess`, `pygments`, `pyserial`) ipython/MAVProxy
   bağımlılığıdır, yani `analiz-requirements.txt`'in eski eksiği; model işinin dışında, not edildi.
4. Ekip venv'ine `VERSIONS.md`'ye yazıldıktan sonra kuruldu; değişiklik aynadakiyle birebir aynı.

## Kararlar ve gerekçeler

1. **Her bağımlılık tek bir dosyada sabit.** numpy, matplotlib (+ contourpy, cycler, fonttools, kiwisolver),
   packaging, psutil, sympy, mpmath `requirements-lock.txt`'te; opencv `analiz-requirements.txt`'te; geri kalanı
   `model-requirements.txt`'te. Aynı paketi iki dosyada yazmak ileride iki farklı sürüm demek olurdu. Ubuntu'nun apt
   ile verdiği paketler (pillow, PyYAML, requests…) apt sürümleriyle yazıldı: ekip venv'inde pip onlara dokunmaz,
   önceki 124 test ve Gazebo bağları aynı paketlerle çalışmaya devam eder. "Temiz venv'deki `pip freeze`'i aynen
   yaz" yolu seçilmedi: pillow 13, python-dateutil 4.0 gibi daha yeni sürümler ekip venv'inde apt'nin önüne geçip
   pandas ve önizleme gibi mevcut araçların altındaki paketleri değiştirirdi.
2. **`setuptools` 80.10.2**, pip'in seçtiği 84.2.1 değil. torch `>=77.0.3` istiyor. 81 ve sonrası `pkg_resources`'ı
   çıkardı; MAVProxy'nin dört modülü (`mmap`, `magical`, `cesium`) onu içe aktarıyor. 84.2.1'de bu içe aktarma
   apt'deki eski kopyaya düşüyordu; apt'de `python3-setuptools` olmayan bir makinede kırılırdı. 80.10.2 venv'in
   içinde tutarlı bir `pkg_resources` taşır (yalnız kullanımdan kalkma uyarısı verir).
3. **`charset-normalizer` 3.5.2** ekip venv'ine kullanılmadan girer: PyPI'daki requests 2.31.0 onu ister, Ubuntu'nun
   requests'i ise `chardet` kullanır (`requests/compat.py`). Dosyanın sistem paketsiz bir venv'de de eksiksiz olması
   için yazıldı; zararsız.
4. **Ultralytics'in sessiz açılması** (`algilama._ultralytics`, süreç başına bir kez): ultralytics bu ayarları içe
   aktarılırken okur, bu yüzden içe aktarmadan önce:
   - `YOLO_OFFLINE=1`: açılıştaki internet kontrolü (DNS sorgusu) yapılmaz; `ONLINE=False` olunca analitik
     (`events`) de kapanır.
   - `YOLO_AUTOINSTALL=0`: eksik paket için `pip install` çalıştırmaz.
   - `YOLO_CONFIG_DIR` = geçici klasör, içinde önceden yazılmış `settings.json` (`sync: false`, veri/ağırlık/koşu
     klasörleri de o klasörde). Ultralytics ayar dosyasını yalnız oraya yazar; klasör süreç bitince silinir.
     Ultralytics'in kendi varsayılanı `~/.config/Ultralytics/settings.json` + `sync: true` (anonim kullanım
     istatistiği) ve veri klasörü olarak çatı reponun yanı olurdu (git kökünü bulduğu için).
   - Açıldıktan sonra `ONLINE` ya da `sync` açıksa hata verilir; ultralytics bu süreçte önceden içe aktarılmışsa
     da (ayarlar geç kalır).
   - Dosya yoksa `YOLO()`'ya hiç verilmez: ultralytics bilmediği bir adı internette (GitHub assets) arardı.
   - Doğrulama: `socket.getaddrinfo`, `create_connection` ve `connect` engellenmiş hâlde yükleme + tahmin → **0 ağ
     çağrısı**; `~/.config/Ultralytics` hiç oluşmadı; geçici klasör çıkışta silindi.
5. **İş parçacığı sayısı ısınmadan sonra kurulur** (uygulamada bulundu): ultralytics ilk tahminde
   `torch_utils.select_device` içinde `torch.set_num_threads(min(8, CPU−1))` yapıyor, yani bizim 4'ümüzü 8'e çekiyordu
   (ilk denemedeki ~47 ms bu yüzden 8 çekirdekle ölçülmüştü). `YoloAlgilayici` kurucuda boş bir kareyle ısınma
   tahmini yapar (ilk çağrı ~1 s, kayıt başlamadan biter), sayıyı sonra kurar ve her karede denetler. Ölçüldü:
   ısınmadan sonra ve üç karede de `torch.get_num_threads() == 4`.
6. **RGB → BGR:** kare okuyucu RGB verir (spec), ultralytics numpy kareyi OpenCV BGR sayar; `cv2.cvtColor` ile
   çevrilir, süre `model_ms`'e dahil (~1 ms).
7. **`imgsz` adımın katı olmalı:** v0.2'nin adımı 32 px. Ultralytics katı olmayan değeri uyarıyla yuvarlar;
   burada alan adıyla hata verilir (`algilama.imgsz: modelin adımının (32 px) katı olmalı (--imgsz), gelen: 650;
   ör. 640 ya da 672`). Görev grubu 2'deki "modelin adımına uygunluğu 3. grupta" notu böyle kapandı.
8. **Sınıf çözümü:** `--sinif`/`algilama.sinif` yoksa adı büyük/küçük harf ayırmadan `person` olan sınıf; ad ya da
   numara verilebilir; yoksa modelin bütün sınıflarını listeleyen hata. Tahmin `classes=[sinif]` ile yalnız o
   sınıfı döndürür.
9. **`modeller.yaml` eşleşmesi önce özetle, sonra adla:** adı değişmiş bir kopya yine tanınır; adı bilinen ama özeti
   farklı dosya uyarı alır ("Bu koşunun sonuçları bu dosyaya aittir"). Özeti kayıtlı olmayan (`yolov8s.pt`) için
   uyarı yok. Bir YAML ayrıntısı: yalnız rakamlardan oluşan bir özet tırnaksız yazılırsa YAML onu sayı okur ve
   doğrulama "64 küçük onaltılık rakam" diye reddeder (testte bu yüzden tırnaklı yazıldı).
10. **Arayüz adları spec'teki gibi Türkçe** (`Kutu`, `Algilayici.algila`, `YoloAlgilayici`, alanlar
    `u0 … sinif_adi`): Vision'ın takacağı sözleşme bunlardır. Diğer kod adları İngilizce.
11. **`to_boxes` (ultralytics çıktısı → `Kutu`, kareye kırpma, güvene göre sıralama) bu grupta yazıldı** çünkü duman
    testi ve `model_dene.py` kutuya ihtiyaç duyuyordu. Testleri 4.1'in işi (taklit ultralytics sonucu, kırpma,
    piksel kenarı kuralı); `tasks.md` 4.1'e not düşüldü.
12. **Ara durum kuralı değişmedi.** Bu grup senaryo koşusuna hiçbir ayar bağlamadı: model koşuda 4. grupta, model
    süreciyle çalışır. `algilama.model/imgsz/conf/sinif/cekirdek` varsayılan dışında verilirse koşu hâlâ "Görev
    grubu 4'te bağlanacak" der, `henuz_bagli_degil` hâlâ `algilama.etkin: 4` içerir;
    `test_settings_of_later_groups_stop_the_run` aynen geçer. Grup 2'nin "`ayarlar.algilama` çözülmüş yolu ve
    sha256'yı yazmalı" notu bu yüzden 4. gruba taşındı (`tasks.md` 4.4'e yazıldı: sim açılmadan `inspect_model`,
    `ModelFile.as_dict()` → `ayarlar.algilama`). Gerekçe: model koşmazken bir koşunun `ozet.json`'u model özeti
    taşısaydı modelin çalıştığını ima ederdi; eksik model dosyası da henüz modelin koşmadığı bir koşuyu durdururdu.
13. **`model_dene.py`** kullanıcının modeli kendi görebilmesi için eklendi; 4. grubun işini (canlı kamera okuyucu,
    model süreci, `algilama.csv`) yapmaz. `--senaryo` kipi `onizleme.py`'nin sabit kamerasıyla kareleri çeker
    (Gazebo, PX4 yok), modeli her karede çalıştırır, aynı anın hakem kutularını (segmentasyon) da çizer. Gazebo
    kodu kopyalanmadı: `onizleme.py`'deki Gazebo açma/bekleme bölümü `capture()` olarak ayrıldı. Bayraklar
    senaryonun `algilama` kurallarıyla doğrulanır (`hedef.read_detection`); senaryonun kendi `algilama` bloğu bu
    araçta kullanılmaz. Süre, aracın kendisi tarafından `algila()` çağrısının çevresinden ölçülür, yani Vision'ın
    ileride takacağı başka bir `Algilayici` da aynı araçla denenebilir.
14. **Türkçe harfler:** Pillow'un yerleşik yazı tipinde ç, ğ, ı, ş, ü yok (kutucuk çıkıyordu). `model_dene.py`
    Ubuntu'nun `fonts-dejavu-core` paketindeki DejaVuSans'ı kullanır, yoksa yerleşik yazı tipine düşer.
15. **`*.pt` → `tez/sim/.gitignore`:** model dosyaları zaten repo dışında; `tez/sim` altında yanlışlıkla bir kopya
    oluşursa `git status`'ta görünmesin (kural 9; 9.7'deki kontrol).

## Test sonuçları

| Kontrol | Sonuç |
|---|---|
| `$P -m pytest tez/sim/testler/test_algilama.py -q` | **6 geçti** |
| `$P -m pytest tez/sim/testler -q` | **132 geçti** (önceki 124 + 6 + 2), 1 uyarı (önceden de vardı, protobuf) |
| Aynı testler `torch`/`torchvision`/`ultralytics` içe aktarması engellenmiş hâlde | **132 geçti** (kabul ölçütü: 3.1 testleri torch'suz geçer) |
| `ruff format` + `ruff check` (`tez/sim/ruff.toml`, ruff 0.16.9) | temiz |
| `tez/pin/verify_pin.sh --worktree` | **KILIT SAGLAM (v1.17.0)** |
| `sha256sum ~/auto-follow-modeller/person_detection_model_v0.2.pt` | `c5f6838be50c2c09ca788e97381b68567f0df3f20e430905142ce88f8abaa440`, 22 525 930 bayt (beklenenle aynı) |
| `$P -m pip check` (ekip venv'i) | `No broken requirements found.` |
| Duman: `YoloAlgilayici` ağ engelliyken | v0.2 yüklendi; `names {0: 'Person'}` → sınıf 0; `imgsz` 640 (`.pt`'den), adım 32; ısınma 1.1 s; **0 ağ çağrısı**; iş parçacığı 4; `~/.config/Ultralytics` yok |
| Duman (3.9): `onizleme.py --senaryo kalabalik_park --zaman 62,66` → `model_dene.py --kare … --tekrar 10` | Kareler kaydedildi (yeniden düzenlenen `onizleme.py` çalıştı); 4 ve 3 kutu; `model_ms` ort. 61 ms; log'da indirme satırı yok (tek "indirme" kelimesi aracın "indirme ve analitik kapalı" satırı) |
| `model_dene.py --senaryo kalabalik_park --zaman 62,66,73,78 --tekrar 5` | 4 kare; aynı anlarda `--kare` ile birebir aynı sonuç (görüntü ve model belirlenimci); görseller aşağıda |
| Hata yolları (`model_dene.py`, sim açılmadan) | `--model ~/auto-follow-modeller/yolov8s.pt` → kaynak + "Almak için" + `--model` önerisi, çıkış 2; `--imgsz 650` → adım hatası; `--sinif kedi` → "modelin sınıfları: 0: Person"; `--conf 0` → `algilama.conf` hatası; ultralytics yokken → "model-requirements.txt ile kurulur"; `--senaryo yok_boyle` → mevcut senaryoları listeler; `--zaman 62,x` / `--kamera 0,0,10` → bayrak adıyla biçim hatası (son üçü model yüklenmeden, çıkış 2) |

Her Gazebo koşusundan sonra çalışan PX4/Gazebo süreci kalmadı (`pgrep -x px4`, `pgrep -f "^gz sim"` boş). Başlamadan
önce de kontrol edildi; kullanıcının 17:25'teki `kalabalik_park` koşusu bitmişti.

## `model_ms` (bu laptop, CPU)

Ölçüm yeri: AMD Ryzen 7 5800H (8 çekirdek / 16 iş parçacığı), ekip venv'i, `YoloAlgilayici` (`model_ms` = renk
çevirme + ön işleme + çıkarım + son işleme). **Model koşarken Gazebo kapalıydı** (`model_dene.py` kareleri önce
çeker, Gazebo'yu kapatır, sonra modeli çalıştırır); simle birlikte koşarken CPU paylaşılacağı için 4. grupta
koşu içinde yeniden ölçülür.

| Durum | `model_ms` |
|---|---|
| `kalabalik_park` kareleri (2304×1296), `imgsz` 640, 4 çekirdek | kare ortalamaları **57–66 ms** (iki `--senaryo` koşusu, 5'er çalıştırma; tek tek en az 56, en çok 80); `--kare` ile 10'ar çalıştırma ort. 56 ve 66 ms; ayrıntı: ön işleme 1.0–1.3 + çıkarım 53–63 + son işleme 0.5 ms |
| İlk çağrı (tahminci kurulumu, kurucuda ısınma) | 1.02–1.11 s |
| Aynı kare, 8 çekirdek | 46 ms (10 çalıştırma) |
| `imgsz` 1280, 4 çekirdek | 227–474 ms (4 kare) |

Beklenti (4. grup için): kamera 30 kare/s (33 ms arayla) üretir; ~60 ms'lik model en çok ~15 kare/s işler, yani
Gazebo kapalıyken bile karelerin yaklaşık yarısı atlanır. Spec bunu zaten öngörüyor (en yeni kare işlenir, atlanan
sayılır); `atlanan_kare_orani` 4. grupta ölçülür.

## Gözlem: v0.2 bu dört karede (ölçüt değil, göz kararı)

Sabit kamera (0, 0, 10 m), 45° aşağı, doğuya; `imgsz` 640, `conf` 0.25. Kırmızı: model; mavi: hakemin hedef kutusu;
turuncu: hakemin diğer insanları.

| Kare | Görünen kişiler (hakem) | v0.2 buldu | Kaçırdı |
|---|---|---|---|
| 62 s | 4 (hedef, sarılı, mavili, kırmızılı) | 4 (güven 0.60–0.79; hedef 0.69, kutusu hakemle neredeyse aynı) | — |
| 66 s | 5 | 3 | hedef; beyaz-bej giysili kişi (insan1) |
| 73 s | 4 (hedef çamın arkasında, yalnız birkaç piksel) | 3 | beyaz-bej giysili kişi |
| 78 s | 3 (+ kadraj kenarında yalnız ayakları görünen biri) | 2 (hedef 0.34, mavili 0.52) | sarılı kişi |

Aynı kareler `imgsz` 1280'de: 66 s'de 5/5 (hedef 0.84, beyaz-bej 0.34), 73 s'de 4/4, 78 s'de 3/3, güvenler çoğunlukla
0.8–0.9; ama 4–8 kat yavaş. 640'ta insan modele ~42–56 px boyunda giriyor (640/2304 ölçeği). Bu bir **açık karar**
olarak spec'e yazıldı; varsayılan `.pt`'deki 640 kalır. Model kalitesinin asıl ölçümü 4. ve 7. gruptadır.

## Görseller

`~/Desktop/Follow/3_m06_Simulasyon/Deneme/` (repo dışı):

| Dosya | Ne |
|---|---|
| `gorev3_model_kare.jpg` | **Ana görsel:** 62 s, 4/4 bulundu; hedefin kırmızı (model) ve mavi (hakem) kutuları üst üste |
| `gorev3_model_kare_t066.jpg`, `_t073.jpg`, `_t078.jpg` | Kaçırma örnekleri (yukarıdaki tablo) |
| `gorev3_model_kare_t066_imgsz1280.jpg` | 66 s, `imgsz` 1280: 5/5 (yalnız model kutuları) |

Kaynakları: `tez/sim/sonuclar/gorev3_model_kalabalik_park/` (ham kareler `kare_<t>.png` + `*_model.jpg`) ve
`tez/sim/sonuclar/gorev3_onizleme_kalabalik_park/`; ikisi de git dışı.

## Karşılaşılan sorunlar

- **torch 2.15 + torchvision 0.29:** pip resmî olmayan bir ikili seçti (yukarıda); 2.14.1 sabitlendi.
- **ultralytics iş parçacığını değiştiriyor:** karar 5.
- **`setuptools` ≥ 81'de `pkg_resources` yok:** karar 2.
- **Pillow'da Türkçe harf yok:** karar 14. Aynı sorun `onizleme.Frames.annotate`'teki "Hedef görünmüyor"
  yazısında da var (ö, ü); ayrıca kadrajın üst kenarındaki bir kişinin hakem etiketi kadraj dışına (y < 0)
  çiziliyor. İkisi de 8. grupta `annotate` `video.py`'ye taşınırken düzeltilmeli (bu grupta dokunulmadı).
- **`VERSIONS.md`'nin sürüm kontrolü satırı** ilk yazımda `import ultralytics` yapıyordu; bu, kapatmaya
  çalıştığımız `~/.config` yazımını ve DNS kontrolünü tetiklerdi. `importlib.metadata` ile okunacak şekilde
  düzeltildi; `VERSIONS.md`'ye "ultralytics'i kendiniz import etmeyin, `yolo` komutunu çalıştırmayın" notu eklendi.
- **Test hatası:** yalnız rakamlı sahte özet YAML'da sayı okundu (karar 9); test düzeltildi, kod değişmedi.
- **Ortamda gördüğüm ama bu işin dışında kalan:** `~/.local`'deki `fonttools` 4.66.1 ve `coverage` 7.16.2,
  `requirements-lock.txt`'te 4.66.0 ve 7.16.1 yazıyor (biri sonradan güncellemiş); `pip check` temiz.
  `analiz-requirements.txt`'te ipython/MAVProxy'nin dört bağımlılığı sabit değil (yukarıda).

## Açık kararlar ve bekleyenler

- **Yusuf Ortatepe:** önerdiği `conf`/`iou` (dosyada eğitim `conf`'u yok), eğitimde kullandığı torch sürümü
  (dosyada yazmıyor), veri setinde eğik/üstten görüntü olup olmadığı, `imgsz` 640 mı 1280 mi (yukarıdaki gözlem).
- **Hüseyin:** model dosyalarının ortak depolama yeri (`modeller.yaml` `kaynak` ve `alma` alanları o zaman
  güncellenir); çatıdaki `tech-stack.md` / `docs/02` güncellemesi (14. grup) bu sürümlerle.
- **`yolov8s.pt`:** 13. grupta elle indirilir, özeti `modeller.yaml`'a yazılır.

## Sonraki gruplar için notlar

- **4. grup:** sim açılmadan ana süreçte `algilama.inspect_model(model_path(sc.detection.model), load_catalog())`;
  `ModelFile.as_dict()` → `ayarlar.algilama`; uyarı varsa rapora. `YoloAlgilayici` model sürecinin içinde ("spawn")
  kurulur, böylece ortam değişkenleri o süreçte ultralytics'ten önce ayarlanır; kurucu ısınmayı yaptığı için ilk
  kare yavaş değildir. `to_boxes`'un testleri 4.1'de. Ara durum satırlarını (`algilama.*`,
  `henuz_bagli_degil["algilama.etkin"]`) bu grup siler.
- **8. grup:** `annotate`'teki Türkçe harf ve kenar dışı etiket sorunu (yukarıda); `model_dene.draw` ile aynı yazı
  tipi yaklaşımı ortaklaştırılabilir.
- **13. grup:** `kur.sh` model kontrolü `algilama.load_catalog` + `inspect_model`'i kullanabilir (indirmez).
- **14. grup:** çatıya yazılacak sürümler: ultralytics 8.4.174, torch 2.14.1+cpu, torchvision 0.29.2+cpu (CPU
  dizini), AGPL-3.0 notu; "Laptop'ta Hailo olmadan algılama" satırı için: simde laptop CPU'sunda Ultralytics.

---

## Kendin dene

Bu bölümdeki her şey bilgisayarında hazır: paketler kurulu, model dosyası yerinde. PX4 gerekmiyor.

**Başlamadan:** Terminal açmak için **Ctrl+Alt+T**'ye bas. Aşağıdaki gri kutulardaki komutları kopyala, terminale
**Ctrl+Shift+V** ile yapıştır (terminalde Ctrl+V çalışmaz) ve **Enter**'a bas. Bir komutu yarıda kesmek için
**Ctrl+C**.

### 1. Hazırlık (her yeni terminalde bir kez)

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot
P=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python
```

Bir şey yazmaz; bu normal. `P`, ekibin Python'unun kısaltmasıdır. Terminali kapatıp açarsan bu iki satırı yine
yapıştır.

### 2. Hazır görsele bak

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev3_model_kare.jpg
```

Resim görüntüleyicide simdeki çayır açılır (dron kamerasının 10 m yükseklikten, 45° aşağı bakışı):
- **Kırmızı kutular:** modelin bulduğu insanlar; altında güveni (ör. `Person 0.69`, 1'e yakın = emin).
- **Mavi kutu ("HEDEF"):** simin bildiği gerçek hedef (hakem). Kırmızı ile mavi üst üste ise model hedefi doğru
  bulmuş.
- **Turuncu kutular:** simin bildiği diğer insanlar.
- Altta: model dosyası, ayarlar ve bu karedeki süre (`model_ms`).

Aynı klasördeki `gorev3_model_kare_t066.jpg`'de model iki kişiyi kaçırıyor (turuncu/mavi kutu var, kırmızı yok);
`gorev3_model_kare_t066_imgsz1280.jpg`'de aynı kare daha büyük girişle, hepsi bulunmuş.

### 3. Kendin üret (Gazebo penceresiz açılır, ~1.5 dakika)

Önce başka bir sim (Gazebo ya da PX4) açıksa kapat. Sonra:

```bash
$P tez/sim/araclar/model_dene.py --senaryo kalabalik_park --zaman 62,66,73,78
```

Terminalde şöyle satırlar görürsün:

```text
Model: /home/ahmet/auto-follow-modeller/person_detection_model_v0.2.pt (22525930 bayt)
  sha256 c5f6838b... (modeller.yaml'da person_detection_model_v0.2.pt)
  Model yükleniyor (ultralytics, CPU; indirme ve analitik kapalı)...
  sınıflar {0: 'Person'} -> 0 (Person) · imgsz 640 (eğitim 640, adım 32) · conf 0.25 · 4 çekirdek · ilk çağrı (hazırlık) 1022 ms
Gazebo açıldı; 78 s simülasyon zamanı bekleniyor...
kare_0062.00.png: 4 kutu (Person 0.79, Person 0.72, Person 0.69, Person 0.60) · model_ms 64 ms [...]
  -> tez/sim/sonuclar/20261111_..._model_kalabalik_park/kare_0062.00_model.jpg
...
Ortalama model_ms: 64 ms (4 çalıştırma, 4 kare)
```

"Gazebo açıldı" satırından sonra ~1 dakika bekler; bu sırada sim 78 saniyelik sahneyi oynatıyor. Bitince
sonuçları aç:

```bash
xdg-open tez/sim/sonuclar/
```

En yeni `..._model_kalabalik_park` klasörüne gir: `kare_0062.00.png` modelin gördüğü ham kare,
`kare_0062.00_model.jpg` kutular çizilmiş hâli.

### 4. Ayarlarla oyna

Komutun sonuna şunları ekleyebilirsin (hepsini birden de):

| Ekle | Ne olur |
|---|---|
| `--imgsz 1280` | Model resmi daha büyük görür: küçük insanları daha iyi bulur, ama ~4–8 kat yavaş |
| `--conf 0.5` | Yalnız güveni 0.5'ten büyük kutular çizilir |
| `--cekirdek 8` | Model 8 çekirdek kullanır (varsayılan 4; simde kalanı Gazebo ve PX4'e kalsın diye) |
| `--tekrar 10` | Her karede modeli 10 kez çalıştırır; ortalama, en az ve en çok süreyi yazar |
| `--zaman 3` | Başka anlar (saniye, virgülle); insanlar 60. saniyede yürümeye başlar |

Örnek, Gazebo'yu yeniden açmadan, az önce çekilen karelerden biriyle (yolu kendi klasörünle değiştir; dosyayı
terminale sürükleyip bırakırsan yolu kendisi yazar):

```bash
$P tez/sim/araclar/model_dene.py --kare tez/sim/sonuclar/gorev3_model_kalabalik_park/kare_0066.00.png --imgsz 1280
```

Çıktı aynı klasörde `kare_0066.00_model.jpg` olur (öncekinin üstüne yazar).

### 5. Kendi fotoğrafında dene

Herhangi bir PNG/JPG olur (ör. telefondan aktardığın bir fotoğraf):

```bash
$P tez/sim/araclar/model_dene.py --kare ~/Resimler/foto.jpg
```

`~/Resimler/foto.jpg` yerine kendi dosyanın yolunu yaz (ya da `--kare ` yazıp dosyayı terminale sürükle). Çıktı
fotoğrafın yanında `foto_model.jpg` olarak çıkar. Bu kipte hakem kutusu yoktur, yalnız kırmızı kutular.

### 6. Kontroller

```bash
$P -c "from importlib.metadata import version as v; print(v('torch'), v('torchvision'), v('ultralytics'))"
sha256sum ~/auto-follow-modeller/person_detection_model_v0.2.pt
$P -m pytest tez/sim/testler -q
```

Beklenen: `2.14.1+cpu 0.29.2+cpu 8.4.174`; `c5f6838be50c2c09ca788e97381b68567f0df3f20e430905142ce88f8abaa440`;
`132 passed`.

### Bir şey ters giderse

| Mesaj | Ne yapmalı |
|---|---|
| `Zaten çalışan bir PX4 veya Gazebo var` | Açık simi kapat (kendi terminalinde Ctrl+C) ve tekrar dene |
| `Model dosyası yok: ...` | Mesajdaki "Almak için" komutunu çalıştır (`<Vision klasörü>` = `~/Desktop/Projects/Auto-Follow/Vision`) |
| `ultralytics kurulu değil` | `tez/env/VERSIONS.md` → "Sim model paketleri" bölümündeki kurulum komutu |
| `algilama.imgsz: modelin adımının (32 px) katı olmalı` | `--imgsz` için 32'nin katı bir sayı ver (640, 960, 1280…) |
| `Gazebo kareleri gelmedi` | Çıktı klasöründeki `sim.log`'a bak; bir kez daha dene |
