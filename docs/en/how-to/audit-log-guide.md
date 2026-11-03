# Audit Log Guide

## 1. Overview

openJiuwen AgentStudio includes a built-in audit log feature that automatically records user operations on key resources, including create, update, delete, read, import, export, and execute operations. Audit logs are independent from application runtime logs, written in JSON format to a dedicated log file for security auditing and troubleshooting.

> **Disabled by default**: The audit log feature is disabled by default and must be manually enabled.

---

## 2. Enabling Audit Logs

### 2.1 Docker Compose Deployment

Set the environment variable in the `.env` file:

```bash
STUDIO_OPERATION_LOG_SWITCH=true
```

Then recreate the service (restart only restarts containers without re-reading environment variables; use recreate to rebuild):

```bash
bash deploy.sh recreate
```

### 2.2 Direct Deployment (Non-Docker)

Set in `application-manager.yml`:

```yaml
studio:
  operationLog:
    switch: true
```

Or set via environment variable:

```bash
export studio_operationLog_switch=true
```

> Restart the service for changes to take effect (`@Value` is bound at startup; modifying environment variables at runtime will not take effect immediately). All Service method calls annotated with `@OperationLog` will be recorded.

---

## 3. Log Storage Location

| Deployment Type | Log Path |
|----------------|----------|
| Docker Compose | Inside container: `/opt/cloud/studio-manager/logs/audit/trace.log` (mapped to host via the `manager_logs` volume) |
| Direct Deployment | `/opt/cloud/studio-manager/logs/audit/trace.log` |

For Docker Compose deployment, check the volume mapping path with:

```bash
docker volume ls | grep manager_logs
```

After confirming the actual volume name, use `docker volume inspect <volume_name>` to view the mapping path. The volume name prefix depends on the deployment directory name (e.g., `agent-studio_manager_logs` or `<directory_name>_manager_logs`).

---

## 4. Log Format

Each audit log entry is a single line of JSON with the following structure:

```json
{
  "timestamp": "2026-09-29T10:30:00.000Z",
  "traceId": "request-id-from-mdc",
  "userId": "user123",
  "userName": "John Doe",
  "operationType": "CREATE",
  "resourceType": "Agent",
  "resourceId": "agent-uuid",
  "resourceName": "My Agent",
  "description": "Create agent",
  "method": "createAgent",
  "success": true,
  "errorMessage": null,
  "params": {
    "projectId": "0",
    "body": {
      "name": "My Agent"
    }
  }
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO-8601 formatted timestamp |
| `traceId` | string | Request trace ID from MDC `request-id`, can be used to correlate with application logs |
| `userId` | string | Operator user ID |
| `userName` | string | Operator user name |
| `operationType` | string | Operation type, see table below |
| `resourceType` | string | Resource type, e.g. Agent/Workflow/Tool/MCP/KnowledgeBase |
| `resourceId` | string | Resource ID, extracted from method parameters |
| `resourceName` | string | Resource name, extracted from method parameters |
| `description` | string | Operation description |
| `method` | string | Audited Java method name |
| `success` | boolean | Whether the operation succeeded |
| `errorMessage` | string/null | Exception message on failure; `null` on success |
| `params` | object | Method parameters (masked), in JSON format |

### Operation Types

| Operation Type | Description |
|----------------|-------------|
| `CREATE` | Create resource |
| `UPDATE` | Update resource |
| `DELETE` | Delete resource |
| `READ` | Read resource |
| `EXPORT` | Export resource |
| `IMPORT` | Import resource |
| `EXECUTE` | Execute operation |

---

## 5. Audit Coverage

Audit logs cover key operations in the following Services (145 audit points total, 26 Services):

| Service | Audit Points | Covered Operations |
|---------|-------------|-------------------|
| `AgentManagementService` | 17 | Create/update/delete/publish/copy agents, etc. |
| `WorkflowManagementService` | 17 | Create/update/delete/publish workflows, etc. |
| `PluginService` | 13 | Create/delete/modify/import/export/publish plugins |
| `ToolManagementService` | 10 | Tool create/update/delete/publish, etc. |
| `KnowledgeBaseServiceImpl` | 9 | Knowledge base create/update/delete, etc. |
| `ComplexIntentManagementService` | 9 | CRUD for complex intents |
| `EnvironmentServiceManagerService` | 7 | Environment service management |
| `KnowledgeBaseDatasetServiceImpl` | 7 | Knowledge base dataset CRUD |
| `ModelServiceMgmtService` | 6 | Model service management |
| `McpServiceManager` | 6 | MCP service create/deploy/delete, etc. |
| `ShareResourceManagerService` | 5 | Resource sharing management |
| `ProviderMgmtService` | 4 | Model provider management |
| `ProviderAuthService` | 4 | Provider authentication management |
| `MessageManagementService` | 4 | Message template/intent package/object management |
| `WorkspaceService` | 3 | Workspace CRUD |
| `WorkspaceMemberService` | 3 | Workspace member management |
| `RouterStrategyMgmtService` | 3 | Routing strategy management |
| `ProviderAuthMgmtService` | 3 | Provider auth info management |
| `MemoryServiceInstanceService` | 3 | Memory service instance management |
| `MemoryRepoManagementService` | 3 | Memory repository management |
| `CustomObjectManagementService` | 3 | Custom object management |
| `SkillManagementService` | 2 | Skill management |
| `McpInnerService` | 1 | MCP internal service operations |
| `CommonManagementService` | 1 | Common management operations |
| `AppManagementService` | 1 | App management |
| `AgentServiceProxyService` | 1 | Agent service proxy operations |

---

## 6. Sensitive Field Masking

When serializing method parameters, audit logs automatically mask values of sensitive fields (replaced with `******`).

### Default Masking Rules

The following field names (case-insensitive) are masked:

- password / pwd
- token / authorization
- api_key / api-key / apikey
- secret / credential
- auth_info / auth_key / auth_id / auth_value / auth_type / auth_keys
- access_key / accesskey
- client_secret / clientsecret
- iam_credentials / iam_ak / iam_sk
- oauth_scope
- app_code
- ak / sk

### Custom Masking Rules

Modify the `sensitiveFieldPattern` regex in `application-manager.yml`:

```yaml
studio:
  operationLog:
    switch: true
    sensitiveFieldPattern: '(?i)(?:.*(?:password|pwd|token|authorization|api[-_]?key|secret|credential|your_custom_field).*)'
