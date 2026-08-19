# K8s 部署指南

## 一、概述

openJiuwen AgentStudio 支持通过 Kubernetes 集群部署，适用于需要多实例高可用、横向扩容和滚动更新的场景。

> 4 个应用服务的技术栈和端口详见[部署总览](./deploy-service.md#服务概览)。外部依赖详见[部署总览 — 外部依赖](./deploy-service.md#外部依赖)，K8s 编排**不内置** MySQL/Redis/MinIO，需自行部署或使用外部实例。

---

## 二、环境要求

| 资源 | 最低配置 | 推荐配置 |
|------|---------|---------|
| K8s 集群 | v1.28+ | v1.32 |
| 工作节点 | 8核 / 16GB | 12核+ / 24GB+ |

### 前置条件

| 软件 | 说明 |
|------|------|
| Kubernetes 集群 | 已部署并可正常访问 |
| kubectl | 已配置且可访问集群 |
| 基础设施 | MySQL/Redis/MinIO 或外部实例已就绪 |

---

## 三、资源配额

各服务资源分配参考（双实例，生产高可用）：

| 服务 | 实例数 | 单实例CPU | 单实例内存 | 总CPU | 总内存 |
|------|--------|----------|-----------|-------|--------|
| studio-console | 1 | 0.25核 | 512MB | 0.25核 | 512MB |
| studio-manager | 2 | 2核 | 4GB | 4核 | 8GB |
| studio-runtime | 2 | 2核 | 4GB | 4核 | 8GB |
| studio-builder | 2 | 2核 | 4GB | 4核 | 8GB |

> studio-console 通常只需 1 个实例（Nginx 无状态反向代理），其余服务建议至少 2 个实例以保证高可用。资源配额来源于各服务的 K8s YAML 配置。

---

## 四、部署流程

```
步骤1             步骤2              步骤3            步骤4          步骤5
准备镜像  →  初始化数据库  →  修改YAML配置  →  kubectl apply  →  验证
```

---

## 五、部署步骤

> 从 [Release 页面](https://atomgit.com/openJiuwen/agent-studio/releases) 下载部署包并解压，K8s YAML 文件位于 `deploy/k8s/` 目录下，共 4 个。

### 步骤 1：准备镜像

K8s 部署支持两种镜像获取方式：

**方式一：离线导入**

1. 确认节点架构：

```bash
uname -m    # x86_64 / aarch64
```

2. 从 [Release 页面](https://atomgit.com/openJiuwen/agent-studio/releases) 下载与架构匹配的离线镜像包，传输到每个 K8s 节点。

3. 在每个节点上加载镜像：

```bash
# 加载 4 个服务的离线镜像包
docker load -i studio-manager_*.tar
docker load -i studio-runtime_*.tar
docker load -i studio-builder_*.tar
docker load -i studio-console_*.tar
```

> 镜像名需与 YAML 中 `image` 字段一致。导入后用 `docker images` 确认。

**方式二：在线拉取**

1. 将各 YAML 中 `spec.template.spec.containers.image` 改为镜像仓库地址（如 `ghcr.io/<owner>/openjiuwen_agent_studio/studio-manager:latest`）
2. 将 `imagePullPolicy` 从默认的 `Never` 改为 `Always`
3. 私有仓库需创建 YAML 中已引用的 `default-secret`：

```bash
kubectl create secret docker-registry default-secret \
  --docker-server=ghcr.io \
  --docker-username=<USERNAME> \
  --docker-password=<PAT>
```

### 步骤 2：初始化数据库与对象存储

K8s 编排不内置基础设施，需自行创建数据库和对象存储桶。

**创建数据库（MySQL）**：

```sql
CREATE DATABASE IF NOT EXISTS `agent-builder` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
GRANT ALL PRIVILEGES ON `agent-builder`.* TO 'root'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
```

**创建数据库（GaussDB）**：

> GaussDB 无需额外创建 schema，`DBCOMPATIBILITY = 'M'` 兼容 MySQL 语法，表结构由应用自动创建。

```sql
CREATE DATABASE "agent-builder" TEMPLATE = template0 ENCODING 'UTF8' DBCOMPATIBILITY = 'M';
```

**创建对象存储桶（MinIO 示例）**：

```bash
mc alias set myminio http://<MINIO_IP>:9000 <ACCESS_KEY> <SECRET_KEY>
mc mb myminio/agent-builder
```

> 主业务表由 studio-manager 首次启动时自动创建；studio-builder 会初始化提示词优化任务所需的存储。无需手动创建应用表。

### 步骤 3：修改 YAML 配置

各 YAML 必填配置项：

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

### 步骤 4：启动服务

按顺序启动各服务（先 manager，再 runtime/builder，最后 console）：

```bash
cd deploy/k8s

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

### 步骤 5：安装后验证

K8s 下访问地址：`http://<节点IP>:30001/openjiuwen/`

验证 Pod 健康状态：

```bash
kubectl get pods -o wide
kubectl describe pod -l app=studio-manager
```

> 容器内日志路径详见[部署总览 — 服务概览](./deploy-service.md#服务概览)。

---

## 六、常用运维命令

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

# 查看滚动更新状态
kubectl rollout status deployment/studio-manager

# 回滚到上一个版本
kubectl rollout undo deployment/studio-manager

# 查看 Service 和端口
kubectl get svc
```

---

## 七、版本升级

K8s 部署通过更新镜像 tag 并触发滚动更新来完成版本升级：

```bash
# 方式一：修改 YAML 中的 image tag 后重新 apply
vi deploy/k8s/studio-manager.yaml   # 修改 image 中的 tag
kubectl apply -f deploy/k8s/studio-manager.yaml

# 方式二：直接设置新镜像
kubectl set image deployment/studio-manager studio-manager=<new-image>:<new-tag>

# 查看滚动更新进度
kubectl rollout status deployment/studio-manager
```

回滚：

```bash
# 回滚到上一个版本
kubectl rollout undo deployment/studio-manager

# 查看发布历史
kubectl rollout history deployment/studio-manager
```

---

## 八、常见问题

### Q1: Pod 状态为 CrashLoopBackOff

**排查**：
1. `kubectl logs <pod-name>` 查看容器日志
2. Python 服务（runtime/builder）启动必须连 Redis，Redis 不可达会直接失败
3. 检查 YAML 中 `REDIS_HOST` 是否正确指向外部 Redis 地址

### Q2: Pod 状态为 ImagePullBackOff

**排查**：
1. 确认镜像名和 tag 正确：`kubectl describe pod <pod-name>` 查看 Events
2. 私有仓库需配置 `imagePullSecrets`
3. 离线导入时确认 `imagePullPolicy` 设为 `IfNotPresent` 或 `Never`
4. 确认镜像已 `docker load` 到目标节点：`docker images | grep studio`

### Q3: Pod 状态为 Pending

**排查**：
1. `kubectl describe pod <pod-name>` 查看调度失败原因
2. 检查节点资源是否充足（CPU/内存）
3. 检查节点是否被 taint 污染：`kubectl get nodes -o jsonpath='{.items[*].metadata.name}' | xargs -I{} kubectl describe node {} | grep -A5 Taints`

### Q4: 服务间无法通信

**排查**：
1. 确认所有服务在同一个 namespace：`kubectl get pods --all-namespaces`
2. 确认 Service 已创建且 ClusterIP 正常：`kubectl get svc`
3. 确认 `agent_builder_endpoint` 指向 `http://studio-builder:31015`
4. 确认 `agent_runtime_endpoint` 指向 `http://studio-runtime:31014`

### Q5: 数据库表未自动创建

**排查**：
1. 确认 `SPRING_DATASOURCE_URL` 正确指向外部数据库
2. 确认数据库用户有 DDL 权限
3. `kubectl logs deployment/studio-manager` 查看 Java 启动日志中的建表信息
4. GaussDB 需确保 `DBCOMPATIBILITY = 'M'`
