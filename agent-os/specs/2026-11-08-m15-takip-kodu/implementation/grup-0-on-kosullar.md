# Görev grubu 0: Ön koşullar (kod yok; kullanıcı ve ekip)

> **Bu dosya ne için?** M15 (AUTO FOLLOW) işinin kod dışı ön koşullarını ve **ekipten gelecek cevapları** tutar. Cevap geldikçe buraya işlenir. Yeni bir oturumda Claude bu dosyayı okuyunca neyin sorulduğunu, neyin cevaplandığını ve cevap gelince **hangi dosyaların değişeceğini** buradan anlar.
>
> **Son güncelleme:** 2026-11-11 · **Masaüstü kopyası:** `~/Desktop/M15_Vision_Sorulari.pdf` (bu dosyanın PDF'i; dosya güncellenince PDF yeniden üretilir)

| # | Ön koşul | Kim | Durum |
|---|---|---|---|
| 0.1 | 7 kilitli yol için izin talebi (`tasks.md` 0.1 tablosu) | Kullanıcı → Hüseyin | Bekliyor |
| 0.3 | Vision ile `AF_LOS` anlaşması (aşağıdaki sorular) | Kullanıcı → Vision (Yusuf Ortatepe) | **Soruldu, cevap bekleniyor** (2026-11-10) |
| 0.4 | Kamera eğimi → `AF_TRK_ANG` | Kullanıcı → Ahmet (m06) | Bekliyor; SITL'de 30° |
| 0.5 | **Gerçek uçuştan önce Pixhawk'ta `COM_LOW_BAT_ACT` = 3** (kritik seviyede RTL, acil seviyede Land). PX4 varsayılanı 0 = yalnızca uyarı (`commander_params.c:293`); X500 V2 airframe'i değiştirmiyor. Neden: Hold 3 kez reddedilir ve pilot devralmazsa drone süresiz bekler (rapor §5.1 G5.14). Bütün modları korur | Kullanıcı → takım / Hüseyin | Bekliyor (2026-11-11) |

---

## Vision'a sorulanlar (0.3)

**Bağlam:** Pi, Pixhawk'a MAVLink 2 `DEBUG_FLOAT_ARRAY` mesajıyla hedefin yönünü gönderecek (spec Bölüm 2, Varsayım V2). PX4 tarafı ve geçici test göndericisi `tez/sitl/af_los_gonder.py` şu an aşağıdaki **varsayımlarla** yazıldı. MAVLink 2 kullanımı Vision tarafından **doğrulandı** (B1), yeniden sorulmaz.

| # | Soru | Neden önemli | Şu anki varsayım | Cevap (Vision) |
|---|---|---|---|---|
| 1 | **Saniyede kaç mesaj gönderecek?** (kamera fps ve modelin hızı; ortalama ve en düşük) | 0.5 s'lik veri zaman aşımının içinde birkaç mesaj olmalı. Hız düşükse hedef kaybı yanlış tetiklenir. Filtre de bu aralığa göre çalışıyor | 10–30 Hz; test göndericisi **20 Hz** (`--hiz`) | — |
| 2 | **Görüntünün çekilmesinden mesajın gönderilmesine kaç ms geçiyor?** (ortalama ve en kötü) | Yaşı 0.5 s'yi geçen mesaj atılıyor. Gecikme büyükse ileride gecikme telafisi gerekebilir (m13) | Test göndericisi **50 ms** sabit (`--yas`) | — |
| 3 | **Yaşı nereden ölçecek?** Kameranın kare zaman damgasından mı, modelin başladığı andan mı? | Yaş "görüntünün çekildiği an"dan ölçülmeli. Yanlış yerden ölçülürse drone gecikmeyi olduğundan az sanır | Kameranın kare zaman damgası | — |
| 4 | **Mesajın yerleşimi uygun mu?** Adı `AF_LOS`; `data[0..2]` yön x/y/z, `data[3]` yaş (ms), `data[4]` sıra no, `data[5]` hedef var (1) / yok (0) | PX4 kodu tam bu sırayla okuyor. Değişirse iki tarafın da kodu değişir | Bu yerleşim | — |
| 5 | **Yönün eksenleri:** Drone'a göre x ileri, y sağ, z aşağı mı (body FRD)? Kameranın eğik takılma açısı Pi tarafında hesaba katılıyor mu? Uzunluğu 1 mi? | Bir işaret ters olursa drone hedefe değil ters yöne gider. **En kritik soru bu.** Yusuf Ortatepe'nin m10 çalışmasıyla eşlenecek (V6) | Body FRD, montaj açısı Pi'de uygulanmış, birim vektör (V1) | — |
| 6 | **Hedef görünmezken ne yapacak?** "Hedef yok" bayrağıyla göndermeye devam mı edecek, yoksa susacak mı? | Bayrak gelirse drone hemen yerinde bekler. Susarsa 0.5 s geç fark eder. Bayrakla göndermesi daha iyi | İkisi de destekleniyor; bayrakla gönderim tercih edilir | — |
| 7 | **Sıra numarası nasıl?** Her mesajda 1 artıyor mu? Program yeniden başlayınca 1'den mi başlıyor? | Tekrar eden mesaj kontrolü ve Pi'nin yeniden başlaması (karar 5b) buna göre çalışıyor | Her mesajda +1; yeniden başlayınca 1'den (PX4 0.5 s sonra kabul eder) | — |
| 8 | **Birden fazla insan görürse hangisini seçiyor?** Takip sırasında hedef başka birine atlayabilir mi? | Hedef atlarsa drone birden başka yöne döner. Bunu bilmek, logları yorumlamak için önemli | Bilinmiyor | — |
| 9 | **Bağlantı:** Pixhawk'a hangi seri porttan ve hangi hızda (baud) bağlanacak? | Pixhawk'ta port ayarı buna göre yapılır | TELEM2 bekleniyor; baud bilinmiyor | — |

---

## Cevap gelince yapılacaklar (Claude için talimat)

Kullanıcı Vision'ın cevaplarını getirdiğinde:

1. Cevapları yukarıdaki tablonun **"Cevap (Vision)"** sütununa yaz, tarihle. Durum satırını (0.3) güncelle.
2. Her cevabı **şu anki varsayımla karşılaştır**. Aynıysa "varsayım doğrulandı" yaz. Farklıysa etkisini kullanıcıya **seçenek + kanıt + öneri** olarak sun (kararı kullanıcı verir) ve şu dosyalara bak:

   | Soru | Farklı çıkarsa değişebilecek yerler |
   |---|---|
   | 1 (hız) | `tez/sitl/af_los_gonder.py` varsayılan hız; gerekirse `AF_DATA_TOUT` (spec Bölüm 10) |
   | 2–3 (yaş) | `af_los_gonder.py` varsayılan yaş; gecikme telafisi gerekirse m13/m16 notu |
   | 4 (yerleşim) | **PX4 kodu** `src/modules/auto_follow/` (girdi okuma), `af_los_gonder.py`, `spec.md` Bölüm 2, `log-sozlugu.md` Bölüm 2, Varsayım V2 |
   | 5 (eksen) | **PX4 kodu** (geometri, spec Bölüm 3), Varsayım V1/V6; SITL S1–S3 yeniden koşulur |
   | 6 (hedef yok) | Kod değişmez; `spec.md` Bölüm 7 notu |
   | 7 (sıra no) | Kod değişmeyebilir; farklıysa doğrulama kontrolü 4 (spec Bölüm 2) |
   | 8 (hedef seçimi) | Kod değişmez; rapora ve log yorumuna not |
   | 9 (bağlantı) | Pixhawk parametreleri (`MAV_1_CONFIG`, baud); gerçek uçuş hazırlığı notu |

3. Kararları `planning/karar-gunlugu.md`'ye, `requirements.md` Varsayımlar'a, `spec.md` "Varsayımlar"a ve `rapor.md`'ye işle (rapor "Uygulamada verilen kararlar" bölümü dahil).
4. Bu dosyanın PDF'ini masaüstünde yeniden üret: `~/Desktop/M15_Vision_Sorulari.pdf` (yöntem: markdown → HTML → `google-chrome --headless --print-to-pdf`; bkz. Claude hafızası). Spec klasörünü commit et (push yok).

## Belge geçmişi

| Tarih | Ne |
|---|---|
| 2026-11-10 | İlk sürüm: Vision'a sorulan 9 soru, şu anki varsayımlar, cevap gelince yapılacaklar |
| 2026-11-11 | 0.5 eklendi: gerçek uçuştan önce `COM_LOW_BAT_ACT` = 3 |
