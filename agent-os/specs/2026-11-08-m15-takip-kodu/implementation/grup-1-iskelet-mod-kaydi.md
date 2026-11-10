# Görev grubu 1: İskelet, mod kaydı, arming check, açılışta başlatma

- **Tarih:** 2026-11-10 · **Dal:** `ozellik/m15-takip-kodu` · **Görev listesi:** `../tasks.md` Grup 1 (1.1–1.14)
- **Durum:** Bitti. İki derleme geçti, SITL duman testi geçti. `verify-pin` CI'da, Hüseyin'in izin listesi PR'ı gelene kadar kırmızı kalır (beklenen).
- Bu not kod okumadan anlaşılacak şekilde yazıldı. Kodda adı geçen her şeyin anlamı `../log-sozlugu.md`'de.

## 1. Ne yapıldı?

PX4'ün içinde, kendini **AUTO FOLLOW** adında yeni bir uçuş modu olarak kaydettiren en küçük modül yazıldı. Bu grupta modül **henüz hiçbir şey uçurmaz**: hedef verisini okumaz, hız istemez. Yalnızca şunları yapar:

1. Açılışta (yalnızca `AF_ENABLE` = 1 ise) kendiliğinden başlar.
2. PX4'e "ben AUTO FOLLOW adında bir modum" der; PX4 ona 23–30 aralığından bir mod numarası verir. SITL'de **23** aldı.
3. PX4'e bu modda hangi kontrolcülerin açık olacağını söyler (konum, hız, irtifa… açık; offboard ve manuel kapalı; "auto" açık).
4. PX4'ün her 300 ms'de sorduğu "çalışabilir misin, neye ihtiyacın var?" sorusuna her seferinde cevap verir.
5. Saniyede 50 kez döner (sabit 20 ms).
6. 16 `AF_*` parametresini tanımlar; QGC'den değiştirilebilirler.
7. `auto_follow stop` ile durdurulunca kaydını PX4'ten siler; mod QGC listesinden kalkar.

### Dosyalar

| Dosya | Ne |
|---|---|
| `src/modules/auto_follow/AutoFollow.hpp`, `AutoFollow.cpp` | Modülün kodu (kayıt, kontrol modu ayarı, arming check cevabı, 50 Hz çevrim, `start` / `stop` / `status`) |
| `src/modules/auto_follow/CMakeLists.txt` | Derleme tanımı (`MODULE_CONFIG module.yaml`) |
| `src/modules/auto_follow/Kconfig` | `CONFIG_MODULES_AUTO_FOLLOW` açma ayarı |
| `src/modules/auto_follow/module.yaml` | 16 parametrenin tanımı |
| `boards/px4/sitl/default.px4board` | `CONFIG_MODULES_AUTO_FOLLOW=y` (alfabetik yerine, tek satır) |
| `boards/px4/fmu-v6c/default.px4board` | `CONFIG_MODULES_AUTO_FOLLOW=y` (tek satır) |
| `ROMFS/px4fmu_common/init.d/rc.mc_apps` | Dosyanın sonuna `AF_ENABLE` = 1 ise `auto_follow start` bloğu (başka satıra dokunulmadı) |

Bu yedi yolun hepsi Hüseyin'e iletilecek 7 yollu talebin içinde (`../spec.md` "Kilitli yollar ve flash"). `tez/pin/allowed-paths.txt`'e dokunulmadı.

## 2. Neden böyle? (spec bölümü / karar)

