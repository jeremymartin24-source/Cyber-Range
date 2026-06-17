# Development Roadmap

## Guiding Principles

- **Ship usable software at the end of every phase.** Each phase closes with a deployable, testable system.
- **Backend before frontend.** Build and test API endpoints before building the UI that consumes them.
- **Wazuh-independent first.** The core platform must be fully functional using simulated alerts before requiring a live Wazuh connection.
- **Migrate forward, never break backward.** All schema changes go through Alembic migrations.

---

## Phase Overview

| Phase | Name | Duration | Deliverable |
|---|---|---|---|
| 1 | Foundation | 3 weeks | Docker stack, auth, user/org CRUD |
| 2 | Core Domain | 4 weeks | Courses, teams, incidents, alerts (mock), evidence, notes |
| 3 | Scenario Engine | 3 weeks | Scenario YAML parsing, launch, instance lifecycle |
| 4 | Wazuh Integration | 3 weeks | Alert ingestion, agent sync, correlation |
| 5 | Reporting & Grading | 3 weeks | Report builder, submission, grading workflow |
| 6 | Campaigns | 2 weeks | Campaign model, stage progression, decision tracking |
| 7 | Frontend | 4 weeks | Next.js UI for all V1 features |
| 8 | Hardening | 2 weeks | Security audit, performance, production config |

**Total: ~24 weeks** for a production-ready V1.

A single developer working part-time (10–15 hours/week) should treat these as estimates; full-time work compresses this significantly.

---

## Phase 1: Foundation

**Goal:** A running Docker stack with working authentication and user management. The skeleton everything else builds on.

### Week 1: Project Scaffolding

- [ ] Initialize git repository and branch strategy (`main`, `dev`, feature branches).
- [ ] Create `docker-compose.yml` with services: `db`, `redis`, `backend`, `frontend`, `worker`, `beat`.
- [ ] Create FastAPI project: `pyproject.toml` (using `uv` or `poetry`), directory structure per spec.
- [ ] Create Next.js 14 project with TypeScript and Tailwind CSS.
- [ ] Configure `.env.example` with all required variables.
- [ ] Write `prestart.sh` that runs `alembic upgrade head` before backend starts.
- [ ] Set up Alembic with initial empty migration.

### Week 2: Database + Auth Backend

- [ ] Write SQLAlchemy models: `Organization`, `User`.
- [ ] Write Alembic migration for `organizations` and `users` tables.
- [ ] Implement `POST /api/v1/auth/login` (JWT issuance, httpOnly cookies).
- [ ] Implement `POST /api/v1/auth/refresh` and `POST /api/v1/auth/logout`.
- [ ] Implement `GET /api/v1/auth/me`.
- [ ] Write `get_current_user` and `require_role` FastAPI dependencies.
- [ ] Add Redis JWT denylist for logout.
- [ ] Write pytest tests for all auth endpoints.

### Week 3: User + Organization CRUD

- [ ] Implement full CRUD for `users` (with role-based access enforcement).
- [ ] Implement full CRUD for `organizations`.
- [ ] Add password change endpoint.
- [ ] Seed script: create default org (Buckeye Manufacturing Group) + one admin user.
- [ ] Add request logging middleware.
- [ ] Verify: `docker compose up` starts all services cleanly, auth flow works end-to-end via Swagger UI.

**Phase 1 Exit Criteria:**
- All services start from cold with `docker compose up`.
- Can register a user, log in, get a token, and log out.
- Alembic migration history is clean.
- Auth tests pass.

---

## Phase 2: Core Domain

**Goal:** The full incident management lifecycle, including alerts (manually created or mock-imported), evidence, and case notes — all without Wazuh.

### Week 4: Courses, Enrollments, Teams

- [ ] SQLAlchemy models + Alembic migration: `Course`, `Enrollment`, `Team`, `TeamMember`.
- [ ] Implement API: courses (CRUD), enrollments, teams (CRUD + member management).
- [ ] Seed script: create one sample course with 5 enrolled students and 2 teams.
- [ ] Tests for all course/team endpoints.

