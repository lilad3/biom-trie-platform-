import base64
import secrets

import pytest

from biometric_core.encryption import AesGcmCipher, DecryptionError, InvalidKeyError


def test_encrypt_decrypt_roundtrip():
    cipher = AesGcmCipher()
    token = cipher.encrypt(b"hello world")
    assert cipher.decrypt(token) == b"hello world"


def test_nonce_is_unique_per_call():
    cipher = AesGcmCipher()
    token1 = cipher.encrypt(b"same plaintext")
    token2 = cipher.encrypt(b"same plaintext")
    assert token1 != token2  # même clé, même message -> ciphertext différent grâce au nonce aléatoire


def test_aad_binds_ciphertext_to_employee_id():
    cipher = AesGcmCipher()
    token = cipher.encrypt(b"template data", associated_data=b"EMP001")
    # Déchiffrement avec le bon AAD : OK
    assert cipher.decrypt(token, associated_data=b"EMP001") == b"template data"
    # Déchiffrement avec un AAD différent (tentative de substitution) : doit échouer
    with pytest.raises(DecryptionError):
        cipher.decrypt(token, associated_data=b"EMP002")


def test_tampered_ciphertext_is_rejected():
    cipher = AesGcmCipher()
    token = cipher.encrypt(b"sensitive template")
    raw = bytearray(base64.b64decode(token))
    raw[-1] ^= 0xFF  # altère le dernier octet (dans le tag d'authentification)
    tampered = base64.b64encode(bytes(raw)).decode()
    with pytest.raises(DecryptionError):
        cipher.decrypt(tampered)


def test_invalid_key_length_rejected(monkeypatch):
    from biometric_core.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("BIOMETRIC_ENCRYPTION_KEY", base64.b64encode(secrets.token_bytes(16)).decode())
    with pytest.raises(InvalidKeyError):
        AesGcmCipher()
    get_settings.cache_clear()


def test_missing_key_rejected(monkeypatch):
    from biometric_core.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("BIOMETRIC_ENCRYPTION_KEY", "")
    with pytest.raises(InvalidKeyError):
        AesGcmCipher()
    get_settings.cache_clear()
