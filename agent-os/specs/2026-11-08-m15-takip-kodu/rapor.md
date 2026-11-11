# AUTO FOLLOW (M15): Yapılanlar, kararlar ve oluşan sistem

> **Sürüm:** 7 (Görev grubu 4), 2026-11-11
>
> **Hazırlayan:** Yusuf Kurt (kararlar) · Claude Code (yazım, kaynak araştırması)
>
> **Durum:** Uygulama başladı. **Görev grubu 1 (iskelet) bitti:** modül kendini AUTO FOLLOW olarak kaydediyor, açılışta `AF_ENABLE` = 1 ise başlıyor, arming check'e cevap veriyor, 50 Hz dönüyor; henüz uçurmuyor (guidance Grup 2'de). **Görev grubu 2 (guidance, filtre, log mesajı) bitti:** modül Pi'nin mesajını 9 kontrolden geçiriyor, hedefin yerini bulup alpha-beta ile yumuşatıyor, mod açıkken hız/irtifa/yaw isteğini PX4'e veriyor, hedef kaybında yerinde bekliyor ve her çevrimde `auto_follow_status` log mesajını yayınlıyor. **Görev grubu 3 (kısa birim testi) bitti:** 7 test spec'in sayısal örneklerini (12,0 m, −1,8 m/s, 2 m/s kırpma, ivme sınırı, bozuk veri, 0,5 s / +1,0 s / hedef yok) doğruladı, hepsi geçti, kod değişmedi. **Grup 2 düzeltme turu bitti:** kullanıcının Grup 2 sonrası kararlarıyla filtre uzun veri kesintisinde, Pi'nin sıra no hafızası `AF_DATA_TOUT` sonra sıfırlanıyor; EKF konum sıfırlamasında tutulan nokta kaydırılıyor; 2 test eklendi (9/9 geçti). **Görev grubu 4 (SITL açık çevrim) bitti:** test göndericisi `tez/sitl/af_los_gonder.py` yazıldı; Gazebo'da ön kontroller ve S1a, S1b, S2, S3, S4 (yerinde bekleme kısmı), S5 uçuldu ve loglardan sayıyla ölçüldü; spec'in beklediği değerler görüldü, modül kodunda hata çıkmadı; açık çevrime özgü 2 davranış (S1b salınımı, S3 dönmesi) ve 5 açık soru var (§4.9, §11). PX4'ten Hold isteme Grup 5'te. Sürüm 1 planlamanın (shape-spec) sonunu, sürüm 2 write-spec turundaki kararları, sürüm 3 Grup 1'in, sürüm 4 Grup 2'nin, sürüm 5 Grup 3'ün, sürüm 6 düzeltme turunun, sürüm 7 Grup 4'ün sonucunu anlatır; uygulama sırasında verilen bütün kararlar §5.1'de. Her grubun ayrıntılı notu `implementation/` klasöründe (bkz. "Belge geçmişi").

Bu rapor kod okumadan anlaşılacak şekilde yazıldı. Amaç, bir sorun çıktığında "bu neden böyle?" sorusunun cevabını tek yerde bulmak. Teknik terimlerin açıklamaları sondaki **Terimler sözlüğü**nde.

İlgili dosyalar (hepsi bu klasörde):

| Dosya | İçerik |
|---|---|
| `rapor.md` (bu dosya) | Bütün hikâye ve oluşan sistem |
| `spec.md` | Resmî spesifikasyon: kodun ne yapacağı, `dosya:satır` kanıtlarıyla |
| `log-sozlugu.md` | Bizim verdiğimiz bütün adların sözlüğü: mod, modül, parametreler, log alanları, durumlar, dosyalar |
| `planning/requirements.md` | Gereksinimler: write-spec'in girdisi, geçerli kararların resmî listesi |
| `planning/karar-gunlugu.md` | Her soru, seçenek, cevap ve gerekçe, kronolojik sırayla |
| `planning/tur1-cevaplar.md` | 1. tur cevaplarının kısa tablosu (tarihsel kayıt) |
| `planning/raw-idea.md` | Görevin ilk tanımı |
| `planning/visuals/` | İki akış şeması (Mermaid) |
| `implementation/` | Görev grubu notları: ne yapıldı, neden, nasıl test edildi, sorunlar (`grup-1-iskelet-mod-kaydi.md`, `grup-2-guidance-filtre-log.md`, `grup-3-birim-testi.md`, `grup-4-sitl-acik-cevrim.md`) |

---

## 1. Özet

Drone'daki Raspberry Pi, kamerada insanı bulur ve Pixhawk'a yalnızca **"hedef, drone'a göre şu yönde"** bilgisini (body FRD LOS birim vektörü) ve bu bilginin **ne kadar eski olduğunu** gönderir. M15'te Pixhawk'ın içine **AUTO FOLLOW** adlı yeni bir uçuş modu yazılacak. Bu mod:

1. gelen yönü kontrol eder (bozuk veya eski veriyi atar),
2. yönü dünyaya göre çevirir ve düz zemin kabulüyle hedefin uzaklığını ve yerini hesaplar,
3. hedefin konumunu ve hızını **alpha-beta filtresiyle** yumuşatır,
4. **hız tabanlı** bir kuralla drone'un ne hızla nereye gideceğine ve burnunu nereye çevireceğine karar verir (guidance),
5. bu isteği PX4'e verir. PX4 kendi kontrol zinciriyle motorlara kadar götürür.

Hedef kaybolursa drone önce yerinde bekler, kısa sürede hedef gelmezse **Hold** moduna geçer ve pilot modu yeniden açana kadar takibe dönmez. Modun her iç durumu, logda **kendi adlarıyla** her uçuşta kaydedilir.

**En önemli kararlar:**

| Konu | Karar |
|---|---|
| PX4'e bağlanma | **External mode** modülü (`mc_nn_control` kalıbı) |
| Kodun yeri | `src/modules/auto_follow/`, SITL ve Pixhawk 6C firmware'ine girer |
| Girdi | MAVLink `DEBUG_FLOAT_ARRAY`, adı `AF_LOS`: LOS x/y/z + yaş + sıra no + hedef var/yok (varsayım; ICD bekleniyor) |
| Guidance | Hız tabanlı: hız = c·hedef hızı + K·(mesafe − istenen mesafe), alpha-beta filtresi |
| İstenen mesafe | Takip açısından: yükseklik farkı / tan(takip açısı) |
| PX4'e verilen | `trajectory_setpoint`: yatay hız + sabit irtifa + mutlak yaw |
| Hedef kaybı | Kademeli (D): 0.5 s veri yoksa yerinde bekle, 1.0 s daha gelmezse Hold |
| Log | Kendi mesajımız `auto_follow_status`, her zaman kaydedilir, log sözlüğü yazılır |
| Test | Kısa birim testi + Gazebo SITL'de S1–S7 senaryoları, sonuçlar pyulog ile ölçülür |
| Güvenlik | Bu modda arm yasak, kalkış Position'da; yerde arm'lıyken moda geçiş engellenecek; modül açılışta kendiliğinden başlar |
| Adlar | Mod `AUTO FOLLOW`, parametreler `AF_*` |

---

## 2. Görev ve bağlam

