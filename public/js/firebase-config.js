// Firebase 프로젝트 생성 후 이 값을 채운다 (docs/SETUP.md 참고).
// Firebase 콘솔 > 프로젝트 설정 > 일반 > "내 앱" > SDK 설정 및 구성 에서 복사.
//
// 채워지기 전까지는 firestore.js가 구독을 건너뛰고 지도/최적각 계산 기능은
// 그대로 동작한다 — 모니터링 기능만 비활성화된다.

export const firebaseConfig = {
  apiKey: "",
  authDomain: "",
  projectId: "",
  storageBucket: "",
  messagingSenderId: "",
  appId: "",
};

export function isFirebaseConfigured() {
  return Boolean(firebaseConfig.projectId && firebaseConfig.apiKey);
}
