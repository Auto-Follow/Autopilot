# Görev Grubu 2 — Senaryo şeması ve komut satırı

- Tarih: 11.11.2026 · dal `ozellik/m06-sim-ortami` · taban commit `fecd763df2` (Görev grubu 1)
- Durum: **uygulandı ve test edildi**, commit'lenmedi (kullanıcı commit'i kendisi atacak).

## Ne yapıldı

| Alt görev | Dosya | Özet |
|---|---|---|
| 2.1 | `tez/sim/testler/test_hedef.py` | 7 yeni test fonksiyonu (31 test durumu): yeni blokların varsayılanları ve okunması; alan adıyla ret (19 durum); `tez_los`'ta `mod_adi` zorunluluğu; algılama kapalıyken `los: model` reddi; `takip.px4_parametreleri` / `--param` ad ve sayı kuralı (7 durum); komut satırının YAML'ı ezmesi ve `ayarlar`; ara durum kuralı + `takip_yuruyen`. Grup 1'in `test_drone_mode_is_gone_and_later_sources_are_refused` testi `test_drone_mode_is_gone` oldu (sonraki kaynakların reddi artık `hedef.load`'da değil, `check_wired`'da) |
| 2.1 | `tez/sim/testler/test_kayit.py`, `test_rapor.py` | `Scenario(...)` çağrısından `"yok"` konumsal argümanı çıktı (`tracking_source` artık `tracking.source`'u okuyan bir özellik) |
| 2.2 | `tez/sim/araclar/hedef.py` | `Tracking`, `Detection`, `Delay`, `Video`, `CommandLine` sınıfları; `takip`, `algilama`, `gecikme`, `kusurlar`, `video` bloklarının doğrulanması; `load(ad, CommandLine)`; `start_params`, `settings` (`ayarlar`), `unwired` / `not_in_effect` / `check_wired` (ara durum), `in_group` (Türkçe ek). `_number` artık `nan`/`inf`'i de reddeder |
| 2.3 | `tez/sim/araclar/senaryo.py` | `parser()` (14 yeni bayrak), `command_line()`, `settings()` (+ PX4 modu), `check_start_params()` (her başlangıç parametresi kalkıştan önce PX4'ten geri okunur), `run()` başında `check_wired`; senaryo + `--param` parametreleri `Simulation(params=...)` ile `calistir.sh`'a |
| 2.3 | `tez/sim/araclar/rapor.py` | `write(..., settings)` → `ozet.json` `ayarlar`; eski üst düzey `takip_kaynagi` alanı `ayarlar.takip.kaynak`'a taşındı |
| 2.4 | `tez/sim/senaryolar/takip_yuruyen.yaml` (yeni) | `yuruyen_insan` yolu, `takip: {kaynak: follow_me, los: model, px4_parametreleri: {FLW_TGT_DST: 8}}`, `drone.yukseklik_m: 8`; diğer bloklar varsayılanlarıyla yorumda |
| 2.5 | `hedef.py`, `senaryo.py` | Ara durum kuralı (aşağıda tablo) |
| — | `tez/sim/README.md`, `spec.md`, `tasks.md` | Yeni alanlar ve bayraklar, ara durum, `ayarlar`; spec 8. madde ve "Senaryo alanları" tablosu (son sütun: bağlandığı grup); `tasks.md` 2.x işaretlendi, 10.1/10.4'e not |

## Kararlar ve gerekçeler

1. **Komut satırı, doğrulamadan önce YAML bloklarına yerleşir** (`hedef._with_command_line`). Böylece tek bir
   doğrulama yolu var: `--conf 1.5` ile YAML'daki `conf: 1.5` aynı mesajı verir ve çapraz kurallar
   (`tez_los` → `mod_adi`, algılama kapalı → `los`) birleşmiş değerlere uygulanır. Hata mesajları YAML alan adını,
   gerektiğinde bayrağı da söyler (ör. `takip.mod_adi: ... komut satırında --mod-adi`). `--param` ve
   `--px4-baslat` senaryonun listelerinin sonuna eklenir (yükleme sırası: dosyalar → `takip.px4_parametreleri` →
   `--param`). argparse'ta `choices` kullanılmadı: geçersiz değer argparse'ın İngilizce mesajı yerine hedef.py'nin
   Türkçe, alan adlı mesajıyla reddedilir.
2. **`hedef.load` bütün Faz A değerlerini kabul eder; bağlanmamış ayarı `hedef.check_wired` durdurur.** Grup 1'de
   `follow_me`/`tez_los` doğrudan `load`'da reddediliyordu; bu, `takip_yuruyen.yaml`'ın yüklenmesini (ve
   `test_shipped_scenarios_load`'u, `onizleme.py --senaryo takip_yuruyen`'i) engellerdi. Şema (geçerli mi?) ile ara
   durum (bugün çalışır mı?) ayrıldı. `senaryo.main` ve `senaryo.run` (f1_testi gibi doğrudan çağıranlar için) ikisi
   de `check_wired` çağırır; ikisi de hiçbir şey açmadan önce.
3. **Ara durum tablosu** (`hedef.unwired`; her grup kendi satırını siler):

   | Varsayılan dışında verilen ayar | Hata | Not |
   |---|---|---|
   | `takip.kaynak: tez_los`, `takip.los: hakem` | Görev grubu 5'te bağlanacak | |
   | `takip.kaynak: follow_me` | Görev grubu 6'da bağlanacak | `takip_yuruyen` bunu verir |
   | `takip.px4_baslat`, `--px4-baslat` | Görev grubu 10'da bağlanacak | |
   | `algilama.model/imgsz/conf/sinif/cekirdek` (algılama açıkken) | Görev grubu 4'te bağlanacak | Algılama kapalıyken modelin ayarları etkisizdir, hata vermez; `ayarlar`'da görünür |
   | `kusurlar` boş değil | Görev grubu 4'te bağlanacak | Anahtarları 4. grupta `kusurlar.py` doğrular |
   | `video.qgc`, `--qgc` | Görev grubu 11'de bağlanacak | |
   | `--kareleri-sakla` | Görev grubu 8'de bağlanacak | |
   | `gecikme.*` ≠ 0, `--gecikme-ms` ≠ 0 | Görev grubu 12'de bağlanacak | |

   **Bugün bağlı olanlar:** `takip.kaynak: yok`, `--modelsiz` / `algilama.etkin: false` (model süreci zaten yok),
   `--videosuz` / `video.mp4: false` (video zaten yok), `takip.px4_parametreleri`, `--param`.
   Hata mesajındaki ek, sayının okunuşuna göre seçilir (`in_group`: 4'te, 5'te, 6'da, 8'de, 10'da, 11'de, 12'de).
   Grup 1'in mesajı "Görev grubu 5'da" diyordu; düzeltildi.
4. **Varsayılanı henüz etkin olmayan ayarlar da görünür:** `ayarlar.henuz_bagli_degil` (`hedef.not_in_effect`):
   bugün `{"algilama.etkin": 4, "takip.los": 5, "video.mp4": 8}`. Gerekçe: varsayılanlar "açık" (model, TEZ_LOS,
   MP4) ama bu gruplar gelene kadar hiçbiri çalışmıyor; `ozet.json` bunu söylemeseydi bugünkü bir koşunun
   `ayarlar`'ı modelin çalıştığını ima ederdi. Aynı liste koşu başında log'a da yazılır.
5. **`takip.px4_parametreleri` ve `--param` bu grupta bağlandı ve koşuda geri okunur** (grup 1'in önerisi;
   spec 10.4 bunu 10. gruba koyuyordu). `calistir.sh --param` 1. gruptan beri vardı; bağlamak yalnız
   `Simulation(params=...)`'ı doldurmaktı, ara hata koymak gereksizdi. Kalkıştan önce yüklenen **her** başlangıç
   parametresi (dosyalar + senaryo + `--param`, bugün 20–21 tane) `PARAM_REQUEST_READ` ile okunur ve
   `ayarlar.px4_parametreleri[AD] = {deger, kaynak, px4}` olarak yazılır (~1 s). PX4 istenen değeri tutmuyorsa koşu
   kalkıştan önce durur ("TAMAMLANMADI", olaylarda parametre, PX4'teki ve istenen değer, kaynağı). Gerekçe: grup
   1'in bulduğu `param set` istisnası (varsayılana eşit değer yazılmaz, airframe'in `set-default`'u kazanır) bir
   ayarı sessizce değiştirebilir; o koşunun ölçütleri istenen ayarlara ait olmazdı. SITL'de denendi (aşağıda:
   `--param MPC_THR_HOVER=0.5` → PX4'te 0.6).
6. **`MIS_TAKEOFF_ALT` senaryo/komut satırı parametresi olarak reddedilir:** `px4_baglanti.takeoff` onu
   `drone.yukseklik_m`'den yazar; verilen değer sessizce ezilirdi. Spec'in seçim kuralı da onu "senaryo verir" diye
   dosyaların dışında tutuyor.
7. **Algılama kapalıyken LOS:** `takip.los: model` açıkça istenirse reddedilir (spec kuralı). `los` hiç
   verilmemişse: `yok` kaynağında LOS yoktur (`ayarlar.takip.los: null`, log'da "LOS yok"); `follow_me`/`tez_los`
   ise `los: hakem` ister. Gerekçe: 4.6'da F1 `--modelsiz` ile koşacak; varsayılan `los: model` her zaman
   uygulansaydı F1 kendi kuralına takılırdı. Yön verecek bir şey yokken (yok + model kapalı) LOS'suz koşu dürüst
   durumdur; takip eden kaynaklar ise bir LOS/hedef kaynağı olmadan anlamsızdır, erken reddedilir.
8. **`takip.mod_adi` başka bir kaynakla verilirse hata değil:** spec'teki C7 akışı (`tez_los` senaryosunu
   `--takip follow_me` ile de koşmak) aksi hâlde kırılırdı. `ayarlar.takip` hem `mod_adi`'yi hem seçilen `mod`'u
   gösterdiği için sessiz değildir.
9. **Diğer doğrulama ayrıntıları:** `algilama.model` `~` açılır, göreli yol çalışılan klasöre göredir;
   `imgsz` tam sayı ≥ 32 (modelin adımına uygunluğu 3. grupta modelle birlikte); `conf` (0, 1]; `sinif` ad ya da
   numara ≥ 0 (`"0"` yazılırsa 0); `cekirdek` ≥ 1; `ek_ms`, `titresim_ms` ≥ 0, saat ofseti ve kayması işaretli;
   bütün sayılar sonlu. Bloklar yalnız sözlük olabilir; boş (`null`) yazılan blok/alan boş sayılır.
10. **`ozet.json`:** `takip_kaynagi` üst düzey alanı kaldırıldı, `ayarlar.takip.{kaynak, mod}`'a taşındı (onu okuyan
    başka kod yoktu). `rapor.html`'de `ayarlar` bölümü 7. gruba bırakıldı (7.4); parametre uyuşmazlığı olaylar
    listesinde görünür.

## Test sonuçları

| Kontrol | Sonuç |
|---|---|
| `pytest tez/sim/testler/test_hedef.py -q` | 62 geçti |
| `pytest tez/sim/testler -q` | 124 geçti (önceki 93 + 31), 1 uyarı (önceden de vardı, protobuf) |
| `ruff format` + `ruff check` (`tez/sim/ruff.toml`, ruff 0.16.9) | temiz |
| `tez/pin/verify_pin.sh --worktree` | **KILIT SAGLAM** (PX4 dosyası değişmedi) |
| `senaryo.py --senaryo takip_yuruyen --ekransiz` | 0.7 s'de, sim açılmadan, çıkış kodu 2: `takip.kaynak: follow_me (--takip): Görev grubu 6'da bağlanacak` (tek satır) |
| Diğer ara durum / şema hataları (komut satırından, sim açılmadan, çıkış 2) | `--takip tez_los` → `takip.mod_adi ... zorunlu ... --mod-adi`; `--conf 0.4 --qgc --gecikme-ms 200 --px4-baslat "x start" --kareleri-sakla --los hakem` → 6 satır (5'te, 10'da, 4'te, 12'de, 11'de, 8'de); `takip_yuruyen --modelsiz` → `takip.los: model, algılama kapalıyken ...`; `--param flw=1` → ad kuralı; `--takip uydu` → geçerli değerler listesi |
| SITL duman: kısa senaryo (scratchpad, `takip.px4_parametreleri: {MPC_XY_VEL_MAX: 8, FLW_TGT_DST: 9}`) + `--param MPC_XY_VEL_MAX=7` | **GEÇTİ** (1 dk 12 s): 21/21 parametre PX4'ten ~1 s'de geri okundu; `FLW_TGT_DST` 9 (`takip.px4_parametreleri`), `MPC_XY_VEL_MAX` 7 (`--param`, senaryonun 8'ini ezdi); sim.log'da `MPC_XY_VEL_MAX: curr: 12 -> new: 7`, `FLW_TGT_DST: curr: 8 -> new: 9`; dron 30.0 s'de Hold'da hazır |
| SITL: aynı senaryo + `--param MPC_THR_HOVER=0.5 --modelsiz --videosuz` | **TAMAMLANMADI, beklenen** (15 s, kalkış yok): "MPC_THR_HOVER PX4'te 0.6, istenen 0.5 (--param)"; `ayarlar.takip.los: null`, `henuz_bagli_degil: {}` |
| `tez/sim/araclar/f1_kabul.sh` | **GEÇTİ** (3 dk 41 s): iki koşuda 20/20 parametre geri okundu; hedef doğrulama farkı en fazla 0.13 m / 0.13 m (sınır 0.30); iki koşu arası 0.000 m (10 ortak an, sınır 0.15); dron 29.8 s'de Hold'da hazır (grup 1'deki gibi; geri okuma kalkışı geciktirmedi) |

Her koşudan sonra çalışan PX4/Gazebo süreci kalmadı (`pgrep -x px4`, `pgrep -f "^gz sim"` boş).

Kısa duman senaryosu repoya girmedi (scratchpad); tekrarlamak için bir `.yaml` dosyasına yazıp
`senaryo.py --senaryo <dosya> --ekransiz --param MPC_XY_VEL_MAX=7` ile koşun:

```yaml
ad: kisa_parametre
aciklama: Görev grubu 2 duman testi; senaryo ve komut satırı parametreleri PX4'ten geri okunur.
dunya: duz_alan
drone: {yukseklik_m: 10}
takip:
  kaynak: yok
  px4_parametreleri: {MPC_XY_VEL_MAX: 8, FLW_TGT_DST: 9}
hedef:
  baslangic: [10, 0]
  yol:
    - {nokta: [14, 0], hiz_mps: 1.4}
zamanlama: {baslama_s: 45, son_bekleme_s: 2}
basari: {}
```

## Karşılaşılan sorunlar

- İlk test sürümünde iki test, aynı `s.yaml` dosyasının üzerine yazıldığı için ve bir beklenen metin farklı olduğu
  için kırmızıydı; ikisi de testte düzeltildi (kod değişmedi).
- PX4'ten okunan float değerler float32'dir (`0.14000000059604645`). `ayarlar.px4_parametreleri[...].px4`'e ham
  değer yazılır (PX4'ün tuttuğu tam değer); olay mesajında 7 anlamlı basamakla gösterilir (`0.6`).
- F1'in iki koşusunda `kadrajda_kalma` 0.45 / 0.42 (grup 1'de 0.44 / 0.44): Hold'daki dronun küçük konum farkından;
  F1'in ölçütü (hedef konumu) değişmedi. Parametre okuma kalkıştan önce bittiği için uçuşa etkisi yok.

## Sonraki gruplar için notlar

- Ara hata ve `henuz_bagli_degil` satırları `hedef.unwired` ve `hedef.not_in_effect`'tedir; bir ayarı bağlayan grup
  kendi satırını siler ve `test_settings_of_later_groups_stop_the_run`'daki ilgili satırı günceller.
- Model yolunun varsayılanı (`~/auto-follow-modeller/...`) `Detection.model is None` iken 3. grupta çözülür;
  `ayarlar.algilama` o zaman çözülmüş yolu ve sha256'yı da yazmalıdır (spec 8: "model özeti de dahildir").
- `FLW_TGT_HT` senaryoda yoksa `drone.yukseklik_m` (6.4): `takip_yuruyen` bilerek yalnız `FLW_TGT_DST`'yi veriyor.
