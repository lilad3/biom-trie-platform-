"""
Tests de BiometricClient. La librairie `responses` mocke requests : ces
tests vérifient le contrat HTTP (endpoints, méthode, signature HMAC,
gestion d'erreurs) sans dépendre d'un vrai serveur biometric-api.
"""
import hashlib
import hmac
import json

import pytest
import responses

from biometric_client import (
    BiometricClient,
    ConfigurationError,
    InvalidResponseError,
    NetworkError,
    ServerError,
)

BASE_URL = "http://localhost:8001"
TOKEN = "test-service-token"


@pytest.fixture
def client():
    return BiometricClient(base_url=BASE_URL, service_auth_token=TOKEN)


def _verify_signature(request, token=TOKEN):
    """Reproduit la vérification côté serveur pour valider que le client signe correctement."""
    timestamp = request.headers["X-Timestamp"]
    signature = request.headers["X-Signature"]
    message = f"{timestamp}.".encode("utf-8") + request.body
    expected = hmac.new(token.encode("utf-8"), message, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(expected, signature)


class TestConfiguration:
    def test_missing_base_url_raises(self):
        with pytest.raises(ConfigurationError):
            BiometricClient(base_url="", service_auth_token=TOKEN)

    def test_missing_token_raises(self):
        with pytest.raises(ConfigurationError):
            BiometricClient(base_url=BASE_URL, service_auth_token="")

    def test_strips_trailing_slashes(self):
        c = BiometricClient(base_url=BASE_URL + "///", service_auth_token=TOKEN)
        assert c._base_url == BASE_URL


class TestEnroll:
    @responses.activate
    def test_enroll_sends_correct_payload_and_signature(self, client):
        responses.add(
            responses.POST,
            f"{BASE_URL}/enroll",
            json={"success": True, "employeeId": "EMP001", "fingerType": "right_index", "message": "ok"},
            status=200,
        )

        result = client.enroll("EMP001", "right_index", "base64img")

        request = responses.calls[0].request
        _verify_signature(request)
        assert json.loads(request.body) == {
            "employeeId": "EMP001",
            "fingerType": "right_index",
            "image": "base64img",
        }
        assert result.success is True
        assert result.employee_id == "EMP001"
        assert result.finger_type == "right_index"


class TestIdentify:
    @responses.activate
    def test_identify_success(self, client):
        responses.add(
            responses.POST,
            f"{BASE_URL}/identify",
            json={"success": True, "employeeId": "EMP002", "score": 55, "message": "ok"},
            status=200,
        )

        result = client.identify("base64img")

        assert responses.calls[0].request.url == f"{BASE_URL}/identify"
        assert result.success is True
        assert result.employee_id == "EMP002"
        assert result.score == 55

    @responses.activate
    def test_identify_no_match(self, client):
        responses.add(
            responses.POST,
            f"{BASE_URL}/identify",
            json={"success": False, "score": 3, "message": "Aucune correspondance."},
            status=200,
        )

        result = client.identify("base64img")
        assert result.success is False
        assert result.employee_id is None


class TestVerify:
    @responses.activate
    def test_verify_match(self, client):
        responses.add(
            responses.POST,
            f"{BASE_URL}/verify",
            json={"success": True, "match": True, "employeeId": "EMP003", "score": 80, "message": "ok"},
            status=200,
        )

        result = client.verify("EMP003", "base64img")
        request = responses.calls[0].request
        assert json.loads(request.body) == {"employeeId": "EMP003", "image": "base64img"}
        assert result.match is True


class TestDelete:
    @responses.activate
    def test_delete_success(self, client):
        responses.add(
            responses.POST,
            f"{BASE_URL}/delete",
            json={"success": True, "employeeId": "EMP004", "message": "supprimé"},
            status=200,
        )

        result = client.delete("EMP004")
        assert json.loads(responses.calls[0].request.body) == {"employeeId": "EMP004"}
        assert result.success is True


class TestHealth:
    @responses.activate
    def test_health_no_signature_required(self, client):
        responses.add(
            responses.GET,
            f"{BASE_URL}/health",
            json={"status": "ok", "enrolled_employees": 5, "service": "biometric-api"},
            status=200,
        )

        result = client.health()
        request = responses.calls[0].request
        assert "X-Signature" not in request.headers
        assert result.enrolled_employees == 5


class TestErrorHandling:
    @responses.activate
    def test_server_error_raises_server_error(self, client):
        responses.add(
            responses.POST,
            f"{BASE_URL}/identify",
            json={"message": "Signature invalide."},
            status=401,
        )

        with pytest.raises(ServerError) as exc_info:
            client.identify("img")
        assert exc_info.value.status_code == 401

    @responses.activate
    def test_connection_error_raises_network_error(self, client):
        import requests as requests_lib

        responses.add(
            responses.POST,
            f"{BASE_URL}/identify",
            body=requests_lib.exceptions.ConnectionError("connection refused"),
        )

        with pytest.raises(NetworkError):
            client.identify("img")

    @responses.activate
    def test_invalid_json_raises_invalid_response_error(self, client):
        responses.add(
            responses.POST,
            f"{BASE_URL}/identify",
            body="not json at all",
            status=200,
            content_type="text/plain",
        )

        with pytest.raises(InvalidResponseError):
            client.identify("img")


class TestContextManager:
    @responses.activate
    def test_context_manager_closes_session(self):
        responses.add(
            responses.POST,
            f"{BASE_URL}/identify",
            json={"success": False, "message": "aucune correspondance"},
            status=200,
        )

        with BiometricClient(base_url=BASE_URL, service_auth_token=TOKEN) as c:
            c.identify("img")
        # Après le with, la session doit être fermée (pas d'assertion directe possible
        # sans introspection de requests.Session, mais l'appel ne doit pas lever d'erreur).
