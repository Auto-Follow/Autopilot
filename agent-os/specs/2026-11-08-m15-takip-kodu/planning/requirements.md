# Spec Gereksinimleri: M15 — Body frame hedef vektöründen PWM'e: PX4 takip kodu

- **Görev:** https://github.com/Auto-Follow/Auto-Follow/issues/6 (yol haritası madde 15; devamı 13 ve 16). Son teslim **2026-11-15**.
- **Repo / dal:** Autopilot, `ozellik/m15-takip-kodu`. Spec klasörü: `agent-os/specs/2026-11-08-m15-takip-kodu/`.
- **Durum:** Shape-spec tamamlandı (2026-11-09). Aynı gün shape-spec sonrası konuşmada açık kalan maddeler karara bağlandı ve bu dosyaya işlendi (KG "Shape-spec sonrası, write-spec öncesi"). Sonraki aşama: `write-spec`; **kullanıcı onay vermeden başlamaz.**
- **Bütün sistemi anlatan rapor:** `../rapor.md`.
- **Kaynaklar (bu dosya bunlardan derlendi, yeni karar içermez):**
  - `planning/raw-idea.md`: görevin ilk tanımı ve issue #6 kabul kriterleri.
  - `planning/tur1-cevaplar.md`: kısa karar tablosu.
  - `planning/karar-gunlugu.md`: kararların hikâyesi, seçenekler, gerekçeler ve kanıtlar. **Asıl kaynak budur.** Bir karar sonradan güncellendiyse son kayıt geçerlidir (ör. 8.2 → D; L2 → kendi uORB mesajımız).
  - `planning/visuals/01-ust-seviye-akis.md`, `planning/visuals/02-px4-detayli-akis.md`.
  - Çatı repo: `../agent-os/product/` (misyon, yol haritası, teknoloji yığını) ve `../agent-os/standards/`.
- **Kaynak gösterimi:** `dosya:satır` biçimindedir ve bu repodaki PX4 v1.17.0 içindir. Çatı dosyaları `../agent-os/...` ile başlar. "KG" = `planning/karar-gunlugu.md`.
- **Etiketler:** **Karar** = kullanıcı açıkça seçti. **Karar (öneri kabul)** = kullanıcı Claude'un önerisini kabul etti; sorun çıkarsa ilk gözden geçirilecek kararlar bunlardır (KG "Kullanıcının notu"). **Varsayım** = ortak spec (ICD, frame) yazılana kadar geçici. **Açık** = henüz karara bağlanmadı. **(doğrulanacak)** = kaynakta kanıtlanamadı, SITL/donanımda ya da write-spec'te doğrulanacak.

---

## 0. Başlangıç açıklaması

`planning/raw-idea.md`'den aynen:

> - Girdi body frame'deki hedef vektörüdür. Sıfırdan kontrolcü yazılmayacak; yalnızca **istenen durumu üreten guidance katmanı** yazılacak. Hız, konum, attitude ve rate kontrolü, mikser ve PWM çıkışı PX4'ün kendi zincirinde kalır.
> - Zincir: FC'ye gelen body FRD LOS → guidance kodu (frame dönüşümü, hedef konumu, guidance) → PX4 setpoint → PX4 kontrol zinciri → PWM.
> - Dahil: entegrasyon kararı ve gerekçesi (değerlendirilen seçenekler dahil); guidance kodu; SITL'de sentetik vektörle drone'un tepki verdiğini gösteren test (ne verildi, drone ne yaptı, ULog adı); geçersiz/eski veri için basit güvenli davranış.
> - Hariç: ayrıntılı failsafe ve mod çıkış akışının tamamı (m16); nihai guidance yasası ve ayarı (m13); Pi tarafı ve ICD.
> - Varsayım: girdi body FRD frame'de hedef yönünü gösteren LOS birim vektörü; mesafe düz dünya kabulü ve irtifadan. Mesaj tipi/frekans/zaman damgası ICD'de (madde 3–5) belirlenecek. Eksenler Yusuf Ortatepe'nin m10 çalışmasıyla eşlenecek.

---

## 1. Amaç ve kapsam

### 1.1 Sade anlatım: ne yapıyoruz?

Drone'daki Raspberry Pi kamerada insanı bulur ve Pixhawk'a yalnızca bir **yön** gönderir: "hedef, drone'a göre şu tarafta" (body FRD LOS birim vektörü). M15'te Pixhawk'ın içine yazılacak kod bu yönü alır ve:

1. hedefin yerde nerede olduğunu hesaplar,
2. drone'un hangi hızla, hangi yöne gitmesi ve burnunu nereye çevirmesi gerektiğine karar verir (**guidance**),
3. bu isteği PX4'e verir.

Gerisini PX4 kendisi yapar: hız → eğilme → açısal hız → motor karışımı → PWM → motorlar. Kontrolcü yazılmaz; yalnızca "ne istendiğini" söyleyen katman yazılır (KG "Genel resim").

### 1.2 Kapsam kararı (Soru 1, **Karar: 1-a**)

- Yol haritasında m15 küçük bir iştir (`S`). Doğrulaması yalnızca "seçilen yaklaşımın en küçük iskeleti SITL ve Pixhawk 6C hedeflerinde derlenir" (`../agent-os/product/roadmap.md:37`). Çalışan guidance ve SITL'de takip, yol haritasında m16'nın (`XL`) içindedir (`../agent-os/product/roadmap.md:38`).
- Issue #6 ise ayrıca çalışan guidance kodu, SITL'de drone'un tepki verdiğinin gösterilmesi ve basit güvenli davranış istiyor.
- **Bu spec issue #6'yı izler**, çünkü görevi veren ve teslim tarihini belirleyen odur. Yol haritasındaki m15 tanımından bu fark bilerek yapılmıştır (KG Soru 1).
- Spec kapsamı: iskelet + ilk guidance (hız tabanlı yasa + alpha-beta filtresi) + basit güvenli davranış (hedef kaybında D, Hold dahil) + log mesajı ve log sözlüğü + kısa birim testleri + SITL senaryoları S1–S7.

### 1.3 m16'ya kalanlar (başlangıç listesi)

Bu liste uygulama sırasında güncellenir. Süre yetmeyen her iş buraya yazılır (KG Soru 14.5).

- Ayrıntılı failsafe ve mod çıkış akışının tamamı (`raw-idea.md:8`).
- C seçeneği: Hold'dan sonra modülün takibe kendiliğinden dönmesi (reddedildi; istenirse m16'da yeniden konuşulur, KG Oturum 2).
- İş sırasında (bkz. 9.4) yetişmeyen adımlar.

---

## 2. Kabul kriterleri (issue #6, "Bitti sayılması için")

`raw-idea.md:9`'dan:

1. Spec klasöründe şemalar var (`planning/visuals/`).
2. PX4'te neyin nereye bağlandığı ve neden yazılmış.
3. Test sonucu yazılmış: **ne verildi, drone ne yaptı, log adı.**
4. Kod `make px4_sitl` ile derleniyor.
5. CI'da `verify-pin`, `derleme-sitl`, `derleme-fmu-v6c` yeşil.
6. PX4'e yeni dosya eklendiyse yolu PR'da gösteriliyor.

Bu spec'in kararlarından gelen ek koşullar:

- Modül Pixhawk 6C firmware'ine de girer; derleme çıktısındaki flash kullanımı spec'e yazılır (Karar 3.1-ii).
- Her SITL testinin ULog dosyası `~/Desktop/AUTO-FOLLOW LOG/` klasörüne kopyalanır ve dosya adı spec'e yazılır (Karar L4).
- Log sözlüğü kodla aynı commit'te güncel tutulur (Karar L2).
- PR açıklamasına `Closes Auto-Follow/Auto-Follow#6` yazılır (görev kaydı).

---

## 3. Kararlar

### 3.1 PX4 entegrasyonu: external mode modülü (Soru 2, **Karar: 2-a**)

