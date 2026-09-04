"""물리 상수와 UI가 공유해야 하는 상수(팔레트, 임계값).

JS에서 이 값들을 다시 정의하지 않는다 — api.get_constants()로 내보내
지도 마커 색상, 쾨펜 범례 색상, 팝업 임계값을 여기서 단일하게 관리한다.
(계획서 "대원칙 1" / 규격서 §4 색상 매핑)
"""

from __future__ import annotations

# ── 태양 기하 ──────────────────────────────────────────────────────
SOLAR_CONSTANT_KWH_M2_DAY = 1.367 * 24 / 1000 * 1000  # 참고용, 실사용은 geometry.py의 시간별 적산
DEG2RAD = 0.017453292519943295
RAD2DEG = 57.29577951308232

# ── 패널/시스템 기본값 (범용 결정질 실리콘 패널 가정) ─────────────────
# 출처: Skoplaki & Palyvos (2009) NOCT 온도모형 리뷰의 대표값,
# 결정질 Si 온도계수 -0.4%/°C는 제조사 스펙시트 통용값(JRC PVGIS 기본값과 동일).
NOCT_C = 45.0
TEMP_COEFF_PER_C = -0.004
SYSTEM_LOSS_FRACTION = 0.14  # 배선·인버터·부정합 등 (PVGIS 기본 시스템손실 14%와 동일)
STC_IRRADIANCE_W_M2 = 1000.0
STC_TEMP_C = 25.0

# ── 최적화 탐색 ────────────────────────────────────────────────────
TILT_COARSE_STEP_DEG = 5.0
TILT_FINE_STEP_DEG = 0.5
TILT_MIN_DEG = 0.0
TILT_MAX_DEG = 90.0
AZIMUTH_COARSE_STEP_DEG = 15.0
AZIMUTH_FINE_STEP_DEG = 5.0

# ── 규격서 §4 마커 상태 임계값 (SolarStation.live_status 기준) ────────
# state 자체는 Pi/Firestore가 채우지만, 프런트가 색상을 분기할 임계값은
# 여기 한 곳에서만 정의한다.
MARKER_STATE_THRESHOLDS = {
    "GENERATING_HIGH": {"power_ratio_of_rated": 0.7, "color": "#10B981", "animation": "pulse"},
    "GENERATING_LOW": {"power_w_min": 0.5, "color": "#F59E0B", "animation": "none"},
    "IDLE": {"power_w_max": 0.5, "color": "#6B7280", "animation": "none"},
    "OFFLINE": {"stale_minutes": 5, "color": "#EF4444", "animation": "blink"},
}

# ── 쾨펜 1차 분류(그룹) 팔레트 — 지도 위 기후 오버레이/범례용 ─────────
# 색상은 통상적인 쾨펜-가이거 지도 관례(열대=파랑/초록, 건조=주황, 온대=노랑,
# 대륙=자홍/보라 계열, 극지=회색) 를 다크 테마 채도에 맞춰 조정.
KOPPEN_GROUP_COLORS = {
    "A": "#2E7D32",  # 열대
    "B": "#F9A825",  # 건조
    "C": "#8BC34A",  # 온대
    "D": "#7E57C2",  # 대륙성
    "E": "#90A4AE",  # 극지
}

KOPPEN_NAME_KO = {
    "Af": "열대 우림",
    "Am": "열대 몬순",
    "As": "열대 사바나(건계 하계)",
    "Aw": "열대 사바나(건계 동계)",
    "BSh": "스텝(고온)",
    "BSk": "스텝(한랭)",
    "BWh": "사막(고온)",
    "BWk": "사막(한랭)",
    "Cfa": "온난 습윤",
    "Cfb": "서안 해양성",
    "Cfc": "냉량 해양성",
    "Csa": "지중해성(고온)",
    "Csb": "지중해성(온난)",
    "Csc": "지중해성(냉량)",
    "Cwa": "온대 계절풍",
    "Cwb": "온대 고원",
    "Cwc": "온대 고산 계절풍",
    "Dfa": "습윤 대륙성(고온 여름)",
    "Dfb": "습윤 대륙성(온난 여름)",
    "Dfc": "아한대(냉량 여름)",
    "Dfd": "아한대(극한 겨울)",
    "Dsa": "대륙성 지중해(고온)",
    "Dsb": "대륙성 지중해(온난)",
    "Dsc": "대륙성 지중해(냉량)",
    "Dsd": "대륙성 지중해(극한)",
    "Dwa": "대륙성 계절풍(고온)",
    "Dwb": "대륙성 계절풍(온난)",
    "Dwc": "아한대 계절풍",
    "Dwd": "아한대 계절풍(극한)",
    "EF": "빙설 기후",
    "ET": "툰드라",
}


def koppen_group(code: str) -> str:
    """쾨펜 코드의 1차 분류 문자(A/B/C/D/E)를 반환."""
    return code[0] if code else "?"
