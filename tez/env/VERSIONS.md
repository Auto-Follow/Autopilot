# Sabit araç sürümleri (Ubuntu 24.04 LTS, x86_64)

Ekipteki herkes **aynı sürümleri** kullanır. Güncelleme ekipçe karar verilmeden yapılmaz.
Kendi makinende kontrol etmek için bu dosyanın sonundaki "Sürüm kontrolü" komutunu çalıştır.

## 1. Mutlaka herkeste aynı olmalı

| Bileşen | Sürüm | Nasıl sabitlendi |
|---|---|---|
| Ubuntu | **24.04 LTS** (24.04.4 veya üstü; .4 / .5 aynı sürümün güncellenmiş hâlidir, fark etmez) | — |
| PX4-Autopilot | **v1.17.0** (`d6f12ad1c4`) | `tez/pin/` + CI |
| QGroundControl | **v5.1.4 (Stable_V5.1)** (x86_64 AppImage, sha256 `1c4ac089abfaac6c6fcd75c7b477ea18da1bc3592cddca5ab1a19c1a13410e65`) | Sürüm adıyla indirilir, otomatik güncelleme yok |
| Gazebo | **Harmonic** — gz-sim 8.15.0, gz-transport 13.6.0, sdformat 14.9.0 | `apt-mark hold` (aşağıda) |
| Gazebo Classic | **kullanılmıyor** (Ubuntu 24.04'te yok) | — |
| Gazebo Python bağları | python3-gz-transport13 13.6.0, python3-gz-msgs10 10.4.0, python3-gz-sim8 8.15.0 | `apt-mark hold` |
| ARM toolchain (Pixhawk firmware) | arm-none-eabi-gcc 13.2.1 (Ubuntu paketi) | `Tools/setup/ubuntu.sh` |
| Python (laptop) | 3.12.3 + `requirements-lock.txt` (PX4 derleme paketleri: empy 3.3.4, pymavlink 2.4.50…) | `pip install --user --break-system-packages -r tez/env/requirements-lock.txt` |
| Pi / görüntü işleme Python | **`Vision` reposunda**: NumPy 2.4.6 · OpenCV 5.0.0.93 · pymavlink 2.4.50 · pyserial 3.5 · PyYAML 6.0.3 (Python 3.11 uyumlu) | `Vision/requirements/*.txt`, repo içi `.venv` |
| Agent OS | **v2.1.1** (`6a6495111e`) — v3 kullanılmıyor; profil `auto-follow` | `tez/env/install-agent-os.sh` (resmi `base-install.sh` main=v3 indirir, kullanmayın) |

## 2. Aynı olması önerilir

| Bileşen | Sürüm | Not |
|---|---|---|
| GCC / CMake / Ninja | 13.3.0 / 3.28.3 / 1.11.1 | Ubuntu 24.04 paketleriyle gelir |
| PlotJuggler | **3.17.2** (x86_64 AppImage, sha256 `6d427ca15f2d937699587eec668d1583e2468bc27bab8aaaee81276ad85941df`) — 4.0 kullanılmıyor | Sürüm adıyla indirilir |
| Laptop analiz/araç Python | `analiz-requirements.txt` (pyulog 1.2.4, MAVProxy 1.8.75, pandas, matplotlib, SciPy…) | venv: `~/Desktop/Projects/Auto-Follow/.venv-tez` |
| Git | 2.43.0 | Ubuntu paketi |

## 3. Kişiden kişiye farklı olabilir (proje sonucunu etkilemez)

| Bileşen | Not |
|---|---|
| NVIDIA sürücüsü | Donanıma bağlı (referans makine: 595.91.07). NVIDIA kartı yoksa gerekmez. |
| VS Code, Claude Code | Kendi kendini günceller. |
| Linux çekirdeği | Ubuntu güncellemeleriyle değişir. |

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
~/Desktop/Projects/Auto-Follow/.venv-tez/bin/pip install -r ~/Desktop/Projects/Auto-Follow/Autopilot/tez/env/analiz-requirements.txt
```

## VS Code eklentileri
```bash
for e in ms-vscode.cpptools ms-vscode.cpptools-extension-pack ms-vscode.cmake-tools twxs.cmake \
  ms-vscode.makefile-tools chiehyu.vscode-astyle dan-c-underwood.arm marus25.cortex-debug \
  editorconfig.editorconfig ms-python.python charliermarsh.ruff redhat.vscode-yaml \
  github.vscode-pull-request-github streetsidesoftware.code-spell-checker anthropic.claude-code; do
  code --install-extension $e; done
```

## Sürüm kontrolü (kendi makinende)
```bash
cd ~/Desktop/Projects/Auto-Follow/Autopilot
lsb_release -ds                                        # Ubuntu 24.04.x LTS
git describe --tags --match 'v[0-9]*' --abbrev=0       # v1.17.0
tez/pin/verify_pin.sh --worktree                       # KILIT SAGLAM (v1.17.0)
gz sim --versions                                      # 8.15.0
arm-none-eabi-gcc --version | head -1                  # 13.2.1
python3 -V                                             # 3.12.3
ls ~/Applications/                                     # QGroundControl-v5.1.4..., PlotJuggler-3.17.2...
grep ^version ~/agent-os/config.yml                    # 2.1.1
```
