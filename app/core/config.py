import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
REFRESH_TOKEN_PEPPER = os.getenv("REFRESH_TOKEN_PEPPER")
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