### Week 5: Endpoints + Incidents

- [ ] SQLAlchemy models + Alembic migration: `Endpoint`, `Incident`.
- [ ] Implement incident number sequence: `INC-YYYY-NNNN`.
- [ ] Implement API: endpoints (CRUD), incidents (full lifecycle).
- [ ] Implement status transition validation (open → investigating → contained → resolved → closed).
- [ ] Implement `student_decisions` logging for: `severity_change`, `status_change`.
- [ ] Seed script: create 3 sample endpoints (BMG-FIN-WS01, BMG-FIN-WS02, BMG-DC01).
- [ ] Tests for incident lifecycle transitions.

### Week 6: Alerts (Mock) + Evidence + Case Notes

- [ ] SQLAlchemy models + Alembic migration: `Alert`, `IncidentAlert`, `Evidence`, `CaseNote`.
- [ ] Implement API: alerts (CRUD, acknowledge, link to incident).
- [ ] Implement `student_decisions` logging for: `alert_acknowledged`, `alert_linked`, `evidence_collected`.
- [ ] Implement API: evidence (CRUD + file upload via multipart).
- [ ] Implement API: case notes (CRUD + pin).
- [ ] Create mock alert fixture loader: reads a JSON file of sample alerts and inserts them for testing.
- [ ] Tests for all new endpoints.

### Week 7: Student Decisions + Endpoint Actions

- [ ] Implement `POST /endpoints/{id}/isolate` and `restore` (simulation mode — updates status, logs decision).
- [ ] Implement decision listing and filtering endpoints.
- [ ] Decision audit middleware: intercept qualifying API actions and auto-write decision records.
- [ ] Tests + integration test: full investigation flow (triage alert → link to incident → collect evidence → add note → isolate endpoint).

**Phase 2 Exit Criteria:**
- Full incident investigation workflow is operable via the API (Swagger UI).
- Decision log is populated correctly by student actions.
- All Phase 2 tests pass.

---

## Phase 3: Scenario Engine

**Goal:** YAML-based scenarios can be loaded, launched, and managed. Simulated alert injection works. Scenario instance lifecycle is complete.

### Week 8: Scenario Model + YAML Parser

- [ ] SQLAlchemy models + Alembic migration: `Scenario`, `ScenarioInstance`, `EndpointAssignment`.
- [ ] Write Pydantic validation schema for the scenario YAML format (full field validation per spec).
- [ ] Implement `POST /api/v1/scenarios/validate` — parse and validate a YAML file, return structured errors.
- [ ] Implement scenario CRUD + publish toggle.
- [ ] Write example scenario files: `tl-001-alert-triage/scenario.yaml` and `ic-001-phishing-finance/scenario.yaml`.
- [ ] Scenario import from YAML file → database record.

### Week 9: Scenario Launch + Instance Lifecycle

- [ ] Implement `ScenarioLaunchService`:
  - Creates `scenario_instance` record.
  - Creates endpoint assignments from `required_agents`.
  - Creates initial incident if `auto_create_incident = true`.
  - Schedules simulated alert injection Celery tasks.
- [ ] Implement scenario instance status transitions (pending → active → completed → graded → archived).
- [ ] Implement `GET /scenario-instances/{id}/progress` — returns completion metrics (alerts acknowledged, evidence count, incident status, report status).
- [ ] Tests for scenario launch and lifecycle.

### Week 10: Simulated Alert Injection + Narrative Injects

- [ ] Implement Celery task `inject_simulated_alert`: reads inject definition from scenario_data, creates synthetic Alert records at scheduled time.
- [ ] Implement narrative inject storage: when scenario launches, schedule `inject_narrative` tasks that write the inject content to a `scenario_injects` table (simple: `scenario_instance_id`, `inject_at`, `type`, `content`, `delivered_at`).
- [ ] Implement `GET /scenario-instances/{id}/injects` for the frontend to poll for new narrative updates.
- [ ] End-to-end test: launch a scenario → wait for simulated alert → verify it appears in `/alerts/`.

