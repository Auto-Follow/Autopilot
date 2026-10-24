## Proje kuralları

### Repolar
| Repo | İçerik |
|---|---|
| `Auto-Follow/Autopilot` | PX4 v1.17.0 (kilitli), tez PX4 modülleri, SITL airframe'leri, Gazebo |
| `Auto-Follow/Vision` | Raspberry Pi 5 Python kodu: görüntü işleme, Pixhawk iletişimi |

Bir özellik iki repoyu birden etkiliyorsa (ör. ICD), her repoda ayrı PR açılır ve PR'lar birbirine link verir.

### Sürüm kilidi (en önemli kural — `Autopilot`)
- PX4 **v1.17.0**'da kilitlidir. `tez/pin/verify_pin.sh` her PR'da CI'da çalışır.
- **Asla:** upstream PX4'ten `pull`/`merge`, `git submodule update --remote`, submodule commit'i değiştirme, `.gitmodules` düzenleme.
- Değişikliğe izin verilen PX4 yolları `tez/pin/allowed-paths.txt` içindedir. Bir özellik bu listenin dışındaki bir dosyayı değiştirmeyi gerektiriyorsa **önce kullanıcıya sor**; listeye ekleme ayrı ve açık bir PR ile yapılır.
- Upstream PX4 dosyasını düzenlemek yerine kendi dosyanı ekle (yeni modül, yeni airframe dosyası, yeni model).
- `v` ile başlayan git tag'i **oluşturma** (PX4 firmware sürümünü `v*` tag'lerinden okur). Tez tag'leri `tez-*` ile başlar.

### Nereye ne konur
| İçerik | Yer |
|---|---|
| Yeni PX4 modülü, parametre, SITL airframe'i, Gazebo modeli | **Adını işi yapan kişi kendi spec'inde belirler**; önceden belirlenmiş bir ad veya ön ek yoktur (PX4 isimlendirme kurallarına uyulur). **Yeri:** PX4 ağacına yeni dosya eklemek kilit listesine (`allowed-paths.txt`) yol eklemeyi gerektirir; gereken yol spec'te yazılır ve PR'da açıkça gösterilir |
| Ortam, kilit, script'ler | `tez/` |
| Pi / görüntü işleme kodu | **`Vision` reposu** (PX4 reposuna Pi kodu konmaz) |
| Spec ve ürün dokümanları | `agent-os/` |

### Git ve ekip çalışması
- `main`'e doğrudan push yok; branch → PR → en az 1 onay → squash merge.
- Branch adı: `ozellik/<kisa-ad>`, `duzeltme/<kisa-ad>`, `deney/<kisa-ad>`
- Commit mesajı: ilk satır kısa ve emir kipinde ("kamera: Gazebo görüntüsünü okuyan fonksiyon ekle"), gerekirse boş satırdan sonra gerekçe.
- Büyük dosya (log, video, veri seti, model ağırlığı) repoya girmez.
- Sürümü değişebilecek her yeni araç/kütüphane `tez/env/VERSIONS.md`'ye sabit sürümüyle yazılır.
