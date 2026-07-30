from fastapi import APIRouter, Depends, Request

from biometric_core import storage
from biometric_core.config import get_settings
from biometric_core.feature_extraction import (
    FeatureExtractionError,
    extract_features,
    serializable_to_keypoints,
)
from biometric_core.matching import match_with_keypoints
from app.models.fingerprint import IdentifyRequest, IdentifyResponse
from app.security.audit import record_audit_event
from app.security.auth import verify_service_signature
from app.security.rate_limit import limiter
from app.security.validators import ImageValidationError, validate_and_decode

router = APIRouter(tags=["identify"])


@router.post(
    "/identify",
    response_model=IdentifyResponse,
    dependencies=[Depends(verify_service_signature)],
)
@limiter.limit("10/minute")
async def identify(request: Request, payload: IdentifyRequest):
    """
    Identification 1:N — compare l'empreinte capturée à TOUS les templates
    enregistrés et retourne le meilleur candidat si son score dépasse
    MIN_GOOD_MATCHES. C'est la route la plus sensible : rate-limitée le plus
    strictement, et chaque tentative est journalisée dans l'audit log de la
    plateforme biométrique elle-même (indépendamment de tout journal que
    l'application hôte tiendrait de son côté).
    """
    settings = get_settings()
    client_ip = request.client.host if request.client else None

    try:
        image_bytes = validate_and_decode(payload.image)
    except ImageValidationError as exc:
        record_audit_event(
            "identify", employee_id=None, success=False,
            client_ip=client_ip, detail="image_invalide",
        )
        return IdentifyResponse(success=False, message=str(exc))

    try:
        probe_keypoints_raw, probe_descriptors = extract_features(image_bytes)
    except FeatureExtractionError as exc:
        record_audit_event(
            "identify", employee_id=None, success=False,
            client_ip=client_ip, detail="extraction_echouee",
        )
        return IdentifyResponse(success=False, message=str(exc))
    finally:
        del image_bytes

    probe_keypoints = serializable_to_keypoints(probe_keypoints_raw)

    best_employee_id = None
    best_score = 0

    for employee_id, finger_type, stored_keypoints_raw, stored_descriptors_raw in storage.iter_all_templates():
        stored_keypoints = serializable_to_keypoints(stored_keypoints_raw)
        stored_descriptors = _to_array(stored_descriptors_raw)

        score = match_with_keypoints(
            probe_keypoints, probe_descriptors,
            stored_keypoints, stored_descriptors,
        )
        if score > best_score:
            best_score = score
            best_employee_id = employee_id

    if best_employee_id is not None and best_score >= settings.MIN_GOOD_MATCHES:
        record_audit_event(
            "identify", employee_id=best_employee_id, success=True,
            client_ip=client_ip, detail=f"score={best_score}",
        )
        return IdentifyResponse(
            success=True, employeeId=best_employee_id, score=best_score,
            message="Empreinte identifiée.",
        )

    record_audit_event(
        "identify", employee_id=None, success=False,
        client_ip=client_ip, detail=f"aucune_correspondance score={best_score}",
    )
    return IdentifyResponse(
        success=False, score=best_score,
        message="Aucune correspondance fiable trouvée.",
    )


def _to_array(data):
    import numpy as np
    return np.array(data, dtype=float)
