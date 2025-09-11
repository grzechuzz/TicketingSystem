import hmac, secrets, hashlib, uuid
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from .config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, JWT_ISSUER, JWT_AUDIENCE
from datetime import timedelta, datetime, timezone
from jose import jwt

ph = PasswordHasher()


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, password)
    except VerifyMismatchError:
        return False


def create_access_token(subject: str | int, *, sid: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
        "typ": "access",
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE
    }
    if sid:
        payload["sid"] = sid
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str, pepper: str) -> str:
    return hmac.new(pepper.encode(), token.encode(), hashlib.sha256).hexdigest()


def new_expiry(days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)
