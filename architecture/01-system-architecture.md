# System Architecture

## Technology Stack

### Rationale Summary

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 14 (App Router) | SSR, TypeScript-first, large ecosystem, self-hostable |
| Backend API | FastAPI (Python) | Python dominates security tooling; Wazuh has a Python SDK; async-native; auto-generates OpenAPI docs |
| Database | PostgreSQL 16 | JSONB for flexible alert/scenario data, full-text search, proven reliability |
| Cache / Queue Broker | Redis 7 | Session cache, background job broker, rate-limit counters |
| Background Workers | Celery 5 | Wazuh polling, scheduled syncs, report generation |
| ORM | SQLAlchemy 2 (async) | Mature, async support via asyncpg, Alembic migrations |
| Auth | JWT (python-jose) | Stateless, self-hosted friendly; httpOnly cookies |
| Containerization | Docker + Docker Compose | Single developer, reproducible environments |

### Why FastAPI over Django or Express

- The Wazuh REST API and Indexer (OpenSearch) have Python SDKs and community libraries.
- Future AI/ML capabilities (alert triage scoring, anomaly detection) use Python.
- FastAPI gives async I/O with minimal boilerplate and zero-config OpenAPI documentation.
- Django is too opinionated; Express requires Python anyway for Wazuh work.

### Why Next.js over plain React or Remix

- App Router enables server components — pages requiring auth checks render server-side, reducing client exposure.
- API routes serve as a lightweight Backend-for-Frontend (BFF) when needed.
- File-based routing keeps the project simple for a single developer.
- Easily self-hosted via `next start` or a Node.js Docker image.

---

## Service Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CyberOps Range                              │
│                                                                     │
│  ┌────────────────────┐        ┌────────────────────────────────┐   │
│  │   Next.js 14       │        │         FastAPI                │   │
│  │   Frontend         │◄──────►│         Backend API            │   │
│  │   :3000            │  REST  │         :8000                  │   │
│  │                    │  /     │                                │   │
│  │  - Student UI      │  JWT   │  - Auth                       │   │
│  │  - Instructor UI   │        │  - Incidents                  │   │
│  │  - Scenario View   │        │  - Scenarios                  │   │
│  │  - Report Builder  │        │  - Reports                    │   │
│  │  - Alert Console   │        │  - Wazuh Proxy                │   │
│  └────────────────────┘        └──────────┬─────────────────────┘  │
│                                           │                         │
│              ┌────────────────────────────┼──────────────────────┐  │
│              │                            │                      │  │
│              ▼                            ▼                      ▼  │
│     ┌─────────────────┐      ┌──────────────────┐   ┌─────────────┐│
│     │  PostgreSQL 16  │      │    Redis 7        │   │   Celery    ││
│     │  :5432          │      │    :6379          │   │   Workers   ││
│     │                 │      │                   │   │             ││
│     │  Primary store  │      │  - JWT denylist   │   │  - Alert    ││
│     │  for all domain │      │  - Session cache  │   │    polling  ││
│     │  data           │      │  - Rate limits    │   │  - Agent    ││
│     │                 │      │  - Job broker     │   │    sync     ││
│     └─────────────────┘      └──────────────────┘   └──────┬──────┘│
│                                                             │       │
└─────────────────────────────────────────────────────────────┼───────┘
                                                              │
                                              ┌───────────────▼────────┐
                                              │    Wazuh Server        │
                                              │    (External / VPN)    │
                                              │                        │
                                              │  REST API  :55000      │
                                              │  Indexer   :9200       │
                                              │  (OpenSearch)          │
                                              └────────────────────────┘
```

---

## Docker Compose Layout

```
cyber-range/
├── docker-compose.yml          # Development
├── docker-compose.prod.yml     # Production overrides
├── .env.example
│
├── backend/                    # FastAPI application
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── app/
│
├── frontend/                   # Next.js application
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│
├── worker/                     # Celery worker (shares backend image)
│   └── Dockerfile
│
├── nginx/                      # Reverse proxy (production)
│   └── nginx.conf
│
├── scenarios/                  # Scenario YAML files (volume-mounted)
│   ├── training-labs/
│   ├── incident-cases/
│   └── campaigns/
│
└── architecture/               # This directory
```

### docker-compose.yml Services

```yaml
services:
  db:          # PostgreSQL 16
  redis:       # Redis 7 Alpine
  backend:     # FastAPI on uvicorn
  worker:      # Celery worker (same image as backend)
  beat:        # Celery beat scheduler
  frontend:    # Next.js
  nginx:       # Reverse proxy (prod only)
