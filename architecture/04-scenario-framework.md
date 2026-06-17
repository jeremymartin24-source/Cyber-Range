# Scenario Framework

## Design Decisions

### File Format: YAML

Scenarios are stored as **YAML files** on disk (version-controlled in the `scenarios/` directory), with a **database record** holding parsed metadata for querying.

**Why YAML over JSON or pure database:**
- Human-readable and easy to author without tooling.
- Supports multi-line strings (narrative text, briefings).
- Version-controllable — instructors can diff scenario changes in git.
- The parsed `scenario_data` JSONB field in PostgreSQL enables queries without file I/O at runtime.

**Why not pure database:**
- Scenario content (narrative, injects, rubrics) is complex nested structure that is painful to edit via SQL.
- YAML files can be shared, reviewed in GitHub, and contributed as a library.

**Hybrid approach:**
- Canonical source: YAML file in `/scenarios/` volume.
- Runtime source: `scenarios.scenario_data` JSONB column (populated on import/save).
- When a YAML file changes on disk, the instructor triggers a re-import via the API.

---

## Scenario Types

The same engine handles all three types. Type controls which fields are required and how the engine interprets the scenario at runtime.

| Type | Description | Key Differences |
|---|---|---|
| `training_lab` | Short, focused, single-skill exercise | May use simulated alerts only; no live Wazuh required |
| `incident_case` | Full incident investigation with evidence, report, and grading | Requires report submission; auto-creates an incident |
| `campaign_stage` | One chapter in a multi-stage campaign | Shares context with prior stages; narrative continuity |

---

## Scenario File Structure

### File Location Convention

```
scenarios/
├── training-labs/
│   └── tl-001-alert-triage/
│       └── scenario.yaml
├── incident-cases/
│   └── ic-001-phishing-finance/
│       └── scenario.yaml
└── campaigns/
    └── bmg-apt-siege/
        ├── campaign.yaml
        ├── stage-01-initial-access/
        │   └── scenario.yaml
        ├── stage-02-lateral-movement/
        │   └── scenario.yaml
        └── stage-03-data-exfiltration/
            └── scenario.yaml
```

---

## Scenario YAML Specification

### Full Field Reference

