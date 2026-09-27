## Hata yönetimi

### Uçuş kodu (PX4 / C++)
- **Güvenlik önce gelir.** Bir hata durumunda araç tanımlı ve güvenli bir davranışa geçmeli (setpoint üretmeyi bırakma, PX4 failsafe'ine devretme). Belirsiz bir durumda "devam et" varsayılanı yok.
- Dış veri (yardımcı bilgisayardan gelen her şey) **zaman aşımına** tabidir: her mesajın zaman damgası `hrt_absolute_time()` ile kontrol edilir; süre aşılırsa veri geçersiz sayılır.
- C++ istisnaları (exceptions) ve RTTI kullanılmaz; hatalar dönüş değeri veya durum bayrağı ile iletilir.
- Başlatma sonrası dinamik bellek ayırma (`new`, `malloc`, büyüyen `std::vector`) yapılmaz; döngü içinde kesinlikle yok.
- Log: `PX4_INFO` / `PX4_WARN` / `PX4_ERR`. Döngü içinde her çevrimde log basma — durum değiştiğinde bir kez yaz.
- Kullanıcıya/QGC'ye gidecek uyarılar için `events` arayüzünü tercih et.

### Python (yardımcı bilgisayar)
- Seri port / MAVLink bağlantısı koparsa yeniden bağlanmayı dene; programı sessizce çökertme.
- Kamera karesi okunamazsa veya işleme süresi limiti aşarsa "hedef yok" bilgisini gönder — eski veriyi tekrar gönderme.
- Yakalanan istisnaları logla (`logging`), boş `except:` yazma.
