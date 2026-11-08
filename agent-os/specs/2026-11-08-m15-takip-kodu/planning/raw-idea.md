# M15 — Body frame hedef vektöründen PWM'e: PX4 takip kodu

Görev: https://github.com/Auto-Follow/Auto-Follow/issues/6 (yol haritası madde 15; devamı 13 ve 16). Son teslim 2026-11-15. Repo: Autopilot. Dal: `ozellik/m15-takip-kodu`.

- Girdi body frame'deki hedef vektörüdür. Sıfırdan kontrolcü yazılmayacak; yalnızca **istenen durumu üreten guidance katmanı** yazılacak. Hız, konum, attitude ve rate kontrolü, mikser ve PWM çıkışı PX4'ün kendi zincirinde kalır.
- Zincir: FC'ye gelen body FRD LOS → guidance kodu (frame dönüşümü, hedef konumu, guidance) → PX4 setpoint → PX4 kontrol zinciri → PWM.
- Dahil: entegrasyon kararı ve gerekçesi (değerlendirilen seçenekler dahil); guidance kodu; SITL'de sentetik vektörle drone'un tepki verdiğini gösteren test (ne verildi, drone ne yaptı, ULog adı); geçersiz/eski veri için basit güvenli davranış.
- Hariç: ayrıntılı failsafe ve mod çıkış akışının tamamı (m16); nihai guidance yasası ve ayarı (m13); Pi tarafı ve ICD.
- Bitti sayılması için (kabul kriterleri, issue #6): spec klasöründe şemalar (`planning/visuals/`), PX4'te neyin nereye bağlandığı ve neden, test sonucu (ne verildi, drone ne yaptı, log adı); kod `make px4_sitl` ile derleniyor; CI `verify-pin`, `derleme-sitl`, `derleme-fmu-v6c` yeşil; PX4'e yeni dosya eklenirse yolu PR'da gösteriliyor.
- Varsayım: girdi body FRD frame'de hedef yönünü gösteren LOS birim vektörü; mesafe düz dünya kabulü ve irtifadan. Mesaj tipi/frekans/zaman damgası ICD'de (madde 3–5) belirlenecek. Eksenler Yusuf Ortatepe'nin m10 çalışmasıyla eşlenecek.
