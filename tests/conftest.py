import base64
import secrets

import pytest


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    """Isole chaque test : clés jetables + fichier de templates temporaire."""
    monkeypatch.setenv("SERVICE_AUTH_TOKEN", "test-token-" + secrets.token_urlsafe(16))
    monkeypatch.setenv("BIOMETRIC_ENCRYPTION_KEY", base64.b64encode(secrets.token_bytes(32)).decode())
    monkeypatch.setenv("ALLOWED_ORIGINS", "[]")
    monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "audit"))

    from biometric_core.config import get_settings
    get_settings.cache_clear()

    settings = get_settings()
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "TEMPLATES_FILE", tmp_path / "templates.enc")

    import biometric_core.encryption as encryption_module
    encryption_module._cipher_instance = None

    # app.config n'existe que dans biometric-api : import tolérant pour que
    # les tests de tests/core/ (qui ne testent que biometric_core seul,
    # sans jamais importer biometric-api) fonctionnent aussi sans lui.
    try:
        from app.config import get_api_settings
        get_api_settings.cache_clear()
    except ImportError:
        get_api_settings = None

    yield

    get_settings.cache_clear()
    encryption_module._cipher_instance = None
    if get_api_settings is not None:
        get_api_settings.cache_clear()
