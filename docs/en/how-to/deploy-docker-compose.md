# Docker Compose Deployment Guide

## 1. Overview

openJiuwen AgentStudio contains 4 application services deployed via Docker Compose orchestration. Orchestration includes built-in infrastructure (MySQL, Redis, MinIO) by default; also supports connecting to existing external instances. The orchestration file includes 8 services by default:

| Type | Services | Description |
|------|---------|-------------|
| Infrastructure | mysql, redis, minio, minio-init | Auto-started and initialized by `deploy.sh` |
| Application services | studio-console, studio-manager, studio-runtime, studio-builder | Business services |

> For tech stack and ports of the 4 application services, see [Deployment Overview](./deploy-service.md#service-overview). For external dependencies, see [Deployment Overview — External Dependencies](./deploy-service.md#external-dependencies); orchestration includes built-in MySQL/Redis/MinIO by default.

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
| Docker Compose | V2 recommended, V1 compatible | Service orchestration (`deploy.sh` auto-detects) |

> Check versions before deployment:
> ```bash
> docker --version
> docker compose version    # V2
> docker-compose version     # V1
> ```

#### Non-root User Deployment

The deployment script calls `docker` commands directly; the deploy user must be in the `docker` group (re-login to take effect):

```bash
sudo usermod -aG docker $USER
```

---

## 3. Deployment

```
Step 1         Step 2            Step 3         Step 4
Download package → Configure image source → deploy.sh all → Verify access
```

### Step 1: Download Package

Download the deployment package from the [Release page](https://atomgit.com/openJiuwen/agent-studio/releases), extract, and enter the directory:

```bash
# Create .env from template
cp .env.template .env
```

### Step 2: Configure Image Source

First check whether images are published to the GHCR public repository:

```bash
docker pull ghcr.io/openjiuwen/openjiuwen_agent_studio/studio-console:latest
```

> The probe uses the `:latest` tag (CI pushes this tag on every build), which is independent of the offline package version on the Release page. If the pull succeeds, images are published and Method 1 (online pull) can be used. If you get 403/404, images are not yet published; use Method 2 (offline import).

**Method 1: Online Pull**

```bash
vi .env
```

Configure the following variables:

- Set `IMAGE_SOURCE=ghcr`
- `IMAGE_TAG`: image tag, defaults to `latest`
- `GHCR_IMAGE_REPOSITORY`: GHCR repository path, format `ghcr.io/<github-user-or-org>/<repo>`
- `GHCR_USERNAME`: GitHub username, **leave empty for public images**
- `GHCR_TOKEN`: GitHub Personal Access Token with `read:packages` scope, **leave empty for public images**

```bash
IMAGE_SOURCE=ghcr
IMAGE_TAG=latest
GHCR_IMAGE_REPOSITORY=ghcr.io/openjiuwen/openjiuwen_agent_studio
GHCR_USERNAME=
GHCR_TOKEN=
```

**Method 2: Offline Import**

1. Check architecture:

```bash
uname -m    # x86_64 / aarch64
```

2. In the deployment package root, create image directories and place offline image packages:

```bash
mkdir -p images dep-images
```

```
agent-studio-deploy/
├── images/        ← App image .tars (4 application services)
└── dep-images/    ← Infrastructure image .tars (MySQL/Redis/MinIO/MC, when using built-in infrastructure)
```

> When using external dependencies, `dep-images/` can be left empty.

##### Obtaining App Image Packages

Download the app image `.tar` files matching your architecture (4 files total) from the [Release page](https://atomgit.com/openJiuwen/agent-studio/releases) and place them into `images/`.

##### Obtaining Infrastructure Image Packages

On a machine with internet access, use the built-in script to export infrastructure images (MySQL/Redis/MinIO/MC):

```bash
bash scripts/export-dependency-images.sh ~/dep-images
```

The script automatically pulls and exports the following images:

| Image | Version |
|-------|---------|
| mysql | 8.0 |
| redis | 7 |
| minio/minio | RELEASE.2024-11-07T00-52-20Z |
| minio/mc | RELEASE.2024-11-05T11-29-45Z |

After export, transfer the `~/dep-images/` directory to the target machine's `dep-images/` directory.

> The script also exports observability images (VictoriaLogs/Vector); these can be ignored if observability is not used.

3. Edit `.env`:

```bash
vi .env
```

- Set `IMAGE_SOURCE=offline`
- Uncomment the four `STUDIO_*_IMAGE` lines (remove leading `#`; **variable names must start at column 0, no leading spaces**), and replace `TAG_PLACEHOLDER` with the actual version and arch
- Image name format: `<service>:<version>.<arch>`, the following is an example; **version and arch must be updated according to the downloaded offline image package name and actual setup**

```bash
IMAGE_SOURCE=offline
STUDIO_CONSOLE_IMAGE=studio-console:v0.2.1.beta1.x86_64
STUDIO_MANAGER_IMAGE=studio-manager:v0.2.1.beta1.x86_64
STUDIO_RUNTIME_IMAGE=studio-runtime:v0.2.1.beta1.x86_64
STUDIO_BUILDER_IMAGE=studio-builder:v0.2.1.beta1.x86_64
```

> `deploy.sh` auto-loads offline image packages from `images/` and `dep-images/`.

### Step 3: One-Click Deployment

```bash
bash deploy.sh all
```

Auto-executes: get images (pull or load) → initialize infrastructure (MySQL/Redis/MinIO + database + MinIO buckets) → start application services → health check → output access address.

> The `all` command gets images first then starts, suitable for **first deployment**. For subsequent updates use `update`, for restart use `restart`.

> 💡 Default deployment does not include a log aggregation stack. For centralized log querying in Grafana, see "[Section 7: Observability (Log Aggregation)](#7-observability-log-aggregation)".

### Step 4: Verify

```bash
bash deploy.sh verify
bash deploy.sh status
bash deploy.sh logs <service-name>
```

Browser access: `http://<IP>/openjiuwen/`

> For in-container log paths, see [Deployment Overview — Service Overview](./deploy-service.md#service-overview).

---

## 4. Version Upgrade and Rollback

### Upgrade

```bash
bash deploy.sh update    # Get latest images → rebuild services → verify
```

> Online mode auto-pulls latest images; offline mode requires replacing tar files in `images/` first.
>
> Brief downtime during upgrade.

### Rollback

```bash
# Online: modify IMAGE_TAG in .env to old version
# Offline: replace old version tars in images/, restore old image names in .env

bash deploy.sh restart
```

---

## 5. Uninstall and Cleanup

```bash
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

## 6. Common Command Reference

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

# Observability / log aggregation (optional, see Section 7)
bash deploy.sh logging              # L1 single-machine log stack (victoria-logs+vector+grafana, local)
bash deploy.sh logging-remote       # L2: application node remote vector (push to monitor node)
bash deploy.sh monitor              # L2: monitor node log stack (victoria-logs+grafana+gateway)
```

---

## 7. Observability (Log Aggregation)

> ⚠️ **Scope**: This section's solution only applies to Docker Compose deployment. For K8s deployment, use log collection DaemonSet and centralized log storage.

The platform includes an **optional** log aggregation stack that enables centralized log querying of four application services (manager/runtime/builder/console) in Grafana, replacing cross-container `docker logs` / `grep`. Two deployment modes:

| Mode | Applicable | Storage | Tech stack | Start/stop entry |
|---|---|---|---|---|
| **L1 Single-machine** | All services on same host | Local filesystem | **VictoriaLogs** + Vector + Grafana | `bash deploy.sh logging` |
| **L2 Cross-node** | Application and monitor on separate machines | Monitor node local disk | **VictoriaLogs** (full-text index) + Vector + Grafana + gateway | Monitor node `bash deploy.sh monitor` + application node `bash deploy.sh logging-remote` |

> L1/L2 both use VictoriaLogs (full-text index, query in seconds; local storage, no object storage dependency). Querying and troubleshooting are the same; see [`deploy/config/observability-readme.md`](../../deploy/config/observability-readme.md).

### 7.1 L1 Single-Machine Mode

Log aggregation stack co-located with application, one command:

```bash
bash deploy.sh start          # First ensure application services are running (logs write to named volumes)
bash deploy.sh logging        # Start log stack (victoria-logs/vector/grafana)
```

After startup, access Grafana: `http://<IP>:3000/` (default admin/admin), Explore → VictoriaLogs query:
```text
_stream:{service=~"manager|runtime|builder|console"} ERROR
```
Stop: `bash deploy.sh logging stop`.

### 7.2 L2 Cross-Node Mode

When application and monitor are on separate machines: Vector runs with application, VictoriaLogs + Grafana + gateway centralized on monitor node, **local storage** (no object storage).

**Monitor node** (use only `monitor` subcommand):
```bash
bash deploy.sh monitor          # Start (first run generates observability/.env; modify TLS address and read/write passwords then re-run)
```

**Each application node** (application first, then vector; order cannot be reversed):
```bash
bash deploy.sh start          # 1) Start application services first (create named volumes)
bash deploy.sh logging-remote # 2) Then start remote vector (push to monitor node gateway)
```

Monitor node and application nodes all use `observability/.env`. Application nodes need a unique
`NODE_NAME`, and `LOGS_GATEWAY_HOST` configured to the monitor node address. Config in old `.env.vector`
needs to be merged into `.env`; that file is no longer used separately.

**Prerequisites**: Monitor node ↔ application node network reachable; all nodes clock-synced (chrony/NTP).

### 7.3 Log Retention Period

- **L1/L2 (VictoriaLogs)**: Configured via `VICTORIA_LOGS_RETENTION`, default 7 days, auto-cleaned after expiry.
- Java, Python runtime, and NGINX logs use real event timestamps from the log body; first import of historical logs won't pollute "recent logs" queries.
- Both are independent from application local audit (180 days).

### 7.4 More

Full architecture diagrams, LogsQL examples, troubleshooting, and evolution paths in [`deploy/config/observability-readme.md`](../../deploy/config/observability-readme.md).

---

## 8. FAQ

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
3. Confirm `STUDIO_*_IMAGE` values in `.env` exactly match the REPOSITORY:TAG shown by `docker images` (verify with `docker images` after `docker load`; note whether repository prefix is included)