- **Ne:** Kod, PX4'ün içinde kendini **yeni bir uçuş modu** olarak kaydettiren bir modüldür. Örnek kalıp PX4'ün kendi `mc_nn_control` modülüdür (`src/modules/mc_nn_control/mc_nn_control.cpp:135-142`). Pilot bu modu QGC'den ya da RC'den seçer.
- **Nasıl çalışır:** Mod aktifken PX4 kendi uçuş görevlerini (FlightTask) durdurur (`FlightModeManager.cpp:139-144`). Modül `trajectory_setpoint` yayınlar. PX4'ün `mc_pos_control` → `mc_att_control` → `mc_rate_control` → `control_allocator` zinciri bunu motorlara kadar taşır.
- **Neden:** Kilitli dosyalara en az dokunan, kodu PX4'ün içinde tutan, PX4'ün kendi kontrol zincirini ve failsafe'ini kullanan seçenek budur.
- **Reddedilenler:**
  - (b) Yeni FlightTask: commander, mesaj tanımları, mod yöneticisi gibi birçok kilitli dosyayı değiştirmeyi gerektirir ve flash'ı daha çok doldurur.
  - (c) Offboard: guidance Pi'de çalışır, kod PX4'ün içinde olmaz; issue #6 ve misyonla çelişir.
  - (d) PX4'ün Follow Me modu: GPS konumu bekler, bizim girdimiz bir yön.
- Kaynak: KG Soru 2.

### 3.2 Kodun yeri (Soru 3, **Karar: 3-a**; 3.1 **Karar: (ii)**)

- Modül PX4'ün normal modül yerinde durur: `src/modules/<ad>/`. Çatı standardının öngördüğü düzen budur (`../agent-os/standards/px4/modules.md:3, 8`).
- Modül iki kart dosyasına `CONFIG_MODULES_<AD>=y` satırıyla açılır: `boards/px4/sitl/default.px4board` ve `boards/px4/fmu-v6c/default.px4board`.
- **Pixhawk 6C'ye de girer (3.1-ii).** Kullanıcının gerekçesi: "Asıl amaç her şeyi 6C'ye derlemek, projeyi gerçek hayatta yapmak; ondan önce SITL'de test edip en iyi hâlini 6C için derleyeceğiz."
- Reddedilen: (b) kilit dışındaki `tez/` klasöründe PX4'ün dış modül özelliği (`EXTERNAL_MODULES_LOCATION`).
- Bu yollar kilit listesinde değil; bkz. Bölüm 6.
- Kaynak: KG Soru 3 ve Soru 3.1.

### 3.3 Modülün iç yapısı (Soru 4, **Karar (öneri kabul)**)

