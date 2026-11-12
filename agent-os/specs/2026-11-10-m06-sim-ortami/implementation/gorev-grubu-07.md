# Görev Grubu 7 — Manyetik alan (iş A) ile ölçütler, ULog özeti ve rapor (iş B)

- Tarih: 12.11.2026 · dal `ozellik/m06-sim-ortami` · taban commit `aac9f18f9c` (Görev grubu 6)
- İki ayrı iş, iki ayrı commit: **A** (manyetik alan, kullanıcı kararı 12.11) ve **B** (`tasks.md` 7.0–7.5 + ekler).
  A'nın koşuları `aac9f18f9c` + yalnız A'nın değişiklikleriyle, B'ninkiler `aac9f18f9c` + A + B ile koşuldu.
- Durum: **A uygulandı ve test edildi**, commit'lenmedi.

## İş A — Manyetik alan

### Kısaca

6. grupta EKF'nin yaw (burun yönü) tahmini koşudan koşuya −2.4°…+8.5° kayıyordu; düz zemin konum hatasının çoğu
bundandı. Kullanıcı "manyetik alan gerçek konuma eşitlensin" dedi. Önce doğrulandı: sebep dünya dosyasındaki
`<magnetic_field>` değeri **değil**, Gazebo Harmonic'in manyetometresinin PX4'e **aynalanmış** ulaşmasıydı. PX4'e gelen
alanın sapması (declination) −2.57°, EKF'nin beklediği +3.41°: dron yerdeyken bile yaw 6.0° yanlıştı. Gazebo'nun
manyetometresi kapatıldı, PX4'ün kendi simüle manyetometresi (`sensor_mag_sim`) açıldı: alan artık PX4'ün dünya
manyetik modeliyle (WMM) aynı. Sonuç (3 + 3 koşu): kayıt penceresinde yaw hatası en çok 11.3° → 2.7°, yerde sabit
+6.0° → ≈ 0°, model kutusunun konum hatası 0.38–0.85 m → 0.24–0.40 m (kutunun kendi payı 0.23–0.26 m). F0 ve F1
yeniden geçti.

**Kullanıcının kararından sapma (onay gerekiyor):** karar "dünyanın alanını eşitle" idi; o değer hiçbir yerde
kullanılmadığı için (aşağıda 1) yalnız onu değiştirmek bir şey düzeltmezdi. Aynı amaca (dronun ölçtüğü alan = gerçek
konumun alanı = EKF'nin beklediği alan) PX4'ün kendi modülüyle ulaşıldı; `<magnetic_field>` de belge amaçlı WMM
değerine eşitlendi.

### Neden doğrulandı (adım adım)

1. **`<magnetic_field>` kullanılmıyor.** gz-sim 8.15'in manyetometre sistemi (`src/systems/magnetometer/Magnetometer.cc`,
   `gz-sim8_8.15.0` etiketinden okundu; kurulu kütüphanedeki dizgiler de aynı) dünyanın alanını yalnız sensör
   oluşturulurken verir, **her adımda** dünyanın `spherical_coordinates`'ından kendi tablolarıyla (10° ızgara, tamsayı
   derece) yeniden hesaplar ve üstüne yazar. Eski değer (6e-06 2.3e-05 −4.2e-05) zaten 14.6° sapma demekti; hiçbir
   ölçümde görülmedi.
