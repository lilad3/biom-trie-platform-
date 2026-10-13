# Image de biometric-api (FastAPI) + biometric-core.
# À construire depuis la RACINE du dépôt, car l'image a besoin des deux dossiers :
#   docker build -f biometric-api/Dockerfile -t biometric-api .
# (docker compose le fait automatiquement, voir docker-compose.yml)

FROM python:3.12-slim

# Pas de .pyc, logs affichés immédiatement (utile avec `docker compose logs`)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 1. Dépendances d'abord : cette couche reste en cache tant que les fichiers
#    de dépendances ne changent pas, même si le code change.
COPY biometric-api/requirements.txt /tmp/requirements.txt
COPY biometric-core /tmp/biometric-core
RUN pip install /tmp/biometric-core -r /tmp/requirements.txt \
    && rm -rf /tmp/biometric-core /tmp/requirements.txt

# 2. Code de l'API
COPY biometric-api/app ./app

# 3. Utilisateur non-root : si le service est compromis, l'attaquant n'est pas root.
#    data/ contient les templates chiffrés et l'audit log (monté en volume).
RUN useradd --system --uid 10001 --no-create-home appuser \
    && mkdir -p /app/data \
    && chown appuser /app/data
USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
