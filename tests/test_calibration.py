"""보정 인터페이스 검증(목업 데이터, 실측 도착 전)."""

from solarmaps.calibration import calibrate_station, theoretical_yield_for_station


def test_theoretical_yield_is_positive_for_typical_station() -> None:
    yield_kwh = theoretical_yield_for_station(
        latitude_deg=37.5665,
        longitude_deg=126.9780,
        tilt_deg=30.0,
        azimuth_deg=180.0,
        utc_offset_hours=9.0,
    )
    assert yield_kwh > 0


def test_calibration_without_measurements_returns_none_factor() -> None:
    result = calibrate_station(
        station_id="station_test_01",
        latitude_deg=37.5665,
        longitude_deg=126.9780,
        tilt_deg=30.0,
        azimuth_deg=180.0,
        utc_offset_hours=9.0,
        measured_daily_energy_wh=[],
        panel_area_m2=0.18,
    )
    assert result.calibration_factor is None
    assert result.measured_annual_kwh_m2 is None
    assert result.theoretical_annual_kwh_m2 > 0


def test_calibration_with_mock_measurements_produces_factor() -> None:
    # 규격서 §5 목업(30W 패널, today_energy_wh ~110)을 흉내낸 값
    result = calibrate_station(
        station_id="station_rooftop_main_01",
        latitude_deg=37.501234,
        longitude_deg=127.039876,
        tilt_deg=30.0,
        azimuth_deg=180.0,
        utc_offset_hours=9.0,
        measured_daily_energy_wh=[110.0, 105.0, 120.0, 98.0, 115.0],
        panel_area_m2=0.18,
    )
    assert result.calibration_factor is not None
    assert result.sample_days == 5
    assert result.measured_annual_kwh_m2 > 0
