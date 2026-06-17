# CyberOps Range

An educational cybersecurity operations simulator where students act as analysts on an internal corporate security team for **Buckeye Manufacturing Group (BMG)**.

Students investigate incidents, analyze endpoint activity, review SIEM alerts, make containment decisions, and write incident reports — simulating real-world security operations work.

## Architecture Documents

| Document | Description |
|---|---|
| [01 — System Architecture](architecture/01-system-architecture.md) | Tech stack, service topology, Docker layout, Wazuh integration |
| [02 — Database Architecture](architecture/02-database-architecture.md) | Complete PostgreSQL schema for all domain entities |
| [03 — API Architecture](architecture/03-api-architecture.md) | REST API design, endpoint inventory, auth model |
| [04 — Scenario Framework](architecture/04-scenario-framework.md) | Scenario file format, engine design, examples |
| [05 — Development Roadmap](architecture/05-development-roadmap.md) | Phased build order with deliverables per phase |

## Version 1 Scope

- Authentication (students + instructors)
- Organizations, courses, and teams
- Incident management lifecycle
- Evidence collection and case notes
- Wazuh alert ingestion and endpoint sync
- Reporting engine
- Basic campaign tracking
- Instructor grading and oversight

## Not in Version 1

- AI personas
- Advanced SOAR automation
- Complex business event simulation
- Multi-tenant SaaS
