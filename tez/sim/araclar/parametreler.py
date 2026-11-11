#!/usr/bin/env python3
"""Start parameters of the simulated drone: .params files -> PX4_PARAM_<NAME>=<value> lines for PX4's posix rcS.

PX4 v1.17.0 posix rcS sets every PX4_PARAM_<NAME> environment variable with `param set` after `param reset_all`
and before the airframe file, so the airframe's `param set-default` lines do not override them and no PX4 file has
to change. calistir.sh exports the lines this tool prints.

File format (tez/sim/parametreler/*.params), one parameter per line, blank lines and # comments are skipped:

    MC_ROLLRATE_P  0.14   # 4019_x500_v2   <- NAME VALUE  # source (the source comment is required)

Load order, the last one wins: gercek_dron.params -> sim.params -> scenario takip.px4_parametreleri -> --param.

    python tez/sim/araclar/parametreler.py [--param NAME=VALUE ...]
"""

import argparse
import math
import re
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

PARAM_DIR = Path(__file__).resolve().parent.parent / "parametreler"
FILES = (PARAM_DIR / "gercek_dron.params", PARAM_DIR / "sim.params")
ENV_PREFIX = "PX4_PARAM_"
NAME_PATTERN = re.compile(r"[A-Z0-9_]{1,16}")  # PX4: upper case, at most 16 characters
NUMBER_PATTERN = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
INT_PATTERN = re.compile(r"[+-]?\d+")
SCENARIO_SOURCE = "takip.px4_parametreleri"
COMMAND_LINE_SOURCE = "--param"

Number = int | float


@dataclass(frozen=True)
class Param:
    name: str
    value: Number  # int when written without a decimal point (PX4 INT32 parameters need that)
    source: str  # "<file>:<line> # <comment>", "takip.px4_parametreleri" or "--param"


def check_name(name: str, where: str) -> str:
    if not NAME_PATTERN.fullmatch(name):
        raise ValueError(f"{where}: '{name}' PX4 parametre adı değil (büyük harf, rakam, '_', en fazla 16 karakter)")
    return name


def parse_value(text: str, where: str) -> Number:
    """'30' -> 30, '0.14' -> 0.14; anything else (nan, inf, words) is rejected with `where` in the message."""
    text = text.strip()
    if INT_PATTERN.fullmatch(text):
        return int(text)
    if NUMBER_PATTERN.fullmatch(text):
        return float(text)
    raise ValueError(f"{where}: değer sayı olmalı, gelen: {text!r}")


def read_file(path: Path) -> list[Param]:
    """Parameters of one .params file, in file order; every bad line is reported with its line number and name."""
    params: list[Param] = []
    first_line: dict[str, int] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        body, _, comment = raw.partition("#")
        if not body.strip():
            continue
        where = f"{path.name}: satır {number}"
        fields = body.split()
        if len(fields) != 2:
            raise ValueError(f"{where}: 'AD DEĞER  # kaynak' biçiminde olmalı, gelen: {raw.strip()!r}")
        name = check_name(fields[0], where)
        value = parse_value(fields[1], f"{where}: {name}")
        if not comment.strip():
            raise ValueError(f"{where}: {name}: kaynak yorumu yok ('{name} {fields[1]}  # kaynak' yazın)")
        if name in first_line:
            raise ValueError(f"{where}: {name}: aynı dosyada satır {first_line[name]}'de de var")
        first_line[name] = number
        params.append(Param(name, value, f"{path.name}:{number} # {comment.strip()}"))
    return params


def from_mapping(values: Mapping[str, object], source: str = SCENARIO_SOURCE) -> list[Param]:
    """{NAME: number} (e.g. the scenario's takip.px4_parametreleri) checked with the same rules as a file."""
    params = []
    for name, value in values.items():
        check_name(str(name), source)
        if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
            raise ValueError(f"{source}: {name}: değer sayı olmalı, gelen: {value!r}")
        params.append(Param(str(name), value, source))
    return params


def parse_assignment(text: str) -> Param:
    """'NAME=VALUE' of the --param option."""
    name, sep, value = text.partition("=")
    if not sep or not value.strip():
        raise ValueError(f"{COMMAND_LINE_SOURCE} {text!r}: AD=DEĞER biçiminde olmalı (ör. FLW_TGT_DST=10)")
    name = check_name(name.strip(), f"{COMMAND_LINE_SOURCE} {text!r}")
    return Param(name, parse_value(value, f"{COMMAND_LINE_SOURCE} {text!r}"), COMMAND_LINE_SOURCE)


def merge(*layers: Iterable[Param]) -> dict[str, Param]:
    """Layers in load order; a later layer replaces the value (and the source) of an earlier one."""
    merged: dict[str, Param] = {}
    for layer in layers:
        for p in layer:
            merged[p.name] = p
    return merged


def load(
    files: Iterable[Path] = FILES,
    scenario: Mapping[str, object] | None = None,
    overrides: Iterable[str] = (),
) -> dict[str, Param]:
    """All start parameters of a run in load order: files -> scenario -> command line (--param NAME=VALUE)."""
    layers = [read_file(Path(f)) for f in files]
    layers.append(from_mapping(scenario or {}))
    layers.append([parse_assignment(text) for text in overrides])
    return merge(*layers)


def format_value(value: Number) -> str:
    """Text for `param set`: integers without a decimal point, floats with up to 9 significant digits."""
    if isinstance(value, int):
        return str(value)
    if value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.9g}"


def matches(expected: Number, actual: Number | None) -> bool:
    """A value read back from PX4 equals the loaded one; PX4 keeps floats as float32 (~7 significant digits)."""
    if actual is None:
        return False
    return abs(actual - expected) <= 1e-6 * max(1.0, abs(expected), abs(actual))


def env_lines(params: Mapping[str, Param]) -> list[str]:
    return [f"{ENV_PREFIX}{p.name}={format_value(p.value)}" for p in params.values()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="AD=DEĞER",
        help="PX4 parametresi, dosyalardan sonra yüklenir (birden çok verilebilir; sonuncu kazanır)",
    )
    args = ap.parse_args(argv)
    try:
        params = load(overrides=args.param)
    except (OSError, ValueError) as e:
        print(f"Parametre hatası: {e}", file=sys.stderr)
        return 2
    print("\n".join(env_lines(params)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
