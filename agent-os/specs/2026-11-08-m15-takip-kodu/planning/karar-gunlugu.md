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

## Açık konular (shape-spec sonunda, 2026-11-09)

- **9. Mod kaydı ayrıntıları** (9.1 ihtiyaç listesi, 9.3 `can_arm_and_run`, 9.4 kontrol bayrakları, 9.5 geçiş yolu): Ayrıca sorulmadı. Diğer kararlardan çıkan öneriler `requirements.md`'de "öneri, write-spec'te teyit" olarak yazılır:
  - `can_arm_and_run` hedef yokken de `true` kalır; aksi hâlde PX4 RTL'e düşer, bu da D kararıyla çelişir.
  - Moda hem QGC'den hem RC anahtarından geçilir.
- **9. Masa testi:** GPS yokken neyin görüleceği.
- **11. Kalıcı gönderici:** Vision ve m06 ile konuşulacak. Geçici test göndericisini biz yazıyoruz.
- **Adlar:** Modül, mod, parametreler, log mesajı ve alanları, sözlük ve rapor dosyaları, test script'leri. Her biri gerektiğinde sorulacak.
- **Kilit listesi talebi:** Hüseyin'e iletilecek.
