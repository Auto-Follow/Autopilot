## Yorum kuralları

- Kod **ne** yaptığını kendisi anlatmalı; yorum **neden** yapıldığını açıklar (fiziksel gerekçe, birim, referans, sınırlama).
- Birimler her zaman belirtilir: `// [m/s]`, `// [rad]`, `// [0..1] normalize`. Koordinat sistemi belirsizse yaz (NED / FRD / görüntü düzlemi).
- Kontrol kazançları ve eşik değerleri için kaynağı yaz (tez bölümü, deney, datasheet).
- PX4 parametreleri `module.yaml` içinde açıklamalı tanımlanır: kısa açıklama, birim, min/max, varsayılan.
- Değişiklik günlüğü, tarih, yazar adı veya geçici not ("şimdilik", "düzeltildi") yorumlara yazılmaz — bunlar commit mesajına aittir.
- Yorumlar Türkçe veya İngilizce olabilir; aynı dosyada tutarlı kal.
