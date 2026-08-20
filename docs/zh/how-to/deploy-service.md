# 安装部署指南

openJiuwen AgentStudio 包含 4 个应用服务，支持两种部署方式。请根据实际场景选择：

## 服务概览

| 服务 | 技术栈 | 默认端口 | 容器内日志路径 | 说明 |
|------|--------|----------|---------------|------|
| studio-console | Nginx + Angular | 80 | `/opt/cloud/wiseagent-nginx/logs/error.log` | 前端控制台 + API 反向代理 |
| studio-manager | Spring Boot (Java 17) | 31111 | `/opt/cloud/studio-manager/logs/studio-agent-manager.log` | 管理面：Agent/知识库/模型/工具/MCP 管理 |
| studio-runtime | Python (FastAPI) | 31014 | `/opt/cloud/logs/jiuwen_python.log` | 执行面：Agent/工作流执行、发布调用、LLM/MCP/记忆 |
| studio-builder | Python (FastAPI) | 31015 | `/opt/cloud/logs/agent-builder/common.log` | 构建面：NL2、Prompt、模型调测 |

## 外部依赖

| 依赖 | 版本 | 必选 | 说明 |
|------|------|------|------|
| MySQL / GaussDB | 8.0+ | ✅ | 主数据存储 |
| Redis | 7.x | ✅ | 缓存/会话/变量存储 |
| MinIO / OBS | latest | ✅ | 对象存储 |
| OpenSearch | 2.x | ❌ | 记忆库向量存储，启用记忆库时必需 |

> Docker Compose 编排内置 MySQL/Redis/MinIO，开箱即用；K8s 部署需自备。

## 选择部署方式

### → [Docker Compose 部署](./deploy-docker-compose.md)

**特点**：单机部署，一键脚本管理全生命周期，编排内置 MySQL/Redis/MinIO。

---

### → [K8s 部署](./deploy-k8s.md)

**特点**：集群部署，多实例，支持横向扩容和滚动更新。
