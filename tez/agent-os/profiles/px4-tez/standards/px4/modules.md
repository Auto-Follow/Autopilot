## PX4 modül yazımı

- Yeni tez modülü `src/modules/tez_<ad>/` altında, `src/examples/work_item` desenine göre yazılır:
  - `ModuleBase<T>` + `ModuleParams` + `px4::ScheduledWorkItem`
  - Uygun iş kuyruğu (`px4::wq_configurations::...`); yoğun hesaplama yüksek öncelikli kuyruklara konmaz
  - Veri geldikçe çalışacaksa `uORB::SubscriptionCallbackWorkItem`, sabit hızda çalışacaksa `ScheduleOnInterval()`
- Dosyalar: `CMakeLists.txt` (`px4_add_module`, `MODULE_CONFIG module.yaml`), `Kconfig`, `module.yaml`, `.cpp/.hpp`
- Modül, kart dosyasında (`boards/px4/sitl/default.px4board`, `boards/px4/fmu-v6c/default.px4board`) `CONFIG_MODULES_TEZ_<AD>=y` ile açılır — bu dosyalar kilit listesinde değilse önce kullanıcıya sor.
- `print_usage()` içinde modülün ne yaptığı ve komutları açıklanır; `status` komutu anlamlı durum bilgisi basar.
- **Pixhawk 6C sınırları:** FLASH ve RAM kısıtlı. Büyük tablo, ağır kütüphane, `double` yoğun hesap ve dinamik bellekten kaçın. Değişiklikten sonra `make px4_fmu-v6c_default` çıktısındaki bellek kullanımını kontrol et.
- Performans ölçümü için `perf_counter` kullan (döngü süresi, kaçırılan mesaj sayısı).