**Phase 3 Exit Criteria:**
- Instructor can launch a scenario (via API) against a team.
- Simulated alerts appear at the correct time offsets.
- Narrative injects are retrievable.
- Student progress endpoint returns accurate data.

---

## Phase 4: Wazuh Integration

**Goal:** Real Wazuh alert ingestion and agent synchronization. Platform works with a live Wazuh server.

### Week 11: Wazuh Client + Agent Sync

- [ ] Implement `WazuhClient` in `backend/app/integrations/wazuh/client.py`:
  - Manager REST API client (python-requests + retry logic).
  - Indexer (OpenSearch) client using `opensearch-py`.
  - Connection pooling, TLS config, API key auth.
- [ ] Implement Celery task `sync_wazuh_agents`:
  - Calls Wazuh Manager `/agents` endpoint.
  - Upserts agent records into `endpoints` table.
  - Updates `status`, `last_seen_at`, `ip_address`, `os_version`.
- [ ] Implement Celery beat schedule: agent sync every 5 minutes.
- [ ] Implement `GET /api/v1/wazuh/health` and `GET /api/v1/wazuh/agents`.
- [ ] Test with a real or mocked Wazuh API (record HTTP fixtures with `responses` library).

### Week 12: Alert Ingestion Pipeline

- [ ] Implement `AlertNormalizer` — maps Wazuh Indexer alert document fields to `Alert` schema:
  - `_id` → `wazuh_alert_id`
  - `rule.id` → `rule_id`, `rule.level` → `rule_level`
  - `agent.name` → `agent_name`
  - `@timestamp` → `timestamp`
  - Full document → `raw_data`
- [ ] Implement Celery task `poll_wazuh_alerts`:
  - Queries Indexer for alerts newer than `last_poll_timestamp` (stored in Redis).
  - Applies per-scenario-instance filters (agent names, rule levels, rule IDs).
  - Normalizes and deduplicates alerts.
  - Bulk-inserts new alerts into PostgreSQL.
- [ ] Implement Celery beat schedule: alert poll every 30 seconds.
- [ ] Implement `POST /api/v1/wazuh/sync/alerts` (manual trigger for instructors).

### Week 13: Alert Correlation Engine

- [ ] Implement `AlertCorrelationEngine`:
  - On each new alert insert, find active scenario instances where:
    - `wazuh.alert_filters.agent_names` contains the alert's `agent_name`, AND
    - Alert `rule_level` ≥ `alert_filters.rule_level_min`, AND
    - Alert `rule_id` not in `rule_ids_exclude`.
  - For each matching scenario instance, insert `incident_alerts` record linking alert to the instance's incident.
- [ ] Write integration tests with a mocked Wazuh Indexer returning fixture alerts.
- [ ] Verify full pipeline: Wazuh alert → normalize → deduplicate → correlate → appears in `/incidents/{id}` alert list.

**Phase 4 Exit Criteria:**
- With a live (or mocked) Wazuh server, alerts flow into the platform within 60 seconds.
- Agent list syncs and populates the endpoints table.
- Alerts are correctly correlated to scenario instance incidents.
- Platform degrades gracefully (logs errors, does not crash) when Wazuh is unreachable.

---

## Phase 5: Reporting & Grading

**Goal:** Students can write and submit incident reports. Instructors can grade them. Auto-scoring runs on student decisions.

### Week 14: Report Backend

- [ ] SQLAlchemy models + Alembic migration: `Report`, `Grade`.
- [ ] Implement `GET /incidents/{id}/report` — creates empty draft if none exists.
- [ ] Implement `PUT /reports/{id}` — partial update (autosave); validate individual section content.
- [ ] Implement `POST /reports/{id}/submit` — lock report, set `submitted_at`, update scenario instance status.
- [ ] Business rule enforcement: cannot submit if `executive_summary` is empty; scenario must be active.
- [ ] Tests for report lifecycle.

### Week 15: Grading Workflow

