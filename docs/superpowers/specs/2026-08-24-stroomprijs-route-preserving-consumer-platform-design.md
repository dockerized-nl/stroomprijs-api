# Stroomprijs: Route-Preserving Consumer Platform Design

**Date:** 2026-08-24
**Task:** STROOM-REDESIGN-001
**Status:** Approved design direction; specification pending customer review
**Baseline:** `main` at `31b537f04fb7c0f89c1c8d940c538bab8788ba80`

## 1. Purpose

Modernize Stroomprijs from a prototype FastAPI application into a trustworthy, Dutch-first electricity decision product for two equally important audiences:

1. Households deciding when to consume electricity or charge appliances, vehicles, and batteries.
2. Solar-panel owners deciding when to export electricity, charge batteries, or favor self-consumption.

The modernization must preserve all current public HTML routes and JSON endpoints while creating a production-ready foundation for k3s.

## 2. Approved product decisions

- The public experience serves households and solar-panel owners equally.
- Dutch is the default public language.
- All current HTML routes and JSON endpoints remain available and compatible.
- The deployment target is production-ready k3s with probes, autoscaling, configuration/secret separation, security hardening, and rollback support.
- The approved architectural direction is a route-preserving split: frontend, FastAPI backend, scheduled ingest/normalization worker, and persistent normalized storage.

## 3. Existing evidence and problems

### Product and UX

- The homepage is an endpoint directory rather than a consumer landing page (`templates/index.html:32-47`).
- Branding emphasizes “API” (`main.py:8`, `README.md:1`) while the product also contains consumer flows (`main.py:187-361`).
- Pages duplicate inline CSS and lack a shared visual system (`templates/*.html`).
- Templates declare English while most consumer copy is Dutch.
- Status meaning depends heavily on red, yellow, and green.
- The chart is not paired with a complete accessible textual alternative.

### Data trust

- EnergyZero is called synchronously during client requests (`main.py:13-20`).
- Calls have no timeout, status validation, retry policy, schema validation, or controlled fallback.
- Hour conversion is manually repeated in several code paths.
- Live verification returned 25 price entries, creating a day-boundary/DST ambiguity.
- Buy/sell guidance does not expose source freshness or a degraded state.

### Testability and operations

- There are no repository tests or CI workflows.
- Business logic depends directly on wall-clock time and network calls.
- JSON endpoints do not have typed response models; OpenAPI exposes empty schemas.
- `/health` returns static HTML and cannot represent readiness.
- The image runs as root, has no image health check, and compose expects `curl` that is not installed.
- No Kubernetes or Helm packaging exists.
- Local virtual-environment and cache artifacts are tracked in Git.

## 4. Scope

### Included

- Dutch-first, responsive consumer UI with a shared visual system.
- Equal household-consumption and solar-export decision support.
- Stable existing routes and response compatibility.
- Normalized price ingestion and freshness-aware recommendations.
- Typed FastAPI contracts and deterministic business logic.
- Persistent last-known-good data.
- Proper health, readiness, and observability semantics.
- Automated unit, integration, contract, UI, container, security, and deployment checks.
- Helm-based production k3s packaging.

### Excluded from the first delivery

- User accounts, authentication, or saved personal preferences.
- Notifications, email, SMS, or mobile push alerts.
- Direct control of batteries, chargers, appliances, or smart-home devices.
- Tariff-provider account integrations.
- Financial guarantees or personalized investment advice.
- Multi-region or multi-cluster deployment.

These can be considered later without changing the route-preserving foundation.

## 5. Public information architecture

### `/` and `/index.html`

A consumer dashboard answering, above the fold:

- Is now a good time to consume or charge?
- Is now a good time to export electricity?
- What are today’s best and worst time windows?

It also shows source, date, Europe/Amsterdam timezone, VAT basis, and last successful refresh. API documentation becomes a secondary utility link rather than the primary journey.

### `/prices`

- Complete normalized hourly timeline.
- Price, start time, end time, and relative classification per slot.
- Responsive chart plus equivalent accessible table.
- Clear DST/day-boundary messaging where a day contains 23 or 25 local-hour slots.

### `/gemiddeld`

- Lowest, average, and highest price.
- Cheapest and most expensive windows.
- Practical explanations for consumption, battery charging, self-consumption, and export.
- All statistics derived from the same normalized dataset shown on `/prices`.

### `/kopen`

Household-oriented consumption/charging recommendation with:

- verdict and non-color iconography;
- short rationale;
- current price and rank;
- next better consumption window;
- freshness/degraded-state disclosure.

### `/verkopen`

