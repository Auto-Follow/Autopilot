# Auto-Follow · PX4 v1.17.0 (Tez)

Holybro X500 V2 + Pixhawk 6C + Raspberry Pi 5 ile auto-follow lisans tezi için PX4 çalışma kopyası.

> **Bu repo PX4 v1.17.0'da kalıcı olarak kilitlidir.** v1.17.x, v1.18 veya upstream `main`'e geçilmeyecek.

## Kurallar
- Bu repo PX4'ün fork'u **değildir**; upstream remote yoktur. `git pull` ile PX4'ten güncelleme **çekmeyin**.
- **Asla** `git submodule update --remote` çalıştırmayın. Doğru komut: `git submodule update --init --recursive`.
- `main`'e doğrudan push yok; her değişiklik PR ile, en az bir ekip üyesinin onayıyla girer.
- CI kırmızıysa PR birleştirilmez: `verify-pin` (sürüm kilidi), `derleme-sitl` ve `derleme-fmu-v6c` (kod iki hedefte de derlenmeli; ~20-30 dk).
- Değişikliğe izin verilen PX4 yolları: `tez/pin/allowed-paths.txt`. Yeni yol eklemek ekipçe konuşulur.
- **`v` ile başlayan tag açmayın** (ör. `v1.0`): PX4 firmware sürümünü `v*` tag'lerinden okur; yanlış tag derlemeyi bozar veya firmware'i yanlış sürümle etiketler. Kendi tag'leriniz `tez-*` ile başlar (ör. `tez-ucus-testi-1`). GitHub'da `v*` tag oluşturma engellidir.

## Kilidi yerelde kontrol etmek
```bash
tez/pin/verify_pin.sh --worktree
```

## Yeni ekip üyesi: kurulum sırası (Ubuntu 24.04)

**Klasör yapısı (herkeste aynı olmalı):**
```
~/Desktop/Projects/Auto-Follow/
├── Autopilot/     ← bu repo (PX4)
├── Vision/        ← Pi / görüntü işleme reposu
└── .venv-tez/     ← laptop log analizi Python ortamı
```

```bash
# 1) Klonla
mkdir -p ~/Desktop/Projects/Auto-Follow && cd ~/Desktop/Projects/Auto-Follow
sudo apt install -y git
git clone --recurse-submodules https://github.com/Auto-Follow/Autopilot.git
git clone https://github.com/Auto-Follow/Vision.git
cd Autopilot

# 2) PX4 bağımlılıkları + Gazebo Harmonic (15-30 dk)
bash Tools/setup/ubuntu.sh
mv Tools/setup/xtensa-esp-elf-*.tar.xz ~/Downloads/ 2>/dev/null   # script'in repoda bıraktığı 112 MB arşiv (commit'lemeyin)

# 3) Kilidi ve derlemeyi doğrula
tez/pin/verify_pin.sh --worktree
make px4_sitl && make px4_fmu-v6c_default
```
4) **Oturumu kapatıp açın** (Pixhawk USB seri port izni — `dialout` grubu).
5) `tez/env/VERSIONS.md`'deki adımlar: Gazebo paketlerini dondurma, QGroundControl 5.1.4, geliştirme araçları, VS Code eklentileri, (hibrit GPU'lu laptopta) NVIDIA ayarı, analiz Python ortamı.
6) Agent OS: `tez/env/install-agent-os.sh`
7) Vision reposu: `../Vision/README.md`

