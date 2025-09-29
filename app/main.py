from fastapi import FastAPI
from app.api.v1.routes import (auth, addresses, organizers, venues, sectors, events, seats, ticket_types,
                               event_ticket_types, booking, cart, payment_methods, payments, orders, invoices,
                               tickets, users, admin_maintenance)
from app.core.middleware.request_id import RequestIdMiddleware
from app.core.redis import create_redis


async def lifespan(app: FastAPI):
    r = await create_redis()
    app.state.redis = r
    try:
        yield
    finally:
        await r.aclose()


app = FastAPI(lifespan=lifespan)
app.add_middleware(RequestIdMiddleware, header_name="X-Request-ID")
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
app.include_router(orders.router)
app.include_router(invoices.router)
app.include_router(tickets.router)
app.include_router(users.router)
app.include_router(admin_maintenance.router)
