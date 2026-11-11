# M15 karar günlüğü

Bu dosya M15 spec'i boyunca konuşulan her konuyu, sorulan her soruyu, değerlendirilen seçenekleri, verilen cevapları ve gerekçeleri **kod okumadan anlaşılacak dille** kaydeder. Amaç: İki gün ya da iki ay sonra bir sorun çıktığında "bu neden böyle yapıldı?" sorusunun cevabını burada bulmak.

- Kodu Claude yazar; kullanıcı kararları verir.
- Kısa cevap tablosu: `tur1-cevaplar.md`. Bu dosya ise o kararların **hikâyesini ve gerekçesini** anlatır.
- Kaynak gösterimi `dosya:satır` biçimindedir ve PX4 v1.17.0 (bu repo) içindir. Çatı repo dosyaları `../agent-os/...` ile başlar.

## Kullanıcının notu (2026-11-09)

> "Bazen senin dediklerin mantıklı geldi ama çok detaylı bilgiye sahip olmadan verdim. O yüzden yapılan her adımı, konuşulan konuları, soruları, cevapları, her şeyi kaydet. Ben bu kodu elle yazmayacağım; ne yapıldığını kod okumadan bilecek seviyede yazılsın. İki gün sonra bir sıkıntı çıktığında her şey kayıtlı olduğundan çözmesi kolay olur."

**Bunun sonuçları:**
- Aşağıda "öneri kabul" diye işaretli kararlar, kullanıcının Claude'un önerisine güvenerek verdiği kararlardır. Bir sorun çıkarsa **ilk gözden geçirilecek yer bunlardır**; gerekçeleri ve reddedilen seçenekler bu yüzden ayrıntılı yazıldı.
- **Dokümantasyon gereksinimi (spec'e girecek):** Uygulama sırasında her görev grubunun sonunda, o adımda ne yapıldığı, neden yapıldığı ve nasıl test edildiği kod okumadan anlaşılacak dille spec klasörüne yazılır. Karşılaşılan sorunlar ve çözümleri de yazılır.

---

## Genel resim: neyi yapıyoruz?

Drone'daki Raspberry Pi kamerada insanı bulur ve Pixhawk'a yalnızca bir **yön** gönderir: "hedef, drone'a göre şu tarafta" (body FRD LOS birim vektörü). M15'te Pixhawk'ın içine yazılacak kod bu yönü alır ve şunları yapar:
1. Hedefin yerde nerede olduğunu hesaplar.
2. Drone'un hangi hızla, hangi yöne gitmesi ve burnunu nereye çevirmesi gerektiğine karar verir. Buna **guidance** denir.
3. Bu isteği PX4'e verir.

PX4 geri kalanı kendisi yapar: hız → eğilme → açısal hız → motor karışımı → PWM → motorlar. Biz kontrolcü yazmıyoruz; yalnızca "ne istendiğini" söyleyen katmanı yazıyoruz.

---

## Oturum 1 — 2026-11-08

### Spec klasörünün adı
- **Soru:** Spec klasörü ne olsun?
- **Cevap:** `2026-11-08-m15-takip-kodu`. Dal adıyla (`ozellik/m15-takip-kodu`) aynı olduğu için seçildi.

### Şemaların PNG'ye çevrilmesi
- **Durum:** Şemaları PNG'ye çevirecek araç (`mmdc`) ve Node.js kurulu değil. Yeni araç kurmak, sürümünü `VERSIONS.md`'ye yazmayı gerektiriyor (çatı kural 4).
- **Cevap:** Şimdilik PNG yok. İki şema `.md` (Mermaid) olarak `planning/visuals/`'a kopyalandı. Eski klasördeki dosyalar değişmedi.

### Çatı repo dokümanları dikkate alındı mı?
- **Kullanıcının sorusu:** "Ana çatıdaki agent-os bilgilerini dikkate alıyorsun değil mi?"
- **Durum:** İlk soru listesi yalnızca PX4 kaynağına dayanıyordu. Bu sorudan sonra çatıdaki `agent-os/product/` (misyon, yol haritası, teknoloji yığını) ve `agent-os/standards/` dosyaları okundu, sorular bunlara göre güncellendi. Bundan sonra her spec işinde bu dosyalar işin başında okunacak.

### Soru 1 — M15'in kapsamı (m15 ile m16 sınırı)
- **Sorun:** Yol haritasında m15 küçük bir iş (`S`). Doğrulaması yalnızca "seçilen yaklaşımın iskeleti SITL ve Pixhawk 6C için derlenir" (`../agent-os/product/roadmap.md:37`). Issue #6 ise ayrıca çalışan guidance kodu ve SITL'de drone'un tepki verdiğinin gösterilmesini istiyor. Yol haritasında bunlar m16'nın (`XL`) içinde.
- **Seçenekler:** a) issue'yu izle, farkı not et; b) işi ikiye böl (iskelet m15, gerisi m16); c) önce Hüseyin'den roadmap ile issue'yu hizalamasını iste.
- **Cevap: a.** Görevi veren issue #6 ve teslim tarihi ona bağlı. Spec'e "roadmap'teki m15 tanımından farklı olarak issue #6'yı izliyoruz" notu ve bir "m16'ya kalanlar" listesi yazılacak.

### Soru 2 — Kod PX4'e nasıl bağlanacak?
- **Seçenekler:**
  - **a) External mode modülü.** PX4'ün kendi örneği `mc_nn_control`, kendini PX4'e "yeni bir uçuş modu" olarak kaydettiriyor (`mc_nn_control.cpp:135-142`). Pilot bu modu QGC'den ya da RC'den seçer. Mod aktifken PX4 kendi uçuş görevlerini durdurur (`FlightModeManager.cpp:139-144`), bizim modül hız isteğini yayınlar, PX4'ün konum kontrolcüsü bunu uygular.
  - **b) Yeni FlightTask.** PX4'ün kendi modlarının yazıldığı yöntem. Kilitli birçok PX4 dosyasını (commander, mesaj tanımları, mod yöneticisi) değiştirmeyi gerektirir; flash'ı da daha çok doldurur.
  - **c) Offboard.** Guidance Pi'de çalışır, Pixhawk'a doğrudan hız gönderilir. Bu durumda kod PX4'ün içinde olmaz; issue #6 ve misyonla çelişir.
  - **d) PX4'ün hazır Follow Me modunu uyarlamak.** Bu mod GPS konumu bekliyor, bizim girdimiz ise bir yön.
- **Cevap: a.** Kilitli dosyalara en az dokunan, kodu PX4'ün içinde tutan ve PX4'ün kendi kontrol zincirini ve failsafe'ini kullanan seçenek bu.

### Soru 3 — Kod repoda nerede duracak?
- **Seçenekler:** a) PX4'ün normal modül yeri `src/modules/<ad>/`. Modül, iki kart dosyasına bir satır eklenerek (`CONFIG_MODULES_<AD>=y`) açılır. b) Kilit dışındaki `tez/` klasöründe, PX4'ün "dış modül" özelliğiyle (`EXTERNAL_MODULES_LOCATION`).
- **Cevap: a.** Çatı standardının öngördüğü düzen bu (`../agent-os/standards/px4/modules.md:3, 8`).
- **Sonuç / yapılacak iş:** `src/modules/<ad>/` ve iki kart dosyası kilit listesinde (`tez/pin/allowed-paths.txt`) yok. Bu yolların listeye eklenmesi için **repo sorumlusunun (Hüseyin) onayı** ve ayrı, açık bir PR gerekir. Claude listeye kendisi eklemez; gereken yollar spec'e yazılır.

### Soru 4 — Modülün iç yapısı (öneri kabul)
- **Kullanıcının cevabı:** "Senin önerin neyse o olsun."
- **Kabul edilen öneri:**
  - Modül PX4'ün kontrolcülerle aynı iş kuyruğunda (`nav_and_controllers`) çalışır. `mc_nn_control` da aynı kuyruğu kullanıyor (`mc_nn_control.cpp:65`).
  - Modül **sabit hızda** döner (önerilen ~50 Hz), veri geldiğinde değil. Gerekçe: Veri kesilince de çalışmaya devam etmeli ki "veri geldi mi, eskidi mi" kontrolü yapılabilsin ve güvenli davranışa geçilebilsin. Yalnızca veri geldiğinde dönseydi, veri kesilince modül de dururdu ve kesintiyi fark edemezdi.
  - Guidance hesabı uçuş donanımından bağımsız ayrı bir sınıfta tutulur, böylece bilgisayarda otomatik testlerle denenebilir.

