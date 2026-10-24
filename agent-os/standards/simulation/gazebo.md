## Gazebo Harmonic simülasyonu

- Simülatör **Gazebo Harmonic** (gz-sim 8). Gazebo Classic (`gazebo-classic_*`, `.world`, `libgazebo_*` eklentileri) kullanılmaz ve önerilmez.
- Başlatma: `make px4_sitl gz_x500` (arayüzlü), `HEADLESS=1 make px4_sitl gz_x500` (arayüzsüz/otomatik test).
- PX4'ün model/dünya dosyaları `Tools/simulation/gz` **submodule'ündedir ve kilitlidir** — oraya dosya eklenmez veya düzenlenmez. Tez modeli/dünyası için kilit listesine uygun ayrı bir konum kullanılır; konum henüz kesinleşmedi, kullanıcıya sor.
- Simülasyon kamerası için hazır `gz_x500_mono_cam` mı kullanılacağı yoksa özel model mi yapılacağı, özel modelin adı ve airframe dosyası **henüz karara bağlanmadı**; varsayma, repo sorumlusuna sor. Gerçek araç ölçülene kadar kütle/atalet standart X500 değerleridir.
- Laptop hibrit GPU'lu: Gazebo NVIDIA'da çalışmalı (`glxinfo -B` → NVIDIA; `nvidia-smi`'de `gz sim -g`).
