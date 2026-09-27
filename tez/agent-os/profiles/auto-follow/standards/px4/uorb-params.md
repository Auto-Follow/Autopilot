## uORB, parametreler ve MAVLink

### uORB
- Önce mevcut uORB mesajlarını kullan (`msg/`). Yeni mesaj eklemek `msg/` altındaki PX4 dosyalarını değiştirir — kilit listesinde değildir, **önce kullanıcıya sor**.
- Yayınlanan her mesaja `timestamp = hrt_absolute_time()` yazılır.
- Abonelikte `update()` dönüş değeri kontrol edilir; veri tazeliği zaman damgasıyla doğrulanır.

### Parametreler
- Tez parametreleri `TEZ_` ön ekiyle adlandırılır (ör. `TEZ_FOL_KP`); PX4 parametre adları en fazla 16 karakterdir.
- `module.yaml`'da tanımlanır: `description`, `type`, `default`, `min`, `max`, `unit`, `decimal`.
- Kodda `DEFINE_PARAMETERS((ParamFloat<px4::params::TEZ_FOL_KP>) _param_tez_fol_kp)`; `parameter_update` aboneliğiyle güncellenir.
- Kazanç ve eşik değerleri koda gömülmez, parametre olur.

### MAVLink
- `mavlink` bir submodule'dür ve kilitlidir — **yeni MAVLink mesajı/dialect eklenmez**.
- Yardımcı bilgisayarla iletişim PX4 v1.17.0'ın zaten desteklediği mesajlarla yapılır. Hangi mesajların kullanılacağı (ICD) **henüz kesinleşmedi**; ICD'yi varsayma, kullanıcıya sor.
