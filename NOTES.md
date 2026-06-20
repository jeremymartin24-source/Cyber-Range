# CyberOps Range — Dev Notes

Running log of what's been built, bugs fixed, and how to operate the stack.

---

## What Is This

A self-hosted cybersecurity SOC simulator for training purposes. Students work through realistic incident response scenarios at a fictional company called **Buckeye Manufacturing Group (BMG)**. Instructors create scenarios and campaigns, enroll students, and grade their work.

**Not a CTF.** Simulates real SOC operations — triage, investigation, decision-making, evidence collection.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), Tailwind CSS |
| Backend | FastAPI (Python 3.12), async SQLAlchemy 2.0 |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7 |
| Background jobs | Celery 5 (worker + beat scheduler) |
| Auth | JWT cookies (httpOnly) |
| Migrations | Alembic |
| Package manager (Python) | uv |
| Container runtime | Docker Compose |

---

## Phases Built

### Phase 1–6 — Core Backend
- Database models: organizations, users, courses, teams, incidents, alerts, evidence, case notes, decisions
- Auth system: JWT login/logout, role-based access (admin / instructor / student)
- Scenario engine: YAML-defined scenarios, scenario runs, inject scheduling via Celery beat
- Campaign system: multi-scenario arcs with ordered progression

### Phase 7 — Next.js Frontend
- Login page, dashboard, incidents, alerts, scenarios, campaigns, courses, admin/users
- Shell layout with role-filtered sidebar navigation
- Server Components for data fetching, Client Components for interactivity

### Phase 8 — Security Hardening
- Rate limiting (slowapi), security headers middleware
- CORS config, httpOnly JWT cookies
- Input validation, production config flags

### Phase 9 — CI/CD
- GitHub Actions workflows for backend lint/test and frontend type-check
- Ruff linting, pytest with async support

### Phase 10 — Seed Data
- First-run seed script creates org, users, courses, scenarios, campaigns
- Idempotent — safe to re-run
- Seed runs automatically on `docker compose up`

### Phase 11 — Instructor Tooling
- Enrollment management (enroll/unenroll students)
- Grade entry and leaderboard
- Course detail views

---

## How to Run Locally

### Prerequisites
- Docker Desktop (with WSL2 backend on Windows)
- Git

### First run
```bash
cp .env.example .env
docker compose up --build
```

Build takes 3–5 minutes the first time. Watch for:
```
backend-1  | Seeding database... done
backend-1  | INFO: Application startup complete.
frontend-1 | ✓ Ready in Xs
```

### Subsequent starts
```bash
docker compose up
```

### URLs
- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/api/docs

### Seed credentials

| Role | Email | Password |
|---|---|---|
| Admin | admin@bmg.example.com | Admin1234! |
| Instructor | instructor@bmg.example.com | Instructor1234! |
| Student | alice@bmg.example.com | Student1234! |
| Student | bob@bmg.example.com | Student1234! |

> **CHANGE THE DEFAULT PASSWORDS IN ANY NON-LOCAL ENVIRONMENT.**

### Pulling code changes while running
```powershell
# In a second terminal (leave docker compose up running)
git pull

# If frontend files changed, restart the frontend container
docker compose restart frontend
```

### Stopping
```bash
docker compose down          # stop, keep database volume
docker compose down -v       # stop + wipe everything (fresh start)
```

---

## Bugs Fixed During First Run

### 1. `bcrypt` incompatibility
**Symptom:** `ValueError: password cannot be longer than 72 bytes` during seed  
**Cause:** `bcrypt >= 4.0` removed internal API that `passlib 1.7.4` depends on  
**Fix:** Pinned `bcrypt>=3.0,<4.0` in `backend/pyproject.toml`

### 2. Alembic migration enum conflicts
**Symptom:** `DuplicateObjectError: type "user_role" already exists`  
**Cause:** Migrations manually called `CREATE TYPE` AND SQLAlchemy's `create_table` also tried to create the same enum  
**Fix:** Removed all manual `op.execute("CREATE TYPE ...")` calls from migrations 001–005; let SQLAlchemy handle enum creation

### 3. Seed field name mismatch
**Symptom:** `TypeError: 'position' is an invalid keyword argument for CampaignScenarioEntry`  
**Cause:** Seed script used `position=` but the model field is `order_index`  
**Fix:** Updated seed script to use `order_index=`

