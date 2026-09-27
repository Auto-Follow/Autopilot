## Gazebo Harmonic simülasyonu

- Simülatör **Gazebo Harmonic** (gz-sim 8). Gazebo Classic (`gazebo-classic_*`, `.world`, `libgazebo_*` eklentileri) kullanılmaz ve önerilmez.
- Başlatma: `make px4_sitl gz_x500` (arayüzlü), `HEADLESS=1 make px4_sitl gz_x500` (arayüzsüz/otomatik test).
- PX4'ün model/dünya dosyaları `Tools/simulation/gz` **submodule'ündedir ve kilitlidir** — oraya dosya eklenmez veya düzenlenmez. Tez modeli/dünyası için kilit listesine uygun ayrı bir konum kullanılır; konum henüz kesinleşmedi, kullanıcıya sor.
- Tez modelleri PX4'ün `x500` modelini temel alır (`<include>` ile); kütle/atalet gerçek araç ölçülene kadar standart X500 değerleridir.
- SITL airframe dosyası `ROMFS/px4fmu_common/init.d-posix/airframes/<id>_gz_x500_tez*` biçimindedir ve gerçek araçtaki `4019_x500_v2` kazançlarını paylaşır.
- Laptop hibrit GPU'lu: Gazebo NVIDIA'da çalışmalı (`glxinfo -B` → NVIDIA; `nvidia-smi`'de `gz sim -g`).
