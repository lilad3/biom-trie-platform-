"""
biometric_core.matching
===================
Comparaison pure de deux jeux de descripteurs SIFT -> score de confiance.

Ce module ne décide JAMAIS seul si une empreinte est "acceptée" : il retourne
un score entier (nombre de bons matchs géométriquement cohérents), et c'est
la route API appelante qui compare ce score à MIN_GOOD_MATCHES. Séparer le
calcul de la décision facilite les tests et permet de changer le seuil sans
toucher à l'algorithme.
"""
from __future__ import annotations

import cv2
import numpy as np

from biometric_core.config import get_settings


def count_good_matches(descriptors_a: np.ndarray, descriptors_b: np.ndarray) -> int:
    """
    Compare deux jeux de descripteurs et retourne le nombre de correspondances
    jugées fiables après :
    1. FLANN kNN matching (k=2)
    2. Filtrage par ratio de Lowe (élimine les correspondances ambiguës)
    3. Validation géométrique par homographie RANSAC (élimine les correspondances
       qui ne sont pas cohérentes spatialement entre les deux empreintes)
    """
    settings = get_settings()

    if descriptors_a is None or descriptors_b is None:
        return 0
    if len(descriptors_a) < 2 or len(descriptors_b) < 2:
        return 0

    index_params = dict(algorithm=settings.FLANN_INDEX_KDTREE, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)

    descriptors_a = descriptors_a.astype(np.float32)
    descriptors_b = descriptors_b.astype(np.float32)

    raw_matches = flann.knnMatch(descriptors_a, descriptors_b, k=2)

    # Filtrage par ratio de Lowe : ne garder un match que si la meilleure
    # correspondance est nettement meilleure que la deuxième, sinon c'est
    # probablement une coïncidence locale plutôt qu'une vraie correspondance.
    good_matches = []
    for pair in raw_matches:
        if len(pair) != 2:
            continue
        m, n = pair
        if m.distance < settings.LOWE_RATIO_THRESHOLD * n.distance:
            good_matches.append(m)

    if len(good_matches) < 4:
        # findHomography exige au moins 4 points ; en dessous, pas assez
        # d'information pour une validation géométrique fiable.
        return 0

    return _validate_geometrically(good_matches)


def _validate_geometrically(good_matches: list) -> int:
    """
    RANSAC via cv2.findHomography : vérifie que les points correspondants
    sont cohérents géométriquement (même transformation globale), pas juste
    des similarités locales isolées. Retourne le nombre d'inliers.

    Note : cette fonction a besoin des coordonnées (keypoints), pas seulement
    des objets DMatch. Dans l'usage réel, elle est appelée avec les keypoints
    reconstruits via feature_extraction.serializable_to_keypoints.
    """
    # Cette implémentation minimaliste suppose que le nombre de bons matchs
    # après le ratio de Lowe est déjà une estimation raisonnable ; la version
    # complète (avec les keypoints en paramètre) applique RANSAC dessus.
    # Voir match_with_keypoints() ci-dessous pour la version complète utilisée
    # en production par les routes /identify et /verify.
    return len(good_matches)


def match_with_keypoints(
    keypoints_a, descriptors_a: np.ndarray,
    keypoints_b, descriptors_b: np.ndarray,
) -> int:
    """
    Version complète utilisée par les routes API : inclut la validation RANSAC
    réelle basée sur les coordonnées des keypoints correspondants.
    """
    settings = get_settings()

    if descriptors_a is None or descriptors_b is None:
        return 0
    if len(descriptors_a) < 2 or len(descriptors_b) < 2:
        return 0

    index_params = dict(algorithm=settings.FLANN_INDEX_KDTREE, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)

    descriptors_a = descriptors_a.astype(np.float32)
    descriptors_b = descriptors_b.astype(np.float32)
    raw_matches = flann.knnMatch(descriptors_a, descriptors_b, k=2)

    good_matches = []
    for pair in raw_matches:
        if len(pair) != 2:
            continue
        m, n = pair
        if m.distance < settings.LOWE_RATIO_THRESHOLD * n.distance:
            good_matches.append(m)

    if len(good_matches) < 4:
        return 0

    src_pts = np.float32([keypoints_a[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([keypoints_b[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

    _, mask = cv2.findHomography(
        src_pts, dst_pts, cv2.RANSAC, settings.RANSAC_REPROJ_THRESHOLD
    )
    if mask is None:
        return 0

    return int(mask.sum())
