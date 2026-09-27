## Yardımcı bilgisayar (Raspberry Pi 5) Python kodu

Bu kod `Vision` reposunda yaşar.

- Hedefler: laptop (Ubuntu 24.04, Python 3.12) ve Raspberry Pi 5 (Raspberry Pi OS 64-bit masaüstlü, Debian 13 Trixie, Python 3.13).
- Aynı kod hem simülasyonda (laptop) hem Pi'de çalışır; fark sadece **konfigürasyonda**:
  - Görüntü kaynağı: Gazebo kamera topic'i (`gz.transport13`) ↔ Pi kamerası
  - MAVLink bağlantısı: `udp:127.0.0.1:14540` (SITL) ↔ `/dev/ttyAMA0` (TELEM2)
  - Bu seçimler komut satırı argümanı veya YAML config ile yapılır; kodda `if simulation:` dalları dağıtılmaz.
- Bağımlılıklar `requirements/` altındaki sabit sürümlerdir: `common.txt` (ortak), `laptop.txt`, `pi.txt`, `ci.txt`. Yeni paket sürümüyle eklenir ve hem **Python 3.12/x86_64** hem **Python 3.13/aarch64** için hazır paketi olmalıdır.
- Kod Python 3.12 ile uyumlu yazılır (`ruff` hedefi `py312`); 3.13'e özgü sözdizimi kullanılmaz. CI 3.12 ve 3.13'ü test eder.
- Laptop ve Pi ortamı: repo içinde `.venv`, `--system-site-packages` ile (laptopta Gazebo Python bağları, Pi'de picamera2 apt'den gelir).
- Pi kamerası `picamera2` ile okunur; apt paketi `python3-picamera2` (pip ile kurulmaz).
- Algılama → karar → gönderim döngüsü zamanlanır; kare başına işlem süresi loglanır. Hedef hızı/gecikme bütçesi aşılırsa bu açıkça raporlanır.
- Pi'de `opencv-python-headless` kullanılır (uçuşta ekran yok); laptopta `opencv-python`.
- Blocking I/O (seri port, kamera) ana işleme döngüsünü kilitlememelidir.
