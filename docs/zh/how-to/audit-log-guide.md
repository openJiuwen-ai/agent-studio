# 审计日志使用指南

## 一、功能概述

openJiuwen AgentStudio 内置审计日志功能，自动记录用户对关键资源的操作行为，包括创建、更新、删除、读取、导入、导出和执行等操作。审计日志独立于应用运行日志，以 JSON 格式写入专用日志文件，便于安全审计和问题排查。

> **默认关闭**：审计日志功能默认关闭，需手动开启。

---

## 二、开启审计日志

### 2.1 Docker Compose 部署

在 `.env` 文件中设置环境变量：

```bash
STUDIO_OPERATION_LOG_SWITCH=true
```

然后重建服务（restart 仅重启容器不会重读环境变量，需用 recreate 重建）：

```bash
bash deploy.sh recreate
```

### 2.2 直接部署（非 Docker）

在 `application-manager.yml` 中设置：

```yaml
studio:
  operationLog:
    switch: true
```

或通过环境变量设置：

```bash
export studio_operationLog_switch=true
```

> 需重启服务后生效（`@Value` 在启动时绑定，运行中修改环境变量不会立即生效）。所有带有 `@OperationLog` 注解的 Service 方法调用都会被记录。

---

## 三、日志存储位置

| 部署方式 | 日志路径 |
|---------|---------|
| Docker Compose | 容器内 `/opt/cloud/studio-manager/logs/audit/trace.log`（通过 `manager_logs` 数据卷映射到宿主机） |
| 直接部署 | `/opt/cloud/studio-manager/logs/audit/trace.log` |

Docker Compose 部署时，可通过以下命令查看数据卷映射路径：

```bash
docker volume ls | grep manager_logs
```

确认实际卷名后，使用 `docker volume inspect <卷名>` 查看映射路径。卷名前缀取决于部署目录名（如 `agent-studio_manager_logs` 或 `<目录名>_manager_logs`）。

---

## 四、日志格式

每条审计日志为一行 JSON，结构如下：

```json
{
  "timestamp": "2026-09-29T10:30:00.000Z",
  "traceId": "request-id-from-mdc",
  "userId": "user123",
  "userName": "张三",
  "operationType": "CREATE",
  "resourceType": "Agent",
  "resourceId": "agent-uuid",
  "resourceName": "我的智能体",
  "description": "创建智能体",
  "method": "createAgent",
  "success": true,
  "errorMessage": null,
  "params": {
    "projectId": "0",
    "body": {
      "name": "我的智能体"
    }
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | string | ISO-8601 格式的时间戳 |
| `traceId` | string | 请求追踪 ID，来自 MDC `request-id`，可用于关联应用日志 |
| `userId` | string | 操作者用户 ID |
| `userName` | string | 操作者用户名 |
| `operationType` | string | 操作类型，见下表 |
| `resourceType` | string | 资源类型，如 Agent/Workflow/Tool/MCP/KnowledgeBase 等 |
| `resourceId` | string | 资源 ID，从方法参数中提取 |
| `resourceName` | string | 资源名称，从方法参数中提取 |
| `description` | string | 操作描述 |
| `method` | string | 被审计的 Java 方法名 |
| `success` | boolean | 操作是否成功 |
| `errorMessage` | string/null | 操作失败时的异常信息，成功时为 `null` |
| `params` | object | 方法参数（已脱敏），JSON 格式 |

### 操作类型

| 操作类型 | 说明 |
|---------|------|
| `CREATE` | 创建资源 |
| `UPDATE` | 更新资源 |
| `DELETE` | 删除资源 |
| `READ` | 读取资源 |
| `EXPORT` | 导出资源 |
| `IMPORT` | 导入资源 |
| `EXECUTE` | 执行操作 |

---

## 五、审计覆盖范围

审计日志覆盖以下 Service 的关键操作（共 145 个审计点，26 个 Service）：

| Service | 审计点数 | 覆盖操作 |
|---------|---------|---------|
| `AgentManagementService` | 17 | 创建/更新/删除/发布/复制智能体等 |
| `WorkflowManagementService` | 17 | 创建/更新/删除/发布工作流等 |
| `PluginService` | 13 | 创建/删除/修改/导入/导出/发布插件 |
| `ToolManagementService` | 10 | 工具创建/更新/删除/发布等 |
| `KnowledgeBaseServiceImpl` | 9 | 知识库创建/更新/删除等 |
| `ComplexIntentManagementService` | 9 | 复杂意图的增删改查 |
| `EnvironmentServiceManagerService` | 7 | 环境服务管理 |
| `KnowledgeBaseDatasetServiceImpl` | 7 | 知识库数据集增删改 |
| `ModelServiceMgmtService` | 6 | 模型服务管理 |
| `McpServiceManager` | 6 | MCP 服务创建/部署/删除等 |
| `ShareResourceManagerService` | 5 | 资源共享管理 |
| `ProviderMgmtService` | 4 | 模型供应商管理 |
| `ProviderAuthService` | 4 | 供应商认证管理 |
| `MessageManagementService` | 4 | 消息模板/意图包/对象管理 |
| `WorkspaceService` | 3 | 工作空间增删改 |
| `WorkspaceMemberService` | 3 | 工作空间成员管理 |
| `RouterStrategyMgmtService` | 3 | 路由策略管理 |
| `ProviderAuthMgmtService` | 3 | 供应商认证信息管理 |
| `MemoryServiceInstanceService` | 3 | 记忆服务实例管理 |
| `MemoryRepoManagementService` | 3 | 记忆库管理 |
| `CustomObjectManagementService` | 3 | 自定义对象管理 |
| `SkillManagementService` | 2 | 技能管理 |
| `McpInnerService` | 1 | MCP 内部服务操作 |
| `CommonManagementService` | 1 | 通用管理操作 |
| `AppManagementService` | 1 | 应用管理 |
| `AgentServiceProxyService` | 1 | 代理服务操作 |

---

## 六、敏感字段脱敏

审计日志在序列化方法参数时，会自动对敏感字段的值进行掩码处理（替换为 `******`）。

### 默认脱敏规则

以下字段名（不区分大小写）会被脱敏：

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

### 自定义脱敏规则

在 `application-manager.yml` 中修改 `sensitiveFieldPattern` 正则表达式：

```yaml
studio:
  operationLog:
    switch: true
    sensitiveFieldPattern: '(?i)(?:.*(?:password|pwd|token|authorization|api[-_]?key|secret|credential|your_custom_field).*)'