2. **Gazebo'nun alanı NED bileşenlerini ENU yuvalarına yazıyor.** `use_earth_frame_ned` varsayılanı `true`:
   dünya alanı (X = kuzey, Y = doğu, Z = aşağı) olarak ENU dünyasına konur; sensör bunu gövdeye (FLU) döndürür.
   Birim gauss'tur (alan adı `field_tesla` olsa da). PX4 v1.17.0'ın `gz_bridge`'i (`GZBridge.cpp` 400–405) bunu
   `x = −y, y = −x, z = z` ile alıyor (yorumunda "weird left handed coordinate system", gz-sim#2460). İkisi birlikte
   doğu bileşenini **aynalıyor**: her burun yönünde PX4 sapmayı ters işaretle görür (`test_manyetometre.py`, 5 yönle
   sınanır).
3. **Sayılar.** Dünyanın kökünde (Zürih, PX4'ün varsayılan evi; 47.398°K, 8.546°D): gz-sim tablosu +2.564° sapma,
   63.25° eğim, 48.07 µT; PX4'ün WMM'i (`src/lib/world_magnetic_model`, WMM-2020, 2024.41 tarihli tablolar) +3.406°,
   63.157°, 48.239 µT. PX4'ün gördüğü −2.564°, beklediği +3.406° → **5.97°** fark.
4. **Ölçümle doğrulama** (önce koşularının ULog'u, `sensor_mag` gerçek duruşla NED'e çevrildi): ölçülen sapma −2.58° /
   −2.59° / −2.64°; yerde, kalkışta ve Follow Target'e kadar askıda EKF yaw − gerçek yaw **+5.9…+6.2°** (sabit).
   Uçuşta EKF, GPS hızından ve 3B manyetometre kaynaştırmasından yeryüzü alanını öğrenmeye çalışırken yaw −4…+11°
   arasında dolaşıyor (öğrenilen sapma +3.41°'den −1.4…−6.5°'ye kaydı). 6. gruptaki koşudan koşuya değişim buydu.
5. **Zaman kayması değil.** EKF ile gerçek duruş arasına 20–100 ms gecikme koymak hatayı büyütüyor (en iyisi 0 ms);
   hatanın yaw hızıyla ilişkisi zayıf (r = 0.13–0.26).

### Neden bu yol seçildi

| Seçenek | Sonuç |
|---|---|
| Yalnız `<magnetic_field>`'ı WMM'e eşitlemek (kararın sözü) | Etkisiz: gz-sim her adımda üstüne yazar |
| EKF'ye Gazebo'nun sapmasını vermek (`EKF2_DECL_TYPE` / `EKF2_MAG_DECL`) | Temiz değil: PX4 v1.17.0 yeryüzü alanı durumunu (`mag_I`) yine WMM'den kurar (`resetMagStates`), sapma ile alan durumu çelişir; ayrıca `DECL_TYPE 0`'da `EKF2_MAG_DECL` hiç kullanılmaz (`getMagDeclination`) |
| Gazebo'nun `use_earth_frame_ned false` ayarı (doğru ENU alanı) | PX4 v1.17.0'ın `gz_bridge` dönüşümü eski ("weird") çerçeveye göre: alan 90° dönmüş ve z ters gelir; PX4 dosyası değiştirilemez |
| Dünyayı sapmanın 0 olduğu bir yere taşımak | Kırılgan (iki tablonun farkı kalır), konumu bir sim hatası yüzünden değiştirir |
| **PX4 `sensor_mag_sim` + Gazebo manyetometre sistemi kapalı** (seçilen) | Stok PX4 modülü (`px4-rc.gzsim` `SENS_EN_MAGSIM 1` ile başlatır; `px4_sitl_default`'ta derli). Alan: PX4'ün WMM'i, dronun **gerçek** konumu (`vehicle_global_position_groundtruth`) ve **gerçek** duruşu (`vehicle_attitude_groundtruth`, `gz_bridge` yayınlar), 50 Hz. Aygıt kimliği 197388 = rcS'in `CAL_MAG0_ID`'si (kalibreli). PX4 dosyası değişmez |

Değişen dosyalar: `tez/sim/server.config` (manyetometre sistemi satırı çıktı, gerekçe yorumda),
`tez/sim/parametreler/sim.params` (`SENS_EN_MAGSIM 1`, gerekçe yorumda), `tez/sim/worlds/duz_alan.sdf` ve `cayir.sdf`
(`<magnetic_field>` = PX4 WMM, ENU tesla: 1.29398e-06 2.17433e-05 −4.30411e-05; hesap ve kaynak yorumda),
`tez/sim/testler/test_manyetometre.py` (yeni, 3 test fonksiyonu, 7 durum), `tez/sim/README.md`, `spec.md`, `tasks.md`
(7.A), `implementation/kabul-kosulari.md`.

### Testler (önce testler yazıldı, ikisi beklendiği gibi kaldı, sonra kod)

| Test | Ne sınar |
|---|---|
| `test_worlds_hold_px4s_wmm_field_of_their_origin` | Her dünyanın `<magnetic_field>`'ı, PX4'ün tablolarından (`geo_magnetic_tables.hpp`, PX4'ün çift doğrusal ara değeri Python'da) dünyanın kökünde hesaplanan ENU alanıyla 2e-10 T içinde aynı; sapma +3.406° |
| `test_the_drone_magnetometer_is_px4s_simulated_one` | `sim.params`'ta `SENS_EN_MAGSIM 1`; `server.config`'te manyetometre sistemi yok; `px4-rc.gzsim` onu bu parametreyle başlatıyor; `SensorMagSim` gerçek duruş ve konum konularını okuyor, kimliği 197388 |
| `test_gazebo_harmonics_field_reaches_px4_with_the_east_part_mirrored` (5 yön) | Neden: Gazebo'nun NED-yuvalı alanı + gövdeye dönüş + `gz_bridge` eşlemesi → PX4 her yönde sapmayı −2.564° görür, eğim aynı kalır (`GZBridge.cpp`'deki iki satır da testte okunur) |

| Kontrol | Sonuç |
|---|---|
| `$P -m pytest tez/sim/testler -q` | **191 geçti** (184 + 7), 1 uyarı (önceden de vardı, protobuf) |
| `ruff format` + `ruff check` (`tez/sim/ruff.toml`) | temiz |
| `tez/pin/verify_pin.sh --worktree` | **KILIT SAGLAM (v1.17.0)** |
| `f0_kabul.sh` | **GEÇTİ**: 21/21 başlangıç parametresi PX4'te (yeni `SENS_EN_MAGSIM` dahil); kamera 30.3 kare/sim-s, RTF 1.00; Hold'da sapma 0.06 / 0.10 m |
| `f1_kabul.sh` | **GEÇTİ**: hedef doğrulama farkı en çok 0.13 / 0.13 m, iki koşu arası 0.000 m |

### Önce / sonra (aynı yöntem: `takip_yuruyen`, model v0.2, stok Follow Me, 3 + 3 koşu)

"Önce" `aac9f18f9c` (temiz ağaç), "sonra" `aac9f18f9c` + A. Yaw hatası iki yolla: 6. gruptaki gibi model karelerinin
EKF pozuyla (`ekf_yaw_hatasi_*`) ve ULog'daki her `vehicle_attitude` örneği `vehicle_attitude_groundtruth`'a karşı
(scratchpad betiği; B'de `olcum.py`'ye girdi: `ekf_yaw_hatasi_ulog_*`, `mag_sapma_olculen_deg`).

| | önce 1 | önce 2 | önce 4 | sonra 1 | sonra 2 | sonra 3 |
|---|---|---|---|---|---|---|
| Yerde ve askıda (Follow Target'ten önce) yaw hatası [°] | +5.9 | +6.0 | +6.0 | ≈ 0 (−0.1…+1.2) | ≈ 0 (−0.5…+0.7) | ≈ 0 (−0.7…−0.1) |
| Ölçülen alanın sapması [°] (PX4 WMM +3.41) | −2.58 | −2.59 | −2.64 | +3.51 | +3.20 | +3.87 |
| Kayıt penceresi yaw hatası ort. / en çok \|·\| (ULog) [°] | −1.93 / 4.41 | +2.46 / **11.29** | +0.91 / 2.79 | −0.79 / 2.07 | −0.89 / 2.67 | +0.51 / 1.49 |
| Aynı, model kareleri (6. grup yöntemi) [°] | −1.80 / 4.38 | +3.49 / 11.28 | +0.86 / 2.62 | −0.78 / 1.93 | −0.67 / 2.66 | −0.00 / 0.44 |
| Bütün uçuşta yaw hatasının std / en çok [°] | 2.92 / 6.0 | 4.35 / 11.3 | 2.98 / 6.4 | 1.77 / 4.3 | 2.45 / 7.3 | 1.52 / 4.4 |
| Model kutusunun konum hatası (EKF pozuyla) ort. [m] | 0.38 | **0.85** | 0.41 | 0.37 | 0.40 | 0.24 |
| Aynı kutular gerçek pozla (kutunun payı) [m] | 0.26 | 0.25 | 0.23 | 0.24 | 0.23 | 0.23 |
| Dron–hedef yatay mesafe ort. / en az [m] | 7.61 / 0.86 | 8.23 / 4.46 | 7.60 / 2.40 | 7.97 / 3.16 | 7.85 / 1.86 | 8.15 / 1.63 |
| RTF | 0.94 | 1.00 | 0.93 | 0.99 | 1.00 | 0.90 |

Önce koşusu 3 başlamadı (aşağıda "Karşılaşılan sorunlar"); yerine 4 koşuldu. Grafik:
`~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev7_A_manyetik_alan_yaw_once_sonra.png`.

**Okuma:** sabit 6°'lik kayma ve onun uçuşta yarattığı yavaş dolaşma gitti; konum hatası artık neredeyse yalnız
kutunun kendi payı (+0.00…0.17 m). **Kalan:** takip başında dron hedef etrafında dönerken (30–50 s) her altı koşuda da
±4°'lik geçici bir EKF sapması var (sonra 2'de +7.3°, 45 s). Zaman kayması değil (yukarıda 5); önce koşularında da
aynı yerde var, yani manyetik alandan bağımsız bir EKF davranışı (hızlı yaw dönüşü + yanal ivme sırasında 3B
manyetometre ve GPS hızı kaynaştırması). Bu iş kapsamında sebebi bulunmadı; gerçek araçta da beklenir, ölçülmeli.

### Karşılaşılan sorunlar

- **Önce koşusu 3 hiç başlamadı:** PX4 açıldı ama bizim MAVLink bağlantımıza 60 s heartbeat gelmedi (PX4 tarafında
  "partner IP" satırı yok, yani PX4 bizden hiçbir şey almadı ve biz de PX4'ten almadık). Önceki ve sonraki koşular
  sorunsuz; bağlantı noktaları boştu. Nedeni bulunamadı, seyrek bir altyapı hatası olarak kaydedildi (B'deki `toplu.py`
  böyle bir koşuyu yeniden dener ve listeler).
- **Aynı koşu rapor yazmadan çöktü:** `KeyError: 'tez_los_px4_eslesen'` (`senaryo._tracking_log_lines`). PX4'e hiç
  `TEZ_LOS` ulaşmayınca ULog'da `debug_vect` yok ve `rapor.ulog_tez_los` anahtarların bir kısmını yazmıyordu. Mevcut
  koddaki hata; B'de testiyle düzeltildi (`test_tez_los_in_a_ulog_without_debug_vect_has_every_key`).
- `sensor_mag_sim` ilk GPS yer gerçeğini bekler: açılışta birkaç saniye "Preflight Fail: Found 0 compass" uyarısı
  çıkıyor, yön hizalaması 7.5 s yerine 8.0–8.4 s'de; sonra kayboluyor, kalkışı etkilemedi.

### Kalan sim-gerçek farkları (manyetometre)

- `sensor_mag_sim`'in gürültüsü 20/20/30 mG beyaz (PX4'te sabit, değiştirilemez); gerçek bir pusulanın (IIS2MDC /
  IST8310) beyaz gürültüsü ≈ 3 mG ama motor/akım girişimi, kalibrasyon artığı, eğim hatası ve yerel manyetik sapma
  (≈ 1–2°) vardır; simde bunların hiçbiri yok. Simdeki yaw bu yüzden gerçeğinden iyi olabilir.
- Gazebo Harmonic'in manyetometresi gelecekte (PX4 ve gz-sim birlikte güncellenince) düzelir; PX4 v1.17.0'da kilitli
  olduğumuz için o yol kapalı.
- Alan PX4'ün kendi WMM tablosundan gelir: simde EKF'nin beklediği alan **tam** ölçülen alandır. Gerçekte WMM ile yerel
  alan arasında fark olur.

### Açık konular (A)

- Kullanıcının ve Hüseyin'in onayı: kararın sözünden farklı yol (PX4 `sensor_mag_sim`). Reddedilirse A tek commit
  olduğu için `git revert` ile geri alınır.
- Takip başındaki ±4°'lik geçici yaw sapmasının sebebi (EKF ayarı mı, gerçekte de olur mu): m22/m25 uçuş ULog'larıyla
  karşılaştırılmalı.

---

## Kendin dene

**Başlamadan:** Terminal açmak için **Ctrl+Alt+T**'ye bas. Aşağıdaki gri kutulardaki komutları kopyala, terminale
**Ctrl+Shift+V** ile yapıştır (terminalde Ctrl+V çalışmaz) ve **Enter**'a bas. Bir komutu yarıda kesmek için
**Ctrl+C**.

### 1. Hazırlık (her yeni terminalde bir kez)

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot
P=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python
```

### 2. Manyetik alan: önce / sonra grafiği

```bash
xdg-open ~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev7_A_manyetik_alan_yaw_once_sonra.png
```

Solda eski hâl: üç koşuda da kalkıştan Follow Target'e kadar çizgiler kırmızı kesikli çizginin (6°) üstünde düz
gidiyor; dron daha uçmadan pusulası 6° yanlış. Sağda yeni hâl: çizgiler 0'da başlıyor. Alttaki tabloda "ölçülen
sapma" −2.6°'den +3.5°'e döndü (PX4'ün beklediği +3.41°) ve konum hatası küçüldü.

### 3. Testler ve kilit

```bash
$P -m pytest tez/sim/testler/test_manyetometre.py -v
tez/pin/verify_pin.sh --worktree
```

Beklenen: `7 passed`; `KILIT SAGLAM (v1.17.0)`.

### 4. Kendin koştur (pencere yok, ~2 dakika)

Önce açık bir sim olmadığından emin ol (iki satır da bir şey yazmamalı):

```bash
pgrep -x px4
pgrep -f "^gz sim"
```

```bash
$P tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz
```

Sonda "Konum (model kutusu, düz zemin): ... EKF yaw hatası ort. ..." satırında değer artık birkaç onda bir derece
civarında olmalı (eskiden −1.8…+3.5°, bir koşuda +8.5°).
