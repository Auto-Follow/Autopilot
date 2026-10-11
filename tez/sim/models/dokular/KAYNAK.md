# Dünya varlıkları: zemin dokuları ve ağaçlar

Hepsi **CC0 1.0 (kamu malı)**: ticari kullanım dahil serbest, kaynak gösterme zorunlu değil (tezde yine de
gösterilmesi iyi olur). Dosyalar git'e girmez; `tez/sim/kur.sh` sha256 ile doğrulayarak indirir. Zemin,
`tez/sim/worlds/<ad>.yaml` dosyasından `araclar/dunya.py` ile üretilir (`models/<ad>_cevre/`, git'e girmez).

| Kullanım | Varlık | Kaynak | Gerçek boyut |
|---|---|---|---|
| Koyu çim | Grass001 (renk haritası, 1K) | https://ambientcg.com/view?id=Grass001 | 1.4 m |
| Açık / kuru çim | Grass004 | https://ambientcg.com/view?id=Grass004 | 1.4 m |
| Aşınmış çim ve toprak | Ground037 | https://ambientcg.com/view?id=Ground037 | 2.1 m |
| Ağaç altı yaprak, dal | forrest_ground_01 (Rob Tuytel) | https://polyhaven.com/a/forrest_ground_01 | 2 m |
| Toprak patika | dry_mud_field_001 (Rob Tuytel, Rico Cilliers) | https://polyhaven.com/a/dry_mud_field_001 | 3 m |
| Meşe | Gazebo Fuel OpenRobotics "Oak tree" v7 | https://app.gazebosim.org/OpenRobotics/fuel/models/Oak%20tree | 6.5 m boy (ölçek 1) |
| Çam | Gazebo Fuel OpenRobotics "Pine Tree" v6 | https://app.gazebosim.org/OpenRobotics/fuel/models/Pine%20Tree | 5 m boy (ölçek 1) |

Uyarlamalar (`dunya.py`): dokular ~1.2 cm/piksele küçültülür; fotoğraf boyunca değişen aydınlık (tekrarlandığında
üstten ızgara gibi görünüyordu) süzülür ve her doku kendi türüne uygun ortalama renge getirilir (fotoğrafların
pozlaması farklıydı: aşınmış zemin çimden iki kat parlak çıkıyordu). Zemin hücrelere bölünür, her hücrede doku
rastgele döndürülüp kaydırılır, komşu hücreler yumuşak geçişle birleşir; böylece dokunun kendi lekeleri sıraya
dizilmez. Ağaçların yalnızca mesh ve dokuları kullanılır; ölçek, yön ve çarpışma şekilleri (gövde silindiri + taç
elipsoidi) `dunya.py`'de yazılır.

Bilinen sınırlar: zemin düzdür (tümsek, çukur yok); çimler düz dokudur (yükseklikleri yok, rüzgârda sallanmaz);
Fuel ağaçları düşük ayrıntılı (yaprak kartları, meşe yaprak dokusu 128 piksel) ve rüzgârda kıpırdamaz. Daha
gerçekçi ağaçlar (ör. Poly Haven, yüzbinlerce üçgen) birkaç tane için kullanılabilir, çok sayıda simi yavaşlatır.
