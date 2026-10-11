# İnsan hedef modeli

Animasyonlu insan (yürü, dur, koş) — Gazebo Fuel **"actor"**, yazar **Mingfei**, sürüm 1:
https://app.gazebosim.org/Mingfei/fuel/models/actor

Lisans: **Creative Commons Attribution 4.0 International (CC BY 4.0)** —
http://creativecommons.org/licenses/by/4.0/ . Kullanırken kaynak gösterilmelidir (tezde de).

`meshes/` git'e girmez (büyük ikili dosyalar); `tez/sim/kur.sh` sha256 ile doğrulayarak indirir.
İndirilen `walk.dae`, `stand.dae`, `run.dae` değiştirilmez. **Uyarlama (CC BY 4.0'ın izin verdiği):** `kur.sh`,
`araclar/animasyon.py` ile `walk_tez.dae` ve `run_tez.dae` kopyalarını üretir. Bunlar aynı yürüme/koşu
döngüsüdür; sadece animasyon kareleri, döngü ayakların yan yana geldiği andan başlayacak şekilde kaydırılmıştır
(yürüme 0.37 m, koşu 0.24 m kalça ilerlemesi). Orijinal döngü adım ortasında başladığı için duruştan kalkan insan
"donmuş bir hamle" pozunda kayıyor gibi görünüyordu (2026-10-11, yandan kamera ölçümü).

Not: Gazebo Harmonic'te bu model `<script><loop>false</loop>` ile kullanılırsa kamera sensörü açıkken
sunucu kilitleniyor (2026-10-11 denemesi). Senaryo yöneticisi bu yüzden `loop=true` + sonda uzun bir
"dur" parçası kullanır.

Gazebo bir rotayı Catmull-Rom eğrisiyle doldurur: sadece iki uç noktası olan bir yürüyüşte insan
yavaş-hızlı-yavaş gider ve hesaplanan yerden ±0.5 m sapar. `hedef.py` bu yüzden her yürüyüş/koşu parçasına
0.2 s arayla ara nokta yazar; ölçülen fark 0.05–0.19 m'ye iner (gövde merkezi yolun biraz önünde).
