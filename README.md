# SolarMaps

HAFS 유리프(유레카 리서치 프로젝트) 산출물. 지도에서 위치를 클릭하면 위도·경도와
쾨펜 기후 구분을 이용해 그 지점의 최적 태양광 패널 설치 각도(경사각·방위각)를
계산해 보여주는 웹 앱이다.

- **지도**: OpenStreetMap + Leaflet
- **호스팅/DB**: Firebase Hosting + Firestore
- **계산 엔진**: 파이썬(표준 라이브러리만 사용), 브라우저에서 **Pyodide**로 실행
- **기후 데이터**: 쾨펜 기후 분류(Chen & Chen 2013) + NASA POWER 월별 기후평년
- **실측 연동**: FNB58 → Raspberry Pi Zero W → Firestore (팀원 별도 구축, [docs/DATA_SPEC.md](docs/DATA_SPEC.md))

물리 모델 상세와 문헌 근거는 [docs/MODEL.md](docs/MODEL.md) 참고.

## 개발 환경 설정

```bash
python -m venv venv
venv/Scripts/pip install -r requirements.txt
```

## 빌드

쾨펜 이진 격자와 Pyodide용 zip을 생성한다 (`public/data/`, `public/py/`는 git에 커밋하지 않음):

```bash
venv/Scripts/python scripts/build.py
```

## 테스트

```bash
venv/Scripts/python -m pytest tests/ -v
```

## 로컬 실행

```bash
venv/Scripts/python -m http.server 8080 --directory public
```

브라우저에서 http://localhost:8080 접속 → 지도 클릭.

## Firebase 설정

프로젝트가 아직 없다면 [docs/SETUP.md](docs/SETUP.md)를 따라 생성한다.
모니터링 기능(발전소 마커·대시보드)은 Firebase 설정 전까지 자동으로 비활성화되며,
지도·최적각 계산 기능은 그대로 동작한다.

## 디렉터리 구조

```
solarmaps/     계산 엔진 (표준 라이브러리만 사용, CPython/Pyodide 겸용)
scripts/       빌드·시드 스크립트
tests/         pytest
koppen/        쾨펜 기후 원본 데이터 (Chen & Chen 2013)
public/        Firebase Hosting 루트 (index.html, css/, js/)
docs/          모델 문서, 데이터 규격서, Firebase 설정 가이드
```

## 배포

```bash
venv/Scripts/python scripts/build.py
firebase deploy
```
