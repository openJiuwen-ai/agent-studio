# AgentStudio Documentation (English)

English documentation, following the Chinese authoritative source under [`zh/`](../zh/).

## Reading Guide

- **New to the project**: Start with [Quick Start](tutorial/01-quick-start.md) to set up your local dev environment.
- **Building apps with the platform**: Read the [User Guide](tutorial/02-user-guide.md) to build your first Agent and Workflow.
- **Specific tasks**: Find deployment, upgrade, and troubleshooting guides in the How-to category.
- **Looking up APIs**: Find REST API reference in the Reference category.
- **Understanding architecture**: Read architecture overviews in the Explanation category.

## Documentation Categories

### Tutorial (I want to learn)

Step-by-step guides for newcomers, numbered by recommended reading order.

- [01-Quick Start](tutorial/01-quick-start.md) — Local dev environment setup, incremental build and debugging
- [02-User Guide](tutorial/02-user-guide.md) — Building agents, workflows, and knowledge base Q&A applications

### How-to (I want to do)

Guides for solving specific tasks, using semantic names.

- [Deploy Service](how-to/deploy-service.md) — Overall deployment entry: Docker Compose and Kubernetes installation and deployment
- [Docker Compose Deployment](how-to/deploy-docker-compose.md) — Docker Compose installation and deployment
- [Kubernetes Deployment](how-to/deploy-k8s.md) — Kubernetes installation and deployment
- [Beta5 Upgrade Deployment](how-to/upgrade-from-beta4.md) — Upgrading from Beta4 and earlier
- [Development Guide](how-to/development-guide.md) — Encryption extension, SSO auth, storage configuration
- [Custom Plugin Development Guide](how-to/custom-plugin-development-guide.md) — Developing and integrating custom plugins
- [Knowledge Base Integration Guide](how-to/knowledge-base-guide.md) — Knowledge base creation, upload, and retrieval integration
- [SQL Custom Node Configuration Guide](how-to/sql-node-guide.md) — SQL custom node configuration
- [Audit Log Guide](how-to/audit-log-guide.md) — Audit log usage and configuration
- [Asset Plaza Preset](how-to/asset-plaza-preset.md) — Application template, model, MCP, plugin and other asset presetting
- [Observability Deployment](how-to/configure-opentelemetry.md) — OpenTelemetry trace pipeline integration
- [Troubleshooting](how-to/troubleshooting.md) — Workflow and agent runtime issue locating

### Reference (I want to look up)

Factual, structured, searchable reference material.

- [REST API Reference](reference/rest-api.md) — API specifications and request/response examples

### Explanation (I want to understand)

Explaining concepts, architecture, and design decisions.

- [Architecture Overview](explanation/architecture-overview.md) — Overall architecture, module details, and tech stack

## Multi-language

- [Chinese Documentation (Authoritative)](../zh/)
- [English Documentation (Following)](./)

## Related Resources

- [README](../../README.md) — Project overview and quick start
- [CHANGELOG](../../CHANGELOG.md) — Version change history
- [Contributing Guide](../../CONTRIBUTING.md)