- **Görev:** [Issue #6](https://github.com/Auto-Follow/Auto-Follow/issues/6), "[M15] Body frame hedef vektöründen PWM'e: PX4 takip kodu". Kişi: Yusuf Kurt. Son teslim: **2026-11-15**.
- **Yol haritası:** Madde 15 "PX4 entegrasyon yaklaşımının seçimi". Devamı madde 13 (kontrol algoritması) ve 16 (PX4 takip modu).
- **Issue'nun istedikleri:**
  1. PX4'te neyin nereye bağlanacağının seçenekleri ve gerekçesiyle belirlenmesi;
  2. SITL'de elle verilen bir hedef vektörüyle drone'un tepki verdiğini gösteren çalışan kod;
  3. şemaların ve test sonuçlarının (ne verildi, drone ne yaptı, log adı) spec klasöründe olması;
  4. CI'da `verify-pin`, `derleme-sitl` ve `derleme-fmu-v6c` kontrollerinin yeşil olması.
- **Ekipteki bağlantılar:**
  - **Yusuf Ortatepe (m10, Vision):** Pikselden body frame'e dönüşüm; bizim girdimizi üretecek taraf. Eksenler onunla eşlenecek.
  - **Ahmet Kazalcı (m06, Autopilot/Gazebo):** Gerçekçi simülasyon, kamera montajı ve yaklaşma mesafesi. Takip açısı onun kamera dokümanından gelecek; hazır olunca testler onun simülasyonuna taşınacak.
  - **Hüseyin Uygun (repo sorumlusu):** Kilitli PX4 dosyalarının değiştirilmesine onay verecek kişi.
- **Sabit kısıtlar:**
  - PX4 **v1.17.0'da kilitli**. Değiştirilebilir yollar `tez/pin/allowed-paths.txt`'de; dışındakiler için repo sorumlusunun onayı gerekiyor.
  - Pixhawk 6C'nin flash'ı **~%98 dolu**.
  - Yeni MAVLink mesajı eklenemez.
  - Simülatör Gazebo Harmonic.

---

## 3. Nasıl çalıştık?

### 3.1 Yöntem
- **Agent OS `shape-spec`** aşaması kullanıldı: önce gereksinimler sorularla netleştirildi, kod yazılmadı.
- Kullanıcının koyduğu çalışma kuralları:
  - **Hiçbir kararı Claude vermez.** Her konu için seçenekler artı ve eksileriyle, PX4 v1.17.0 kaynağından **`dosya:satır` kanıtıyla** ve bir öneriyle sunuldu; kararı kullanıcı verdi.
  - **Adlar** (modül, parametre, mod, dosya, topic) kullanıcıya soruldu.
  - Doğrulanamayan her şey "(doğrulanacak)" diye işaretlendi; ad, topic veya alan uydurulmadı.
  - **Her şey kayıt altına alındı.** Kullanıcının sözleriyle: "Bazen dediklerin mantıklı geldi ama çok detaylı bilgiye sahip olmadan verdim; kodu elle yazmayacağım; ne yapıldığını kod okumadan bilecek seviyede yazılsın." Bu yüzden öneriye güvenilerek verilen kararlar **"öneri kabul"** diye ayrıca işaretlendi; sorun çıkarsa ilk bakılacak yerler bunlar.
  - Agent OS bir aşamayı bitirince, açık konular konuşulmadan bir sonrakine geçilmedi.
- Bilgi kaynakları:
  - bu repodaki PX4 v1.17.0 kaynak kodu;
  - çatı repodaki ürün planı (`../agent-os/product/`) ve standartlar (`../agent-os/standards/`);
  - issue #6, #7 (m06) ve #8 (m10);
  - repolardaki diğer dallar.

### 3.2 Zaman çizelgesi

**Oturum 1: 2026-11-08**
1. Issue #6 ve talimat dosyası okundu.
2. Spec klasörünün adı soruldu: `2026-11-08-m15-takip-kodu` (dal adıyla aynı).
3. Şemaları PNG'ye çevirecek araç (`mmdc`, Node.js) kurulu değildi. Kullanıcı "şimdilik PNG'siz devam" dedi.
4. Spec klasörü açıldı; iki şema `planning/visuals/`'a kopyalandı.
5. PX4 kaynağı tarandı ve ilk soru listesi hazırlandı.
6. Kullanıcı "ana çatıdaki agent-os bilgilerini dikkate alıyorsun değil mi?" diye sordu. O ana kadar yalnızca PX4 kaynağına bakılmıştı. Çatıdaki ürün planı ve standartlar okundu, sorular bunlara göre yeniden yazıldı. Bu eksik, sonraki işler için Claude'un hafızasına kural olarak yazıldı.
7. 14 başlıklı 1. tur soru listesi sunuldu. Kullanıcı birçoğunu cevapladı, bazılarını "detaylı konuşalım" diye ayırdı.
8. Kullanıcının isteğiyle bütün repolar tarandı: hiçbir yerde Pi'den yön gönderen kod yok (bkz. 9).
9. Cevaplar `planning/tur1-cevaplar.md`'ye yazıldı ve commit edildi.

**Oturum 2: 2026-11-09** (şarj bittiği için ara verildi, `claude --resume` ile devam edildi)

10. Hedef kaybı davranışı konuşuldu; kullanıcı "önemli" olarak işaretledi. Karar: D.
11. Yükseklik parametreleri ve fmu-v6c kararları verildi.
12. Guidance yasası ayrıntılı konuşuldu: hız tabanlı, alpha-beta, takip açısı.
13. Kullanıcı her şeyin kaydedilmesini istedi; `planning/karar-gunlugu.md` açıldı.
14. Test ve log konuşuldu. Kullanıcının Betaflight "track hold" örneğinden bir log sözlüğü kuralı çıktı. Masaüstünde `AUTO-FOLLOW LOG` klasörü açıldı.
15. Kapsam ve toparlama yapıldı; spec-shaper ajanı `planning/requirements.md`'yi yazdı ve commit edildi.
16. Spec-shaper'ın bulduğu açıklar konuşuldu: süreler, eşikler, yükseklik formülü, log kaydı, hedef yokken moda giriş, TBD'ler.
17. Adlar verildi: `AUTO FOLLOW`, `AF_*`.
18. Zaman damgası konusunda bulgu: `DEBUG_VECT` zaman bilgisini taşıyamıyor. Girdi `DEBUG_FLOAT_ARRAY`'e çevrildi.
19. Kullanıcı write-spec'e geçmeden her şeyin kaydedilmesini istedi: `requirements.md` güncellendi ve bu rapor yazıldı.

**Oturum 3: 2026-11-10** (write-spec)

20. Spec-writer ajanı `spec.md`'yi yazdı, şema kopyalarını güncelledi.
21. Claude ajanın bulgularını PX4 kaynağında kontrol etti; belgelerdeki hatalar (A), yeni bulgular (B) ve öneriler (C) kullanıcıya sunuldu.
22. Kullanıcının cevaplarıyla `spec.md`, `requirements.md`, karar günlüğü ve bu rapor güncellendi; bütün adların sözlüğü `log-sozlugu.md` yazıldı.

### 3.3 Commit'ler (dal `ozellik/m15-takip-kodu`, push yok)

| Commit | Ne |
|---|---|
| `2adda900bb` | Ham fikir, şemalar, 1. tur cevapları |
| `76ae2878a4` | Hedef kaybı davranışı (D, Hold m15'te) |
| `41ab91fa88` | Yükseklik parametreleri (13-iii), fmu-v6c (3.1-ii) |
| `45895b8c3c` | Guidance kararları ve karar günlüğü |
| `04ff974d35` | Test kapsamı ve log kararları |
| `5e0b3cd65e` | Log mesajı ve birim testi kararı |
| `16f53b1fa4` | Log alan adları için gerekenler; `logger_topics.txt` düzeltmesi |
| `6d479e0101` | Kendi log mesaj tipi kararı (L2-b) |
| `e44529d567` | Kapsam ve toparlama (14) |
| `7f34f4cf01` | Açık konular güncellendi |
| `fef6bb9972` | `requirements.md` |
| `b484ec9127` | Cevap tablosuna güncellik notu |
| `8769196099` | Mod adı AUTO FOLLOW, `AF_` ön eki |
| `a9791e8014` | Süreler, eşikler, formül, log, parametre adları |
| `696289b889` | `AUTO_FOLLOW_TARGET` uyarısı |
| `f2c68b3433` | Girdi mesajı `DEBUG_FLOAT_ARRAY` |
| `676c4ced10` | `requirements.md` güncellemesi ve bu rapor (sürüm 1) |
| `71361a82ba` | Rapor başlığı biçim düzeltmesi |
| `164b6131f0` | `spec.md` (taslak; öneriler onay bekliyordu) |
| `6c24883e4f` | Write-spec turu kararları, sözlük, rapor sürüm 2 |
| `70323c83cf`, `e8131d3c23` | Spec son cevaplar ve son hali (rapor 2.1) |
| `f6394fc7b3`, `3594966ada` | Görev listesi (`tasks.md`) ve güncellemesi |
| `29116e848c` | Görev grubu 1: iskelet, mod kaydı, arming check, açılışta başlatma; rapor sürüm 3 |
| `836c4ef047` | Görev grubu 2: doğrulama, geometri, alpha-beta, guidance, setpoint, log mesajı; rapor sürüm 4 |
| `ee09be902e` | Lisans başlığına tez ekibi satırı, Grup 1 sorularının cevapları |
| `774583fdbc` | Görev grubu 3: kısa birim testi; rapor sürüm 5 |
| `909f13ec97` | Grup 2 soruları (filtre sıfırlama, EKF reset kaydırma kararları) |
| `1ac574d8cb` | Grup 2 düzeltme turu: filtre ve sıra no sıfırlama, EKF reset kaydırma; rapor sürüm 6 |
| *(bu sürüm)* | Görev grubu 4: test göndericisi, ön kontroller, S1–S5; rapor sürüm 7 |

---

## 4. Oluşan sistem

### 4.1 Büyük resim

```mermaid
flowchart TD
  pi[/"Raspberry Pi (Vision)<br/>LOS x,y,z + yaş + sıra no + hedef var/yok"/]
  mav["MAVLink DEBUG_FLOAT_ARRAY<br/>name = AF_LOS<br/>(SITL: UDP, gerçek: TELEM2 seri)"]
  rx["PX4 mavlink modülü<br/>uORB debug_array'e çevirir"]
  subgraph AF["auto_follow modülü (bizim kod, 50 Hz)"]
    v["1. Doğrula"]
    ned["2. LOS'u dünyaya çevir (NED)"]
    rng["3. Mesafe ve hedef konumu<br/>(düz zemin)"]
    ab["4. Alpha-beta filtresi<br/>hedef konumu + hızı"]
    g["5. Guidance: hız + yaw + irtifa<br/>sınırlar, ivme sınırı"]
    sm["Durum makinesi<br/>TAKİP / KAYIP-BEKLE / HOLD İSTE"]
  end
  att[/"vehicle_attitude<br/>(drone eğikliği, yönü)"/]
  lpos[/"vehicle_local_position<br/>(drone konumu, irtifa)"/]
  ts["trajectory_setpoint<br/>yatay hız + irtifa + yaw"]
  pos["mc_pos_control"] --> attc["mc_att_control"] --> rate["mc_rate_control"] --> alloc["control_allocator"] --> pwm["PWM → ESC → motorlar"]
  cmd["vehicle_command<br/>Hold isteği"]
  com["commander (mod yönetimi)"]
  st["auto_follow_status<br/>(log mesajı, adlı alanlar)"]
  log[("ULog<br/>gerçek: SD kart<br/>SITL: laptop")]

  pi --> mav --> rx --> v --> ned --> rng --> ab --> g --> ts --> pos
  att --> ned
  lpos --> rng
  lpos --> g
  sm --- v
  sm --- g
  sm --> cmd --> com
  AF --> st --> log
```

**Bizim yazdığımız tek parça `auto_follow` modülü.** Pi tarafı Vision ekibinin işi. `trajectory_setpoint`'ten motorlara kadar her şey PX4'ün kendi, denenmiş kodu. Bu zincirin varlığı kaynakta doğrulandı:
- `mc_pos_control` `trajectory_setpoint`'i okur (`src/modules/mc_pos_control/MulticopterPositionControl.hpp:107`) ve `vehicle_attitude_setpoint` yayınlar (`:99`);
- `mc_att_control` → `vehicle_rates_setpoint` (`src/modules/mc_att_control/mc_att_control.hpp:105,115`);
- `mc_rate_control` → tork ve itki (`src/modules/mc_rate_control/MulticopterRateControl.hpp:100,110,111`);
- `control_allocator` → `actuator_motors` (`src/modules/control_allocator/ControlAllocator.hpp:178,179,187`).

### 4.2 Modun PX4'e bağlanması: external mode
- PX4 v1.17.0, PX4'ün içinde ya da dışında çalışan bir programın kendini **yeni bir uçuş modu** olarak kaydettirmesine izin veriyor. Örneği PX4'ün kendi `mc_nn_control` modülü (`src/modules/mc_nn_control/mc_nn_control.cpp:135-142`).
- `auto_follow` açılışta PX4'e "ben **AUTO FOLLOW** adında bir modum" der. PX4 ona dış modlara ayrılmış **23–30** aralığından bir mod numarası verir (`msg/versioned/VehicleStatus.msg:59-66`). Bu mod QGC'nin mod listesinde görünür ve RC anahtarına atanabilir.
- Mod aktifken PX4 kendi uçuş görevlerini (FlightTask) **çalıştırmaz** (`src/modules/flight_mode_manager/FlightModeManager.cpp:139-144`). Bu yüzden konum kontrolcüsüne istek (`trajectory_setpoint`) vermek bizim modülün işi.
- PX4 her 300 ms'de modüle "çalışabilir misin?" diye sorar; modül 50 ms içinde cevap vermelidir (`HealthAndArmingChecks/checks/externalChecks.hpp:69-70`). Modül donarsa PX4 bunu fark eder ve kendi failsafe'ini çalıştırır.
- **Modül açılışta kendiliğinden başlar.** PX4 arm iken yeni mod kaydını kabul etmiyor (`ModeManagement.cpp:371-380`); uçuş sırasında mod listesi değişmesin diye. Bu yüzden modül arm'dan önce başlamalı. Çözüm: PX4'ün her multikopter açılışında çalıştırdığı `rc.mc_apps` dosyasına bir satır (SITL'de ve 6C'de aynı dosya; `mc_nn_control` da böyle başlıyor, `rc.mc_apps:40-43`). Bu kilitli bir dosya; Hüseyin'in onayı gerekiyor (7. yol). Satır `AF_ENABLE` parametresine bağlı: varsayılan 0, yani firmware ilk yüklendiğinde mod görünmez. Kullanıcı 1 yapıp QGC'den reboot atar; güç kesmek gerekmez. Sorun olursa 0 yapılıp reboot atılır ve mod listeden kalkar.
- **Modül "çalışabilirim" der** (`can_arm_and_run = true`), hedef yokken bile. "Çalışamam" derse PX4 drone'u Hold'a değil **eve dönüşe (RTL)** gönderir (`src/modules/commander/failsafe/failsafe.cpp:698-702`); hedef bir an görünmedi diye drone eve uçmamalı. Hedefin yokluğunu modül kendisi yönetir (4.4). Tek istisna adayı: drone yerde arm'lıyken ve mod henüz açık değilken "çalışamam" demek; böylece PX4 yerdeyken moda geçişi reddeder (4.7). Mod açık değilken RTL tehlikesi yoktur.
- Moda **QGC'den** ya da **RC anahtarından** geçilir. **Bu modda arm etmek yasak** (kalkış Position modunda yapılır; bu modda kalkış mantığı yok). Araç arm edilmemişken ise moda geçilebilir; PX4 disarm araçta her mod değişikliğine zaten izin veriyor (`src/modules/commander/UserModeIntention.cpp:54-55`). Bu, kullanıcının "masa testinde arm etmeden moda geçebilmeliyim" isteğini karşılıyor.
- **Neden bu yol seçildi?** Değerlendirilen diğer yollar:
  - **Yeni FlightTask:** kilitli birçok PX4 dosyasını değiştirmeyi gerektirir.
  - **Offboard:** kod Pi'ye taşınır; issue ve misyonla çelişir.
  - **PX4'ün Follow Me'sini uyarlamak:** GPS konumu bekliyor, bizim girdimiz bir yön.

  External mode, kilitli dosyalara en az dokunan, kodu PX4'ün içinde tutan ve PX4'ün kendi kontrol zincirini ve güvenlik mekanizmalarını kullanan yol.

### 4.3 Girdi: Pi'den ne geliyor?

| Kutu (`data[]`) | İçerik | Birim |
|---|---|---|
| 0, 1, 2 | Hedef yönü, LOS birim vektörü (body FRD: x ileri, y sağ, z aşağı) | — |
| 3 | Yaş: görüntünün çekildiği andan gönderime kadar geçen süre | ms |
| 4 | Sıra numarası | — |
| 5 | Hedef var (1) / yok (0) | — |

- Taşıyıcı mesaj: MAVLink `DEBUG_FLOAT_ARRAY`, `name` = `AF_LOS`. PX4 bunu uORB `debug_array`'e çevirir (`src/modules/mavlink/mavlink_receiver.cpp:2814-2832`).
- **Neden bu mesaj?** İlk seçim `DEBUG_VECT` idi. Kullanıcı "Vision bana body frame ve **timestamp** gönderecek" deyince kaynak yeniden incelendi: PX4 bu mesajların kendi zaman alanını atıp yerine varış anını yazıyor (`mavlink_receiver.cpp:2804`). `DEBUG_VECT`'in veri kısmı yalnızca 3 sayı olduğu için zaman bilgisi FC'ye ulaşamazdı. `DEBUG_FLOAT_ARRAY` 58 sayılık bir kutu; zaman, sıra no ve bayrak sığıyor.
- **Neden "yaş"?** Pi'nin saati ile Pixhawk'ın saati aynı değil. Pi "X ms önce çektim" derse Pixhawk kendi saatiyle hesaplar: çekim anı ≈ varış anı − X. Kablo gecikmesi birkaç ms, ihmal edilir.
- **Bu bir varsayım.** Kesin biçim ortak ICD'de (yol haritası 3–5) belirlenecek. Vision tarafıyla bu yerleşim konuşulacak.

### 4.4 Modun durumları

```mermaid
stateDiagram-v2
  [*] --> PASIF
  PASIF: PASİF (mod kapalı)<br/>veri işlenebilir, PX4'e istek gönderilmez
  TAKIP: TAKİP<br/>geçerli veri var, guidance çalışır
  KAYIP: KAYIP-BEKLE<br/>drone yerinde bekler (hover)
  HOLD: HOLD İSTENDİ<br/>PX4 Hold moduna geçer, AUTO FOLLOW biter

  PASIF --> TAKIP: pilot modu açtı ve geçerli veri var
  PASIF --> KAYIP: pilot modu açtı ama hedef yok (Hold girişten 1.5 s sonra)
  TAKIP --> KAYIP: 0.5 s geçerli veri yok (AF_DATA_TOUT) ya da Pi "hedef yok" dedi
  KAYIP --> TAKIP: 1.0 s dolmadan geçerli veri geldi
  KAYIP --> HOLD: 1.0 s doldu (AF_LOST_T)
  HOLD --> PASIF: PX4 Hold'da, takip kendiliğinden başlamaz
  TAKIP --> PASIF: pilot başka moda geçti
  KAYIP --> PASIF: pilot başka moda geçti
```

- **Zaman çizelgesi:**
  ```
  son geçerli mesaj ──0.5 s──▶ KAYIP-BEKLE (yerinde bekle) ──1.0 s──▶ Hold
  ```
  Toplamda son geçerli mesajdan 1.5 s sonra drone Hold'dadır. Pi "hedef yok" derse ilk 0.5 s beklenmez, KAYIP-BEKLE hemen başlar.
- **Takibe dönüş:** Hold'dan sonra drone, hedef görünse bile takibe **kendiliğinden dönmez**. Pilot QGC'den modu yeniden seçer (tek tık) ya da RC anahtarını başka konuma alıp geri getirir. Anahtarı yerinde bırakmak yetmez, çünkü PX4 yalnızca anahtar **konumu değişince** mod isteği gönderiyor (`src/modules/manual_control/ManualControl.cpp:176-177`).
- **Hold nasıl istenir:** Modül `VEHICLE_CMD_SET_NAV_STATE` komutunu gönderir (`src/modules/commander/Commander.cpp:936-944`).
- **Hedef görünmezken moda girilirse:** KAYIP-BEKLE ile başlanır, ama süre **giriş anından** sayılır: 0.5 + 1.0 = 1.5 s içinde geçerli hedef gelmezse Hold. (Sürüm 1'deki şema yanlışlıkla 1.0 s gösteriyordu.) Pratikte mod, hedef görünürken açılır.
- **Neden bu davranış (D)?** Değerlendirilen dört seçenek:
  - **A:** Moddan hiç çıkma, hedef gelince devam et.
  - **B:** Hemen Hold'a geç, pilot yeniden açar.
  - **C:** Hold'a geç, hedef gelince modül takibi kendiliğinden yeniden açar.
  - **D:** Kısa kayıpta A, uzun kayıpta B.

  Kullanıcı ilk uçuşlar için en güvenlisini sordu. Cevap B davranışıydı. Gerekçeler:
  - Model yanlış bir şeyi hedef sanarsa drone pilot onayı olmadan harekete geçmez.
  - Denenmemiş kodumuz yerine PX4'ün denenmiş Hold modu devreye girer.
  - Mod değişimi QGC'de herkesçe görülür.

  D seçildi, çünkü `AF_LOST_T` kısa tutulunca (1 s) pratikte B gibi davranır; güven arttıkça bu süre uzatılarak kısa kayıplarda takibin kesilmemesi sağlanır. C reddedildi: pilotun bilerek moddan çıktığını ayırt etmek zor ve yanlış algılamayla birleşince drone onaysız harekete geçebilir.
- **"Sorun olunca yayını kesmek" neden yapılmıyor?** Çatı standardı hata anında "setpoint üretmeyi bırak" diyor (`../agent-os/standards/global/error-handling.md:4`). Ama PX4 kaynağında, istek yayını kesilirse konum kontrolcüsü **son gelen isteği uygulamaya devam ediyor**; yedek güvenli istek yalnızca modun ilk açıldığı anda üretiliyor (`MulticopterPositionControl.cpp:438, 443-449, 636-686`). Yani yayını kesmek "son hıza devam et" demek. Bu yüzden modül, sorun anında susmak yerine aktif olarak "yerinde dur" isteği gönderir. Bu çelişki spec'e not olarak yazıldı.

### 4.5 Her döngüde ne oluyor? (50 Hz, adım adım)

> **Gerçekleşen hâli (Görev grubu 2, 2026-11-10).** Aşağıdaki adımlar kodda böyle yazıldı. Ayrıntılı anlatım, küçük kod kararları ve açık sorular: `implementation/grup-2-guidance-filtre-log.md`. Uçuş davranışı Grup 4'te SITL'de, sayısal doğruluk Grup 3'te birim testiyle sınanacak.

Modül saniyede 50 kez çalışır. Veri gelmese de çalışır; yalnızca veri gelince çalışsaydı veri kesildiğinde modül de durur ve kesintiyi fark edemezdi. Her çevrimde, mod kayıt ve arming check işlerinden (4.2) sonra:

**Adım 0: Hazırlık.** Bir önceki çevrimden beri geçen süre ölçülür (~20 ms). PX4'ün konum ve tutum bilgisi okunur. PX4'ün konum tahmini (EKF) kendini sıfırladıysa filtre unutulur; bir sonraki geçerli mesaj onu yeniden kurar. Aynı anda tutulan yatay konum ve tutulan irtifa, sıfırlamanın sıçraması (`delta_xy`, `delta_z`) kadar kaydırılır; böylece drone gerçekte yerinde kalır, PX4'ün kendi modları da böyle yapar (Karar 2026-11-10, 4). Filtrenin tahmini bir adım ilerletilir ("hedef bu hızla gidiyordu, şimdi şurada olmalı"). Bunlar mod kapalıyken de yapılır.

**Adım 1: Girdiyi doğrula.** Yeni bir mesaj geldiyse **bu sırayla** bakılır; ilk geçilemeyen kontrol mesajın sonucu olur ve mesaj atılır:
1. Adı `AF_LOS` mu? (`debug_array`'i başka yazılımlar da kullanabilir.) → değilse `CHECK_NAME`
2. Altı sayı geçerli mi (NaN ya da sonsuz değil mi)? → `CHECK_NONFINITE`
3. Vektörün uzunluğu 1'e yakın mı? (±`AF_NORM_TOL` = 0.1) → `CHECK_NORM`
4. Sıra numarası öncekinden büyük mü? (Tekrar eden ya da geri giden mesaj atılır.) → `CHECK_SEQ`. "Önceki", 1–4. kontrolleri geçen son mesajındır; `AF_DATA_TOUT` (0,5 s) boyunca böyle bir mesaj gelmezse unutulur, böylece yeniden başlayan Pi (sıra no yine 1'den) kabul edilir (Karar 2026-11-10, 5b-a).
5. Gerçek yaşı = (şimdi − varış) + Pi'nin yazdığı yaş, `AF_DATA_TOUT` (0.5 s)'ten küçük mü? → `CHECK_AGE`
6. "Hedef var" bayrağı 1 mi? → `CHECK_NO_TARGET` (bozuk veri değil; ayrı sayılır, takip sırasında gelirse hemen yerinde beklemeye geçilir)
7. Drone'un kendi konum bilgisi geçerli mi? → `CHECK_POSITION`
8. Yön yeterince aşağı bakıyor mu? (en az `AF_MIN_DEP` = 10°) → `CHECK_DEPRESSION` (Adım 2–3'te)
9. Yükseklik farkı pozitif ve mesafe 0 ile `AF_MAX_RNG` (40 m) arasında mı? → `CHECK_RANGE` (Adım 3'te)

Pi'nin ham değerleri (yön, yaş, sıra no, bayrak, varış anı) mesaj geçse de geçmese de log mesajına yazılır (adı `AF_LOS` olmayanlar hariç). Atılan mesaj nedeniyle sayılır, konsola **en fazla saniyede bir** uyarı düşer; guidance hesabına asla girmez. 9 kontrolü geçen mesajın varış anı "son geçerli mesaj" olarak saklanır.

**Adım 2: Yönü dünyaya çevir.** Pi'nin verdiği yön drone'a göredir (ileri/sağ/aşağı). Drone'un eğikliği ve burnunun yönü (`vehicle_attitude`) kullanılarak "kuzey/doğu/aşağı" (NED) yönüne çevrilir. Görüntünün çekildiği anki eğiklik değil, mesajın işlendiği çevrimdeki eğiklik kullanılır (varıştan en fazla ~20 ms sonra; V3); farkın önemli olup olmadığı loglardaki gecikmeye (`latency`) bakılarak sonra karar verilecek.

**Adım 3: Mesafe ve hedefin yeri.** Zemin düz kabul edilir:
```
yükseklik farkı = drone yüksekliği − AF_GND_OFS − AF_TGT_HGT
mesafe          = yükseklik farkı / tan(aşağı bakış açısı)
hedef konumu    = drone konumu + mesafe × (yönün yatay kısmı)
```
- Drone yüksekliği PX4'ün kendi irtifa tahmininden okunur (`-vehicle_local_position.z`); zemin = kalkış yeri.
- `AF_TGT_HGT` (1.0 m): Pi insanın ayağına değil gövdesine bakıyorsa o noktanın yerden yüksekliği.
- `AF_GND_OFS` (0 m): Hedefin yürüdüğü zemin kalkış yerinden yüksekse (ör. tepe) farkı.
- Drone yerdeyken yükseklik farkı negatiftir (≈ −1 m), mesajlar `CHECK_RANGE` ile atılır; SITL'de böyle görüldü.

**Adım 4: Alpha-beta filtresi.** Ölçülen hedef konumu her görüntüde biraz titrer. Filtre iki iş yapar:
- **Tahmin** (her çevrimde, Adım 0): "Hedef en son şu hızla gidiyordu, şimdi şurada olmalı."
- **Düzeltme** (yalnızca 9 kontrolü geçen mesajda): Tahmin ile ölçüm arasındaki fark `AF_ALPHA` oranında konuma, `AF_BETA` / (iki görüntünün çekim anı arasındaki süre) oranında hıza eklenir. İlk mesajda filtre ölçüme kurulur, hız 0.

Çıktı: yumuşatılmış hedef konumu ve **hedefin hızı**. PX4'ün Follow Me modundaki benzer filtre GPS mesajına bağlı olduğu için kullanılamadı (`flight_mode_manager/tasks/AutoFollowTarget/follow_target_estimator/TargetEstimator.hpp:112, 210`); küçük, kendi filtremiz yazıldı (`AlphaBetaFilter.hpp`).

**Adım 5: Durum.** Durum makinesi (4.4) bu çevrimin durumuna karar verir: mod kapalıysa PASIF; açıksa TAKIP, KAYIP_BEKLE ya da HOLD_ISTENDI. `AF_DATA_TOUT` (0,5 s) boyunca geçerli mesaj gelmediyse filtre de unutulur (mod kapalıyken de); eski kestirim hiç kullanılmaz, bir sonraki geçerli mesaj filtreyi yeniden kurar (konum = ölçüm, hız = 0) (Karar 2026-11-10, 3). Moda girişin ilk çevriminde o anki irtifa saklanır, hız sınırlayıcı drone'un o anki yatay hızından başlar, burun o anki yönünde kalır.

**Adım 6 (yalnızca mod açık ve TAKIP'te): İstenen mesafe ve hız kuralı.** Kullanıcının takip tasarımı: "Hedefi sabit yükseklikte ve sabit açıyla, kadrajın ortasında tutarak takip edeceğim."
```
istenen mesafe = yükseklik farkı / tan(AF_TRK_ANG)
yatay hız      = AF_K_FF × (filtrenin hedef hızı) + AF_K_DIST × (mesafe − istenen mesafe) × (hedefe doğru yatay yön)
```
- "Mesafe" filtrenin kestirdiği hedefe olan yatay mesafedir; yükseklik farkı son geçerli mesajınkidir.
- `AF_TRK_ANG`, hedefin kadraj ortasında durduğu aşağı bakış açısı, yani kameranın eğimi. Değeri m06'dan gelecek; SITL'de 30°.
- Sıra: önce kural, sonra hız en fazla `AF_VEL_MAX` (2 m/s) olacak şekilde kırpılır, sonra bir çevrimde en fazla `AF_ACC_MAX` (3 m/s²) × 20 ms = 0,06 m/s değişir. İvme sınırı hız vektörünün büyüklüğüne uygulanır; yani çapraz giderken de aynı sınır geçerlidir.
- `AF_K_FF` = 0 iken drone yalnızca mesafe farkına bakar. Yürüyen hedefin biraz gerisinde kalabilir. `AF_K_FF` açılınca hedefin hızı eklenir ve bu açık kapanır. İlk testlerde 0 tutulur (nedeni 4.9'da).
- **Neden hız tabanlı?** Konum tabanlı yasada ("hedefin 8 m gerisine git") her ölçümde hedef noktası zıplar ve drone sarsılır; PX4 bu mesaj için yumuşak istek bekliyor (`msg/versioned/TrajectorySetpoint.msg:3`). Pure pursuit ve PN önleme ("hedefe çarp") yasaları; mesafe korumazlar.

**Adım 7: Yaw ve irtifa.**
- **Yaw:** Burun kestirilen hedefe çevrilir, böylece hedef kadrajın ortasında kalır. Hedef 1 m'den (`AF_YAW_MIN_D`) yakına gelirse ("tam altında") yön belirsizleşir; o zaman yaw değiştirilmez (`yaw_frozen` = 1). Dönüş hızını PX4'ün kendi sınırı belirler (doğrulanacak).
- **İrtifa:** Moda girildiği andaki irtifa sabit tutulur.

**Adım 8: PX4'e ver** (yalnızca mod açıkken, her çevrimde; moda girişin ilk çevriminde de). `trajectory_setpoint` yayınlanır:
- **TAKIP:** `velocity[0..1]` = sınırlı yatay hız, `position[2]` = giriş irtifası, `yaw` = burun açısı.
- **KAYIP_BEKLE ve HOLD_ISTENDI:** `position[0..1]` = hedefin kaybolduğu anki drone konumu, `velocity[0..1]` = 0, `position[2]` = giriş irtifası, `yaw` = son yaw. Takip geri gelirse hız 0'dan yumuşakça artar.
- **Drone'un konum bilgisi geçersizse** (her durumda): `position[0..1]` boş, `velocity[0..1]` = 0; asıl tepkiyi PX4 verir (konum gereksinimi, A10).
- Diğer alanlar boş (NaN). PX4 bu karışımı geçerli sayıyor: her eksende konum ya da hız verilmiş olması, x ve y'nin aynı türde olması yeterli (`src/modules/mc_pos_control/PositionControl/PositionControl.cpp:224-250`).
- Mod kapalıyken hiç yayın yapılmaz. Hata anında da modül susmaz, aktif olarak "yerinde dur" ister; çünkü yayın kesilince PX4 son isteği uygulamaya devam eder (4.7).

**Adım 9: Log mesajını yayınla** (4.8): her çevrimde, mod kapalıyken de.

**Sayısal örnek (baştan sona):**
- Drone 10 m irtifada, burnu kuzeyde, düz duruyor. Pi'den yön (0.8, 0, 0.6) geliyor, yani hedef önde ve aşağıda.
- Adım 2: Drone düz ve kuzeye baktığı için NED yönü de (0.8 kuzey, 0 doğu, 0.6 aşağı).
- Adım 3: Aşağı bakış açısı = asin(0.6) ≈ 36.9°. Yükseklik farkı = 10 − 0 − 1.0 = 9.0 m. Mesafe = 9.0 / tan(36.9°) = 9.0 / 0.75 = **12.0 m**.
- Adım 5: İstenen mesafe = 9.0 / tan(30°) = **15.6 m**.
- Adım 6: Fark = 12.0 − 15.6 = −3.6 m → hız = 0.5 × (−3.6) = **−1.8 m/s**, yani hedeften uzaklaşarak 1.8 m/s geri (2 m/s sınırının altında).
- Adım 7: Yaw kuzeyde kalır.
- Sonuç: Drone hedef 30°'lik açıda, yani kadraj ortasında görünene kadar yavaşça geri çekilir.

### 4.6 Parametreler

Hepsi QGC'den değiştirilebilir, kod yeniden derlenmez. Ön ek `AF_` (PX4 v1.17.0'da çakışma yok); her biri en fazla 16 karakter. Değerler **başlangıç** değeri; gerçek değerleri testler gösterecek.

| Parametre | Anlamı | Başlangıç | Neden bu değer |
|---|---|---|---|
| `AF_ENABLE` | Modülü açılışta başlat (1) / başlatma (0) | 0 | İlk yüklemede mod görünmesin; kullanıcı bilerek açar. Değişince QGC'den reboot yeterli |
| `AF_TRK_ANG` | Takip açısı (kamera eğimi) | 30° (SITL) | m06'dan gelecek |
| `AF_K_DIST` | Mesafe kazancı | 0.5 1/s | 2 m hata → 1 m/s, yumuşak |
| `AF_K_FF` | Hedef hızı katsayısı | 0 | Açık çevrim testlerde kaçmayı önler (4.9) |
| `AF_VEL_MAX` | En fazla hız | 2 m/s | İlk testler için yavaş |
| `AF_ACC_MAX` | İvme sınırı | 3 m/s² | PX4'ün otomatik modlardaki değeri (`MPC_ACC_HOR`, `multicopter_autonomous_params.c:88`) |
| `AF_ALPHA`, `AF_BETA` | Filtre katsayıları | 0.5 / 0.17 | Başlangıç; SITL'de ayarlanacak (β ≈ α²/(2−α)) |
| `AF_DATA_TOUT` | Veri zaman aşımı | 0.5 s | Pi 10–30 Hz gönderir; 0.5 s, 5–15 kayıp mesaj demek |
| `AF_LOST_T` | Kayıptan Hold'a | 1.0 s | PX4 offboard kaybı da 1 s (`COM_OF_LOSS_T`); ilk uçuşlarda kısa |
| `AF_YAW_MIN_D` | Bunun altında yaw sabit | 1 m | Hedef altındayken yön belirsiz |
| `AF_TGT_HGT` | Hedef noktası yüksekliği | 1.0 m | İnsanın gövde ortası |
| `AF_GND_OFS` | Zemin farkı | 0 m | Düz arazi |
| `AF_NORM_TOL` | Vektör uzunluk toleransı | 0.1 | Bozuk veri yakalayıcı, ince ayar değil |
| `AF_MIN_DEP` | En küçük aşağı bakış açısı | 10° | Aşağıdaki tablo |
| `AF_MAX_RNG` | En büyük menzil | 40 m | Aşağıdaki tablo |

`AF_MIN_DEP` ve `AF_MAX_RNG` neden gerekli? Hedef ufka yakın göründükçe açıdaki küçük bir hata mesafede büyük hataya dönüşür (5 m irtifada):

| Aşağı bakış açısı | Mesafe | Açıda 1° hata olursa |
|---|---|---|
| 30° | 8.7 m | ~0.5 m hata |
| 10° | 28.4 m | ~3 m hata |
| 5° | 57.2 m | ~10 m hata |

Çevrim hızı parametre değil; kodda sabit 50 Hz.

### 4.7 Güvenlik davranışları

| Durum | Ne olur |
|---|---|
| Bozuk mesaj (NaN, yanlış ad, uzunluk ≠ 1, tekrar eden sıra no, yukarı bakan yön, çok uzak) | Atılır, sayılır, loga yazılır; drone etkilenmez |
| Görüntü çok eski (yaş > 0.5 s) | Atılır |
| 0.5 s geçerli veri yok ya da Pi "hedef yok" dedi | KAYIP-BEKLE: drone yerinde bekler (mevcut konum, hız 0, son yaw) |
| 1.0 s daha veri yok | Hold istenir; takip kendiliğinden başlamaz |
| Hedef görünmezken moda girildi | Aynı kural, 1.5 s içinde hedef yoksa Hold |
| Drone'un kendi konumu geçersiz (ör. GPS yok) | Hedef hesaplanmaz, takip yapılmaz; yatay hız 0 istenir |
| Hız isteği | En fazla 2 m/s, en fazla 3 m/s² ivmeyle değişir |
| Modül donarsa | PX4 cevap alamadığını fark eder ve kendi failsafe'ini çalıştırır |
| Pilot | Her an başka moda geçebilir. İlk uçuşta RC'de Position moduna ayrılmış bir anahtar konumu olmalı |
| Bu modda arm | Yasak. Önce Position'da arm edilip kalkılır, AUTO FOLLOW havada açılır |
| Yerde arm'lıyken moda geçiş | Engellenir: modül yerdeyken PX4'e "şu an çalışamam" der, PX4 geçişi reddeder (QGC'de mesaj + uyarı sesi). Disarm iken geçiş serbest |
| Pilot çubuğu oynatırsa | Drone Position moduna geçer (güvenlik amaçlı; SITL'de doğrulanacak) |
| Hold isteği reddedilirse | Yerinde beklemeye devam eder; 1 s arayla en fazla 3 kez yeniden ister |

- **(doğrulanacak):** Çubuk oynayınca Position'a geçişin gerçekten çalıştığı (SITL ön kontrolü).
- **İlk uçuş önerisi:** `AF_LOST_T` kısa (1 s), `AF_VEL_MAX` düşük (2 m/s), `AF_K_FF` = 0.

### 4.8 Loglama

**Kullanıcının gereksinimi:** "Her durumu log kaydına almamız gerek; gerekirse ek kod yazalım. Alpha-beta filtresinin girdisi ve çıktısı ve analizi çok önemli. Yazılan durumları logda kendi adlarıyla göreceğim; ekstra bir şey açmama gerek kalmasın."

Bu isteğe kullanıcının bir örneği eşlik etti: Özelleştirilmiş bir Betaflight'taki "track hold" modu için `trk` önekli bir log alan sözlüğü yapılmıştı (ör. `trkAzErr` = azimut hatası). Bizde de her özelleştirmenin loga girmesi ve bir sözlüğü olması kararlaştırıldı.

- **Log mesajı:** Kendi uORB mesajımız `msg/AutoFollowStatus.msg` → topic `auto_follow_status`. Alanlar logda adlarıyla görünür (PlotJuggler ve Flight Review'da da).
- **Her logda her zaman kaydedilir:** PX4'ün varsayılan log listesine eklenir; kullanıcı ayrıca bir ayar açmaz.
- **İçerik** (alan adları kararlaştı, önek yok; tam liste ve anlamları `log-sozlugu.md`):
  - Pi'den gelen ham veri (LOS x/y/z, yaş, sıra no, hedef var),
  - doğrulama sonucu ve atılan mesaj sayaçları,
  - filtrenin girdisi (ölçülen hedef konumu) ve çıktısı (kestirilen konum ve hız),
  - mesafe, istenen mesafe, hız isteği,
  - durum (TAKİP / KAYIP-BEKLE / HOLD İSTENDİ),
  - toplam gecikme,
  - AUTO FOLLOW'un mod numarası.
- **Gerçekleşen hâli (Görev grubu 2, 2026-11-10):** `msg/AutoFollowStatus.msg` yazıldı (39 alan, `STATE_*` 0–3, `CHECK_*` 0–9; adlar spec'teki tablodan, önek yok). `msg/CMakeLists.txt`'e ve `logged_topics.cpp`'ye (`add_topic("auto_follow_status")`, aralıksız) birer satır eklendi. Kısa SITL denemesinde (arm yok, mod kapalı) mesaj 50 Hz yayınlandı ve ULog'da 39 alanın hepsi kendi adıyla göründü (pyulog 1.2.4; 96 s'de 4 809 örnek, kayıp yok). "Henüz hesaplanmadı" değerleri NaN yazılır. Her alanın hangi durumda ne değer aldığı `log-sozlugu.md` Bölüm 4'te.
- **`DEBUG_FLOAT_ARRAY` yalnızca taşıyıcı.** Logda bakılan, `auto_follow_status`'un adlı alanları. Ham `debug_array` logda yalnızca debug ayarı açıksa ve `data[0]`… diye görünür; ihtiyaç yok.
- **Zaten kendiliğinden kaydedilenler:** `trajectory_setpoint`, `vehicle_status` (mod değişimleri), `vehicle_command` (Hold isteği), `vehicle_local_position`, `vehicle_attitude`, `vehicle_control_mode`, `actuator_motors` (`src/modules/logger/logged_topics.cpp:131-150, 214`).
- **Sözlük:** `log-sozlugu.md`. Kullanıcının isteğiyle yalnız log alanları değil, **bizim verdiğimiz bütün adlar** orada: mod, modül ve komutları, parametreler, girdi mesajı, log alanları, durumlar, doğrulama sonuçları, dosyalar. Her ad için anlam, birim, frame ve hangi durumda ne değer aldığı yazılır. Kod değişince aynı commit'te güncellenir.
- **Logların yeri:**
  - **Gerçek uçuş:** 6C'deki SD kart, `/fs/microsd/log/<tarih>/<saat>.ulg` (`logger.cpp:1296`).
  - **SITL:** laptop, `build/px4_sitl_default/rootfs/log/<tarih>/<saat>.ulg`. Bu klasör `make clean` ile ya da 7 klasör sınırı dolunca silinir (`SDLOG_DIRS_MAX` = 7, `ROMFS/px4fmu_common/init.d-posix/rcS:183`). Bu yüzden her testten sonra **`~/Desktop/AUTO-FOLLOW LOG/`** klasörüne kopyalanır.
  - Log dosyaları repoya girmez (kural 9); spec'e yalnızca adları yazılır.
- **Masa testinde log almak** (kod gerekmez; kullanıcı kendisi yapar):
  1. SD kart takılı olsun.
  2. QGC → Vehicle Setup → Parameters → `SDLOG_MODE`'u kullanıcı kendisi seçer. Bilgi: 1 = açılıştan disarm'a kadar (masada arm/disarm yapılırsa kayıt orada durur), 2 = açılıştan kapanışa kadar.
  3. Kartı yeniden başlat; bu parametre yeniden başlatmadan devreye girmez (`logger/module.yaml:31`).
  4. Testten sonra logu Analyze Tools → Log Download ile indir ve `AUTO-FOLLOW LOG`'a koy.
  5. Uçuştan önce `SDLOG_MODE` = 0'a dön ve kartı yeniden başlat. Varsayılan 0 = "yalnızca arm iken"; kullanıcı bunu varsayılan bırakmak istedi.
- **⚠️ Uyarı (log sözlüğüne de yazılacak): PX4'ün kendi `AUTO_FOLLOW_TARGET` modu bizim AUTO FOLLOW ile ilgili değildir.**
  - PX4'ün GPS tabanlı Follow Me modu, `nav_state` = **19** (`msg/versioned/VehicleStatus.msg:55`; kod `FlightTaskAutoFollowTarget`, parametreler `FLW_TGT_*`). Bazı log araçları 19'u "Auto Follow" diye gösterebilir.
  - Bizim AUTO FOLLOW **23–30** aralığından bir numara alır; hangisi olduğu `auto_follow_status`'ta yazar.
  - Çalışma anında çakışma yok: PX4 modları numarayla ayırıyor, kod, parametre ve topic adları da ayrı. Kodda hiçbir şeye `AutoFollowTarget` / `follow_target` adı verilmeyecek. RC anahtarı (`COM_FLTMODEx`) bizim modun dış mod sırasıyla ayarlanır: değer 100 = "External Mode 1" = `nav_state` 23 (Grup 4'te SITL'de görüldü; değer 23 değildir). QGC listesinde "Follow Me" ile "AUTO FOLLOW"u karıştırmayın.

### 4.9 Test planı

İki aşama, en basitten başlayarak.

**1) Birim testi (kısa tutulacak; süre kısıtlı)**
- Guidance hesabı uçuştan bağımsız bir sınıfta (`AutoFollowGuidance`) olduğu için bilgisayarda drone'suz ve Gazebo'suz, saniyeler içinde test edilir (GoogleTest, `AutoFollowGuidanceTest.cpp`; `../agent-os/standards/testing/test-writing.md:6-10`).
- Yalnızca temel hesaplar sınanır:
  - mesafe ve yön (ör. "10 m, şu yön → 12 m"),
  - hız kuralı ve sınırları,
  - bozuk veri,
  - zaman aşımı.
- Testler firmware'e girmez, flash'ı etkilemez.

**Birim testi sonuçları (Görev grubu 3, 2026-11-10):** `make tests TESTFILTER=AutoFollowGuidance` → **7 testin 7'si geçti**; guidance kodu değişmedi, hata bulunmadı. Ayrıntı: `implementation/grup-3-birim-testi.md`.

| # | Test | Beklenen (spec) | Sonuç |
|---|---|---|---|
| 1 | Geometri: 10 m, düz, burun kuzey, LOS (0,8; 0; 0,6) | aşağı bakış 36,9°, h = 9,0 m, **d = 12,0 m**; burun doğudayken hedef doğuda | Geçti |
| 2 | Kural: aynı örnek, `AF_TRK_ANG` 30° | istenen 15,6 m, **−1,8 m/s** (geri), kırpma yok | Geçti |
| 3 | Kırpma: S1a, LOS (0,951; 0; 0,309) | d ≈ 27,7 m, kural ≈ +6,0 m/s, çıkış **2 m/s** | Geçti |
| 4 | İvme sınırı: bir çevrim (20 ms) | değişim ≤ `AF_ACC_MAX · Δt` = 0,06 m/s, çaprazda da | Geçti |
| 5 | Bozuk veri | NaN/Inf → `CHECK_NONFINITE`, norm 0,71 → `CHECK_NORM`, tekrar/eski sıra no → `CHECK_SEQ`, yanlış ad → `CHECK_NAME` | Geçti |
| 6 | Veri kesilmesi | 0,5 s sonra KAYIP_BEKLE, +1,0 s sonra HOLD_ISTENDI | Geçti |
| 7 | Hedef yok (bayrak 0) | hemen KAYIP_BEKLE, 1,0 s sonra HOLD_ISTENDI | Geçti |
| 8 | Yeniden başlayan Pi (düzeltme turu, Karar 5b-a): önceki sıra no 1000, sonra sıra no 1 | 0,48 s'de hâlâ `CHECK_SEQ`; **0,5 s'de** önceki numara unutulur, sıra no 1 `CHECK_OK` | Geçti |
| 9 | Uzun kesintiden sonra filtre (düzeltme turu, Karar 3): hareketli hedef kestirimi, sonra veri yok | 0,48 s'de kestirim hâlâ kullanılır; **0,5 s'de** eskimiş sayılır; sıfırlamadan sonraki ilk ölçümde konum = ölçüm, hız = 0 | Geçti |

Düzeltme turundan sonra (2026-11-10): **9 testin 9'u geçti.**

- Birim testinde olmayanlar (yaş, konum, aşağı bakış ve menzil kontrolleri, filtre, yaw donması, hedefsiz giriş) SITL'de (S4, S5) ölçülecek.

**2) SITL testleri (Gazebo, `gz_x500`)**
- Drone **Position** modunda kalkar, havada AUTO FOLLOW'a alınır ve geçici test script'i (`tez/sitl/af_los_gonder.py`, pymavlink 2.4.50) Pi gibi `AF_LOS` mesajı gönderir.

Örnek değerler: irtifa 10 m, takip açısı 30° → istenen mesafe 15.6 m.

| # | Script ne gönderir | Drone'dan beklenen | Çevrim |
|---|---|---|---|
| S1a | "Hedef uzakta" (aşağı bakış 18°, takip açısından sığ) | İleri gider; kural ~6 m/s ister, 2 m/s'de kırpılır | Açık |
| S1b | "Hedef yakında" (aşağı bakış 37°, takip açısından dik) | ~1.8 m/s geri gider | Açık |
| S2 | "Hedef sağında" | Burnunu sağa çevirir; açık çevrimde dönmeye devam eder (beklenen) | Açık |
| S3 | "Hedef neredeyse tam altta" (80°) | Geri gider; kural ~7 m/s ister, 2 m/s'de kırpılır | Açık |
| S4 | Göndermeyi keser / "hedef yok" der / hedef yokken mod açılır | 0.5 s sonra yerinde bekler, 1.0 s sonra Hold (hedefsiz girişte girişten 1.5 s) | Açık |
| S5 | Bozuk veri (NaN, yanlış ad, yukarı bakan yön, tekrar eden sıra no, eski, çok uzak) | Atar, sayaç artar, etkilenmez | Açık |
| S6 | Yerde duran hayali insan | Takip açısının verdiği mesafeye gelip durur | Kapalı |
| S7 | Yürüyen hayali insan, `AF_K_FF` > 0 | Geride kalmadan takip eder | Kapalı |

**SITL sonuçları (Görev grubu 4, 2026-11-10/11; açık çevrim, `AF_K_FF` = 0, `AF_LOST_T` = 1,0 s):** ayrıntı ve bütün sayılar `implementation/grup-4-sitl-acik-cevrim.md`. Loglar `~/Desktop/AUTO-FOLLOW LOG/`'da, özgün adlarıyla (PX4 logu UTC saatiyle adlandırır). İrtifa elle kalkış yüzünden 9,9 m oldu (h ≈ 8,92 m, istenen mesafe 15,46 m); beklenenler buna göre.

| # | Script ne gönderdi | Drone ne yaptı / ölçülen | Beklenen | Sonuç | ULog |
|---|---|---|---|---|---|
| Ön | Disarm/arm/geçiş denemeleri, giriş/çıkış, RC anahtarı ve çubuğu, MAVLink 2 | Mod açılışta kendiliğinden 23 numarayla kaydoldu (10 açılışta, yeniden açılışta da); disarm iken geçiş kabul; bu modda arm reddedildi; yerde arm'lıyken geçiş reddedildi (`Switching to External 1 is currently not available`); girişin ilk çevriminde setpoint başladı, çıkışta durdu; RC anahtarı (`COM_FLTMODE6` = 100) ile giriş/çıkış; çubuk oynayınca Position; `debug_array` verisi sıfır değil | Spec ön kontrolleri | Geçti (QGC ekranı kullanıcıda; Hold sonrası yeniden giriş Grup 5) | `20_48_09.ulg`, `20_52_31.ulg`, `20_55_24.ulg` |
| S1a | LOS (0,951; 0; 0,309) | Girişte d = 27,81 m, kural +6,17 m/s → **2,00 m/s** ileri; ivme ≤ 3,000 m/s²; drone 2,04 m/s ileri | ileri, ~6 → 2 m/s, ≤ 3 m/s² | Geçti | `20_56_47.ulg` |
| S1b | LOS (0,8; 0; 0,6) | Girişte d = 11,93 m, kural **−1,76 m/s** (geri), kırpma yok; uçarken eğimle salınım, ortalama 1,53 m/s geri | geri ~1,8 m/s | Geçti (salınım gözlemi) | `20_58_51.ulg` |
| S2 | LOS (0; 0,8; 0,6) | Burun **sağa** döndü ve dönmeyi sürdürdü: ortalama 192°/s, en çok 206°/s (`MC_YAWRATE_MAX` 200°/s) | sağa dönüş | Geçti | `21_00_19.ulg` |
| S3 | LOS (0,174; 0; 0,985) | Girişte d = 1,61 m, kural −6,93 m/s → **2,00 m/s** geri; yaw donmadı; ~2,5 s sonra kendi etrafında dönmeye başladı | geri, 2 m/s kırpma, yaw donmaz | Geçti (dönme gözlemi) | `21_01_32.ulg` |
| S4 | Kesinti 1,0 s ve 3,0 s; "hedef yok" 0,5 s ve 3,0 s; hedefsiz giriş | KAYIP_BEKLE kesintiden **0,51 s** sonra, HOLD_ISTENDI **1,51 s** sonra; kısa kesintide takip kendiliğinden sürdü; "hedef yok"ta **bir çevrimde** bekleme, **1,00 s** sonra HOLD_ISTENDI; hedefsiz girişte **1,50 s**; HOLD_ISTENDI'de veri dönünce takibe dönülmedi; beklemede hız isteği 0, drone tutulan noktada (en çok 0,7 m fren payı) | 0,5 / +1,0 s; hemen / 1,0 s; 1,5 s | Geçti (Hold isteği Grup 5) | `21_02_55.ulg` |
| S5 | Araya karışık ve sürekli: yanlış ad, NaN/Inf, norm, sıra no, eski, ufuk, uzak | Araya karışıkta her tür yalnızca kendi sayacını artırdı, durum hep TAKIP, hız isteği salınım içinde (`uzak` hariç); sürekli bozukta 0,5 s / 1,5 s'de bekleme / HOLD_ISTENDI. İstisnalar: **`sira`** (aynı sıra no sürekli gelince her 0,5 s'de bir mesaj kabul ediliyor, Hold'a gidilmiyor) ve **`ufuk`/`uzak`** (gövdeye sabit yön drone eğilince eşiği geçiyor; kontrol 400 mesajın 400'ünde eşikte doğru karar verdi) | atılır, sayaç artar, drone etkilenmez | Geçti, 3 türde açık çevrim / spec çelişkisi notu | `21_05_34.ulg`, `21_10_47.ulg` |

- **Kapalı çevrim kısa kontrolü** (`20_48_09.ulg`): 20 m öndeki hayali hedefe 4,5 s'de 15,5 m'ye geldi, aşım 0,04 m, son 10 s'de hata −0,006 ± 0,02 m. Ayrıntılı ölçüm S6'da.
- **Açık çevrimin doğası:** LOS gövdeye sabit; drone eğildikçe aynı gövde yönü dünyada başka açıya denk gelir. Spec'in sayıları drone düzken (moda girişte) birebir görüldü; uçarken eğim yüzünden kaydı (S1b salınımı, S3 dönmesi, S5 `ufuk`/`uzak`). Kod hatası değil; gerçek uçuşta kamera bu eğimi görüntüde görür.

- **Neden S1 ikiye ayrıldı?** Sürüm 1'de "hedef önünde → ileri gider" yazıyordu; bu yanlıştı. Drone hedefe, aşağı bakış açısı takip açısına (30°) eşit olacak mesafede durmak ister. Hedef 30°'den sığ görünüyorsa uzaktadır → ileri; dik görünüyorsa yakındır → geri.
- **Neden S2'de burun dönmeye devam eder?** Script hep "hedef sağda" der. Drone döndükçe hedef yine sağda görünür. Bu kodun hatası değil, testin doğası. S2'de yalnızca dönüş yönü kontrol edilir; yaw'ın hedefte doğru durması S6'da ölçülür.
- **Ön kontroller** (her test oturumunun başında): modül açılışta başladı mı, QGC'de `AUTO FOLLOW` görünüyor mu, disarm iken moda geçiliyor mu, bu modda arm reddediliyor mu, yerde arm'lıyken moda geçiş reddediliyor mu, QGC ve RC anahtarıyla giriş/çıkış, Hold'dan sonra anahtar aç-kapa ile yeniden giriş.
- **Hangi test SITL'siz?** Yalnızca birim testi. Açık çevrim testleri de Gazebo'da yapılır ama basittir: script sabit bir yön gönderir.
- RC kaybı ve modül donması testleri bu spec'te yok; m16 adayı.
- **Açık çevrim:** Script sabit bir yön gönderir. Hedef drone'la birlikte kayıyormuş gibi davranır.
- **Kapalı çevrim:** Script yerde hayali bir insan tutar, drone'un konumunu okur ve o insana göre gerçek yönü hesaplar. Mesafe tutma ancak böyle gerçekten test edilir.
- **Neden S1–S5'te `AF_K_FF` = 0?** Sabit yön gönderilince filtre "hedef de benim hızımla gidiyor" sanır; hedef hızı eklenirse drone hızlandıkça hedef de hızlanmış görünür ve drone `AF_VEL_MAX`'a kadar kaçar.
- **Değerlendirme:** Göz kararı test sayılmaz. Her testin logu `tez/analiz/af_log_analiz.py` (pyulog 1.2.4) ile okunur. Spec'e her senaryo için ne verildi, ne beklendi, ne ölçüldü ve log adı tablo olarak yazılır. Kesin başarı eşikleri yol haritası madde 1'de belirlenecek; şimdilik öneri.
- **Sonrası:** Ahmet'in gerçekçi simülasyonu (m06) hazır olunca testler oraya taşınır. Kullanıcı: "O bitene kadar her şey bizde."

### 4.10 Dosyalar ve kilitli yollar (planlanan)

| Yol | Ne | Kilit durumu |
|---|---|---|
| `src/modules/auto_follow/` (`AutoFollow.cpp/.hpp`, `AutoFollowGuidance.cpp/.hpp`, `AlphaBetaFilter.hpp`, `AutoFollowGuidanceTest.cpp`, `CMakeLists.txt`, `Kconfig`, `module.yaml`) | Modül, guidance, filtre, birim testi, parametre tanımları | **Kilitli**, onay gerekli |
| `boards/px4/sitl/default.px4board`, `boards/px4/fmu-v6c/default.px4board` | `CONFIG_MODULES_AUTO_FOLLOW=y` satırı | **Kilitli**, onay gerekli |
| `msg/AutoFollowStatus.msg` | Log mesajı | **Kilitli**, onay gerekli |
| `msg/CMakeLists.txt` | Mesaj listesine bir satır (`:39`) | **Kilitli**, onay gerekli |
| `src/modules/logger/logged_topics.cpp` | `auto_follow_status`'u her zaman kaydeden bir satır | **Kilitli**, onay gerekli |
| `ROMFS/px4fmu_common/init.d/rc.mc_apps` | Açılışta `auto_follow start` satırı | **Kilitli**, onay gerekli |
| `tez/sitl/af_los_gonder.py` | Geçici test göndericisi | İzinli (`tez/*`) |
| `tez/analiz/af_log_analiz.py` | Log değerlendirme script'i | İzinli |
| `agent-os/specs/2026-11-08-m15-takip-kodu/` (`log-sozlugu.md`, `rapor.md`, …) | Dokümanlar | İzinli |

- Kilitli **yedi** yolun `tez/pin/allowed-paths.txt`'e eklenmesi için **repo sorumlusu Hüseyin'e tek bir talep** iletilecek. `rc.mc_apps` reddedilirse geri dönüş: SITL'de modül elle başlatılır, 6C'de SD karttaki `etc/extras.txt` kullanılır. Ekleme ayrı ve açık bir PR ile yapılır; Claude listeyi kendisi genişletmez. Kullanıcı: "Kilitli dosyalara böyle durumlarda dokunuruz, sıkıntı yok."
- **Log mesajı için neden kilitli dosya:** PX4'ün SD karttaki `logger_topics.txt` dosyasıyla kilitli dosyaya dokunmadan ek topic loglanabileceği önce düşünüldü. Ama bu dosya varsa PX4 **yalnızca içindekileri** logluyor ve varsayılan listeyi tamamen kapatıyor (`logged_topics.cpp:531-540`). Doğru yol, `logged_topics.cpp`'ye bir satır eklemek.
- **Geri dönüş:** Hüseyin log mesajı için gereken yolları reddederse PX4'ün hazır `debug_array` mesajı kullanılır; alanlar logda `data[0]`… diye görünür, adlar sözlükten okunur.
- **Flash:** 6C'nin flash'ı ~%98 dolu. Derleme çıktısındaki kullanım spec'e yazılır. Taşarsa Hüseyin'e haber verilir; modül kapatarak yer açılmaz (o iş m14). Not: `CONSTRAINED_FLASH` ayarı açılırsa `DEBUG_FLOAT_ARRAY` işleyicisi derlemeden çıkar (`mavlink_receiver.cpp:284-305`), yani m14'te dikkat edilmeli.
- **Flash ölçümü (Grup 1 sonu):** modül yokken 1 926 408 B (%97,98), iskelet + 16 parametreyle **1 931 164 B / 1920 KB (%98,22)**; artış **+4 756 B**, boş kalan ~34 KB. Grup 2 (guidance, filtre, log mesajı) bunun üstüne eklenecek.
- **Flash ölçümü (Grup 2 sonu):** **1 936 100 B / 1920 KB (%98,48)**; Grup 1'e göre artış **+4 936 B**, boş kalan ~29 KB (29 980 B).
- **Grup 1'de yazılanlar:** `src/modules/auto_follow/` içinde `AutoFollow.cpp/.hpp`, `CMakeLists.txt`, `Kconfig`, `module.yaml`; iki kart dosyasına birer satır; `rc.mc_apps`'in sonuna 4 satırlık başlatma bloğu. **Grup 2'de yazılanlar:** `AutoFollowGuidance.cpp/.hpp` (ayrı kütüphane), `AlphaBetaFilter.hpp`, `AutoFollow.cpp/.hpp`'ye girdi, setpoint ve log; `msg/AutoFollowStatus.msg`; `msg/CMakeLists.txt` ve `logged_topics.cpp`'ye birer satır. **Grup 3'te yazılanlar:** `AutoFollowGuidanceTest.cpp` ve `CMakeLists.txt`'e `px4_add_unit_gtest` satırı (firmware'e girmez, flash değişmedi).

---

## 5. Bütün kararlar

"Tür" sütunu: **Karar** = kullanıcı açıkça seçti; **Öneri kabul** = kullanıcı Claude'un önerisine güvenerek kabul etti (sorun çıkarsa ilk bakılacak yerler).

| # | Konu | Seçenekler | Seçilen | Neden | Tür |
|---|---|---|---|---|---|
| 1 | Kapsam (m15 ile m16) | a) issue #6'yı izle · b) iskelet m15, gerisi m16 · c) önce Hüseyin hizalasın | a | Görev ve teslim issue'ya bağlı; fark not edilir | Karar |
| 2 | PX4 entegrasyonu | a) external mode · b) FlightTask · c) offboard · d) Follow Me uyarla | a | Kilitli dosyalara en az dokunan; kod PX4 içinde; PX4 zinciri ve failsafe'i kullanılır | Karar |
| 3 | Kodun yeri | a) `src/modules` + px4board · b) `tez/` dış modül | a | Standardın öngördüğü düzen | Karar |
| 3.1 | 6C firmware'i | i) yalnız SITL · ii) 6C de | ii | "Asıl amaç 6C'ye derlemek; önce SITL'de test" | Karar |
| 4 | Modül iç yapısı | — | `nav_and_controllers` kuyruğu, sabit 50 Hz, ayrı guidance sınıfı | Veri kesilince de çalışmalı; test edilebilirlik | Öneri kabul |
| 5 | Girdi mesajı | `DEBUG_VECT` · `DEBUG_FLOAT_ARRAY` · `LANDING_TARGET` · `NAMED_VALUE_FLOAT` | Önce `DEBUG_VECT`, sonra **`DEBUG_FLOAT_ARRAY`** | Zaman bilgisi `DEBUG_VECT` ile taşınamıyor | Karar (varsayım) |
| 5b | Zaman bilgisinin kullanımı | — | Yaş (ms) + sıra no + hedef bayrağı; eskilik kontrolü; gecikme loga; telafi şimdilik yok | Saatler farklı; güvenlik; ihtiyaç veriyle belirlenecek | Karar (öneri) |
| 6 | Guidance yasası | a) hız tabanlı · b) konum tabanlı · c) PN / pure pursuit | a | Yumuşak; tek kazanç; mesafe korur | Karar |
| 6.1 | Filtre | yok · alçak geçiren · alpha-beta | Alpha-beta, kendi sınıfımız | Kullanıcının isteği; hem konum hem hız verir | Karar |
| 6.1b | Hedef hızı yasaya | — | Eklenir, katsayıyla (0 = kapalı) | Yürüyen hedefte geride kalmayı önler | Karar |
| 6.2 | İvme sınırı | var · yok | Var (3 m/s²) | İlk uçuşlarda sert eğilmeyi önler | Öneri kabul |
| 6.3 | Hedef altındayken yaw | — | 1 m altında yaw sabit | Kullanıcının sabit açılı tasarımında nadir; geçici durumlara koruma | Karar |
| 6.4 | İstenen mesafe | açı ile · mesafe ile | Açı ile (`AF_TRK_ANG`) | Kullanıcının "sabit yükseklik, sabit açı, kadraj ortası" tasarımına birebir uyuyor | Öneri kabul |
| 7 | PX4'e verilen | `trajectory_setpoint` · `goto_setpoint` | `trajectory_setpoint`, mutlak yaw | Hız tabanlı yasaya uyan tek seçenek | Karar |
| 8 | Doğrulama | — | 4.5 Adım 1'deki liste | Standart (`validation.md`) | Öneri kabul |
| D | Hedef kaybı | A · B · C · D | D, Hold m15'te, ilk uçuşlarda kısa süre | Güvenlik + kullanılabilirlik | Karar ("önemli") |
| S | Süreler | — | 0.5 s / 1.0 s | Pi hızı; PX4 offboard ile tutarlı | Öneri kabul |
| E | Eşikler | — | Hepsi parametre; 0.1 / 10° / 40 m | Kullanıcı: "tahmin olacak, parametre olsun" | Karar (değerler öneri) |
| 9 | Disarm durumda moda geçiş | — | PX4 zaten izin veriyor | Masa testi gereksinimi | Bulgu |
| 5a | Hedef yokken moda giriş | a) D aynen · b) girişte daha uzun bekle | a | En basit ve en güvenli | Karar |
| 10 | Test | — | Kısa birim testi + S1–S7 | "En basitten başla, süre kısıtlı" | Karar |
| L2 | Log mesajı | a) `debug_array` · b) kendi mesajımız · c) `debug_key_value` | b (geri dönüş a) | "Kendi adlarıyla göreceğim" | Karar |
| L1/4 | Log kaydı | her zaman · debug ayarıyla | Her zaman, ham girdi mesaja kopyalanır | "Ekstra bir şey açmama gerek kalmasın" | Karar |
| L3 | Masa testi logu | — | `SDLOG_MODE` varsayılan; kullanıcı elle değiştirir | "Parametreden ayarlarım" | Karar |
| L4 | Logların yeri | — | `~/Desktop/AUTO-FOLLOW LOG/` | SITL logları silinebiliyor | Karar |
| 11 | Kalıcı gönderici | — | Vision ve m06 ile konuşulacak; geçici olanı biz yazıyoruz | "Karar bende değil" | Açık |
| 12 | Adlar | — | `AUTO FOLLOW`, `AF_*`, `auto_follow`, `auto_follow_status`, `AF_LOS` ve dosya adları | Kullanıcı verdi | Karar |
| 12b | `AUTO_FOLLOW_TARGET` | adı değiştir · uyarı yaz | Uyarı (sözlük ve rapor) + log'a mod no | Çalışma anında çakışma yok | Karar |
| 13 | Yükseklik | i · ii · iii | iii (hedef yüksekliği + zemin ofseti) | Mesafe hatasını düzeltir | Karar |
| 14 | Kapsam ve toparlama | — | 14.1–14.5 öneri gibi; 14.3 yerine bu rapor | Masaüstü dosyası kişisel çalışma | Öneri kabul + Karar |
| A1 | Senaryo listesi | spec-shaper'ın S6/S7'si (RC kaybı, modül) · konuşulan tablo | Konuşulan tablo; RC kaybı ve modül donması m16 adayı | "En konuştuğumuz hale getir" | Karar |
| A2 | S1 beklentisi | — | S1a (uzak → ileri) / S1b (yakın → geri) | İleri/geri, açıya bağlı | Karar |
| A3 | Hedefsiz girişte süre | — | Girişten 1.5 s sonra Hold | Karar 5a ile tutarlı | Karar |
| A5 | Masa testinde `SDLOG_MODE` | 1 · 2 | Kullanıcı kendisi seçer | "Kendim ayarlayacağım" | Karar |
| B2 | Modülün açılışta başlaması | a) elle / SD kart · b) `rc.mc_apps` satırı | b (7. kilitli yol) | Unutulma riski yok, kendiliğinden | Karar |
| B4 | Yerde arm'lıyken moda geçiş | a) PX4'e "çalışamam" bildir · b) girişte Hold iste | a | PX4'ün kendi reddi; drone moda hiç girmez; RTL riski yok | Karar |
| A13 | Başlatma satırının koşulu | koşulsuz · parametreyle | `AF_ENABLE`, varsayılan 0 | Ucuz kapatma düğmesi; ilk yüklemede kapalı | Karar |
| A2 | RC çubuğuyla müdahale | çubuk modu değiştirmez · Position'a geçer | Position'a geçer | "Güvenlik amaçlı olsun" | Karar |
| İç | Kodun iç düzeni | — | Hesaplar ayrı kütüphanede saf fonksiyonlar | Birim testi drone'suz çalışsın | Öneri kabul |
| A3 | Masa testi | — | Liste yeterli; dışarıda GPS fix'li arm'sız testler sonra eklenebilir | "Geliştirmeye açık, düşüneceğim" | Karar |
| C1 | Bu modda arm | serbest · yasak | Yasak; disarm iken geçiş serbest | "Arm değilken bu moda geçebileyim" | Karar |
| C2 | Davranış ayrıntıları (filtre, ivme sınırı başlangıcı, Hold reddi, konum geçersiz, parametre sınırları, `AF_ALPHA` 0.5 / `AF_BETA` 0.17) | — | Spec'teki öneriler | — | Öneri kabul |
| C3 | Log alan adları ve sözlük | önekli · öneksiz | Öneksiz; bütün adlar için ayrıntılı sözlük | "Her şeyi detaylı kaydet" | Karar |