### Soru 5 — Pi'den gelen yön hangi mesajla gelecek?
- **Durum:** Hangi mesajın kullanılacağı ortak ICD'de (yol haritası madde 3–5) belirlenecek; ICD henüz yazılmadı. Yeni MAVLink mesajı eklemek yasak; yalnızca PX4 v1.17.0'ın zaten tanıdığı mesajlar kullanılabilir.
- **Seçenekler:** a) `DEBUG_VECT` (üç sayı: x, y, z ve kısa bir ad); b) `DEBUG_FLOAT_ARRAY` (daha çok alan, sıra numarası da konabilir); c) `LANDING_TARGET` (hassas iniş için tasarlanmış, çakışma riski); d) `NAMED_VALUE_FLOAT` (mesaj başına tek sayı).
- **Cevap: a, "Varsayım" olarak.** ICD gelince güncellenecek.
- **Bilinen sınırlamalar (spec'e yazılacak):**
  - Mesajda sıra numarası yok.
  - Zaman damgası ölçüm anını değil, mesajın Pixhawk'a varış anını gösteriyor (`mavlink_receiver.cpp:2804`).
  - Başka yazılımlar da aynı mesajı kullanabileceği için mesajın adına bakılarak süzülmesi gerekir.
  - Bu mesajın işleyicisi, flash'ta yer açmak için kullanılan `CONSTRAINED_FLASH` ayarı açılırsa derlemeden çıkar. m14 (flash'ta yer açma) yapılırken bu bilinmeli.

### Soru 7 — PX4'e ne verilecek?
- **Cevap:** `trajectory_setpoint` mesajı ile **yatay hız + irtifa + mutlak yaw** (burnun bakacağı açı). Diğer alanlar boş (NaN) bırakılır. PX4 bu karışımı geçerli kabul ediyor (`PositionControl.cpp:224-250`).
- `goto_setpoint` (yalnızca "şu noktaya git") hız tabanlı yasaya uymadığı için seçilmedi.

### Soru 8 — Bozuk veya eski veri gelirse (öneri kabul)
- **Kullanıcının cevabı:** "Önerilen gibi."
- **Her gelen mesajda yapılacak kontroller:**
  - Sayılar geçerli mi (NaN veya sonsuz değil mi)?
  - Vektörün uzunluğu 1'e yakın mı?
  - Mesajın adı doğru mu?
  - Mesaj zaman aşımına uğradı mı?
  - Yön yeterince aşağı bakıyor mu? Ufka yakın bir yön mesafeyi sonsuz yapar.
  - Hesaplanan mesafe makul mü?
  - Drone'un kendi konum bilgisi geçerli mi?
- Geçersiz mesaj atılır, sayılır ve (çok sık olmamak kaydıyla) loga yazılır; asla guidance hesabına girmez.
- **Önemli bulgu (standart ile PX4 kaynağı arasında çelişki):** Çatı standardı hata durumunda "setpoint üretmeyi bırak, PX4 failsafe'ine devret" diyor (`../agent-os/standards/global/error-handling.md:4`). Ama PX4 kaynağında, modül yayını keserse konum kontrolcüsü **son gelen isteği uygulamaya devam ediyor** (`MulticopterPositionControl.cpp:438, 443-449`). Yani yayını kesmek "son hıza devam et" demek. Bu yüzden modül, sorun anında susmak yerine aktif olarak "yerinde dur" isteği göndermeli. Çelişki spec'e not olarak yazılacak.
- 8.2 (tepki) daha sonra **D** olarak güncellendi (aşağıda, Oturum 2).

### Soru 9 — Mod kaydı ve arm
- **Kullanıcının isteği:** "Arm edilmemişken de masa testleri için bu moda geçebilmem lazım."
- **Bulgu:** PX4 arm edilmemiş araçta her mod değişikliğine zaten izin veriyor (`UserModeIntention.cpp:54-55`). "Bu modda arm etme" yasağı (`mode_req_prevent_arming`) moda geçişi engellemiyor, yalnızca o moddayken arm etmeyi engelliyor (`modeCheck.cpp:196-205`).
- **Açık kalanlar:**
  - Kapalı ortamda GPS yoksa drone kendi konumunu bilmez; modül hedef konumunu hesaplamaz. Masada ne görülmek isteniyor?
  - Gerçek kartta log varsayılan olarak yalnızca arm iken alınır (`SDLOG_MODE`=0, `logger/module.yaml:16-30`). Masa testi için ayarın değişmesi gerekir.
  - Modun ihtiyaç listesi, RC/QGC ile geçiş.

### Soru 10 — Test
- Kullanıcı soruyu anlamadı; sade dille yeniden anlatıldı. Kararlar bekleniyor (Oturum 2'de konuşulacak).

### Soru 11 — Sahte yönü kim gönderecek?
- **Kullanıcının cevabı:** "Karar bende değil, Vision tarafındaki arkadaşta. Tüm repoları tara, bana dön."
- **Tarama sonucu (2026-11-08):** Hiçbir repoda bu yönü gönderen kod yok.
  - Vision `main` dalında henüz kod yok.
  - Vision'ın `model-training` dalında yalnızca model dosyaları var. Kural 9'a göre bunların repoya girmemesi gerekiyor; repo sorumlusuna söylenebilir.
  - Ahmet'in `deney/ai-follow-sim` dalı, README'sine göre "tezde kullanılmayacak" bir deneme. GPS mesajı (`FOLLOW_TARGET`) ile PX4'ün hazır Follow Me modunu kullanıyor; fikir kaynağı olabilir.
  - Issue #7'ye (m06, Ahmet) göre SITL'de "model → PX4" bağlantısı onun işine de giriyor.
- **Sonuç:** Karar Yusuf Ortatepe (Vision, m10/m12) ve Ahmet Kazalcı (m06) ile konuşulduktan sonra verilecek.

### Soru 12 — Adlar
- **Cevap:** "Süreçte karar verelim; her ad gerektiğinde sor."
- Modül, parametre, mod, dosya ve topic adlarının her biri gerektiği anda sorulacak; PX4 kuralları (büyük harf, en fazla 16 karakter, çakışma yok) hatırlatılacak. Eski taslak adlar (`tez_follow`, `TEZ_FOL_*`, `TEZ_LOS`) geçersiz.

### Soru 13 — Varsayımlar (ilk cevap)
- İlk cevap "a parametresi olsun" iki şekilde okunabildiği için teyit istendi. Teyit Oturum 2'de geldi.

---

## Oturum 2 — 2026-11-09

### Hedef kaybolunca ne olacak? (⚠️ kullanıcı "önemli" olarak işaretledi)
- **Kullanıcının fikri:** "Hedef kaybolduktan sonra moddan çıksın, Hold atsın. Tekrar tanıdığında modu yeniden açmak için anahtarı aç-kapa yapmam gerekir diye düşündüm. Model uçuş modundan bağımsız sürekli algılama yapacak; ama benim modum açık değilse takip olmayacak, ben açınca algıladığı şeye gidecek."
- **Kaynaktan bulgular:**
  - RC anahtarı yalnızca **konumu değişince** mod isteği gönderiyor (`ManualControl.cpp:176-177`). Modül drone'u Hold'a aldıktan sonra anahtar "takip" konumunda durmaya devam etse de takip yeniden başlamaz. Anahtar başka konuma alınıp geri getirilmeli. QGC'den ise tek tıkla dönülür.
  - Modül, Hold'u bir komutla kendisi isteyebilir (`VEHICLE_CMD_SET_NAV_STATE`, `Commander.cpp:936-944`).
  - "Ben çalışamıyorum" sinyali verilirse PX4 drone'u Hold'a değil **eve dönüşe (RTL)** gönderiyor (`failsafe/failsafe.cpp:698-702`). Bu yüzden o yol seçilmedi.
- **Seçenekler:**
  - **A)** Moddan çıkma; yerinde bekle, hedef görününce kendiliğinden devam et.
  - **B)** Hold'a geç; takibi pilot yeniden açar.
  - **C)** Hold'a geç; hedef geri gelince modül takibi kendiliğinden yeniden açar.
  - **D)** Kademeli: kısa kayıpta A, uzun kayıpta B.
- **Kullanıcının sorusu:** "Güvenlik için sence ilk test uçuşlarında hangisi mantıklı?"
- **Cevap:** İlk uçuşlarda en güvenlisi B davranışı. Gerekçeler:
  - Model yanlış bir şeyi hedef sanırsa drone pilot onayı olmadan harekete geçmez.
  - Denenmemiş kodumuz yerine PX4'ün denenmiş Hold modu devreye girer.
  - QGC'de mod değiştiği için durum herkesçe görülür.

  Öneri, kodu D olarak yazmak ve `T_kayip` süresini ilk uçuşlarda kısa tutmaktı (davranış pratikte B olur). Güven arttıkça bu süre uzatılır.
- **Karar: D.** Hold geçişi **m15'te yapılır** ve SITL'de test edilir. İlk uçuşlarda `T_kayip` kısa tutulur (~1 s).
- **Reddedilen:** C. Pilotun bilerek moddan çıktığını ayırt etmek zor; yanlış algılamayla birleşince drone onaysız harekete geçebilir. İstenirse m16'da yeniden konuşulur.
- **Uçuş testlerine not:** İlk uçuşta pilotun RC'de her an Position moduna geçebileceği bir anahtar konumu olmalı. RC çubuğuna dokununca external moddan çıkılıp çıkılmadığı henüz doğrulanmadı.