| Ne | Neden | Kaynak |
|---|---|---|
| External mode, `mc_nn_control` kalıbı | PX4'ün içinde, kilitli dosyalara en az dokunan yol | spec Bölüm 1, Karar 2-a, 3-a |
| Klasör, komut, açma ayarı adları; mod adı `AUTO FOLLOW` | Kullanıcının verdiği adlar | spec Bölüm 1, `requirements.md` 5.2 |
| `ModuleBase` + `ModuleParams` + `ScheduledWorkItem`, kuyruk `nav_and_controllers`, sabit 50 Hz | Veri kesilse de modül dönmeli ki kesintiyi fark etsin | spec Bölüm 1 (Karar), tasks 1.1–1.2 |
| `Run()` sırası: çıkış → kayıt isteği → cevabın beklenmesi → arming check cevabı → "mod aktif mi" kapısı | `mc_nn_control.cpp:436-477` ile aynı sıra | tasks 1.3 |
| Kontrol bayrakları; `flag_control_auto_enabled = true` | RC çubuğu oynayınca Position'a geçilsin (güvenlik) | A1, A2, C1 |
| Mod gereksinimleri (`mode_req_*`) | Tutum, açısal hız, yerel irtifa ve yerel konum gerekli; GPS, home, görev, RC gerekmiyor | A1, C1 |
| `mode_req_prevent_arming = true` | Bu modda arm yasak; disarm iken moda geçiş serbest | C1 |
| `can_arm_and_run = !(yerde && mod aktif değil)` | Yerde arm'lıyken moda geçişi PX4 reddetsin; mod aktifken hep "çalışabilirim" (aksi halde RTL) | A14-a, Karar 5-a |
| `rc.mc_apps` satırı, `AF_ENABLE` koşulu, varsayılan 0 | Kayıt yalnızca disarm iken kabul edilir, modül arm'dan önce başlamalı | B2-b, A13-b |
| İki kart dosyasına açma satırı | Modül 6C firmware'ine de girer | Karar 3.1-ii |
| 16 parametre, spec tablosundaki değerlerle | — | spec Bölüm 10 |

## 3. Nasıl çalışıyor? (sade anlatım)

- **Başlangıç:** PX4 açılırken `rc.mc_apps` dosyasını çalıştırır. Dosyanın sonundaki yeni blok `AF_ENABLE` parametresine bakar: 1 ise `auto_follow start` komutunu verir, 0 ise hiçbir şey yapmaz. Varsayılan 0 olduğu için firmware ilk yüklendiğinde mod görünmez.
- **İlk çevrim:** Modül PX4'ün komutanına (commander) bir kayıt isteği gönderir: ad `AUTO FOLLOW`, "hem mod hem arming check kaydet".
- **Sonraki çevrimler:** Cevap gelene kadar bekler. Cevap "başarılı" ise mod numarasını (23–30) ve arming check numarasını saklar, hemen ardından hangi kontrolcülerin açık olacağını PX4'e bildirir. Cevap "reddedildi" ise konsola bir kez hata yazar ve yeniden denemez (PX4 arm iken kaydı reddeder).
- **Her çevrimde:** PX4'ün durumunu (`vehicle_status`: şu anki mod) ve yerde olup olmadığını (`vehicle_land_detected`) okur. PX4 yeni bir "çalışabilir misin?" sorusu sorduysa cevaplar. Mod şu an seçili mi (`mode active`) her çevrimde bilinir; Grup 2'de hesaplar bu kapının arkasına girecek.
- **Durdurma:** `auto_follow stop` verilince modül önce "kaydımı sil" mesajını yayınlar, PX4 modu listeden kaldırana kadar (en fazla 1 s) bekler, sonra kapanır. Neden beklediği 6. bölümde (sorun 2).
- **Açılar:** `AF_TRK_ANG` ve `AF_MIN_DEP` QGC'de derece girilir; modül bunları her parametre değişiminde radyana çevirip saklar (Grup 2'de kullanılacak).

## 4. Nasıl test edildi?

### 4.1 Derlemeler

| Derleme | Sonuç |
|---|---|
| `make px4_sitl_default` | Geçti. PX4 derlemesi uyarıyı hata sayar (`-Werror`); modülde uyarı yok. |
| `make px4_fmu-v6c_default` | Geçti. Modülde uyarı yok. `region FLASH overflowed` yok. |

6C derlemesinde kart dosyası değişince yapılandırma yeniden çalıştı ve iki eski uyarı göründü: CMake'in `find_package` politika uyarısı ve NuttX Kconfig'in `ARCH_CHIP_UNSET` uyarısı. İkisi de PX4 v1.17.0'ın kendi yapılandırmasından geliyor, bizim koddan değil (SITL'in ilk derlemesinde de aynı CMake uyarısı vardı).

### 4.2 Flash (Pixhawk 6C)

| Ölçüm | FLASH (kullanılan / toplam) | Yüzde | Boş kalan |
|---|---|---|---|
| Modül yokken (aynı commit, değişiklikten önce) | 1 926 408 B / 1 966 080 B (1920 KB) | %97,98 | 39 672 B |
| Grup 1 sonu (modül + 16 parametre) | 1 931 164 B / 1 966 080 B (1920 KB) | %98,22 | 34 916 B (~34 KB) |
| **Artış** | **+4 756 B (~4,6 KB)** | +0,24 puan | |