Solar-oriented export recommendation with:

- verdict and non-color iconography;
- short rationale;
- current price and rank;
- next better export window;
- freshness/degraded-state disclosure.

### `/health`

Retained as a compatibility HTML page. It displays a user-friendly service status but is not used as the sole Kubernetes probe.

## 6. Compatibility contract

The following paths remain available:

### HTML

- `/`
- `/index.html`
- `/health`
- `/prices`
- `/gemiddeld`
- `/kopen`
- `/verkopen`

### JSON

- `/api/prices`
- `/api/kopen`
- `/api/verkopen`

Legacy JSON field names and basic shapes remain compatible. Corrections to time-slot handling must not silently remove fields. New metadata may be additive, including:

- `timezone`
- `source`
- `source_timestamp`
- `last_refresh`
- `freshness_status`

New typed endpoints may be introduced under `/api/v1/`, but they do not replace the legacy paths in this delivery.

A checked-in compatibility fixture and contract tests will capture the accepted legacy behavior before implementation changes.

## 7. Target architecture

### 7.1 Frontend

An SSR-capable Dutch-first web frontend serves the HTML route surface. The preferred implementation is Next.js because it provides shared components, server rendering, accessible routing, asset bundling, and a clear path to later internationalization.

Responsibilities:

- shared layout, design tokens, typography, navigation, and status components;
- consumer page rendering;
- accessible chart and table presentation;
- responsive behavior;
- controlled error, empty, loading, and stale-data states;
- server-side requests to the internal API;
- preservation of existing HTML paths.

The frontend does not calculate prices or recommendation policy independently.

### 7.2 FastAPI backend

FastAPI remains the source of API/domain behavior.

Responsibilities:

- existing JSON endpoints;
- optional `/api/v1/` typed endpoints;
- Pydantic request/response models;
- price-query and recommendation services;
- compatibility adapters for legacy responses;
- structured errors and logs;
- liveness, readiness, and metrics endpoints;
- datastore access.

The request path does not call EnergyZero directly.

### 7.3 Ingest/normalization worker

A scheduled worker fetches EnergyZero data independently of user traffic.

Responsibilities:

- bounded request timeout;
- status-code validation;
- bounded retries with backoff and jitter;
- upstream schema validation;
- UTC timestamp parsing;
- Europe/Amsterdam timezone conversion;
- correct 23-, 24-, and 25-slot local days;
- duplicate/missing-slot detection;
- recommendation-window calculation;
- atomic persistence of a new snapshot;
- preservation of last-known-good data on failure;
- metrics/logs for freshness and anomalies.

The initial k3s implementation uses a CronJob or an equivalent scheduled worker. The refresh cadence is configurable.

### 7.4 Persistent storage

PostgreSQL stores normalized price snapshots and derived recommendation metadata.

Minimum logical entities:

- price source snapshot;
- normalized price slot;
- recommendation set;
- ingest run/audit record.

Every served dataset has explicit source and freshness metadata. PostgreSQL is supplied externally or as a separately managed Helm release; it is not tightly embedded into the application chart.

## 8. Data flow

1. The scheduled worker requests the configured EnergyZero endpoint.
2. It validates the response and timestamps.
3. It normalizes slots into Europe/Amsterdam without manual `+1 hour` rules.
4. It validates slot count and uniqueness for the local date.
5. It calculates the six cheapest and six most expensive slots using deterministic tie behavior.
6. It writes the snapshot, slots, recommendations, and ingest audit atomically.
7. The API reads the newest acceptable snapshot from PostgreSQL.
8. The frontend renders API data and freshness status.
9. If ingestion fails, the last-known-good snapshot remains available until its configured maximum age.
10. Once data exceeds the maximum age, recommendation endpoints return a controlled degraded/unavailable result rather than authoritative guidance.

## 9. Recommendation policy

The first delivery preserves the current policy concept:

- “Kopen/verbruiken” is favorable during the six cheapest normalized slots.
- “Verkopen/terugleveren” is favorable during the six most expensive normalized slots.
- Other slots are neutral.

The UI explains this policy in plain Dutch. Tie handling is deterministic and covered by tests. If insufficient valid slots exist, the product does not manufacture a recommendation.

The product presents guidance, not a guarantee. Consumer copy must avoid implying guaranteed savings or financial returns.

## 10. Error and degraded-state behavior

### Upstream failures

- Timeouts, non-2xx responses, invalid JSON, invalid schemas, and incomplete data are captured as failed ingest runs.
- Raw stack traces or provider payloads are not exposed publicly.
- Last-known-good data may be served while it is inside the configured freshness window.
- The UI displays when the data was last refreshed and warns when it is stale.
- Recommendations become unavailable after the maximum freshness threshold.

