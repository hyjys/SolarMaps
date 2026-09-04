"""일사 계산 검증: 물리적으로 반드시 성립해야 하는 성질들을 확인한다."""

import pytest

from solarmaps.irradiance import (
    erbs_diffuse_fraction,
    extraterrestrial_daily_kwh_m2,
    hourly_poa_series,
)

SUMMER_SOLSTICE_DOY = 172
WINTER_SOLSTICE_DOY = 355
SPRING_EQUINOX_DOY = 80


def test_extraterrestrial_zero_at_equator_is_stable_across_seasons() -> None:
    # 적도는 계절에 따른 대기권외 일사 변동이 상대적으로 작다(연중 태양 고도 높음)
    summer = extraterrestrial_daily_kwh_m2(0.0, SUMMER_SOLSTICE_DOY)
    winter = extraterrestrial_daily_kwh_m2(0.0, WINTER_SOLSTICE_DOY)
    assert summer > 0 and winter > 0
    assert abs(summer - winter) / winter < 0.15


def test_extraterrestrial_high_latitude_summer_exceeds_equator() -> None:
    # 백야에 가까운 고위도 여름은 하루 총 일사가 적도보다 클 수 있음(일조시간 효과)
    high_lat_summer = extraterrestrial_daily_kwh_m2(65.0, SUMMER_SOLSTICE_DOY)
    equator_summer = extraterrestrial_daily_kwh_m2(0.0, SUMMER_SOLSTICE_DOY)
    assert high_lat_summer > equator_summer


def test_extraterrestrial_polar_night_is_zero() -> None:
    assert extraterrestrial_daily_kwh_m2(75.0, WINTER_SOLSTICE_DOY) == 0.0


def test_erbs_high_clearness_gives_low_diffuse_fraction() -> None:
    assert erbs_diffuse_fraction(0.9) < erbs_diffuse_fraction(0.3)


def test_erbs_output_is_bounded() -> None:
    for kt in (0.0, 0.1, 0.22, 0.5, 0.8, 1.0):
        f = erbs_diffuse_fraction(kt)
        assert 0.0 <= f <= 1.0


def test_poa_energy_conserved_for_flat_panel() -> None:
    # 수평(tilt=0) 패널은 입사각 코사인이 항상 sin(고도각)과 같아 GHI와 매우 근접해야 함
    series = hourly_poa_series(
        latitude_deg=37.5665,
        longitude_deg=126.9780,
        day_of_year=SUMMER_SOLSTICE_DOY,
        ghi_daily_kwh_m2=5.0,
        diffuse_daily_kwh_m2=1.5,
        surface_tilt_deg=0.0,
        surface_azimuth_deg=180.0,
        albedo=0.2,
        utc_offset_hours=9.0,
    )
    assert series
    total_ghi = sum(r.ghi_w_m2 for r in series)
    total_poa = sum(r.poa_w_m2 for r in series)
    assert total_ghi > 0
    # 수평면은 POA ≈ GHI (지표반사 성분만큼만 약간 증가)
    assert total_poa == pytest.approx(total_ghi, rel=0.15)


def test_tilted_south_facing_beats_flat_in_winter_at_midlatitude() -> None:
    # 중위도 겨울에는 남향 경사 패널이 수평 패널보다 총 POA가 커야 함(태양 고도가 낮으므로)
    common = dict(
        latitude_deg=37.5665,
        longitude_deg=126.9780,
        day_of_year=WINTER_SOLSTICE_DOY,
        ghi_daily_kwh_m2=2.5,
        diffuse_daily_kwh_m2=1.0,
        albedo=0.2,
        utc_offset_hours=9.0,
    )
    flat = hourly_poa_series(surface_tilt_deg=0.0, surface_azimuth_deg=180.0, **common)
    tilted = hourly_poa_series(surface_tilt_deg=37.0, surface_azimuth_deg=180.0, **common)
    assert sum(r.poa_w_m2 for r in tilted) > sum(r.poa_w_m2 for r in flat)


def test_north_facing_worse_than_south_facing_in_northern_hemisphere() -> None:
    # 춘분에는 해가 정동에서 떠 정서로 지므로, 여름철과 달리 이른아침/늦저녁에
    # 북향면이 직달광을 받는 경계효과가 없다 — 남향 우위가 명확하게 성립해야 함.
    common = dict(
        latitude_deg=37.5665,
        longitude_deg=126.9780,
        day_of_year=SPRING_EQUINOX_DOY,
        ghi_daily_kwh_m2=4.0,
        diffuse_daily_kwh_m2=1.5,
        albedo=0.2,
        utc_offset_hours=9.0,
        surface_tilt_deg=30.0,
    )
    south = hourly_poa_series(surface_azimuth_deg=180.0, **common)
    north = hourly_poa_series(surface_azimuth_deg=0.0, **common)
    assert sum(r.poa_w_m2 for r in south) > sum(r.poa_w_m2 for r in north)


def test_poa_nonnegative() -> None:
    series = hourly_poa_series(
        latitude_deg=60.0,
        longitude_deg=10.0,
        day_of_year=WINTER_SOLSTICE_DOY,
        ghi_daily_kwh_m2=0.3,
        diffuse_daily_kwh_m2=0.25,
        surface_tilt_deg=60.0,
        surface_azimuth_deg=180.0,
        albedo=0.6,
        utc_offset_hours=1.0,
    )
    for r in series:
        assert r.poa_w_m2 >= 0.0
        assert r.ghi_w_m2 >= 0.0
