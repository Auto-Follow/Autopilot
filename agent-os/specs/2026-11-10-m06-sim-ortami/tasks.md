# Görev Dağılımı: m06 Simülasyon Ortamı

- Spec: `spec.md` (tasarımın tek kaynağı) · gereksinimler: `planning/requirements.md` · görseller: `planning/visuals/blok_diyagram_elle.jpeg`, `planning/visuals/blok_diyagram_dijital.mmd`
- Dal `ozellik/m06-sim-ortami` · PR başlığı `[M06] Simülasyon ortamı` · son teslim 15.11.2026 (bugün 10.11.2026)

## Genel Bakış

| Bölüm | Görev grupları | Nerede |
|---|---|---|
| Faz A, kritik yol: **15.11 en az demo** | 1–9 | bu dal, ilk PR |
| Faz A, kalanlar (15.11'den sonra da olabilir, ama **aynı PR'da ve merge'den önce**; Faz B'ye kaymaz) | 10–13 | bu dal, ilk PR |
| Faz A, çatı repo | 14 | **ayrı repo** (`~/Desktop/Projects/Auto-Follow`), ayrı dal, ayrı PR |
| Faz B | 15–17 | ikinci PR, 15.11'den sonra |

Toplam: 17 görev grubu (Faz A: 13 bu dalda + 1 çatıda; Faz B: 3).

### Her grup için geçerli kurallar

- **Önce test:** Her grup 2–8 odaklı birim testiyle başlar (pytest, donanımsız, simsiz; `ultralytics`/`torch` gerekmez). SITL koşuları birim testi sayılmaz; doğrulama alt görevinde ayrıca yapılır. Mevcut 76 test her grupta geçmeye devam eder.
- **Doğrulama komutları** (her grubun son alt görevinde açıkça tekrarlanır):

  ```bash
  cd ~/Desktop/Projects/Auto-Follow/Autopilot
  P="${TEZ_PYTHON:-$HOME/Desktop/Projects/Auto-Follow/.venv-tez/bin/python}"
  S=tez/sim/araclar
  $P -m pytest tez/sim/testler -q                                    # birim testleri (birkaç saniye)
  $P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim   # ruff 0.16.9
  tez/pin/verify_pin.sh --worktree                                   # beklenen: KILIT SAGLAM
  ```

  Gazebo penceresiyle çalışırken AMD hibrit GPU için önce `export DRI_PRIME=1` (otomatik koşularda `--ekransiz`).
- **Görsel kontrol:** Video üreten gruplarda Ahmet `kosu.mp4`'ü VLC'de açar (`vlc tez/sim/sonuclar/<klasör>/kosu.mp4`). Bir düzeltme, sorunun gösterildiği sahne yeniden koşularak doğrulanır.
- **Commit (kural 10):** Grup bittiğinde ve doğrulaması geçtiğinde commit atılır: `2026-11-10-m06-sim-ortami: Görev grubu <N> — <ne yapıldı>`. Önce `git rev-parse --show-toplevel` ile Autopilot reposunda ve `ozellik/m06-sim-ortami` dalında olunduğu kontrol edilir. Dosyalar adıyla eklenir (`git add -A` / `git add .` yok). Push, PR, amend, rebase ve `reset --hard` yalnız kullanıcı isteyince yapılır.
- **Belgeleme (kural 11):** Her grup kararlarını, test sonuçlarını ve karşılaşılan sorunları `implementation/gorev-grubu-<NN>.md` dosyasına yazar. SITL koşularının özet sayıları ve commit'leri ayrıca `implementation/kabul-kosulari.md` tablosuna eklenir. Video ve ULog yazılmaz (kural 9). Tasarım spec'ten saparsa `spec.md` aynı commit'te güncellenir.
- **Kod kuralları:** Kod, değişken adları ve yorumlar İngilizce; belgeler Türkçe. `tez/sim` çalışma anında `../Vision` ya da çatıya bağlanmaz (kural 7). PX4, ROMFS ve submodule dosyası değişmez; `allowed-paths.txt` genişletilmez. Yeni Python modülü `tez/sim/ruff.toml` içindeki `known-first-party` listesine eklenir.
- **Sürüm sabitliği (kural 4):** Yeni bir paket, sürümü `tez/env/VERSIONS.md`'ye (ve gerekiyorsa requirements dosyasına) yazılmadan kullanılmaz. Bu yüzden sürüm sabitleme, paketi ilk kullanan grubun içindedir (3: `ultralytics`/`torch`, 8: `ffmpeg`, 11: GStreamer); 13. grup yalnız tamamlar.

### Dış kişilere bağlı işler ve o arada nasıl ilerlenir

| Kim | Ne bekleniyor | Etkilenen grup | O arada |
|---|---|---|---|
| Hüseyin (onay bekliyor) | (b) yolu ve iskelet modülün PR'dan çıkarılması | 1 | (b) yoluyla ilerlenir. 1. grup tek ve ayrı bir commit olduğu için reddedilirse `git revert` ile geri alınabilir. |
| Hüseyin (onay bekliyor) | Ortak model depolama yeri; m06/m08 sınırı | 3, 13 | Varsayılan `~/auto-follow-modeller/` + `--model`. `modeller.yaml`'daki `kaynak` alanı karar gelince güncellenir. |
| Hüseyin (onay bekliyor) | Çatı `tech-stack.md` / `docs/02` güncellemesi; Gazebo standardında AMD ifadesi | 14 | Metin hazırlanır; çatı PR'ı açılmadan önce kullanıcıya ve Hüseyin'e sorulur. |
| Yusuf Ortatepe | v0.2 üst verisinin teyidi (sınıf, imgsz, önerilen `conf`/`iou`, eğitim sürümleri) | 3, 4 | Spec'teki bayt taramasıyla okunan üst veri kullanılır; sınıf adı `.pt`'den okunur, `--imgsz`/`--conf`/`--sinif` ile değiştirilebilir. Teyit gelince spec "Model dosyası" tablosu güncellenir. |
| Yusuf Kurt / Yusuf Algan | Modülün yeri ve başlatma komutu, `TEZ_LOS` biçiminin uygunluğu. Ekipten gelen bilgi (09.11, Yusuf Algan; kesinleşmiş değil, m15/m16 spec'inde yazılınca o geçerli): mod adı **"AUTO FOLLOW"** (QGC'de böyle görünecek), parametre öneki **`AF_`** (`AF_XXX`); m15/m16 spec'inde kesinleşmesi | 5, 10, 13 | `tez_los` mekanizması stok "Hold" adıyla ve iskelet modülle (`c4b4abf342`, ağaç dışında açılır) denenir; modül gelince `--mod-adi "AUTO FOLLOW"` (kod değişmez, mod adla seçilir). `m06_kabul.sh`'taki 3. koşu modül hazır olunca koşulur. |

---

## Faz A — Kritik Yol: 15.11 En Az Demo

### PX4 Tarafı

#### Görev Grubu 1: (b) yolu — stok 4001, başlangıç parametreleri, F0 uyarlaması
**Bağımlılık:** Yok · **Emek:** ~0.75 gün · **Onay:** Hüseyin'in onayı bekleniyor (yine de ilerlenir)

