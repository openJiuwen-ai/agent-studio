# Installation and Deployment Guide

## 1. Overview

openJiuwen AgentStudio contains 4 application services, supporting two deployment methods: Docker Compose single-machine deployment (see Sections 3 and 4) and Kubernetes cluster deployment (see Section 5). Default deployment is via Docker Compose orchestration:

| Service | Tech stack | Default port | Description |
|---------|-----------|-------------|-------------|
| studio-console | Nginx + Angular | 80 | Frontend console + API reverse proxy |
| studio-manager | Spring Boot (Java 17) | 31111 | Management plane: Agent/knowledge base/model/tool/MCP management |
| studio-runtime | Python (FastAPI) | 31014 | Execution plane: Agent/workflow execution, published calls, LLM/MCP/memory |
| studio-builder | Python (FastAPI) | 31015 | Build plane: NL2, Prompt, model tuning |

The deployment plan includes built-in infrastructure (MySQL, Redis, MinIO), no need to pre-deploy external dependencies. External infrastructure is also supported. The orchestration file includes 8 services by default:

| Type | Services | Description |
|------|---------|-------------|
| Infrastructure | mysql, redis, minio, minio-init | Auto-started and initialized by `deploy.sh` |
| Application services | studio-console, studio-manager, studio-runtime, studio-builder | Business services |

| Dependency | Version | Required | Description |
|-----------|---------|----------|-------------|
| MySQL / GaussDB | 8.0+ | ✅ | Main data storage. Default driver `org.mariadb.jdbc.Driver`; for GaussDB change to `com.huawei.opengauss.jdbc.Driver` |
| Redis | 7.x | ✅ | Cache/session/variable storage, supports standalone/cluster/sentinel modes |
| MinIO / OBS | latest | ✅ | Object storage |
| OpenSearch | 2.x | ❌ | Memory store vector storage; required when enabling memory store |

> From Beta5, the original Java `studio-service` has been removed; its capabilities were split into Manager, Runtime, and Builder; port 31113 or `STUDIO_SERVICE_IMAGE` are no longer used in deployment.

> 📁 **Deployment directory**: All deployment-related files are under the `deploy/` directory, using the same set of scripts and orchestration files; online/offline is distinguished only by `IMAGE_SOURCE` in `.env`.

---

## 2. Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 8 cores | 12+ cores |
| Memory | 16GB | 24GB+ |
| Disk | 50GB | 100GB |

Service resource allocation:

| Service | CPU | Memory |
|---------|-----|--------|
| studio-console | 0.5 core | 512MB |
| studio-manager | 2 cores | 4GB |
| studio-runtime | 2 cores | 4GB |
| studio-builder | 2 cores | 4GB |

### Prerequisites

| Software | Version | Description |
|----------|---------|-------------|
| Docker | ≥ 19.03 | Container runtime |
| Docker Compose | V2 | Service orchestration (`docker compose` command) |

> Before deployment, ensure Docker and Docker Compose are installed and running: `docker --version && docker compose version`

> In this document, `<project-root>` refers to the root directory of the cloned project, e.g. `/home/user/agent-studio`.

---

## 3. Online Deployment

> **Applicable scenario**: Deployment machine can access the internet and pull GHCR/Docker Hub images.
>
> **Prerequisites**: Docker and Docker Compose installed; application images published to image repository (image building is done by maintainers, not covered in this document).
>
> **Deployment script**: `deploy/deploy.sh` — one script manages the full lifecycle.

```
Step 1                  Step 2             Step 3
Clone code + config .env → deploy.sh all → Browser access
```

### Step 1: Get Code and Configure Environment

```bash
# Clone code
git clone <repository-url> && cd agent-studio

# Configure environment variables
cd deploy
cp .env.template .env
vi .env
```

**Required config items** (`.env`):

```bash
# Image source (choose one: ghcr / dockerhub / offline / custom)
IMAGE_SOURCE=ghcr
IMAGE_TAG=latest

# GHCR image repository address
GHCR_IMAGE_REPOSITORY=ghcr.io/<owner>/openjiuwen_agent_studio

# Private image repository login credentials (leave empty for public images)
GHCR_USERNAME=<USERNAME>
GHCR_TOKEN=<PAT>
```