### Datastore failures

- API readiness fails.
- User-facing requests return a controlled service-unavailable response.
- Liveness remains process-local so Kubernetes can distinguish an alive-but-unready pod.

### Frontend failures

- Each page has a Dutch error state and retry action.
- Core values have textual rendering independent of charts or JavaScript-enhanced visualization.

## 11. Accessibility and visual design requirements

- Document language is `nl` by default.
- WCAG 2.2 AA is the acceptance target for primary journeys.
- Status is represented by text, icon, and color together.
- Full keyboard navigation is supported.
- Focus states are visible.
- Chart information is available in a semantic table or equivalent textual summary.
- Reduced-motion preferences are respected.
- Mobile layout shows current consume/export decisions and best/worst windows without excessive scrolling.
- Shared design tokens prevent per-page inline-style divergence.
- Price formatting follows Dutch conventions while preserving API numeric values.

## 12. API and health semantics

### Typed API behavior

- Every JSON endpoint has a concrete Pydantic response model.
- OpenAPI contains schemas and representative examples.
- Compatibility tests protect current legacy fields.
- Errors use controlled, machine-readable responses.

### Health endpoints

- `/health`: compatibility HTML status page.
- `/health/live`: process-local JSON liveness.
- `/health/ready`: JSON readiness based on datastore connectivity and acceptable snapshot freshness; it does not call EnergyZero on every probe.
- `/metrics`: optional Prometheus-compatible metrics endpoint, restricted as appropriate by network policy or ingress routing.

## 13. k3s and Helm design

The repository will contain a versioned Helm chart with:

- frontend Deployment and ClusterIP Service;
- API Deployment and ClusterIP Service;
- ingest CronJob;
- Traefik-compatible Ingress;
- ConfigMap values;
- Secret references, not literal secret values;
- NetworkPolicy;
- HPA for frontend/API where metrics and load behavior support it;
- optional PodDisruptionBudget when replicas exceed one;
- ServiceAccounts with token automount disabled unless needed.

### Ingress

- Public traffic enters only through 80/443, with HTTP redirected to HTTPS.
- TLS is issued by cert-manager or a configured internal CA.
- Canonical host and HSTS are configured.
- `/api` routes to the API service; consumer routes route to the frontend.
- Rate limiting applies to public endpoints.
- `/docs`, `/redoc`, and `/openapi.json` are disabled or access-restricted in production according to configuration.

### Pod security

- non-root user;
- `allowPrivilegeEscalation: false`;
- all Linux capabilities dropped;
- `seccompProfile: RuntimeDefault`;
- read-only root filesystem where supported;
- explicit CPU/memory requests and limits;
- no unnecessary service-account token.

### Network policy

- default deny;
- ingress only from the intended ingress/controller paths;
- API access only from the frontend/ingress paths required by the selected routing model;
- egress only to DNS, PostgreSQL, telemetry endpoints when configured, and EnergyZero over TLS for the worker.

## 14. Configuration and secrets

ConfigMap/environment configuration includes:

- public domain;
- EnergyZero base URL;
- Europe/Amsterdam timezone;
- request timeout;
- retry policy;
- refresh cadence;
- cache/freshness thresholds;
- docs/OpenAPI enablement;
- logging level;
- feature flags.

Secrets include only secret material such as PostgreSQL credentials or future provider credentials. Production secrets are injected at runtime using k3s Secrets or a selected External Secrets, Sealed Secrets, or SOPS workflow. No `.env`, literal credentials, or secret-like placeholders are committed.

## 15. Observability

- JSON structured logs to stdout.
- Correlation/request IDs.
- Metrics for ingest success/failure, upstream latency, snapshot age, API latency, 5xx rates, readiness failures, and recommendation availability.
- Alerts for stale data, repeated ingest failure, high 5xx rate, and unavailable replicas.
- No sensitive values or full upstream payloads in logs.

## 16. Testing and CI gates

### Unit tests

- timestamp parsing and timezone conversion;
- 23-, 24-, and 25-slot days;
- duplicate/missing slots;
- negative and zero prices;
- deterministic ties;
- cheapest/most-expensive classification;
- buy, sell, and neutral outcomes;
- stale-data policy.

### Integration and contract tests

- EnergyZero timeout, non-2xx, invalid JSON, partial response, and recovery;
- atomic datastore writes;
- API success and controlled failure responses;
- legacy JSON compatibility fixtures;
- concrete OpenAPI schemas and examples;
- HTML routes returning the intended pages;
- consistency between UI and API values.

