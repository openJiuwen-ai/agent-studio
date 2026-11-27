# AgentStudio Documentation (中文)

中文文档为本仓库的**权威版本**（与英文文档 [`../en/`](../en/) 保持同步）。

## 阅读指南

- **刚接触项目**：从[快速启动](tutorial/01-quick-start.md)开始，搭建本地开发环境。
- **用平台构建应用**：阅读[用户指南](tutorial/02-user-guide.md)，构建你的第一个智能体和工作流。
- **解决具体任务**：在操作指南分类中查找部署、升级与问题排查指南。
- **查询接口**：在参考文档分类中查找 REST API 规格。
- **理解架构**：在解释文档分类中阅读架构概述。

## 文档分类

### 教程（我想学习）

面向新手的分步指南，按推荐阅读顺序编号。

- [01-快速启动](tutorial/01-quick-start.md) — 本地开发环境搭建、增量构建与调试
- [02-用户指南](tutorial/02-user-guide.md) — 构建智能体、工作流与知识库问答应用

### 操作指南（我要做）

解决具体任务的指南，使用语义化命名。

- [安装部署](how-to/deploy-service.md) — 部署总入口：Docker Compose 与 Kubernetes 安装部署
- [Docker Compose 部署](how-to/deploy-docker-compose.md) — Docker Compose 安装与部署
- [Kubernetes 部署](how-to/deploy-k8s.md) — Kubernetes 安装与部署
- [Beta5 升级部署](how-to/upgrade-from-beta4.md) — 从 Beta4 及更早版本升级
- [开发指南](how-to/development-guide.md) — 加密扩展、SSO 鉴权、存储配置
- [自定义插件开发指南](how-to/custom-plugin-development-guide.md) — 自定义插件的开发与接入
- [HTTP 工具 Schema 约定](how-to/http-tool-schema-guide.md) — HTTP / OpenAPI 工具请求体与 schema 契约
- [资产广场预置](how-to/asset-plaza-preset.md) — 应用模板、模型、MCP、插件等资产预置
- [可观测性部署](how-to/configure-opentelemetry.md) — OpenTelemetry 链路管道接入
- [知识库接入指南](how-to/knowledge-base-guide.md) — 知识库创建、上传与检索接入
- [SQL 自定义节点配置指南](how-to/sql-node-guide.md) — SQL 自定义节点配置
- [审计日志使用指南](how-to/audit-log-guide.md) — 审计日志的使用与配置
- [运行问题排查](how-to/troubleshooting.md) — 工作流与智能体运行问题定位
- [常见问题 FAQ](../FAQ/faq.md) — 高频问题速查

### 参考文档（我要查询）

事实性、结构化、可检索的参考材料。

- [REST API 参考](reference/rest-api.md) — 接口规格与请求/响应示例

### 解释文档（我想理解）

讲解概念、架构与设计决策。

- [架构概述](explanation/architecture-overview.md) — 总体架构、模块细节与技术栈

## 多语言

- [中文文档（权威）](./)
- [English Documentation (Following)](../en/)

## 相关资源

- [README](../../README.md) — 项目概览与快速开始
- [CHANGELOG](../../CHANGELOG.md) — 版本变更历史
- [贡献指南](../../CONTRIBUTING.md)
