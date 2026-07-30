"""
Vérifie que les opérations sensibles (enroll/identify/verify/delete)
sont bien journalisées dans l'audit log, avec les bonnes métadonnées,
et JAMAIS avec de donnée biométrique brute (image, descripteurs).
"""
import base64
import json
import os

import cv2
import numpy as np
from fastapi.testclient import TestClient


def _fingerprint_like_image_b64(seed: int) -> str:
    rng = np.random.default_rng(seed)
    image = rng.integers(0, 255, size=(300, 300), dtype=np.uint8)
    image = cv2.GaussianBlur(image, (5, 5), 0)
    for i in range(0, 300, 15):
        cv2.line(image, (0, i), (300, i), (255,), 1)
    success, encoded = cv2.imencode(".png", image)
    assert success
    return base64.b64encode(encoded.tobytes()).decode()


def _client():
    from app.main import app
    return TestClient(app)


def _signed_headers(body_dict: dict):
    from app.config import get_api_settings
    from app.security.auth import sign_request

    settings = get_api_settings()
    body_bytes = json.dumps(body_dict).encode()
    headers = sign_request(body_bytes, settings.SERVICE_AUTH_TOKEN)
    headers["Content-Type"] = "application/json"
    return headers, body_bytes


def _read_audit_lines() -> list[dict]:
    audit_dir = os.environ["AUDIT_LOG_DIR"]
    audit_file = os.path.join(audit_dir, "audit.log")
    if not os.path.exists(audit_file):
        return []
    with open(audit_file, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_enroll_success_is_audited():
    client = _client()
    image_b64 = _fingerprint_like_image_b64(seed=101)
    body = {"employeeId": "EMP_AUDIT_1", "fingerType": "right_index", "image": image_b64}
    headers, body_bytes = _signed_headers(body)

    response = client.post("/enroll", content=body_bytes, headers=headers)
    assert response.status_code == 200

    events = _read_audit_lines()
    enroll_events = [e for e in events if e["event"] == "enroll" and e["employeeId"] == "EMP_AUDIT_1"]
    assert len(enroll_events) == 1
    assert enroll_events[0]["success"] is True
    assert "timestamp" in enroll_events[0]
    assert "clientIp" in enroll_events[0]


def test_audit_never_contains_image_data():
    client = _client()
    image_b64 = _fingerprint_like_image_b64(seed=102)
    body = {"employeeId": "EMP_AUDIT_2", "fingerType": "left_thumb", "image": image_b64}
    headers, body_bytes = _signed_headers(body)
    client.post("/enroll", content=body_bytes, headers=headers)

    events = _read_audit_lines()
    for event in events:
        serialized = json.dumps(event)
        # L'image (base64) ne doit jamais transiter dans le log d'audit.
        assert image_b64 not in serialized


def test_delete_failure_is_audited():
    client = _client()
    body = {"employeeId": "EMP_JAMAIS_ENROLE"}
    headers, body_bytes = _signed_headers(body)

    response = client.post("/delete", content=body_bytes, headers=headers)
    assert response.status_code == 200

    events = _read_audit_lines()
    delete_events = [e for e in events if e["event"] == "delete" and e["employeeId"] == "EMP_JAMAIS_ENROLE"]
    assert len(delete_events) == 1
    assert delete_events[0]["success"] is False


def test_identify_no_match_is_audited():
    client = _client()
    image_b64 = _fingerprint_like_image_b64(seed=103)
    body = {"image": image_b64}
    headers, body_bytes = _signed_headers(body)

    response = client.post("/identify", content=body_bytes, headers=headers)
    assert response.status_code == 200

    events = _read_audit_lines()
    identify_events = [e for e in events if e["event"] == "identify"]
    assert len(identify_events) >= 1
    assert identify_events[-1]["success"] is False