Ayrıntılı gerekçeler ve kullanıcının kendi sözleri: `planning/karar-gunlugu.md`.

### 5.1 Uygulamada verilen kararlar

Kod yazılırken spec'in söylemediği ya da açık bıraktığı her nokta burada toplanır (kullanıcının talimatı, 2026-11-10: "Hep böyle noktaları, seçimlerde, yapılan adımlarda hep rapor olarak kaydedeceğiz"). Her grubun notunda (`implementation/`) aynı kararlar daha ayrıntılı anlatılır.

"Kim karar verdi" sütunu: **Kullanıcı** = kullanıcı seçeneklerden birini açıkça seçti · **Öneri kabul** = kullanıcı Claude'un önerisini kabul etti ("öneri", "olur", "tamam") · **Kod içi** = kullanıcıya görünen bir ad ya da davranış değil; ajan kod yazarken seçti, gerekçesi yazıldı (sorun çıkarsa ilk bakılacak yerlerden biri).

**Görev grubu 1 (iskelet)** — ayrıntı `implementation/grup-1-iskelet-mod-kaydi.md` Bölüm 5–7:

| # | Konu | Seçenekler | Seçilen | Neden | Kim karar verdi |
|---|---|---|---|---|---|
| U1.1 | `auto_follow stop` ne zaman kapansın? | a) kayıt silme mesajını yayınlayıp hemen kapan (`mc_nn_control` kalıbı) · b) PX4 modu listeden kaldırana kadar bekle (en fazla 1 s) | b; kaldırıldığı `vehicle_status.can_set_nav_states_mask`'taki mod bitinden anlaşılır | (a)'da mesaj PX4'e ulaşmıyordu (yayıncı silinince mesaj görünmez oluyor), mod "cevap vermiyor" yoluyla kalkıyordu. İlk denenen `valid_nav_states_mask` dış mod bitini hep 1 gösterdiği için işe yaramadı | Kod içi (SITL'de bulunan hatanın düzeltmesi) |
| U1.2 | QGC parametre grubu adı | `AUTO FOLLOW` · `Auto Follow` · `auto_follow` | `AUTO FOLLOW` | Mod adıyla aynı; QGC'de aranınca bulunur | Öneri kabul ("öneri") |
| U1.3 | `module.yaml` açıklamalarının dili | İngilizce · Türkçe | İngilizce | PX4 geleneği, QGC'de görünen metin; Türkçe açıklamalar `log-sozlugu.md`'de | Öneri kabul ("öneri") |
| U1.4 | Yeni dosyaların lisans başlığı | a) "PX4 Development Team" · b) ekip adı · c) kişi adı | a kalır, altına ikinci satır: `Copyright (c) 2026 Pamukkale Elektrik-Elektronik Mühendisliği tez ekibi.` BSD-3 metni aynen | Başlık yalnızca yorumdur, firmware'e ve flash'a girmez; PX4 geleneği korunur, ekip de görünür | Kullanıcı ("A kalsın, altına … tez ekibini ekleyelim") |
| U1.5 | Arming check cevabında spec'te geçmeyen iki alan (`mode_req_*_relaxed`) | doldur · sıfır bırak | Sıfır (false) | Mesaj sıfırla başlatılır; daha sıkı olan `mode_req_local_position` zaten true | Kod içi |
| U1.6 | Kontrol bayrağı `flag_multicopter_position_control_enabled` | true · false | true | Şema (A) ile aynı; commander bunu zaten kendisi hesaplıyor | Kod içi |
| U1.7 | Kayıt silmede `mode_executor_id` | 0 (`mc_nn_control`) · −1 | −1 | "Executor yok" demek (şema (A)) | Kod içi |
| U1.8 | Kayıt reddedilirse | yeniden dene · bir kez hata yaz | Konsola bir kez `PX4_ERR`, yeniden deneme yok | Şema (A) "Kayıt başarısız" kutusu; QGC uyarısı (events) bu grupta yapılmadı | Kod içi |
| U1.9 | `vehicle_land_detected` hiç gelmemişse | yerde say · havada say | Havada ("yerde değil") | Mesajın boş hâli; PX4 multikopterde `land_detector`'ı her açılışta başlatıyor | Kod içi |
| U1.10 | `module.yaml` ondalık basamakları, `AF_ENABLE` tipi | — | Basamaklar varsayılan ve sınırlar tam görünecek kadar (ör. `AF_BETA` 2 basamak); `AF_ENABLE` tam sayı 0–1, "yeniden başlatma gerekir" işaretli | QGC'de doğru görünsün; modül `AF_ENABLE`'ı okumaz, yalnızca açılış dosyası okur | Kod içi |

