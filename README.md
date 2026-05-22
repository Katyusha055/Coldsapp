# Coldsapp Backend API

## The Problem

Repair shops and technicians in Latin America typically manage their entire client workflow through WhatsApp — no ticketing system, no status tracking, no history. When a shop handles dozens of open repairs simultaneously, it becomes impossible to keep track of what's pending, what's ready, and who has been contacted.

Coldsapp solves this by providing a backend that centralizes clients and repair tickets, with a clear status lifecycle and per-tenant data isolation. The eventual frontend (likely Vue.js) will consume this API to give technicians a simple, usable interface.

---

## Overview

FastAPI backend following a layered architecture organized by feature. Currently exposes two modules: `clients` and `tickets`.

**Tech stack:** Python 3.12, FastAPI, Pydantic v2, psycopg (PostgreSQL driver), uvicorn.

---

## Architecture

Each feature follows the same three-layer structure:

```
router.py     → HTTP boundary: path params, request/response models, status codes
service.py    → Business logic: validation, orchestration, DB connection lifecycle
repository.py → SQL: queries and persistence contracts
models.py     → Pydantic request/response schemas
schema.py     → DB table creation (called at app startup)
```

App entrypoint: `backend/main.py`
Router aggregator: `backend/api/routers.py`

---

## Authentication

There is no real auth system yet. `backend/core/auth.py` exposes `get_user_id()` which always returns `1`. All endpoints behave as if the authenticated user is always `user_id = 1`.

Operational implications:
- Every request is scoped to `user_id = 1`.
- Tests seed a user with `id = 1` to align with this.
- The DB schema enforces per-user ownership at the query level (all queries filter by `user_id`), so the isolation logic is already in place for when real auth is added.
- Replacing auth requires only changing `get_user_id()` — no other layer needs to change.

---

## Data Models

### Users
```
id            SERIAL PRIMARY KEY
name          VARCHAR NOT NULL
phone         VARCHAR NOT NULL
password_hash VARCHAR NOT NULL
```
Not directly exposed through the API yet.

### Clients
```
id          SERIAL PRIMARY KEY
user_id     INTEGER FK → users.id ON DELETE CASCADE
name        VARCHAR NOT NULL
phone       VARCHAR NOT NULL
description TEXT (nullable)
created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
```
Index on `phone` (`clients_phone_index`).

### Tickets
```
id           SERIAL PRIMARY KEY
user_id      INTEGER FK → users.id ON DELETE CASCADE
client_id    INTEGER FK → clients.id ON DELETE CASCADE
title        VARCHAR(200) NOT NULL
description  TEXT (nullable)
status       VARCHAR(20) NOT NULL DEFAULT 'pending'
             CHECK (status IN ('pending','in_progress','ready','delivered','cancelled'))
received_at  TIMESTAMPTZ DEFAULT NOW()
ready_at     TIMESTAMPTZ (nullable, set automatically when status → 'ready')
delivered_at TIMESTAMPTZ (nullable, set automatically when status → 'delivered')
deleted_at   TIMESTAMPTZ (nullable, soft-delete marker)
created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
```
Indexes on `client_id` and `status`.

---

## Ticket Status Lifecycle

Status transitions are strictly enforced by the service layer. Only the following moves are valid:

```
pending  ──→  in_progress  ──→  ready  ──→  delivered
   └──────────────┴──────────────┴─────────→  cancelled
```

| From        | Allowed targets              |
|-------------|------------------------------|
| pending     | in_progress, cancelled       |
| in_progress | ready, cancelled             |
| ready       | delivered, cancelled         |
| delivered   | (none — terminal state)      |
| cancelled   | (none — terminal state)      |

Any other transition returns `400 Bad Request`.

Side effects on status change:
- Transitioning to `ready` → `ready_at` is set to the current UTC time.
- Transitioning to `delivered` → `delivered_at` is set to the current UTC time.
- These fields are set by the service layer, not the DB default.

---

## Multi-tenant Isolation

Every query in every repository function filters by `user_id`. A user can never read, modify, or delete a record that belongs to another user — even if they know the `id`. Attempting to access another tenant's record returns `404` (not `403`), to avoid leaking whether the record exists.

---

## Clients Endpoints

