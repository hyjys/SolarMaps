"""태양 기하: 적위, 시간각, 입사각.

전부 표준 라이브러리 math만 사용하는 닫힌 형태 근사식이다. 브라우저에서
Pyodide로 실행해도 되는 정도로 가벼우면서, 최적 경사각 계산에 필요한
정밀도는 충분하다.

참고 문헌:
- Spencer, J.W. (1971) 적위 푸리에 근사 — Cooper(1969) 근사보다 정확
  (Duffie & Beckman, *Solar Engineering of Thermal Processes*, 4th ed., eq. 1.6.1b)
- 균시차: Spencer(1971) 계수 (Duffie & Beckman eq. 1.5.3)
- 입사각 코사인 공식: Duffie & Beckman eq. 1.6.2
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_TWO_PI = 2.0 * math.pi


def day_angle_rad(day_of_year: int) -> float:
    """1/1=1 인 연중일을 라디안 각도로. 365일 기준(윤년 오차는 무시할 수준)."""
    return _TWO_PI * (day_of_year - 1) / 365.0


def solar_declination_deg(day_of_year: int) -> float:
    """Spencer(1971) 푸리에 근사. 결과 단위는 도(°)."""
    g = day_angle_rad(day_of_year)
    delta_rad = (
        0.006918
        - 0.399912 * math.cos(g)
        + 0.070257 * math.sin(g)
        - 0.006758 * math.cos(2 * g)
        + 0.000907 * math.sin(2 * g)
        - 0.002697 * math.cos(3 * g)
        + 0.00148 * math.sin(3 * g)
    )
    return math.degrees(delta_rad)


def equation_of_time_min(day_of_year: int) -> float:
    """균시차(분). Spencer(1971) 근사, Duffie & Beckman eq. 1.5.3."""
    g = day_angle_rad(day_of_year)
    e = (
        229.18
        * (
            0.000075
            + 0.001868 * math.cos(g)
            - 0.032077 * math.sin(g)
            - 0.014615 * math.cos(2 * g)
            - 0.040849 * math.sin(2 * g)
        )
    )
    return e


def solar_time_hour(clock_hour: float, longitude_deg: float, day_of_year: int, utc_offset_hours: float) -> float:
    """표준시(clock_hour, 시)를 태양시(진태양시, 시)로 변환.

    longitude_deg: 동경 양수. utc_offset_hours: 해당 표준시간대(예: KST=+9).
    """
    standard_meridian_deg = utc_offset_hours * 15.0
    eot = equation_of_time_min(day_of_year)
    time_correction_min = 4.0 * (longitude_deg - standard_meridian_deg) + eot
    return clock_hour + time_correction_min / 60.0


def hour_angle_deg(solar_time_hour_value: float) -> float:
    """태양시 12시를 0으로 하는 시간각(°). 오전 음수, 오후 양수."""
    return 15.0 * (solar_time_hour_value - 12.0)


@dataclass(frozen=True)
class SolarPosition:
    altitude_deg: float  # 태양 고도각 (지평선=0, 천정=90)
    zenith_deg: float
    azimuth_deg: float  # 북=0, 동=90, 남=180, 서=270 (모델 전체의 방위각 규약과 일치)


def solar_position(latitude_deg: float, declination_deg: float, hour_angle_deg_value: float) -> SolarPosition:
    """위도·적위·시간각으로부터 태양 고도·방위각을 계산.

    방위각은 북=0/동=90/남=180/서=270 규약(규격서 §3 hardware.azimuth_deg와 동일)을
    쓰기 위해, 통상 남=0 기준의 표준 공식 결과에 180°를 더해 변환한다.
    """
    lat = math.radians(latitude_deg)
    dec = math.radians(declination_deg)
    h = math.radians(hour_angle_deg_value)

    sin_alt = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(h)
    sin_alt = max(-1.0, min(1.0, sin_alt))
    altitude = math.asin(sin_alt)

    if altitude <= 0:
        return SolarPosition(altitude_deg=math.degrees(altitude), zenith_deg=90.0 - math.degrees(altitude), azimuth_deg=180.0)

    cos_az_south = (sin_alt * math.sin(lat) - math.sin(dec)) / (math.cos(altitude) * math.cos(lat))
    cos_az_south = max(-1.0, min(1.0, cos_az_south))
    az_south = math.acos(cos_az_south)  # 0..pi, 남=0 기준, 부호 미정(크기만)
    if h < 0:  # 오전은 남쪽 기준 동쪽(음의 방향). 오후(h>0)는 양의 부호를 그대로 사용.
        az_south = -az_south

    azimuth_north_based = (math.degrees(az_south) + 180.0) % 360.0

    return SolarPosition(
        altitude_deg=math.degrees(altitude),
        zenith_deg=90.0 - math.degrees(altitude),
        azimuth_deg=azimuth_north_based,
    )


def incidence_cosine(
    surface_tilt_deg: float,
    surface_azimuth_deg: float,
    sun_altitude_deg: float,
    sun_azimuth_deg: float,
) -> float:
    """경사면 입사각의 코사인. 태양이 지평선 아래거나 면 뒤쪽이면 0.

    surface_azimuth_deg, sun_azimuth_deg 모두 북=0/동=90/남=180/서=270 규약.
    Duffie & Beckman eq. 1.6.2 (면-법선 입사각 코사인)와 동치.
    """
    if sun_altitude_deg <= 0:
        return 0.0

    beta = math.radians(surface_tilt_deg)
    theta_z = math.radians(90.0 - sun_altitude_deg)
    gamma = math.radians(sun_azimuth_deg - surface_azimuth_deg)

    cos_theta = (
        math.cos(theta_z) * math.cos(beta)
        + math.sin(theta_z) * math.sin(beta) * math.cos(gamma)
    )
    return max(0.0, cos_theta)


def daylight_hours_range(latitude_deg: float, declination_deg: float) -> tuple[float, float] | None:
    """일출~일몰의 시간각 범위(°, -180..180). 극야면 None, 백야면 (-180, 180)."""
    lat = math.radians(latitude_deg)
    dec = math.radians(declination_deg)
    cos_h0 = -math.tan(lat) * math.tan(dec)
    if cos_h0 <= -1.0:
        return (-180.0, 180.0)  # 백야: 종일 태양이 지지 않음
    if cos_h0 >= 1.0:
        return None  # 극야: 종일 태양이 뜨지 않음
    h0 = math.degrees(math.acos(cos_h0))
    return (-h0, h0)
