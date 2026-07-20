# openJiuwen AgentStudio

中文 | [English](README.md)

openJiuwen AgentStudio提供了一站式AI Agent开发平台，为开发者提供从开发到部署的全栈解决方案。该部分采用低代码 / 零代码的可视化设计与编排工具，能让开发者快速打造和调试智能体和工作流。

---

## 1 文档适用人群

本项目适用于以下类型的读者：

| 适用人群 | 说明 |
|----------|------|
| **后端开发工程师** | 想要了解Java后端服务架构、API设计、业务逻辑实现的开发者 |
| **前端开发工程师** | 想要了解Angular前端项目结构、组件开发、路由配置的开发者 |
| **运维工程师** | 想要了解Docker部署、服务配置、环境变量设置的运维人员 |
| **技术架构师** | 想要了解整体系统架构、技术选型、模块划分的技术决策者 |
| **AI应用开发者** | 想要了解Agent开发平台能力、RAG知识库、工作流编排的开发者 |
| **测试工程师** | 想要了解系统功能模块、接口规范的测试人员 |

---

## 2 项目整体结构

```
agent-studio/
├── backend/                          # Java后端服务模块
├── agent-runtime/                    # Python运行时服务
├── agent_builder/                    # NL2、Prompt与模型调用服务
├── packages/                         # Python共享包
├── frontend/                         # Angular前端应用模块
├── docs/                             # 项目文档模块
├── docker/                           # Docker部署配置
├── deploy/                           # 统一部署脚本与Compose配置
└── LICENSE / README.md 等根文件
```

---

## 3 快速开始

### 3.1 环境要求

| 要求 | 版本 |
|------|------|
| JDK | 17+ |
| Maven | 3.8+ |
| Node.js | 22（最低18） |
| npm/pnpm | 9+ / 7+ |
| MySQL / GaussDB | MySQL 8.0+ |
| Redis | 7+ |
| Docker | 20+ |

### 3.2 本地完整启动

```bash
cp deploy/.env.template deploy/.env
bash docker/package.sh
bash docker/build.sh
bash deploy/deploy.sh local
```

当前完整环境包含 `studio-console`、`studio-manager`、`studio-runtime` 和 `studio-builder` 四个应用服务。原 `studio-service` 的能力已拆分并集成到 Manager、Runtime 和 Builder。首次启动、单服务增量构建和 `.last-build.env` 使用方法详见[本地开发快速启动](docs/本地开发快速启动.md)。

### 3.3 前端开发

1. 进入`frontend`目录
2. 安装依赖：`pnpm install`
3. 启动开发服务器：`pnpm start`

### 3.4 Docker部署

1. 源码编译构建指导：[源码编译构建指导.md](docker/%E6%BA%90%E7%A0%81%E7%BC%96%E8%AF%91%E6%9E%84%E5%BB%BA%E6%8C%87%E5%AF%BC.md)
2. 安装部署指南：[安装部署指南.md](docs/%E5%AE%89%E8%A3%85%E9%83%A8%E7%BD%B2%E6%8C%87%E5%8D%97.md)
3. 本地开发快速启动：[本地开发快速启动.md](docs/%E6%9C%AC%E5%9C%B0%E5%BC%80%E5%8F%91%E5%BF%AB%E9%80%9F%E5%90%AF%E5%8A%A8.md)

---

## 4 特性表格

| 特性 | 说明 |
|------|------|
| **低代码/零代码开发** | 提供可视化的Agent和工作流设计与编排工具 |
| **多模型支持** | 支持主流大语言模型的集成与切换 |
| **RAG知识库** | 提供了知识库的创建、上传、检索功能 |
| **工作流编排** | 支持复杂工作流的编排与执行 |
| **插件市场** | 支持插件的浏览、安装与管理 |
| **提示词工程** | 提供提示词的编写、调试、优化功能 |
| **MCP协议支持** | 支持Model Context Protocol协议 |
| **多数据源集成** | 支持MySQL、PostgreSQL等多种数据源 |
| **云原生部署** | 提供Docker和Kubernetes部署支持 |
| **权限与认证** | 支持JWT、LDAP、SAML等多种认证方式 |

---

## 5 约束条件

| 约束项 | 说明 |
|--------|------|
| **JDK版本** | 必须使用JDK 17或更高版本 |
| **Node.js版本** | 必须使用Node.js 18或更高版本 |
| **数据库要求** | 默认使用MySQL 8.0，也支持GaussDB |
| **浏览器兼容** | 前端支持主流浏览器的最近两个版本 |
| **网络要求** | 服务间通信需要内网互通或正确配置安全组 |
| **内存要求** | 单服务最低建议2GB内存，生产环境建议4GB+ |
| **存储要求** | 根据业务数据量预留足够的数据库和对象存储空间 |

---

## 6 技术栈概览

| 层级 | 技术 |
|------|------|
| **后端框架** | Spring Boot 3.5.15、Spring Security 6.5.10 |
| **前端框架** | Angular 20.3.25、NG-ZORRO 20.4.4 |
| **数据访问** | MariaDB JDBC 3.5.6（默认连接 MySQL 兼容数据库）、PostgreSQL JDBC 42.7.11、H2 2.2.224、Redis/Redisson 3.39.0 |
| **对象存储** | 华为云OBS SDK 3.23.9 |
| **通信框架** | Netty 4.1.133.Final |
| **构建工具** | Maven 3.8+、Angular Build 20.3.13 |

详细技术栈请参考 [项目架构.md](docs/项目架构.md)。

---

## 7 更多信息

- 安装部署参考 [安装部署指南](docs/安装部署指南.md)
- 快速体验参考 [用户指南](docs/用户指南.md)
- API接口参考 [API参考](docs/API参考.md)
- 架构设计参考 [项目架构](docs/项目架构.md)

---

# ⚖️ **许可证**

本项目采用 Apache 2.0 许可证。详见 [LICENSE](LICENSE) 文件。

# 🤝 **贡献指南**

欢迎提交 Issue 和 Pull Request！