- **İş kuyruğu:** `nav_and_controllers`. PX4'ün kontrolcüleri ve `mc_nn_control` da bu kuyruğu kullanır (`mc_nn_control.cpp:65`).
- **Sabit hızlı çevrim:** `ScheduleOnInterval`, önerilen ~50 Hz (kesin değer write-spec'te yazılır). Gerekçe: Modül veri gelmese de döner; böylece "veri geldi mi, eskidi mi" kontrolü yapılır ve güvenli davranışa geçilir. Yalnızca veri geldiğinde dönseydi, veri kesilince modül de durur ve kesintiyi fark edemezdi.
- **Guidance hesabı ayrı bir sınıfta**, uçuş donanımından bağımsız tutulur. Böylece bilgisayarda otomatik birim testleriyle sınanabilir (`../agent-os/standards/testing/test-writing.md:6`).
- Kaynak: KG Soru 4.

### 3.4 Girdi mesajı: `DEBUG_FLOAT_ARRAY` → `debug_array` (**Karar**, 2026-11-09; ilk karar 5-a `DEBUG_VECT`'in yerine geçer; **Varsayım**)

- **Kullanıcı:** "Vision'daki arkadaşım bana body frame verisi ve timestamp gönderecek; girdimiz bu."
- **Neden `DEBUG_VECT` değil:** PX4 v1.17.0, MAVLink debug mesajlarının kendi zaman alanını atıp yerine varış anını yazıyor (`src/modules/mavlink/mavlink_receiver.cpp:2804`, `:2822`). `DEBUG_VECT`'in veri kısmı yalnızca x, y, z olduğu için Pi'nin zaman bilgisi FC'ye taşınamaz. `DEBUG_FLOAT_ARRAY`'in veri kısmı 58 sayı (`msg/DebugArray.msg`), zaman bilgisi bu kısımda taşınır.
- Pi'den gelen veri MAVLink `DEBUG_FLOAT_ARRAY` ile gelir ve PX4'te uORB `debug_array`'e dönüşür (`mavlink_receiver.cpp:2814-2832`). Mesaj adı (`name`): **`AF_LOS`**.
- **Kutu yerleşimi (Varsayım; ICD m3–5 yazılınca güncellenir):**

| Kutu | İçerik | Birim | Ne işe yarar |
|---|---|---|---|
| `data[0..2]` | LOS x, y, z (body FRD birim vektör) | — | Asıl girdi |
| `data[3]` | Yaş: görüntünün çekildiği andan gönderime kadar geçen süre | ms | Verinin gerçek eskiliği |
| `data[4]` | Sıra numarası (her mesajda 1 artar) | — | Tekrar eden ya da sırası karışmış mesajı yakalamak |
| `data[5]` | Hedef var (1) / yok (0) | — | Pi "hedefi kaybettim" dediği anda bilmek |

- **Neden "yaş":** Pi'nin saati ile Pixhawk'ın saati aynı değil. Pi "X ms önce çekildi" derse Pixhawk kendi saatiyle hesaplar: çekim anı ≈ varış anı − X. Seri hat gecikmesi birkaç ms olduğu için ihmal edilir. Bu biçim Vision tarafıyla (Yusuf Ortatepe) konuşulacak (Bölüm 10).
- **Zaman bilgisiyle yapılanlar (m15):** Bkz. 3.13.
- **Kalan sınırlamalar:**
  - `debug_array` ortak bir topic; başka yazılımlar da yayınlayabilir. Bu yüzden `name` = `AF_LOS` olanlar alınır.
  - İşleyici, `CONSTRAINED_FLASH` açılırsa derleme dışı kalır (`mavlink_receiver.cpp:284-305`, `:2748-2833`). m14 yapılırken bu bilinmelidir.
- Yeni MAVLink mesajı eklenmez (`../agent-os/standards/px4/uorb-params.md:15-16`).
- Kaynak: KG Soru 5; KG "Shape-spec sonrası" → "Girdi mesajı — Karar".

### 3.5 PX4'e verilen istek: `trajectory_setpoint` (Soru 7, **Karar: 7-a, mutlak yaw**)

- `trajectory_setpoint` ile: **yatay hız** (`velocity[0..1]`) + **irtifa** (`position[2]`) + **mutlak yaw** (burnun bakacağı açı). Diğer alanlar NaN bırakılır. PX4 bu karışımı geçerli kabul eder (`PositionControl.cpp:224-250`).
- Reddedilen: `goto_setpoint` ("şu noktaya git"); hız tabanlı yasaya uymaz.
- Mod aktifken her çevrimde setpoint yayınlanır. Mod aktif değilken setpoint yayınlanmaz; modül veriyi işlemeye devam edebilir (KG "Hedef kaybolunca ne olacak?", `tur1-cevaplar.md` "Mod kapalıyken").
- Kaynak: KG Soru 7.

### 3.6 Guidance (Soru 6)

#### 3.6.1 Ortak adım: yönden hedef konumuna

- Gelen yön (body FRD), drone'un eğikliği ve burun yönü kullanılarak dünyaya göre yöne (NED) çevrilir.
- Zemin düz kabul edilir; drone'un yüksekliğinden yatay mesafe bulunur. Örnek: 10 m yükseklikte (0.8, 0, 0.6) yönü → yaklaşık 37° aşağı bakış → yaklaşık 13.3 m yatay mesafe.
- Hedefin yerel NED konumu = drone'un konumu + bu yatay uzaklık. Küresel koordinat (GPS enlem/boylam) dönüşümü yapılmaz.
- Kaynak: KG Soru 6 "Ortak adım".

#### 3.6.2 Yasa: hız tabanlı (**Karar: 6-a**)

- Kural, hedefin yönünde:

  **istenen yatay hız = c × (kestirilen hedef hızı) + K × (yatay mesafe − istenen mesafe)**

- Hız en fazla **v_max** olur (kırpma).
- **İvme sınırı var (6.2, öneri kabul):** Hız isteği bir anda değil, en fazla belli bir ivmeyle değişir. Gerekçe: Ani hız isteği drone'u sert eğer; ilk uçuşlar için güvenlik.
- **İrtifa sabit tutulur.** Tutulan irtifa, moda girildiği andaki irtifadır (6.4).
- **Burun hedefe döner** (mutlak yaw); böylece hedef kadrajın ortasında kalır.
- **Hedef hızı katsayısı c (onaylandı):** Parametredir; 0 verilirse bu kısım kapanır. Gerekçe: Yalnızca mesafe farkına bakan yasa, yürüyen hedefin biraz gerisinde kalır; hedefin hızı eklenince bu açık kapanır.
  - **Dikkat:** SITL'de sabit bir yön gönderilirse sanal hedef drone'la birlikte hareket ediyormuş gibi görünür. Filtre "hedef de benim hızımla gidiyor" der ve drone v_max'a kadar kaçar (pozitif geri besleme). Bu yüzden **ilk sabit-yön testleri c = 0 ile yapılır.** c > 0 testleri için kapalı çevrim test gerekir (bkz. 3.10).
- Reddedilenler: (b) konum tabanlı (her ölçümde hedef noktası zıplar, drone sarsılır); (c) pure pursuit / PN (önleme yasaları, mesafe korumaz).
- Nihai yasa ve ince ayar m13'tür; bu spec ilk yasayı yazar.
- Kaynak: KG Soru 6, `tur1-cevaplar.md` madde 6.

#### 3.6.3 Filtre: kendi alpha-beta sınıfımız (**Karar: 6.1**)

- Ölçülen hedef NED konumu filtreye girer. Filtre konumu yumuşatır ve aynı anda hedefin hızını kestirir. **Alpha** ve **beta** parametredir.
- PX4'teki benzer filtre (`TargetEstimator`) doğrudan kullanılamaz: GPS'li `follow_target` topic'ine bağlı bir work item'dır (`src/modules/flight_mode_manager/tasks/AutoFollowTarget/follow_target_estimator/TargetEstimator.hpp:112, 210`). Yalnızca fikir kaynağıdır (`FLW_TGT_RS`, `src/modules/flight_mode_manager/tasks/AutoFollowTarget/follow_target_params.c:53`).
- Bu yüzden küçük, kendi alpha-beta sınıfımız yazılır (**onaylandı**). Donanımdan bağımsız guidance sınıfıyla aynı şekilde birim testine açıktır.
- Kullanıcının vurgusu: "Alpha-beta filtresinin girdisi ve çıktısı ve bunların analizi çok önemli." Filtrenin girdisi ve çıktısı loga yazılır (bkz. 3.9).

#### 3.6.4 İstenen mesafe: takip açısından (**Karar 6.4, öneri kabul**)

- Kullanıcının takip tasarımı: "Hedefi belli bir mesafeden, dünyayı düz kabul ederek, sürekli kadrajın ortasında tutarak takip edeceğim. Yükseklik sabit, aradaki açı sabit olacak."
- **Takip açısı** bir parametredir: hedefin kadraj ortasında durduğu aşağı bakış açısı. Kamera aşağı eğik monte edildiyse bu açı kameranın eğimidir.
- **istenen mesafe = irtifa / tan(takip açısı).** Örnek: 5 m irtifa, 30° → yaklaşık 8.7 m.
- Kamera eğimi Ahmet Kazalcı'nın m06 kamera montaj dokümanından gelecek. SITL için o zamana kadar bir değer seçilecek.

#### 3.6.5 Yaw koruması (**Karar 6.3, onaylandı**)

- Normal takipte hedef drone'un altına gelmez.
- Geçici durumlar için (hedef drone'a doğru koşarsa, moda girişte hedef çok yakınsa) koruma: **yatay mesafe ~1 m'nin altındaysa yaw değiştirilmez.** Kullanıcı: "mantıklı, olsun."

### 3.7 Bozuk veya eski veri (Soru 8, **Karar (öneri kabul)**)

- **Her gelen mesajda yapılan kontroller (8.1):**
  - Sayılar geçerli mi (NaN/sonsuz değil, `PX4_ISFINITE`)?
  - Vektörün uzunluğu 1'e yakın mı (birim norm toleransı)?
  - Mesajın adı (`name`) doğru mu?
  - Mesaj zaman aşımına uğradı mı (yaş < zaman aşımı)?
  - Yön yeterince aşağı bakıyor mu (en küçük aşağı açı)? Ufka yakın bir yön mesafeyi sonsuz yapar.
  - Hesaplanan mesafe makul mü (en büyük menzil)?
  - Drone'un kendi konum bilgisi (yerel konum) geçerli mi?
- Geçersiz mesaj **atılır**, `perf_counter` ile **sayılır** ve **hız sınırlı** olarak loglanır; guidance hesabına asla girmez (`../agent-os/standards/global/validation.md:7`).
- **Eşik değerleri (Karar, 2026-11-09):** Hepsi parametredir ve testlerden sonra QGC'den değiştirilir:
  - Vektör uzunluk toleransı `AF_NORM_TOL` = 0.1. İnce ayar değil, bozuk veri yakalayıcı.
  - En küçük aşağı bakış açısı `AF_MIN_DEP` = 10°, en büyük menzil `AF_MAX_RNG` = 40 m. Gerekçe: Açı küçüldükçe açıdaki hata mesafeye büyüyerek yansır. 5 m irtifada 1° hata, 30°'de ~0.5 m, 10°'de ~3 m, 5°'de ~10 m mesafe hatası demek.
  - Çevrim hızı parametre değildir; kodda sabit 50 Hz.
- **Ek kontroller (girdi `DEBUG_FLOAT_ARRAY` olduğu için):**
  - Sıra numarası öncekinden büyük mü (tekrar ya da geri giden mesaj atılır)?
  - Yaş, veri zaman aşımından küçük mü?
  - "Hedef var" bayrağı 1 mi?
  - Bu kontrollerle standarttaki tekrar/eski mesaj maddesi (`../agent-os/standards/global/validation.md:6`) karşılanır.
- **Süreler (Karar, 2026-11-09):** Veri zaman aşımı `AF_DATA_TOUT` = 0.5 s; dolunca "kayıp" başlar ve drone yerinde bekler. "Kayıp" başladıktan `AF_LOST_T` = 1.0 s sonra Hold'a geçilir (3.8). Toplamda son geçerli mesajdan 1.5 s sonra drone Hold'dadır. Gerekçe: Pi 10–30 Hz gönderecek, 0.5 s 5–15 kayıp mesaj demek; PX4 offboard kaybı da 1 s bekler (`COM_OF_LOSS_T`, `src/modules/commander/commander_params.c:340`). Pi "hedef yok" derse kayıp zaman aşımını beklemeden hemen başlar.
- Kaynak: KG Soru 8, `tur1-cevaplar.md` madde 8.

### 3.8 Hedef kaybı davranışı: D (kademeli) (**Karar**; kullanıcı "önemli" olarak işaretledi)

Bu karar `tur1-cevaplar.md`'deki ilk 8.2 kaydının ("hover yayınla, Hold isteği m16'ya") yerine geçer.

- **Kısa kayıp** (`T_kayip` dolmadan): Mod açık kalır. Modül **hover** yayınlar: mevcut konum + hız 0 + son yaw. Hedef yeniden görülürse takip **kendiliğinden sürer**.
- **Uzun kayıp** (`T_kayip` aşıldı): Modül `VEHICLE_CMD_SET_NAV_STATE` komutuyla **Hold** (`AUTO_LOITER`) ister (`src/modules/commander/Commander.cpp:936-944`). Hedef geri gelse de drone takibe **kendiliğinden dönmez**.
  - Pilot modu yeniden açar: QGC'den tek tıkla ya da RC anahtarını başka konuma alıp geri getirerek. Anahtarı yerinde bırakmak yetmez, çünkü RC mod isteği yalnızca anahtar konumu değişince gönderilir (`ManualControl.cpp:176-177`).
- **`T_kayip`** = `AF_LOST_T`, başlangıç 1.0 s. "Kayıp" durumu veri zaman aşımıyla (`AF_DATA_TOUT` = 0.5 s) ya da Pi'nin "hedef yok" bayrağıyla başlar; `AF_LOST_T` o andan itibaren sayılır.
- **Hedef görünmezken moda girilirse (Karar 5-a, 2026-11-09):** D aynen uygulanır; 1.5 s içinde geçerli hedef gelmezse Hold. Pratikte mod, hedef görünürken açılır. `can_arm_and_run` hedef yokken de `true` kalır; `false` olursa PX4 RTL'e düşer.
- **İlk test uçuşları:** `T_kayip` kısa tutulur (ör. 0.5–1 s); davranış pratikte B olur ("kayıpta hemen Hold, kendiliğinden dönüş yok"). Gerekçeler:
  - Model yanlış bir şeyi hedef sanırsa drone pilot onayı olmadan harekete geçmez.
  - Denenmemiş kodumuz yerine PX4'ün denenmiş Hold modu devreye girer.
  - QGC'de mod değiştiği için durum herkesçe görülür.
  - Güven arttıkça değer büyütülür. Her uçuşta kullanılan değer log/test planına yazılır.
- **Hold geçişi m15'te yapılır** ve SITL'de test edilir (S4: veri kesilir → hover → `T_kayip` sonra Hold).
- **Reddedilenler:**
  - C (Hold'dan sonra modülün takibi kendiliğinden yeniden açması): pilotun bilerek moddan çıktığını ayırt etmek zor; yanlış algılamayla birleşince drone onaysız harekete geçebilir. İstenirse m16'da konuşulur.
  - `can_arm_and_run = false` yolu ("ben çalışamıyorum" sinyali): PX4 Hold'a değil **RTL'e** düşer (`src/modules/commander/failsafe/failsafe.cpp:698-702`).
- **Mod kapalıyken:** Model ve modül veriyi sürekli işleyebilir, ama setpoint yalnızca mod aktifken yayınlanır. Mod kapalıysa takip olmaz.
- **(doğrulanacak), uçuş testlerine not:** RC çubuğuna dokununca external moddan çıkılıp çıkılmadığı (RC override) doğrulanmadı. İlk uçuş planında (m22/m25) pilotun RC'de her an Position moduna geçebileceği bir anahtar konumu bulunmalı.
- Kaynak: KG Oturum 2 "Hedef kaybolunca ne olacak?", `tur1-cevaplar.md` "ÖNEMLİ — Hedef kaybı davranışı".

### 3.9 Disarm durumda moda geçiş (Soru 9, gereksinim)

- **Kullanıcının gereksinimi:** "Arm edilmemişken de masa testleri için bu moda geçebilmem lazım."
- **Bulgu:** PX4 v1.17.0 disarm araçta her mod değişikliğine zaten izin veriyor: "Always allow mode change while disarmed" (`src/modules/commander/UserModeIntention.cpp:54-55`, `always_allow = force || !isArmed()`). Mod gereksinimleri (`canRun`) yalnızca araç arm iken kontrol edilir (`:58-59`).
- `mode_req_prevent_arming` moda geçişi engellemez, yalnızca o moddayken arm etmeyi engeller ("Mode not suitable for arming", `src/modules/commander/HealthAndArmingChecks/checks/modeCheck.cpp:196-205`).
- Disarm iken `mc_pos_control` motorlara bir şey göndermez; masada görülecek olan, modülün hesapladığı setpoint'tir.
- Mod kaydının ayrıntıları ve masa testi Açık (bkz. Bölüm 10).
- Kaynak: KG Soru 9, `tur1-cevaplar.md` "Bulgu: 9. madde".

### 3.10 Yükseklik (Soru 13, **Karar: (iii)**, flash'a sığarsa)

- Drone yüksekliği PX4'ün kendi irtifa tahmininden okunur: **`-vehicle_local_position.z`** (V4 = a).
- **Hedef yüksekliği** (hedefin bakılan noktası, ör. ayak mı gövde ortası mı; V5) ve **zemin ofseti**, ikisi de parametredir.
- Flash'a sığmazsa geri dönüş: (i), yalnızca hedef yüksekliği parametresi. Bir parametre flash'ta çok az yer kapladığı için büyük olasılıkla sığar; kesin durum 6C derlemesinde görülecek.
- Kullanıcı: "Flash'a sığdırabilirsek 3. seçenek en iyisi."
- **Formül (Karar, 2026-11-09):**
  ```
  yükseklik farkı  = drone yüksekliği (−z) − AF_GND_OFS − AF_TGT_HGT
  mesafe           = yükseklik farkı / tan(aşağı bakış açısı)
  istenen mesafe   = yükseklik farkı / tan(AF_TRK_ANG)
  ```
  Varsayılanlar: `AF_TGT_HGT` = 1.0 m, `AF_GND_OFS` = 0 m. Örnek: drone 10 m, açı 30°. Düzeltmesiz mesafe 17.3 m; hedef yüksekliği 1.2 m girilince 15.2 m. Düzeltme olmasa ~2 m hata olurdu. Zemin ofseti, hedefin yürüdüğü zemin kalkış yerinden farklı yükseklikteyse kullanılır (ör. 2 m yüksek tepe → 2).
- Kaynak: KG Oturum 2 Soru 13, `tur1-cevaplar.md` madde 13.

### 3.11 Loglama (L1–L4)

**Kullanıcının gereksinimi (önemli):** "Her durumu log kaydına almamız gerek. Bunun için ek kod yazmak gerekirse de yazalım. Alpha-beta filtresinin girdisi ve çıktısı ve bunların analizi çok önemli." Ek netleştirme: "Sözlük kesin olacak. Yazılan durumları logda **kendi adlarıyla** göreceğim."

- **Kural (bu spec ve sonraki her özelleştirme için):**
  - Yapılan her özelleştirmenin iç durumu loga yazılır.
  - Her log alanı için bir **log sözlüğü** yazılır: alan adı, anlamı, birimi, frame'i, hangi durumda ne değer aldığı. Sözlük spec klasöründe tutulur ve kodla birlikte güncellenir.
  - Kullanıcının örneği: Özelleştirilmiş Betaflight'taki "track hold" modu için `trk` önekli alan sözlüğü (ör. `trkAzErr` = azimut hatası). Bizim alan adları ve önekleri yazılırken kullanıcıya sorulur.
- **L2 — Karar: (b) kendi uORB mesaj tipimiz.** Alanlar logda kendi adlarıyla görünür. Modül her döngüde bu mesajı doldurur ve yayınlar. Kullanıcı: "Kilitli dosyalara böyle durumlarda dokunuruz, sıkıntı yok."
  - Gereken kilitli değişiklikler: yeni `msg/<Ad>.msg`; `msg/CMakeLists.txt`'e bir satır (mesaj listesi `msg/CMakeLists.txt:39`); `src/modules/logger/logged_topics.cpp`'ye bir `add_topic` satırı. Bkz. Bölüm 6.
  - **Geri dönüş:** Hüseyin reddederse (a) PX4'ün hazır `debug_array` mesajı (`msg/DebugArray.msg`, ad + 58 sayılık dizi) + sözlük. Bu durumda alanlar logda `data[0]`, `data[1]`… görünür; adlar ancak sözlükten ya da sözlüğü kullanan analiz script'inden gelir.
  - Reddedilen: (c) `debug_key_value` (alan başına bir mesaj; her döngüde çok mesaj gerekir, logger hepsini yakalamayabilir (doğrulanacak)).
  - Önceki ara karar "(a) şimdi, (b) sonra" bu kararla geçersizdir.
- **Log mesajı:** `msg/AutoFollowStatus.msg` → topic **`auto_follow_status`** (Karar, adlar 2026-11-09).
- **Her zaman kaydedilir (Karar 4, 2026-11-09):** `logged_topics.cpp`'deki varsayılan listeye eklenir. Kullanıcı ayrıca bir ayar açmaz: "Her zaman kaydedilsin, ekstra bir şey açmama gerek kalmasın."
- **Logda olması istenen içerik:**
  - Pi'den gelen ham girdi (LOS x/y/z, yaş, sıra no, hedef var), bu mesaja kopyalanır;
  - doğrulama sonucu ve atılan mesaj sayaçları;
  - filtrenin girdisi (ölçülen hedef konumu) ve çıktısı (kestirilen konum ve hız);
  - hesaplanan mesafe, istenen mesafe ve hız isteği;
  - durum (takip / kayıp-bekle / Hold istendi);
  - AUTO FOLLOW'un **mod numarası** (`nav_state` 23–30).

  Kesin alan listesi ve adları write-spec'te log sözlüğüyle birlikte kullanıcıya sorulur.
- **Kullanıcının sorusu:** "Logda her şeyi kendi isimleriyle göreceğiz değil mi?" Evet; `DEBUG_FLOAT_ARRAY` yalnızca taşıyıcıdır, logda bakılan `auto_follow_status`'un adlı alanlarıdır.
- **Varsayılan olarak zaten loga girenler** (kod gerekmez): `trajectory_setpoint` (bizim isteğimiz), `vehicle_status` (mod değişimleri, Hold), `vehicle_command` (Hold isteği), `vehicle_local_position`, `vehicle_attitude`, `vehicle_control_mode`, `actuator_motors` (`src/modules/logger/logged_topics.cpp:131-150, 214`).
- **L1 — Güncellendi (2026-11-09):** Debug bitini açmaya **gerek yok**. Ham girdi zaten `auto_follow_status`'a kopyalanıyor ve bu mesaj her zaman kaydediliyor. Ham `debug_array` yalnızca debug biti açıksa kaydedilir (`logged_topics.cpp:290-294`); ihtiyaç yok.
- **L3 — Karar:** `SDLOG_MODE` varsayılan kalır (0 = yalnızca arm iken log, `src/modules/logger/module.yaml:16-30`). Kullanıcı: "Masa testi yapacağımda parametreden 0/1 ayarlarım; bu zaten normal PX4 parametresi." Not: Bu parametre değiştikten sonra kart **yeniden başlatılmalı** (`logger/module.yaml:31`, `reboot_required: true`). SITL'de varsayılan 1'dir (`ROMFS/px4fmu_common/init.d-posix/rcS:180`).
- **Logların yeri** (kullanıcının gereksinimi: gerçek uçuşta 6C'nin SD kartı, simülasyonda laptop). PX4 bunu kendisi yapıyor, kod gerekmez:
  - Gerçek uçuş: `/fs/microsd/log/<tarih>/<saat>.ulg` (`src/modules/logger/logger.cpp:1296`).
  - SITL: `build/px4_sitl_default/rootfs/log/<tarih>/<saat>.ulg`.
- **L4 — Karar:** SITL logları `build/` içinde olduğu için `make clean` ile ya da en eski klasörler silinirken kaybolabilir (`SDLOG_DIRS_MAX` = 7, `ROMFS/px4fmu_common/init.d-posix/rcS:183`). Bu yüzden **her testten sonra** log, masaüstündeki **`~/Desktop/AUTO-FOLLOW LOG/`** klasörüne kopyalanır (klasör 2026-11-09'da açıldı). Repo dışında olduğu için kural 9 ile çelişmez. Spec'e log dosyasının adı yazılır.
- Kaynak: KG "Log kararları (L1–L4)" ve "L2 ve test kararları (kesin)".

### 3.12 Testler (Soru 10)

Kullanıcının çerçevesi: "Arkadaşım gerçek uçuş ortamına yakın bir simülasyon hazırlıyor; o bitince tamamen oraya geçeceğiz. O bitene kadar her şey bizde: kod yazımı bitince Gazebo'da en basit testten başlayıp oluşabilecek tüm durumları test edeceğiz."

- **10.1 — Birim testi (Karar: kısa tutulur).** Bilgisayarda, drone'suz, saniyeler içinde biten otomatik testler (GoogleTest, `../agent-os/standards/testing/test-writing.md:6-10`). Yalnızca temel hesaplar sınanır: mesafe/yön hesabı, hız yasası ve sınırları, bozuk veri, zaman aşımı. Süre kısıtlı olduğu için hemen SITL'e geçilir.
- **10.2 — SITL senaryoları S1–S7 (Karar).** Gazebo Harmonic'te, en basitten karmaşığa. Senaryo başlıkları `visuals/02-px4-detayli-akis.md`'deki (D) bloğundan alınmıştır (taslak; içerik write-spec'te bu spec'in kararlarına ve yeni adlara göre güncellenir):

  | # | Başlık | Bu spec'teki beklenti |
  |---|---|---|
  | S1 | Kayıt ve başlatma | Modül açılışta modu kaydeder, mod listede görünür |
  | S2 | Nominal takip | Sentetik yönle drone hedefe göre hız ve yaw üretir |
  | S3 | Mod seçimi ve çıkış | QGC ve RC ile giriş/çıkış; disarm iken geçiş |
  | S4 | Hedef kaybı | Veri kesilir → hover → `T_kayip` sonra Hold; `T_kayip` dolmadan veri dönerse takip sürer |
  | S5 | Girdi doğrulama ve güvenli taraf | Yanlış ad, NaN/Inf, norm dışı, eski, ufka yakın yön atılır ve sayılır |
  | S6 | RC kaybı | PX4 varsayılan davranışı gözlenir (doğrulanacak) |
  | S7 | Modül sağlığı ve fallback | Modül durur/donarsa PX4'ün davranışı gözlenir (doğrulanacak) |

  - **Açık çevrim** = sabit yön gönderilir. **Kapalı çevrim** = script yerde hayali bir hedef tutar ve drone'un konumuna göre gerçek yönü hesaplar. İlk sabit-yön testleri c = 0 ile yapılır; c > 0 testleri kapalı çevrimle yapılır (3.6.2).
  - Her senaryo için yazılacaklar: **ne verildi, drone ne yaptı, ULog adı** (kabul kriteri).
  - Standart gereği: mümkünse `HEADLESS=1`; her testten sonra SITL parametre dosyası sıfırlanır (`../agent-os/standards/testing/test-writing.md:13-15`).
- **10.3 — Değerlendirme:** ULog + pyulog script'iyle ölçülür; göz kararı "iyi uçtu" test sayılmaz (`../agent-os/standards/testing/test-writing.md:14`). pyulog sabit sürümü 1.2.4 (`tez/env/VERSIONS.md:28`, analiz venv'i).
- **Geçici test göndericisi (11 için geçici çözüm):** m06 hazır olana kadar sahte yönü gönderen test script'i **bu işin parçasıdır ve biz yazarız.** Açık ve kapalı çevrim kiplerini kapsar. Script: `tez/sitl/af_los_gonder.py`; Pi'nin göndereceği `DEBUG_FLOAT_ARRAY` (`AF_LOS`) mesajını 3.4'teki yerleşimle taklit eder. Değerlendirme script'i: `tez/analiz/af_log_analiz.py`. (Not: `tez/*` kilit listesinde, `tez/pin/allowed-paths.txt:4`; pymavlink 2.4.50 laptop kilit dosyasında, `tez/env/VERSIONS.md:17`.)
- **m06'ya taşıma notu:** Gerçekçi simülasyon Ahmet Kazalcı'nın m06 işidir. O hazır olunca testler oraya taşınır.
- Kaynak: KG Soru 10 (iki anlatım) ve "L2 ve test kararları (kesin)".

### 3.13 Zaman bilgisinin kullanımı (**Karar**, 2026-11-09)

- Kullanıcı: "Geldikten sonra ne yapacağımız bize kalmış; isteklerime göre uygun olanı söyle, kafama yatarsa yaparız." Öneri sunuldu, kullanıcı "bunlar tamam" dedi.
- **m15'te yapılanlar:**
  - **Eskilik kontrolü gerçek yaşa göre:** Çekim anı ≈ varış anı − yaş. Görüntü `AF_DATA_TOUT`'tan eskiyse reddedilir. Pi'de işlem takılırsa eski bir görüntü "taze" görünmez.
  - **Gecikme loga yazılır:** Her mesajın yaşı ve hesaplanan toplam gecikmesi `auto_follow_status`'a girer. Gerçek gecikme testlerde sayıyla görülür.
  - **"Hedef yok" bayrağı:** Pi 0 gönderirse "kayıp" durumu, veri zaman aşımını beklemeden hemen başlar.
  - **Sıra numarası:** Tekrar eden ya da geri giden mesaj atılır ve sayılır.
- **m15'te yapılmayan:** Gecikme telafisi, yani LOS'u NED'e çevirirken görüntünün çekildiği andaki tutumu kullanmak (son ~0.5 s'lik tutum geçmişi gerekir). Önce loglardaki gerçek gecikmeye bakılır; büyükse m13/m16'da eklenir. İhtiyaç tahminle değil veriyle belirlenir. V3 bu yüzden "varış anındaki tutum" olarak kalır.
- Pi tarafı biçimi farklı gönderirse (ör. yaş yerine mutlak saat), yalnızca girdiyi okuyan kısım değişir.

---

## 4. Varsayımlar

Ortak spec'ler (yol haritası 3, 4, 5) yazılmadığı için aşağıdakiler kesinleşmiş değildir (`../agent-os/product/roadmap.md:69`). Ortak spec yazılınca bu spec ona göre güncellenir.

| # | Varsayım | Kaynak / durum |
|---|---|---|
| V1 | **Girdi:** Body FRD frame'de hedef yönünü gösteren **LOS birim vektörü** (x ileri, y sağ, z aşağı). Kamera montaj açısı Pi tarafında uygulanmıştır; FC montaj açısını bilmez. | 1. tur soru 13 (kullanıcıya sunulan metin). İtiraz gelmedi. |
| V2 | **Taşıma:** MAVLink `DEBUG_FLOAT_ARRAY` (`name` = `AF_LOS`) → `debug_array`; kutu yerleşimi 3.4'te (LOS x/y/z, yaş ms, sıra no, hedef var/yok). Pi body frame LOS ve zaman damgası gönderecek (kullanıcı). Kesin biçim ve frekans ICD'de (m3–5). | Karar 2026-11-09 (3.4). |
| V3 | **Tutum:** LOS → NED dönüşümünde verinin FC'ye **varış anındaki** `vehicle_attitude` kullanılır; gecikme telafisi yok. | 1. tur soru 13. İtiraz gelmedi. |
| V4 | **Yükseklik:** Drone yüksekliği `-vehicle_local_position.z`. Zemin düz ve kalkış düzlemi kabul edilir; mesafe düz dünya kabulüyle irtifadan hesaplanır. | **Karar 13-(iii)** (3.10). |
| V5 | **Hedef noktası:** Hedefin bakılan noktasının yüksekliği (ayak / gövde ortası) ve zemin ofseti parametredir. | **Karar 13-(iii)** (3.10). |
| V6 | **Eksenler:** LOS vektörünün eksen yönleri ve işaretleri Yusuf Ortatepe'nin m10 çalışmasıyla eşlenecek. **Açık.** | 1. tur soru 13; issue #6 "Dikkat". |

- **Not (ana ajan düzeltmesi):** Spec-shaper V1–V6 metinlerini kaynak dosyalarda bulamamıştı. Metinler, 1. turda kullanıcıya sunulan soru listesinin 13. maddesinden alınarak tamamlandı. O listenin tam metni yalnızca konuşma kaydında duruyordu.
- **Girdi mesajının sınırlamaları:** bkz. 3.4.
- **Eksenler:** LOS vektörünün eksen yönleri ve işaretleri **Yusuf Ortatepe'nin m10** (piksel → body frame) çalışmasıyla eşlenecek. **Açık.**
- **Takip açısı / kamera eğimi:** **Ahmet Kazalcı'nın m06** kamera montaj dokümanıyla eşlenecek. SITL için o zamana kadar bir değer seçilecek. **Açık.**

---

## 5. Parametreler: başlangıç değerleri ve adlar

### 5.1 Parametreler ve başlangıç değerleri (adlar **Karar**, 2026-11-09; değerler öneri kabul)

Hepsi parametredir (`../agent-os/standards/px4/uorb-params.md:12`: kazanç ve eşikler koda gömülmez). Testlerden sonra QGC'den değiştirilir, kod yeniden derlenmez. Ön ek `AF_` (kullanıcı); PX4 v1.17.0'da `AF_` önekli parametre yok. Hepsi en fazla 16 karakter.

| Parametre | Sade anlamı | Başlangıç |
|---|---|---|
| `AF_TRK_ANG` | Takip açısı: hedefin kadraj ortasında durduğu aşağı bakış açısı | Kamera eğimi (m06'dan); SITL için 30° |
| `AF_K_DIST` | Mesafe kazancı K (2 m hata → 1 m/s) | 0.5 1/s |
| `AF_K_FF` | Hedef hızı katsayısı c (0 = kapalı) | 0 (ilk testler); kapalı çevrim testle açılır |
| `AF_VEL_MAX` | Takipte en fazla yatay hız | 2 m/s |
| `AF_ACC_MAX` | İvme sınırı: hız isteği ne kadar sert değişebilir | 3 m/s² (PX4 `MPC_ACC_HOR` varsayılanı, `src/modules/mc_pos_control/multicopter_autonomous_params.c:88`) |
| `AF_ALPHA`, `AF_BETA` | Alpha-beta filtre katsayıları | SITL'de denenerek seçilecek |
| `AF_DATA_TOUT` | Veri zaman aşımı: bu süre veri gelmezse "kayıp" | 0.5 s |
| `AF_LOST_T` | "Kayıp"tan Hold'a kadar süre (T_kayip) | 1.0 s |
| `AF_YAW_MIN_D` | Bu yatay mesafenin altında yaw değişmez | 1 m |
| `AF_TGT_HGT` | Hedefin bakılan noktasının yüksekliği | 1.0 m |
| `AF_GND_OFS` | Hedefin zemininin kalkış yerine göre yüksekliği | 0 m |
| `AF_NORM_TOL` | LOS vektör uzunluk toleransı | 0.1 |
| `AF_MIN_DEP` | En küçük aşağı bakış açısı | 10° |
| `AF_MAX_RNG` | En büyük menzil | 40 m |

- Çevrim hızı parametre değildir; kodda sabit 50 Hz.

### 5.2 Adlar (Soru 12 süreç kararı; adlar **Karar**, 2026-11-09)

| Ne | Ad |
|---|---|
| QGC/RC'de görünen mod adı | **`AUTO FOLLOW`** |
| Modül klasörü ve shell komutu | `auto_follow` (`src/modules/auto_follow/`), `CONFIG_MODULES_AUTO_FOLLOW` |
| Parametre ön eki ve adları | `AF_` (5.1) |
| Log mesajı | `msg/AutoFollowStatus.msg` → topic `auto_follow_status` |
| Pi'den gelen mesajın adı | `AF_LOS` (`DEBUG_FLOAT_ARRAY` `name`) |
| Kaynak dosyalar | `AutoFollow.cpp/.hpp`, `AutoFollowGuidance.cpp/.hpp`, `AlphaBetaFilter.hpp` |
| Birim test dosyası | `AutoFollowGuidanceTest.cpp` |
| SITL test göndericisi | `tez/sitl/af_los_gonder.py` |
| Log değerlendirme script'i | `tez/analiz/af_log_analiz.py` |
| Log sözlüğü | `log-sozlugu.md` (spec klasörü) |
| Rapor | `rapor.md` (spec klasörü) |

- Log mesajının alan adları henüz verilmedi; write-spec'te sözlükle birlikte sorulur. Bundan sonra gereken yeni her ad da aynı şekilde sorulur.
- **Eski taslak adlar geçersizdir:** `tez_follow`, `TEZ_FOL_*`, `TEZ_LOS`, `CONFIG_MODULES_TEZ_FOLLOW`.
- **⚠️ `AUTO_FOLLOW_TARGET` uyarısı (Karar):** PX4'ün kendi Follow Me modu (`NAVIGATION_STATE_AUTO_FOLLOW_TARGET` = 19, `msg/versioned/VehicleStatus.msg:55`; kod `FlightTaskAutoFollowTarget`, parametreler `FLW_TGT_*`) bizim AUTO FOLLOW ile **ilgili değildir**.
  - Çalışma anında çakışma yok: PX4 modları numarayla ayırıyor (bizimki 23–30), kod, parametre ve topic adları da ayrı.
  - Karışıklık yalnızca insan tarafında olabilir: QGC'de iki benzer ad görünür ve bazı log araçları 19'u "Auto Follow" diye gösterebilir.
  - Önlemler: uyarı **log sözlüğüne ve rapora** yazılır; log mesajına mod numarası eklenir; kodda hiçbir şeye `AutoFollowTarget` / `follow_target` adı verilmez; RC anahtarı (`COM_FLTMODEx`) bizim mod numarasıyla ayarlanır.

## 6. Kilitli yollar, onay ve flash

### 6.1 Kilit listesine eklenmesi gereken yollar

Bu yolların hiçbiri şu an `tez/pin/allowed-paths.txt`'te yok. Hepsi **tek bir talep** olarak repo sorumlusuna (**Hüseyin**) iletilir:

| Yol | Neden |
|---|---|
| `src/modules/<ad>/` | Yeni modül (3.2) |
| `boards/px4/sitl/default.px4board` | Modülü SITL'de açan satır (3.2) |
| `boards/px4/fmu-v6c/default.px4board` | Modülü Pixhawk 6C'de açan satır (3.2, 3.1-ii) |
| `msg/<Ad>.msg` | Kendi log mesajımız (L2-b) |
| `msg/CMakeLists.txt` | Yeni mesajı listeye ekleyen satır (`msg/CMakeLists.txt:39`) |
| `src/modules/logger/logged_topics.cpp` | Yeni mesajı loga ekleyen `add_topic` satırı (L2-b) |

- **Ajan kilit listesini kendisi asla düzenlemez.** Ekleme, repo sorumlusunun onayıyla ayrı ve açık bir PR'la yapılır (çatı `CLAUDE.md`, `Autopilot/CLAUDE.md`; `../agent-os/standards/global/conventions.md:14`).
- Hüseyin log mesajı yollarını (son üç satır) reddederse L2 geri dönüşü (`debug_array`) uygulanır; o durumda bu üç yol gerekmez.
- Yeni dosyaların yolları PR açıklamasında gösterilir (kabul kriteri 6).
- Commit/PR öncesi `tez/pin/verify_pin.sh --worktree` çalıştırılır.

### 6.2 Flash

- Pixhawk 6C flash'ı ~%98 dolu (~40 KB boş) (`../agent-os/product/tech-stack.md:43`, `../agent-os/product/roadmap.md:36`).
- Kod küçük tutulur; `make px4_fmu-v6c_default` çıktısındaki flash kullanımı spec'e yazılır.
- **`region FLASH overflowed` olursa:** Hüseyin'e haber verilir. **Başka modül kapatılarak yer açılmaz** (o iş m14).
- 13-(iii)'ün geri dönüşü (zemin ofseti parametresinin çıkarılması) flash'a bağlıdır (3.10).

---

## 7. Standartla çelişki notları ve düzeltmeler

### 7.1 "Setpoint üretmeyi bırak" kuralı ile PX4 kaynağı

- Çatı standardı hata durumunda "setpoint üretmeyi bırak, PX4 failsafe'ine devret" diyor (`../agent-os/standards/global/error-handling.md:4`).
- PX4 kaynağında ise modül yayını keserse konum kontrolcüsü **son gelen isteği uygulamaya devam eder** (`src/modules/mc_pos_control/MulticopterPositionControl.cpp:438, 443-449`). Yani yayını kesmek "son hıza devam et" demektir.
- Bu yüzden modül, sorun anında susmaz; **aktif olarak "yerinde dur" (hover) isteği** gönderir (3.8). Bu çelişki spec'e ve rapora not olarak yazılır. Standardın değişmesi ayrı bir iştir (çatıda profil değişikliği).

### 7.2 `logger_topics.txt` düzeltmesi

- Önceki bir bilgi eksikti: "SD karttaki `etc/logging/logger_topics.txt` ile kilitli dosyaya dokunmadan ek topic loglanır."
- Doğrusu: Bu dosya varsa PX4 **yalnızca dosyadaki topic'leri** loglar ve varsayılan listeyi tamamen devre dışı bırakır (`src/modules/logger/logged_topics.cpp:531-540`).
- Bu yüzden kendi mesajımız için doğru yol `logged_topics.cpp`'ye bir `add_topic` satırı eklemektir (6.1).

### 7.3 Sıra numarası kontrolü

- `../agent-os/standards/global/validation.md:6` tekrar/eski mesaj kontrolünü sıra numarası veya zaman damgasıyla istiyor. **Çözüldü (2026-11-09):** Girdi `DEBUG_FLOAT_ARRAY` olduğu için sıra numarası ve yaş mesajın içinde taşınıyor (3.4, 3.7). Kesin biçim ICD'ye bağlı.

---

## 8. Dokümantasyon gereksinimleri

Kullanıcının notu (KG, 2026-11-09): "Ben bu kodu elle yazmayacağım; ne yapıldığını kod okumadan bilecek seviyede yazılsın. İki gün sonra bir sıkıntı çıktığında her şey kayıtlı olduğundan çözmesi kolay olur."

- **Karar günlüğü** (`planning/karar-gunlugu.md`) iş boyunca güncel tutulur: her soru, seçenek, cevap ve gerekçe.
- **Her görev grubunun sonunda** spec klasörüne kod okumadan anlaşılacak dille yazılır: ne yapıldı, neden yapıldı, nasıl test edildi, hangi sorunlarla karşılaşıldı ve nasıl çözüldü.
- **Log sözlüğü** spec klasöründe tutulur ve **kodla aynı commit'te** güncellenir (3.11).
- **Kullanıcı raporu (14.3):** Spec klasörüne, işin ne olduğunu, hangi kararların neden alındığını, nasıl test edildiğini ve sonuçlarını sade dille anlatan bir **rapor `.md`** yazılır. Karar günlüğünden ve uygulama notlarından derlenir. **Dosya adı oluşturulurken kullanıcıya sorulur.**
  - Bu rapor, masaüstündeki `guidance-yasalari.md` dosyasına yapılan atfın yerini alır. Kullanıcı: "`guidance-yasalari.md` benim çalışmam içindi. Onun yerine benim ne yaptığımı anlatan bir rapor `.md` daha iyi olur." Masaüstündeki dosya spec'e alınmaz ve ona dokunulmaz.
  - `planning/visuals/01-ust-seviye-akis.md` kopyasındaki masaüstü dosyası bağlantısı (`:9`) **ileride** bu rapora işaret edecek şekilde değiştirilir. **Şimdi değiştirilmez.** Eski klasördeki asıl şema hiç değişmez.
- Her SITL testinin sonucu (ne verildi, drone ne yaptı, ULog adı) ve 6C flash kullanımı spec'e yazılır (Bölüm 2).
- **Commit düzeni** (çatı kural 10–11): her spec aşaması ve her görev grubu ayrı commit; mesaj `2026-11-08-m15-takip-kodu: ...`; PR başlığı `[M15] ...`. Push kullanıcı istemeden yapılmaz.

---

## 9. Kapsam dışı, ürün planı notu, eski taslaklar, iş sırası (Soru 14, **Karar (öneri kabul)**)

### 9.1 Kapsam dışı (14.1)

| Konu | Nereye |
|---|---|
| C seçeneği (Hold'dan kendiliğinden dönüş) ve ayrıntılı failsafe | m16 |
| Nihai guidance yasası ve ince ayar | m13 |
| Pi tarafı, ICD ve kalıcı yön göndericisi | Vision (m3–5, m12) |
| Gerçekçi simülasyon, kamera ve hareketli insan modeli | m06 |
| Gerçek uçuş | m22, m25 |
| Flash'ta yer açma | m14 |
| Ekip için "her özelleştirme loga girer + log sözlüğü" standardı | Ayrı m00 (kullanıcı ve repo sorumlusu onayıyla; çatıda `agent-os-profilleri/` → derleme → üç repoda PR). Kullanıcı kuralı ve `SDLOG_MODE` notunu ekibin WhatsApp grubuna iletecek. |

### 9.2 Ürün planı notu (14.2)

- `../agent-os/product/tech-stack.md:44`'teki "Takip modunun PX4'e entegrasyon yaklaşımı — Seçilmedi — Karar bekliyor" satırı için spec'e ve PR açıklamasına **"karar: external mode, güncellenmeli"** notu düşülür.
- Güncellemeyi **repo sorumlusu** yapar; bu spec çatı dosyalarını değiştirmez.

### 9.3 Eski taslak spec'ler (14.4)

- `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/` ve `agent-os/specs/2026-10-18-m15-fc-only-flow-diagrams/` taslaktır ve bağlamaz. **Dosyalarına dokunulmaz.**
- Bu spec'te atıf: "taslaktı, yerini bu spec aldı."

### 9.4 İş sırası (14.5)

1. İskelet (SITL + 6C derlemesi)
2. Guidance + alpha-beta
3. Kısa birim testi
4. SITL S1–S5
5. Hold geçişi
6. S6–S7 + log mesajı ve sözlüğü

Yetişmeyenler "m16'ya kalanlar" listesine (1.3) yazılır.

---

## 10. Açık konular

Shape-spec sonrası konuşmada kapananlar (2026-11-09): süreler, doğrulama eşikleri, yükseklik formülü, log mesajının kaydı, hedef yokken moda giriş, girdi mesajı ve zaman damgası, bütün adlar (log alanları hariç). Kalanlar:

| # | Konu | Durum |
|---|---|---|
| 9.x | **Mod kaydının teknik ayrıntıları** (9.1 `mode_req_*` listesi, 9.4 kontrol bayrakları) | Öneri: `angular_velocity`, `attitude`, `local_alt`, `local_position` gerekli; pozisyon/hız/irtifa/tutum/rate/allocation bayrakları açık, manual/offboard kapalı (doğrulanacak). Write-spec'te teyit. Moda geçiş: hem QGC hem RC (Karar). `can_arm_and_run` = `true` (Karar 5-a). |
| 9 | **Masa testi (GPS yokken)** | Kapalı ortamda yerel konum geçersiz olur ve modül hedef konumunu hesaplamaz. Masada ne görülmek isteniyor? Write-spec'te konuşulacak. Masa testinde log: kullanıcı `SDLOG_MODE`'u kendisi değiştirir, kart yeniden başlatılır. |
| ICD | **Vision ile girdi biçimi** | Pi'nin `AF_LOS` mesajını 3.4'teki yerleşimle (LOS x/y/z, yaş ms, sıra no, hedef var/yok) göndermesi Yusuf Ortatepe ile konuşulacak. Eksenler m10 ile eşlenecek. |
| 11 | **Kalıcı gönderici** | Vision (m12) ve m06 ile konuşulacak. Geçici test göndericisini biz yazıyoruz (3.12). |
| LOG | **Log mesajının alan adları** | Write-spec'te log sözlüğüyle birlikte sorulacak. |
| 6 | **Kilit listesi talebi** | 6.1'deki yollar Hüseyin'e tek talep olarak iletilecek. |
| m06 | **Kamera eğimi / takip açısı** | Ahmet'in m06 kamera montaj dokümanından gelecek; SITL için 30°. |
| RC | **RC override** | Çubuğa dokununca external moddan çıkılıp çıkılmadığı (doğrulanacak). |
| GECIKME | **Gecikme telafisi** | m15'te yok. Loglardaki gerçek gecikmeye bakılır; gerekirse m13/m16'da eklenir (3.13). |

---

## 11. Görseller

- **Bash kontrolü:** `planning/visuals/` klasöründe resim/PDF dosyası yok. İki şema Mermaid (`.md`) olarak var:
  - `planning/visuals/01-ust-seviye-akis.md`: Üst seviye akış. FC'ye MAVLink ile gelen body FRD LOS → mod aktif mi → mesaj geçerli mi → LOS'u NED'e çevir → aşağı açı ve mesafe → hedefin NED konumu → hedef kestirimi → guidance (istenen mesafe, hız, yaw, sınırlar) → PX4 kontrolcüleri → PWM → ESC → motorlar. Hedef görünmezse "yerinde bekle", süre dolunca "Hold". Referans görselin şekil dilini kullanan sade, siyah-beyaz bir akış (paralelkenar girdi, kutu işlem, eşkenar dörtgen karar, kesik çizgi TBD).
  - `planning/visuals/02-px4-detayli-akis.md`: PX4 v1.17.0'a özel detaylı akış. Bloklar: (A) başlatma, mod kaydı ve arming check; (B) çevrim başına veri akışı (run loop); (C) mod seçimi, çıkış, hedef kaybı ve failsafe; (D) doğrulama akışı (GoogleTest → Gazebo SITL → ULog/pyulog → gerçek uçuş, S1–S7). Her kutu `dosya:satır` kanıtlı.
- **Durum:** Şemalar eski taslak spec'ten kopyalanmıştır; eski klasördeki dosyalar değişmedi (KG Oturum 1).
- **Güncelleme onayı (2026-11-09):** Kullanıcı TBD'lerin güncellenmesini onayladı. Kararlaşanlar kararla değişecek (ICD → `DEBUG_FLOAT_ARRAY` varsayımı, yükseklik, guidance, setpoint, süreler → `AF_` adları, SITL girdisi → geçici gönderici). Açık kalanlar TBD olarak kalacak (kilit listesi onayı, ICD zaman biçimi, insan modeli/m06). Eski adlar AUTO FOLLOW / `AF_` olacak, masaüstü bağlantısı rapora çevrilecek. Değişiklik yalnızca bu spec'teki kopyalara uygulanır; write-spec aşamasında yapılır.
- **Bilinen farklar (henüz düzeltilmedi):** Şemalarda eski taslak adlar (`tez_follow`, `TEZ_FOL_*`) ve bu spec'te karara bağlanmış konular hâlâ "TBD" olarak geçiyor (ör. yükseklik kaynağı, setpoint tipi); masaüstü `guidance-yasalari.md` atfı iki dosyada da var (`01-ust-seviye-akis.md:9`, `02-px4-detayli-akis.md:8`). Şemaların güncellenmesi write-spec/uygulama aşamasında, kullanıcıya sorularak yapılır.
- **PNG dönüşümü ertelendi:** `mmdc` ve Node.js kurulu değil. Yeni araç kurmak sabit sürümüyle `tez/env/VERSIONS.md`'ye yazılmayı gerektirir (çatı kural 4). **Kurmadan önce kullanıcıya sorulur.**

---

## 12. Mevcut koddan yararlanma

Kodu kopyalamak için değil, kalıp ve kanıt olarak (spec-writer bunlara bakar):

| Ne | Yol | Kullanım |
|---|---|---|
| External mode kalıbı | `src/modules/mc_nn_control/` (`mc_nn_control.cpp:65` iş kuyruğu, `:135-142` mod kaydı) | Modülün PX4'e kendini mod olarak kaydetmesi |
| PX4 modül yazım deseni | `src/examples/work_item` | `ModuleBase` + `ModuleParams` + `ScheduledWorkItem` (`../agent-os/standards/px4/modules.md:3-7`) |
| Hedef kestirimi fikri | `follow_target_estimator/TargetEstimator.hpp:112, 210`, `follow_target_params.c:53` (`FLW_TGT_RS`) | Yalnızca fikir; GPS'e bağlı olduğu için doğrudan kullanılmaz |
| Hold isteği | `src/modules/commander/Commander.cpp:936-944` (`VEHICLE_CMD_SET_NAV_STATE`) | Uzun kayıpta Hold |
| Setpoint karışımı | `PositionControl.cpp:224-250` | Hız xy + konum z + yaw geçerliliği |
| Ahmet Kazal'ın deneme dalı | Autopilot `origin/deney/ai-follow-sim` (`follow_core.py:37,46`, `geolocation.py`, pyulog analizi) | README'ye göre "tezde kullanılmayacak"; `FOLLOW_TARGET` ile PX4 Follow Me'yi kullanıyor. Geolocation, gecikme/kayıp simülasyonu ve pyulog analizi için fikir kaynağı; kod doğrudan alınmaz |

---

## 13. Kaynaklar arasındaki farklar (bilgi notu)

- `tur1-cevaplar.md`'deki bazı kayıtlar sonradan güncellendi; geçerli olan karar günlüğündeki son kayıttır: 8.2 → D (Hold m15'te); madde 6'daki ilk formül → hedef hızı katsayılı yasa; madde 13 "Teyit bekliyor" → (iii); L2 "(a) şimdi, (b) sonra" → (b). `tur1-cevaplar.md`'nin "Sonraki adım" bölümündeki açık maddeler karar günlüğünün sonunda kapanmıştır.
- Mesaj zaman aşımı ile `T_kayip` ilişkisi **çözüldü (2026-11-09):** `AF_DATA_TOUT` 0.5 s sonra kayıp başlar, `AF_LOST_T` 1.0 s sonra Hold (3.7, 3.8).
- 5-a (`DEBUG_VECT`) kararı, 2026-11-09'da `DEBUG_FLOAT_ARRAY` ile değiştirildi (3.4). `tur1-cevaplar.md`'deki 5. satır tarihsel kayıttır.
- V1–V6 metinleri dosyalarda yoktu; ana ajan 1. tur soru listesinden tamamladı (Bölüm 4).
