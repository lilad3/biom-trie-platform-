"""
biometric_core.feature_extraction
=============================
Extraction pure des caractéristiques d'une empreinte : image -> descripteurs.

Aucune dépendance à HTTP, Django, au stockage ou au chiffrement : ce module
est 100% portable et testable isolément (c'est la partie "coeur" que le
cahier des charges veut garder indépendante de DigitalPersona lui-même).
"""
from __future__ import annotations

import cv2
import numpy as np

from biometric_core.config import get_settings


class FeatureExtractionError(Exception):
    """L'image fournie ne permet pas d'en extraire des caractéristiques exploitables."""


def decode_grayscale_image(image_bytes: bytes) -> np.ndarray:
    """Décode des octets d'image (PNG/JPEG déjà validés en amont) en tableau niveaux de gris."""
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FeatureExtractionError("Impossible de décoder l'image (format invalide ou corrompue).")
    return image


def enhance_contrast(gray_image: np.ndarray) -> np.ndarray:
    """
    CLAHE (Contrast Limited Adaptive Histogram Equalization) : indispensable
    pour les empreintes digitales, dont le contraste varie énormément selon
    la pression du doigt, l'humidité, et le capteur utilisé.
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray_image)


def extract_features(image_bytes: bytes) -> tuple[list[dict], np.ndarray]:
    """
    Pipeline complet : décodage -> CLAHE -> SIFT.
    Retourne (keypoints_sérialisables, descripteurs_bruts).
    Lève FeatureExtractionError si aucune caractéristique n'est détectable
    (image trop floue, trop uniforme, pas une empreinte).
    """
    settings = get_settings()  # noqa: F841 (réservé pour d'éventuels seuils configurables)

    gray = decode_grayscale_image(image_bytes)
    enhanced = enhance_contrast(gray)

    sift = cv2.SIFT_create()
    keypoints, descriptors = sift.detectAndCompute(enhanced, None)

    if descriptors is None or len(keypoints) == 0:
        raise FeatureExtractionError(
            "Aucune caractéristique détectable sur cette image (image de mauvaise "
            "qualité ou ne représentant pas une empreinte)."
        )

    serializable_keypoints = keypoints_to_serializable(keypoints)
    return serializable_keypoints, descriptors


def keypoints_to_serializable(keypoints: list[cv2.KeyPoint]) -> list[dict]:
    """
    Les objets cv2.KeyPoint ne sont pas JSON-sérialisables nativement.
    On extrait les champs nécessaires pour pouvoir les reconstruire plus tard.
    """
    return [
        {
            "pt": [kp.pt[0], kp.pt[1]],
            "size": kp.size,
            "angle": kp.angle,
            "response": kp.response,
            "octave": kp.octave,
            "class_id": kp.class_id,
        }
        for kp in keypoints
    ]


def serializable_to_keypoints(data: list[dict]) -> list[cv2.KeyPoint]:
    """Inverse de keypoints_to_serializable, pour reconstruire avant matching si nécessaire."""
    return [
        cv2.KeyPoint(
            x=item["pt"][0], y=item["pt"][1], size=item["size"],
            angle=item["angle"], response=item["response"],
            octave=item["octave"], class_id=item["class_id"],
        )
        for item in data
    ]


def descriptors_to_list(descriptors: np.ndarray) -> list[list[float]]:
    """Pour la sérialisation JSON avant chiffrement."""
    return descriptors.astype(float).tolist()


def descriptors_from_list(data: list[list[float]]) -> np.ndarray:
    return np.array(data, dtype=np.float32)
