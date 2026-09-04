# 물리 모델

SolarMaps의 `solarmaps/` 패키지가 계산하는 방식과 근거 문헌을 정리한다.
전체 흐름: **위치 → 쾨펜 기후 분류 → 월별 기후평년(일사·기온) → 태양 기하 →
경사면 일사 → 손실 반영 발전량 → (경사각, 방위각) 탐색**.

## 1. 쾨펜 기후 분류 ([solarmaps/koppen.py](../solarmaps/koppen.py))

[koppen/](../koppen/) 폴더의 0.5도 격자 데이터(Chen & Chen 2013, `p1981_2010` 컬럼)를
이진 조회 테이블(`public/data/koppen.bin`)로 변환해 사용한다. 클릭 지점이 바다 등
미분류 셀이면 최근접 육지 셀을 나선 탐색으로 찾는다.

## 2. 태양 기하 ([solarmaps/geometry.py](../solarmaps/geometry.py))

- 적위: Spencer(1971) 푸리에 근사
- 균시차: Spencer(1971) 근사
- 태양 고도·방위각: Duffie & Beckman, *Solar Engineering of Thermal Processes* eq. 1.6.5 계열
- 방위각 규약: 북=0°, 동=90°, 남=180°, 서=270° (규격서 `hardware.azimuth_deg`와 동일)

## 3. 일사 ([solarmaps/irradiance.py](../solarmaps/irradiance.py))

- 대기권외 일적산: Duffie & Beckman eq. 1.10.3
- 산란/직달 분리: NASA POWER가 `ALLSKY_SFC_SW_DIFF`를 직접 주면 그 값을 쓰고,
  없으면 Erbs et al. (1982) 상관식으로 청천지수에서 추정
- 경사면 전이: **Hay-Davies (1980)** 이방성 모형 — 직달 + (등방+주변광)산란 + 지표반사.
  Perez 모형보다 단순하면서 등방 모형보다 정확해 Pyodide 환경에 적합

## 4. 손실 모형 ([solarmaps/energy.py](../solarmaps/energy.py))

| 손실 요인 | 근거 |
| --- | --- |
| 셀온도(NOCT) | Duffie & Beckman eq. 23.3.5, Skoplaki & Palyvos (2009) 리뷰 |
| 온도계수 -0.4%/°C | 결정질 Si 제조사 스펙시트 통용값 (PVGIS/PVWatts 기본값과 동일) |
| 입사각수정(IAM) | ASHRAE(2013) b0=0.05 근사 |
| 오염(soiling) | 쾨펜별 정성적 근사 — 건조기후(B)가 습윤기후보다 수 배 높음 (Sarver et al. 2013 정성적 경향) |
| 적설(snow) | 경사각의 연속함수로 근사(0도 35% 손실 → 60도 5% 손실). Andrews & Pearce (2013) 정성적 결과 참고 |
| 시스템손실 | PVWatts 기본값 14% (배선·인버터·부정합 등 일괄) |

## 5. 최적화 ([solarmaps/optimizer.py](../solarmaps/optimizer.py))

경사각 0~90도를 5도 격자로 전수조사한 뒤, 최적점 근방을 0.5도 격자로 재탐색한다
(2단계 조밀→정밀 탐색). 목적함수는 연간 총 손실반영발전량.

### 방위각의 한계

월별 기후평년만으로는 하루 오전/오후가 대칭이라 최적 방위각이 항상 적도 방향
(북반구 180°, 남반구 0°)으로 수렴한다. 이는 계산 오류가 아니라 입력 데이터의
본질적 한계이며, 결과 화면에 `azimuth_symmetric_model: true`로 명시하고
방위각 이탈 손실 곡선(±90도)을 함께 제공해 실무적 판단을 돕는다.

## 6. 검증

`tests/`의 각 테스트는 해석해(춘분 남중고도, 백야/극야 경계 등) 또는 정성적 경향
(위도가 높을수록 최적 경사각이 커진다 등)을 확인한다. 절대 오차보다 물리적으로
타당한 방향을 가리키는지를 우선한다 — 실측 데이터 도착 전까지는 정밀한 문헌값
일치가 목표가 아니라, 신뢰할 수 있는 1차 근사가 목표다.

실측 예시(2026-09-04): 서울(37.5665, 126.978)에서 NASA POWER 실측 기후평년 기준
경사각 32.5°, PVGIS 공개 참고값(~33-34°)과 근접함을 확인.

## 7. 실측 보정 ([solarmaps/calibration.py](../solarmaps/calibration.py))

실측 데이터가 들어오면(규격서 `solar_logs` 컬렉션), 설치 당시 고정 설치각으로
계산한 이론 발전량과 실측 발전량을 비교해 지점별 보정계수를 산출한다. 현재는
목업 데이터로 인터페이스만 검증된 상태이며, 실측이 쌓이면 결과 패널에
"이론값 / 실측 보정값" 토글로 노출할 예정이다.
