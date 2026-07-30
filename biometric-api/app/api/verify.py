from fastapi import APIRouter, Depends, Request

from biometric_core import storage
from biometric_core.config import get_settings
from biometric_core.encryption import DecryptionError
from biometric_core.feature_extraction import (
    FeatureExtractionError,
    extract_features,
    serializable_to_keypoints,
)
from biometric_core.matching import match_with_keypoints
from app.models.fingerprint import VerifyRequest, VerifyResponse
from app.security.audit import record_audit_event
from app.security.auth import verify_service_signature
from app.security.rate_limit import limiter
from app.security.validators import ImageValidationError, validate_and_decode

router = APIRouter(tags=["verify"])


@router.post(
    "/verify",
    response_model=VerifyResponse,
    dependencies=[Depends(verify_service_signature)],
)
@limiter.limit("10/minute")
async def verify(request: Request, payload: VerifyRequest):
    """
    Vérification 1:1 — compare l'empreinte capturée uniquement aux templates
    d'un employé précis déjà identifié par ailleurs (ex: badge + empreinte en
    double authentification). Beaucoup plus rapide et moins sujet aux faux
    positifs que /identify puisqu'on ne compare pas à toute la base.
    Chaque tentative est journalisée dans l'audit log de la plateforme.
    """
    settings = get_settings()
    client_ip = request.client.host if request.client else None

    try:
        image_bytes = validate_and_decode(payload.image)
    except ImageValidationError as exc:
        record_audit_event(
            "verify", employee_id=payload.employeeId, success=False,
            client_ip=client_ip, detail="image_invalide",
        )
        return VerifyResponse(success=False, match=False, employeeId=payload.employeeId, message=str(exc))

    try:
        probe_keypoints_raw, probe_descriptors = extract_features(image_bytes)
    except FeatureExtractionError as exc:
        record_audit_event(
            "verify", employee_id=payload.employeeId, success=False,
            client_ip=client_ip, detail="extraction_echouee",
        )
        return VerifyResponse(success=False, match=False, employeeId=payload.employeeId, message=str(exc))
    finally:
        del image_bytes

    probe_keypoints = serializable_to_keypoints(probe_keypoints_raw)

    try:
        stored = storage.get_employee_templates(payload.employeeId)
    except DecryptionError:
        record_audit_event(
            "verify", employee_id=payload.employeeId, success=False,
            client_ip=client_ip, detail="templates_corrompus",
        )
        return VerifyResponse(
            success=False, match=False, employeeId=payload.employeeId,
            message="Templates de cet employé illisibles (données corrompues).",
        )

    if not stored:
        record_audit_event(
            "verify", employee_id=payload.employeeId, success=False,
            client_ip=client_ip, detail="aucun_template_enregistre",
        )
        return VerifyResponse(
            success=False, match=False, employeeId=payload.employeeId,
            message="Aucune empreinte enregistrée pour cet employé.",
        )

    best_score = 0
    for finger_type, templates in stored.items():
        for template in templates:
            stored_keypoints = serializable_to_keypoints(template["keypoints"])
            stored_descriptors = _to_array(template["descriptors"])
            score = match_with_keypoints(
                probe_keypoints, probe_descriptors,
                stored_keypoints, stored_descriptors,
            )
            best_score = max(best_score, score)

    is_match = best_score >= settings.MIN_GOOD_MATCHES
    record_audit_event(
        "verify", employee_id=payload.employeeId, success=is_match,
        client_ip=client_ip, detail=f"score={best_score}",
    )
    return VerifyResponse(
        success=True, match=is_match, employeeId=payload.employeeId, score=best_score,
        message="Empreinte correspondante." if is_match else "Empreinte non correspondante.",
    )


def _to_array(data):
    import numpy as np
    return np.array(data, dtype=float)