**Görev grubu 2 (guidance, filtre, log mesajı): kullanıcıya sorulan 6 nokta** — ayrıntı `implementation/grup-2-guidance-filtre-log.md` Bölüm 7 ve 10, gerekçeler ve kullanıcının sözleri `planning/karar-gunlugu.md` "Görev grubu 2 sonrası sorular":

| # | Konu | Seçenekler | Seçilen | Neden | Kim karar verdi |
|---|---|---|---|---|---|
| G2-1 | Adı `AF_LOS` olmayan `debug_array` mesajı `los_*` alanlarına yazılsın mı? | a) yazılmaz · b) her mesaj yazılır | a (kod değişmedi) | `los_*` alanları her zaman Pi'nin `AF_LOS`'unu gösterir; yabancı mesaj yalnızca `reject_name_count`'u artırır. İçeriği gerekirse kod değiştirmeden `SDLOG_PROFILE`'a 32 (debug) eklenir | Kullanıcı ("1-a") |
| G2-2 | Nedene göre `perf` sayaçları | a) eklenmez · b) tek sayaç · c) her neden için bir sayaç | a; spec Bölüm 2'deki cümle düzeltildi | Aynı sayılar zaten log mesajında ve `auto_follow status`'ta; yeni ad ve flash gerekmez | Kullanıcı ("2-a") |
| G2-3 | Uzun veri kesintisinden sonra filtre | a) sıfırlanmaz (spec'in eski hâli) · b) `AF_DATA_TOUT` boyunca geçerli mesaj yoksa sıfırlanır | b (kod değişti, spec Bölüm 4) | Eski kestirim hiç kullanılmaz; veri dönünce ilk mesajlarda yanlış yöne hız istenmez. Eksisi: KAYIP_BEKLE'den dönüşte hedef hızı sıfırdan başlar (`AF_K_FF` = 0 iken etkisi yok) | Öneri kabul ("olur") |
| G2-4 | EKF konum sıfırlamasında tutulan nokta | a) kaydırılmaz · b) `delta_xy` / `delta_z` kadar kaydırılır | b (kod değişti, spec Bölüm 8) | Drone fiziksel olarak yerinde kalır; PX4'ün kendi modları da böyle yapar (`FlightTaskManualAcceleration.cpp:106-109`, `MulticopterPositionControl.cpp:700-707`) | Öneri kabul ("olur") |
| G2-5a | Sıra kontrolündeki "önceki" hangi mesajın? | 1–4. kontrolleri (ad, sonlu, norm, sıra) geçen son mesaj · 9 kontrolü geçen son mesaj | 1–4 (kod değişmedi) | Masada (konum geçersizken) de tekrar eden mesaj `CHECK_SEQ` olarak görülür | Kullanıcı ("5a olsun") |
| G2-5b | "Önceki numara" unutulsun mu? | a) `AF_DATA_TOUT` boyunca sıra kontrolünü geçen mesaj yoksa · b) hiç · c) büyük geri düşüşte hemen (yeni eşik) · d) moda her girişte | a (kod değişti, spec Bölüm 2) | Pi ne zaman yeniden başlarsa başlasın (sıra no yine 1'den) mesajları kendiliğinden kabul edilir; yeni ad/eşik gerekmez. Güvenlik açısından seçenekler aynı (Hold'dan sonra takibe kendiliğinden dönülmez) | Kullanıcı ("a olsun") |
| G2-6 | NaN davranışları: PASIF'te guidance alanları NaN; hiç geçerli mesaj yokken PASIF'te `time_since_valid` NaN; hedefsiz girişte `lost_time` ilk 0,5 s 0 | onay · değiştir | Onay (kod değişmedi) | Sözlükte böyle anlatıldı | Kullanıcı ("tamam") |

