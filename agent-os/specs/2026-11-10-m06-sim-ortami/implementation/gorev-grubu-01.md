# Görev Grubu 1 — (b) yolu: stok 4001, başlangıç parametreleri, F0 uyarlaması

- Tarih: 11.11.2026 · dal `ozellik/m06-sim-ortami` · taban commit `6ddbe1e45a` (bu grubun commit'i bunun üstüne gelir)
- Durum: **uygulandı ve test edildi.** Hüseyin'in (b) yolu ve iskelet modülün PR'dan çıkarılması için onayı hâlâ
  bekleniyor; grup tek ve ayrı bir commit olduğu için reddedilirse `git revert` ile geri alınabilir.

## Ne yapıldı

| Alt görev | Dosya | Özet |
|---|---|---|
| 1.1 | `tez/sim/testler/test_parametreler.py` (yeni), `test_hedef.py`, `test_kayit.py`, `test_rapor.py` | 7 yeni test fonksiyonu (14 test durumu) + `test_hedef.py`'ye 2 test ve 2 hata durumu; `Scenario` kurucusundaki `"tez"` → `"yok"` |
| 1.2 | `tez/sim/parametreler/gercek_dron.params`, `sim.params` (yeni) | 7 kazanç satırı (4019) + 7 davranış satırı (22.08) ve `SDLOG_PROFILE 163`; her satırda kaynak yorumu |
| 1.3 | `ROMFS/.../4030_gz_x500_tez`, `.post` (silindi), `ROMFS/.../airframes/CMakeLists.txt` (`main`'e döndü), `tez/px4/` (silindi) | `git diff --stat main -- ROMFS tez/px4` boş. İskelet modül `c4b4abf342`'de okunabilir |
| 1.4 | `tez/sim/araclar/parametreler.py` (yeni) | Ayrıştırma, birleştirme sırası, `PX4_PARAM_*` satırları, komut satırı girişi, `matches` (float32 toleranslı karşılaştırma) |
| 1.5 | `tez/sim/calistir.sh` | `PX4_SYS_AUTOSTART=4001`, `PX4_GZ_MODEL_NAME=x500_tez_0`, `PX4_GZ_WORLD`, `PX4_SIM_MODEL=x500_tez`; `--param AD=DEĞER` (çoklu); parametreler sim açılmadan kontrol edilir |
| 1.6 | `tez/sim/derle.sh` | `tez/px4/src/CMakeLists.txt` yoksa stok `px4_sitl_default`; önbellekteki `EXTERNAL_MODULES_LOCATION` farklıysa yeniden yapılandırma |
| 1.7 | `tez/sim/araclar/simulasyon.py`, `px4_baglanti.py` | Hazır satırı `"Startup script returned successfully"`; parametreler `calistir.sh`'a; "unresponsive" yalnız `external_mode=True`; `TEZ_MODE_NAME` kaldırıldı; `get_param`, `decode_param_value`, `FOLLOW_TARGET_MODE_NAME` |
| 1.8 | `hedef.py`, `senaryo.py`, `rapor.py`, `senaryolar/*.yaml` | `drone.mod` → `takip.kaynak` (yalnız `yok` → "Hold"); rapor ve `ozet.json` takip kaynağını yazar |
| 1.9 | `tez/sim/araclar/f0_testi.py` | Kamera + `SYS_AUTOSTART 4001` + 15 parametrenin geri okunması + "Hold"/"Follow Target" listede + 10 m kalkış + Hold'da 15 s + iniş + temiz kapanış |
| 1.10 | `tez/sim/README.md`, `tez/sim/ruff.toml`, `tez/sim/worlds/{duz_alan,cayir}.sdf` | İskelet modül ve ROMFS satırları çıktı, "(b) yolu" bölümü eklendi; `known-first-party`'ye `parametreler`; dünya dosyalarındaki "airframe 4030" yorumu düzeltildi |

## Kararlar ve gerekçeler

1. **Parametre yükleme yöntemi: rcS'in `PX4_PARAM_<AD>` döngüsü** (spec 1. madde). Doğrulandı: stok posix rcS bu
   değişkenleri `param reset_all`'dan sonra, airframe dosyasından önce `param set` ile yazıyor; `param set`
   değeri her zaman kullanıcı katmanına (`user_config`) yazıyor, `param set-default` ise yalnız varsayılan katmanını
   değiştiriyor (`src/lib/parameters/parameters.cpp`). Bu yüzden rcS'in sonraki `param set-default SDLOG_PROFILE 131`
   satırı bizim `163`'ümüzü ezmiyor (koşuda `param show SDLOG_PROFILE` → 163).
2. **Bulgu: `param set` varsayılana eşit değeri hiç yazmaz.** `src/systemcmds/param/param.cpp` `do_set`, yalnız
   `i != newval` iken `param_set` çağırıyor. Varsayılana eşit 7 davranış parametresi bu yüzden kullanıcı katmanına
   girmiyor (sim log'unda `curr -> new` satırı yalnız değeri farklı olan 8 parametre için çıkıyor). Böyle bir değeri
   sonradan bir `param set-default` satırı (ör. airframe) değiştirebilir; ör. `--param MPC_THR_HOVER=0.5` verilirse
   4001'in `param set-default MPC_THR_HOVER 0.60` satırı kazanır. Bugünkü dosyalarda böyle bir çakışma yok (F0: 15/15
   parametre PX4'te aynı), ama bu yüzden **F0 her değeri PX4'ten geri okur** ve spec 1. madde buna göre düzeltildi.
   Senaryo/komut satırı parametrelerinin de koşuda geri okunması 2. gruba (`ayarlar`) öneri olarak bırakıldı.
3. **Dosya biçimi biraz sıkılaştırıldı:** kaynak yorumu (`# kaynak`) zorunlu (yorum standardı: kazancın kaynağı
   yazılır); aynı dosyada aynı ad iki kez yazılırsa iki satır numarasıyla reddedilir. Dosyalar arası tekrar ise yükleme
   sırasının parçasıdır (sonuncu kazanır). Değerde `nan`/`inf` ve kelimeler reddedilir; tamsayı biçimi korunur (INT32
   parametreleri için).
4. **`calistir.sh` dışarıdan gelen `PX4_PARAM_*` değişkenlerini siler.** Kullanıcının kabuğunda kalmış bir değişken
   yükleme sırasını sessizce bozardı; tek yol `--param`. Parametre hatası Gazebo açılmadan, dosya/satır/ad ile verilir
   (denendi: `--param flw_tgt_dst=8` → çıkış kodu 2, süreç açılmadı).
5. **`derle.sh` yeniden yapılandırma bu grupta gerekti.** Mevcut `build/px4_sitl_tez`'in CMake önbelleğinde
   `EXTERNAL_MODULES_LOCATION=.../tez/px4` kayıtlıydı; klasör silinince `cmake --build` kırılırdı. `derle.sh` artık
   istenen değeri (`tez/px4/src/CMakeLists.txt` varsa o klasör, yoksa boş) önbellektekiyle karşılaştırıp farklıysa
   `-DEXTERNAL_MODULES_LOCATION=<değer>` ile yeniden yapılandırıyor. `--harici` bayrağı 10. grupta bunun üstüne gelir.
   Derleme sonrası: önbellekte değer boş, `rootfs/etc/init.d-posix/airframes`'ta 4030 yok, `bin/px4`'te
   `tez_auto_follow` yok.
6. **Hazır satırı** `"Startup script returned successfully"` (`platforms/posix/src/px4/common/main.cpp`): rcS
   bitmiş, PX4 dünyadaki drona bağlanmış ve modüller açılmış demek. `wait_ready` ayrıca "Unknown model",
   "gz_bridge failed" ve "Startup script returned with return value" satırlarında beklemeden `False` döner.
   Koşu başına hazır olma ~14 s'ye indi (eski satır, modülün kaydını bekliyordu).
7. **F0 stok modlara uyarlandı.** "Tez modunda yerde arm reddi" ve "unresponsive" kontrolleri çıktı (stok modda
   anlamsız; "unresponsive" yalnız `Simulation(external_mode=True)` ile, 10. grupta). Mod listesinde "Hold" ve
   "Follow Target" adla aranıyor; adlar PX4'ün `src/lib/modes/ui.hpp` `nav_state_names` tablosundan.
8. **`takip.kaynak` bu grupta yalnız `yok`.** `follow_me` ve `tez_los` "Görev grubu 6'da / 5'te bağlanacak" hatası
   verir (2.5'teki ara durum kuralıyla aynı biçim; sessizce yok sayılmaz). Eski `drone.mod`, "kaldırıldı; yerine
   `takip.kaynak`" mesajıyla reddedilir. Kodda `Scenario.drone_mode` → `Scenario.tracking_source`; `ozet.json`'a
   `takip_kaynagi` alanı eklendi (2. gruptaki `ayarlar` sözlüğüne taşınabilir).
9. **`PX4_SIM_MODEL=x500_tez`** (eski airframe `gz_x500_tez` kullanıyordu). `PX4_SYS_AUTOSTART` verildiği için rcS
   model adıyla airframe aramıyor; `px4-rc.gzsim` `PX4_GZ_MODEL_NAME` dolu olduğu için "bağlan" dalına giriyor.
10. **`Simulation` `calistir.sh`'a `TEZ_PYTHON` olarak kendi yorumlayıcısını verir** (kullanıcı başka birini
    seçmediyse); böylece `parametreler.py` aynı venv'de çalışır.

## 22.08 parametrelerinin v1.17.0 varsayılanlarıyla karşılaştırılması

Yöntem: tek seferlik betik (scratchpad'de, repoya girmedi). `22.08.2026.params` (QGC biçimi, gerçek araç, v1.17.0
`d6f12ad1c4`) satır satır okundu ve iki referansla karşılaştırıldı:
- **v1.17.0 meta verisi:** `build/px4_sitl_default/parameters.json` (derleme çıktısı; `build/px4_sitl_tez`'inkiyle
  bayt bayt aynı).
- **Stok 4001 SITL etkin varsayılanı:** meta veri + stok 4001 açılışında çalışan `param set-default` satırları
  (`init.d-posix/rcS`, `init.d/rc.mc_defaults`, `airframes/4001_gz_x500`, `px4-rc.simulator`). Simin gerçek araçtan
  farkı bu sütundan okunur.

Sayılar: 22.08 dosyasında 1109 parametre; 241'i SITL meta verisinde yok (donanıma özgü: `PWM_*`, `UAVCAN_*`, DShot,
sürücüler, seri port ayarları); meta varsayılandan farklı 120, stok 4001 SITL'den farklı 122.

**Dahil sınıfındaki farklar** (`MC_*`, `IMU_*_CUTOFF`, `MPC_*`, `FLW_TGT_*`, `EKF2_HGT_REF`, `EKF2_MAG_TYPE`):

| Parametre | 22.08 | v1.17.0 meta | stok 4001 SITL | 4019_x500_v2 | Karar |
|---|---|---|---|---|---|
| `IMU_GYRO_CUTOFF` | 30 | 40 | 40 | 30 | `gercek_dron.params` |
| `MC_ROLLRATE_P`, `MC_PITCHRATE_P` | 0.14 | 0.15 | 0.15 | 0.14 | `gercek_dron.params` |
| `MC_ROLLRATE_I`, `MC_PITCHRATE_I` | 0.3 | 0.2 | 0.2 | 0.3 | `gercek_dron.params` |
| `MC_ROLLRATE_D`, `MC_PITCHRATE_D` | 0.004 | 0.003 | 0.003 | 0.004 | `gercek_dron.params` |
| `MC_AT_EN` | 1 | 0 | 1 (rcS `set-default -s`) | — | Simde zaten 1; yazılmadı |

Sonuç: dahil sınıfında stok 4001 SITL'den farklı olan **yalnız 7 kazanç** var ve 22.08'deki değerleri 4019
airframe'iyle aynı. Spec "Başlangıç parametreleri" tablosu doğru çıktı; değişiklik gerekmedi.

**Gereksinimlerde adı geçen davranış parametreleri:** `FLW_TGT_HT 8`, `FLW_TGT_DST 8`, `FLW_TGT_ALT_M 0`,
`EKF2_HGT_REF 1`, `EKF2_MAG_TYPE 0`, `MPC_YAWRAUTO_MAX 60`, `MPC_TILTMAX_AIR 45`: üçünde de (22.08, meta, stok SITL)
aynı. İzlenebilirlik için `gercek_dron.params`'a yazıldı (spec kararı).

**Dahil olmayan farklar** (seçim kuralına göre alınmadı):

| Sınıf | Sayı | Örnekler |
|---|---|---|
| Hariç: kalibrasyon (`CAL_*`) | 52 | ivmeölçer, jiroskop, manyetometre, barometre ofset/ölçek ve kimlikleri |
| Hariç: RC (`RC*`) | 13 | `RC_MAP_*`, kanal uçları |
| Hariç: `CA_*` geometri | 11 | 4019'un ±1 rotor konumları (sim modeli 4001'in gerçek ölçülerini kullanır) |
| Hariç: failsafe | 10 | `NAV_DLL_ACT 1` (simde 2), `COM_RC_IN_MODE 0`, `COM_LOW_BAT_ACT 0`, `COM_RCL_EXCEPT 1`, `FD_FAIL_P/R 55`, `GF_MAX_HOR_DIST 100`, `GF_MAX_VER_DIST 20`, `RTL_RETURN_ALT 7`, `RTL_DESCEND_ALT 3` |
| Hariç: batarya (`BAT*`) | 7 | `BAT1_CAPACITY 5200`, eşikler |
| Hariç: model fiziği | 1 | `MPC_THR_HOVER` 0.5 (simde 4001'in 0.6'sı) |
| Hariç: senaryo verir | 1 | `MIS_TAKEOFF_ALT 5` |
| Hariç: `SENS_*`, `MAV_*` | 2 | `SENS_IMU_MODE 0`, `MAV_TYPE` |
| Kuralın listesinde yok | 26 | `IMU_INTEG_RATE` 200 (simde `px4-rc.simulator` 250), `EKF2_MULTI_IMU 3`, `EKF2_REQ_GPS_H` 10 (simde 0.5), `EKF2_MAG_DECL`, `COM_FLTMODE*`, `PWM_MAIN_FUNC*`, `SDLOG_*`, `SYS_AUTOSTART 4019`, `CBRK_USB_CHK`, `COM_CPU/RAM_MAX`, … |

Kullanıcıya not (karar gerekirse): kuralın dışında kalıp uçuş davranışına dokunabilecek birkaç fark var:
`IMU_INTEG_RATE` (200 ↔ 250), çoklu EKF (`EKF2_MULTI_IMU 3` + `SENS_IMU_MODE 0` ↔ simde tek EKF), geofence ve RTL
yükseklikleri. Spec'in seçim kuralı bunları bilerek dışarıda bırakıyor; değiştirmek kuralın değişmesini gerektirir.

## Test sonuçları

| Kontrol | Sonuç |
|---|---|
| `pytest tez/sim/testler/test_parametreler.py tez/sim/testler/test_hedef.py -q` | 45 geçti |
| `pytest tez/sim/testler -q` | 93 geçti (önceki 76 + 17), 1 uyarı (önceden de vardı) |
| `ruff format` + `ruff check` (`tez/sim/ruff.toml`, ruff 0.16.9) | temiz |
| `shellcheck tez/sim/calistir.sh tez/sim/derle.sh` | temiz |
| `git diff --stat main -- ROMFS tez/px4` | boş |
| `tez/pin/verify_pin.sh --worktree` (çalışma ağacında, commit'ten önce) | "KILIT BOZULMUS": betik yalnız commit'lenmiş durumu (`git diff BASE HEAD`) okur; HEAD hâlâ eski 3 ROMFS dosyasını taşıyor. Aynı betik, bu grubun bütün değişikliklerini içeren ve dala bağlanmayan bir aday commit nesnesiyle (`git commit-tree`, geçici indeks) koşuldu → **"KILIT SAGLAM"**. Commit'ten sonra gerçek betik de "KILIT SAGLAM" vermeli |
| `tez/sim/derle.sh` | geçti; CMake stok yapılandırmaya döndü (`EXTERNAL_MODULES_LOCATION` boş) |
| Elle duman testi: `calistir.sh --ekransiz --param MPC_XY_VEL_MAX=7` | `env SYS_AUTOSTART: 4001`, "PX4 will attach to existing model", `gz_bridge ... model: x500_tez_0`; "Unknown model" yok; `px4-param show` → `SYS_AUTOSTART 4001`, `IMU_GYRO_CUTOFF 30`, `MC_ROLLRATE_P 0.14`, `MC_PITCHRATE_D 0.004`, `FLW_TGT_* 8/8/0`, `EKF2_HGT_REF 1`, `EKF2_MAG_TYPE 0`, `MPC_YAWRAUTO_MAX 60`, `MPC_TILTMAX_AIR 45`, `SDLOG_PROFILE 163`, `MPC_XY_VEL_MAX 7`; temiz kapanış |
| `tez/sim/araclar/f0_kabul.sh` | **GEÇTİ** (1 dk 10 s): 2304×1296, 30.4 kare/sim-s, RTF 1.00, fx 1773.9; `SYS_AUTOSTART 4001`; 15/15 parametre; "Hold" + "Follow Target" listede; Hold'da 15 s, en büyük sapma yatay 0.05 m, dikey 0.07 m; iniş, disarm, temiz kapanış; sim log'unda "Unknown model" yok |
| `tez/sim/araclar/f1_kabul.sh` | **GEÇTİ** (3 dk 41 s): iki koşuda hedef doğrulama farkı en fazla 0.13 m (sınır 0.30); iki koşu arasında 0.000 m (sınır 0.15); takip kaynağı `yok`, mod "Hold" |

Koşu sonunda çalışan PX4/Gazebo süreci kalmadı (`pgrep -x px4`, `pgrep -f "^gz sim"` boş).

## Karşılaşılan sorunlar

- `verify_pin.sh --worktree` commit'ten önce yeşil olamaz (yukarıda). Görev listesindeki "bugün bu dalda KILIT
  BOZULMUS → KILIT SAGLAM" beklentisi commit'ten sonra gerçekleşir; commit'ten önce aday commit nesnesiyle
  doğrulandı.
- `tasks.md` 1.5 ve spec 8. madde `calistir.sh`'ta bir `--temiz` seçeneğinden söz ediyordu; `--temiz`
  `derle.sh`'ın seçeneğidir (`calistir.sh` zaten her açılışta parametreleri sıfırlar). Spec metni düzeltildi.
- `px4-shutdown` PX4 kapanırken 255 döndürüyor (istemci, sunucu kapanınca bağlantıyı kaybediyor); eski koşularda da
  aynıydı, `Simulation.stop` sonucu kontrol etmiyor, `calistir.sh` Gazebo'yu kapatıyor.

## Ek karar (11.11.2026): IMU_INTEG_RATE, RTL ve geofence

**IMU_INTEG_RATE: simde 250 Hz kalır.** Gerçek araçtaki 200, PX4'ün firmware varsayılanıdır (`imu_parameters.c`); kimse bilerek seçmemiştir. Gerçek Pixhawk 6C'de IMU çok daha hızlı örnekler, 200 Hz yalnız EKF'ye giden entegrasyon penceresidir. Simde Gazebo IMU'su 250 Hz yayınlar (`x500_base` `update_rate 250`). PX4 bu yüzden `px4-rc.simulator`'da varsayılanı 250 yapar ("Simulator IMU data provided at 250 Hz"). 200 Hz'lik pencere 4 ms'lik örneklerin tam katı olmaz, simde düzensiz entegrasyon yaratır. Hız denetleyicisi entegre veriyi değil ham açısal hızı kullandığı için uçuşa etkisi zaten ihmal edilebilir.

**RTL ve geofence: simin kendi değerleri** (Ahmet: "gerçek dron ayarlarını boşver"; `sim.params`):

| Parametre | Değer | Gerekçe |
|---|---|---|
| `RTL_RETURN_ALT` | 30 m | Dünyadaki en uzun ağaç ~11 m (çam, ölçek 2.4), takip yüksekliği en çok 15 m. 30 m, ~20 m'lik kampüs ağaçlarını da 10 m payla aşar. |
| `RTL_DESCEND_ALT` | 10 m | Evin üstünde bu yüksekliğe inip bekler; kalkış yerinin 8 m çevresi ağaçsız. |
| `GF_MAX_HOR_DIST` | 150 m | Ayrıntılı 120 m'lik zemini ve uzun yürüyüşleri kapsar. Varsayılanı 0'dır (kapalı). |
| `GF_MAX_VER_DIST` | 40 m | `RTL_RETURN_ALT`'ın ve en yüksek takip yüksekliğinin üstünde. Varsayılanı 0'dır (kapalı). |
| `GF_ACTION` | 2 (Hold) | Çitte durur, kararı operatör verir. Hem varsayılan hem gerçek araçtaki değer. |

Doğrulama: pytest 93/93, `f0_kabul.sh` GEÇTİ (20/20 parametre PX4'te dosyadaki değerde; Hold sapması yatay 0.06 m, dikey 0.06 m).

Çoklu EKF (`EKF2_MULTI_IMU`, `SENS_IMU_MODE`) alınmadı: simde tek IMU var.
