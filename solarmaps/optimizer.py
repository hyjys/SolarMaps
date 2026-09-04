"""(경사각, 방위각) 탐색으로 연간 최적 설치각을 찾는다.

탐색은 조밀(5도) 격자 전수조사 → 그 근방을 정밀(0.5도) 격자로 재탐색하는
2단계 방식이다. 목적함수(연간 총 상대발전량)가 경사각·방위각 각각에 대해
단봉(unimodal)이라 국소최적에 빠질 위험이 낮고, 12개월 x 24시간 x 격자점
수 규모에서도 순수 파이썬으로 충분히 빠르다(계획서 성능 추산 참고).

방위각의 정직한 처리(계획서 "방위각에 대한 정직한 처리"):
월별 기후평년만 쓰면 하루 중 오전/오후가 대칭이라 최적 방위각은 항상
적도 방향으로 수렴한다. 이를 감추지 않고 azimuth_symmetric_model=True로
결과에 명시하며, 손실 곡선(±각도별 발전량 손실 %)을 함께 제공한다.
"""

from __future__ import annotations

import calendar

from solarmaps.climate import get_climate_params
from solarmaps.constants import (
    AZIMUTH_COARSE_STEP_DEG,
    AZIMUTH_FINE_STEP_DEG,
    TILT_COARSE_STEP_DEG,
    TILT_FINE_STEP_DEG,
    TILT_MAX_DEG,
    TILT_MIN_DEG,
)
from solarmaps.energy import monthly_energy_from_hourly
from solarmaps.irradiance import (
    erbs_diffuse_fraction,
    extraterrestrial_daily_kwh_m2,
    hourly_poa_series,
)
from solarmaps.models import AzimuthLossPoint, MonthlyClimate, MonthlyYield, OptimalResult

# 각 월의 대표일(연중일). 월평균 일사와 가장 근접한 날짜를 쓰는 Klein(1977) 관례.
REPRESENTATIVE_DAY_OF_YEAR = {1: 17, 2: 47, 3: 75, 4: 105, 5: 135, 6: 162, 7: 198, 8: 228, 9: 258, 10: 288, 11: 318, 12: 344}

_DUE_SOUTH = 180.0
_DUE_NORTH = 0.0


def default_azimuth_for_hemisphere(latitude_deg: float) -> float:
    """대칭 모형에서의 기본(적도 방향) 방위각. 북반구=남향180, 남반구=북향0."""
    return _DUE_SOUTH if latitude_deg >= 0 else _DUE_NORTH


def build_fallback_monthly_climate(latitude_deg: float, koppen_code: str) -> list[MonthlyClimate]:
    """NASA POWER 조회 실패 시: 쾨펜 청천지수(kt_fallback)로 월별 기후를 근사 생성.

    대기권외 일사(H0)에 쾨펜별 대표 청천지수를 곱해 GHI를 만들고, Erbs로
    산란을 분리한다. 기온은 위도 기반 대략치(적도 27도 -> 극지 -15도 선형)로 근사.
    """
    climate = get_climate_params(koppen_code)
    result: list[MonthlyClimate] = []
    for month, doy in REPRESENTATIVE_DAY_OF_YEAR.items():
        h0 = extraterrestrial_daily_kwh_m2(latitude_deg, doy)
        ghi = h0 * climate.kt_fallback
        diffuse_fraction = erbs_diffuse_fraction(climate.kt_fallback)
        diffuse = ghi * diffuse_fraction
        clearsky = h0 * 0.75  # 대기권외 대비 청천 대기투과율 근사(Duffie&Beckman 전형값)

        # 아주 거친 기온 근사: 위도가 높을수록, 겨울일수록 낮아짐(부호는 반구 반영)
        seasonal_phase = 1.0 if latitude_deg >= 0 else -1.0
        month_offset = (month - 7) * seasonal_phase  # 7월을 반구별 "한여름"으로 정렬
        seasonal_swing = 15.0 * (1 - abs(latitude_deg) / 90.0) if abs(latitude_deg) < 90 else 0
        t_base = 27.0 - 0.55 * abs(latitude_deg)
        t_ambient = t_base - seasonal_swing * 0.5 + seasonal_swing * 0.5 * (1 - 2 * abs(month_offset) / 6.0)

        result.append(
            MonthlyClimate(
                month=month,
                ghi_kwh_m2_day=max(0.1, ghi),
                diffuse_kwh_m2_day=max(0.0, diffuse),
                clearsky_ghi_kwh_m2_day=max(0.1, clearsky),
                t_ambient_c=t_ambient,
                source="climate_fallback",
            )
        )
    return result


