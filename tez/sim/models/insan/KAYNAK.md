# İnsan hedef modeli

Gerçek bir insan hareket kaydıyla canlandırılmış, kıyafetli bir insan (1.71 m, genç erkek, gömlek + kot + ayakkabı).
`meshes/` git'e girmez: `tez/sim/kur.sh` → `tez/sim/insan/uret.sh` indirip üretir (indirmeler sha256 kontrollü,
`~/.cache/auto-follow-insan` içinde saklanır; üretim ~10 s).

| Parça | Kaynak | Lisans |
|---|---|---|
| İnsan, deri, saç, göz, kıyafet, ayakkabı | MakeHuman sistem varlıkları (`makehuman_system_assets_cc0.zip`), MPFB 2 ile | **CC0** (serbest) |
| Hareket (yürüme 35_01, koşu 35_17, ayakta durma 113_21) | CMU Graphics Lab Motion Capture Database, cgspeed BVH dönüşümü | Araştırma ve ticari kullanıma serbest; teşekkür metni istenir (aşağıda) |
| Araçlar (dağıtılmaz) | Blender 4.5 LTS, MPFB 2.0.18 | GPL (yalnızca üretimde kullanılır) |

Tezde ve yayınlarda teşekkür kısmına (CMU'nun istediği metin):

> The data used in this project was obtained from mocap.cs.cmu.edu. The database was created with funding from
> NSF EIA-0196217.

## Nasıl üretiliyor (`tez/sim/insan/uret.py`)

1. MPFB ile insan; `cmu_mb` iskeleti (kemik adları CMU kaydıyla aynı).
2. CMU hareketi kemik kemik aktarılır (dinlenme pozuna göre dünya dönüşü; A-pozu/T-pozu farkı kemik yönleriyle
   kalibre edilir). Kalça ilerlemesi ve yüksekliği **bacak boyu oranıyla** ölçeklenir: ayaklar kalçanın gittiği kadar
   adım atar, basan ayak kaymaz.
3. Kayıttan bir adım döngüsü (sol ayak inişinden sol ayak inişine) kesilir, +x yönüne çevrilir, döngü dikişsiz
   kapatılır, 30 kare/s. Yürüme 1.08 s'de 1.53 m (1.41 m/s, saniyede 1.85 adım), koşu 0.73 s'de 2.54 m (3.46 m/s),
   ayakta durma 6 s.
4. COLLADA dışa aktarımı ve Gazebo düzeltmeleri: `keep_flat_curves` (yoksa sabit kanallar atılır, kemikler dinlenme
   pozuna döner); iskelet nesnesinin kendi animasyonu silinir (Gazebo dosyadaki ilk animasyonu kullanır ve x ilerlemesi
   göremeyince `interpolate_x`'i kapatır); kanallar düz liste; eklem kimlikleri = kemik adları.
5. `insan.json`: animasyon başına kalça yüksekliği (Gazebo kökü yol noktası yüksekliğine koyar), adım ve doğal hız.

## Doğrulama (2026-10-11, yandan kamera, zemine 5 cm ızgara)

Yürürken yere basan ayakkabı ızgaraya göre yerinde kalır (eski Mingfei modelinde basan ayak 0.12–0.2 m/s
kayıyordu: hareket kaydı başka oranlı bir iskelete aktarılmıştı). Tepe kamerası doğrulaması ≤ 0.10 m.

## Gazebo hatası (gz-sim 8) ve önlemi

`interpolate_x` (bacakları yürünen mesafeye kilitler) her animasyon **dosya yolu** için yalnızca ilk yörüngede açılır
(`SceneManager.cc`, `animInterpolateCheck`); sonraki yörüngeler zamana göre oynar ve doğal hızdan farklı hızlarda ayak
kayar. `hedef.py` her hareketli yörüngeye aynı dosyanın farklı yazımını verir (`./walk.dae`, `././walk.dae`, …).
0.9 m/s'de ikinci yürüme bacağında karşılaştırıldı: önlemsiz kayıyor, önlemle yerinde.

## Bilinen eksikler

- Kalça yüksekliği her animasyonda sabit (Gazebo kökün yüksekliğini animasyondan almaz): yürürken ~±2 cm iniş-çıkış
  yok, ayak yere ±2 cm gömülüp kalkabilir.
- Yerinde dönüş/kalkış/duruş için ayrı animasyon yok (dar yayda adım atarak dönüyor; durunca yürüme pozu ayakta
  durma pozuna atlıyor).
- Tek kişi, tek kıyafet. Varlık paketinde 24 deri (yaş/köken/cinsiyet), 20 kıyafet, 10 saç var: farklı insanlar
  `uret.py`'deki birkaç satırla üretilebilir.
