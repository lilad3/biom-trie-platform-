import base64
import json

import cv2
import numpy as np
import pytest
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


@pytest.fixture
def client():
    # Import tardif : nécessaire pour que la fixture isolated_env (conftest)
    # ait déjà positionné les variables d'environnement avant que
    # app.main / biometric_core.config ne les lisent.
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


def test_health_requires_no_auth(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_enroll_without_signature_rejected(client):
    response = client.post("/enroll", json={
        "employeeId": "EMP001", "fingerType": "right_index", "image": "irrelevant",
    })
    assert response.status_code == 422  # headers requis manquants


def test_enroll_then_identify_flow(client):
    image_b64 = _fingerprint_like_image_b64(seed=7)
    enroll_body = {"employeeId": "EMP001", "fingerType": "right_index", "image": image_b64}
    headers, body_bytes = _signed_headers(enroll_body)

    enroll_response = client.post("/enroll", content=body_bytes, headers=headers)
    assert enroll_response.status_code == 200
    assert enroll_response.json()["success"] is True

    # Identifier avec la MÊME image doit retrouver EMP001
    identify_body = {"image": image_b64}
    headers2, body_bytes2 = _signed_headers(identify_body)
    identify_response = client.post("/identify", content=body_bytes2, headers=headers2)
    assert identify_response.status_code == 200
    result = identify_response.json()
    assert result["success"] is True
    assert result["employeeId"] == "EMP001"


def test_verify_matches_correct_employee(client):
    image_b64 = _fingerprint_like_image_b64(seed=11)
    enroll_body = {"employeeId": "EMP002", "fingerType": "left_thumb", "image": image_b64}
    headers, body_bytes = _signed_headers(enroll_body)
    client.post("/enroll", content=body_bytes, headers=headers)

    verify_body = {"employeeId": "EMP002", "image": image_b64}
    headers2, body_bytes2 = _signed_headers(verify_body)
    response = client.post("/verify", content=body_bytes2, headers=headers2)
    assert response.status_code == 200
    result = response.json()
    assert result["match"] is True


def test_delete_without_signature_rejected(client):
    response = client.post("/delete", json={"employeeId": "EMP003"})
    assert response.status_code == 422  # headers requis manquants


def test_delete_removes_enrolled_employee(client):
    image_b64 = _fingerprint_like_image_b64(seed=23)
    enroll_body = {"employeeId": "EMP003", "fingerType": "right_thumb", "image": image_b64}
    headers, body_bytes = _signed_headers(enroll_body)
    enroll_response = client.post("/enroll", content=body_bytes, headers=headers)
    assert enroll_response.status_code == 200

    delete_body = {"employeeId": "EMP003"}
    headers2, body_bytes2 = _signed_headers(delete_body)
    delete_response = client.post("/delete", content=body_bytes2, headers=headers2)
    assert delete_response.status_code == 200
    result = delete_response.json()
    assert result["success"] is True
    assert result["employeeId"] == "EMP003"

    # Vérifier avec la même image doit maintenant échouer : plus de template.
    verify_body = {"employeeId": "EMP003", "image": image_b64}
    headers3, body_bytes3 = _signed_headers(verify_body)
    verify_response = client.post("/verify", content=body_bytes3, headers=headers3)
    assert verify_response.status_code == 200
    assert verify_response.json()["match"] is False


def test_delete_unknown_employee_returns_success_false(client):
    delete_body = {"employeeId": "EMP_INCONNU"}
    headers, body_bytes = _signed_headers(delete_body)
    response = client.post("/delete", content=body_bytes, headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is False
