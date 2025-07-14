from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from datetime import timedelta, datetime, timezone
from jose import jwt
import os

ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, password)
    except VerifyMismatchError:
        return False


SECURITY_KEY: str = os.getenv("SECURITY_KEY")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


def create_access_token(subject: str | int, roles: list[str]) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(subject),
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    return jwt.encode(payload, SECURITY_KEY, algorithm=ALGORITHM)