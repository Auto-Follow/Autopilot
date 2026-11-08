# Task Group 1: Baseline Kopyaları ve PWM Zinciri Kaynak Doğrulaması

Tarih: 2026-10-18. Kaynak ağacı: `tez-base-1.17.0-14-g503566a6bc`. `git diff --quiet v1.17.0 HEAD -- src boards ROMFS Tools` boş çıktı verdi, yani doğrulanan satırlar v1.17.0 ile aynıdır. `build/px4_fmu-v6c_default/parameters.xml` 2026-09-29 21:29 tarihli derleme çıktısıdır.

## 1. Baseline kopyaları

`S=/tmp/claude-1000/-home-yusuf-Desktop-Projects-Auto-Follow-Autopilot/4b91b3e4-86c9-4515-ad60-66129800d8c8/scratchpad`

| Repo dosyası | Baseline kopyası | Boyut | sha256 |
|---|---|---|---|
| `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/diagrams/01-ust-seviye-akis.md` | `$S/baseline-fc/01-ust-seviye-akis.md` | 3079 | `5c67ac358166ef5a8969c578786c275797579e668f18b244f3cb1769edb7743b` |
| `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/diagrams/02-px4-detayli-akis.md` | `$S/baseline-fc/02-px4-detayli-akis.md` | 78780 | `0a750a265a5176a238ebc8c194515a347ca51609e317f0854f977dce9860d697` |

- Kopyalar `cp` ile (`-p` olmadan) alındı. Kopya mtime: `2026-10-18 15:40:41.049 +0300`. Bu, 6.8'deki `find -newer` kontrolünün referansıdır. Örnek: `find <repo> -newer $S/baseline-fc/01-ust-seviye-akis.md -type f`.
- Kopyalama anında repo dosyalarının mtime değerleri: Şema 1 `2026-10-18 13:39:25 +0300`, Şema 2 `2026-10-18 14:40:30 +0300`.
- `cmp` iki dosya için de fark bulmadı.

### Baseline MPE parse sonucu

Döküm dosyaları `$S/baseline-fc-inspect-01-ust-seviye-akis.txt` ve `$S/baseline-fc-inspect-02-px4-detayli-akis.txt` altındadır. Her iki çalıştırmanın çıkış kodu 0'dır.

| Dosya / blok | Sonuç | Node | Kenar | Subgraph |
|---|---|---|---|---|
| Şema 1, blok 1 | PARSE OK | 16 | 15 | 2 (`piBox`, `fcBox`) |
| Şema 2, blok 1 (A) | PARSE OK | 47 | 56 | 4 |
| Şema 2, blok 2 (B) | PARSE OK | 56 | 72 | 4 |
| Şema 2, blok 3 (C) | PARSE OK | 61 | 73 | 4 |
| Şema 2, blok 4 (D) | PARSE OK | 49 | 63 | 7 |

- Şema 2'de `tbd` sınıflı node sayısı 7'dir: `aPre`, `bIcd`, `bAltTbd`, `bGuidTbd`, `bSpTbd`, `cTimeTbd`, `dPerson`. Beklenen değerle aynıdır.
- Şema 1'de `tbd` sınıflı iki node vardır: `icdMsg`, `inAlt`.
- Baseline (B) içinde `bEsc` (`bCtl` üyesi) ve `bAlloc -> bEsc "actuator_motors"` kenarı bulunur. "Kontrolcü zinciri" notunda (Şema 2 satır 435) "(pwm_out, dshot ve gz_bridge `MixingOutput` kullanır)" ifadesi vardır.

## 2. PWM zinciri ad envanteri

Etiketler şunlardır. **doğrulandı**: v1.17.0 kaynağında satırıyla görüldü. **(build çıktısı)**: yalnızca `build/` altındaki üretilmiş dosyada görüldü, satır numarası derlemeye bağlıdır. **(doğrulanacak)**: kaynaktan kanıtlanamaz veya donanıma ya da kullanıcı kurulumuna bağlıdır.

### mixer_module ve FunctionMotors

