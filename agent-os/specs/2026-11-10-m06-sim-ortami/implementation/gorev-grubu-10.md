# Görev Grubu 10 — Kendi PX4 modülünü takmak: `derle.sh --harici`, `--px4-baslat`, kılavuz

- Tarih: 14.11.2026 · dal `ozellik/m06-sim-ortami` · taban commit `4e902e86aa` + çalışma ağacı
- Kapsam: `tasks.md` 10.0–10.6
- Durum: **uygulandı, test edildi, koşuldu**; commit'i ana oturum atar.

## Kısaca

- Ağaç dışı bir PX4 modülü artık **PX4 dosyası değiştirmeden** sime takılıyor: `tez/sim/derle.sh --harici <klasör>`
  derler, `--px4-baslat "<modül> start"` (senaryoda `takip.px4_baslat`) PX4 açılınca başlatır, mod kalkıştan önce
  **adıyla** PX4'ün listesinden seçilir, koşu stok koşularla **aynı ölçütleri, raporu ve `kosu.mp4`'ü** üretir ve
  sonunda `sim.log`'da "unresponsive" aranır.
- **İskelet modülle denendi** (`c4b4abf342`'deki `tez_auto_follow`, scratchpad'e açıldı, bugünkü PX4 v1.17.0 ile
  **değiştirilmeden** derlendi): `takip_yuruyen` harici modlu koşu **GEÇTİ**. "Tez Auto Follow" PX4'ün listesinde
  (18 ad), adıyla seçildi, kayıt boyunca o modda kaldı (%100), "unresponsive" yok, `TEZ_LOS` 892 gönderildi = ULog 892.
  **İskelet seçildiği yerde konum tuttuğu için dron hedefi izlemedi** (mesafe 12.9 m'den 26.5 m'ye açıldı); bu
  beklenen bir sonuçtur. Amaç takip başarımı değil, mekanizmanın (derleme, başlatma, adla seçim, ölçüt, MP4)
  çalıştığını göstermekti.
- Bayraksız `derle.sh` yeniden stok SITL'e döndü (önbellek boş, modül ikilide yok, eski komut bağlantısı silindi);
  **F0 GEÇTİ**. 289 birim testi geçti (285 + 4 yeni), ruff temiz, **KILIT SAGLAM**.
- README'ye "C. Kendi PX4 modülünü takmak" bölümü girdi (spec C1–C8, iskelet notları `c4b4abf342`'ye atıfla).
- Yol üstünde iki sorun bulundu ve düzeltildi: videoda harici mod "External 1" yazıyordu (artık kayıtlı adı);
  stok derlemede 10.11'den kalma `bin/px4-tez_auto_follow` bağlantısı duruyordu (artık `derle.sh` siler).
