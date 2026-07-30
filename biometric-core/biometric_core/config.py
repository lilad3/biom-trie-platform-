"""
biometric_core.config
================
Point d'entrée UNIQUE pour la configuration du package biometric-core.

Ce Settings ne contient QUE des paramètres intrinsèques à la biométrie :
chiffrement, stockage des templates, seuils d'extraction/matching,
validation des images. Il ne contient JAMAIS de paramètres propres à une
API HTTP (host, port, CORS, rate limiting, JWT, tolérance de signature...)
— ceux-là appartiennent à l'application hôte (ex: biometric-api), pas au
cœur biométrique, pour que ce package reste utilisable tel quel par
n'importe quel projet Python (script, notebook, autre framework web...)
sans traîner de configuration HTTP dont il n'a pas besoin.

Tout est chargé depuis le fichier .env du répertoire de travail du process
qui importe ce package.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# BASE_DIR n'est PAS calculé relativement à ce fichier (le package peut être
# installé dans site-packages) : il vaut le répertoire de travail courant du
# process, pour que `.env` et `data/` soient résolus par rapport à
# l'application hôte, pas par rapport au lieu d'installation du package.
BASE_DIR = Path.cwd()


class Settings(BaseSettings):
    """Configuration strictement biométrique, indépendante de tout framework web."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Chiffrement AES-256-GCM ---
    BIOMETRIC_ENCRYPTION_KEY: str  # base64, doit décoder vers exactement 32 octets

    # --- Stockage des templates chiffrés ---
    DATA_DIR: Path = BASE_DIR / "data"
    TEMPLATES_FILE: Path = BASE_DIR / "data" / "templates.enc"

    # --- Seuils d'extraction et de matching biométrique (SIFT/FLANN/RANSAC) ---
    MIN_GOOD_MATCHES: int = 18
    LOWE_RATIO_THRESHOLD: float = 0.75
    RANSAC_REPROJ_THRESHOLD: float = 7.5
    FLANN_INDEX_KDTREE: int = 1

    # --- Validation des images reçues avant extraction ---
    MAX_IMAGE_SIZE: int = 5 * 1024 * 1024  # 5 Mo
    ALLOWED_FORMATS: tuple[str, ...] = ("png", "jpg", "jpeg")
    MIN_IMAGE_DIMENSION: int = 64
    MAX_IMAGE_DIMENSION: int = 4000


@lru_cache
def get_settings() -> Settings:
    """Settings mis en cache : chargés une seule fois au démarrage du process."""
    return Settings()