| Ad / ifade | Durum | Kaynak |
|---|---|---|
| `MixingOutput::update()`: fonksiyon güncellemesi, armed değilse çıkış = NAN | doğrulandı | `src/lib/mixer_module/mixer_module.cpp:440-575` (başlık `:421`, `_function_allocated[i]->update()` `:441`, `_armed.armed` `:460`, NAN `:464`/`:470`, `limitAndUpdateOutputs` çağrısı `:480`) |
| `limitAndUpdateOutputs`: kill/lockdown → disarmed değer (`PWM_MAIN_DISn`) | doğrulandı | `mixer_module.cpp:489`, `:491-495` |
| `limitAndUpdateOutputs`: termination → `actualFailsafeValue` (`PWM_MAIN_FAILn`) | doğrulandı | `mixer_module.cpp:497-501` |
| `limitAndUpdateOutputs`: normal → `output_limit_calc` | doğrulandı | `mixer_module.cpp:505` |
| `output_limit_calc_single`: NAN → disarmed, motor için [-1,1] → `MIN`..`MAX` doğrusal ölçek | doğrulandı | `mixer_module.cpp:535-576` (`:538-539`, `:570-571`) |
| Sürücü çağrısı `_interface.updateOutputs(...)` | doğrulandı | `mixer_module.cpp:527` |
| `actuator_outputs` yayını sürücü çağrısından **sonra** yapılır, yalnızca `updateOutputs` true dönerse | doğrulandı | `mixer_module.cpp:527-529`, yayın fonksiyonu `:666-675` (`_outputs_pub.publish` `:675`, kapanış `:676`) |
| `<prefix>_FUNCn` / `DISn` / `MINn` / `CENTn` / `MAXn` / `FAILn`, `<prefix>_REV` | doğrulandı | `mixer_module.cpp:117`, `:119`, `:121`, `:123`, `:125`, `:127`, `:131` (aralık `:117-131`) |
| `actualFailsafeValue`: FAIL = varsayılan ise fonksiyonun failsafe değeri, değilse param değeri | doğrulandı | `mixer_module.cpp:690-706` (fonksiyon `:691-710`, `UINT16_MAX` testi `:696`, `defaultFailsafeValue` `:700`, param değeri `:706`) |
| `FunctionMotors`: `actuator_motors` aboneliği | doğrulandı | `src/lib/mixer_module/functions/FunctionMotors.hpp:52` |
| `FunctionMotors`: `THR_MDL_FAC` (thrust factor) eğrisi | doğrulandı | `FunctionMotors.hpp:53`, `:65`, `:83-107`. Param bağlantısı `mixer_module.cpp:270`, `mixer_module.hpp:300` |
| `FunctionMotors`: [0,1] → [-1,1], reversible olmayan motorda negatif → NAN | doğrulandı | `FunctionMotors.hpp:109-118` (`:115-116`). Spec aralığı `:52-118`, `updateValues` `:120`'de kapanır |
| `THR_MDL_FAC` varsayılanı 0 | doğrulandı | `src/lib/mixer_module/motor_params.c:57` |
| Motor1..12 = 101..112, Disabled = 0 | doğrulandı | `src/lib/mixer_module/output_functions.yaml:10-12` (`start: 101`, `count: 12`), `:5` (`Disabled: 0`) |

### px4io, kart ve başlatma

| Ad / ifade | Durum | Kaynak |
|---|---|---|
| px4io `MixingOutput` öneki `PWM_MAIN` | doğrulandı | `src/drivers/px4io/px4io.cpp:227` |
| `PX4IO::updateOutputs` → `io_reg_set(PX4IO_PAGE_DIRECT_PWM, ...)`, atanmamış kanala 0 | doğrulandı | `px4io.cpp:363-378` (`:367-369`, `:375`, `return true` `:378`) |
| `module.yaml`: `param_prefix: PWM_MAIN`, DIS 1000 / MIN 1000 / MAX 2000, protokol OneShot / PWM 50/100/200/400 Hz, varsayılan 400, DShot yok | doğrulandı | `src/drivers/px4io/module.yaml:5`, `:10-12`, `:22-28` (dosyada "DShot" geçmez) |
| PX4IO seri hattı `/dev/ttyS4` (USART6), 1.5 Mbps | doğrulandı | `boards/px4/fmu-v6c/src/board_config.h:59-72` (`:62`, `:72`) |
| V6C10 / V6C11 "NO PX4IO" | doğrulandı (kaynak) / kullanıcının kartı (doğrulanacak) | `board_config.h:149-150`. Ek kaynak: `boards/px4/fmu-v6c/src/manifest.c:89-100`, `:108-109` (PX4IO `present = 0`) |
| `CONFIG_DRIVERS_PX4IO=y` | doğrulandı | `boards/px4/fmu-v6c/default.px4board:32` |
| `CONFIG_BOARD_IO` = `px4_io-v2_default` | doğrulandı | kök `Kconfig:81-84` (`boards/px4/fmu-v6c/Kconfig` yok) |
| IO'lu kartta FMU çıkışları `PWM_AUX` öneki alır | doğrulandı | `src/lib/parameters/CMakeLists.txt:91-93`, `Tools/module_config/generate_params.py:53-67` |
| `px4io start` | doğrulandı | `ROMFS/px4fmu_common/init.d/rcS:414` (`px4io supported` kapısı `:389`) |
| `dshot start`, `pwm_out start` (AUX, çizilmez) | doğrulandı | `rcS:478-479` |
| 4019_x500_v2 `PWM_*_FUNC` ataması yapmaz | doğrulandı | `ROMFS/px4fmu_common/init.d/airframes/4019_x500_v2:1-36` (yalnızca `IMU_GYRO_CUTOFF`, `MC_*RATE_*`, `CA_ROTOR*`). Çağırdığı `rc.mc_defaults` içinde de yok |
| MAIN 1–4 ↔ motor sırası | (doğrulanacak) | Kaynakta kanıt yok, donanım kablolamasına bağlı |
| `PWM_MAIN_FUNC1..4 = 101..104` atamasının QGC Actuators sekmesinde elle yapılması | (doğrulanacak) | Kullanıcı kurulumu. Kaynakta tek kanıt: varsayılan 0, 4019 ayarlamaz |

