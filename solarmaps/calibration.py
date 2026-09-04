"""실측 ↔ 이론 보정.

규격서(docs/DATA_SPEC.md)의 solar_stations 문서는 설치각(tilt_angle_deg,
azimuth_deg)과 실시간 출력을 담고 있다. solar_logs에는 1분 주기 발전량이
쌓인다. 실측이 들어오기 시작하면, 이 모듈이 "그 설치각에서 이론 모형이
예측한 발전량"과 "실제 발전량"을 비교해 지점별 보정계수를 낸다.

지금은 실측이 없으므로(계획서 Context) 목업 데이터로 인터페이스만 검증한다.
station의 hardware.tilt_angle_deg/azimuth_deg를 optimizer의 단일角
평가 함수에 넣어 이론 발전량을 얻고, 실측 today_energy_wh 누적을 이론치와
비교해 손실계수를 산출하는 흐름이다.
"""

from __future__ import annotations

from dataclasses import dataclass

from solarmaps.koppen import load_grid
from solarmaps.optimizer import (
    _annual_energy_for_angle,
    build_fallback_monthly_climate,
)


@dataclass(frozen=True)
class StationCalibration:
    station_id: str
    theoretical_annual_kwh_m2: float
    measured_annual_kwh_m2: float | None
    calibration_factor: float | None  # measured / theoretical. None이면 실측 누적치 부족
    sample_days: int


def theoretical_yield_for_station(
    *,
    latitude_deg: float,
    longitude_deg: float,
    tilt_deg: float,
    azimuth_deg: float,
    utc_offset_hours: float,
    koppen_code: str | None = None,
) -> float:
    """설치 당시 고정 설치각으로 예상되는 연간 상대발전량(kWh/m^2 등가지표)."""
    if koppen_code is None:
        koppen_code = load_grid().lookup(latitude_deg, longitude_deg).code
    monthly_climate = build_fallback_monthly_climate(latitude_deg, koppen_code)
    energy, _ = _annual_energy_for_angle(
        monthly_climate,
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        utc_offset_hours=utc_offset_hours,
        tilt_deg=tilt_deg,
        azimuth_deg=azimuth_deg,
        koppen_code=koppen_code,
    )
    return energy


def calibrate_station(
    *,
    station_id: str,
    latitude_deg: float,
    longitude_deg: float,
    tilt_deg: float,
    azimuth_deg: float,
    utc_offset_hours: float,
    measured_daily_energy_wh: list[float],  # solar_logs에서 집계한 일별 today_energy_wh 시계열
    panel_area_m2: float,
    koppen_code: str | None = None,
) -> StationCalibration:
    """실측 일별 발전량 시계열로 이론 대비 보정계수를 산출.

    measured_daily_energy_wh가 비어 있으면(실측 미도착) calibration_factor=None을
    반환한다 — 프런트는 이 경우 "이론값" 배지를 계속 표시해야 한다(계획서 Phase 5).
    """
    theoretical_annual = theoretical_yield_for_station(
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        tilt_deg=tilt_deg,
        azimuth_deg=azimuth_deg,
        utc_offset_hours=utc_offset_hours,
        koppen_code=koppen_code,
    )

    n = len(measured_daily_energy_wh)
    if n == 0 or panel_area_m2 <= 0:
        return StationCalibration(
            station_id=station_id,
            theoretical_annual_kwh_m2=theoretical_annual,
            measured_annual_kwh_m2=None,
            calibration_factor=None,
            sample_days=0,
        )

    measured_avg_daily_wh_m2 = sum(measured_daily_energy_wh) / n / panel_area_m2
    measured_annual_kwh_m2 = measured_avg_daily_wh_m2 * 365.0 / 1000.0
    theoretical_daily_avg = theoretical_annual / 365.0
    factor = (measured_annual_kwh_m2 / 365.0) / theoretical_daily_avg if theoretical_daily_avg > 0 else None

    return StationCalibration(
        station_id=station_id,
        theoretical_annual_kwh_m2=theoretical_annual,
        measured_annual_kwh_m2=measured_annual_kwh_m2,
        calibration_factor=factor,
        sample_days=n,
    )
