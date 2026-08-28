# Coldsapp

CRM for repair shops in Latin America. Tracks clients and repair tickets with per-tenant data isolation. Built for small shops that currently manage their workflow through WhatsApp.

## Stack

- **Backend:** Python 3.11, FastAPI, Pydantic v2, psycopg (no ORM)
- **Frontend:** Vue.js 3, PrimeVue 4 (Aura theme), Pinia, Vue Router, Vite, Nginx (production)
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

## Contacts

Separate from ticket/client contacts: this is the broadcast/marketing contact list for a shop's connected WhatsApp number, used for future bulk messaging.

- `POST /contacts/import` reconciles Evolution's `findContacts` and `findChats` (neither alone returns the full contact set) into one list, keyed by a resolved `remote_jid` — `@lid`-only entries with no resolvable number are discarded, never stored.
- `GET /contacts` lists contacts with `opted_out = false`; the blacklist (`opted_out = true`) is the same table, not a separate one — there's no DELETE endpoint, since a hard delete would just reappear on the next import.
- Contact names can be edited manually; a blank/missing name is never persisted as a placeholder string in the backend or the database — "Sin Nombre" is applied only in the frontend's read layer.
- Frontend: `Contactos > Todos` and `Contactos > Lista Negra`, each with name search, pagination, and inline `opted_out` editing.

See `dev_notes.md`'s "Contacts module" section for the full reconciliation/edge-case rationale, and `SECURITY.md` for the hardening work done so far (part 1 of an OWASP-oriented pass; part 2 — rate limiting, webhook apikey validation, short-lived SSE tokens — is still pending).

## Local development

```bash
git clone https://github.com/Katyusha055/Coldsapp
cd Coldsapp

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

- `.env.example` — the backend/database/Evolution config used by `docker compose up` (`api` and `db` services).
- `.env.evo.example` — config for the self-hosted `evolution-api` and its own Postgres/Redis services.
- `backend/.env.tests.example` — used only when running `pytest` directly (outside Docker).

All three list every required variable with an empty value. There's no separate frontend `.env`: `VITE_API_URL` is baked in at build time from the root `.env` as a Docker build arg in local development (see `docker-compose.yml`), and set through the hosting platform's own environment configuration in production — a frontend `.env` file would just be a second, easy-to-forget place to keep that value in sync.