**Görev grubu 2: kod içi küçük kararlar** — ayrıntı grup-2 notu Bölüm 6:

| # | Konu | Seçilen | Neden | Kim karar verdi |
|---|---|---|---|---|
| K2.1 | Kontrollerin yazımı | "NaN geçemez" biçiminde; tutum hiç gelmediyse sıfır dörtlü tutulur, LOS NaN'a döner ve mesaj kontrol 8'de atılır | Tutum yokken "düz ve kuzeye bakıyor" sanılmasın | Kod içi |
| K2.2 | LOS dönüşümden önce | Birim uzunluğa getirilir | `asin` her zaman açı verir, 1'den biraz uzun vektör NaN üretmez | Kod içi |
| K2.3 | Mesafe formülünün yazımı | `d = h × yatay uzunluk / LOS_NED_z` (matematikçe `h / tan δ`) | Hedef tam alttayken sıfıra bölme olmaz | Kod içi |
| K2.4 | Hedef bayrağı "1 mi?" | `abs(data[5] − 1) ≤ FLT_EPSILON` | PX4 derleyici ayarı float eşitliğini hata sayar | Kod içi |
| K2.5 | Filtrede iki çekim anı arası süre ≤ 0 ise | Hız düzeltmesi yapılmaz, yalnızca konum | `β/Δt` sonsuz olurdu | Kod içi |
| K2.6 | İvme sınırının süresi | İki çevrim arasında gerçekten geçen süre (~20 ms) | Sınır gerçek zamana göre doğru olsun | Kod içi |
| K2.7 | LOS hangi tutumla çevrilir? | Mesajın işlendiği çevrimdeki en son tutum (varıştan en fazla ~20 ms sonra) | V3 "varış anındaki tutum" bu küçük farkla uygulanır | Kod içi |
| K2.8 | Hedef tam drone'un üstündeyse | Kuralın mesafe kısmı 0 | Yön tanımsız | Kod içi |
| K2.9 | TAKIP'te filtre kurulu değilse (EKF sıfırlaması hemen sonrası) | Yatay hız 0; bir sonraki kabul edilen mesaj filtreyi kurar | Kestirim yokken hareket istenmesin | Kod içi |
| K2.10 | Moda girişte irtifa geçersizse | `alt_hold_z` NaN, dikey hız 0 istenir | Setpoint geçerli kalsın (yalnızca masada olabilir) | Kod içi |
| K2.11 | Atılan mesaj uyarısı | Konsola en fazla saniyede bir; "hedef yok" için uyarı yok | Mesajlar tam hızda gelebilir; hedef yok bozuk veri değil | Kod içi |
| K2.12 | Konsol metinleri | Yalnızca sözlükteki adlar (`STATE_*`, `CHECK_*`, sayaç adları) | Logla konsol aynı dili konuşsun | Kod içi |
| K2.13 | Şema ile spec çelişkisi (konum kontrolünün sırası) | Spec'e uyuldu (konum 7. kontrol); şemaya dokunulmadı | Spec geçerli kaynak | Kod içi |

