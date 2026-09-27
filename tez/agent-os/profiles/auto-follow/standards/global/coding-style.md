## Kod stili

### C++ (PX4 içindeki kod)
- **PX4 stiline uy, kendi stilini getirme.** Biçim `Tools/astyle/astylerc` ile belirlenir: tab girinti (8), Linux brace stili, satır en fazla 140 karakter, tek satırlık `if` gövdelerinde de süslü parantez.
- Commit öncesi: `make format` (düzeltir) veya `make check_format` (kontrol eder).
- İsimlendirme (PX4 geleneği):
  - Sınıflar `CamelCase` (`TezFollow`), fonksiyonlar ve değişkenler `snake_case`
  - Özel üye değişkenler `_` ön ekli (`_vehicle_status_sub`, `_param_tez_kp`)
  - Sabitler `UPPER_SNAKE_CASE` veya `static constexpr`
  - Modül klasörü ve komut adı `snake_case` (`src/modules/tez_follow`)
- Yeni kod, benzer PX4 modüllerinin (ör. `src/examples/work_item`) desenini takip eder.
- Fonksiyonlar kısa ve tek amaçlı olsun; ölü kod ve yorum satırına alınmış blok bırakma.

### Python (yardımcı bilgisayar ve araçlar)
- PEP 8; biçim ve lint: `ruff format` + `ruff check`
- Tip ipuçları (type hints) zorunlu; herkese açık fonksiyonlarda docstring
- Modül/fonksiyon `snake_case`, sınıf `CamelCase`, sabit `UPPER_SNAKE_CASE`

### Genel
- Anlamlı isimler; tek harfli değişken sadece döngü sayacı veya matematik formülünde
- Kopyala-yapıştır yerine ortak fonksiyon (DRY)
- Geriye dönük uyumluluk kodu yazma (proje v1.17.0'da sabit)
