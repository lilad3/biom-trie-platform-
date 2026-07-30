"""
app.security.validators
=========================
Validation stricte de toute image reçue AVANT qu'elle n'atteigne OpenCV.
Une image malformée envoyée directement à cv2.imdecode peut planter le
service ou être vecteur d'exploitation ; on valide donc en amont.
"""
from __future__ import annotations

import base64
import binascii

import cv2
import numpy as np

from biometric_core.config import get_settings

# Magic bytes réels des formats autorisés (ne jamais se fier à une extension déclarée).
_MAGIC_BYTES = {
    "png": b"\x89PNG\r\n\x1a\n",
    "jpeg": b"\xff\xd8\xff",
}


class ImageValidationError(Exception):
    """L'image fournie ne respecte pas les contraintes de sécurité/format."""


def decode_base64_payload(image_field: str) -> bytes:
    """Retire un éventuel préfixe data:image/...;base64, puis décode strictement."""
    if "," in image_field and image_field.strip().startswith("data:"):
        image_field = image_field.split(",", 1)[1]
    try:
        return base64.b64decode(image_field, validate=True)
    except binascii.Error as exc:
        raise ImageValidationError("Champ image : base64 invalide.") from exc


def validate_image_bytes(raw: bytes) -> None:
    """Valide taille, magic bytes réels, et dimensions décodées."""
    settings = get_settings()

    if len(raw) == 0:
        raise ImageValidationError("Image vide.")
    if len(raw) > settings.MAX_IMAGE_SIZE:
        raise ImageValidationError(
            f"Image trop volumineuse ({len(raw)} octets, max {settings.MAX_IMAGE_SIZE})."
        )

    if not (raw.startswith(_MAGIC_BYTES["png"]) or raw.startswith(_MAGIC_BYTES["jpeg"])):
        raise ImageValidationError("Format d'image non reconnu (seuls PNG et JPEG sont acceptés).")

    array = np.frombuffer(raw, dtype=np.uint8)
    decoded = cv2.imdecode(array, cv2.IMREAD_GRAYSCALE)
    if decoded is None:
        raise ImageValidationError("Image illisible (fichier corrompu ou format falsifié).")

    height, width = decoded.shape[:2]
    if not (settings.MIN_IMAGE_DIMENSION <= width <= settings.MAX_IMAGE_DIMENSION):
        raise ImageValidationError(f"Largeur d'image hors limites : {width}px.")
    if not (settings.MIN_IMAGE_DIMENSION <= height <= settings.MAX_IMAGE_DIMENSION):
        raise ImageValidationError(f"Hauteur d'image hors limites : {height}px.")


def validate_and_decode(image_field: str) -> bytes:
    """Fonction unique à appeler depuis les routes API : décode + valide, ou lève ImageValidationError."""
    raw = decode_base64_payload(image_field)
    validate_image_bytes(raw)
    return raw
