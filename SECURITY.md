# Security

This documents **part 1** of the OWASP-oriented hardening pass referenced in
`dev_notes.md` ("Security — planned work"). Four items, already implemented
in this PR, are recorded below with status, rationale, and known
limitations.

Part 2 is not started and is not covered here: rate limiting (especially on
`/auth/token`), webhook apikey validation, and replacing the long-lived JWT
currently used for SSE auth (`/whatsapp/events?token=`) with a short-lived,
scope-limited token. See `dev_notes.md`'s "Security — planned work" and the
"JWT passed as a query parameter for SSE" entry for the current state of
those.

---

## 1. Security headers

**What was implemented:** An `@app.middleware("http")` function
(`security_headers`, registered inside `setup_middleware()`) sets four
headers on every response, unconditionally:

- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), camera=(), microphone=()`

A fifth header is conditional:

- `Strict-Transport-Security: max-age=63072000; includeSubDomains` — only
  when `settings.is_production` **and** `request.url.scheme == "https"`.
  The scheme check exists because `request.url.scheme` reads `"https"`
  behind Railway's proxy (uvicorn is run with `--proxy-headers
  --forwarded-allow-ips='*'`, confirmed in the root `Dockerfile`'s `CMD`).
  Gating on both avoids sending HSTS on local `http://localhost`, where a
  browser that remembers the policy would then refuse to load the app
  over plain HTTP.

**Status:** Mitigated.

**Rationale:** `X-Frame-Options: DENY` blocks the app from being framed by
another origin (clickjacking). `X-Content-Type-Options: nosniff` stops the
browser from MIME-sniffing a response into an unintended content type.
`Referrer-Policy` limits what leaks in the `Referer` header on cross-origin
navigation to origin-only, not full path/query. `Permissions-Policy`
explicitly denies geolocation/camera/microphone at the browser level,
closing off those APIs even if a script injection ever occurred.
`Strict-Transport-Security` forces HTTPS on subsequent visits within
`max-age`, mitigating SSL-stripping/downgrade attacks once a client has
seen the header once over real HTTPS.

**Trade-offs / known limitations:**
- These headers are set on the **backend's** (FastAPI) JSON responses only.
  The actual page a browser renders and can be framed/navigated is served
  by the separate frontend container (nginx, `frontend/Dockerfile`). Its
  config, `frontend/nginx.conf`, sets **no headers at all** — checked
  directly, it's a bare `server` block with only `try_files` for SPA
  routing. So the browser-rendered app currently has none of this
  protection; only direct API responses do. `X-Frame-Options` on the API
  in particular protects little on its own, since a clickjacking attack
  would target the rendered SPA page, not a JSON endpoint.
- No `Content-Security-Policy` is implemented, despite CSP being listed
  in `dev_notes.md`'s "Post audit: security middlewares" as planned. Not
  done yet — not silently dropped, just not part of this PR.
- HSTS depends on the proxy correctly forwarding scheme information
  (`--forwarded-allow-ips='*'` trusts any forwarder, which is what Railway
  requires here but would be a spoofing risk behind an untrusted proxy).

**Code reference:** `backend/middleware.py`, `setup_middleware()` →
`security_headers` (nested `@app.middleware("http")` function). Called
from `backend/main.py`.

---

## 2. Automatic docs disabled in production

**What was implemented:** The FastAPI app is instantiated with:

```python
app = FastAPI(
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
)
```

`settings.DOCS_ENABLED` is set once in `Settings.__init__` as
`self.ENV != "production"` — i.e. docs are on for every value of `ENV`
except the literal string `"production"` (`ENV` itself is validated
against `{"development", "production"}` at startup; anything else raises
`RuntimeError` before the app can even boot).

**Status:** Mitigated.

**Rationale:** `/docs`, `/redoc`, and `/openapi.json` fully enumerate every
route, request/response schema, and field name in the API. Leaving them on
in production hands an attacker a ready-made map of the entire surface
(including routes they might not otherwise find) with no reconnaissance
effort.

