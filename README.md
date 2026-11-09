# Flock Energy — Urja Meter Ops API

Flock Energy's Urja Meter Ops API is a production-grade FastAPI service that wraps the legacy Urja Meter Ops portal at `https://urja-ops.flockenergy.tech`. It authenticates via session-cookie login, scrapes the portal's HTML table responses using BeautifulSoup, and re-exposes the data as clean, validated JSON endpoints backed by Pydantic v2 models.

## Quick Start

```bash
# Clone and enter the project
git clone flock-energy-api
cd flock-energy-api

# Create a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate
# Windows: venv\Scripts\activate | Mac/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Access API docs
# Open http://localhost:8000/docs in your browser
```

## curl Examples

```bash
# Health check
curl http://localhost:8000/api/v1/health

# List meters (paginated)
curl "http://localhost:8000/api/v1/meters?page=1&page_size=25"

# Get meter detail
curl http://localhost:8000/api/v1/meters/J100001

# List transformers
curl http://localhost:8000/api/v1/transformers
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client (browser / curl)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/JSON
┌──────────────────────────▼──────────────────────────────────┐
│                   FastAPI Application                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              API Router (/api/v1)                         │ │
│  │  GET  /health                                           │ │
│  │  GET  /meters           ?page=1&page_size=25            │ │
│  │  GET  /meters/{id}                                  │ │
│  │  GET  /meters/{id}/consumption                           │ │
│  │  GET  /transformers                                     │ │
│  │  GET  /hierarchy                                        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                           │                                    │
│  ┌────────────────────────▼────────────────────────────────┐ │
│  │         Dependency Injection (get_portal_client)         │ │
│  │   Creates per-request UrjaPortalClient, closes after   │ │
│  └─────────────────────────────────────────────────────────┘ │
│                           │                                    │
│  ┌────────────────────────▼────────────────────────────────┐ │
│  │              UrjaPortalClient                             │ │
│  │  - Async httpx.AsyncClient with cookie jar              │ │
│  │  - login() → POST /login (form-encoded)                │ │
│  │  - _ensure_auth() → validates session, re-auths if     │ │
│  │    needed (single retry)                                │ │
│  │  - get_meters_html(page) → GET /meters?page={page}    │ │
│  │  - get_meter_detail_html(id) → GET /meters/{id}       │ │
│  │  - get_consumption_html(id) → GET /meters/{id}/       │ │
│  │    consumption                                          │ │
│  │  - get_transformers_html() → GET /transformers         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                           │                                    │
│  ┌────────────────────────▼────────────────────────────────┐ │
│  │              HTML Parsers (BeautifulSoup)                │ │
│  │  parse_meters_list()    → list[MeterBase]              │ │
│  │  parse_meter_detail()   → MeterDetail                  │ │
│  │  parse_consumption()    → list[ConsumptionReading]     │ │
│  │  parse_transformers()   → list[Transformer]            │ │
│  └─────────────────────────────────────────────────────────┘ │
│                           │                                    │
│  ┌────────────────────────▼────────────────────────────────┐ │
│  │              Pydantic Models                              │ │
│  │  MeterBase, MeterDetail, ConsumptionReading             │ │
│  │  Transformer, PaginatedMeters, MeterStatus (enum)       │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `PORTAL_BASE_URL` | No | `https://urja-ops.flockenergy.tech` | Base URL of the Urja Meter Ops portal |
| `PORTAL_USERNAME` | Yes | *(none)* | Portal login username |
| `PORTAL_PASSWORD` | Yes | *(none)* | Portal login password |
| `REQUEST_TIMEOUT` | No | `30` | HTTP request timeout in seconds |

## Setup

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and fill in PORTAL_USERNAME and PORTAL_PASSWORD
```

### Running

```bash
# Development server (auto-reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/meters` | Paginated meter list |
| `GET` | `/api/v1/meters/{meter_id}` | Meter detail |
| `GET` | `/api/v1/meters/{meter_id}/consumption` | Consumption readings |
| `GET` | `/api/v1/transformers` | Transformer list |
| `GET` | `/api/v1/hierarchy` | Transformer-to-meter hierarchy |

## OpenAPI Schema

The OpenAPI schema is available at `/openapi.json` when the server is running. You can also export it without starting the server:

```bash
python export_openapi.py --output openapi.json
```

## Assumptions and Trade-offs

### Assumptions

1. **Session cookie auth**: The portal uses standard HTTP session cookies. The client stores and sends cookies automatically via `httpx.AsyncClient`.
2. **HTML table structure**: The portal's HTML tables follow a consistent structure with `<table>`, `<tr>`, `<th>`, and `<td>` elements.
3. **Column header normalization**: Column headers are normalized to snake_case for matching. Multiple header variations are supported (e.g., `METER` and `meter_id` both map to `meter_id`).
4. **Single-table pages**: Each endpoint's HTML response contains the relevant data in the first `<table>` element.
5. **No JavaScript rendering**: The portal does not require JavaScript execution to render its data. All content is available in the initial HTML response.

### Trade-offs

1. **HTML parsing vs. HTML scraping**: The parsers use BeautifulSoup to extract structured data from HTML tables. This approach is fragile to DOM changes but avoids the complexity of a headless browser.
2. **Synchronous parsing**: HTML parsing is synchronous. For very large tables, this could block the event loop. The current implementation is suitable for moderate-sized tables typical of meter operations portals.
3. **Single retry on auth failure**: The client re-authenticates once on 401/403 responses. This is a simple strategy that avoids infinite retry loops but may not handle all session expiry scenarios.
4. **No caching**: Every request fetches fresh data from the portal. No caching layer is implemented, which ensures data freshness at the cost of portal load.
5. **Graceful degradation over strict validation**: Parser functions skip malformed rows and return partial results rather than failing entirely. This prioritizes availability over completeness.

## Project Structure

```
flock-energy-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Environment-based settings
│   ├── models.py            # Pydantic v2 data models
│   ├── client.py            # Async HTTP client (UrjaPortalClient)
│   ├── parser.py            # BeautifulSoup HTML parsers
│   ├── dependencies.py      # FastAPI dependency injection
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           └── router.py    # API v1 routes
├── tests/
│   ├── __init__.py
│   ├── test_client.py
│   ├── test_models.py
│   └── test_parser.py
├── .env.example
├── .gitignore
├── export_openapi.py
├── openapi.json
├── requirements.txt
├── README.md
├── PROTOCOL.md
└── REFLECTION.md
```

## Links

- [PROTOCOL.md](PROTOCOL.md) — Auth workflow, discovered endpoints, data structures, quirks
- [openapi.json](openapi.json) — OpenAPI schema (generated)
- [API Docs](http://localhost:8000/docs) — Interactive API documentation (when server is running)
