from fastapi import FastAPI
from app.api.v1.routes import auth, addresses, organizers, venues

app = FastAPI()
app.include_router(auth.router)
app.include_router(addresses.router)
app.include_router(organizers.router)
app.include_router(venues.router)