**Görev grubu 3 (birim testi)** — ayrıntı `implementation/grup-3-birim-testi.md` Bölüm 2 ve 6:

| # | Konu | Seçilen | Neden | Kim karar verdi |
|---|---|---|---|---|
| K3.1 | Zaman aşımının başladığı an (bilgi, spec A3'e uygun) | Durum makinesi referansı her durumda `max(son geçerli mesaj, giriş anı)`; girişten sonra yeni mesaj gelmezse 0,5 s giriş anından sayılır. Test 6 son geçerli mesajın girişten sonra geldiği durumu sınar; kod değişmedi | Spec A3 genel kural olarak yazılmış; fark en fazla girişten önceki mesajın yaşı kadar (< 0,5 s) | Kod içi (bilgi) |
| K3.2 | Test değerleri | Parametre varsayılanları ve spec'in sayısal örnekleri; testler saf fonksiyonları zamanı argümanla çağırır | Spec örnekleri bu değerlerle hesaplanmış | Kod içi |

**Grup 2 düzeltme turu (2026-11-10)** — ayrıntı grup-2 notu Bölüm 10:

| # | Konu | Seçenekler | Seçilen | Neden | Kim karar verdi |
|---|---|---|---|---|---|
| D1 | G2-3'te süre nereden sayılır? | a) yalnızca son geçerli mesajdan · b) durum makinesiyle aynı referanstan (mod kapalıyken son geçerli mesaj, açıkken `max(son geçerli mesaj, giriş anı)`) | b | Filtre, TAKIP → KAYIP_BEKLE zaman aşımıyla aynı çevrimde sıfırlanır. (a)'da girişten hemen önce gelen mesajdan sonra veri kesilirse TAKIP'te kısa bir "kestirim yok, hız 0" penceresi oluşurdu | Kod içi |
| D2 | G2-5b'de süre nasıl ölçülür? | — | Sıra kontrolünü geçen son mesajın işlendiği çevrimden sayılır; unutma bir sonraki mesaj işlenirken uygulanır (etkisi aynı). Hesap saf fonksiyonda (`keep_previous_seq`, kod içi ad, sözlüğe girmez), birim testli | Kullanıcıya görünen ad eklenmez; test edilebilir | Kod içi |
| D3 | EKF sayaçları | — | Yatay (`xy_reset_counter`) ve dikey (`z_reset_counter`) ayrı ele alınır: yatayda tutulan konum, dikeyde tutulan irtifa kaydırılır; ikisi de filtreyi sıfırlar (önceki gibi) | Her sıçrama yalnızca kendi eksenini kaydırsın | Kod içi |
| D4 | Pi yavaş gönderirse (2 Hz'den yavaş) | — | Her mesajda önceki numara unutulmuş olur; bilerek bırakıldı | Eski/tekrar mesaj yine yaş kontrolüyle (`CHECK_AGE`, 0,5 s) atılır | Kod içi |
| D5 | EKF yön (heading) sıfırlamasında tutulan yaw | a) kaydır · b) kaydırma | **a**: tutulan yaw `delta_heading` kadar kaydırılır (`heading_reset_counter`); Grup 5'te uygulanacak | PX4 setpoint'i yalnızca bir kez kaydırıyor (`MulticopterPositionControl.cpp:709-711`); kaydırma olmazsa drone eski açıyı tutturmak için gereksiz döner. Kullanıcı: "1a olsun, Grup 5'te ekle" (2026-11-10) | Kullanıcı |

