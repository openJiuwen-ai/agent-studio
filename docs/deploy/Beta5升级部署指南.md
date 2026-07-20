# Beta5 升级部署指南

> 本文面向从 Beta4 及更早版本升级到 **Beta5** 的部署场景，重点说明本版本的**架构整改**与**环境变量变化**。新增部署可参考 [`安装部署指南.md`](../安装部署指南.md)，本文不再重复通用步骤。
>
> 环境变量以源码 `docker/k8s/` 目录下的 YAML 为准（`studio-manager.yaml`、`studio-builder.yaml`、`studio-runtime.yaml`、`studio-console.yaml`）。

---

## 一、架构整改概述

Beta5 对执行面做了拆分与下沉，核心变化两点：

1. **移除 `studio-service`**（Java / Spring Boot，端口 31113）。原执行面的 Agent 执行 / 对话 / 模型调用 / 知识检索 等职责被拆解：
   - 模型调用能力迁入 Python 服务；默认使用 OBS 模型配置直连真实模型，不再依赖原 `studio-service` 路由；如部署方另有独立模型网关，仍可显式配置外部网关；
   - NL2 生成、提示词优化、模型调测等“构建期”能力独立为新的 `studio-builder` 微服务。
2. **新增 `studio-builder`**（Python / FastAPI，端口 31015）。承担原嵌在 `studio-runtime` 镜像内的 `agent_builder` 模块——NL2 接口、提示词优化任务、模型调测等，独立构建、独立伸缩。

服务清单变化：

| 服务 | 技术栈 | 端口 | Beta4 及之前 | Beta5 |
|------|--------|------|--------------|-------|
| studio-console | Nginx + Angular | 80 | ✅ | ✅（nginx 上游需重定向，见三） |
| studio-manager | Spring Boot (Java 17) | 31111 | ✅ | ✅ |
| studio-service | Spring Boot (Java 17) | 31113 | ✅ | ❌ **已移除** |
| studio-runtime | Python (FastAPI) | 31014 | ✅ | ✅ |
| studio-builder | Python (FastAPI) | 31015 | ❌ | ✅ **新增** |

> 服务总数不变（仍为 4 个应用服务），但执行面由“一个 Java service”变为“runtime + builder 两个 Python 服务”。
>
> ⚠️ 旧版命名混淆提示已失效：Beta4 文档里“`studio-service` 容器装 Java `studio-runtime` 模块 JAR”的说明不再适用——Beta5 起不再有 `studio-service`，`studio-runtime` 容器即 Python `agent-runtime`。

### 1.1 依赖关系变化

```
Beta4：                       Beta5：
console → manager             console → manager
        → service ──┐                 → runtime  ──┐
        → runtime ──┤                 → builder ──┤
                    │                              │
manager → service（模型路由）   manager → builder（n2l/提示词）
runtime → service（模型路由）   runtime → OBS 直连模型（默认）
                                      └→ 外部模型网关（可选）
```

- `studio-manager` 不再调用 `studio-service`，改调 `studio-builder`（n2l 生成）与 `studio-runtime`。
- `studio-runtime` 不再经 `studio-service` 做模型路由，默认 `MODEL_CONFIG_STRATEGY=obs` 直连真实模型。仅在部署了独立外部模型网关时配置 `MODEL_ROUTER_API`。

---

## 二、环境变量变化

> 标注说明：🆕 新增 · 🗑️ 移除 · 🔁 改名/改默认值。每个服务仅列出**变化项**，未列出的变量与 Beta4 保持一致，详见 `docker/k8s/<svc>.yaml`。

### 2.1 studio-manager

| 变量 | 变化 | Beta5 取值 / 说明 |
|------|------|-------------------|
| `agent_builder_endpoint` | 🆕 / 🔁（替代 `jiu_wen_service_endpoint`） | `http://studio-builder:31015`，n2l 生成接口调用地址，HTTPS 启动改 `https://` |
| `agent_runtime_endpoint` | 🆕 / 🔁（替代 `jiuwen_base_url`） | `http://studio-runtime:31014`，runtime 调用地址 |
| `jiu_wen_service_endpoint` | 🗑️ | 由 `agent_builder_endpoint` 取代 |
| 对 `studio-service` 的调用 | 🗑️ | manager 不再依赖 service |

其余（数据库 `spring_datasource_*`、Redis `redis_*`、对象存储 `obs_*`、HTTPS `server_ssl_*`、`user_auth_endpoint`、`system_crypt_name`、`auth_sso_validate_url` 等）不变。

