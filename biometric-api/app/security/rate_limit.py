"""
app.security.rate_limit
=========================
Limite les tentatives sur les routes sensibles (surtout /identify, qui
compare une image à toute la base et est donc la cible naturelle d'attaques
par force brute / déni de service).

Limite appliquée par IP source. En production multi-workers, utiliser
RATE_LIMIT_STORAGE_URI=redis://... (sinon chaque worker a son propre
compteur en mémoire et la limite réelle globale explose).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_api_settings

settings = get_api_settings()

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
)
