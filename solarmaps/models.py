"""엔진 전역에서 쓰는 데이터 구조."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClimateParams:
    """쾨펜 코드 하나에 대응하는 물리 파라미터 (climate.py의 표에서 채워짐)."""

    code: str
    name_ko: str
    albedo: float  # 지표 반사율 (0..1)
    soiling_rate: float  # 월간 오염에 의한 출력 손실률 (0..1)
    snow_months: tuple[int, ...]  # 적설 손실이 발생하는 월(1-12, 북반구 기준 표기)
    kt_fallback: float  # NASA POWER 조회 실패 시 사용할 평균 청천지수
    diurnal_skew: float  # 오전(-) / 오후(+) 운량 비대칭. 0 = 대칭
    notes: str = ""  # 문헌 근거


@dataclass(frozen=True)
class MonthlyClimate:
    """지점 1개월치 기후평년 값 (NASA POWER 또는 fallback에서 채워짐)."""

    month: int  # 1-12
    ghi_kwh_m2_day: float  # 수평면 전일사량 일평균
    diffuse_kwh_m2_day: float  # 수평면 산란일사량 일평균
    clearsky_ghi_kwh_m2_day: float  # 청천 수평면 일사량 일평균
    t_ambient_c: float  # 월평균 기온
    source: str  # "nasa_power" | "climate_fallback"


@dataclass(frozen=True)
class SiteInput:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class MonthlyYield:
    month: int
    energy_kwh_m2: float  # 해당 월 단위면적당 발전량 추정치(패널 효율 반영 전, 상대비교용)
    poa_kwh_m2_day: float  # 경사면 전일사량 일평균 (plane of array)


@dataclass(frozen=True)
class AzimuthLossPoint:
    azimuth_deg: float
    loss_percent: float  # 최적 방위각 대비 손실률(%)


@dataclass(frozen=True)
class OptimalResult:
    latitude: float
    longitude: float
    koppen_code: str
    koppen_name_ko: str
    tilt_deg: float
    azimuth_deg: float  # 북=0, 동=90, 남=180, 서=270 (규격서 §3 hardware.azimuth_deg 규약)
    annual_energy_kwh_m2: float
    gain_vs_flat_percent: float  # 수평 설치(0도) 대비 이득
    monthly: list[MonthlyYield] = field(default_factory=list)
    azimuth_loss_curve: list[AzimuthLossPoint] = field(default_factory=list)
    azimuth_symmetric_model: bool = True  # True면 방위각이 대칭 모형 산출값(정직화 경고용)
    climate_source: str = "climate_fallback"