```

---

## 七、日志滚动与保留

| 配置项 | 默认值 | 说明 |
|--------|-------|------|
| 单文件最大大小 | `50MB` | 超过后滚动到新文件，可通过环境变量 `TRACE_FILE_ROLLING_SIZE` 修改 |
| 最大文件数量 | `200` | 超过后删除最旧文件，可通过环境变量 `TRACE_FILE_MAX_COUNT` 修改 |
| 最长保留时间 | `180 天` | 超期自动清理，可通过环境变量 `TRACE_FILE_MAX_AGE` 修改 |
| 写入方式 | 异步 | 通过异步 Appender 写入，不影响业务性能 |

Docker Compose 部署时，在 `.env` 中设置：

```bash
TRACE_FILE_ROLLING_SIZE=50MB
TRACE_FILE_MAX_COUNT=200
TRACE_FILE_MAX_AGE=180d
```

---

## 八、日志查询示例

审计日志为 JSON 格式，每行一条记录，推荐使用 `jq` 工具查询：

```bash
# 查看所有失败的审计记录
cat /opt/cloud/studio-manager/logs/audit/trace.log | jq 'select(.success == false)'

# 按操作类型筛选
cat /opt/cloud/studio-manager/logs/audit/trace.log | jq 'select(.operationType == "CREATE")'

# 按用户筛选
cat /opt/cloud/studio-manager/logs/audit/trace.log | jq 'select(.userId == "user123")'

# 按时间段筛选
cat /opt/cloud/studio-manager/logs/audit/trace.log | jq 'select(.timestamp >= "2026-09-29" and .timestamp < "2026-09-30")'

# 查看特定资源的操作历史
cat /opt/cloud/studio-manager/logs/audit/trace.log | jq 'select(.resourceId == "agent-uuid")'

# 统计各操作类型的次数
cat /opt/cloud/studio-manager/logs/audit/trace.log | jq -r '.operationType' | sort | uniq -c | sort -rn

# 查看删除操作且失败的记录
cat /opt/cloud/studio-manager/logs/audit/trace.log | jq 'select(.operationType == "DELETE" and .success == false)'
```

Docker Compose 部署时，可通过 `docker exec` 查询：

```bash
docker exec agent-studio-studio-manager-1 cat /opt/cloud/studio-manager/logs/audit/trace.log | jq 'select(.success == false)'
```

---

## 九、与可观测性日志的区别

| 维度 | 审计日志 | 可观测性日志（VictoriaLogs） |
|------|---------|---------------------------|
| 用途 | 记录用户操作行为，用于安全审计 | 记录应用运行日志，用于排障监控 |
| 格式 | JSON（结构化） | 文本（半结构化） |
| 存储 | 独立文件 `audit/trace.log` | VictoriaLogs 数据库 |
| 保留 | 180 天 | 默认 7 天（可配置） |
| 开启 | 默认关闭，需设 `STUDIO_OPERATION_LOG_SWITCH=true` | 可选部署，见 [Docker Compose 部署指南 — 可观测性](./deploy-docker-compose.md#七可观测性日志聚合) |

两者相互独立，可同时启用。
