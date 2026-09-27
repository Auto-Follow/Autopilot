## Proje kuralları

### Repolar
| Repo | İçerik |
|---|---|
| `Algan-Otopilot/px4-autopilot-tez` | PX4 v1.17.0 (kilitli), tez PX4 modülleri, SITL airframe'leri, Gazebo |
| `Algan-Otopilot/algan-vision` | Raspberry Pi 5 Python kodu: görüntü işleme, Pixhawk iletişimi |

Bir özellik iki repoyu birden etkiliyorsa (ör. ICD), her repoda ayrı PR açılır ve PR'lar birbirine link verir.

### Sürüm kilidi (en önemli kural — `px4-autopilot-tez`)
- PX4 **v1.17.0**'da kilitlidir. `tez/pin/verify_pin.sh` her PR'da CI'da çalışır.
- **Asla:** upstream PX4'ten `pull`/`merge`, `git submodule update --remote`, submodule commit'i değiştirme, `.gitmodules` düzenleme.
- Değişikliğe izin verilen PX4 yolları `tez/pin/allowed-paths.txt` içindedir. Bir özellik bu listenin dışındaki bir dosyayı değiştirmeyi gerektiriyorsa **önce kullanıcıya sor**; listeye ekleme ayrı ve açık bir PR ile yapılır.
- Upstream PX4 dosyasını düzenlemek yerine kendi dosyanı ekle (yeni modül, yeni airframe dosyası, yeni model).

### Nereye ne konur
| İçerik | Yer |
|---|---|
| Tez PX4 modülleri | `src/modules/tez_*` (henüz `allowed-paths.txt`'de değil — ilk modülde ayrı PR ile eklenecek) |
| Tez SITL airframe'leri | `ROMFS/px4fmu_common/init.d-posix/airframes/*_gz_x500_tez*` |
| Ortam, kilit, script'ler | `tez/` |
| Pi / görüntü işleme kodu | **`algan-vision` reposu** (PX4 reposuna Pi kodu konmaz) |
| Spec ve ürün dokümanları | `agent-os/` |

### Git ve ekip çalışması
- `main`'e doğrudan push yok; branch → PR → en az 1 onay → squash merge.
- Branch adı: `ozellik/<kisa-ad>`, `duzeltme/<kisa-ad>`, `deney/<kisa-ad>`
- Commit mesajı: ilk satır kısa ve emir kipinde ("tez_follow: hedef zaman aşımı ekle"), gerekirse boş satırdan sonra gerekçe.
- Büyük dosya (log, video, veri seti, model ağırlığı) repoya girmez.
- Sürümü değişebilecek her yeni araç/kütüphane `tez/env/VERSIONS.md`'ye sabit sürümüyle yazılır.
