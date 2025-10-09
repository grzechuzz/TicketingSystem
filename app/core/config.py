import os

def get_secret(secret_name: str) -> str | None:
    secret_path = f'/run/secrets/{secret_name}'
    try:
        with open(secret_path, 'r', encoding='utf-8') as secret_file:
            return secret_file.read().strip()
    except IOError:
        return os.getenv(secret_name)


DB_PASSWORD = get_secret('db_password')
SECRET_KEY = get_secret('secret_key')
REFRESH_TOKEN_PEPPER = get_secret('refresh_token_pepper')

POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
REDIS_URL = os.getenv("REDIS_URL")

if POSTGRES_USER and DB_PASSWORD and POSTGRES_DB:
    DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{POSTGRES_DB}"
else:
    raise ValueError("Can't build DATABASE_URL")  # TODO - implement custom exception class

REFRESH_ROTATE = True
REFRESH_SLIDING = False
REFRESH_TOKEN_TTL_DAYS = 30
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
JWT_ISSUER = "ticketing-api"
JWT_AUDIENCE = "ticketing-web"

AUDIT_STREAM = os.getenv("AUDIT_STREAM", "audit:events")
AUDIT_GROUP = os.getenv("AUDIT_GROUP", "audit-g1")
AUDIT_BATCH = int(os.getenv("AUDIT_BATCH", "200"))
AUDIT_BLOCK_MS = int(os.getenv("AUDIT_BLOCK_MS", "5000"))
