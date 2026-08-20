# openJiuwen AgentStudio

中文 | [English](README.md)

---

## 1 项目定位

openJiuwen AgentStudio 提供一站式 AI Agent 开发平台，为开发者提供从开发到部署的全栈解决方案，采用低代码 / 零代码的可视化设计与编排工具，让开发者快速打造和调试智能体与工作流。

本项目适用于以下类型的读者：

| 适用人群 | 说明 |
|----------|------|
| 后端开发工程师 | 想要了解 Java 后端服务架构、API 设计、业务逻辑实现的开发者 |
| 前端开发工程师 | 想要了解 Angular 前端项目结构、组件开发、路由配置的开发者 |
| 运维工程师 | 想要了解 Docker 部署、服务配置、环境变量设置的运维人员 |
| 技术架构师 | 想要了解整体系统架构、技术选型、模块划分的技术决策者 |
| AI 应用开发者 | 想要了解 Agent 开发平台能力、RAG 知识库、工作流编排的开发者 |
| 测试工程师 | 想要了解系统功能模块、接口规范的测试人员 |

## 2 核心特性

| 特性 | 说明 |
|------|------|
| 低代码/零代码开发 | 提供可视化的 Agent 和工作流设计与编排工具 |
| 多模型支持 | 支持主流大语言模型的集成与切换 |
| RAG 知识库 | 提供知识库的创建、上传、检索功能 |
| 工作流编排 | 支持复杂工作流的编排与执行 |
| 插件市场 | 支持插件的浏览、安装与管理 |
| 提示词工程 | 提供提示词的编写、调试、优化功能 |
| MCP 协议支持 | 支持 Model Context Protocol 协议 |
| 多数据源集成 | 支持 MySQL、PostgreSQL 等多种数据源 |
| 云原生部署 | 提供 Docker 和 Kubernetes 部署支持 |
| 权限与认证 | 支持 Simple 鉴权、SSO 远程鉴权 |

## 3 相关文档

- [文档总览](docs/README.md) — 文档导航入口
- [快速启动](docs/zh/tutorial/01-quick-start.md) — 本地开发环境搭建
- [安装部署](docs/zh/how-to/deploy-service.md) — Docker/K8s 部署
- [REST API 参考](docs/zh/reference/rest-api.md) — 接口规范
- [CHANGELOG](CHANGELOG.md) | [贡献指南](CONTRIBUTING.md)

## 4 环境要求

| 要求 | 版本 |
|------|------|
| JDK | 17+ |
| Maven | 3.8+ |
| Node.js | 22（最低 18） |
| npm/pnpm | 9+ / 7+ |
| MySQL / GaussDB | MySQL 8.0+ |
| Redis | 7+ |
| Docker | 20+ |

| 约束项 | 说明 |
|--------|------|
| JDK 版本 | 必须使用 JDK 17 或更高版本 |
| 数据库 | 默认 MySQL 8.0，也支持 GaussDB |
| 浏览器 | 前端支持主流浏览器最近两个版本 |
| 内存 | 单服务最低 2GB，生产环境建议 4GB+ |

> 详细技术栈请参考 [架构概述](docs/zh/explanation/architecture-overview.md)。

## 5 安装指南

```bash
cp deploy/.env.template deploy/.env
bash docker/package.sh
bash docker/build.sh
bash deploy/deploy.sh local
```

完整环境包含 `studio-console`、`studio-manager`、`studio-runtime`、`studio-builder` 四个应用服务。详细部署步骤见 [安装部署指南](docs/zh/how-to/deploy-service.md)。

## 6 Quick Start

前端开发：

```bash
cd frontend
pnpm install
pnpm start
```

完整环境启动、增量构建与调试详见 [本地开发快速启动](docs/zh/tutorial/01-quick-start.md)。

## 7 License

本项目采用 Apache 2.0 许可证。详见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎提交 Issue 和 Pull Request，参见 [贡献指南](CONTRIBUTING.md)。
