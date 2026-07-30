"""
biometric_client._auth
========================
Signature HMAC-SHA256 des requêtes vers biometric-api, selon le protocole
exact attendu par app.security.auth.verify_service_signature côté serveur :

  X-Timestamp: <epoch_seconds>
  X-Signature: hex(HMAC_SHA256(SERVICE_AUTH_TOKEN, f"{timestamp}.{raw_body}"))

Ce module réimplémente volontairement cette logique plutôt que d'importer
biometric-api : le client SDK doit être installable seul, dans n'importe
quel projet (Django, Flask, script...), sans jamais dépendre du code du
serveur biométrique lui-même.
"""
from __future__ import annotations

import hashlib
import hmac
import time


def sign_request(body_bytes: bytes, service_auth_token: str, timestamp: int | None = None) -> dict[str, str]:
    """Calcule les headers X-Timestamp/X-Signature attendus par biometric-api."""
    timestamp = timestamp if timestamp is not None else int(time.time())
    message = f"{timestamp}.".encode("utf-8") + body_bytes
    signature = hmac.new(service_auth_token.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return {"X-Timestamp": str(timestamp), "X-Signature": signature}