### Soru 13 — Varsayımlar (teyit)
- **Konu:** Mesafe, drone'un yüksekliğinden hesaplanıyor. İki ayrı yükseklik var: drone'un yüksekliği nereden okunacak (V4) ve hedefin hangi noktasına bakılıyor (V5; ayak mı, gövde ortası mı).
- **Cevap:** "Flash'a sığdırabilirsek 3. seçenek en iyisi."
- **Karar: (iii).** Drone yüksekliği PX4'ün kendi irtifa tahmininden (`-local_position.z`) okunur. **Hedef yüksekliği** ve **zemin ofseti** ikisi de parametre olur. Flash'a sığmazsa yalnızca hedef yüksekliği parametresi kalır. Bir parametre flash'ta çok az yer kapladığı için büyük olasılıkla sığar; kesin değer 6C derlemesinde görülecek.

### Soru 3.1 — Modül Pixhawk 6C firmware'ine de girecek mi?
- **Kullanıcının cevabı:** "Asıl amaç her şeyi 6C'ye derlemek, projeyi gerçek hayatta yapmak. Ondan önce SITL'de test edip en iyi hâlini 6C için derleyeceğiz."
- **Karar: Evet.** Modül 6C'ye de eklenir ve derleme çıktısındaki flash kullanımı spec'e yazılır. Taşarsa Hüseyin'e haber verilir; modül kapatarak yer açılmaz (o iş m14).

### Soru 6 — Guidance yasası
- **Anlatılan:**
  - **Ortak adım:** Gelen yön, drone'un eğikliği ve burun yönü kullanılarak dünyaya göre yöne çevrilir. Zemin düz kabul edilerek yükseklikten mesafe bulunur. Örnek: 10 m yükseklikte (0.8, 0, 0.6) yönü → yaklaşık 37° aşağı bakış → 13.3 m yatay mesafe.
  - **Seçenekler:** a) hız tabanlı; b) konum tabanlı (her ölçümde hedef noktası zıplar, drone sarsılır); c) pure pursuit / PN (önleme yasaları, mesafe korumaz).
- **Karar 6-a: hız tabanlı.**
  - Kural: **istenen hız = hedefin hızı × c + K × (mesafe − istenen mesafe)**, hedefin yönünde. Hız en fazla v_max olur.
  - İrtifa sabit tutulur. Burun hedefe döner, böylece hedef kadrajın ortasında kalır.
- **Karar 6.1: alpha-beta filtresi.**
  - Kullanıcı alpha-beta filtresi istedi. Bu filtre ölçülen hedef konumunu yumuşatır ve aynı anda hedefin hızını da kestirir.
  - PX4'teki benzer filtre (`TargetEstimator`) GPS mesajına bağlı olduğu için doğrudan kullanılamıyor (`follow_target_estimator/TargetEstimator.hpp:112, 210`). Küçük, kendi alpha-beta sınıfımız yazılacak (**onaylandı**). Alpha ve beta parametre olur.
- **Karar: Kestirilen hedef hızı yasaya eklenir (onaylandı).**
  - Bunu yöneten katsayı (c) parametre olur; 0 verilirse bu kısım kapanır.
  - Gerekçe: Yalnızca mesafe farkına bakan yasa, yürüyen hedefin biraz gerisinde kalır; hedefin hızı eklenince bu açık kapanır.
  - **Dikkat:** SITL'de sabit bir yön gönderilirse sanal hedef drone'la birlikte hareket ediyormuş gibi görünür. Filtre bu durumda "hedef de benim hızımla gidiyor" der ve drone v_max'a kadar kaçar. Bu yüzden ilk sabit-yön testleri c = 0 ile yapılır. c > 0 testleri için kapalı çevrim test gerekir: script drone'un konumunu okuyup gerçek bir sanal hedefe göre yön hesaplar.
- **Kullanıcının takip tasarımı (6.3 cevabı):** "Hedefi belli bir mesafeden, dünyayı düz kabul ederek, sürekli kadrajın ortasında tutarak takip edeceğim. Yükseklik sabit, aradaki açı sabit olacak."
- **Karar 6.3:** Normal takipte hedef drone'un altına gelmez. Geçici durumlar için (hedef drone'a doğru koşarsa, moda girişte hedef çok yakınsa) küçük bir koruma eklenir: yatay mesafe ~1 m'nin altındaysa yaw değiştirilmez (**onaylandı: "mantıklı, olsun"**).
- **Karar 6.4: İstenen mesafe açı ile tanımlanır (öneri kabul).**
  - Takip açısı bir parametredir: hedefin kadraj ortasında durduğu açı. Kamera aşağı eğik monte edildiyse bu açı kameranın eğimidir.
  - İrtifa, moda girildiği andaki irtifadır.
  - Mesafe kendiliğinden çıkar: **mesafe = irtifa / tan(açı)**. Örnek: 5 m irtifa, 30° → ~8.7 m.
  - Kamera eğimi Ahmet'in m06 kamera montaj dokümanından gelecek; SITL için o zamana kadar bir değer seçilecek.
- **Karar 6.2: Hız değişimine ivme sınırı konur (öneri kabul).** Hız isteği bir anda değil, en fazla belli bir ivmeyle değişir. Gerekçe: Ani hız isteği drone'u sert eğer; ilk uçuşlar için güvenlik.
- **Başlangıç değerleri (öneri kabul; hepsi parametre, adları yazılırken sorulacak):**

