# Coldsapp

CRM for repair shops in Latin America. Tracks clients and repair tickets with per-tenant data isolation. Built for small shops that currently manage their workflow through WhatsApp.

## Stack

- **Backend:** Python 3.12, FastAPI, Pydantic v2, psycopg (no ORM)
- **Frontend:** Vue.js 3, PrimeVue 4 (Aura theme), Vue Router, Vite, Nginx (production)
- **Auth:** PyJWT, pwdlib
- **Database:** PostgreSQL
- **Deploy:** Railway + Docker

## Production

- Backend: https://coldsapp.up.railway.app
- Frontend: https://coldsapp.up.railway.app

## Local development

```bash
git clone https://github.com/Katyusha055/Coldsapp
cd coldsapp_second

cp .env.example .env
# fill in the required values in .env

docker compose up
```

The API will be available at `http://localhost:8000`. Interactive docs at `/docs`. The frontend will be available at `http://localhost:5173`.

**Running tests:**

```bash
cp backend/.env.tests.example backend/.env.tests
# fill in test DB credentials — DB_NAME must contain the word "test"

pytest backend/
```

Tests run against a real PostgreSQL database. Each test truncates all tables on teardown.

## Environment variables

See `.env.example` for the application, `backend/.env.tests.example` for the test suite, and `frontend/src/services/.env.example` for the frontend. All files list all required variables with empty values.