### 4. Frontend Docker build: mixed React runtimes
**Symptom:** `TypeError: Cannot read properties of null (reading 'useContext')` during `npm run build`  
**Cause:** `ENV NODE_ENV=development` was in the Dockerfile `base` stage and leaked into the `builder` stage, causing Next.js to load both dev and prod React runtimes simultaneously  
**Fix:** Moved `ENV NODE_ENV=development` to only the `dev` stage in `frontend/Dockerfile`

### 5. `uv` package download timeouts
**Symptom:** `Failed to download sqlalchemy==2.0.51 — network timeout`  
**Cause:** Default uv HTTP timeout (30s) too short on slow connections  
**Fix:** Added `UV_HTTP_TIMEOUT=120` to `backend/Dockerfile`

### 6. API proxy routing (frontend → backend)
**Symptom:** Login returns "Network error — please try again"  
**Cause:** `next.config.js` rewrites used `NEXT_PUBLIC_API_URL=http://localhost:8000` as the proxy destination. Inside the Docker container, `localhost` points to the frontend container itself, not the backend.  
**Fix:** Changed rewrite destination to use `INTERNAL_API_URL=http://backend:8000`

### 7. `prestart.sh` CRLF line endings on Windows
**Symptom:** `exec ./prestart.sh: no such file or directory` on all backend containers  
**Cause:** Git on Windows converts LF → CRLF. The Linux kernel tries to exec `#!/bin/bash\r` (with carriage return) which doesn't exist.  
**Fix:** Added `.gitattributes` enforcing `eol=lf` for all shell scripts and text files  
**Note:** After pulling this fix, run `git rm --cached -r . && git reset --hard` once to re-normalize existing files

### 8. Seed race condition across containers
**Symptom:** `UniqueViolationError: duplicate key value violates unique constraint "users_email_key"` — backend crashes on startup  
**Cause:** `backend`, `worker`, and `beat` containers all run `prestart.sh` in parallel. All three tried to seed the database simultaneously; the first one wins and the other two crash.  
**Fix:** Added `SKIP_SEED=1` env var to `worker` and `beat` in `docker-compose.yml`. Modified `prestart.sh` to skip seed when that var is set. Only `backend` seeds now.

### 9. Users page crash
**Symptom:** `Error: users.map is not a function` on `/admin/users`  
**Cause:** `GET /api/v1/users` returns a paginated object `{items, total, limit, offset}` but the page called `.map()` directly on the response  
**Fix:** Updated `frontend/src/app/(app)/admin/users/page.tsx` to use `data.items`

---

## Known Quirks

### Hydration error overlay on login page
A React hydration mismatch error overlay appears in the browser when visiting the login page. This is caused by a password manager browser extension (LastPass, Bitwarden, etc.) injecting values into the form inputs before React hydrates. It's cosmetic — click X to dismiss and the app works normally. Does not appear in incognito mode.

### File watcher doesn't always fire on Windows
When you pull code changes, the Next.js dev server inside Docker doesn't always detect file changes from the Windows filesystem (WSL2 inotify limitation). If a change isn't reflected after a browser refresh, run `docker compose restart frontend`.

### Beat scheduler noise in logs
The `beat-1` container logs `Scheduler: Sending due task...` every 30–60 seconds. This is normal — it's scheduling background jobs for scenario inject processing and Wazuh alert polling.

---

## Role Permissions Summary

| Feature | Admin | Instructor | Student |
|---|:---:|:---:|:---:|
| Dashboard | ✓ | ✓ | ✓ |
| Incidents | ✓ | ✓ | ✓ |
| Alerts | ✓ | ✓ | ✓ |
| Scenarios | ✓ | ✓ | — |
| Campaigns | ✓ | ✓ | — |
| Courses | ✓ | ✓ | ✓ |
| Users (admin panel) | ✓ | — | — |

---

## Production Checklist (when you're ready to deploy)

- [ ] Set a real `SECRET_KEY` (long random string, not the example value)
- [ ] Change all seed passwords
- [ ] Set `JWT_COOKIE_SECURE=true` (requires HTTPS)
- [ ] Set `ALLOWED_ORIGINS` to your actual domain
- [ ] Set `WAZUH_VERIFY_TLS=true` if using real Wazuh
- [ ] Put the stack behind a reverse proxy (nginx/Caddy) with TLS
- [ ] Remove or restrict `/api/docs` and `/api/redoc` endpoints
