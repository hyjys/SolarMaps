# Firebase 프로젝트 설정

SolarMaps는 Firebase Hosting(정적 파일 서빙)과 Firestore(실측 데이터 저장소)를 사용합니다.
아직 프로젝트가 없으므로 아래 순서로 생성합니다.

## 1. 프로젝트 생성

1. https://console.firebase.google.com 접속 → "프로젝트 추가"
2. 프로젝트 이름 입력 (예: `solarmaps-hafs`) → 프로젝트 ID가 자동 생성됨 (예: `solarmaps-hafs-a1b2c`)
3. Google Analytics는 필요 없으므로 꺼도 무방
4. 요금제는 **Spark(무료)** 로 충분 — Hosting + Firestore 읽기/쓰기 정도의 사용량은 무료 한도 내

## 2. 웹 앱 등록

1. 프로젝트 개요 → `</>` (웹 아이콘) 클릭
2. 앱 닉네임 입력 (예: `SolarMaps Web`) → Firebase Hosting 설정은 건너뛰어도 됨(CLI로 별도 진행)
3. 표시되는 `firebaseConfig` 객체를 복사

```js
const firebaseConfig = {
  apiKey: "...",
  authDomain: "...",
  projectId: "...",
  storageBucket: "...",
  messagingSenderId: "...",
  appId: "...",
};
```

4. 이 값을 [public/js/firebase-config.js](../public/js/firebase-config.js)의 `firebaseConfig` 객체에 붙여넣기

## 3. Firestore 활성화

1. 좌측 메뉴 "Firestore Database" → "데이터베이스 만들기"
2. 위치는 `asia-northeast3(서울)` 권장 (지연시간)
3. 보안 규칙은 일단 "테스트 모드"로 시작해도 되지만, 배포 전 `firestore.rules`를 적용해야 함 (아래 4번)

## 4. Firebase CLI 연결

```bash
npm install -g firebase-tools
firebase login
```

프로젝트 루트의 `.firebaserc`에서 `REPLACE_WITH_YOUR_PROJECT_ID`를 실제 프로젝트 ID로 교체:

```json
{ "projects": { "default": "solarmaps-hafs-a1b2c" } }
```

Firestore 규칙/인덱스 배포:

```bash
firebase deploy --only firestore:rules,firestore:indexes
```

## 5. Pi(FNB58) 쪽 쓰기 권한

`firestore.rules`는 클라이언트 쓰기를 전면 차단합니다(공개 읽기 전용 대시보드).
Raspberry Pi에서 Firestore에 쓰려면 **서비스 계정**을 발급해 Admin SDK로 접근해야 합니다.

1. 프로젝트 설정 → 서비스 계정 → "새 비공개 키 생성" → JSON 다운로드
2. 이 파일은 **절대 커밋하지 않음** (`.gitignore`에 `serviceAccountKey.json` 등록됨)
3. Pi 쪽 코드(별도 팀원 담당, [docs/DATA_SPEC.md](DATA_SPEC.md) 참고)에서 이 키로 Admin SDK 초기화

## 6. 목업 데이터 시드 (로컬 테스트용)

```bash
venv/Scripts/python scripts/seed_firestore.py
```

`GOOGLE_APPLICATION_CREDENTIALS` 환경변수로 서비스 계정 키 경로를 지정하거나,
프로젝트 루트에 `serviceAccountKey.json`을 두면 자동으로 인식합니다.

## 7. 배포

```bash
firebase deploy --only hosting
```

배포 전 반드시 빌드 산출물을 최신화:

```bash
venv/Scripts/python scripts/build.py
```
