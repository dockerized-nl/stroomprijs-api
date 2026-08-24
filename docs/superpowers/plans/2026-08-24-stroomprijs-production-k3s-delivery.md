# Stroomprijs Production k3s Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package, secure, validate, and document the approved frontend/API/worker architecture for production-grade k3s without performing a production deployment.

**Architecture:** Build separate immutable non-root frontend and backend images, deploy them through a versioned Helm chart, run ingestion as a CronJob, and expose only Traefik ingress routes. CI validates security policy, manifests, images, compatibility, and an ephemeral k3d deployment before any human-approved release.

**Tech Stack:** Docker BuildKit/buildx, Helm 3, k3s/k3d, Traefik, cert-manager integration, Kubernetes NetworkPolicy/HPA/PDB, Trivy, Gitleaks, Syft/Grype or equivalent SBOM scan, GitHub Actions, GHCR.

**Spec:** `docs/superpowers/specs/2026-08-24-stroomprijs-route-preserving-consumer-platform-design.md`

## Global Constraints

- This plan does not authorize a production deployment or billable infrastructure change.
- Images run as non-root, drop all capabilities, deny privilege escalation, and use read-only root filesystems where supported.
- Public traffic enters only through HTTPS ingress; direct NodePort/host-port publication is prohibited.
- `/docs`, `/redoc`, and `/openapi.json` are disabled by default in production values.
- ConfigMap holds non-secret runtime configuration; Secret references hold only secret material.
- No literal credentials or secret-like placeholders are committed.
- NetworkPolicy is default-deny with explicit ingress/egress allowances.
- Existing public HTML and JSON paths remain reachable through ingress.
- Every task ends with a focused commit and verified rollback impact.

## File structure

- `backend/Dockerfile` — hardened backend/worker image.
- `frontend/Dockerfile` — hardened Next.js standalone image.
- `docker-compose.dev.yml` — local integration without production credentials.
- `charts/stroomprijs/` — application Helm chart.
- `charts/stroomprijs/templates/` — workloads, services, ingress, policy, autoscaling, and tests.
- `charts/stroomprijs/values.yaml` — safe defaults.
- `charts/stroomprijs/values-production.example.yaml` — production shape without secrets.
- `scripts/k3d-smoke.sh` — ephemeral cluster verification.
- `docs/operations/` — runbook and rollback documentation.
- `.github/workflows/container-ci.yml` — image build/scan/SBOM gates.
- `.github/workflows/k3s-ci.yml` — Helm/policy/k3d gates.
- `.github/workflows/release.yml` — approval-gated GHCR release workflow.

---

### Task 1: Hardened deterministic container images

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `backend/.dockerignore`
- Create: `frontend/.dockerignore`
- Create: `tests/container/test_images.py`
- Replace: root `Dockerfile` with compatibility documentation or backend forwarding build.

**Interfaces:**
- Produces: images `stroomprijs-api:<sha>` and `stroomprijs-web:<sha>` with OCI health metadata and non-root users.

- [ ] **Step 1: Write failing image-policy tests**

```python
@pytest.mark.parametrize("image", ["stroomprijs-api:test", "stroomprijs-web:test"])
def test_image_runs_non_root(image, docker_inspect):
    config = docker_inspect(image)
    assert config["Config"]["User"] not in ("", "0", "root")
    assert config["Config"]["Healthcheck"] is not None
```

Also assert no shell package manager cache, source `.env`, `venv`, `node_modules`, or development dependencies exist in final stages.

- [ ] **Step 2: Build current images and verify tests fail**

Run:

```bash
docker build -t stroomprijs-api:test -f backend/Dockerfile .
docker build -t stroomprijs-web:test -f frontend/Dockerfile .
python3 -m pytest tests/container/test_images.py -v
```

Expected: initial FAIL until Dockerfiles are hardened.

- [ ] **Step 3: Implement multi-stage images**

Backend final stage uses a pinned Python 3.11 slim digest, copies only installed runtime dependencies and `backend`, creates UID/GID 10001, sets `USER 10001:10001`, and defines a Python-based health check against `/health/live` without requiring curl. Frontend uses Next standalone output, pinned Node LTS digest, UID/GID 10001, and a Node-based local health check. Both set OCI source/revision labels and use exec-form commands.

- [ ] **Step 4: Verify runtime and scan prerequisites**

Run:

```bash
docker build --build-arg VCS_REF=$(git rev-parse HEAD) -t stroomprijs-api:test -f backend/Dockerfile .
docker build --build-arg VCS_REF=$(git rev-parse HEAD) -t stroomprijs-web:test -f frontend/Dockerfile .
python3 -m pytest tests/container/test_images.py -v
docker run --rm stroomprijs-api:test id
docker run --rm stroomprijs-web:test id
```

