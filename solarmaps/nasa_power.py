"""NASA POWER 월별 기후평년 API 조회.

CORS 확인됨: access-control-allow-origin: * (2026-09-04 실측).
Climatology 엔드포인트는 2001-2020 20년 평년값을 월 단위로 제공하며,
ALLSKY_SFC_SW_DIFF(산란일사)를 직접 주므로 Erbs 상관식은 fallback으로만
쓴다.

CPython은 urllib으로, Pyodide는 pyodide.http.pyfetch로 조회한다 — 두 함수
모두 동일한 JSON 파싱/변환 로직(_parse_power_response)을 공유하므로
네트워크 계층만 갈아끼우면 된다. 네트워크가 없거나 API가 실패하면
climate.py의 쾨펜별 kt_fallback으로 대체한다(analyze() 호출부 책임).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from solarmaps.models import MonthlyClimate

POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"
POWER_PARAMETERS = "ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DIFF,CLRSKY_SFC_SW_DWN,T2M"

_MONTH_KEYS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def build_power_url(latitude_deg: float, longitude_deg: float) -> str:
    return (
        f"{POWER_BASE_URL}?parameters={POWER_PARAMETERS}"
        f"&community=RE&longitude={longitude_deg}&latitude={latitude_deg}&format=JSON"
    )


@dataclass(frozen=True)
class PowerFetchError(Exception):
    reason: str

    def __str__(self) -> str:  # pragma: no cover - 단순 위임
        return self.reason


def _parse_power_response(payload: dict) -> list[MonthlyClimate]:
    params = payload["properties"]["parameter"]
    ghi = params["ALLSKY_SFC_SW_DWN"]
    diffuse = params.get("ALLSKY_SFC_SW_DIFF", {})
    clearsky = params.get("CLRSKY_SFC_SW_DWN", {})
    t2m = params.get("T2M", {})

    result: list[MonthlyClimate] = []
    for i, key in enumerate(_MONTH_KEYS, start=1):
        g = ghi.get(key)
        if g is None or g <= -900:  # POWER fill_value = -999
            continue
        d = diffuse.get(key, 0.0)
        c = clearsky.get(key, g / 0.75 if g else 0.0)
        t = t2m.get(key, 15.0)
        result.append(
            MonthlyClimate(
                month=i,
                ghi_kwh_m2_day=float(g),
                diffuse_kwh_m2_day=float(d) if d is not None and d > -900 else 0.0,
                clearsky_ghi_kwh_m2_day=float(c) if c is not None and c > -900 else float(g) / 0.75,
                t_ambient_c=float(t) if t is not None and t > -900 else 15.0,
                source="nasa_power",
            )
        )
    if len(result) != 12:
        raise PowerFetchError(f"POWER 응답에 12개월 데이터가 모두 있지 않음 ({len(result)}개월만 수신)")
    return result


def fetch_monthly_climate_sync(latitude_deg: float, longitude_deg: float, timeout_sec: float = 10.0) -> list[MonthlyClimate]:
    """CPython 전용 동기 조회(urllib). pytest·시드 스크립트에서 사용."""
    import urllib.error
    import urllib.request

    url = build_power_url(latitude_deg, longitude_deg)
    try:
        with urllib.request.urlopen(url, timeout=timeout_sec) as resp:  # noqa: S310 (고정 HTTPS 공개 API)
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PowerFetchError(f"NASA POWER 조회 실패: {exc}") from exc
    return _parse_power_response(payload)


async def fetch_monthly_climate_async(latitude_deg: float, longitude_deg: float) -> list[MonthlyClimate]:
    """Pyodide 전용 비동기 조회(pyfetch). 브라우저(py-bridge.js)에서 await로 호출."""
    from pyodide.http import pyfetch  # type: ignore[import-not-found]

    url = build_power_url(latitude_deg, longitude_deg)
    try:
        response = await pyfetch(url)
        payload = await response.json()
    except Exception as exc:  # pyodide 예외 타입이 다양해 광범위하게 포착
        raise PowerFetchError(f"NASA POWER 조회 실패: {exc}") from exc
    return _parse_power_response(payload)
