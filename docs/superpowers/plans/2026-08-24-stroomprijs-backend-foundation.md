# Stroomprijs Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, typed FastAPI backend that ingests and normalizes EnergyZero data, preserves legacy JSON contracts, stores last-known-good snapshots, and exposes honest health semantics.

**Architecture:** Extract pricing logic from `main.py` into focused domain, provider, persistence, and API modules. A scheduled worker writes validated Europe/Amsterdam snapshots to PostgreSQL; request handlers read stored data and never call EnergyZero directly.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, PostgreSQL, Alembic, HTTPX, pytest, pytest-asyncio, Ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-08-24-stroomprijs-route-preserving-consumer-platform-design.md`

## Global Constraints

- Preserve `/api/prices`, `/api/kopen`, `/api/verkopen`, and all legacy response fields.
- Preserve `/`, `/index.html`, `/health`, `/prices`, `/gemiddeld`, `/kopen`, and `/verkopen` until the frontend plan replaces their rendering.
- Default timezone is exactly `Europe/Amsterdam`.
- Recommendations use the six cheapest and six most expensive valid normalized slots.
- No recommendation is emitted from invalid data or data older than `MAX_DATA_AGE_SECONDS`.
- No public request performs an EnergyZero network call.
- Runtime configuration comes from environment variables; secret values are never committed.
- Tests must cover 23-, 24-, and 25-slot local days.
- Use clearly non-secret test values such as `postgresql+asyncpg://app:local-dev-only-not-a-secret@localhost/stroomprijs`.
- Every task follows RED → GREEN → REFACTOR and ends with a focused commit.

## File structure

- `pyproject.toml` — Python dependencies and lint/type/test configuration.
- `.gitignore` — generated/local artifact exclusions.
- `backend/app/config.py` — environment-backed settings.
- `backend/app/domain/models.py` — immutable domain values.
- `backend/app/domain/normalization.py` — UTC-to-local slot normalization and validation.
- `backend/app/domain/recommendations.py` — deterministic buy/sell policy.
- `backend/app/providers/energyzero.py` — bounded upstream client and schema validation.
- `backend/app/db.py` — async engine/session lifecycle.
- `backend/app/persistence/models.py` — SQLAlchemy storage models.
- `backend/app/persistence/snapshots.py` — atomic snapshot repository.
- `backend/app/services/ingest.py` — provider → normalization → recommendations → persistence orchestration.
- `backend/app/api/schemas.py` — typed API response models.
- `backend/app/api/legacy.py` — legacy compatibility adapters.
- `backend/app/api/routes.py` — API and health routes.
- `backend/app/main.py` — FastAPI composition root.
- `backend/app/worker.py` — one-shot scheduled ingest entrypoint.
- `backend/alembic/` — database migrations.
- `tests/` — unit, integration, contract, and health tests.

---

### Task 1: Reproducible Python baseline and repository hygiene

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `tests/test_repository_hygiene.py`
- Modify: `requirements.txt`
- Delete from Git: `venv/`, `__pycache__/`

**Interfaces:**
- Produces: `pytest`, `ruff`, and `mypy` commands used by every later task.

- [ ] **Step 1: Write the failing hygiene test**

```python
# tests/test_repository_hygiene.py
from pathlib import Path
import subprocess

FORBIDDEN_PARTS = {"venv", "__pycache__", ".env"}


def test_generated_and_secret_files_are_not_tracked() -> None:
    tracked = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
    offenders = [p for p in tracked if FORBIDDEN_PARTS.intersection(Path(p).parts)]
    assert offenders == []
```

- [ ] **Step 2: Run the test and verify the current repo fails**

Run: `python3 -m pytest tests/test_repository_hygiene.py -v`
Expected: FAIL because pytest is unavailable or tracked `venv`/`__pycache__` paths are reported.

- [ ] **Step 3: Add tooling and cleanup rules**

Create `pyproject.toml` with runtime dependencies `fastapi`, `uvicorn`, `pydantic-settings`, `httpx`, `sqlalchemy`, `asyncpg`, `alembic`, and dev dependencies `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`. Configure Python `>=3.11`, Ruff line length 100, strict mypy for `backend/app`, and pytest paths `tests`.

