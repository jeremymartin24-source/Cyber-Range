# Database Architecture

## Overview

PostgreSQL 16 with SQLAlchemy 2 async ORM and Alembic migrations.

All primary keys are UUIDs (`gen_random_uuid()`). Timestamps are stored as `TIMESTAMPTZ` (UTC). Soft-deletes are not used — records are hard-deleted or status-flagged. JSONB columns are used where schema flexibility is needed (raw alert data, scenario configuration, grading rubrics).

---

## Entity Relationship Diagram

```
organizations
    │
    ├──< users (many users per org)
    │       │
    │       ├──< enrollments >──< courses (many-to-many)
    │       │
    │       └──< team_members >──< teams (many-to-many)
    │
    └──< courses
            │
            ├──< scenario_instances
            │       │
            │       ├──< incidents
            │       │       │
            │       │       ├──< incident_alerts >──< alerts
            │       │       ├──< evidence
            │       │       ├──< case_notes
            │       │       └──< reports
            │       │               └──< grades
            │       │
            │       └──< student_decisions
            │
            └──< campaign_enrollments >──< campaigns
                                              └──< campaign_stages
                                                      └── scenario_id → scenarios

endpoints (linked to scenario_instances via endpoint_assignments)
alerts (linked to incidents via incident_alerts)
scenarios (definition library, referenced by scenario_instances)
```

---

## Schema Definitions

### `organizations`

The top-level tenant. In V1 there is typically one organization: Buckeye Manufacturing Group.

```sql
CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) NOT NULL,
    slug        VARCHAR(100) NOT NULL UNIQUE,
    settings    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`settings` keys (example):
```json
{
  "branding": { "company_name": "Buckeye Manufacturing Group" },
  "wazuh_agent_prefix": "BMG-"
}
```

---

### `users`

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    role            VARCHAR(20)  NOT NULL CHECK (role IN ('admin','instructor','student')),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_organization ON users(organization_id);
CREATE INDEX idx_users_role ON users(role);
```

---

### `courses`

An academic course (e.g., "IST 4400 — Cybersecurity Operations, Fall 2025").

```sql
CREATE TABLE courses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    instructor_id   UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    semester        VARCHAR(20),   -- 'Fall', 'Spring', 'Summer'
    year            SMALLINT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### `enrollments`

Student membership in a course.

```sql
CREATE TABLE enrollments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id   UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    status      VARCHAR(20) NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','withdrawn','completed')),
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, course_id)
);
```

---

### `teams`

Optional grouping of students within a course for collaborative scenario work.

```sql
CREATE TABLE teams (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id   UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (course_id, name)
);

CREATE TABLE team_members (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id     UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        VARCHAR(20) NOT NULL DEFAULT 'analyst'
                    CHECK (role IN ('lead','analyst')),
    joined_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (team_id, user_id)
);
```

---

### `scenarios`

The scenario definition library. Scenarios are authored by instructors and stored as YAML files on disk. This table stores metadata and the parsed content for querying.

```sql
CREATE TABLE scenarios (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    created_by          UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title               VARCHAR(255) NOT NULL,
    description         TEXT,
    type                VARCHAR(30) NOT NULL
                            CHECK (type IN ('training_lab','incident_case','campaign_stage')),
    difficulty          VARCHAR(20) NOT NULL DEFAULT 'intermediate'
                            CHECK (difficulty IN ('beginner','intermediate','advanced')),
    estimated_duration  INT,            -- minutes
    tags                JSONB NOT NULL DEFAULT '[]',
    file_path           VARCHAR(500),   -- path inside /scenarios volume
    scenario_data       JSONB NOT NULL DEFAULT '{}',  -- full parsed YAML content
    is_published        BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_scenarios_type ON scenarios(type);
CREATE INDEX idx_scenarios_published ON scenarios(is_published);
CREATE INDEX idx_scenarios_tags ON scenarios USING GIN(tags);
```

---

### `scenario_instances`

A launched copy of a scenario assigned to a course + team/student. One scenario can be launched multiple times across courses or semesters.

```sql
CREATE TABLE scenario_instances (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id     UUID NOT NULL REFERENCES scenarios(id) ON DELETE RESTRICT,
    course_id       UUID NOT NULL REFERENCES courses(id) ON DELETE RESTRICT,
    launched_by     UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,

    -- Assignment target: team OR individual student (exactly one must be set)
    team_id         UUID REFERENCES teams(id) ON DELETE SET NULL,
    assigned_to     UUID REFERENCES users(id) ON DELETE SET NULL,

    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','active','paused','completed','graded','archived')),
    started_at      TIMESTAMPTZ,
    due_at          TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    runtime_config  JSONB NOT NULL DEFAULT '{}', -- instructor overrides at launch time
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CHECK (
        (team_id IS NOT NULL AND assigned_to IS NULL) OR
        (team_id IS NULL AND assigned_to IS NOT NULL)
    )
);

CREATE INDEX idx_si_course ON scenario_instances(course_id);
CREATE INDEX idx_si_status ON scenario_instances(status);
CREATE INDEX idx_si_team ON scenario_instances(team_id);
CREATE INDEX idx_si_user ON scenario_instances(assigned_to);
```

---

### `endpoints`

Wazuh agents / managed workstations visible within a scenario context.

```sql
CREATE TABLE endpoints (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    wazuh_agent_id  VARCHAR(20) NOT NULL,   -- Wazuh's numeric agent ID
    hostname        VARCHAR(255) NOT NULL,
    ip_address      INET,
    os_platform     VARCHAR(50),            -- 'windows', 'linux', 'macos'
    os_version      VARCHAR(100),
    agent_version   VARCHAR(50),
    status          VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active','offline','isolated','decommissioned')),
    last_seen_at    TIMESTAMPTZ,
    tags            JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, wazuh_agent_id)
);