### Parametre varsayılanları (build çıktısı)

`build/px4_fmu-v6c_default/parameters.xml`. Satır numaraları derlemeye bağlıdır, şemaya "(build çıktısı)" etiketiyle yazılır.

| Parametre | Varsayılan | Satır | Durum |
|---|---|---|---|
| `PWM_MAIN_FUNC1` | 0 (Disabled). Değer listesinde Motor 1..4 = 101..104 | `:2166` | (build çıktısı) |
| `PWM_MAIN_TIM0` (MAIN 1-2) | 400 | `:2783` | (build çıktısı) |
| `PWM_MAIN_TIM1` (MAIN 3-4) | 400 | `:2796` | (build çıktısı) |
| `PWM_MAIN_TIM2` (MAIN 5-8) | 400 | `:2809` | (build çıktısı) |
| `PWM_MAIN_DIS1` | 1000 ("set when not armed") | `:2054` | (build çıktısı) |
| `PWM_MAIN_MIN1` | 1000 | `:2718` | (build çıktısı) |
| `PWM_MAIN_MAX1` | 2000 | `:2670` | (build çıktısı) |
| `PWM_MAIN_FAIL1` | -1 ("When set to -1 (default), the value depends on the function") | `:2110`, açıklama `:2113` | (build çıktısı) |
| `THR_MDL_FAC` | 0.0 | `:14363` | (build çıktısı). Kaynak satırı `motor_params.c:57` doğrulandı |

- `PWM_MAIN_FUNC9` ve `PWM_MAIN_TIM3` yoktur, yani MAIN 1–8. `PWM_AUX_FUNC1` (`:1360`) ve DShot seçenekli `PWM_AUX_TIM0` (`:2009`) vardır. Bu, "MAIN = px4io (DShot yok), AUX = FMU" ayrımını doğrular.

### SITL yan notu

| Ad / ifade | Durum | Kaynak |
|---|---|---|
| `SIM_GZ_EC_FUNC1..4 = 101..104` | doğrulandı | `ROMFS/px4fmu_common/init.d-posix/airframes/4001_gz_x500:35-38` |
| `SIM_GZ_EC_MIN1..4 = 150` | doğrulandı | `4001_gz_x500:40-43` |
| `SIM_GZ_EC_MAX1..4 = 1000` | doğrulandı | `4001_gz_x500:45-48` |
| `SIM_GZ_EC` öneki | doğrulandı | `src/modules/simulation/gz_bridge/module.yaml:13` |
| gz_bridge aynı `MixingOutput`'u kullanır | doğrulandı | `src/modules/simulation/gz_bridge/GZMixingInterfaceESC.hpp:81` |
| Çıkış PWM değil motor hızıdır (`gz::msgs::Actuators` velocity, `/<model>/command/motor_speed`) | doğrulandı | `GZMixingInterfaceESC.cpp:48`, `:80-88` |

## 3. Kalıcı "(doğrulanacak)" maddeleri

- IO'suz V6C10 / V6C11 sürümleri: kaynakta "NO PX4IO" doğrulandı, ama kullanıcının kartının hangi sürüm olduğu bilinmiyor. Kartta IO olduğu varsayılır.
- MAIN 1–4 ↔ motor sırası.
- QGC Actuators ataması (`PWM_MAIN_FUNC1..4 = 101..104`).
- `PWM_MAIN_FAIL` = -1 anlamı ("fonksiyonun varsayılan failsafe değeri"). Kaynak bunu destekler (bkz. 4. bölüm). Etiket, `tasks.md` 1.6 gereği şemada "(doğrulanacak)" olarak kalır.

## 4. Spec ↔ kaynak farkları ve ek bulgular

Hiçbir spec satır numarası kaynakla çelişmiyor. Bütün aralıklar spec'te yazan içeriği gösteriyor. Düzeltme gerekmez. Bilgi amaçlı küçük notlar:

