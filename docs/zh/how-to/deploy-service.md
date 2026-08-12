# 安装部署指南

## 一、概述

openJiuwen AgentStudio 包含 4 个应用服务，支持两种部署方式：基于 Docker Compose 单机部署（见三、四章）和基于 Kubernetes 集群部署（见第五章）。默认通过 Docker Compose 编排部署：

| 服务 | 技术栈 | 默认端口 | 说明 |
|------|--------|----------|------|
| studio-console | Nginx + Angular | 80 | 前端控制台 + API 反向代理 |
| studio-manager | Spring Boot (Java 17) | 31111 | 管理面：Agent/知识库/模型/工具/MCP 管理 |
| studio-runtime | Python (FastAPI) | 31014 | 执行面：Agent/工作流执行、发布调用、LLM/MCP/记忆 |
| studio-builder | Python (FastAPI) | 31015 | 构建面：NL2、Prompt、模型调测 |

部署方案内置基础设施（MySQL、Redis、MinIO），无需提前部署外部依赖。也支持使用外部基础设施。编排文件默认包含 8 个服务：

| 类型 | 服务 | 说明 |
|------|------|------|
| 基础设施 | mysql、redis、minio、minio-init | 由 `deploy.sh` 自动启动和初始化 |
| 应用服务 | studio-console、studio-manager、studio-runtime、studio-builder | 业务服务 |

| 依赖 | 版本 | 必选 | 说明 |
|------|------|------|------|
| MySQL / GaussDB | 8.0+ | ✅ | 主数据存储。默认驱动 `org.mariadb.jdbc.Driver`，GaussDB 需改为 `com.huawei.opengauss.jdbc.Driver` |
| Redis | 7.x | ✅ | 缓存/会话/变量存储，支持单机/集群/哨兵模式 |
| MinIO / OBS | latest | ✅ | 对象存储 |
| OpenSearch | 2.x | ❌ | 记忆库向量存储，启用记忆库时必需 |

> 从 Beta5 开始，原 Java `studio-service` 已移除，其能力分别下沉到 Manager、Runtime 和 Builder；部署中不再使用 31113 端口或 `STUDIO_SERVICE_IMAGE`。

> 📁 **部署目录**：所有部署相关文件统一在 `deploy/` 目录下，使用同一套脚本和编排文件，在线/离线仅通过 `.env` 中的 `IMAGE_SOURCE` 区分。

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
| Docker Compose | V2 | 服务编排（`docker compose` 命令） |

> 部署前请确保 Docker 和 Docker Compose 已安装并正常运行：`docker --version && docker compose version`

> 本文档中 `<项目根目录>` 指项目 clone 的根目录，如 `/home/user/agent-studio`。

---

## 三、在线部署

> **适用场景**：部署机器可访问外网，可拉取 GHCR/Docker Hub 镜像。
>
> **前置条件**：已安装 Docker 和 Docker Compose；应用镜像已发布到镜像仓库（镜像构建由维护者完成，本文档不涉及）。
>
> **部署脚本**：`deploy/deploy.sh` — 一个脚本管理全生命周期。

```
步骤1                   步骤2              步骤3
clone 代码 + 配置 .env → deploy.sh all → 浏览器访问
```

### 步骤 1：获取代码并配置环境

```bash
# 克隆代码
git clone <仓库地址> && cd agent-studio

# 配置环境变量
cd deploy
cp .env.template .env
vi .env
```

**必填配置项**（`.env`）：

```bash
# 镜像来源（四选一：ghcr / dockerhub / offline / custom）
IMAGE_SOURCE=ghcr
IMAGE_TAG=latest

# GHCR 镜像仓库地址
GHCR_IMAGE_REPOSITORY=ghcr.io/<owner>/openjiuwen_agent_studio

# 私有镜像仓库登录凭证（公开镜像可留空）
GHCR_USERNAME=<USERNAME>
GHCR_TOKEN=<PAT>
```

