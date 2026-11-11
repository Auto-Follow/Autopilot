# Kabul Koşuları (SITL)

Her SITL kabul koşusunun özet sayıları ve kod sürümü. Video ve ULog repoya girmez (kural 9); koşu klasörleri
`build/px4_sitl_tez/tez_kabul/` ve `tez/sim/sonuclar/` altında, git dışında kalır. Ayrıntılar ilgili
`gorev-grubu-<NN>.md` dosyasındadır.

| Tarih | Grup | Koşu | Sonuç | Özet sayılar | Kod | Süre |
|---|---|---|---|---|---|---|
| 11.11.2026 | 1 | `tez/sim/araclar/f0_kabul.sh` (stok 4001, takip yok) | GEÇTİ | Kamera 2304×1296, 30.4 kare/sim-s, RTF 1.00, fx 1773.9 px; `SYS_AUTOSTART 4001`; 15/15 başlangıç parametresi PX4'te aynı; "Hold" + "Follow Target" AVAILABLE_MODES'ta; Hold'da 15 s, en büyük sapma yatay 0.05 m / dikey 0.07 m; iniş + disarm; temiz kapanış | `6ddbe1e45a` + Görev grubu 1 değişiklikleri (commit'ten önce) | 1 dk 10 s |
| 11.11.2026 | 1 | `tez/sim/araclar/f1_kabul.sh` (`yuruyen_insan` ×2, `--dogrula`, takip kaynağı `yok`) | GEÇTİ | Hedef doğrulama farkı en fazla 0.13 m / 0.13 m (sınır 0.30); iki koşu arası 0.000 m (sınır 0.15); dron 29.8 s'de Hold'da hazır; kadrajda kalma 0.44 / 0.44; en uzun kayıp 10.6 / 10.5 s; ortalama yükseklik 9.99 / 9.97 m | `6ddbe1e45a` + Görev grubu 1 değişiklikleri (commit'ten önce) | 3 dk 41 s |