```

---

## Authentication Model

```
POST /api/v1/auth/login
  → Returns: access_token (15 min) + refresh_token (7 days)
  → Both tokens delivered as httpOnly, Secure, SameSite=Strict cookies
  → access_token also returned in response body for API clients

POST /api/v1/auth/refresh
  → Validates refresh_token cookie
  → Issues new access_token

POST /api/v1/auth/logout
  → Adds access_token to Redis denylist (TTL = remaining token lifetime)
  → Clears cookies
```

### Roles

| Role | Capabilities |
|---|---|
| `student` | Access assigned scenarios, incidents, evidence, reports |
| `instructor` | All student capabilities + create/launch scenarios, review/grade reports, monitor all students |
| `admin` | All capabilities + manage organizations, users, system configuration |

Role is stored on the `users` table and encoded in the JWT payload.

---

## Wazuh Integration Architecture

Students never interact with Wazuh directly. CyberOps Range acts as a translation layer: consuming Wazuh data, filtering it through scenario context, and presenting it as platform-native alerts and endpoint data.

### Integration Components

#### 1. Wazuh API Client (`backend/app/integrations/wazuh/`)

A thin Python wrapper around the Wazuh Manager REST API (port 55000) and the Wazuh Indexer (OpenSearch, port 9200). Handles authentication (API key or basic auth), TLS, and retry logic.

#### 2. Alert Ingestion Pipeline

```
Wazuh Indexer (OpenSearch)
        │
        │  Celery beat polls every 30 seconds
        ▼
WazuhAlertPoller (Celery task)
        │
        │  Filters by: scenario_instance agent names,
        │              rule level threshold,
        │              time window
        ▼
AlertNormalizer
        │  Maps Wazuh alert fields → CyberOps Range Alert schema
        │  Deduplicates (wazuh_alert_id uniqueness)
        ▼
PostgreSQL alerts table
        │
        │  Correlation engine runs after insert
        ▼
AlertCorrelationEngine
        │  Matches alert agent/rule to open incident_scenario_instances
        │  Links alert to incident if match found
        ▼
incident_alerts join table
```

#### 3. Agent / Endpoint Synchronization

```
Wazuh Manager API (/agents endpoint)
        │
        │  Celery beat polls every 5 minutes
        ▼
AgentSyncTask
        │  Upserts agent records into endpoints table
        │  Updates: status, last_seen, ip_address, os_version
        ▼
PostgreSQL endpoints table
```

#### 4. Alert-to-Incident Correlation Rules

Correlation is configured per scenario in the scenario YAML file (`wazuh_configuration.alert_filters`). When an alert arrives:

1. Find all active `scenario_instances` that include the alert's agent name.
2. Check if the alert's `rule_id` or `rule_groups` match the scenario's filter list.
3. If matched, insert a row in `incident_alerts` linking the alert to the scenario's incident.
4. If no open incident exists for that scenario instance, create one automatically (configurable per scenario).

#### 5. Simulated Alert Injection

For scenarios that run without a live Wazuh environment (training labs), the scenario YAML defines `simulated_alerts`. A Celery task injects these as synthetic alert records at the specified `inject_at` offset from scenario start time.

---

## Environment Configuration

All configuration is via environment variables loaded from `.env`.

```
# Application
SECRET_KEY=
ENVIRONMENT=development|production
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/cyberops

# Redis
REDIS_URL=redis://redis:6379/0

# Wazuh
WAZUH_MANAGER_URL=https://wazuh-manager:55000
WAZUH_INDEXER_URL=https://wazuh-manager:9200
WAZUH_API_USER=
WAZUH_API_PASSWORD=
WAZUH_VERIFY_TLS=false  # set true in production with valid cert

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# JWT
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Alerts
ALERT_POLL_INTERVAL_SECONDS=30
AGENT_SYNC_INTERVAL_SECONDS=300
WAZUH_ALERT_LEVEL_THRESHOLD=5
```

---

## Production Deployment

Target: single Linux server (Ubuntu 22.04 LTS), self-hosted.

```
Internet → Nginx (443/TLS) → Next.js (3000)
                           → FastAPI (8000)
```

- TLS via Let's Encrypt (certbot) or self-signed for isolated lab environments.
- Docker volumes for PostgreSQL data persistence.
- Redis with `appendonly yes` for durability.
- Backups: `pg_dump` via cron to a mounted backup volume.
- No Kubernetes required for V1. Single `docker compose up -d` deployment.