> `offline` 和 `custom` 模式下还需配置 `STUDIO_*_IMAGE` 镜像名，详见[四、离线部署](#四离线部署)。

使用内置依赖时，数据库/Redis/MinIO 等配置项已在 `.env` 中预填默认值，一般无需修改。使用外部依赖时，需将对应地址和凭证替换为实际值。详见文件内注释。

### 步骤 2：一键部署

```bash
cd <项目根目录>/deploy
bash deploy.sh all
```

脚本自动执行：登录镜像仓库 → 拉取镜像 → 初始化基础设施（MySQL/Redis/MinIO + 数据库 + MinIO 桶） → 启动应用服务 → 健康检查 → 输出访问地址。

> `all` 命令会先拉取镜像再启动，适合**首次部署**。后续更新使用 `update`，重启使用 `restart`。

> 💡 默认部署不含日志聚合栈。如需在 Grafana 中集中查询日志（替代跨容器 grep），见下方「十、可观测性（日志聚合）」。

### 步骤 3：验证访问

浏览器访问：`http://<IP>/openjiuwen/`

---

## 四、离线部署

> **适用场景**：部署机器无法访问外网。
>
> **核心思路**：在外部（有网机器）下载 Docker 镜像并导出为 tar 文件，传输到目标机器，由 `deploy.sh` 自动导入部署。
>
> **前置条件**：目标机器已安装 Docker 和 Docker Compose。
>
> **部署脚本**：与在线部署使用同一个 `deploy.sh`，`.env` 中 `IMAGE_SOURCE=offline` 即可。

```
 第一阶段：有网机器（下载镜像）            第二阶段：目标机器（导入部署）
┌──────────────────────────────┐        ┌──────────────────────────────┐
│ 步骤1: 下载并导出镜像 tar 包  │        │ 步骤1: 准备部署目录 + 放置 tar │
│ 步骤2: 传输到目标机器         │──传输──▶│ 步骤2: 配置 .env              │
│                              │        │ 步骤3: deploy.sh all          │
└──────────────────────────────┘        └──────────────────────────────┘
```

### 第一阶段：在有网机器上下载镜像

#### 步骤 1：下载并导出应用镜像

登录镜像仓库后，拉取 4 个应用镜像，重命名为短名再导出为 tar（短名需与目标机器 `.env` 中的 `STUDIO_*_IMAGE` 一致）：

```bash
# 登录 GHCR（公开镜像可跳过）
echo <PAT> | docker login ghcr.io -u <USERNAME> --password-stdin

REGISTRY=ghcr.io/<owner>/openjiuwen_agent_studio
for SVC in studio-manager studio-console studio-runtime studio-builder; do
  docker pull ${REGISTRY}/${SVC}:latest
  docker tag  ${REGISTRY}/${SVC}:latest ${SVC}:latest
  docker save ${SVC}:latest -o ${SVC}.tar
done
```

> 也可从 Docker Hub 下载（镜像名形如 `<owner>/openjiuwen_agent_studio:studio-<svc>-latest`），按相同方式 retag、save。

#### 导出依赖镜像（使用内置基础设施时需要）

若使用内置 MySQL/Redis/MinIO，还需在有网机器上拉取并导出依赖镜像：

```bash
docker pull mysql:8.0          && docker save mysql:8.0          -o mysql.tar
docker pull redis:7            && docker save redis:7            -o redis.tar
docker pull minio/minio:latest && docker save minio/minio:latest -o minio.tar
docker pull minio/mc:latest    && docker save minio/mc:latest    -o mc.tar
```

> 也可使用 `deploy/scripts/export-dependency-images.sh` 一键导出。

#### 步骤 2：传输到目标机器

将应用镜像 tar 传到目标机器的 `deploy/images/`，依赖镜像 tar 传到 `deploy/dep-images/`：

```bash
scp studio-*.tar user@target-host:~/deploy/images/
scp mysql.tar redis.tar minio.tar mc.tar user@target-host:~/deploy/dep-images/
```

### 第二阶段：在目标机器上部署

#### 步骤 1：准备部署目录

将项目仓库的 `deploy/` 目录传到目标机器（路径任意，下文以 `~/deploy` 为例），并确保 `images/`、`dep-images/` 两个子目录已放入对应的 tar 文件：

```
~/deploy/
├── deploy.sh
├── docker-compose.yml
├── .env.template
├── init.sql
├── config/nginx.conf
├── images/        ← 4 个应用镜像 .tar（第一阶段导出）
└── dep-images/    ← 依赖镜像 .tar（MySQL/Redis/MinIO/MC，使用内置基础设施时）
```

#### 步骤 2：配置环境

镜像导入由 `deploy.sh all` 自动完成（检测到 `IMAGE_SOURCE=offline` 时自动 `docker load` `images/` 与 `dep-images/` 下的 tar）。只需配置 `.env`：

```bash
cd ~/deploy
cp .env.template .env
vi .env
```

离线部署 `.env` 关键配置：

```bash
IMAGE_SOURCE=offline

# 镜像名需与导入后的本地镜像名一致（默认用 latest 短名）
STUDIO_CONSOLE_IMAGE=studio-console:latest
STUDIO_MANAGER_IMAGE=studio-manager:latest
STUDIO_RUNTIME_IMAGE=studio-runtime:latest
STUDIO_BUILDER_IMAGE=studio-builder:latest
```

> 使用内置依赖时，数据库/Redis/MinIO 默认值指向内置基础设施，无需修改。使用外部依赖时，替换为实际地址和凭证。

#### 步骤 3：一键部署

```bash
bash deploy.sh all
```

自动执行：加载镜像（`docker load`）→ 初始化基础设施 → 启动应用服务 → 健康检查 → 输出访问地址。

> 与在线部署使用完全相同的命令，只是镜像来源不同（`docker load` 替代 `docker pull`）。

浏览器访问：`http://<IP>/openjiuwen/`

---

## 五、基于K8s部署

> **适用场景**：需要高可用、集群部署的生产环境。
>
> **前置条件**：已部署 Kubernetes 集群（v1.32 推荐），`kubectl` 已配置且可访问集群；基础设施（MySQL/Redis/MinIO 或外部实例）已就绪。
>
> **说明**：K8s 部署**不使用 `deploy.sh`**，直接通过 `kubectl apply` YAML 完成。K8s 编排不内置 MySQL/Redis/MinIO，需自行部署或使用外部实例。

### 5.1 K8s 资源配额

各服务资源分配参考（双实例，生产高可用）：

| 服务 | 实例数 | 单实例CPU | 单实例内存 | 总CPU | 总内存 |
|------|--------|----------|-----------|-------|--------|
| studio-console | 1 | 0.25核 | 512MB | 0.25核 | 512MB |
| studio-manager | 2 | 2核 | 4GB | 4核 | 8GB |
| studio-runtime | 2 | 2核 | 4GB | 4核 | 8GB |
| studio-builder | 2 | 2核 | 4GB | 4核 | 8GB |

> K8s 部署时 studio-console 通常只需 1 个实例（Nginx 无状态反向代理），其余服务建议至少 2 个实例以保证高可用。资源配额来源于各服务的 K8s YAML 配置。

### 5.2 部署流程

```
步骤1             步骤2              步骤3            步骤4          步骤5
准备镜像  →  初始化数据库  →  修改YAML配置  →  kubectl apply  →  验证
```

### 5.3 部署步骤

#### 步骤 1：准备镜像

K8s 部署支持两种镜像获取方式：

**方式一：在线拉取**

配置各 YAML 中 `spec.template.spec.containers.image` 为镜像仓库地址（如 `ghcr.io/<owner>/openjiuwen_agent_studio/studio-manager:latest`），K8s 自动从仓库拉取。私有仓库需配置 `imagePullSecrets`。

**方式二：离线导入**

在每个 K8s 节点上加载镜像 tar（参考[四、离线部署](#四离线部署)的镜像导出方式），并将各 YAML 中 `imagePullPolicy` 设为 `IfNotPresent` 或 `Never`：

```bash
# 在每个 K8s 节点执行
docker load -i studio-manager.tar
docker load -i studio-runtime.tar
docker load -i studio-builder.tar
docker load -i studio-console.tar
```

> 镜像名需与 YAML 中 `image` 字段一致。导入后用 `docker images` 确认。

#### 步骤 2：初始化数据库与对象存储

K8s 编排不内置基础设施，需自行创建数据库和对象存储桶。

**创建数据库（MySQL）**：

```sql
CREATE DATABASE IF NOT EXISTS `agent_studio` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
GRANT ALL PRIVILEGES ON `agent_studio`.* TO 'root'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
```

**创建数据库（GaussDB）**：

> GaussDB 无需额外创建 schema，`DBCOMPATIBILITY = 'M'` 兼容 MySQL 语法，表结构由应用自动创建。

```sql
CREATE DATABASE agent_studio TEMPLATE = template0 ENCODING 'UTF8' DBCOMPATIBILITY = 'M';
```

**创建对象存储桶（MinIO 示例）**：

```bash
mc alias set myminio http://<MINIO_IP>:9000 <ACCESS_KEY> <SECRET_KEY>
mc mb myminio/agent-builder
```

> 主业务表由 studio-manager 首次启动时自动创建；studio-builder 会初始化提示词优化任务所需的存储。无需手动创建应用表。

#### 步骤 3：修改 YAML 配置

K8s YAML 文件位于源码 `docker/k8s/` 目录（或部署包的 `k8s/` 目录下），共 4 个：

| YAML 文件 | 必填配置 |
|----------|---------|
| studio-manager.yaml | 镜像信息、数据库（MySQL/GaussDB）、Redis、OBS |
| studio-runtime.yaml | 镜像信息、Redis、OBS |
| studio-builder.yaml | 镜像信息、Redis、提示词任务数据库、OBS |
| studio-console.yaml | 镜像信息 |

修改每个 YAML 中 `spec.template.spec.containers.env` 的环境变量：

> **重要**：每个 YAML 中标记为 `[必填]` 的环境变量必须配置，`[选填]` 项默认值通常无需修改。

**studio-runtime.yaml 关键配置项**（示例）：

```yaml
# [必填] Redis
- name: REDIS_HOST
  value: '<REDIS_IP>'
- name: REDIS_PORT
  value: '6379'
- name: REDIS_PASSWORD
  value: '<REDIS_PASSWORD>'

# [必填] 对象存储
- name: DATASOURCE_OBS_SERVER
  value: '<OBS_URL>'
- name: DATASOURCE_OBS_BUCKET
  value: '<BUCKET_NAME>'
- name: DATASOURCE_OBS_AK
  value: '<AK>'
- name: DATASOURCE_OBS_SK
  value: '<SK>'

# 模型配置默认从 OBS 读取并由 runtime 直连模型
- name: MODEL_CONFIG_STRATEGY
  value: 'obs'
```

`studio-builder.yaml` 还需要配置 Redis、对象存储和 `STORE_DB_*`。其健康检查端口为 `31015`，Manager 中的 `agent_builder_endpoint` 应指向 `http://studio-builder:31015`。

> HTTPS 启动和 Redis 集群/哨兵配置详见各 YAML 中对应注释。
>
#### 步骤 4：启动服务

按顺序启动各服务（先 manager，再 runtime/builder，最后 console）：

```bash
cd docker/k8s   # 或部署包的 k8s/ 目录

kubectl apply -f studio-manager.yaml
kubectl apply -f studio-runtime.yaml
kubectl apply -f studio-builder.yaml
kubectl apply -f studio-console.yaml
```

查看 Pod 状态：

```bash
kubectl get pods
```

预期所有 Pod 状态为 `Running`。

#### 步骤 5：安装后验证

参见[六、安装后验证](#六安装后验证)。

K8s 下访问地址：`http://<节点IP>:30001/openjiuwen/`

### 5.4 K8s 常用运维命令

```bash
# 查看各服务 Pod
kubectl get pods -l app=studio-manager
kubectl get pods -l app=studio-runtime
kubectl get pods -l app=studio-builder
kubectl get pods -l app=studio-console

# 查看服务日志
kubectl logs -f deployment/studio-manager
kubectl logs -f deployment/studio-runtime
kubectl logs -f deployment/studio-builder
kubectl logs -f deployment/studio-console

# 重启服务（滚动更新）
kubectl rollout restart deployment/studio-manager

# 扩缩容
kubectl scale deployment/studio-runtime --replicas=3
```

---

## 六、安装后验证

```bash
cd <项目根目录>/deploy    # 在线部署
cd ~/deploy  # 离线部署

bash deploy.sh verify
bash deploy.sh status
```

**常见日志查看**：

```bash
bash deploy.sh logs <服务名>
```

**容器内日志路径**：

| 服务 | 路径 |
|------|------|
| studio-manager | `/opt/cloud/studio-manager/logs/studio-agent-manager.log` |
| studio-runtime | `/opt/cloud/logs/jiuwen_python.log` |
| studio-builder | `/opt/cloud/logs/agent-builder/common.log` |
| studio-console | `/opt/cloud/wiseagent-nginx/logs/error.log` |

---

## 七、版本升级与回滚

### 在线升级

```bash
cd <项目根目录>/deploy
bash deploy.sh update       # 拉取最新镜像 → 初始化数据库 → 重启应用 → 验证
```

> 升级期间短暂不可用。如需零停机，请多实例 + 负载均衡。

### 在线回滚

```bash
cd <项目根目录>/deploy

# 修改 .env 中的 IMAGE_TAG 为旧版本
vi .env

# 重启
bash deploy.sh restart
```

### 离线升级

1. 在外部获取新版本镜像 tar 包并传输到目标机器
2. 替换 `images/` 目录下的 tar 文件
3. 更新 `.env` 中的 `STUDIO_*_IMAGE` 镜像 tag（如版本号变化）
4. 执行：

```bash
cd ~/deploy
bash deploy.sh update
```

### 离线回滚

```bash
# 替换 images/ 下的旧版本 tar 文件，恢复 .env 中的旧 tag
cd ~/deploy
bash deploy.sh stop
bash deploy.sh all
```

---

## 八、卸载与清理

```bash
cd <项目根目录>/deploy    # 在线部署
cd ~/deploy  # 离线部署

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

## 九、常用命令参考

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

# 可观测性 / 日志聚合（可选，详见第十章）
bash deploy.sh logging              # L1 单机日志栈（victoria-logs+vector+grafana，本机）
bash deploy.sh logging-remote       # L2：app 节点远程 vector（push 到监控节点）
bash deploy.sh monitor              # L2：监控节点日志栈（victoria-logs+grafana+gateway）
```

---

## 十、可观测性（日志聚合）

> ⚠️ **适用范围**：本章方案只适用于 **docker-compose 部署**（第三章在线 / 第四章离线）。
> **K8s 部署**（第五章）请使用日志采集 DaemonSet 和集中式日志存储，本章 Compose 方案不适用。

平台内置**可选**的日志聚合栈，可在 Grafana 中集中查询五个 app 服务（manager/service/runtime/builder/console）的日志，替代跨容器 `docker logs` / `grep`。两种部署模式：

| 模式 | 适用 | 存储 | 技术栈 | 启停入口 |
|---|---|---|---|---|
| **L1 单机** | 所有服务同一台主机 | 本地文件系统 | **VictoriaLogs** + Vector + Grafana | `./deploy.sh logging` |
| **L2 跨节点** | app 与监控分机部署 | 监控节点本地盘 | **VictoriaLogs**（全文索引）+ Vector + Grafana + gateway | 监控节点 `./deploy.sh monitor` + app 节点 `./deploy.sh logging-remote` |

> L1/L2 统一使用 VictoriaLogs（全文索引，查询秒级；本地存储，无对象存储依赖）。查询和排障方式一致，详见 [`deploy/config/observability-readme.md`](../deploy/config/observability-readme.md)。

### 10.1 L1 单机模式（推荐先试）

日志聚合栈与 app 同机，一条命令：

```bash
cd deploy
./deploy.sh start          # 先确保 app 服务在运行（日志才会写入命名卷）
./deploy.sh logging        # 启动日志栈（victoria-logs/vector/grafana）
```

启动后访问 Grafana：`http://<IP>:3000/`（默认 admin/admin），Explore → VictoriaLogs 查询：
```text
_stream:{service=~"manager|service|runtime|builder|console"} ERROR
```
停止：`./deploy.sh logging stop`。

### 10.2 L2 跨节点模式（生产）

app 与监控分机时：Vector 跟 app 走、VictoriaLogs + Grafana + gateway 集中在监控节点、**本地存储**（无对象存储）。

**监控节点**（只用 `monitor` 子命令）：
```bash
cd deploy
./deploy.sh monitor          # 启动（首次生成 observability/.env，修改 TLS 地址和读写口令后再跑）
```

**每个 app 节点**（先 app 后 vector，顺序不能反）：
```bash
cd deploy
./deploy.sh start          # 1) 先启动 app 服务（建立命名卷）
./deploy.sh logging-remote # 2) 再启动远程 vector（push 到监控节点 gateway）
```

监控节点和 app 节点统一使用 `deploy/observability/.env`。app 节点需设置唯一的
`NODE_NAME`，并把 `LOGS_GATEWAY_HOST` 配置为监控节点地址。旧版 `.env.vector`
中的配置需要合并到 `.env`，该文件已不再单独使用。

**前提**：监控节点 ↔ app 节点网络可达；所有节点时钟同步（chrony/NTP）。

### 10.3 日志保留周期

- **L1/L2（VictoriaLogs）**：通过 `VICTORIA_LOGS_RETENTION` 配置，默认 7 天，超期自动清理。
- Java、Python runtime 和 NGINX 日志使用正文中的真实事件时间，首次导入历史日志不会污染“最近日志”查询。
- 两者均与 app 本地 audit（180 天）相互独立。

### 10.4 更多

完整架构图、LogsQL 示例、排障和演进路径见 [`deploy/config/observability-readme.md`](../deploy/config/observability-readme.md)。

---

## 十一、常见问题

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
3. 确认 `.env` 中 `STUDIO_*_IMAGE` 的 tag 与导入后的本地镜像名一致（`docker load` 后用 `docker images` 查看）
