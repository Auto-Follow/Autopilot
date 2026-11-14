# Autopilot (PX4 v1.17.0 — kilitli)

Ortak kurallar ve Agent OS düzeni: üst klasördeki çatı repo `../CLAUDE.md` (Claude onu da otomatik okur). Ürün planı: `../agent-os/product/`.

## Bu repoya özel

- **Kilit:** Değişmesine izin verilen yollar `tez/pin/allowed-paths.txt` içindedir. Listede olmayan bir PX4 dosyasını değiştirmen gerekiyorsa **dur ve repo sorumlusuna sor**; listeyi kendiliğinden genişletme.
- Commit/PR öncesi: `tez/pin/verify_pin.sh --worktree`
- Submodule'ler: sadece `git submodule update --init --recursive` (**`--remote` asla**).
- Derleme: `make px4_sitl` (simülasyon), `make px4_fmu-v6c_default` (Pixhawk 6C). Simülasyon: `make px4_sitl gz_x500`.
- **Pixhawk 6C flash'ı ~%98 dolu.** Yeni modül eklemek firmware'i taşırabilir (`region FLASH overflowed`); böyle bir durumda repo sorumlusuna haber ver, modül kapatarak kendiliğinden yer açma.
- Zorunlu CI: `verify-pin`, `derleme-sitl`, `derleme-fmu-v6c`. Kurulum ve sorun giderme: `TEZ_README.md`. Sabit sürümler: `tez/env/VERSIONS.md`.

## Simülasyon ortamı (m06, `tez/sim`)

- Simülasyon, kamera ve montaj, PX4'e giden takip mesajları (`TEZ_LOS`, `FOLLOW_TARGET`), takip modu denemesi veya insan algılama modeliyle ilgili bir işe başlamadan önce **`agent-os/specs/2026-11-10-m06-sim-ortami/EKIP_ICIN_OZET.md`** dosyasını oku (kararlar, ölçümler, varsayımlar, komutlar).
- Kamera ve montaj değerlerinin tek dosyası: `tez/sim/kamera_montaji.yaml`. Oradaki frame/mesaj tanımları ortak spec'ler (m03, m05) yazılana kadar varsayımdır.
