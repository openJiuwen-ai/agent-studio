# AgentStudio 文档

本目录是 openJiuwen AgentStudio 的用户文档权威源，按 [Diátaxis 文档框架](https://diataxis.fr/) 组织为四类，帮助不同意图的读者快速定位所需内容。中文为权威源（`zh/`），英文跟随（`en/`）。

## 阅读建议

- **新手入门**：从 [快速启动](zh/tutorial/01-quick-start.md) 开始，跑通本地开发环境。
- **想用平台搭应用**：阅读 [用户指南](zh/tutorial/02-user-guide.md)，跟着搭建第一个智能体与工作流。
- **遇到具体任务**：在 How-to 分类中查找部署、升级、排障等操作指南。
- **查接口配置**：在 Reference 分类中查阅 REST API 参考。
- **理解架构设计**：在 Explanation 分类中阅读架构概述。

## 文档分类

### Tutorial 教程（我想学）

按步骤带新手入门，使用数字前缀表示推荐阅读顺序。

- [01-快速启动](zh/tutorial/01-quick-start.md) — 本地开发环境搭建与增量构建调试
- [02-用户指南](zh/tutorial/02-user-guide.md) — 搭建智能体、工作流与知识库问答应用

### How-to 操作指南（我想做）

解决具体任务的步骤指南，使用语义化名称。

- [安装部署](zh/how-to/deploy-service.md) — Docker Compose 与 Kubernetes 安装部署
- [Beta5 升级部署](zh/how-to/upgrade-from-beta4.md) — 从 Beta4 及更早版本升级
- [开发指南](zh/how-to/development-guide.md) — 加解密扩展、SSO 鉴权、存储配置
- [资产广场预置](zh/how-to/asset-plaza-preset.md) — 应用模板、模型、MCP、插件等资产预置
- [可观测性部署](zh/how-to/configure-opentelemetry.md) — OpenTelemetry 链路追踪接入
- [运行问题排查](zh/how-to/troubleshooting.md) — 工作流与智能体运行问题定位

### Reference 参考文档（我想查）

事实性、结构化、可检索的参考材料。

- [REST API 参考](zh/reference/rest-api.md) — API 接口规范与请求响应示例

### Explanation 解释文档（我想理解）

解释概念、架构与设计决策。

- [架构概述](zh/explanation/architecture-overview.md) — 项目整体架构、模块详解与技术栈

## 多语言

- [中文文档（权威源）](zh/)
- [英文文档（跟随）](en/)

## 相关资源

- [README](../README_zh.md) — 项目概览与快速开始
- [CHANGELOG](../CHANGELOG.md) — 版本变更记录
- [贡献指南](../CONTRIBUTING.md)
