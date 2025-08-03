from fastapi import FastAPI
from app.api.v1.routes import auth, addresses, organizers, venues, sectors, events, seats

app = FastAPI()
app.include_router(auth.router)
app.include_router(addresses.router)
app.include_router(organizers.router)
app.include_router(venues.router)
app.include_router(sectors.router)
app.include_router(events.router)
app.include_router(seats.router)