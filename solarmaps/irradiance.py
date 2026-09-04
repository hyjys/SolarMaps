"""일사 계산: 대기권외 일사, 청천지수, 산란/직달 분리, 경사면 전이.

참고 문헌:
- 대기권외 일사·일적산: Duffie & Beckman eq. 1.10.3, 1.10.4 (Spencer 이심율 보정)
- Erbs, D.G. et al. (1982), "Estimation of the diffuse radiation fraction
  for hourly, daily and monthly-average global radiation" — 청천지수 → 산란비율
  상관식 (POWER가 DIFF를 직접 주지 않을 때의 fallback)
- Hay, J.E. & Davies, J.A. (1980), "Calculation of the solar radiation
  incident on an inclined surface" — 이방성(주변광 포함) 경사면 전이 모형.
  등방 모형보다 정확하면서 Perez 모형처럼 다항 계수표가 필요 없어
  Pyodide 환경에 적합.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from solarmaps.geometry import (
    daylight_hours_range,
    hour_angle_deg,
    incidence_cosine,
    solar_declination_deg,
    solar_position,
    solar_time_hour,
)

SOLAR_CONSTANT_W_M2 = 1367.0


def eccentricity_correction(day_of_year: int) -> float:
    """지구 공전궤도 이심률에 의한 대기권외 일사 보정계수 E0 (Duffie&Beckman eq. 1.4.1b)."""
    b = 2.0 * math.pi * (day_of_year - 1) / 365.0
    return (
        1.000110
        + 0.034221 * math.cos(b)
        + 0.001280 * math.sin(b)
        + 0.000719 * math.cos(2 * b)
        + 0.000077 * math.sin(2 * b)
    )


def extraterrestrial_daily_kwh_m2(latitude_deg: float, day_of_year: int) -> float:
    """수평면 대기권외 일적산 일사량(kWh/m^2/day). Duffie & Beckman eq. 1.10.3."""
    dec = solar_declination_deg(day_of_year)
    rng = daylight_hours_range(latitude_deg, dec)
    if rng is None:
        return 0.0  # 극야

    lat = math.radians(latitude_deg)
    dec_rad = math.radians(dec)
    e0 = eccentricity_correction(day_of_year)

    if rng == (-180.0, 180.0):
        ws = math.pi  # 백야: 일출각을 종일(180도=pi rad)로 취급
    else:
        ws = math.radians(rng[1])

    h0_j = (
        (24.0 * 3600.0 / math.pi)
        * SOLAR_CONSTANT_W_M2
        * e0
        * (
            math.cos(lat) * math.cos(dec_rad) * math.sin(ws)
            + ws * math.sin(lat) * math.sin(dec_rad)
        )
    )
    return max(0.0, h0_j / 3_600_000.0)  # J -> kWh


def erbs_diffuse_fraction(clearness_index_kt: float) -> float:
    """Erbs et al. (1982) 일별 청천지수 → 산란비율(diffuse fraction) 상관식."""
    kt = max(0.0, min(1.0, clearness_index_kt))
    if kt <= 0.22:
        result = 1.0 - 0.09 * kt
    elif kt <= 0.80:
        result = 0.9511 - 0.1604 * kt + 4.388 * kt**2 - 16.638 * kt**3 + 12.336 * kt**4
    else:
        result = 0.165  # 매우 청천한 경우 최소 산란비율로 수렴 (Erbs 원 논문 상한 처리)
    return max(0.0, min(1.0, result))


@dataclass(frozen=True)
class HourlyPoaResult:
    hour: float
    ghi_w_m2: float
    poa_w_m2: float  # plane of array (경사면 전일사)
    cos_incidence: float


def hourly_poa_series(
    *,
    latitude_deg: float,
    longitude_deg: float,
    day_of_year: int,
    ghi_daily_kwh_m2: float,
    diffuse_daily_kwh_m2: float,
    surface_tilt_deg: float,
    surface_azimuth_deg: float,
    albedo: float,
    utc_offset_hours: float,
    hour_step: float = 1.0,
) -> list[HourlyPoaResult]:
    """일적산 GHI/산란을 시간대별로 분배하고 Hay-Davies로 경사면에 전이.

    월별 기후평년(NASA POWER)만 가진 상태에서 "하루의 대표일"을 만드는 근사다:
    일적산 값을 대기권외 순간 일사 형태에 비례 배분해 시간별 곡선을 복원한다.
    """
    dec = solar_declination_deg(day_of_year)
    rng = daylight_hours_range(latitude_deg, dec)
    if rng is None or ghi_daily_kwh_m2 <= 0:
        return []

    h0_daily_kwh = extraterrestrial_daily_kwh_m2(latitude_deg, day_of_year)
    if h0_daily_kwh <= 1e-6:
        return []

    ecc = eccentricity_correction(day_of_year)

    # 1차 패스: 각 시각의 대기권외 순간 일사(수평면)를 배분 가중치로 계산
    hours: list[float] = []
    weights: list[float] = []
    positions: list[tuple[float, float]] = []  # (altitude_deg, azimuth_deg)
    hour = 0.0
    while hour < 24.0:
        st = solar_time_hour(hour, longitude_deg, day_of_year, utc_offset_hours)
        h_deg = hour_angle_deg(st)
        pos = solar_position(latitude_deg, dec, h_deg)
        weight = SOLAR_CONSTANT_W_M2 * ecc * math.sin(math.radians(pos.altitude_deg)) if pos.altitude_deg > 0 else 0.0
        hours.append(hour)
        weights.append(max(0.0, weight))
        positions.append((pos.altitude_deg, pos.azimuth_deg))
        hour += hour_step

    total_weight = sum(weights)
    if total_weight <= 0:
        return []

    # 가중치 총합이 일적산 GHI(Wh/m^2)와 같아지도록 스케일
    ghi_daily_wh = ghi_daily_kwh_m2 * 1000.0
    scale = ghi_daily_wh / (total_weight * hour_step)

    diffuse_daily = max(0.0, min(diffuse_daily_kwh_m2, ghi_daily_kwh_m2))
    if ghi_daily_kwh_m2 > 0 and diffuse_daily_kwh_m2 > 0:
        diffuse_fraction_daily = diffuse_daily / ghi_daily_kwh_m2
    else:
        kt = max(0.0, min(1.2, ghi_daily_kwh_m2 / h0_daily_kwh))
        diffuse_fraction_daily = erbs_diffuse_fraction(kt)

    results: list[HourlyPoaResult] = []
    for h, w, (alt, az) in zip(hours, weights, positions, strict=True):
        ghi_w = w * scale
        if ghi_w <= 0 or alt <= 0:
            results.append(HourlyPoaResult(hour=h, ghi_w_m2=0.0, poa_w_m2=0.0, cos_incidence=0.0))
            continue

        cos_theta = incidence_cosine(surface_tilt_deg, surface_azimuth_deg, alt, az)
        diffuse_w = ghi_w * diffuse_fraction_daily
        direct_w = max(0.0, ghi_w - diffuse_w)
        i0_now = SOLAR_CONSTANT_W_M2 * ecc

        poa_w = _hay_davies_poa(
            direct_horizontal_w_m2=direct_w,
            diffuse_horizontal_w_m2=diffuse_w,
            ghi_w_m2=ghi_w,
            extraterrestrial_w_m2=i0_now,
            cos_incidence=cos_theta,
            sun_altitude_deg=alt,
            surface_tilt_deg=surface_tilt_deg,
            albedo=albedo,
        )
        results.append(HourlyPoaResult(hour=h, ghi_w_m2=ghi_w, poa_w_m2=poa_w, cos_incidence=cos_theta))

    return results


def _hay_davies_poa(
    *,
    direct_horizontal_w_m2: float,
    diffuse_horizontal_w_m2: float,
    ghi_w_m2: float,
    extraterrestrial_w_m2: float,
    cos_incidence: float,
    sun_altitude_deg: float,
    surface_tilt_deg: float,
    albedo: float,
) -> float:
    """Hay-Davies 이방성 모형: 직달 + (등방+주변광) 산란 + 지표반사.

    Hay & Davies (1980). 이방성 지수 Ai = 직달 수평성분 / 대기권외 수평 일사.
    """
    if sun_altitude_deg <= 0:
        return 0.0

    sin_alt = math.sin(math.radians(sun_altitude_deg))
    beam_normal = direct_horizontal_w_m2 / sin_alt if sin_alt > 1e-6 else 0.0
    direct_on_surface = beam_normal * cos_incidence

    anisotropy_index = direct_horizontal_w_m2 / extraterrestrial_w_m2 if extraterrestrial_w_m2 > 0 else 0.0
    anisotropy_index = max(0.0, min(1.0, anisotropy_index))

    beta_rad = math.radians(surface_tilt_deg)
    view_factor_sky = (1.0 + math.cos(beta_rad)) / 2.0

    circumsolar_ratio = cos_incidence / sin_alt if sin_alt > 1e-6 else 0.0
    circumsolar = diffuse_horizontal_w_m2 * anisotropy_index * circumsolar_ratio
    isotropic_sky = diffuse_horizontal_w_m2 * (1.0 - anisotropy_index) * view_factor_sky
    diffuse_on_surface = max(0.0, isotropic_sky + max(0.0, circumsolar))

    view_factor_ground = (1.0 - math.cos(beta_rad)) / 2.0
    reflected_on_surface = ghi_w_m2 * albedo * view_factor_ground

    return max(0.0, direct_on_surface + diffuse_on_surface + reflected_on_surface)
