# Docker Compose 部署指南

## 一、概述

openJiuwen AgentStudio 包含 4 个应用服务，通过 Docker Compose 编排部署。编排内置基础设施（MySQL、Redis、MinIO），默认开箱即用；也支持外接已有实例。编排文件默认包含 8 个服务：

| 类型 | 服务 | 说明 |
|------|------|------|
| 基础设施 | mysql、redis、minio、minio-init | 由 `deploy.sh` 自动启动和初始化 |
| 应用服务 | studio-console、studio-manager、studio-runtime、studio-builder | 业务服务 |

> 4 个应用服务的技术栈和端口详见[部署总览](./deploy-service.md#服务概览)。外部依赖详见[部署总览 — 外部依赖](./deploy-service.md#外部依赖)，编排内置 MySQL/Redis/MinIO，默认开箱即用。

---

## 二、环境要求

| 资源 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 8核 | 12核以上 |
| 内存 | 16GB | 24GB以上 |
| 磁盘 | 50GB | 100GB |

各服务资源分配：

| 服务 | CPU | 内存 |
|------|-----|------|
| studio-console | 0.5核 | 512MB |
| studio-manager | 2核 | 4GB |
| studio-runtime | 2核 | 4GB |
| studio-builder | 2核 | 4GB |

### 前置条件

| 软件 | 版本要求 | 说明 |
|------|---------|------|
| Docker | ≥ 19.03 | 容器运行时 |
| Docker Compose | 推荐 V2，兼容 V1 | 服务编排（`deploy.sh` 自动检测兼容） |

> 部署前检查版本：
> ```bash
> docker --version
> docker compose version    # V2
> docker-compose version     # V1
> ```

#### 非 root 用户部署

部署脚本直接调用 `docker` 命令，部署用户需加入 `docker` 组（加入后重新登录生效）：

```bash
sudo usermod -aG docker $USER
```

---

## 三、部署

```
步骤1         步骤2            步骤3         步骤4
下载部署包 → 配置镜像来源 → deploy.sh all → 验证访问
```

### 步骤 1：下载部署包

从 [Release 页面](https://atomgit.com/openJiuwen/agent-studio/releases) 下载部署包并解压，进入解压目录：

```bash
# 从模板创建环境变量文件
cp .env.template .env
```

### 步骤 2：配置镜像来源

先探测镜像是否已发布到 GHCR 公共仓库：

```bash
docker pull ghcr.io/openjiuwen/openjiuwen_agent_studio/studio-console:latest
```

> 探测用 `:latest` 标签（CI 每次构建都会推送此标签），与 Release 页面的离线包版本号无关。能拉取成功说明镜像已发布，可使用方式一在线拉取；若报 403/404，说明尚未发布，请使用方式二离线导入。

**方式一：在线拉取**

```bash
vi .env
```

配置以下变量：

- `IMAGE_SOURCE=ghcr`
- `IMAGE_TAG`：镜像标签，默认 `latest`
- `GHCR_IMAGE_REPOSITORY`：GHCR 仓库地址，格式 `ghcr.io/<GitHub用户名或组织名>/<仓库名>`
- `GHCR_USERNAME`：GitHub 用户名，**公开镜像可留空**
- `GHCR_TOKEN`：GitHub Personal Access Token，需 `read:packages` 权限，**公开镜像可留空**

```bash
IMAGE_SOURCE=ghcr
IMAGE_TAG=latest
GHCR_IMAGE_REPOSITORY=ghcr.io/openjiuwen/openjiuwen_agent_studio
GHCR_USERNAME=
GHCR_TOKEN=
```

**方式二：离线导入**

1. 确认架构：

```bash
uname -m    # x86_64 / aarch64
```

2. 在部署包根目录下创建镜像目录并放入离线镜像包：

```bash
mkdir -p images dep-images
```

```
agent-studio-deploy/
├── images/        ← 业务镜像 .tar（4 个应用服务）
└── dep-images/    ← 基础镜像 .tar（MySQL/Redis/MinIO/MC，使用内置基础设施时需要）
```

> 使用外部依赖时 `dep-images/` 可留空。

##### 获取业务镜像包

从 [Release 页面](https://atomgit.com/openJiuwen/agent-studio/releases) 下载匹配架构的业务镜像 `.tar` 文件（共 4 个），放入 `images/`。

##### 获取基础镜像包

在有网络的机器上，使用部署包内置脚本导出基础镜像（含 MySQL/Redis/MinIO/MC）：

```bash
bash scripts/export-dependency-images.sh ~/dep-images
```

脚本自动拉取并导出以下镜像：

| 镜像 | 版本 |
|------|------|
| mysql | 8.0 |
| redis | 7 |
| minio/minio | RELEASE.2024-11-07T00-52-20Z |
| minio/mc | RELEASE.2024-11-05T11-29-45Z |

导出完成后，将 `~/dep-images/` 传输到目标机器的 `dep-images/` 目录下。

> 脚本同时导出可观测性镜像（VictoriaLogs/Vector），不使用可观测性功能时可忽略。

3. 编辑 `.env`：

```bash
vi .env
```

- 将 `IMAGE_SOURCE` 改为 `offline`
- 取消 `STUDIO_*_IMAGE` 四行的注释（删除行首 `#`，**变量名须顶格，不能有前导空格**），并将 `TAG_PLACEHOLDER` 替换为实际版本号和架构
- 镜像名格式：`<服务>:<版本号>.<架构>`，以下为示例，**版本号和架构需参考下载的离线镜像包名称和实际进行修改**

```bash
IMAGE_SOURCE=offline
STUDIO_CONSOLE_IMAGE=studio-console:v0.2.1.beta1.x86_64
STUDIO_MANAGER_IMAGE=studio-manager:v0.2.1.beta1.x86_64
STUDIO_RUNTIME_IMAGE=studio-runtime:v0.2.1.beta1.x86_64
STUDIO_BUILDER_IMAGE=studio-builder:v0.2.1.beta1.x86_64
```

> `deploy.sh` 会自动加载 `images/` 和 `dep-images/` 下的离线镜像包。

### 步骤 3：一键部署

```bash
bash deploy.sh all
```

自动执行：获取镜像（拉取或加载）→ 初始化基础设施（MySQL/Redis/MinIO + 数据库 + MinIO 桶） → 启动应用服务 → 健康检查 → 输出访问地址。

> `all` 命令会先获取镜像再启动，适合**首次部署**。后续更新使用 `update`，重启使用 `restart`。

> 💡 默认部署不含日志聚合栈。如需在 Grafana 中集中查询日志，见「[八、可观测性（日志聚合）](#八可观测性日志聚合)」。

### 步骤 4：验证

```bash
bash deploy.sh verify
bash deploy.sh status
bash deploy.sh logs <服务名>
```

浏览器访问：`http://<IP>/openjiuwen/`

> 容器内日志路径详见[部署总览 — 服务概览](./deploy-service.md#服务概览)。

---

## 四、版本升级与回滚

### 升级

```bash
bash deploy.sh update    # 获取最新镜像 → 重建服务 → 验证
```

> 在线模式自动拉取最新镜像；离线模式需先替换 `images/` 下的 tar 文件。
>
> 升级期间短暂不可用。

### 回滚

```bash
# 在线：修改 .env 中 IMAGE_TAG 为旧版本
# 离线：替换 images/ 下的旧版本 tar，恢复 .env 中的旧镜像名

bash deploy.sh restart
```

---

## 五、卸载与清理

```bash
# 停止服务（保留数据）
bash deploy.sh stop

# 停止基础设施（仅内置基础设施时）
bash deploy.sh stop-infra

# 停止所有（应用 + 基础设施）
bash deploy.sh stop-all

# 完全清理（⚠️ 删除数据卷，数据不可恢复）
bash deploy.sh clean all
```

---

## 六、常用命令参考

```bash
bash deploy.sh all         # 一键部署（拉/加载镜像 + 启动一切 + 验证）
bash deploy.sh infra       # 仅启动基础设施（MySQL/Redis/MinIO + 初始化数据库和桶）
bash deploy.sh init-db     # 仅初始化数据库和 MinIO 桶（基础设施需已运行）
bash deploy.sh start       # 启动所有服务（infra + app）
bash deploy.sh stop        # 停止所有服务
bash deploy.sh stop-infra  # 仅停止基础设施
bash deploy.sh stop-all    # 停止所有服务
bash deploy.sh restart     # 重启应用服务
bash deploy.sh update      # 拉取/加载镜像 + 重建服务 + 验证
bash deploy.sh verify      # 验证 HTTP 健康端点
bash deploy.sh status      # 查看服务状态
bash deploy.sh logs [svc]  # 查看日志
bash deploy.sh clean all   # 完全清理（⚠️ 数据不可恢复）

# 可观测性 / 日志聚合（可选，详见第八章）
bash deploy.sh logging              # L1 单机日志栈（victoria-logs+vector+grafana，本机）
bash deploy.sh logging-remote       # L2：应用节点远程 vector（push 到监控节点）
bash deploy.sh monitor              # L2：监控节点日志栈（victoria-logs+grafana+gateway）
```

---

## 七、API 文档（Swagger UI）

平台提供统一的环境变量 `API_DOCS_ENABLED` 控制管理面和运行面的 API 文档开关。

| 服务 | 技术栈 | 文档覆盖 |
|------|--------|---------|
| studio-manager | springdoc-openapi | 49 个 Controller 的全部管理面接口 |
| studio-runtime | FastAPI 原生 OpenAPI 3 | 28 个运行面接口 |

> **默认关闭**：API 文档默认不开启，按需设置 `API_DOCS_ENABLED=true` 即可开启。

### 开启方式

编辑 `.env` 文件，添加或修改：

```bash
API_DOCS_ENABLED=true
```

重启服务生效：

```bash
bash deploy.sh restart
```

### 访问地址

| 页面 | 地址 |
|------|------|
| 管理面 Swagger UI（可交互调试） | `http://<MANAGER_IP>:31111/swagger-ui.html` |
| 管理面 OpenAPI JSON（可导入 Postman） | `http://<MANAGER_IP>:31111/v3/api-docs` |
| 管理面 — 智能体管理分组 | `http://<MANAGER_IP>:31111/v3/api-docs/agent-management` |
| 管理面 — 提示词工程分组 | `http://<MANAGER_IP>:31111/v3/api-docs/prompt-engineering` |
| 运行面 Swagger UI（可交互调试） | `http://<RUNTIME_IP>:31014/runtime/docs` |
| 运行面 ReDoc（只读文档） | `http://<RUNTIME_IP>:31014/runtime/redoc` |
| 运行面 OpenAPI JSON | `http://<RUNTIME_IP>:31014/runtime/openapi.json` |

### 关闭

```bash
# .env 中改回 false 或删除该行（默认即为 false）
API_DOCS_ENABLED=false
bash deploy.sh restart
```

> 不再需要时建议将 `API_DOCS_ENABLED` 改回 `false`（默认值）。

---

## 八、可观测性（日志聚合）

> ⚠️ **适用范围**：本章方案只适用于 Docker Compose 部署。K8s 部署请使用日志采集 DaemonSet 和集中式日志存储。

平台内置**可选**的日志聚合栈，可在 Grafana 中集中查询四个应用服务（manager/runtime/builder/console）的日志，替代跨容器 `docker logs` / `grep`。两种部署模式：

| 模式 | 适用 | 存储 | 技术栈 | 启停入口 |
|---|---|---|---|---|
| **L1 单机** | 所有服务同一台主机 | 本地文件系统 | **VictoriaLogs** + Vector + Grafana | `bash deploy.sh logging` |
| **L2 跨节点** | 应用与监控分机部署 | 监控节点本地盘 | **VictoriaLogs**（全文索引）+ Vector + Grafana + gateway | 监控节点 `bash deploy.sh monitor` + 应用节点 `bash deploy.sh logging-remote` |

> L1/L2 统一使用 VictoriaLogs（全文索引，查询秒级；本地存储，无对象存储依赖）。查询和排障方式一致，详见 [`deploy/config/observability-readme.md`](../../deploy/config/observability-readme.md)。

### 7.1 L1 单机模式

日志聚合栈与应用服务同机，一条命令：

```bash
bash deploy.sh start          # 先确保应用服务在运行（日志才会写入命名卷）
bash deploy.sh logging        # 启动日志栈（victoria-logs/vector/grafana）
```

启动后访问 Grafana：`http://<IP>:3000/`（默认 admin/admin），Explore → VictoriaLogs 查询：
```text
_stream:{service=~"manager|runtime|builder|console"} ERROR
```
停止：`bash deploy.sh logging stop`。

### 7.2 L2 跨节点模式

应用与监控分机时：Vector 跟应用走、VictoriaLogs + Grafana + gateway 集中在监控节点、**本地存储**（无对象存储）。

**监控节点**（只用 `monitor` 子命令）：
```bash
bash deploy.sh monitor          # 启动（首次生成 observability/.env，修改 TLS 地址和读写口令后再跑）
```

**每个应用节点**（先应用后 vector，顺序不能反）：
```bash
bash deploy.sh start          # 1) 先启动应用服务（建立命名卷）
bash deploy.sh logging-remote # 2) 再启动远程 vector（push 到监控节点 gateway）
```

监控节点和应用节点统一使用 `observability/.env`。应用节点需设置唯一的
`NODE_NAME`，并把 `LOGS_GATEWAY_HOST` 配置为监控节点地址。旧版 `.env.vector`
中的配置需要合并到 `.env`，该文件已不再单独使用。

**前提**：监控节点 ↔ 应用节点网络可达；所有节点时钟同步（chrony/NTP）。

### 7.3 日志保留周期

- **L1/L2（VictoriaLogs）**：通过 `VICTORIA_LOGS_RETENTION` 配置，默认 7 天，超期自动清理。
- Java、Python runtime 和 NGINX 日志使用正文中的真实事件时间，首次导入历史日志不会污染"最近日志"查询。
- 两者均与应用本地 audit（180 天）相互独立。

### 7.4 更多

完整架构图、LogsQL 示例、排障和演进路径见 [`deploy/config/observability-readme.md`](../../deploy/config/observability-readme.md)。

---

## 九、常见问题

### Q1: 数据库连接失败

**现象**：日志报 `Communications link failure` 或 `Access denied`

**排查**：
1. 确认数据库已创建：`SHOW DATABASES LIKE 'agent-builder';`
2. 确认 `.env` 中 IP 和端口可达：`telnet <MYSQL_IP> 3306`
3. Docker 中 MySQL 用宿主机 IP，不用 `127.0.0.1`
4. 获取 Docker 网桥 IP：`ip addr show docker0 | grep inet`

### Q2: Redis 连接失败

**现象**：日志报 `Unable to connect to Redis`

**排查**：
1. 确认 Redis 运行：`redis-cli -h <IP> -p 6379 ping`
2. 有密码需配 `REDIS_PASSWORD`
3. 集群/哨兵模式确认 `REDIS_MODE` 等配置正确

### Q3: 容器内无法访问宿主机服务

**现象**：容器内无法连接宿主机 MySQL/Redis/MinIO

**排查**：
1. `ip addr show docker0 | grep inet`（通常 `172.17.0.1`）
2. `.env` 中将 `127.0.0.1` 替换为该 IP

### Q4: studio-runtime 反复重启

**现象**：容器状态 Restarting

**排查**：
1. `docker compose logs studio-runtime` 查看日志
2. Python 服务启动必须连 Redis，Redis 不可达会直接失败
3. 检查 `REDIS_HOST` 是否用了 `127.0.0.1`

### Q5: 镜像拉取失败 / 403

**现象**：`docker pull ghcr.io/...` 报 403

**排查**：私有镜像需登录 `echo <PAT> | docker login ghcr.io -u <USER> --password-stdin`，PAT 需 `read:packages` 权限。或在 `.env` 中配置 `GHCR_USERNAME` 和 `GHCR_TOKEN` 后使用 `bash deploy.sh update`（会自动登录仓库并拉取最新镜像）。

### Q6: 端口冲突

**现象**：`bind: address already in use`

**排查**：`netstat -tlnp | grep -E '80|31111|31014|31015'`，在 `.env` 中修改冲突端口。

### Q7: 离线部署镜像加载失败

**现象**：`docker load` 报错

**排查**：
1. 确认 `.env` 中 `IMAGE_SOURCE=offline`
2. 确认 `images/` 和 `dep-images/` 目录下有 `.tar` 文件
3. 确认 `.env` 中 `STUDIO_*_IMAGE` 的值与 `docker images` 显示的 REPOSITORY:TAG 完全一致（`docker load` 后用 `docker images` 查看，注意是否带仓库前缀）