CREATE INDEX idx_endpoints_hostname ON endpoints(hostname);
CREATE INDEX idx_endpoints_status ON endpoints(status);
CREATE INDEX idx_endpoints_org ON endpoints(organization_id);
```

### `endpoint_assignments`

Links endpoints to scenario instances (which endpoints are visible in a given scenario).

```sql
CREATE TABLE endpoint_assignments (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_instance_id UUID NOT NULL REFERENCES scenario_instances(id) ON DELETE CASCADE,
    endpoint_id          UUID NOT NULL REFERENCES endpoints(id) ON DELETE CASCADE,
    role_label           VARCHAR(100),  -- e.g., "Finance Workstation", "Domain Controller"
    UNIQUE (scenario_instance_id, endpoint_id)
);
```

---

### `incidents`

The central work object for students. Each scenario instance produces one or more incidents.

```sql
CREATE TABLE incidents (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_instance_id UUID NOT NULL REFERENCES scenario_instances(id) ON DELETE CASCADE,
    organization_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    incident_number      VARCHAR(30) NOT NULL UNIQUE,  -- e.g., INC-2025-0042
    title                VARCHAR(255) NOT NULL,
    description          TEXT,
    severity             VARCHAR(10) NOT NULL DEFAULT 'medium'
                             CHECK (severity IN ('critical','high','medium','low','informational')),
    status               VARCHAR(20) NOT NULL DEFAULT 'open'
                             CHECK (status IN ('open','investigating','contained','resolved','closed')),
    category             VARCHAR(50),   -- 'phishing','ransomware','insider_threat', etc.
    assigned_to          UUID REFERENCES users(id) ON DELETE SET NULL,
    team_id              UUID REFERENCES teams(id) ON DELETE SET NULL,
    detected_at          TIMESTAMPTZ,
    contained_at         TIMESTAMPTZ,
    resolved_at          TIMESTAMPTZ,
    closed_at            TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_incidents_scenario_instance ON incidents(scenario_instance_id);
CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_incidents_severity ON incidents(severity);
CREATE INDEX idx_incidents_team ON incidents(team_id);
```

Incident numbers are generated by a sequence:
```sql
CREATE SEQUENCE incident_seq START 1;
-- application builds: 'INC-' || to_char(now(), 'YYYY') || '-' || lpad(nextval('incident_seq')::text, 4, '0')
```

---

### `alerts`

Normalized alerts ingested from Wazuh (or injected as simulated alerts).

```sql
CREATE TABLE alerts (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    scenario_instance_id UUID REFERENCES scenario_instances(id) ON DELETE SET NULL,

    -- Wazuh identifiers
    wazuh_alert_id       VARCHAR(255) UNIQUE,  -- null for simulated alerts
    is_simulated         BOOLEAN NOT NULL DEFAULT false,

    -- Rule information
    rule_id              INT,
    rule_level           SMALLINT,
    rule_description     TEXT,
    rule_groups          JSONB NOT NULL DEFAULT '[]',

    -- Agent / endpoint
    agent_id             VARCHAR(20),
    agent_name           VARCHAR(255),
    endpoint_id          UUID REFERENCES endpoints(id) ON DELETE SET NULL,

    -- Alert body
    raw_data             JSONB NOT NULL DEFAULT '{}',
    timestamp            TIMESTAMPTZ NOT NULL,

    -- Student interaction
    is_acknowledged      BOOLEAN NOT NULL DEFAULT false,
    acknowledged_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_at      TIMESTAMPTZ,

    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_alerts_scenario_instance ON alerts(scenario_instance_id);
CREATE INDEX idx_alerts_timestamp ON alerts(timestamp DESC);
CREATE INDEX idx_alerts_rule_level ON alerts(rule_level);
CREATE INDEX idx_alerts_agent_name ON alerts(agent_name);
CREATE INDEX idx_alerts_wazuh_id ON alerts(wazuh_alert_id);
CREATE INDEX idx_alerts_raw_data ON alerts USING GIN(raw_data);
```

### `incident_alerts`

Links alerts to incidents (many-to-many: an alert can be linked to one incident; an incident has many alerts).

```sql
CREATE TABLE incident_alerts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    alert_id    UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    linked_by   UUID REFERENCES users(id) ON DELETE SET NULL,
    linked_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (incident_id, alert_id)
);
```

---

### `evidence`

Evidence collected by students during an investigation.

```sql
CREATE TABLE evidence (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id        UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    collected_by       UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,

    type               VARCHAR(50) NOT NULL
                           CHECK (type IN (
                               'screenshot','log_extract','alert_export',
                               'file_hash','network_capture','process_list',
                               'registry_key','email_header','other'
                           )),
    title              VARCHAR(255) NOT NULL,
    description        TEXT,
    content            TEXT,          -- raw text content
    structured_data    JSONB,         -- for structured evidence (hashes, IPs, etc.)
    file_path          VARCHAR(500),  -- uploaded file, if any
    file_size_bytes    BIGINT,

    -- Source traceability
    source_alert_id    UUID REFERENCES alerts(id) ON DELETE SET NULL,
    source_endpoint_id UUID REFERENCES endpoints(id) ON DELETE SET NULL,

    is_key_evidence    BOOLEAN NOT NULL DEFAULT false,
    collected_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_evidence_incident ON evidence(incident_id);
CREATE INDEX idx_evidence_type ON evidence(type);
```

---

### `case_notes`

Free-form notes written by students and instructors on an incident.

```sql
CREATE TABLE case_notes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    author_id   UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    content     TEXT NOT NULL,
    is_pinned   BOOLEAN NOT NULL DEFAULT false,
    is_private  BOOLEAN NOT NULL DEFAULT false,  -- instructor-only notes
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_case_notes_incident ON case_notes(incident_id);
```

---

### `reports`

The formal incident report submitted by students.

```sql
CREATE TABLE reports (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id          UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    scenario_instance_id UUID NOT NULL REFERENCES scenario_instances(id) ON DELETE CASCADE,
    author_id            UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    team_id              UUID REFERENCES teams(id) ON DELETE SET NULL,

    status               VARCHAR(20) NOT NULL DEFAULT 'draft'
                             CHECK (status IN ('draft','submitted','graded','returned')),

    -- Report sections (structured)
    executive_summary    TEXT,
    timeline             JSONB NOT NULL DEFAULT '[]',    -- [{timestamp, event, source}]
    affected_assets      JSONB NOT NULL DEFAULT '[]',    -- [{hostname, ip, role, impact}]
    iocs                 JSONB NOT NULL DEFAULT '[]',    -- [{type, value, context}]
    containment_actions  JSONB NOT NULL DEFAULT '[]',    -- [{action, timestamp, performed_by}]
    recovery_actions     JSONB NOT NULL DEFAULT '[]',    -- [{action, timestamp}]
    recommendations      TEXT,
    lessons_learned      TEXT,

    submitted_at         TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (scenario_instance_id, author_id)
);

CREATE INDEX idx_reports_incident ON reports(incident_id);
CREATE INDEX idx_reports_status ON reports(status);
```

---

### `grades`

Instructor grades for submitted reports.

```sql
CREATE TABLE grades (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id            UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    scenario_instance_id UUID NOT NULL REFERENCES scenario_instances(id) ON DELETE CASCADE,
    graded_by            UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    student_id           UUID REFERENCES users(id) ON DELETE SET NULL,
    team_id              UUID REFERENCES teams(id) ON DELETE SET NULL,

    score                NUMERIC(5,2) NOT NULL,
    max_score            NUMERIC(5,2) NOT NULL DEFAULT 100.00,
    rubric_scores        JSONB NOT NULL DEFAULT '{}',  -- { criterion_id: { score, feedback } }
    overall_feedback     TEXT,

    graded_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (report_id)
);
```

---

### `student_decisions`

Timestamped log of significant student actions during a scenario. Used for grading decision quality and providing a replay of the investigation.

```sql
CREATE TABLE student_decisions (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_instance_id UUID NOT NULL REFERENCES scenario_instances(id) ON DELETE CASCADE,
    incident_id          UUID REFERENCES incidents(id) ON DELETE SET NULL,
    user_id              UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,

    decision_type        VARCHAR(50) NOT NULL
                             CHECK (decision_type IN (
                                 'initial_triage',
                                 'severity_change',
                                 'alert_acknowledged',
                                 'alert_linked',
                                 'evidence_collected',
                                 'endpoint_isolated',
                                 'endpoint_restored',
                                 'user_account_disabled',
                                 'escalation',
                                 'note_added',
                                 'report_submitted',
                                 'other'
                             )),

    decision_data        JSONB NOT NULL DEFAULT '{}',  -- context-specific payload
    rationale            TEXT,   -- student's written justification (optional)

    -- Auto-scoring (optional, set by grading engine)
    auto_score           NUMERIC(5,2),
    auto_feedback        TEXT,

    decided_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_decisions_scenario_instance ON student_decisions(scenario_instance_id);
CREATE INDEX idx_decisions_user ON student_decisions(user_id);
CREATE INDEX idx_decisions_type ON student_decisions(decision_type);
CREATE INDEX idx_decisions_decided_at ON student_decisions(decided_at);
```

---

### `campaigns`

A multi-stage storyline that spans multiple scenarios over a semester.

```sql
CREATE TABLE campaigns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    course_id       UUID REFERENCES courses(id) ON DELETE SET NULL,
    created_by      UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    narrative       TEXT,  -- overall story context shown to students
    status          VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft','active','completed','archived')),
    start_date      DATE,
    end_date        DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `campaign_stages`

Each stage in a campaign maps to a scenario. Stages can have prerequisites.

```sql
CREATE TABLE campaign_stages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    scenario_id     UUID NOT NULL REFERENCES scenarios(id) ON DELETE RESTRICT,
    stage_number    SMALLINT NOT NULL,
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    narrative_intro TEXT,  -- story text shown when stage unlocks
    prerequisites   JSONB NOT NULL DEFAULT '[]',  -- [stage_id, ...] that must be completed
    unlock_conditions JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (campaign_id, stage_number)
);
```

### `campaign_enrollments`

Tracks which teams or students are enrolled in a campaign and their progress.

```sql
CREATE TABLE campaign_enrollments (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id          UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    team_id              UUID REFERENCES teams(id) ON DELETE CASCADE,
    user_id              UUID REFERENCES users(id) ON DELETE CASCADE,
    current_stage_number SMALLINT NOT NULL DEFAULT 1,
    status               VARCHAR(20) NOT NULL DEFAULT 'active'
                             CHECK (status IN ('active','paused','completed')),
    enrolled_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at         TIMESTAMPTZ,
    UNIQUE (campaign_id, team_id),
    CHECK (
        (team_id IS NOT NULL AND user_id IS NULL) OR
        (team_id IS NULL AND user_id IS NOT NULL)
    )
);
```

---

## Migration Strategy

- **Alembic** manages all schema changes.
- Each migration is a discrete, reversible Python file.
- Migrations run automatically on container start via a `prestart.sh` script that calls `alembic upgrade head`.
- Never edit migrations that have been applied to production — always add new ones.

## Indexing Strategy

- All foreign keys are indexed.
- `timestamp DESC` index on `alerts` supports the default time-sorted alert view.
- GIN indexes on JSONB columns used for query filters (`tags`, `raw_data`).
- `incident_number` is unique and indexed for lookup.
- `wazuh_alert_id` is unique to prevent duplicate ingestion.
