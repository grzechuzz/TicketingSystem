from fastapi import FastAPI
from app.api.v1.routes import auth

app = FastAPI()
app.include_router(auth.router)