```yaml
# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO METADATA
# ─────────────────────────────────────────────────────────────────────────────
id: ic-001-phishing-finance        # Unique scenario identifier (kebab-case)
version: "1.2"                     # Scenario file format version
type: incident_case                # training_lab | incident_case | campaign_stage

metadata:
  title: "Phishing Attack — Finance Department"
  description: >
    A targeted phishing email delivered to three Finance Department users
    results in malware execution and credential harvesting. Students must
    triage alerts, isolate affected endpoints, collect evidence, and
    produce a formal incident report.
  difficulty: intermediate           # beginner | intermediate | advanced
  estimated_duration: 90            # minutes
  tags:
    - phishing
    - malware
    - credential-harvesting
    - windows
  learning_objectives:
    - Identify phishing indicators in email headers and Wazuh alerts
    - Correlate multi-endpoint alerts to a single incident
    - Make and document an endpoint isolation decision
    - Write an executive summary appropriate for non-technical leadership

  author: "instructor@bmg.example.com"
  created: "2025-08-01"
  last_updated: "2025-10-01"

# ─────────────────────────────────────────────────────────────────────────────
# FICTIONAL CONTEXT
# Shown to students to establish the scenario setting
# ─────────────────────────────────────────────────────────────────────────────
fiction:
  organization: "Buckeye Manufacturing Group"
  student_role: "Security Analyst — BMG SOC"
  date_context: "Monday, October 14, 2025 — 09:15 AM EST"
  department_affected: "Finance Department (Columbus, OH)"

narrative:
  briefing: |
    You've just started your shift and your colleague flagged something before
    heading to a meeting. Three members of the Finance Department received what
    appears to be a vendor invoice email this morning. One of them opened an
    attachment at approximately 09:12 AM. You're seeing elevated alert activity
    on endpoint BMG-FIN-WS01.

    Triage the alerts, determine the scope of impact, contain the threat, and
    document your investigation.

  injects:
    # Timed narrative updates delivered to students during the scenario
    - at: "T+20m"
      type: manager_message
      from: "SOC Manager"
      subject: "Status Update Request"
      content: |
        Hey — CFO is asking if we need to notify the board. Can you give me
        a quick status in the next 10 minutes? At minimum tell me: confirmed
        or unconfirmed, how many machines, and whether we've contained it.

    - at: "T+45m"
      type: system_notification
      content: "A second Finance workstation (BMG-FIN-WS02) has started generating alerts."

    - at: "T+60m"
      type: manager_message
      from: "IT Help Desk"
      subject: "User complaint"
      content: |
        User jdoe@bmg.com just called saying their computer is running slow
        and they can't access the network share. They mentioned they opened
        an invoice email this morning. Should I send them to you?

# ─────────────────────────────────────────────────────────────────────────────
# WAZUH CONFIGURATION
# Controls how real and simulated alerts flow into this scenario
# ─────────────────────────────────────────────────────────────────────────────
wazuh:
  # Filter real Wazuh alerts for this scenario
  # Only alerts matching ALL conditions below are ingested
  alert_filters:
    agent_names:
      - BMG-FIN-WS01
      - BMG-FIN-WS02
    rule_level_min: 7
    rule_ids_include: []      # empty = all rules passing level filter
    rule_ids_exclude:
      - 31000                 # exclude noisy rule
    rule_groups_include:
      - syscheck
      - windows
      - web

  # Simulated alerts injected regardless of live Wazuh status
  # Use for offline/demo environments or to guarantee specific events fire
  simulated_alerts:
    - inject_at: "T+2m"
      rule_id: 92200
      rule_level: 12
      rule_description: "PowerShell executed by Microsoft Word"
      rule_groups: ["windows", "powershell", "attack"]
      agent_name: "BMG-FIN-WS01"
      data:
        win:
          eventdata:
            parentImage: "C:\\Program Files\\Microsoft Office\\WINWORD.EXE"
            image: "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
            commandLine: "powershell -nop -w hidden -enc <base64>"
            user: "bmg\\j.doe"
            utcTime: "2025-10-14T09:14:23.000Z"

    - inject_at: "T+8m"
      rule_id: 87702
      rule_level: 14
      rule_description: "Possible credential harvesting tool detected"
      rule_groups: ["windows", "credential-access"]
      agent_name: "BMG-FIN-WS01"
      data:
        win:
          eventdata:
            image: "C:\\Users\\j.doe\\AppData\\Local\\Temp\\svhost.exe"
            hashes: "SHA256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    - inject_at: "T+42m"
      rule_id: 5715
      rule_level: 9
      rule_description: "Multiple authentication failures followed by success"
      rule_groups: ["authentication", "windows"]
      agent_name: "BMG-FIN-WS02"
      data:
        win:
          system:
            eventID: "4625"
          eventdata:
            targetUserName: "svc.finance"
            ipAddress: "10.0.1.55"  # BMG-FIN-WS01 IP — lateral movement indicator

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# Defines which Wazuh agents are relevant to this scenario
# ─────────────────────────────────────────────────────────────────────────────
endpoints:
  required_agents:
    - hostname: BMG-FIN-WS01
      wazuh_agent_id: "012"
      role_label: "Finance Workstation — J. Doe"
      os: "Windows 11 Pro"
      ip: "10.0.1.55"
      criticality: high

    - hostname: BMG-FIN-WS02
      wazuh_agent_id: "013"
      role_label: "Finance Workstation — M. Johnson"
      os: "Windows 11 Pro"
      ip: "10.0.1.56"
      criticality: high

    - hostname: BMG-DC01
      wazuh_agent_id: "001"
      role_label: "Domain Controller"
      os: "Windows Server 2022"
      ip: "10.0.0.10"
      criticality: critical

# ─────────────────────────────────────────────────────────────────────────────
# INITIAL CONDITIONS
# State created when the scenario is launched
# ─────────────────────────────────────────────────────────────────────────────
initial_conditions:
  auto_create_incident: true
  incident:
    title: "Suspicious Email Activity — Finance Department"
    severity: high
    category: phishing
    description: >
      Initial alert triggered by PowerShell execution via Microsoft Word
      on BMG-FIN-WS01. Possible phishing-delivered malware.

# ─────────────────────────────────────────────────────────────────────────────
# GRADING RUBRIC
# Defines how instructor grades the report and how auto-scoring works
# ─────────────────────────────────────────────────────────────────────────────
grading:
  total_points: 100
  auto_grade_decisions: true     # score student_decisions records automatically
  instructor_review_required: true

  report_rubric:
    - id: executive_summary
      label: "Executive Summary"
      points: 20
      guidance: |
        Should be 2-4 paragraphs. Non-technical. Must state: confirmed vs. suspected,
        number of affected endpoints, brief impact assessment, and current status.

    - id: timeline
      label: "Incident Timeline"
      points: 25
      guidance: |
        Must include at minimum: initial alert time, PowerShell execution,
        credential harvesting attempt, second-host activity, and isolation decision.
        Timestamps must be sourced from alert data, not estimated.

    - id: iocs
      label: "Indicators of Compromise"
      points: 15
      guidance: |
        Must identify: the PowerShell command hash, the dropped binary hash,
        the C2 IP address from network logs, and the compromised user account.

    - id: containment_actions
      label: "Containment Actions"
      points: 20
      guidance: |
        Must document: which endpoints were isolated, when, and why.
        Must describe account disablement if performed.

    - id: recommendations
      label: "Recommendations"
      points: 20
      guidance: |
        Must be specific to BMG's environment. Generic recommendations score
        0-10 points. Recommendations tied to specific findings score 11-20.

  decision_scoring:
    # Auto-scored when a student logs a decision of this type
    - decision_type: initial_triage
      points: 5
      time_window: "T+15m"
      description: "Triage the first alert within 15 minutes of scenario start"

    - decision_type: endpoint_isolated
      points: 10
      target_endpoint: BMG-FIN-WS01
      description: "Isolate the primary affected endpoint"

    - decision_type: evidence_collected
      min_count: 3
      points: 5
      description: "Collect at least 3 evidence items"

# ─────────────────────────────────────────────────────────────────────────────
# HINTS
# Shown to students when stuck (configurable by instructor at launch)
# ─────────────────────────────────────────────────────────────────────────────
hints:
  enabled: true
  mode: on_request    # on_request | timed | disabled

  items:
    - id: hint_01
      trigger_condition: "no_triage_after_20m"
      level: 1    # 1=nudge, 2=specific, 3=direct
      text: |
        Start with the highest-severity alert. What process spawned the
        suspicious PowerShell command? Is that normal behavior?

    - id: hint_02
      trigger_condition: "no_isolation_after_45m"
      level: 2
      text: |
        You've identified malware execution on BMG-FIN-WS01. Consider
        whether this machine should be isolated from the network to prevent
        further spread while you continue your investigation.
```

