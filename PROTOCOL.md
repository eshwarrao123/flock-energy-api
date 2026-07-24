# Urja Meter Ops — Protocol Documentation

**Project:** Flock Energy — Urja Meter Ops API
**Version:** 1.0.0
**Last Updated:** 2026-07-24

---

## 1. Authentication Workflow

### 1.1 Session Cookie-Based Auth

The legacy Urja Meter Ops portal uses **session cookie-based authentication**. There is no JWT or token-based mechanism; the portal relies on server-side session state stored in cookies.

### 1.2 Login Flow

```
Client                          Portal
  |                                |
  |--- POST /login -------------->|
  |    Body: {username, password}  |
  |                                |
  |<-- 302 Redirect ---------------|
  |    Location: /dashboard       |
  |                                |
  |--- GET /dashboard ------------>|
  |    Cookie: session=<id>       |
  |                                |
  |<-- 200 OK ---------------------|
  |    Body: dashboard HTML       |
```

1. The client POSTs credentials (`username` and `password`) as form-encoded data to `/login`.
2. The portal responds with a `302` redirect to the dashboard.
3. The `httpx.AsyncClient` with `follow_redirects=True` automatically follows the redirect.
4. The session cookie is stored in the client's cookie jar and sent with subsequent requests.
5. If the portal returns a `401` or `403` on any subsequent request, the client triggers a re-authentication attempt (single retry).

### 1.3 Session Expiry

Sessions expire after a configurable timeout on the portal side. The API client detects expiry by checking for redirect-to-login or 401/403 responses and re-authenticates automatically once before raising an error.

### 1.4 Security Considerations

- Credentials are loaded from environment variables (`PORTAL_USERNAME`, `PORTAL_PASSWORD`).
- Passwords are never logged; the `Settings.__repr__` method masks the password field.
- **Cookie name**: The portal sets a session cookie (name unconfirmed without live credentials; `httpx` stores it automatically in its cookie jar).
- **HTTPS**: The portal base URL is `https://`, so cookies are transmitted over TLS. Whether the `HttpOnly` or `Secure` flag is set could not be confirmed without live access.
- **CSRF**: No CSRF token was observed in the login form fields used (`username`, `password`). If the portal adds a CSRF token in the future, the `login()` method would need a two-step GET-then-POST flow.

---

## 2. Discovered Endpoints

### 2.1 Meter List

| Property | Value |
|---|---|
| **URL** | `/meters` |
| **Method** | `GET` |
| **Query Params** | `page` (int, default 1), `page_size` (int, default 25) |
| **Auth Required** | Yes |
| **Response** | HTML table with columns: METER, SERIAL, MAKE, PHASE, STATUS, DT |

**Column order observed (via static analysis and parser defaults):** `METER` (→ `meter_id`), `SERIAL` (→ `serial_number`), `MAKE` (→ `make`), `PHASE` (→ `phase`), `STATUS` (→ `status`), `DT` (→ `dt_id`). The parser normalizes all headers to snake_case, so minor variations in casing or spacing are handled automatically.

### 2.2 Meter Detail

| Property | Value |
|---|---|
| **URL** | `/meters/{meter_id}` |
| **Method** | `GET` |
| **Path Params** | `meter_id` (string) |
| **Auth Required** | Yes |
| **Response** | HTML page with meter detail fields |

**Field mapping (inferred from parser):** The detail page renders key–value pairs in a two-column `<table>` or as `label: value` text nodes. Keys are normalized to snake_case. Recognized fields: `location` / `address`, `installation_date` / `installed`, `last_reading` / `reading`, `last_reading_at` / `last_updated`, `serial_number` / `serial`, `make`, `phase`, `status`, `dt_id` / `dt`. Any additional fields present in the HTML are ignored.

### 2.3 Consumption Data

| Property | Value |
|---|---|
| **URL** | `/meters/{meter_id}/consumption` |
| **Method** | `GET` |
| **Path Params** | `meter_id` (string) |
| **Query Params** | `from` (date, YYYY-MM-DD), `to` (date, YYYY-MM-DD) |
| **Auth Required** | Yes |
| **Response** | HTML table with columns: timestamp, kwh_import, kwh_export, kvah |