- [ ] Implement `POST /reports/{id}/grade` — instructor submits rubric scores + feedback.
- [ ] Implement `PUT /grades/{id}` — instructor revises grade.
- [ ] Implement `GradingEngine.score_decisions()`:
  - For each `decision_scoring` rule in scenario YAML, query `student_decisions` for matching records.
  - Compute auto-score (time-window-based, count-based, type-based).
  - Write auto-score and feedback to `student_decisions.auto_score`.
- [ ] Implement `GET /scenario-instances/{id}/grades` for instructor grade overview.
- [ ] Implement `POST /reports/{id}/return` — instructor returns report for revision (status → returned).
- [ ] Tests for grading and auto-scoring.

### Week 16: Report Completeness Validation

- [ ] Report section completeness checks:
  - `timeline`: requires ≥ 1 event with a timestamp.
  - `affected_assets`: requires ≥ 1 asset.
  - `iocs`: no minimum required (some investigations find no IOCs).
  - `containment_actions`: required if incident status reached `contained`.
- [ ] Implement report completeness score: percentage of optional sections filled.
- [ ] Expose completeness via `GET /reports/{id}` as `completeness_pct` field.
- [ ] Tests.

**Phase 5 Exit Criteria:**
- Student can draft, autosave, and submit a report.
- Instructor can grade a submitted report with per-rubric scores.
- Auto-scoring runs on submission and populates decision scores.
- Grade is visible to student after grading.

---

## Phase 6: Campaigns

**Goal:** Instructors can create multi-stage campaigns. Students progress through stages sequentially.

### Week 17: Campaign Model + Enrollment

- [ ] SQLAlchemy models + Alembic migration: `Campaign`, `CampaignStage`, `CampaignEnrollment`.
- [ ] Implement campaign CRUD API.
- [ ] Implement campaign stage CRUD (add/remove/reorder stages).
- [ ] Implement `POST /campaigns/{id}/enroll` — enroll a team or student.
- [ ] Implement stage prerequisite validation on enrollment.

### Week 18: Stage Progression

- [ ] Implement `CampaignProgressionService`:
  - On scenario instance completion → check if all prerequisite stages for next stage are met.
  - If prerequisites met → automatically launch next stage's scenario for the same team.
  - Deliver narrative intro inject for the unlocked stage.
- [ ] Implement `GET /campaigns/{id}/progress` — per-team progress summary.
- [ ] Implement `campaign.yaml` import: parse and validate campaign files, load stages.
- [ ] Tests: enroll team → complete stage 1 → verify stage 2 auto-launches.

**Phase 6 Exit Criteria:**
- A full 3-stage campaign can be run from enrollment through completion.
- Stage auto-progression works correctly.
- Campaign progress is visible to instructors.

---

## Phase 7: Frontend (Next.js)

**Goal:** A functional web UI for all V1 features. Prioritize student workflow, then instructor workflow.

### Week 19: Auth + Layout

- [ ] Login page, logout.
- [ ] JWT token management (stored in httpOnly cookie via Next.js API route that proxies to FastAPI).
- [ ] Role-based layout: student sidebar vs. instructor sidebar.
- [ ] Protected route middleware (Next.js App Router).

### Week 20: Student — Scenario + Incident View

- [ ] Student dashboard: active scenario instances, due dates.
- [ ] Scenario detail: briefing, narrative injects (polled every 30s), assigned endpoints.
- [ ] Incident detail: status, severity, assigned alerts, evidence list, case notes.
- [ ] Alert list with filters (agent, level, acknowledged).
- [ ] Alert acknowledge + link to incident UI.
- [ ] Endpoint list with isolate/restore buttons.

### Week 21: Student — Evidence + Notes + Report

- [ ] Evidence collection form (type selector, text/file input, link to alert).
- [ ] Case notes text editor.
- [ ] Incident report builder: section-by-section form, autosave (debounced PUT).
- [ ] Timeline editor: add/edit/delete timeline events.
- [ ] IOC table: add/remove IOC rows.
- [ ] Affected assets table.
- [ ] Report submit with confirmation modal.

### Week 22: Instructor Views

