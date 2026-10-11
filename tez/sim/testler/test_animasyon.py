"""Animation copies that start at another frame (the feet together instead of mid-stride)."""

import re

import animasyon

FRAMES = 5


def channel(name: str, xs: list[float]) -> str:
    mats = " ".join(f"1 0 0 {x} 0 1 0 0 0 0 1 1 0 0 0 1" for x in xs)
    arr = f"_t_{name}_pose_matrix"
    return (
        f'<animation id="{arr}"><source><float_array id="{arr}-input-array" count="{FRAMES}">0 1 2 3 4</float_array>'
        f'</source><source><float_array id="{arr}-output-array" count="{16 * FRAMES}">{mats}</float_array></source>'
        f'<channel target="{name}/transform"/></animation>'
    )


def dae() -> str:
    hips = channel("Hips", [0.0, 0.1, 0.2, 0.3, 0.4])  # 0.1 m of hip travel per frame
    leg = channel("LeftLeg", [5.0, 6.0, 7.0, 8.0, 9.0])  # a constant offset per frame, not travel
    return f"<COLLADA><library_animations>{hips}{leg}</library_animations></COLLADA>"


def x_of(text: str, name: str) -> list[float]:
    arr = re.search(rf'id="_t_{name}_pose_matrix-output-array" count="\d+">([^<]*)<', text).group(1).split()
    return [float(arr[16 * i + 3]) for i in range(FRAMES)]


def test_starts_at_the_chosen_frame_and_keeps_moving_forward() -> None:
    out = animasyon.retime(dae(), 0.2)
    assert x_of(out, "Hips") == [0.0, 0.1, 0.2, 0.3, 0.4]  # 0.2,0.3,0.4 then 0.0+0.5, 0.1+0.5, shifted to start at 0
    assert x_of(out, "LeftLeg") == [7.0, 8.0, 9.0, 5.0, 6.0]  # other bones only change order
    assert "0 1 2 3 4" in out  # key times unchanged


def test_zero_offset_changes_nothing() -> None:
    assert x_of(animasyon.retime(dae(), 0.0), "LeftLeg") == [5.0, 6.0, 7.0, 8.0, 9.0]
