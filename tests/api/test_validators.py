import base64

import cv2
import numpy as np
import pytest

from app.security.validators import ImageValidationError, validate_and_decode


def _valid_png_base64() -> str:
    image = np.random.randint(0, 255, size=(200, 200), dtype=np.uint8)
    success, encoded = cv2.imencode(".png", image)
    assert success
    return base64.b64encode(encoded.tobytes()).decode()


def test_accepts_valid_png():
    raw = validate_and_decode(_valid_png_base64())
    assert len(raw) > 0


def test_rejects_invalid_base64():
    with pytest.raises(ImageValidationError):
        validate_and_decode("not-valid-base64!!!")


def test_rejects_non_image_bytes():
    fake = base64.b64encode(b"this is definitely not an image").decode()
    with pytest.raises(ImageValidationError):
        validate_and_decode(fake)


def test_rejects_oversized_declared_as_image(monkeypatch):
    from biometric_core.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("MAX_IMAGE_SIZE", "10")  # 10 octets max, forcément dépassé
    with pytest.raises(ImageValidationError):
        validate_and_decode(_valid_png_base64())
    get_settings.cache_clear()


def test_strips_data_url_prefix():
    payload = "data:image/png;base64," + _valid_png_base64()
    raw = validate_and_decode(payload)
    assert len(raw) > 0
