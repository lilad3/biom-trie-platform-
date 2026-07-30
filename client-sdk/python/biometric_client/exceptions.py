"""
biometric_client.exceptions
=============================
Hiérarchie d'exceptions du SDK client. Le développeur ne voit jamais
d'exception requests/httpx brute : tout est traduit en exceptions de ce
module, avec un message et un code stables quel que soit le client HTTP
utilisé en interne.
"""
from __future__ import annotations


class BiometricClientError(Exception):
    """Classe de base de toutes les erreurs du SDK client."""

    def __init__(self, message: str, code: str = "CLIENT_ERROR", status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


class NetworkError(BiometricClientError):
    """Le serveur biométrique n'a pas pu être contacté (réseau, DNS, connexion refusée)."""

    def __init__(self, message: str = "Impossible de contacter le serveur biométrique."):
        super().__init__(message, code="NETWORK_ERROR")


class TimeoutError_(BiometricClientError):
    """Le serveur biométrique n'a pas répondu dans le délai imparti."""

    def __init__(self, message: str = "Le serveur biométrique n'a pas répondu à temps."):
        super().__init__(message, code="TIMEOUT")


class ServerError(BiometricClientError):
    """Le serveur biométrique a répondu avec un code d'erreur HTTP."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message, code="SERVER_ERROR", status_code=status_code)


class InvalidResponseError(BiometricClientError):
    """La réponse du serveur n'est pas un JSON exploitable."""

    def __init__(self, message: str = "Réponse du serveur biométrique illisible."):
        super().__init__(message, code="INVALID_RESPONSE")


class ConfigurationError(BiometricClientError):
    """Le client a été mal configuré (paramètres manquants ou invalides)."""

    def __init__(self, message: str):
        super().__init__(message, code="CONFIGURATION_ERROR")
