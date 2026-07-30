"""
biometric_core
================
Cœur biométrique pur : extraction (CLAHE/SIFT), matching (FLANN/Lowe/RANSAC),
chiffrement (AES-256-GCM) et stockage chiffré des templates.

Ce package n'a AUCUNE dépendance à HTTP, FastAPI, Django ou tout autre
framework web. Il ne connaît ni utilisateurs, ni JWT, ni rôles. Il expose
uniquement des fonctions Python pures, testables isolément, et réutilisables
par n'importe quelle application (API REST, script, notebook...).

C'est la partie "biometric-core" de l'architecture décrite dans le cahier
des charges : elle ne doit jamais changer selon le framework qui l'utilise.
"""
from biometric_core.config import Settings, get_settings
from biometric_core.encryption import (
    AesGcmCipher,
    DecryptionError,
    InvalidKeyError,
    get_cipher,
)
from biometric_core.feature_extraction import (
    FeatureExtractionError,
    descriptors_from_list,
    descriptors_to_list,
    extract_features,
    keypoints_to_serializable,
    serializable_to_keypoints,
)
from biometric_core.matching import count_good_matches, match_with_keypoints
from biometric_core.storage import (
    add_template,
    delete_employee_templates,
    employee_count,
    get_employee_templates,
    iter_all_templates,
)

__version__ = "1.0.0"

__all__ = [
    "Settings",
    "get_settings",
    "AesGcmCipher",
    "DecryptionError",
    "InvalidKeyError",
    "get_cipher",
    "FeatureExtractionError",
    "extract_features",
    "keypoints_to_serializable",
    "serializable_to_keypoints",
    "descriptors_to_list",
    "descriptors_from_list",
    "count_good_matches",
    "match_with_keypoints",
    "add_template",
    "get_employee_templates",
    "iter_all_templates",
    "employee_count",
    "delete_employee_templates",
]
