"""
biometric_client.client
=========================
BiometricClient — le SDK officiel Python pour biometric-api.

Le développeur n'écrit jamais de requests.post() manuel, ne calcule jamais
de signature HMAC, ne construit jamais d'URL : il utilise directement
client.enroll(...), client.identify(...), client.verify(...), client.delete(...).

Ce client est fait pour être utilisé CÔTÉ SERVEUR (dans l'application hôte :
Django, Flask, FastAPI, un script...), jamais côté navigateur — il porte le
secret SERVICE_AUTH_TOKEN nécessaire à la signature HMAC inter-services.

Usage :
    from biometric_client import BiometricClient

    client = BiometricClient(
        base_url="http://localhost:8001",
        service_auth_token="...",
    )
    result = client.identify(image_base64)
    if result.success:
        print(result.employee_id)
"""
from __future__ import annotations

import json
from typing import Optional

import requests

from biometric_client._auth import sign_request
from biometric_client.exceptions import (
    ConfigurationError,
    InvalidResponseError,
    NetworkError,
    ServerError,
    TimeoutError_,
)
from biometric_client.models import (
    DeleteResult,
    EnrollResult,
    HealthResult,
    IdentifyResult,
    VerifyResult,
)


class BiometricClient:
    """
    Client officiel pour biometric-api. Une instance = une connexion à un
    déploiement de biometric-api (une base_url, un service_auth_token).
    """

    def __init__(
        self,
        base_url: str,
        service_auth_token: str,
        timeout_seconds: float = 15.0,
    ):
        if not base_url:
            raise ConfigurationError("base_url est requis pour initialiser BiometricClient.")
        if not service_auth_token:
            raise ConfigurationError("service_auth_token est requis pour initialiser BiometricClient.")

        self._base_url = base_url.rstrip("/")
        self._service_auth_token = service_auth_token
        self._timeout_seconds = timeout_seconds
        self._session = requests.Session()

    def _post(self, path: str, payload: dict) -> dict:
        body_bytes = json.dumps(payload).encode("utf-8")
        headers = sign_request(body_bytes, self._service_auth_token)
        headers["Content-Type"] = "application/json"

        try:
            response = self._session.post(
                self._base_url + path,
                data=body_bytes,
                headers=headers,
                timeout=self._timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise TimeoutError_() from exc
        except requests.exceptions.RequestException as exc:
            raise NetworkError(f"Impossible de contacter le serveur biométrique : {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise InvalidResponseError() from exc

        if not response.ok:
            message = data.get("message") if isinstance(data, dict) else None
            raise ServerError(
                message or f"Erreur du serveur biométrique (HTTP {response.status_code}).",
                status_code=response.status_code,
            )

        return data

    def _get(self, path: str) -> dict:
        try:
            response = self._session.get(self._base_url + path, timeout=self._timeout_seconds)
        except requests.exceptions.Timeout as exc:
            raise TimeoutError_() from exc
        except requests.exceptions.RequestException as exc:
            raise NetworkError(f"Impossible de contacter le serveur biométrique : {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise InvalidResponseError() from exc

        if not response.ok:
            raise ServerError(
                f"Erreur du serveur biométrique (HTTP {response.status_code}).",
                status_code=response.status_code,
            )

        return data

    def enroll(self, employee_id: str, finger_type: str, image_base64: str) -> EnrollResult:
        """Enregistre une nouvelle empreinte pour un employé."""
        data = self._post(
            "/enroll",
            {"employeeId": employee_id, "fingerType": finger_type, "image": image_base64},
        )
        return EnrollResult.from_dict(data)

    def identify(self, image_base64: str) -> IdentifyResult:
        """Identification 1:N : retrouve l'employé correspondant parmi tous les enrôlés."""
        data = self._post("/identify", {"image": image_base64})
        return IdentifyResult.from_dict(data)

    def verify(self, employee_id: str, image_base64: str) -> VerifyResult:
        """Vérification 1:1 : confirme (ou non) qu'une image correspond à cet employé."""
        data = self._post("/verify", {"employeeId": employee_id, "image": image_base64})
        return VerifyResult.from_dict(data)

    def delete(self, employee_id: str) -> DeleteResult:
        """Supprime définitivement toutes les empreintes d'un employé."""
        data = self._post("/delete", {"employeeId": employee_id})
        return DeleteResult.from_dict(data)

    def health(self) -> HealthResult:
        """Sonde de disponibilité du service (aucune authentification requise)."""
        data = self._get("/health")
        return HealthResult.from_dict(data)

    def close(self) -> None:
        """Ferme la session HTTP sous-jacente. Optionnel (GC le fait aussi)."""
        self._session.close()

    def __enter__(self) -> "BiometricClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
