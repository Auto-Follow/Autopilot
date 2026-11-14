# Görev Grubu 12 — Yapay gecikme, saat modeli, yeniden kilit beklemesi ve `karsilastir.py`

- Tarih: 15.11.2026 · dal `ozellik/m06-sim-ortami` · taban commit `29bdb0d8d3` + çalışma ağacı
- Kapsam: `tasks.md` 12.0–12.5 (12.4: kullanıcının 12.11 kararı, 5. grubun açık konusu)
- Durum: **tamam** (commit `a78245da2b`, `74d62db2c8`). Ahmet'in görsel kontrolü 15.11: "kutular geride" (bölüm 5).

## Kısaca

- `senaryo.py --gecikme-ms 200` (senaryoda `gecikme: {ek_ms: 200}`) yakalama → PX4 yoluna her `TEZ_LOS` ve
  `FOLLOW_TARGET` için **200 sim ms** ekler; `gecikme.titresim_ms` düzgün dağılımlı, sabit tohumlu bir titreşim
  (`ek_ms` ± `titresim_ms`), `gecikme.saat_ofset_ms` / `saat_kayma_ppm` `TEZ_LOS`'un `time_usec`'ini damgalayan saati
  kaydırır. Varsayılanlar 0: varsayılan koşu bugünkü gibi davranır (0 ms koşusu 17. grubun üç koşusunun aralığında).
- **Ölçülen ek gecikme ayarlananla tutarlı:** aynı kodla `takip_yuruyen` 0 ms → 200 ms: uçtan uca `uctan_uca_ms_ort`
  **138.75 → 340.44 sim ms (Δ +201.69)**, p50 140.08 → 340.09 (Δ +200.01), PX4'ün varış damgasıyla 136.34 → 338.60
  (Δ +202.25), `FOLLOW_TARGET` 135.82 → 341.41; hattaki süre `ek_gecikme_ms` ort. **200.30** (kayıt penceresinde en
  çok 203.63; bütün koşuda en az 200.00, p50 200.10, p95 200.94, en çok 205.71). Doğal titreşim (titreşim ayarı 0):
  uçtan uca std 13.5 → 17.3 ms, p5–p95 bandı 43.0 → 55.8 ms.
- **Kişi 200 ms'de de sonuna kadar izlendi** (tarama kapısı: son `FOLLOW_TARGET` koşu sonundan 0.83 s sonra; en az
  yatay mesafe 6.93 m ≥ 3 m); mod %100 "Follow Target", `TEZ_LOS` ULog / gönderilen %100. Bulma oranı %62.9 / %61.4,
  kilit kaybı (pencere) 1 / 3 (17. grubun üç koşusunda 3–5), RTF 0.89 / 0.98.
- **Model kutusu videoda belirgin geride:** PX4'teki son model sonucunun yaşı (yürüyüşte, kutulu anlarda) p50
  **196 → 396 ms**, kutu merkezinin hakem kutusundan uzaklığı ort. **65 → 126 px** (2304×1296 görüntüde). Üç kare
  (0 ms üstte, 200 ms altta) bölüm 5'te; Ahmet'in görsel kontrolü 15.11: "kutular geride".
- `takip.yeniden_kilit_bekleme_s` / `--yeniden-kilit-bekleme-s`: kilit düştükten sonra operatörün tepki süresi
  (sim s, varsayılan 0 = bugünkü davranış). `kalabalik_park` 1.5 s ile: kilit 69.50 s'de düştü,
  69.57–70.95 s'nin 19 karesi `tepki_bekleniyor`, 71.02 s'den sonra olağan nedenler (bekleme tam 1.5 s).
- `karsilastir.py`: koşu ve `toplu.py` klasörlerini (ortalama, en az–en çok) tek tabloda yan yana koyar (ayarlar,
  ölçütler, ilk sütuna göre Δ); terminal + `--html`.
- 309 birim testi geçti (298 + 11), ruff temiz, **KILIT SAGLAM**.

## 1. Ne yapıldı

| Alt görev | Dosya | Sonuç |
|---|---|---|
| 12.1 | `tez/sim/testler/test_gecikme.py` (+4), `test_karsilastir.py` (yeni, 1), `test_takip.py` (+3), `test_hedef.py` (güncellendi, +3 durum) | Bölüm 4 |
| 12.2 | `tez/sim/araclar/gecikme.py`, `takip.py`, `px4_baglanti.py`, `hedef.py`, `senaryo.py` | `gecikme.LinkDelay` (`ek_ms` ± `titresim_ms`, düzgün, sabit tohum), `gecikme.ClockModel` (`time_usec`), `DelayLine` herhangi bir saatte (sim saati) bekler; `Tracker(delay=, stamp=)`; `LosSender(stamp=)`; `hedef.unwired` boş (2. grubun `gecikme.*` / `--gecikme-ms` ara hatası kalktı); `senaryo.py` günlüğe gecikme satırı yazar |
| 12.3 | `tez/sim/araclar/karsilastir.py` (yeni), `tez/sim/ruff.toml` | Tek koşu ve `toplu.py` klasörleri; terminal tablosu, `--hepsi`, `--html` |
| 12.4 | `takip.py`, `hedef.py`, `senaryo.py`, `rapor.py` | `takip.yeniden_kilit_bekleme_s` / `--yeniden-kilit-bekleme-s`; `Selection(relock_wait_s=)`, `kilitsiz_neden = tepki_bekleniyor`; `ayarlar.takip`, raporun "Ayarlar" tablosu |
| 12.5 | koşular | Bölüm 5 |
| belgeler | `spec.md` (4., 5., 6., 8. madde, alan tablosu, dosya planı, test planı, açık konular), `tasks.md`, `EKIP_ICIN_OZET.md` (bir paragraf), `tez/sim/README.md` (kullanım satırları), `implementation/kabul-kosulari.md`, bu dosya | |