---

## Campaign File Structure

A campaign wraps multiple scenario stages with a shared narrative.

```yaml
# campaigns/bmg-apt-siege/campaign.yaml
id: bmg-apt-siege
version: "1.0"
type: campaign

metadata:
  title: "Operation APT Siege — BMG Targeted Attack"
  description: >
    A sophisticated threat actor has targeted Buckeye Manufacturing Group.
    Students will investigate a multi-stage attack from initial access through
    data exfiltration over a five-week period.
  difficulty: advanced
  estimated_duration_weeks: 5
  tags: [apt, advanced, multi-stage, campaign]

narrative:
  overall_briefing: |
    Intelligence reports indicate that a threat actor group with nation-state
    ties has been targeting U.S. manufacturing companies in the Midwest.
    BMG's threat intelligence feed flagged indicators matching this group
    last week. Your team will investigate and respond to each phase of
    this intrusion as it unfolds.

stages:
  - stage_number: 1
    scenario_id: ic-002-initial-access
    title: "Stage 1: The Door Opens"
    narrative_intro: |
      It's Monday morning. An endpoint detection alert has fired overnight.
      Something got in. Your job is to figure out how.
    prerequisites: []

  - stage_number: 2
    scenario_id: ic-003-lateral-movement
    title: "Stage 2: Moving Through the Network"
    narrative_intro: |
      The attacker didn't stop at one machine. Review what happened next.
    prerequisites:
      - stage_number: 1
        completion_status: completed    # or 'submitted' (report submitted is enough)

  - stage_number: 3
    scenario_id: ic-004-exfiltration
    title: "Stage 3: Data Out the Door"
    narrative_intro: |
      Large volumes of data are moving. Where is it going? What did they take?
    prerequisites:
      - stage_number: 2
        completion_status: completed
```

