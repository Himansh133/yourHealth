import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_rejects_short_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(jwt_secret="change-me")


def test_accepts_32_byte_jwt_secret():
    assert Settings(jwt_secret="x" * 32).jwt_secret == "x" * 32
