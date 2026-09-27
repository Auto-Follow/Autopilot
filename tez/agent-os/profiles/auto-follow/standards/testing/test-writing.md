## Test yazımı

Test piramidi: önce hızlı birim testleri, sonra SITL (Gazebo) senaryoları, en son gerçek uçuş. **Gerçek uçuşa, aynı davranış SITL'de doğrulanmadan çıkılmaz.**

### PX4 / C++
- Saf hesaplama (kontrol yasası, filtre, ICD çözümleme) donanımdan bağımsız sınıf/fonksiyonlara ayrılır ve GoogleTest ile test edilir:
  - `px4_add_unit_gtest(SRC FooTest.cpp LINKLIBS ...)` — uORB/parametre gerektirmeyen testler
  - `px4_add_functional_gtest(...)` — uORB/parametre altyapısı gereken testler
  - Çalıştırma: `make tests TESTFILTER=<isim>`
- Her kontrol yasası için en az: nominal girdi, sınır değerler, NaN/Inf girdi, zaman aşımı senaryosu.

### SITL (Gazebo Harmonic)
- Her uçuş davranışı `make px4_sitl gz_<model>` ile doğrulanır; mümkünse `HEADLESS=1` ile otomatikleştirilir.
- Testin çıktısı ULog'dur; değerlendirme `pyulog` ile script'le yapılır (ör. takip hatası, aşım, tepki süresi). Göz kararı "iyi uçtu" test sayılmaz.
- Test sonrası SITL parametre dosyası (`build/px4_sitl_default/rootfs/parameters*.bson`) sıfırlanır; testler birbirinin parametresini devralmaz.

### Python (yardımcı bilgisayar)
- `pytest`; görüntü işleme fonksiyonları kayıtlı örnek karelerle, MAVLink paketleme/çözümleme gidiş-dönüş testiyle sınanır.
- Donanım (kamera, seri port) testlerde taklit edilir; testler donanım olmadan çalışmalı.

### Genel
- Test, davranışı test eder; iç uygulama detayını değil.
- Yeni özellik testsiz birleştirilmez; hata düzeltmesine o hatayı yakalayan test eklenir.