### 2.2 studio-runtime

| 变量 | 变化 | Beta5 取值 / 说明 |
|------|------|-------------------|
| `MODEL_ROUTER_API` | 🔁 可选 | 删除旧值 `http://studio-service:31113/v1/agent-builder`；默认不配置。仅使用独立外部模型网关时设置，例如 `https://<model-gateway>/v1/agent-builder`，不得指向 `studio-runtime` 或 `studio-builder` 自身 |
| `MODEL_CONFIG_STRATEGY` | 🔁 默认值 | 默认 `obs`（OBS 直连，绕过模型路由）；可选 `env` / `ir` |

模型缓存、沙箱、OpenSearch、记忆库、`STORE_DB_*`、`IR_LLM_API_KEY`、日志等变量不变。若使用 `MODEL_CONFIG_STRATEGY=ir` 并通过网关解析模型，应同时提供有效的外部 `MODEL_ROUTER_API`。

### 2.3 studio-builder（🆕 全新服务）

完整变量见 `docker/k8s/studio-builder.yaml`，分组如下：

| 分组 | 变量 | 说明 |
|------|------|------|
| 服务监听 | `SERVER_HOST` / `SERVER_PORT` | `0.0.0.0` / `31015` |
| Redis [必填] | `REDIS_HOST` `REDIS_PASSWORD` `REDIS_PORT` `REDIS_MODE` `REDIS_DATABASE`（集群 `REDIS_CLUSTER_NODES`、哨兵 `REDIS_SENTINEL_MASTER` `REDIS_SENTINEL_NODES`） | 与 studio-runtime 同一套 Redis 语义 |
| 对象存储 [必填] | `DATASOURCE_OBS_SERVER` `DATASOURCE_OBS_BUCKET` `DATASOURCE_OBS_AK` `DATASOURCE_OBS_SK` `DATASOURCE_OBS_ENABLE_SSL` | 与 studio-runtime 一致 |
| 模型配置 | `MODEL_CONFIG_STRATEGY` | 默认 `obs` |
| 外部模型网关 [选填] | `MODEL_ROUTER_API` | 默认不配置；仅接入独立外部模型网关时填写 `https://<model-gateway>/v1/agent-builder`，不得填写旧 `studio-service:31113`，也不得指向 builder 自身 |
| 提示词任务持久化 [选填] | `STORE_DB_TYPE`（mysql/gaussdb）`STORE_DB_HOST` `STORE_DB_PORT` `STORE_DB_USER` `STORE_DB_PASSWORD` `STORE_DB_DATABASE`（默认 `agent-builder`）`STORE_DB_SCHEMA` `STORE_DB_SSLMODE` | 不填则仅存内存；与 runtime 共用同一套 `STORE_DB_*` 语义 |
| 日志 | `JIUWEN_LOG_FILE` `JIUWEN_LOG_PATH` `JIUWEN_LOGGING_LOG_FILE` `LOGGING_LOG_PATH` `TGF_LOG_DIR` `LOG_VERBOSE` | 默认写到 `/opt/cloud/logs/` |

> studio-builder 启动时会按需初始化提示词优化任务所需的存储表；`studio-manager` 负责主业务表。`STORE_DB_*` 未完整配置时，提示词任务存储不可按数据库持久化。

### 2.4 studio-service（🗑️ 整体移除）

以下变量随服务一并废弃，升级时从编排中清除，无需再配置：

```
spring_datasource_*   redis_*   obs_*   storage_*   user_auth_endpoint
agent_manager_endpoint   jiuwen_base_url   server_ssl_*   koosearch_endpoint
system_crypt_name   auth_sso_validate_url
```

### 2.5 studio-console

console 容器本身无新增环境变量，但其 nginx 上游（`backend.conf`）需要重定向：

| nginx 变量 | Beta4 | Beta5 |
|-----------|-------|-------|
| `manager_backend` | `studio-manager` | `studio-manager`（不变） |
| `service_backend` | `studio-service:31113` | **需移除** |

> 不要把旧 `$service_backend:31113` location 机械改成 Runtime。Beta5 标准路由中，`/v1/agent-builder/chat/completions`、`/v1/agent-builder/embeddings`、`/v1/agent-builder/rerank` 直达 Builder，其余 `/v1`、`/v2` 请求默认进入 Manager，再由 Manager 按业务语义调用 Runtime 或 Builder。升级时应整体替换为发版包 `docker/compose/config/nginx.conf`（K8s 场景使用 `studio-console.yaml` 中对应配置），不要手工维护旧路由清单。

