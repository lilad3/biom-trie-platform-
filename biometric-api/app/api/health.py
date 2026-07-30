from fastapi import APIRouter

from biometric_core import storage
from app.config import get_api_settings
from app.models.fingerprint import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    """
    Aucune authentification requise : simple sonde de disponibilité pour
    un load balancer / orchestrateur, sans exposer de donnée sensible.
    """
    settings = get_api_settings()
    return HealthResponse(
        status="ok",
        enrolled_employees=storage.employee_count(),
        service=settings.SERVICE_NAME,
    )
