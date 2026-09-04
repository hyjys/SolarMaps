"""태양 기하 해석해 대조 테스트."""

import math

import pytest

from solarmaps.geometry import (
    daylight_hours_range,
    hour_angle_deg,
    incidence_cosine,
    solar_declination_deg,
    solar_position,
)

SPRING_EQUINOX_DOY = 80  # 3/21 근사
SUMMER_SOLSTICE_DOY = 172  # 6/21 근사
WINTER_SOLSTICE_DOY = 355  # 12/21 근사


def test_equinox_declination_near_zero() -> None:
    assert abs(solar_declination_deg(SPRING_EQUINOX_DOY)) < 1.0


def test_solstice_declination_near_23_45() -> None:
    assert solar_declination_deg(SUMMER_SOLSTICE_DOY) == pytest.approx(23.45, abs=0.5)
    assert solar_declination_deg(WINTER_SOLSTICE_DOY) == pytest.approx(-23.45, abs=0.5)


@pytest.mark.parametrize("lat", [0.0, 20.0, 37.5665, 60.0, -33.87])
def test_equinox_noon_altitude_equals_90_minus_abs_lat(lat: float) -> None:
    dec = solar_declination_deg(SPRING_EQUINOX_DOY)
    pos = solar_position(lat, dec, hour_angle_deg(12.0))  # 태양시 정오, h=0
    expected = 90.0 - abs(lat - dec)
    assert pos.altitude_deg == pytest.approx(expected, abs=0.2)


def test_northern_hemisphere_solar_noon_faces_south() -> None:
    dec = solar_declination_deg(SUMMER_SOLSTICE_DOY)
    pos = solar_position(37.5665, dec, hour_angle_deg(12.0))
    assert pos.azimuth_deg == pytest.approx(180.0, abs=1.0)


def test_afternoon_sun_is_west_of_south() -> None:
    dec = solar_declination_deg(SUMMER_SOLSTICE_DOY)
    pos = solar_position(37.5665, dec, hour_angle_deg(15.0))
    assert pos.azimuth_deg > 180.0  # 남쪽 지나 서쪽으로 이동


def test_morning_sun_is_east_of_south() -> None:
    dec = solar_declination_deg(SUMMER_SOLSTICE_DOY)
    pos = solar_position(37.5665, dec, hour_angle_deg(9.0))
    assert pos.azimuth_deg < 180.0


def test_arctic_circle_summer_solstice_is_midnight_sun() -> None:
    dec = solar_declination_deg(SUMMER_SOLSTICE_DOY)
    rng = daylight_hours_range(70.0, dec)  # 북위 70도, 북극권 안쪽
    assert rng == (-180.0, 180.0)


def test_arctic_circle_winter_solstice_is_polar_night() -> None:
    dec = solar_declination_deg(WINTER_SOLSTICE_DOY)
    rng = daylight_hours_range(70.0, dec)
    assert rng is None


def test_equator_equinox_daylight_is_12_hours() -> None:
    dec = solar_declination_deg(SPRING_EQUINOX_DOY)
    rng = daylight_hours_range(0.0, dec)
    assert rng is not None
    h0_neg, h0_pos = rng
    daylight_hours = (h0_pos - h0_neg) / 15.0
    assert daylight_hours == pytest.approx(12.0, abs=0.1)


def test_incidence_cosine_normal_incidence_is_one() -> None:
    # 태양이 정확히 면의 법선 방향에서 비출 때 cos(theta) = 1
    cos_theta = incidence_cosine(
        surface_tilt_deg=30.0,
        surface_azimuth_deg=180.0,
        sun_altitude_deg=60.0,  # 90 - 30
        sun_azimuth_deg=180.0,
    )
    assert cos_theta == pytest.approx(1.0, abs=1e-9)


def test_incidence_cosine_sun_below_horizon_is_zero() -> None:
    cos_theta = incidence_cosine(30.0, 180.0, sun_altitude_deg=-5.0, sun_azimuth_deg=180.0)
    assert cos_theta == 0.0


def test_incidence_cosine_flat_panel_equals_sin_altitude() -> None:
    # 수평(tilt=0) 패널의 입사각 코사인 = sin(고도각) (방위각 무관)
    cos_theta = incidence_cosine(0.0, 0.0, sun_altitude_deg=40.0, sun_azimuth_deg=123.0)
    assert cos_theta == pytest.approx(math.sin(math.radians(40.0)), abs=1e-6)