Create `.gitignore` containing:

```gitignore
.venv/
venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.env
.env.*
!.env.example
node_modules/
.next/
coverage/
playwright-report/
```

Remove tracked generated files with `git rm -r --cached venv __pycache__` and replace `requirements.txt` with a compatibility export note pointing contributors to `pyproject.toml`.

- [ ] **Step 4: Verify the baseline**

Run:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest tests/test_repository_hygiene.py -v
.venv/bin/ruff check backend tests
.venv/bin/mypy backend/app
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```bash
git add .gitignore pyproject.toml requirements.txt backend/app/__init__.py tests/test_repository_hygiene.py
git add -u venv __pycache__
git commit -m "chore: establish reproducible python baseline"
```

---

### Task 2: Centralized configuration and domain models

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/domain/__init__.py`
- Create: `backend/app/domain/models.py`
- Create: `tests/domain/test_models.py`

**Interfaces:**
- Produces: `Settings`, `PriceSlot`, `PriceSnapshot`, `Recommendation`, `RecommendationState`, and `FreshnessStatus`.

- [ ] **Step 1: Write failing configuration/domain tests**

```python
from datetime import UTC, datetime
from decimal import Decimal
from backend.app.config import Settings
from backend.app.domain.models import PriceSlot


def test_settings_default_to_amsterdam_and_closed_docs() -> None:
    settings = Settings(database_url="postgresql+asyncpg://app:local-dev-only-not-a-secret@db/app")
    assert settings.timezone == "Europe/Amsterdam"
    assert settings.docs_enabled is False
    assert settings.request_timeout_seconds == 5.0


def test_price_slot_requires_increasing_boundaries() -> None:
    start = datetime(2026, 8, 24, 10, tzinfo=UTC)
    slot = PriceSlot(start_utc=start, end_utc=start.replace(hour=11), price_eur_kwh=Decimal("0.12"))
    assert slot.duration_seconds == 3600
```

- [ ] **Step 2: Run and verify failure**

Run: `.venv/bin/pytest tests/domain/test_models.py -v`
Expected: FAIL because modules do not exist.

- [ ] **Step 3: Implement exact settings and immutable models**

`Settings` must expose: `database_url`, `energyzero_base_url`, `timezone`, `request_timeout_seconds`, `request_retries`, `refresh_cron`, `max_data_age_seconds`, `docs_enabled`, and `log_level`. Use `BaseSettings` with prefix `STROOMPRIJS_`.

Use frozen Pydantic models. `PriceSlot` validates timezone-aware UTC boundaries and `end_utc > start_utc`. `PriceSnapshot` contains `source`, `source_timestamp`, `local_date`, `timezone`, `average_eur_kwh`, and `slots`. Recommendation enums use exact wire values `OK`, `NOT OK`, and `neutraal` for compatibility.

- [ ] **Step 4: Run tests and static checks**

Run:

```bash
.venv/bin/pytest tests/domain/test_models.py -v
.venv/bin/ruff check backend/app/config.py backend/app/domain tests/domain
.venv/bin/mypy backend/app/config.py backend/app/domain
```

Expected: all exit 0.

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/app/domain tests/domain/test_models.py
git commit -m "feat: add typed configuration and pricing models"
```

---

### Task 3: DST-safe normalization

**Files:**
- Create: `backend/app/domain/normalization.py`
- Create: `tests/domain/test_normalization.py`

**Interfaces:**
- Consumes: `PriceSlot`, `PriceSnapshot`.
- Produces: `normalize_energyzero_prices(payload: dict, local_date: date, timezone: str) -> PriceSnapshot`.

- [ ] **Step 1: Write failing table-driven tests**

Create fixtures with UTC timestamps for normal date `2026-08-24`, spring transition `2026-03-29`, and fall transition `2026-10-25`. Assert 24, 23, and 25 unique `(start_utc, end_utc)` slots respectively; assert local labels preserve both repeated fall-back hours through distinct UTC offsets. Add tests rejecting duplicate UTC timestamps, missing required fields, naive timestamps, and mismatched local dates.

