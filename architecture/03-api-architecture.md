# API Architecture

## Design Principles

- **REST over HTTP/JSON** — no GraphQL in V1. Simple and debuggable.
- **Versioned from day one** — all routes under `/api/v1/`. Version 2 can coexist when needed.
- **Role-enforced at route level** — FastAPI dependency injection enforces role requirements per endpoint.
- **Auto-documented** — FastAPI generates OpenAPI 3.1 docs at `/api/docs` and `/api/redoc`.
- **Consistent error format** — all errors return `{ "detail": "message", "code": "ERROR_CODE" }`.
- **Pagination** — list endpoints use cursor-based pagination: `?limit=50&cursor=<uuid>`.

---

## Project Structure (FastAPI)

```
backend/app/
├── main.py                  # FastAPI app factory, router registration, middleware
├── config.py                # Settings via pydantic-settings (reads from env)
├── database.py              # Async SQLAlchemy engine and session factory
│
├── api/
│   └── v1/
│       ├── router.py        # Aggregates all v1 routers
│       ├── auth.py
│       ├── users.py
│       ├── organizations.py
│       ├── courses.py
│       ├── teams.py
│       ├── scenarios.py
│       ├── scenario_instances.py
│       ├── incidents.py
│       ├── alerts.py
│       ├── endpoints.py
│       ├── evidence.py
│       ├── case_notes.py
│       ├── reports.py
│       ├── grades.py
│       ├── campaigns.py
│       └── wazuh.py         # Instructor-facing Wazuh proxy/status endpoints
│
├── models/                  # SQLAlchemy ORM models
├── schemas/                 # Pydantic request/response schemas
├── crud/                    # Database access functions
├── services/                # Business logic layer
│   ├── auth_service.py
│   ├── incident_service.py
│   ├── report_service.py
│   ├── grading_service.py
│   └── scenario_service.py
│
├── integrations/
│   └── wazuh/
│       ├── client.py        # HTTP client for Wazuh Manager + Indexer APIs
│       ├── normalizer.py    # Maps Wazuh alert fields → Alert schema
│       └── simulator.py     # Simulated alert injection for offline scenarios
│
├── workers/                 # Celery tasks
│   ├── celery_app.py
│   ├── alert_poller.py
│   ├── agent_sync.py
│   └── scenario_tasks.py
│
└── dependencies/
    ├── auth.py              # get_current_user, require_role dependencies
    └── pagination.py
```

---

## Authentication Endpoints

```
POST   /api/v1/auth/login          Student or instructor login
POST   /api/v1/auth/logout         Invalidate tokens
POST   /api/v1/auth/refresh        Issue new access token from refresh token
GET    /api/v1/auth/me             Current user profile
PUT    /api/v1/auth/me/password    Change own password
```

### Login Request / Response

