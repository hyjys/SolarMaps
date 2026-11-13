// Firestore 실시간 구독과 서버 조회 공용 래퍼.

import { firebaseConfig, isFirebaseConfigured } from "./firebase-config.js?v=3";

let appPromise = null;

async function getApp() {
  if (!isFirebaseConfigured()) return null;
  if (!appPromise) {
    appPromise = (async () => {
      const { initializeApp } = await import("https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js");
      return initializeApp(firebaseConfig);
    })().catch((err) => {
      appPromise = null;
      throw err;
    });
  }
  return appPromise;
}

export async function fetchCollectionFromServer(collectionPath) {
  const app = await getApp();
  if (!app) throw new Error("Firebase 미설정");

  const { getFirestore, collection, getDocsFromServer } = await import(
    "https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js"
  );
  const snapshot = await getDocsFromServer(collection(getFirestore(app), collectionPath));
  return snapshot.docs.map((doc) => ({ id: doc.id, data: doc.data() }));
}

// collectionPath: "solar_stations" 등. handler(docs: Array<{id, data}>) 콜백.
// 반환값은 unsubscribe 함수(또는 미설정 시 no-op).
export async function subscribe(collectionPath, handler) {
  const app = await getApp();
  if (!app) {
    console.info(`[firestore] Firebase 미설정 — ${collectionPath} 구독 건너뜀`);
    return () => {};
  }
  const { getFirestore, collection, onSnapshot } = await import(
    "https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js"
  );
  const db = getFirestore(app);
  return onSnapshot(collection(db, collectionPath), (snapshot) => {
    const docs = snapshot.docs.map((d) => ({ id: d.id, data: d.data() }));
    handler(docs);
  });
}

// 단일 문서 구독 (school_energy_summary/latest 등).
export async function subscribeDoc(collectionPath, docId, handler) {
  const app = await getApp();
  if (!app) {
    console.info(`[firestore] Firebase 미설정 — ${collectionPath}/${docId} 구독 건너뜀`);
    return () => {};
  }
  const { getFirestore, doc, onSnapshot } = await import(
    "https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js"
  );
  const db = getFirestore(app);
  return onSnapshot(doc(db, collectionPath, docId), (snap) => {
    handler(snap.exists() ? snap.data() : null);
  });
}
