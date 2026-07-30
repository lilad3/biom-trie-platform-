"""
app.security.auth
===================
Authentification INTER-SERVICES, pas authentification utilisateur.

Ce micro-service ne connaît jamais le JWT de l'utilisateur final : celui-ci
est vérifié en amont par le backend principal (Django), qui a déjà appliqué
le RBAC (rôle autorisé à pointer/enregistrer une empreinte). Ce qui transite
ici, c'est une confiance service-à-service.

Mécanisme : signature HMAC-SHA256 de chaque requête avec SERVICE_AUTH_TOKEN
comme clé, plus une fenêtre de tolérance temporelle pour empêcher le rejeu.

Le backend appelant doit envoyer :
  X-Timestamp: <epoch_seconds>
  X-Signature: hex(HMAC_SHA256(SERVICE_AUTH_TOKEN, f"{timestamp}.{raw_body}"))
"""
from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import Header, HTTPException, Request, status

from app.config import get_api_settings


async def verify_service_signature(
    request: Request,
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
) -> None:
    """
    Dépendance FastAPI à ajouter sur CHAQUE route sensible (enroll/identify/verify).
    Lève 401 si la signature est absente/invalide, ou 408 si la requête est trop
    ancienne (protection anti-rejeu).
    """
    settings = get_api_settings()

    try:
        timestamp = int(x_timestamp)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "X-Timestamp invalide.")

    now = int(time.time())
    if abs(now - timestamp) > settings.SIGNATURE_TOLERANCE_SECONDS:
        raise HTTPException(status.HTTP_408_REQUEST_TIMEOUT, "Requête expirée (anti-rejeu).")

    body = await request.body()
    message = f"{timestamp}.".encode("utf-8") + body
    expected_signature = hmac.new(
        settings.SERVICE_AUTH_TOKEN.encode("utf-8"), message, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, x_signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Signature invalide.")


def sign_request(body_bytes: bytes, service_auth_token: str, timestamp: int | None = None) -> dict[str, str]:
    """
    Fonction utilitaire côté APPELANT (ex: Django) pour générer les headers
    attendus. À réutiliser dans le client HTTP du backend principal.
    """
    timestamp = timestamp or int(time.time())
    message = f"{timestamp}.".encode("utf-8") + body_bytes
    signature = hmac.new(service_auth_token.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return {"X-Timestamp": str(timestamp), "X-Signature": signature}
