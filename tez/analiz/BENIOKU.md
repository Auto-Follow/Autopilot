# AUTO FOLLOW log analizi rehberi (`af_log_analiz.py`)

Bu rehber, M15 AUTO FOLLOW modunun uçuş loglarını (ULog, `.ulg`) okuyan `tez/analiz/af_log_analiz.py` script'ini kod okumadan kullanmak ve sonuçlarını yorumlamak içindir. Script'in yaptığı her hesap burada sade dille anlatılır.

- **Görev:** M15 (issue #6), görev grubu 6.8. Kararlar: `agent-os/specs/2026-11-08-m15-takip-kodu/planning/karar-gunlugu.md` ("Görev grubu 6 öncesi sorular").
- **Logdaki adların anlamı:** `agent-os/specs/2026-11-08-m15-takip-kodu/log-sozlugu.md`. Bu rehberde geçen `range_est`, `yaw_cmd` gibi adların hepsi oradaki `auto_follow_status` alanlarıdır.

## İçindekiler

1. Script ne işe yarar?
2. Kurulum
3. Çalıştırma (örnek komutlar)
4. Script logu nasıl böler? (bölüm)
5. Ölçüler: ne demek, nasıl hesaplanır, iyi/kötü örnek
6. Örnek çıktı (gerçek bir SITL logundan)
7. Grafikler nasıl okunur?
8. Filtre girdisi ve çıktısı nasıl yorumlanır?
9. CSV dosyası
10. Sık hatalar ve sınırlar

---

## 1. Script ne işe yarar?

PX4, uçuş boyunca olan her şeyi bir log dosyasına yazar. AUTO FOLLOW modülü de her çevrimde (saniyede 50 kez) kendi durumunu **`auto_follow_status`** adlı log mesajına yazar: Pi'den gelen yön, doğrulama sonucu, hedefin ölçülen ve kestirilen yeri, istenen mesafe, PX4'e verilen hız ve burun yönü isteği, durum (TAKIP, KAYIP_BEKLE…) gibi.

Script bu logu açar ve sorular sorar: "Drone hedefe istenen mesafede durabildi mi? Kaç saniyede? Fazla gidip geri geldi mi? Burnu hedefe bakıyor mu? Hedef kaybolunca kaç saniyede Hold'a geçti? Filtre ölçümü ne kadar yumuşattı?" Her sorunun cevabını bir sayı olarak, Türkçe başlıklı bir tabloda verir. Göz kararı test sayılmadığı için (`agent-os/standards/testing/test-writing.md`) testlerin sonucu bu sayılarla yazılır.

Script hiçbir şeyi değiştirmez; yalnızca logu okur.

## 2. Kurulum

Gerekenler (sürümler sabit, `tez/env/requirements-lock.txt`): Python 3.12, **pyulog 1.2.4**, **numpy 2.5.3**, **matplotlib 3.11.2** (yalnızca grafik için).

Ekipteki laptop kurulumu (`tez/env/VERSIONS.md` ile aynı):

```bash
# PX4 derleme paketleri (pyulog, numpy, matplotlib bunların içinde)
pip install --user --break-system-packages -r ~/Desktop/Projects/Auto-Follow/Autopilot/tez/env/requirements-lock.txt
# Log analizi ortamı (sistem paketlerini de görür)
python3 -m venv --system-site-packages ~/Desktop/Projects/Auto-Follow/.venv-tez
~/Desktop/Projects/Auto-Follow/.venv-tez/bin/pip install -r ~/Desktop/Projects/Auto-Follow/Autopilot/tez/env/analiz-requirements.txt
```

Kurulduğunu denemek için:

```bash
~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python -c "import pyulog, numpy, matplotlib; print('tamam')"
```

## 3. Çalıştırma (örnek komutlar)

Komutlar `Autopilot` klasöründen verilir. Kısaltma: `PY=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python`.

```bash
# 1) En basit: logdaki her AUTO FOLLOW bölümünün tablosu ekrana
$PY tez/analiz/af_log_analiz.py "$HOME/Desktop/AUTO-FOLLOW LOG/21_08_57.ulg"

# 2) Yalnızca bir zaman aralığına bak (saniye, PX4 açılışından beri)
$PY tez/analiz/af_log_analiz.py "$HOME/Desktop/AUTO-FOLLOW LOG/21_08_57.ulg" --aralik 100 140

# 3) Grafikleri de çiz (klasör yoksa açılır) ve bütün sayıları CSV'ye yaz
$PY tez/analiz/af_log_analiz.py "$HOME/Desktop/AUTO-FOLLOW LOG/21_08_57.ulg" \
    --grafik ~/af-grafikler --csv ~/af-grafikler/sonuc.csv

# 4) Tabloyu dosyaya kaydet (Markdown; VS Code / GitHub'da tablo olarak görünür)
$PY tez/analiz/af_log_analiz.py LOG.ulg > sonuc.md

# Yardım
$PY tez/analiz/af_log_analiz.py --help
```

| Seçenek | Ne yapar |
|---|---|
| `<ulog>` (zorunlu) | Okunacak log dosyası |
| `--aralik BAS BIT` | Yalnızca BAS–BIT saniyeleri arasına bakar. Zaman, **PX4 açıldığından beri geçen saniyedir** (logdaki zaman; grup notlarındaki "t" ile aynı). Bir bölüm aralığın sınırında kesilirse yalnızca aralıktaki kısmı ölçülür |
| `--grafik KLASOR` | Her bölüm için 6 PNG grafik çizer (Bölüm 7) |
| `--csv DOSYA` | Bütün ölçüleri tek bir CSV dosyasına yazar (Bölüm 9) |

**Grafikleri ve CSV'leri repoya koymayın** (çatı kural 9: log, grafik çıktısı gibi üretilmiş dosyalar repoya girmez). Repo dışında bir klasör verin.

**Senaryo seçeneği yoktur:** script hangi testin (S4, S6…) yapıldığını bilmez; her bölüm için bütün ölçüleri basar. Hangi ölçüye bakılacağı senaryoya göre değişir (Bölüm 5'in sonundaki tablo).

## 4. Script logu nasıl böler? (bölüm)

Bir SITL oturumunda ya da bir uçuşta AUTO FOLLOW birkaç kez açılıp kapanabilir (ör. S6'da 5 kez, her başlangıç mesafesi için bir kez). Script her açık kalma süresini ayrı bir **bölüm** sayar:

- **Bölümün başı:** `auto_follow_status.mode_active` 0'dan 1'e geçtiği çevrim (modül "PX4'ün modu artık benim" dediği an).
- **Bölümün sonu:** `mode_active`'in 1 olduğu son çevrim.
- **Çıkış:** bölümden hemen sonra `vehicle_status.nav_state`'in aldığı değer, yani PX4'ün hangi moda geçtiği: `Position` (pilot ya da script değiştirdi), `Hold` (bizim modül hedef kaybında istedi), `RTL`, `Land` (PX4'ün kendi güvenlik tepkisi)…
- Log ya da `--aralik` mod açıkken bitiyorsa "mod hâlâ açıktı" yazılır.

Her bölümün tablosunun üstünde, o bölüm başladığında geçerli olan `AF_*` parametreleri yazılır (uçuş sırasında değiştirilen parametreler logdan okunur; ör. S7'de iki bölüm arasında `AF_K_FF` 0'dan 1,0'a değişti).

Zaman hep **PX4 açılışından beri saniye**dir. Log dosyasının adı (`21_08_57.ulg`) logun açıldığı **UTC** saatidir (Türkiye saati = UTC + 3).

## 5. Ölçüler: ne demek, nasıl hesaplanır, iyi/kötü örnek

Tablonun sütunları: **Grup · Ölçü · Değer · Birim · Not.** "—" = bu bölümde hesaplanamadı (ör. TAKIP yoksa mesafe hatası). Sayılarda ondalık ayırıcı noktadır.

Önemli: **mesafe, burun, hız ve filtre ölçüleri yalnızca TAKIP durumundaki çevrimlerden hesaplanır** (KAYIP_BEKLE ve HOLD_ISTENDI'de drone yerinde bekler, hedefe göre hata anlamsızdır).

### 5.1 Genel

| Ölçü | Ne demek | Nasıl hesaplanır |
|---|---|---|
| Başlangıç, Bitiş, Süre | Bölümün zamanı | Bölüm 4 |
| `mode_nav_state` | PX4'ün AUTO FOLLOW'a verdiği mod numarası (23–30; SITL'de hep 23) | Logdan aynen. **19 değildir** (19 PX4'ün kendi Follow Me'si) |
| Çıkış | Bölüm bitince PX4'ün geçtiği mod ve anı | `vehicle_status.nav_state`. Örnekler: Position (pilot ya da test script'i değiştirdi), Hold (AUTO FOLLOW hedef kaybında istedi ya da PX4 failsafe'i), RTL / Land / Descend (PX4 failsafe'i: batarya, konum kaybı) |

### 5.2 Durum

| Ölçü | Ne demek | Nasıl hesaplanır | İyi / kötü örnek |
|---|---|---|---|
| TAKIP / KAYIP_BEKLE / HOLD_ISTENDI süresi | Bölüm boyunca her durumda geçen süre | O durumdaki çevrim sayısı × 0,02 s | Duran ya da yürüyen hedefte (S6, S7) **yalnızca TAKIP** olmalı. KAYIP_BEKLE görülüyorsa veri kesilmiş ya da mesajlar atılmış demektir (sayaçlara bakın) |
| Girişteki durum | Mod açıldığında modülün durumu | İlk çevrimin `state` değeri | Veri geliyorsa TAKIP; hedefsiz girişte KAYIP_BEKLE (beklenen, S4-d) |
| Geçiş N: A → B | Durum değişiklikleri ve süreleri | `state` alanının değiştiği çevrimler. **→ KAYIP_BEKLE:** neden "hedef yok" mesajıysa süre ilk "hedef yok" mesajının varışından, değilse son geçerli mesajın varışından (hedefsiz girişte girişten) ölçülür. **→ HOLD_ISTENDI:** KAYIP_BEKLE'de geçen süre. **KAYIP_BEKLE → TAKIP:** veri dönmeden önce beklemede geçen süre | Veri kesilince ≈ 0,5 s (`AF_DATA_TOUT`) + bir çevrim (≤ 0,02 s): **0,508 s iyi**; "hedef yok"ta bir çevrim (**0,016 s iyi**); beklemeden Hold'a ≈ 1,0 s (`AF_LOST_T`): **1,000 s iyi**. 0,6 s ya da 1,2 s gibi değerler zamanlamada bir sorun demektir |

### 5.3 Hold

| Ölçü | Ne demek | Nasıl hesaplanır | İyi / kötü örnek |
|---|---|---|---|
| `hold_request_count` (bu bölümde) | Bölümde PX4'e gönderilen Hold isteği sayısı | Alanın, bölümün HOLD_ISTENDI çevrimlerindeki en büyük değeri (alan mod kapanınca son değerini koruduğu için önceki bölümün değeri sayılmaz) | 0 = AUTO FOLLOW Hold istemedi; **1 = istek gitti, PX4 kabul etti (iyi)**; 2–3 = PX4 reddetti ya da cevap vermedi; 3 ve çıkış Hold değilse Hold hiç kabul edilmemiştir (QGC'ye uyarı düşer) |
| Hold'a geçişi kim yaptı | Çıkış Hold ama AUTO FOLLOW Hold istememişse | Bölümde HOLD_ISTENDI yoksa yazılır; o zaman aşağıdaki süreler hesaplanmaz | Örnek: batarya kritik seviyesinde PX4'ün kendi failsafe'i önce 5 s Hold yapar (Grup 6, T1): "PX4 (AUTO FOLLOW istemedi)" |
| Son geçerli mesaj → `nav_state` = 4 | Veri kesildikten Hold'a kadar geçen süre (spec S4'ün ana ölçüsü) | Çıkış Hold ise: Hold anı − son kabul edilen mesajın Pixhawk'a varış anı | Beklenen `AF_DATA_TOUT` + `AF_LOST_T` = 1,5 s + ~0,03 s: **1,528 s iyi** (Grup 5). 2 s ya da Hold hiç yoksa sorun |
| İlk "hedef yok" → `nav_state` = 4 | Pi "hedef yok" dedikten Hold'a kadar | Hold anı − son geçerli mesajdan sonraki ilk "hedef yok" mesajının varışı | Beklenen ≈ `AF_LOST_T` = 1,0 s: **1,036 s iyi** |
| Giriş → `nav_state` = 4 | Hedefsiz moda girişte Hold'a kadar | Hold anı − bölümün başı (girişten 0,5 s öncesine kadar geçerli mesaj yoksa) | Beklenen ≈ 1,5 s: **1,524 s iyi** |
| Hold isteği → `nav_state` = 4 | PX4'ün isteği işleme süresi | Hold anı − son `vehicle_command` (`SET_NAV_STATE`) anı | 0,02 s civarı iyi |

### 5.4 Mesafe (`range_est − range_desired`)

**Mesafe hatası** = kestirilen hedefe yatay mesafe (`range_est`) − istenen mesafe (`range_desired`). Artı = drone hedefe istenenden **uzak** (ileri gitmeli); eksi = **yakın** (geri gitmeli). İstenen mesafe 10 m irtifada ve `AF_TRK_ANG` = 30°'de ≈ 15,5 m'dir (yükseklik farkı / tan 30°).

| Ölçü | Ne demek | Nasıl hesaplanır | İyi / kötü örnek |
|---|---|---|---|
| `range_desired` ortalama | İstenen mesafe | TAKIP çevrimlerinin ortalaması | 10 m irtifada ≈ 15,5 m. Çok değişiyorsa irtifa tutulamıyor demektir |
| Mesafe hatası ilk değer | Moda girildiği andaki hata | İlk TAKIP çevrimi | Testin başlangıç koşulu (ör. 20 m'den başlayınca ≈ +4,5 m) |
| Ortalama, std, en büyük (mutlak) | Bütün bölüm boyunca hatanın ortalaması, yayılımı (standart sapma) ve en büyük büyüklüğü | TAKIP çevrimleri | Yaklaşma kısmını da içerdiği için başlangıç mesafesine bağlıdır; kararlı hâl için "son 5 s"e bakın |
| Son değer | Bölümün son TAKIP çevrimindeki hata | — | Duran hedefte 0'a yakın (±0,1 m) iyi |
| **Son 5 s ortalama** (std notta) | Kararlı hâldeki hata | Bölümün son 5 saniyesinin ortalaması ve std'si | Duran hedefte **0,00 ± 0,03 m iyi**. Yürüyen hedefte `AF_K_FF` = 0 iken **artı** bir hata kalır (drone geride kalır; beklenen hedef hızı / `AF_K_DIST` = 1,4 / 0,5 = **2,8 m**), `AF_K_FF` = 1,0 iken ≈ 0 beklenir |
| **Oturma süresi** (±0,3 m) | Hata ±0,3 m bandına girip **bir daha çıkmadığı** an, TAKIP başından itibaren | Bandın dışındaki son çevrimden bir sonraki çevrimin zamanı − ilk TAKIP çevrimi. Bölüm sonunda bant dışındaysa "oturmadı" | Küçük olan iyi. S6'da 20 m'den **4,4 s**; 30 m'den 9,2 s (uzaklık arttıkça uzar, çünkü hız 2 m/s'de kırpılır). "oturmadı" = drone istenen mesafeye hiç yerleşemedi (yürüyen hedefte `AF_K_FF` = 0 ile beklenen) |
| **Aşma** | Drone istenen mesafeyi ne kadar geçti (fazla gidip geri geldi mi) | Hatanın ilk işaretinin tersine en fazla ne kadar gittiği. Başlangıçta zaten bantta ise "—" | **0,05 m'nin altı iyi** (S6'da 0,01–0,05 m). 0,5 m üstü = drone hedefi geçip geri dönüyor, yumuşak değil |
| **Salınım: işaret değişimi** | Hata kaç kez +0,1 m'nin üstünden −0,1 m'nin altına (ya da tersi) geçti | Sayım (±0,1 m altındaki küçük kıpırtılar sayılmaz) | **0 iyi** (hiç gidip gelmedi); 1 = bir kez geçip döndü (aşma); 3 ve üstü = salınım var |
| **Salınım: son 5 s tepe-tepe** | Kararlı hâlde hatanın en büyüğü − en küçüğü | Son 5 s | **0,1 m'nin altı iyi** (S6'da 0,05–0,08 m); 0,5 m üstü = drone ileri geri sallanıyor |

### 5.5 Hız (`vel_cmd_law`, `vel_cmd`)

| Ölçü | Ne demek | Nasıl hesaplanır | İyi / kötü örnek |
|---|---|---|---|
| **Kırpma süresi** | Kuralın istediği hızın `AF_VEL_MAX`'ı (2 m/s) aştığı, yani PX4'e daha küçük hızın gittiği süre | `vel_cmd_law` büyüklüğü > `AF_VEL_MAX` olan TAKIP çevrimleri × 0,02 s | Uzak başlangıçta kırpma olağandır (30 m'den 6,1 s). Kararlı takipte kırpma **olmamalı**; yürüyen hedefte uzun kırpma = drone hedefe yetişemiyor |
| `vel_cmd_law` büyüklüğü en büyük | Kuralın istediği en büyük hız (sınırlardan önce) | `AF_K_FF`·hedef hızı + `AF_K_DIST`·mesafe hatası büyüklüğü | Bilgi: 30 m'den girişte 7,2 m/s |
| `vel_cmd` büyüklüğü ortalama / en büyük | PX4'e giden hız isteği | `vel_cmd` büyüklüğü | En büyük ≤ `AF_VEL_MAX` olmalı (**2,00 iyi**; daha büyükse kırpma çalışmıyor) |
| `vel_cmd` değişim hızı en büyük | Hız isteğinin bir çevrimden ötekine en hızlı değişimi (ivme) | Ardışık TAKIP çevrimleri arasındaki hız farkı / süre | ≤ `AF_ACC_MAX` (3 m/s²) olmalı: **3,00 iyi** (sınır çalışıyor). 3'ten büyükse ivme sınırı çalışmıyor |
| Drone yatay hızı ortalama / en büyük | Drone'un gerçekte ne kadar hızlı gittiği (`vehicle_local_position`) | Bölümdeki örnekler | En büyük ≈ 2,0–2,1 m/s (PX4 isteği biraz aşabilir) |

### 5.6 Burun (yaw)

Üç açı farkı verilir; hepsi derece ve ±180° içine sarılmıştır (ör. 350° fark −10° yazılır):

- **`yaw_cmd` − gerçek yön:** modülün istediği burun yönü ile drone'un gerçek yönü (`vehicle_local_position.heading`) arasındaki fark. **PX4'ün isteği ne kadar iyi izlediğini** gösterir.
- **`yaw_cmd` − hedef yönü:** istenen burun yönü ile drone'dan kestirilen hedefe (`target_est_ned`) bakan yön arasındaki fark. `AF_YAWRATE_MAX` (60°/s) yüzünden istek hedefe hemen dönmez; bu fark o gecikmeyi ve yaw donmasını gösterir.
- **Gerçek yön − hedef yönü:** drone'un burnunun hedefe ne kadar baktığı. **"Burun hedefte mi?" sorusunun cevabı budur.**

| Ölçü | Nasıl hesaplanır | İyi / kötü örnek |
|---|---|---|
| Her fark için ortalama, en büyük (mutlak), son 5 s ortalama | TAKIP çevrimleri | Son 5 s ortalama: **0,0° iyi**; 3° üstü = hedef kadrajın ortasında değil. En büyük, girişteki dönüşü içerir (S6'da hedef 30° sağda başladığı için ≈ 30°) |
| **Burun aşması** | Gerçek yön − hedef yönü, ilk işaretinin tersine en fazla ne kadar geçti (başlangıçta ±2° içindeyse yazılmaz) | S6'da **5,5–7,5°**: drone dönüşü biraz fazla yapıp geri geliyor (PX4'ün tutum kontrolcüsü; Grup 6 notunda) |
| **Burun oturma süresi** (±2°) | Gerçek yön − hedef yönü ±2° bandına girip bir daha çıkmadığı an, TAKIP başından | S6'da 30°'lik dönüşte **2,5–2,6 s**. Yalnız dönüş 0,5 s sürer (60°/s), kalanı aşmanın sönmesi |
| `yaw_frozen` süresi | Hedef `AF_YAW_MIN_D` (1 m) içinde olduğu için burnun dondurulduğu süre | Normal takipte (≈ 15 m) **0**. Hedef drone'un altına girerse artar |

### 5.7 Filtre (alpha-beta: girdi ve çıktı)

Filtrenin **girdisi** her yeni mesajdan hesaplanan hedef yeri `target_meas_ned`'dir (ölçüm). **Çıktısı** kestirilen hedef yeri `target_est_ned` ve kestirilen hedef hızı `target_vel_ned`'dir. Ayrıntılı yorum Bölüm 8'de.

| Ölçü | Ne demek | Nasıl hesaplanır | İyi / kötü örnek |
|---|---|---|---|
| Ölçüm sayısı, ölçüm hızı | Filtrenin kaç yeni ölçümle düzeltildiği | `filter_updated` = 1 olan çevrimler; hız = sayı / bölüm süresi | Gönderim hızına (SITL'de 20 Hz) eşit olmalı: **20,0 Hz iyi**. Daha azsa mesajlar atılıyor ya da kesiliyor |
| Girdi–çıktı uzaklığı ortalama / std / en büyük | Filtrenin çıktısı ölçümden ne kadar farklı | Ölçüm gelen çevrimlerde `target_meas_ned` ile `target_est_ned` arasındaki yatay uzaklık (düzeltmeden sonra) | Duran hedefte **0,01 m civarı iyi**. Büyükse ya ölçüm gürültülü ya da hedef hareket ediyor ve filtre geride kalıyor |
| `target_vel_ned` büyüklüğü ortalama / son 5 s / en büyük | Filtrenin kestirdiği hedef hızı | `target_vel_ned` büyüklüğü | Duran hedefte son 5 s **0,00 iyi**; yürüyen hedefte gerçek hıza (S7'de 1,4 m/s) yakın olmalı. En büyük, drone hızlanırken oluşan sahte hızları da gösterir (Bölüm 8) |
| Ölçümlerden türetilen hız ortalama | Ölçülen hedef yerlerinin 1 s içindeki değişiminden hesaplanan hız (filtreden bağımsız kontrol) | (ölçüm(t) − ölçüm(t − 1 s)) / 1 s | Filtrenin hız kestirimiyle karşılaştırmak için |
| Türetilen hız ile `target_vel_ned` farkı ortalama | Filtrenin hız kestirimi ölçümlerle ne kadar uyumlu | İki hız vektörü arasındaki farkın büyüklüğü, ortalama | Küçük (0,1 m/s altı) iyi. Büyükse filtrenin hız kestirimi gürültülü ya da gecikmeli |

### 5.8 Girdi (Pi'den gelen mesajlar)

| Ölçü | Ne demek | Nasıl hesaplanır | İyi / kötü örnek |
|---|---|---|---|
| `latency` ortalama / en küçük / en büyük | Kullanılan ölçümün toplam gecikmesi = (Pixhawk'ın işlediği an − mesajın varışı) + Pi'nin bildirdiği yaş | Ölçüm gelen çevrimlerde `latency` alanı | SITL'de yaş sabit 50 ms → **54–70 ms** (işlem payı ≤ 20 ms). Gerçek uçuşta Pi'nin görüntü işleme süresi eklenir; gecikme telafisi gerekip gerekmediğine bu sayıyla karar verilecek (m13/m16) |
| `accept_count` artışı | Bölümde kabul edilen mesaj sayısı | Sayaç, bölüm sonu − bölümden hemen önce | Gönderim hızı × süre (30 s × 20 Hz = 600) |
| `no_target_count` artışı | "Hedef yok" mesajı sayısı | Aynı | Hedef görünürken 0 |
| `reject_*_count` artışı (8 tane) | Nedene göre atılan mesajlar (ad, NaN, uzunluk, sıra no, yaş, konum, açı, menzil) | Aynı | Normal uçuşta **hepsi 0**. Sıfır olmayan sayaç, Pi'nin mesajında ya da drone'un konumunda bir sorun olduğunu söyler (anlamları sözlükte, Bölüm 6) |

### 5.9 İrtifa

| Ölçü | Ne demek | İyi / kötü örnek |
|---|---|---|
| `alt_hold_z` | Moda girişte tutulan irtifa (NED z, aşağı artı: −9,94 = 9,94 m yukarıda) | — |
| Drone irtifası en küçük / en büyük | Bölüm boyunca gerçek irtifa | Fark 0,1 m civarı iyi (S6'da 9,92–9,97 m) |

### 5.10 Hangi senaryoda hangi ölçüye bakılır?

| Senaryo | Bakılacak ölçüler |
|---|---|
| S1a, S1b, S3 (açık çevrim, sabit yön) | Kırpma süresi, `vel_cmd` en büyük, değişim hızı; girişteki mesafe hatası |
| S2 (hedef sağda) | `yaw_cmd` − gerçek yön (dönüş) |
| S4 (hedef kaybı) | Durum geçişleri, Hold ölçüleri, `hold_request_count` |
| S5 (bozuk veri) | `reject_*_count` artışları, durum süreleri |
| **S6 (duran hedef)** | Oturma süresi, aşma, salınım, son 5 s mesafe hatası, kırpma süresi, burun oturma süresi ve son 5 s burun hatası |
| **S7 (yürüyen hedef)** | `--aralik` ile yürüme bacaklarında son 5 s mesafe hatası (geride kalma), `target_vel_ned` (≈ 1,4 m/s), filtre girdisi/çıktısı, kırpma |

## 6. Örnek çıktı (gerçek bir SITL logundan)

Grup 6, S6 (duran hayali insan), başlangıç mesafesi **20 m**, burnun 30° sağı: `21_08_57.ulg`, bölüm 3. Komut: `$PY tez/analiz/af_log_analiz.py "$HOME/Desktop/AUTO-FOLLOW LOG/21_08_57.ulg"` (çıktının bölüm 3 kısmı, girdi sayaçlarının bir kısmı kısaltıldı):

```text
## Bölüm 3: 108.560–138.580 s (30.0 s)

Parametreler (bölüm başında): AF_K_DIST = 0.5, AF_K_FF = 0, AF_VEL_MAX = 2, AF_ACC_MAX = 3, AF_ALPHA = 0.5, AF_BETA = 0.17, AF_TRK_ANG = 30, AF_TGT_HGT = 1, AF_DATA_TOUT = 0.5, AF_LOST_T = 1, AF_YAWRATE_MAX = 60, AF_YAW_MIN_D = 1

| Grup | Ölçü | Değer | Birim | Not |
|---|---|---|---|---|
| Genel | Çıkış | Position (nav_state 2, t = 138.588 s) |  |  |
| Durum | TAKIP süresi | 30.040 | s |  |
| Durum | KAYIP_BEKLE süresi | 0.000 | s |  |
| Mesafe | range_desired ortalama | 15.48 | m | istenen mesafe |
| Mesafe | Mesafe hatası ilk değer | 4.52 | m | t = 108.560 s |
| Mesafe | Mesafe hatası son 5 s ortalama | 0.00 | m | std 0.025 m |
| Mesafe | Oturma süresi (hata ±0.3 m içinde) | 4.400 | s | ... |
| Mesafe | Aşma | 0.04 | m | ... |
| Mesafe | Salınım: işaret değişimi | 0 | adet | ... |
| Mesafe | Salınım: son 5 s tepe-tepe | 0.08 | m | en büyük − en küçük hata |
| Hız | Kırpma süresi | 1.200 | s | vel_cmd_law büyüklüğü > AF_VEL_MAX (2 m/s) olan süre |
| Hız | vel_cmd büyüklüğü en büyük | 2.00 | m/s | PX4'e giden |
| Hız | vel_cmd değişim hızı en büyük | 3.00 | m/s² | TAKIP içinde; sınır AF_ACC_MAX = 3 |
| Burun | gerçek yön − hedef yönü en büyük (mutlak) | 30.0 | deg |  |
| Burun | gerçek yön − hedef yönü son 5 s ortalama | 0.0 | deg |  |
| Burun | Burun aşması | 6.9 | deg | ... |
| Burun | Burun oturma süresi (gerçek yön − hedef yönü ±2 deg) | 2.520 | s | ... |
| Filtre | Ölçüm hızı | 20.0 | Hz |  |
| Filtre | Girdi–çıktı uzaklığı ortalama | 0.00 | m | ... |
| Filtre | target_vel_ned büyüklüğü en büyük | 1.10 | m/s | kestirilen hedef hızı |
| Filtre | target_vel_ned büyüklüğü son 5 s ortalama | 0.00 | m/s |  |
| Girdi | latency ortalama | 58.0 | ms | kabul edilen mesajlar |
| Girdi | accept_count artışı | 601 | adet |  |
| Girdi | reject_seq_count artışı | 0 | adet |  |
| İrtifa | Drone irtifası en küçük | 9.92 | m |  |
| İrtifa | Drone irtifası en büyük | 9.97 | m |  |
```

**Bu tablo nasıl okunur?** Drone hedefe 20 m uzakta, hedef burnun 30° sağındayken AUTO FOLLOW'a alındı. İstenen mesafe 15,48 m, yani başta 4,52 m fazla uzaktı. Kural 2 m/s'den fazla hız istedi, 1,2 s boyunca 2 m/s'de kırpıldı; ivme sınırı (3 m/s²) çalıştı. Drone 4,4 s'de ±0,3 m bandına girdi ve bir daha çıkmadı, istenen mesafeyi yalnızca 4 cm geçti, hiç salınmadı; son 5 s'de hata 0,00 ± 0,03 m. Burun 30°'lik dönüşü 2,5 s'de tamamladı (6,9° fazla dönüp geri geldi), sonra tam hedefe baktı. Filtre her mesajla (20 Hz) düzeltildi; duran hedefin hızını son 5 s'de 0,00 m/s kestirdi, ama drone hızlanırken bir an 1,1 m/s'lik sahte bir hız gördü (Bölüm 8). Hiç mesaj atılmadı. **Sonuç: S6 için iyi bir koşu.**

## 7. Grafikler nasıl okunur?

`--grafik KLASOR` verilince her bölüm için 6 PNG yazılır. Dosya adı `<log adı>_bolum<N>_<tür>.png` (ör. `21_08_57_bolum3_mesafe.png`). Yatay eksen hep zaman (s, PX4 açılışından beri). TAKIP dışındaki çevrimlerde mesafe ve burun çizgileri kesiktir.

| Dosya | İçinde ne var | Nasıl okunur |
|---|---|---|
| `_mesafe` | Üstte mesafe hatası ve yeşil ±0,3 m bandı; altta `range_est` (kestirilen), `range_desired` (istenen) ve `range_meas` (ölçülen, noktalar) | İyi: hata eğrisi bir kez bandın içine iner ve orada kalır, 0'ın öbür yanına geçmez. Kötü: bandın içine girip çıkan dalgalı eğri (salınım) ya da banda hiç girmeyen eğri. Altta mavi ve yeşil üst üste ise filtre ölçümü izliyor |
| `_burun` | Üç açı farkı (Bölüm 5.6) | İyi: yeşil (gerçek yön − hedef yönü) birkaç saniyede 0'a iner ve orada kalır. Turuncu (`yaw_cmd` − hedef yönü) girişte 60°/s ile düz bir çizgi gibi 0'a gider (yaw hız sınırı). Mavi (`yaw_cmd` − gerçek yön) PX4'ün gecikmesidir |
| `_hiz` | `vel_cmd_law` (kural), `vel_cmd` (PX4'e giden), drone hızı, hedef hızı, kırmızı kesikli `AF_VEL_MAX` | Mavi kırmızı çizginin üstündeyken turuncu çizgi 2'de düz kalır: kırpma. Turuncunun eğimi ivme sınırıdır. Yeşil (drone) turuncuyu biraz geriden izler. Kırmızı (hedef hızı) duran hedefte 0'a yakın kalmalı |
| `_filtre` | Üstte hedefin kuzey (x), ortada doğu (y) konumu: noktalar ölçüm (girdi), çizgi kestirim (çıktı); altta kestirilen hedef hızı bileşenleri, büyüklüğü (siyah) ve ölçümden türetilen hız (noktalar) | Bölüm 8 |
| `_harita` | Yukarıdan bakış: drone'un yolu, ölçülen hedef noktaları, kestirilen hedef yolu; yeşil nokta drone'un girişteki yeri. Yukarısı kuzey, sağ doğu | Duran hedefte ölçüm ve kestirim tek bir noktada toplanır. Yürüyen hedefte (S7) hedefin L yolu ve drone'un onu arkadan izleyen yolu görülür |
| `_durum` | `state` (PASIF/TAKIP/KAYIP_BEKLE/HOLD_ISTENDI), `check_result` (son mesajın doğrulama sonucu), `time_since_valid` ve `lost_time` | S4'te: veri kesilince `time_since_valid` 0,5'e kadar artar, durum KAYIP_BEKLE olur, `lost_time` 1,0'a kadar sayar, HOLD_ISTENDI. S5'te: `check_result` sıfırdan farklı değerlere sıçrar (atılan mesajın nedeni) |

## 8. Filtre girdisi ve çıktısı nasıl yorumlanır?

Alpha-beta filtresi iki iş yapar: **(1)** ölçülen hedef yerini yumuşatır, **(2)** hedefin hızını kestirir (bu hız `AF_K_FF` > 0 iken drone'un hız isteğine eklenir). Her yeni ölçümde filtre önce "hedef son hızıyla şuraya gitmiş olmalı" diye tahmin eder, sonra ölçümle tahmin arasındaki farkın `AF_ALPHA` (0,5) katı kadar yeri, `AF_BETA` (0,17) ile orantılı olarak hızı düzeltir.

`_filtre` grafiğinde ve tablodaki "Filtre" satırlarında şunlara bakın:

1. **Duran hedefte (S6):** ölçüm noktaları ile kestirim çizgisi üst üste olmalı (girdi–çıktı uzaklığı ≈ 0,01 m) ve hedef hızı 0'da kalmalı. S6'da son 5 s'de hız 0,00 m/s, uzaklık en çok 0,05–0,13 m.
2. **Drone hızlanırken görülen sahte hız:** S6'da hedef durduğu hâlde kestirilen hız, drone hızlanıp yavaşladığı birkaç saniyede 0,4–2,3 m/s'ye çıktı (30 m'den girişte en çok 2,25 m/s). Nedeni: Pi'nin (SITL'de test göndericisinin) yönü hesapladığı an ile Pixhawk'ın o yönü dünyaya çevirdiği andaki tutum (eğim) arasındaki küçük zaman farkı. Drone eğilirken bu fark ölçülen hedef yerini birkaç desimetre kaydırır, filtre bunu "hedef hareket etti" sanar. `AF_K_FF` = 0 iken etkisi yoktur; `AF_K_FF` > 0 iken drone'un hız isteğine kısa bir sıçrama olarak girer (S7 sonuçlarında). Gecikme telafisi (m13/m16) bunu azaltır.
3. **Yürüyen hedefte (S7):** ölçüm noktaları düzgün bir doğru boyunca ilerler; kestirim çizgisi onların hemen üstündedir. Hız grafiğinde kestirilen hız yürüme başlayınca 0'dan ~1,4 m/s'ye çıkmalı, 90° sağa dönüşte bileşenler yer değiştirmeli (ör. kuzey hızı küçülürken doğu hızı büyür) ve hedef durunca 0'a dönmeli. Kestirim gerçek hıza ne kadar çabuk yetişiyorsa filtre o kadar "hızlı"; siyah çizgi ne kadar az titriyorsa o kadar "sakin"dir.
   - Gerçek örnek (`21_14_07.ulg`, `AF_K_FF` = 0, bölüm 1): yürürken kestirilen hız ortalama **1,39 m/s** (gerçek 1,4), titreşim (std) 0,03–0,04 m/s; yürüme başlangıcında ve dönüşte ~0,5 s'de gerçek hıza yetişti; girdi–çıktı uzaklığı ortalama 0,01 m. **Bu iyi bir filtre davranışıdır.**
   - Aynı yol, `AF_K_FF` = 1,0 (bölüm 2): kestirilen hızın ortalaması yine 1,39–1,43 m/s, ama **±0,4 m/s titreşiyor** (std 0,38 m/s, ~3–6 Hz) ve hedef durunca da 0'a inmeyip ~0,4 m/s civarında titremeyi sürdürüyor; "türetilen hız ile `target_vel_ned` farkı" 0,07'den 0,35 m/s'ye çıktı. Olası nedeni (doğrulanacak) 2. maddedeki sahte hızın bir döngüye girmesi: kestirilen hız drone'un hız isteğine eklenince drone'un eğimi kıpırdıyor, eğim ölçümü kaydırıyor, filtre yeni bir sahte hız görüyor. Mesafe hatası yine küçük (±0,15 m) ama drone'un eğimi `AF_K_FF` = 0'a göre 4–7 kat daha fazla kıpırdıyor (eğim std 0,09–0,11° yerine 0,36–0,72°). **Bu, filtre ayarı ya da gecikme telafisi gerektirebilecek bir davranıştır** (Grup 6 notunda kullanıcıya soruldu).
4. **Ayar ne zaman gerekir?** Kestirilen hız çok titriyorsa (siyah çizgi gürültülü) `AF_ALPHA`/`AF_BETA` küçültülebilir; hız gerçek hıza çok geç yetişiyorsa büyütülebilir. **Bu parametreler kullanıcıya sorulmadan değiştirilmez** (karar 2026-11-11).

## 9. CSV dosyası

`--csv DOSYA` ile her bölümün her ölçüsü bir satır olur. Sütunlar: `bolum, grup, olcu, deger, birim, not` (UTF-8, virgülle ayrılmış, ondalık ayırıcı nokta). Excel / LibreOffice'te açarken "virgülle ayrılmış, UTF-8" seçin. Birden fazla logu karşılaştırmak için her logun CSV'si ayrı dosyaya yazılıp yan yana konabilir (ör. S6'nın beş mesafesi tek logda beş bölüm olarak gelir).

## 10. Sık hatalar ve sınırlar

| Belirti | Neden | Çözüm |
|---|---|---|
| `ModuleNotFoundError: No module named 'pyulog'` | Python ortamı kurulu değil ya da sistem Python'u kullanıldı | Bölüm 2; `.venv-tez/bin/python` ile çalıştırın |
| `HATA: ... logda auto_follow_status yok` | Log AUTO FOLLOW modülü olmayan bir firmware'le ya da modül başlamadan alınmış (`AF_ENABLE` = 0) | `AF_ENABLE` = 1 yapıp yeniden başlatın; gerçek kartta log yalnızca arm iken alınır (`SDLOG_MODE` = 0) |
| "Bulunan AUTO FOLLOW bölümü: 0" | Mod bu logda hiç açılmamış ya da `--aralik` yanlış | `--aralik`'i kaldırın; zamanın PX4 açılışından beri saniye olduğunu unutmayın (saat değil) |
| Mesafe ve burun satırlarında "—" | Bölümde TAKIP hiç yok (ör. hedefsiz giriş) | Beklenen; durum ve Hold satırlarına bakın |
| "Oturma süresi: oturmadı" | Hata bölüm sonunda ±0,3 m dışında | Bölüm çok kısa, hedef yürüyor ya da drone salınıyor; grafiğe bakın |
| Grafik ve CSV repoda görünüyor | Çıktı klasörü repo içinde verildi | Repo dışında bir klasör kullanın; repoya eklemeyin |
| Açık çevrim testlerinde (S1–S3) burun ve hedef hızı tuhaf | Açık çevrimde hedef drone'a bağlı "kayar"; hedef yönü ve hızı gerçek değildir | Açık çevrimde yalnızca hız ve kırpma ölçülerine bakın (Bölüm 5.10) |

**Sınırlar:** Script testin "doğru" olup olmadığına karar vermez; sayıları verir. Kesin başarı eşikleri yol haritası m01'e aittir; bu rehberdeki "iyi / kötü" örnekler SITL sonuçlarına göre öneridir. "Hedef yönü" filtrenin kestirdiği hedefe göredir; hedefin gerçek yeri logda yoktur (SITL'de test göndericisi bilir, gerçek uçuşta kimse bilmez).