def _annual_energy_for_angle(
    monthly_climate: list[MonthlyClimate],
    *,
    latitude_deg: float,
    longitude_deg: float,
    utc_offset_hours: float,
    tilt_deg: float,
    azimuth_deg: float,
    koppen_code: str,
) -> tuple[float, list[MonthlyYield]]:
    climate = get_climate_params(koppen_code)
    total = 0.0
    monthly_yields: list[MonthlyYield] = []

    for mc in monthly_climate:
        doy = REPRESENTATIVE_DAY_OF_YEAR[mc.month]
        series = hourly_poa_series(
            latitude_deg=latitude_deg,
            longitude_deg=longitude_deg,
            day_of_year=doy,
            ghi_daily_kwh_m2=mc.ghi_kwh_m2_day,
            diffuse_daily_kwh_m2=mc.diffuse_kwh_m2_day,
            surface_tilt_deg=tilt_deg,
            surface_azimuth_deg=azimuth_deg,
            albedo=climate.albedo,
            utc_offset_hours=utc_offset_hours,
        )
        days = calendar.monthrange(2023, mc.month)[1]  # 평년 월 일수(비윤년 기준으로 고정)
        monthly = monthly_energy_from_hourly(
            series,
            month=mc.month,
            ambient_temp_c=mc.t_ambient_c,
            climate=climate,
            latitude_deg=latitude_deg,
            days_in_month=days,
            surface_tilt_deg=tilt_deg,
        )
        total += monthly.effective_kwh_m2
        poa_daily_avg = monthly.poa_kwh_m2 / days if days else 0.0
        monthly_yields.append(
            MonthlyYield(month=mc.month, energy_kwh_m2=monthly.effective_kwh_m2, poa_kwh_m2_day=poa_daily_avg)
        )

    return total, monthly_yields


def _search_tilt_azimuth(
    monthly_climate: list[MonthlyClimate],
    *,
    latitude_deg: float,
    longitude_deg: float,
    utc_offset_hours: float,
    koppen_code: str,
    azimuth_fixed: float | None,
) -> tuple[float, float, float, list[MonthlyYield]]:
    """조밀 → 정밀 2단계 격자탐색. azimuth_fixed가 주어지면 방위각은 고정."""

    def evaluate(tilt: float, azimuth: float) -> tuple[float, list[MonthlyYield]]:
        return _annual_energy_for_angle(
            monthly_climate,
            latitude_deg=latitude_deg,
            longitude_deg=longitude_deg,
            utc_offset_hours=utc_offset_hours,
            tilt_deg=tilt,
            azimuth_deg=azimuth,
            koppen_code=koppen_code,
        )

    def frange(start: float, stop: float, step: float) -> list[float]:
        n = int(round((stop - start) / step))
        return [start + i * step for i in range(n + 1)]

    azimuths_coarse = [azimuth_fixed] if azimuth_fixed is not None else frange(0.0, 360.0 - AZIMUTH_COARSE_STEP_DEG, AZIMUTH_COARSE_STEP_DEG)

    best_tilt, best_az, best_energy, best_monthly = 0.0, azimuths_coarse[0], -1.0, []
    for tilt in frange(TILT_MIN_DEG, TILT_MAX_DEG, TILT_COARSE_STEP_DEG):
        for az in azimuths_coarse:
            energy, monthly = evaluate(tilt, az)
            if energy > best_energy:
                best_tilt, best_az, best_energy, best_monthly = tilt, az, energy, monthly

    tilt_fine_range = frange(max(TILT_MIN_DEG, best_tilt - TILT_COARSE_STEP_DEG), min(TILT_MAX_DEG, best_tilt + TILT_COARSE_STEP_DEG), TILT_FINE_STEP_DEG)
    if azimuth_fixed is not None:
        az_fine_range = [azimuth_fixed]
    else:
        az_fine_range = frange(best_az - AZIMUTH_COARSE_STEP_DEG, best_az + AZIMUTH_COARSE_STEP_DEG, AZIMUTH_FINE_STEP_DEG)
        az_fine_range = [a % 360.0 for a in az_fine_range]

    for tilt in tilt_fine_range:
        for az in az_fine_range:
            energy, monthly = evaluate(tilt, az)
            if energy > best_energy:
                best_tilt, best_az, best_energy, best_monthly = tilt, az, energy, monthly

    return best_tilt, best_az, best_energy, best_monthly