> For `offline` and `custom` modes, also configure `STUDIO_*_IMAGE` image names; see [Section 4: Offline Deployment](#4-offline-deployment).

When using built-in dependencies, database/Redis/MinIO config items are pre-filled with defaults in `.env` and generally don't need modification. When using external dependencies, replace corresponding addresses and credentials with actual values. See comments in the file for details.

### Step 2: One-Click Deployment

```bash
cd <project-root>/deploy
bash deploy.sh all
```

The script automatically: logs into image repository → pulls images → initializes infrastructure (MySQL/Redis/MinIO + database + MinIO buckets) → starts application services → health check → outputs access address.

> The `all` command pulls images first then starts, suitable for **first deployment**. For subsequent updates use `update`, for restart use `restart`.

> 💡 Default deployment does not include a log aggregation stack. For centralized log querying in Grafana (replacing cross-container grep), see "Section 10: Observability (Log Aggregation)" below.

### Step 3: Verify Access

Browser access: `http://<IP>/openjiuwen/`

---

## 4. Offline Deployment

> **Applicable scenario**: Deployment machine cannot access the internet.
>
> **Core approach**: Download Docker images externally (on a networked machine) and export as tar files, transfer to target machine, and `deploy.sh` automatically imports and deploys.
>
> **Prerequisites**: Docker and Docker Compose installed on target machine.
>
> **Deployment script**: Same `deploy.sh` as online deployment; set `IMAGE_SOURCE=offline` in `.env`.

```
Phase 1: Networked machine (download images)        Phase 2: Target machine (import & deploy)
┌──────────────────────────────────────┐        ┌──────────────────────────────────────┐
│ Step 1: Download and export image tar │        │ Step 1: Prepare deploy dir + place tar│
│ Step 2: Transfer to target machine    │──xfer─▶│ Step 2: Configure .env                │
│                                       │        │ Step 3: deploy.sh all                 │
└──────────────────────────────────────┘        └──────────────────────────────────────┘
```

### Phase 1: Download Images on Networked Machine

#### Step 1: Download and Export Application Images

After logging into the image repository, pull 4 application images, rename to short names, then export as tar (short names must match `STUDIO_*_IMAGE` in target machine's `.env`):

```bash
# Login to GHCR (skip for public images)
echo <PAT> | docker login ghcr.io -u <USERNAME> --password-stdin

REGISTRY=ghcr.io/<owner>/openjiuwen_agent_studio
for SVC in studio-manager studio-console studio-runtime studio-builder; do
  docker pull ${REGISTRY}/${SVC}:latest
  docker tag  ${REGISTRY}/${SVC}:latest ${SVC}:latest
  docker save ${SVC}:latest -o ${SVC}.tar
done
```

> Can also download from Docker Hub (image names like `<owner>/openjiuwen_agent_studio:studio-<svc>-latest`), retag and save the same way.

#### Export Dependency Images (when using built-in infrastructure)

If using built-in MySQL/Redis/MinIO, also pull and export dependency images on the networked machine:

```bash
docker pull mysql:8.0          && docker save mysql:8.0          -o mysql.tar
docker pull redis:7            && docker save redis:7            -o redis.tar
docker pull minio/minio:latest && docker save minio/minio:latest -o minio.tar
docker pull minio/mc:latest    && docker save minio/mc:latest    -o mc.tar
```

> Can also use `deploy/scripts/export-dependency-images.sh` for one-click export.

#### Step 2: Transfer to Target Machine

Transfer application image tars to `deploy/images/` and dependency image tars to `deploy/dep-images/`:

```bash
scp studio-*.tar user@target-host:~/deploy/images/
scp mysql.tar redis.tar minio.tar mc.tar user@target-host:~/deploy/dep-images/
```

### Phase 2: Deploy on Target Machine

#### Step 1: Prepare Deployment Directory

Transfer the project's `deploy/` directory to the target machine (any path, `~/deploy` used as example below), and ensure `images/` and `dep-images/` subdirectories contain the corresponding tar files:

```
~/deploy/
├── deploy.sh
├── docker-compose.yml
├── .env.template
├── init.sql
├── config/nginx.conf
├── images/        ← 4 application image .tars (exported in Phase 1)
└── dep-images/    ← Dependency image .tars (MySQL/Redis/MinIO/MC, when using built-in infrastructure)
```

#### Step 2: Configure Environment

Image import is done automatically by `deploy.sh all` (auto `docker load` tars in `images/` and `dep-images/` when `IMAGE_SOURCE=offline` is detected). Just configure `.env`:

```bash
cd ~/deploy
cp .env.template .env
vi .env
```

Key config for offline deployment `.env`:

```bash
IMAGE_SOURCE=offline

# Image names must match local image names after import (default: latest short names)
STUDIO_CONSOLE_IMAGE=studio-console:latest
STUDIO_MANAGER_IMAGE=studio-manager:latest
STUDIO_RUNTIME_IMAGE=studio-runtime:latest
STUDIO_BUILDER_IMAGE=studio-builder:latest
```

> When using built-in dependencies, database/Redis/MinIO defaults point to built-in infrastructure; no changes needed. When using external dependencies, replace with actual addresses and credentials.

#### Step 3: One-Click Deployment

```bash
bash deploy.sh all
```

Auto-executes: load images (`docker load`) → initialize infrastructure → start application services → health check → output access address.

> Uses the exact same command as online deployment, only the image source differs (`docker load` instead of `docker pull`).

Browser access: `http://<IP>/openjiuwen/`

---

## 5. K8s Deployment

> **Applicable scenario**: Production environments requiring high availability and cluster deployment.
>
> **Prerequisites**: Kubernetes cluster deployed (v1.32 recommended), `kubectl` configured and can access cluster; infrastructure (MySQL/Redis/MinIO or external instances) ready.
>
> **Note**: K8s deployment **does not use `deploy.sh`**; done directly via `kubectl apply` YAML. K8s orchestration does not include built-in MySQL/Redis/MinIO; deploy your own or use external instances.

### 5.1 K8s Resource Quotas

Service resource allocation reference (dual instances, production HA):

| Service | Instances | CPU per instance | Memory per instance | Total CPU | Total memory |
|---------|-----------|-----------------|--------------------|-----------:|-------------:|
| studio-console | 1 | 0.25 core | 512MB | 0.25 core | 512MB |
| studio-manager | 2 | 2 cores | 4GB | 4 cores | 8GB |
| studio-runtime | 2 | 2 cores | 4GB | 4 cores | 8GB |
| studio-builder | 2 | 2 cores | 4GB | 4 cores | 8GB |

> For K8s deployment, studio-console typically needs only 1 instance (Nginx stateless reverse proxy); other services should have at least 2 instances for HA. Resource quotas come from each service's K8s YAML config.

### 5.2 Deployment Flow

```
Step 1          Step 2           Step 3            Step 4          Step 5
Prepare images → Init database → Modify YAML config → kubectl apply → Verify
```

### 5.3 Deployment Steps

#### Step 1: Prepare Images

K8s deployment supports two image acquisition methods:

**Method 1: Online Pull**

Configure `spec.template.spec.containers.image` in each YAML to the image repository address (e.g. `ghcr.io/<owner>/openjiuwen_agent_studio/studio-manager:latest`); K8s auto-pulls from repository. Private repositories need `imagePullSecrets`.

**Method 2: Offline Import**

Load image tars on each K8s node (refer to image export method in [Section 4: Offline Deployment](#4-offline-deployment)), and set `imagePullPolicy` to `IfNotPresent` or `Never` in each YAML:

```bash
# Execute on each K8s node
docker load -i studio-manager.tar
docker load -i studio-runtime.tar
docker load -i studio-builder.tar
docker load -i studio-console.tar
```

> Image names must match the `image` field in YAML. After import, verify with `docker images`.

#### Step 2: Initialize Database and Object Storage

K8s orchestration does not include infrastructure; create database and object storage bucket yourself.

**Create database (MySQL)**:

```sql
CREATE DATABASE IF NOT EXISTS `agent_studio` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
GRANT ALL PRIVILEGES ON `agent_studio`.* TO 'root'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
```

**Create database (GaussDB)**:

> GaussDB does not require creating a schema separately; `DBCOMPATIBILITY = 'M'` is MySQL-syntax compatible; table structures are created automatically by the application.

```sql
CREATE DATABASE agent_studio TEMPLATE = template0 ENCODING 'UTF8' DBCOMPATIBILITY = 'M';
```

**Create object storage bucket (MinIO example)**:

```bash
mc alias set myminio http://<MINIO_IP>:9000 <ACCESS_KEY> <SECRET_KEY>
mc mb myminio/agent-builder
```

> Main business tables are created automatically by studio-manager on first startup; studio-builder initializes storage for prompt optimization tasks. No need to manually create application tables.

#### Step 3: Modify YAML Configuration

K8s YAML files are in the source `docker/k8s/` directory (or `k8s/` in the deployment package), 4 in total:

| YAML file | Required config |
|-----------|----------------|
| studio-manager.yaml | Image info, database (MySQL/GaussDB), Redis, OBS |
| studio-runtime.yaml | Image info, Redis, OBS |
| studio-builder.yaml | Image info, Redis, prompt task database, OBS |
| studio-console.yaml | Image info |

Modify environment variables in `spec.template.spec.containers.env` of each YAML:

> **Important**: Environment variables marked `[required]` in each YAML must be configured; `[optional]` defaults generally don't need modification.

**studio-runtime.yaml key config items** (example):

```yaml
# [required] Redis
- name: REDIS_HOST
  value: '<REDIS_IP>'
- name: REDIS_PORT
  value: '6379'
- name: REDIS_PASSWORD
  value: '<REDIS_PASSWORD>'

# [required] Object storage
- name: DATASOURCE_OBS_SERVER
  value: '<OBS_URL>'
- name: DATASOURCE_OBS_BUCKET
  value: '<BUCKET_NAME>'
- name: DATASOURCE_OBS_AK
  value: '<AK>'
- name: DATASOURCE_OBS_SK
  value: '<SK>'

# Model config defaults to reading from OBS with runtime direct-connecting the model
- name: MODEL_CONFIG_STRATEGY
  value: 'obs'
```

`studio-builder.yaml` also needs Redis, object storage, and `STORE_DB_*` configuration. Its health check port is `31015`; Manager's `agent_builder_endpoint` should point to `http://studio-builder:31015`.

> For HTTPS startup and Redis cluster/sentinel configuration, see corresponding comments in each YAML.
>
#### Step 4: Start Services

Start services in order (manager first, then runtime/builder, then console):

```bash
cd docker/k8s   # or k8s/ directory in deployment package

kubectl apply -f studio-manager.yaml
kubectl apply -f studio-runtime.yaml
kubectl apply -f studio-builder.yaml
kubectl apply -f studio-console.yaml
```

View Pod status:

```bash
kubectl get pods
```

All Pods should be in `Running` state.

#### Step 5: Post-Installation Verification

See [Section 6: Post-Installation Verification](#6-post-installation-verification).

K8s access address: `http://<node-IP>:30001/openjiuwen/`

### 5.4 K8s Common Operations

```bash
# View service Pods
kubectl get pods -l app=studio-manager
kubectl get pods -l app=studio-runtime
kubectl get pods -l app=studio-builder
kubectl get pods -l app=studio-console

# View service logs
kubectl logs -f deployment/studio-manager
kubectl logs -f deployment/studio-runtime
kubectl logs -f deployment/studio-builder
kubectl logs -f deployment/studio-console

# Restart service (rolling update)
kubectl rollout restart deployment/studio-manager

# Scale
kubectl scale deployment/studio-runtime --replicas=3
```

---

## 6. Post-Installation Verification

```bash
cd <project-root>/deploy    # Online deployment
cd ~/deploy  # Offline deployment

bash deploy.sh verify
bash deploy.sh status
```

**Common log viewing**:

```bash
bash deploy.sh logs <service-name>
```

**In-container log paths**:

| Service | Path |
|---------|------|
| studio-manager | `/opt/cloud/studio-manager/logs/studio-agent-manager.log` |
| studio-runtime | `/opt/cloud/logs/jiuwen_python.log` |
| studio-builder | `/opt/cloud/logs/agent-builder/common.log` |
| studio-console | `/opt/cloud/wiseagent-nginx/logs/error.log` |

---

## 7. Version Upgrade and Rollback

### Online Upgrade

```bash
cd <project-root>/deploy
bash deploy.sh update       # Pull latest images → init database → restart apps → verify
```

> Brief downtime during upgrade. For zero-downtime, use multiple instances + load balancing.

### Online Rollback

```bash
cd <project-root>/deploy

# Modify IMAGE_TAG in .env to old version
vi .env

# Restart
bash deploy.sh restart
```

### Offline Upgrade

1. Obtain new version image tars externally and transfer to target machine
2. Replace tar files in `images/` directory
3. Update `STUDIO_*_IMAGE` image tags in `.env` (if version numbers changed)
4. Execute:

```bash
cd ~/deploy
bash deploy.sh update
```

### Offline Rollback

```bash
# Replace old version tar files in images/, restore old tags in .env
cd ~/deploy
bash deploy.sh stop
bash deploy.sh all
```

---

## 8. Uninstall and Cleanup

```bash
cd <project-root>/deploy    # Online deployment
cd ~/deploy  # Offline deployment

# Stop services (retain data)
bash deploy.sh stop

# Stop infrastructure (only when using built-in infrastructure)
bash deploy.sh stop-infra

# Stop all (app + infrastructure)
bash deploy.sh stop-all

# Full cleanup (⚠️ deletes data volumes, data is irrecoverable)
bash deploy.sh clean all
```

---

## 9. Common Command Reference

```bash
bash deploy.sh all         # One-click deploy (pull/load images + start everything + verify)
bash deploy.sh infra       # Start infrastructure only (MySQL/Redis/MinIO + init database and buckets)
bash deploy.sh init-db     # Init database and MinIO buckets only (infrastructure must be running)
bash deploy.sh start       # Start all services (infra + app)
bash deploy.sh stop        # Stop all services
bash deploy.sh stop-infra  # Stop infrastructure only
bash deploy.sh stop-all    # Stop all services
bash deploy.sh restart     # Restart application services
bash deploy.sh update      # Pull/load images + rebuild services + verify
bash deploy.sh verify      # Verify HTTP health endpoints
bash deploy.sh status      # View service status
bash deploy.sh logs [svc]  # View logs
bash deploy.sh clean all   # Full cleanup (⚠️ data irrecoverable)

# Observability / log aggregation (optional, see Section 10)
bash deploy.sh logging              # L1 single-machine log stack (victoria-logs+vector+grafana, local)
bash deploy.sh logging-remote       # L2: app node remote vector (push to monitor node)
bash deploy.sh monitor              # L2: monitor node log stack (victoria-logs+grafana+gateway)
```

---

## 10. Observability (Log Aggregation)

> ⚠️ **Scope**: This section's solution only applies to **docker-compose deployment** (Section 3 online / Section 4 offline).
> **K8s deployment** (Section 5) should use log collection DaemonSet and centralized log storage; this Compose solution does not apply.

The platform includes an **optional** log aggregation stack that enables centralized log querying of five app services (manager/service/runtime/builder/console) in Grafana, replacing cross-container `docker logs` / `grep`. Two deployment modes:

| Mode | Applicable | Storage | Tech stack | Start/stop entry |
|---|---|---|---|---|
| **L1 Single-machine** | All services on same host | Local filesystem | **VictoriaLogs** + Vector + Grafana | `./deploy.sh logging` |
| **L2 Cross-node** | App and monitor on separate machines | Monitor node local disk | **VictoriaLogs** (full-text index) + Vector + Grafana + gateway | Monitor node `./deploy.sh monitor` + app node `./deploy.sh logging-remote` |

> L1/L2 both use VictoriaLogs (full-text index, query in seconds; local storage, no object storage dependency). Querying and troubleshooting are the same; see [`deploy/config/observability-readme.md`](../../deploy/config/observability-readme.md).

### 10.1 L1 Single-Machine Mode (recommended to try first)

Log aggregation stack co-located with app, one command:

```bash
cd deploy
./deploy.sh start          # First ensure app services are running (logs write to named volumes)
./deploy.sh logging        # Start log stack (victoria-logs/vector/grafana)
```

After startup, access Grafana: `http://<IP>:3000/` (default admin/admin), Explore → VictoriaLogs query:
```text
_stream:{service=~"manager|service|runtime|builder|console"} ERROR
```
Stop: `./deploy.sh logging stop`.

### 10.2 L2 Cross-Node Mode (Production)

When app and monitor are on separate machines: Vector runs with app, VictoriaLogs + Grafana + gateway centralized on monitor node, **local storage** (no object storage).

**Monitor node** (use only `monitor` subcommand):
```bash
cd deploy
./deploy.sh monitor          # Start (first run generates observability/.env; modify TLS address and read/write passwords then re-run)
```

**Each app node** (app first, then vector; order cannot be reversed):
```bash
cd deploy
./deploy.sh start          # 1) Start app services first (create named volumes)
./deploy.sh logging-remote # 2) Then start remote vector (push to monitor node gateway)
```

Monitor node and app nodes all use `deploy/observability/.env`. App nodes need a unique `NODE_NAME`, and `LOGS_GATEWAY_HOST` configured to the monitor node address. Config in old `.env.vector` needs to be merged into `.env`; that file is no longer used separately.

**Prerequisites**: Monitor node ↔ app node network reachable; all nodes clock-synced (chrony/NTP).

### 10.3 Log Retention Period

- **L1/L2 (VictoriaLogs)**: Configured via `VICTORIA_LOGS_RETENTION`, default 7 days, auto-cleaned after expiry.
- Java, Python runtime, and NGINX logs use real event timestamps from the log body; first import of historical logs won't pollute "recent logs" queries.
- Both are independent from app local audit (180 days).

### 10.4 More

Full architecture diagrams, LogsQL examples, troubleshooting, and evolution paths in [`deploy/config/observability-readme.md`](../../deploy/config/observability-readme.md).

---

## 11. FAQ

### Q1: Database Connection Failure

**Symptom**: Logs report `Communications link failure` or `Access denied`

**Troubleshooting**:
1. Confirm database created: `SHOW DATABASES LIKE 'agent-builder';`
2. Confirm IP and port reachable in `.env`: `telnet <MYSQL_IP> 3306`
3. In Docker, MySQL uses host IP, not `127.0.0.1`
4. Get Docker bridge IP: `ip addr show docker0 | grep inet`

### Q2: Redis Connection Failure

**Symptom**: Logs report `Unable to connect to Redis`

**Troubleshooting**:
1. Confirm Redis running: `redis-cli -h <IP> -p 6379 ping`
2. If password set, configure `REDIS_PASSWORD`
3. For cluster/sentinel mode, confirm `REDIS_MODE` etc. configured correctly

### Q3: Cannot Access Host Services from Container

**Symptom**: Cannot connect to host MySQL/Redis/MinIO from container

**Troubleshooting**:
1. `ip addr show docker0 | grep inet` (usually `172.17.0.1`)
2. Replace `127.0.0.1` with this IP in `.env`

### Q4: studio-runtime Repeatedly Restarting

**Symptom**: Container status Restarting

**Troubleshooting**:
1. `docker compose logs studio-runtime` to view logs
2. Python services must connect to Redis on startup; unreachable Redis will fail directly
3. Check if `REDIS_HOST` uses `127.0.0.1`

### Q5: Image Pull Failure / 403

**Symptom**: `docker pull ghcr.io/...` reports 403

**Troubleshooting**: Private images require login `echo <PAT> | docker login ghcr.io -u <USER> --password-stdin`; PAT needs `read:packages` permission. Or configure `GHCR_USERNAME` and `GHCR_TOKEN` in `.env` then use `bash deploy.sh update` (auto-logs in to repository and pulls latest images).

### Q6: Port Conflict

**Symptom**: `bind: address already in use`

**Troubleshooting**: `netstat -tlnp | grep -E '80|31111|31014|31015'`, modify conflicting ports in `.env`.

### Q7: Offline Deployment Image Load Failure

**Symptom**: `docker load` error

**Troubleshooting**:
1. Confirm `IMAGE_SOURCE=offline` in `.env`
2. Confirm `images/` and `dep-images/` directories have `.tar` files
3. Confirm `STUDIO_*_IMAGE` tags in `.env` match local image names after import (verify with `docker images` after `docker load`)
