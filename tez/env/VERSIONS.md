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
| Raspberry Pi 5 işletim sistemi | **Raspberry Pi OS (64-bit) masaüstlü**, Debian 13 Trixie — imaj `2026-09-15-raspios-trixie-arm64.img.xz` (sha256 `61d95799550aac32788bb3cacc3d471dcc860f8053ce989dec4aecc388b799dd`), Python 3.13.5 | İmaj dosyası Imager'da "Use custom" ile yazılır (listeden seçilmez) |
| Pi / görüntü işleme Python | **`Vision` reposunda**: NumPy 2.4.6 · OpenCV 5.0.0.93 · pymavlink 2.4.50 · pyserial 3.5 · PyYAML 6.0.3 (laptop 3.12 + Pi 3.13) · picamera2 (Pi'de apt) | `Vision/requirements/*.txt`, repo içi `.venv` |
| Sim model paketleri (laptop CPU) | **ultralytics 8.4.174 · torch 2.14.1+cpu · torchvision 0.29.2+cpu** (Python 3.12, x86_64) ve bütün bağımlılıkları; sim'deki algılama ölçütleri bunlara bağlıdır. **Lisans:** Ultralytics AGPL-3.0 (yalnız yerel simde çalışır, dağıtılmaz) | `tez/env/model-requirements.txt`, venv `.venv-tez`, PyTorch CPU dizini (aşağıda); model dosyaları repo dışında (`~/auto-follow-modeller/`, `tez/sim/modeller.yaml`) |
| Agent OS | **v2.1.1** (`6a6495111e`) — v3 kullanılmıyor; profiller `auto-follow` (çatı) + `auto-follow-repo` (Autopilot, Vision) | Çatı repo: `kurulum.sh` → `kurulum/install-agent-os.sh` (resmi `base-install.sh` main=v3 indirir, kullanmayın) |

## 2. Aynı olması önerilir

| Bileşen | Sürüm | Not |
|---|---|---|
| GCC / CMake / Ninja | 13.3.0 / 3.28.3 / 1.11.1 | Ubuntu 24.04 paketleriyle gelir |
| PlotJuggler | **3.17.2** (x86_64 AppImage, sha256 `6d427ca15f2d937699587eec668d1583e2468bc27bab8aaaee81276ad85941df`) — 4.0 kullanılmıyor | Sürüm adıyla indirilir |
| Laptop analiz/araç Python | `analiz-requirements.txt` (pyulog 1.2.4, MAVProxy 1.8.75, pandas, matplotlib, SciPy…) | venv: `~/Desktop/Projects/Auto-Follow/.venv-tez` |
| Git | 2.43.0 | Ubuntu paketi |
| ffmpeg (sim videosu `kosu.mp4`) | **ffmpeg 7:6.1.1-3ubuntu5** (libavcodec60 7:6.1.1-3ubuntu5, libx264-164 2:0.164.3108+git31e19f9-1) | Ubuntu 24.04 paketi (`sudo apt install ffmpeg`, aşağıdaki "Geliştirme araçları"nda); `tez/sim/araclar/video.py` ham BGR kareleri boruyla verir: `libx264`, `yuv420p`, `veryfast`, `crf 23`, `+faststart`. OpenCV'nin `VideoWriter`'ı kullanılmaz (pip OpenCV'de H.264 yok). Kontrol: `dpkg-query -W ffmpeg libx264-164` |
| VLC (videoyu izlemek için) | 3.0.20-3build6 | Ubuntu paketi; `kosu.mp4` bununla denendi. Uçbirimdeki "Timestamp conversion failed" satırları VLC'nin kendisinden gelir. **Canlı yayını (`yayin.sdp`, H.264 RTP) açamaz:** paket live555'siz derlenmiş (`--disable-live555`), SDP'den RTP alamıyor; QGC'siz izlemek için ffmpeg paketinin `ffplay`'i (`ffplay -protocol_whitelist file,udp,rtp -i tez/sim/araclar/yayin.sdp`) ya da `gst-launch-1.0` |
| GStreamer (sim'den QGC'ye canlı video, `senaryo.py --qgc` / `goruntu_yayini.py --qgc`) | **GStreamer 1.24.2**: libgstreamer1.0-0 1.24.2-1ubuntu0.1, gir1.2-gstreamer-1.0 1.24.2-1ubuntu0.1, gir1.2-gst-plugins-base-1.0 1.24.2-1ubuntu0.6, gstreamer1.0-plugins-base 1.24.2-1ubuntu0.6, gstreamer1.0-plugins-good 1.24.2-1ubuntu1.8 (`rtph264pay`, `udpsink`), gstreamer1.0-plugins-ugly 1.24.1-1build1 (`x264enc`, libx264-164 2:0.164.3108+git31e19f9-1), gstreamer1.0-libav 1.24.1-1build1 (`avdec_h264`, yalnız `gst-launch-1.0` ile izlemek için), gstreamer1.0-tools 1.24.2-1ubuntu0.1, gstreamer1.0-x 1.24.2-1ubuntu0.6 (`autovideosink` penceresi); Python bağı **python3-gi 3.48.2-1** (ekip venv'i `--system-site-packages` ile görür) | Ubuntu 24.04 paketleri (aşağıdaki "Canlı video paketleri"); hat: `appsrc` → `queue leaky=downstream` → `videoconvert` → `x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000 key-int-max=15` → `rtph264pay config-interval=1 pt=96 mtu=1400` → `udpsink 127.0.0.1:5600`. Kontrol: `dpkg-query -W python3-gi gir1.2-gstreamer-1.0 gstreamer1.0-plugins-ugly gstreamer1.0-libav` |
| libfuse2t64 (QGC AppImage'ı için) | 2.9.9-8.1build1 | Ubuntu 24.04 paketi; AppImage FUSE 2 ister (yoksa "dlopen(): error loading libfuse.so.2"). Kontrol: `dpkg-query -W libfuse2t64` |

## 3. Kişiden kişiye farklı olabilir (proje sonucunu etkilemez)

| Bileşen | Not |
|---|---|
| NVIDIA sürücüsü | Donanıma bağlı (referans makine: 595.91.07). NVIDIA kartı yoksa gerekmez. |
| AMD ekran kartı (Mesa) | Ubuntu 24.04'ün kendi Mesa sürücüsü; ayrı kurulum yok. Hibrit AMD laptopta Gazebo için `DRI_PRIME=1` (aşağıda). |
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
sudo apt install -y libfuse2t64        # AppImage FUSE 2 ister (yoksa "dlopen(): error loading libfuse.so.2"); 2.9.9-8.1build1
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

## Hibrit ekran kartlı laptop (AMD + AMD, ör. Ryzen iGPU + Radeon RX 6600M): `DRI_PRIME=1`
Mesa varsayılan olarak işlemcinin içindeki kartı (iGPU) seçer; Gazebo orada yavaş çalışır. Ayrık kartı seçmek için
Gazebo'yu (ve QGC'yi) açan terminalde `export DRI_PRIME=1` (kalıcı olsun diye `~/.bashrc` sonuna da yazılabilir):
```bash
echo 'export DRI_PRIME=1            # Gazebo/QGC: ayrık AMD kartı' >> ~/.bashrc   # yeni terminallerde geçerli
glxinfo -B | grep "OpenGL renderer"   # ayrık kart görünmeli, ör. "AMD Radeon RX 6600M (radeonsi, navi23 ...)"
env -u DRI_PRIME glxinfo -B | grep "OpenGL renderer"   # karşılaştırma: iGPU, ör. "AMD Radeon Graphics (... renoir ...)"
```
`glxinfo` `mesa-utils` paketindedir (9.0.0-2, aşağıdaki "Geliştirme araçları"). Aynı terminalden başlatılan
penceresiz koşular (`--ekransiz`, kabul testleri) da bu değişkeni devralır. Referans makinenin (Ryzen 7 5800H +
RX 6600M) `~/.bashrc`'sinde bu satır vardır.

## Geliştirme araçları (apt)
```bash
sudo apt install -y --no-install-recommends clangd valgrind python3-venv python3-dev \
  python3-gz-transport13 python3-gz-msgs10 python3-gz-sim8 picocom minicom tmux htop \
  rpi-imager v4l-utils ffmpeg gstreamer1.0-tools bear mesa-utils
sudo apt-mark hold python3-gz-transport13 python3-gz-msgs10 python3-gz-sim8
```

### Canlı video paketleri (sim → QGC, `--qgc`) ve QGC AppImage
Sürümleri yukarıdaki tabloda ("Aynı olması önerilir"); Ubuntu 24.04'ün kendi paketleridir:
```bash
sudo apt install -y --no-install-recommends python3-gi gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 \
  gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly gstreamer1.0-libav \
  gstreamer1.0-tools gstreamer1.0-x libfuse2t64
dpkg-query -W python3-gi gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-tools libfuse2t64
~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; Gst.init(None); print(Gst.version_string(), all(Gst.ElementFactory.find(e) for e in ('x264enc', 'rtph264pay', 'avdec_h264')))"   # GStreamer 1.24.2 True
```
`gstreamer1.0-plugins-bad` (`netsim`, Wi-Fi benzetimi) Faz B'de gerekir; şimdilik kurulmaz.

## Laptop analiz/araç Python ortamı (Pi kodu için `Vision` reposuna bakın)
```bash
python3 -m venv --system-site-packages ~/Desktop/Projects/Auto-Follow/.venv-tez
~/Desktop/Projects/Auto-Follow/.venv-tez/bin/pip install -r ~/Desktop/Projects/Auto-Follow/Autopilot/tez/env/analiz-requirements.txt
```

## Sim model paketleri (laptop CPU: ultralytics + torch)
Simülasyondaki insan algılayıcı (`tez/sim/araclar/algilama.py`) için; yalnız laptop (Ubuntu 24.04, Python 3.12, x86_64).
Pi'ye kurulmaz (orada Hailo, yol haritası m02/m07), CI'da gerekmez (birim testleri torch'suz çalışır).
Önce yukarıdaki "Laptop analiz/araç Python ortamı" kurulur, sonra:
```bash
~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python -m pip install \
  -r ~/Desktop/Projects/Auto-Follow/Autopilot/tez/env/model-requirements.txt \
  --extra-index-url https://download.pytorch.org/whl/cpu
~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python -m pip check        # No broken requirements found.
```
- `torch==2.14.1+cpu` / `torchvision==0.29.2+cpu` yalnız PyTorch CPU dizininde vardır (`+cpu` sürümü PyPI'da olamaz);
  CUDA'lı paketler (birkaç GB) inmez. torchvision 0.29 torch 2.14 için derlenmiştir; pip torch 2.15'i de kabul ederdi, seçilmedi.
- `ultralytics==8.4.174`: v0.2 model dosyasını kaydeden sürüm. OpenCV, `analiz-requirements.txt`'teki **5.0.0.93** kalır.
- Her bağımlılık tek bir dosyada sabittir: numpy, matplotlib, psutil, sympy, packaging… `requirements-lock.txt`'te;
  opencv-python `analiz-requirements.txt`'te; geri kalanı (Ubuntu'nun apt ile verdiği pillow 10.2.0, PyYAML 6.0.1,
  requests 2.31.0 dahil) `model-requirements.txt`'te. Ekip venv'inde pip yalnız yeni paketleri kurar; torch'un istediği
  `setuptools` 80.10.2 ve anyio'nun istediği `typing_extensions` 4.16.0 venv içinde apt sürümlerinin (68.1.2, 4.10.0)
  önüne geçer, apt dosyaları değişmez.
- **Lisans:** Ultralytics AGPL-3.0'dır. Model yalnız yerel simde çalıştırılır, dağıtılmaz.
- Kod ultralytics'i otomatik indirme, analitik ve ayar dosyası yazımı kapalı açar (`YOLO_OFFLINE=1`,
  `YOLO_AUTOINSTALL=0`, ayar dosyası geçici bir klasörde; `~/.config/Ultralytics` oluşmaz). ultralytics'i kendiniz
  `import` etmeyin, `yolo` komutunu çalıştırmayın: o zaman ayar dosyası `~/.config/Ultralytics`'e yazılır ve internete
  bakılır. Modeli denemek için: `tez/sim/araclar/model_dene.py`.
- Model dosyaları repoya girmez (kural 9): `~/auto-follow-modeller/`; bilinen dosyalar ve sha256 özetleri
  `tez/sim/modeller.yaml`'dadır. `tez/sim/kur.sh` sonunda klasörü bu kayıtlara göre denetler ve her dosyanın sha256'sını
  yazar (indirmez; eksik dosya uyarıdır ve nereden alınacağını söyler). Yalnız denetim:
  `~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/algilama.py`.
  - `person_detection_model_v0.2.pt` (sim'in varsayılan modeli; Yusuf Ortatepe): sha256
    `c5f6838be50c2c09ca788e97381b68567f0df3f20e430905142ce88f8abaa440`, 22 525 930 bayt; geçici kaynak Vision
    `model-training` dalı, commit `ebff718` (ortak depolama yeri kararı bekliyor).
  - `yolov8s.pt` (kıyas için stok COCO modeli, AGPL-3.0): ultralytics 8.4.174'ün kendisinin kullanacağı adres
    `https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s.pt` (`ultralytics/utils/downloads.py`,
    `attempt_download_asset(release="v8.4.0")`). Elle indirilir (15.11.2026): sha256
    `1f47a78bf100391c2a140b7ac73a1caae18c32779be7d310658112f7ac9aa78a`, 22 588 772 bayt (`modeller.yaml`).
- Bu dosyadaki model sürümleri `model-requirements.txt` ile aynıdır (15.11.2026'da ekip venv'inde denetlendi: üç
  dosyadaki her sabit sürüm kurulu olanla aynı; `pip check` temiz).

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
~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python -c "from importlib.metadata import version as v; print(v('torch'), v('torchvision'), v('ultralytics'))"   # 2.14.1+cpu 0.29.2+cpu 8.4.174
sha256sum ~/auto-follow-modeller/person_detection_model_v0.2.pt   # c5f6838b... (tez/sim/modeller.yaml)
~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python -m pip check     # No broken requirements found.
~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/algilama.py   # model klasörü: TAMAM / EKSİK satırları
dpkg-query -W libfuse2t64 ffmpeg gstreamer1.0-plugins-ugly python3-gi   # 2.9.9-8.1build1, 7:6.1.1-3ubuntu5, 1.24.1-1build1, 3.48.2-1
glxinfo -B | grep "OpenGL renderer"                    # hibrit laptop: ayrık kart (NVIDIA ya da DRI_PRIME=1 ile AMD)
```
