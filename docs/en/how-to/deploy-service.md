# Installation and Deployment Guide

openJiuwen AgentStudio contains 4 application services, supporting two deployment methods. Choose based on your actual scenario:

## Service Overview

| Service | Tech stack | Default port | In-container log path | Description |
|---------|-----------|-------------|----------------------|-------------|
| studio-console | Nginx + Angular | 80 | `/opt/cloud/wiseagent-nginx/logs/error.log` | Frontend console + API reverse proxy |
| studio-manager | Spring Boot (Java 17) | 31111 | `/opt/cloud/studio-manager/logs/studio-agent-manager.log` | Management plane: Agent/knowledge base/model/tool/MCP management |
| studio-runtime | Python (FastAPI) | 31014 | `/opt/cloud/logs/jiuwen_python.log` | Execution plane: Agent/workflow execution, published calls, LLM/MCP/memory |
| studio-builder | Python (FastAPI) | 31015 | `/opt/cloud/logs/agent-builder/common.log` | Build plane: NL2, Prompt, model tuning |

## External Dependencies

| Dependency | Version | Required | Description |
|-----------|---------|----------|-------------|
| MySQL / GaussDB | 8.0+ | ✅ | Main data storage |
| Redis | 7.x | ✅ | Cache/session/variable storage |
| MinIO / OBS | latest | ✅ | Object storage |
| OpenSearch | 2.x | ❌ | Memory store vector storage; required when enabling memory store |

> Docker Compose orchestration includes built-in MySQL/Redis/MinIO out of the box; K8s deployment requires external instances.

## Choose a Deployment Method

### → [Docker Compose Deployment](./deploy-docker-compose.md)

**Features**: Single-machine deployment, one-click script manages the full lifecycle, orchestration includes built-in MySQL/Redis/MinIO.

---

### → [Kubernetes Deployment](./deploy-k8s.md)

**Features**: Cluster deployment, multi-instance, supports horizontal scaling and rolling updates.
