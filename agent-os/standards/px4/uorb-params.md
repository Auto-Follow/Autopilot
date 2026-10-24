## uORB, parametreler ve MAVLink

### uORB
- Önce mevcut uORB mesajlarını kullan (`msg/`). Yeni mesaj eklemek `msg/` altındaki PX4 dosyalarını değiştirir — kilit listesinde değildir, **önce kullanıcıya sor**.
- Yayınlanan her mesaja `timestamp = hrt_absolute_time()` yazılır.
- Abonelikte `update()` dönüş değeri kontrol edilir; veri tazeliği zaman damgasıyla doğrulanır.

### Parametreler
- Parametre adlarını **işi yapan kişi kendi spec'inde belirler**; önceden belirlenmiş bir ön ek yoktur. PX4 kuralları: büyük harf ve alt çizgi, en fazla 16 karakter, mevcut PX4 parametreleriyle çakışmamalı. Aynı modülün parametrelerinde ortak bir ön ek kullanmak okunabilirliği artırır; ön eki modülü yazan kişi seçer.
- `module.yaml`'da tanımlanır: `description`, `type`, `default`, `min`, `max`, `unit`, `decimal`.
- Kodda `DEFINE_PARAMETERS((ParamFloat<px4::params::<PARAM_ADI>>) _param_<param_adi>)`; `parameter_update` aboneliğiyle güncellenir.
- Kazanç ve eşik değerleri koda gömülmez, parametre olur.

### MAVLink
- `mavlink` bir submodule'dür ve kilitlidir — **yeni MAVLink mesajı/dialect eklenmez**.
- Yardımcı bilgisayarla iletişim PX4 v1.17.0'ın zaten desteklediği mesajlarla yapılır. Hangi mesajların kullanılacağı (ICD) **henüz kesinleşmedi**; ICD'yi varsayma, kullanıcıya sor.
