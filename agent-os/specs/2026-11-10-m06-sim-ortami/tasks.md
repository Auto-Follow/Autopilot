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
| Yusuf Kurt / Yusuf Algan | m15 modunun adı, modülün yeri, parametre öneki, `TEZ_LOS` biçiminin uygunluğu | 5, 10, 13 | `tez_los` mekanizması stok "Hold" adıyla ve iskelet modülle (`c4b4abf342`, ağaç dışında açılır) denenir. `m06_kabul.sh`'taki 3. koşu modül hazır olunca koşulur. |

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

- [ ] 8.0 Her koşunun VLC'de açılan aynı düzende bir `kosu.mp4` üretmesi
  - [ ] 8.1 Testleri yaz (3–5 test)
    - `test_video.py`: tek karelik birleşim 2000×720, boyutlar çift; kutuların sol panelde doğru yerde (2304×1296 → 1280×720 ölçek); taklit `subprocess` ile ffmpeg komutunda `libx264`, `yuv420p`, `+faststart`, `rawvideo`/`bgr24`
    - Kare seçimi: sim zamanında 15 fps ızgarasına denk gelen kareler (her 2. kare)
  - [ ] 8.2 `VERSIONS.md`'ye `ffmpeg` apt sürümünü `dpkg-query -W ffmpeg` ile yaz (kullanılmadan önce)
  - [ ] 8.3 `araclar/goruntu_yayini.py`, kayıt kısmı: ayrı süreç; `/x500_tez/kamera/image`'dan `subscribe_raw`; kayıt penceresindeki kareleri 1280×720 JPEG (kalite 90) olarak `kareler/`'e yazar (QGC RTP kısmı 11. grupta)
  - [ ] 8.4 `araclar/video.py`: `onizleme.py`'deki `Frames.annotate` ve ffmpeg çağrısı buraya taşınıp ortaklaştırılır
    - Sol 1280×720: hakem kutuları (hedef mavi, diğerleri turuncu); o anda PX4'ün elindeki son model sonucu (`gonderim` zamanına göre; seçilen kutu kalın kırmızı + güven, diğerleri ince); "HEDEF YOK"; sim zamanı, mod, uçtan uca gecikme
    - Sağ 720×720 üstten görünüm (`plot_map` renkleri): dron, hedef, diğer insanlar, ağaçlar, kameranın zemin izdüşümü, son 10 s iz, `follow_me`'de `FOLLOW_TARGET` noktası, ölçek çubuğu, yatay mesafe
    - Ham BGR → `ffmpeg` boru: `libx264 -pix_fmt yuv420p -preset veryfast -crf 23 -movflags +faststart`, 15 fps. OpenCV `VideoWriter` kullanılmaz.
  - [ ] 8.5 `senaryo.py`: koşu bittikten sonra çevrimdışı birleştirme; `kareler/` sonra silinir (`--kareleri-sakla` ile kalır); `--videosuz` bağlanır. `onizleme.py` WebM yerine MP4 üretir. `ruff.toml`'a `goruntu_yayini`, `video`, `olcum`, `takip`, `konumlama`, `gecikme` eklenmiş olmalıdır.
  - [ ] 8.6 Doğrulama

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

**Kabul Ölçütleri:**
- 8.1'deki testler geçer; `ffprobe` h264 / yuv420p / 2000×720 verir
- Video VLC 3.0.20'de açılır ve Ahmet'in görsel kontrolünden geçer

### Demo

#### Görev Grubu 9: 15.11 en az demo — koşular, görsel kontrol ve sonuçların spec'e yazılması
**Bağımlılık:** Görev Grupları 1–8 · **Emek:** ~0.4 gün

