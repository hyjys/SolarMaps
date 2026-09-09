"""FNB58 리더 — OpenFNB58(GPLv3, vendored) 프로토콜 구현을 감싸는 얇은 어댑터.

이전 버전은 FNB58 HID 프로토콜을 자체 추정치로 구현했으나, 실제로는
https://github.com/yeckel/OpenFNB58 에 리버스엔지니어링으로 검증된 구현이
이미 있다. 그 코드를 pi/vendor/openfnb58/fnb58.py 에 그대로 복사해 두고
(pi/vendor/openfnb58/ORIGIN.md — 출처·라이선스 GPLv3), 여기서는 그 모듈의
공개 함수(find_hidraw/open_hid/hid_write/hid_read/decode_packet 등)를 호출해
우리 PowerReader 인터페이스에 맞춰주기만 한다. 디코딩 로직 자체는 건드리지 않았다.

USB HID(`/dev/hidraw*`) 전용이라 Linux(Raspberry Pi OS)에서만 동작한다.
사용자를 `plugdev` 그룹에 넣어야 root 없이 접근 가능 (pi/README.md 참고).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from .base import PowerReader, Sample

_VENDOR_DIR = Path(__file__).resolve().parent.parent / "vendor" / "openfnb58"
if str(_VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(_VENDOR_DIR))

import fnb58 as openfnb58  # noqa: E402 — vendored OpenFNB58 (GPLv3)


class FNB58Reader(PowerReader):
    """OpenFNB58의 USB HID 프로토콜로 FNB58을 읽는다.

    read()는 60ms 이내에 새 데이터가 없으면 None을 반환한다(호출 쪽에서
    다음 루프까지 기다리면 됨) — main.py의 "샘플 없으면 이번 틱은 건너뜀"
    루프와 맞춘 논블로킹 동작.
    """

    def __init__(self, poll_interval_s: float = 1.0) -> None:
        self.poll_interval_s = poll_interval_s
        self._fd: int | None = None
        self._next_poll = 0.0
        self._queue: list[dict] = []

    def open(self) -> None:
        path = openfnb58.find_hidraw()
        self._fd = openfnb58.open_hid(path)
        if not openfnb58._hid_init(self._fd):  # noqa: SLF001 — vendored helper, drain+INIT1+INIT2×2
            raise RuntimeError("FNB58 초기화 명령 전송 실패 — 연결/권한을 확인하세요")
        self._next_poll = time.time()

    def read(self) -> Sample | None:
        if self._fd is None:
            raise RuntimeError("open()을 먼저 호출해야 합니다")

        if self._queue:
            s = self._queue.pop(0)
            return Sample(voltage_v=s["voltage_V"], current_a=s["current_A"])

        now = time.time()
        if now >= self._next_poll:
            openfnb58.hid_write(self._fd, openfnb58.CMD_POLL)
            self._next_poll = now + self.poll_interval_s

        timeout = max(0.05, min(1.0, self._next_poll - time.time()))
        data = openfnb58.hid_read(self._fd, timeout=timeout)
        if data is None:
            return None

        samples = openfnb58.decode_packet(data)
        if not samples:
            return None

        self._queue = samples
        s = self._queue.pop(0)
        return Sample(voltage_v=s["voltage_V"], current_a=s["current_A"])

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None


if __name__ == "__main__":
    # 단독 실행 시 빠른 연결 확인용. 좀 더 자세한 디버깅(raw 패킷 덤프,
    # BLE 모드, 트리거 등)은 vendor/openfnb58/fnb58.py를 직접 실행:
    #   python pi/vendor/openfnb58/fnb58.py --once
    with FNB58Reader() as reader:
        print("FNB58 측정 시작 (Ctrl+C로 종료)")
        try:
            while True:
                sample = reader.read()
                if sample is not None:
                    print(f"V={sample.voltage_v:.3f}V  I={sample.current_a:.3f}A  P={sample.power_w:.3f}W")
        except KeyboardInterrupt:
            pass