```json
POST /api/v1/auth/login
{
  "email": "jsmith@bmg.example.com",
  "password": "..."
}

Response 200:
{
  "user": {
    "id": "uuid",
    "email": "jsmith@bmg.example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "role": "student"
  },
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

Cookies set: `access_token` (15 min), `refresh_token` (7 days). Both `httpOnly`, `Secure`, `SameSite=Strict`.

---

## User Endpoints

```
GET    /api/v1/users/              List users [admin, instructor]
POST   /api/v1/users/             Create user [admin]
GET    /api/v1/users/{id}         Get user [admin, instructor, self]
PUT    /api/v1/users/{id}         Update user [admin, self]
DELETE /api/v1/users/{id}         Deactivate user [admin]
GET    /api/v1/users/{id}/enrollments   Student course enrollments
GET    /api/v1/users/{id}/decisions     Student decision history [instructor, self]
```

---

## Organization Endpoints

```
GET    /api/v1/organizations/          List [admin]
POST   /api/v1/organizations/          Create [admin]
GET    /api/v1/organizations/{id}      Get [admin, instructor]
PUT    /api/v1/organizations/{id}      Update [admin]
```

---

## Course Endpoints

```
GET    /api/v1/courses/                    List courses (filtered by role)
POST   /api/v1/courses/                    Create [instructor, admin]
GET    /api/v1/courses/{id}               Get course
PUT    /api/v1/courses/{id}               Update [instructor (own), admin]
DELETE /api/v1/courses/{id}               Archive [admin]
GET    /api/v1/courses/{id}/students      Student roster [instructor, admin]
POST   /api/v1/courses/{id}/enroll        Enroll student [instructor, admin]
DELETE /api/v1/courses/{id}/students/{uid}  Remove student [instructor, admin]
GET    /api/v1/courses/{id}/teams         List teams
GET    /api/v1/courses/{id}/scenarios     Scenario instances in this course
```

---

## Team Endpoints

```
GET    /api/v1/teams/                      List [instructor, admin]
POST   /api/v1/teams/                      Create [instructor, admin]
GET    /api/v1/teams/{id}                 Get team
PUT    /api/v1/teams/{id}                 Update [instructor, admin]
DELETE /api/v1/teams/{id}                 Delete [instructor, admin]
POST   /api/v1/teams/{id}/members         Add member
DELETE /api/v1/teams/{id}/members/{uid}   Remove member
```

---

## Scenario Endpoints

```
GET    /api/v1/scenarios/              Scenario library [instructor, admin]
POST   /api/v1/scenarios/             Create scenario [instructor, admin]
GET    /api/v1/scenarios/{id}         Get scenario detail
PUT    /api/v1/scenarios/{id}         Update [instructor (own), admin]
DELETE /api/v1/scenarios/{id}         Delete (if no instances) [admin]
POST   /api/v1/scenarios/{id}/publish Toggle published state [instructor, admin]
POST   /api/v1/scenarios/validate     Validate a YAML scenario file before saving
```

---

## Scenario Instance Endpoints

```
GET    /api/v1/scenario-instances/         List [role-filtered]
POST   /api/v1/scenario-instances/         Launch scenario [instructor, admin]
GET    /api/v1/scenario-instances/{id}    Get instance + progress
PUT    /api/v1/scenario-instances/{id}    Update (status, due_at) [instructor, admin]
DELETE /api/v1/scenario-instances/{id}    Archive [admin]
GET    /api/v1/scenario-instances/{id}/progress   Student progress summary
GET    /api/v1/scenario-instances/{id}/endpoints  Assigned endpoints
GET    /api/v1/scenario-instances/{id}/decisions  All student decisions [instructor]
```

### Launch Scenario Request

```json
POST /api/v1/scenario-instances/
{
  "scenario_id": "uuid",
  "course_id": "uuid",
  "team_id": "uuid",          // or "assigned_to": "uuid"
  "due_at": "2025-11-01T23:59:00Z",
  "runtime_config": {
    "auto_create_incident": true,
    "alert_level_threshold": 7
  }
}
```

---

## Incident Endpoints

```
GET    /api/v1/incidents/                       List [role-filtered]
POST   /api/v1/incidents/                       Create manually [instructor, admin]
GET    /api/v1/incidents/{id}                  Get incident
PUT    /api/v1/incidents/{id}                  Update (title, severity, status, assigned_to)
PUT    /api/v1/incidents/{id}/status           Change status with timestamp recording
POST   /api/v1/incidents/{id}/assign           Assign to user
GET    /api/v1/incidents/{id}/timeline         Chronological event timeline
```

### Status Transition Rules

```
open → investigating → contained → resolved → closed

