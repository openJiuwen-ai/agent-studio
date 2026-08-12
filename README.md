# openJiuwen AgentStudio

[中文](README_zh.md) | English

---

## 1 Project Overview

openJiuwen AgentStudio is an all-in-one AI Agent development platform that provides a full-stack solution from development to deployment, with low-code / no-code visual design and orchestration tools to rapidly build and debug agents and workflows.

This project is intended for:

| Audience | Description |
|----------|-------------|
| Backend Engineers | Java backend service architecture, API design, and business logic |
| Frontend Engineers | Angular frontend project structure, components, and routing |
| DevOps Engineers | Docker deployment, service configuration, and environment variables |
| Technical Architects | System architecture, technology selection, and module breakdown |
| AI Application Developers | Agent platform capabilities, RAG knowledge base, workflow orchestration |
| QA Engineers | Functional modules and interface specifications |

## 2 Core Features

| Feature | Description |
|---------|-------------|
| Low-code / No-code | Visual Agent and workflow design and orchestration |
| Multi-Model Support | Integration and switching of mainstream LLMs |
| RAG Knowledge Base | Knowledge base creation, upload, and retrieval |
| Workflow Orchestration | Complex workflow orchestration and execution |
| Plugin Marketplace | Plugin browsing, installation, and management |
| Prompt Engineering | Prompt writing, debugging, and optimization |
| MCP Protocol | Model Context Protocol support |
| Multi-Datasource | MySQL, PostgreSQL, and more |
| Cloud-Native | Docker and Kubernetes deployment |
| Auth & Authorization | Simple Auth, SSO |

## 3 Related Documentation

- [Docs Overview](docs/README.md) — documentation entry
- [Quick Start](docs/en/tutorial/01-quick-start.md) — local dev environment setup
- [Deployment](docs/en/how-to/deploy-service.md) — Docker/K8s deployment
- [REST API Reference](docs/en/reference/rest-api.md) — interface specification
- [CHANGELOG](CHANGELOG.md) | [Contributing](CONTRIBUTING.md)

## 4 Requirements

| Requirement | Version |
|-------------|---------|
| JDK | 17+ |
| Maven | 3.8+ |
| Node.js | 22 (18 minimum) |
| npm/pnpm | 9+ / 7+ |
| MySQL / GaussDB | MySQL 8.0+ |
| Redis | 7+ |
| Docker | 20+ |

| Constraint | Description |
|------------|-------------|
| JDK | JDK 17 or higher required |
| Database | MySQL 8.0 default; GaussDB also supported |
| Browser | Latest two versions of mainstream browsers |
| Memory | 2 GB minimum per service; 4 GB+ recommended for production |

> For the detailed technology stack, see [Architecture Overview](docs/en/explanation/architecture-overview.md).

## 5 Installation

```bash
cp deploy/.env.template deploy/.env
bash docker/package.sh
bash docker/build.sh
bash deploy/deploy.sh local
```

The complete environment contains four application services: `studio-console`, `studio-manager`, `studio-runtime`, and `studio-builder`. See the [Deployment Guide](docs/en/how-to/deploy-service.md) for details.

## 6 Quick Start

Frontend development:

```bash
cd frontend
pnpm install
pnpm start
```

For full environment startup, incremental builds, and debugging, see [Local Dev Quick Start](docs/en/tutorial/01-quick-start.md).

## 7 License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file.

## Contributing

Issues and Pull Requests are welcome. See the [Contributing Guide](CONTRIBUTING.md).
