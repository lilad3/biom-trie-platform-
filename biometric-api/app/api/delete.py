from fastapi import APIRouter, Depends, Request

from biometric_core import storage
from app.models.fingerprint import DeleteRequest, DeleteResponse
from app.security.audit import record_audit_event
from app.security.auth import verify_service_signature
from app.security.rate_limit import limiter

router = APIRouter(tags=["delete"])


@router.post(
    "/delete",
    response_model=DeleteResponse,
    dependencies=[Depends(verify_service_signature)],
)
@limiter.limit("10/minute")
async def delete(request: Request, payload: DeleteRequest):
    """
    Supprime définitivement tous les templates biométriques d'un employé
    (tous doigts confondus). Utilisé par le backend principal lors d'un
    départ d'employé, d'un retrait de droit d'accès biométrique, ou d'une
    demande RGPD/droit à l'effacement. Opération irréversible : journalisée
    systématiquement dans l'audit log, qu'elle réussisse ou non.

    Cette route ne fait AUCUNE vérification métier (l'employé existe-t-il
    encore dans le backend principal, l'utilisateur a-t-il le rôle requis,
    etc.) : ces décisions restent entièrement à la charge de l'application
    appelante, comme pour les autres routes de ce service.
    """
    client_ip = request.client.host if request.client else None
    deleted = storage.delete_employee_templates(payload.employeeId)

    record_audit_event(
        "delete", employee_id=payload.employeeId, success=deleted,
        client_ip=client_ip,
        detail="templates_supprimes" if deleted else "aucun_template_trouve",
    )

    return DeleteResponse(
        success=deleted,
        employeeId=payload.employeeId,
        message=(
            "Empreintes supprimées avec succès."
            if deleted
            else "Aucune empreinte trouvée pour cet employé."
        ),
    )