**Date-range filtering:** The `from` and `to` query parameters are listed as observed possibilities. The current client does not forward date-range parameters — it fetches all available readings and returns them. If the portal supports server-side filtering, passing `from`/`to` through the client would reduce data transfer.

### 2.4 Transformers

| Property | Value |
|---|---|
| **URL** | `/transformers` |
| **Method** | `GET` |
| **Auth Required** | Yes |
| **Response** | HTML table with columns: transformer_id, name, capacity_kva, meter_count |

**Column headers observed (inferred from parser):** `transformer_id` / `id`, `name` / `transformer_name`, `capacity_kva` / `capacity` / `kva`, `meter_count` / `meters` / `count`. All are normalized to snake_case. Additional metadata columns, if present, are silently ignored by the current parser.

### 2.5 Login Page

| Property | Value |
|---|---|
| **URL** | `/login` |
| **Method** | `GET` (renders form), `POST` (submits credentials) |
| **Auth Required** | No |
| **Response** | HTML login form |

---

## 3. Data Structures

### 3.1 MeterBase

| Field | Type | Description |
|---|---|---|
| `meter_id` | `str` | Unique identifier (e.g., `J100001`) |
| `serial_number` | `str` | Manufacturer serial number |
| `make` | `str` | Meter manufacturer (e.g., `Electra`, `Siemens`) |
| `phase` | `str` | Phase configuration (`Single` or `Three`) |
| `status` | `MeterStatus` | Enum: `Installed`, `Faulty`, `Decommissioned` |
| `dt_id` | `str` | Distribution transformer identifier |

### 3.2 MeterDetail

Extends `MeterBase` with:

| Field | Type | Description |
|---|---|---|
| `location` | `str \| None` | Physical installation location |
| `installation_date` | `date \| None` | Date of installation |
| `last_reading` | `float \| None` | Most recent reading value |
| `last_reading_at` | `datetime \| None` | Timestamp of last reading |

### 3.3 ConsumptionReading

| Field | Type | Description |
|---|---|---|
| `timestamp` | `datetime` | When the reading was recorded |
| `kwh_import` | `float` | Imported energy (kWh) |
| `kwh_export` | `float \| None` | Exported energy (kWh) |
| `kvah` | `float \| None` | Apparent energy (kVAh) |

### 3.4 Transformer

| Field | Type | Description |
|---|---|---|
| `transformer_id` | `str` | Unique identifier |
| `name` | `str` | Human-readable name |
| `capacity_kva` | `float \| None` | Rated capacity |
| `meter_count` | `int` | Number of meters served |

### 3.5 PaginatedMeters

| Field | Type | Description |
|---|---|---|
| `items` | `list[MeterBase]` | Meter objects for current page |
| `total` | `int` | Total matching records |
| `page` | `int` | Current page (1-indexed) |
| `page_size` | `int` | Items per page |

---

## 4. Portal Quirks and Known Issues

### 4.1 HTML-Based Data

The portal returns **HTML tables**, not JSON or XML. All data extraction is performed via BeautifulSoup parsing. The parser functions are designed to be resilient to:

- Missing columns (uses defaults)
- Malformed rows (skips with warning)
- Unexpected HTML structures (returns empty collections)

### 4.2 Column Name Variations

The portal may use different column header names for the same data across pages. The parser normalizes headers to snake_case and attempts multiple fallback key names (e.g., `meter_number`, `meter_no`, `METER` all map to the same field).

**Known column name variations handled by the parser:**

| Canonical Key | Accepted Raw Headers |
|---|---|
| `meter_id` | `METER`, `meter`, `id`, `meter_id` |
| `serial_number` | `SERIAL`, `serial`, `meter_number`, `serial_number` |
| `dt_id` | `DT`, `dt`, `dt_id` |
| `capacity_kva` | `capacity`, `kva`, `capacity_kva` |
| `meter_count` | `meters`, `count`, `meter_count` |

The `normalize_key()` function strips all non-alphanumeric characters, collapses multiple underscores, and lowercases the result before matching.

### 4.3 Date Format Inconsistencies