| Ne | Sade anlamı | Başlangıç |
|---|---|---|
| Takip açısı | Hedefin kadraj ortasında durduğu aşağı bakış açısı | Kamera eğimi (m06'dan); SITL için seçilecek |
| K | Mesafe hatası kadar ne hızla düzeltilsin (2 m hata → 1 m/s) | 0.5 1/s |
| v_max | Takipte en fazla hız | 2 m/s |
| İvme sınırı | Hız ne kadar sert değişebilir | 3 m/s² (PX4'ün otomatik modlardaki `MPC_ACC_HOR`, `multicopter_autonomous_params.c:88`) |
| Alpha, beta | Filtrenin yeni ölçüme ne kadar güveneceği | SITL'de denenerek seçilecek |
| Hedef hızı katsayısı (c) | Hedefin hızı ne kadar eklensin | 0 (ilk testler); kapalı çevrim test ile açılacak |
| `T_kayip` | Kaç saniye kayıptan sonra Hold'a geçilsin | 1 s |
| Yaw koruma mesafesi | Bunun altında yaw değişmez | ~1 m |
| Hedef yüksekliği, zemin ofseti | Mesafe hesabını düzeltir | Seçilecek |

### Soru 10 — Test (ikinci anlatım ve ilk cevap)
- **Anlatılan:**
  - 10.1 birim testi (bilgisayarda drone'suz, saniyeler içinde biten otomatik testler).
  - 10.2 SITL senaryoları S1–S7. **Açık çevrim** = sabit yön gönderilir; **kapalı çevrim** = script yerde hayali bir hedef tutar ve drone'un konumuna göre gerçek yönü hesaplar.
  - 10.3 log'dan pyulog ile ölçüm.
  - 10.4 logların yeri.
- **Kullanıcının cevabı:** "Arkadaşım gerçek uçuş ortamına yakın bir simülasyon hazırlıyor; o bitince tamamen oraya geçeceğiz. O bitene kadar her şey bizde: kod yazımı bitince Gazebo'da en basit testten başlayıp oluşabilecek tüm durumları test edeceğiz."
- **Kayıt:**
  - **10.2: Tüm senaryolar (S1–S7)** bu spec'te, en basitten karmaşığa doğru test edilir.
  - Gerçekçi simülasyon, Ahmet'in m06 işidir. O hazır olunca testler oraya taşınır; bu spec'e "m06 hazır olunca testler oraya taşınacak" notu düşülür.
  - **11 için geçici çözüm:** m06 hazır olana kadar sahte yönü gönderen test script'i bu işin parçasıdır ve biz yazarız. Kalıcı göndericinin kim ve nerede olacağı yine Vision ve m06 ile konuşulacak.
- **Logların yeri (kullanıcının gereksinimi):** "Ek bir uçuş modu yazdığımız için loglar gerçek uçuşta 6C'ye takılı SD karta, simülasyonda ULog olarak benim bilgisayarıma kaydedilmeli."
  - **Bulgu:** PX4 bunu zaten kendisi yapıyor, kod gerekmiyor:
    - Gerçek uçuşta loglar SD karta yazılır: `/fs/microsd/log/<tarih>/<saat>.ulg` (`src/modules/logger/logger.cpp:1296`).
    - SITL'de loglar laptoptaki `build/px4_sitl_default/rootfs/log/<tarih>/<saat>.ulg` klasörüne yazılır (laptopta görüldü, ör. `2026-09-29/18_45_10.ulg`).
    - Varsayılan olarak loga giren konular: `trajectory_setpoint` (bizim isteğimiz), `vehicle_status` (mod değişimleri, Hold), `vehicle_command` (Hold isteği), `vehicle_local_position`, `vehicle_attitude`, `vehicle_control_mode`, `actuator_motors` (`logged_topics.cpp:131-150, 214`).
  - **Dikkat edilecekler (karar bekliyor):**
    - Bizim girdimiz `debug_vect`, yalnızca `SDLOG_PROFILE`'da "debug" biti açıksa kaydedilir (`logged_topics.cpp:290-294`, bit 5).
    - Gerçek kartta log varsayılan olarak yalnızca arm iken alınır (`SDLOG_MODE`=0); masa testinde kayıt olmaz.
    - SITL log klasörü `build/` içinde. `make clean` ile ya da en eski klasörler silinirken kaybolur (`SDLOG_DIRS_MAX`=7, `ROMFS/px4fmu_common/init.d-posix/rcS:183`). Testten sonra repo dışına kopyalanmalı.
    - Modülün iç durumu (filtre kestirimi, kayıp durumu, atılan mesaj sayısı) varsayılan topic'lerde yok; yeni mesaj eklemek ise yasak (`msg/` kilitli).

### Log kararları (L1–L4)
- **L2 — Kullanıcının gereksinimi (önemli):** "Her durumu log kaydına almamız gerek. Bunun için ek kod yazmak gerekirse de yazalım. Alpha-beta filtresinin girdisi ve çıktısı ve bunların analizi çok önemli."
  - Kullanıcının örneği: Bir projede özelleştirilmiş Betaflight'ta "track hold" modu vardı. OSD'de hedef kutusu (bbox) görünüyor, mod açılınca drone burnunu yaw ekseninde hedefe çeviriyordu. Bu modu log'da incelemek için `trk` önekli bir alan sözlüğü yapılmıştı, ör. `trkAzErr` = azimut hatası.
  - **Kural (bu spec ve sonraki her özelleştirme için):**
    - Yapılan her özelleştirmenin iç durumu loga yazılır.
    - Her log alanı için bir **log sözlüğü** yazılır: alan adı, anlamı, birimi, frame'i, hangi durumda ne değer aldığı. Log incelenirken bu sözlüğe bakılır.
    - Sözlük spec klasöründe tutulur ve kodla birlikte güncellenir.
  - **Teknik seçenekler (karar bekliyor):**
    - (a) PX4'ün hazır `debug_array` mesajı (`msg/DebugArray.msg`): ad + 58 sayılık dizi, tek mesajda. Sayıların sırası ve anlamı sözlükte tanımlanır.
    - (b) Yeni bir uORB mesajı: alan adları logda doğrudan görünür. Ama `msg/` kilitli; Hüseyin'in onayı ve kilit listesine yol eklenmesi gerekir. Yeni mesajı loglamak için kilitli `logged_topics.cpp`'yi değiştirmek gerekmez: PX4 SD karttaki `etc/logging/logger_topics.txt` dosyasından ek topic okuyabiliyor (`logged_topics.cpp:533`).
    - (c) `debug_key_value`: alan başına bir mesaj, `trkAzErr` gibi en fazla 10 karakterlik adlarla. Her döngüde çok sayıda mesaj gerekir; logger hepsini yakalamayabilir (doğrulanacak).
- **L1:** Kullanıcı "her durum kaydedilsin" dediği için log ayarındaki debug biti açılır. Debug biti açık değilse (a) ve (c) loga girmez.
- **L3 — Karar:** Varsayılan kalır (`SDLOG_MODE` = 0, yalnızca arm iken log). Kullanıcı: "Masa testi yapacağımda parametreden 0/1 ayarlarım; bu zaten normal PX4 parametresi." Not: Bu parametre değiştikten sonra kartın **yeniden başlatılması** gerekir (`logger/module.yaml:31`, `reboot_required: true`).
- **L4 — Karar:** SITL logları silinebildiği için (`make clean`, 7 klasör sınırı) her testten sonra masaüstündeki **`~/Desktop/AUTO-FOLLOW LOG/`** klasörüne kopyalanır. Klasör kullanıcının isteğiyle 2026-11-09'da açıldı. Repo dışında olduğu için kural 9 ile çelişmez. Spec'e log dosyasının adı yazılır.

### L2 ve test kararları (kesin)
- **L2 — Kesin karar:** Şimdi PX4'ün hazır `debug_array` mesajı kullanılır ve log sözlüğü yazılır. Hüseyin'e kendi mesaj tipimiz (b) sorulur; onaylarsa sonradan ona geçilir ve sözlük aynen kullanılır. Alan adları ve önekleri (Betaflight'taki `trk…` gibi) yazılırken kullanıcıya sorulur.
- **Ekip kuralı önerisi:** "PX4'te yapılan her özelleştirme loga girer ve bir log sözlüğü olur" kuralı ve masa testinde `SDLOG_MODE` notu kullanıcının istediği durum. Kullanıcı bunu ekibin WhatsApp grubuna atacak. Kuralı herkes için bağlayıcı yapmak, çatı repoda standart değişikliği demek (`agent-os-profilleri/` → derleme script'leri → üç repoda PR); bu ayrı bir iştir (m00, kullanıcı ve repo sorumlusu onayıyla).
- **Kullanıcının netleştirmesi (aynı gün):** "Sözlük kesin olacak. Yazılan durumları logda **kendi adlarıyla** göreceğim. Bunun için ek kod yazılacak mı?"
  - **Cevap:** Her iki seçenekte de ek kod var: modül her döngüde bir log mesajı doldurur ve yayınlar. Ama alanları logda **kendi adlarıyla** görmek yalnızca (b) kendi mesaj tipimizle mümkün. (a) `debug_array`'de alanlar `data[0]`, `data[1]`… olarak görünür; adlar ancak sözlükten ya da sözlüğü kullanan analiz script'inden gelir.
  - **⚠️ Düzeltme (önceki bilgi eksikti):** "SD karttaki `logger_topics.txt` ile kilitli dosyaya dokunmadan ek topic loglanır" bilgisi eksikti. Bu dosya varsa PX4 **yalnızca dosyadaki topic'leri** loglar ve varsayılan listeyi tamamen devre dışı bırakır (`logged_topics.cpp:531-540`). Bu yüzden (b) için doğru yol, `src/modules/logger/logged_topics.cpp`'ye bir `add_topic` satırı eklemektir. Bu dosya da kilitli.
  - **(b) için gereken kilitli PX4 değişiklikleri:**
    - yeni `msg/<Ad>.msg`,
    - `msg/CMakeLists.txt`'e bir satır (mesaj listesi `msg/CMakeLists.txt:39`),
    - `src/modules/logger/logged_topics.cpp`'ye bir satır.

    Bunlar Hüseyin'den istenecek kilit listesi genişletmesine eklenir.
- **L2 — Güncel kesin karar (önceki "(a) şimdi, (b) sonra" kararının yerine geçer):** **(b) kendi mesaj tipimiz.** Alanlar logda kendi adlarıyla görünür. Kullanıcı: "Kilitli dosyalara böyle durumlarda dokunuruz, sıkıntı yok."
  - Gereken kilitli yollar, Hüseyin'den istenecek tek kilit listesi talebine eklenir: `src/modules/<ad>/`, iki `.px4board`, `msg/<Ad>.msg`, `msg/CMakeLists.txt`, `src/modules/logger/logged_topics.cpp`.
  - Çatı kuralı gereği listeyi Claude kendisi genişletmez; ekleme ayrı ve açık bir PR ile, repo sorumlusunun onayıyla yapılır.
  - Hüseyin reddederse geri dönüş: (a) `debug_array` + sözlük.
- **10.1 — Karar:** Birim testi yapılır ama **kısa tutulur**. Yalnızca temel hesaplar sınanır: mesafe/yön hesabı, hız yasası ve sınırları, bozuk veri, zaman aşımı. Süre kısıtlı olduğu için hemen SITL'e geçilir.
- **10.2 — Karar:** SITL senaryoları S1–S7 (en basitten başlayarak).

### Soru 14 — Kapsam ve toparlama
- **Cevap:** "14 öneri gibi olsun" (**öneri kabul**). Tek değişiklik 14.3'te.
- **14.1 Kapsam dışı:**
  - C seçeneği ve ayrıntılı failsafe → m16
  - Nihai yasa ve ince ayar → m13
  - Pi tarafı, ICD ve kalıcı gönderici → Vision (m3–5, m12)
  - Gerçekçi simülasyon ve insan modeli → m06
  - Gerçek uçuş → m22, m25
  - Flash'ta yer açma → m14
  - Ekip için "log sözlüğü" standardı → ayrı m00
- **14.2:** `tech-stack.md`'deki "entegrasyon yaklaşımı: Karar bekliyor" satırı için spec'e ve PR açıklamasına "karar: external mode, güncellenmeli" notu düşülür. Güncellemeyi repo sorumlusu yapar.
- **14.3 — Değişti:** Kullanıcı: "`guidance-yasalari.md` benim çalışmam içindi. Onun yerine benim ne yaptığımı anlatan bir rapor `.md` daha iyi olur."
  - Masaüstündeki dosya spec'e alınmaz ve ona dokunulmaz.
  - Spec klasörüne, işin ne olduğunu, hangi kararların neden alındığını, nasıl test edildiğini ve sonuçlarını sade dille anlatan bir **rapor** yazılır. Rapor karar günlüğünden ve uygulama notlarından derlenir. Dosyanın adı oluşturulurken kullanıcıya sorulur.
  - `planning/visuals/01-ust-seviye-akis.md` kopyasındaki masaüstü dosyası bağlantısı, ileride bu rapora işaret edecek şekilde değiştirilir. Eski klasördeki asıl şema değişmez.
- **14.4:** Eski iki taslak spec'e dokunulmaz; bu spec'te "taslaktı, yerini bu spec aldı" atfı yapılır.
- **14.5 — İş sırası:**
  1. İskelet (SITL + 6C derlemesi)
  2. Guidance + alpha-beta
  3. Kısa birim testi
  4. SITL S1–S5
  5. Hold geçişi
  6. S6–S7 + log mesajı ve sözlüğü

  Yetişmeyenler "m16'ya kalanlar" listesine yazılır.

---

### Shape-spec sonrası, write-spec öncesi (2026-11-09)
- **Adlar (kullanıcı):** Mod adı **"AUTO FOLLOW"**. Parametreler buna paralel olarak **`AF_XXX`**.
  - Çakışma kontrolü: PX4 v1.17.0 kaynağında `AF_` önekli parametre yok; `auto_follow` adlı modül, topic veya mesaj da yok.
  - Benzer adlı bir PX4 modu var: PX4'ün kendi Follow Me modu kodda `NAVIGATION_STATE_AUTO_FOLLOW_TARGET` / `AutoFollowTarget` adlarını kullanıyor (`commander/ModeUtil/control_mode.cpp:166`). Çakışma yok, ama log ve QGC'de karıştırılmaması için not edildi.
- Spec-shaper'ın bulduğu açıklar kullanıcıya sunuldu. Kullanıcının cevapları:
  - (1) süreler parametre olsun, varsayılanlar güvenli seçilsin;
  - (2) eşikler tahmin olacağı için parametre olsun, konuşulacak;
  - (3) ve (4) anlaşılmadı, sade anlatılacak;
  - (5) "hedef yokken çalışırsa ne olur ki?";
  - (6) TBD yerler tek tek sorulacak.

- **Cevaplar (2026-11-09):**
  - **1 — Karar:** Veri zaman aşımı `AF_DATA_TOUT` = 0.5 s; bu süre dolunca "kayıp" başlar ve drone yerinde bekler. `AF_LOST_T` = 1.0 s; "kayıp" başladıktan 1 s sonra Hold. Toplamda son geçerli mesajdan 1.5 s sonra Hold. Gerekçe: Pi 10–30 Hz gönderecek, 0.5 s 5–15 kayıp mesaj demek; PX4 offboard kaybı da 1 s bekler (`COM_OF_LOSS_T`).
  - **2 — Karar:** Bütün eşikler parametre olur, testlerden sonra QGC'den değiştirilir.
    - `AF_NORM_TOL` = 0.1. İnce ayar değil, bozuk veri yakalayıcı.
    - `AF_MIN_DEP` = 10°, `AF_MAX_RNG` = 40 m. Gerekçe: Açı küçüldükçe açı hatası mesafe hatasına büyüyerek yansıyor. 5 m irtifada 1° hata, 30°'de ~0.5 m, 10°'de ~3 m, 5°'de ~10 m mesafe hatası yapıyor.
    - Çevrim hızı parametre değil, kodda sabit 50 Hz.
  - **3 — Karar:** yükseklik farkı = drone yüksekliği − `AF_GND_OFS` − `AF_TGT_HGT`; mesafe = yükseklik farkı / tan(aşağı bakış açısı); istenen mesafe = yükseklik farkı / tan(`AF_TRK_ANG`). Varsayılanlar: `AF_TGT_HGT` = 1.0 m, `AF_GND_OFS` = 0 m. Örnek: 10 m, 30°; düzeltmesiz 17.3 m, hedef yüksekliği 1.2 m ile 15.2 m.
  - **4 — Karar:** AUTO FOLLOW log mesajı **her logda her zaman** kaydedilir (varsayılan topic listesi); kullanıcı ayrıca bir ayar açmaz. Pi'den gelen ham yön de bu mesajın içine kopyalanır. Böylece L1'deki "debug bitini aç" gereği kalkar.
  - **5 — Karar: (a).** `can_arm_and_run` hedef yokken de `true` kalır; `false` olursa PX4 RTL'e düşer. Hedef görünmezken moda girilirse D aynen uygulanır (1.5 s içinde hedef yoksa Hold). Pratikte mod, hedef görünürken açılır.
  - **6 — Kullanıcı:** "ICD'de bana body frame (LOS) ve timestamp gelecek." Kalan TBD'ler daha önce cevaplandı.
    - **Bulgu:** PX4 v1.17.0'da MAVLink `DEBUG_VECT` ve `DEBUG_FLOAT_ARRAY` mesajlarının kendi zaman damgası alanı FC'de **atılıyor**; uORB'a varış zamanı yazılıyor (`mavlink_receiver.cpp:2804` ve `:2822`). Yani Pi'nin zaman damgası ancak mesajın **veri kısmında** taşınırsa FC'ye ulaşır. `DEBUG_VECT`'in veri kısmı yalnızca x, y, z (3 sayı); `DEBUG_FLOAT_ARRAY`'in veri kısmı 58 sayı (`msg/DebugArray.msg`). Karar bekliyor.
  - **Parametre adları — Karar:** `AF_TRK_ANG`, `AF_K_DIST`, `AF_K_FF`, `AF_VEL_MAX`, `AF_ACC_MAX`, `AF_ALPHA`, `AF_BETA`, `AF_DATA_TOUT`, `AF_LOST_T`, `AF_YAW_MIN_D`, `AF_TGT_HGT`, `AF_GND_OFS`, `AF_NORM_TOL`, `AF_MIN_DEP`, `AF_MAX_RNG`. Kullanıcı "okey" dedi. Diğer adlar (modül, log mesajı, dosyalar) henüz onaylanmadı.
  - **Kullanıcının sorusu:** AUTO FOLLOW, PX4'ün `AUTO_FOLLOW_TARGET`'ı ile karışır mı? Yalnızca logda mı, yoksa çalışırken de mi? Cevap bir sonraki girişte.

- **AUTO_FOLLOW_TARGET sorusunun cevabı:** Çalışma anında çakışma yok. PX4 modları numarayla ayırıyor (Follow Me = 19, `VehicleStatus.msg:55`; AUTO FOLLOW = 23–30, `:59-66`). Kod, parametre ve topic adları da ayrı. Karışıklık yalnızca insan tarafında olabilir: QGC mod listesinde iki benzer ad görünür ve log araçları 19'u "Auto Follow" diye gösterebilir.
  - **Karar:** Adlar kalır. Log mesajına AUTO FOLLOW'un mod numarası yazılır.
  - **Log sözlüğüne ve rapora bir uyarı yazılır:** "PX4'ün kendi `AUTO_FOLLOW_TARGET` (Follow Me, `nav_state` 19) modu bizim AUTO FOLLOW ile ilgili değildir."
  - Kodda hiçbir şeye `AutoFollowTarget` / `follow_target` adı verilmez.
- **Zaman damgası — kullanıcı:** "Vision'daki arkadaşım bana body frame verisi ve timestamp gönderecek; girdimiz bu. Geldikten sonra ne yapacağımız bize kalmış. İsteklerime göre uygun olan neyse onu söyle, kafama yatarsa yaparız." Öneri bir sonraki mesajda sunuldu, karar bekliyor.

- **Girdi mesajı — Karar (5-a'nın yerine geçer):** MAVLink **`DEBUG_FLOAT_ARRAY`** → uORB `debug_array` (`mavlink_receiver.cpp:2814-2832`). Ad `AF_LOS`. Varsayılan kutu yerleşimi (ICD gelene kadar varsayım):
  - [0..2] LOS x, y, z
  - [3] yaş (ms)
  - [4] sıra numarası
  - [5] hedef var (1) / yok (0)
- **Kullanıcının sorusu:** "Yine de logda her şeyi kendi isimleriyle göreceğiz değil mi?"
  - **Cevap:** Evet. Gelen değerler modülde AUTO FOLLOW'un kendi log mesajına adlı alanlar olarak kopyalanır (karar 4 + L2-b), ör. LOS x/y/z, yaş, sıra no, hedef var. Bu mesaj her logda her zaman kaydedilir.
  - Ham `debug_array` logda `data[0]`… olarak yalnızca debug biti açıksa görünür; buna ihtiyaç yok.
  - Koşul: Kendi mesajımız için gereken kilitli yolları (`msg/`, `logged_topics.cpp`) Hüseyin'in onaylaması. Onaylamazsa geri dönüş yolunda adlar logda görünmez.

- **Zaman bilgisinin kullanımı — Karar (kullanıcı: "bunlar tamam"):**
  - Pi zamanı **yaş (ms)** olarak gönderir; yanında sıra numarası ve hedef var/yok bayrağı.
  - FC eskiliği gerçek yaşa göre kontrol eder ve gecikmeyi loga yazar.
  - "Hedef yok" bayrağı gelince kayıp durumu hemen başlar.
  - Gecikme telafisi m15'te yok; loglardaki gerçek gecikmeye göre gerekirse m13/m16'da eklenir.
  - Gerekçe: Pi ve Pixhawk saatleri farklı, "yaş" saat eşitlemesi gerektirmiyor; eskilik kontrolü güvenliği doğrudan artırıyor; ihtiyaç tahminle değil veriyle belirlenecek.
- **Diğer adlar — Karar (kullanıcı: "bunlar tamam"):**
  - modül `auto_follow`
  - log mesajı `AutoFollowStatus.msg` → `auto_follow_status`
  - Pi mesajı `AF_LOS`
  - kaynak dosyalar `AutoFollow.cpp/.hpp`, `AutoFollowGuidance.cpp/.hpp`, `AlphaBetaFilter.hpp`
  - birim test `AutoFollowGuidanceTest.cpp`
  - script'ler `tez/sitl/af_los_gonder.py`, `tez/analiz/af_log_analiz.py`
  - spec dosyaları `log-sozlugu.md`, `rapor.md`

  Log alanlarının adları write-spec'te sorulacak.
- **Kullanıcının talimatı:** "Şimdi write-spec'e geçme. Bu soruları, konuşmaları, her şeyi kaydet: şu zamana kadar ne yaptık, nasıl yaptık, seçimler neydi, neden seçtik ve şu ana kadar yaptıklarımızla nasıl bir sistem oluşuyor; her şeyi en ince detayına kadar kaydet."
  - Bunun üzerine:
    - `requirements.md` bugünkü bütün kararlarla güncellendi;
    - spec klasörünün köküne bütün süreci ve oluşan sistemi anlatan `rapor.md` yazıldı.
  - Write-spec kullanıcı onayı bekliyor.

## Açık konular (güncel, 2026-11-09 gece)

Güncel liste `../rapor.md` Bölüm 11'de ve `requirements.md` Bölüm 10'da. Kısaca:
- mod kaydının teknik ayrıntıları,
- masa testinde GPS yokken ne görüleceği,
- log alan adları,
- RC override,
- şema kopyalarının güncellenmesi (onaylandı, write-spec'te),
- Vision ile girdi biçimi,
- m06'dan kamera eğimi,
- Hüseyin'den kilit listesi onayı.

---

## Write-spec turu (2026-11-10)

Spec-writer ajanı `spec.md`'yi yazdı ve iki şema kopyasını güncelledi (commit `164b6131f0`, taslak). Claude, ajanın bulgularını PX4 kaynağında kontrol etti. Sonra belgelerdeki hataları, yeni bulguları ve onay bekleyen önerileri üç grupta kullanıcıya sundu: **A** belgelerdeki hatalar, **B** yeni bulgular, **C** öneriler. Aşağıda her maddenin sorusu, kullanıcının cevabı ve sonucu var.

### A. Belgelerdeki hatalar

- **A1 — S6/S7 iki belgede farklıydı.**
  - Sorun: Spec-shaper `requirements.md` §3.12'ye eski taslak şemadan S6 = "RC kaybı", S7 = "modül sağlığı" yazmıştı. Kullanıcıyla konuşulan ve raporda (§4.9) duran tabloda ise S6 = yerde duran hayali insan, S7 = yürüyen hayali insan.
  - Claude'un önerisi: konuşulan tablo esas olsun. RC kaybı ve modül donması testleri süre kısıtı yüzünden m16'ya kalsın.
  - Kullanıcı: "En konuştuğumuz hale getir."
  - **Karar:** S1–S7, konuşulan tablodur. Eski taslaktaki "kayıt ve başlatma" ile "mod seçimi ve çıkış" başlıklarındaki kontroller yeni senaryo olmadı; her test oturumunun başındaki **ön kontroller** olarak yazıldı. RC kaybı ve modül donması testleri bu spec'te yok; m16 adayı olarak kapsam dışına yazıldı.
- **A2 — S1'in beklentisi yanlış kurulmuştu.**
  - Sorun: "Hedef önünde → ileri gider" her zaman doğru değil. Drone'un ileri mi geri mi gideceği hedefin göründüğü açıya bağlı. Aşağı bakış açısı takip açısından (30°) sığsa hedef uzaktadır ve drone ileri gider. Dikse hedef yakındır ve drone geri gider. Raporun kendi örneğinde 37° → 1.8 m/s geri.
  - Kullanıcı: "Dediğin gibi olsun."
  - **Karar:**
    - S1a: uzak hedef, 18° → ileri; hız 2 m/s'de kırpılır.
    - S1b: yakın hedef, 37° → ~1.8 m/s geri.
    - S3'ün beklentisi de netleşti: hedef neredeyse tam altta (80°) → geri, hız 2 m/s'de kırpılır. Eski metin "geri gider ya da durur" belirsizdi.
- **A3 — Hedefsiz girişte süre.**
  - Sorun: Raporun durum şeması 1.0 s gösteriyordu, karar ise 1.5 s idi.
  - Kullanıcı: "Okey."
  - **Karar:**
    - Zaman referansı `max(son geçerli mesaj, giriş anı)`.
    - Girişte geçerli veri yoksa KAYIP_BEKLE ile başlanır.
    - Hold zamanı giriş + 0.5 + 1.0 = 1.5 s.
- **A4 — İş sırası çakışıyordu.**
  - Sorun: S4'ün Hold kısmının testi, Hold kodundan önceki adıma yazılmıştı.
  - Kullanıcı: "Okey."
  - **Karar:** 4. adımda S4'ün yalnızca KAYIP_BEKLE kısmı test edilir. Hold kısmı 5. adımdan (Hold geçişi) sonra test edilir.
- **A5 — Masa testinde `SDLOG_MODE` değeri.**
  - Sorun: Raporda 2 yazıyordu, oysa kullanıcı önce "0/1 oynarım" demişti.
  - Kullanıcı: "Bunu ben loglardan kendim ayarlayacağım."
  - **Karar:** Belgeler değer önermez. Seçenekler yalnızca bilgi olarak yazılır: 1 = açılıştan disarm'a, 2 = açılıştan kapanışa. "Kart yeniden başlatılmalı" notu kalır.

### B. Yeni bulgular

- **B1 — MAVLink 2.**
  - Bulgu: `DEBUG_FLOAT_ARRAY`'in `data` alanı bir MAVLink 2 ek alanıdır (`common.xml:7630-7631`). MAVLink 1 ile gelirse değerler 0 olur.
  - Kullanıcı Vision tarafıyla görüştü: "pymavlink'te MAVLink 2.0 kullanıyormuş."
  - **Durum:** Kullanıcının bildirimiyle doğrulandı. Masa ve SITL testinde `los_frd` alanlarının sıfır gelmediği de kontrol edilecek.
- **B2 — Modülün açılışta başlatılması.**
  - Bulgu: PX4, arm iken yeni mod kaydını reddediyor (`ModeManagement.cpp:371-380`). Bunun amacı, uçuş sırasında mod listesinin değişmesini engellemek.
  - Kullanıcı: "Arm etmeden önce başlatma işi saçma, onu çözelim. Galiba B seçeneği; eğer çözüm oysa B olsun."
  - Claude'un kontrolü:
    - `rc.mc_apps` her multikopter açılışında, arm'dan önce çalışıyor.
    - SITL: `init.d-posix/rcS:289` → `rc.vehicle_setup:20-24` → `rc.mc_apps`.
    - 6C: `init.d/rcS:485` → aynı yol.
    - `mc_nn_control` da böyle başlıyor (`rc.mc_apps:40-43`).
    - Sonuç: Satır eklenince modül her açılışta kendiliğinden başlar; kullanıcının bir şey yapması gerekmez. B gerçekten çözüm.
  - **Karar: B2-b.**
    - `ROMFS/px4fmu_common/init.d/rc.mc_apps`'e bir satır eklenir.
    - Bu **yedinci kilitli yol**; Hüseyin'e giden talebe eklenir.
    - Hüseyin reddederse geri dönüş (a): SITL'de elle, 6C'de SD kartta `etc/extras.txt`.
    - Satırın koşulsuz mu, açma/kapama parametresiyle mi olacağı açık; kullanıcıya soruldu (spec A13).
- **B3 — Açık çevrimde burun dönmeye devam eder.**
  - Kullanıcının sorusu: "Açık çevrim dediğin SITL olmadan kısa bir doğrulama testi değil mi? Öyleyse sorun yok; hızlıca yapıp SITL testlerine geçmemiz gerek."
  - Cevap: SITL'siz kısa test **birim testi**dir (10.1). Açık çevrim testleri de SITL'de yapılır, ama basittir: script sabit bir yön gönderir.
  - Plan değişmez: kısa birim testi → SITL açık çevrim (S1–S5) → SITL kapalı çevrim (S6–S7).
- **B4 — Yerde arm'lıyken moda geçiş.**
  - Kullanıcı: "AUTO FOLLOW'da herhangi bir kalkış yok. Arm'lıyken ve yerdeyken moda geçmese daha iyi olur; oraya bir güvenlik adımı getirmemiz gerek."
  - **Karar:** Güvenlik adımı eklenecek.
  - Claude'un kaynak kontrolü:
    - Arming check cevabında `can_arm_and_run = false` gelirse PX4 o modu "çalışamaz" işaretler (`externalChecks.cpp:158-160, 188-190`).
    - Arm'lı araçta mod geçişi `canRun`'a bakar (`UserModeIntention.cpp:58-59`). Bu durumda geçiş reddedilir; QGC'de "Switching to … is currently not available" yazar ve uyarı sesi çalar (`Commander.cpp:2620-2638`).
    - Disarm iken geçiş yine serbesttir (`UserModeIntention.cpp:54-55`).
    - Mod aktifken `can_arm_and_run = false` olursa RTL'e düşülür (`failsafe.cpp:698-702`). Bu yüzden koşul yalnızca mod aktif **değilken** kullanılmalı.
  - Yöntem seçenekleri kullanıcıya sunuldu (spec A14):
    - (a) yerdeyken ve mod aktif değilken PX4'e "şu an çalışamam" bildirmek,
    - (b) girişte yerdeyse modülün hemen Hold istemesi.
  - Öneri (a). Cevap bekleniyor.

### C. Öneriler

- **C1 — Mod kaydı ayrıntıları.**
  - Kullanıcı: "Bu modda arm etmek yasak olsun, ancak arm değilken bu moda geçebileyim."
  - **Karar:** `mode_req_prevent_arming = true`. Disarm iken moda geçiş serbest; PX4 bunu zaten sağlıyor, kod gerekmez.
  - Mod gereksinimleri (açısal hız, tutum, yerel irtifa, yerel konum) ve kontrol bayrakları öneri kabul.
  - RC çubuğuyla müdahale (spec A2) cevaplanmadı; yeniden soruldu.
- **C2 — Davranış ayrıntıları.**
  - Kullanıcı: "Okey."
  - **Karar (öneri kabul):**
    - Filtre yatayda çalışır; ilk ölçümde hedef hızı 0 kabul edilir; EKF reset'te filtre sıfırlanır.
    - `AF_ALPHA` 0.5, `AF_BETA` 0.17.
    - İvme sınırı moda girişte drone'un o anki hızından başlar.
    - Hold reddedilirse hover sürer; istek 1 s arayla en fazla 3 kez tekrarlanır.
    - Drone kendi konumunu kaybederse yatay hız 0 istenir.
    - Parametrelerin birimleri ve min/max değerleri spec'teki gibi.
    - Log mesajı mod kapalıyken (PASIF) de 50 Hz yayınlanır.
- **C3 — Log alanlarının adları.**
  - Kullanıcı: "Buradaki isimler gayet güzel, ama bizim yazdığımız, isimlerini verdiğimiz her şeyi detaylı kaydet; detaylı sözlük hazırlanacak."
  - **Karar:**
    - Log alan adları spec tablosundaki gibi; önek yok.
    - Durum adları PASIF / TAKIP / KAYIP_BEKLE / HOLD_ISTENDI.
    - Bizim verdiğimiz **bütün adlar** için ayrıntılı sözlük yazılır: mod, modül ve komutları, dosyalar, girdi mesajı, parametreler, log mesajı ve alanları, durumlar, doğrulama sonuçları, script'ler.
    - Sözlük, adı önceden onaylı `log-sozlugu.md` dosyasıdır; kapsamı genişletildi. İlk sürümü bu turda yazıldı. Kod yazıldıkça aynı commit'te güncellenir.

### Bu turdan sonra açık kalanlar (kullanıcıya soruldu; cevaplar aşağıda, "Son cevaplar")

- spec A13: `rc.mc_apps` satırı koşulsuz mu, açma/kapama parametresiyle mi? Parametreyle olursa adı kullanıcı verir.
- spec A14: yerde arm'lıyken geçiş engelinin yöntemi, (a) ya da (b).
- spec A2: RC çubuğuyla müdahale (çubuk oynayınca Position'a geçiş).
- Henüz sunulmamış iki öneri:
  - kodun iç düzeni: hesaplar `AutoFollowGuidance` kütüphanesinde, zamanı argüman alan saf fonksiyonlar (birim testi için);
  - masa testinde gözlenecekler listesi (spec A3).

### Son cevaplar (2026-11-10)

- **A14 — Kullanıcı: "1-a".** **Karar:** drone yerdeyken ve mod aktif değilken modül arming check'e `can_arm_and_run = false` der; PX4 arm'lı araçta geçişi reddeder, QGC'de mesaj + uyarı sesi. Disarm iken geçiş serbest; mod aktifken koşul devreye girmez (RTL riski yok).
- **A13 — Kullanıcı: "2-b".** Soru: "6C'ye ilk yüklediğimde 0 olarak gelecek; açıp reboot atmam yeterli mi, güç kesip açmam mı lazım?" Cevap: QGC'den "Reboot Vehicle" yeterli; PX4 açılış dosyalarını her reboot'ta baştan çalıştırır, parametre kalıcı saklanır. Kullanıcıya soruldu: ad **`AF_ENABLE`** (kullanıcı seçti), varsayılan **0 = kapalı** (kullanıcı seçti, öneriydi). SITL'de `PX4_PARAM_AF_ENABLE=1`.
- **A2 — Kullanıcı: "evet, güvenlik amaçlı olsun".** **Karar:** `flag_control_auto_enabled = true`; pilot çubuğu oynatınca Position'a geçilir (`COM_RC_OVERRIDE`); SITL'de doğrulanacak.
- **İç düzen — Kullanıcı: "okey".** **Karar (öneri kabul):** hesaplar `AutoFollowGuidance` kütüphanesinde, zamanı argüman alan saf fonksiyonlar.
- **A3 — Kullanıcı:** "Masa testlerine şimdilik bunlar yeter, ama mesela dışarıda arm etmeden GPS fix olduğunda yapılacak testler eklenebilir; burası geliştirmeye açık, bunu not al, burayı düşüneceğim." **Karar:** liste yeterli. **Not (geliştirmeye açık):** dışarıda, arm'sız, GPS fix'li masa/yer testleri (geometri ve guidance çıktısı görülebilir) sonra eklenebilir; kullanıcı düşünecek.
- Kullanıcı create-tasks'a geçişi onayladı. Son cevaplar `spec.md`, `requirements.md` §3.14, `log-sozlugu.md` ve rapor (sürüm 2.1) dosyalarına işlendi.

### create-tasks turu (2026-11-10)

Görev listesi ajanı `tasks.md`'yi yazdı (commit `f6394fc7b3`). Yeni karar gerektiren üç konu kullanıcıya soruldu:
- **Log mesajı geç geliyordu** (Grup 6), ama S1–S5 ölçümleri onun alanlarına dayanıyor. Seçenekler: (a) Grup 2'ye taşı · (b) sırayı koru, S1–S5'i sonra yeniden koş. Öneri (a). Kullanıcı: **"1-a"**. Log yolları yine Hüseyin'in onayına bağlı.
- **Grup notlarının yeri.** Öneri `implementation/grup-<N>-notu.md`. Kullanıcı: "Kayıt yeri okey, ama dosya adları o grupta ne var anlatan isimler olsun." **Karar:** `implementation/` altında `grup-0-on-kosullar.md`, `grup-1-iskelet-mod-kaydi.md`, `grup-2-guidance-filtre-log.md`, `grup-3-birim-testi.md`, `grup-4-sitl-acik-cevrim.md`, `grup-5-hold-gecisi.md`, `grup-6-kapali-cevrim-analiz.md` (kullanıcının ilkesine göre Claude'un önerdiği adlar; kullanıcı değiştirebilir). SITL sonuç kayıtları da bu notlara girer.
- **Hold 3 denemede de reddedilirse.** Öneri: hover sürer, QGC'ye uyarı ve log, pilot RC ile devralır; modül kendi başına RTL/iniş istemez. Kullanıcı: **"tamam"**.
- Kullanıcı implement adımı için onay verdi ("güncellemeni yap, implement için onayım var").

### Görev grubu 1 sonrası sorular (2026-11-10)

- **QGC parametre grubu adı** (`module.yaml` zorunlu alan; kaynaklarda yoktu, Grup 1'de geçici `AUTO FOLLOW` kondu). Seçenekler: `AUTO FOLLOW` / `Auto Follow` / `auto_follow`. Öneri `AUTO FOLLOW` (mod adıyla aynı). Kullanıcı: **"öneri"** → **Karar: `AUTO FOLLOW`**.
- **`module.yaml` açıklamalarının dili.** Seçenekler: İngilizce (PX4 geleneği, QGC'de görünen) / Türkçe. Öneri İngilizce; Türkçe açıklamalar `log-sozlugu.md`'de. Kullanıcı: **"öneri"** → **Karar: İngilizce**.
- **Lisans başlığı.** Kullanıcı soruyu anlamadı; sade anlatım verildi: başlık yalnızca yorumdur, firmware'e girmez, flash'ı etkilemez; Copyright satırı kodun sahibini, BSD-3 metni kullanım şartını söyler. Seçenekler: (a) "PX4 Development Team" · (b) ekip adı · (c) kişi adı. Öneri (b).
  - Kullanıcı: "A kalsın, biz altına Pamukkale Elektrik-elektronik mühendisliği tez ekibini ekleyelim ama."
  - **Karar:** PX4 satırı kalır; altına ikinci bir Copyright satırı eklenir: `Copyright (c) 2026 Pamukkale Elektrik-Elektronik Mühendisliği tez ekibi.` Lisans metni (BSD-3) aynen kalır. Lisans başlığı olan bütün yeni dosyalara, Grup 2 bittikten sonra uygulanır.

### Görev grubu 2 sonrası sorular (2026-11-10)

Grup 2 ajanı spec'in söylemediği 6 nokta buldu (ayrıntı `implementation/grup-2-guidance-filtre-log.md` Bölüm 7). Kullanıcının cevapları:
- **3 — Uzun veri kesintisinden sonra filtre.** Öneri: `AF_DATA_TOUT` boyunca geçerli veri yoksa filtre de sıfırlansın. Kullanıcı: **"olur"** → **Karar.**
- **4 — EKF konum sıfırlamasında bekleme noktası.** Öneri: PX4 modları gibi tutulan nokta (`_hold_xy`, `alt_hold_z`) sıfırlamanın `delta_xy` / `delta_z` kadar kaydırılsın. Kullanıcı: **"olur"** → **Karar.**
- **Kullanıcının genel talimatı (3. cevapla birlikte):** "Burayı not et. Hep böyle noktaları, en son yaptıklarımızda, seçimlerde, yapılan adımlarda hep rapor olarak kaydedeceğiz." → Uygulama sırasında çıkan her seçim (spec'in söylemediği nokta, seçenekler, seçilen, neden) hem grup notuna hem `rapor.md`'ye ("Uygulamada verilen kararlar" bölümü) yazılır.
- **1, 2, 5, 6:** Kullanıcı daha ayrıntılı anlatım istedi; anlatıldı, cevap bekleniyor. Anlatım sırasında 5'e bağlı yeni bir nokta bulundu: sıra no "öncekinden büyük" kuralı hiç sıfırlanmıyor (`AutoFollow.cpp:268-270`, `AutoFollowGuidance.cpp:75`); Pi uçuşta yeniden başlarsa sıra no 1'den başlar ve bütün mesajlar `CHECK_SEQ` ile atılır.
- **1 — Adı `AF_LOS` olmayan mesajlar `los_*` alanlarına yazılsın mı?** Ayrıntılı anlatıldı (ortak `debug_array` kanalı, örnek). Kullanıcının sorusu: "1a yaparsam logda ne gelmiş tam adıyla görebilecek miyim?" Cevap: evet, `los_*` alanları her zaman Pi'nin `AF_LOS`'unu adlı alanlarla gösterir; yabancı mesaj yalnızca `reject_name_count`'u artırır. Yabancı mesajın adını/içeriğini görmek gerekirse kod gerekmeden `SDLOG_PROFILE`'a 32 eklenir (debug grubu, `logger/module.yaml:82`, `logged_topics.cpp:290-294`). Kullanıcı: **"1-a"** → **Karar: yazılmaz** (şu anki hal).
- **2 — Nedene göre `perf` sayaçları.** Kullanıcı: **"2-a"** → **Karar: eklenmez**; sayaçlar log mesajında ve `auto_follow status`'ta. Spec'teki cümle düzeltilir.
- **5a — Sıra kontrolünde "önceki".** Kullanıcı: **"5a olsun"** → **Karar:** 1–4. kontrolleri (ad, sonlu, norm, sıra) geçen son mesaj (şu anki hal).
- **5b — "Önceki numara" unutulsun mu?** Kullanıcı kafasının karıştığını söyledi, bütün seçenekler ayrıntılı anlatıldı: (a) `AF_DATA_TOUT` boyunca sıra kontrolünü geçen mesaj yoksa unutulsun · (b) hiç unutulmasın · (c) büyük geri düşüşte hemen kabul (yeni eşik gerekir) · (d) moda her girişte unutulsun. Güvenlik açısından hepsi aynı (Hold'dan sonra takibe kendiliğinden dönülmüyor); fark kullanılabilirlikte. Öneri (a). Kullanıcı: **"a olsun"** → **Karar: (a).**
- **6 — NaN davranışları** (PASIF'te guidance alanları NaN; hiç geçerli mesaj yoksa `time_since_valid` NaN; hedefsiz girişte `lost_time` ilk 0.5 s 0). Kullanıcı: **"tamam"** → **Karar** (şu anki hal).
- Kullanıcının sorusu: "Bu sadece Pi uçuşta AUTO FOLLOW'dayken yeniden başlarsa olur, mod kapalıyken Pi restart atsa sorun olmaz, doğru mu?" Cevap: eski kodda (b) sorun, Pixhawk açık kaldığı sürece Pi **ne zaman** yeniden başlarsa başlasın (mod kapalıyken, yerde, uçuş öncesi) çıkardı; (a) ile hiçbir durumda çıkmaz.

### Düzeltme turu sonrası (2026-11-10)

- **D5 — EKF yön (heading) sıfırlamasında tutulan yaw.** Düzeltme turunda bulundu: KAYIP_BEKLE / HOLD_ISTENDI'de (ve `yaw_frozen` iken) tutulan yaw `delta_heading` kadar kaydırılmıyor; PX4 setpoint'i yalnızca bir kez kaydırıyor (`MulticopterPositionControl.cpp:709-711`), sonraki çevrimde bizim istek eski açıyı geri getirir. Seçenekler: (a) kaydırılsın (karar 4'ün devamı) · (b) böyle kalsın. Öneri (a). Kullanıcı örnekli anlatım istedi; örnekle anlatıldı (PX4 yön sayısı düzelir, drone fiziksel olarak dönmez; kaydırma yoksa drone eski sayıyı tutturmak için gereksiz döner). Kullanıcı: **"1a olsun, Grup 5'te ekle"** → **Karar (a):** tutulan yaw `delta_heading` kadar kaydırılır (`heading_reset_counter`, PX4 kalıbı `MulticopterPositionControl.cpp:709-711`); Grup 5'te uygulanır.
- **Test göndericisi değerleri ve seçenek adları** (`tez/sitl/af_los_gonder.py`). Öneri: hız 20 Hz, yaş 50 ms sabit; seçenekler `--cevrim acik|kapali`, `--los X Y Z`, `--senaryo <kes|hedef-yok|yanlis-ad|nan|norm|sira|eski|ufuk|uzak>`, `--hiz`, `--yas`, `--baglanti` (varsayılan `udpout:127.0.0.1:14540`). Kullanıcı: "Şimdilik önerin gibi olsun, ama ileride değiştirebilirim; Vision'daki arkadaşıma sorayım, test göndericisini ona göre güncelleriz." → **Karar (geçici):** öneri gibi. Vision'a sorulacaklar listesi kullanıcıya verildi (Grup 0.3 ile birlikte).

### Görev grubu 4 sonrası sorular (2026-11-11)

Grup 4 özetiyle 6 nokta soruldu (ayrıntı `implementation/grup-4-sitl-acik-cevrim.md` Bölüm 9, rapor §5.1 U4.16–U4.20). Kullanıcının cevapları:
- **1 — Sıra no hep aynı gelirse (donmuş Pi).** Öneri: "önceki numara" yalnızca `AF_DATA_TOUT` boyunca **hiç `AF_LOS` mesajı gelmezse** unutulsun (5b-a'nın inceltilmesi). Kullanıcı: **"biraz aç"** → örnekli ayrıntılı anlatım verildi; **cevap bekleniyor**.
- **2 — `AF_YAW_MIN_D` = 1 m yeter mi (S3'teki dönme)?** Öneri: şimdilik 1 m, S6–S7'de bakılsın. Kullanıcı: **"okey"** → **Karar.**
- **3 — Yaw dönüş hızı.** Öneri: S6–S7'ye bakıp gerekirse parametre eklemek. Kullanıcı: **"sen şimdiden ekle, parametre dursun"** → **Karar: ayrı yaw hız sınırı parametresi Grup 5'te eklenir.** Adı ve varsayılan değeri kullanıcıya soruldu (kanıt: PX4'ün otomatik modlarındaki sınır `MPC_YAWRAUTO_MAX` = 60°/s, `multicopter_autonomous_params.c:148`, `FlightTaskAuto.cpp:306-307`; bizim mod FlightTask'ı kullanmadığı için yalnızca `MC_YAWRATE_MAX` = 200°/s geçerli, `mc_att_control_params.c:147`).
- **4 — Test göndericisi bağlantı adresi `udpin:0.0.0.0:14540`.** Kullanıcı: **"okey"** → **Karar.**
- **5 — Test akışı script'i repoya alınsın mı?** Kullanıcı: **"script geçici durmasın, benim bilgisayarımda dursun; ileride repoya almaya bakarız, ama şu an benim PC'de"** → **Karar:** repoya girmez, kullanıcının bilgisayarında kalıcı bir yerde durur. Not: script'ler geçici klasördeydi (scratchpad) ve bilgisayar yeniden açılınca silinmişti; Grup 4 ajanının kayıtlarından (yazdığı dosya içerikleri ve sonradan yaptığı düzeltmeler sırasıyla) geri çıkarıldı, derleme kontrolü geçti. Kalıcı yeri ve klasör adı kullanıcıya soruldu.
- **6 — Grup 5'ten sonra hedefsiz girişte 1,5 s'de Hold.** Kullanıcı: **"okey"** → **Karar** (A3 ile tutarlı).