- [ ] 9.0 Spec'teki "En az demo (15.11)" listesinin tamamını göstermek
  - [ ] 9.1 Test yazılmaz (yeni kod yok). Bu grupta bulunan her hata için önce o hatayı yakalayan bir birim testi eklenir (test standardı).
  - [ ] 9.2 Koşu 1: `takip_yuruyen`, v0.2 (CPU), stok Follow Me, kapalı döngü
  - [ ] 9.3 Koşu 2: `kalabalik_park`, `yok`, model ölçütleri (karıştırma, örtülme)
  - [ ] 9.2/9.3 için (karar 4, 12.11): her senaryo **3 kez** koşulur (`toplu.py --tekrar 3`); sonuçlar koşu bazında ve dağılımıyla (ort / en az / en çok) verilir, tek koşuyla sonuç söylenmez
  - [ ] 9.4 İki koşu da `rapor.html`, `ozet.json`, `kosu.mp4` üretir; `TEZ_LOS` ULog'da görünür (`tez_los_px4_sayisi`)
  - [ ] 9.5 Görsel kontrol (Ahmet, VLC): spec "Görsel kontrol" listesinin tamamı; kalabalıkta yanlış kişiye geçişler videoda ve `yanlis_kisi_orani`'nda aynı anda görülür. Gösterilen sorunlar aynı sahnede yeniden koşularak doğrulanır.
  - [ ] 9.6 Belgeler: `implementation/kabul-kosulari.md`'ye iki koşunun özet sayıları (model, LOS, zaman, takip ölçütleri; RTF; model sha256) ve commit; karşılaşılan sorunlar `implementation/gorev-grubu-09.md`'ye. Spec'teki "Yaklaşma mesafesi", "Kamera parametreleri", "İnsan hedefi" ve "Varsayımlar" bölümlerinin güncel olduğu kontrol edilir (issue #7 "bitti" listesi).
  - [ ] 9.7 Doğrulama

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
  - [ ] 9.8 Stok Follow Me parametre karşılaştırması (kullanıcı isteği 12.11; 7. grupta ölçülen stok davranış: takip başında gereksiz yörünge dönüşleri, köşede aşma, yakın geçiş; spec "PX4 stok Follow Target davranışı"): `takip_yuruyen`'de her ayar 3 koşu (`toplu.py --tekrar 3 -- --param ...`), aynı ölçütlerle (`arkada_kalma_hatasi_*`, `baslangic_yorunge_donusu_deg`, `yuruyus_basi_yorunge_donusu_deg`, `px4_rota_*`, `en_az_yatay_mesafe_m`, `yakin_mesafe_3m_suresi_s`, `kadraj_yakin_sinir_alti_s`, `hedef_kadrajda_orani`, `kilit_kaybi_sayisi`, `px4_kestirim_hatasi_*`). Adaylar: `FLW_TGT_RS` (0.1 varsayılan; 0.05, 0.3, 0.5), `FLW_TGT_MAX_VEL` (5; 3, 8), `FLW_TGT_FA` (180, değişmez; yalnız bilgi). Model kaynağı ve "mükemmel algılayıcı" (`--los hakem`) ayrı ayrı. Amaç: stok modun ayarla ne kadar düzeldiğini ölçmek ve m15'e (Kurt) karşılaştırma tabanı vermek; m06'da varsayılan parametreler değişmez

**Kabul Ölçütleri:**
- "En az demo (15.11)" listesindeki her madde sağlanır ve sayılarıyla `implementation/`'a yazılır
- `verify_pin.sh --worktree` geçer; repoya video, ULog ya da model girmez

---

## Faz A — Kalanlar (aynı PR, merge'den önce)

### Takım Arkadaşı Entegrasyonu

#### Görev Grubu 10: Kendi PX4 modülünü takmak — `derle.sh --harici`, `--px4-baslat`, kılavuz
**Bağımlılık:** Görev Grubu 9 · **Emek:** ~0.5 gün · **Bekleyen:** Kurt/Algan modülü (o arada iskelet modül ağaç dışında)

- [ ] 10.0 m15 modunun sime kolayca takılıp aynı senaryo, ölçüt ve videoyla denenebilmesi
  - [ ] 10.1 Testleri yaz (2–4 test): `calistir.sh`'a giden argüman listesinin oluşturulması (`takip.px4_baslat` + `--px4-baslat`, `takip.px4_parametreleri` + `--param` sırası); "unresponsive" kontrolünün yalnız harici modlu koşuda açılması. (`takip.px4_parametreleri` + `--param` sırası 2. grupta `test_hedef.py`'de sınandı.)
  - [ ] 10.2 `derle.sh --harici <klasör>` → `EXTERNAL_MODULES_LOCATION`; bayrak yoksa `tez/px4/src/CMakeLists.txt` varsa o, yoksa stok; çıktı her zaman `build/px4_sitl_tez`; klasör önbellektekinden farklıysa CMake yeniden yapılandırılır
  - [ ] 10.3 `calistir.sh --px4-baslat "<komut>"` (çoklu): `px4-logger status` başarılı olana kadar en çok 90 s beklenir; komut `rootfs` içinde `bin/px4-<komut>` ile çalışır, çıktısı sim log'una yazılır
  - [ ] 10.4 `senaryo.py`/`simulasyon.py`: `takip.px4_baslat`, `takip.px4_parametreleri`, `--px4-baslat` bağlanır; harici modlu koşu sonunda `sim.log`'da "unresponsive" aranır. 2. gruptaki ilgili ara hatalar kaldırılır. (`takip.px4_parametreleri` ve `--param` 2. grupta bağlandı ve koşuda PX4'ten geri okunuyor; burada yalnız `px4_baslat` kalır.)
  - [ ] 10.5 README "C. Kendi PX4 modülünü takmak" bölümü (spec "Takım Arkadaşı Kılavuzu" C1–C8); iskelet modül notları (`PARENT_SCOPE`, `DEPENDS` yok, `register_ext_component_request`, 24 karakter) `c4b4abf342`'ye atıfla
  - [ ] 10.6 Doğrulama

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

**Kabul Ölçütleri:**
- 10.1'deki testler geçer
- Ağaç dışı bir modül derlenir, başlatılır, adıyla seçilir; aynı ölçütler ve MP4 üretilir
- Bayraksız derleme stok hâle döner; m06 kilit listesine yol eklemez

### Video Yayını

