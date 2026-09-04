"""쾨펜 코드 → 물리 파라미터 표.

이 표는 "지점 실측이 도착하기 전까지" 쓰는 1차 근사치다. 쾨펜 30개 분류
각각에 대해 논문 단위로 지점 측정된 albedo·soiling 데이터가 존재하지
않으므로, 아래 값은 그룹(A/B/C/D/E) 단위의 대표적 범위를 코드별 하위분류
(강수/기온 패턴)로 보정한 공학적 근사치다. 실측이 도착하면
calibration.py가 지점별 손실계수를 이 값 위에 얹어 보정한다.

참고 문헌:
- Chen, D. & Chen, H.W. (2013) — 쾨펜 분류 정의 및 코드 체계
- Duffie, J.A. & Beckman, W.A., *Solar Engineering of Thermal Processes*
  — 지표 알베도의 지피 유형별 대표값(설원 0.4-0.8, 초지 0.2-0.3, 사막 0.25-0.4 등)
- Sarver, T. et al. (2013), "A comprehensive review of the impact of dust
  on the use of solar energy" — 건조기후 오염손실이 습윤기후 대비 수배
  높다는 정성적 경향
- NREL PVWatts 기본 시스템손실 14%, ASHRAE IAM 계수 — energy.py에서 사용
"""

from __future__ import annotations

from solarmaps.constants import koppen_group
from solarmaps.models import ClimateParams

_ALL_MONTHS = tuple(range(1, 13))
_NH_WINTER = (11, 12, 1, 2, 3)  # 북반구 기준 표기. energy.py에서 남반구는 6개월 이동시켜 사용.


def _make(
    code: str,
    name_ko: str,
    albedo: float,
    soiling_rate: float,
    snow_months: tuple[int, ...],
    kt_fallback: float,
    diurnal_skew: float,
    notes: str,
) -> ClimateParams:
    return ClimateParams(
        code=code,
        name_ko=name_ko,
        albedo=albedo,
        soiling_rate=soiling_rate,
        snow_months=snow_months,
        kt_fallback=kt_fallback,
        diurnal_skew=diurnal_skew,
        notes=notes,
    )


