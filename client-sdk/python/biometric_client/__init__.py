"""
biometric_client
==================
SDK officiel Python pour biometric-api. Le développeur n'écrit jamais de
requests.post() manuel, ne calcule jamais de signature HMAC : il utilise
directement BiometricClient.enroll(...)/identify(...)/verify(...)/delete(...).

Usage :
    from biometric_client import BiometricClient

    client = BiometricClient(base_url="http://localhost:8001", service_auth_token="...")
    result = client.identify(image_base64)
"""
from biometric_client.client import BiometricClient
from biometric_client.exceptions import (
    BiometricClientError,
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

__version__ = "1.0.0"

__all__ = [
    "BiometricClient",
    "BiometricClientError",
    "ConfigurationError",
    "InvalidResponseError",
    "NetworkError",
    "ServerError",
    "TimeoutError_",
    "DeleteResult",
    "EnrollResult",
    "HealthResult",
    "IdentifyResult",
    "VerifyResult",
]
