"""koppen_30year_1901-2010.tsv → 720x360 uint8 이진 격자 + 범례 JSON.

원본은 0.5도 격자 중심좌표(경도, 위도) + 기간별 쾨펜 코드의 TSV다.
런타임(Pyodide 포함)에서 매번 텍스트를 파싱하지 않도록, 경도 -180..180 /
위도 -90..90을 0.5도 간격 720x360 배열로 펼쳐 raw uint8 바이트로 저장한다.
바이트 값 0 = 데이터 없음(대개 해양), 1..N = koppen_legend.json의 codes 인덱스.

같은 로직으로 십년별 컬럼(koppen_decadal_1901-2010.tsv)도 함께 구워서
기후대 변화 추이 기능(계획서 "부가 기능")에 사용한다.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KOPPEN_DIR = ROOT / "koppen"
OUT_DIR = ROOT / "public" / "data"

GRID_W = 720  # 경도: -180.00 ~ 179.50, 0.5도 간격
GRID_H = 360  # 위도: -90.00 ~ 89.50, 0.5도 간격


def lon_to_col(lon: float) -> int:
    return round((lon + 180.0) / 0.5 - 0.5)


def lat_to_row(lat: float) -> int:
    # 행 0 = 남극(-90) 쪽. get()에서 위도를 그대로 이 방향으로 사용한다.
    return round((lat + 90.0) / 0.5 - 0.5)


def build_code_table(*tsv_paths: Path) -> list[str]:
    """여러 TSV에 등장하는 모든 코드를 모아 정렬된 코드표를 만든다(인덱스 1부터)."""
    codes: set[str] = set()
    for path in tsv_paths:
        with path.open(newline="", encoding="ascii") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader)  # 헤더 스킵
            for row in reader:
                for cell in row[2:]:
                    cell = cell.strip()
                    if cell and cell.upper() != "NAN":
                        codes.add(cell)
    return sorted(codes)


def build_single_layer(tsv_path: Path, column: str, code_index: dict[str, int]) -> bytearray:
    grid = bytearray(GRID_W * GRID_H)  # 0 = no data
    with tsv_path.open(newline="", encoding="ascii") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        col_idx = header.index(column)
        for row in reader:
            lon = float(row[0])
            lat = float(row[1])
            code = row[col_idx].strip()
            if not code or code.upper() == "NAN":
                continue
            col = lon_to_col(lon)
            r = lat_to_row(lat)
            if 0 <= col < GRID_W and 0 <= r < GRID_H:
                grid[r * GRID_W + col] = code_index[code]
    return grid


def build_multi_layer(tsv_path: Path, columns: list[str], code_index: dict[str, int]) -> dict[str, bytearray]:
    grids = {c: bytearray(GRID_W * GRID_H) for c in columns}
    with tsv_path.open(newline="", encoding="ascii") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        col_indices = {c: header.index(c) for c in columns}
        for row in reader:
            lon = float(row[0])
            lat = float(row[1])
            col = lon_to_col(lon)
            r = lat_to_row(lat)
            if not (0 <= col < GRID_W and 0 <= r < GRID_H):
                continue
            idx = r * GRID_W + col
            for c, ci in col_indices.items():
                code = row[ci].strip()
                if code and code.upper() != "NAN":
                    grids[c][idx] = code_index[code]
    return grids


def main() -> None:
    thirty_year = KOPPEN_DIR / "koppen_30year_1901-2010.tsv"
    decadal = KOPPEN_DIR / "koppen_decadal_1901-2010.tsv"
    for p in (thirty_year, decadal):
        if not p.exists():
            print(f"missing: {p}", file=sys.stderr)
            sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    codes = build_code_table(thirty_year, decadal)
    code_index = {c: i + 1 for i, c in enumerate(codes)}  # 0은 "데이터 없음"으로 예약

    # 주 분류: 최신 30년 평년(1981-2010)
    current = build_single_layer(thirty_year, "p1981_2010", code_index)
    (OUT_DIR / "koppen.bin").write_bytes(bytes(current))

    # 부가 기능: 십년별 전체 트랙 (기후대 변화 추이)
    with decadal.open(newline="", encoding="ascii") as f:
        decade_columns = next(csv.reader(f, delimiter="\t"))[2:]

    decades = build_multi_layer(decadal, decade_columns, code_index)
    decades_dir = OUT_DIR / "koppen_decades"
    decades_dir.mkdir(exist_ok=True)
    for period, grid in decades.items():
        (decades_dir / f"{period}.bin").write_bytes(bytes(grid))

    legend = {
        "grid_width": GRID_W,
        "grid_height": GRID_H,
        "cell_size_deg": 0.5,
        "lon_origin": -180.0,
        "lat_origin": -90.0,
        "codes": codes,  # index (1-based) -> 쾨펜 코드. 0 = 데이터 없음
        "period_current": "p1981_2010",
        "decade_periods": decade_columns,
        "source": "Chen, D. and H. W. Chen (2013), Environmental Development, 6, 69-79.",
    }
    (OUT_DIR / "koppen_legend.json").write_text(
        json.dumps(legend, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    n_cells = sum(1 for b in current if b != 0)
    print(f"codes: {len(codes)}")
    print(f"koppen.bin: {len(current)} bytes, {n_cells} classified cells")
    print(f"koppen_decades/: {len(decades)} periods x {GRID_W * GRID_H} bytes")


if __name__ == "__main__":
    main()
