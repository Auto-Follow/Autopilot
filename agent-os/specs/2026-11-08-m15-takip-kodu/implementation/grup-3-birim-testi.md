# Görev grubu 3: Kısa birim testi

- **Tarih:** 2026-11-10 · **Dal:** `ozellik/m15-takip-kodu` · **Görev listesi:** `../tasks.md` Grup 3 (3.1–3.6)
- **Durum:** Bitti. 7 testin hepsi geçti. Modül kodu (guidance) **değişmedi**; yalnızca test dosyası ve `CMakeLists.txt`'e bir satır eklendi.
- Bu not kod okumadan anlaşılacak şekilde yazıldı. Adların anlamı `../log-sozlugu.md`'de.

## 1. Ne yapıldı?

Guidance hesapları (Grup 2'deki `AutoFollowGuidance` kütüphanesi) için bilgisayarda, drone'suz ve Gazebo'suz çalışan kısa bir GoogleTest dosyası yazıldı. Testler spec'teki sayısal örnekleri birebir kullanır; böylece "kod spec'in söylediği sayıyı veriyor mu?" sorusu saniyeler içinde cevaplanır.

| Dosya | Ne | Yeni mi? |
|---|---|---|
| `src/modules/auto_follow/AutoFollowGuidanceTest.cpp` | 7 test | Yeni |
| `src/modules/auto_follow/CMakeLists.txt` | `px4_add_unit_gtest(SRC AutoFollowGuidanceTest.cpp LINKLIBS AutoFollowGuidance)` satırı | Bir satır |

Testler firmware'e girmez (yalnızca `make tests` derlemesinde derlenir), flash'ı etkilemez. Dosya, Hüseyin'e iletilecek 7 yolun ilki olan `src/modules/auto_follow/` içinde; `tez/pin/allowed-paths.txt`'e dokunulmadı.

## 2. Neden böyle?

| Ne | Neden | Kaynak |
|---|---|---|
| Kısa tutuldu (7 test, ~8 sınırının altında) | Süre kısıtlı; yalnızca temel hesaplar | Karar 10.1, tasks 3.1 |
| Testler hesap fonksiyonlarını doğrudan çağırır, zamanı argümanla verir | Grup 2'de hesaplar bunun için uORB'suz, saf fonksiyon olarak yazıldı | "İç düzen" kararı, spec Bölüm 11 |
| `px4_add_unit_gtest` (uORB/parametre altyapısı gerekmez) | PX4'ün kendi kalıbı | `PositionControl/CMakeLists.txt`, `cmake/px4_add_gtest.cmake:40`, `test-writing.md:6-10` |
| Parametre değerleri varsayılanlar (`AF_TRK_ANG` 30°, `AF_K_DIST` 0,5, `AF_K_FF` 0, `AF_VEL_MAX` 2, `AF_ACC_MAX` 3, `AF_DATA_TOUT` 0,5, `AF_LOST_T` 1,0 …) | Spec örnekleri bu değerlerle hesaplanmış | spec Bölüm 10 |

## 3. Testler ve ne kanıtladıkları (sade dille)

| # | Test adı (kod içi) | Ne verildi | Ne beklendi | Ne kanıtlıyor |
|---|---|---|---|---|
| 1 | `GeometrySpecExample` | Drone 10 m'de, düz, burun kuzeyde; LOS (0,8; 0; 0,6); `AF_TGT_HGT` 1,0, `AF_GND_OFS` 0 | Aşağı bakış 36,9°, h = 9,0 m, **d = 12,0 m**, hedef 12 m kuzeyde. Aynı LOS burun doğudayken: hedef 12 m doğuda | Pi'nin "kameraya göre" verdiği yön, drone'un yönüyle doğru çevriliyor ve yerdeki mesafe doğru bulunuyor (spec Bölüm 3 örneği) |
| 2 | `LawSpecExampleMovesAway` | Test 1'deki hedef (12 m), `AF_TRK_ANG` 30° | İstenen mesafe 15,6 m; hız **−1,8 m/s** (hedeften uzaklaş, güneye); burun hedefe (yaw 0); 2 m/s'nin altında olduğu için kırpılmaz | Hız kuralı spec'teki sayıyı veriyor; hedef yakınsa drone geri gidiyor (spec Bölüm 5 örneği, S1b) |
| 3 | `LawClippedToVelMaxS1a` | S1a geometrisi: LOS (0,951; 0; 0,309), aşağı bakış 18° | d ≈ 27,7 m; kural ≈ **+6,0 m/s** ister; çıkış **2 m/s**'ye kırpılır, yön aynı kalır | Uzak hedefte hız `AF_VEL_MAX`'ı aşmıyor (S1a) |
| 4 | `AccelerationLimitPerCycle` | Bir çevrim (20 ms), `AF_ACC_MAX` 3 m/s² → en fazla 0,06 m/s değişim | Hover'dan 2 m/s'ye sıçrama isteği → yalnızca 0,06 m/s ilerler; çapraz sıçramada **değişimin uzunluğu** 0,06 m/s (eksen başına değil); küçük değişim olduğu gibi geçer | Hız komutu bir çevrimde `AF_ACC_MAX · Δt`'den fazla değişmiyor, her yönde aynı sınırla |
| 5 | `CorruptInputRejected` | Geçerli bir `AF_LOS` örneği ve bozuk kopyaları | Geçerli → `CHECK_OK`; NaN (LOS'ta) ve sonsuz (yaşta) → `CHECK_NONFINITE`; LOS uzunluğu 0,71 → `CHECK_NORM`; aynı ve eski sıra no → `CHECK_SEQ`; başka ad (`OTHER`) ve aynı başlayan uzun ad (`AF_LOS2`) → `CHECK_NAME` | Bozuk veri doğru nedenle ayıklanıyor (spec Bölüm 2, kontrol 1–4) |
| 6 | `DataTimeoutThenHold` | TAKIP'te, son geçerli örnek t1'de geldi, sonra hiç gelmedi | t1 + 0,48 s: hâlâ TAKIP; **t1 + 0,5 s: KAYIP_BEKLE** (`time_since_valid` 0,5 s); t1 + 1,48 s: hâlâ KAYIP_BEKLE; **t1 + 1,5 s: HOLD_ISTENDI** (`lost_time` 1,0 s) | Veri kesilince 0,5 s sonra yerinde bekleme, 1,0 s sonra Hold isteği (spec Bölüm 7 zaman çizelgesi) |
| 7 | `NoTargetImmediatelyLost` | TAKIP'te; 0,1 s sonra bayrağı 0 olan örnek | Örnek `CHECK_NO_TARGET`; bir sonraki çevrimde **hemen KAYIP_BEKLE** (0,5 s beklenmez); "hedef yok" örneğinden 0,98 s sonra hâlâ KAYIP_BEKLE, **1,0 s sonra HOLD_ISTENDI** | Pi "hedef yok" deyince zaman aşımı beklenmeden yerinde beklemeye geçiliyor (spec Bölüm 7) |

Hesaplanan değerler (elle): aşağı bakış 0,6435 rad; istenen mesafe 9 / tan 30° = 15,59 m; kural 0,5 × (12,0 − 15,59) = −1,79 m/s; S1a: d = 9 × 0,951 / 0,309 = 27,70 m, kural 0,5 × (27,70 − 15,59) = +6,06 m/s. Testlerdeki toleranslar: mesafeler 0,001 m, hızlar 0,01 m/s (S1a kuralı 0,1 m/s, çünkü spec "≈ 6,0" diyor), süreler tam (mikrosaniye).

## 4. Nasıl çalıştırıldı, sonuç

| Komut | Sonuç |
|---|---|
| `make tests TESTFILTER=AutoFollowGuidance` | **Geçti.** Yalnızca `unit-AutoFollowGuidance` koştu (1/1 ctest, 0,00 s). Test programı doğrudan çalıştırılınca: **7 testin 7'si geçti** (`[  PASSED  ] 7 tests.`). İlk derleme ~2 dk 20 s (`build/px4_sitl_test` sıfırdan kuruldu). Test dosyasında derleme uyarısı yok; logdaki uyarılar PX4'ün kendi `fuzztest`/`abseil` bağımlılıklarından. |
| `make px4_sitl_default` | **Geçti** (test dosyası bu derlemeye girmez; yalnızca sürüm başlığı yeniden üretildi). |
| `make px4_fmu-v6c_default` | Çalıştırılmadı: modül kodu değişmedi, test firmware'e girmez (tasks 3.3). Flash Grup 2'deki gibi: 1 936 100 B / 1920 KB (%98,48). |
| `tez/pin/verify_pin.sh --worktree` | Beklenen kırmızı: listede yalnızca onay bekleyen 7 yoldaki dosyalar var (14 dosya, hepsi Grup 1–3'ün); başka yol yok. |

`astyle` / `make check_format` çalıştırılmadı (sürüm sabit değil, çatı kural 4); biçim PX4 stiline elle uyduruldu.

## 5. Çıkan sorunlar

- **Kod hatası bulunmadı.** Testler ilk denemede geçti; guidance koduna dokunulmadı.
- Sorun değil, not: `make tests`, `build/px4_sitl_test` adlı ayrı bir derleme klasörü kurar (ilk seferde ~2 dk). Sonraki koşular yalnızca değişen dosyaları derler.

## 6. Testi yazarken görülen bir davranış (bilgi; spec'e uygun, yeni karar değil)

- **Zaman aşımının başladığı an:** Durum makinesi zaman referansını her durumda `max(son geçerli mesaj, giriş anı)` olarak alır (spec Bölüm 7, Karar A3). Yani moda geçerli bir hedefle girilir ve **girişten sonra hiç yeni mesaj gelmezse**, 0,5 s son mesajdan değil giriş anından sayılır (girişten hemen önce gelen bir mesaj varsa fark en fazla o mesajın yaşı kadar, < 0,5 s). Test 6 bu yüzden son geçerli mesajın girişten sonra geldiği durumu sınar; spec'teki "son geçerli mesaj ──0,5 s──▶ KAYIP_BEKLE" çizelgesi bu durumda birebir doğrulanır. Spec A3'ü genel kural olarak yazdığı için kod değiştirilmedi.

## 7. Sınanmayanlar (bilerek, kısa tutmak için)

Yaş kontrolü (`CHECK_AGE`), konum kontrolü (`CHECK_POSITION`), aşağı bakış ve menzil kontrolleri (`CHECK_DEPRESSION`, `CHECK_RANGE`), alpha-beta filtresi, yaw donması (`AF_YAW_MIN_D`), hedefsiz giriş (A3, 1,5 s) ve KAYIP_BEKLE'den TAKIP'e dönüş birim testinde yok. Bunlar Grup 4'te SITL'de (S4, S5) ölçülür. Grup 2'den açık kalan 5 soru (yanlış adlı mesajın ham kaydı, `perf` sayaçları, uzun boşlukta filtre, EKF sıfırlamasında tutma noktası, sıra no'da "önceki") bu grupta değiştirilmedi ve testler bu konularda bir şey varsaymaz.

## 8. Sonraki grup için notlar

- Grup 4, 5 ve 6'da kod değişirse `make tests TESTFILTER=AutoFollowGuidance` yeniden koşulur (tasks 4.12, 5.4).
- Bir hata düzeltilirse o hatayı yakalayan test bu dosyaya eklenir (`test-writing.md`, "hata düzeltmesine o hatayı yakalayan test eklenir").