- [ ] Instructor dashboard: course overview, active scenarios, pending reports to grade.
- [ ] Scenario library: browse, publish/unpublish, launch dialog.
- [ ] Launch scenario modal: select team/student, set due date, override config.
- [ ] Scenario instance monitor: team progress, alert activity, decision log.
- [ ] Report grading UI: split view (report | rubric), per-criterion scoring, feedback text, submit grade.
- [ ] Wazuh status panel: connectivity, agent list, manual sync buttons.

**Phase 7 Exit Criteria:**
- A student can complete a full scenario (alerts → evidence → report → submit) via the UI.
- An instructor can launch a scenario, monitor a student, and grade a report.
- No console errors on critical paths.

---

## Phase 8: Hardening

**Goal:** Production-ready. Security audited. Documented.

### Week 23: Security & Performance

- [ ] Security audit:
  - Review all endpoints for missing role checks.
  - Verify IDOR (Insecure Direct Object Reference) protections — students cannot access other teams' incidents.
  - CSRF protection on state-mutating endpoints.
  - Rate limiting verified under load.
  - File upload validation (type, size limits, virus scan stub).
- [ ] Performance:
  - Add `EXPLAIN ANALYZE` on the 5 heaviest queries; add indexes where needed.
  - Enable PostgreSQL connection pooling (`pgbouncer` or SQLAlchemy pool tuning).
  - Add Redis caching for heavy read endpoints (endpoint list, scenario library).
- [ ] Error handling: ensure all unhandled exceptions are caught and return a structured 500 response with a request ID.

### Week 24: Production Configuration + Ops

- [ ] `docker-compose.prod.yml`: adds Nginx, sets resource limits, disables debug mode.
- [ ] Nginx config: TLS termination, proxy to Next.js and FastAPI, security headers (HSTS, CSP, X-Frame-Options).
- [ ] Automated database backup: `pg_dump` cron job to a named volume.
- [ ] Health check endpoints: `GET /api/health` (FastAPI + DB + Redis status).
- [ ] Structured JSON logging: all backend logs emit JSON with `request_id`, `user_id`, `duration_ms`.
- [ ] `.env.example` is accurate and complete.
- [ ] Deployment runbook: `DEPLOY.md` documents the exact steps to deploy from scratch and update.
- [ ] Smoke test: fresh `docker compose up` on a clean machine, run through full student → instructor workflow manually.

**Phase 8 Exit Criteria:**
- No student can access another student's data.
- Deployment works from a clean server with one `docker compose up -d`.
- Backup cron is active.
- All services have health checks.

---

## V2 Backlog (Not In V1 Scope)

The following are intentionally deferred. Document here so they are not forgotten.

| Feature | Reason Deferred |
|---|---|
| WebSocket real-time alerts | Polling is sufficient for V1; WebSocket adds operational complexity |
| Real endpoint isolation via Wazuh Active Response | Requires careful safety controls and Wazuh config |
| AI-generated narrative injects / personas | Requires LLM integration design and cost control |
| Multi-tenant SaaS (multiple orgs, billing) | Scope beyond one institution |
| SOAR-style automated playbooks | Complex rules engine; manual decision-making is more educational in V1 |
| Mobile UI | Desktop-first for analyst work |
| LDAP/SSO authentication | Nice-to-have; JWT is sufficient for a single institution |
| Public scenario marketplace / sharing | Requires trust/review process |
| Student self-registration | Manual instructor enrollment is safer for academic settings |

---

## Technology Version Pins

Track these when starting implementation. Pin to specific versions to avoid drift.

| Package | Version |
|---|---|
| Python | 3.12 |
| FastAPI | 0.115.x |
| SQLAlchemy | 2.0.x |
| Alembic | 1.13.x |
| Pydantic | 2.x |
| Celery | 5.4.x |
| python-jose | 3.3.x |
| asyncpg | 0.29.x |
| opensearch-py | 2.7.x |
| Node.js | 22 LTS |
| Next.js | 14.x |
| TypeScript | 5.x |
| PostgreSQL | 16 |
| Redis | 7.2 |
| Nginx | 1.27 |
