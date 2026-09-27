## Teknoloji yığını

Kesinleşmiş olanlar düz, henüz kesinleşmemiş olanlar **(taslak)** olarak işaretlidir. Taslak bir maddeye dayanan bir karar vermeden önce kullanıcıya sor.

### Araç ve donanım
- **Gövde:** Holybro X500 V2 (quadrotor X)
- **Uçuş kontrolcüsü:** Pixhawk 6C — firmware hedefi `px4_fmu-v6c_default`, airframe `SYS_AUTOSTART=4019`
- **Yardımcı bilgisayar:** Raspberry Pi 5 — Pixhawk TELEM2'ye seri hatla bağlı

### Uçuş yazılımı
- **PX4-Autopilot v1.17.0 — kalıcı olarak kilitli.** Başka bir PX4 sürümüne, upstream `main`'e veya v1.18'e geçiş önerme.
- Dil: C++ (PX4 modülleri), NuttX RTOS (donanım), POSIX (SITL)
- Derleme: `make` + CMake + Ninja; donanım için `arm-none-eabi-gcc` 13.2.1

### Simülasyon
- **Gazebo Harmonic** (gz-sim 8.15.0) — `make px4_sitl gz_<model>`
- Gazebo Classic **kullanılmaz** (Ubuntu 24.04'te yok); `gazebo-classic_*` hedeflerini önerme.

### Yardımcı bilgisayar / görüntü işleme
- Repo: `Vision`. Python **3.11+** (Pi işletim sistemi henüz kesinleşmedi: Raspberry Pi OS = 3.11, Ubuntu = 3.12; kod iki sürümde de çalışmalı)
- OpenCV 5.0, NumPy 2.4.6, pymavlink — sabit sürümler `Vision/requirements/*.txt`
- Pixhawk ile iletişim: MAVLink **(taslak — mesaj seti/ICD henüz kesinleşmedi)**
- ROS 2 **şu an kullanılmıyor (taslak karar)**; ROS 2 bağımlılığı ekleme.

### Yer istasyonu ve analiz
- QGroundControl v5.1.4 (Stable_V5.1)
- Log analizi: ULog + pyulog, PlotJuggler 3.17.2

### Geliştirme ortamı
- Ubuntu 24.04 LTS, VS Code, Claude Code + Agent OS v2.1.1
- Tüm sabit sürümler: `tez/env/VERSIONS.md`