Any status → closed (instructor only)
Backwards transitions require instructor role.
```

Status changes automatically write a `student_decisions` record of type `severity_change` or record to `incident` timestamps (`contained_at`, `resolved_at`, etc.).

---

## Alert Endpoints

```
GET    /api/v1/alerts/                         List alerts [role-filtered by scenario]
GET    /api/v1/alerts/{id}                    Get alert detail (including raw_data)
POST   /api/v1/alerts/{id}/acknowledge        Acknowledge alert (writes decision record)
POST   /api/v1/alerts/{id}/link               Link to incident
DELETE /api/v1/alerts/{id}/link               Unlink from incident [instructor]
GET    /api/v1/alerts/unassigned              Unlinked alerts for current scenario instances
```

### List Alerts Query Parameters

```
?scenario_instance_id=uuid
?incident_id=uuid
?rule_level_min=5
?agent_name=BMG-FIN-WS01
?is_acknowledged=false
?from=2025-10-01T00:00:00Z
?to=2025-10-02T00:00:00Z
?limit=50&cursor=uuid
```

---

## Endpoint (Workstation) Endpoints

```
GET    /api/v1/endpoints/                     List endpoints [role-filtered]
GET    /api/v1/endpoints/{id}                Get endpoint detail + agent status
PUT    /api/v1/endpoints/{id}                Update tags/labels [instructor, admin]
GET    /api/v1/endpoints/{id}/alerts         Alerts from this endpoint
POST   /api/v1/endpoints/{id}/isolate        Simulate isolation decision (writes decision record)
POST   /api/v1/endpoints/{id}/restore        Simulate restoration (writes decision record)
```

Note: `isolate` and `restore` are **simulation actions** — they do not call the real Wazuh active response API in V1. They update the endpoint `status` field and log a `student_decisions` record. Real isolation can be added in V2.

---

## Evidence Endpoints

```
GET    /api/v1/incidents/{id}/evidence       List evidence items
POST   /api/v1/incidents/{id}/evidence       Create evidence item
GET    /api/v1/evidence/{id}                Get evidence item
PUT    /api/v1/evidence/{id}                Update (title, description, is_key_evidence)
DELETE /api/v1/evidence/{id}               Delete [instructor or owner]
POST   /api/v1/evidence/{id}/upload        Upload file attachment (multipart/form-data)
```

### Create Evidence Request

```json
POST /api/v1/incidents/{id}/evidence
{
  "type": "log_extract",
  "title": "Suspicious PowerShell execution — BMG-FIN-WS01",
  "description": "PowerShell spawned by winword.exe at 09:14 UTC",
  "content": "...",
  "source_alert_id": "uuid",
  "source_endpoint_id": "uuid",
  "is_key_evidence": true
}
```

---

## Case Note Endpoints

```
GET    /api/v1/incidents/{id}/notes         List notes (excludes private unless instructor)
POST   /api/v1/incidents/{id}/notes         Add note
PUT    /api/v1/notes/{id}                   Edit note (owner only, within 15 min)
DELETE /api/v1/notes/{id}                  Delete [instructor or owner]
PUT    /api/v1/notes/{id}/pin              Toggle pinned [instructor]
```

---

## Report Endpoints

```
GET    /api/v1/incidents/{id}/report        Get report (creates draft if none exists)
PUT    /api/v1/reports/{id}                Autosave report sections
POST   /api/v1/reports/{id}/submit         Submit for grading (locks report)
GET    /api/v1/reports/                     List [instructor: all; student: own]
```

### Report Update Request (partial — all fields optional)

```json
PUT /api/v1/reports/{id}
{
  "executive_summary": "On October 14, 2025, BMG's Finance department...",
  "timeline": [
    {
      "timestamp": "2025-10-14T09:14:00Z",
      "event": "Suspicious PowerShell execution detected",
      "source": "Wazuh Alert #31101",
      "alert_id": "uuid"
    }
  ],
  "iocs": [
    { "type": "file_hash", "value": "e3b0c44298fc1c149afb...", "context": "Dropped payload" },
    { "type": "ip_address", "value": "198.51.100.42", "context": "C2 callback" }
  ],
  "affected_assets": [
    { "hostname": "BMG-FIN-WS01", "ip": "10.0.1.55", "role": "Finance Workstation", "impact": "Compromised" }
  ],
  "containment_actions": [
    { "action": "Isolated BMG-FIN-WS01 from network", "timestamp": "2025-10-14T09:45:00Z" }
  ],
  "recommendations": "Implement application whitelisting..."
}
```

---

## Grade Endpoints

```
GET    /api/v1/reports/{id}/grade          Get grade (instructor or report owner)
POST   /api/v1/reports/{id}/grade          Submit grade [instructor]
PUT    /api/v1/grades/{id}                 Update grade [instructor]
GET    /api/v1/scenario-instances/{id}/grades   All grades for a scenario [instructor]
```

### Grade Submission Request

```json
POST /api/v1/reports/{id}/grade
{
  "score": 87.5,
  "max_score": 100,
  "rubric_scores": {
    "executive_summary": { "score": 18, "max": 20, "feedback": "Clear and concise." },
    "timeline":          { "score": 22, "max": 25, "feedback": "Missing the initial phishing email event." },
    "iocs":              { "score": 15, "max": 15, "feedback": "All IOCs identified." },
    "containment":       { "score": 17, "max": 20, "feedback": "Isolation was timely but not documented." },
    "recommendations":   { "score": 15, "max": 20, "feedback": "Recommendations were generic." }
  },
  "overall_feedback": "Good investigation overall. Work on documenting decisions in real time."
}
```

---

## Campaign Endpoints

```
GET    /api/v1/campaigns/                      List [role-filtered]
POST   /api/v1/campaigns/                      Create [instructor, admin]
GET    /api/v1/campaigns/{id}                 Get campaign + stages
PUT    /api/v1/campaigns/{id}                 Update [instructor (own), admin]
GET    /api/v1/campaigns/{id}/stages          List stages
POST   /api/v1/campaigns/{id}/stages          Add stage
PUT    /api/v1/campaigns/{id}/stages/{sid}    Update stage
DELETE /api/v1/campaigns/{id}/stages/{sid}    Remove stage
POST   /api/v1/campaigns/{id}/enroll          Enroll team/student
GET    /api/v1/campaigns/{id}/progress        Enrollment progress [instructor]
```

---

## Wazuh Status Endpoints (Instructor Only)

```
GET    /api/v1/wazuh/health            Wazuh API connectivity status
GET    /api/v1/wazuh/agents            Raw agent list from Wazuh
POST   /api/v1/wazuh/sync/agents       Trigger immediate agent sync
POST   /api/v1/wazuh/sync/alerts       Trigger immediate alert poll
GET    /api/v1/wazuh/rules/{id}        Look up a Wazuh rule by ID
```

These endpoints exist so instructors can verify Wazuh connectivity without leaving the platform.

---

## Standard Error Responses

| HTTP Code | Scenario |
|---|---|
| 400 | Validation error, bad request body |
| 401 | Missing or expired token |
| 403 | Valid token but insufficient role |
| 404 | Resource not found |
| 409 | Conflict (duplicate, invalid state transition) |
| 422 | Pydantic validation error |
| 500 | Unhandled server error |

```json
{
  "detail": "Cannot submit a report with an empty executive summary.",
  "code": "REPORT_INCOMPLETE"
}
```

---

## Middleware Stack

Applied in order:

1. **CORS** — restricts to configured frontend origin.
2. **Request ID** — attaches `X-Request-ID` header for log correlation.
3. **Auth** — validates JWT on protected routes (FastAPI dependency, not global middleware).
4. **Rate limiting** — Redis-backed, per-user: 60 req/min for students, 200 req/min for instructors.
5. **Audit logging** — writes to structured log file for all mutating operations (POST/PUT/DELETE).

---

## WebSocket Support (V1 Limited)

V1 does not implement WebSocket for real-time alert push. Instead, the frontend polls:

- `GET /api/v1/alerts/?scenario_instance_id=X&is_acknowledged=false` every 30 seconds.
- `GET /api/v1/incidents/{id}` when the student is on the incident detail page.

Real-time WebSocket push (new alerts, incident status changes, instructor messages) is a V2 feature.
