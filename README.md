# Coldsapp

CRM for repair shops in Latin America. Tracks clients and repair tickets with per-tenant data isolation. Built for small shops that currently manage their workflow through WhatsApp.

## Stack

- **Backend:** Python 3.12, FastAPI, Pydantic v2, psycopg (no ORM)
- **Frontend:** Vue.js 3, PrimeVue 4 (Aura theme), Vue Router, Vite, Nginx (production)
- **Auth:** PyJWT, pwdlib
- **Database:** PostgreSQL
- **WhatsApp:** [Evolution API](https://github.com/EvolutionAPI/evolution-api) (self-hosted, Baileys-based)
- **Deploy:** Railway + Docker

## WhatsApp integration

Each shop connects one WhatsApp number by scanning a QR code, generated via a self-hosted [Evolution API](https://github.com/EvolutionAPI/evolution-api) instance. Once connected:

- Incoming messages from unknown numbers are queued as "pending contacts" for the shop to convert into clients or discard.
- Ticket status changes (e.g. "ready for pickup") trigger an outbound WhatsApp notification to the client, if one is configured with a phone number.
- Live updates (new messages, connection status) reach the frontend over SSE (`GET /whatsapp/events`).

Evolution API is unofficial (built on the reverse-engineered Baileys library), which is why contacts are keyed by `remote_jid` rather than phone number — see `dev_notes.md` for the reasoning. Migrating to Meta's official Cloud API is a planned phase 2 item.

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