1. `mixer_module.cpp:440-575`: `update()` başlığı `:421`'de, `output_limit_calc_single` kapanışı `:576`'dadır. Aralık, ilgili satırların hepsini (`:441`–`:574`) kapsar, değiştirmeye gerek yoktur.
2. `FunctionMotors.hpp:52-118`: `updateValues` `:120`'de kapanır. İçerik aralık içindedir.
3. `mixer_module.cpp:690-706`: `actualFailsafeValue` `:691-710`'dur. Belirleyici satırlar `:696-706` aralıktadır.
4. "armed değil → disarmed" iki yerde görülür. Birincisi `update()` NAN → `output_limit_calc_single` `:538-539` yoludur (spec aralığında). İkincisi `output_limit_calc` OFF durumudur (`mixer_module.cpp:578-663`, OFF `:633-638`), bu aralık spec listesinde yoktur. TG3 isterse `:578-663` aralığını ekleyebilir. Zorunlu değildir.
5. `PWM_MAIN_FAIL` = -1 kaynakta şöyle çözülür: `_failsafe_value` `uint16_t`'dir (`mixer_module.hpp:244`), -1 değeri 65535 = `UINT16_MAX` olur (`mixer_module.cpp:194`, `:696`). Sonra `defaultFailsafeValue` çağrılır. `FunctionMotors` bunu override etmez, taban sınıf NAN döner (`FunctionProviderBase.hpp:64`). NAN → `output_limit_calc_single` → disarmed değer (`:538-539`). Yani motorlarda termination çıkışı fiilen `PWM_MAIN_DIS` (1000) olur. `parameters.xml:2174` ("'Disarmed' for the rest") bunu doğrular. Etiket yine de 1.6 gereği "(doğrulanacak)" kalır.
6. MAIN 1–4 hızı tek bir `PWM_MAIN_TIMx` değildir. `PWM_MAIN_TIM0` MAIN 1-2'yi, `PWM_MAIN_TIM1` MAIN 3-4'ü yönetir (`parameters.xml:2784`, `:2797`). Spec'teki "`PWM_MAIN_TIMx`" yazımı doğrudur. Şemada istenirse "TIM0/TIM1" diye açılabilir.
7. px4io `MixingOutput` ramp-up açıktır (`mixer_module.hpp:122` varsayılan `ramp_up = true`, `px4io.cpp:227`). Arm'dan sonra 500 ms boyunca disarmed değerden hedefe rampa yapılır (`mixer_module.cpp:582`, `:640-654`). gz_bridge'de ramp kapalıdır (`GZMixingInterfaceESC.hpp:81`). Spec'te yoktur, eklenmesi zorunlu değildir.
8. px4io da `MixingOutput` kullanır (`px4io.cpp:227`). Mevcut "Kontrolcü zinciri" notu yalnızca pwm_out, dshot ve gz_bridge'i sayar. Bu ifade spec gereği korunur, px4io yeni "PWM zinciri" maddesinde yer alır.
9. Requirements'taki `Kconfig:81-84`, kök `Kconfig` dosyasıdır. Kart klasöründe `Kconfig` yoktur. Bu satır spec'in not listesinde yoktur, bilgi amaçlıdır.
10. V6C10/V6C11 için ek kaynak: `boards/px4/fmu-v6c/src/manifest.c:108-109` (PX4IO `present = 0`, `:89-94`). `rcS:389` (`px4io supported`) bu manifest'e bağlıdır.

## 5. Grup 1 kontrol sonuçları (K1–K5)

Betik `$S/tg1_checks.sh` (salt okunur), çıktısı `$S/tg1_checks.out`. Sonuç: 108 PASS, 0 FAIL, çıkış kodu 0.

| Kontrol | Sonuç |
|---|---|
| K1: iki baseline kopyası var ve `cmp` ile repo dosyalarıyla birebir aynı | PASS |
| K2: 13 kaynak yolu mevcut (`parameters.xml` dahil) | PASS |
| K3: mixer_module, FunctionMotors, px4io, `module.yaml`, board_config ve px4board satırları beklenen içeriği gösteriyor | PASS |
| K4: `PWM_MAIN_FUNC1`=0, `TIM0..2`=400, `DIS1`=1000, `MIN1`=1000, `MAX1`=2000, `FAIL1`=-1, `THR_MDL_FAC`=0 (`motor_params.c:57`), Motor1..4 = 101..104 | PASS |
| K5: 4019'da (ve `rc.mc_defaults`'ta) `PWM_*_FUNC` yok. `4001_gz_x500:35-48` FUNC 101..104 / MIN 150 / MAX 1000. `rcS:414` `px4io start` | PASS |
| Ek: kaynak ağacı v1.17.0 ile aynı. `git status` yalnızca `?? agent-os/specs/` | PASS |