Date fields may appear in different formats across pages (ISO 8601, `YYYY-MM-DD`, or locale-specific formats). The parser attempts ISO 8601 parsing first and falls back gracefully.

**Date formats handled:** The parser attempts `datetime.fromisoformat()` (ISO 8601: `YYYY-MM-DDTHH:MM:SS`) and `date.fromisoformat()` (`YYYY-MM-DD`). Other locale-specific formats (e.g., `DD/MM/YYYY`) are not handled and will silently return `null` for the affected field.

### 4.4 Session Management

- The portal uses standard session cookies.
- Sessions may expire after a period of inactivity.
- The client handles session expiry by re-authenticating once before raising an error.

**Session timeout:** The portal-side session timeout is unknown without live access. The client handles expiry by re-authenticating once on receiving a 401, 403, or redirect-to-login response. If re-authentication also fails, the error is propagated to the caller as an HTTP 502.

### 4.5 Pagination

The meter list endpoint supports pagination via `page` and `page_size` query parameters. The default page size is 25, with a maximum of 1000.

**Pagination limits:** The API layer enforces a minimum of 1 and a maximum of 1000 for `page_size`. The portal itself does not appear to enforce a separate limit — the client fetches a single portal page per API request and slices the result set in Python. The maximum number of records per portal page is unknown without live testing.

### 4.6 Error Responses

The portal may return HTML error pages instead of HTTP error codes for certain failure scenarios. The API client treats any non-2xx response as an error.

**Error page patterns:** The portal is expected to return an HTML redirect (302 → `/login`) for unauthenticated requests and potentially an HTML error page for server-side failures. The API client treats any non-2xx final status as an error, wraps it in HTTP 502, and propagates a structured JSON error body to the caller.

---

## 5. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   FastAPI App                        │
│  ┌───────────────────────────────────────────────┐  │
│  │              API Router (/api/v1)             │  │
│  │  /health  /meters  /meters/{id}              │  │
│  │  /meters/{id}/consumption                     │  │
│  │  /transformers  /hierarchy                    │  │
│  └──────────────────┬────────────────────────────┘  │
│                     │                               │
│  ┌──────────────────▼────────────────────────────┐  │
│  │         Dependency Injection                   │  │
│  │  get_portal_client() → UrjaPortalClient       │  │
│  └──────────────────┬────────────────────────────┘  │
│                     │                               │
│  ┌──────────────────▼────────────────────────────┐  │
│  │           UrjaPortalClient                    │  │
│  │  - Async httpx client with cookie jar         │  │
│  │  - login() → POST /login                      │  │
│  │  - _ensure_auth() → GET /meters check         │  │
│  │  - get_meters_html()                          │  │
│  │  - get_meter_detail_html()                    │  │
│  │  - get_consumption_html()                     │  │
│  │  - get_transformers_html()                    │  │
│  └──────────────────┬────────────────────────────┘  │
│                     │                               │
│  ┌──────────────────▼────────────────────────────┐  │
│  │           HTML Parsers                        │  │
│  │  parse_meters_list()  → list[MeterBase]       │  │
│  │  parse_meter_detail() → MeterDetail           │  │
│  │  parse_consumption()  → list[ConsumptionReading]│
│  │  parse_transformers() → list[Transformer]     │  │
│  └──────────────────┬────────────────────────────┘  │
│                     │                               │
│  ┌──────────────────▼────────────────────────────┐  │
│  │           Pydantic Models                     │  │
│  │  MeterBase, MeterDetail, ConsumptionReading   │  │
│  │  Transformer, PaginatedMeters, MeterStatus    │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 6. Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `PORTAL_BASE_URL` | No | `https://urja-ops.flockenergy.tech` | Base URL of the Urja Meter Ops portal |
| `PORTAL_USERNAME` | Yes | *(none)* | Portal login username |
| `PORTAL_PASSWORD` | Yes | *(none)* | Portal login password |
| `REQUEST_TIMEOUT` | No | `30` | HTTP request timeout in seconds |

---

## 7. Running the API

```bash
# Copy environment file
cp .env.example .env

# Edit credentials
nano .env

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Access API docs
# http://localhost:8000/docs
```

---

## 8. Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/test_parser.py -v
```