### UI tests

- Dutch copy and `lang="nl"`;
- responsive primary journeys;
- keyboard and focus behavior;
- non-color status meaning;
- chart/table equivalence;
- no-JavaScript or failed-chart graceful degradation;
- stale/upstream-unavailable states.

### Release gates

- formatting, lint, type, and syntax checks;
- full automated test suite;
- secret scan;
- dependency and container vulnerability scan with defined high/critical threshold;
- prohibition on tracked `venv`, caches, `.env`, and generated runtime artifacts;
- deterministic Docker image build;
- container smoke tests against liveness/readiness and one legacy API route;
- Helm lint/template checks and Kubernetes schema validation;
- policy checks for security context, ingress/TLS, resources, NetworkPolicy, and secret references;
- ephemeral k3s/k3d deployment smoke test;
- Tester approval;
- DevSecOps approval;
- Pentester approval before public exposure;
- human approval for production deployment.

## 17. Migration and rollout

1. Capture current route/API behavior with compatibility tests.
2. Introduce deterministic domain services and typed models behind existing routes.
3. Add normalized storage and worker ingestion.
4. Switch existing API paths to last-known-good normalized data.
5. Build the Dutch-first frontend and route existing HTML paths through it.
6. Add Helm packaging and deploy to an ephemeral k3s/k3d environment.
7. Run full quality/security/deployment gates.
8. Deploy to a non-production environment and validate real refresh/readiness behavior.
9. Promote only after Tester, DevSecOps, Pentester, and human approval.

Rollback uses immutable image/chart versions. A failed rollout returns to the last known-good frontend, API, worker, and chart release. Database changes must be backward-compatible for at least one deployed application version and include a tested rollback or forward-fix procedure.

## 18. Delivery slices

### P0 — trustworthy foundation

- repository cleanup;
- compatibility fixtures;
- normalized time-slot logic;
- typed API models;
- upstream timeout/error handling;
- persistent last-known-good snapshots;
- worker separation;
- real liveness/readiness;
- deterministic tests and CI baseline.

### P1 — Dutch consumer experience

- shared design system;
- new consumer dashboard;
- household and solar recommendations;
- accessible charts/tables;
- responsive route-preserving pages;
- trust/freshness/tax/source messaging;
- controlled loading/error/stale states.

### P2 — production k3s

- hardened container images;
- Helm chart;
- Traefik ingress/TLS;
- HPA, resources, NetworkPolicy, and optional PDB;
- observability and alerts;
- k3d/k3s deployment verification;
- rollout and rollback documentation.

## 19. Acceptance criteria

The design is implemented only when evidence shows:

1. All existing HTML and JSON paths remain available.
2. Legacy JSON response compatibility is protected by automated contract tests.
3. A Dutch first-time user can identify current consumption and export recommendations plus today’s best/worst windows within five seconds.
4. The UI shows source, date, timezone, VAT basis, and last refresh.
5. Time slots are correct and explicitly tested for 23-, 24-, and 25-slot local days.
6. No recommendation is issued from invalid or excessively stale data.
7. Core decisions do not rely on color or chart reading alone.
8. JSON endpoints have typed OpenAPI contracts.
9. Public requests do not trigger unbounded EnergyZero calls.
10. Kubernetes readiness reflects datastore/freshness policy rather than a static page.
11. Frontend and API images run as non-root with required pod hardening.
12. Helm/k3s validation, test, scan, smoke, and review gates pass.
13. Rollback is documented and tested in a non-production environment.
14. Tester, DevSecOps, Pentester, and Jesse approve before public production rollout.

## 20. Risks and mitigations

- **Scope expansion:** keep accounts, notifications, and device control out of the first delivery.
- **Compatibility ambiguity:** capture baseline responses and route behavior before refactoring.
- **DST/time errors:** centralize normalization and test real Dutch DST transition dates.
- **Upstream instability:** scheduled bounded ingest plus last-known-good storage and explicit freshness policy.
- **Frontend/backend divergence:** frontend consumes typed API contracts; calculations live only in domain services.
- **Operational complexity:** deliver in P0/P1/P2 slices and validate in ephemeral k3s before production.
- **Database overhead:** use a minimal schema and externally managed PostgreSQL; avoid premature event architecture.
- **Security drift:** enforce container, manifest, dependency, and secret gates in CI.

## 21. Approval boundary

This specification authorizes implementation planning only after Jesse reviews and approves the written document. It does not authorize production deployment, billable infrastructure changes, secret creation, or destructive operations. Those actions require separate human approval at their respective gates.