## Sorun giderme
| Belirti | Çözüm |
|---|---|
| Klasörü taşıdıktan/yeniden adlandırdıktan sonra `make px4_fmu-v6c_default` → `Kconfig ... not found` (eski yol) | NuttX kaynak klasörüne üretilen dosyalar eski yolu tutuyor: `(cd platforms/nuttx/NuttX/nuttx && git clean -fdX) && (cd platforms/nuttx/NuttX/apps && git clean -fdX) && rm -rf build` |
| Klasör taşındıktan sonra SITL/Gazebo eski yolu arıyor | `rm -rf build && make px4_sitl` |
| `verify_pin` → "yerel submodule'lar kayitli commit'te degil" | `git submodule update --init --recursive` (**`--remote` DEĞİL**) |
| `git status`'ta `Tools/setup/xtensa-esp-elf-*.tar.xz` | Repo dışına taşıyın; commit'lemeyin (GitHub 100 MB sınırı) |
| `git status` → `modified: platforms/nuttx/NuttX/nuttx (untracked content)` | Pixhawk derlemesinin ürettiği `tools/jlink-nuttx`; zararsız, commit'e girmez, kilidi etkilemez |
| Gazebo çok yavaş / Intel GPU kullanıyor | `tez/env/VERSIONS.md` → NVIDIA PRIME offload bölümü |

## Sık kullanılan komutlar
| Amaç | Komut |
|---|---|
| Simülasyon (standart X500, Gazebo Harmonic) | `make px4_sitl gz_x500` |
| Pixhawk 6C firmware | `make px4_fmu-v6c_default` |
| Gerçek araç airframe | `SYS_AUTOSTART = 4019` (Holybro X500 V2) |

Simülatör **Gazebo Harmonic**'tir (`gz_*` hedefleri). `gazebo-classic_*` hedefleri Ubuntu 24.04'te desteklenmez, kullanmayın.

## Agent OS v2.1.1 (Claude Code ile spec odaklı geliştirme)
Repoda kurulu: `agent-os/` (standartlar, ürün ve spec dokümanları) ve `.claude/` (komutlar + alt ajanlar).
Sürüm **v2.1.1**'de sabittir; v3'e geçilmeyecek.

| Claude Code komutu | Ne yapar |
|---|---|
| `/plan-product` | Ürün misyonu, yol haritası, teknoloji yığını → `agent-os/product/` |
| `/shape-spec` | Bir özelliği soru-cevapla şekillendirir |
| `/write-spec` | Şekillenen özellikten spec yazar → `agent-os/specs/` |
| `/create-tasks` | Spec'ten görev listesi çıkarır |
| `/implement-tasks` | Görevleri uygular |
| `/orchestrate-tasks` | Görevleri alt ajanlara dağıtarak uygular |

### Ekip kuralı: yol haritası
`agent-os/product/roadmap.md`'yi **sadece proje lideri** günceller (PR merge edildikten sonra).
Doğrulama ajanı roadmap'i düzenlemez; tamamlanan maddeleri doğrulama raporunda "önerilen" olarak listeler.

### Standartlar: `auto-follow` profili
Ajanlara verilen standartlar web şablonları değil, projeye özel **`auto-follow`** profilinden gelir:
`tez/agent-os/profiles/auto-follow/` (PX4 C++ stili, modül yazımı, uORB/parametre, hata yönetimi, SITL testleri, Gazebo Harmonic, Pi Python kodu).
`default` profilinden miras alır; `frontend/` ve `backend/` standartları hariç tutulur.
Ayrıca iki ajan ezilir (orijinal Agent OS dosyaları değişmez): `implementer` rolü PX4/robotik geliştirici olarak tanımlanır, `implementation-verifier` roadmap'i düzenlemez.

**Standart değiştirmek:** `agent-os/standards/` altındakileri değil, `tez/agent-os/profiles/auto-follow/standards/` altındakileri düzenleyin, sonra yeniden derleyin:
```bash
tez/env/install-agent-os.sh   # ~/agent-os'a v2.1.1 + profil bağlantısı (resmi base-install.sh KULLANMAYIN: main=v3)
echo y | ~/agent-os/scripts/project-install.sh --re-install --profile auto-follow
```
> `--re-install` `agent-os/` klasörünü siler. `agent-os/product/` veya `agent-os/specs/` oluştuktan sonra önce onları yedekleyin.
