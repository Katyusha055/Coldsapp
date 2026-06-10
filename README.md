# Coldsapp

Backend API for repair shop management. Tracks clients and repair tickets with per-tenant data isolation. Built for small shops in Latin America that currently manage their workflow through WhatsApp.

## Stack

- **Backend:** Python 3.12, FastAPI, Pydantic v2, psycopg (no ORM)
- **Auth:** PyJWT, pwdlib
- **Database:** PostgreSQL
- **Deploy:** Railway + Docker
- **Frontend:** in development (see below, it will be using VueJS, Javascript, and NodeJS)

## Local development

```bash
git clone https://github.com/Katyusha055/Coldsapp
cd coldsapp_second

cp .env.example .env
# fill in the required values in .env

docker compose up
```

The API will be available at `http://localhost:8000`. Interactive docs at `/docs`.

**Running tests:**

```bash
cp backend/.env.tests.example backend/.env.tests
# fill in test DB credentials — DB_NAME must contain the word "test"

pytest backend/
```

Tests run against a real PostgreSQL database. Each test truncates all tables on teardown.

## Environment variables

See `.env.example` for the application and `backend/.env.tests.example` for the test suite. Both files list all required variables with empty values.

## Frontend

The frontend is currently in development and will be added to this repository once ready. When available, it will provide a complete interface for shop operators and make the application self-explanatory for end users.
