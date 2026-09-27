# Sabit araç sürümleri (Ubuntu 24.04.4 LTS, x86_64)

Ekipteki herkes **aynı sürümleri** kullanır. Güncelleme ekipçe karar verilmeden yapılmaz.

| Bileşen | Sürüm | Nasıl sabitlendi |
|---|---|---|
| PX4-Autopilot | **v1.17.0** (`d6f12ad1c4`) | `tez/pin/` + CI |
| Gazebo | **Harmonic** — gz-sim 8.15.0, gz-transport 13.6.0, sdformat 14.9.0 | `apt-mark hold` (aşağıda) |
| Gazebo Classic | **kullanılmıyor** (Ubuntu 24.04'te yok) | — |
| ARM toolchain | arm-none-eabi-gcc 13.2.1 (Ubuntu paketi) | `Tools/setup/ubuntu.sh` |
| GCC / CMake | 13.3.0 / 3.28.3 | Ubuntu 24.04 paketleri |
| Python | 3.12.3 + `requirements-lock.txt` | `pip install --user --break-system-packages -r tez/env/requirements-lock.txt` |
| QGroundControl | **v5.1.4** (x86_64 AppImage, sha256 `1c4ac089abfaac6c6fcd75c7b477ea18da1bc3592cddca5ab1a19c1a13410e65`) | Sürüm adıyla indirilir, otomatik güncelleme yok |

## Gazebo paketlerini dondurmak
```bash
sudo apt-mark hold $(dpkg-query -W -f='${db:Status-Abbrev} ${Package}\n' \
  | awk '$1=="ii" && $2 ~ /^(gz-|libgz-|libsdformat14|python3-gz|python3-sdformat)/{print $2}')
```

## QGroundControl
```bash
mkdir -p ~/Applications && cd ~/Applications
curl -L -o QGroundControl-v5.1.4-x86_64.AppImage \
  https://github.com/mavlink/qgroundcontrol/releases/download/v5.1.4/QGroundControl-x86_64.AppImage
echo "1c4ac089abfaac6c6fcd75c7b477ea18da1bc3592cddca5ab1a19c1a13410e65  QGroundControl-v5.1.4-x86_64.AppImage" | sha256sum -c
chmod +x QGroundControl-v5.1.4-x86_64.AppImage
sudo usermod -aG dialout $USER && sudo apt remove -y modemmanager   # sonra oturumu kapat/aç
```