Rapor (`rapor.py`): ölçüt tablosuna `ek_gecikme_ms_ort` / `ek_gecikme_ms_maks` satırları (ozet.json'da 7. gruptan beri
vardı, raporda gösterilmiyordu), "Ayarlar"da yeniden kilit beklemesi ve gecikme biriminin (sim ms) yazılması.

## 2. Kararlar ve gerekçeler

1. **Gecikme sim saatinde sayılır.** Hat `takip.Tracker`'da sim saatiyle (`SimClock.to_sim(monotonic)`) kurulur:
   mesaj hazır olduktan `ek_ms` **sim** ms sonra çıkar. Gecikme gerçek sistemin (Pi, Hailo, seri hat) gecikmesini
   temsil eder; dron ve lockstep'teki PX4 sim zamanında yaşar. Duvar saatinde 200 ms, PX4'e RTF kadar kısalmış
   (RTF ≈ 0.85–0.95 → 170–190 sim ms) ulaşırdı. Hattın iş parçacığı kalan süre kadar **duvar** saniyesi uyur ve yeniden
   bakar; sim saati duvar saatinden yavaş akarken (RTF < 1) hiç aşmaz (testli, RTF 0.5). Sonuç: `ek_gecikme_ms`
   (`algilama.csv`, `tez_los.csv`) 12. gruptan beri sim ms'dir (`serbest_sim − hazir_sim`; öncesinde duvar ms, 0
   gecikmede ikisi de ≈ 0.02 ms). Modelin kendi süresi (`model_ms`) duvar saatinde kalır (spec: RTF < 1'de model sim
   saatine göre olduğundan hızlı görünür; bu bilinen fark değişmedi).
