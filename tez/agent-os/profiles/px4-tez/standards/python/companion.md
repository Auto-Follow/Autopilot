## Yardımcı bilgisayar (Raspberry Pi 5) Python kodu

Bu kod `algan-vision` reposunda yaşar.


- Aynı kod hem simülasyonda (laptop) hem Pi'de çalışır; fark sadece **konfigürasyonda**:
  - Görüntü kaynağı: Gazebo kamera topic'i (`gz.transport13`) ↔ Pi kamerası
  - MAVLink bağlantısı: `udp:127.0.0.1:14540` (SITL) ↔ `/dev/ttyAMA0` (TELEM2)
  - Bu seçimler komut satırı argümanı veya YAML config ile yapılır; kodda `if simulation:` dalları dağıtılmaz.
- Bağımlılıklar `requirements/` altındaki sabit sürümlerdir: `common.txt` (ortak), `laptop.txt`, `pi.txt`, `ci.txt`. Yeni paket sürümüyle eklenir ve **Python 3.11 ile uyumlu** olmalıdır (ör. NumPy 2.5+ 3.12 istediği için 2.4.6'da sabit).
- Kod Python 3.11 ile uyumlu yazılır (`ruff` hedefi `py311`); 3.12'ye özgü sözdizimi kullanılmaz. CI iki sürümü de test eder.
- Laptop ortamı: repo içinde `.venv` (Gazebo Python bağları için `--system-site-packages`).
- Algılama → karar → gönderim döngüsü zamanlanır; kare başına işlem süresi loglanır. Hedef hızı/gecikme bütçesi aşılırsa bu açıkça raporlanır.
- Pi'de `opencv-python-headless` kullanılır (ekran yok); laptopta `opencv-python`.
- Blocking I/O (seri port, kamera) ana işleme döngüsünü kilitlememelidir.
