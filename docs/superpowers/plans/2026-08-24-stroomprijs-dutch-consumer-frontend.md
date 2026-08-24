# Stroomprijs Dutch Consumer Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver an accessible, mobile-first Dutch consumer website that serves households and solar-panel owners equally while preserving every existing HTML route.

**Architecture:** A Next.js App Router frontend renders all public HTML routes and consumes typed internal FastAPI endpoints. Domain calculations remain in the backend; the frontend owns presentation, navigation, accessibility, and clear fresh/stale/unavailable states.

**Tech Stack:** Next.js App Router, TypeScript, React, CSS Modules/design tokens, Recharts or an accessible SVG chart wrapper, Vitest, Testing Library, Playwright, axe-core.

**Spec:** `docs/superpowers/specs/2026-08-24-stroomprijs-route-preserving-consumer-platform-design.md`

## Global Constraints

- Public copy defaults to Dutch and every page declares `lang="nl"`.
- Preserve `/`, `/index.html`, `/health`, `/prices`, `/gemiddeld`, `/kopen`, and `/verkopen`.
- Serve households and solar-panel owners with equal visual priority.
- Core meaning uses text, icon, and color; never color alone.
- Every chart has a semantic table or equivalent textual representation.
- Source, local date, timezone, VAT basis, and last refresh are visible.
- The frontend never calculates cheapest/most-expensive membership independently.
- The product must render a useful server-side result without client JavaScript.
- Primary flows target WCAG 2.2 AA.
- Every task follows RED → GREEN → REFACTOR and ends with a focused commit.

## File structure

- `frontend/package.json` — frontend commands and pinned dependencies.
- `frontend/src/app/` — route-preserving App Router pages.
- `frontend/src/components/` — shared navigation, decision, trust, timeline, and status components.
- `frontend/src/lib/api.ts` — server-side typed backend client.
- `frontend/src/lib/types.ts` — API types generated or checked against backend OpenAPI.
- `frontend/src/styles/` — design tokens and global responsive rules.
- `frontend/src/content/nl.ts` — centralized Dutch product copy.
- `frontend/tests/` — unit, accessibility, and browser tests.

---

### Task 1: Frontend baseline, route shell, and Dutch metadata

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/globals.css`
- Create: `frontend/src/content/nl.ts`
- Create: `frontend/tests/layout.test.tsx`

**Interfaces:**
- Produces: `RootLayout`, global design tokens, Dutch metadata, and shared copy constants.

- [ ] **Step 1: Write the failing layout test**

```tsx
import { render, screen } from "@testing-library/react";
import RootLayout, { metadata } from "@/app/layout";

