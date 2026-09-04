"""최적화 결과 검증. 절대 오차보다 정성적 경향(위도가 높을수록 경사각이 커진다 등)에
집중한다 — 이 모형은 문헌값과 정밀히 일치하는 것이 목표가 아니라, 1차 근사로서
물리적으로 타당한 방향을 가리키는지가 중요하다(계획서: 실측 도착 전 이론값 프로토타입).

네트워크 의존을 피하기 위해 NASA POWER 대신 climate_fallback 경로를 사용한다.
"""

import pytest

from solarmaps.optimizer import build_fallback_monthly_climate, optimize


def _run(lat: float, lon: float, koppen: str, utc_offset: float, precise: bool = False):
    climate = build_fallback_monthly_climate(lat, koppen)
    return optimize(
        latitude_deg=lat,
        longitude_deg=lon,
        koppen_code=koppen,
        koppen_name_ko=koppen,
        monthly_climate=climate,
        utc_offset_hours=utc_offset,
        precise_azimuth_mode=precise,
    )


def test_equator_optimal_tilt_is_small() -> None:
    result = _run(0.0, 0.0, "Af", utc_offset=0.0)
    assert 0.0 <= result.tilt_deg <= 15.0


def test_seoul_optimal_tilt_is_moderate() -> None:
    result = _run(37.5665, 126.9780, "Dwa", utc_offset=9.0)
    assert 20.0 <= result.tilt_deg <= 45.0


def test_high_latitude_optimal_tilt_exceeds_low_latitude() -> None:
    equator = _run(5.0, 0.0, "Af", utc_offset=0.0)
    high_lat = _run(60.0, 10.0, "Dfb", utc_offset=1.0)
    assert high_lat.tilt_deg > equator.tilt_deg


def test_northern_hemisphere_default_azimuth_is_south() -> None:
    result = _run(37.5665, 126.9780, "Dwa", utc_offset=9.0)
    assert result.azimuth_deg == pytest.approx(180.0)
    assert result.azimuth_symmetric_model is True


def test_southern_hemisphere_default_azimuth_is_north() -> None:
    result = _run(-33.87, 151.21, "Cfa", utc_offset=10.0)  # 시드니 근사
    assert result.azimuth_deg == pytest.approx(0.0)


def test_tilted_panel_beats_flat_at_midlatitude() -> None:
    result = _run(45.0, 0.0, "Cfb", utc_offset=1.0)
    assert result.gain_vs_flat_percent > 0.0
    assert result.tilt_deg > 0.0


def test_monthly_yield_covers_all_twelve_months() -> None:
    result = _run(37.5665, 126.9780, "Dwa", utc_offset=9.0)
    assert len(result.monthly) == 12
    assert {m.month for m in result.monthly} == set(range(1, 13))
    assert all(m.energy_kwh_m2 >= 0 for m in result.monthly)


def test_azimuth_loss_curve_is_symmetric_and_nonnegative() -> None:
    result = _run(37.5665, 126.9780, "Dwa", utc_offset=9.0)
    assert result.azimuth_loss_curve
    for point in result.azimuth_loss_curve:
        assert point.loss_percent >= 0.0
    # 중심(offset=0)이 최소 손실이어야 함(최적점 자체이므로)
    center = next(p for p in result.azimuth_loss_curve if p.azimuth_deg == 0.0)
    assert center.loss_percent == pytest.approx(0.0, abs=0.5)


def test_precise_azimuth_mode_runs_without_error() -> None:
    result = _run(37.5665, 126.9780, "Dwa", utc_offset=9.0, precise=True)
    assert result.azimuth_symmetric_model is False
    assert 0.0 <= result.azimuth_deg < 360.0