Expected: tests pass and both `id` outputs show UID 10001.

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile frontend/Dockerfile backend/.dockerignore frontend/.dockerignore Dockerfile tests/container/test_images.py
git commit -m "build: harden application containers"
```

---

### Task 2: Helm chart baseline and route-preserving ingress

**Files:**
- Create: `charts/stroomprijs/Chart.yaml`
- Create: `charts/stroomprijs/values.yaml`
- Create: `charts/stroomprijs/templates/_helpers.tpl`
- Create: `charts/stroomprijs/templates/frontend-deployment.yaml`
- Create: `charts/stroomprijs/templates/frontend-service.yaml`
- Create: `charts/stroomprijs/templates/api-deployment.yaml`
- Create: `charts/stroomprijs/templates/api-service.yaml`
- Create: `charts/stroomprijs/templates/ingest-cronjob.yaml`
- Create: `charts/stroomprijs/templates/ingress.yaml`
- Create: `charts/stroomprijs/templates/tests/route-test.yaml`
- Create: `tests/helm/test_rendered_routes.py`

**Interfaces:**
- Produces: chart `stroomprijs` with frontend, API, worker, services, and Traefik-compatible ingress.

- [ ] **Step 1: Write failing rendered-manifest tests**

Render chart and assert: frontend/API are `ClusterIP`; ingress routes `/api`, `/health/live`, `/health/ready` to API and all consumer HTML paths to frontend; CronJob uses backend image with `python -m backend.app.worker`; no NodePort/LoadBalancer services exist.

- [ ] **Step 2: Run and verify failure**

Run: `python3 -m pytest tests/helm/test_rendered_routes.py -v`
Expected: FAIL because chart does not exist.

- [ ] **Step 3: Implement chart baseline**

Values require explicit image repositories/tags, public host, ingress class `traefik`, and PostgreSQL Secret reference. Use named ports, checksums for config rollout, selectors from helpers, and immutable image tags. Ingress path precedence must prevent frontend from capturing `/api` and machine health paths.

- [ ] **Step 4: Verify Helm output**

Run:

```bash
helm lint charts/stroomprijs
helm template stroomprijs charts/stroomprijs --set global.host=stroomprijs.test --set api.image.tag=test --set frontend.image.tag=test > /tmp/stroomprijs-rendered.yaml
python3 -m pytest tests/helm/test_rendered_routes.py -v
```

Expected: lint and tests pass.

- [ ] **Step 5: Commit**

```bash
git add charts/stroomprijs tests/helm/test_rendered_routes.py
git commit -m "feat: add route-preserving Helm chart"
```

---

### Task 3: Config, secrets, probes, resources, and autoscaling

**Files:**
- Create: `charts/stroomprijs/templates/configmap.yaml`
- Create: `charts/stroomprijs/templates/serviceaccounts.yaml`
- Create: `charts/stroomprijs/templates/frontend-hpa.yaml`
- Create: `charts/stroomprijs/templates/api-hpa.yaml`
- Create: `charts/stroomprijs/templates/pdb.yaml`
- Create: `charts/stroomprijs/values-production.example.yaml`
- Create: `tests/helm/test_runtime_policy.py`
- Modify: workload templates and `values.yaml`.

**Interfaces:**
- Produces: ConfigMap keys, Secret references, startup/liveness/readiness probes, resource defaults, HPA, PDB, and tokenless ServiceAccounts.

- [ ] **Step 1: Write failing policy tests**

Assert all Deployments define requests/limits and startup/liveness/readiness probes; API readiness uses `/health/ready`; liveness uses `/health/live`; CronJob has deadline/backoff/history limits; ServiceAccounts disable token automount; production example contains no literal Secret object or credential value; HPA targets only frontend/API.

- [ ] **Step 2: Run and verify failure**

Run: `python3 -m pytest tests/helm/test_runtime_policy.py -v`
Expected: FAIL until policies are rendered.

- [ ] **Step 3: Implement explicit runtime policy**

ConfigMap exposes API base URL, timezone, request timeout/retries, refresh cadence, max data age, docs flag, and log level. Deployments reference an existing Secret key for DB DSN. Default resources are conservative and non-zero. HPA defaults to 2–6 replicas for frontend/API and is configurable. PDB renders only when replicas exceed one.

- [ ] **Step 4: Verify policy matrix**

Run:

```bash
helm lint charts/stroomprijs
python3 -m pytest tests/helm/test_runtime_policy.py -v
```

Expected: all default and production-example renders pass.

- [ ] **Step 5: Commit**

```bash
git add charts/stroomprijs tests/helm/test_runtime_policy.py
git commit -m "feat: add k3s runtime controls"
```

---

### Task 4: Pod security and default-deny NetworkPolicy

**Files:**
- Create: `charts/stroomprijs/templates/networkpolicy.yaml`
- Create: `tests/helm/test_security_policy.py`
- Modify: all workload templates.

**Interfaces:**
- Produces: restricted pod/container security contexts and explicit network flows.

- [ ] **Step 1: Write failing security tests**

For each pod template assert: `runAsNonRoot: true`, UID/GID 10001, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, capabilities drop `ALL`, `seccompProfile.type: RuntimeDefault`, and no token mount. Assert NetworkPolicies default-deny ingress/egress, allow ingress from configured Traefik namespace/selectors, allow frontend-to-API, API/worker-to-PostgreSQL, worker-to-DNS and TLS egress, and do not grant broad `0.0.0.0/0` except configurable upstream TLS egress when DNS-based policy is unavailable.

- [ ] **Step 2: Run and verify failure**

Run: `python3 -m pytest tests/helm/test_security_policy.py -v`
Expected: FAIL until all controls exist.

- [ ] **Step 3: Implement workload and network hardening**

Set writable `emptyDir` mounts only for `/tmp` where required. Keep API/frontend root filesystems read-only. Use per-component ServiceAccounts. Document that standard NetworkPolicy cannot select DNS names and provide a configurable CIDR/egress-gateway option for EnergyZero.

- [ ] **Step 4: Verify Helm security gate**

Run:

```bash
helm template stroomprijs charts/stroomprijs --set global.host=stroomprijs.test --set api.image.tag=test --set frontend.image.tag=test | kubeconform -strict -summary
python3 -m pytest tests/helm/test_security_policy.py -v
```

Expected: schema and policy tests pass.

- [ ] **Step 5: Commit**

```bash
git add charts/stroomprijs tests/helm/test_security_policy.py
git commit -m "security: enforce pod and network isolation"
```

---

### Task 5: TLS, rate limiting, canonical host, and docs protection

**Files:**
- Create: `charts/stroomprijs/templates/traefik-middlewares.yaml`
- Create: `charts/stroomprijs/templates/certificate.yaml`
- Create: `tests/helm/test_ingress_security.py`
- Modify: `charts/stroomprijs/templates/ingress.yaml`
- Modify: `charts/stroomprijs/values.yaml`

**Interfaces:**
- Produces: HTTPS redirect, HSTS/security headers, rate limiting, TLS certificate reference, canonical host, and production docs suppression.

- [ ] **Step 1: Write failing ingress tests**

Assert production render has TLS, HTTP-to-HTTPS middleware, HSTS, configured host only, rate-limit middleware, no wildcard host, and `STROOMPRIJS_DOCS_ENABLED=false`. Assert certificate renders only when cert-manager integration is enabled.

- [ ] **Step 2: Run and verify failure**

Run: `python3 -m pytest tests/helm/test_ingress_security.py -v`
Expected: FAIL until ingress security is implemented.

- [ ] **Step 3: Implement Traefik resources**

Create separate redirect and secure routers if required by Traefik chart behavior. Apply security headers and average/burst rate limits from values. Route docs only when docs are explicitly enabled; otherwise backend returns 404 because FastAPI docs URLs are disabled.

- [ ] **Step 4: Verify default and production renders**

Run:

```bash
helm lint charts/stroomprijs
python3 -m pytest tests/helm/test_ingress_security.py -v
```

Expected: all ingress/TLS tests pass without hardcoded domains or issuers.

- [ ] **Step 5: Commit**

```bash
git add charts/stroomprijs tests/helm/test_ingress_security.py
git commit -m "security: protect public k3s ingress"
```

---

### Task 6: Observability and operational runbooks

**Files:**
- Create: `charts/stroomprijs/templates/servicemonitor.yaml`
- Create: `charts/stroomprijs/templates/prometheusrule.yaml`
- Create: `docs/operations/k3s-runbook.md`
- Create: `docs/operations/rollback.md`
- Create: `tests/helm/test_observability.py`

**Interfaces:**
- Produces: optional metrics integration and explicit operator procedures.

- [ ] **Step 1: Write failing observability tests**

Assert opt-in ServiceMonitor targets API metrics internally, alerts cover stale snapshot, repeated ingest failure, 5xx ratio, and unavailable replicas, and no metrics ingress is public by default.

- [ ] **Step 2: Run and verify failure**

Run: `python3 -m pytest tests/helm/test_observability.py -v`
Expected: FAIL because resources do not exist.

- [ ] **Step 3: Implement resources and exact runbooks**

Runbook contains commands for Helm diff/template, rollout status, pod logs, readiness inspection, ingest CronJob execution, snapshot-age verification, and incident triage. Rollback document uses `helm history`, `helm rollback <release> <revision> --wait`, compatibility checks, and explicit database migration decision points. It states production commands require human approval.

- [ ] **Step 4: Verify docs and render**

Run:

```bash
python3 -m pytest tests/helm/test_observability.py -v
helm template stroomprijs charts/stroomprijs --set monitoring.enabled=true --set global.host=stroomprijs.test --set api.image.tag=test --set frontend.image.tag=test > /tmp/stroomprijs-monitoring.yaml
```

Expected: tests pass and monitoring resources render only when enabled.

- [ ] **Step 5: Commit**

```bash
git add charts/stroomprijs docs/operations tests/helm/test_observability.py
git commit -m "ops: add k3s observability and rollback runbooks"
```

---

### Task 7: Ephemeral k3d end-to-end deployment gate

**Files:**
- Create: `scripts/k3d-smoke.sh`
- Create: `scripts/wait-for-snapshot.py`
- Create: `tests/e2e/test_k3s_routes.py`
- Create: `.github/workflows/k3s-ci.yml`

**Interfaces:**
- Produces: repeatable ephemeral cluster deployment and compatibility verification.

- [ ] **Step 1: Write failing route smoke tests**

Test HTTPS/host routing in the ephemeral environment, HTML 200s for every legacy page, JSON 200s and expected fields for every legacy API, docs 404 in production values, liveness/readiness behavior, and a controlled stale-data readiness failure fixture.

- [ ] **Step 2: Run and verify failure before cluster automation exists**

Run: `python3 -m pytest tests/e2e/test_k3s_routes.py -v`
Expected: FAIL because no target cluster URL is configured.

- [ ] **Step 3: Implement isolated k3d smoke workflow**

Script creates a uniquely named k3d cluster, imports locally built images, installs a disposable PostgreSQL test dependency, creates a Secret with `local-dev-only-not-a-secret`, installs the chart, runs ingest fixture/bootstrap, waits on rollout/readiness, executes tests, captures diagnostics on failure, and deletes only its uniquely named cluster in a trap.

- [ ] **Step 4: Run the full ephemeral gate**

Run: `scripts/k3d-smoke.sh`
Expected: cluster creates, chart installs, all route/health/compatibility tests pass, diagnostics are empty, and cluster is removed.

- [ ] **Step 5: Commit**

```bash
git add scripts/k3d-smoke.sh scripts/wait-for-snapshot.py tests/e2e/test_k3s_routes.py .github/workflows/k3s-ci.yml
git commit -m "test: verify Stroomprijs on ephemeral k3s"
```

---

### Task 8: GHCR release workflow and approval boundary

**Files:**
- Create: `.github/workflows/container-ci.yml`
- Create: `.github/workflows/release.yml`
- Create: `docs/operations/release-checklist.md`
- Modify: `README.md`

**Interfaces:**
- Produces: immutable multi-architecture GHCR images, SBOM/provenance artifacts, chart package, and an approval-gated release process.

- [ ] **Step 1: Add workflow-policy tests**

Create a test parsing workflow YAML and asserting: pull requests build/test/scan but do not push; release workflow triggers only on version tags or manual dispatch; GHCR permissions are least-privilege; images use digest/commit tags; provenance and SBOM are generated; production deployment is absent or protected by an explicit GitHub Environment approval.

- [ ] **Step 2: Run and verify failure**

Run: `python3 -m pytest tests/ci/test_release_workflows.py -v`
Expected: FAIL until workflows exist.

- [ ] **Step 3: Implement build and release workflows**

Container CI runs BuildKit builds, Trivy high/critical scans, Gitleaks, SBOM generation, and smoke tests. Release publishes `ghcr.io/dockerized-nl/stroomprijs-api` and `ghcr.io/dockerized-nl/stroomprijs-web` with immutable version and SHA tags plus packaged Helm chart. Do not add automatic production deployment.

- [ ] **Step 4: Run the local release gate**

Run:

```bash
python3 -m pytest tests/ci/test_release_workflows.py -v
gitleaks detect --source . --no-banner
trivy image --severity HIGH,CRITICAL --exit-code 1 stroomprijs-api:test
trivy image --severity HIGH,CRITICAL --exit-code 1 stroomprijs-web:test
helm package charts/stroomprijs --destination /tmp/stroomprijs-chart
```

Expected: tests and scans pass; chart package is generated; no registry push or deployment occurs locally.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/container-ci.yml .github/workflows/release.yml docs/operations/release-checklist.md README.md tests/ci/test_release_workflows.py
git commit -m "ci: add secure GHCR release pipeline"
```

## Plan exit criteria

- Frontend/API images are non-root, scanned, reproducible, and smoke-tested.
- Helm chart renders valid route-preserving, probe-aware workloads.
- TLS, rate limiting, docs suppression, pod security, and NetworkPolicy are enforced by tests.
- Config and secret references are separated.
- Ephemeral k3d verifies HTML/API compatibility and readiness behavior.
- Release produces immutable GHCR artifacts and a Helm package without automatic production deployment.
- Rollback is documented and tested outside production.
- Production remains blocked on Tester, DevSecOps, Pentester, and human approval.