```

---

## 7. Log Rollover and Retention

| Config Item | Default | Description |
|-------------|---------|-------------|
| Max single file size | `50MB` | Rolls over to a new file when exceeded; modifiable via `TRACE_FILE_ROLLING_SIZE` |
| Max file count | `200` | Oldest files are deleted when exceeded; modifiable via `TRACE_FILE_MAX_COUNT` |
| Max retention period | `180 days` | Auto-cleaned after expiry; modifiable via `TRACE_FILE_MAX_AGE` |
| Write mode | Async | Written via async Appender, does not affect business performance |

For Docker Compose deployment, set in `.env`:

```bash
TRACE_FILE_ROLLING_SIZE=50MB
TRACE_FILE_MAX_COUNT=200
TRACE_FILE_MAX_AGE=180d
```

---

## 8. Log Query Examples

Audit logs are in JSON format, one record per line. The `jq` tool is recommended for querying:

```bash
# View all failed audit records
cat /opt/cloud/studio-manager/logs/audit/trace.log | jq 'select(.success == false)'

# Filter by operation type
cat /opt/cloud/studio-manager/logs/audit/trace.log | jq 'select(.operationType == "CREATE")'

# Filter by user
cat /opt/cloud/studio-manager/logs/audit/trace.log | jq 'select(.userId == "user123")'

# Filter by time range
cat /opt/cloud/studio-manager/logs/audit/trace.log | jq 'select(.timestamp >= "2026-09-29" and .timestamp < "2026-09-30")'

# View operation history for a specific resource
cat /opt/cloud/studio-manager/logs/audit/trace.log | jq 'select(.resourceId == "agent-uuid")'

# Count operations by type
cat /opt/cloud/studio-manager/logs/audit/trace.log | jq -r '.operationType' | sort | uniq -c | sort -rn

# View failed delete operations
cat /opt/cloud/studio-manager/logs/audit/trace.log | jq 'select(.operationType == "DELETE" and .success == false)'
```

For Docker Compose deployment, query via `docker exec`:

```bash
docker exec agent-studio-studio-manager-1 cat /opt/cloud/studio-manager/logs/audit/trace.log | jq 'select(.success == false)'
```

---

## 9. Differences from Observability Logs

| Dimension | Audit Log | Observability Log (VictoriaLogs) |
|-----------|-----------|----------------------------------|
| Purpose | Records user operations for security auditing | Records application runtime logs for troubleshooting and monitoring |
| Format | JSON (structured) | Text (semi-structured) |
| Storage | Dedicated file `audit/trace.log` | VictoriaLogs database |
| Retention | 180 days | 7 days by default (configurable) |
| Enablement | Disabled by default; set `STUDIO_OPERATION_LOG_SWITCH=true` | Optional deployment; see [Docker Compose Deployment Guide — Observability](./deploy-docker-compose.md#7-observability-log-aggregation) |

The two are independent and can be enabled simultaneously.