```python
@pytest.mark.parametrize(("local_date", "expected_count"), [
    (date(2026, 8, 24), 24),
    (date(2026, 3, 29), 23),
    (date(2026, 10, 25), 25),
])
def test_normalizes_valid_local_day(payload_factory, local_date, expected_count):
    snapshot = normalize_energyzero_prices(
        payload_factory(local_date), local_date, "Europe/Amsterdam"
    )
    assert len(snapshot.slots) == expected_count
    assert len({slot.start_utc for slot in snapshot.slots}) == expected_count
```

- [ ] **Step 2: Run and verify failure**

Run: `.venv/bin/pytest tests/domain/test_normalization.py -v`
Expected: FAIL because normalization is undefined.

- [ ] **Step 3: Implement normalization without manual hour shifting**

Parse every `readingDate` as UTC, sort by UTC instant, derive each one-hour end boundary, convert only for local-date membership using `zoneinfo.ZoneInfo`, reject duplicates/incomplete records, and compute the average from accepted slots using `Decimal`. Do not add a fixed hour offset.

- [ ] **Step 4: Verify all transition tests pass**

Run: `.venv/bin/pytest tests/domain/test_normalization.py -v`
Expected: 23/24/25-slot cases and invalid-input cases all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/normalization.py tests/domain/test_normalization.py
git commit -m "feat: normalize electricity slots across DST"
```

---

### Task 4: Deterministic recommendation policy

**Files:**
- Create: `backend/app/domain/recommendations.py`
- Create: `tests/domain/test_recommendations.py`

**Interfaces:**
- Consumes: `PriceSnapshot`, an injected `now: datetime`.
- Produces: `build_recommendations(snapshot, now) -> tuple[Recommendation, Recommendation]`.

- [ ] **Step 1: Write failing policy tests**

Cover cheapest, most expensive, neutral, tied values, negative prices, repeated fall-back local hours, insufficient slots, and stale snapshots. Require tie ordering by `(price, start_utc)` and exactly six selected slots when at least twelve valid slots exist.

```python
def test_current_cheapest_slot_means_buy_ok_and_sell_not_ok(snapshot_factory):
    snapshot = snapshot_factory(prices=range(24))
    now = snapshot.slots[0].start_utc
    buy, sell = build_recommendations(snapshot, now)
    assert buy.status.value == "OK"
    assert sell.status.value == "NOT OK"
```

- [ ] **Step 2: Run and verify failure**

Run: `.venv/bin/pytest tests/domain/test_recommendations.py -v`
Expected: FAIL because policy is undefined.

- [ ] **Step 3: Implement the minimal pure policy**

Sort low windows by `(price, start_utc)` and high windows by `(-price, start_utc)`. Match the injected UTC instant against slot boundaries. Return Dutch explanations, current slot rank, and next favorable slot. Raise `RecommendationUnavailable` for invalid or insufficient snapshots; freshness policy is enforced by the service layer.

- [ ] **Step 4: Run and verify**

Run: `.venv/bin/pytest tests/domain/test_recommendations.py -v`
Expected: all branches PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/recommendations.py tests/domain/test_recommendations.py
git commit -m "feat: add deterministic consume and export guidance"
```

---

### Task 5: Bounded EnergyZero provider client

**Files:**
- Create: `backend/app/providers/__init__.py`
- Create: `backend/app/providers/energyzero.py`
- Create: `tests/providers/test_energyzero.py`

**Interfaces:**
- Produces: `EnergyZeroClient.fetch_prices(local_date: date) -> dict` and typed exceptions `UpstreamTimeout`, `UpstreamRejected`, `UpstreamInvalidPayload`.

- [ ] **Step 1: Write failing HTTPX MockTransport tests**

Test exact query boundaries, `inclBtw=true`, timeout mapping, non-2xx mapping, invalid JSON, and bounded retry count. Assert exceptions never include raw response bodies.

- [ ] **Step 2: Run and verify failure**

Run: `.venv/bin/pytest tests/providers/test_energyzero.py -v`
Expected: FAIL because client is undefined.

