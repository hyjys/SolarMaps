# SolarMaps Pi 노드

FNB58 USB-C 파워미터로 태양광 패널 발전량을 측정해 Firestore(`solar_stations`,
`solar_logs`)로 올린다. 스키마는 [../docs/DATA_SPEC.md](../docs/DATA_SPEC.md) §3 참고.

이 디렉터리만 Raspberry Pi Zero W에 그대로 복사해서 쓰면 된다(저장소 나머지는
웹 앱/계산 엔진용이라 Pi에는 필요 없음).

## 구성

```
pi/
  main.py                 실행 진입점 (샘플링 → 집계 → Firestore 업로드 루프)
  readers/
    base.py               Sample / PowerReader 인터페이스
    fnb58.py               FNB58 실기 리더 — vendor/openfnb58를 감싸는 어댑터
    simulator.py           하드웨어 없이 테스트용 가짜 리더
  vendor/openfnb58/
    fnb58.py               OpenFNB58 원본 그대로 (GPLv3) — 직접 수정하지 않음
    LICENSE, ORIGIN.md      출처·라이선스
  firestore_client.py     firebase-admin 또는 REST 폴백으로 Firestore 쓰기
  telemetry.py             Pi CPU 온도 / Wi-Fi 신호 세기
  config.example.json     설정 템플릿 (복사해서 config.json으로 사용)
  solarmaps-pi.service    systemd 유닛 (부팅 시 자동 시작)
```

## 설치 (Raspberry Pi OS)

```bash
sudo apt install -y libhidapi-hidraw0 python3-venv iw
cd /home/pi
git clone <이 저장소> solarmaps-src   # 또는 pi/ 폴더만 scp로 복사
cp -r solarmaps-src/pi solarmaps-pi
cd solarmaps-pi

python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## 설정

```bash
cp config.example.json config.json
```

`config.json`을 열어:
- `station.*`: 이 노드의 지점 정보(위치, 패널 제원) — `docs/DATA_SPEC.md`의 `SolarStation` 스키마와 동일
- `device.mode`: 처음엔 `"simulator"`로 두고 파이프라인부터 확인 권장. 실기 연결 후 `"fnb58"`로 전환
- `firebase.service_account_path`: Firebase 콘솔 → 프로젝트 설정 → 서비스 계정에서 발급한 JSON 키 경로
  (이 파일은 절대 git에 커밋하지 않는다 — `.gitignore`에 등록돼 있음)

서비스 계정 발급 절차는 [../docs/SETUP.md](../docs/SETUP.md) §5 참고.

## FNB58 프로토콜: OpenFNB58 사용

`readers/fnb58.py`는 자체 프로토콜 추정치가 아니라, 리버스엔지니어링으로
검증된 [OpenFNB58](https://github.com/yeckel/OpenFNB58)의 USB HID 구현을
그대로 감싸 쓴다. 실제 파일은 [vendor/openfnb58/fnb58.py](vendor/openfnb58/fnb58.py)에
수정 없이 복사돼 있고 ([ORIGIN.md](vendor/openfnb58/ORIGIN.md) — 출처·커밋·라이선스),
`readers/fnb58.py`는 그 모듈의 `find_hidraw`/`decode_packet` 등을 호출해
우리 `PowerReader` 인터페이스에 맞추는 얇은 어댑터일 뿐이다.

⚠️ **이 파일은 GPLv3다.** `pi/` 폴더를 배포·공개할 때는 이 라이선스 조건
(소스 공개, 라이선스 고지 유지)이 적용된다는 점을 알고 있어야 한다. 자세한
내용은 `vendor/openfnb58/ORIGIN.md` 참고.

### 준비물 (Linux/Raspberry Pi OS 전용, USB HID 방식)

```bash
sudo usermod -aG plugdev $USER   # /dev/hidraw* 접근 권한, 재로그인 필요
```

재로그인 후에도 `Cannot open /dev/hidraw0: permission denied`가 나면 `ls -l /dev/hidraw*`로
소유 그룹을 확인한다. `root root`뿐이고 `plugdev`가 안 붙어 있으면(배포판 기본 udev 규칙이
이 장치를 못 잡는 경우) FNB58 전용 udev 규칙을 추가해야 한다:

```bash
sudo tee /etc/udev/rules.d/99-fnb58.rules <<'EOF'
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="2e3c", ATTRS{idProduct}=="5558", MODE="0660", GROUP="plugdev"
EOF
sudo udevadm control --reload-rules
sudo udevadm trigger   # 또는 USB 케이블 재연결
```

### 연결 확인

```bash
cd pi
venv/bin/python vendor/openfnb58/fnb58.py --once      # 단발 측정값 확인
venv/bin/python readers/fnb58.py                      # 우리 어댑터로 확인
```

값이 정상적으로 나오면 `config.json`의 `device.mode`를 `"fnb58"`로 설정한다.
VID/PID(`2e3c:5558`)는 코드에 고정돼 있어 별도 설정이 필요 없다.

하드웨어가 아직 없거나 먼저 파이프라인만 검증하고 싶으면 `device.mode`를
`"simulator"`로 두면 된다(하드웨어 없이도 지도에 마커가 뜨고 값이 갱신되는지
확인 가능).

## 실행

```bash
venv/bin/python main.py config.json
```

정상 동작 시:
- `station_update_interval_s`(기본 5초)마다 `solar_stations/{station_id}` 문서가 갱신됨 →
  지도 앱의 마커 색상/팝업이 실시간으로 바뀐다.
- `log_interval_s`(기본 60초)마다 `solar_logs`에 1건씩 추가됨 → 마커 클릭 시 일일 발전 추이 차트에 반영.
- 앱은 `last_updated`가 5분 넘게 갱신 안 되면 해당 마커를 `OFFLINE`으로 표시한다
  (docs/DATA_SPEC.md §4) — 즉 Pi 쪽에서 `OFFLINE` 상태를 직접 쓸 필요는 없고,
  네트워크가 끊기면 이 루프가 계속 재시도하다가 자연히 앱이 OFFLINE으로 인식한다.

## 부팅 시 자동 시작 (systemd)

```bash
sudo cp solarmaps-pi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now solarmaps-pi
journalctl -u solarmaps-pi -f   # 로그 확인
```

## school_energy_summary는 여기서 다루지 않음

`school_energy_summary/latest`(학교 전체 자립률·탄소 저감량 집계, DATA_SPEC.md §3
컬렉션 4)는 여러 station의 데이터를 모아 계산하는 별도의 배치/집계 작업 몫이라
이 Pi 노드 코드 범위 밖이다. 현재는 `scripts/seed_firestore.py`로 목업 값을
넣어 대시보드 카드를 테스트하고 있고, 실제 집계 스크립트(Cloud Function 등)는
추후 별도로 구현하면 된다.
