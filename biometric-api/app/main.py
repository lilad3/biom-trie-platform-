"""
app.main
=========
Point d'entrée de biometric-api : l'API REST FastAPI de la plateforme
biométrique (biometric-platform). Ce package assemble les routes HTTP
(enroll, identify, verify, delete, health), la sécurité inter-services et
le rate limiting, en s'appuyant entièrement sur biometric-core pour toute
la logique métier (extraction, matching, chiffrement, stockage).

Ce service ne gère QUE : réception HTTP, authentification inter-services,
rate limiting, et délégation à biometric-core. Il ne connaît ni utilisateurs,
ni rôles, ni pointages, ni rapports, ni logs métier — tout cela reste dans
l'application hôte (Django, Laravel, Node...), qui l'appelle via un
connecteur ou directement via HTTP signé.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import delete, enroll, health, identify, verify
from app.config import get_api_settings
from app.security.rate_limit import limiter

settings = get_api_settings()

app = FastAPI(
    title="Biometric API",
    description=(
        "API REST indépendante de la plateforme biométrique : enrôlement, "
        "identification, vérification et suppression d'empreintes digitales. "
        "Toute la logique biométrique (extraction SIFT, matching FLANN/RANSAC, "
        "chiffrement AES-256-GCM, stockage) est déléguée au package "
        "biometric-core. Cette API ne gère ni utilisateurs, ni rôles, ni "
        "logs métier : ceux-ci restent dans l'application hôte."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS : uniquement les backends principaux explicitement autorisés (jamais "*"
# pour une API qui traite des données biométriques).
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Signature", "X-Timestamp"],
)

app.include_router(health.router)
app.include_router(enroll.router)
app.include_router(identify.router)
app.include_router(verify.router)
app.include_router(delete.router)


@app.get("/", include_in_schema=False)
async def root():
    return {"service": settings.SERVICE_NAME, "docs": "/docs"}
