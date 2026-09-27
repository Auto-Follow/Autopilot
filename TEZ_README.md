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

### Standartlar: `px4-tez` profili
Ajanlara verilen standartlar web şablonları değil, projeye özel **`px4-tez`** profilinden gelir:
`tez/agent-os/profiles/px4-tez/` (PX4 C++ stili, modül yazımı, uORB/parametre, hata yönetimi, SITL testleri, Gazebo Harmonic, Pi Python kodu).
`default` profilinden miras alır; `frontend/` ve `backend/` standartları hariç tutulur.
Ayrıca iki ajan ezilir (orijinal Agent OS dosyaları değişmez): `implementer` rolü PX4/robotik geliştirici olarak tanımlanır, `implementation-verifier` roadmap'i düzenlemez.

**Standart değiştirmek:** `agent-os/standards/` altındakileri değil, `tez/agent-os/profiles/px4-tez/standards/` altındakileri düzenleyin, sonra yeniden derleyin:
```bash
tez/env/install-agent-os.sh   # ~/agent-os'a v2.1.1 + profil bağlantısı (resmi base-install.sh KULLANMAYIN: main=v3)
echo y | ~/agent-os/scripts/project-install.sh --re-install --profile px4-tez
```
> `--re-install` `agent-os/` klasörünü siler. `agent-os/product/` veya `agent-os/specs/` oluştuktan sonra önce onları yedekleyin.