def compute_azimuth_loss_curve(
    monthly_climate: list[MonthlyClimate],
    *,
    latitude_deg: float,
    longitude_deg: float,
    utc_offset_hours: float,
    koppen_code: str,
    optimal_tilt_deg: float,
    optimal_azimuth_deg: float,
    optimal_energy: float,
    step_deg: float = 15.0,
    span_deg: float = 90.0,
) -> list[AzimuthLossPoint]:
    """최적 방위각을 중심으로 ±span_deg를 훑어 손실률(%) 곡선을 만든다."""
    points: list[AzimuthLossPoint] = []
    offset = -span_deg
    while offset <= span_deg + 1e-9:
        az = (optimal_azimuth_deg + offset) % 360.0
        energy, _ = _annual_energy_for_angle(
            monthly_climate,
            latitude_deg=latitude_deg,
            longitude_deg=longitude_deg,
            utc_offset_hours=utc_offset_hours,
            tilt_deg=optimal_tilt_deg,
            azimuth_deg=az,
            koppen_code=koppen_code,
        )
        loss_pct = (1.0 - energy / optimal_energy) * 100.0 if optimal_energy > 0 else 0.0
        points.append(AzimuthLossPoint(azimuth_deg=offset, loss_percent=max(0.0, loss_pct)))
        offset += step_deg
    return points


def optimize(
    *,
    latitude_deg: float,
    longitude_deg: float,
    koppen_code: str,
    koppen_name_ko: str,
    monthly_climate: list[MonthlyClimate],
    utc_offset_hours: float,
    precise_azimuth_mode: bool = False,
) -> OptimalResult:
    """최적 (경사각, 방위각)을 계산해 OptimalResult로 반환.

    precise_azimuth_mode=False(기본): 대칭 모형이므로 방위각은 반구 기본값(180/0)으로
    고정하고 경사각만 탐색한다 — 어차피 대칭 모형은 항상 적도 방향을 반환하므로,
    이 편이 계산량을 줄이면서 azimuth_symmetric_model=True 임을 명확히 한다.
    precise_azimuth_mode=True: 방위각도 함께 탐색한다(시간별 비대칭 데이터를 쓸 때 대비).
    """
    climate_source = monthly_climate[0].source if monthly_climate else "climate_fallback"
    azimuth_fixed = None if precise_azimuth_mode else default_azimuth_for_hemisphere(latitude_deg)

    best_tilt, best_az, best_energy, best_monthly = _search_tilt_azimuth(
        monthly_climate,
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        utc_offset_hours=utc_offset_hours,
        koppen_code=koppen_code,
        azimuth_fixed=azimuth_fixed,
    )

    flat_energy, _ = _annual_energy_for_angle(
        monthly_climate,
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        utc_offset_hours=utc_offset_hours,
        tilt_deg=0.0,
        azimuth_deg=best_az,
        koppen_code=koppen_code,
    )
    gain_pct = ((best_energy / flat_energy) - 1.0) * 100.0 if flat_energy > 0 else 0.0

    loss_curve = compute_azimuth_loss_curve(
        monthly_climate,
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        utc_offset_hours=utc_offset_hours,
        koppen_code=koppen_code,
        optimal_tilt_deg=best_tilt,
        optimal_azimuth_deg=best_az,
        optimal_energy=best_energy,
    )

    return OptimalResult(
        latitude=latitude_deg,
        longitude=longitude_deg,
        koppen_code=koppen_code,
        koppen_name_ko=koppen_name_ko,
        tilt_deg=best_tilt,
        azimuth_deg=best_az,
        annual_energy_kwh_m2=best_energy,
        gain_vs_flat_percent=gain_pct,
        monthly=best_monthly,
        azimuth_loss_curve=loss_curve,
        azimuth_symmetric_model=not precise_azimuth_mode,
        climate_source=climate_source,
    )