it("declares Dutch and consumer-first branding", () => {
  render(<RootLayout><main>inhoud</main></RootLayout>);
  expect(document.documentElement.lang).toBe("nl");
  expect(metadata.title).toMatch(/Stroomprijs/);
  expect(screen.getByText("inhoud")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run and verify failure**

Run: `cd frontend && npm test -- layout.test.tsx`
Expected: FAIL because frontend files do not exist.

- [ ] **Step 3: Create the minimal Next.js baseline**

Use scripts `dev`, `build`, `start`, `lint`, `typecheck`, `test`, and `test:e2e`. `RootLayout` must render `<html lang="nl">`, set a consumer title/description, import globals, and expose a skip link. Tokens define semantic colors for background, surface, text, muted text, border, favorable, unfavorable, neutral, focus, spacing, radii, and typography. Do not copy the old inline CSS.

- [ ] **Step 4: Verify baseline**

Run:

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm test -- layout.test.tsx
npm run build
```

Expected: all commands exit 0 and `/` builds server-side.

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat: establish Dutch consumer frontend"
```

---

### Task 2: Typed backend client and freshness states

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/format.ts`
- Create: `frontend/tests/api.test.ts`
- Create: `frontend/tests/format.test.ts`

**Interfaces:**
- Consumes: backend `/api/v1/prices/today` and recommendation endpoints from the backend plan.
- Produces: `getTodayPrices()`, `getConsumeRecommendation()`, `getExportRecommendation()`, `formatPrice()`, `formatSlotRange()`, and discriminated `Fresh | Stale | Unavailable` states.

- [ ] **Step 1: Write failing client/format tests**

```ts
it("maps 503 to an unavailable state without leaking details", async () => {
  server.use(http.get("*/api/v1/prices/today", () => HttpResponse.json({detail: "db host secret"}, {status: 503})));
  await expect(getTodayPrices()).resolves.toEqual({kind: "unavailable"});
});

it("formats Dutch euro per kWh values", () => {
  expect(formatPrice(0.1234)).toBe("€ 0,1234/kWh");
});
```

- [ ] **Step 2: Run and verify failure**

Run: `cd frontend && npm test -- api.test.ts format.test.ts`
Expected: FAIL because the client and formatters are undefined.

- [ ] **Step 3: Implement server-side client**

Use `INTERNAL_API_BASE_URL`, a bounded fetch timeout, `cache: "no-store"` for current status, and controlled mappings for fresh/stale/unavailable. Types must include source, timezone, source timestamp, last refresh, VAT flag, normalized slots, and backend-owned recommendation fields. Never surface raw backend errors.

- [ ] **Step 4: Verify tests and type consistency**

Run:

```bash
cd frontend
npm test -- api.test.ts format.test.ts
npm run typecheck
```

Expected: all tests pass with no implicit `any`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib frontend/tests/api.test.ts frontend/tests/format.test.ts
git commit -m "feat: add typed electricity API client"
```

---

### Task 3: Shared consumer decision and trust components

**Files:**
- Create: `frontend/src/components/AppHeader.tsx`
- Create: `frontend/src/components/DecisionCard.tsx`
- Create: `frontend/src/components/TrustBar.tsx`
- Create: `frontend/src/components/BestWindows.tsx`
- Create: `frontend/src/components/ServiceNotice.tsx`
- Create: `frontend/src/components/components.module.css`
- Create: `frontend/tests/components.test.tsx`

**Interfaces:**
- Produces: shared components used by every page; `DecisionCard` accepts backend recommendation data and persona `consume | export`.

- [ ] **Step 1: Write failing component/accessibility tests**

Assert both persona labels are present, status contains visible text and icon, stale data exposes a warning, source/timezone/VAT/refresh are readable, links have visible focus classes, and headings follow one `h1` then `h2` order.

```tsx
it("does not communicate status with color alone", () => {
  render(<DecisionCard persona="consume" recommendation={fixture.ok} />);
  expect(screen.getByText("Goed moment om stroom te gebruiken")).toBeVisible();
  expect(screen.getByLabelText("gunstig")).toBeVisible();
});
```

- [ ] **Step 2: Run and verify failure**

Run: `cd frontend && npm test -- components.test.tsx`
Expected: FAIL because components do not exist.

- [ ] **Step 3: Implement shared components**

`AppHeader` links to dashboard, prices, analysis, consume, and export routes. `DecisionCard` renders title, action, rationale, price/rank, next window, and semantic icon. `TrustBar` renders exact source/date/timezone/VAT/refresh labels. `ServiceNotice` supports stale and unavailable states with `role="status"` or `role="alert"`.

- [ ] **Step 4: Verify components and axe checks**

Run: `cd frontend && npm test -- components.test.tsx`
Expected: all assertions and component axe checks pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components frontend/tests/components.test.tsx
git commit -m "feat: add accessible decision components"
```

---

### Task 4: Consumer dashboard on `/` and `/index.html`

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/index.html/page.tsx`
- Create: `frontend/src/components/Dashboard.tsx`
- Create: `frontend/tests/dashboard.test.tsx`
- Create: `frontend/tests/e2e/dashboard.spec.ts`

**Interfaces:**
- Consumes: three typed client functions and shared components.
- Produces: `Dashboard` shared by `/` and `/index.html`.

- [ ] **Step 1: Write failing dashboard tests**

Assert a first viewport contains both consume and export decisions, best/worst windows, and trust metadata. Assert `/index.html` renders the same dashboard. Assert stale data is visibly marked and unavailable data suppresses authoritative recommendations.

- [ ] **Step 2: Run and verify failure**

Run: `cd frontend && npm test -- dashboard.test.tsx`
Expected: FAIL because dashboard is undefined.

- [ ] **Step 3: Implement server-rendered dashboard**

Fetch all data on the server, render the two personas with equal card weight, show best/worst windows, add Dutch explanatory copy, and place API documentation under a secondary “Voor ontwikkelaars” link. `/index.html` imports and returns the same component rather than redirecting.

- [ ] **Step 4: Verify unit and browser behavior**

Run:

```bash
cd frontend
npm test -- dashboard.test.tsx
npm run build
npm run test:e2e -- dashboard.spec.ts
```

Expected: both routes return 200, primary content is present at mobile and desktop sizes, and the server-rendered HTML includes recommendations.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app frontend/src/components/Dashboard.tsx frontend/tests/dashboard.test.tsx frontend/tests/e2e/dashboard.spec.ts
git commit -m "feat: build household and solar dashboard"
```

---

### Task 5: Route-preserving prices and analysis pages

**Files:**
- Create: `frontend/src/app/prices/page.tsx`
- Create: `frontend/src/app/gemiddeld/page.tsx`
- Create: `frontend/src/components/PriceTimeline.tsx`
- Create: `frontend/src/components/PriceTable.tsx`
- Create: `frontend/src/components/StatisticsSummary.tsx`
- Create: `frontend/tests/prices.test.tsx`
- Create: `frontend/tests/e2e/prices.spec.ts`

**Interfaces:**
- Consumes: normalized slots and backend-derived statistics/recommendation groups.
- Produces: accessible timeline/table and analysis pages.

- [ ] **Step 1: Write failing data parity and accessibility tests**

Assert one table row per slot, exact displayed values match API fixtures, 23/24/25-slot labels are unambiguous, repeated fall-back hours include offset/context, chart has an accessible name, and the table remains visible when chart JavaScript fails.

- [ ] **Step 2: Run and verify failure**

Run: `cd frontend && npm test -- prices.test.tsx`
Expected: FAIL because pages/components do not exist.

- [ ] **Step 3: Implement the two pages**

`/prices` renders current price, normalized timeline, and semantic table. `/gemiddeld` renders lowest/average/highest, cheapest/most-expensive windows, and practical household/solar explanations. The chart consumes backend classifications and is enhancement-only; the table is authoritative.

- [ ] **Step 4: Verify 23/24/25-slot and no-JS behavior**

Run:

```bash
cd frontend
npm test -- prices.test.tsx
npm run test:e2e -- prices.spec.ts
```

Expected: all slot-count fixtures, mobile widths, and JavaScript-disabled assertions pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/prices frontend/src/app/gemiddeld frontend/src/components/PriceTimeline.tsx frontend/src/components/PriceTable.tsx frontend/src/components/StatisticsSummary.tsx frontend/tests/prices.test.tsx frontend/tests/e2e/prices.spec.ts
git commit -m "feat: add accessible price planning views"
```

---

### Task 6: Route-preserving consume, export, and public health pages

**Files:**
- Create: `frontend/src/app/kopen/page.tsx`
- Create: `frontend/src/app/verkopen/page.tsx`
- Create: `frontend/src/app/health/page.tsx`
- Create: `frontend/src/components/RecommendationPage.tsx`
- Create: `frontend/tests/recommendations.test.tsx`
- Create: `frontend/tests/health-page.test.tsx`

**Interfaces:**
- Produces: existing consumer decision paths and compatibility health page.

- [ ] **Step 1: Write failing state matrix tests**

Test `OK`, `NOT OK`, `neutraal`, stale, and unavailable states for both routes. Assert `kopen` uses consumption terminology and `verkopen` uses solar/export terminology. Test `/health` presents API readiness/freshness without pretending all dependencies are healthy.

- [ ] **Step 2: Run and verify failure**

Run: `cd frontend && npm test -- recommendations.test.tsx health-page.test.tsx`
Expected: FAIL because pages are undefined.

- [ ] **Step 3: Implement shared recommendation page**

Render backend verdict, rationale, current price/rank, next recommended window, and freshness notice. Public `/health` queries machine health endpoints server-side and uses Dutch labels `Beschikbaar`, `Beperkt beschikbaar`, or `Niet beschikbaar`; do not expose database/provider internals.

- [ ] **Step 4: Verify all route states**

Run: `cd frontend && npm test -- recommendations.test.tsx health-page.test.tsx`
Expected: all state permutations pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/kopen frontend/src/app/verkopen frontend/src/app/health frontend/src/components/RecommendationPage.tsx frontend/tests/recommendations.test.tsx frontend/tests/health-page.test.tsx
git commit -m "feat: add consume export and status pages"
```

---

### Task 7: Full accessibility, responsive, and visual regression gate

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/tests/e2e/accessibility.spec.ts`
- Create: `frontend/tests/e2e/responsive.spec.ts`
- Create: `frontend/tests/e2e/visual.spec.ts`
- Create: `frontend/tests/e2e/fixtures.ts`
- Create: `.github/workflows/frontend-ci.yml`
- Modify: `README.md`

**Interfaces:**
- Produces: frontend CI jobs `quality`, `unit`, `build`, `e2e`, and `accessibility`.

- [ ] **Step 1: Add failing whole-site browser tests**

For every public HTML path, assert HTTP 200, one `h1`, skip-link behavior, keyboard-reachable navigation, visible focus, no serious/critical axe violations, no horizontal overflow at 320px, and stable screenshots at 390×844 and 1440×1000.

- [ ] **Step 2: Run and capture initial failures**

Run: `cd frontend && npm run test:e2e`
Expected: failures identify remaining accessibility/responsive differences before fixes.

- [ ] **Step 3: Fix only evidence-backed frontend issues and add CI**

Correct focus order, contrast, overflow, labels, or breakpoints found by tests. Workflow runs `npm ci`, lint, typecheck, unit tests, production build, Playwright, and axe checks. Upload Playwright report only on failure.

- [ ] **Step 4: Run the complete frontend gate**

Run:

```bash
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
npm run test:e2e
```

Expected: every command exits 0 and all approved route screenshots are generated consistently.

- [ ] **Step 5: Commit**

```bash
git add frontend .github/workflows/frontend-ci.yml README.md
git commit -m "test: enforce accessible responsive frontend"
```

## Plan exit criteria

- Every existing HTML route returns the new Dutch-first experience.
- Household and solar decisions have equal priority on the dashboard.
- All displayed values are sourced from typed backend contracts.
- Fresh/stale/unavailable behavior is explicit and tested.
- Core meaning is accessible without color, charts, or client JavaScript.
- Mobile, accessibility, visual, type, unit, and build gates pass.