**Görev grubu 4 (SITL açık çevrim, test göndericisi)** — ayrıntı `implementation/grup-4-sitl-acik-cevrim.md` Bölüm 2, 3, 6:

| # | Konu | Seçenekler | Seçilen | Neden | Kim karar verdi |
|---|---|---|---|---|---|
| U4.1 | Test göndericisinin bağlantı varsayılanı | Kararda yazan `udpout:127.0.0.1:14540` · a) `udpin:0.0.0.0:14540` · b) `udpout:127.0.0.1:14580` | a (seçenek adı aynı, değer düzeltildi) | PX4 SITL onboard kanalı 14580'i dinler, 14540'a gönderir (`px4-rc.mavlink:4-5, 26`); kararda yazan değerle mesaj PX4'e ulaşmazdı. PX4 ilk paketi gönderenin adresini sabit tutar (`mavlink_receiver.cpp:3203-3218`); b'de yeniden başlatılan script yeni porttan gönderir, kapalı çevrim konum alamaz | Kod içi (kullanıcıya bildirildi, onayı soruldu) |
| U4.2 | Gönderenin MAVLink kimliği | — | Sistem 1, bileşen 191 (`MAV_COMP_ID_ONBOARD_COMPUTER`); HEARTBEAT göndermez | Pi drone'un parçası; PX4 `DEBUG_FLOAT_ARRAY` için kimlik aramıyor | Kod içi |
| U4.3 | `--los` varsayılanı | — | (0,8; 0; 0,6) | spec Bölüm 3 örneği (S1b) | Kod içi |
| U4.4 | Senaryoların zaman çizelgesi ve bozuk değerler | — | `kes`: 10 s'de 1,0 s, 20 s'de 3,0 s kesinti · `hedef-yok`: 0,5 s ve 3,0 s · bozma türleri: 10–20 s her 5. mesaj, 20–23 s hepsi · ad `AF_TEST`, NaN / +sonsuz, 0,7 kat, aynı / 10 geri sıra no, yaş 600 ms, 5°, 11° (dosyanın başındaki sabitler; yeni komut satırı seçeneği yok) | Tek koşuda iki varyant (kısa/uzun); seçenek listesi sabit tutuldu | Kod içi |
| U4.5 | Sıra no | — | Her **gönderilen** mesajda +1 (bozuk dahil); kesintide artmaz | Pi'nin davranışına en yakın | Kod içi |
| U4.6 | Hedefsiz moda giriş (S4-d) | yeni seçenek · script'i çalıştırmamak | Script çalıştırılmaz | Seçenek listesine ad eklememek için | Kod içi |
| U4.7 | Kapalı çevrim hayali hedef | — | Başlangıçta burnun 20 m önünde, yerde, duruyor (`HEDEF_ILERI_M`, `HEDEF_HIZ_NED` sabitleri); tutum `ATTITUDE` (roll, pitch, yaw); konum/tutum 0,5 s'den eskiyse mesaj gönderilmez | S6/S7'nin hedef yeri, hızı ve yolu henüz sorulmadı | Kod içi (S6/S7 için kullanıcıya sorulacak) |
| U4.8 | `--los` birim vektöre çevrilsin mi? | çevir · aynen gönder | Aynen | `norm` gibi bozuk değerler de elle verilebilsin | Kod içi |
| U4.9 | Script çalıştırılabilir | — | `chmod +x` | ruff 0.16.9 varsayılan kuralı (EXE001) | Kod içi |
| U4.10 | Kalkış ve mod değişimi (başsız SITL'de RC yok) | a) simüle joystick ile Position · b) Takeoff modu | a: MAVLink `MANUAL_CONTROL`, Position'da kalkış (spec'ten sapma yok); mod değişimi `MAV_CMD_DO_SET_MODE` (1, 4, 11) — QGC'nin gönderdiği komut | Test edilen kural ("bu modda kalkış/arm yok") spec'teki yoldan sınanır | Kod içi |
| U4.11 | RC anahtarı nasıl verilir? | — | `RC_CHANNELS_OVERRIDE` + bir oturumda `COM_RC_IN_MODE` 0, `RC_CHAN_CNT` 8, `RC_MAP_*`, `COM_FLTMODE1` 2, `COM_FLTMODE6` 100 | Joystick'in mod anahtarı yok; PX4 anahtarı yalnızca RC'den okur (`ManualControl.cpp:170-172`) | Kod içi |
| U4.12 | Test akışı ve ölçüm script'leri | repoya al · geçici tut | Geçici (scratchpad); ölçüm pyulog 1.2.4 Python arayüzüyle | Bu grubun dosyaları yalnızca `af_los_gonder.py` ve dokümanlar; kalıcı analiz script'i Grup 6. Repoya alınması kullanıcıya soruldu (§11) | Kod içi |
| U4.13 | S5 `ufuk`/`uzak` için ek oturum | — | Temel LOS 30° ile tekrar (`21_10_47.ulg`) | İlk koşuda açık çevrim eğim etkisi sonucu karıştırdı | Kod içi |
| U4.14 | Oturum sonu | — | Pilot kapanmadan önce `logger stop`; süreçler PID ile | Pilot kapanınca "Manual control lost" → RTL oluyordu; `px4-shutdown` takılıyor (Grup 1) | Kod içi |
| U4.15 | Sözlükteki RC anahtarı cümlesi | — | "`COM_FLTMODEx` bizim mod numarasıyla" → "değer 100 = External Mode 1 = `nav_state` 23" (sözlük, spec Bölüm 9 alıntısı, §4.8) | SITL'de 23 değil 100 çalıştı (`ManualControl.cpp:595`); yazım düzeltmesi, karar değil | Kod içi |
| U4.16 | Test göndericisi bağlantı adresi (U4.1'in onayı) | a) `udpin:0.0.0.0:14540` · b) `udpout:127.0.0.1:14580` | a | Bkz. U4.1. Kullanıcı: "okey" (2026-11-11) | Öneri kabul |
| U4.17 | `AF_YAW_MIN_D` (hedef neredeyse altındayken yaw dondurma mesafesi) | 1 m kalsın · büyütülsün | 1 m kalır; S6–S7 kapalı çevrimde bakılır | S3'teki dönme açık çevrimden; normal takipte drone hedefe ~15,6 m uzakta. Gerekirse QGC'den değişir, kod gerekmez. Kullanıcı: "okey" (2026-11-11) | Öneri kabul |
| U4.18 | Ayrı yaw hız sınırı | PX4'ün 200°/s'si (`MC_YAWRATE_MAX`) · ayrı parametre şimdi · S6–S7'ye göre karar | **Ayrı parametre şimdi eklenecek** (Grup 5); adı ve varsayılan değeri kullanıcıya soruldu | Öneri "S6–S7'ye bakalım" idi; kullanıcı: "sen şimdiden ekle, parametre dursun" (2026-11-11) | Kullanıcı |
| U4.19 | Test akışı ve ölçüm script'leri | repoya al (`tez/sitl/`) · kullanıcının bilgisayarında kalıcı tut | **Kullanıcının bilgisayarında, repoda değil**; ileride repoya alınabilir. Yeri ve klasör adı kullanıcıya soruldu | Kullanıcı: "script geçici durmasın, benim bilgisayarımda dursun, ileride repoya almaya bakarız" (2026-11-11). Script'ler geçici klasörde bilgisayar yeniden açılınca silinmişti; ajan kayıtlarından geri çıkarıldı | Kullanıcı |
| U4.20 | Hedefsiz girişte Hold (Grup 5'ten sonra) | — | Masa testinde hedefsiz moda girilirse 1,5 s sonra Hold istenir | A3 ile tutarlı. Kullanıcı: "okey" (2026-11-11) | Öneri kabul |

---

## 6. Varsayımlar (ortak spec'ler yazılınca güncellenecek)

| # | Varsayım |
|---|---|
| V1 | Girdi, body FRD frame'de hedef yönünü gösteren LOS birim vektörü (x ileri, y sağ, z aşağı). Kamera montaj açısı Pi tarafında uygulanmış. |
| V2 | Taşıyıcı `DEBUG_FLOAT_ARRAY` (`AF_LOS`), kutu yerleşimi 4.3'teki gibi. Kesin biçim ve frekans ICD'de (m3–5). |
| V3 | LOS → NED dönüşümünde verinin geldiği andaki tutum kullanılır; gecikme telafisi yok. |
| V4 | Drone yüksekliği `-vehicle_local_position.z`; zemin düz ve kalkış yeri. |
| V5 | Hedefin bakılan noktası `AF_TGT_HGT` kadar yüksekte; zemin farkı `AF_GND_OFS`. |
| V6 | Eksen yönleri ve işaretleri Yusuf Ortatepe'nin m10 çalışmasıyla eşlenecek (**açık**). |

---

## 7. PX4 kaynağından öğrenilenler

Bunlar kararları doğrudan etkileyen bulgular; hepsi PX4 v1.17.0 kaynağında doğrulandı.

1. **External mode'da PX4 uçuş görevi çalıştırmıyor:** İsteği bizim modül vermeli (`FlightModeManager.cpp:139-144`).
2. **Yayın kesilirse son istek uygulanmaya devam ediyor:** Güvenli davranış aktif olarak gönderilmeli (`MulticopterPositionControl.cpp:438, 443-449`).
3. **"Çalışamam" sinyali RTL'e götürüyor:** Hold'a değil (`failsafe.cpp:698-702`).
4. **Hold bir komutla istenebiliyor** (`Commander.cpp:936-944`).
5. **RC mod anahtarı yalnızca konum değişince istek gönderiyor** (`ManualControl.cpp:176-177`).
6. **Disarm araçta her mod değişikliğine izin var** (`UserModeIntention.cpp:54-55`); "bu modda arm etme" yasağı moda geçişi engellemiyor (`modeCheck.cpp:196-205`).
7. **MAVLink debug mesajlarının zaman alanı FC'de atılıyor** (`mavlink_receiver.cpp:2804, 2822`).
8. **`logger_topics.txt` varsayılan log listesinin yerine geçiyor** (`logged_topics.cpp:531-540`).
9. **`debug_vect` / `debug_array` yalnızca debug ayarı açıksa loglanıyor** (`logged_topics.cpp:290-294`). SITL varsayılanı bu ayarı içermiyor (`SDLOG_PROFILE` 131).
10. **Gerçek kartta log varsayılan olarak yalnızca arm iken alınıyor** (`SDLOG_MODE` = 0); değişiklik yeniden başlatma ister (`logger/module.yaml:16-31`).
11. **SITL loglarının en fazla 7 klasörü tutuluyor** (`init.d-posix/rcS:183`).
12. **PX4'ün Follow Me hedef filtresi GPS mesajına bağlı** (`TargetEstimator.hpp:112, 210`).
13. **Follow Me = `nav_state` 19, dış modlar = 23–30** (`VehicleStatus.msg:55, 59-66`).
14. **Hız (xy) + konum (z) karışımı geçerli** (`PositionControl.cpp:224-250`).
15. **PX4'ün otomatik modlarındaki yatay ivme sınırı 3 m/s²** (`multicopter_autonomous_params.c:88`).
16. **PX4 arm iken yeni mod kaydını reddediyor** (`ModeManagement.cpp:371-380`); modül arm'dan önce başlamalı.
17. **`rc.mc_apps` her multikopter açılışında çalışıyor**, SITL'de de 6C'de de (`init.d-posix/rcS:289`, `init.d/rcS:485`, `rc.vehicle_setup:20-24`).
18. **Arm'lı araçta mod geçişi, modun "çalışabilirim" cevabına bakıyor** (`UserModeIntention.cpp:58-59`, `externalChecks.cpp:158-160, 188-190`); ret QGC'de mesaj ve uyarı sesiyle görünüyor (`Commander.cpp:2620-2638`).
19. **`DEBUG_FLOAT_ARRAY`'in veri kısmı MAVLink 2 ek alanı** (`common.xml:7630-7631`); MAVLink 1 ile değerler 0 gelir.
20. **(Grup 1) Modül, "kaydımı sil" mesajını yayınlayıp hemen kapanırsa mesaj PX4'e ulaşmıyor.** Kapanan modülün yayını "yayınlanmıyor" sayılıyor ve okunamıyor (`platforms/common/uORB/Publication.hpp:65-72`, `uORBManager.hpp:453`). `mc_nn_control`'de de aynı kalıp var. Bizim modül PX4 modu listeden kaldırana kadar (en fazla 1 s) bekleyip öyle kapanıyor.
21. **(Grup 1) SITL'de arm iken de mod kaydı kabul ediliyor:** SITL `COM_MODE_ARM_CHK`'yı 1 yapıyor (`init.d-posix/px4-rc.simulator:8`); gerçek kartta varsayılan 0 (`commander_params.c:1048`).
22. **(Grup 1) Dış mod bitleri `valid_nav_states_mask`'ta kayıt olmasa da 1** (`ModeManagement.cpp:648-652`); "mod kayıtlı mı" bilgisi `can_set_nav_states_mask`'ta.
23. **(Grup 1) SITL'de `shutdown` komutu takılıyor** ("Exiting NOW." sonrası süreç kapanmıyor); bizim modül kapalıyken de aynı. Test oturumları süreç kapatılarak bitiriliyor.

---

## 8. Yol boyunca düzeltilen hatalar

Şeffaflık için: Süreç içinde Claude'un yaptığı ve sonradan düzeltilen hatalar.

1. **İlk soru listesi çatı repo standartlarını içermiyordu.** Kullanıcı sorunca düzeltildi; artık her spec işinin başında çatı dokümanları okunuyor.
2. **"Local position estimator `FOL_` parametresi kullanıyor" notu yanlıştı.** Spec-shaper kaynakta kontrol etti; böyle bir parametre yok.
3. **"`logger_topics.txt` ile kilitli dosyaya dokunmadan loglanır" bilgisi eksikti.** Dosya varsayılan listeyi tamamen kapatıyor. Düzeltildi ve karar günlüğüne yazıldı.
4. **Girdi mesajı ilk başta `DEBUG_VECT` seçilmişti.** Zaman damgasını taşıyamadığı sonradan görüldü; `DEBUG_FLOAT_ARRAY`'e geçildi.
5. **V1–V6 varsayım metinleri ilk soru listesinden sonra dosyalara yazılmamıştı.** Spec-shaper bulamadı; ana konuşmadan tamamlandı.
6. **Görev talimatını içeren prompt dosyası `/tmp` altındaydı** ve yeniden başlatmada kaybolabilirdi. İçeriği Claude'un kalıcı hafızasına alındı.
7. **`requirements.md`'de S6/S7 konuşulandan farklıydı** (RC kaybı / modül sağlığı). Spec-shaper eski taslak şemadan almıştı; konuşulan tabloya döndürüldü.
8. **S1'in beklentisi yanlıştı** ("hedef önünde → ileri"). İleri/geri açıya bağlı; S1a/S1b olarak düzeltildi.
9. **Hedefsiz girişte süre** bu raporun şemasında 1.0 s görünüyordu; karar 1.5 s idi. Düzeltildi.
10. **İş sırasında S4'ün Hold testi, Hold kodundan önce** yazılmıştı. Sıra düzeltildi.
11. **Masa testi için `SDLOG_MODE` = 2 yazılmıştı**; kullanıcı değeri kendisi seçmek istiyordu. Öneri kaldırıldı.
12. **Spec-writer ajanı, talimata rağmen `git status` çalıştırdı** (yalnızca okuma; zarar yok).
13. **(Grup 1) Eksik başlık dosyası:** ilk SITL derlemesi `SubscriptionInterval` başlığı eklenmediği için hata verdi; eklendi.
14. **(Grup 1) `auto_follow stop` düzeltmesinde yanlış maske:** ilk hâlinde `valid_nav_states_mask`'a bakıldı; bu maske kayıt yokken de 1 kaldığı için modül her durdurmada 1 s bekledi. `can_set_nav_states_mask`'a geçildi.
15. **(Grup 1) SITL'i kapatırken `pkill -f "gz sim"`** komutu çalıştıran kabuğun kendisini de eşledi; sonraki kapatmalarda PID kullanıldı. Dosya etkilenmedi.

---

## 9. Ekip bağımlılıkları ve yapılacaklar

| Kim | Ne | Neden önemli |
|---|---|---|
| **Hüseyin** | 4.10'daki **yedi** kilitli yol için onay (tek talep; `rc.mc_apps` dahil) | Onay olmadan CI'daki `verify-pin` kırmızı kalır |
| **Hüseyin** | `tech-stack.md`'de "entegrasyon yaklaşımı: external mode" güncellemesi | Ürün planını yalnızca o günceller |
| **Hüseyin** | İstenirse "her özelleştirmenin log sözlüğü olsun" ekip standardı (ayrı m00) | Herkes için bağlayıcı olsun diye |
| **Hüseyin** | Vision `model-training` dalında `.pt` model dosyaları var (Vision PR #5) | Kural 9: model ağırlığı repoya girmemeli |
| **Yusuf Ortatepe (Vision)** | `AF_LOS` biçimi: LOS x/y/z, yaş (ms), sıra no, hedef var/yok. MAVLink 2: ✓ doğrulandı (2026-11-10) | Bizim girdimiz |
| **Yusuf Ortatepe (m10)** | Eksen yönleri ve işaretleri | V6 |
| **Ahmet (m06)** | Kamera eğimi → `AF_TRK_ANG`; gerçekçi simülasyon | Takip açısı ve testlerin taşınacağı yer |
| **Yusuf Kurt** | WhatsApp grubuna log kuralları notu | Ekip bilgilensin |

Repo taraması sonucu (2026-11-08): Hiçbir repoda Pi'den yön gönderen kod yok. Ahmet'in `deney/ai-follow-sim` dalı, README'sine göre "tezde kullanılmayacak" bir deneme; `FOLLOW_TARGET` (GPS) ile PX4'ün Follow Me'sini kullanıyor. Geolocation ve gecikme/kayıp simülasyonu için fikir kaynağı.

---

## 10. Kapsam dışı (m16 ve sonrasına kalanlar)

- Hold'dan sonra takibe kendiliğinden dönüş (C) ve ayrıntılı failsafe akışı → **m16**
- Nihai guidance yasası ve ince ayar; gecikme telafisi (gerekirse) → **m13** / **m16**
- Pi tarafı, ICD ve kalıcı gönderici → **Vision** (m3–5, m12)
- Gerçekçi simülasyon ve hareketli insan modeli → **m06**
- Gerçek uçuş → **m22**, **m25**
- Flash'ta yer açma → **m14**
- Ekip için log sözlüğü standardı → ayrı **m00**
- RC kaybı ve modül donması SITL testleri → **m16** adayı

Yol haritasındaki m15 yalnızca "iskelet derlenir" diyor; bu spec, issue #6'yı izleyerek m16'nın bir kısmını da kapsıyor (karar 1).

---

## 11. Açık konular

Grup 1'in 3 sorusu (QGC grup adı, lisans başlığı, `module.yaml` dili) ve Grup 2'nin 6 sorusu cevaplandı; seçilenler §5.1'de.

Uygulamadan açık kalan:
- **Grup 4'ten 5 soru** (`implementation/grup-4-sitl-acik-cevrim.md` Bölüm 9). Kullanıcının cevapları (2026-11-11), ayrıntı §5.1 U4.16–U4.20:
  1. **Sıra no sürekli aynı gelirse** (donmuş Pi): Karar 5b-a gereği her 0,5 s'de bir mesaj kabul ediliyor, Hold'a gidilmiyor; spec S5'teki "uzun bozuk veri hedef kaybı yoluna girer" cümlesiyle çelişiyor. Kullanıcı daha ayrıntılı anlatım istedi; anlatıldı, **cevap bekleniyor**.
  2. `AF_YAW_MIN_D` = 1 m kalır, S6–S7'de bakılır (**karar**).
  3. **Ayrı yaw hız sınırı parametresi Grup 5'te eklenecek** (karar); **adı ve varsayılanı soruldu**.
  4. Bağlantı adresi `udpin:0.0.0.0:14540` onaylandı (**karar**).
  5. Test akışı script'leri repoya girmez, kullanıcının bilgisayarında kalıcı durur (**karar**); **yeri ve klasör adı soruldu**.
- **QGC'de bakılacaklar (kullanıcı):** mod listesinde `AUTO FOLLOW`; yerde arm'lıyken geçiş reddinin ve bu modda arm reddinin QGC'de hangi metinle göründüğü (PX4'ün metni "External 1" diyor).
- **EKF yön (heading) sıfırlaması:** karar verildi (§5.1 D5, a): tutulan yaw `delta_heading` kadar kaydırılacak; **Grup 5'te uygulanacak**.

Bekleyen dış bağımlılıklar:
- Hüseyin: 7 kilitli yol için onay.
- Vision: `AF_LOS` yerleşimi ve eksenler (m10).
- Ahmet (m06): kamera eğimi → `AF_TRK_ANG`; gerçekçi simülasyon.
- **Geliştirmeye açık (kullanıcı notu):** dışarıda, arm etmeden, GPS fix'liyken yapılacak masa/yer testleri eklenebilir; kullanıcı düşünecek.
- Şemaların PNG'ye çevrilmesi: ertelendi.

---

## 12. Sonraki adımlar

1. `spec.md` son haline geldi (2026-11-10).
2. `/agent-os:create-tasks`: görev listesi (kullanıcı onayladı).
3. Uygulama, iş sırasıyla:
   1. iskelet (moda kaydolan modül, açılışta başlatma, yerdeyken geçiş engeli, SITL ve 6C derlemesi) — **bitti (2026-11-10)**, not: `implementation/grup-1-iskelet-mod-kaydi.md`
   2. guidance, alpha-beta ve log mesajı — **bitti (2026-11-10)**, not: `implementation/grup-2-guidance-filtre-log.md`
   3. kısa birim testi — **bitti (2026-11-10)**, not: `implementation/grup-3-birim-testi.md`
   4. SITL ön kontroller + S1–S5 (S4'ün yalnız yerinde-bekleme kısmı) — **bitti (2026-11-11)**, not: `implementation/grup-4-sitl-acik-cevrim.md`
   5. Hold geçişi, S4'ün tamamı
   6. S6–S7, analiz script'i ve sözlüğün son eşitlemesi (log mesajı Grup 2'ye taşındı ve yazıldı)

   Her görev grubundan sonra ne yapıldığı, neden yapıldığı ve nasıl test edildiği bu rapora ve spec klasörüne sade dille yazılır.
4. Yetişmeyenler "m16'ya kalanlar" listesine; PR açıklamasına `Closes Auto-Follow/Auto-Follow#6`.

---

## 13. Terimler sözlüğü

| Terim | Anlamı |
|---|---|
| **LOS** (line of sight) | Görüş doğrultusu: drone'dan hedefe bakan yön |
| **Body FRD** | Drone'a bağlı eksenler: x ileri (Forward), y sağ (Right), z aşağı (Down) |
| **NED** | Dünyaya bağlı eksenler: Kuzey (North), Doğu (East), Aşağı (Down) |
| **Birim vektör** | Uzunluğu 1 olan, yalnızca yön bilgisi taşıyan vektör |
| **Guidance** | "Drone ne yapmalı?" kararını veren katman (hız, yön, burun); kontrolcü değil |
| **Setpoint** | PX4'e verilen istek ("şu hızla git, burnunu şuraya çevir") |
| **External mode** | PX4'e sonradan kaydolan, QGC'de görünen kullanıcı uçuş modu |
| **Alpha-beta filtresi** | Ölçümü yumuşatan ve hedefin hızını kestiren basit filtre |
| **Hold** | PX4'ün olduğu yerde asılı kalma modu |
| **RTL** | Eve dönüş modu |
| **Failsafe** | Bir şey ters gidince PX4'ün kendi güvenlik tepkisi |
| **SITL** | Gazebo simülasyonunda gerçek PX4 kodunun çalıştırılması |
| **ULog (`.ulg`)** | PX4'ün uçuş log dosyası |
| **uORB / topic** | PX4 içindeki modüllerin birbirine veri gönderdiği kanal ve kanalın adı |
| **MAVLink** | Pi / QGC ile Pixhawk arasındaki haberleşme dili |
| **ICD** | Pi ile Pixhawk arasındaki mesajların ortak tanımı (henüz yazılmadı) |
| **`nav_state`** | PX4'ün o anki mod numarası |
| **QGC** | QGroundControl, yer kontrol yazılımı |
| **Flash** | Pixhawk'ta firmware'in durduğu kalıcı bellek (~%98 dolu) |
| **PWM / ESC** | Motor sürücüsüne giden sinyal / motor sürücüsü |
| **Açık / kapalı çevrim test** | Sabit veri gönderen test / drone'un tepkisine göre veri üreten test (ikisi de Gazebo'da) |
| **Birim testi** | Drone'suz ve Gazebo'suz, bilgisayarda saniyeler içinde biten hesap testi |
| **Arming check** | PX4'ün modüle düzenli sorduğu "çalışabilir misin?" sorusu ve cevabı |
| **Land detector (`landed`)** | PX4'ün "drone yerde mi?" kararını veren parçası |
| **`rc.mc_apps`** | PX4'ün her multikopter açılışında çalıştırdığı başlatma dosyası |
| **MAVLink 2 ek alanı** | Yalnızca MAVLink 2'de taşınan mesaj kısmı; MAVLink 1 ile 0 gelir |
| **Bizim verdiğimiz adlar** | Hepsi `log-sozlugu.md`'de |

---

## Belge geçmişi

| Sürüm | Tarih | Ne eklendi |
|---|---|---|
| 1 | 2026-11-09 | Shape-spec sonu: süreç, bütün kararlar, oluşan sistem (henüz kod yok) |
| 2.1 | 2026-11-10 | Son cevaplar: `AF_ENABLE` (varsayılan 0), yerde arm'lıyken geçiş engeli yöntemi (a), çubukla Position'a geçiş, masa testi notu |
| 2 | 2026-11-10 | Write-spec turu: S1–S7 düzeltmesi (S1a/S1b), açılışta başlatma (`rc.mc_apps`, 7. kilitli yol), bu modda arm yasağı, yerdeyken geçiş engeli kararı, hedefsiz girişte 1.5 s, `SDLOG_MODE` kullanıcıya bırakıldı, öneriler kabul, bütün adların sözlüğü |
| 3 | 2026-11-10 | Görev grubu 1 (iskelet): yazılan dosyalar, 6C flash ölçümü (%97,98 → %98,22, +4 756 B), SITL duman testi (mod 23, `AF_ENABLE` = 0 iken başlamıyor), `auto_follow stop` düzeltmesi, PX4'ten 4 yeni bulgu, onay bekleyen 3 küçük konu |
| 4 | 2026-11-10 | Görev grubu 2 (guidance, filtre, log mesajı): §4.5 gerçekleşen hâliyle (9 kontrol, geometri, filtre, kural → kırpma → ivme sınırı, durumlar, setpoint), §4.8 log mesajı yazıldı ve SITL'de 50 Hz görüldü, 6C flash %98,22 → %98,48 (+4 936 B), kullanıcıya 5 soru (yanlış adlı mesajın ham kaydı, `perf` sayaçları, uzun boşlukta filtre, EKF sıfırlamasında tutma noktası, sıra no'da "önceki") |
| 5 | 2026-11-10 | Görev grubu 3 (kısa birim testi): `AutoFollowGuidanceTest.cpp`, 7 test (geometri 12,0 m, kural −1,8 m/s, 2 m/s kırpma, ivme sınırı, bozuk veri, 0,5 s / +1,0 s zaman aşımı, hedef yok), hepsi geçti; kod değişmedi, hata bulunmadı; §4.9'a sonuç tablosu; flash değişmedi (%98,48) |
| 6 | 2026-11-10 | Grup 2 düzeltme turu (kullanıcının Grup 2 sonrası kararları): filtre `AF_DATA_TOUT` boyunca geçerli veri yoksa sıfırlanır (3), EKF konum sıfırlamasında tutulan nokta `delta_xy` / `delta_z` kadar kaydırılır (4), sıra no hafızası `AF_DATA_TOUT` sonra unutulur (5b-a), spec'teki `perf` cümlesi düzeltildi (2-a); 1-a, 5a, 6 kod değişikliği yok. 2 test eklendi (9/9 geçti); 6C flash +160 B (%98,48). Yeni §5.1 "Uygulamada verilen kararlar": Grup 1–3 ve bu turun bütün uygulama kararları; §4.5 ve §11 güncellendi |
| 7 | 2026-11-11 | Görev grubu 4 (SITL açık çevrim): test göndericisi `tez/sitl/af_los_gonder.py` (bağlantı varsayılanı `udpin:0.0.0.0:14540` olarak düzeltildi); ön kontroller (mod 23, arm ve geçiş kuralları, giriş/çıkışta setpoint, RC anahtarı ve çubuğu, MAVLink 2) ve S1a–S5 sonuçları §4.9'da (ULog adlarıyla); modül kodu değişmedi; §5.1'e Grup 4 uygulama kararları (U4.1–U4.15); §11'e 5 yeni soru; RC anahtarı cümlesi düzeltildi (`COM_FLTMODEx` = 100) |
