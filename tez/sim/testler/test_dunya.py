"""World description files and the ground baking helpers (no textures or Gazebo needed)."""

from collections.abc import Callable
from pathlib import Path

import dunya
import numpy as np
import pytest

GOOD = """
ad: deneme
tohum: 4
alan: {merkez: [20, 0], boyut_m: 48}
yollar:
  - {noktalar: [[-10, 0], [10, 0], [30, 5]], genislik_m: 2}
agaclar:
  - {tur: mese, konum: [20, 15]}
agac_gruplari:
  - {merkez: [40, -20], yaricap_m: 8, sayi: 4, turler: [cam]}
"""


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[str], dunya.World]:
    def load(text: str) -> dunya.World:
        (tmp_path / "worlds").mkdir(exist_ok=True)
        (tmp_path / "worlds" / "deneme.yaml").write_text(text, encoding="utf-8")
        monkeypatch.setattr(dunya, "SIM_DIR", tmp_path)
        return dunya.load("deneme")

    return load


def test_load(world: Callable[[str], dunya.World]) -> None:
    w = world(GOOD)
    assert w.size == 48 and w.origin() == (-4.0, -24.0)
    assert len(w.trees) == 5 and {t.kind for t in w.trees[1:]} == {"cam"}
    assert w.trees[0].x == 20 and 1.0 <= w.trees[0].scale <= 1.5
    # the group stays in its disc, off the path, trees apart
    for t in w.trees[1:]:
        assert np.hypot(t.x - 40, t.y + 20) <= 8 + 1e-9
    assert world(GOOD).trees[3].x == w.trees[3].x  # same seed, same forest


@pytest.mark.parametrize(
    "change, message",
    [
        (("boyut_m: 48", "boyut_m: 50"), "24 m'nin katı"),
        (("tur: mese", "tur: kavak"), "ağaç türü"),
        (("konum: [20, 15]", "konum: [3, 2]"), "kalkış yerine"),
        (("sayi: 4", "sayi: 60"), "sığmadı"),
        (("tohum: 4", "tohum: 4\nfazla: 1"), "bilinmeyen alan"),
        (("genislik_m: 2", "genislik: 2"), "yollar[0]"),
    ],
)
def test_mistakes_name_the_field(world: Callable[[str], dunya.World], change: tuple[str, str], message: str) -> None:
    with pytest.raises(ValueError, match=message.replace("[", r"\[")):
        world(GOOD.replace(*change))


def test_world_without_description_file() -> None:
    assert dunya.load("duz_alan") is None


def test_shipped_worlds_load() -> None:
    for path in (dunya.SIM_DIR / "worlds").glob("*.yaml"):
        assert dunya.load(path.stem).trees


def test_path_distance() -> None:
    straight = dunya.Trail(dunya._smooth_line(np.array([[-10.0, 0.0], [0.0, 0.0], [10.0, 0.0]])), 2.0)
    d = dunya.path_distance([straight], np.array([0.0, 0.0, 0.0]), np.array([0.0, 1.0, 4.0]))
    assert d == pytest.approx([-1.0, 0.0, 3.0], abs=0.02)  # 2 m wide: inside, on the edge, 3 m off


def test_noise_is_continuous_and_periodic() -> None:
    x = np.linspace(0, 48, 2001)
    n = dunya.value_noise(x, np.zeros_like(x), 5.0, 1)
    assert np.abs(n).max() <= 1 and np.abs(np.diff(n)).max() < 0.05  # no jumps (tile edges are just positions)
    p = dunya.value_noise(np.array([3.0, 3.0 + 48]), np.array([7.0, 7.0 - 48]), 18.0, 2, period=48)
    assert p[0] == pytest.approx(p[1])  # the outer tile repeats seamlessly


def test_stochastic_tiling_is_seamless() -> None:
    src = dunya.Source.__new__(dunya.Source)
    rng = np.random.default_rng(0)
    src.n = 40
    src.stack = np.stack([np.rot90(rng.random((40, 40, 3)), k) for k in range(4)]).astype(np.float32)
    gx, gy = np.arange(0, 400), np.arange(300, -100, -1)
    whole = src.stochastic(gx, gy, 5)
    left, right = src.stochastic(gx[:173], gy, 5), src.stochastic(gx[173:], gy, 5)
    assert np.allclose(whole, np.concatenate([left, right], axis=1))  # tiles baked apart join exactly
    periodic = src.stochastic(np.arange(0, 480), gy, 5, period_px=240)
    assert np.allclose(periodic[:, :240], periodic[:, 240:])


def test_tree_blocks_its_trunk(world: Callable[[str], dunya.World]) -> None:
    w = world(GOOD)
    t = w.trees[0]
    assert w.blocked(t.x + 0.2, t.y) is t
    assert w.blocked(t.x + 3.0, t.y) is None
