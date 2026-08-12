# Beta5 Upgrade Deployment Guide

> This guide is for upgrading from **Beta4** and earlier to **Beta5**, focusing on **architecture changes** and **environment variable changes**. For new deployments, refer to [Deployment Guide](./deploy-service.md); this guide does not repeat general steps.
>
> Environment variables are authoritative in the source `docker/k8s/` YAML files (`studio-manager.yaml`, `studio-builder.yaml`, `studio-runtime.yaml`, `studio-console.yaml`).

---

## 1. Architecture Changes Overview

Beta5 splits and restructures the execution layer with two core changes:

1. **Removed `studio-service`** (Java / Spring Boot, port 31113). The original execution-layer responsibilities — Agent execution, conversation, model invocation, knowledge retrieval — were decomposed:
   - Model invocation capability migrated to Python services; by default uses OBS model configuration to directly connect to real models, no longer relying on the original `studio-service` routing; if the deployer has a separate model gateway, an external gateway can still be explicitly configured;
   - NL2 generation, prompt optimization, model tuning and other "build-time" capabilities were separated into a new `studio-builder` microservice.
2. **Added `studio-builder`** (Python / FastAPI, port 31015). Takes over the `agent_builder` module originally embedded in the `studio-runtime` image — NL2 interface, prompt optimization tasks, model tuning, etc. — with independent build and independent scaling.

Service list changes:

| Service | Tech Stack | Port | Beta4 & earlier | Beta5 |
|---------|-----------|------|-----------------|-------|
| studio-console | Nginx + Angular | 80 | ✅ | ✅ (nginx upstream needs redirect, see Section 3) |
| studio-manager | Spring Boot (Java 17) | 31111 | ✅ | ✅ |
| studio-service | Spring Boot (Java 17) | 31113 | ✅ | ❌ **Removed** |
| studio-runtime | Python (FastAPI) | 31014 | ✅ | ✅ |
| studio-builder | Python (FastAPI) | 31015 | ❌ | ✅ **New** |

> Total service count unchanged (still 4 application services), but the execution layer changed from "one Java service" to "runtime + builder two Python services".
>
> ⚠️ The old naming confusion note is no longer valid: the Beta4 documentation's "`studio-service` container runs Java `studio-runtime` module JAR" no longer applies — from Beta5 there is no `studio-service`; the `studio-runtime` container is the Python `agent-runtime`.

### 1.1 Dependency Changes

```
Beta4:                         Beta5:
console → manager               console → manager
         → service ──┐                   → runtime  ──┐
         → runtime ──┤                   → builder ──┤
                     │                                │
manager → service (model routing)   manager → builder (n2l/prompt)
runtime → service (model routing)   runtime → OBS direct model (default)
                                     └→ external model gateway (optional)
```

- `studio-manager` no longer calls `studio-service`; it now calls `studio-builder` (n2l generation) and `studio-runtime`.
- `studio-runtime` no longer routes models through `studio-service`; by default `MODEL_CONFIG_STRATEGY=obs` directly connects to real models. Only configure `MODEL_ROUTER_API` when a standalone external model gateway is deployed.

---

## 2. Environment Variable Changes

> Legend: 🆕 Added · 🗑️ Removed · 🔁 Renamed/changed default. Only **changed items** are listed per service; unlisted variables remain the same as Beta4. See `docker/k8s/<svc>.yaml` for details.

### 2.1 studio-manager

| Variable | Change | Beta5 Value / Description |
|----------|--------|--------------------------|
| `agent_builder_endpoint` | 🆕 / 🔁 (replaces `jiu_wen_service_endpoint`) | `http://studio-builder:31015`, n2l generation API endpoint; change to `https://` for HTTPS |
| `agent_runtime_endpoint` | 🆕 / 🔁 (replaces `jiuwen_base_url`) | `http://studio-runtime:31014`, runtime call address |
| `jiu_wen_service_endpoint` | 🗑️ | Replaced by `agent_builder_endpoint` |
| Calls to `studio-service` | 🗑️ | manager no longer depends on service |

Others (database `spring_datasource_*`, Redis `redis_*`, object storage `obs_*`, HTTPS `server_ssl_*`, `user_auth_endpoint`, `system_crypt_name`, `auth_sso_validate_url`, etc.) remain unchanged.

