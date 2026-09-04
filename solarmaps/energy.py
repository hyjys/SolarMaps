"""경사면 일사(POA)로부터 상대 발전량을 추정한다.

여기서 산출하는 값은 "단위 정격출력당 상대 에너지"이며, 최적화(optimizer.py)의
비교 목적에는 절대 스케일이 중요하지 않다 — 경사각/방위각 사이의 상대적
우열만 정확하면 된다. 실제 kWh 절대값이 필요해지는 시점(실측 보정)은
calibration.py가 지점별 계수로 맞춘다.

참고 문헌:
- NOCT 셀온도모형: Duffie & Beckman eq. 23.3.5 / Skoplaki & Palyvos (2009) 리뷰
- 결정질 실리콘 온도계수 -0.4%/°C: 제조사 스펙시트 통용값, PVGIS/PVWatts 기본값과 동일
- ASHRAE 입사각수정계수(IAM): ASHRAE(2013) b0=0.05 근사 (Duffie&Beckman eq. 6.17.1)
- 오염(soiling)·적설(snow) 손실: climate.py의 쾨펜별 근사치를 곱셈 손실로 적용
"""

from __future__ import annotations

from dataclasses import dataclass

from solarmaps.constants import (
    NOCT_C,
    STC_IRRADIANCE_W_M2,
    STC_TEMP_C,
    SYSTEM_LOSS_FRACTION,
    TEMP_COEFF_PER_C,
)
from solarmaps.irradiance import HourlyPoaResult
from solarmaps.models import ClimateParams

ASHRAE_IAM_B0 = 0.05


def ashrae_iam(cos_incidence: float) -> float:
    """ASHRAE 입사각수정계수. cos_incidence<=0(면 뒤쪽/일몰)이면 0."""
    if cos_incidence <= 1e-4:
        return 0.0
    return max(0.0, 1.0 - ASHRAE_IAM_B0 * (1.0 / cos_incidence - 1.0))


def cell_temperature_c(poa_w_m2: float, ambient_temp_c: float) -> float:
    """NOCT 모형: Tcell = Tamb + (NOCT-20)/800 * POA."""
    return ambient_temp_c + (NOCT_C - 20.0) / 800.0 * poa_w_m2


def temperature_loss_factor(cell_temp_c: float) -> float:
    """STC(25도) 대비 온도손실 계수. 음의 온도계수이므로 저온에서는 1보다 커질 수 있음."""
    return 1.0 + TEMP_COEFF_PER_C * (cell_temp_c - STC_TEMP_C)


def month_is_snow_affected(month: int, climate: ClimateParams, latitude_deg: float) -> bool:
    """월이 해당 지점의 적설 영향월에 해당하는지. 남반구는 climate 표(북반구 기준)를 6개월 이동."""
    effective_month = month
    if latitude_deg < 0:
        effective_month = ((month - 1 + 6) % 12) + 1
    return effective_month in climate.snow_months


_SNOW_LOSS_AT_FLAT = 0.35  # 경사각 0도(수평)에서의 적설 피복 손실 비율
_SNOW_LOSS_AT_STEEP = 0.05  # 경사각 60도 이상에서 잔류하는 손실 비율(완전히 사라지지는 않음)
# 근거: Andrews & Pearce (2013), "The effect of snowfall on solar photovoltaic
# performance"의 정성적 결과 — 저경사각일수록 적설 잔류로 월간 손실이 커지고
# 고경사각(눈이 미끄러지는 각도)에서는 대부분 해소됨. 정확한 비율은 지역별로
# 편차가 크므로(폭설·습설·건설 등) 온건한 중앙값을 채택했다. 쾨펜 세부코드별
# 차등화(Dwa의 짧은 3개월 경미한 적설 vs Dfd의 9개월 극한 적설)는 snow_months
# 개월수로 이미 반영되므로, 월별 손실 강도 자체는 climate.py에서 굳이
# 재조정하지 않는다.
_SNOW_LOSS_STEEP_TILT_DEG = 60.0