- Ekipten gelen bilgi (09.11, Yusuf Algan; **kesinleşmiş değil, m15/m16 spec'inde kesinleşecek**): mod adı
  "AUTO FOLLOW", parametre öneki `AF_`. Bu yüzden kodda hiçbir ad yazılı değil; Kurt/Algan modülü gelince aynı komut
  onun adı ve başlatma komutuyla koşulur (bölüm 7).

## 1. Ne yapıldı

| Alt görev | Dosya | Sonuç |
|---|---|---|
| 10.1 | `tez/sim/testler/test_harici_mod.py` (yeni, 4 test); `test_hedef.py`, `test_olcum.py` (güncellendi) | Bölüm 4 |
| 10.2 | `tez/sim/derle.sh` | `--harici <klasör>` → `EXTERNAL_MODULES_LOCATION` (mutlak yol); bayrak yoksa `tez/px4/src/CMakeLists.txt` varsa o, yoksa stok; çıktı her zaman `build/px4_sitl_tez`; önbellekteki klasörden farklıysa yeniden yapılandırma; klasör denetimi, `PARENT_SCOPE` uyarısı, derlemeden çıkan modüllerin `bin/px4-*` bağlantılarını silme; `--help` |
| 10.3 | `tez/sim/calistir.sh` | `--px4-baslat "<komut>"` (çoklu, sırayla): komutun derlemede olduğu sim açılmadan denetlenir; PX4 açılınca `px4-logger status` başarılı olana kadar en çok 90 s beklenir; komutlar `rootfs` içinde `bin/px4-<komut> <argümanlar>` ile arka planda çalışır; çıktı ve çıkış kodu sim log'una |
| 10.4 | `tez/sim/araclar/simulasyon.py`, `senaryo.py`, `hedef.py`, `olcum.py` | `Simulation(px4_start=...)`, `external_mode`, `wait_ready` başlatma komutlarını bekler, `start_results`, `unresponsive`; `senaryo.simulation()`, harici modun adını 10 s'ye kadar bekleme, "unresponsive" → TAMAMLANMADI, `ozet.json` → `harici_mod`; `hedef.unwired`'dan 10. grubun ara hatası silindi; `olcum.with_mode_name` |
| 10.5 | `tez/sim/README.md` | "C. Kendi PX4 modülünü takmak" (C1–C8 + iskelet notları + iskelet denemesi); "Kurulum", "Çalıştırma", "Senaryolar", "Dosyalar" bölümlerinde `--harici` / `--px4-baslat` |
| 10.6 | koşular | Bölüm 5 |
| belgeler | `spec.md`, `tasks.md`, `EKIP_ICIN_OZET.md`, `implementation/kabul-kosulari.md`, bu dosya | spec'e "Uygulamada (10. grup)" notları; `EKIP_ICIN_OZET.md`'deki "10. grupta gelecek" satırı ve "AUTO FOLLOW" komutu (başlatma komutu olmadan reddedilirdi) güncellendi |

## 2. Kararlar ve gerekçeler

1. **"Harici modlu koşu" = başlatma komutu verilmiş koşu** (`Simulation.external_mode = bool(px4_start)`). Bizim (b)
   yolumuzda bir harici mod ancak PX4'ten sonra başlatılan bir modülle kaydolabilir; ayrı bir bayrak, unutulup
   kontrolü kapatabilirdi. Eski `Simulation(external_mode=...)` parametresi kaldırıldı (kullanan yoktu).
2. **"unresponsive" bulunursa koşu "TAMAMLANMADI"** (yalnız olay değil). Commander modu "unresponsive" sayınca mod
   çalışamaz olur; o koşunun ölçütleri takılan modu ölçmez. Ölçütler, rapor ve video yine yazılır; olaylarda satır
   sayısı ve ilk satır bulunur, `ozet.json` → `harici_mod.unresponsive` bütün satırları tutar. Kapanıştan sonra
   kalan süreç gibi diğer sorunlar eskisi gibi yalnız olaydır. Arama büyük/küçük harfe duyarsız `unresponsive`
   (commander: `No response from <id>, flagging unresponsive`, `externalChecks.cpp`). **Kullanıcı kararı
   (14.11.2026, Ahmet):** böyle kalır; "unresponsive" bulunan harici koşu TAMAMLANMADI sayılır.
3. **Komutun derlemede olduğu sim açılmadan denetlenir** (`bin/px4-<ilk kelime>` var mı). Yoksa
   `'<komut>' bu PX4 derlemesinde yok … Ağaç dışı bir modülse önce: tez/sim/derle.sh --harici <klasör>` ile çıkış
   kodu 2. Gerekçe: modülsüz bir derlemeyle koşu ancak ~20 s sonra PX4'ün "command not found"una çarpardı; takım
   arkadaşının en olası hatası (`derle.sh --harici`'yi unutmak) hemen ve nedeniyle söylenir. Denetim dünya ve süreç
   denetimlerinden önce yapılır (test bunu, var olmayan bir dünyayla sınar: mesaj dünya hakkında olsaydı sıra yanlış
   olurdu).
4. **Derlemeden çıkan modülün komut bağlantısı silinir.** PX4 `bin/px4-<komut>` bağlantılarını derleme sonrası
   oluşturur (`px4_posix_generate_symlinks`, POST_BUILD) ama hiç silmez. Bugünkü stok derlemede 23.10'dan kalma
   `bin/px4-tez_auto_follow -> px4` duruyordu: 3. maddedeki denetim onu "var" sayar, koşu sonra PX4'te düşerdi.
   `derle.sh` derlemeden sonra `px4-alias.sh`'ta (yapılandırmada güncel modül listesinden yazılır,
   `px4_posix_generate_alias`) olmayan `bin/px4-*` bağlantılarını siler (yalnız bağlantı; `px4`, `px4-alias.sh`
   dosyadır). Stoka dönüşte "Derlemede olmayan modülün komutu silindi: bin/px4-tez_auto_follow" yazdı.
5. **`wait_ready` iki satır bekler:** `Startup script returned successfully` ve `PX4 başlatma komutları tamam`.
   Komutlar logger'ı bekler ve rcS logger'ı sondan bir önce başlatır (`init.d-posix/rcS`: `rc.logging`, sonra
   `mavlink boot_complete`); yani komutlar rcS'in son satırından önce de bitebilir. Üç açılışta da rcS'ten ~1 s sonra
   bittiler. Başarısızlık satırlarında (`PX4 başlatma komutu başarısız`, `PX4 başlatma komutları çalıştırılamadı`)
   beklemeden `False` ("Simülasyon açılmadı"). Satırlar `simulasyon.START_*`'ta; test `calistir.sh`'ın aynılarını
   yazdığını denetler. Neden `px4-logger status`: spec'te böyle; ayrıca terminalde PX4 ön planda `pxh>` kabuğunu
   tuttuğu için çıktıyı izlemek yerine istemciyle sormak her iki modda (terminal / arka plan) çalışır.
6. **Başarısız bir komut kalanları durdurur** (sonraki komutlar ilkine bağlı olabilir) ve koşu açılmaz. Terminalde
   elle çalışırken PX4 kapanmaz; yalnız satır yazılır.
7. **Kelimeler boşlukla ayrılır, tırnak desteklenmez** (`read -r -a`). PX4 komutları için yeterli; README'de yazılı.
   Komutlar `< /dev/null` ile çalışır (terminalde arka plandaki istemci girişe dokunmasın).
8. **Harici modun adı 10 s'ye kadar beklenir** (`senaryo.EXTERNAL_MODE_WAIT_S`; liste her saniye yeniden istenir).
   Modül kaydı başlatma komutundan birkaç ms sonra olur (iskelette `status` komutu "not registered" dedi, hemen
   arkasından `registered as`); iskelet isteğini 1 s'de bir yineler. Koşularda ad ilk istekte bulundu. Bulunamazsa
   hata PX4'ün listesine ek olarak "ad modülün `register_ext_component_request`'te yazdığıyla aynı olmalı (en çok 24
   karakter), modülün çıktısı sim.log'da" ipucunu verir.
9. **Harici yuva rapor ve videoda kayıtlı adıyla yazılır.** ULog'daki `vehicle_status.nav_state` 23'tür; PX4'ün ad
   tablosunda bu "External 1"dir (harici modun adını PX4 yalnız çalışırken bilir). İlk koşunun videosunda durum
   satırında "External 1" yazıyordu. `olcum.with_mode_name` koşunun seçtiği yuvayı (`istenen_nav_state`) koşunun
   kullandığı adla (AVAILABLE_MODES) yazar; PX4'ün kendi modları PX4'ün adını korur (test: `test_olcum.py`). Koşu
   yinelendi, videoda "Tez Auto Follow" görünüyor.
10. **`derle.sh --harici` küçük denetimleri:** klasörde `src/CMakeLists.txt` yoksa (ör. yanlışlıkla `src`'nin kendisi
    verilirse) CMake'e gitmeden çıkış kodu 2; `PARENT_SCOPE` yoksa uyarı; klasör `realpath` ile mutlak yapılır
    (PX4 CMake değeri önbellekte verildiği gibi tutar; göreli yol başka klasörden çağrıda "farklı" görünür ve gereksiz
    yeniden yapılandırırdı). Hangi klasörle derlendiği ve neden yeniden yapılandırıldığı yazılır.

Tasarım spec'ten sapmadı; yukarıdaki ayrıntılar spec'e "Uygulamada (10. grup)" notları olarak eklendi (6. ve 7.
madde, 8. maddedeki ara durum, alan tablosu, dosya tablosu, test planı, kılavuz C notu).

## 3. İskelet modül (`c4b4abf342`) notları

Kaynak: `git show c4b4abf342:tez/px4/src/...` (repoda değil). Scratchpad'e açıldı ve **hiç değiştirilmeden** bugünkü
PX4 v1.17.0 ile derlendi (`external_modules/modules/tez_auto_follow/...TezAutoFollow.cpp.o`, ccache ile 8 s).

| Konu | İskelette | Neden (PX4 v1.17.0 kaynağı) |
|---|---|---|
| Modül listesi | `tez/px4/src/CMakeLists.txt`: `set(config_module_list_external modules/tez_auto_follow PARENT_SCOPE)` | PX4 `CMakeLists.txt` `add_subdirectory("${EXTERNAL_MODULES_LOCATION}/src" external_modules)` sonra `foreach(external_module ${config_module_list_external})`: liste üst kapsamda okunur |
| Bağımlılık | `px4_add_module(MODULE modules__tez_auto_follow MAIN tez_auto_follow SRCS ...)`, **`DEPENDS` yok** | Harici modüller `src/lib`'den önce yapılandırılır (`CMakeLists.txt` 406–413 → 424); `px4_work_queue` vb. `px4` ikilisine zaten bağlanır |
| Kayıt | `register_ext_component_request`: `register_mode` + `register_arming_check`, `name` = "Tez Auto Follow" | `msg/versioned/RegisterExtComponentRequest.msg`: `char[25] name` → en çok **24 karakter**; "AUTO FOLLOW" 11 karakter |
| Arming check | her `arming_check_request`'e `arming_check_reply` (`can_arm_and_run`, `mode_req_*`, `mode_req_prevent_arming = true`) | Commander 300 ms'de bir sorar, 50 ms bekler, art arda 3 (kayıttan hemen sonra 10) cevapsızda "unresponsive" (`externalChecks.hpp`); iskelet 10 ms'de bir çalışır |
| Kontrol | `config_control_setpoints` + mod seçiliyken `trajectory_setpoint` (giriş anındaki konum ve yaw) | Konum kontrolcüsü zinciri; takip mantığı `update_setpoint()`'in yerine gelir |
| Çıkış | `unregister_ext_component` | Modül durunca yuva boşalır |
| Başlatma | eski airframe `4030_gz_x500_tez.post` (`tez_auto_follow start`) | Bugünkü (b) yolunda o airframe yok: `--px4-baslat "tez_auto_follow start"` |
| Gerçek kart | commit mesajında `px4_fmu-v6c_default` + modül: +2.8 KB, FLASH %98.1 | Bu grupta kart derlemesi yapılmadı (Pixhawk kodu değişmedi) |

## 4. Testler

`tez/sim/testler/test_harici_mod.py` (yeni, 4 test; simsiz, donanımsız):

1. `test_start_commands_reach_calistir_in_order`: senaryodaki `takip.px4_baslat` (2 komut) + `--px4-baslat` (1)
   `calistir.sh`'a bu sırayla ve `--param`'lardan sonra gider; `hedef.check_wired` artık durdurmaz; stok olmayan ad
   (`Tez Auto Follow`) başlatma komutuyla sim açılmadan reddedilmez, komutsuz reddedilir; `ayarlar.takip.px4_baslat`
   aynı sırada; komutsuz koşu harici modlu değildir.
2. `test_unresponsive_is_looked_for_only_with_an_external_mode`: aynı `sim.log` satırı stok koşuda sorun değildir;
   harici modlu koşuda sorundur (2 satır sayılır, ilk satır mesajdadır); temiz harici koşuda sorun yoktur.
3. `test_the_run_waits_until_calistir_ran_the_start_commands`: `wait_ready` yalnız rcS bitince `True` dönmez,
   rcS + "tamam" (iki sırada da) `True`, başarısız komut ve gelmeyen logger `False`; `start_results` çıkış kodlarını
   okur; `calistir.sh` aynı satırları yazar.
4. `test_calistir_refuses_a_start_command_before_anything_starts`: `calistir.sh` derlemede olmayan
   (`yok_boyle_modul start`), boş ve değersiz `--px4-baslat`'ı sim açılmadan çıkış kodu 2 ile reddeder; stok bir komut
   (`logger status`) geçer (sonra dünya yok hatası). `build/px4_sitl_tez/bin/px4` yoksa atlanır.

Güncellenen: `test_hedef.py` (10. grubun ara hatası beklentisi çıktı, `px4_start` "bağlı" listesinde),
`test_olcum.py` (harici yuvanın kayıtlı adıyla yazılması, PX4 modlarının adını koruması).

| Kontrol | Sonuç |
|---|---|
| `pytest tez/sim/testler -q` | **289 passed** (önce 285), 1 uyarı (sistemdeki protobuf, eskiden beri) |
| `ruff format` + `ruff check` (`tez/sim/ruff.toml`) | 59 dosya değişmedi; All checks passed |
| `tez/pin/verify_pin.sh --worktree` | **KILIT SAGLAM (v1.17.0)** |
| `bash -n` + `shellcheck` (`derle.sh`, `calistir.sh`) | temiz (shellcheck yalnız denetim için, iş akışına eklenmedi) |
| `derle.sh` hata yolları | `--harici` değersiz, `--harici <klasör>/src`, bilinmeyen seçenek → çıkış kodu 2, CMake'e gidilmedi |

## 5. Koşular (10.6)

Ayrıntılı satırlar `kabul-kosulari.md`'de. Sıra: harici derleme → duman testi → senaryo (iki kez) → stoka dönüş + F0.

| Adım | Komut | Sonuç |
|---|---|---|
| Harici derleme | `tez/sim/derle.sh --harici <scratchpad>/iskelet/tez/px4` | 8 s (ccache); yeniden yapılandırma; `EXTERNAL_MODULES_LOCATION` önbellekte; `bin/px4-tez_auto_follow` var; aynı klasörle ikinci çağrı yeniden yapılandırmadı ("no work to do") |
| Duman testi (scratchpad betiği) | `Simulation(px4_start=("tez_auto_follow start", "tez_auto_follow status"))` + AVAILABLE_MODES | 14.0 s'de hazır, iki komut çıkış 0, 18 mod, "Tez Auto Follow" `custom_mode` 0xb040000, unresponsive 0, temiz kapanış |
| Senaryo (son kod) | `senaryo.py --senaryo takip_yuruyen --ekransiz --takip tez_los --mod-adi "Tez Auto Follow" --px4-baslat "tez_auto_follow start" --los hakem --cikti tez/sim/sonuclar/g10_harici_iskelet` | **GEÇTİ**, 2 dk 27 s |
| Stoka dönüş | `tez/sim/derle.sh` | yeniden yapılandırdı, önbellek boş, bağlantı silindi, ikilide "Tez Auto Follow" yok (7 s) |
| F0 | `tez/sim/araclar/f0_kabul.sh` | **GEÇTİ** (1 dk 9 s) |

Senaryo seçeneklerinin adları `senaryo.py --help` ile doğrulandı; görev metnindeki komutla aynı.

**Harici modlu koşunun sayıları** (`tez/sim/sonuclar/g10_harici_iskelet/`):

| Ne | Değer |
|---|---|
| Başlatma | `tez_auto_follow start` çıkış kodu 0 (rcS'ten ~1 s sonra); `registered as 'Tez Auto Follow' (nav_state 23, arming check 0)` |
| Mod listesi | 18 ad = 17 stok + "Tez Auto Follow" (`ayarlar.takip.px4_modlari`); ad ilk istekte bulundu |
| Mod seçimi | 26.5 s'de adıyla; ULog `nav_state` 23 25.7–90.5 s; **istenen modda %100**; `sim.log`: `mode active, holding N 0.0 E 0.0 D -8.9 m` |
| "unresponsive" | **0 satır** (`ozet.json` → `harici_mod: {baslatma: [{komut, cikis_kodu: 0}], unresponsive: []}`) |
| `TEZ_LOS` (hakem) | kayıt penceresinde 892 gönderildi = ULog 892 (%100, ±%5 koşulu), uçtan uca ort. 42 ms (p95 46) |
| Takip | dron konum tuttu: yatay mesafe ort. 21.2 m (12.9 → 26.5 m), hedefin tamamı kadrajda %100, 6 m altı geçiş 0. **Beklenen:** iskelet hedefi izlemez |
| Model (bilgi) | hedef görünürken bulma %39 (kişi uzaklaştıkça küçülüyor), yanlış kişi %0; LOS (i)–(ii) ort. 0.13° |
| Çıktılar | `kosu.mp4` (h264, yuv420p, 2000×720, 944 kare, 62.9 s; durum satırında "Tez Auto Follow"), `rapor.html`, `ozet.json`, `ucus.ulg`, CSV'ler |
| RTF | 0.881 (ilk koşuda 0.989; aynı komut, makinenin o anki yükü) |

**Yorum:** Kabul ölçütlerinin üçü sağlandı: ağaç dışı modül derlendi, başlatıldı, adıyla seçildi ve stok koşularla
aynı ölçütler ile MP4 üretildi; bayraksız derleme stoka döndü; kilit listesine yol eklenmedi. "GEÇTİ" yalnız
koşunun tamamlandığını söyler (`takip_yuruyen`'in `basari` eşiği yok); iskelet takip etmediği için takip ölçütleri
(mesafe, arkada kalma açısı ort. 70°) bir takip modunu değil, havada bekleyen dronu ölçer.

## 6. Karşılaşılan sorunlar

1. **Videoda mod adı "External 1"** (ilk koşu): ULog'un yuva adı. `olcum.with_mode_name` ile düzeltildi, test
   eklendi, koşu yinelendi (karar 9). İlk koşunun klasörü yenisiyle değiştirildi.
2. **Stok derlemede eski `bin/px4-tez_auto_follow`** (23.10'dan): PX4 derlemesi bağlantı silmiyor. `derle.sh` artık
   siler (karar 4).
3. **İskelet derlemesinde sorun çıkmadı**: düzeltme gerekmedi (PX4 kilitli olduğu için API aynı). Scratchpad kopyası
   değiştirilmedi.
4. Açılışta bir kez `Arming denied: Resolve system health failures first` + `No connection to the GCS`: stok
   koşularda da aynı (ör. `gorev17c_kalabalik/.../sim.log`); GCS bağlanınca kalkış yapılıyor, harici modla ilgisi yok.
   "unresponsive" aramasına girmez.

## 7. Kurt / Algan modülü gelince koşulacak komut

Ekipten gelen bilgiye göre (09.11, Yusuf Algan; **kesinleşmiş değil, m15/m16 spec'inde kesinleşecek**) mod adı
"AUTO FOLLOW"; modülün yeri ve başlatma komutu henüz bilinmiyor (`<modül>` yerine onların komutu yazılır).

Modül onların dalında `tez/px4/` altındaysa `derle.sh` onu kendisi bulur; başka bir klasördeyse `--harici`:

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && tez/sim/derle.sh --harici <onların klasörü>/tez/px4
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz --takip tez_los --mod-adi "AUTO FOLLOW" --px4-baslat "<modül> start" --los hakem
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz --takip tez_los --mod-adi "AUTO FOLLOW" --px4-baslat "<modül> start" --los model
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && tez/sim/derle.sh
```

Önce `--los hakem` (mükemmel algılayıcı: yalnız modun kendi davranışı), sonra `--los model` (v0.2'nin kutuları).
Modülün parametreleri `--param AF_XXX=<değer>` ya da senaryo kopyasında `takip.px4_parametreleri` ile verilir (her
biri koşuda PX4'ten geri okunur). Sonuç `implementation/`'a ve `kabul-kosulari.md`'ye yazılır; `m06_kabul.sh`'ın
isteğe bağlı 3. koşusu (13. grup) aynı komuttur.

## 8. Dosyalar (commit'e girecekler)

- `tez/sim/derle.sh`
- `tez/sim/calistir.sh`
- `tez/sim/araclar/simulasyon.py`
- `tez/sim/araclar/senaryo.py`
- `tez/sim/araclar/hedef.py`
- `tez/sim/araclar/olcum.py`
- `tez/sim/testler/test_harici_mod.py` (yeni)
- `tez/sim/testler/test_hedef.py`
- `tez/sim/testler/test_olcum.py`
- `tez/sim/README.md`
- `agent-os/specs/2026-11-10-m06-sim-ortami/spec.md`
- `agent-os/specs/2026-11-10-m06-sim-ortami/tasks.md`
- `agent-os/specs/2026-11-10-m06-sim-ortami/EKIP_ICIN_OZET.md`
- `agent-os/specs/2026-11-10-m06-sim-ortami/implementation/gorev-grubu-10.md` (yeni, bu dosya)
- `agent-os/specs/2026-11-10-m06-sim-ortami/implementation/kabul-kosulari.md`

`tez/sim/ruff.toml` değişmedi (yeni Python modülü yok; test dosyası `known-first-party`'ye girmez). Repoya iskelet
modül, video ya da ULog girmedi. Repo dışı: `/home/ahmet/Desktop/Follow/3_m06_Simulasyon/g10_harici_mod_iskelet.mp4`,
`tez/sim/sonuclar/g10_harici_iskelet/` (git dışı).

## 9. Açık konular ve sorulacaklar

- ~~"unresponsive" bulunan harici koşunun "TAMAMLANMADI" sayılması~~ → karara bağlandı (14.11.2026, Ahmet): böyle
  kalır (karar 2).
- Kurt/Algan: modülün yeri (`tez/px4` dalı mı, ayrı repo mu), başlatma komutu, kesin mod adı ve `AF_` öneki
  (m15/m16 spec'i). Kodda değişiklik gerekmez.
- `karsilastir.py` (C7) 12. grupta; `m06_kabul.sh` 3. koşusu 13. grupta.
- Gerçek kartta başlatma (`etc/extras.txt`) ve flash payı m15/m16'nın işi; bu grupta kart derlemesi yapılmadı.
- QGC'nin listesinde görünme bu grupta pencereli denenmedi (koşular ekransızdı); aynı AVAILABLE_MODES listesini
  okuduğu için görünmesi beklenir; aşağıdaki "Kendin dene" 6'da bakılabilir.

---

## Kendin dene

**Başlamadan:** Terminal açmak için **Ctrl+Alt+T**. Aşağıdaki gri kutulardaki satırları **tek tek** kopyala, terminale
**Ctrl+Shift+V** ile yapıştır ve **Enter**'a bas. Her satır tek başına çalışır (değişken yok; yeni bir terminalde de
olur). Bir komutu yarıda kesmek için **Ctrl+C**. VLC: **Boşluk** duraklat/sürdür, **Ctrl+T** zamana git,
**[** / **]** yavaşlat/hızlandır, **F** tam ekran.

### 1. Videoyu izle (koşu hazır)

```bash
vlc /home/ahmet/Desktop/Follow/3_m06_Simulasyon/g10_harici_mod_iskelet.mp4 2>/dev/null
```

Neye bakacaksın:
- **Sol üst durum satırı:** `t = ... · Tez Auto Follow · uçtan uca .. ms` — dron baştan sona takılan modda (harici
  mod adıyla seçildi; ilk denemede burada "External 1" yazıyordu, düzeltildi).
- **Sağdaki kuşbakışı harita:** turuncu üçgen dron, mavi nokta kişi. Dron **hiç kımıldamaz**: iskelet modül seçildiği
  yerde konum tutar. Yeşil yıldız "olması gereken yer" (kişinin 12.9 m arkası); dron oraya gitmez. Bu beklenen
  davranıştır: deneme takibi değil, modülün takılıp seçilebildiğini gösterir.
- **0:33** kişi doğuya yürümeye başlar, mesafe 12.9 m'den açılır; **0:46** kuzeye koşar; **0:51** batıya döner;
  **1:03** biter (≈ 26 m). Soldaki kamera görüntüsünde kişi gittikçe küçülür ve kadrajın sol üstüne kayar; mavi
  hakem kutusu hep üstündedir, kırmızı model kutusu kişi küçüldükçe seyrekleşir (durum satırında "bu karede hedef
  bulunamadı").

### 2. Rapor ve sonuç dosyaları

```bash
firefox /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/g10_harici_iskelet/rapor.html
```

Raporda: "Mod zaman çizelgesi (ULog)" tablosunda **Tez Auto Follow (23)** satırı; "Ölçümler"de "İstenen PX4
modunda geçen süre / kayıt penceresi" **%100.0**; "Ayarlar"da "PX4 başlatma komutları: tez_auto_follow start" ve
PX4'ün mod listesinde "Tez Auto Follow".

```bash
grep -A 9 '"harici_mod"' /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/g10_harici_iskelet/ozet.json
```

Beklenen: `"komut": "tez_auto_follow start"`, `"cikis_kodu": 0`, `"unresponsive": []`.

```bash
grep -E "başlatma|tez_auto_follow|unresponsive" /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/g10_harici_iskelet/sim.log
```

Beklenen: `PX4 başlatma komutu: tez_auto_follow start`, `... bitti (çıkış kodu 0) ...`, `PX4 başlatma komutları tamam
(1 komut)`, `registered as 'Tez Auto Follow' (nav_state 23, ...)`, `mode active, holding ...`; "unresponsive" hiç yok.

### 3. Kendin koştur (pencere yok, ~3 dakika + derlemeler)

Önce açık bir sim olmadığından emin ol (iki satır da bir şey yazmamalı):

```bash
pgrep -x px4
```

```bash
pgrep -f "^gz sim"
```

İskelet modülü repo dışına aç (repoya girmez):

```bash
mkdir -p /tmp/iskelet && cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && git archive c4b4abf342 tez/px4 | tar -x -C /tmp/iskelet
```

Modülle derle (sonunda "Derleme tamam: ... (harici modüller: /tmp/iskelet/tez/px4)"):

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && tez/sim/derle.sh --harici /tmp/iskelet/tez/px4
```

Koştur (sonunda "SONUÇ: GEÇTİ"; günlükte "Harici mod 'Tez Auto Follow': listede" ve "'unresponsive' satırı 0"):

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz --takip tez_los --mod-adi "Tez Auto Follow" --px4-baslat "tez_auto_follow start" --los hakem --cikti tez/sim/sonuclar/g10_kendin_dene
```

```bash
vlc /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/g10_kendin_dene/kosu.mp4 2>/dev/null
```

**İş bitince mutlaka stoka dön** (sonra F0, F1 ve demo koşuları stok derlemeyle çalışır):

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && tez/sim/derle.sh
```

Beklenen: "Harici modüller: yok (stok PX4 SITL)", "Derlemede olmayan modülün komutu silindi: bin/px4-tez_auto_follow".

### 4. Pencereli deneme: Gazebo'da izle (aynı senaryo)

3. adımdaki gibi önce `pgrep` iki satırı boş olmalı ve modülle derlenmiş olmalı (`tez/sim/derle.sh --harici
/tmp/iskelet/tez/px4`). Gazebo penceresi açılır (AMD ekran kartı için `DRI_PRIME=1` aynı satırda):

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && DRI_PRIME=1 /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --takip tez_los --mod-adi "Tez Auto Follow" --px4-baslat "tez_auto_follow start" --los hakem --cikti tez/sim/sonuclar/g10_pencereli
```

Gazebo'da dron 9 m'ye kalkar ve orada asılı kalır; kişi 60. saniyede yürümeye başlar ve dron onu izlemez (iskelet).
Bu koşu sırasında QGC'yi de açabilirsin (5. adımdaki komut); kendiliğinden bağlanır ve üstteki uçuş modu yazısında
"Tez Auto Follow" görünür. İş bitince `tez/sim/derle.sh` ile stoka dön.

### 5. Elle: QGC'nin mod listesinde "Tez Auto Follow"

Modülle derlenmiş olmalı. Simi pencereyle ve PX4 kabuğuyla aç (bu terminal `pxh>` olur):

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && DRI_PRIME=1 tez/sim/calistir.sh --px4-baslat "tez_auto_follow start"
```

Terminalde birkaç saniye sonra `PX4 başlatma komutları tamam (1 komut)` ve `registered as 'Tez Auto Follow'`
satırları çıkar. İkinci bir terminalde QGC'yi aç:

```bash
/home/ahmet/Desktop/QGroundControl-v5.1.4-x86_64.AppImage
```

QGC'de: üstteki uçuş modu yazısına tıkla → listede stok modların yanında **Tez Auto Follow** var. Yerdeyken seçersen
arm edilmez (iskelet Follow Me gibi yerde arm'ı reddeder). Önce **Takeoff** (sol taraftaki kalkış düğmesi, kaydırarak
onayla), dron kalkıp havada durunca listeden **Tez Auto Follow**'u seç: dron olduğu yerde asılı kalır. `pxh>` terminalinde:

```bash
tez_auto_follow status
```

Beklenen: `mode 'Tez Auto Follow': registered, nav_state 23, active`. Kapatmak için `pxh>`'ye `shutdown` yaz (Gazebo
da kapanır), sonra stoka dön:

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && tez/sim/derle.sh
```

### 6. Hata mesajlarını gör (sim açılmaz, 1 saniye)

Stok derlemeyle (yukarıdaki `tez/sim/derle.sh`'tan sonra) modülü başlatmaya çalışmak, sim açılmadan nedenini söyler:

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && tez/sim/calistir.sh --ekransiz --px4-baslat "tez_auto_follow start"
```

Beklenen: `'tez_auto_follow' bu PX4 derlemesinde yok (...). Ağaç dışı bir modülse önce: tez/sim/derle.sh --harici
<klasör>`.

Başlatma komutu olmadan stok olmayan bir mod adı (ekipten gelen ad "AUTO FOLLOW"; kesinleşmiş değil):

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --takip tez_los --mod-adi "AUTO FOLLOW"
```

Beklenen: `takip.mod_adi: 'AUTO FOLLOW' PX4'ün seçilebilir modları arasında yok (--mod-adi) ...` ve PX4'ün 17
modunun listesi, "modülü takip.px4_baslat / --px4-baslat ile başlatın" ipucu.

### 7. Kontroller

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && /home/ahmet/Desktop/Projects/Auto-Follow/.venv-tez/bin/python -m pytest tez/sim/testler -q
```

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && tez/pin/verify_pin.sh --worktree
```

```bash
cd /home/ahmet/Desktop/Projects/Auto-Follow/Autopilot && tez/sim/araclar/f0_kabul.sh
```

Beklenen: `289 passed`; `KILIT SAGLAM (v1.17.0)`; F0 (~1 dakika) sonunda `SONUÇ: GEÇTİ` (stok derlemeyle).

Kılavuzun tamamı (takım arkadaşları için): `/home/ahmet/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/README.md` →
"C. Kendi PX4 modülünü takmak".
