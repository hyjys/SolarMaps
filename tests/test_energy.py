"""손실 모형 검증."""

import pytest

from solarmaps.climate import get_climate_params
from solarmaps.energy import (
    ashrae_iam,
    cell_temperature_c,
    month_is_snow_affected,
    monthly_energy_from_hourly,
    temperature_loss_factor,
)
from solarmaps.irradiance import hourly_poa_series


def test_ashrae_iam_normal_incidence_is_near_one() -> None:
    assert ashrae_iam(1.0) == pytest.approx(1.0, abs=1e-6)


def test_ashrae_iam_grazing_incidence_is_low() -> None:
    assert ashrae_iam(0.1) < 0.6


def test_ashrae_iam_behind_panel_is_zero() -> None:
    assert ashrae_iam(0.0) == 0.0
    assert ashrae_iam(-0.3) == 0.0


def test_cell_temperature_rises_with_irradiance() -> None:
    low = cell_temperature_c(200.0, 20.0)
    high = cell_temperature_c(900.0, 20.0)
    assert high > low


def test_temperature_loss_factor_below_one_when_hot() -> None:
    assert temperature_loss_factor(60.0) < 1.0


def test_temperature_loss_factor_above_one_when_cold() -> None:
    assert temperature_loss_factor(0.0) > 1.0


def test_temperature_loss_factor_is_one_at_stc() -> None:
    assert temperature_loss_factor(25.0) == pytest.approx(1.0)


def test_snow_month_detection_northern_hemisphere() -> None:
    dfb = get_climate_params("Dfb")  # snow_months include 12,1,2 등
    assert month_is_snow_affected(1, dfb, latitude_deg=37.5) is True
    assert month_is_snow_affected(7, dfb, latitude_deg=37.5) is False


def test_snow_month_detection_southern_hemisphere_shifts_six_months() -> None:
    dfb = get_climate_params("Dfb")
    # 남반구에서는 계절이 반전되므로, 원래 1월(겨울)이 7월에 대응해야 함
    assert month_is_snow_affected(7, dfb, latitude_deg=-33.9) is True
    assert month_is_snow_affected(1, dfb, latitude_deg=-33.9) is False


def test_monthly_energy_is_nonnegative_and_finite() -> None:
    climate = get_climate_params("Cfa")
    series = hourly_poa_series(
        latitude_deg=35.0,
        longitude_deg=129.0,
        day_of_year=172,
        ghi_daily_kwh_m2=5.5,
        diffuse_daily_kwh_m2=2.0,
        surface_tilt_deg=30.0,
        surface_azimuth_deg=180.0,
        albedo=climate.albedo,
        utc_offset_hours=9.0,
    )
    result = monthly_energy_from_hourly(
        series,
        month=6,
        ambient_temp_c=24.0,
        climate=climate,
        latitude_deg=35.0,
        days_in_month=30,
        surface_tilt_deg=30.0,
    )
    assert result.effective_kwh_m2 >= 0
    assert result.effective_kwh_m2 < result.poa_kwh_m2 * 1.5  # 손실계수들이 폭주하지 않았는지
    assert result.avg_cell_temp_c > 24.0  # 셀온도는 항상 주변온도보다 높아야 함(양의 일사 시간대 평균)


def test_snow_increases_loss_in_affected_month() -> None:
    climate = get_climate_params("Dfc")  # 적설월이 넓은 기후
    common = dict(
        latitude_deg=45.0,
        longitude_deg=10.0,
        surface_tilt_deg=20.0,
        surface_azimuth_deg=180.0,
        albedo=climate.albedo,
        utc_offset_hours=1.0,
        diffuse_daily_kwh_m2=1.0,
        ghi_daily_kwh_m2=2.0,
    )
    winter_series = hourly_poa_series(day_of_year=15, **common)  # 1월, 적설월
    summer_series = hourly_poa_series(day_of_year=196, **common)  # 7월, 비적설월

    winter = monthly_energy_from_hourly(
        winter_series, month=1, ambient_temp_c=-5.0, climate=climate,
        latitude_deg=45.0, days_in_month=31, surface_tilt_deg=20.0,
    )
    summer = monthly_energy_from_hourly(
        summer_series, month=7, ambient_temp_c=18.0, climate=climate,
        latitude_deg=45.0, days_in_month=31, surface_tilt_deg=20.0,
    )
    # 손실 배율만 비교하기 위해 POA 대비 유효발전 비율을 확인
    winter_ratio = winter.effective_kwh_m2 / winter.poa_kwh_m2 if winter.poa_kwh_m2 else 0
    summer_ratio = summer.effective_kwh_m2 / summer.poa_kwh_m2 if summer.poa_kwh_m2 else 0
    assert winter_ratio < summer_ratio
