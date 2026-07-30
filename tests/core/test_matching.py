import cv2
import numpy as np
import pytest

from biometric_core.feature_extraction import (
    FeatureExtractionError,
    extract_features,
    serializable_to_keypoints,
)
from biometric_core.matching import match_with_keypoints


def _make_textured_image_bytes(seed: int) -> bytes:
    """Génère une image synthétique texturée (pas une vraie empreinte, mais
    assez de structure pour que SIFT y détecte des points caractéristiques)."""
    rng = np.random.default_rng(seed)
    image = rng.integers(0, 255, size=(300, 300), dtype=np.uint8)
    image = cv2.GaussianBlur(image, (5, 5), 0)
    # Ajoute des formes géométriques pour garantir des keypoints stables
    cv2.circle(image, (100, 100), 40, (255,), 2)
    cv2.rectangle(image, (150, 150), (250, 250), (0,), 3)
    success, encoded = cv2.imencode(".png", image)
    assert success
    return encoded.tobytes()


def _make_blank_image_bytes() -> bytes:
    image = np.zeros((100, 100), dtype=np.uint8)
    success, encoded = cv2.imencode(".png", image)
    assert success
    return encoded.tobytes()


def test_extract_features_returns_keypoints_and_descriptors():
    image_bytes = _make_textured_image_bytes(seed=1)
    keypoints, descriptors = extract_features(image_bytes)
    assert len(keypoints) > 0
    assert descriptors.shape[0] == len(keypoints)


def test_extract_features_rejects_blank_image():
    with pytest.raises(FeatureExtractionError):
        extract_features(_make_blank_image_bytes())


def test_matching_same_image_scores_high():
    image_bytes = _make_textured_image_bytes(seed=42)
    kp_raw, desc = extract_features(image_bytes)
    kp = serializable_to_keypoints(kp_raw)

    score = match_with_keypoints(kp, desc, kp, desc)
    assert score > 0  # une image comparée à elle-même doit produire des matchs


def test_matching_different_images_scores_lower():
    image_a_bytes = _make_textured_image_bytes(seed=1)
    image_b_bytes = _make_textured_image_bytes(seed=999)

    kp_a_raw, desc_a = extract_features(image_a_bytes)
    kp_b_raw, desc_b = extract_features(image_b_bytes)
    kp_a = serializable_to_keypoints(kp_a_raw)
    kp_b = serializable_to_keypoints(kp_b_raw)

    self_score = match_with_keypoints(kp_a, desc_a, kp_a, desc_a)
    cross_score = match_with_keypoints(kp_a, desc_a, kp_b, desc_b)

    assert self_score >= cross_score
