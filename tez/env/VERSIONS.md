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
| QGroundControl | **v5.1.4 (Stable_V5.1)** (x86_64 AppImage, sha256 `1c4ac089abfaac6c6fcd75c7b477ea18da1bc3592cddca5ab1a19c1a13410e65`) | Sürüm adıyla indirilir, otomatik güncelleme yok |
| Agent OS | **v2.1.1** (`6a6495111e`) — v3 kullanılmıyor; profil `px4-tez` | `tez/env/install-agent-os.sh` (resmi `base-install.sh` main=v3 indirir, kullanmayın) |
| PlotJuggler | **3.17.2** (x86_64 AppImage, sha256 `6d427ca15f2d937699587eec668d1583e2468bc27bab8aaaee81276ad85941df`) — 4.0 kullanılmıyor | Sürüm adıyla indirilir |
| Gazebo Python bağları | python3-gz-transport13 13.6.0, python3-gz-msgs10 10.4.0, python3-gz-sim8 8.15.0 | `apt-mark hold` |
| Laptop analiz/araç Python | `analiz-requirements.txt` (pyulog, MAVProxy, pandas, matplotlib, SciPy…) — log analizi ve SITL denemeleri için | venv: `~/Desktop/Projects/Auto-Follow/.venv-tez` |
| Pi / görüntü işleme Python | **`Vision` reposunda** (`requirements/*.txt`, NumPy 2.4.6 — Python 3.11 uyumu) | repo içi `.venv` |

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

## Hibrit ekran kartlı laptop (Intel + NVIDIA): Gazebo'yu NVIDIA'da çalıştırmak
`prime-select query` → `on-demand` iken `~/.bashrc` sonuna:
```bash
export __NV_PRIME_RENDER_OFFLOAD=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
```
Kontrol: `glxinfo -B | grep "OpenGL renderer"` → NVIDIA görünmeli; simülasyon açıkken `nvidia-smi`'de `gz sim -g` listelenmeli.
Oturum X11 olmalı (Ubuntu giriş ekranında "Ubuntu on Xorg").

## Geliştirme araçları (apt)
```bash
sudo apt install -y --no-install-recommends clangd valgrind python3-venv python3-dev \
  python3-gz-transport13 python3-gz-msgs10 python3-gz-sim8 picocom minicom tmux htop \
  rpi-imager v4l-utils ffmpeg gstreamer1.0-tools bear mesa-utils
sudo apt-mark hold python3-gz-transport13 python3-gz-msgs10 python3-gz-sim8
```

## Laptop analiz/araç Python ortamı (Pi kodu için `Vision` reposuna bakın)
```bash
python3 -m venv --system-site-packages ~/Desktop/Projects/Auto-Follow/.venv-tez
~/Desktop/Projects/Auto-Follow/.venv-tez/bin/pip install -r tez/env/analiz-requirements.txt
```

## VS Code eklentileri
```bash
for e in ms-vscode.cpptools ms-vscode.cpptools-extension-pack ms-vscode.cmake-tools twxs.cmake \
  ms-vscode.makefile-tools chiehyu.vscode-astyle dan-c-underwood.arm marus25.cortex-debug \
  editorconfig.editorconfig ms-python.python charliermarsh.ruff redhat.vscode-yaml \
  github.vscode-pull-request-github streetsidesoftware.code-spell-checker anthropic.claude-code; do
  code --install-extension $e; done
```
