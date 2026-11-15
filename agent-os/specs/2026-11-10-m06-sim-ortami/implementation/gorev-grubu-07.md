# Görev Grubu 7 — Manyetik alan (iş A) ile ölçütler, ULog özeti ve rapor (iş B)

- Tarih: 12.11.2026 · dal `ozellik/m06-sim-ortami` · taban commit `aac9f18f9c` (Görev grubu 6)
- İki ayrı iş, iki ayrı commit: **A** (manyetik alan, kullanıcı kararı 12.11) ve **B** (`tasks.md` 7.0–7.5 + ekler).
  A'nın koşuları `aac9f18f9c` + yalnız A'nın değişiklikleriyle, B'ninkiler `aac9f18f9c` + A + B ile koşuldu.
- Durum: **A ve B uygulandı ve test edildi**, commit'lenmedi (iki ayrı commit için A'nın yaması:
  `~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev7_is_A.patch`; aşağıda "Commit ayrımı").

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

## İş B — Görev Grubu 7: ölçütler, ULog özeti, rapor ve çok koşu

### Kısaca

Her koşu artık spec'in "Ölçüt Tanımları"ndaki **bütün** anahtarları `ozet.json`'a yazıyor (uygulanmayan `null`); ölçütler
tek bir modülde (`araclar/olcum.py`). Rapor; kontroller ve uyarılar (model görüntüde çalışıyor mu, 3 m uyarısı,
kameranın yakın sınırı, mod, RTF), gruplu ölçüm tabloları, iki yeni grafik (takip zaman çizelgesi; PX4'ün varsaydığı
rota ve yörünge açısı), mod zaman çizelgesi ve ayarlar (model sha256, PX4 parametreleri) gösteriyor. Kullanıcının
videoda gördüğü salınım ve hedefi kaçırma sayıya döküldü: yeni ölçütler en az mesafe ve 3 m altı süre, kameranın
yakın görüş sınırı ve altında kalınan süre, hedefin tamamı kadrajda mı, **arkada kalma açısı hatası** ve takip başında
dronun hedef etrafında taradığı açı. Aynı senaryoyu N kez koşup dağılımını veren `araclar/toplu.py` eklendi.

