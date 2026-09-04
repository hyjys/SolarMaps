"""쾨펜 격자 조회 검증. 알려진 도시 좌표 → 통설적으로 알려진 쾨펜 코드."""

from solarmaps.koppen import load_grid

grid = load_grid()


def test_seoul_is_dwa_or_dwb() -> None:
    # 서울은 습윤대륙성 겨울건조(Dwa/Dwb 경계 근방). 0.5도 격자 특성상 인접값 허용.
    lookup = grid.lookup(37.5665, 126.9780)
    assert lookup.code in {"Dwa", "Dwb", "Dfa", "Dfb"}
    assert not lookup.is_interpolated


def test_singapore_is_tropical_rainforest() -> None:
    lookup = grid.lookup(1.3521, 103.8198)
    assert lookup.code == "Af"


def test_riyadh_is_hot_desert() -> None:
    lookup = grid.lookup(24.7136, 46.6753)
    assert lookup.code == "BWh"


def test_oslo_is_continental_or_oceanic() -> None:
    lookup = grid.lookup(59.9139, 10.7522)
    assert lookup.code in {"Dfb", "Cfb"}


def test_ocean_point_falls_back_to_nearest_land() -> None:
    # 태평양 한복판 — 미분류 셀. 최근접 육지 탐색이 동작해야 한다.
    lookup = grid.lookup(0.0, -150.0)
    assert lookup.code
    assert lookup.is_interpolated
    assert lookup.distance_deg > 0


def test_antarctica_is_polar() -> None:
    lookup = grid.lookup(-80.0, 0.0)
    assert lookup.code in {"EF", "ET"}
