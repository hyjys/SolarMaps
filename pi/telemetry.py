"""라즈베리파이 자체 상태(CPU 온도, Wi-Fi 신호) — DATA_SPEC.md §3 telemetry 필드."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_THERMAL_ZONE = Path("/sys/class/thermal/thermal_zone0/temp")


def cpu_temp_c() -> float | None:
    try:
        raw = _THERMAL_ZONE.read_text().strip()
        return int(raw) / 1000.0
    except (FileNotFoundError, ValueError):
        pass

    # 개발 PC(리눅스가 아니거나 thermal_zone0가 없는 경우)를 위한 폴백.
    try:
        out = subprocess.run(
            ["vcgencmd", "measure_temp"], capture_output=True, text=True, timeout=2
        ).stdout
        m = re.search(r"[\d.]+", out)
        return float(m.group()) if m else None
    except (FileNotFoundError, subprocess.SubprocessError):
        return None


def wifi_rssi_dbm(interface: str = "wlan0") -> float | None:
    try:
        out = subprocess.run(
            ["iw", "dev", interface, "link"], capture_output=True, text=True, timeout=2
        ).stdout
        m = re.search(r"signal:\s*(-?\d+)\s*dBm", out)
        return float(m.group(1)) if m else None
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
