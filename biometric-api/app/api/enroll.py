from fastapi import APIRouter, Depends, Request

from biometric_core import storage
from biometric_core.feature_extraction import FeatureExtractionError, extract_features
from app.models.fingerprint import EnrollRequest, EnrollResponse
from app.security.audit import record_audit_event
from app.security.auth import verify_service_signature
from app.security.rate_limit import limiter
from app.security.validators import ImageValidationError, validate_and_decode

router = APIRouter(tags=["enroll"])


@router.post(
    "/enroll",
    response_model=EnrollResponse,
    dependencies=[Depends(verify_service_signature)],
)
@limiter.limit("20/minute")
async def enroll(request: Request, payload: EnrollRequest):
    """
    Enregistre une nouvelle empreinte pour un employé.

    Étapes : décodage + validation stricte -> extraction SIFT (CLAHE inclus)
    -> chiffrement AES-256-GCM (AAD = employeeId) -> stockage. L'image brute
    n'est JAMAIS conservée après extraction : elle n'existe qu'en mémoire le
    temps du traitement de cette requête, jamais écrite sur disque.
    Chaque tentative est journalisée dans l'audit log de la plateforme.
    """
    client_ip = request.client.host if request.client else None

    try:
        image_bytes = validate_and_decode(payload.image)
    except ImageValidationError as exc:
        record_audit_event(
            "enroll", employee_id=payload.employeeId, success=False,
            client_ip=client_ip, detail="image_invalide",
        )
        return EnrollResponse(
            success=False, employeeId=payload.employeeId,
            fingerType=payload.fingerType, message=str(exc),
        )

    try:
        keypoints, descriptors = extract_features(image_bytes)
    except FeatureExtractionError as exc:
        record_audit_event(
            "enroll", employee_id=payload.employeeId, success=False,
            client_ip=client_ip, detail="extraction_echouee",
        )
        return EnrollResponse(
            success=False, employeeId=payload.employeeId,
            fingerType=payload.fingerType, message=str(exc),
        )
    finally:
        del image_bytes  # ne jamais garder l'image brute en mémoire plus que nécessaire

    storage.add_template(
        employee_id=payload.employeeId,
        finger_type=payload.fingerType,
        keypoints=keypoints,
        descriptors=descriptors.astype(float).tolist(),
    )

    record_audit_event(
        "enroll", employee_id=payload.employeeId, success=True,
        client_ip=client_ip, detail=f"fingerType={payload.fingerType}",
    )
    return EnrollResponse(
        success=True,
        employeeId=payload.employeeId,
        fingerType=payload.fingerType,
        message="Empreinte enregistrée avec succès.",
    )