### 2.2 studio-runtime

| Variable | Change | Beta5 Value / Description |
|----------|--------|--------------------------|
| `MODEL_ROUTER_API` | 🔁 Optional | Delete old value `http://studio-service:31113/v1/agent-builder`; not configured by default. Only set when using a standalone external model gateway, e.g. `https://<model-gateway>/v1/agent-builder`; must not point to `studio-runtime` or `studio-builder` itself |
| `MODEL_CONFIG_STRATEGY` | 🔁 Default value | Default `obs` (OBS direct connection, bypassing model routing); optional `env` / `ir` |

Model cache, sandbox, OpenSearch, memory store, `STORE_DB_*`, `IR_LLM_API_KEY`, logging and other variables remain unchanged. If using `MODEL_CONFIG_STRATEGY=ir` and resolving models through a gateway, a valid external `MODEL_ROUTER_API` must also be provided.

### 2.3 studio-builder (🆕 New service)

Full variables in `docker/k8s/studio-builder.yaml`, grouped as follows:

| Group | Variables | Description |
|-------|-----------|-------------|
| Server listen | `SERVER_HOST` / `SERVER_PORT` | `0.0.0.0` / `31015` |
| Redis [required] | `REDIS_HOST` `REDIS_PASSWORD` `REDIS_PORT` `REDIS_MODE` `REDIS_DATABASE` (cluster `REDIS_CLUSTER_NODES`, sentinel `REDIS_SENTINEL_MASTER` `REDIS_SENTINEL_NODES`) | Same Redis semantics as studio-runtime |
| Object storage [required] | `DATASOURCE_OBS_SERVER` `DATASOURCE_OBS_BUCKET` `DATASOURCE_OBS_AK` `DATASOURCE_OBS_SK` `DATASOURCE_OBS_ENABLE_SSL` | Same as studio-runtime |
| Model config | `MODEL_CONFIG_STRATEGY` | Default `obs` |
| External model gateway [optional] | `MODEL_ROUTER_API` | Not configured by default; only fill in `https://<model-gateway>/v1/agent-builder` when connecting a standalone external model gateway; must not use old `studio-service:31113` or point to builder itself |
| Prompt task persistence [optional] | `STORE_DB_TYPE` (mysql/gaussdb) `STORE_DB_HOST` `STORE_DB_PORT` `STORE_DB_USER` `STORE_DB_PASSWORD` `STORE_DB_DATABASE` (default `agent-builder`) `STORE_DB_SCHEMA` `STORE_DB_SSLMODE` | If not filled, only in-memory; shares same `STORE_DB_*` semantics as runtime |
| Logging | `JIUWEN_LOG_FILE` `JIUWEN_LOG_PATH` `JIUWEN_LOGGING_LOG_FILE` `LOGGING_LOG_PATH` `TGF_LOG_DIR` `LOG_VERBOSE` | Default writes to `/opt/cloud/logs/` |

> studio-builder initializes storage tables for prompt optimization tasks on startup as needed; `studio-manager` is responsible for main business tables. If `STORE_DB_*` is not fully configured, prompt task storage cannot be persisted to database.

### 2.4 studio-service (🗑️ Entirely removed)

The following variables are deprecated along with the service; remove them from orchestration during upgrade — no need to configure:

```
spring_datasource_*   redis_*   obs_*   storage_*   user_auth_endpoint
agent_manager_endpoint   jiuwen_base_url   server_ssl_*   koosearch_endpoint
system_crypt_name   auth_sso_validate_url
```

### 2.5 studio-console

The console container itself has no new environment variables, but its nginx upstream (`backend.conf`) needs redirecting:

| nginx variable | Beta4 | Beta5 |
|---------------|-------|-------|
| `manager_backend` | `studio-manager` | `studio-manager` (unchanged) |
| `service_backend` | `studio-service:31113` | **Must be removed** |

> Do not mechanically change the old `$service_backend:31113` location to Runtime. In Beta5 standard routing, `/v1/agent-builder/chat/completions`, `/v1/agent-builder/embeddings`, `/v1/agent-builder/rerank` go directly to Builder; `/v1/.*/agents/.*/conversations/.*/additional-questions`, `/v1/.*/agents/.*/conversations`, and `/v1/.*/workflows/.*/conversations` go directly to studio-runtime; other `/v1`, `/v2` requests go to Manager by default, which then calls Runtime or Builder based on business semantics. During upgrade, replace entirely with the release package `docker/compose/config/nginx.conf` (for K8s use the corresponding config in `studio-console.yaml`); do not manually maintain the old routing list.

