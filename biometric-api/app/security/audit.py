"""
app.security.audit
====================
Journalisation d'audit des opérations biométriques sensibles
(enroll / identify / verify / delete).

Objectif : traçabilité complète de qui a fait quoi, quand, avec quel
résultat — SANS jamais journaliser de donnée biométrique elle-même
(pas d'image, pas de descripteurs, pas de template). Seuls des métadonnées
non sensibles sont enregistrées : type d'opération, identifiant employé
concerné (pas l'image), résultat, adresse IP appelante, timestamp UTC.

Ce log est écrit en JSON Lines (un événement = une ligne JSON), append-only,
ce qui facilite l'ingestion par un système de log centralisé (ELK, Loki...)
en production. Il ne remplace pas un SIEM : en production, rediriger ce
logger vers un stockage inviolable (write-once, ou système de log externe)
plutôt que le fichier local par défaut.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Literal

AuditEvent = Literal["enroll", "identify", "verify", "delete"]

_logger = logging.getLogger("biometric_api.audit")
_logger.setLevel(logging.INFO)
_configured_dir: Path | None = None


def _ensure_configured() -> None:
    """
    Configure les handlers du logger d'audit au premier appel (paresseux, pas
    au chargement du module) pour que AUDIT_LOG_DIR puisse être positionné par
    l'environnement (y compris par les tests, via monkeypatch) avant la
    première écriture. Si AUDIT_LOG_DIR change entre deux appels, les
    handlers sont reconstruits pour pointer vers le nouveau répertoire —
    utile pour l'isolation des tests, qui utilisent un tmp_path différent
    à chaque test.
    """
    global _configured_dir

    audit_dir = Path(os.environ.get("AUDIT_LOG_DIR", Path.cwd() / "data" / "audit"))

    if _configured_dir == audit_dir and _logger.handlers:
        return

    for h in list(_logger.handlers):
        _logger.removeHandler(h)
        h.close()

    # Un fichier dédié à l'audit, distinct des logs applicatifs génériques,
    # pour qu'il puisse être archivé/protégé avec une politique de rétention
    # propre (exigence légale d'audit biométrique).
    audit_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(audit_dir / "audit.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(handler)

    # En plus du fichier, toujours émettre sur stdout : en conteneur/production,
    # c'est souvent stdout qui est collecté par l'orchestrateur (Docker, k8s...).
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(stream_handler)

    _configured_dir = audit_dir


def record_audit_event(
    event: AuditEvent,
    *,
    employee_id: str | None,
    success: bool,
    client_ip: str | None,
    detail: str = "",
) -> None:
    """
    Enregistre un événement d'audit. Ne JAMAIS passer d'image, de descripteur,
    ou de template en argument `detail` : cette fonction est conçue pour ne
    manipuler que des métadonnées non sensibles.
    """
    _ensure_configured()
    entry = {
        "timestamp": time.time(),
        "event": event,
        "employeeId": employee_id,
        "success": success,
        "clientIp": client_ip,
        "detail": detail,
    }
    _logger.info(json.dumps(entry, ensure_ascii=False))