**Trade-offs / known limitations:**
- This hides the schema; it doesn't restrict the routes themselves. Every
  endpoint is still reachable and still protected by whatever auth/
  authorization it already has (or doesn't) — this is obscurity on top of
  real controls, not a substitute for them.
- A single environment variable (`ENV`) gates this. If `ENV` is
  misconfigured to anything other than exactly `"production"` in a
  production deployment (e.g. left unset, defaulting to `"development"`),
  docs are exposed with no other check catching the mistake.

**Code reference:** `backend/main.py` (FastAPI instantiation) and
`backend/settings.py`, `Settings.__init__` (`self.DOCS_ENABLED = self.ENV
!= "production"`).

---

## 3. Global exception handler

**What was implemented:** `backend/main.py` registers a catch-all handler:

```python
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

It logs the full exception and traceback server-side (`logger.exception`,
which — per `backend/core/logging_config.py` — writes to both a rotating
file at `logs/app.log` and the console) and returns a fixed, generic JSON
body to the client: `{"detail": "Internal server error"}`, status 500. No
exception type, message, or traceback is ever included in the response.

**Status:** Mitigated.

**Rationale:** Without this, an unhandled exception (a bug, an
unanticipated DB error, a bad assumption about response shape) would
otherwise surface FastAPI/Starlette's default debug response, which can
include the exception message and, depending on configuration, a
traceback — leaking internal implementation details (file paths, query
structure, library versions) to whoever triggered the error.

**Trade-offs / known limitations:**
- This only handles bare `Exception`. `HTTPException` (and Starlette's
  `HTTPException`) is intercepted separately, upstream, by FastAPI's own
  default handler with its original status code and `detail` — by design,
  per the handler's own docstring. That's intentional: a `404 Client not
  found` or `409 Conflict` is a deliberate, safe response and should keep
  its specific message; this handler exists only for the genuinely
  *unplanned* case.
- It only covers exceptions raised during the normal request/response
  cycle. `backend/whatsapp/router.py`'s `/whatsapp/events` SSE endpoint
  streams via `EventSourceResponse` over an async generator
  (`whatsapp_events`); an exception raised inside that generator **after**
  the stream has started (headers already sent) cannot be converted into a
  clean 500 JSON body — by the time it happens, the response is already
  committed. This handler covers standard request handling; it doesn't
  cover a fault mid-stream on that one endpoint.
- Logging the traceback to `logs/app.log`/console assumes those are not
  themselves exposed anywhere. Not verified as part of this item — treat
  as an assumption, not a checked guarantee.

**Code reference:** `backend/main.py`, `unhandled_exception_handler`
(registered via `@app.exception_handler(Exception)`).

---

## 4. Centralized settings module

**What was implemented:** `backend/settings.py` defines a `Settings` class,
instantiated once as the module-level `settings` object, replacing what
were previously scattered `os.getenv()` calls across `connect.py`,
`auth/utils.py`, and various repositories. It:

- Calls `load_dotenv(override=False)` once, so real environment variables
  (Docker, Railway, the test suite) always win over the committed `.env`
  file.
- Reads and validates `ENV` against `{"development", "production"}`,
  raising `RuntimeError` at import time for anything else.
- Exposes `settings.is_production` (a `@property` returning `self.ENV ==
  "production"`) and `settings.DOCS_ENABLED` (derived from the same `ENV`
  check) — the mode flags items 1 and 2 above depend on.
- Loads every other required variable (`DB_*`, `SECRET_KEY`, `ALGORITHM`,
  `ACCESS_TOKEN_EXPIRE_HOURS`, `EVO_API_URL`, `EVO_API_TOKEN`,
  `WHATSAPP_WEBHOOK_URL`, `CORS_ORIGINS`) through a shared `_required()`
  helper that raises `RuntimeError` immediately if a required variable is
  missing or empty.

**Status:** Mitigated.

**Rationale:** Centralizing config means the production/development
distinction is decided in exactly one place instead of being re-derived
(potentially inconsistently) wherever a flag was needed. `_required()`
fails fast at startup — a misconfigured deployment (missing secret, missing
DB credential) crashes immediately with a clear message, instead of
surfacing as a confusing failure deep inside a request, or worse, running
with a silently empty/`None` secret.

**Trade-offs / known limitations:**
- `_required()` checks presence and non-emptiness, not value quality — a
  weak or accidentally-reused `SECRET_KEY`, for example, would still pass.
- `ENV` defaults to `"development"` when unset (`os.getenv("ENV",
  "development")`) rather than requiring it explicitly. A deployment that
  forgets to set `ENV=production` fails open into development mode
  (docs enabled, no HSTS) rather than failing to start — the opposite of
  the fail-fast behavior applied to the other variables.
- Validated at **import time**, which is early, but is still just Python
  running — there's no separate secret-management layer (e.g. a vault) and
  no runtime rotation; changing a value requires a redeploy/restart.

**Code reference:** `backend/settings.py`, `Settings` class (module-level
`settings` instance).

---

## 5. Client-side session isolation on logout

*Added after the part-1 pass above, in response to a reported bug — not part
of the original OWASP hardening PR.*

**What was implemented:** Pinia stores are module singletons that live for
the whole lifetime of the SPA's JS runtime, not for a login session. On
logout the frontend previously only removed the JWT and navigated away, so
the store contents stayed in memory. Three changes:

- `logout()` in `frontend/src/services/AuthService.js` now calls
  `removeToken()` **and** `resetStores()`, which calls Pinia's `$reset()`
  on every session-scoped store (currently `useContactsStore`).
- `Login.vue`'s `submit()` calls `resetStores()` on a successful login,
  before `saveToken()` — a guard for any logout path that doesn't route
  through `logout()`.
- `handleAuthError(err)` (the centralized 401 handler, item introduced in
  the same change) redirects with `window.location.assign(...)` rather than
  the SPA router, so session-expiry always triggers a full page reload,
  which recreates the runtime and drops all in-memory state independently
  of `resetStores()`.

**Status:** Mitigated.

**Rationale:** `contacts` (and `wa_pending_contacts`) are tenant-scoped by
`instance_id`, not `user_id`. After operator A logged out, the in-memory
contacts store still held A's rows. Operator B logging in on the same tab
without a hard refresh hit the store's cache guard in `loadContacts()`
(`if (this.loaded && !force) return;`) and was served A's contacts — a
cross-tenant data exposure, most plausible on a shared front-desk device. A
manual browser refresh cleared it only because that recreates the JS
runtime and re-initializes the store.

**Trade-offs / known limitations:**
- The store list inside `resetStores()` is maintained by hand. A new
  session-scoped Pinia store that isn't added there will leak across
  logins in exactly the same way. There is no framework enforcement — same
  class of gap as the manual tenancy filters noted elsewhere.
- `resetStores()` only clears Pinia state. Module-scoped or component
  state that outlives navigation would not be covered; there is none of
  note today, but the guarantee is "the stores we listed", not "all
  client state".
- The explicit topbar logout uses SPA navigation (no reload), so between
  that logout and the next login the previous data still sits in the JS
  heap until GC. `resetStores()` clears the store references immediately,
  which is the meaningful part, but the process is not memory-zeroed the
  way the `window.location` reload on the 401 path is.
- On the 401 path the full reload makes the `resetStores()` call inside
  `logout()` redundant; it is kept because the topbar logout path does not
  reload.
- The JWT in `localStorage` continues to be cleared only by
  `removeToken()` (unchanged) — see the "only the JWT lives in
  localStorage" note in `dev_notes.md`.

**Code reference:** `frontend/src/services/AuthService.js` (`logout`,
`resetStores`, `handleAuthError`); `frontend/src/views/pages/auth/Login.vue`
(`submit`).
