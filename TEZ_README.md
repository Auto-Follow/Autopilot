# Algan-Otopilot · PX4 v1.17.0 (Tez)

Holybro X500 V2 + Pixhawk 6C + Raspberry Pi 5 ile auto-follow lisans tezi için PX4 çalışma kopyası.

> **Bu repo PX4 v1.17.0'da kalıcı olarak kilitlidir.** v1.17.x, v1.18 veya upstream `main`'e geçilmeyecek.

## Kurallar
- Bu repo PX4'ün fork'u **değildir**; upstream remote yoktur. `git pull` ile PX4'ten güncelleme **çekmeyin**.
- **Asla** `git submodule update --remote` çalıştırmayın. Doğru komut: `git submodule update --init --recursive`.
- `main`'e doğrudan push yok; her değişiklik PR ile, en az bir ekip üyesinin onayıyla girer.
- CI (`PX4 v1.17.0 surum kilidi`) kırmızıysa PR birleştirilmez.
- Değişikliğe izin verilen PX4 yolları: `tez/pin/allowed-paths.txt`. Yeni yol eklemek ekipçe konuşulur.

## Kilidi yerelde kontrol etmek
```bash
tez/pin/verify_pin.sh --worktree
```

## Klonlama (ekip üyeleri)
```bash
git clone --recurse-submodules https://github.com/Algan-Otopilot/px4-autopilot-tez.git
cd px4-autopilot-tez
bash Tools/setup/ubuntu.sh        # Ubuntu 24.04: derleyiciler + Gazebo Harmonic
tez/pin/verify_pin.sh --worktree
```

## Sık kullanılan komutlar
| Amaç | Komut |
|---|---|
| Simülasyon (standart X500, Gazebo Harmonic) | `make px4_sitl gz_x500` |
| Pixhawk 6C firmware | `make px4_fmu-v6c_default` |
| Gerçek araç airframe | `SYS_AUTOSTART = 4019` (Holybro X500 V2) |

Simülatör **Gazebo Harmonic**'tir (`gz_*` hedefleri). `gazebo-classic_*` hedefleri Ubuntu 24.04'te desteklenmez, kullanmayın.
