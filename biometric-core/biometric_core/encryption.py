"""
biometric_core.encryption
=====================
Chiffrement AES-256-GCM strict pour les templates biométriques.

Garanties :
- Clé de 256 bits exclusivement chargée depuis .env (BIOMETRIC_ENCRYPTION_KEY).
- Un nonce aléatoire de 12 octets à CHAQUE chiffrement (jamais réutilisé).
- Confidentialité + intégrité + authenticité (GCM = AEAD).
- Support d'"associated data" pour lier cryptographiquement un template à
  son identifiant (empêche la substitution d'un template chiffré d'un
  employé vers un autre sans casser le déchiffrement).
- Erreurs distinctes pour clé invalide (config cassée) vs échec de
  déchiffrement (donnée altérée/corrompue).
"""
from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from biometric_core.config import get_settings

NONCE_SIZE_BYTES = 12
KEY_SIZE_BYTES = 32  # AES-256


class InvalidKeyError(Exception):
    """La clé de chiffrement est absente, mal formée, ou n'a pas la bonne longueur."""


class DecryptionError(Exception):
    """Le déchiffrement a échoué : tag d'authentification invalide (donnée altérée) ou mauvaise clé."""


def _load_key() -> bytes:
    settings = get_settings()
    raw = settings.BIOMETRIC_ENCRYPTION_KEY
    if not raw:
        raise InvalidKeyError("BIOMETRIC_ENCRYPTION_KEY est absent de la configuration (.env).")
    try:
        key = base64.b64decode(raw, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise InvalidKeyError("BIOMETRIC_ENCRYPTION_KEY n'est pas du base64 valide.") from exc
    if len(key) != KEY_SIZE_BYTES:
        raise InvalidKeyError(
            f"BIOMETRIC_ENCRYPTION_KEY doit décoder vers exactement {KEY_SIZE_BYTES} octets "
            f"(AES-256) ; obtenu {len(key)} octets."
        )
    return key


class AesGcmCipher:
    """
    Encapsule AESGCM avec une clé chargée une seule fois (fail-fast au démarrage
    du service si la clé est absente/invalide, plutôt qu'un échec silencieux
    au premier appel).
    """

    def __init__(self) -> None:
        self._key = _load_key()
        self._aesgcm = AESGCM(self._key)

    def encrypt(self, plaintext: bytes, associated_data: bytes | None = None) -> str:
        """
        Chiffre `plaintext`. Retourne une chaîne base64 = nonce(12) || ciphertext_avec_tag.
        `associated_data` (ex: employeeId encodé) est authentifié mais pas chiffré :
        toute modification de l'AAD entre chiffrement et déchiffrement fait échouer
        le déchiffrement, ce qui empêche de réassocier un template à un autre employé.
        """
        nonce = os.urandom(NONCE_SIZE_BYTES)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, associated_data)
        return base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, token: str, associated_data: bytes | None = None) -> bytes:
        try:
            raw = base64.b64decode(token, validate=True)
        except Exception as exc:  # noqa: BLE001
            raise DecryptionError("Token chiffré mal formé (base64 invalide).") from exc

        if len(raw) < NONCE_SIZE_BYTES:
            raise DecryptionError("Token chiffré trop court pour contenir un nonce valide.")

        nonce, ciphertext = raw[:NONCE_SIZE_BYTES], raw[NONCE_SIZE_BYTES:]
        try:
            return self._aesgcm.decrypt(nonce, ciphertext, associated_data)
        except Exception as exc:  # noqa: BLE001
            # Toute exception ici (InvalidTag, etc.) signifie : donnée corrompue,
            # altérée, ou mauvaise clé/AAD. On ne distingue pas la cause précise
            # côté appelant pour ne pas donner d'oracle à un attaquant.
            raise DecryptionError("Échec du déchiffrement : donnée corrompue, altérée, ou clé/AAD incorrecte.") from exc

    def encrypt_json(self, data: dict, associated_data: bytes | None = None) -> str:
        import json
        return self.encrypt(json.dumps(data).encode("utf-8"), associated_data)

    def decrypt_json(self, token: str, associated_data: bytes | None = None) -> dict:
        import json
        return json.loads(self.decrypt(token, associated_data).decode("utf-8"))


_cipher_instance: AesGcmCipher | None = None


def get_cipher() -> AesGcmCipher:
    """Singleton paresseux : la clé n'est chargée/validée qu'au premier usage réel."""
    global _cipher_instance
    if _cipher_instance is None:
        _cipher_instance = AesGcmCipher()
    return _cipher_instance
