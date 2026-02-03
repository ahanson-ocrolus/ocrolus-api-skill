# Ocrolus Automations

Production-grade Python framework for Ocrolus API automations. Each automation is a self-contained module runnable from the CLI. Shared logic (auth, retries, streaming) lives in a common client and utilities.

## Features

- **CLI**: Typer-based `move-book` and `list-automations`; run via `python3 -m ocrolus_automations` or `ocrolus-auto`
- **Config**: pydantic-settings with `.env` and env vars; multiple org credential sets (`OCROLUS_ORGS__ORG1__CLIENT_ID`, etc.)
- **Ocrolus client**: Token caching per org, book status/create, document download (streaming) and upload (multipart)
- **Retries**: Tenacity with exponential backoff for 429, 5xx, timeouts
- **Streaming**: Download → spooled in-memory/temp buffer → upload; no PDFs persisted to disk
- **Logging**: Console + optional file, structured format, secret redaction
- **Dry-run**: `--dry-run` prints what would happen without creating books or uploading

## Setup

### 1. Create a virtual environment (Python 3.11+)

```bash
cd ocrolus_automations
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Install the package (editable, with dev deps for tests)

```bash
pip install -e ".[dev]"
```

### 3. Configure environment

Copy `.env.example` to `.env` and set values (never commit `.env`):

```bash
cp .env.example .env
# Edit .env: set OCROLUS_ORGS__ORG1__CLIENT_ID, OCROLUS_ORGS__ORG1__CLIENT_SECRET, etc.
```

**Secrets**: Use environment variables or a local `.env` file. Do not hardcode credentials. Add `.env` to `.gitignore` (already there in the repo root).

### 4. Run an example

```bash
# List automations
ocrolus-auto list-automations

# Dry-run move book (no create/upload)
python -m ocrolus_automations move-book \
  --source-book-uuid <your-source-book-uuid> \
  --target-book-name "Copy of My Book" \
  --org-source org1 \
  --org-target org2 \
  --dry-run

# Actual run (optional: limit docs)
python -m ocrolus_automations move-book \
  --source-book-uuid <uuid> \
  --target-book-name "Copy of My Book" \
  --max-docs 5
```

## Example commands

| Command | Description |
|--------|-------------|
| `ocrolus-auto list-automations` | Show available automations and usage |
| `ocrolus-auto move-book --source-book-uuid X --target-book-name "Y"` | Copy book from source org to new book in target org |
| `ocrolus-auto move-book ... --dry-run` | Print actions without creating book or uploading |
| `ocrolus-auto move-book ... --max-docs 10` | Transfer at most 10 documents |

## Configuration

- **Org credentials**: `OCROLUS_ORGS__<ORG>__CLIENT_ID` and `OCROLUS_ORGS__<ORG>__CLIENT_SECRET`. Org names are lowercased (e.g. `ORG1` → `org1`).
- **API base**: `OCROLUS_API_BASE` (default `https://api.ocrolus.com`), `OCROLUS_AUTH_BASE` (default `https://auth.ocrolus.com`).
- **Logging**: `LOG_LEVEL=INFO`, `LOG_FILE=logs/ocrolus_automations.log`.

## Adding a new automation

1. **Create a module** under `src/ocrolus_automations/automations/`, e.g. `my_automation.py`.
2. **Implement a run function** (e.g. `run_my_automation(...)`) that uses `OcrolusClient` and returns an exit code (0 = success).
3. **Register a CLI command** in `src/ocrolus_automations/cli.py`: add a Typer command that calls your run function and `raise typer.Exit(exit_code)`.
4. **Export** the run function from `automations/__init__.py` if desired.

The Ocrolus client and HTTP/streaming utilities are shared; automations stay self-contained and call into the client.

## Tests

```bash
pytest
# With coverage
pytest --cov=ocrolus_automations --cov-report=term-missing
```

## API assumptions (customization)

Request/response shapes are centralized so you can adjust once:

- **Auth**: `POST {auth_base}/oauth/token` with `client_id`, `client_secret`, `grant_type=client_credentials`; response `access_token` (and optional `expires_in`).
- **Book status**: `GET {api_base}/v1/book/status?book_uuid=...`; doc list is read from configurable keys (see next steps below).
- **Book add**: `POST {api_base}/v1/book/add` with JSON body including `name`; response must expose a book UUID (e.g. `book_uuid` or `uuid`).
- **Document download**: `GET {api_base}/v2/document/download?doc_uuid=...` returns raw bytes (streaming).
- **Book upload**: `POST {api_base}/v1/book/upload` multipart with `book_uuid` and file field (e.g. `file`).

---

## Next steps: plugging in your API shapes

1. **Book status doc list**  
   Run `GET /v1/book/status` for a real book and paste the JSON (redact any secrets). Then:
   - In `automations/move_book.py`, `extract_docs_from_status()` tries keys `documents`, `docs`, `document_list` by default. If your response uses a different key (e.g. `book.documents`), either:
     - Add that key to `DEFAULT_DOCS_PATH_KEYS` in `move_book.py`, or  
     - Pass `doc_list_paths=["your_key"]` (and optional `doc_uuid_key` / `doc_name_key`) when calling `run_move_book` or via a small config layer.
   - The code logs top-level keys once when extraction fails (`Book status top-level keys: [...]`); use that to pick the right path.

2. **Auth and other endpoints**  
   If your auth URL, body, or response fields differ, edit `clients/ocrolus_client.py`: `_fetch_token()` and the response parsing. If create-book or upload use different URLs or field names, update `create_book()` and `upload_document()` in the same file. All assumptions are documented in that module’s docstring.

3. **Optional: config-driven paths**  
   You can add settings (e.g. `book_status_docs_key`, `doc_uuid_key`) in `config.py` and pass them into `run_move_book` so you don’t change code when the API shape changes.
