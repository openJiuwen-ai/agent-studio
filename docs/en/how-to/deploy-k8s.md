# Kubernetes Deployment Guide

## 1. Overview

openJiuwen AgentStudio supports deployment via Kubernetes clusters, suitable for scenarios requiring multi-instance high availability, horizontal scaling, and rolling updates.

> For tech stack and ports of the 4 application services, see [Deployment Overview](./deploy-service.md#service-overview). For external dependencies, see [Deployment Overview — External Dependencies](./deploy-service.md#external-dependencies); K8s orchestration **does not include** MySQL/Redis/MinIO; deploy your own or use external instances.

---

## 2. Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| K8s cluster | v1.28+ | v1.32 |
| Worker node | 8 cores / 16GB | 12+ cores / 24GB+ |

### Prerequisites

| Software | Description |
|----------|-------------|
| Kubernetes cluster | Deployed and accessible |
| kubectl | Configured and can access cluster |
| Infrastructure | MySQL/Redis/MinIO or external instances ready |

---

## 3. Resource Quotas

Service resource allocation reference (dual instances, production HA):

| Service | Instances | CPU per instance | Memory per instance | Total CPU | Total memory |
|---------|-----------|-----------------|--------------------|-----------:|-------------:|
| studio-console | 1 | 0.25 core | 512MB | 0.25 core | 512MB |
| studio-manager | 2 | 2 cores | 4GB | 4 cores | 8GB |
| studio-runtime | 2 | 2 cores | 4GB | 4 cores | 8GB |
| studio-builder | 2 | 2 cores | 4GB | 4 cores | 8GB |

> studio-console typically needs only 1 instance (Nginx stateless reverse proxy); other services should have at least 2 instances for HA. Resource quotas come from each service's K8s YAML config.

---

## 4. Deployment Flow

```
Step 1          Step 2           Step 3            Step 4          Step 5
Prepare images → Init database → Modify YAML config → kubectl apply → Verify
```

---

## 5. Deployment Steps

> Download and extract the deployment package from the [Release page](https://atomgit.com/openJiuwen/agent-studio/releases). K8s YAML files are in the `deploy/k8s/` directory, 4 in total.

### Step 1: Prepare Images

K8s deployment supports two image acquisition methods:

**Method 1: Offline Import**

1. Check node architecture:

```bash
uname -m    # x86_64 / aarch64
```

2. Download the offline image package matching your architecture from the [Release page](https://atomgit.com/openJiuwen/agent-studio/releases), and transfer to each K8s node.

3. Load images on each node:

```bash
# Load offline images for 4 services
docker load -i studio-manager_*.tar
docker load -i studio-runtime_*.tar
docker load -i studio-builder_*.tar
docker load -i studio-console_*.tar
```

> Image names must match the `image` field in YAML. After import, verify with `docker images`.

**Method 2: Online Pull**

1. Change `spec.template.spec.containers.image` in each YAML to the repository address (e.g. `ghcr.io/<owner>/openjiuwen_agent_studio/studio-manager:latest`)
2. Change `imagePullPolicy` from the default `Never` to `Always`
3. For private registries, create the `default-secret` already referenced in the YAMLs:

```bash
kubectl create secret docker-registry default-secret \
  --docker-server=ghcr.io \
  --docker-username=<USERNAME> \
  --docker-password=<PAT>
```

### Step 2: Initialize Database and Object Storage

K8s orchestration does not include infrastructure; create database and object storage bucket yourself.

**Create database (MySQL)**:

```sql
CREATE DATABASE IF NOT EXISTS `agent-builder` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
GRANT ALL PRIVILEGES ON `agent-builder`.* TO 'root'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
```

**Create database (GaussDB)**:

> GaussDB does not require creating a schema separately; `DBCOMPATIBILITY = 'M'` is MySQL-syntax compatible; table structures are created automatically by the application.

```sql
CREATE DATABASE "agent-builder" TEMPLATE = template0 ENCODING 'UTF8' DBCOMPATIBILITY = 'M';
```

**Create object storage bucket (MinIO example)**:

```bash
mc alias set myminio http://<MINIO_IP>:9000 <ACCESS_KEY> <SECRET_KEY>
mc mb myminio/agent-builder
```

> Main business tables are created automatically by studio-manager on first startup; studio-builder initializes storage for prompt optimization tasks. No need to manually create application tables.

### Step 3: Modify YAML Configuration

Required config for each YAML:

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

### Step 4: Start Services

Start services in order (manager first, then runtime/builder, then console):

```bash
cd deploy/k8s

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

### Step 5: Post-Installation Verification

K8s access address: `http://<node-IP>:30001/openjiuwen/`

Verify Pod health status:

```bash
kubectl get pods -o wide
kubectl describe pod -l app=studio-manager
```

> For in-container log paths, see [Deployment Overview — Service Overview](./deploy-service.md#service-overview).

---

## 6. Common Operations

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

# View rolling update status
kubectl rollout status deployment/studio-manager

# Rollback to previous version
kubectl rollout undo deployment/studio-manager

# View Services and ports
kubectl get svc
```

---

## 7. Version Upgrade

K8s deployment performs version upgrades by updating image tags and triggering rolling updates:

```bash
# Method 1: Modify image tag in YAML then re-apply
vi deploy/k8s/studio-manager.yaml   # Modify tag in image
kubectl apply -f deploy/k8s/studio-manager.yaml

# Method 2: Set new image directly
kubectl set image deployment/studio-manager studio-manager=<new-image>:<new-tag>

# View rolling update progress
kubectl rollout status deployment/studio-manager
```

Rollback:

```bash
# Rollback to previous version
kubectl rollout undo deployment/studio-manager

# View release history
kubectl rollout history deployment/studio-manager
```

---

## 8. API Documentation (Swagger UI)

The platform provides a unified environment variable `API_DOCS_ENABLED` to control API documentation for both the management and runtime services.

| Service | Tech Stack | Documentation Coverage |
|---------|-----------|----------------------|
| studio-manager | springdoc-openapi | All 49 Controllers' management API endpoints |
| studio-runtime | FastAPI built-in OpenAPI 3 | All 28 runtime API endpoints |

> **Disabled by default**: API documentation is not enabled by default. Set `API_DOCS_ENABLED=true` to enable as needed.

### Enable

Edit `deploy/k8s/studio-manager.yaml` and `deploy/k8s/studio-runtime.yaml`, uncomment and set to true in the env section:

```yaml
- name: API_DOCS_ENABLED
  value: 'true'
```

Restart Pods to take effect:

```bash
kubectl rollout restart deployment/studio-manager deployment/studio-runtime
```

### Access URLs

| Page | URL |
|------|-----|
| Manager Swagger UI (interactive) | `http://<MANAGER_IP>:31111/swagger-ui.html` |
| Manager OpenAPI JSON (import to Postman) | `http://<MANAGER_IP>:31111/v3/api-docs` |
| Manager — Agent Management group | `http://<MANAGER_IP>:31111/v3/api-docs/agent-management` |
| Manager — Prompt Engineering group | `http://<MANAGER_IP>:31111/v3/api-docs/prompt-engineering` |
| Runtime Swagger UI (interactive) | `http://<RUNTIME_IP>:31014/runtime/docs` |
| Runtime ReDoc (read-only) | `http://<RUNTIME_IP>:31014/runtime/redoc` |
| Runtime OpenAPI JSON | `http://<RUNTIME_IP>:31014/runtime/openapi.json` |

### Disable

```yaml
# Change back to false or re-comment the lines
- name: API_DOCS_ENABLED
  value: 'false'
```

> When no longer needed, set `API_DOCS_ENABLED` back to `false` (default).

---

## 9. FAQ

### Q1: Pod Status is CrashLoopBackOff

**Troubleshooting**:
1. `kubectl logs <pod-name>` to view container logs
2. Python services (runtime/builder) must connect to Redis on startup; unreachable Redis will fail directly
3. Check if `REDIS_HOST` in YAML correctly points to external Redis address

### Q2: Pod Status is ImagePullBackOff

**Troubleshooting**:
1. Confirm image name and tag are correct: `kubectl describe pod <pod-name>` to view Events
2. Private repositories need `imagePullSecrets` configured
3. For offline import, confirm `imagePullPolicy` is set to `IfNotPresent` or `Never`
4. Confirm image has been `docker load`ed on target node: `docker images | grep studio`

### Q3: Pod Status is Pending

**Troubleshooting**:
1. `kubectl describe pod <pod-name>` to view scheduling failure reason
2. Check if node resources are sufficient (CPU/memory)
3. Check if node is tainted: `kubectl get nodes -o jsonpath='{.items[*].metadata.name}' | xargs -I{} kubectl describe node {} | grep -A5 Taints`

### Q4: Services Cannot Communicate

**Troubleshooting**:
1. Confirm all services are in the same namespace: `kubectl get pods --all-namespaces`
2. Confirm Service is created and ClusterIP is normal: `kubectl get svc`
3. Confirm `agent_builder_endpoint` points to `http://studio-builder:31015`
4. Confirm `agent_runtime_endpoint` points to `http://studio-runtime:31014`

### Q5: Database Tables Not Auto-Created

**Troubleshooting**:
1. Confirm `SPRING_DATASOURCE_URL` correctly points to external database
2. Confirm database user has DDL permissions
3. `kubectl logs deployment/studio-manager` to view table creation info in Java startup logs
4. For GaussDB, ensure `DBCOMPATIBILITY = 'M'`