**Ana bulgu (3'er koşu):** stok Follow Me'de dron kişi dururken etrafında ileri geri **629–699°** tarıyor (ideal: 0°),
kişi yürürken "arkasından" ortalama **55–69°** sapıyor (p95 119–157°, 4–7 s yanında ya da önünde), üç koşunun ikisinde
3 m'nin altına iniyor (en az 1.66 m) ve 1–4.3 s kameranın yakın görüş sınırının (≈ 4.0 m) içinde kalıyor. Aynı stok
mod "mükemmel algılayıcı"yla (kişinin gerçek konumu, gürültüsüz) üç koşuda da aynı şeyi yapıyor: PX4 rotayı kişi
yürüyene kadar ≈ 37 s **kuzey** varsayıyor, dron kişi dururken etrafında 194–195°, yürümeye başlayınca 97° dönüyor
(iki gereksiz dönüş), arkada kalma hatası ort. 47–48°. Model kutusunun konum titreşimi bu iki dönüşü ileri geri bir
salınıma çeviriyor. Bunlar PX4 v1.17.0'ın stok Follow Target görevinin davranışıdır; aşağıda kaynak satırlarıyla.

### Ne yapıldı

| Alt görev | Dosya | Özet |
|---|---|---|
| 7.1 | `testler/test_olcum.py` (yeni, 16 test) | `senaryo.py`'nin özet satırları her takip kaynağında (B koşularında bulunan hata); spec tablosu = `olcum.KEYS` (iki yönde); PX4 nav_state adları (`ui.hpp`); model (algılama, IoU, seçim, yanlış kişi + aynı kıyafet, yanlış pozitif); LOS açı hatası ve sistematik fark; TEZ_LOS akışı, gecikme istatistikleri, kilit; kareler ve süreler; mesafe / 3 m / kadraj sınırları / tamamı kadrajda / arkada kalma / yörünge dönüşleri; hover titremesinin dönüş sayılmaması; PX4 `follow_target_status`; mod zaman çizelgesi ve korunma oranı; ULog'da `debug_vect` yokken bütün anahtarlar (A'da bulunan hata); ULog `TEZ_LOS` ve `follow_target` sayımları (`test_rapor.py`'den taşındı); EKF yaw ve ölçülen sapma; `measure`'ın bütün anahtarları yazması. Beklenen değerler testte elle hesaplanır |
| 7.1 | `test_rapor.py` (+2, 2 taşındı), `test_toplu.py` (yeni, 4), `test_algilama.py`, `test_takip.py` | Kontroller ve 3 m uyarısı (olay ve uyarı, başarı eşiği değil); `ozet.json`'da bütün anahtarlar ve yeni HTML bölümleri; çok koşunun dağılımı, yeniden deneme kuralı, komut, özet dosyaları; `DetectionLog.metrics` testi `test_olcum`'a, `takip.angle_deg` `kamera.angle_deg`'e taşındı |
| 7.2 | `araclar/olcum.py` (yeni) | `measure(RunData)`: model, LOS, zaman, takip ölçütleri; `tracking_metrics` (yeni takip geometrisi), `orbit_turn`, `frame_limits`; 5./6. gruptaki geçici ölçütler buraya taşındı (`takip.Tracker.metrics` ve yardımcıları, `algilama.DetectionLog.metrics`, `senaryo.tracking_results`'taki hesaplar, `rapor.debug_names` / `tez_los_in_ulog` / `follow_target_in_ulog`) |
| 7.3 | `araclar/olcum.py` | `Topics` (iki ULog dosyası birleşik), `mode_timeline` / `mode_kept` / `wanted_nav_state`, `follow_status_in_ulog`, `attitude_in_ulog` (EKF yaw ve ölçülen manyetik sapma, A'nın izlenmesi için) |
| 7.4 | `araclar/rapor.py` | `checks` (4. gruptaki IoU kontrolü buraya taşındı), `METRIC_GROUPS`, `plot_tracking`, `plot_px4_follow`, mod zaman çizelgesi, ayarlar, `ozet.json` → `kontroller`; `metrics`, `_visibility`, `plot_map` korundu |
| 7.4 | `araclar/senaryo.py` | Mod kaydı (`ModeLog`: heartbeat'in onayladığı an ve değişiklikler), `olcum.RunData` → `measure`, log satırları (yeni takip satırları), `tracking_sections` |
| 7.6 | `araclar/toplu.py` (yeni) | Çok koşu (karar 4): ayrı süreçler, yeniden deneme, `toplu.json` / `toplu.csv` / `toplu.html` |
| belge | `spec.md`, `tasks.md`, `README.md`, `ruff.toml`, `kabul-kosulari.md` | Ölçüt tablosu (yeni anahtarlar, tanımlar), "PX4 stok Follow Target davranışı", "Çok koşu", Açık Konular (6. grubun kararları); 7.x işaretlendi, 9. gruba 3 koşu kuralı ve 9.8 (stok parametre karşılaştırması); README "Ölçütler, rapor ve çok koşu"; ruff: `olcum`, `toplu` |

### Kararlar ve gerekçeler

1. **Bütün ölçütler tek modülde, `RunData` ile.** `measure` canlı nesnelere değil, koşunun kayıtlarına (hakem satırları,
   model satırları, gönderim denemeleri, ULog dosyaları) bakar: her takip kaynağı (stok Follow Me, m15'in modu) aynı
   hesaptan geçer ve bir koşu sonradan da ölçülebilir. `KEYS` spec tablosundan test edilir; tablo ile kod ayrışamaz.
2. **`los_i_ii_fark_*` → `los_aci_hatasi_*`.** Tanım: seçilen kutunun LOS (i)'si ile aynı karenin LOS (ii)'si, kutu
   hedefken; her kaynakta ölçülür, `takip.los: model`'de gönderilen `TEZ_LOS` budur (hakem kaynağında gönderilen
   zaten doğru cevap olduğu için ölçmenin anlamı yok).
3. **`iou_ort` yalnız bulunan karelerde** (IoU ≥ 0.5): bulunamayan kareler `kacirma_orani`'na girer; ikisi karışmaz.
4. **Arkada kalma açısı:** hedeften drona yön ile hedefin hareket yönünün tersi arasındaki açının mutlak değeri; hedef
   ≥ 0.5 m/s iken (durarak dönen kişide "arka" tanımsız). Hareket yönü hakemin yolundan (`hedef_yaw`), dron Gazebo'dan.
   Köşede ideal bir takipçinin de bir süre sapacağı unutulmamalı (kişi 90° dönünce "arka" anında 90° döner); ölçüt bu
   yüzden ortalama, p95 ve > 90° süreyle birlikte okunur.
5. **Yörünge dönüşü:** hedef etrafındaki açı 0.5 s'de bir örneklenir ve iki yöndeki dönüşler toplanır; 30 Hz'de
   toplanırsa hover titremesi dönüş gibi birikir (`test_orbit_turn_ignores_hover_jitter`: 2 cm gürültü 30 Hz'de > 50°,
   0.5 s'de < 15°). İki pencere: mod seçiminden kişinin yürümeye başlamasına ("takip başı") ve yürüyüşün ilk 10 s'si.
   PX4'ün rota varsayımıyla birlikte kayıt penceresinden önceye bakan tek ölçütlerdir; spec'te istisna olarak yazıldı.
6. **Kameranın yakın görüş sınırı** her karenin gerçek kamera yüksekliğiyle, nominal 45° montaj ve `camera_info`'nun
   düşey açısıyla, düz uçuş için hesaplanır; dronun eğimi katılmaz (ivmelenirken burun eğilince sınır kayar). Gerçek
   kesilmeyi hakemin piksel izdüşümü verir: `ayak_kadrajda_orani` ve `hedef_kadrajda_orani` (ayak ve baş görüntüde).
7. **3 m uyarısı (karar 3):** her aralık olaylara ve raporun "Kontroller ve uyarılar"ına yazılır; koşunun sonucunu
   değiştirmez. Eşik sabiti `olcum.NEAR_DISTANCE_M = 3.0`, m01'e öneri.
8. **Mod korunma oranı ULog'dan:** istenen nav_state, koşunun mod seçtiği an (heartbeat onayladığında) PX4'ün olduğu
   durumdur; böylece harici modlarda da (EXTERNALn) numara koda gömülmez. ULog yoksa koşunun heartbeat kaydı kullanılır.
9. **Çok koşu ayrı süreçlerle (`toplu.py`), `senaryo.py --tekrar` değil:** bir koşunun çökmesi ya da takılan bir
   Gazebo diğerlerini etkilemez, hiçbir koşu öncekinin durumunu (gz-transport düğümleri, model süreci) devralmaz.
   Başlayamayan koşu (ozet yok ya da dron hazır olmadan TAMAMLANMADI) yeniden denenir ve listelenir; uçup kalan koşu
   sonuçtur. Dağılım için ortalama, en az, en çok (3 koşuda standart sapma anlamlı değil).
10. **Kontroller olaylardan ayrı (`ozet.json` → `kontroller`):** başarısız model kontrolü ve 3 m uyarısı olaylara da
    yazılır; RTF ve mod uyarıları zaten `senaryo.py`'nin olaylarındadır, tekrar yazılmaz.

### PX4 stok Follow Target davranışı: bulgular kaynaktan doğrulandı

`src/modules/flight_mode_manager/tasks/AutoFollowTarget/` yalnız okundu; ayrıntı spec "PX4 stok Follow Target
davranışı".

| İddia | Kaynak | Durum |
|---|---|---|
| Mod açılınca rota ve yörünge açısı 0 (kuzey); ilk hedef nokta hedefin kuzeyi | `FlightTaskAutoFollowTarget.hpp:284` `_target_course_rad{0.0f}`, `:286` `_orbit_angle_setpoint_rad{0.0f}`; `.cpp:87` yörünge yörüngesini 0'a sıfırlar; `.cpp:240` istenen konum = hedef + mesafe·(cos, sin) yörünge açısı (NED) | **Doğru.** Ek: görev nesnesi her mod geçişinde yeniden kurulur (`Templates/FlightTasks_generated.cpp.em:64`, placement new), yani her Follow Target seçiminde baştan "kuzey" |
| Rota yalnız süzülmüş ve süzülmemiş hız ≥ 1 m/s iken güncellenir | `.cpp:191–192`, `.hpp:94` `TARGET_SPEED_DEADZONE_FOR_ORIENTATION_TRACKING = 1.0` | **Doğru, bir farkla:** "kişi dururken rota 0'da kalır" yalnız konum gürültüsüzken geçerli. Model kaynağında kutudan bulunan konum ±0.5–1 m titrer, kestirici bunu ≥ 1 m/s'lik sahte hızlara çevirir: rota kayıt başladıktan 2 s sonra 0'dan ayrılıp −170°, +10°, 180°, −70° arasında atlıyor (`px4_rota_kuzey_varsayimi_s` 2.0 s, üç koşuda). Dron bu yüzden iki temiz dönüş yerine kişinin etrafında ileri geri salınıyor |
| Yörünge ivme/hız sınırlı | `.hpp:99–102` (`ORBIT_TRAJECTORY_MAX_JERK 4`, `..._ACCELERATION 2`), `.cpp:207–209` (/ mesafe), `FLW_TGT_MAX_VEL 5` | **Doğru:** 8 m'de 0.25 rad/s², 0.625 rad/s; 180° ≈ 7 s |
| Kestirici en çok 500 ms'de bir konum füzyonu, `FLW_TGT_RS` 0.1 | `TargetEstimator.hpp:60`, `follow_target_params.c:53` | **Doğru.** Ek: görev bunun üstüne 1 rad/s'lik ikinci dereceden bir süzgeç koyar (`.hpp:82`); köşede gecikme ve aşma bundan da gelir |
| 45° kamera 8 m'de yeri ≈ 3.6 m'den itibaren görür | Kamera raporu (41° düşey) | **Simde ≈ 3.9–4.0 m** (40.1° düşey açı, kamera yerden ≈ 8.2 m, base_link'ten 0.151 m önde): `kadraj_yakin_sinir_m` 3.96–3.98 |

### Test sonuçları (B)

| Kontrol | Sonuç |
|---|---|
| `$P -m pytest tez/sim/testler/test_olcum.py tez/sim/testler/test_rapor.py tez/sim/testler/test_toplu.py -q` | **27 geçti** (16 + 7 + 4) |
| `$P -m pytest tez/sim/testler -q` | **211 geçti** (A'dan sonra 191; B: +16 `test_olcum`, +4 `test_toplu`, +2 `test_rapor`, −2 taşınan, `test_algilama`'nın ölçüt kısmı taşındı), 1 uyarı (önceden de vardı, protobuf). `torch`/`ultralytics` gerekmez |
| `ruff format` + `ruff check` (`tez/sim/ruff.toml`, ruff 0.16.9) | temiz |
| `tez/pin/verify_pin.sh --worktree` | **KILIT SAGLAM (v1.17.0)** |
| `toplu.py --senaryo takip_yuruyen --tekrar 3` | 3/3 GEÇTİ, 3 deneme (eşik yok); aşağıda |
| `toplu.py --senaryo takip_yuruyen --tekrar 3 -- --los hakem` | 3/3 GEÇTİ, 3 deneme; aşağıda |
| `toplu.py --senaryo kalabalik_park --tekrar 3` | 3/3 GEÇTİ, 3 deneme (ilk deneme benim hatamla çıkmıştı: "Karşılaşılan sorunlar"); aşağıda |
| `senaryo.py --senaryo takip_yuruyen --ekransiz` (örnek rapor ve animasyon, son kod) | GEÇTİ (`sonuclar/gorev7_B_ornek_takip_yuruyen`): mesafe ort. 8.08 m, en az 4.12 m; 3 m altı yok; arkada kalma ort. 47° (p95 79°); takip başı 463°, yürüyüş başı 88°; PX4 rotayı 0.8 s kuzey varsaydı; kişinin tamamı kadrajda %79; RTF 0.94. Örnek rapor bu koşudan |
| `f0_kabul.sh` (son kod) | **GEÇTİ**: 21/21 başlangıç parametresi; kamera 30.4 kare/sim-s, RTF 1.00; Hold'da sapma 0.05 / 0.10 m; temiz kapanış |
| `f1_kabul.sh` (son kod; `rapor.py` / `senaryo.py` değiştiği için) | **GEÇTİ**: hedef doğrulama farkı en çok 0.13 / 0.13 m; iki koşu arası 0.000 m (`yok` + `--modelsiz` yolu, yeni ölçüm ve rapor koduyla) |
| `ozet.json` → `olcutler` | Her koşuda `olcum.KEYS`'in 106 anahtarının hepsi (uygulanmayan `null`); `rapor.html` yeni bölümleri gösteriyor (ekran görüntüleri aşağıda) |

Her koşudan önce `pgrep -x px4` / `pgrep -f "^gz sim"` boştu; sonra da açık PX4, Gazebo ya da model süreci kalmadı.

### Sayılar: 3'er koşu (karar 4)

Kayıt penceresi 60 s → senaryo sonu (`takip_yuruyen` 89.4 s, `kalabalik_park` 89.3 s); "takip başı" mod seçiminden 60 s'ye. Her grup `toplu.py` ile (her koşu ilk denemede başladı). Model v0.2, CPU, 4 çekirdek, `imgsz` 640. Bütün klasörler `tez/sim/sonuclar/` altında.

**takip_yuruyen, model kutusu, stok Follow Me** (`gorev7_B_takip_yuruyen_x3`, 3 koşu: GEÇTİ, GEÇTİ, GEÇTİ)

| Ölçüt | koşu 1 | koşu 2 | koşu 3 | ort. | en az | en çok |
|---|---|---|---|---|---|---|
| Dron–hedef yatay mesafe ort. [m] | 7.40 | 8.20 | 8.50 | **8.04** | 7.40 | 8.50 |
| Yatay mesafe en az [m] | 1.66 | 2.91 | 3.02 | **2.53** | 1.66 | 3.02 |
| Yatay mesafe en çok [m] | 9.7 | 12.1 | 14.4 | **12.0** | 9.7 | 14.4 |
| 3 m altında [s] (olay) | 1.1 | 0.4 | 0.0 | **0.5** | 0.0 | 1.1 |
| 3 m altına iniş [kez] | 1.0 | 1.0 | 0.0 | **0.7** | 0.0 | 1.0 |
| Kameranın yakın görüş sınırı [m] | 3.98 | 3.96 | 3.97 | **3.97** | 3.96 | 3.98 |
| Bu sınırdan yakın [s] | 1.5 | 4.3 | 1.0 | **2.3** | 1.0 | 4.3 |
| Arkada kalma açısı hatası ort. [°] | 69 | 55 | 59 | **61** | 55 | 69 |
| Arkada kalma açısı hatası p95 [°] | 151 | 119 | 157 | **143** | 119 | 157 |
| Hata > 90° (yanında/önünde) [s] | 7.2 | 4.1 | 4.6 | **5.3** | 4.1 | 7.2 |
| Takip başı: hedef dururken taranan açı [°] | 699 | 686 | 629 | **671** | 629 | 699 |
| Yürüyüşün ilk 10 s'si: taranan açı [°] | 157 | 204 | 252 | **204** | 157 | 252 |
| PX4 rotayı kuzey (0°) varsaydı [s] | 2.0 | 2.0 | 2.0 | **2.0** | 2.0 | 2.0 |
| PX4 rota hatası ort. [°] (hedef ≥ 1 m/s) | 27 | 51 | 30 | **36** | 27 | 51 |
| PX4 yörünge hedefinin dönüşü, takip başı [°] | 607 | 613 | 542 | **588** | 542 | 613 |
| Hedefin tamamı kadrajda [%] | 81 | 40 | 63 | **61** | 40 | 81 |
| Hedefin merkezi kadrajda [%] | 88 | 45 | 71 | **68** | 45 | 88 |
| Hedef gerçekten görünür [%] | 94 | 48 | 77 | **73** | 48 | 94 |
| En uzun kadraj dışı [s] | 1.5 | 11.3 | 4.9 | **5.9** | 1.5 | 11.3 |
| Algılama oranı [%] | 71 | 55 | 60 | **62** | 55 | 71 |
| Seçim doğru [%] | 69 | 55 | 60 | **61** | 55 | 69 |
| Yanlış kişi [%] | 0.0 | 0.0 | 0.0 | **0.0** | 0.0 | 0.0 |
| … aynı kıyafetli [%] | 0.0 | 0.0 | 0.0 | **0.0** | 0.0 | 0.0 |
| Yanlış pozitif / kare | 0.000 | 0.008 | 0.000 | **0.003** | 0.000 | 0.008 |
| Kilit kaybı | 7.0 | 5.0 | 4.0 | **5.3** | 4.0 | 7.0 |
| LOS açı hatası ort. [°] | 0.43 | 0.34 | 0.50 | **0.42** | 0.34 | 0.50 |
| Model kutusunun konum hatası ort. [m] | 0.35 | 0.29 | 0.38 | **0.34** | 0.29 | 0.38 |
| … gerçek pozla (kutunun payı) [m] | 0.27 | 0.27 | 0.30 | **0.28** | 0.27 | 0.30 |
| Gönderilen FOLLOW_TARGET hatası ort. [m] | 0.34 | 0.43 | 0.37 | **0.38** | 0.34 | 0.43 |
| PX4'ün hedef kestirimi hatası ort. [m] | 0.60 | 5.98 | 1.80 | **2.79** | 0.60 | 5.98 |
| PX4 kestirimi bayat [s] | 0.0 | 8.6 | 3.4 | **4.0** | 0.0 | 8.6 |
| EKF yaw hatası ort. (ULog) [°] | 1.42 | 0.06 | 1.24 | **0.91** | 0.06 | 1.42 |
| EKF yaw hatası en çok (ULog) [°] | 3.0 | 2.8 | 2.3 | **2.7** | 2.3 | 3.0 |
| Uçtan uca gecikme ort. [sim ms] | 138 | 134 | 144 | **139** | 134 | 144 |
| `model_ms` ort. | 81 | 80 | 86 | **82** | 80 | 86 |
| İşlenen kare [1/sim-s] | 12.4 | 12.8 | 11.8 | **12.3** | 11.8 | 12.8 |
| İstenen modda [%] | 100 | 100 | 100 | **100** | 100 | 100 |
| RTF | 0.98 | 0.97 | 0.97 | **0.97** | 0.97 | 0.98 |

**takip_yuruyen, mükemmel algılayıcı (--los hakem), stok Follow Me** (`gorev7_B_takip_yuruyen_hakem_x3`, 3 koşu: GEÇTİ, GEÇTİ, GEÇTİ)

| Ölçüt | koşu 1 | koşu 2 | koşu 3 | ort. | en az | en çok |
|---|---|---|---|---|---|---|
| Dron–hedef yatay mesafe ort. [m] | 7.63 | 7.58 | 7.64 | **7.62** | 7.58 | 7.64 |
| Yatay mesafe en az [m] | 3.07 | 3.19 | 3.06 | **3.11** | 3.06 | 3.19 |
| Yatay mesafe en çok [m] | 9.6 | 9.5 | 9.4 | **9.5** | 9.4 | 9.6 |
| 3 m altında [s] (olay) | 0.0 | 0.0 | 0.0 | **0.0** | 0.0 | 0.0 |
| 3 m altına iniş [kez] | 0.0 | 0.0 | 0.0 | **0.0** | 0.0 | 0.0 |
| Kameranın yakın görüş sınırı [m] | 3.97 | 3.95 | 3.97 | **3.96** | 3.95 | 3.97 |
| Bu sınırdan yakın [s] | 1.1 | 1.0 | 1.1 | **1.1** | 1.0 | 1.1 |
| Arkada kalma açısı hatası ort. [°] | 48 | 48 | 47 | **48** | 47 | 48 |
| Arkada kalma açısı hatası p95 [°] | 104 | 101 | 100 | **101** | 100 | 104 |
| Hata > 90° (yanında/önünde) [s] | 1.5 | 1.5 | 1.4 | **1.5** | 1.4 | 1.5 |
| Takip başı: hedef dururken taranan açı [°] | 195 | 194 | 194 | **194** | 194 | 195 |
| Yürüyüşün ilk 10 s'si: taranan açı [°] | 97 | 97 | 97 | **97** | 97 | 97 |
| PX4 rotayı kuzey (0°) varsaydı [s] | 36.8 | 36.8 | 37.6 | **37.1** | 36.8 | 37.6 |
| PX4 rota hatası ort. [°] (hedef ≥ 1 m/s) | 20 | 22 | 23 | **22** | 20 | 23 |
| PX4 yörünge hedefinin dönüşü, takip başı [°] | 178 | 178 | 177 | **178** | 177 | 178 |
| Hedefin tamamı kadrajda [%] | 92 | 92 | 91 | **92** | 91 | 92 |
| Hedefin merkezi kadrajda [%] | 95 | 95 | 93 | **94** | 93 | 95 |
| Hedef gerçekten görünür [%] | 96 | 96 | 96 | **96** | 96 | 96 |
| En uzun kadraj dışı [s] | 1.3 | 1.3 | 1.3 | **1.3** | 1.3 | 1.3 |
| Algılama oranı [%] | 70 | 67 | 65 | **68** | 65 | 70 |
| Seçim doğru [%] | 70 | 67 | 64 | **67** | 64 | 70 |
| Yanlış kişi [%] | 0.0 | 0.0 | 0.0 | **0.0** | 0.0 | 0.0 |
| … aynı kıyafetli [%] | 0.0 | 0.0 | 0.0 | **0.0** | 0.0 | 0.0 |
| Yanlış pozitif / kare | 0.000 | 0.000 | 0.000 | **0.000** | 0.000 | 0.000 |
| Kilit kaybı | 2.0 | 2.0 | 2.0 | **2.0** | 2.0 | 2.0 |
| LOS açı hatası ort. [°] | 0.28 | 0.27 | 0.26 | **0.27** | 0.26 | 0.28 |
| Model kutusunun konum hatası ort. [m] | 0.34 | 0.32 | 0.33 | **0.33** | 0.32 | 0.34 |
| … gerçek pozla (kutunun payı) [m] | 0.21 | 0.22 | 0.21 | **0.21** | 0.21 | 0.22 |
| Gönderilen FOLLOW_TARGET hatası ort. [m] | 0.00 | 0.00 | 0.00 | **0.00** | 0.00 | 0.00 |
| PX4'ün hedef kestirimi hatası ort. [m] | 0.24 | 0.22 | 0.26 | **0.24** | 0.22 | 0.26 |
| PX4 kestirimi bayat [s] | 0.0 | 0.0 | 0.0 | **0.0** | 0.0 | 0.0 |
| EKF yaw hatası ort. (ULog) [°] | -1.62 | -1.50 | -1.52 | **-1.54** | -1.62 | -1.50 |
| EKF yaw hatası en çok (ULog) [°] | 5.6 | 5.4 | 4.8 | **5.2** | 4.8 | 5.6 |
| Uçtan uca gecikme ort. [sim ms] | 72 | 72 | 73 | **72** | 72 | 73 |
| `model_ms` ort. | 86 | 86 | 87 | **86** | 86 | 87 |
| İşlenen kare [1/sim-s] | 11.9 | 12.1 | 11.8 | **11.9** | 11.8 | 12.1 |
| İstenen modda [%] | 100 | 100 | 100 | **100** | 100 | 100 |
| RTF | 0.95 | 0.95 | 0.96 | **0.95** | 0.95 | 0.96 |

**kalabalik_park, model kutusu, yok (Hold: dron 10 m'de bekler)** (`gorev7_B_kalabalik_park_x3`, 3 koşu: GEÇTİ, GEÇTİ, GEÇTİ)

| Ölçüt | koşu 1 | koşu 2 | koşu 3 | ort. | en az | en çok |
|---|---|---|---|---|---|---|
| Dron–hedef yatay mesafe ort. [m] | 12.54 | 12.54 | 12.55 | **12.54** | 12.54 | 12.55 |
| Yatay mesafe en az [m] | 7.08 | 7.06 | 7.10 | **7.08** | 7.06 | 7.10 |
| Yatay mesafe en çok [m] | 17.1 | 17.1 | 17.1 | **17.1** | 17.1 | 17.1 |
| 3 m altında [s] (olay) | 0.0 | 0.0 | 0.0 | **0.0** | 0.0 | 0.0 |
| 3 m altına iniş [kez] | 0.0 | 0.0 | 0.0 | **0.0** | 0.0 | 0.0 |
| Kameranın yakın görüş sınırı [m] | 4.90 | 4.88 | 4.89 | **4.89** | 4.88 | 4.90 |
| Bu sınırdan yakın [s] | 0.0 | 0.0 | 0.0 | **0.0** | 0.0 | 0.0 |
| Hedefin tamamı kadrajda [%] | 100 | 100 | 100 | **100** | 100 | 100 |
| Hedefin merkezi kadrajda [%] | 100 | 100 | 100 | **100** | 100 | 100 |
| Hedef gerçekten görünür [%] | 81 | 81 | 81 | **81** | 81 | 81 |
| En uzun kadraj dışı [s] | 0.0 | 0.0 | 0.0 | **0.0** | 0.0 | 0.0 |
| Algılama oranı [%] | 74 | 71 | 71 | **72** | 71 | 74 |
| Seçim doğru [%] | 67 | 61 | 49 | **59** | 49 | 67 |
| Yanlış kişi [%] | 7.4 | 13.1 | 18.9 | **13.1** | 7.4 | 18.9 |
| … aynı kıyafetli [%] | 4.0 | 8.0 | 11.0 | **7.7** | 4.0 | 11.0 |
| Yanlış pozitif / kare | 0.000 | 0.003 | 0.000 | **0.001** | 0.000 | 0.003 |
| Kilit kaybı | 1.0 | 2.0 | 3.0 | **2.0** | 1.0 | 3.0 |
| LOS açı hatası ort. [°] | 0.23 | 0.23 | 0.18 | **0.21** | 0.18 | 0.23 |
| Model kutusunun konum hatası ort. [m] | 0.16 | 0.29 | 0.20 | **0.22** | 0.16 | 0.29 |
| … gerçek pozla (kutunun payı) [m] | 0.20 | 0.20 | 0.16 | **0.19** | 0.16 | 0.20 |
| EKF yaw hatası ort. (ULog) [°] | 0.60 | -0.76 | -0.44 | **-0.20** | -0.76 | 0.60 |
| EKF yaw hatası en çok (ULog) [°] | 0.8 | 1.1 | 1.0 | **1.0** | 0.8 | 1.1 |
| Uçtan uca gecikme ort. [sim ms] | 131 | 134 | 131 | **132** | 131 | 134 |
| `model_ms` ort. | 84 | 86 | 84 | **85** | 84 | 86 |
| İşlenen kare [1/sim-s] | 12.9 | 12.8 | 13.4 | **13.0** | 12.8 | 13.4 |
| İstenen modda [%] | 100 | 100 | 100 | **100** | 100 | 100 |
| RTF | 0.91 | 0.89 | 0.87 | **0.89** | 0.87 | 0.91 |

**Okuma:**

- **Stok Follow Me'nin iki gereksiz dönüşü gerçek ve tekrarlanabilir:** "mükemmel algılayıcı"da (konum gürültüsüz)
  PX4 rotayı kişi yürüyene kadar 36.8–37.6 s kuzey varsaydı, dron duran kişinin etrafında 194–195°, yürümeye
  başlayınca 97° döndü (üç koşuda aynı). PX4'ün kendi yörünge hedefi de 177–178° döndü.
- **Model kutusuyla bu, salınıma dönüşüyor:** rota 2 s sonra kuzeyden ayrılıp gürültüyle atlıyor; dron duran kişinin
  etrafında ileri geri 629–699° tarıyor (mükemmel algılayıcının 3.5 katı), yürüyüş başında 157–252°.
- **Arkada kalma:** mükemmel algılayıcıda bile ortalama 47–48° (p95 100–104°; köşelerde 1.4–1.5 s yanında/önünde):
  stok modun gecikmesi. Modelle 55–69° (p95 119–157°, 4.1–7.2 s yanında/önünde).
- **Yakınlık ve kadraj:** modelle üç koşunun ikisinde 3 m'nin altı (en az 1.66 m, 1.1 s), kameranın yakın sınırının
  (3.96–3.98 m) içinde 1.0–4.3 s; mükemmel algılayıcıda en az 3.06–3.19 m, sınırın içinde 1.0–1.1 s (79 s civarındaki
  geri dönüşte). Kişinin tamamı kadrajda: modelle %40–81, mükemmel algılayıcıda %91–92.
- **Koşudan koşuya değişim modelde büyük:** koşu 2 kişiyi kaybetti (merkez kadrajda %45, en uzun kayıp 11.3 s, PX4
  kestirimi 8.6 s bayat, kestirim hatası ort. 5.98 m). Bu yüzden tek koşuyla sonuç söylenmez (karar 4).
- **Kalabalık park (dron Hold'da):** model hedefi görünürken %71–74 buluyor, seçim %49–67 doğru; seçilen kutu
  karelerin %7.4–18.9'unda başka bir kişide, %4.0–11.0'unda hedefle aynı kıyafetli kişide (m11'in ölçeceği şey).
- **İş A'nın etkisi B'de de görülüyor:** ULog'dan EKF yaw hatası ortalaması model koşularında 0.06–1.42°, hover'da
  (kalabalık park) −0.76…+0.60° (en çok 1.1°). Mükemmel algılayıcı koşularında ort. −1.5°, en çok 4.8–5.6°: takip
  başındaki yörünge dönüşü sırasında A'da da görülen geçici EKF sapması.
- RTF: `takip_yuruyen` model 0.97–0.98, hakem 0.95–0.96, `kalabalik_park` 0.87–0.91 (beş kişi ve ağaçlar; iki
  koşuda < 0.9 uyarısı). RTF < 1 iken sim saatiyle ölçülen süreler etkilenmez.

### Dron neden hedefin etrafında dönüyor, neden hep arkasında değil? (yeni başlayana)

Stok Follow Me'yi bir futbolcuya benzetelim. Antrenör ("PX4") oyuncuya şöyle der: "Topu sürenin hep **8 m arkasında** dur."
Ama antrenör topu sürenin **hangi yöne koştuğunu** iki şekilde bilir: ya oyuncu en az 1 m/s ile koşuyorsa (yönü
hızından anlar) ya da hiç bilmez. Bilmediği durumda aklında kalan son yönü kullanır; maçın başında bu yön
**kuzeydir** (koddaki sıfır).

1. **Mod açılınca:** PX4 kişinin kuzeye gittiğini varsayar. "Arkası" güney olur; dron, kişinin batısından (kalktığı
   yer) kuzeyine, oradan doğusu üzerinden güneyine doğru kişinin etrafında döner. Kişi daha yürümedi bile.
   "Mükemmel algılayıcı" koşularında PX4 rotayı kişi yürüyene kadar ≈ 37 s kuzey varsaydı ve dron bu sırada
   kişinin etrafında ≈ 200° döndü (1. gereksiz dönüş).
2. **Kişi dururken:** Model kişiyi her karede biraz farklı yerde bulur (kutu kenarları ±birkaç piksel = yerde ±0.5–1 m).
   PX4'ün hedef kestiricisi bu sıçramaları "kişi hareket ediyor" diye 1 m/s'yi aşan sahte hızlara çevirir ve rotayı
   rastgele yönlere günceller (koşularda rota kayıt başladıktan 2 s sonra kuzeyden ayrıldı ve −170°, +10°, 180°, −70°
   arasında atladı). Her yeni rota yeni bir "arka" demektir: dron duran kişinin etrafında ileri geri **salınır**
   (üç koşuda 629–699° tarandı). "Mükemmel algılayıcı"da (`--los hakem`) bu titreşim yok; orada yalnız 1. maddedeki
   dönüş görülür.
3. **Kişi yürümeye başlayınca:** Rota (örneğin doğu) güncellenir; "arka" bu kez batı olur ve dron yeniden döner
   (2. gereksiz dönüş; mükemmel algılayıcıda ≈ 100°). Oysa dron kalktığı yerde zaten kişinin batısındaydı: hiç dönmeseydi yürüyüşte tam arkasında olacaktı.
4. **Köşelerde:** PX4 kişinin konumunu en sık yarım saniyede bir alır ve süzer; kişi döndüğünde PX4 bir süre "düz
   gidiyor" sanar, dron kişinin yanına hatta önüne geçer (aşma). Kişi kadrajdan çıkabilir, kilit düşebilir.
5. **Dönüş hızı sınırlı:** PX4 hedefin etrafındaki dönüşü yumuşatır (8 m'de 180° ≈ 7 s). Hızlı yön değişimine yetişemez.
6. **Yakın geçiş:** Model kişiyi birkaç kare göremezse PX4 son hızla öngörür; kişi geri dönmüşse dron onun üstünden
   geçer. 45° kamera 8 m yükseklikte yeri ancak ≈ 3.9 m önünden itibaren gördüğü için kişi bundan yakındayken
   ayakları kadrajın altında kalır, kutu kesilir, konum hesabı bozulur.

Bunların hiçbiri simin hatası değildir: PX4 v1.17.0'ın stok Follow Me kodu böyle yazılmış (spec "PX4 stok Follow Target
davranışı", satır numaralarıyla). Gerçek dronda da aynısı olur. Takımın kendi takip algoritması (Yusuf Kurt, m15) bu
yüzden yazılıyor; sim, ikisini aynı ölçütlerle karşılaştırmak için kuruldu.
### Karşılaşılan sorunlar (B)

- **Benim hatam, `yok` kaynağında rapor yazılmadan çıkış:** `senaryo._geometry_log_lines` `FLW_TGT_DST` metnini
  `follow_distance` None iken de biçimliyordu (`TypeError`); `kalabalik_park`'ın ilk koşusu rapor yazmadan çıktı ve
  `toplu.py` onu (doğru biçimde) "başlayamadı" sayıp yeniden denedi. Zincir durduruldu (yalnız kendi süreçlerim, temiz
  kapandı), hatayı yakalayan test yazıldı (`test_run_log_lines_of_every_tracking_source`), düzeltildi ve
  `kalabalik_park` baştan koşuldu. Ders: `toplu.py`'nin "başlayamayan koşu" sayımı bir kod hatasını da yeniden dener;
  çıkış kodu 1 ve ozet yoksa günlükte `Traceback` aranmalı (B'de değiştirilmedi, "Açık kararlar"da).
- **`takip_yuruyen` ×3 bu düzeltmelerden önce koşuldu:** ölçümleri aynı koddan geçti (hata yalnız `yok`'un özet
  satırındaydı); yalnız raporlarındaki "Takip zaman çizelgesi" lejantı eski yerinde (uzak sınır çizgisinin üstünde),
  sonradan grafiğin üstüne taşındı. Örnek rapor ve animasyon son kodla koşulan ayrı bir koşudan.
- **Makine çalışma sırasında yeniden başladı** (kullanım sınırı arası): scratchpad'deki A yaması ve yardımcı betikler
  silindi; A yaması paylaşımlı bir klonda yeniden üretildi (kullanıcının reposuna ve index'ine dokunulmadan) ve HEAD'e
  uygulanabildiği denetlendi. Sonuç klasörleri ve A'nın grafiği yerindeydi.

### Kalan sim-gerçek farkları (B'nin ölçtükleri için)

- **Hakem kusursuzdur:** "arkada kalma", "kadrajda" ve mesafe Gazebo'nun gerçek konumlarıyla ölçülür; gerçek uçuşta
  bunların yerini RTK GPS'li bir hedef ya da yer kamerası tutmalı (m17/m25).
- **Hedefin hareketi:** insan modeli kayıtlı bir yolu izler (`yuruyus.py`; hız ve yol dalgalanması tohumlu); gerçek
  insan dronun yaklaşmasına tepki verebilir, aniden durup dönebilir. Köşe davranışı senaryoya bağlıdır.
- **Yakın görüş sınırı düz uçuş içindir:** gerçekte dron ivmelenirken burnunu 10–25° eğer, sınır kayar; piksel
  izdüşümüne dayanan ölçütler (`ayak_kadrajda_orani`, `hedef_kadrajda_orani`) eğimi zaten içerir.
- **Konum gürültüsü PX4'ün rotasını oynatıyor:** simde konumun titreşimi yalnız model kutusundan gelir (gz_bridge'in
  GPS gürültüsü küçük, rüzgâr yok); gerçekte M8N GPS ve gövde titreşimi eklenir, rota daha da oynayabilir.
  `--los hakem` (gürültüsüz konum) alt sınırı gösterir.
- Model laptop CPU'sunda (v0.2); Hailo'daki gecikme ve kaçırma başka olur (m08).

### Açık kararlar ve bekleyenler

- **3 m uyarısının kesin eşiği** ve en az mesafe için bir başarı ölçütü: m01'e öneri (Hüseyin).
- **Stok parametrelerle iyileşir mi:** 9.8'de (`FLW_TGT_RS`, `FLW_TGT_MAX_VEL`), 3'er koşu.
- **Gerçek araçta `follow_target*` kaydı** (karar 5, 12.11): şimdi çözülmez, açık konu (spec "Açık Konular").
- **Yanlış kişiye atlama süzgeci** (karar 2): m06'ya eklenmedi, m11'de (Ortatepe); sim ölçüyor
  (`yanlis_kisi_orani`, `kilit_kaybi_sayisi`, `px4_kestirim_*`).
- **`toplu.py`'nin yeniden deneme kuralı:** bir kod hatası da "başlayamadı" görünür (yukarıda); `Traceback` görülen
  koşuyu yeniden denememek gerekebilir (karar kullanıcıda; şimdilik her deneme listelenir, günlük `kosu_<i>.log`'da).
- **Manyetometre (A):** kararın sözünden farklı yol, onay bekliyor.

### Commit ayrımı (A ve B aynı dosyalara dokundu)

A'nın dosyaları yalnız A'nındır: `tez/sim/server.config`, `tez/sim/parametreler/sim.params`,
`tez/sim/worlds/duz_alan.sdf`, `tez/sim/worlds/cayir.sdf`, `tez/sim/testler/test_manyetometre.py`. Ortak dosyalarda
A'ya ait olanlar:

| Dosya | A'nın kısmı | Geri kalanı B |
|---|---|---|
| `spec.md` | "Varsayımlar" 6'daki "Manyetik alan (7. grup, iş A …)" maddesi; "Açık Konular"daki "Simdeki manyetik alan" maddesi; Dosya Planı'ndaki `server.config` … `test_manyetometre.py` satırı | "Ölçüt Tanımları" (tablo, "Çok koşu", "PX4 stok Follow Target davranışı"), 9. madde notu, Dosya Planı (`olcum.py`, `toplu.py`), Test Planı, diğer Açık Konular |
| `tasks.md` | 7.A satırı | 7.0–7.6, 9. grup eklemeleri |
| `README.md` | "PX4 tarafı"ndaki "Manyetometre" maddesi; Dosyalar'da `server.config` satırındaki "ve manyetometresiz" | Durum, çıktılar tablosu, "Ölçütler, rapor ve çok koşu", araçlar satırı |
| `kabul-kosulari.md` | "7 (A)" satırları | "7 (B)" satırları |
| `gorev-grubu-07.md` | Dosyanın A hâli (başlık + "İş A" + A'nın "Kendin dene"si) | "Durum" satırı, "İş B" bölümü, birleşik "Kendin dene" |

A'nın tam hâli yama olarak: `~/Desktop/Follow/3_m06_Simulasyon/Deneme/gorev7_is_A.patch` (HEAD `aac9f18f9c`'ye karşı;
`git apply --cached` ile önce A commit'lenir, kalan değişiklikler B'dir).

### Görseller (repo dışı)

`~/Desktop/Follow/3_m06_Simulasyon/Deneme/`:

| Dosya | Ne |
|---|---|
| `gorev7_stok_followme_kusbakisi_hakem.mp4` | **Stok Follow Me'nin mekanizması, temiz hâliyle** (`gorev7_B_takip_yuruyen_hakem_x3/kosu_1`, "mükemmel algılayıcı", yarı hız, VLC'de ] ile gerçek hız). Kuşbakışı harita: kişi (mavi) ve yürüdüğü yön, dron (turuncu üçgen, burun) ve son 15 s'lik izi, kameranın yerde gördüğü alan, 3 m halkası (kırmızı) ve kameranın yakın görüş sınırı (gri), dronun olması gereken yer (yeşil yıldız: kişinin 8 m arkası), PX4'ün kişi kestirimi (mor kare) ve varsaydığı rota (mor ok), PX4'ün yörünge açısı hedefi (mor halka) ve nihai hedefi (mor ×: rota + 180°). Üstte o an ne olduğunu anlatan cümle; sağda mesafe, arkada kalma açısı hatası ve "hedef kamerada mı" grafikleri, hareketli imleçle |
| `gorev7_stok_followme_kusbakisi_model.mp4` | Aynısı **model kutusuyla** (`gorev7_B_takip_yuruyen_x3/kosu_1`, v0.2, CPU): kişi dururken PX4'ün rotası konum titreşimiyle oynuyor ve dron ileri geri salınıyor; köşede aşma, yakın geçiş |
| `gorev7_stok_followme_kusbakisi_hakem_kare.png`, `..._model_kare.png` | Animasyonlardan birer kare (yürüyüşün 15. saniyesi) |
| `gorev7_takip_zaman_cizelgesi.png` | Raporun yeni grafiği, `gorev7_B_takip_yuruyen_x3/kosu_1` (model; 78.6 s'de 1.66 m yakın geçiş, köşede aşma) için güncel rapor koduyla çizildi: mesafe (3 m, kameranın yakın/uzak sınırı, 8 m), arkada kalma açısı hatası, hedef kamerada (tamamı / merkezi / görünür) |
| `gorev7_px4_rota_ve_yorunge.png` | Raporun ikinci yeni grafiği, aynı koşu: PX4'ün varsaydığı rota − gerçek rota; PX4'ün yörünge açısı hedefi, dronun gerçek açısı ve olması gereken "arka" |
| `gorev7_3_kosu_dagilim.png` | 3'er koşunun dağılım tablosu: `takip_yuruyen` model, `takip_yuruyen` hakem, `kalabalik_park` (koşu koşu, ort., en az, en çok) |
| `gorev7_toplu_takip_yuruyen_ekran_*.png` | `toplu.html`'in ekran görüntüsü (ana ölçütler ve koşu noktaları) |
| `gorev7_rapor_ekran_*.png` | Örnek `rapor.html`'in yeni bölümleri (kontroller, gruplu ölçümler, grafikler, mod zaman çizelgesi, ayarlar) |
| `gorev7_ornek_rapor_takip_yuruyen.html` | Örnek `rapor.html` (`gorev7_B_ornek_takip_yuruyen`, son kod; resimler gömülü, tek dosya; Firefox ile açılır) |
| `gorev7_A_manyetik_alan_yaw_once_sonra.png` | İş A: EKF yaw hatası önce / sonra (3 + 3 koşu) |
| `gorev7_is_A.patch` | İş A'nın değişikliklerinin tamamı (ayrı commit için) |

Animasyonlar repo dışında, scratchpad betiğiyle üretildi (`toplu`/`senaryo` çıktılarını okur; matplotlib kareleri
ffmpeg 6.1.1'e borudan, `libx264`, `yuv420p`, `+faststart`; video üretme yolu 6. grupla aynı). Repo kodu video
üretmez (MP4 8. grupta).

---

## Kendin dene

Bu bölümdeki her şey bilgisayarında hazır: paketler kurulu, model dosyası yerinde, PX4 derli.

**Başlamadan:** Terminal açmak için **Ctrl+Alt+T**'ye bas. Aşağıdaki gri kutulardaki komutları kopyala, terminale
**Ctrl+Shift+V** ile yapıştır (terminalde Ctrl+V çalışmaz) ve **Enter**'a bas. Bir komutu yarıda kesmek için
**Ctrl+C**.

### 1. Hazırlık (her yeni terminalde bir kez)

```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot
P=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python
D=~/Desktop/Follow/3_m06_Simulasyon/Deneme
```

Bir şey yazmaz; bu normal.

### 2. Stok Follow Me neden salınıyor: kuşbakışı animasyon

```bash
vlc $D/gorev7_stok_followme_kusbakisi_hakem.mp4
```

Önce "mükemmel algılayıcı" (kişinin gerçek konumu PX4'e gidiyor, gürültü yok). Solda kuşbakışı harita (kuzey yukarı):

- **Mavi nokta** kişi, mavi ok yürüdüğü yön; **turuncu üçgen** dron (sivri ucu burnu), turuncu çizgi son 15 s'lik yolu.
- **Yeşil yıldız**: dronun olması gereken yer, kişinin 8 m arkası (kişi yürürken).
- **Mor kare** PX4'ün "kişi burada" dediği yer, **mor ok** PX4'ün kişinin gittiğini sandığı yön, **mor halka** PX4'ün
  dronu şu an gönderdiği yer, **mor ×** PX4'ün nihai hedefi (rotanın 180° tersi).
- **Kırmızı kesikli halka** 3 m (uyarı), **gri kesikli halka** kameranın yakın görüş sınırı (≈ 4 m): dron bunun
  içine girerse kişinin ayakları görüntüden çıkar. Açık mavi dörtgen kameranın yerde gördüğü alan.
- Üstte o anda ne olduğunu anlatan bir cümle; dron kameranın yakın sınırının ya da 3 m'nin içine girince cümle
  **kırmızı** olur ("kişinin ayakları kadrajdan çıkıyor"). Sağda mesafe, arkada kalma açısı hatası ve "hedef kamerada
  mı" grafikleri (siyah çizgi şimdiki an).

Bak: mod açılınca mor ok **kuzeyi** gösteriyor (kişi duruyor ama PX4 kuzeye gittiğini varsayıyor), mor × kişinin
güneyinde, dron oraya doğru kişinin etrafında dönüyor (1. gereksiz dönüş). 60. saniyede kişi doğuya yürüyünce mor ok
doğuyu, mor × batıyı gösteriyor ve dron yeniden dönüyor (2. gereksiz dönüş). Köşelerde (≈ 72 s ve ≈ 79 s) mor ok
kişinin yeni yönüne geç dönüyor; dron kişinin yanına/önüne geçiyor (sağda arkada kalma hatası 90°'nin üstüne çıkar).

Sonra gerçek model kutusuyla:

```bash
vlc $D/gorev7_stok_followme_kusbakisi_model.mp4
```

Kişi dururken mor ok sürekli yön değiştiriyor: model kişiyi her karede biraz farklı yerde bulduğu için PX4 kişinin
hareket ettiğini sanıyor. Dron kişinin etrafında ileri geri salınıyor; kullanıcının videoda gördüğü buydu. ≈ 78–79
s'de (videoda ≈ 1:50) kişi kuzeyden batıya dönerken dron onun 1.7 m yakınından geçiyor: cümle kırmızı, kişi kadrajın
dışında.

VLC kısayolları: **Boşluk** duraklat/sürdür, **E** bir kare ileri, **Shift+→ / Shift+←** 3 s ileri/geri, **]** / **[**
hızlandır/yavaşlat (videolar yarı hızdadır; ] ile gerçek hıza çıkar), **F** tam ekran. VLC'nin uçbirime yazdığı
"Timestamp conversion failed" satırları VLC 3.0.20'nin kendisinden gelir, video sağlamdır.

### 3. Grafikler

```bash
xdg-open $D/gorev7_takip_zaman_cizelgesi.png
xdg-open $D/gorev7_px4_rota_ve_yorunge.png
xdg-open $D/gorev7_3_kosu_dagilim.png
xdg-open $D/gorev7_A_manyetik_alan_yaw_once_sonra.png
```

- **Zaman çizelgesi:** üstte dron–hedef mesafesi (kırmızı kesikli 3 m, gri kesikli kameranın yakın sınırı, turuncu
  8 m), ortada arkada kalma açısı hatası (0° = tam arkasında, 90° = yanında, 180° = önünde), altta kişinin kamerada
  görünüp görünmediği.
- **PX4 rota ve yörünge:** üstte PX4'ün varsaydığı rota (mor) ile kişinin gerçek rotası (mavi); altta PX4'ün dronu
  göndermek istediği açı (mor), dronun gerçek açısı (turuncu), olması gereken "arka" (mavi).
- **3 koşu dağılımı:** üç senaryo grubunun (model ile Follow Me, mükemmel algılayıcıyla Follow Me, kalabalık park)
  her ölçütü koşu koşu, ortalama, en az, en çok.
- **Manyetik alan (A):** solda eski, sağda yeni EKF yaw hatası.

### 4. Raporu aç

```bash
firefox $D/gorev7_ornek_rapor_takip_yuruyen.html
```

Yeni bölümler: en üstte **"Kontroller ve uyarılar"** (sarı: 3 m uyarısı ve kameranın yakın sınırı), sonra gruplu
**"Ölçümler"** (önce takip: mesafe ve kadraj, "hedefin arkasında kalma ve yörünge (stok Follow Me davranışı)"; sonra
model, LOS, zaman), **"Grafikler"** (ilk ikisi yeni), **"Mod zaman çizelgesi"** ve **"Ayarlar"** (model dosyasının
sha256'sı, PX4'e yüklenen her parametre ve PX4'ten geri okunan değeri). Ekran görüntüleri: `$D/gorev7_rapor_ekran_*.png`.
Üç koşunun özet sayfası:

```bash
firefox ~/Desktop/Projects/Auto-Follow/Autopilot/tez/sim/sonuclar/gorev7_B_takip_yuruyen_x3/toplu.html
```

### 5. Kendin koştur (pencere yok)

Önce açık bir sim olmadığından emin ol (iki satır da bir şey yazmamalı):

```bash
pgrep -x px4
pgrep -f "^gz sim"
```

Tek koşu (~2 dakika):

```bash
$P tez/sim/araclar/senaryo.py --senaryo takip_yuruyen --ekransiz
```

Sonda "Takip (follow_me): ..." satırları yeni ölçütleri yazar (en az mesafe, 3 m altı süre, kameranın yakın sınırı,
arkada kalma hatası, kişi dururken dronun etrafında döndüğü açı). Aynı senaryoyu 3 kez koşup dağılımını almak (~6.5
dakika):

```bash
$P tez/sim/araclar/toplu.py --senaryo takip_yuruyen --tekrar 3
```

"Mükemmel algılayıcı" ile aynısı: komutun sonuna `-- --los hakem` ekle. Sonuç klasörünün yolu en son satırda yazar;
`toplu.html`'i Firefox'ta aç.

### 6. Kontroller

```bash
$P -m pytest tez/sim/testler -q
tez/pin/verify_pin.sh --worktree
tez/sim/araclar/f0_kabul.sh
tez/sim/araclar/f1_kabul.sh
```

Beklenen: `211 passed`; `KILIT SAGLAM (v1.17.0)`; F0 (~1 dakika) ve F1 (~4 dakika) sonunda `SONUÇ: GEÇTİ`.

### Bir şey ters giderse

| Mesaj | Ne yapmalı |
|---|---|
| `Zaten çalışan bir PX4 veya Gazebo var` | Açık simi kendi terminalinde Ctrl+C ile kapat ya da bitmesini bekle |
| `toplu.py`: "Koşu N başlayamadı (altyapı hatası), yeniden deneniyor" | Kendiliğinden yeniden dener; tekrar ederse `kosu_N.log`'da `Traceback` var mı bak |
| Raporda sarı "3 m altına indi" | Hata değil, ölçülen bir uyarı: stok Follow Me kişinin çok yakınından geçti |
| Raporda `RTF ... (< 0.9)` uyarısı | Beklenen (model işlemciyi paylaşıyor); tarayıcı gibi ağır programları kapatmak yardımcı olur |
| Açılışta "Preflight Fail: Found 0 compass" | Birkaç saniye görülür (PX4'ün pusulası ilk GPS'i bekler), sonra kaybolur |
