import app.core.security as security
import time_machine
from jose import jwt
from datetime import datetime, timezone, timedelta


def test_hash_password_returns_non_plaintext():
    password = "Pass!WorD12@3"
    h = security.hash_password(password)
    assert isinstance(h, str)
    assert h != password


def test_verify_password_true_for_correct():
    password = "Pass!WorD12@3"
    h = security.hash_password(password)
    assert security.verify_password(password, h) is True


def test_verify_password_false_for_incorrect():
    password = "Pass!WorD12@3"
    h = security.hash_password(password)
    assert security.verify_password("Password123", h) is False


@time_machine.travel("2025-01-01 12:00:00", tick=False)
def test_create_access_token_contains_expected_claims(monkeypatch):
    monkeypatch.setattr(security, "SECRET_KEY", "fake-key")

    token = security.create_access_token(subject=1, roles=["ADMIN", "CUSTOMER"])
    payload = jwt.decode(token, "fake-key", algorithms=[security.ALGORITHM])

    now = datetime.now(timezone.utc)
    assert payload["iat"] == int(now.timestamp())
    assert payload["exp"] == int((now + timedelta(minutes=30)).timestamp())
    assert payload["roles"] == ["ADMIN", "CUSTOMER"]
    assert payload["sub"] == '1'