def _snow_loss_fraction(surface_tilt_deg: float) -> float:
    """적설 손실을 경사각의 연속함수로 근사: 경사가 클수록 눈이 미끄러져 손실이 선형으로 줄어듦.

    계단함수(특정 임계각에서 손실이 급변)로 두면 최적화 탐색이 물리적 의미 없이
    그 임계각으로 튀는 인위적 결과를 낳으므로, 0~60도 구간을 선형 보간한다.
    """
    t = max(0.0, min(_SNOW_LOSS_STEEP_TILT_DEG, surface_tilt_deg))
    frac = t / _SNOW_LOSS_STEEP_TILT_DEG
    return _SNOW_LOSS_AT_FLAT + (_SNOW_LOSS_AT_STEEP - _SNOW_LOSS_AT_FLAT) * frac


@dataclass(frozen=True)
class MonthlyEnergyResult:
    month: int
    poa_kwh_m2: float  # 손실 반영 전 순수 경사면 일사 누적
    effective_kwh_m2: float  # 온도·오염·적설·IAM 손실을 반영한 상대 발전량 지표
    avg_cell_temp_c: float


def monthly_energy_from_hourly(
    hourly_series: list[HourlyPoaResult],
    *,
    month: int,
    ambient_temp_c: float,
    climate: ClimateParams,
    latitude_deg: float,
    days_in_month: int,
    surface_tilt_deg: float,
) -> MonthlyEnergyResult:
    """하루 대표 시계열(hourly_series)을 해당 월의 일수만큼 적산해 월간 상대 발전량을 계산."""
    if not hourly_series:
        return MonthlyEnergyResult(month=month, poa_kwh_m2=0.0, effective_kwh_m2=0.0, avg_cell_temp_c=ambient_temp_c)

    daily_poa_wh = 0.0
    daily_effective_wh = 0.0
    temp_samples: list[float] = []
    hour_step = hourly_series[1].hour - hourly_series[0].hour if len(hourly_series) > 1 else 1.0

    for r in hourly_series:
        if r.poa_w_m2 <= 0:
            continue
        cell_t = cell_temperature_c(r.poa_w_m2, ambient_temp_c)
        temp_samples.append(cell_t)
        temp_factor = temperature_loss_factor(cell_t)
        iam_factor = ashrae_iam(r.cos_incidence)

        effective_w = r.poa_w_m2 * temp_factor * iam_factor
        daily_poa_wh += r.poa_w_m2 * hour_step
        daily_effective_wh += effective_w * hour_step

    soiling_factor = 1.0 - climate.soiling_rate
    snow_factor = 1.0 - _snow_loss_fraction(surface_tilt_deg) if month_is_snow_affected(
        month, climate, latitude_deg
    ) else 1.0
    system_factor = 1.0 - SYSTEM_LOSS_FRACTION

    monthly_poa_kwh = (daily_poa_wh / 1000.0) * days_in_month
    monthly_effective_kwh = (daily_effective_wh / 1000.0) * days_in_month * soiling_factor * snow_factor * system_factor

    avg_temp = sum(temp_samples) / len(temp_samples) if temp_samples else ambient_temp_c

    return MonthlyEnergyResult(
        month=month,
        poa_kwh_m2=monthly_poa_kwh,
        effective_kwh_m2=monthly_effective_kwh,
        avg_cell_temp_c=avg_temp,
    )


def normalize_to_stc_reference(effective_kwh_m2: float) -> float:
    """STC 기준(1000 W/m^2)으로 정규화한 '피크시간(peak sun hours)' 등가값.

    실제 패널 정격출력(W)을 곱하면 kWh로 환산되지만, 여기서는 상대비교용
    지표로만 사용하므로 곱셈 계수 없이 반환한다.
    """
    return effective_kwh_m2 / (STC_IRRADIANCE_W_M2 / 1000.0)
