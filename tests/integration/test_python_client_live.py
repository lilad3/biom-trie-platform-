"""
Test d'intégration BOUT-EN-BOUT : lance un vrai processus uvicorn servant
biometric-api, puis tape dessus avec le vrai BiometricClient (biometric_client),
en passant par un vrai socket réseau — pas de mock, pas de TestClient qui
court-circuite la pile HTTP.

Objectif : prouver que biometric-api et le client SDK Python s'interconnectent
réellement (même protocole de signature, mêmes schémas JSON, mêmes routes),
et pas seulement que chacun se comporte bien isolément derrière des mocks.

Ces tests sont plus lents (démarrage d'un vrai serveur) : ils sont
volontairement séparés de tests/api/ et tests/core/ pour ne pas ralentir
la boucle de développement rapide sur ces suites-là.
"""
import base64
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _fingerprint_like_image_b64(seed: int) -> str:
    rng = np.random.default_rng(seed)
    image = rng.integers(0, 255, size=(300, 300), dtype=np.uint8)
    image = cv2.GaussianBlur(image, (5, 5), 0)
    for i in range(0, 300, 15):
        cv2.line(image, (0, i), (300, i), (255,), 1)
    success, encoded = cv2.imencode(".png", image)
    assert success
    return base64.b64encode(encoded.tobytes()).decode()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(host: str, port: int, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Le serveur biometric-api n'a pas démarré sur {host}:{port} à temps.")


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    """Démarre un vrai processus uvicorn servant biometric-api, isolé (clés jetables,
    stockage temporaire), et l'arrête proprement à la fin du module de tests."""
    data_dir = tmp_path_factory.mktemp("integration_data")
    port = _free_port()
    token = "integration-test-token-abc123"
    encryption_key = base64.b64encode(os.urandom(32)).decode()

    env = os.environ.copy()
    env["SERVICE_AUTH_TOKEN"] = token
    env["BIOMETRIC_ENCRYPTION_KEY"] = encryption_key
    env["ALLOWED_ORIGINS"] = "[]"
    env["AUDIT_LOG_DIR"] = str(data_dir / "audit")
    env["PYTHONPATH"] = str(REPO_ROOT / "biometric-api")

    process = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", str(port),
            "--app-dir", str(REPO_ROOT / "biometric-api"),
        ],
        cwd=str(data_dir),  # data/ et .env relatifs seront résolus ici, hors du repo
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    try:
        _wait_for_server("127.0.0.1", port)
        yield {"base_url": f"http://127.0.0.1:{port}", "token": token}
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture
def client(live_server):
    from biometric_client import BiometricClient
    return BiometricClient(base_url=live_server["base_url"], service_auth_token=live_server["token"])


def test_health_reaches_real_server(client):
    result = client.health()
    assert result.status == "ok"
    assert result.service == "biometric-api"


def test_enroll_then_identify_round_trip(client):
    image = _fingerprint_like_image_b64(seed=555)

    enroll_result = client.enroll("INTEG_EMP1", "right_index", image)
    assert enroll_result.success is True

    identify_result = client.identify(image)
    assert identify_result.success is True
    assert identify_result.employee_id == "INTEG_EMP1"


def test_enroll_then_verify_round_trip(client):
    image = _fingerprint_like_image_b64(seed=556)

    client.enroll("INTEG_EMP2", "left_thumb", image)
    verify_result = client.verify("INTEG_EMP2", image)
    assert verify_result.match is True


def test_delete_round_trip(client):
    image = _fingerprint_like_image_b64(seed=557)

    client.enroll("INTEG_EMP3", "right_thumb", image)
    delete_result = client.delete("INTEG_EMP3")
    assert delete_result.success is True

    verify_result = client.verify("INTEG_EMP3", image)
    assert verify_result.match is False


def test_wrong_token_is_rejected_by_real_server(live_server):
    from biometric_client import BiometricClient, ServerError

    bad_client = BiometricClient(base_url=live_server["base_url"], service_auth_token="wrong-token")
    with pytest.raises(ServerError) as exc_info:
        bad_client.identify(_fingerprint_like_image_b64(seed=558))
    assert exc_info.value.status_code == 401
