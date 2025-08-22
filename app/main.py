from fastapi import FastAPI
from app.api.v1.routes import (auth, addresses, organizers, venues, sectors, events, seats, ticket_types,
                               event_ticket_types, booking, cart, payment_methods, payments)

app = FastAPI()
app.include_router(auth.router)
app.include_router(addresses.router)
app.include_router(organizers.router)
app.include_router(venues.router)
app.include_router(sectors.router)
app.include_router(events.router)
app.include_router(seats.router)
app.include_router(ticket_types.router)
app.include_router(event_ticket_types.router)
app.include_router(booking.router)
app.include_router(cart.router)
app.include_router(payment_methods.router)
app.include_router(payments.router)