2. **Gecikmesiz yol aynen kaldı.** Gecikme 0 iken ve hatta bekleyen yokken mesaj, saat ne derse desin çağıranın iş
   parçacığında hemen çıkar (`due > ready` koşulu; sim saati çevrildiği için `ready`'nin bir tık gerisini okuyabilir) ve
   çıkış damgası hazır olma anından önce olamaz. Bu yüzden varsayılan koşuda yola iş parçacığı geçişi eklenmedi;
   0 ms koşusunda `ek_gecikme_ms` ort. 0.02 ms, en çok 0.09 ms (17. grubun koşusunda 0.02 / 0.05).
3. **Titreşim:** her mesajın gecikmesi `ek_ms + U(−titresim_ms, +titresim_ms)`, 0'ın altına inmez (Linux netem'in
   "delay ZAMAN TİTREŞİM" kuralı; ortalama `ek_ms`). Sıra korunur: kısa gecikme çeken bir mesaj öndekini geçmez (gerçek
   bir seri hattaki gibi; o mesajın ölçülen `ek_gecikme_ms`'i çektiğinden büyük olur). Üreteç **sabit tohumla**
   (`gecikme.JITTER_SEED = 0`, `random.Random`): aynı senaryo aynı gecikmeleri aynı sırayla çeker. Senaryoya tohum alanı
   eklenmedi (spec'in alan tablosunda yok, tasks.md istemiyor); farklı tekrarlar için gerekirse `gecikme.tohum` önerilir
   (bölüm 8).
4. **Saat modeli:** `time_usec = t + saat_ofset_ms + saat_kayma_ppm × t`. "Geçen süre" karenin kendi sim zamanıdır:
   sim saati simle başlar ve PX4 lockstep'te onunla açılır (±4 ms), yani açılışta doğru olup o andan beri kayan bir
   saat. Alan işaretsiz (`uint64`) olduğu için 0'ın altına düşen damga 0 gider. Gönderilen damga ile `tez_los.csv` →
   `time_usec` aynı işlevden gelir (`px4_baglanti.LosSender(stamp=gecikme.ClockModel.time_usec)`); ofset ve kayma 0
   iken bit bit eskisiyle aynı (`round(t × 1e6)`, testli).
5. **Saat modeli yalnız `TEZ_LOS`'ta.** tasks.md 12.2 ve spec'in formülü `time_usec`'i (DEBUG_VECT) anar;
   `FOLLOW_TARGET.timestamp` yakalama anı olarak kaldı. PX4 v1.17.0 ikisini de kullanmaz (varış zamanını kullanır;
   spec "Varsayımlar" 2), yani saat ayarlarının PX4'ün davranışına etkisi yoktur; m05 (ICD) zaman damgalı bir yol
   seçerse anlam kazanır. Gecikme ise ikisine de uygulanır: `FOLLOW_TARGET` karesinin `TEZ_LOS`'unun arkasından aynı
   hattan gider (6. grup).
6. **`--gecikme-ms` yalnız `ek_ms`'i ezer** (spec 8. madde); titreşim ve saat ayarları senaryonun `gecikme` bloğundan.
   Yeni bayrak eklenmedi.
7. **Yeniden kilit beklemesi** (`takip.yeniden_kilit_bekleme_s`, sim s, ≥ 0, varsayılan 0): kilit düştükten sonra
   karelerin yakalama zamanı, kilidin düştüğü karenin zamanından bu kadar ileri olmadan hakemle yeniden kilitlenilmez;
   bu karelerde `secim = kilitsiz`, `kilitsiz_neden = tepki_bekleniyor` (hakem karesi olsun olmasın: operatör henüz
   bakmadı). İlk kilit beklemez (operatör hedefi baştan seçer). Süre karelerin sim zamanıyla ölçülür, böylece RTF'ten
   bağımsızdır. 0 s'de seçim, kare zamanı verilmeyen eski seçimle seçim seçim aynıdır (testli).
8. **`karsilastir.py`'nin sütunu:** tek koşu klasörü (`ozet.json`) ya da `toplu.py` klasörü (`toplu.json`; sütun
   `toplu.aggregate`'in ortalaması, parantezde en az–en çok; koşular arasında farklı bir ayar "farklı: a / b"). Ayarlar
   `ayarlar`'ın noktalı adlarıyla; varsayılan görünümde farklı olanlar ve her zaman takip / gecikme / eğim / model
   sha256 (sha terminalde 40 karakterde kesilir, HTML'de tam). Koşunun kendi ölçümü olan `model_bilgisi.isinma_ms`,
   `pid` ve koşuya özel `kamera.gazebo_modeli` yolu ayar sayılmaz (iki aynı ayarlı koşuda da farklıdır). Ölçütler:
   önce gecikmeler (`uctan_uca_ms_*`, `ek_gecikme_ms_*`, `hazir_ms_ort`, PX4 varış damgalı uçtan uca, `FOLLOW_TARGET`
   uçtan uca), sonra `toplu.MAIN_KEYS`; `--hepsi` bütün sayısal ölçütler ve ayarlar. Her sütunun ilk sütundan farkı
   (Δ; oranlarda yüzde puan). Uydurma alan adı yok: değerler `ozet.json`'dakidir, etiketler raporun
   (`rapor.METRIC_GROUPS`). `--html` `toplu.html` düzeninde, her koşunun `rapor.html` / `kosu.mp4` bağlantılarıyla.
9. **Faz A'da ara hata kalmadı:** `hedef.unwired` boş döner; `check_wired` / `not_in_effect` düzeni Faz B'nin
   ekleyeceği alanlar için yerinde kaldı.

## 3. Testler

Hepsi simsiz, donanımsız; `ultralytics` / `torch` gerekmez. Yeni ve değişen testlerin hepsi 12. grup öncesi kodda
(HEAD `29bdb0d8d3`'ün `tez/sim`'i scratchpad'e açılıp) kırmızı: `test_gecikme.py`'nin 4 yenisi, `test_takip.py`'nin 3
yenisi, `test_hedef.py`'nin değişen 6 durumu düştü, `test_karsilastir.py` modül olmadığı için toplanamadı.

`tez/sim/testler/test_gecikme.py` (+4; 5. gruptaki sıra testi aynen kaldı):

1. `test_jitter_is_uniform_round_the_extra_delay_seeded_and_never_negative`: `LinkDelay(200, 30)`'un 4000 çekilişi
   170–230 ms içinde, ortalama 200 ± 1, üç dilime eşit (± 0.04, ortada toplanmıyor); aynı tohumla aynı dizi, başka
   tohumla başka; titreşimsiz hep 200; `LinkDelay(10, 30)` 0'ın altına inmez (0'da kesilir); negatif / NaN reddi.
2. `test_delay_counts_in_the_lines_clock_even_when_it_runs_slower_than_the_wall`: duvar saatinin yarı hızında akan bir
   saatle (RTF 0.5) 100 ms'lik mesaj o saatte 100–110 ms sonra çıkar (duvar saatinde ≥ 200 ms; aşma yok), arkasındaki
   20 ms'lik mesaj onu geçmez; gecikmesiz mesaj, saat hazır olma anının bir tık gerisini okusa da hemen ve çağıranın
   iş parçacığında çıkar, damgası hazır olma anından önce olmaz.
3. `test_clock_model_stamps_time_usec_with_offset_and_drift`: ofset / kayma 0 iken beş zamanda `round(t × 1e6)` =
   `algilama.time_key(t)`; 12.5 ms / 200 ppm'de 61 s → 61 024 700 µs; −5 ms / −50 ppm'de 100 s → 99 990 000 µs;
   −1500 ms'de 1 s → 0 (işaretsiz alan); sonsuz ofset reddi.
4. `test_tracker_delays_every_tez_los_in_sim_time_and_sends_the_clock_models_time_usec`: gerçek zamanda, RTF 0.5'lik
   bir `SimClock` ile `takip.Tracker(delay=LinkDelay(80), stamp=ClockModel(12.5, 200))`: üç karenin `TEZ_LOS`'u PX4
   bağlantısına (taklit) giden `time_usec` = saat modeli = `tez_los.csv` → `time_usec`; `ek_gecikme_ms` 80–90 sim ms
   (`algilama.csv` ve `tez_los.csv`'de aynı), uçtan uca ort. 200 ± 10 sim ms (sonuç kareden 120 ms sonra + 80).

`tez/sim/testler/test_takip.py` (+3):

5. `test_relock_waits_the_reaction_time_after_a_lost_lock`: 1.5 s beklemeyle kilit 61.0 s'de düşer; 61.1–62.4 s'nin
   14 karesi `kilitsiz` / `tepki_bekleniyor` (hakem kutusu tam üstündeyken bile), 62.5 s'de yeniden kilit (kilit 2,
   doğru kutu); beklemede hakem yoksa da neden `tepki_bekleniyor`, bekleme bitince `hakem_yok`; negatif bekleme reddi.
6. `test_relock_without_a_wait_is_the_behaviour_of_before`: 0 s'de seçim, kare zamanı verilmeyen (5. grup) seçimle
   aynı dizide seçim seçim aynı; kayıptan sonraki ilk kare yeniden kilit.
7. `test_the_tracker_writes_the_reaction_time_into_algilama_csv`: `Tracker(relock_wait_s=1.5)`: `algilama.csv`'de
   14 `tepki_bekleniyor` satırı (61.1–62.4 s), kilit olayları ilk kilit 60.0, kayıp 61.0, yeniden kilit 62.5 s.

`tez/sim/testler/test_karsilastir.py` (yeni, 1):

8. `test_two_runs_and_a_toplu_folder_side_by_side`: elle yazılmış iki koşu ve iki koşulu bir `toplu.py` klasörü:
   sütun başlıkları, `uctan_uca_ms_ort` 120.00 / 321.50 / 135.00 (130.00–140.00) ve Δ +201.50 / +15.00, oranın yüzde
   puan farkı (−7.0 puan), toplu sütunun sonucu "GEÇTİ 1/2 (GEÇTİ, KALDI)", `gecikme.ek_ms` satırı, koşular arasında
   farklı ayar ("farklı: 0 / 1.5"); değeri olmayan ölçüt, koşunun ölçümü olan `isinma_ms` ve koşuya özel
   `gazebo_modeli` satır olmaz; aynı olan PX4 parametresi yalnız `--hepsi`'de; `--html` raporun etiketini, Δ'yı,
   `rapor.html` bağlantısını ve toplu koşunun sonucunu yazar; `ozet.json`'suz klasör çıkış kodu 2.

`tez/sim/testler/test_hedef.py` (güncellendi): tam senaryoda `yeniden_kilit_bekleme_s: 1.5` okunur; yeni üç hata
durumu (negatif, metin, sonsuz; alan adıyla); `--yeniden-kilit-bekleme-s 1.5` → `ayarlar.takip`; "sonraki grupların
ayarları" testi: `--gecikme-ms 200` artık durdurmaz, bütün `gecikme` bloğu ve bekleme bağlı, `hedef.unwired` boş.

| Kontrol | Sonuç |
|---|---|
| `pytest tez/sim/testler/test_gecikme.py -q` | **5 passed** |
| `pytest tez/sim/testler -q` | **309 passed** (önce 298), 1 uyarı (sistemdeki protobuf, eskiden beri) |
| `ruff format` + `ruff check` (`tez/sim/ruff.toml`) | 62 dosya (1'i biçimlendirildi); All checks passed; `karsilastir` `known-first-party`'de |
| `tez/pin/verify_pin.sh --worktree` | **KILIT SAGLAM (v1.17.0)**; değişiklik yalnız `tez/sim/` ve spec klasöründe |

## 4. Koşular (12.5)

Aynı kod (taban `29bdb0d8d3` + bu grubun çalışma ağacı), aynı anda tek sim, her koşudan önce `pgrep -x px4` ve
`pgrep -f "^gz sim"` boş. Model v0.2 (sha256 `c5f6838b…`), CPU 4 çekirdek, `imgsz` 640; kamera 35°, `takip_yuruyen`
9 m / 12.9 m, `FLW_TGT_RS 0.3`.

| Koşu | Komut | Sonuç | Süre |
|---|---|---|---|
| `tez/sim/sonuclar/gorev12_gecikme0` | `senaryo.py --senaryo takip_yuruyen --ekransiz --cikti …` | GEÇTİ | 2 dk 22 s |
| `tez/sim/sonuclar/gorev12_gecikme200` | aynı + `--gecikme-ms 200` | GEÇTİ | 2 dk 17 s |
| `tez/sim/sonuclar/gorev12_kilit_bekleme1.5` | `senaryo.py --senaryo kalabalik_park --ekransiz --yeniden-kilit-bekleme-s 1.5 --cikti …` | GEÇTİ | 2 dk 38 s |

### 4.1 Karşılaştırma (`karsilastir.py`)

```bash
$P $S/karsilastir.py tez/sim/sonuclar/gorev12_gecikme0 tez/sim/sonuclar/gorev12_gecikme200 \
    tez/sim/sonuclar/gorev17_varsayilan_takip_yuruyen_x3 --html tez/sim/sonuclar/gorev12_gecikme200/karsilastirma.html
```

Üçüncü sütun 17. grubun aynı varsayılanla (35° · 9 / 12.9) üç koşusu (`toplu.py` klasörü; ortalama, parantezde en
az–en çok; o koşularda `takip.yeniden_kilit_bekleme_s` alanı henüz yoktu: "–"). Ayarlarda tek fark `gecikme.ek_ms`
(0 / 200 / 0). Tablodan (kayıt penceresi; Δ = sütun − 0 ms):

| Ölçüt | 0 ms | 200 ms | 17. grup ×3 | Δ 200 − 0 |
|---|---|---|---|---|
| `uctan_uca_ms_ort` [sim ms] | 138.75 | 340.44 | 137.00 (133.85–140.51) | **+201.69** |
| `uctan_uca_ms_p50` / `_p95` / `_maks` | 140.08 / 157.29 / 175.48 | 340.09 / 367.64 / 384.95 | 138.68 / 152.72 / 163.50 | +200.01 / +210.35 / +209.48 |
| `ek_gecikme_ms_ort` / `_maks` [sim ms] | 0.02 / 0.09 | 200.30 / 203.63 | 0.02 / 0.07 | +200.28 / +203.54 |
| `hazir_ms_ort` (yakalama → hatta giriş) | 138.70 | 139.94 | 136.95 | +1.24 |
| `uctan_uca_px4_ms_ort` (PX4'ün varış damgası) | 136.34 | 338.60 | 135.28 | +202.25 |
| `follow_target_uctan_uca_ms_ort` | 135.82 | 341.41 | 135.21 | +205.59 |
| `yatay_mesafe_ort_m` / `en_az_yatay_mesafe_m` | 12.50 / 7.91 | 12.42 / 6.93 | 12.08 / 6.63 (5.68–7.12) | −0.07 / −0.98 |
| `hedef_kadrajda_orani` | %93.2 | %93.4 | %95.0 | +0.2 puan |
| `en_uzun_kayip_s` | 0.36 | 1.02 | 0.54 (0.00–0.86) | +0.66 |
| `algilama_orani` / `secim_dogru_orani` | %62.9 / %62.9 | %61.4 / %61.4 | %62.2 / %60.1 | −1.5 puan |
| `kilit_kaybi_sayisi` / `yeniden_kilit_sayisi` | 1 / 2 | 3 / 3 | 4 / 5 (3–5 / 4–6) | +2 / +1 |
| `kose_px4_yetisme_ort_s` / `_maks_s` | 1.95 / 2.24 | 2.49 / 3.58 | 2.29 / 2.91 | +0.54 / +1.34 |
| `arkada_kalma_hatasi_ort_deg` | 78.2 | 73.6 | 76.5 | −4.6 |
| `px4_kestirim_hatasi_ort_m` | 0.92 | 1.05 | 0.84 | +0.13 |
| `islenen_kare_hizi_hz` / `model_ms_ort` | 11.35 / 97.4 | 10.16 / 98.5 | 11.43 / 90.2 | −1.19 / +1.1 |
| `rtf_ort` (en yavaş 5 s) | 0.89 (0.87) | 0.98 (0.98) | 0.95 (0.92–1.00) | +0.09 |
| `mod_korunma_orani`, `tez_los_px4_orani` | %100, %100 | %100, %100 | %100 | 0 |

`tez_los.csv`'den (bütün koşu, gönderilen mesajlar): uçtan uca 0 ms'de ort. 136.2, std 13.5, p5–p95 114.4–157.4
(en az 97.6, en çok 189.8); 200 ms'de ort. 337.3, std 17.3, p5–p95 310.9–366.7 (en az 293.4, en çok 425.4).
Hattaki süre 200 ms'de en az 200.00, p50 200.10, p95 200.94, en çok 205.71 sim ms: hat çekilen gecikmeyi aşmıyor,
uyanma payı p95'te < 1 ms. Gecikmenin kendisi dışında ölçütler 17. grubun üç koşusunun dağılımı içinde ya da hemen
yanında; 200 ms'de köşede PX4'ün yeni yöne yetişmesi 0.5–1.3 s gecikti ve kişi bir kez 1.02 s kadrajdan çıktı (tek
koşu, dağılım için 3 koşu gerekir; bölüm 8). İşlenen kare hızının (sim s başına) düşmesi RTF'ten: duvar saniyesi
başına ikisi de ≈ 10 kare (11.35 × 0.89 = 10.1, 10.16 × 0.98 = 9.96).

**"Kişi sonuna kadar izlendi" kapısı** (Görev Grubu 17'nin kapısı, `tarama.run_numbers`: son giden `FOLLOW_TARGET`
ile koşu sonu arası ≤ 3 s; ve en az yatay mesafe ≥ 3 m): 0 ms son `FOLLOW_TARGET` 89.93 s (koşu sonu 89.43 s), en az
7.91 m → geçti; **200 ms son `FOLLOW_TARGET` 90.26 s, en az 6.93 m → geçti.** Tek koşu: 200 ms'nin kapıyı "3/3"
geçtiği söylenemez.

### 4.2 Yeniden kilit beklemesi (`kalabalik_park`, 1.5 s)

`ozet.json` → `ayarlar.takip.yeniden_kilit_bekleme_s` 1.5; raporun "Ayarlar" tablosunda "1.5 sim s"; günlükte
"Yeniden kilit beklemesi: kilit düştükten 1.5 sim s sonra". Bütün koşuda 2 kilit, 1 kayıp (hedef çamın arkasına
girerken):

| t [s] | `secim` | `kilitsiz_neden` |
|---|---|---|
| 69.500 | `kilit_kaybi` (10. kaçırma) | |
| 69.568 … 70.952 (19 işlenen kare) | `kilitsiz` | **`tepki_bekleniyor`** |
| 71.020 | `kilitsiz` | `hedef_gorunmuyor` (hedef çamın arkasında, 0 piksel) |
| 71.116 … | `kilitsiz` | `kutu_eslesmedi` |
| 77.85 | `yeniden_kilit` (IoU eşiği aşıldı) | |

Bekleme 69.500 + 1.5 = 71.000 s'de bitti: son `tepki_bekleniyor` karesi 70.952, sonraki kare (71.020) olağan
nedene döndü. Bu koşuda yeniden kilidi bekleme değil örtülme geciktirdi (hedef ≈ 70–76 s çamın arkasında): 17.
grubun aynı senaryodaki beklemesiz koşularında aynı kayıptan sonra yeniden kilit 77.92 / 78.41 / 78.41 s. Yani
1.5 s'lik bekleme bu senaryonun tek kaybında sonucu değiştirmedi; kısa kayıpların (17. grubun 1. koşusunda kayıptan
0.07–0.13 s sonra yeniden kilit) yerini alacağı koşularda fark görülür. Ölçütler: seçili kare %60, seçim doğru %48,
yanlış kişi %14, bulma %59, hedef kadrajda %98, RTF 0.78 (17. grubun üç koşusu: %47–53, %12–19, RTF 0.85–0.86).
Videoda (`gorev12_kare_70.4s_tepki_bekleniyor.jpg`) üstte "kilit yok (tepki_bekleniyor)", ortada "HEDEF YOK", altta
"kilit yok (hakemle yeniden kilit bekleniyor) · PX4'e 'hedef yok' gidiyor".

### 4.3 Videolar (`ffprobe`)

| Video | codec / piksel / boyut | Kare | Süre | Kayıt (hakem) |
|---|---|---|---|---|
| `gorev12_gecikme0/kosu.mp4` | h264 / yuv420p / 2000×720 | 958 | 63.87 s | 63.89 s |
| `gorev12_gecikme200/kosu.mp4` | h264 / yuv420p / 2000×720 | 944 | 62.93 s | 62.93 s |
| `gorev12_kilit_bekleme1.5/kosu.mp4` | h264 / yuv420p / 2000×720 | 957 | 63.80 s | – |

Üçünde de "kamera karesi olmayan an 0", kareler silindi.

### 4.4 200 ms × 3 (kullanıcı isteği 15.11)

`toplu.py --senaryo takip_yuruyen --tekrar 3 --cikti tez/sim/sonuclar/gorev12_gecikme200_x3 -- --gecikme-ms 200`
(commit `a78245da2b`; 3/3 GEÇTİ, ilk denemede). Karşılaştırma 17. grubun aynı ayarlı 0 ms × 3 koşusuyla
(`gorev17_varsayilan_takip_yuruyen_x3`): `karsilastir.py ... --html tez/sim/sonuclar/gorev12_gecikme200_x3/karsilastirma.html`.
Değerler ort. (en az–en çok).

| Ölçüt | 0 ms × 3 (17. grup) | 200 ms × 3 | Δ |
|---|---|---|---|
| Uçtan uca gecikme ort. [sim ms] | 137.00 (133.85–140.51) | 332.68 (331.06–333.77) | +195.68 |
| Hattaki süre `ek_gecikme_ms` ort. [sim ms] | 0.02 | 200.37 (200.17–200.55) | +200.35 |
| Kişi sonuna kadar izlendi (son `FOLLOW_TARGET` koşu sonundan en çok 3 s önce) | 3/3 | **3/3** | |
| En az yatay mesafe [m] | 6.63 (5.68–7.12) | 6.58 (5.91–7.04) | −0.05 |
| Yatay mesafe ort. [m] | 12.08 (11.58–12.35) | 12.11 (12.01–12.19) | +0.03 |
| Kaydın 6 m altı | %0.6 | %0.2 | |
| En uzun kayıp [s] | 0.54 (0.00–0.86) | 0.89 (0.53–1.22) | +0.35 |
| Köşede PX4'ün yetişmesi ort. / en çok [s] | 2.29 / 2.91 | 2.59 / 3.72 | +0.29 / +0.81 |
| Bulma oranı | %62.2 | %60.0 | −2.2 puan |
| Kilit kaybı | 4.00 (3–5) | 5.00 (3–7) | +1.00 |
| Konum hatası ort. [m] | 0.36 | 0.39 | +0.03 |
| RTF | 0.95 | 0.97 | |

Uçtan uca fark +195.7 ms (hattaki +200.4 ms'den ≈ 5 ms az: 200 ms koşularında model hazır olma süresi `hazir_ms_ort`
132 ms, 17. grupta 137 ms; RTF farkı). Sonuç: **200 ms'lik ek gecikmede stok Follow Me bu senaryoda kişiyi 3/3 sonuna
kadar izliyor, mesafe değişmiyor**; değişen köşede yetişme (en çok +0.8 s), en uzun kayıp (+0.35 s) ve kilit kaybı
(+1). Etkiler 3 koşunun yayılımıyla aynı büyüklükte, yani 200 ms bu senaryoda takibi bozmuyor, köşelerde biraz
geciktiriyor. Ayrıntı: `tez/sim/sonuclar/gorev12_gecikme200_x3/toplu.html`.

## 5. Görsel kontrol: model kutusunun gecikmesi (Ahmet: "kutular geride", 15.11)

Videoda kırmızı kutu "PX4'teki son model sonucu"dur (gönderim anına göre; 8. grup); 200 ms'de PX4'e 200 ms geç
ulaştığı için hakemin o anki mavi kutusunun daha gerisinde kalmalı. Ölçüyle (yürüyüş, 60 s'den sonra, PX4'teki son
sonucun kutulu olduğu ve hedefin göründüğü her hakem karesi; `algilama.csv` + `dogru_cevap.csv`):

| | 0 ms (572 an) | 200 ms (549 an) |
|---|---|---|
| PX4'teki son sonucun karesinin yaşı p50 / p95 | 196 / 232 ms | 396 / 460 ms |
| Kutu merkezi − hakem kutusu merkezi, ort. (yatay / dikey) | 65 px (39 / 43) | 126 px (69 / 87) |
| Yatay fark p95 | 115 px | 200 px |

(Piksel 2304×1296 kamera görüntüsünde; videonun kamera paneli 1280×720, × 0.556.) Hakem kutusu yürüyüşte p50 ≈ 177 px
boyunda, 80 px eninde: ortalama fark 0 ms'de boyun ≈ %37'si, 200 ms'de ≈ %71'i; yatay fark 200 ms'de ortalama kutunun
eni kadar (69 / 80 px).

Çıkarılan kareler (aynı sim anı, **üstte 0 ms, altta 200 ms**, kamera + kuşbakışı):

| Dosya | Ne görünüyor |
|---|---|
| `tez/sim/sonuclar/gorev12_gecikme200/gorev12_kare_70.8s_ust_0ms_alt_200ms.jpg` | Dron dönerken: 0 ms'de kırmızı kutu kişinin üstünde (164 ms önceki kare), 200 ms'de kişinin yarım boyu kadar yukarıda (332 ms önceki kare) |
| `…/gorev12_kare_78.6s_ust_0ms_alt_200ms.jpg` | Köşeden sonra kişi kameraya doğru yürürken: 0 ms'de kutu mavi kutunun hemen sol üstünde (196 ms), 200 ms'de bir kutu boyundan fazla yukarıda ve solda, kişiyle örtüşmüyor (428 ms) |
| `…/gorev12_kare_88.4s_ust_0ms_alt_200ms.jpg` | Dron sonda dönerken: 0 ms'de kutu kişinin hemen solunda (164 ms), 200 ms'de bir kutu genişliğinden fazla solda (360 ms) |
| `tez/sim/sonuclar/gorev12_kilit_bekleme1.5/gorev12_kare_70.4s_tepki_bekleniyor.jpg` | Bekleme sırasında durum satırları (4.2) |

Benim yorumum: 200 ms'de kutu her üç anda da 0 ms'ye göre belirgin geride; geride kalma, kişinin değil çoğu zaman
**dronun** hareketinden (dönüş, hızlanma) görüntünün kaymasından geliyor (70.8 s ve 88.4 s'de kişi duruyor). Ahmet'in
kontrolü (15.11, kareler ve videolar): "kutular geride"; `tasks.md` 12.0 / 12.5 kapandı.

## 6. Karşılaşılan sorunlar

- **`ek_gecikme_ms`'in birimi değişti** (duvar ms → sim ms; karar 1). Eski koşuların sütunu duvar ms'dir; 0 gecikmede
  ikisi de ≈ 0.02 ms olduğu için karşılaştırmayı etkilemez. Spec'e ve sütun açıklamalarına yazıldı.
- **Çevrilmiş saat geri okuyabilir:** `SimClock.to_sim(şimdi)` en yeni saat mesajından ileri tahmin yapar; yeni mesaj
  gelince tahmin birkaç ms geri dönebilir. Gecikmesiz yol bu yüzden saate bakmadan hemen çıkar ve çıkış damgası hazır
  olma anına kırpılır (karar 2, testli); yoksa varsayılan koşuda ara sıra fazladan bir iş parçacığı geçişi olurdu.
- Bir ölçüm betiğinde `tee` ile `head` aynı boruya bağlanınca tablo dosyası yarıda kesildi (`mod_korunma_orani` yok
  sanıldı); araçta hata yok, tablo yeniden yazıldı.
- Hata ya da tekrar edilen koşu yok; üç koşu ilk denemede GEÇTİ.

## 7. Kalan sim-gerçek farkları (gecikme için)

- Yapay gecikme sabit ya da düzgün dağılımlı; gerçek Pi → Pixhawk gecikmesinin dağılımı (Hailo süresi, seri hat,
  kuyruk) ölçülmedi (m23 bench ölçümü). Kuyruk biriktirmesi (bant genişliği sınırı) yok: mesajlar yalnız sırayla
  bekler.
- Saat modeli PX4'ün davranışını değiştirmez (PX4 v1.17.0 `time_usec` / `timestamp`'i okumuyor); m05 zaman damgalı bir
  yol seçerse anlam kazanır.
- Modelin kendi süresi duvar saatinde kalır (RTF < 1'de sim saatine göre olduğundan hızlı görünür; spec 4).

## 8. Açık konular ve öneriler

- ~~**Görsel kontrol (Ahmet)**~~ → kapandı 15.11: "kutular geride".
- ~~**Tek koşu**~~ → kapandı, 3 koşu yapıldı (kullanıcı isteği 15.11, bölüm 4.4).
- **Öneri (yapılmadı):** `gecikme.tohum` alanı (aynı titreşim dizisi yerine tekrar başına farklı tohum); şimdilik sabit
  tohum `gecikme.JITTER_SEED = 0`.
- **Öneri (yapılmadı):** saat modelini `FOLLOW_TARGET.timestamp`'e de uygulamak (Pi'nin saati iki mesajı da damgalar);
  tasks.md yalnız `TEZ_LOS`'u istiyor, PX4 ikisini de kullanmıyor.
- 1.5 s beklemenin etkisini görmek için kısa kayıplı bir senaryo ya da daha çok koşu gerekir (bu `kalabalik_park`
  koşusunun tek kaybını örtülme belirledi). Varsayılan 0 s kaldı (kullanıcı kararı 12.11).

## 9. Dosyalar (commit'e girecekler)

- `tez/sim/araclar/gecikme.py`
- `tez/sim/araclar/karsilastir.py` (yeni)
- `tez/sim/araclar/takip.py`
- `tez/sim/araclar/px4_baglanti.py`
- `tez/sim/araclar/hedef.py`
- `tez/sim/araclar/senaryo.py`
- `tez/sim/araclar/rapor.py`
- `tez/sim/ruff.toml`
- `tez/sim/testler/test_gecikme.py`
- `tez/sim/testler/test_karsilastir.py` (yeni)
- `tez/sim/testler/test_takip.py`
- `tez/sim/testler/test_hedef.py`
- `tez/sim/README.md`
- `agent-os/specs/2026-11-10-m06-sim-ortami/spec.md`
- `agent-os/specs/2026-11-10-m06-sim-ortami/tasks.md`
- `agent-os/specs/2026-11-10-m06-sim-ortami/EKIP_ICIN_OZET.md`
- `agent-os/specs/2026-11-10-m06-sim-ortami/implementation/gorev-grubu-12.md` (yeni, bu dosya)
- `agent-os/specs/2026-11-10-m06-sim-ortami/implementation/kabul-kosulari.md`

Repo dışı / git dışı: koşu klasörleri `tez/sim/sonuclar/gorev12_*` (videolar, kareler, `karsilastirma.html`),
çözümleme betikleri scratchpad'de. PX4 dosyası, ROMFS, submodule değişmedi; `VERSIONS.md` değişmedi (yeni paket yok).

## Kendin dene

**Başlamadan:** Terminal açmak için **Ctrl+Alt+T**. Aşağıdaki gri kutulardaki satırları **tek tek** kopyala, terminale
**Ctrl+Shift+V** ile yapıştır ve **Enter**'a bas. Her satır tek başına çalışır. Bir komutu yarıda kesmek için
**Ctrl+C**.

### 1. Hazır kareler (asıl görsel kontrol, 1 dakika)

Her resimde üstte 0 ms, altta 200 ms koşusu, aynı sim anı. Kırmızı kutu PX4'teki son model sonucu, mavi kutu hakem
(kişinin o anki doğru yeri). Altta kırmızı kutu mavi kutunun belirgin biçimde gerisinde olmalı; üst satırdaki "PX4'teki
son model sonucu: … ms önceki kare" altta ≈ 200 ms daha büyük.

```bash
xdg-open /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev12_gecikme200/gorev12_kare_78.6s_ust_0ms_alt_200ms.jpg
```

```bash
xdg-open /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev12_gecikme200/gorev12_kare_70.8s_ust_0ms_alt_200ms.jpg
```

```bash
xdg-open /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev12_gecikme200/gorev12_kare_88.4s_ust_0ms_alt_200ms.jpg
```

### 2. İki videoyu izle (~2 × 1 dakika)

Önce 0 ms, sonra 200 ms. Kişi 60. saniyeden (videoda ≈ 0:34) sonra yürür; köşeler videoda ≈ 0:47 ve 0:51. Sol üstteki
"uçtan uca" 0 ms'de ≈ 120–160 ms, 200 ms'de ≈ 320–370 ms yazar.

```bash
vlc /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev12_gecikme0/kosu.mp4 2>/dev/null
```

```bash
vlc /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev12_gecikme200/kosu.mp4 2>/dev/null
```

### 3. Karşılaştırma tablosu

Terminalde (en üstte ayarlar, sonra ölçütler; en sağdaki iki sütun ilk koşuya göre fark):

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/karsilastir.py tez/sim/sonuclar/gorev12_gecikme0 tez/sim/sonuclar/gorev12_gecikme200 tez/sim/sonuclar/gorev17_varsayilan_takip_yuruyen_x3 | less -S
```

(`less`'ten **q** ile çıkılır; sağa kaydırmak için sağ ok.) Aynı tablo tarayıcıda:

```bash
xdg-open /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev12_gecikme200/karsilastirma.html
```

`uctan_uca_ms_ort` satırında 138.75 → 340.44, fark +201.69 olmalı.

### 4. Yeniden kilit beklemesi

```bash
xdg-open /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev12_kilit_bekleme1.5/gorev12_kare_70.4s_tepki_bekleniyor.jpg
```

Üst satırda "kilit yok (tepki_bekleniyor)", altta "kilit yok (hakemle yeniden kilit bekleniyor)". Bekleyen kareleri
saymak (19 satır, 69.568–70.952 s beklenir):

```bash
grep -c tepki_bekleniyor /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev12_kilit_bekleme1.5/algilama.csv
```

Videonun kendisi (bekleme ≈ 0:44–0:45.5):

```bash
vlc /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev12_kilit_bekleme1.5/kosu.mp4 2>/dev/null
```

### 5. Kendin koştur (isteğe bağlı, ~2.5 dakika; önce açık sim olmamalı)

```bash
pgrep -x px4
```

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz --gecikme-ms 200 --cikti tez/sim/sonuclar/g12_kendin_dene_200
```

Günlükte "Yapay gecikme: 200 ± 0 sim ms" satırı ve sonda "SONUÇ: GEÇTİ".

### 6. Kontroller

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python -m pytest tez/sim/testler -q
```

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && tez/pin/verify_pin.sh --worktree
```

Beklenen: `309 passed`; `KILIT SAGLAM (v1.17.0)`.