---

## Scenario Engine: Runtime Behavior

### At Launch (Instructor triggers)

```
ScenarioLaunchService.launch(scenario_id, course_id, assignment)
  1. Load scenario YAML → validate against schema
  2. Create scenario_instance record (status=pending)
  3. Create endpoint_assignment records for required_agents
  4. If initial_conditions.auto_create_incident = true → create incident record
  5. Schedule simulated alert injection tasks (Celery, eta = launch_time + offset)
  6. If wazuh.alert_filters defined → register filter in alert poller config
  7. Set scenario_instance.status = active, record started_at
  8. Notify assigned team/student
```

### During Active Scenario (Background workers)

```
AlertPollerTask (every 30s):
  1. Query Wazuh Indexer for new alerts since last_poll_timestamp
  2. Filter by registered scenario instance configurations
  3. For each matching alert:
     a. Normalize fields
     b. Deduplicate by wazuh_alert_id
     c. Insert to alerts table
     d. Run AlertCorrelationEngine → link to incident if match
  4. Update last_poll_timestamp in Redis

SimulatedAlertTask (fires at T+N):
  1. Load inject definition from scenario_data
  2. Build synthetic Alert record (is_simulated=true, wazuh_alert_id=null)
  3. Insert to alerts table
  4. Run correlation engine

DecisionAuditMiddleware (on every mutating API call):
  1. Detect if action qualifies as a decision_type
  2. Write student_decisions record with user, timestamp, decision_data
```

### At Completion (Student submits report / Instructor closes)

```
ScenarioCompletionService.complete(scenario_instance_id)
  1. Set scenario_instance.status = completed, completed_at = now()
  2. Unregister Wazuh alert filter
  3. If auto_grade_decisions = true → run GradingEngine.score_decisions()
  4. If campaign_stage → check if next stage prerequisites are met → unlock next stage
```

---

## Scenario Validation Schema

Before a YAML file is accepted by the API (`POST /api/v1/scenarios/validate`), it is validated against a Pydantic schema that enforces:

- `id` is a valid kebab-case string
- `type` is one of the allowed values
- `metadata.title` is non-empty
- `metadata.estimated_duration` is a positive integer
- `grading.total_points` equals the sum of all `report_rubric` point values
- All `simulated_alerts` have required fields: `inject_at`, `rule_id`, `rule_level`, `agent_name`
- All `endpoints.required_agents` have `hostname` and `wazuh_agent_id`
- `prerequisites` in campaign stages reference valid `stage_number` values within the campaign

Validation errors return a structured list of field paths and messages, making authoring feedback clear.

---

## Scenario Library Conventions

### Naming

| Type | ID Pattern | Example |
|---|---|---|
| Training Lab | `tl-NNN-short-description` | `tl-001-alert-triage` |
| Incident Case | `ic-NNN-short-description` | `ic-001-phishing-finance` |
| Campaign | `camp-NNN-short-description` | `camp-001-bmg-apt-siege` |
| Campaign Stage | `ic-NNN-short-description` | `ic-005-lateral-movement` (reusable) |

### Difficulty Guidelines

| Level | Duration | Expected Student Experience |
|---|---|---|
| beginner | 30–45 min | First 2–3 weeks of course; single alert, single endpoint |
| intermediate | 60–90 min | Mid-course; 3–5 alerts, 2–3 endpoints, report required |
| advanced | 90–180 min | Late course or campaign; multi-stage, ambiguous indicators |