#### Görev Grubu 11: QGC'ye canlı video (H.264 RTP, UDP 5600)
**Bağımlılık:** Görev Grubu 9 · **Emek:** ~0.6 gün

- [ ] 11.0 Model ve hakem kutuları çizilmiş görüntünün QGC'de canlı izlenmesi
  - [ ] 11.1 Testleri yaz (2–4 test): UDP 5610 JSON mesajının paketlenmesi/çözülmesi (son model sonucu + hakem kutusu); GStreamer hattı metninde gerekli öğeler ve ayarlar (`leaky=downstream`, `tune=zerolatency`, `key-int-max=15`, `config-interval=1`, `pt=96`, `sync=false`); tek başına modda LOS gönderilmemesi
  - [ ] 11.2 apt paketlerini sabitle (kullanılmadan önce): `python3-gi`, `gir1.2-gstreamer-1.0`, `gir1.2-gst-plugins-base-1.0`, `gstreamer1.0-plugins-base`, `-good`, `-ugly`, `gstreamer1.0-libav`, `libfuse2t64`. Sürümler `dpkg-query -W` ile okunup `VERSIONS.md`'ye yazılır.
  - [ ] 11.3 `goruntu_yayini.py`, yayın kısmı: `appsrc` (BGR, 1280×720, 15/1, canlı) → `queue leaky=downstream max-size-buffers=2` → `videoconvert` (I420) → `x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000 key-int-max=15` (`constrained-baseline`) → `rtph264pay config-interval=1 pt=96 mtu=1400` → `udpsink host=127.0.0.1 port=5600 sync=false`. Deney dalındaki sabit `x500_mono_cam_0` kullanılmaz.
  - [ ] 11.4 Kutular: senaryo koşusunda ana süreçten `127.0.0.1:5610` UDP JSON; tek başına modda `--model` ile kendi algılayıcısı (hakem kutusu yok, LOS yok)
  - [ ] 11.5 `araclar/yayin.sdp`; `--qgc` / `video.qgc` bağlanır (ayrı süreç, sızdıran kuyruk). 2. gruptaki `--qgc` ara hatası kaldırılır.
  - [ ] 11.6 Doğrulama

    ```bash
    $P -m pytest tez/sim/testler -q
    $P -m ruff format --config tez/sim/ruff.toml tez/sim && $P -m ruff check --config tez/sim/ruff.toml tez/sim
    tez/pin/verify_pin.sh --worktree
    $P $S/senaryo.py --senaryo takip_yuruyen --ekransiz --qgc
    gst-launch-1.0 udpsrc port=5600 caps="application/x-rtp,media=video,encoding-name=H264,payload=96" ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false
    vlc tez/sim/araclar/yayin.sdp                                # QGC'siz ikinci yol
    ```

    **Görsel kontrol (Ahmet):** QGC 5.1.4 → Uygulama Ayarları → Video → "UDP h.264 Video Stream", port 5600; görüntü akar, kutular çizilidir. `--qgc`'li koşunun `islenen_kare_hizi_hz` ve RTF değerleri 9. gruptaki koşuyla `karsilastir.py` (12. grup) ya da `ozet.json` üzerinden karşılaştırılır; belirgin düşüş varsa `implementation/`'a yazılır.

**Kabul Ölçütleri:**
- 11.1'deki testler geçer; apt sürümleri `VERSIONS.md`'dedir
- QGC'de canlı görüntü vardır; yayın model ve kayıt hattını belirgin yavaşlatmaz

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

#### Görev Grubu 17: Yaklaşma mesafelerinin gerçek modelle yeniden ölçülmesi
**Bağımlılık:** Görev Grubu 15 (isteğe bağlı), m15 hazırsa o da · **Emek:** ~1 gün (koşu süresi ağırlıklı)

- [ ] 17.0 45° raporundaki sayıların yeni simde doğrulanması
  - [ ] 17.1 Testleri yaz (2–3 test): raporun "zor yolu" senaryosunun (yürü, dön, dur, birden koş, geri dön) doğrulaması; çoklu koşu özet tablosu
  - [ ] 17.2 3'er koşu: 8/8, 10/10, 15/12; aralık sınırları (8 m'de 6.5 ve 10 m; 10 m'de 8 ve 12 m); olumsuz kontrol 6/8; `duz_alan` ve `cayir`; `follow_me` (m15 hazırsa o da)
  - [ ] 17.3 Sonuçlar (kadrajda kalma, gerçekten görünür kalma, en uzun kayıp, konum hatası) spec "Yaklaşma mesafesi" bölümüyle karşılaştırılır ve bölüm güncellenir
  - [ ] 17.4 Doğrulama: pytest + ruff + `verify_pin.sh --worktree`; koşu klasörleri `karsilastir.py` ile tek tabloda; seçilmiş birkaç `kosu.mp4` Ahmet'in VLC kontrolünden geçer

**Kabul Ölçütleri:** Spec'teki yaklaşma mesafesi tablosu yeni ölçümlerle güncellenmiştir.

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
12. Görev Grupları 15 → 16 → 17 — Faz B, ikinci PR

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
