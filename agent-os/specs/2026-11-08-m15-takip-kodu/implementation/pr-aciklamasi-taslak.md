# PR açıklaması taslağı (M15)

> **Durum:** taslak (görev 6.18). **Push ve PR açılmadı**; kullanıcı isteyince açılır. Aşağıdaki "PR başlığı" ve "PR açıklaması" kısımları GitHub'a olduğu gibi yapıştırılmak içindir. Dal: `ozellik/m15-takip-kodu` (Autopilot) → `main`.

## PR başlığı

```text
[M15] AUTO FOLLOW: body FRD LOS'tan PX4 setpoint'ine takip modu (external mode)
```

## PR açıklaması

````markdown
## Ne yapıldı?

PX4 v1.17.0'a **AUTO FOLLOW** adlı bir uçuş modu eklendi (yol haritası m15, issue #6). Raspberry Pi'nin gönderdiği "hedef drone'a göre şu yönde" bilgisi (MAVLink 2 `DEBUG_FLOAT_ARRAY`, ad `AF_LOS`: body FRD LOS birim vektörü + yaş + sıra no + hedef var/yok) Pixhawk'ta 9 kontrolden geçirilir, düz zemin kabulüyle hedefin yeri bulunur, alpha-beta filtresiyle yumuşatılır ve hız tabanlı bir kuralla PX4'e `trajectory_setpoint` (yatay hız + sabit irtifa + mutlak yaw) verilir. Hedef kaybolunca drone önce yerinde bekler (0,5 s), 1,0 s içinde hedef dönmezse PX4'ten Hold ister ve takibe kendiliğinden dönmez. Modun her iç durumu kendi log mesajı `auto_follow_status` ile her logda kaydedilir.

- **Entegrasyon yaklaşımı:** external mode modülü (`mc_nn_control` kalıbı); kontrolcü yazılmadı, hızdan PWM'e zincir PX4'ün.
- **Açma:** `AF_ENABLE` = 1 + reboot (varsayılan 0: ilk yüklemede mod görünmez). Mod QGC'de `AUTO FOLLOW` adıyla, `nav_state` 23–30 aralığından (SITL'de 23) görünür. PX4'ün kendi Follow Me'si (`nav_state` 19) ile ilgisi yoktur.
- **Parametreler:** 17 adet `AF_*` (QGC grubu `AUTO FOLLOW`).
- **Spec ve dokümanlar:** `agent-os/specs/2026-11-08-m15-takip-kodu/` (`spec.md`, `rapor.md`, `log-sozlugu.md`, `tasks.md`, `implementation/grup-0..6-*.md`).

## PX4'e eklenen / değişen dosyalar (kabul kriteri 6)

Yeni dosyalar:
- `src/modules/auto_follow/AutoFollow.cpp`, `AutoFollow.hpp` — modül: kayıt, 50 Hz çevrim, setpoint, Hold isteği, log
- `src/modules/auto_follow/AutoFollowGuidance.cpp`, `AutoFollowGuidance.hpp` — doğrulama, geometri, guidance, sınırlar, durum makinesi (ayrı kütüphane)
- `src/modules/auto_follow/AlphaBetaFilter.hpp` — alpha-beta filtresi
- `src/modules/auto_follow/AutoFollowGuidanceTest.cpp` — birim testi (12 test, `make tests TESTFILTER=AutoFollowGuidance`)
- `src/modules/auto_follow/CMakeLists.txt`, `Kconfig`, `module.yaml` — derleme, açma ayarı, 17 parametre
- `msg/AutoFollowStatus.msg` — log mesajı (39 alan)

Değişen PX4 dosyaları (birer satır / blok):
- `boards/px4/sitl/default.px4board`, `boards/px4/fmu-v6c/default.px4board` — `CONFIG_MODULES_AUTO_FOLLOW=y`
- `msg/CMakeLists.txt` — `AutoFollowStatus.msg`
- `src/modules/logger/logged_topics.cpp` — `add_topic("auto_follow_status")`
- `ROMFS/px4fmu_common/init.d/rc.mc_apps` — `AF_ENABLE` = 1 ise açılışta `auto_follow start`

Tez araçları (izinli `tez/*`):
- `tez/sitl/af_los_gonder.py` — SITL test göndericisi (Pi'yi taklit eder; açık/kapalı çevrim, S4/S5 senaryoları, S6/S7 hedefi)
- `tez/analiz/af_log_analiz.py` + `tez/analiz/BENIOKU.md` — ULog analiz script'i ve rehberi

## Pixhawk 6C flash

`make px4_fmu-v6c_default`: **1 937 316 B / 1 966 080 B (%98,54)**, boş 28 764 B. Modül yokken 1 926 408 B (%97,98) → **+10 908 B**. Taşma yok; başka modül kapatılmadı.

## Test

- Birim testi: `make tests TESTFILTER=AutoFollowGuidance` → 12/12 (CI'da çalışmaz, yerelde).
- SITL (Gazebo Harmonic, `gz_x500`): ön kontroller, S1a–S5 (açık çevrim), S4 tam (Hold dahil), S6 (duran hedef, 5 başlangıç mesafesi), S7 (yürüyen hedef, L yolu, `AF_K_FF` 0 ve 1,0), batarya ve GPS arızası denemeleri. Her senaryo için "ne verildi, drone ne yaptı, ULog adı": `rapor.md` §4.9 ve `implementation/grup-4..6-*.md`. ULog'lar repoda değil.

## Kontroller

- Zorunlu CI: `verify-pin`, `derleme-sitl`, `derleme-fmu-v6c`.
- ⚠️ **`verify-pin` bu PR'da kırmızı olacak:** yukarıdaki 7 PX4 yolu (`src/modules/auto_follow/`, iki kart dosyası, `msg/AutoFollowStatus.msg`, `msg/CMakeLists.txt`, `logged_topics.cpp`, `rc.mc_apps`) henüz `tez/pin/allowed-paths.txt`'te değil. Repo sorumlusunun onayıyla izin listesi **ayrı bir PR**'la güncellenip birleşince yeşile döner. Yerelde `tez/pin/verify_pin.sh --worktree` yalnızca bu 7 yoldaki 15 dosyayı gösteriyor, başka yol yok.

## Notlar

- `agent-os/product/tech-stack.md:44` ("Takip modunun PX4'e entegrasyon yaklaşımı: Seçilmedi") için: **karar: external mode, güncellenmeli** (ürün planını repo sorumlusu günceller; çatı repoda ayrı PR).
- Gerçek uçuştan önce Pixhawk'ta `COM_LOW_BAT_ACT` = 3 önerilir (PX4 varsayılanı 0 = yalnızca uyarı; rapor §5.1 G5.14).

Closes Auto-Follow/Auto-Follow#6

🤖 Generated with [Claude Code](https://claude.com/claude-code)
````

## Taslakla ilgili notlar (PR'a girmez)

- Flash sayısı Grup 5 sorusu 3-b'den sonraki son ölçümdür (rapor §4.10); Grup 6'da PX4 kodu değişmedi. PR açılmadan önce CI'daki `derleme-fmu-v6c` çıktısıyla karşılaştırılır.
- `Closes Auto-Follow/Auto-Follow#6` çatı reponun issue'sunu kapatır (issue çatı repoda).
- PR açıklamasının sonundaki "Generated with Claude Code" satırı ajan talimatı gereği eklendi; kullanıcı istemezse silinir.
- Commit listesi PR'da GitHub'ın kendi listesinden görünür; squash merge yapılacağı için (çatı kural 3) ayrıca yazılmadı.
