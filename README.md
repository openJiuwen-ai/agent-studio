# openJiuwen AgentStudio

[中文](README_zh.md) | English

openJiuwen AgentStudio is an all-in-one AI Agent development platform that provides developers with a full-stack solution from development to deployment. It offers low-code / no-code visual design and orchestration tools that let developers rapidly build and debug agents and workflows.

---

## 1 Intended Audience

This project is intended for the following readers:

| Audience | Description |
|----------|-------------|
| **Backend Engineers** | Developers who want to understand the Java backend service architecture, API design, and business logic implementation |
| **Frontend Engineers** | Developers who want to understand the Angular frontend project structure, component development, and routing configuration |
| **DevOps Engineers** | Operators who want to understand Docker deployment, service configuration, and environment variable setup |
| **Technical Architects** | Decision-makers who want to understand the overall system architecture, technology selection, and module breakdown |
| **AI Application Developers** | Developers who want to understand the Agent development platform capabilities, RAG knowledge base, and workflow orchestration |
| **QA Engineers** | Testers who want to understand the system's functional modules and interface specifications |

---

## 2 Project Structure

```
agent-studio/
├── backend/                          # Java backend service module
├── frontend/                         # Angular frontend application module
├── docs/                             # Project documentation
├── docker/                           # Docker deployment configuration
└── LICENSE / README.md (root files)
```

---

## 3 Quick Start

### 3.1 Requirements

| Requirement | Version |
|-------------|---------|
| JDK | 17+ |
| Maven | 3.8+ |
| Node.js | 18+ |
| npm/pnpm | 9+ / 7+ |
| PostgreSQL | 12+ |
| Redis | 6+ |
| Docker | 20+ |

### 3.2 Backend Development

1. Clone the repository
2. Execute `backend/sql/schema.sql` to create database tables
3. Execute `backend/sql/init.sql` and `data.sql` to initialize data
4. Configure the database and Redis connection information
5. Run the Maven build: `mvn clean install`
6. Start the Manager service or the Runtime service

### 3.3 Frontend Development

1. Change into the `frontend` directory
2. Install dependencies: `pnpm install`
3. Start the development server: `pnpm start`

### 3.4 Docker Deployment

1. Source build guide: [源码编译构建指导.md](docker/%E6%BA%90%E7%A0%81%E7%BC%96%E8%AF%91%E6%9E%84%E5%BB%BA%E6%8C%87%E5%AF%BC.md)
2. Installation and deployment guide: [安装部署指南.md](docs/%E5%AE%89%E8%A3%85%E9%83%A8%E7%BD%B2%E6%8C%87%E5%8D%97.md)

---

## 4 Features

| Feature | Description |
|---------|-------------|
| **Low-code / No-code Development** | Provides visual Agent and workflow design and orchestration tools |
| **Multi-Model Support** | Supports the integration and switching of mainstream large language models |
| **RAG Knowledge Base** | Provides knowledge base creation, upload, and retrieval capabilities |
| **Workflow Orchestration** | Supports the orchestration and execution of complex workflows |
| **Plugin Marketplace** | Supports browsing, installing, and managing plugins |
| **Prompt Engineering** | Provides prompt writing, debugging, and optimization features |
| **MCP Protocol Support** | Supports the Model Context Protocol |
| **Multi-Datasource Integration** | Supports multiple datasources such as MySQL and PostgreSQL |
| **Cloud-Native Deployment** | Provides Docker and Kubernetes deployment support |
| **Authentication & Authorization** | Supports multiple authentication methods including JWT, LDAP, and SAML |

---

## 5 Constraints

| Constraint | Description |
|------------|-------------|
| **JDK Version** | JDK 17 or higher is required |
| **Node.js Version** | Node.js 18 or higher is required |
| **Database** | PostgreSQL 12+ is recommended for production |
| **Browser Compatibility** | The frontend supports the latest two versions of mainstream browsers |
| **Network** | Inter-service communication requires intra-network connectivity or properly configured security groups |
| **Memory** | A minimum of 2 GB per service is recommended; 4 GB+ is recommended for production |
| **Storage** | Reserve sufficient database and object storage capacity based on your data volume |

---

## 6 Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend Framework** | Spring Boot 3.5.14, Spring Security 6.5.10 |
| **Frontend Framework** | Angular 20.3.17, NG-ZORRO 20.4.4 |
| **Database** | PostgreSQL 42.7.11, Redis 3.39.0, H2 2.2.224 |
| **Object Storage** | Huawei Cloud OBS SDK 3.23.9 |
| **Communication Framework** | Netty 4.1.133.Final |
| **Build Tools** | Maven 3.8+, Angular Build 20.3.13 |

For the detailed technology stack, see [项目架构.md](docs/项目架构.md).

---

## 7 More Information

- Installation and deployment: [安装部署指南.md](docs/安装部署指南.md)
- Quick experience: [用户指南.md](docs/用户指南.md)
- API reference: [API参考.md](docs/API参考.md)
- Architecture design: [项目架构.md](docs/项目架构.md)

---

# ⚖️ License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.

# 🤝 Contributing

Issues and Pull Requests are welcome!
