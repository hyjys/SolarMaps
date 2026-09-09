"""FNB58 실기 없이 파이프라인(샘플링 → 집계 → Firestore 업로드)을 테스트하기 위한 가짜 리더.

실제 태양광 발전 패턴(낮 동안 종 모양 곡선 + 잡음)을 흉내내므로, config.json에서
device.mode를 "simulator"로 두면 하드웨어 없이 앱 전체 파이프라인을 확인할 수 있다.
"""

from __future__ import annotations

import math
import random
import time
from datetime import datetime

from .base import PowerReader, Sample


class SimulatorReader(PowerReader):
    def __init__(self, rated_power_w: float = 30.0, panel_voltage_v: float = 5.0) -> None:
        self.rated_power_w = rated_power_w
        self.panel_voltage_v = panel_voltage_v
        self._t0 = time.monotonic()

    def open(self) -> None:
        pass

    def read(self) -> Sample | None:
        now = datetime.now()
        hour = now.hour + now.minute / 60
        # 06:00~18:00 사이 종 모양 곡선, 그 밖은 0에 가까운 잡음(야간).
        daylight = max(0.0, math.sin(math.pi * (hour - 6) / 12)) if 6 <= hour <= 18 else 0.0
        noise = random.uniform(-0.03, 0.03)
        ratio = max(0.0, min(1.0, daylight + noise))

        power_w = self.rated_power_w * ratio
        voltage_v = self.panel_voltage_v * random.uniform(0.98, 1.02)
        current_a = power_w / voltage_v if voltage_v > 0 else 0.0
        return Sample(voltage_v=voltage_v, current_a=current_a)

    def close(self) -> None:
        pass
