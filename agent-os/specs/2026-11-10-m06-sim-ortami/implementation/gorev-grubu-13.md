# Görev Grubu 13 — `m06_kabul.sh`, `kur.sh` model kontrolü, sürümlerin ve README'nin tamamlanması

- Tarih: 15.11.2026 · dal `ozellik/m06-sim-ortami` · taban commit `bbe3c16b6e` + çalışma ağacı
- Kapsam: `tasks.md` 13.0–13.9 (Faz A'nın son Autopilot grubu; ardından PR)
- Durum: **13.4 dışında uygulandı, test edildi, koşuldu**; commit'i ana oturum atar. 13.4 (`yolov8s.pt`) dosyanın
  elle indirilmesini bekliyor (bölüm 7). Görsel kontrol Ahmet'te ("Kendin dene" 1–2).

## Kısaca

- **Yeni kabul testi `tez/sim/araclar/m06_kabul.sh`** (`m06_testi.py`, F0'ın OK / HATA ve "SONUÇ" düzeni): koşu 1
  `takip_yuruyen` (v0.2 + stok Follow Me), koşu 2 `kalabalik_park` (v0.2, Hold), her biri ayrı bir `senaryo.py`
  süreci; spec "Test Planı"nın yedi koşulu her koşuda bir satır. `--mod-adi` / `--px4-baslat` ile isteğe bağlı koşu 3
  (takılmış bir PX4 modu, ör. m15). Çıktı `tez/sim/sonuclar/<tarih>_m06_kabul/`.
- **13.9 zinciri:** F0 GEÇTİ → F1 GEÇTİ → **m06 GEÇTİ** (4 dk 55 s; 2 koşu × 7 koşul + kilit, hepsi OK). Koşu 1:
  `TEZ_LOS` ULog 356 = gönderilen 356, "Follow Target" kayıtta %100, ULog `follow_target` 56, IoU ≥ 0.5 346 karenin
  212'sinde, video h264 / yuv420p / 2000×720 61.93 s (kayıt 61.97 s), 135/135 anahtar. Koşu 2: 404 = 404, Hold %100,
  237 / 390, video 64.87 s (64.81 s), 135/135.
- **Koşu 3 iskelet modülle** (`derle.sh --harici`, "Tez Auto Follow"): GEÇTİ (mod %100, "unresponsive" 0, `TEZ_LOS`
  337 = 337); bayraksız `derle.sh` stoka döndü, F0 yine GEÇTİ.
- **`kur.sh` sonunda model klasörünü denetler** (`algilama.py`; indirmez): bu makinede v0.2 `TAMAM`, `yolov8s.pt`
  `EKSİK` + "Almak için" satırı; eksik model uyarıdır (çıkış 0), bozuk `modeller.yaml` hatadır (1).
- **`yolov8s.pt`'nin adresi** kurulu ultralytics 8.4.174'ün kodundan:
  `https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s.pt` (`modeller.yaml`, spec, VERSIONS);
  dosya indirilmedi, sha256 / boyut `null` (13.4 açık).
- **Belgeler:** `VERSIONS.md` (AMD `DRI_PRIME=1`, QGC'de `libfuse2t64`, AGPL, model dosyaları; sürüm değişmedi, venv
  ile tutarlı), README yeniden düzenlendi (A1–A7, B1–B6, C, Ayrıntılar, Sorun giderme), spec / tasks / ekip özeti.
- **Temiz klon (13.8):** README'deki dosya ve bayrakların hepsi var; submodule / derleme / kurulum adımları denenmedi
  (ağ / süre); README'ye `requirements-lock.txt` adımı ve üç sorun giderme satırı eklendi.
- 312 birim testi (309 + 3), ruff temiz, **KILIT SAGLAM**.

## 1. Ne yapıldı

| Alt görev | Dosya | Sonuç |
|---|---|---|
| 13.1 | `tez/sim/testler/test_m06_testi.py` (yeni, 2 test), `test_algilama.py` (+1 test, 1 test güncellendi) | Bölüm 3 |
| 13.2 | `tez/sim/araclar/m06_testi.py` (yeni), `m06_kabul.sh` (yeni), `simulasyon.py` (`LEFT_RUNNING`), `rapor.py` (`MODE_KEPT`), `toplu.py` (`wait_until_closed` herkese açık), `ruff.toml` | Yedi koşul, OK / HATA satırları, "SONUÇ: GEÇTİ / KALDI" (F0 düzeni) |
| 13.3 | `tez/sim/kur.sh`, `tez/sim/araclar/algilama.py` (`check_folder`, `folder_lines`, `main`) | Model klasörü `modeller.yaml`'a göre denetlenir; indirmez; eksik model uyarı (çıkış 0) |
| 13.4 | `tez/sim/modeller.yaml` | `yolov8s.pt`'nin adresi (ultralytics 8.4.174'ün kendi adresi); dosya indirilmedi, sha256 / boyut `null`; **açık** |
| 13.5 | `tez/env/VERSIONS.md` | AMD `DRI_PRIME=1` bölümü, QGC kurulumunda `libfuse2t64`, AGPL tablo 1'de, model dosyaları, sürüm kontrolü satırları; sürüm değişmedi |
| 13.6 | `tez/sim/README.md` (yeniden düzenlendi), `TEZ_README.md` (+2 satır) | A. Kurulum (A1–A7), B. Çalıştırma (B1–B6), C, Ayrıntılar, Sorun giderme, Dosyalar |
| 13.7 | `spec.md`, `tasks.md`, `EKIP_ICIN_OZET.md`, bu dosya, `kabul-kosulari.md` | Bölüm 8 |
| 13.8 | scratchpad'de klon (silindi) | Bölüm 6 |
| 13.9 | koşular | Bölüm 4–5 |

## 2. Kararlar ve gerekçeler

1. **Her koşu ayrı bir `senaryo.py` süreci** (`toplu.command`, `toplu.read_summary`): F1 gibi süreç içinde değil.
   Gerekçe: model süreci, gz-transport düğümleri ve bellek bir koşudan ötekine taşınmaz (`toplu.py`'nin kararıyla aynı);
   kullanıcının elle koştuğu yolun aynısı denenir. `senaryo.py`'nin çıktısı hem ekrana hem
   `kosu<i>_<senaryo>.log`'a yazılır; kontrol satırları her koşudan sonra ve sonda özet olarak tekrar basılır.
2. **Takip kaynağı ve LOS açıkça verilir** (`--takip follow_me|yok --los model`): senaryo dosyası değişse de kabul
   testi spec'teki koşuyu koşar.
3. **Çıktı yeri `tez/sim/sonuclar/<tarih>_m06_kabul/`** (F0 / F1 gibi `build/.../tez_kabul` değil): `tasks.md` 13.9
   videoyu `tez/sim/sonuclar/<m06 koşu 1>/kosu.mp4` olarak açar ve kabul koşusunun videosu kullanıcının bakacağı
   sonuçtur. `--cikti` verilirse dolu bir klasör reddedilir (eski bir `kosu.mp4` yeni koşunun yerine denetlenmesin;
   F1'in yaptığı gibi silmek yerine, çünkü klasör kullanıcının sonuçlarıdır).
4. **Koşul 1'deki parametreler:** her koşuda `ayarlar.px4_parametreleri`'nin her satırı (dosyalar + senaryo +
   `--param`; kalkıştan önce `PARAM_REQUEST_READ` ile okunan değer) istenen değerde olmalı, iki `.params` dosyasının her
   adı yüklü olmalı ve `SYS_AUTOSTART` 4001 olmalı. F0'dan farkı: senaryo bir dosya değerini ezebilir (`takip_yuruyen`'de
   `FLW_TGT_DST` 8 → 12.9), bu yüzden dosyadaki değer değil koşunun istediği değer denetlenir. `SYS_AUTOSTART` koşunun
   ULog başlığından okunur (pyulog `parse_header_only`, ~5 ms): `ozet.json`'da yok ve koşu sırasında PX4'e ikinci bir
   MAVLink bağlantısı açmak gerekmez.
5. **Koşul 4 bütün koşulara uygulanır** (spec yalnız koşu 1'i yazar): koşunun modu adıyla seçilmiş ve kayıt boyunca
   korunmuş olmalı (`mod_korunma_orani` ≥ 0.999, raporun uyarı eşiğiyle aynı sabit `rapor.MODE_KEPT`); `follow_target`
   ULog kaydı yalnız `follow_me`'de aranır. Gerekçe: koşu 2'de Hold'dan düşen ya da koşu 3'te harici moddan düşen bir
   dron da zinciri bozar; ek bir eşik değil, aynı koşulun öteki koşulara uygulanmasıdır.
6. **"Koşu tamamlandı" satırı:** `TAMAMLANMADI` (açılmayan sim, tutmayan parametre, "unresponsive", eğim farkı,
   bozuk `TEZ_LOS` akışı, model süreci hatası) kalır; `KALDI` yalnız senaryonun `basari` eşiklerinden gelir ve spec
   "işlevseldir, başarım eşiği değildir" dediği için m06 koşulu sayılmaz (bugünkü senaryolarda `basari: {}`).
7. **Temiz kapanış:** `senaryo.py` kapanışta 10 s bekleyip kalan süreci olaya yazar (`simulasyon.LEFT_RUNNING`, artık
   sabit); m06 ayrıca `senaryo.py` bittikten hemen sonra `running()`'e bakar. Sonraki koşudan önce 120 s'ye kadar
   beklenir (`toplu.wait_until_closed`, önce `_wait_until_closed`'dı).
8. **İsteğe bağlı koşu 3 `--los model`'le:** gerçek zincir (model → `TEZ_LOS` → mod). 10. gruptaki `--los hakem`
   denemesi `senaryo.py` ile yapılabilir (README C6).
9. **`kur.sh`'ın model denetimi `algilama.py`'de** (`check_folder` + küçük komut satırı): `modeller.yaml`'ı okuyan ve
   sha256 hesaplayan kod zaten oradaydı (`load_catalog`, `file_sha256`); bash'te YAML ayrıştırmak yerine aynı kod.
   Eksik / farklı model uyarıdır (çıkış 0): spec bir hata koşulu tanımlamıyor ve modelsiz koşular (`--modelsiz`, F0, F1)
   çalışır; yalnız bozuk `modeller.yaml` hatadır (her modelli koşuyu da bozar). Venv yoksa denetim atlanır, uyarı
   yazılır.
10. **`yolov8s.pt`'nin adresi** kurulu paketin kodundan: `ultralytics/utils/downloads.py` → `GITHUB_ASSETS_NAMES`
    `yolov8{n,s,m,l,x}.pt`'yi içerir ve `attempt_download_asset(file, repo="ultralytics/assets", release="v8.4.0")`
    bu adlar için `https://github.com/ultralytics/assets/releases/download/v8.4.0/<ad>` kullanır
    (`nn/tasks.py:1862` `attempt_download_asset(weight)`, varsayılan sürümle). `alma`'da `curl -fL` (`-f`: HTTP
    hatasında bir HTML sayfası `yolov8s.pt` diye kaydedilmez).
11. **README:** önceki gruplarda iki eski ifade ("`TEZ_` ön eki", "kilit listesinde izinli iki dosya") zaten kalkmıştı;
    `../Vision/.venv` yalnız `ruff.toml`'un yorumunda kalmıştı, ekip venv'ine döndü. Metnin ayrıntılı bölümleri
    (11. grubun `--qgc` / ffplay / gst-launch, 12. grubun `--gecikme-ms` / `--yeniden-kilit-bekleme-s` / `karsilastir.py`
    satırları dahil) kelimesi kelimesine taşındı; yeni yazılanlar A, B1–B2, B6, Sorun giderme ve atıflar.

## 3. Testler

`tez/sim/testler/test_m06_testi.py` (yeni, 2 test; simsiz):

1. `test_ozet_json_has_every_key_of_the_metric_definitions`: bütün `olcum.KEYS` (135) varken geçer, `null` değerler
   sayılır ("2 tanesi null"), fazla anahtar sorun değildir; iki anahtar silinince ikisi de adıyla eksik, `olcutler`
   yoksa hepsi eksik; `rapor.html` yoksa kalır.
2. `test_tez_los_in_the_ulog_is_the_sent_count_within_five_percent`: (333, 333), (100, 95), (100, 105), (892, 850)
   geçer; (100, 94), (100, 106), (333, 316), (892, 0) kalır; hiç gönderilmeyen (0 / `null`) ve ULog'da olmayan kalır;
   `tez_los_check` `ozet.json`'dan okur.

`tez/sim/testler/test_algilama.py`: yeni `test_model_folder_check_of_kur_sh` (kayıtla aynı / farklı / özetsiz / eksik /
kayıtsız kopya; "Almak için" satırı ve kaynak, yazılacak sha256; klasör yoksa hepsi eksik + `mkdir -p`; `main` eksik
modelde 0 döner); `test_catalog_in_the_repo_and_its_checks` artık `yolov8s.pt` kaydının adresini de denetler.

Üç test de kod yazılmadan önce kırmızıydı (modül yok / `check_folder` yok / adres yok).

| Kontrol | Sonuç |
|---|---|
| `pytest tez/sim/testler -q` | **312 passed** (önce 309), 1 uyarı (sistemdeki protobuf, eskiden beri) |
| `ruff format` + `ruff check` (`tez/sim/ruff.toml`) | 64 dosya değişmedi; All checks passed |
| `tez/pin/verify_pin.sh --worktree` | **KILIT SAGLAM (v1.17.0)** |
| `bash -n` + `shellcheck` (`kur.sh`, `m06_kabul.sh`) | temiz |
| m06 kontrolleri, sim'siz | 12. grubun iki koşusu ve 10. grubun harici koşusu üzerinde (koşu 1 / 2 / 3 olarak) bütün satırlar OK: kontroller gerçek `ozet.json`'larla tutarlı |

## 4. Koşular (13.9)

Sıra: `derle.sh` (stok, "no work to do") → `kur.sh` → `f0_kabul.sh && f1_kabul.sh && m06_kabul.sh --cikti
tez/sim/sonuclar/gorev13_m06` (02:57–03:07). Satır satır `kabul-kosulari.md`; günlükler `tez/sim/sonuclar/gorev13_kur.log`,
`gorev13_f0.log`, `gorev13_f1.log`, `gorev13_m06.log`.

| Adım | Sonuç |
|---|---|
| `kur.sh` | Varlıklar kurulu, `cayir` güncel; model satırları: `TAMAM person_detection_model_v0.2.pt` (sha256 `c5f6838b…a440`, 22 525 930 bayt), `EKSİK yolov8s.pt` + kaynak + "Almak için"; çıkış 0 |
| F0 | GEÇTİ (≈ 1 dk 10 s): 2304×1296, 30.3 kare/sim-s, fx 1773.9; 4001; 21/21 parametre; Hold + Follow Target; 10 m; Hold'da sapma 0.05 / 0.06 m; temiz kapanış |
| F1 | GEÇTİ (4 dk 25 s): hedef farkı en fazla 0.13 / 0.13 m, iki koşu arası 0.000 m; RTF 0.941 / 0.942 |
| m06 | **GEÇTİ** (4 dk 55 s; spec "~8–10 dk" tahmininden kısa) |

**m06'nın yedi koşulu** (`tez/sim/sonuclar/gorev13_m06/`):

| Koşul | Koşu 1 `takip_yuruyen` (`follow_me`) | Koşu 2 `kalabalik_park` (`yok`) |
|---|---|---|
| Koşu tamamlandı | GEÇTİ, çıkış 0 | GEÇTİ, çıkış 0 |
| 1. kilit + parametreler | KILIT SAGLAM; 22/22 parametre PX4'te istenen değerde, dosyalardaki 21/21 yüklü, ULog'da `SYS_AUTOSTART` 4001 | aynı kilit; 21/21, 21/21, 4001 |
| 2. model | v0.2 yüklendi, sha256 `c5f6838b…a440` (`modeller.yaml`'da kayıtlı); IoU ≥ 0.5 346 karenin 212'sinde (en iyi 0.91) | aynı model; 390 karenin 237'sinde (0.93) |
| 3. `TEZ_LOS` ULog'da | ULog 356 = gönderilen 356 (%0) | 404 = 404 (%0) |
| 4. mod | "Follow Target" 27.5 s'de adıyla, kayıtta %100 (ULog); ULog `follow_target` 56 kayıt | "Hold" 24.4 s'de, %100 |
| 5. video (`ffprobe`) | h264, yuv420p, 2000×720, 929 kare, 61.93 s; kayıt 61.97 s | 973 kare, 64.87 s; kayıt 64.81 s |
| 6. `ozet.json` + rapor | 135/135 anahtar (0 null), `rapor.html` | 135/135 (40 null: takip ve PX4 Follow Target ölçütleri), `rapor.html` |
| 7. temiz kapanış | PX4 ve Gazebo kapandı; harici mod yok | aynı |

Bilgi (koşul değil): koşu 1 RTF 0.926, bulma %61.3, kilit kaybı 2, en az mesafe 6.23 m (79.5 s), uçtan uca 131.7 ms;
koşu 2 RTF 0.833 (raporda uyarı), bulma %60.8, yanlış kişi %13.6, seçim doğru %49.5. 17. grubun ve 12. grubun koşularının
aralığında.

**Koşu 1 videosu (`ffprobe`):** `codec_name=h264`, `profile=High`, `pix_fmt=yuv420p`, 2000×720, `r_frame_rate=15/1`,
929 kare, 61.93 s, 4.3 MB (`tez/sim/sonuclar/gorev13_m06/kosu1_takip_yuruyen/kosu.mp4`). Videoda kişi 0:32.5'te
yürümeye başlar; köşeler 0:32.7 (kalkış), 0:45.5, 0:50.0; en az mesafe 0:52.0.

## 5. İsteğe bağlı koşu 3 (iskelet modül)

İskelet modül (`c4b4abf342`, 10. grup) scratchpad'e `git archive` ile açıldı, değiştirilmedi:
`tez/sim/derle.sh --harici <scratchpad>/g13/iskelet/tez/px4` (7 s, `bin/px4-tez_auto_follow` var), sonra
`tez/sim/araclar/m06_kabul.sh --cikti tez/sim/sonuclar/gorev13_m06_kosu3 --mod-adi "Tez Auto Follow" --px4-baslat
"tez_auto_follow start"` (03:08–03:15, 7 dk 15 s; günlük `gorev13_m06_kosu3.log`): **SONUÇ: GEÇTİ**, 3 koşu × 7
koşul + kilit.

| | Koşu 3 (`takip_yuruyen --takip tez_los --mod-adi "Tez Auto Follow" --los model --px4-baslat "tez_auto_follow start"`) |
|---|---|
| Başlatma | `tez_auto_follow start` çıkış 0; `sim.log`: "registered as 'Tez Auto Follow' (nav_state 23, arming check 0)"; PX4'ün mod listesi 18 ad |
| 1–3 | 22/22 parametre, 4001; IoU ≥ 0.5 336 karenin 160'ında (0.87); `TEZ_LOS` 337 = 337 |
| 4 | "Tez Auto Follow" 27.4 s'de adıyla, kayıtta %100 (ULog `nav_state` 23) |
| 5–6 | 944 kare, 62.93 s (kayıt 62.96 s); 135/135 anahtar (32 null) |
| 7 | temiz kapanış; `sim.log`'da "unresponsive" 0 satır |
| Takip | iskelet seçildiği yerde konum tutar ("mode active, holding N 0.0 E -0.0 D -8.9 m"): yatay mesafe ort. 21.3 m, en çok 26.5 m. **Beklenen**: kabul işlevseldir, takip başarımı değil |

Aynı harici derlemede koşu 1 ve 2 de geçti (modül derlemede ama başlatılmadı: 17 mod; `TEZ_LOS` 365 = 365, 405 = 405).
Ardından bayraksız `tez/sim/derle.sh` stoka döndü ("Derlemede olmayan modülün komutu silindi", `EXTERNAL_MODULES_LOCATION`
boş) ve F0 yine GEÇTİ (`gorev13_f0_stoka_donus.log`). Kurt / Algan'ın modülü gelince aynı komut onun adı ve başlatma
komutuyla koşulur.

## 6. Temiz klon denemesi (13.8)

`git clone /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot <scratchpad>/g13/klon` (1.5 s, 918 MB, dal
`ozellik/m06-sim-ortami` @ `bbe3c16b6e`); commit'lenmemiş 19 dosya (bu grubun değişiklikleri) klona kopyalandı. Sonra
README A bir takım arkadaşı gibi satır satır izlendi; bitince klon silindi.

| Adım | Klonda | Sonuç |
|---|---|---|
| A1 `git submodule update --init --recursive`, `Tools/setup/ubuntu.sh`, `make px4_sitl` | **denenmedi** (ağ / süre: 29 submodule, PX4 derlemesi) | Dosyalar var. Submodule'süz `verify_pin.sh --worktree` → "KILIT BOZULMUS" (submodule satırlarının başında `-`); `--worktree`'siz → "KILIT SAGLAM". A1'in sırası (önce submodule) doğru; sorun giderme satırı eklendi |
| A2 apt paketleri, QGC | **denenmedi** (kurulum / ağ) | Paket adları `VERSIONS.md` ile aynı; bu makinede `dpkg-query -W` sürümleri tutuyor |
| A3 venv, pip | **denenmedi** (ağ); ekip venv'i kullanıldı | Üç requirements dosyası klonda var. Bu sırada bulundu: A3'te `requirements-lock.txt` (`~/.local`; model paketleri numpy / matplotlib'i oradan alır) yazılı değildi, eklendi |
| A4 model dosyası | asıl makinedeki `~/auto-follow-modeller/` | `git -C Vision show ebff718:...` için commit Vision klonunda var (`git cat-file -t ebff718` → commit) |
| A5 `derle.sh` | **denenmedi** (PX4 derlemesi, submodule'süz olmaz) | `bash -n` temiz; `--help`, `--harici` asıl ağaçta koşuldu |
| A5 `kur.sh` | ağ kapalı (geçersiz proxy) | Varlıklar yokken ilk indirmede `curl: (7)` ile durdu (beklenen: ilk kurulum internet ister; sorun giderme satırı eklendi). Asıl ağaçtaki varlıklar gerçek kopya olarak konunca: hepsi "kurulu / güncel", **ekip yapısı dışındaki klonda venv bulunamadı** → "UYARI: Python ortamı yok … denetlenmedi", çıkış 0 (sorun giderme satırı eklendi); `TEZ_PYTHON=…/.venv-tez/bin/python` ile model satırları (`TAMAM` v0.2, `EKSİK` yolov8s.pt), çıkış 0; klonda bozulan `modeller.yaml` → "HATA: … okunamadı", çıkış 1 |
| A7 kabul testleri | **klonda denenmedi** (derleme yok) | Asıl ağaçta koşuldu (bölüm 4). Klonda araçların `--help`'i açıldı (`senaryo`, `m06_testi`, `f0_testi`, `toplu`, `karsilastir`, `algilama`, `goruntu_yayini`); pytest 311 geçti + 1 atlandı (derleme gerektiren `calistir.sh` testi) |
| README'deki dosyalar ve bayraklar | asıl ağaçta, betikle | README'de bir araçla geçen her `--bayrak` o aracın `--help`'inde var (`tarama.py kos ... -- --videosuz` gibi `--`'dan sonrakiler `senaryo.py`'nindir); bağlantılı her dosya var |

Klonda `dunya.py` (sistem `python3`) "güncel" dedi; bu makinede sistem `python3` PIL ve PyYAML'ı apt'ten (`python3-pil`
10.2.0, `python3-yaml` 6.0.1), numpy'ı `~/.local`'dan alıyor. Temiz bir Ubuntu'da `python3-pil` kurulu değilse ilk
`kur.sh` dünya üretiminde durabilir (denenmedi): bölüm 10, öneri 1.

## 7. 13.4: `yolov8s.pt` ve kıyas koşusu (açık)

Adres yazıldı (bölüm 2, karar 10), dosya indirilmedi. Kalan iş (kullanıcı; tam komutlar "Kendin dene" 6):

1. İndir: `mkdir -p ~/auto-follow-modeller && curl -fL -o ~/auto-follow-modeller/yolov8s.pt https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s.pt`.
2. `tez/sim/kur.sh` → `ÖZETSİZ yolov8s.pt: sha256 …, … bayt`: bu iki değer `modeller.yaml` (`sha256`, `boyut_bayt`),
   spec "Model dosyası" tablosu ve "Açık Konular" → "Uygulamada sabitlenecek sürümler"e yazılır; sonra `kur.sh`
   `TAMAM` der.
3. Kıyas koşusu (model ölçütleri için takipsiz senaryo; COCO'nun `person` sınıfı adıyla seçilir, `imgsz` `.pt`'den):
   `senaryo.py --senaryo kalabalik_park --ekransiz --model ~/auto-follow-modeller/yolov8s.pt --cikti
   tez/sim/sonuclar/gorev13_yolov8s_kalabalik_park`.
4. `karsilastir.py tez/sim/sonuclar/gorev13_m06/kosu2_kalabalik_park tez/sim/sonuclar/gorev13_yolov8s_kalabalik_park
   --html tez/sim/sonuclar/gorev13_yolov8s_kalabalik_park/karsilastirma.html` (ilk sütun v0.2, aynı kod ve senaryo;
   farklı ayar satırında model sha256 görünür). Sonuç `implementation/`'a ve `kabul-kosulari.md`'ye yazılır.

Bilinmeyen: GitHub'daki v8.4.0 `yolov8s.pt`'nin ultralytics 8.4.174 ile `YOLO_OFFLINE` / `weights_only` yüklemesi
denenmedi (dosya yok). Yüklenmezse koşu sim açılmadan "Model hatası" ile durur (çıkış 2).

## 8. Belgeler

- `spec.md`: 3. gereksinim (kıyas modelinin adresi), 7. gereksinim (`kur.sh`'ın uygulaması), 10. gereksinimdeki
  "TBD" (11. grupta yazılmıştı), "Model dosyası" (teyit gelmedi; kıyas modeli), Dosya planı (`kur.sh`, `modeller.yaml`,
  `m06_testi.py`, README, VERSIONS), Test Planı (`test_m06_testi.py` satırı, m06 kabulünün uygulaması), Takım
  Arkadaşı Kılavuzu (README A / B), teslim sırası 7, Açık Konular (durumlar, sürümler, üç yeni madde).
- `tasks.md`: 13.1–13.3, 13.5–13.9 `[x]` ve "Uygulamada" notları; 13.4 ve 13.0 açık; "Durum (15.11)".
- `EKIP_ICIN_OZET.md` 7. bölüm: kurulum README'ye atıf, kabul testleri satırı, kendi modunla kabul testi.
- `kabul-kosulari.md`: F0, F1, m06, koşu 3, stoka dönüş F0.
- `tez/sim/README.md`, `tez/env/VERSIONS.md`, `TEZ_README.md`, `tez/sim/ruff.toml` yorumu.

## 9. Karşılaşılan sorunlar ve bulgular

1. **`~/.local` sürüm kayması (bu makine, kural 4):** `requirements-lock.txt` `coverage==7.16.1`, `fonttools==4.66.0`
   der; kurulu 7.16.2 ve 4.66.1. Üç dosyanın kalan her sabit sürümü kurulu olanla aynı (`model-requirements.txt` 29/29,
   `analiz-requirements.txt` 24/24, kilit 27/29); `pip check` temiz. Dosya değiştirilmedi, sürüm düzeltilmedi (karar
   kullanıcının; komut bölüm 10).
2. **ULog birikmesi:** `build/px4_sitl_tez/rootfs/log/` 14 GB (her açılışın ULog'u; koşular kopyasını alır). Silinmedi;
   README "Sorun giderme"ye yazıldı.
3. **README'deki iki eski ifade zaten yoktu** (önceki gruplarda kalkmış); `../Vision/.venv` yalnız `ruff.toml`
   yorumundaydı.
4. Kabul koşularında sorun çıkmadı; altyapı hatası (heartbeat yok, Gazebo takılması) görülmedi, yeniden deneme
   gerekmedi.

## 10. Açık konular ve sorulacaklar

- **13.4 (kullanıcı):** `yolov8s.pt`'yi indirmek, sha256 / boyutu yazmak, kıyas koşusu (bölüm 7).
- **Öneri 1 (onay bekliyor, uygulanmadı):** `kur.sh`'ın `animasyon.py` ve `dunya.py` çağrılarını sistem `python3`
  yerine `TEZ_PYTHON` / ekip venv'iyle çalıştırmak (spec 7. gereksinimin sözü; dünyalar sabit sürümlü numpy / pillow ile
  üretilir, temiz makinede `python3-pil` gerekmez). Bu makinede dünya yeniden üretilmez (girdi özeti değişmez).
- **Öneri 2 (onay bekliyor):** ULog birikmesi için bir temizlik (ör. koşu kopyasını aldıktan sonra rootfs'teki ULog'u
  silmek ya da `derle.sh --temiz`'e eklemek); şimdilik yalnız belgede.
- **Kullanıcıya:** `~/.local` kayması için `pip install --user --break-system-packages -r tez/env/requirements-lock.txt`
  (yalnız bu iki paketi kilitteki sürüme döndürür).
- **Hüseyin'e (değişmedi):** ortak model depolama yeri (`modeller.yaml` `kaynak`), m06/m08 sınırı, çatı
  `tech-stack.md` / `docs/02` (Görev Grubu 14: model paketleri, AGPL, GStreamer / ffmpeg, `libfuse2t64`, `DRI_PRIME`).
- **Ortatepe'den (değişmedi):** v0.2 üst verisinin teyidi.
- **Kurt / Algan'dan (değişmedi):** modülün yeri ve başlatma komutu; gelince `m06_kabul.sh --mod-adi "AUTO FOLLOW"
  --px4-baslat "<komut>"`.

## 11. Dosyalar (commit'e girecekler)

- `tez/sim/araclar/m06_testi.py` (yeni), `tez/sim/araclar/m06_kabul.sh` (yeni), `tez/sim/testler/test_m06_testi.py`
  (yeni), `tez/sim/araclar/simulasyon.py`, `tez/sim/araclar/rapor.py`, `tez/sim/araclar/toplu.py`, `tez/sim/ruff.toml`
- `tez/sim/kur.sh`, `tez/sim/araclar/algilama.py`, `tez/sim/testler/test_algilama.py`
- `tez/sim/modeller.yaml`
- `tez/env/VERSIONS.md`
- `tez/sim/README.md`, `TEZ_README.md`
- `agent-os/specs/2026-11-10-m06-sim-ortami/spec.md`, `tasks.md`, `EKIP_ICIN_OZET.md`,
  `implementation/gorev-grubu-13.md` (yeni, bu dosya), `implementation/kabul-kosulari.md`

Repo dışı / git dışı: koşu klasörleri `tez/sim/sonuclar/gorev13_*` (videolar, ULog, raporlar) ve günlükler
`gorev13_*.log`; iskelet modül ve README taslakları scratchpad'de. PX4 dosyası, ROMFS, submodule değişmedi; kilit listesi
genişlemedi; yeni paket kurulmadı, ağdan bir şey indirilmedi.

## Kendin dene

**Başlamadan:** Terminal açmak için **Ctrl+Alt+T**. Aşağıdaki gri kutulardaki satırları **tek tek** kopyala, terminale
**Ctrl+Shift+V** ile yapıştır ve **Enter**'a bas. Her satır tek başına çalışır. Bir komutu yarıda kesmek için
**Ctrl+C**.

### 1. Kabul koşusunun videosu: koşu 1, takip (asıl görsel kontrol, ~1 dakika)

Kişi videoda 0:32.5'te yürümeye başlar; köşeler ≈ 0:45.5 ve 0:50.0; dron kişiye en çok 0:52.0'de yaklaşır (6.2 m).
Bakılacaklar: kırmızı model kutusu kişinin üstünde ve biraz gerisinde, mavi hakem kutusu kişiyle çakışıyor; sağdaki
haritada dron kişiyi ≈ 12.9 m geriden izliyor; üstte mod "Follow Target".

```bash
vlc /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev13_m06/kosu1_takip_yuruyen/kosu.mp4 2>/dev/null
```

### 2. Koşu 2 (kalabalık park, dron Hold'da) ve koşu 3 (iskelet modül)

Koşu 2'de kişi 0:35.5'te yürür; kilit 0:44.7'de düşer (kişi çamın arkasında), 0:53.4'te yeniden kilitlenir; yanlış
kişiye geçişlerde altta kırmızı "YANLIŞ KİŞİ".

```bash
vlc /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev13_m06/kosu2_kalabalik_park/kosu.mp4 2>/dev/null
```

Koşu 3'te üstte mod "Tez Auto Follow"; iskelet modül yalnız konum tutar, dron kişiyi **izlemez** (beklenen).

```bash
vlc /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev13_m06_kosu3/kosu3_takip_yuruyen/kosu.mp4 2>/dev/null
```

### 3. Raporlar

```bash
xdg-open /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev13_m06/kosu1_takip_yuruyen/rapor.html
```

```bash
xdg-open /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev13_m06/kosu2_kalabalik_park/rapor.html
```

### 4. Kabul testinin özeti (OK / HATA satırları)

Sonda `SONUÇ: GEÇTİ` olmalı (her koşuda 8 satır OK):

```bash
sed -n '/=== m06 kabul testi: özet ===/,$p' /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev13_m06.log
```

```bash
tail -3 /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev13_f0.log
```

```bash
tail -3 /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev13_f1.log
```

### 5. `kur.sh`'ın model satırları (indirmez, ~1 saniye)

Sonda `TAMAM person_detection_model_v0.2.pt` ve `EKSİK yolov8s.pt` (+ "Almak için" satırı) görünmeli:

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && tez/sim/kur.sh
```

### 6. 13.4: `yolov8s.pt`'yi indirmek ve kıyas koşusu (isteğe bağlı, ~22 MB + ~2.5 dakika)

İndir (internet gerekir):

```bash
mkdir -p /home/ahmet/auto-follow-modeller && curl -fL -o /home/ahmet/auto-follow-modeller/yolov8s.pt https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s.pt
```

sha256'sı ve boyutu (`kur.sh` `ÖZETSİZ yolov8s.pt: sha256 …, … bayt` yazar; bu iki değeri bana ya da ana oturuma ver,
`modeller.yaml`'a ve spec'e yazılacak):

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && tez/sim/kur.sh
```

Kıyas koşusu (önce açık sim olmamalı; `pgrep -x px4` boş dönmeli):

```bash
pgrep -x px4
```

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo kalabalik_park --ekransiz --model /home/ahmet/auto-follow-modeller/yolov8s.pt --cikti tez/sim/sonuclar/gorev13_yolov8s_kalabalik_park
```

v0.2 ile yan yana (ilk sütun v0.2'nin kabul koşusu):

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/karsilastir.py tez/sim/sonuclar/gorev13_m06/kosu2_kalabalik_park tez/sim/sonuclar/gorev13_yolov8s_kalabalik_park --html tez/sim/sonuclar/gorev13_yolov8s_kalabalik_park/karsilastirma.html
```

```bash
xdg-open /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev13_yolov8s_kalabalik_park/karsilastirma.html
```

### 7. Kabul testini kendin koştur (isteğe bağlı, ~5 dakika; önce açık sim olmamalı)

```bash
pgrep -x px4
```

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && tez/sim/araclar/m06_kabul.sh
```

Sonda `SONUÇ: GEÇTİ`; videolar `tez/sim/sonuclar/<tarih>_m06_kabul/` altında.

### 8. Kontroller

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python -m pytest tez/sim/testler -q
```

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && tez/pin/verify_pin.sh --worktree
```

Beklenen: `312 passed`; `KILIT SAGLAM (v1.17.0)`.
