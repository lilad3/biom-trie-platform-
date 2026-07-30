# biometric-core

Le cœur biométrique **pur** de la plateforme. Zéro dépendance à HTTP, FastAPI,
Django, ou tout autre framework. Ce package ne fait que :

- **Extraction** : image → keypoints/descripteurs SIFT (avec CLAHE pour le contraste).
- **Matching** : deux jeux de descripteurs → score de correspondance (FLANN + ratio de Lowe + validation géométrique RANSAC).
- **Chiffrement** : AES-256-GCM strict pour les templates (nonce unique, AAD lié à l'employé).
- **Stockage** : persistance chiffrée des templates sur disque (JSON + tokens chiffrés individuellement).

Ce package **ne connaît jamais** : utilisateurs, JWT, rôles, HTTP, endpoints, requêtes réseau.
C'est `biometric-api` (ou toute autre application) qui l'utilise et l'expose via un protocole.

## Installation

En développement (depuis `biometric-platform/`) :

```bash
pip install -e ./biometric-core
```

## Utilisation

```python
from biometric_core import extract_features, count_good_matches

keypoints, descriptors = extract_features(image_bytes)
```

## Configuration

Toute la configuration passe par un fichier `.env` dans le répertoire de travail
de l'application hôte (voir `biometric_core.config.Settings` pour la liste complète
des variables : clés de chiffrement, seuils de matching, limites de validation d'image...).

## Tests

Les tests de ce package se trouvent dans `biometric-platform/tests/core/`.