- [ ] **Step 3: Implement async client**

Inject `httpx.AsyncClient`, settings, and sleeper. Use configured timeout and at most `request_retries + 1` attempts for timeout/5xx only. Call `raise_for_status()`, parse JSON, verify `Prices` is a list and `average` is numeric, then return the payload.

- [ ] **Step 4: Verify provider behavior**

Run: `.venv/bin/pytest tests/providers/test_energyzero.py -v`
Expected: all success and failure cases PASS with exact attempt counts.

- [ ] **Step 5: Commit**

```bash
git add backend/app/providers tests/providers/test_energyzero.py
git commit -m "feat: add bounded EnergyZero client"
```

---

### Task 6: PostgreSQL snapshot persistence and migration

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/persistence/__init__.py`
- Create: `backend/app/persistence/models.py`
- Create: `backend/app/persistence/snapshots.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_price_snapshots.py`
- Create: `tests/persistence/test_snapshots.py`

**Interfaces:**
- Produces: `SnapshotRepository.save(snapshot, recommendations, ingest_record) -> UUID`, `latest_acceptable(now, max_age) -> StoredSnapshot | None`, and `latest_ingest_status() -> IngestStatus`.

- [ ] **Step 1: Write failing repository integration tests**

Against an ephemeral PostgreSQL database, test atomic insert, rollback on duplicate slot, newest-snapshot selection, max-age rejection, and preservation of prior snapshot after a failed transaction.

- [ ] **Step 2: Run and verify failure**

Run: `.venv/bin/pytest tests/persistence/test_snapshots.py -v`
Expected: FAIL because database models/repository do not exist.

- [ ] **Step 3: Implement schema and repository**

Create tables `price_snapshots`, `price_slots`, `recommendations`, and `ingest_runs`. Enforce uniqueness on `(snapshot_id, start_utc)` and indexes for `local_date`/`created_at`. Store prices as `NUMERIC`, timestamps as timezone-aware columns, and snapshot writes in one transaction.

- [ ] **Step 4: Verify migration and integration tests**

Run:

```bash
.venv/bin/alembic -c backend/alembic.ini upgrade head
.venv/bin/pytest tests/persistence/test_snapshots.py -v
```

Expected: migration and tests exit 0.

- [ ] **Step 5: Commit**

```bash
git add backend/app/db.py backend/app/persistence backend/alembic.ini backend/alembic tests/persistence
git commit -m "feat: persist normalized price snapshots"
```

---

### Task 7: One-shot ingest service and worker

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/ingest.py`
- Create: `backend/app/worker.py`
- Create: `tests/services/test_ingest.py`

**Interfaces:**
- Consumes: `EnergyZeroClient`, `normalize_energyzero_prices`, `build_recommendations`, `SnapshotRepository`.
- Produces: `IngestService.run(local_date: date, now: datetime) -> IngestResult` and executable `python -m backend.app.worker`.

- [ ] **Step 1: Write failing orchestration tests**

Test success persistence, invalid payload rejection, provider timeout audit, atomic failure, and last-known-good preservation. Assert one provider call and one repository transaction per run.

- [ ] **Step 2: Run and verify failure**

Run: `.venv/bin/pytest tests/services/test_ingest.py -v`
Expected: FAIL because service is undefined.

- [ ] **Step 3: Implement orchestration and exit codes**

`run()` records start/end/status, normalizes and derives recommendations, then persists atomically. Worker builds dependencies from `Settings`, returns exit 0 on success and non-zero on failed ingest, and logs structured fields without provider payloads or credentials.

- [ ] **Step 4: Verify service and CLI**

Run:

```bash
.venv/bin/pytest tests/services/test_ingest.py -v
STROOMPRIJS_DATABASE_URL='postgresql+asyncpg://app:local-dev-only-not-a-secret@localhost/stroomprijs' .venv/bin/python -m backend.app.worker
```

