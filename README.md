# 🎫 Ticketing System API 🎫
## 📝 Overview
***
A modular REST API for event ticketing. Built with FastAPI, Pydantic, Alembic, PostgreSQL, SQLAlchemy-async, Redis and Docker.

It enables creating and managing events of various types — seated, general admission (GA) or hybrid layouts — along with complete support for ticket sales, reservations, payments and invoices. It supports both personalized tickets requiring attendee data and general access tickets without user details.

The system includes role-based access control with three predefined roles (<kbd>CUSTOMER</kbd>, <kbd>ORGANIZER</kbd>, <kbd>ADMIN</kbd>) and provides the ability to manage users and assign roles directly through the API.

Also features an integrated auditing module (Redis Streams + background worker) for tracking all critical actions.
***
## ⚙️ Requirements
* Docker
* Linux, macOS or Windows with WSL (or Git Bash)
***
## 🚀 Quick start
### 1. Clone repository
<kbd>git clone https://github.com/grzechuzz/FastAPI-TicketingSystem.git</kbd>
### 2. Generate .env and secrets
<kbd>chmod +x setup.sh</kbd>\
<kbd>./setup.sh</kbd>
### 3. Start the stack
<kbd>docker compose up -d</kbd>
### 4. Access the API
Swagger UI: http://127.0.0.1:8000/docs 

Admin credentials are displayed in the terminal output after running **setup.sh** script. You can use them to log in via the `auth/login` endpoint in Swagger.
### Useful commands
API logs: <kbd>docker compose logs -f api</kbd>\
Stop: <kbd>docker compose down</kbd>\
Stop and remove data: <kbd>docker compose down -v</kbd>\
Run again: <kbd>docker compose up -d</kbd>
> **Note:** The setup.sh script is intended for local development and demo environments.
> In production, you should create the .env file and secrets manually, following your own deployment and security polices.
***
## 🧠 Tech Stack
* **FastAPI** — async REST framework
* **Pydantic** — data validation and settings management  
* **SQLAlchemy (async)** — ORM  
* **Alembic** — migrations  
* **PostgreSQL** — database  
* **Redis Streams** — audit/event queue  
* **Docker** - containerization