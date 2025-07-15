from fastapi import FastAPI
from app.api.v1.routes import auth, addresses

app = FastAPI()
app.include_router(auth.router)
app.include_router(addresses.router)