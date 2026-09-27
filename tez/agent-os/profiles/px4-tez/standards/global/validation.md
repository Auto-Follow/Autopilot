## Girdi doğrulama

- Yardımcı bilgisayardan Pixhawk'a gelen her alan kullanılmadan önce doğrulanır:
  - `PX4_ISFINITE()` ile NaN/Inf kontrolü
  - Tanımlı aralık kontrolü (ör. normalize değerler −1…1, güven 0…1)
  - Sıra numarası/zaman damgası ile tekrar veya eski mesaj kontrolü
- Geçersiz mesaj **atılır**, sayılır ve (hız sınırlı olarak) loglanır; kontrol yasasına asla girmez.
- Kontrol çıkışları (hız/ivme setpoint'leri) parametrelerle tanımlı sınırlara kırpılır (saturation).
- PX4 parametreleri `module.yaml` içinde `min`/`max` ile sınırlandırılır.
- Python tarafında gönderilmeden önce aynı aralık kontrolleri yapılır (iki taraflı doğrulama).
