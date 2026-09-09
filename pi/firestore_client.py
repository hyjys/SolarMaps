"""Pi → Firestore 업로드.

scripts/seed_firestore.py와 같은 패턴: firebase-admin(grpcio)이 설치돼 있으면
Admin SDK를, 아니면 google-auth + REST API로 자동 대체한다. Pi Zero W처럼
느린 기기에서 firebase-admin 설치/휠이 안 맞는 경우에도 동작하게 하기 위함.

firestore.rules는 클라이언트 SDK 경로의 쓰기를 막아 두지만, 여기서 쓰는
서비스 계정 인증(Admin SDK 또는 OAuth2 access token)은 그 규칙을 우회하는
관리자 권한 경로라 문제 없다 (docs/DATA_SPEC.md, docs/SETUP.md §5 참고).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _to_firestore_value(v: Any) -> dict:
    if isinstance(v, bool):
        return {"booleanValue": v}
    if isinstance(v, int):
        return {"integerValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, str):
        return {"stringValue": v}
    if isinstance(v, list):
        return {"arrayValue": {"values": [_to_firestore_value(x) for x in v]}}
    if isinstance(v, dict):
        return {"mapValue": {"fields": {k: _to_firestore_value(x) for k, x in v.items()}}}
    return {"nullValue": None}


class FirestoreClient:
    """set_station() / add_log()만 제공하는 최소 클라이언트."""

    def __init__(self, service_account_path: str, project_id: str | None = None) -> None:
        self._admin_db = None
        self._rest_project_id: str | None = None
        self._rest_creds = None

        cred_path = Path(service_account_path)
        if not cred_path.exists():
            raise FileNotFoundError(
                f"서비스 계정 키를 찾을 수 없음: {cred_path} "
                "(docs/SETUP.md §5 참고, .gitignore에 등록된 파일이므로 Pi에 직접 복사해야 함)"
            )

        try:
            import firebase_admin
            from firebase_admin import credentials, firestore

            cred = credentials.Certificate(str(cred_path))
            firebase_admin.initialize_app(cred, {"projectId": project_id} if project_id else None)
            self._admin_db = firestore.client()
            print("[firestore] firebase-admin SDK 사용")
        except ImportError:
            print("[firestore] firebase-admin 미설치 — REST API 폴백 사용")
            import google.auth
            import google.auth.transport.requests
            from google.oauth2 import service_account

            if project_id is None:
                project_id = json.loads(cred_path.read_text(encoding="utf-8")).get("project_id")
            self._rest_project_id = project_id
            self._rest_creds = service_account.Credentials.from_service_account_file(
                str(cred_path), scopes=["https://www.googleapis.com/auth/datastore"]
            )
            self._rest_creds.refresh(google.auth.transport.requests.Request())

    def _rest_token(self) -> str:
        import google.auth.transport.requests

        if not self._rest_creds.valid:
            self._rest_creds.refresh(google.auth.transport.requests.Request())
        return self._rest_creds.token

    def _rest_put(self, collection: str, doc_id: str, data: dict) -> None:
        base_url = (
            f"https://firestore.googleapis.com/v1/projects/{self._rest_project_id}"
            f"/databases/(default)/documents"
        )
        body = json.dumps({"fields": {k: _to_firestore_value(v) for k, v in data.items()}}).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/{collection}/{doc_id}",
            data=body,
            method="PATCH",
            headers={"Authorization": f"Bearer {self._rest_token()}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            resp.read()

    def _rest_add(self, collection: str, data: dict) -> None:
        base_url = (
            f"https://firestore.googleapis.com/v1/projects/{self._rest_project_id}"
            f"/databases/(default)/documents"
        )
        body = json.dumps({"fields": {k: _to_firestore_value(v) for k, v in data.items()}}).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/{collection}",
            data=body,
            method="POST",
            headers={"Authorization": f"Bearer {self._rest_token()}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            resp.read()

    def set_station(self, station_id: str, data: dict) -> None:
        """solar_stations/{station_id} 문서를 통째로 덮어쓴다."""
        if self._admin_db is not None:
            self._admin_db.collection("solar_stations").document(station_id).set(data)
        else:
            self._rest_put("solar_stations", station_id, data)

    def add_log(self, data: dict) -> None:
        """solar_logs에 자동 ID로 새 문서를 추가한다 (1분 주기 로그)."""
        if self._admin_db is not None:
            self._admin_db.collection("solar_logs").add(data)
        else:
            self._rest_add("solar_logs", data)