---

## 三、升级步骤

### 3.1 K8s 部署升级

```
步骤1            步骤2            步骤3                步骤4
删除 service  →  apply builder  →  滚动更新 manager/runtime  →  更新 console
```

```bash
cd docker/k8s   # 或部署包的 k8s/ 目录

# 1) 移除 studio-service（K8s 目录下已无 studio-service.yaml，直接删除旧资源）
kubectl delete deployment studio-service -n default
kubectl delete svc studio-service -n default || true

# 2) 部署新增的 studio-builder
kubectl apply -f studio-builder.yaml

# 3) 滚动更新 manager / runtime（环境变量已变更）
kubectl apply -f studio-manager.yaml
kubectl apply -f studio-runtime.yaml

# 4) 更新 console（nginx 上游重定向）
kubectl apply -f studio-console.yaml

# 观察
kubectl get pods -l app=studio-builder
kubectl rollout status deployment/studio-manager
kubectl rollout status deployment/studio-runtime
```

升级前后校验各 YAML 的 `env` 段已按本文二节调整；镜像 tag 切到 Beta5 版本。

### 3.2 Docker Compose 部署升级

```bash
cd <项目根目录>/deploy

# 1) 拉取/加载 Beta5 镜像（含新增 studio-builder，不再有 studio-service）
bash deploy.sh update

# 2) 确认 .env 已按本文二节更新（见 3.3）

# 3) 重启使编排生效
bash deploy.sh restart

# 4) 验证
bash deploy.sh verify
bash deploy.sh status
```

> `deploy.sh update` 会读取新版 `docker-compose.yml`：旧 `studio-service` 服务块已移除，新增 `studio-builder` 服务块。应从 `.env` 清理 `STUDIO_SERVICE_IMAGE`、`SERVICE_PORT`、`JIUWEN_BASE_URL`、`JIUWEN_BUILDER_URL` 以及指向 `studio-service:31113` 的 `MODEL_ROUTER_API`；如需外部模型网关，再以新的外部 HTTPS 地址单独配置 `MODEL_ROUTER_API`。

---

## 四、回滚

回滚到 Beta4 需同时复原服务与变量：

1. `.env` 恢复 `STUDIO_SERVICE_IMAGE`、`MODEL_ROUTER_API`、`JIUWEN_BUILDER_URL`、旧 `AGENT_RUNTIME_ENDPOINT=http://studio-service:31113` 等旧值，删除 `STUDIO_BUILDER_IMAGE` 与 `STORE_DB_*`（如为本次新增）。
2. K8s：`kubectl delete -f studio-builder.yaml`，重新 `kubectl apply` 旧版 `studio-service.yaml`、`studio-manager.yaml`、`studio-runtime.yaml`、`studio-console.yaml`。
3. Compose：用 Beta4 的 `docker-compose.yml` 与镜像 tag，`bash deploy.sh stop && bash deploy.sh all`。

> ⚠️ 跨版本回滚属破坏性操作，执行前务必备份数据库与对象存储。

---

## 五、升级自检

| 检查项 | 命令 / 方法 |
|--------|------------|
| builder 已就绪 | `kubectl get pods -l app=studio-builder` 全 `Running`；`curl http://<builder_ip>:31015/v1/health` |
| service 已下线 | `kubectl get deploy studio-service` 应返回 NotFound；console 不再有指向 31113 的健康流量 |
| manager 调用 builder | manager 日志无 `studio-builder:31015` 连接失败；n2l / 提示词优化功能可用 |
| 模型调用 | 默认模式下 `MODEL_CONFIG_STRATEGY=obs` 生效，Runtime/Builder 日志无 `studio-service:31113` 报错且模型调用成功；若配置 `MODEL_ROUTER_API`，确认目标是独立外部网关且网关调用成功 |
| 历史会话 / 工作流 | 升级后对存量 Agent / 工作流做一次对话与执行回归（Beta5 修复了控制器与 LLM 节点历史会话问题） |

如出现 builder / runtime 反复重启，先查 Redis 与 OBS 连通性（Python 服务启动必须连 Redis，不可达会直接失败），再查 `STORE_DB_*` 凭证是否含特殊字符（旧版曾因密码特殊字符导致连接失败）。
