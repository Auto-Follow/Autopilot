## Yardımcı bilgisayar (Raspberry Pi 5) Python kodu

- Aynı kod hem simülasyonda (laptop) hem Pi'de çalışır; fark sadece **konfigürasyonda**:
  - Görüntü kaynağı: Gazebo kamera topic'i (`gz.transport13`) ↔ Pi kamerası
  - MAVLink bağlantısı: `udp:127.0.0.1:14540` (SITL) ↔ `/dev/ttyAMA0` (TELEM2)
  - Bu seçimler komut satırı argümanı veya YAML config ile yapılır; kodda `if simulation:` dalları dağıtılmaz.
- Bağımlılıklar `tez/env/companion-requirements.txt`'deki sabit sürümlerdir; yeni paket eklenirse sürümüyle bu dosyaya yazılır.
- Laptop ortamı: `~/Desktop/Projects/Algan-Otopilot/.venv-tez` (Gazebo Python bağları için `--system-site-packages`).
- Algılama → karar → gönderim döngüsü zamanlanır; kare başına işlem süresi loglanır. Hedef hızı/gecikme bütçesi aşılırsa bu açıkça raporlanır.
- Pi'de `opencv-python-headless` kullanılır (ekran yok); laptopta `opencv-python`.
- Blocking I/O (seri port, kamera) ana işleme döngüsünü kilitlememelidir.