FastAPI's auto-docs (`/docs`) cover request/response schemas and 422 validation errors. This section documents behavior that is not visible there.

---

### `GET /clients/`
Returns all clients belonging to the current user, ordered by `id ASC`. Returns an empty list if none exist — never 404.

---

### `POST /clients/`
Creates a client owned by the current user. `user_id` is injected server-side from auth and is never accepted from the request body.

---

### `GET /clients/{client_id}`
- `404` when the client does not exist **or** belongs to a different user.

---

### `GET /clients/by-phone/{phone}`
- `404` when no client with that phone exists for the current user.
- Matches exact phone string — no normalization or partial matching.

---

### `PATCH /clients/{client_id}`
Only fields explicitly provided with a non-null value are updated. Omitted fields or `null` values are ignored (the router applies `exclude_none=True` before passing to the service).

- `404` when the client does not exist or belongs to a different user.
- If all provided fields are `null` or missing, the repository raises an unhandled `ValueError` (results in `500`). Sending at least one non-null field avoids this.

---

### `DELETE /clients/{client_id}`
**Hard delete** — the row is permanently removed from the database.

Response is always `200 OK` with a JSON body, regardless of whether the row existed:

```json
{ "deleted": true,  "id": 10 }
{ "deleted": false, "id": 99 }
```

`deleted: false` means the row did not exist for the current user. This endpoint never returns `404`.

---

## Tickets Endpoints

---

### `POST /tickets/`
Creates a ticket. `user_id` is injected server-side.

Business logic validation (not visible in schema):
- `client_id` must refer to a client that exists **and** belongs to the current user.
- `404` if the client is not found or belongs to a different user.

Initial state: `status = 'pending'`, `ready_at = null`, `delivered_at = null`.

---

### `GET /tickets/`
Returns all non-deleted tickets belonging to the current user, ordered by `created_at DESC`. Returns an empty list if none exist.

---

### `GET /tickets/{ticket_id}`
- `404` when the ticket does not exist, has been soft-deleted, or belongs to a different user.

---

### `DELETE /tickets/{ticket_id}`
**Soft delete** — sets `deleted_at = NOW()`. The row remains in the database but is excluded from all subsequent queries.

- `204 No Content` on success (no response body).
- `404` when the ticket does not exist, is already deleted, or belongs to a different user.

Unlike the clients delete, this endpoint does return `404` on failure.

---

### `PATCH /tickets/{ticket_id}/status`
Updates the ticket status following the transition rules described above.

- `400` when the requested transition is not allowed (e.g., `pending → delivered`). Detail message: `"Cannot transition from {current} to {new}"`.
- `404` when the ticket does not exist or belongs to a different user.
- `ready_at` and `delivered_at` are set automatically as a side effect — they cannot be set directly through the API.

---

### `PATCH /tickets/{ticket_id}`
Updates `title` and/or `description`. This endpoint does **not** update `status`, `client_id`, or any timestamp — use `/status` for status changes.

- `400` with `"No fields to update"` when both `title` and `description` are absent or `null`.
- `404` when the ticket does not exist or belongs to a different user.

---

## Testing

Run the full test suite from the project root:

```bash
pytest backend/
```

Requires a `backend/.env.tests` file (git-ignored) pointing to a test database. Use `backend/clients/tests/.env.tests` as reference for the expected variables (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`). The database name must contain the word `test` — the test loader enforces this as a safety check.

### Test structure

```
backend/
  conftest.py                        # Shared fixtures: load_test_env, api_client,
                                     #   clean_db (autouse), create_user
  clients/tests/
    repository_test.py               # Unit tests for the repository layer (mocked DB)
    service_test.py                  # Integration tests via API against the test DB
    multi_tenant_test.py             # Tenant isolation: user A cannot access user B's clients
    schema_test.py                   # (placeholder)
  tickets/tests/
    service_test.py                  # Unit tests for the service layer (mocked dependencies)
    api_test.py                      # Integration tests via API against the test DB
    multi_tenant_test.py             # Tenant isolation: user A cannot access user B's tickets
```

`clean_db` runs after every test and truncates `tickets`, `clients`, and `users` with `RESTART IDENTITY CASCADE`, so tests are fully isolated from each other.
