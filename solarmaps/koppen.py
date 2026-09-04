"""0.5도 격자 쾨펜 기후 조회.

scripts/build_koppen.py 가 만든 public/data/koppen.bin (+ legend, + 십년별
트랙)을 읽는다. 파일시스템 접근 방식은 두 런타임에서 다르게 마련된다:

- CPython: 로컬 경로를 그대로 읽는다.
- Pyodide: JS(py-bridge.js)가 fetch()로 받은 bytes를 Pyodide 가상 FS의
  같은 상대경로에 미리 write해 둔다. 이 모듈은 그 사실을 몰라도 되고,
  똑같이 pathlib로 읽으면 된다.

바다처럼 분류되지 않은 셀(코드 0)을 클릭한 경우, 나선형으로 탐색 반경을
넓혀가며 가장 가까운 분류된 육지 셀을 찾는다(해안선 클릭 대비).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
_DEFAULT_DATA_DIR = _PACKAGE_DIR.parent / "public" / "data"

_MAX_SEARCH_RADIUS_CELLS = 60  # 0.5도 격자 기준 30도 반경까지 탐색 (태평양 한복판까지 포괄)


@dataclass(frozen=True)
class KoppenLookup:
    code: str
    is_interpolated: bool  # True면 클릭 지점이 바다 등 미분류라 최근접 육지값을 사용
    distance_deg: float  # 최근접 탐색으로 이동한 거리(도). 직접 조회면 0.0


class KoppenGrid:
    def __init__(self, grid: bytes, legend: dict):
        self._grid = grid
        self._legend = legend
        self._w = legend["grid_width"]
        self._h = legend["grid_height"]
        self._codes = legend["codes"]  # index 1..N -> code

    @property
    def codes(self) -> list[str]:
        return self._codes

    def _lon_to_col(self, lon: float) -> int:
        lon = ((lon + 180.0) % 360.0) - 180.0  # -180..180 정규화
        return min(self._w - 1, max(0, int((lon + 180.0) / 0.5)))

    def _lat_to_row(self, lat: float) -> int:
        lat = max(-90.0, min(90.0, lat))
        return min(self._h - 1, max(0, int((lat + 90.0) / 0.5)))

    def _code_at_cell(self, row: int, col: int) -> str | None:
        idx = self._grid[row * self._w + col]
        if idx == 0:
            return None
        return self._codes[idx - 1]

    def lookup(self, lat: float, lon: float) -> KoppenLookup:
        col = self._lon_to_col(lon)
        row = self._lat_to_row(lat)

        code = self._code_at_cell(row, col)
        if code is not None:
            return KoppenLookup(code=code, is_interpolated=False, distance_deg=0.0)

        for radius in range(1, _MAX_SEARCH_RADIUS_CELLS + 1):
            best: tuple[float, str] | None = None
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    if max(abs(dr), abs(dc)) != radius:
                        continue  # 이전 반경에서 이미 검사한 내부 셀은 건너뜀
                    r, c = row + dr, col + dc
                    if not (0 <= r < self._h and 0 <= c < self._w):
                        continue
                    found = self._code_at_cell(r, c)
                    if found is None:
                        continue
                    dist_sq = dr * dr + dc * dc
                    if best is None or dist_sq < best[0]:
                        best = (dist_sq, found)
            if best is not None:
                distance_deg = (best[0] ** 0.5) * 0.5
                return KoppenLookup(code=best[1], is_interpolated=True, distance_deg=distance_deg)

        raise LookupError(f"({lat}, {lon}) 근방 {_MAX_SEARCH_RADIUS_CELLS * 0.5}도 내에 분류된 셀이 없습니다")


def load_grid(data_dir: str | Path | None = None) -> KoppenGrid:
    base = Path(data_dir) if data_dir is not None else _DEFAULT_DATA_DIR
    legend = json.loads((base / "koppen_legend.json").read_text(encoding="utf-8"))
    grid_bytes = (base / "koppen.bin").read_bytes()
    return KoppenGrid(grid=grid_bytes, legend=legend)
