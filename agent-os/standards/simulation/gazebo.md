## Gazebo Harmonic simülasyonu

- Simülatör **Gazebo Harmonic** (gz-sim 8). Gazebo Classic (`gazebo-classic_*`, `.world`, `libgazebo_*` eklentileri) kullanılmaz ve önerilmez.
- Başlatma: `make px4_sitl gz_x500` (arayüzlü), `HEADLESS=1 make px4_sitl gz_x500` (arayüzsüz/otomatik test).
- PX4'ün model/dünya dosyaları `Tools/simulation/gz` **submodule'ündedir ve kilitlidir** — oraya dosya eklenmez veya düzenlenmez. Tez modeli/dünyası için kilit listesine uygun ayrı bir konum kullanılır; konum henüz kesinleşmedi, kullanıcıya sor.
- Simülasyon kamerası için hazır `gz_x500_mono_cam` mı yoksa özel bir model mi kullanılacağı yol haritası madde 6'da karara bağlanır (henüz seçilmedi; varsayma). Özel model veya airframe dosyası yapılırsa **adını işi yapan kişi kendi spec'inde belirler**; önceden belirlenmiş bir ad yoktur. Gerçek araç ölçülene kadar kütle/atalet standart X500 değerleridir.
- Laptop hibrit GPU'lu: Gazebo NVIDIA'da çalışmalı (`glxinfo -B` → NVIDIA; `nvidia-smi`'de `gz sim -g`).
