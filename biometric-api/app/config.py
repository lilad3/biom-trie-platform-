"""
app.config
===========
Configuration propre à biometric-api : tout ce qui concerne le service HTTP
lui-même (host, port, sécurité inter-services, rate limiting, CORS).

Ce fichier ne contient JAMAIS de paramètres biométriques (chiffrement,
seuils de matching, validation d'image...) — ceux-là vivent dans
biometric_core.config.Settings, chargé séparément et indépendamment.
Les deux Settings lisent le même fichier .env (chacun ne retient que les
clés qui le concernent), donc une seule variable d'environnement suffit à
tout configurer, mais le code reste proprement séparé par responsabilité.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """Configuration strictement liée à l'exposition HTTP de la plateforme biométrique."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Service ---
    SERVICE_NAME: str = "biometric-api"
    SERVICE_HOST: str = "0.0.0.0"
    SERVICE_PORT: int = 8001
    DEBUG: bool = False

    # --- Sécurité inter-services (cette API ne connaît ni utilisateurs ni JWT :
    #     seul le backend hôte s'authentifie auprès d'elle, via HMAC) ---
    SERVICE_AUTH_TOKEN: str
    SIGNATURE_TOLERANCE_SECONDS: int = 30  # fenêtre anti-rejeu pour les requêtes signées HMAC

    # --- Rate limiting ---
    IDENTIFY_RATE_LIMIT: str = "10/minute"
    ENROLL_RATE_LIMIT: str = "20/minute"
    VERIFY_RATE_LIMIT: str = "10/minute"
    RATE_LIMIT_STORAGE_URI: str = "memory://"  # ex: "redis://localhost:6379" en multi-workers

    # --- CORS : uniquement les backends principaux autorisés à appeler cette API ---
    ALLOWED_ORIGINS: tuple[str, ...] = ()


@lru_cache
def get_api_settings() -> ApiSettings:
    """ApiSettings mis en cache : chargés une seule fois au démarrage du process."""
    return ApiSettings()