- [x] 1.0 PX4 dosyalarına dokunmadan stok 4001 + gerçek dron ayarlarıyla simi açmak
  - [x] 1.1 Testleri yaz: `testler/test_parametreler.py` (5–7 test)
    - Yorum ve boş satır atlanır; `AD DEĞER  # kaynak` ayrıştırılır
    - Ad `^[A-Z0-9_]{1,16}$`'e uymazsa ya da değer sayı değilse satır numarası ve adla reddedilir
    - Yükleme sırası: `gercek_dron.params` → `sim.params` → `takip.px4_parametreleri` → `--param` (sonuncu kazanır)
    - `--param AD=DEĞER` ayrıştırma ve hatalı biçimin reddi
    - `PX4_PARAM_<AD>=<değer>` listesinin üretimi
    - `test_hedef.py`'ye: `drone.mod` artık reddedilir; `takip.kaynak` verilmezse `yok`
  - [x] 1.2 Başlangıç parametre dosyalarını oluştur
    - `tez/sim/parametreler/gercek_dron.params`: `4030_gz_x500_tez`'teki 7 kazanç satırı (4019) + 22.08 davranış parametreleri (spec "Başlangıç parametreleri" tablosu), her satırda `# kaynak`
    - `tez/sim/parametreler/sim.params`: `SDLOG_PROFILE 163`
    - `~/Desktop/Follow/4_Ucus/Drone parametreleri/22.08.2026.params` v1.17.0 varsayılanlarıyla (derleme çıktısındaki parametre meta verisi) tek seferlik bir betikle karşılaştırılır. Seçim kuralı spec 1. maddededir (dahil / hariç). Betik repoya girmez; sonuç tablosu `implementation/gorev-grubu-01.md`'ye yazılır. 22.08 dosyası repoya girmez.
  - [x] 1.3 PX4 dosyalarını v1.17.0 hâline döndür
    - Kazançlar 1.2'de taşındıktan **sonra** `4030_gz_x500_tez`, `4030_gz_x500_tez.post`, `airframes/CMakeLists.txt` `main`'deki hâline döndürülür
    - `tez/px4/` daldan çıkarılır (yeni bir silme commit'iyle; geçmiş yeniden yazılmaz). İskelet modül `c4b4abf342` commit'inde okunabilir kalır.
  - [x] 1.4 Parametre ayrıştırıcısını yaz: `araclar/parametreler.py` (yeni)
    - Ayrıştırma, birleştirme sırası, `PX4_PARAM_*` ortam listesinin üretimi; `calistir.sh`'ın çağırabileceği küçük bir komut satırı girişi
    - Yorumlayıcı `TEZ_PYTHON`'dan, yoksa ekip venv'inden alınır (`f0_kabul.sh` deseni)
  - [x] 1.5 `tez/sim/calistir.sh`'ı (b) yoluna geçir
    - `PX4_SYS_AUTOSTART=4001`, `PX4_GZ_MODEL_NAME=x500_tez_0`, `PX4_GZ_WORLD=<dünya>`, `PX4_SIM_MODEL=x500_tez`
    - İki `.params` dosyası + `--param AD=DEĞER` (birden çok) → `PX4_PARAM_*`
    - Her açılışta `parameters*.bson` silinir
    - `--ekransiz`, `--dunya`, `--temiz` ve PX4'ü kapatma yolu aynen kalır
  - [x] 1.6 `tez/sim/derle.sh`: `tez/px4/src/CMakeLists.txt` yoksa stok `px4_sitl_default` (+ `px4_gz_plugins`) `build/px4_sitl_tez`'e derlenir. (`--harici` 10. grupta.)
  - [x] 1.7 `simulasyon.py` ve `px4_baglanti.py`
    - Hazır satırı `"registered as"` yerine `"Startup script returned successfully"`
    - Parametreler `calistir.sh`'a aktarılır; "unresponsive" kontrolü yalnız harici modlu koşuda (bayrak; 10. grupta kullanılır)
    - `TEZ_MODE_NAME` kaldırılır; `get_param` (`PARAM_REQUEST_READ`) eklenir
  - [x] 1.8 Senaryoyu iskelet modsuz hâle getir (en az değişiklik; tam şema 2. grupta)
    - `hedef.py`: `drone.mod` kalkar; `takip.kaynak` yalnız `yok` (→ "Hold") kabul edilir
    - `senaryo.py` modu "Hold" olarak adıyla seçer; `rapor.py` "dron modu" yerine takip kaynağını yazar
    - 3 senaryo `takip: {kaynak: yok}` olur
  - [x] 1.9 `f0_testi.py`'yi uyarla
    - Kamera çözünürlüğü, hızı, fx (mevcut)
    - `SYS_AUTOSTART == 4001`; iki `.params` dosyasındaki her satır PX4'te aynı değerde (`get_param`)
    - "Hold" ve "Follow Target" AVAILABLE_MODES'ta
    - 10 m kalkış; Hold'da 15 s konum tutma (sapma < 0.5 m); iniş, disarm, temiz kapanış
  - [x] 1.10 `tez/sim/README.md`'den iskelet modül ve ROMFS satırlarını çıkar, kısa bir "(b) yolu" bölümü ekle (tam yeniden yazım 13. grupta); `ruff.toml`'a `parametreler` ekle
  - [x] 1.11 Doğrulama

    ```bash
    $P -m pytest tez/sim/testler/test_parametreler.py tez/sim/testler/test_hedef.py -q
    $P -m pytest tez/sim/testler -q
    $P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim
    tez/pin/verify_pin.sh --worktree          # KILIT SAGLAM (bugün bu dalda KILIT BOZULMUS)
    git diff --stat main -- ROMFS tez/px4     # boş olmalı
    tez/sim/derle.sh
    $S/f0_kabul.sh                            # SONUÇ: GEÇTİ
    $S/f1_kabul.sh                            # SONUÇ: GEÇTİ (iki koşunun hedef farkı ≤ 0.15 m)
    ```

    `build/px4_sitl_tez/rootfs/` altındaki sim log'unda "Unknown model" olmadığı ve parametrelerin `param show` ile yüklendiği görülür.

**Kabul Ölçütleri:**
- 1.1'deki testler ve mevcut 76 test geçer; `verify_pin.sh --worktree` "KILIT SAGLAM" verir
- `f0_kabul.sh` ve `f1_kabul.sh` stok 4001 ile geçer; parametre dosyalarındaki her değer PX4'te doğrulanır
- ROMFS ve `tez/px4` `main` ile aynıdır

### Senaryo Altyapısı

#### Görev Grubu 2: Senaryo şeması ve komut satırı
**Bağımlılık:** Görev Grubu 1 · **Emek:** ~0.3 gün

- [x] 2.0 Faz A'nın bütün senaryo alanlarını ve bayraklarını tek yerde tanımlamak
  - [x] 2.1 Testleri yaz: `test_hedef.py`'ye (5–7 test)
    - Yeni bloklar varsayılanlarıyla okunur (`takip`, `algilama`, `gecikme`, `kusurlar`, `video`; spec "Senaryo alanları" tablosu)
    - Yanlış alan adı ya da değer, alan adıyla reddedilir (`_check_keys`, `_number` deseni)
    - `takip.kaynak: tez_los` iken `mod_adi` zorunlu
    - `algilama.etkin: false` iken `takip.los: model` reddedilir
    - `takip.px4_parametreleri` ad kuralı (1. gruptaki ayrıştırıcıyla aynı)
    - Komut satırı YAML'ı ezer; geçerli ayarların hepsi `ayarlar` sözlüğünde toplanır
  - [x] 2.2 `hedef.py`: yeni bloklar ve doğrulama (`kusurlar` burada yalnız sözlük olarak alınır; anahtarları 4. grupta `kusurlar.py` doğrular)
  - [x] 2.3 `senaryo.py` bayrakları: `--model`, `--imgsz`, `--conf`, `--sinif`, `--modelsiz`, `--takip`, `--mod-adi`, `--los`, `--param` (çoklu), `--px4-baslat` (çoklu), `--gecikme-ms`, `--qgc`, `--videosuz`, `--kareleri-sakla`
    - Geçerli ayarlar (PX4'e yüklenen parametreler dahil) `ozet.json` → `ayarlar` alanına yazılır
  - [x] 2.4 `senaryolar/takip_yuruyen.yaml`: `yuruyen_insan` yolu, `takip: {kaynak: follow_me, los: model}`, yükseklik 8 m, `FLW_TGT_DST 8`
  - [x] 2.5 Ara durum kuralı: Sonraki gruplarda bağlanacak bir ayar varsayılan dışında verilirse (ör. `follow_me`, `tez_los`, `gecikme.ek_ms ≠ 0`, `--qgc`) `senaryo.py` koşuyu başlatmadan "Görev grubu N'de bağlanacak" hatası verir. Bu hata ilgili grupta kaldırılır; sessizce yok sayılan ayar olmaz.
  - [x] 2.6 Doğrulama

    ```bash
    $P -m pytest tez/sim/testler/test_hedef.py -q
    $P -m pytest tez/sim/testler -q
    $P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim
    tez/pin/verify_pin.sh --worktree
    $S/f1_kabul.sh                                                 # GEÇTİ
    $P $S/senaryo.py --senaryo takip_yuruyen --ekransiz            # sim açılmadan "Görev grubu 6'da bağlanacak" hatası
    ```

**Kabul Ölçütleri:**
- 2.1'deki testler geçer; bütün Faz A alanları ve bayrakları ayrıştırılır
- Hatalı alan adı hangi alan olduğunu söyler; henüz bağlanmamış ayar sessizce yok sayılmaz

### Görüntü ve Model

#### Görev Grubu 3: Model ortamı — sürüm sabitleme, model dosyası, model yolu
**Bağımlılık:** Görev Grubu 2 · **Emek:** ~0.4 gün · **Bekleyen:** Ortatepe teyidi, Hüseyin'in depolama kararı

- [x] 3.0 v0.2 modelinin, sabit sürümlü paketlerle laptop CPU'sunda yüklenebilmesi
  - [x] 3.1 Testleri yaz: `testler/test_algilama.py`, 1. kısım (4–6 test)
    - Model yolu önceliği: `--model` > `algilama.model` > `~/auto-follow-modeller/person_detection_model_v0.2.pt`
    - Dosya yoksa hata, dosyanın nereden alınacağını söyler
    - sha256 hesaplanır; `modeller.yaml`'daki özetten farklıysa uyarı verilir
    - Sınıf çözümü (bir `names` sözlüğüyle): `Person`/`person` → 0; numara; olmayan ad → mevcut adları listeleyen hata
  - [x] 3.2 Sürümleri belirle (uydurulmaz)
    - Scratchpad'de temiz bir Python 3.12 venv'inde CPU `torch`/`torchvision` (PyTorch CPU dizini) ve `ultralytics` kurulur. Önce `.pt`'yi kaydeden 8.4.174 denenir; seçilen sürüm dosyayı yükleyebilmelidir.
    - `ultralytics`'in çektiği `opencv-python`, `analiz-requirements.txt`'teki 5.0.0.93 ile uyumlu olmalıdır
    - `pip freeze` → `tez/env/model-requirements.txt` (bütün bağımlılıklar sabit sürümle; dizin adresi dosyada yorum olarak)
  - [x] 3.3 `tez/env/VERSIONS.md`: model paketleri satırı, kurulum komutu, Ultralytics AGPL-3.0 notu (model yalnız yerel simde çalışır, dağıtılmaz)
  - [x] 3.4 Ekip venv'ine kur: `$P -m pip install -r tez/env/model-requirements.txt` (dizin seçeneğiyle)
  - [x] 3.5 Model dosyasını yerleştir (repo dışı, kural 9)
    - `mkdir -p ~/auto-follow-modeller && git -C ../Vision show ebff718:models/person_detection_model_v0.2.pt > ~/auto-follow-modeller/person_detection_model_v0.2.pt` (yalnız okuma; Vision reposu değişmez)
    - `sha256sum` → `c5f6838be50c2c09ca788e97381b68567f0df3f20e430905142ce88f8abaa440`, boyut 22 525 930 bayt
  - [x] 3.6 `tez/sim/modeller.yaml` (yeni): v0.2 kaydı (ad, sha256, boyut, kaynak: "Vision `model-training` `ebff718`, geçici"). `yolov8s.pt` kaydı TBD olarak açılır; 13. grupta doldurulur.
  - [x] 3.7 `araclar/algilama.py`, 1. kısım: `Kutu` (`u0, v0, u1, v1, guven, sinif, sinif_adi`), `Algilayici` arayüzü, model yolu çözümü, sha256, sınıf çözümü. `ultralytics` yalnız `YoloAlgilayici` içinde içe aktarılır.
  - [x] 3.8 `YoloAlgilayici`: `device=cpu`, `torch.set_num_threads(cekirdek)` (varsayılan 4), `imgsz` varsayılanı `.pt`'deki eğitim değeri, `conf` 0.25; otomatik model/yazı tipi indirme ve analitik kapalı
  - [x] 3.9 Doğrulama

    ```bash
    $P -m pytest tez/sim/testler/test_algilama.py -q
    $P -m pytest tez/sim/testler -q
    $P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim
    tez/pin/verify_pin.sh --worktree
    sha256sum ~/auto-follow-modeller/person_detection_model_v0.2.pt
    $P -m pip check
    ```

    Duman testi: `YoloAlgilayici` v0.2'yi yükler, `names`, `imgsz` ve kayıtlı bir Gazebo karesinde (`onizleme.py` çıktısı) `model_ms` değerini yazar; log'da indirme satırı yoktur. Sonuçlar `implementation/gorev-grubu-03.md`'ye.

**Kabul Ölçütleri:**
- 3.1'deki testler `ultralytics`/`torch` olmadan geçer
- Paketler `model-requirements.txt` ve `VERSIONS.md`'ye yazılmadan kullanılmamıştır
- v0.2 CPU'da yüklenir, sınıf `Person` (0) olarak çözülür; `.pt` repoda yoktur

#### Görev Grubu 4: Kare okuyucu, kusur aşaması, model süreci ve `algilama.csv`
**Bağımlılık:** Görev Grubu 3 · **Emek:** ~0.75 gün

- [x] 4.0 Gazebo kamera görüntüsünün laptopta okunup modelden geçirilmesi; gecikme ve kare atlamanın ölçülmesi
  - [x] 4.1 Testleri yaz (6–8 test)
    - `test_kusurlar.py`: boş ayarda kare bit bit aynı; Faz B alanı (`gurultu`, `bulaniklik`, `rolling_shutter`, `pozlama`) "Faz B'de uygulanacak" hatası verir; bilinmeyen alan reddedilir
    - `test_algilama.py`, 2. kısım: taklit Ultralytics sonucundan `Kutu`'ya dönüşüm, görüntü sınırına kırpma, piksel kenarı kuralı (`u0 ≤ u < u1`); sahte algılayıcıyla arayüz
      (Dönüşüm `algilama.to_boxes` olarak 3. grupta duman testi için yazıldı, testi yok; bu alt görev onu sınar ve gerekirse düzeltir.)
    - `test_goruntu.py` (yeni, Test Planı'nda yok): yalnız en yeni kare tutulur, üzerine yazılan kare `atlanan` sayılır; sim ↔ duvar saati eşlemesi
  - [x] 4.2 `araclar/goruntu.py`: `/x500_tez/kamera/image`'a `subscribe_raw`; geri çağırma yalnız ham bayt + `time.monotonic()` + sayaç saklar; protobuf yalnız işlenecek karede çözülür; kare nesnesi (RGB `uint8` 1296×2304×3, `t`, `varis`, `sira`); `uretilen`/`atlanan` sayaçları; `/world/<dünya>/clock` ile saat eşleme (~100 Hz'e kısılır)
  - [x] 4.3 `araclar/kusurlar.py`: `KameraKusurlari.uygula(kare, t) -> kare`; Faz A'da geçişsiz; `kusur_ms` ölçülür
  - [x] 4.4 Model süreci (`multiprocessing`, "spawn"): kare okuyucu + kusur aşaması + algılayıcı; sonuçlar FIFO kuyrukla ana sürece; `basla`, `bitis`, `model_ms`. `--modelsiz` ya da `algilama.etkin: false` iken hiç başlatılmaz.
    - 3. gruptan hazır: `algilama.model_path` + `inspect_model` (dosya yoksa nereden alınacağını söyler, sha256 + `modeller.yaml` uyarısı), `YoloAlgilayici` (kurucuda ısınma; `last_model_ms`). Sim açılmadan önce ana süreçte `inspect_model` çağrılır; `ModelFile.as_dict()` `ayarlar.algilama`'ya yazılır (spec 8: "model özeti de dahildir"). `algilama.*` ara hatası ve `henuz_bagli_degil["algilama.etkin"]` bu grupta kaldırılır.
  - [x] 4.5 `senaryo.py`: model süreci kayıttan önce açılır, kayıt bitince kapanır. `algilama.csv` (işlenen kare başına zamanlar, kutu sayısı; seçim/LOS/konum sütunları 5–6. gruplarda dolar) ve `kutular.csv` (bütün kutular) `round(t*1e6)` anahtarıyla yazılır. `uretilen`, `islenen`, `atlanan_kare_orani`, `islenen_kare_hizi_hz`, RTF (0.9 altında uyarı) geçici olarak `ozet.json`'a.
  - [x] 4.6 `f1_testi.py` `--modelsiz` ile koşar; `ruff.toml`'a `goruntu`, `kusurlar`, `algilama` eklenir
  - [x] 4.7 Doğrulama

    ```bash
    $P -m pytest tez/sim/testler/test_kusurlar.py tez/sim/testler/test_algilama.py tez/sim/testler/test_goruntu.py -q
    $P -m pytest tez/sim/testler -q
    $P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim
    tez/pin/verify_pin.sh --worktree
    $S/f1_kabul.sh                                                 # --modelsiz, GEÇTİ
    $P $S/senaryo.py --senaryo kalabalik_park --ekransiz           # model açık, takip yok
    ```

    Koşu klasöründe `algilama.csv` ve `kutular.csv` doludur; `model_ms`, `atlanan_kare_orani`, RTF yazılır. Geçici kontrol: en az bir karede bir model kutusunun `dogru_cevap.csv`'deki hedef kutusuyla IoU'su ≥ 0.5'tir (bu kontrol 7. grupta `olcum.py`'ye taşınır). Sayılar `implementation/kabul-kosulari.md`'ye.

**Kabul Ölçütleri:**
- 4.1'deki testler geçer; boş kusur ayarında kare değişmez
- Model gerçekten Gazebo görüntüsünde çalışır; kuyruk büyümez, atlanan kareler sayılır
- F1 `--modelsiz` ile geçmeye devam eder

### Takip Döngüsü

#### Görev Grubu 5: Hedef seçimi, LOS (i)/(ii), `TEZ_LOS` ve adla mod seçimi
**Bağımlılık:** Görev Grubu 4 · **Emek:** ~0.75 gün · **Bekleyen:** Kurt'un mod adı (o arada stok "Hold" adıyla denenir)

- [x] 5.0 Seçilen hedefin yönünü `DEBUG_VECT` "TEZ_LOS" olarak PX4'e göndermek; `yok` ve `tez_los` kaynakları
  - [x] 5.1 Testleri yaz (6–8 test)
    - `test_takip.py`: ilk kilit (hakem kutusuyla en yüksek IoU); en yakın kutu izleme; kapı (önceki köşegenin 1.5 katı); 10 işlenen karede kilit kaybı ve `yeniden_kilit_sayisi`; LOS (i) gidiş-dönüş (bilinen poz + hedef → `project` → piksel → LOS) ile `los_govde` arasındaki açı < 0.01°
    - `test_mesajlar.py`: `DEBUG_VECT` paketleme/çözme (ad `TEZ_LOS`, birim norm, NaN = hedef yok); sonlu olmayan ya da `|norm − 1| ≥ 1e-3` vektör gönderilmez ve sayılır
    - (Uygulamada: 14 test fonksiyonu, 21 test durumu: `test_takip.py` 6 (LOS gidiş-dönüşü 8 poz/kamera durumu, takip iş parçacığının iki kaynağı), `test_mesajlar.py` 5 (akış kuralları, tek gönderim kilidi, `AVAILABLE_MODES` adları, stok mod listesinin PX4 kaynağıyla aynılığı), `test_gecikme.py` 1 (sıra), `test_kayit.py` +1 (hakemin satır + segmentasyon birleştirmesi), `test_rapor.py` +1 (ULog'daki `TEZ_LOS` sayımı ve eşleştirmesi); `test_hedef.py` ara durum testi güncellendi)
  - [x] 5.2 `araclar/takip.py`: geçici hedef seçimi; LOS (i) kutu merkezi → `Camera.pixel_to_los` (`camera_info` iç parametreleri, bozulma) → `camera_to_body(45°)`, nominal montaj; LOS (ii) hakemin `los_govde`'si (yalnız `gorunur` iken, segmentasyon karesi geldikten sonra; ek gecikme ölçülür). Dönüşüm kodu kopyalanmaz, `kamera.py` kullanılır.
  - [x] 5.3 `araclar/gecikme.py`, 1. kısım: sıra koruyan hat ve `serbest` damgası, ek gecikme 0 (yapay gecikme ve saat modeli 12. grupta)
  - [x] 5.4 `px4_baglanti.py`: tek gönderim kilidi (GCS heartbeat iş parçacığıyla çakışmaz), `send_los` (iki taraflı doğrulama); işlenen kare başına bir mesaj, en çok 30 Hz, aynı kare iki kez gitmez; hedef yoksa NaN
  - [x] 5.5 Takip iş parçacığı (`senaryo.py`): model sonucu → seçim → LOS → gecikme hattı → gönderim → `algilama.csv` satırı (seçilen kutu, LOS, durum, `ulasma_ms`, `bekleme_ms`, `uctan_uca_ms`). `TEZ_LOS` her kaynakta gider, `yok` dahil.
    (4. gruptan hazır: `algilama.ModelProcess` her `FrameResult`'ı sırayla bir iş parçacığında `on_result(sonuç, alinma)`'ya verir; `algilama.DetectionLog` satırı yazar ve sütunları `ROW_COLUMNS`'tadır; `goruntu.SimClock.to_sim` duvar saatini sim saatine çevirir. Ölçülen: sonucun FIFO'dan ana sürece geçişi (`teslim_ms`) ort. ≈ 9–10 ms, en çok ≈ 78–84 ms; ana süreçteki GIL çekişmesinden (hakemin segmentasyon çözümü), gönderim gecikmesine girer.)
    (Uygulamada: takip iş parçacığı `ModelProcess`'in sonuç iş parçacığıdır (`takip.Tracker.on_model`); hakemin kareleri `kayit.Recorder(on_frame=...)` → `tez-hakem-los` iş parçacığı. Yeni `tez_los.csv`: her `TEZ_LOS` denemesi. Ayrıntı ve ölçümler: `implementation/gorev-grubu-05.md`.)
  - [x] 5.6 Mod adla seçilir (`Vehicle.modes`, AVAILABLE_MODES): `yok` → "Hold", `tez_los` → `takip.mod_adi`; ad yoksa koşu başlamadan mevcut adları listeleyen hata. Mod numarası koda gömülmez. 2. gruptaki `tez_los` ve `--los hakem` ara hataları kaldırılır.
  - [x] 5.7 Doğrulama

    ```bash
    $P -m pytest tez/sim/testler/test_takip.py tez/sim/testler/test_mesajlar.py -q
    $P -m pytest tez/sim/testler -q
    $P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim
    tez/pin/verify_pin.sh --worktree
    $P $S/senaryo.py --senaryo kalabalik_park --ekransiz                                   # yok, LOS model
    $P $S/senaryo.py --senaryo kalabalik_park --ekransiz --takip tez_los --mod-adi "Hold"  # adla mod seçimi duman testi
    $P $S/senaryo.py --senaryo kalabalik_park --ekransiz --takip tez_los --mod-adi "Yok Boyle Mod"  # sim açılmadan, adları listeleyen hata
    $P -c "import sys;from pyulog import ULog;u=ULog(sys.argv[1],['debug_vect']);print({d.name:len(d.data['timestamp']) for d in u.data_list})" tez/sim/sonuclar/<klasör>/ucus.ulg
    ```

    ULog'daki `debug_vect` sayısı gönderilen `TEZ_LOS` sayısının ±%5'i içindedir (`SDLOG_PROFILE 163`).

**Kabul Ölçütleri:**
- 5.1'deki testler geçer; geçersiz vektör PX4'e gitmez
- `TEZ_LOS` ULog'da görünür; mod yalnız adıyla seçilir

#### Görev Grubu 6: Düz zemin konum hesabı, `FOLLOW_TARGET` ve stok Follow Me ile kapalı döngü
**Bağımlılık:** Görev Grubu 5 · **Emek:** ~0.6 gün

- [x] 6.0 Model kutusundan hesaplanan konumla stok Follow Me'nin hedefi izlemesi
  - [x] 6.1 Testleri yaz (5–7 test)
    - `test_konumlama.py`: bilinen pozda zemin noktası → piksel → konum, hata < 1 cm; `u_D < 0.25` reddi; kenara 8 px'ten yakın kutu reddi; poz geçmişi kare anını 0.15 s içinde kapsamıyorsa ret; NED ↔ enlem/boylam gidiş-dönüş
    - `test_mesajlar.py`'ye: `FOLLOW_TARGET` (1e7 tamsayı enlem/boylam, NaN hız, `est_capabilities=1`, `alt` = ev noktası AMSL)
    - (Uygulamada: 14 test fonksiyonu, 25 durum: `test_konumlama.py` 5 (gidiş-dönüş 4 duruş × 2 kamera, `u_D`, kenar, poz geçmişi, PX4 ve Gazebo enlem/boylam dönüşümleri), `test_mesajlar.py` +4 (FOLLOW_TARGET, akış kuralları, poz kancası, EKF kökeninin istenmesi), `test_takip.py` +3 (model ve hakem kaynağıyla FOLLOW_TARGET, kaydedicinin yeniden başlatılması), `test_hedef.py` +1 (`FLW_TGT_HT` kuralı; ara durum testi güncellendi), `test_rapor.py` +1 (ULog'da `follow_target` ve PX4'ün kestirimi). `alt` uygulamada zeminin AMSL'si: ev − 0.227 m. Ayrıntı: `implementation/gorev-grubu-06.md`.)
  - [x] 6.2 `araclar/konumlama.py`: kutunun alt ortası → `kamera.py` zinciri → zemin düzlemi (ev D + 0.227 m); kare anındaki EKF pozu (`ATTITUDE_QUATERNION` + `LOCAL_POSITION_NED`, `time_boot_ms` interpolasyonu); `GPS_GLOBAL_ORIGIN`'e göre enlem/boylam
  - [x] 6.3 `px4_baglanti.py`: `message_hooks` ile poz geçmişi (ana `recv_match` döngüsü bozulmaz); `send_follow_target` (en çok 10 Hz)
    (5. gruptan hazır: bağlantının bütün gönderimleri `serialize_sends` kilidinden geçer, `send_follow_target` de `self.m.mav` üstünden gönderince kilitlidir; `TEZ_LOS` akış kuralları `LosSender`'da, `FOLLOW_TARGET` için benzeri yazılabilir. Konum hesabı `takip.Tracker.on_model`'in seçtiği kutuyu (`Choice.box`) kullanır; `algilama.csv` sütunları `takip.ROW_COLUMNS`'a eklenir.)
    (Uygulamada: iki akışın ortak kuralları `FrameStream`'e taşındı (`LosSender`, `FollowTargetSender`); "en çok 10 Hz" = kare zamanları ≥ 96 ms; akış hızları `ATTITUDE_QUATERNION` 50 Hz, `LOCAL_POSITION_NED` 30 Hz. PX4 konumu en sık 500 ms'de bir kaynaştırır, 3 s mesaj gelmezse kestirimi bayat sayar.)
  - [x] 6.4 `follow_me` kaynağı: "Follow Target"e adla geçiş; `FLW_TGT_HT` senaryoda yoksa `drone.yukseklik_m` (parametre sırasına uygun); `--los hakem` iken `FOLLOW_TARGET` gerçek konumdan, yalnız hedef görünürken ("mükemmel algılayıcı"); `algilama.csv` konum sütunları. 2. gruptaki `follow_me` ara hatası kaldırılır.
    (Uygulamada eklendi: PX4 kaydedicisi `follow_target*` konularını ancak kendisi başlarken varlarsa yazdığı için `follow_me` koşusunda kayıt penceresinden önce bir kez yeniden başlatılır (`simulasyon.restart_logger`; ULog `ucus_once.ulg` + `ucus.ulg`); `follow_target.csv`; konum her takip kaynağında hesaplanır.)
  - [x] 6.5 Doğrulama

    ```bash
    $P -m pytest tez/sim/testler/test_konumlama.py tez/sim/testler/test_mesajlar.py -q
    $P -m pytest tez/sim/testler -q
    $P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim
    tez/pin/verify_pin.sh --worktree
    $P $S/senaryo.py --senaryo takip_yuruyen --ekransiz --los hakem   # önce mükemmel algılayıcı
    $P $S/senaryo.py --senaryo takip_yuruyen --ekransiz               # sonra model (v0.2, CPU)
    ```

    Kayıt boyunca mod "Follow Target"te kalır; ULog `follow_target` içerir (5.7'deki pyulog satırında `follow_target` da sayılır); mevcut F1 ölçütlerinde yatay mesafe ≈ 8 m civarındadır. Pencereli bir koşu (`DRI_PRIME=1`, `--ekransiz` olmadan) Gazebo'da gözle izlenebilir; asıl görsel kontrol 8. gruptaki MP4'tedir.

**Kabul Ölçütleri:**
- 6.1'deki testler geçer
- `takip_yuruyen` v0.2 modeli ve stok Follow Me ile kapalı döngüde uçar; döngü el çizimindeki gibi kapanır

### Ölçüm ve Video

#### Görev Grubu 7: Ölçütler, ULog özeti ve rapor
**Bağımlılık:** Görev Grubu 6 · **Emek:** ~0.5 gün

- [x] 7.A Manyetik alan (kullanıcı kararı 12.11, 6. grubun açık konusu; ayrı commit): EKF yaw kaymasının sebebi doğrulandı (Gazebo Harmonic manyetometresi PX4'e doğu bileşeni aynalanmış ulaşıyordu: −2.57° yerine +3.41° beklenen sapma), Gazebo manyetometre sistemi kapatılıp PX4 `sensor_mag_sim` açıldı (`SENS_EN_MAGSIM 1`), dünyaların `<magnetic_field>`'ı PX4 WMM değerine eşitlendi; testler `test_manyetometre.py`; önce/sonra 3'er `takip_yuruyen` koşusu, F0 ve F1 yeniden geçti (`implementation/gorev-grubu-07.md`, A)
- [x] 7.0 Her koşunun aynı ölçütleri üretmesi
  - [x] 7.1 Testleri yaz: `testler/test_olcum.py` (5–8 test, elle hazırlanmış tablolarla)
    - IoU; algılama/kaçırma oranı; seçim doğruluğu
    - Yanlış kişi (aynı kıyafetli kişi ayrıca); yanlış pozitif kare başı
    - LOS açı hatası ve yatay/dikey sapma farkı
    - Gecikme istatistikleri (ort/p50/p95/maks); atlanan kare oranı
    - (Uygulamada: `test_olcum.py` 16 test (`senaryo.py`'nin her takip kaynağındaki özet satırları (B koşularında bulunan hata), spec tablosuyla anahtar karşılaştırması, PX4 nav_state adları, model, LOS, akış, kareler, mesafe/kadraj/arkada kalma/yörünge, hover titremesi, `follow_target_status`, mod zaman çizelgesi, ULog'da `debug_vect` yokken bütün anahtarlar (6. gruptan kalan hata), ULog sayımları, EKF yaw ve ölçülen sapma, `measure`'ın bütün anahtarları yazması); `test_rapor.py` +2 (kontroller ve 3 m uyarısı; ozet.json'da bütün anahtarlar, yeni HTML bölümleri), 2 ULog testi `test_olcum.py`'ye taşındı; `test_toplu.py` 4 (çok koşu); `test_algilama.py` ölçüt kısmı `test_olcum.py`'ye taşındı)
  - [x] 7.2 `araclar/olcum.py`: spec "Ölçüt Tanımları"ndaki bütün anahtarlar; yalnız kayıt penceresinde; uygulanamayan ölçüt NaN (ör. `yok`'ta `geolocation_hatasi`)
    (Uygulamada: `olcum.measure(RunData)`; 5./6. gruptaki geçici ölçütler (`takip.Tracker.metrics`, `algilama.DetectionLog.metrics`, `senaryo.tracking_results`, `rapor.ulog_*`) buraya taşındı. Kullanıcının 12.11 isteğiyle eklenenler: en az yatay mesafe, 3 m altı süre ve olayları (karar 3), kameranın yakın/uzak görüş sınırı ve dışında kalınan süre, hedefin tamamı/ayakları kadrajda, arkada kalma açısı hatası, takip başı ve yürüyüş başı yörünge dönüşü, PX4'ün `follow_target_status` özeti (rota kuzey varsayımı, rota hatası, yörünge hedefinin dönüşü), ULog'dan EKF yaw hatası ve ölçülen manyetik sapma.)
  - [x] 7.3 ULog özeti: `TEZ_LOS` (`debug_vect`) sayısı ve hızı, `follow_target` sayısı, `vehicle_status` mod zaman çizelgesi, `mod_korunma_orani`
    (5. grupta öne alındı: `rapor.ulog_tez_los` → `tez_los_px4_sayisi`, `tez_los_px4_hizi_hz`, değerle eşleştirilen `uctan_uca_px4_ms_*`; `takip.Tracker.metrics` geçici olarak `uctan_uca_ms_*`, `tez_los_*`, `yeniden_kilit_sayisi`, `secim_dogru_orani`, `los_i_ii_fark_*` verir: `olcum.py`'ye taşınır.)
    (Uygulamada: `olcum.Topics` iki ULog dosyasını (`ucus_once.ulg` + `ucus.ulg`) birleştirir; `vehicle_status.nav_state` zaman çizelgesi `ozet.json` → `mod.ulog`; `mod_korunma_orani` istenen nav_state'e göre (mod seçildiği an PX4'ün durumu), ULog yoksa koşunun heartbeat kaydından.)
  - [x] 7.4 `rapor.py`: `rapor.write` yeni bölümleri ekler (model, LOS, zaman, takip, `ayarlar`, model sha256, RTF uyarısı); `metrics`, `_visibility`, `plot_map` korunur. 4. gruptaki geçici IoU kontrolü buraya taşınır.
    (Uygulamada: "Kontroller ve uyarılar" (`rapor.checks`: model görüntüde çalışıyor (IoU), 3 m uyarısı, kameranın yakın sınırı, mod, RTF; `ozet.json` → `kontroller`), gruplu ölçüm tabloları, "Takip zaman çizelgesi" ve "PX4 Follow Target" grafikleri, mod zaman çizelgesi, "Ayarlar" (takip, model dosyası ve sha256, PX4 başlangıç parametreleri: istenen / PX4'ten okunan / kaynak).)
  - [x] 7.5 Doğrulama

    ```bash
    $P -m pytest tez/sim/testler/test_olcum.py tez/sim/testler/test_rapor.py -q
    $P -m pytest tez/sim/testler -q
    $P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim
    tez/pin/verify_pin.sh --worktree
    $P $S/senaryo.py --senaryo kalabalik_park --ekransiz
    ```

    `ozet.json`'da "Ölçüt Tanımları"ndaki bütün anahtarlar vardır (değer NaN olabilir); `rapor.html` tarayıcıda açılır ve yeni bölümleri gösterir.

    Uygulamada (karar 4): `$P $S/toplu.py --senaryo takip_yuruyen --tekrar 3` ve `$P $S/toplu.py --senaryo kalabalik_park --tekrar 3`; ardından `$S/f1_kabul.sh`. Sonuçlar `implementation/gorev-grubu-07.md` (B) ve `kabul-kosulari.md`.
  - [x] 7.6 Çok koşu (karar 4, 12.11): `araclar/toplu.py --senaryo <ad> --tekrar N [-- senaryo.py bayrakları]`: her koşu ayrı süreçte, koşu bazında ve toplu (ort / en az / en çok) `toplu.json`, `toplu.csv`, `toplu.html`; başlayamayan koşu yeniden denenir ve listelenir; `--ozet` var olan koşuları özetler

**Kabul Ölçütleri:**
- 7.1'deki testler geçer; ölçütler elle hesaplanan değerlerle aynıdır
- Bütün ölçüt anahtarları her koşuda yazılır; başarı eşiği yoktur, yalnız ölçülür

#### Görev Grubu 8: Kare kaydı ve MP4 video (VLC)
**Bağımlılık:** Görev Grubu 7 · **Emek:** ~0.6 gün

- [x] 8.0 Her koşunun VLC'de açılan aynı düzende bir `kosu.mp4` üretmesi
  - [x] 8.1 Testleri yaz (3–5 test)
    - `test_video.py`: tek karelik birleşim 2000×720, boyutlar çift; kutuların sol panelde doğru yerde (2304×1296 → 1280×720 ölçek); taklit `subprocess` ile ffmpeg komutunda `libx264`, `yuv420p`, `+faststart`, `rawvideo`/`bgr24`
    - Kare seçimi: sim zamanında 15 fps ızgarasına denk gelen kareler (her 2. kare)
    - (Uygulamada: `test_video.py` 10 test (birleşim, kutuların yeri, PX4'ün o anda elindeki model sonucu, kameranın yerdeki izdüşümü, kuşbakışı ölçek ve kuzey, durum satırı ve kırmızı durumlar, ffmpeg borusu ve komutu, küçük bir koşu klasöründen bütün video ve `kareler/`'in silinmesi, kare–ızgara eşlemesi, `onizleme.py`'nin MP4'ü); `test_goruntu_yayini.py` 3 test (15 fps ızgarası ve pencere, JPEG, dolu kuyrukta kare düşürme ve sayma); `test_hedef.py` (`--kareleri-sakla` bağlandı, `henuz_bagli_degil` boş), `test_toplu.py` (`toplu.html`'den `kosu.mp4` bağlantısı). Hepsi taklit ffmpeg'le; ffmpeg, Gazebo, `torch` gerekmez)
  - [x] 8.2 `VERSIONS.md`'ye `ffmpeg` apt sürümünü `dpkg-query -W ffmpeg` ile yaz (kullanılmadan önce)
    (Uygulamada: ffmpeg 7:6.1.1-3ubuntu5, libavcodec60 7:6.1.1-3ubuntu5, libx264-164 2:0.164.3108+git31e19f9-1; izlemek için VLC 3.0.20-3build6.)
  - [x] 8.3 `araclar/goruntu_yayini.py`, kayıt kısmı: ayrı süreç; `/x500_tez/kamera/image`'dan `subscribe_raw`; kayıt penceresindeki kareleri 1280×720 JPEG (kalite 90) olarak `kareler/`'e yazar (QGC RTP kısmı 11. grupta)
    (Uygulamada: `FrameRecorder` ("spawn" süreç, model süreci gibi simden önce açılır); geri çağırma yalnız başlığı okur, `GridPicker` her 1/15 s'lik ızgara anına en çok 20 ms uzaklıktaki kareyi seçer (her 2. kare; kaybolan karenin yeri boş kalır, sonrakiler kaymaz); yazıcı iş parçacığı çözer, iki adımda küçültür (tam yarıya kutu süzgeci + 1280×720'ye çift doğrusal), JPEG yazar (`kareler/<t_us>.jpg`). Kuyruk 6 kare; dolarsa yeni kare düşer ve sayılır. Süreç OpenCV'yi tek iş parçacığında çalıştırır ve `nice 5` ile Gazebo, PX4 ve modelin arkasında kalır. Pencere hakemin kaydıyla aynıdır: `senaryo._Recording` ikisini birlikte açıp kapatır.)
  - [x] 8.4 `araclar/video.py`: `onizleme.py`'deki `Frames.annotate` ve ffmpeg çağrısı buraya taşınıp ortaklaştırılır
    - Sol 1280×720: hakem kutuları (hedef mavi, diğerleri turuncu); o anda PX4'ün elindeki son model sonucu (`gonderim` zamanına göre; seçilen kutu kalın kırmızı + güven, diğerleri ince); "HEDEF YOK"; sim zamanı, mod, uçtan uca gecikme
    - Sağ 720×720 üstten görünüm (`plot_map` renkleri): dron, hedef, diğer insanlar, ağaçlar, kameranın zemin izdüşümü, son 10 s iz, `follow_me`'de `FOLLOW_TARGET` noktası, ölçek çubuğu, yatay mesafe
    - Ham BGR → `ffmpeg` boru: `libx264 -pix_fmt yuv420p -preset veryfast -crf 23 -movflags +faststart`, 15 fps. OpenCV `VideoWriter` kullanılmaz.
    - (Uygulamada: video yalnız koşu klasörünün dosyalarından yapılır (`video.make`; `video.py <klasör>` ile yeniden de yapılabilir): `kareler/`, `dogru_cevap.csv`, `algilama.csv` + `kutular.csv`, `tez_los.csv`, `follow_target.csv`, `ozet.json`, ULog. Kuşbakışına kullanıcının 13.11 isteğiyle 7. gruptaki açıklayıcı animasyonun öğeleri eklendi: olması gereken "arka" noktası, 3 m halkası, kameranın yakın görüş sınırı halkası, son 3 s'nin FOLLOW_TARGET noktaları, `follow_me`'de PX4'ün kestirimi, varsaydığı rota (ok), gönderdiği yer (yörünge açısı hedefi) ve hedeflediği yer; altta durum satırı (kilit kaybı, hedef yok, yakın sınır / 3 m içinde, kadraj dışı → kırmızı; köşede aşma → turuncu; PX4'ün sahte hız kestirimi ve rotası). Model sonucu "PX4'ün elinde" sayıldığı an: gönderim, yoksa gecikme hattından çıkış, yoksa hazır olma (hakem kaynağı). Yazılar PIL + matplotlib'in DejaVu Sans'ıyla (Türkçe harfler), şekiller OpenCV ile.)
  - [x] 8.5 `senaryo.py`: koşu bittikten sonra çevrimdışı birleştirme; `kareler/` sonra silinir (`--kareleri-sakla` ile kalır); `--videosuz` bağlanır. `onizleme.py` WebM yerine MP4 üretir. `ruff.toml`'a `goruntu_yayini`, `video`, `olcum`, `takip`, `konumlama`, `gecikme` eklenmiş olmalıdır.
    (Uygulamada: video `rapor.write`'ın `video` kancasıyla, `ozet.json` ve CSV'ler yazıldıktan sonra yapılır; sonucu `ozet.json` → `video` (kare sayısı, süre, eksik kare, üretim süresi, kaydedicinin defteri) ve raporun başındaki "Video" satırı. Video yapılamazsa koşu kalmaz, olaylara yazılır. `toplu.py` her koşunun `kosu.mp4`'ünü `toplu.html`'den bağlar. `hedef.unwired`'daki `--kareleri-sakla` ara hatası ve `not_in_effect`'teki `video.mp4` satırı silindi.)
  - [x] 8.6 Doğrulama

    ```bash
    $P -m pytest tez/sim/testler/test_video.py -q
    $P -m pytest tez/sim/testler -q
    $P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim
    tez/pin/verify_pin.sh --worktree
    $P $S/senaryo.py --senaryo takip_yuruyen --ekransiz
    ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,pix_fmt,width,height -of csv=p=0 tez/sim/sonuclar/<klasör>/kosu.mp4   # h264,yuv420p,2000,720
    ffprobe -v error -show_entries format=duration -of csv=p=0 tez/sim/sonuclar/<klasör>/kosu.mp4    # kayıt penceresi ±1 s
    vlc tez/sim/sonuclar/<klasör>/kosu.mp4
    ```

    **Görsel kontrol (Ahmet, VLC):** model kutusu hedefin üstünde, gecikmesi gözle görülebiliyor; hakem kutusu hedefle çakışıyor; üstten görünüm kamera görüntüsüyle tutarlı; dron hedefi 8 m geriden izliyor.

    (Uygulamada 13.11: hepsi geçti. `takip_yuruyen` ve `kalabalik_park` videoları h264 / yuv420p / 2000×720, süreleri hakemin kaydına (`kayit_suresi_s`) 0.03 / 0.01 s yakın; `toplu.py` 3'lü grupta her koşunun videosu ve `toplu.html` bağlantıları; oturumun 32 videolu koşusunda eksik ya da düşen kare yok; VLC 3.0.20 açtı; F0 ve F1 geçti. Kare kaydı RTF'i ≈ 0.05 düşürüyor (dönüşümlü 3 + 3: 0.788 / 0.836). Video, spec'in "kayıt penceresi"nden farklı olarak hakemin kaydını (takip başı dahil) kapsar; gerekçe ve sayılar `implementation/gorev-grubu-08.md`. Görsel kontrol Ahmet'te.)

**Kabul Ölçütleri:**
- 8.1'deki testler geçer; `ffprobe` h264 / yuv420p / 2000×720 verir
- Video VLC 3.0.20'de açılır ve Ahmet'in görsel kontrolünden geçer

### Demo

#### Görev Grubu 9: 15.11 en az demo — koşular, görsel kontrol ve sonuçların spec'e yazılması
**Bağımlılık:** Görev Grupları 1–8 · **Emek:** ~0.4 gün

- [ ] 9.0 Spec'teki "En az demo (15.11)" listesinin tamamını göstermek (13.11: 9.5 dışında tamam; 9.5 Ahmet'in görsel kontrolü, izleme listesi `implementation/gorev-grubu-09.md` 6)
  - [x] 9.1 Test yazılmaz (yeni kod yok). Bu grupta bulunan her hata için önce o hatayı yakalayan bir birim testi eklenir (test standardı).
    (Uygulamada: kullanıcının 13.11 kararları ve sorusu yeni kod getirdi, hepsi önce testle: `test_yakin_gecis.py` (yeni, 5 test: bacaklar / köşeler, PX4'ün köşeye yetişmesi ve aşma, 6 m altı geçişlerin sebebi, ayrıştırma, ULog → dünya), `test_olcum.py`, `test_rapor.py`, `test_toplu.py`, `test_video.py`, `test_hedef.py` (RS kararı). Bulunan iki hata testle düzeltildi: videoda "PX4'ün dronu gönderdiği yer" kestirimden çiziliyordu (köşede metrelerce kayık; artık PX4'ün ayar noktası ve süzülmüş hedefi), bacak bulma bir NaN yaw'dan sonra rotayı kaybederdi. 225 → 234 test.)
  - [x] 9.2 Koşu 1: `takip_yuruyen`, v0.2 (CPU), stok Follow Me, kapalı döngü
    (Uygulamada: `sonuclar/gorev9_takip_yuruyen_x3`, senaryonun yeni varsayılanı `FLW_TGT_RS 0.3` ile; 3/3 GEÇTİ, mod %100 "Follow Target", salınım yok (196–202°), yatay mesafe ort. 7.9 m. Köşedeki yakın geçişten (0.45–1.94 m) sonra kişi kadrajdan çıktı ve stok mod onu 3/3 koşuda bir daha bulamadı: PX4'ün davranışı, belgeye yazıldı.)
  - [x] 9.3 Koşu 2: `kalabalik_park`, `yok`, model ölçütleri (karıştırma, örtülme)
    (Uygulamada: `sonuclar/gorev9_kalabalik_park_x3`, 3/3 GEÇTİ; algılama %71.6, seçim doğru %63.7, yanlış kişi %8.6 (aynı kıyafet %3.2), hedef 70.2–75.7 s çamın arkasında (%19.5 örtülü), RTF 0.72–0.76.)
  - [x] 9.2/9.3 için (karar 4, 12.11): her senaryo **3 kez** koşulur (`toplu.py --tekrar 3`); sonuçlar koşu bazında ve dağılımıyla (ort / en az / en çok) verilir, tek koşuyla sonuç söylenmez
  - [x] 9.4 İki koşu da `rapor.html`, `ozet.json`, `kosu.mp4` üretir; `TEZ_LOS` ULog'da görünür (`tez_los_px4_sayisi`)
    (Uygulamada: 6/6 koşu üçünü de üretti; `ffprobe` h264 / yuv420p / 2000×720, süre kayıt süresinin ±0.06 s içinde; `TEZ_LOS` ULog / gönderilen %100.)
  - [ ] 9.5 Görsel kontrol (Ahmet, VLC): spec "Görsel kontrol" listesinin tamamı; kalabalıkta yanlış kişiye geçişler videoda ve `yanlis_kisi_orani`'nda aynı anda görülür. Gösterilen sorunlar aynı sahnede yeniden koşularak doğrulanır.
    (Hazırlandı 13.11: videolar `~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev9_*_kosu.mp4`, dakika:saniyeli izleme listesi ve yanlış kişi anları (kare kare `ozet.json` ile aynı sayılar; iki örnek kare gözle doğrulandı) `implementation/gorev-grubu-09.md` 6 ve "Kendin dene" 3. Ahmet'in kontrolü bekleniyor.)
  - [x] 9.6 Belgeler: `implementation/kabul-kosulari.md`'ye iki koşunun özet sayıları (model, LOS, zaman, takip ölçütleri; RTF; model sha256) ve commit; karşılaşılan sorunlar `implementation/gorev-grubu-09.md`'ye. Spec'teki "Yaklaşma mesafesi", "Kamera parametreleri", "İnsan hedefi" ve "Varsayımlar" bölümlerinin güncel olduğu kontrol edilir (issue #7 "bitti" listesi).
    (Uygulamada: `kabul-kosulari.md`'ye 23 satır (RS 12, demo 6, 10/10 3, F0, F1); spec'te dört bölüm güncellendi (yeni simde kapalı döngü ölçümü; RTF ve kişi boyu; senaryolar ve köşe anları; konum kaymasının etkisi), ayrıca "PX4 stok Follow Target davranışı" 6, "Ölçüt Tanımları", karar 2–3, "Açık Konular".)
  - [x] 9.7 Doğrulama

    ```bash
    $P -m pytest tez/sim/testler -q
    $P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim
    tez/pin/verify_pin.sh --worktree                           # KILIT SAGLAM
    $S/f0_kabul.sh && $S/f1_kabul.sh                           # GEÇTİ
    $P $S/senaryo.py --senaryo takip_yuruyen --ekransiz
    $P $S/senaryo.py --senaryo kalabalik_park --ekransiz
    vlc tez/sim/sonuclar/<klasör-1>/kosu.mp4 tez/sim/sonuclar/<klasör-2>/kosu.mp4
    git status --short                                         # sonuclar/, .pt, .ulg, .mp4 görünmez
    ```

    PR (taslak ya da hazır) yalnız kullanıcı isteyince açılır. Zorunlu CI: `verify-pin`, `derleme-sitl`, `derleme-fmu-v6c`.

    (Uygulamada 13.11: 234 test geçti, ruff temiz, KILIT SAGLAM, F0 ve F1 GEÇTİ; senaryo koşuları `toplu.py --tekrar 3` ile (9.2/9.3); `git status` yalnız kod ve belge. Kullanıcı kararları: 1 `FLW_TGT_RS` 0.3 (0.2 ölçüldü, salınımı 3 koşunun yalnız birinde giderdi; ayrı yama), 2 video penceresi spec'e, 3 RTF payı `tasks.md` 11.6, 4 köşe ölçütleri `olcum.py`'de. Kullanıcının sorusu için 6 m altı geçişler, sebepleri ve ULog ayrıştırması; 10 m / 10 m denemesi (karar kullanıcıda). Ayrıntı `implementation/gorev-grubu-09.md`.)
  - [x] 9.8 Stok Follow Me parametre karşılaştırması (kullanıcı isteği 12.11; 7. grupta ölçülen stok davranış: takip başında gereksiz yörünge dönüşleri, köşede aşma, yakın geçiş; spec "PX4 stok Follow Target davranışı"): `takip_yuruyen`'de her ayar 3 koşu (`toplu.py --tekrar 3 -- --param ...`), aynı ölçütlerle (`arkada_kalma_hatasi_*`, `baslangic_yorunge_donusu_deg`, `yuruyus_basi_yorunge_donusu_deg`, `px4_rota_*`, `en_az_yatay_mesafe_m`, `yakin_mesafe_3m_suresi_s`, `kadraj_yakin_sinir_alti_s`, `hedef_kadrajda_orani`, `kilit_kaybi_sayisi`, `px4_kestirim_hatasi_*`). Adaylar: `FLW_TGT_RS` (0.1 varsayılan; ~~0.05~~, 0.3, 0.5, 0.8), `FLW_TGT_MAX_VEL` (5; 3, 8), `FLW_TGT_FA` (180, değişmez; yalnız bilgi). Model kaynağı ve "mükemmel algılayıcı" (`--los hakem`) ayrı ayrı. Amaç: stok modun ayarla ne kadar düzeldiğini ölçmek ve m15'e (Kurt) karşılaştırma tabanı vermek; m06'da varsayılan parametreler değişmez
    (13.11'de, 9. grubun geri kalanından önce yapıldı; kullanıcının sorusu: "model kişiyi her karede biraz farklı yerde buluyor, PX4 bunu kişi 1 m/s'den hızlı gidiyor sanıyor, dron salınıyor". **Aday düzeltmesi:** PX4 `FLW_TGT_RS`'yi 0.1–1.0'a kısar (`TargetEstimator::update_filter_gains`), 0.05 yazılsa 0.1 gibi davranırdı; küçük değer daha tepkisel, daha az gürültü bastırır ve 0.1 zaten en tepkisel uçtur. Bu yüzden adaylar 0.1, 0.3, 0.5, 0.8. Önce sayıyla açıklandı: takip başında (kişi dururken) gönderilen konumun titreşimi ve PX4'ün `vel_est`'indeki sahte hız için yeni ölçütler `olcum.follow_start_metrics` (`follow_target_titresim_baslangic_m`, `follow_target_ardisik_fark_baslangic_p50_m`, `follow_target_drona_dogru_baslangic_m`, `follow_target_hizi_baslangic_hz`, `px4_kestirim_hizi_baslangic_*`, `px4_rota_degisimi_baslangic_sayisi`; testli, spec tablosunda, raporda ayrı tablo, `toplu.py` ana tablosunda). Koşular: model kaynağı her ayar 3 koşu (varsayılanda ayrıca 3 videosuz), `--los hakem` varsayılan ve en iyi RS için 3'er. Sonuçlar, öneri ve m11/m15 için sayılar: `implementation/gorev-grubu-09-on-followme-ayar.md`. Varsayılan parametreler değişmedi; karar kullanıcının. **9. grupta kullanıcı kararıyla (13.11) 0.2 de ölçüldü ve Follow Me senaryoları `FLW_TGT_RS 0.3`'e geçti**; köşe ölçütleri `olcum.py`'ye taşındı (`gorev-grubu-09.md` 1–2).)
  - [x] 9.9 Kullanıcı kararları (14.11): (1) `takip_yuruyen` 10 m yükseklik / 10 m geride (kamera raporunun çim alan ayarı, `FLW_TGT_RS 0.3` kalır); 8 m / 8 m ayrı senaryo `takip_yuruyen_8m`; 9. gruptaki `takip_yuruyen_10m` kaldırıldı. Gerçek uçuş ayarı ekip kararıdır. (2) Videonun alt durum satırında kırmızı "YANLIŞ KİŞİ": PX4'e giden seçilen kutu hakeme göre başka bir kişideyse (aynı kıyafetli kişi ayrıca belirtilir), `yanlis_kisi_orani` ile aynı kural (`olcum.wrong_person`). Önce testler (`test_olcum.py`, `test_video.py` +2, `test_hedef.py`); F0 / F1 etkilenmez
    (Uygulamada: `implementation/gorev-grubu-09.md` bölüm 13; doğrulama koşuları `takip_yuruyen` (10/10) ve `kalabalik_park`, ikisi de videolu, `kabul-kosulari.md`'de.)

**Kabul Ölçütleri:**
- "En az demo (15.11)" listesindeki her madde sağlanır ve sayılarıyla `implementation/`'a yazılır
- `verify_pin.sh --worktree` geçer; repoya video, ULog ya da model girmez

---

## Faz A — Kalanlar (aynı PR, merge'den önce)

### Takım Arkadaşı Entegrasyonu

#### Görev Grubu 10: Kendi PX4 modülünü takmak — `derle.sh --harici`, `--px4-baslat`, kılavuz
**Bağımlılık:** Görev Grubu 9 · **Emek:** ~0.5 gün · **Bekleyen:** Kurt/Algan modülü (o arada iskelet modül ağaç dışında). Ekipten gelen bilgi (09.11, Yusuf Algan; kesinleşmiş değil, m15/m16 spec'inde yazılınca o geçerli): mod adı **"AUTO FOLLOW"** (QGC'de böyle görünecek), parametre öneki **`AF_`** (`AF_XXX`).

- [x] 10.0 m15 modunun sime kolayca takılıp aynı senaryo, ölçüt ve videoyla denenebilmesi
  - [x] 10.1 Testleri yaz (2–4 test): `calistir.sh`'a giden argüman listesinin oluşturulması (`takip.px4_baslat` + `--px4-baslat`, `takip.px4_parametreleri` + `--param` sırası); "unresponsive" kontrolünün yalnız harici modlu koşuda açılması. (`takip.px4_parametreleri` + `--param` sırası 2. grupta `test_hedef.py`'de sınandı.)
  - [x] 10.2 `derle.sh --harici <klasör>` → `EXTERNAL_MODULES_LOCATION`; bayrak yoksa `tez/px4/src/CMakeLists.txt` varsa o, yoksa stok; çıktı her zaman `build/px4_sitl_tez`; klasör önbellektekinden farklıysa CMake yeniden yapılandırılır
  - [x] 10.3 `calistir.sh --px4-baslat "<komut>"` (çoklu): `px4-logger status` başarılı olana kadar en çok 90 s beklenir; komut `rootfs` içinde `bin/px4-<komut>` ile çalışır, çıktısı sim log'una yazılır
  - [x] 10.4 `senaryo.py`/`simulasyon.py`: `takip.px4_baslat`, `takip.px4_parametreleri`, `--px4-baslat` bağlanır; harici modlu koşu sonunda `sim.log`'da "unresponsive" aranır. 2. gruptaki ilgili ara hatalar kaldırılır. (`takip.px4_parametreleri` ve `--param` 2. grupta bağlandı ve koşuda PX4'ten geri okunuyor; burada yalnız `px4_baslat` kalır.)
  - [x] 10.5 README "C. Kendi PX4 modülünü takmak" bölümü (spec "Takım Arkadaşı Kılavuzu" C1–C8); iskelet modül notları (`PARENT_SCOPE`, `DEPENDS` yok, `register_ext_component_request`, 24 karakter) `c4b4abf342`'ye atıfla
  - [x] 10.6 Doğrulama

    ```bash
    $P -m pytest tez/sim/testler -q
    $P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim
    tez/pin/verify_pin.sh --worktree
    # iskelet modül ağaç dışında (repo değişmez); <iskelet> = scratchpad altında boş yeni bir klasör
    git archive c4b4abf342 tez/px4 | tar -x -C <iskelet>
    tez/sim/derle.sh --harici <iskelet>/tez/px4
    $P $S/senaryo.py --senaryo takip_yuruyen --ekransiz --takip tez_los --mod-adi "Tez Auto Follow" \
        --px4-baslat "tez_auto_follow start" --los hakem          # mod AVAILABLE_MODES'ta, "unresponsive" yok, MP4 üretilir
    tez/sim/derle.sh && $S/f0_kabul.sh                          # bayraksız: yeniden yapılandırma + stok derleme, GEÇTİ
    ```

    Kurt'un modülü hazır olduğunda aynı komut onun adı ve başlatma komutuyla koşulur ve `implementation/`'a yazılır.
    Ekipten gelen bilgiye göre (09.11, kesinleşmiş değil) o koşu şöyle olur; başlatma komutu henüz bilinmiyor:

    ```bash
    $P $S/senaryo.py --senaryo takip_yuruyen --ekransiz --takip tez_los --mod-adi "AUTO FOLLOW" \
        --px4-baslat "<modülün başlatma komutu>" --los hakem
    ```

**Kabul Ölçütleri:**
- 10.1'deki testler geçer
- Ağaç dışı bir modül derlenir, başlatılır, adıyla seçilir; aynı ölçütler ve MP4 üretilir
- Bayraksız derleme stok hâle döner; m06 kilit listesine yol eklemez

**Durum (14.11):** uygulandı ve doğrulandı. 4 yeni test (`test_harici_mod.py`) + `test_hedef.py` / `test_olcum.py`
güncellemesi, 289 test geçti; ruff temiz; KILIT SAGLAM. İskelet (`c4b4abf342`, scratchpad'de, değiştirilmeden derlendi)
ile `takip_yuruyen` harici modlu koşu GEÇTİ ("Tez Auto Follow" listede, adıyla seçildi, istenen modda %100,
"unresponsive" yok, `TEZ_LOS` 892 = ULog 892, `kosu.mp4` + `rapor.html` + `ozet.json`); bayraksız `derle.sh` stoka döndü,
F0 GEÇTİ. Ayrıntı: `implementation/gorev-grubu-10.md`. Kurt/Algan'ın modülüyle koşu modül gelince yapılacak.

### Video Yayını

#### Görev Grubu 11: QGC'ye canlı video (H.264 RTP, UDP 5600)
**Bağımlılık:** Görev Grubu 9 · **Emek:** ~0.6 gün

- [ ] 11.0 Model ve hakem kutuları çizilmiş görüntünün QGC'de canlı izlenmesi (14.11: 11.7'deki Ahmet'in QGC görsel kontrolü dışında tamam)
  - [x] 11.1 Testleri yaz (2–4 test): UDP 5610 JSON mesajının paketlenmesi/çözülmesi (son model sonucu + hakem kutusu); GStreamer hattı metninde gerekli öğeler ve ayarlar (`leaky=downstream`, `tune=zerolatency`, `key-int-max=15`, `config-interval=1`, `pt=96`, `sync=false`); tek başına modda LOS gönderilmemesi
    (Uygulamada: `test_goruntu_yayini.py` +5: kutu mesajı gidiş-dönüşü, iki taraflı ret, gerçek UDP soketi ve `Tracker`'ın mesajı; hattın öğeleri + `yayin.sdp` + gerçek hatla H.264 RTP alıcısından kutuların doğru yerde çıkması; tek başına modun MAVLink'siz olması; tek işçinin yayın ve kayda hizmeti; 11.6 için kareleri model sürecinden paylaşılan bellekle alma. `test_video.py` +1 (etiketin kendi kutusunda çizimi = bütün karede çizim), `test_hedef.py` güncellendi. 289 → 295.)
  - [x] 11.2 apt paketlerini sabitle (kullanılmadan önce): `python3-gi`, `gir1.2-gstreamer-1.0`, `gir1.2-gst-plugins-base-1.0`, `gstreamer1.0-plugins-base`, `-good`, `-ugly`, `gstreamer1.0-libav`, `libfuse2t64`. Sürümler `dpkg-query -W` ile okunup `VERSIONS.md`'ye yazılır.
    (Uygulamada: GStreamer 1.24.2 — gir1.2-gstreamer-1.0 1.24.2-1ubuntu0.1, gir1.2-gst-plugins-base-1.0 / -base 1.24.2-1ubuntu0.6, -good 1.24.2-1ubuntu1.8, -ugly 1.24.1-1build1, -libav 1.24.1-1build1, -tools 1.24.2-1ubuntu0.1, -x 1.24.2-1ubuntu0.6; `python3-gi` 3.48.2-1; `libfuse2t64` 2.9.9-8.1build1; yeni paket kurulmadı.)
  - [x] 11.3 `goruntu_yayini.py`, yayın kısmı: `appsrc` (BGR, 1280×720, 15/1, canlı) → `queue leaky=downstream max-size-buffers=2` → `videoconvert` (I420) → `x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000 key-int-max=15` (`constrained-baseline`) → `rtph264pay config-interval=1 pt=96 mtu=1400` → `udpsink host=127.0.0.1 port=5600 sync=false`. Deney dalındaki sabit `x500_mono_cam_0` kullanılmaz.
    (Uygulamada: `LiveStream`, `pipeline_description`; ek olarak `x264enc threads=1` (≈ %20 daha az işlemci, +1.3 ms), `do-timestamp=true`; yayın simin başından sonuna gider.)
  - [x] 11.4 Kutular: senaryo koşusunda ana süreçten `127.0.0.1:5610` UDP JSON; tek başına modda `--model` ile kendi algılayıcısı (hakem kutusu yok, LOS yok)
    (Uygulamada: `BoxMessage` / `BoxSender` / `BoxListener`, `takip.Tracker(overlay=...)`, `video.draw_live`; tek başına `goruntu_yayini.py --qgc --model <dosya>` açık bir simde denendi: 659 / 659 kare, 616'sında kutu.)
  - [x] 11.5 `araclar/yayin.sdp`; `--qgc` / `video.qgc` bağlanır (ayrı süreç, sızdıran kuyruk). 2. gruptaki `--qgc` ara hatası kaldırıldı.
    (Uygulamada: kayıtla aynı süreç; `--videosuz --qgc` yalnız yayın; `ozet.json` → `yayin`. **Sabit VLC 3.0.20-3build6 bu yayını açamıyor** (Ubuntu paketi live555'siz); `yayin.sdp`'yi ffmpeg paketinin `ffplay`'i açar, `gst-launch-1.0` da çalışır.)
  - [x] 11.6 Kare kaydının RTF payı (kullanıcı kararı 13.11, 9. grupta alındı): 8. grupta ölçülen ≈ 0.05'lik payı (dönüşümlü 3 + 3 koşu: videolu 0.788 / `--videosuz` 0.836; kaynağı abonelik mi JPEG işi mi ayrılamadı) QGC yayınıyla birlikte ele al: kayıt ve yayın aynı süreçte olacağı için ikisinin toplam payını ölç; seçenekler (`implementation/gorev-grubu-08.md`, "Ne yapılabilir"): kareleri model sürecinin zaten aldığı abonelikten almak, kaydı/yayını ayrı çekirdeğe almak, 3'ten fazla dönüşümlü koşuyla payı abonelik / işleme diye ayırmak. Karar verilene kadar RTF'in önemli olduğu ölçümlerde `--videosuz`; sonucu `implementation/`'a ve spec 9. maddeye yaz
    (Uygulamada: üç dönüşümlü seri, 40 koşu. Önce: tur içi pay video −0.084, video + `--qgc` −0.114, kameraya pasif abone tek başına −0.062: payın çoğu ikinci aboneliğin kendisi. Kaydedici artık kareleri model sürecinin aboneliğinden paylaşılan bellekle alır (seçenek 2), kareyi kopyasız okuyup tamponlara küçültür; yayının yazıları kendi kutularında, x264 tek iş parçacığında. Sonra: video −0.027 ± 0.067, video + `--qgc` +0.001 ± 0.027; kaydedici + yayın süreci 0.48 → 0.30 çekirdek. Ölçülebilir pay kalmadı; `--videosuz` kuralının kalkması kullanıcı onayı bekliyor. `implementation/gorev-grubu-11.md` 5, spec 9. madde.)
  - [ ] 11.7 Doğrulama

    ```bash
    $P -m pytest tez/sim/testler -q
    $P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim
    tez/pin/verify_pin.sh --worktree
    $P $S/senaryo.py --senaryo takip_yuruyen --ekransiz --qgc
    gst-launch-1.0 udpsrc port=5600 caps="application/x-rtp,media=video,encoding-name=H264,payload=96" ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false
    vlc tez/sim/araclar/yayin.sdp                                # QGC'siz ikinci yol
    ```

    **Görsel kontrol (Ahmet):** QGC 5.1.4 → Uygulama Ayarları → Video → "UDP h.264 Video Stream", port 5600; görüntü akar, kutular çizilidir. `--qgc`'li koşunun `islenen_kare_hizi_hz` ve RTF değerleri 9. gruptaki koşuyla `karsilastir.py` (12. grup) ya da `ozet.json` üzerinden karşılaştırılır; belirgin düşüş varsa `implementation/`'a yazılır.

    (Uygulamada 14.11: 295 test geçti, ruff temiz, KILIT SAGLAM, F0 GEÇTİ. `takip_yuruyen --ekransiz --qgc --cikti tez/sim/sonuclar/g11_qgc` GEÇTİ: yayın 1583 kare = UDP 5600 alıcısı 1583 (kayıp 0), 15.0 kare/sim-s, kutu mesajı 948 / 948, alıcının karesinde kırmızı seçili kutu + mavi hakem kutusu (`~/Desktop/Follow/3_m06_Simulasyon/g11_qgc_yayin_karesi.jpg`); `kosu.mp4` h264 / yuv420p / 2000×720. `--qgc`'nin işlenen kare hızına ve RTF'e ölçülebilir etkisi yok (11.6). `gst-launch-1.0` alıcı hattı çalıştı; `vlc tez/sim/araclar/yayin.sdp` sabit VLC'de çalışmıyor, yerine `ffplay -protocol_whitelist file,udp,rtp -fflags nobuffer -flags low_delay -i tez/sim/araclar/yayin.sdp`. Ahmet'in QGC kontrolü bekleniyor: `implementation/gorev-grubu-11.md` "Kendin dene" 2.)

**Kabul Ölçütleri:**
- 11.1'deki testler geçer; apt sürümleri `VERSIONS.md`'dedir
- QGC'de canlı görüntü vardır; yayın model ve kayıt hattını belirgin yavaşlatmaz

**Durum (14.11):** uygulandı, test edildi, koşuldu; QGC'deki görsel kontrol Ahmet'te. 295 test, ruff temiz, KILIT
SAGLAM, F0 GEÇTİ; doğrulama koşusu GEÇTİ (yayın kayıpsız alındı, kutular çizili); 11.6'da kayıt + yayının RTF payı
−0.114'ten +0.001 ± 0.027'ye indi. Kullanıcıya sorular: `--videosuz` kuralının kalkması, VLC yerine ffplay. Ayrıntı:
`implementation/gorev-grubu-11.md`.

### Gecikme ve Karşılaştırma

#### Görev Grubu 12: Yapay gecikme, saat modeli ve `karsilastir.py`
**Bağımlılık:** Görev Grubu 9 · **Emek:** ~0.3 gün

- [ ] 12.0 Yakalama → PX4 yoluna ayarlanabilir gecikme eklemek ve koşuları yan yana koymak
  - [ ] 12.1 Testleri yaz (4–6 test): `test_gecikme.py` (sıra korunur; `ek_ms`; tohumlu titreşim aynı tohumla aynı; `saat_ofset_ms` ve `saat_kayma_ppm` ile `time_usec`); `karsilastir.py` iki `ozet.json`'dan tablo; `test_takip.py`'ye yeniden kilit bekleme süresi (12.4: kilit düştükten sonra süre dolana kadar yeniden kilit yok, 0 s'de bugünkü davranış)
  - [ ] 12.2 (5. gruptan hazır: `gecikme.DelayLine.put(item, hazir, extra_ms)` öğe başına gecikme alır ve sırayı korur; `Tracker` hattı `sc.delay.extra_ms` ile kurar; `time_usec` bugün yakalama anıdır, saat modeli `takip.Tracker._attempt`'teki `time_usec` alanına girer.) `gecikme.py`, 2. kısım: `ek_ms` + `titresim_ms` (düzgün dağılım, tohumlu), saat modeli; `ek_gecikme_ms` loglanır. `gecikme` bloğu ve `--gecikme-ms` bağlanır; ara hata kaldırılır. Faz A varsayılanları 0'dır.
  - [ ] 12.3 `araclar/karsilastir.py`: birden çok koşunun `ozet.json`'unu (ölçütler + `ayarlar`) tek tabloda yan yana koyar
  - [ ] 12.4 Yeniden kilit için operatör/kod tepki süresi (kullanıcı kararı, 12.11, 5. grubun açık kararı): senaryo alanı `takip.yeniden_kilit_bekleme_s` (sim saniyesi, ≥ 0, varsayılan **0** = bugünkü davranış, bir sonraki işlenen karede yeniden kilit). Kilit düştükten sonra bu süre dolmadan hakemle yeniden kilitlenilmez (gerçekte operatör QGC'de ~1–2 s sonra tıklar ya da m11'in otomatik yeniden bulma yöntemi çalışır). `algilama.csv`'de bekleme sırasında `kilitsiz_neden = tepki_bekleniyor`; değer `ozet.json` → `ayarlar.takip` ve raporda görünür. `hedef.py` alan doğrulaması (`_number`, en az 0) ve `--yeniden-kilit-bekleme-s` bayrağı bu alt görevde eklenir.
  - [ ] 12.5 Doğrulama

    ```bash
    $P -m pytest tez/sim/testler/test_gecikme.py -q
    $P -m pytest tez/sim/testler -q
    $P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim
    tez/pin/verify_pin.sh --worktree
    $P $S/senaryo.py --senaryo takip_yuruyen --ekransiz --gecikme-ms 200 --cikti tez/sim/sonuclar/gecikme200
    $P $S/karsilastir.py tez/sim/sonuclar/<9. grup koşusu> tez/sim/sonuclar/gecikme200   # uctan_uca_ms farkı ≈ 200
    vlc tez/sim/sonuclar/gecikme200/kosu.mp4
    ```

    **Görsel kontrol (Ahmet):** 200 ms'lik koşuda model kutusu hedefin gerisinde, 0 ms'liğe göre belirgin biçimde.

**Kabul Ölçütleri:**
- 12.1'deki testler geçer; ölçülen ek gecikme ayarlananla tutarlıdır
- `karsilastir.py` aynı senaryonun iki koşusunu tek tabloda verir

### Kabul, Kurulum ve Belgeler

#### Görev Grubu 13: `m06_kabul.sh`, `kur.sh` model kontrolü, sürümlerin ve README'nin tamamlanması
**Bağımlılık:** Görev Grupları 10–12 · **Emek:** ~0.75 gün

- [ ] 13.0 Takım arkadaşının klonlayıp birkaç betikle simi ayağa kaldırabilmesi; PR'ın hazır olması
  - [ ] 13.1 Testleri yaz (2–3 test): `m06_testi.py`'nin `ozet.json` anahtar denetimi ve `TEZ_LOS` sayısı ±%5 karşılaştırması (elle hazırlanmış örneklerle)
  - [ ] 13.2 `araclar/m06_testi.py` + `m06_kabul.sh` (`f0_testi.py` "GEÇTİ/KALDI" düzeni): koşu 1 `takip_yuruyen` (`follow_me`, model), koşu 2 `kalabalik_park` (`yok`, model), isteğe bağlı koşu 3 (`--mod-adi`, `--px4-baslat`); spec "Test Planı"ndaki 7 geçme koşulu
  - [ ] 13.3 `kur.sh`: sonda model klasörünü ve sha256 özetlerini `modeller.yaml`'a göre kontrol edip yazar; indirmez
  - [ ] 13.4 COCO `yolov8s.pt`: elle indirilip `~/auto-follow-modeller/`'a konur; kaynak adresi, boyutu ve sha256 `modeller.yaml`'a ve spec'e yazılır; `--model` ile bir kıyas koşusu `karsilastir.py`'ye girer
  - [ ] 13.5 `VERSIONS.md`'yi tamamla: `libfuse2t64`, `DRI_PRIME=1` notu, AGPL notu; `model-requirements.txt` ile tutarlılık
  - [ ] 13.6 `tez/sim/README.md`'yi (b) yoluna göre yeniden yaz: ön koşullar, kılavuz A/B/C, AMD `DRI_PRIME=1`, QGC `libfuse2t64`; `TEZ_` ön eki ve "kilit listesinde izinli iki dosya" ifadeleri düzeltilir; ruff komutu `../Vision/.venv` yerine ekip venv'ini (`$P -m ruff`) kullanır
  - [ ] 13.7 Spec'i güncelle: "Açık Konular"daki durumlar; "Uygulamada sabitlenecek sürümler (TBD)" doldurulur; Ortatepe teyidi geldiyse "Model dosyası" tablosu; `implementation/` notları tamamlanır
  - [ ] 13.8 (İsteğe bağlı, zaman kalırsa) Scratchpad'e temiz bir klon alınır ve README A adımları (`derle.sh`, `kur.sh`, `f0_kabul.sh`) takım arkadaşı gibi izlenir; eksik adım README'ye eklenir
  - [ ] 13.9 Doğrulama

    ```bash
    $P -m pytest tez/sim/testler -q
    $P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim
    tez/pin/verify_pin.sh --worktree
    tez/sim/kur.sh                                 # model klasörü ve sha256 sonucu yazılır
    $S/f0_kabul.sh && $S/f1_kabul.sh && $S/m06_kabul.sh   # üçü de SONUÇ: GEÇTİ
    vlc tez/sim/sonuclar/<m06 koşu 1>/kosu.mp4
    ```

    PR öncesi: `git log --oneline main..HEAD` her grubun commit'ini gösterir; PR başlığı `[M06] Simülasyon ortamı`; push ve PR yalnız kullanıcı isteyince.

**Kabul Ölçütleri:**
- `f0_kabul.sh`, `f1_kabul.sh`, `m06_kabul.sh` geçer; bütün birim testleri geçer
- `VERSIONS.md`, `model-requirements.txt`, `modeller.yaml` ve README eksiksizdir; spec'te TBD kalan sürüm yoktur
- Spec ve `implementation/` notları kodla aynı durumu anlatır

### Çatı Repo (ayrı repo, bu dalda yapılmaz)

#### Görev Grubu 14: Çatı PR'ı — `tech-stack.md` ve `docs/02` sürüm güncellemesi
**Bağımlılık:** Görev Grupları 3, 8, 11 (sürümler belli olunca) · **Emek:** ~0.2 gün · **Onay:** Hüseyin (ürün planını o günceller/onaylar)

- [ ] 14.0 Ekip özetindeki sürümlerin Autopilot `VERSIONS.md` ile aynı olması
  - [ ] 14.1 Test yazılmaz (yalnız belge). Kontrol: çatıdaki sürümler `VERSIONS.md` ve `model-requirements.txt` ile birebir aynı
  - [ ] 14.2 **Autopilot dalında değil**, çatı repoda: `git -C ~/Desktop/Projects/Auto-Follow rev-parse --show-toplevel` ile repo doğrulanır; kullanıcı onayıyla çatıda `ozellik/m06-<ad>` dalı açılır (ad kullanıcıyla belirlenir)
  - [ ] 14.3 `agent-os/product/tech-stack.md` ("Kesin" / "Karar bekliyor": sim'de laptop CPU'da Ultralytics, sürümleri, AGPL notu, GStreamer/ffmpeg) ve `docs/02-ortak-yazilim-surumleri.md` güncellenir
  - [ ] 14.4 (Ayrı iş, Hüseyin onayıyla) Gazebo standardındaki "NVIDIA'da çalışmalı" ifadesinin AMD `DRI_PRIME=1` için genişletilmesi `agent-os-profilleri/` üzerinden yapılır; sonuç üç repoda ayrı PR olur. m06 PR'ını bekletmez.
  - [ ] 14.5 Doğrulama

    ```bash
    git -C ~/Desktop/Projects/Auto-Follow rev-parse --show-toplevel     # çatı repo
    git -C ~/Desktop/Projects/Auto-Follow diff --stat                   # yalnız tech-stack.md ve docs/02
    git -C ~/Desktop/Projects/Auto-Follow/Autopilot status --short      # Autopilot dalı bu işten etkilenmez
    ```

    Commit çatıda (`<spec-klasor-adi>: ...` biçimi), PR başlığı `[M06] ...`; push ve PR kullanıcı ve Hüseyin onayıyla.

**Kabul Ölçütleri:**
- Çatıdaki sürümler Autopilot'takilerle aynıdır; iş ayrı repoda, ayrı dal ve PR'dadır

---

## Faz B — İkinci PR (15.11'den sonra; ilk PR'a girmez)

Faz B aynı spec'e bağlıdır, ilk PR merge edildikten sonra yeni bir dalda (`ozellik/m06-<ad>`, ad kullanıcıyla belirlenir) yapılır. Kurallar ve doğrulama komutları Faz A ile aynıdır.

#### Görev Grubu 15: Kamera kusurlarının ayarı ve açılması
**Bağımlılık:** Faz A merge · **Emek:** ~1–1.5 gün · **Bekleyen:** m09 (CM3 kayıtları; o arada veri sayfası değerleri, varsayım olarak yazılır)

- [ ] 15.0 `kusurlar.py`'deki ayrılmış alanların uygulanması
  - [ ] 15.1 Testleri yaz (4–8 test): her kusur tek başına açılır; aynı tohumla aynı sonuç; kapalıyken kare bit bit aynı (Faz A testi korunur)
  - [ ] 15.2 Gürültü: SDF gürültüsü kapatılır (`tez/sim/models` altında); Python'da okuma + atış gürültüsü
  - [ ] 15.3 Hareket bulanıklığı (pozlama süresi × açısal hız, Gazebo pozundan); rolling shutter (satır okuma süresi × açısal hız); pozlama/parlaklık (gökyüzü kadraja girince yerin kararması)
  - [ ] 15.4 Aynı kusurlar aynı tohumla video karelerine de uygulanır; MP4'te kusurlu ve kusursuz görüntü yan yana
  - [ ] 15.5 Doğrulama: pytest + ruff + `verify_pin.sh --worktree`; `kalabalik_park` kusurlu/kusursuz iki koşu → `karsilastir.py` ile model ölçütlerine etkisi; Ahmet'in VLC kontrolü

**Kabul Ölçütleri:** Her kusur birim testinden geçer; model ölçütlerine etkisi raporlanır.

#### Görev Grubu 16: Wi-Fi gecikme/kayıp benzetimi (yalnız video yolu)
**Bağımlılık:** Görev Grubu 11 · **Emek:** ~0.5 gün

- [ ] 16.0 QGC video yoluna gerçekçi bağlantı kusurları
  - [ ] 16.1 Testleri yaz (2–4 test): Gilbert-Elliott kayıp modeli (tohumlu, deneydeki `LinkImpairment` deseni yeniden yazılır); `video.wifi.{gecikme_ms, kayip, patlama}` alan doğrulaması
  - [ ] 16.2 `gstreamer1.0-plugins-bad` sürümü `VERSIONS.md`'ye yazılır, sonra `netsim` hatta eklenir
  - [ ] 16.3 Doğrulama: pytest + ruff + `verify_pin.sh --worktree`; QGC'de görüntü gecikmesi ve donma süreleri ölçülüp `implementation/`'a yazılır

**Kabul Ölçütleri:** `TEZ_LOS` yolu etkilenmez; video yolundaki gecikme ve kayıp ayarlanabilir ve ölçülür.

#### Görev Grubu 17: Yaklaşma mesafelerinin gerçek modelle yeniden ölçülmesi — kamera eğimi (30–45°) × yükseklik × mesafe taraması (öne alındı, 14.11)
**Bağımlılık:** — (öne alındı; Görev Grubu 15'in kamera kusurları olmadan, m15 yok: stok Follow Me) · **Emek:** ~1.5 gün (koşu süresi ağırlıklı) · Ayrıntı: `implementation/gorev-grubu-17-on-kamera-acisi.md`

Kullanıcının isteği (14.11): kamera raporundaki modelsiz 30–45° × mesafe taramasını bu modelle (v0.2, CPU, kapalı döngü,
stok Follow Me) yeniden yapmak ve "hangi seçenek benim için daha iyi" sorusuna gerekçeli bir öneri vermek; ek istekler:
düşük yükseklik bandı 4–7 m (30° / 4 m / 8 m dahil), modelin hangi koşullarda iyi algıladığı, düşük yüksekliğin gerçek
bedeli, "30°'de yaklaşınca kişiyi kaçırma artıya döner mi?" sorusu. Varsayılan 45° montaj ve senaryo varsayılanları
değişmez; karar kullanıcının ve ekibin. **14.11 (İş 2–3):** kullanıcı 37.5°'nin ve genişletilmiş taramanın
denenmesini istedi, seçimi bize bıraktı ve seçilen ayarın simin varsayılanı olmasını istedi; gerçek uçuş için de bir
değer önerilmesi istendi (17.10–17.12). (Faz B'deki asıl tanım: aşağıdaki 17.2'nin ayarları; ızgara bunları kapsıyor,
`cayir` dünyası ve olumsuz kontrol 6/8 aşama 1'de `duz_alan`'da.)

- [ ] 17.0 Kamera eğimi ayarı, tarama ve öneri (13.11: 17.8'deki Ahmet'in VLC kontrolü dışında tamam)
  - [x] 17.1 Testleri yaz: 30–45°'de bilinen poz → piksel → zemin gidiş-dönüşü, LOS (i), yakın/uzak sınır, Tracker'ın montajı, Gazebo eğiminin geri okunması, senaryo alanı / `--kamera-egim`, modelin eğimli kopyası (asıl model değişmez), videonun yakın sınırı (`test_kamera_egimi.py`); tarama: merkez mesafesi ve kadraj kontrolü, plan, başka bir yolun aynı ayarları, kaydırılmış yol, kaldığı yerden sürme, koşu başına kayıp / piksel boyu / yaklaşma / kadrajdan çıkış kenarı, geometrik paylar (kullanıcının sayılarıyla), kapılar ve puanlar, aşama 2 adayları (`test_tarama.py`)
  - [x] 17.2 Kamera eğimi senaryo ve komut satırı ayarı (`kamera.egim_deg`, `--kamera-egim`; 0–60°, varsayılan 45°): Gazebo modelinin koşu kopyası, LOS (i), düz zemin konum, yakın sınır, video ve rapor tek kaynaktan; `ozet.json` → `ayarlar.kamera`, `kamera_montaji.egim_deg`
    (Uygulamada: aşama 1'in 81 koşusunda Gazebo'nun eğimi senaryoyla ≤ 1.7·10⁻⁵° aynı; LOS (i)–(ii) açı farkı 0.27–0.40°, 45°'deki gibi; kutunun konum payı 0.23–0.26 m, eğimden bağımsız.)
  - [x] 17.3 Tarama sürücüsü `araclar/tarama.py` (plan / kos / ozet; `durum.json` ile kaldığı yerden sürer) ve karar kuralı koşulardan önce belgeye yazıldı (kapılar, 7 grup, eşit ağırlık, aşama 2 adayları)
  - [x] 17.4 Aşama 1: 81 bileşim × 1 koşu, videosuz (ana bant 30/35/40/45° × 8/10/12/15 m × 0.8/1/1.25 merkez mesafesi + 8 m; düşük bant 4/5/6/7 m × merkez + 8 m, yalnız `duz_alan`); `FLW_TGT_HT` < 8'in uygulandığı geri okuma ve ULog yüksekliğiyle doğrulandı
    (Uygulamada: 81/81 koşu, 23 bileşim kapıdan geçti; 12 m ve üstünde model kişiyi bulamıyor, 4–7 m'de köşede dron kişinin üstüne geliyor; düşük bantta 26/26 koşuda `FLW_TGT_HT` PX4'te istenen değerde, ULog yüksekliği ±0.15 m. Önceki ajan 62/81'de durduruldu, aynı komut kaldığı yerden sürdü.)
  - [x] 17.5 Aşama 2: adaylar + 45° 8/8 ve 10/10 başvuruları 3'er koşu (videolu); en iyi 1–2 aday ve 45° 10/10 için `--los hakem` 3'er koşu ve `kivrimli_yuruyus` yolu 3'er koşu
    (Uygulamada: 8 bileşim × 3 = 24 koşu; kapıyı 3/3 geçen 35° 7/10, 30° 6/10.4, 35° 8/11.4, 40° 12/11.4, hiçbir 45° ayarı. Mükemmel algılayıcı ve kıvrımlı yol kuralın ilk ikisi, 35° 8/11.4 ve 45° 10/10 için 3'er koşu (24): hakemle dördü de geçti; kıvrımlı yolda yalnız 35° 8/11.4 3/3. Toplam 129 tarama koşusu.)
  - [x] 17.6 Ölçütler ve sonuç: sonuç tablosu (artı/eksi), ısı haritaları, aday karşılaştırması, kamera raporunun modelsiz sonuçlarıyla yan yana (ne değişti, neden), "yaklaşınca kaçırma" sorusunun cevabı (yaklaşma payı, genişlik, piksel boyu, ölçülen yaklaşma), modelin hangi koşullarda iyi algıladığı (lojistik regresyon, ölçülemeyenler, Ortatepe'ye öneriler); öneri (açı, yükseklik, mesafe, gerekçe, bedeli, ikinci seçenek)
    (Uygulamada: öneri 35° · 8 m / 11.4 m, kuralın birincisi 35° · 7 m / 10 m, ikinci seçenek 30° · 6 m / 10.4 m, 45°'de kalınacaksa 10 m / 10 m; köşe yaklaşması ≈ 6.2 m mutlak, mesafeyle ölçeklenmiyor; algılamayı piksel boyu belirliyor. Belge bölüm 4–9.)
  - [x] 17.7 Belgeler: spec "Yaklaşma mesafesi", "Kamera parametreleri", senaryo alanları, Dosya / Test Planı, README, `kabul-kosulari.md`; gerçeklik farkları (montaj parçası, CM3 FOV, Hailo, rüzgâr, SHGM, alan) ve düşük yüksekliğin bedeli; repo dışında görseller, iki video, özet PDF
  - [ ] 17.8 Doğrulama: pytest + ruff + `verify_pin.sh --worktree`; F0 / F1; videoların `ffprobe`'u; Ahmet'in VLC kontrolü (önerilen ayar ve 45° 10/10)
    (13.11: 270 test geçti, ruff temiz, KILIT SAGLAM, F0 ve F1 GEÇTİ; videolar h264 / yuv420p / 2000×720. 14.11: 281 test geçti, ruff temiz, KILIT SAGLAM; F0 ve F1 yeni varsayılanla GEÇTİ. Ahmet'in VLC kontrolü bekleniyor: "Kendin dene" 4 ve 11 (seçilen 35° · 9/12.9, 37.5°'nin kayıp koşusu, yeni varsayılanla demo).)
  - [x] 17.9 Canlı hakem akışının "≈ 7 s durması" (İş 1, ayrı commit): kök nedeni kanıtla, önce hatayı yakalayan test, düzelt, etkilenen kıvrımlı yol koşularını yeniden koş
    (Uygulamada: Gazebo'nun segmentasyon kamerası (gz-sensors 8.2.2) başlığa her karede bir `frame_id` ekliyor; saf Python protobuf ile çözülen kare koşu boyunca yavaşladı, tam GC 0.3 s'de bir, ≈ 70 s sonra gz-transport iş parçacığı geride kaldı ve yeniden kilit olamadı. Kare artık ham okunuyor (`kayit.read_image`), hakemin gecikmesi her koşuda `ozet.json` → `tez_los.hakem_akisi`. `test_hakem_akisi.py` 5 test (eski yolda 20 000 girdili kare 108.5 ms, sınır 5 ms); 275 test. Ölçümlü koşuda iş parçacığı CPU'su 0.15 → 0.87 yerine ≈ 0.19 sabit, tam GC 122 yerine 1. Kıvrımlı yol 3 ayar × 3 yeniden koşuldu: hakem %95 ≤ 49 ms, engellenen kilit 0; 35° 7/10 ve 30° 6/10.4 2/3 (belirsiz kayıplar hataymış), 35° 8/11.4 2/3. Belge bölüm 16, yama `~/Desktop/Follow/3_m06_Simulasyon/Deneme/hakem_akisi_duzeltme.patch`.)
  - [x] 17.10 İş 2: 37.5° ve genişletilmiş tarama (37.5° × 6–12 m, 35° ve 40°'ye 9 m; aşama 1 ekleri 1'er koşu, 35° / 37.5° / 40° adayları + önceki öneri + rakipler + 45° 10/10 iki yolda 3'er koşu; montaj toleransı ±2.5°; kıvrımlı yolun gürültüsü için ek koşular); kapılar ve son seçim kuralı koşulardan önce yazıldı; son karar
    (Uygulamada: aşama 1 ekleri 19 bileşim, 13'ü kapıdan geçti (37.5°'de 7–10 m'nin hepsi; 12 m'de model kişiyi bulamıyor); aşama 2 (takip yolu) 9 × 3: kapıyı 3/3 geçen 30° 6/10.4, 35° 8/11.4, 35° 9/12.9, 37.5° 8/11.4, 37.5° 9/12.9; kural puanıyla birinci 37.5° 9/12.9 (0.540, 35° 8/11.4 ile berabere). Kıvrımlı yol 9 × 3: 3/3 yalnız 35° 9/12.9; 37.5° 9/12.9 1/3, 45° 10/10 0/3 (yarıda kesilen koşu yeniden koşuldu). **Son karar 35° · 9 m / 12.9 m** (son seçimin 3. adımı: iki yolda 3/3). Ek koşular: kıvrımlı yolda 35° toplam 5/6, 37.5° 1/6; montaj toleransı 32.5° takip 3/3, kıvrımlı 2/3 (yatık tarafa sorun yok, dik tarafa ani geri dönüş belirgin kötü). Belge bölüm 17–18.)
  - [x] 17.11 Gerçek uçuş için önerilen ayar (doğrulanmamış): montaj açısı ve toleransı, uçuş yüksekliği, geride durma mesafesi ve aralıkları, simdeki dayanağı, simin temsil etmediği yanlar (rüzgâr, GPS / baro yükseklik, zemin eğimi, gerçek kamera, Hailo, stok Follow Me yerine m15), ilk saha uçuşunda adım adım doğrulama planı
    (Uygulamada: 35° (hedef 35°, en çok +1°; 32.5°'ye kadar yatık olabilir), 9 m (8–9 m), 12.9 m (= yükseklik / tan 35°; 11.4–12.9 m, stok Follow Me ile 11.4 m'nin altına inilmez); belge bölüm 19, spec "Yaklaşma mesafesi", PDF. İlk uçuşta doğrulanacak.)
  - [x] 17.12 İş 3: seçilen ayar simin varsayılanı: `kamera.NOMINAL_TILT_DEG` 35° ve `models/x500_tez` (tek kaynak, test karşılaştırır), `takip_yuruyen` 9 m / 12.9 m (`FLW_TGT_RS 0.3` kalır), 45° senaryoları `takip_yuruyen_45_10m` / `takip_yuruyen_45_8m`, `kalabalik_park` 9 m, eski koşuların videosu kaydedilen montajla; `gercek_dron.params` değişmedi; önce testler; F0 / F1; `takip_yuruyen` ×3 ve `kalabalik_park` ×3
    (Uygulamada: `test_varsayilan_montaj.py` 5 test (6 durum), önce 5 durum kırmızı; 281 test geçti (275 + 6), ruff temiz, KILIT SAGLAM. F0 ve F1 GEÇTİ; `takip_yuruyen` ×3: kişi 3/3 izlendi, en az 6.63 (5.68–7.12) m, bulma %62 (58–65); `kalabalik_park` ×3: hedef %99 (98–100) kadrajda, yanlış kişi %16 (12–19) (45° / 10 m'de %6–12). Belge bölüm 20, `gorev-grubu-09.md` bölüm 14.)
  - [x] 17.13 İş 4 (14.11 akşam, kullanıcının fikri): alçak + uzak takip denemesi (kişi görüntünün ortasının üstünde): 30° 6/12.9, 30° 7/12.9, 32.5° 7/12.9, 35° 8/12.9 iki yolda 3'er koşu (videolu) + aynı eğim / yükseklikte `kalabalik_park` (Hold) 3'er koşu; başvurular 35° 9/12.9 ve 35° 8/11.4 aynı koddan (yeniden koşulmadı); tasarım, kapılar ve gerçek uçuş okuması koşulardan önce yazıldı; `FLW_TGT_HT` < 8 geri okuma + ULog; `cayir`'de ağaç / çarpma kontrolü; tek tablo; gerçek uçuş için başlangıç + yedek; görseller, videolar, PDF bölümü
    (Uygulamada: 36 koşu, hepsi GEÇTİ, 17:34–19:10; kod değişmedi. Takip yolunda dördü de 3/3 (köşede 6.7–7.9 m; seçili 5.8–7.0), kıvrımlı yolda 30° 6/12.9 dışındakiler 3/3; kuralın sim seçimi 30° 7/12.9. Ama kişi merkezin üstünde olduğu için hızlanırken (burun 12–18° aşağı) üstten çıkıyor (baş ort. 1.5–5.7 s / koşu; 30° 6 m'de bir kayıp) ve kalabalıkta yanlış kişi %39–77 (35° 9 m'de %16; 6–8 m'de seçim yürüyüşün 3. saniyesinde arkadaki aynı kıyafetli kişiye atlıyor). Önceden yazılan şart (b) sağlanmadı: gerçek uçuş başlangıcı 35° 9/12.9 kalıyor, yedek 35° 8/12.9 (13.11'in 8/11.4'ü yerine; doğrulanmamış). `FLW_TGT_HT` 6/7 m PX4'te uygulandı (ULog ±0.12 m). Varsayılanlar değişmedi. Belge bölüm 21.)

**Kabul Ölçütleri:** Spec'teki yaklaşma mesafesi bölümü yeni ölçümlerle güncellenmiştir; öneri ölçütlere dayanır ve bedeliyle birlikte yazılıdır; 17.0–17.9'da varsayılanlar değişmemiştir. 17.10–17.12 (14.11, kullanıcının isteği): son karar kuralla ve gerekçesiyle yazılıdır; seçilen ayar simin varsayılanıdır (tek kaynak, testli), F0 / F1 ve demo senaryoları yeni varsayılanla geçer; gerçek uçuş önerisi "doğrulanmamış" olarak yazılıdır.

---

## Uygulama Sırası

1. Görev Grubu 1 — (b) yolu, parametreler, F0 (onay bekliyor, ilerlenir)
2. Görev Grubu 2 — Senaryo şeması ve komut satırı
3. Görev Grubu 3 — Model ortamı ve sürüm sabitleme
4. Görev Grubu 4 — Kare okuyucu, kusur aşaması, model süreci
5. Görev Grubu 5 — Hedef seçimi, LOS, `TEZ_LOS`, adla mod
6. Görev Grubu 6 — Konum hesabı, `FOLLOW_TARGET`, Follow Me kapalı döngü
7. Görev Grubu 7 — Ölçütler ve rapor
8. Görev Grubu 8 — MP4 video
9. Görev Grubu 9 — **15.11 en az demo**
10. Görev Grupları 10, 11, 12 (birbirinden bağımsız, her sırayla) → 13 — Faz A'nın kalanı, aynı PR, merge'den önce
11. Görev Grubu 14 — çatı repo, ayrı PR (sürümler belli olunca, paralel)
12. Görev Grupları 15 → 16 → 17 — Faz B, ikinci PR (17, kullanıcının isteğiyle 14.11'de öne alındı ve bu dalda genişletilerek yapıldı: kamera eğimi × yükseklik × mesafe taraması; ayrı commit, `implementation/gorev-grubu-17-on-kamera-acisi.md`)

<details>
<summary>Ek: Claude'un çalışma sırası tahmini (ekip takvimi değildir)</summary>

Bu tablo, görev listesini oluşturan Claude ajanının işi 15.11'e (issue #7 son teslim) göre sıralamak için yaptığı kaba
tahmindir. Kimse onaylamadı; bağlayıcı değildir.

| Tarih | Gruplar | Tahmini emek |
|---|---|---|
| 10.11 | 1 | ~0.75 gün |
| 11.11 | 2, 3, 4'ün başı | 0.3 + 0.4 + … |
| 12.11 | 4, 5 | 0.75 + 0.75 |
| 13.11 | 6, 7 | 0.6 + 0.5 |
| 14.11 | 8, 9'un başı | 0.6 + … |
| 15.11 | 9 (demo) + tampon | 0.4 |
| 15.11 sonrası, merge öncesi | 10, 11, 12, 13, 14 | 0.5 + 0.6 + 0.3 + 0.75 + 0.2 |
| Faz B | 15, 16, 17 | 1–1.5 + 0.5 + 1 |

Gecikme olursa demodan hiçbir madde düşürülmez; 10–13 kayar.

</details>