_TABLE: dict[str, ClimateParams] = {
    # ── A: 열대 ── 짙은 식생, 잦은 강우로 오염 낮음, 습도 높아 청천지수 낮음
    "Af": _make("Af", "열대 우림", 0.16, 0.010, (), 0.44, 0.00,
                "연중 강한 대류운, 상시 다습. 오염은 잦은 비로 자정."),
    "Am": _make("Am", "열대 몬순", 0.17, 0.012, (), 0.46, 0.15,
                "우기 오후 집중호우형 대류운 → 오후 일사 저하(양의 diurnal_skew)."),
    "As": _make("As", "열대 사바나(건계 하계)", 0.19, 0.020, (), 0.52, -0.10,
                "건계에는 청천 우세."),
    "Aw": _make("Aw", "열대 사바나(건계 동계)", 0.19, 0.020, (), 0.52, 0.15,
                "우기 오후 대류운 발달 경향(Am과 유사한 비대칭)."),

    # ── B: 건조 ── 식생 희박, 지표 밝음, 청천지수 매우 높음, 먼지 오염 심함
    "BSh": _make("BSh", "스텝(고온)", 0.27, 0.045, (), 0.62, 0.00,
                 "반건조 나지, 황사성 먼지 축적이 습윤기후 대비 수 배."),
    "BSk": _make("BSk", "스텝(한랭)", 0.28, 0.035, (12, 1, 2), 0.60, 0.00,
                 "한랭 스텝은 겨울 강설 가능."),
    "BWh": _make("BWh", "사막(고온)", 0.32, 0.055, (), 0.68, 0.00,
                 "최고 청천지수·최고 오염손실 조합(Sarver et al. 2013 정성적 경향)."),
    "BWk": _make("BWk", "사막(한랭)", 0.30, 0.040, (12, 1, 2), 0.65, 0.00,
                 "고위도/고원 한랭사막, 동계 강설 가능."),

    # ── C: 온대 ── 계절 식생, 중간 정도 오염·알베도
    "Cfa": _make("Cfa", "온난 습윤", 0.19, 0.018, (), 0.50, 0.00,
                 "여름 습윤+겨울 온난, 연중 강수 고름."),
    "Cfb": _make("Cfb", "서안 해양성", 0.20, 0.015, (), 0.44, 0.00,
                 "잦은 강우·구름으로 청천지수 낮음(서유럽형)."),
    "Cfc": _make("Cfc", "냉량 해양성", 0.22, 0.014, (12, 1, 2), 0.42, 0.00,
                 "고위도 해양성, 짧고 서늘한 여름."),
    "Csa": _make("Csa", "지중해성(고온)", 0.21, 0.030, (), 0.58, 0.00,
                 "여름 건조·고온 → 오염 축적, 겨울 강우로 자정 반복."),
    "Csb": _make("Csb", "지중해성(온난)", 0.21, 0.025, (), 0.55, 0.00,
                 "Csa보다 여름이 서늘."),
    "Csc": _make("Csc", "지중해성(냉량)", 0.22, 0.022, (12, 1), 0.53, 0.00,
                 "고지대 지중해성, 드물게 저온."),
    "Cwa": _make("Cwa", "온대 계절풍", 0.19, 0.022, (), 0.52, 0.20,
                 "여름 몬순 오후 대류운, 겨울 건조 청천."),
    "Cwb": _make("Cwb", "온대 고원", 0.20, 0.020, (12, 1), 0.54, 0.15,
                 "고원 몬순형."),
    "Cwc": _make("Cwc", "온대 고산 계절풍", 0.21, 0.018, (12, 1, 2), 0.52, 0.15,
                 "고산 몬순형, 동계 저온."),

    # ── D: 대륙성 ── 뚜렷한 4계절, 겨울 적설이 지배적 손실 요인
    "Dfa": _make("Dfa", "습윤 대륙성(고온 여름)", 0.20, 0.016, (12, 1, 2), 0.50, 0.00,
                 "여름 습윤·고온, 겨울 적설."),
    "Dfb": _make("Dfb", "습윤 대륙성(온난 여름)", 0.22, 0.014, (11, 12, 1, 2, 3), 0.48, 0.00,
                 "적설기간이 Dfa보다 김(서울 인근 대표 기후)."),
    "Dfc": _make("Dfc", "아한대(냉량 여름)", 0.28, 0.012, (10, 11, 12, 1, 2, 3, 4), 0.50, 0.00,
                 "장기 적설, 여름 짧고 서늘."),
    "Dfd": _make("Dfd", "아한대(극한 겨울)", 0.35, 0.010, (9, 10, 11, 12, 1, 2, 3, 4, 5), 0.52, 0.00,
                 "시베리아형 극한 겨울, 장기간 적설 피복."),
    "Dsa": _make("Dsa", "대륙성 지중해(고온)", 0.21, 0.028, (12, 1, 2), 0.56, 0.00,
                 "여름 건조 대륙성."),
    "Dsb": _make("Dsb", "대륙성 지중해(온난)", 0.23, 0.024, (11, 12, 1, 2, 3), 0.54, 0.00, ""),
    "Dsc": _make("Dsc", "대륙성 지중해(냉량)", 0.27, 0.018, (10, 11, 12, 1, 2, 3, 4), 0.53, 0.00, ""),
    "Dsd": _make("Dsd", "대륙성 지중해(극한)", 0.32, 0.014, (9, 10, 11, 12, 1, 2, 3, 4), 0.53, 0.00, ""),
    "Dwa": _make("Dwa", "대륙성 계절풍(고온)", 0.20, 0.018, (12, 1, 2), 0.53, 0.10,
                 "여름 몬순 습윤, 겨울 건조 한랭(한반도 내륙형)."),
    "Dwb": _make("Dwb", "대륙성 계절풍(온난)", 0.23, 0.015, (11, 12, 1, 2, 3), 0.51, 0.10, ""),
    "Dwc": _make("Dwc", "아한대 계절풍", 0.29, 0.012, (10, 11, 12, 1, 2, 3, 4), 0.51, 0.05, ""),
    "Dwd": _make("Dwd", "아한대 계절풍(극한)", 0.36, 0.010, (9, 10, 11, 12, 1, 2, 3, 4, 5), 0.52, 0.05,
                 "동시베리아형, Dfd와 유사하게 극단적."),

    # ── E: 극지 ── 만년설/빙하, 알베도 최고, 대기 건조로 청천지수도 높음
    "EF": _make("EF", "빙설 기후", 0.65, 0.005, tuple(_ALL_MONTHS), 0.58, 0.00,
                "연중 빙설 피복. 발전량 자체가 패널 노출 여부에 크게 좌우됨(운영상 한계)."),
    "ET": _make("ET", "툰드라", 0.55, 0.008, (9, 10, 11, 12, 1, 2, 3, 4, 5), 0.56, 0.00,
                "짧은 여름에만 지표 노출."),
}


def get_climate_params(koppen_code: str) -> ClimateParams:
    """쾨펜 코드에 대응하는 파라미터를 반환. 미등록 코드는 소속 그룹의 평균으로 근사."""
    if koppen_code in _TABLE:
        return _TABLE[koppen_code]
    group = koppen_group(koppen_code)
    fallback_candidates = [p for c, p in _TABLE.items() if c.startswith(group)]
    if not fallback_candidates:
        raise KeyError(f"알 수 없는 쾨펜 코드: {koppen_code}")
    n = len(fallback_candidates)
    return ClimateParams(
        code=koppen_code,
        name_ko=f"{koppen_code} (그룹 {group} 평균 근사)",
        albedo=sum(p.albedo for p in fallback_candidates) / n,
        soiling_rate=sum(p.soiling_rate for p in fallback_candidates) / n,
        snow_months=fallback_candidates[0].snow_months,
        kt_fallback=sum(p.kt_fallback for p in fallback_candidates) / n,
        diurnal_skew=sum(p.diurnal_skew for p in fallback_candidates) / n,
        notes="미등록 세부코드 → 그룹 평균 근사치",
    )


def all_codes() -> list[str]:
    return sorted(_TABLE.keys())
