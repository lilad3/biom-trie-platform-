"""
biometric_core.storage
==================
Gère la persistance de templates.enc.

Différence importante avec l'ancien système : chaque template (par employé,
par doigt) est chiffré INDIVIDUELLEMENT avec AES-256-GCM, en utilisant
l'employeeId comme "associated data" (AAD). Avantages sur un unique gros
blob chiffré global :
- Une écriture (enroll) ne nécessite pas de déchiffrer/rechiffrer TOUT le
  fichier à chaque fois.
- L'AAD lie cryptographiquement chaque template à son employeeId : on ne
  peut pas copier le blob chiffré d'un employé vers un autre sans casser
  le déchiffrement (protection contre la substitution d'identité).

Structure sur disque (templates.enc, JSON) :
{
  "EMP001": {
    "right_index": ["<token_b64_1>", "<token_b64_2>", ...],
    "left_thumb": ["<token_b64>"]
  },
  "EMP002": { ... }
}
Chaque <token_b64> est le résultat de AesGcmCipher.encrypt(payload, aad=employeeId).
`payload` (avant chiffrement) = JSON {"keypoints": [...], "descriptors": [...]}.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from biometric_core.config import get_settings
from biometric_core.encryption import DecryptionError, get_cipher

_lock = threading.Lock()  # protège contre les écritures concurrentes sur le fichier JSON


def _templates_path() -> Path:
    settings = get_settings()
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return settings.TEMPLATES_FILE


def _read_index() -> dict:
    path = _templates_path()
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    return json.loads(content) if content else {}


def _write_index(index: dict) -> None:
    path = _templates_path()
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(index, f)
    tmp_path.replace(path)  # écriture atomique : évite un fichier corrompu en cas de crash


def add_template(employee_id: str, finger_type: str, keypoints: list[dict], descriptors: list[list[float]]) -> None:
    """Chiffre et ajoute un nouveau template pour un employé/doigt donné."""
    cipher = get_cipher()
    payload = json.dumps({"keypoints": keypoints, "descriptors": descriptors}).encode("utf-8")
    token = cipher.encrypt(payload, associated_data=employee_id.encode("utf-8"))

    with _lock:
        index = _read_index()
        index.setdefault(employee_id, {}).setdefault(finger_type, []).append(token)
        _write_index(index)


def get_employee_templates(employee_id: str) -> dict[str, list[dict]]:
    """
    Déchiffre et retourne tous les templates d'un employé, groupés par doigt.
    Lève DecryptionError si un template est corrompu/altéré ou si l'AAD ne
    correspond pas (tentative de substitution détectée).
    """
    cipher = get_cipher()
    index = _read_index()
    entry = index.get(employee_id, {})

    result: dict[str, list[dict]] = {}
    for finger_type, tokens in entry.items():
        result[finger_type] = [
            json.loads(cipher.decrypt(token, associated_data=employee_id.encode("utf-8")).decode("utf-8"))
            for token in tokens
        ]
    return result


def iter_all_templates():
    """
    Générateur (employee_id, finger_type, keypoints, descriptors) sur TOUS les
    templates stockés, utilisé par /identify pour comparer une empreinte à
    l'ensemble de la base. Les entrées corrompues sont ignorées avec un log,
    plutôt que de faire échouer toute l'identification.
    """
    import logging
    logger = logging.getLogger("biometric_service.storage")

    cipher = get_cipher()
    index = _read_index()

    for employee_id, fingers in index.items():
        for finger_type, tokens in fingers.items():
            for token in tokens:
                try:
                    data = json.loads(
                        cipher.decrypt(token, associated_data=employee_id.encode("utf-8")).decode("utf-8")
                    )
                except DecryptionError:
                    logger.error(
                        "Template corrompu ou altéré ignoré pour employee_id=%s finger_type=%s",
                        employee_id, finger_type,
                    )
                    continue
                yield employee_id, finger_type, data["keypoints"], data["descriptors"]


def employee_count() -> int:
    return len(_read_index())


def delete_employee_templates(employee_id: str) -> bool:
    with _lock:
        index = _read_index()
        if employee_id in index:
            del index[employee_id]
            _write_index(index)
            return True
        return False