- Modülün kendi kodu ~4,0 KB (`AutoFollow.cpp` nesne dosyası, text 4058 B); kalanı parametre tablosu ve açıklama metinleri.
- RAM (AXI_SRAM): 61 964 B → 62 028 B (+64 B).
- Kodda `double` yok. Dinamik bellek yalnızca bir yerde: modül başlarken kendi nesnesini bir kez oluşturur (`new AutoFollow()`, PX4'ün bütün modüllerindeki `ModuleBase` deseni; durdurulunca PX4 siler). Çevrim içinde bellek ayrılmaz (`error-handling.md:7` "başlatma sonrası" kuralına uygun).

### 4.3 SITL duman testi (Gazebo Harmonic 8.15, `gz_x500`, `HEADLESS=1`, araç arm edilmedi)

Her koşudan önce `build/px4_sitl_default/rootfs/parameters*.bson` silindi. SITL arka planda çalıştırıldı, komutlar PX4'ün konsol istemcisiyle verildi (`build/px4_sitl_default/bin/px4-auto_follow status`, `px4-work_queue status`, `px4-commander status`, `px4-param show`, `px4-listener`). Testten sonra bütün px4 ve gz süreçleri kapatıldı ve parametre dosyası yine silindi.

**Koşu A: `PX4_PARAM_AF_ENABLE=1 HEADLESS=1 make px4_sitl gz_x500`**

| Kontrol | Görülen | Sonuç |
|---|---|---|
| Modül açılışta kendiliğinden başladı mı? | Konsolda `INFO [auto_follow] mode 'AUTO FOLLOW' registered: nav_state 23, arming check id 0` | Geçti |
| `auto_follow status` | `registered, nav_state 23, arming check id 0` · `mode active: no, landed: yes` · çevrim aralığı ortalama ~19,7–20,0 ms | Geçti |
| `commander status` | `External Mode 1: nav_state: 23, name: AUTO FOLLOW` | Geçti |
| `work_queue status` | `wq:nav_and_controllers` altında `auto_follow 50.1 Hz 19979 us (20000 us)` | Geçti |
| `param show AF_*` | 16 parametre, varsayılanlar spec Bölüm 10 ile aynı; `AF_ENABLE` = 1 | Geçti |
| Arming check cevabı (`listener arming_check_reply`) | `mode_req_angular_velocity/attitude/local_alt/local_position` = True; `global_position`, `home_position`, `mission`, `manual_control` = False; `prevent_arming` = True; `can_arm_and_run` = **False** (drone yerde, mod aktif değil → A14 beklenen) | Geçti |
| PX4 cevapları kabul ediyor mu? | Konsolda "unresponsive" / "No response" uyarısı yok (normal çalışmada) | Geçti |
| Mod seçilebilir mi? (`listener vehicle_status`) | `can_set_nav_states_mask`'ta bit 23 = 1 | Geçti |
| `auto_follow stop` | Komut 0,23 s'de döndü; hemen ardından `commander status`'ta dış mod yok; "unresponsive" uyarısı yok | Geçti (düzeltmeden sonra; bkz. sorun 2) |
| `auto_follow start` (yeniden) | Yine `nav_state 23` aldı (PX4 adın hash'iyle aynı slotu verdi; `COM_MODE0_HASH` dolu) | Geçti |

**Koşu B: `HEADLESS=1 make px4_sitl gz_x500` (`PX4_PARAM_AF_ENABLE` verilmedi)**

| Kontrol | Görülen | Sonuç |
|---|---|---|
| Modül başladı mı? | `auto_follow status` → `not running`; konsolda `auto_follow` satırı yok | Geçti (başlamadı) |
| `AF_ENABLE` | 0 (varsayılan) | Geçti |
| `commander status` | Dış mod yok | Geçti |
| `work_queue status` | `auto_follow` yok | Geçti |

### 4.4 Bu grupta test edilmeyenler (Grup 4 ön kontrollerine kaldı)

QGC'de mod listesinde görünmesi, disarm iken moda geçiş ve bu modda arm reddi, yerde arm'lıyken moda geçiş reddi ve QGC mesajı, RC anahtarı ve çubukla geçişler. Görev tanımı gereği araç bu testte arm edilmedi ve QGC bağlanmadı.

## 5. Kod içinde verilen küçük kararlar (yeni ad ya da davranış değil)

- `arming_check_reply` mesajında spec listesinde geçmeyen iki alan (`mode_req_local_position_relaxed`, `mode_req_global_position_relaxed`) **false** kalır: mesaj sıfırla başlatılır, "gerekmiyor" demektir. Bu modda zaten daha sıkı olan `mode_req_local_position` = true. (`mc_nn_control` cevabı sıfırlamadan doldurduğu için bu alanlar orada rastgele kalabiliyor; bizde bu yok.)
- Kontrol bayraklarında `flag_multicopter_position_control_enabled` = true (şema `planning/visuals/02-px4-detayli-akis.md` (A) ile aynı). Commander bu bayrağı zaten kendisi yeniden hesaplıyor (`Commander.cpp:2603-2617`).
- Kayıt silmede `mode_executor_id = -1` (şema (A): "executor yok"). `mc_nn_control` bunu 0 bırakıyor.
- Kayıt reddedilirse konsola bir kez `PX4_ERR`, yeniden deneme yok (şema (A) "Kayıt başarısız" kutusu). Şemadaki "QGC uyarısı events ile (öneri)" bu grupta yapılmadı.
- `vehicle_land_detected` hiç gelmemişse "yerde değil" kabul edilir (mesajın boş hali). PX4 multikopterde `land_detector`'ı her açılışta başlatıyor (`rc.mc_apps:38`); SITL'de mesaj geldi (`landed: yes`).
- `module.yaml` açıklamaları İngilizce yazıldı (PX4 geleneği; QGC parametre ekranında görünür). Ondalık basamak (`decimal`) değerleri, varsayılan ve sınırların QGC'de tam görünmesine göre seçildi (ör. `AF_BETA` 0.17 için 2 basamak).
- `AF_ENABLE` tipi tam sayı (`int32`), 0–1, "değişince yeniden başlatma gerekir" işaretli. Modül bu parametreyi okumaz; yalnızca açılış dosyası okur.

## 6. Çıkan sorunlar ve çözümleri

1. **İlk SITL derlemesi hata verdi:** `uORB::SubscriptionInterval` için gereken başlık dosyası eklenmemişti. Eklendi, derleme geçti.
2. **`auto_follow stop` kaydı silmiyordu.** İlk denemede modül durdurulunca mod hemen kalkmadı; ~1,2 s sonra konsolda `No response from 0, flagging unresponsive` göründü ve mod, PX4'ün "cevap vermeyen mod" yolu üzerinden kalktı. `listener unregister_ext_component` "never published" dedi.
   - **Neden:** Modül "kaydımı sil" mesajını yayınlayıp hemen kapanıyordu. PX4'te yayıncı nesnesi silinince konusu "yayınlanmıyor" diye işaretleniyor (`platforms/common/uORB/Publication.hpp:65-72`) ve bu durumda okuyucu yeni mesajı göremiyor (`platforms/common/uORB/uORBManager.hpp:453`). Commander bir sonraki turunda mesajı okuyamadan mesaj kayboluyordu. `mc_nn_control`'de de aynı kalıp var (`mc_nn_control.cpp:438-445`).
   - **Çözüm:** Modül, "kaydımı sil" mesajından sonra PX4 modu listeden kaldırana kadar çalışmaya devam eder, sonra kapanır. Kaldırıldığını `vehicle_status.can_set_nav_states_mask`'taki mod bitinden anlar (bu bit yalnızca kayıtlı modlar için 1, `ModeManagement.cpp:636-652`). En fazla 1 s bekler; commander `vehicle_status`'u en az saniyede 2 kez yayınladığı için (`Commander.cpp:1930-1931`) bu yeterli. Araç arm'lıyken (6C'de `COM_MODE_ARM_CHK` = 0) PX4 silme isteğini zaten işlemez; o durumda 1 s sonra kapanır ve PX4 modu "cevap vermiyor" sayar (şema (C)'de önceden yazılı davranış).
   - **Ara hata:** Çözümün ilk hâlinde `valid_nav_states_mask` kullanıldı; bu maskede dış mod bitleri kayıt olmasa da 1 kalıyor (`ModeManagement.cpp:648-652`), modül hep 1 s bekledi. `can_set_nav_states_mask`'a geçildi; durdurma 0,23 s'ye indi.
   - Not: Bu yüzden şema (A)'daki "Kayıt silme … ardından `exit_and_cleanup()`" kutusu artık "… PX4 kaydı kaldırana kadar (en fazla 1 s) bekle, sonra `exit_and_cleanup()`" diye okunmalı; şemanın (A) notlarına bir satır eklendi.
3. **SITL'de `COM_MODE_ARM_CHK` = 1.** Spec "kayıt yalnızca disarm iken kabul edilir, `COM_MODE_ARM_CHK` varsayılan 0" diyor; bu 6C için doğru (`commander_params.c:1048`). SITL ise bu parametreyi 1 yapıyor (`ROMFS/px4fmu_common/init.d-posix/px4-rc.simulator:8`), yani **SITL'de arm iken de kayıt kabul edilir**. Bizim davranışımızı değiştirmez; ama Grup 4'te "arm iken kayıt reddi" SITL'de görülemez, gerçek kartta görülür. Spec Bölüm 1'e not düşüldü.
4. **SITL'de `shutdown` komutu takılıyor.** `px4-shutdown` "Exiting NOW." yazıp PX4 sürecini kapatamıyor. Modül **kapalıyken** (Koşu B) de aynısı oldu; yani bizim modülle ilgili değil, PX4/Gazebo tarafında var olan bir durum. Süreçler PID ile kapatıldı. Grup 4'te test oturumlarını kapatırken bu bilinmeli.
5. **Kendi kabuğumu öldürdüm:** SITL'i kapatırken `pkill -f "gz sim"` komutu, aynı metni içerdiği için komutu çalıştıran kabuğun kendisini de eşledi. Sonraki kapatmalarda `pgrep -f "[g]z sim"` kalıbı ve PID kullanıldı. Hiçbir dosya etkilenmedi.
6. **`perf` çevrim süresi SITL'de 0 µs görünüyor.** SITL "lockstep" zamanla çalıştığı için çevrim içinde zaman ilerlemiyor; commander'da da aynı. Gerçek kartta anlamlı değer verir. Çevrim aralığı sayacı (`interval`) doğru: ~20 ms.

## 7. Kullanıcıya sorulacaklar (bu grupta açık kalan)

1. **QGC'deki parametre grubu adı.** `module.yaml` her parametre için bir grup adı ister; QGC'nin parametre ekranında başlık olarak görünür. Kaynaklarda bu ad yok. Derleme için şimdilik **`AUTO FOLLOW`** (zaten kararlaştırılmış mod adı) yazıldı; **onay bekliyor**. Seçenekler:
   - a) `AUTO FOLLOW` (şu anki): mod adıyla aynı, kolay bulunur. Eksi: QGC'de Follow Me'nin `Follow target` grubuna yakın görünebilir (uyarıdaki karışıklık riski).
   - b) `Auto Follow`: PX4'ün diğer gruplarıyla aynı yazım (ör. `Multicopter Position Control`). Eksi: mod adından farklı yazım.
   - c) `auto_follow`: modül adıyla aynı. Eksi: QGC'de diğer gruplardan farklı görünür.
   - Öneri: **a**. Değiştirmek yalnızca `module.yaml`'daki bir satırdır; parametre adlarını, mod numarasını ve logları etkilemez.
2. **Yeni dosyalardaki lisans başlığı.** PX4 ağacındaki dosyaların geleneği olan BSD-3 başlığı "Copyright (c) 2026 PX4 Development Team" ile yazıldı. Ekip/tez adına farklı bir sahiplik satırı istenirse değiştirilir (davranışı etkilemez).
3. **`module.yaml` açıklama dili.** İngilizce yazıldı (PX4 geleneği). QGC'de Türkçe görünsün istenirse çevrilir; uzun metin flash'ı biraz artırır.

## 8. Sonraki grup için notlar

- Grup 2 (guidance + log mesajı) "mod aktif mi" kapısının arkasına girecek. `Run()` erken dönüş yapmadan yazıldı: kayıt beklerken de çevrim sonuna kadar gider, böylece Grup 2'deki `auto_follow_status` yayını PASIF'te ve kayıt yokken de (`mode_nav_state` = 0) yapılabilir.
- `_trk_ang_rad` ve `_min_dep_rad` hazır; diğer parametreler `_param_af_*` adlarıyla okunur.