Expected: tests PASS; CLI exits according to the test database/provider fixture environment used in CI.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services backend/app/worker.py tests/services/test_ingest.py
git commit -m "feat: add scheduled price ingest worker"
```

---

### Task 8: Typed API, legacy compatibility, and honest health

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/schemas.py`
- Create: `backend/app/api/legacy.py`
- Create: `backend/app/api/routes.py`
- Create: `backend/app/main.py`
- Create: `tests/api/test_legacy_contract.py`
- Create: `tests/api/test_health.py`
- Create: `tests/api/fixtures/legacy_prices.json`
- Modify: `main.py`

**Interfaces:**
- Produces: FastAPI `app`, legacy routes, `/api/v1/prices/today`, `/api/v1/recommendations/consume`, `/api/v1/recommendations/export`, `/health/live`, and `/health/ready`.

- [ ] **Step 1: Capture and write failing contract tests**

Record sanitized baseline field shapes for all three legacy endpoints. Tests assert the legacy keys `text`, `average`, `labels`, `values`, `prices`, `status`, `action`, `message`, `current_hour`, and `current_time` remain present as applicable. Add tests that OpenAPI has concrete schemas, liveness is process-local, readiness fails without DB/fresh data, and readiness does not invoke EnergyZero.

- [ ] **Step 2: Run and verify failure**

Run: `.venv/bin/pytest tests/api/test_legacy_contract.py tests/api/test_health.py -v`
Expected: FAIL because new app/routes are undefined.

- [ ] **Step 3: Implement typed routes and compatibility adapters**

Build Pydantic schemas with additive freshness metadata. Legacy adapters map stored normalized slots back to old fields without manual hour shifting. `backend/app/main.py` configures docs URLs only when `docs_enabled` is true. Root `main.py` temporarily re-exports `app` from `backend.app.main` so existing `uvicorn main:app` remains valid.

- [ ] **Step 4: Verify API, OpenAPI, and health**

Run:

```bash
.venv/bin/pytest tests/api -v
.venv/bin/python -m py_compile main.py backend/app/main.py
```

Expected: all tests pass; generated OpenAPI includes non-empty schemas for JSON endpoints.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api backend/app/main.py main.py tests/api
git commit -m "feat: serve typed and compatible electricity APIs"
```

---

### Task 9: Backend CI quality and security gates

**Files:**
- Create: `.github/workflows/backend-ci.yml`
- Create: `scripts/check-repo-hygiene.py`
- Create: `tests/test_openapi_contract.py`
- Modify: `README.md`

**Interfaces:**
- Produces: required backend CI jobs `quality`, `test`, `contract`, `secret-scan`, and `dependency-scan`.

- [ ] **Step 1: Write failing gate tests**

Add a test loading `backend.app.main.app.openapi()` and asserting schemas for every legacy and v1 JSON endpoint. Extend the hygiene script to reject tracked virtual environments, caches, `.env` files, and high-risk credential filenames.

- [ ] **Step 2: Run and verify failure before workflow/config exists**

Run: `.venv/bin/pytest tests/test_openapi_contract.py tests/test_repository_hygiene.py -v`
Expected: contract test fails until every schema is attached.

- [ ] **Step 3: Add CI workflow**

Workflow must install from `pyproject.toml`, start PostgreSQL as a service, run Ruff, mypy, all pytest suites, OpenAPI contract checks, Gitleaks, and `pip-audit`. Do not use secret-like CI placeholders; use `local-dev-only-not-a-secret`.

- [ ] **Step 4: Run the complete backend gate locally**

Run:

```bash
.venv/bin/ruff check backend tests scripts
.venv/bin/mypy backend/app
.venv/bin/pytest -q
.venv/bin/pip-audit
python3 scripts/check-repo-hygiene.py
```

Expected: every command exits 0.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/backend-ci.yml scripts/check-repo-hygiene.py tests/test_openapi_contract.py README.md
git commit -m "ci: enforce backend quality and compatibility"
```

## Plan exit criteria

- Legacy JSON contracts are covered and passing.
- All public data reads come from normalized stored snapshots.
- 23/24/25-slot behavior is deterministic and tested.
- Upstream failures cannot block public request workers.
- `/health/live` and `/health/ready` have distinct verified semantics.
- OpenAPI schemas are concrete.
- Backend CI and security gates pass from a clean checkout.