---

## 3. Upgrade Steps

### 3.1 K8s Deployment Upgrade

```
Step 1           Step 2           Step 3                    Step 4
Delete service → apply builder → rolling update manager/runtime → update console
```

```bash
cd docker/k8s   # or the k8s/ directory in the deployment package

# 1) Remove studio-service (no studio-service.yaml in K8s directory; delete old resources directly)
kubectl delete deployment studio-service -n default
kubectl delete svc studio-service -n default || true

# 2) Deploy the new studio-builder
kubectl apply -f studio-builder.yaml

# 3) Rolling update manager / runtime (environment variables changed)
kubectl apply -f studio-manager.yaml
kubectl apply -f studio-runtime.yaml

# 4) Update console (nginx upstream redirect)
kubectl apply -f studio-console.yaml

# Observe
kubectl get pods -l app=studio-builder
kubectl rollout status deployment/studio-manager
kubectl rollout status deployment/studio-runtime
```

Before and after upgrade, verify that the `env` sections of each YAML have been adjusted per Section 2; switch image tags to Beta5 versions.

### 3.2 Docker Compose Deployment Upgrade

```bash
cd <project-root>/deploy

# 1) Pull/load Beta5 images (includes new studio-builder, no more studio-service)
bash deploy.sh update

# 2) Confirm .env has been updated per Section 2 (see 3.3)

# 3) Restart for orchestration to take effect
bash deploy.sh restart

# 4) Verify
bash deploy.sh verify
bash deploy.sh status
```

> `deploy.sh update` reads the new `docker-compose.yml`: the old `studio-service` service block has been removed, and a new `studio-builder` service block has been added. Clean up `STUDIO_SERVICE_IMAGE`, `SERVICE_PORT`, `JIUWEN_BASE_URL`, `JIUWEN_BUILDER_URL`, and `MODEL_ROUTER_API` pointing to `studio-service:31113` from `.env`; if an external model gateway is needed, configure `MODEL_ROUTER_API` separately with the new external HTTPS address.

---

## 4. Rollback

Rolling back to Beta4 requires restoring both services and variables:

1. Restore old values in `.env`: `STUDIO_SERVICE_IMAGE`, `MODEL_ROUTER_API`, `JIUWEN_BUILDER_URL`, old `AGENT_RUNTIME_ENDPOINT=http://studio-service:31113`, etc.; remove `STUDIO_BUILDER_IMAGE` and `STORE_DB_*` (if newly added).
2. K8s: `kubectl delete -f studio-builder.yaml`, re-`kubectl apply` old `studio-service.yaml`, `studio-manager.yaml`, `studio-runtime.yaml`, `studio-console.yaml`.
3. Compose: use Beta4's `docker-compose.yml` and image tags, `bash deploy.sh stop && bash deploy.sh all`.

> ⚠️ Cross-version rollback is a destructive operation; back up the database and object storage before executing.

---

## 5. Upgrade Self-Check

| Check item | Command / Method |
|-----------|-----------------|
| builder is ready | `kubectl get pods -l app=studio-builder` all `Running`; `curl http://<builder_ip>:31015/v1/health` |
| service is offline | `kubectl get deploy studio-service` should return NotFound; console no longer has health traffic to 31113 |
| manager calls builder | manager logs show no `studio-builder:31015` connection failures; n2l / prompt optimization features work |
| Model invocation | In default mode `MODEL_CONFIG_STRATEGY=obs` is active, Runtime/Builder logs show no `studio-service:31113` errors and model calls succeed; if `MODEL_ROUTER_API` is configured, confirm the target is a standalone external gateway and gateway calls succeed |
| Historical sessions / workflows | After upgrade, run a conversation and execution regression on existing Agents / workflows (Beta5 fixed controller and LLM node historical session issues) |

If builder / runtime repeatedly restarts, first check Redis and OBS connectivity (Python services must connect to Redis on startup; unreachable will fail immediately), then check whether `STORE_DB_*` credentials contain special characters (older versions had connection failures due to password special characters).
