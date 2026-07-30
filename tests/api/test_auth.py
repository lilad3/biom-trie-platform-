import hashlib
import hmac
import time

import pytest
from fastapi import HTTPException

from app.config import get_api_settings
from app.security.auth import sign_request


class DummyRequest:
    def __init__(self, body: bytes):
        self._body = body

    async def body(self):
        return self._body


@pytest.mark.asyncio
async def test_valid_signature_passes():
    from app.security.auth import verify_service_signature

    settings = get_api_settings()
    body = b'{"employeeId": "EMP001"}'
    headers = sign_request(body, settings.SERVICE_AUTH_TOKEN)

    await verify_service_signature(
        DummyRequest(body), x_signature=headers["X-Signature"], x_timestamp=headers["X-Timestamp"]
    )  # ne doit pas lever d'exception


@pytest.mark.asyncio
async def test_wrong_signature_rejected():
    from app.security.auth import verify_service_signature

    body = b'{"employeeId": "EMP001"}'
    with pytest.raises(HTTPException) as exc_info:
        await verify_service_signature(
            DummyRequest(body), x_signature="0" * 64, x_timestamp=str(int(time.time()))
        )
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_expired_timestamp_rejected():
    from app.security.auth import verify_service_signature

    settings = get_api_settings()
    body = b'{"employeeId": "EMP001"}'
    old_timestamp = int(time.time()) - 3600  # une heure dans le passé
    message = f"{old_timestamp}.".encode() + body
    signature = hmac.new(settings.SERVICE_AUTH_TOKEN.encode(), message, hashlib.sha256).hexdigest()

    with pytest.raises(HTTPException) as exc_info:
        await verify_service_signature(
            DummyRequest(body), x_signature=signature, x_timestamp=str(old_timestamp)
        )
    assert exc_info.value.status_code == 408


@pytest.mark.asyncio
async def test_tampered_body_rejected():
    from app.security.auth import verify_service_signature

    settings = get_api_settings()
    original_body = b'{"employeeId": "EMP001"}'
    headers = sign_request(original_body, settings.SERVICE_AUTH_TOKEN)

    tampered_body = b'{"employeeId": "EMP999"}'  # corps modifié après signature
    with pytest.raises(HTTPException) as exc_info:
        await verify_service_signature(
            DummyRequest(tampered_body), x_signature=headers["X-Signature"], x_timestamp=headers["X-Timestamp"]
        )
    assert exc_info.value.status_code == 401
