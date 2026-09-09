"""전력 측정 리더 공통 인터페이스.

FNB58(실기)과 시뮬레이터(하드웨어 없이 테스트용)가 같은 인터페이스를 쓰도록 해서
main.py의 샘플링/집계/Firestore 업로드 로직이 어떤 리더를 쓰든 동일하게 동작한다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Sample:
    voltage_v: float
    current_a: float

    @property
    def power_w(self) -> float:
        return self.voltage_v * self.current_a


class PowerReader:
    """서브클래스는 open()/read()/close()만 구현하면 된다."""

    def open(self) -> None:
        raise NotImplementedError

    def read(self) -> Sample | None:
        """가장 최근 측정값 하나를 반환한다. 측정 불가 시 None."""
        raise NotImplementedError

    def close(self) -> None:
        pass

    def __enter__(self) -> "PowerReader":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()
