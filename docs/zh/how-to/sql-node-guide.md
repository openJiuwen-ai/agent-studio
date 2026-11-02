# SQL 自定义节点配置指南

## 一、概述

SQL 自定义节点（Sql / DataQuery）允许在工作流中通过 SQL 语句访问外部数据库，实现数据查询与写入能力。SQL 执行能力部署在 Java manager 中，Python 运行时通过 HTTP 调用执行。

### 架构简介

```
工作流执行 → Python FlowSql 节点 → HTTP POST → Java manager DatasourceExecuteService
                                                          ↓
                                          HikariCP 连接池 → 目标数据库 (MySQL/PostgreSQL/GaussDB)
```

### 支持的数据库类型

| 数据库类型 | JDBC 驱动 | 连接属性 |
|-----------|----------|---------|
| MySQL | `org.mariadb.jdbc.Driver` | `allowLoadLocalInfile=false`, `allowUrlInLocalInfile=false` |
| PostgreSQL | `org.postgresql.Driver` | `stringtype=unspecified`（允许隐式类型转换） |
| GaussDB | `com.huawei.opengauss.jdbc.Driver` | `stringtype=unspecified`（允许隐式类型转换） |

> PostgreSQL 和 GaussDB 配置了 `stringtype=unspecified`，使 JDBC 驱动以 `unknown` 类型发送字符串参数，由数据库自行推断并隐式转换为目标列类型（如 INTEGER、BOOLEAN 等），与 MySQL 的宽松类型行为一致。

---

## 二、配置项说明

### 2.1 SQL 执行配置（Java manager 侧）

以下配置项作用于 `studio-manager` 服务，控制 SQL 执行的安全策略和资源限制。

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|---------|--------|------|
| `datasource.execute.timeout` | `datasource_execute_timeout` | `25` | SQL 执行超时时间（秒），超时自动中断查询 |
| `datasource.execute.max-response` | `datasource_execute_max_response` | `1000` | SQL 查询最大返回行数，防止大结果集导致 OOM |
| `datasource.execute.sql-limit` | `datasource_execute_sql_limit` | `8000` | SQL 语句最大长度（字符数），超长拒绝执行 |
| `datasource.execute.allowed-operations` | `datasource_execute_allowed_operations` | `SELECT,INSERT,UPDATE` | 允许的 SQL 操作类型（逗号分隔），默认禁止 DELETE、DROP 等 |

### 2.2 连接池配置（Java manager 侧）

以下配置项控制 HikariCP 连接池和 Caffeine LRU 缓存的行为。

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|---------|--------|------|
| `datasource.cache.hours` | `datasource_cache_hours` | `24` | 数据源连接池缓存 TTL（小时），超时自动清理空闲连接池 |
| `datasource.cache.pool-size` | `datasource_cache_pool_size` | `150` | 数据源连接池缓存最大数量（LRU 淘汰） |
| `datasource.max-connections-per-host` | `datasource_max_connections_per_host` | `5` | 单个数据源最大连接数（HikariCP `maximumPoolSize`） |

> **大小写说明**：manager 侧环境变量在 K8s YAML 中使用小写下划线格式（如 `datasource_execute_timeout`），与 Spring Boot Relaxed Binding 兼容。请勿同时添加大写格式变量（如 `DATASOURCE_EXECUTE_TIMEOUT`）——当两者同时存在时，Spring `SystemEnvironmentPropertySource` 会优先解析小写变量，大写变量的值不会生效。runtime 侧环境变量（见 2.3 节）使用大写格式，因 Python `os.getenv()` 区分大小写。

> 连接池固定参数（不可配置）：`minimumIdle=2`、`idleTimeout=300000ms`(5分钟)、`maxLifetime=1800000ms`(30分钟)、`keepaliveTime=120000ms`(2分钟)、`connectionTimeout=10000ms`(10秒)。

### 2.3 运行时配置（Python runtime 侧）

以下配置项作用于 `studio-runtime` 服务，控制 Python 侧 SQL 节点的 HTTP 调用行为。

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `AGENT_MANAGER_ENDPOINT` | `http://studio-manager:31111` | Java manager 服务地址，SQL 节点通过此地址调用 SQL 执行 API |
| `DATASOURCE_EXECUTE_TIMEOUT` | `25` | SQL 执行 HTTP 调用超时时间（秒），应与 manager 侧 `datasource.execute.timeout` 保持一致或略大 |

> `AGENT_MANAGER_ENDPOINT` 为空时，SQL 节点将报错（错误码 101755），提示 manager 未部署。HTTPS 启动时需改为 `https://` 前缀。

---

## 三、K8s 部署配置

### 3.1 studio-manager.yaml

SQL 节点/数据源执行配置已预置在 `deploy/k8s/studio-manager.yaml` 的 `[选填] SQL节点/数据源执行配置` 区域，默认值通常无需修改：

```yaml
# ======== [选填] SQL节点/数据源执行配置 ========
# SQL执行超时时间（秒），超时自动中断查询
- name: datasource_execute_timeout
  value: '25'
# SQL执行最大返回行数，防止大结果集OOM
- name: datasource_execute_max_response
  value: '1000'
# SQL语句最大长度（字符数），超长拒绝执行
- name: datasource_execute_sql_limit
  value: '8000'
# 允许的SQL操作类型（逗号分隔），默认仅允许 SELECT/INSERT/UPDATE
- name: datasource_execute_allowed_operations
  value: 'SELECT,INSERT,UPDATE'
# 数据源连接池缓存TTL（小时），超时自动清理空闲连接池
- name: datasource_cache_hours
  value: '24'
# 数据源连接池缓存最大数量（LRU淘汰）
- name: datasource_cache_pool_size
  value: '150'
# 单个数据源最大连接数（HikariCP maximumPoolSize）
- name: datasource_max_connections_per_host
  value: '5'
```

### 3.2 studio-runtime.yaml

SQL 节点运行时配置已预置在 `deploy/k8s/studio-runtime.yaml` 的 `[选填] SQL节点配置` 区域：

```yaml
# ======== [选填] SQL节点配置 ========
# Java manager 服务地址（SQL节点通过HTTP调用manager执行SQL），HTTPS启动需改成https
- name: AGENT_MANAGER_ENDPOINT
  value: 'http://studio-manager:31111'
# SQL执行HTTP调用超时时间（秒）
- name: DATASOURCE_EXECUTE_TIMEOUT
  value: '25'
```

### 3.3 调整配置示例

**场景：增大查询返回行数至 5000，超时调整至 60 秒**

修改 `studio-manager.yaml`：
```yaml
- name: datasource_execute_max_response
  value: '5000'
- name: datasource_execute_timeout
  value: '60'
```

同步修改 `studio-runtime.yaml`（HTTP 超时应 ≥ manager 超时）：
```yaml
- name: DATASOURCE_EXECUTE_TIMEOUT
  value: '65'
```

**场景：允许 DELETE 操作**

修改 `studio-manager.yaml`：
```yaml
- name: datasource_execute_allowed_operations
  value: 'SELECT,INSERT,UPDATE,DELETE'
```

---

## 四、配置项与代码映射

| 配置项 | 代码位置 | 说明 |
|--------|---------|------|
| `datasource.execute.timeout` | `DatasourceExecuteService.java` `@Value("${datasource.execute.timeout:25}")` | `statement.setQueryTimeout()` |
| `datasource.execute.max-response` | `DatasourceExecuteService.java` `@Value("${datasource.execute.max-response:1000}")` | `convertResultSetToResp()` 行数限制 |
| `datasource.execute.sql-limit` | `DatasourceExecuteService.java` `@Value("${datasource.execute.sql-limit:8000}")` | `validateSqlStatement()` 长度校验 |
| `datasource.execute.allowed-operations` | `DatasourceExecuteService.java` `@Value("${datasource.execute.allowed-operations:SELECT,INSERT,UPDATE}")` | `validateSqlStatement()` 白名单 |
| `datasource.cache.hours` | `DatasourceConnectionFactory.java` `@Value("${datasource.cache.hours:24}")` | Caffeine `expireAfterAccess` |
| `datasource.cache.pool-size` | `DatasourceConnectionFactory.java` `@Value("${datasource.cache.pool-size:150}")` | Caffeine `maximumSize` |
| `datasource.max-connections-per-host` | `DatasourceConnectionFactory.java` `@Value("${datasource.max-connections-per-host:5}")` | HikariCP `maximumPoolSize` |
| `AGENT_MANAGER_ENDPOINT` | `flow_sql.py` `os.getenv("AGENT_MANAGER_ENDPOINT", "")` | HTTP 调用目标地址 |
| `DATASOURCE_EXECUTE_TIMEOUT` | `flow_sql.py` `int(os.getenv("DATASOURCE_EXECUTE_TIMEOUT", "25"))` | aiohttp 请求超时 |

---

## 五、SQL 安全策略

SQL 执行服务内置多层安全防护：

| 防护层 | 说明 | 对应配置项 |
|--------|------|-----------|
| 操作白名单 | 仅允许 SELECT/INSERT/UPDATE（可配置） | `datasource.execute.allowed-operations` |
| 长度限制 | SQL 语句最大 8000 字符（可配置） | `datasource.execute.sql-limit` |
| 禁止多语句 | 拒绝分号分隔的多条 SQL | 固定规则 |
| 禁止注释 | 拒绝 `--`、`/* */` 注释 | 固定规则 |
| 条件注入检测 | 拒绝 `OR 1=1`、`AND 1=1` | 固定规则 |
| 十六进制检测 | 拒绝 `0x` 编码 | 固定规则 |
| 危险函数检测 | 拒绝 `LOAD_FILE`、`INTO OUTFILE`、`SLEEP`、`BENCHMARK` | 固定规则 |
| 参数化查询 | 使用 PreparedStatement `?` 占位符，防止 SQL 注入 | 固定规则 |
| 内联变量校验 | `{{{variable}}}` 内联替换需通过字符白名单和关键词黑名单校验 | 固定规则 |

---

## 六、数据源管理

数据源通过前端「开发配置 → 数据源管理」页面进行管理，支持创建、编辑、删除、连通性检查。

### 支持的数据源连接参数

| 参数 | 说明 |
|------|------|
| 数据源名称 | 最长 64 字符，工作空间内唯一 |
| 描述 | 最长 2048 字符（选填） |
| 数据库类型 | MySQL / PostgreSQL / GaussDB |
| 网络类型 | 公网访问 |
| 主机地址 | 数据库 IP 或域名 |
| 端口 | MySQL 默认 3306，PostgreSQL/GaussDB 默认 5432 |
| 数据库名 | 目标数据库名称 |
| SASL_SSL | 是否启用 SSL 连接 |
| 用户名 | 数据库登录用户名 |
| 密码 | 数据库登录密码（加密存储） |

### REST API

数据源管理接口（`DatasourceController`，路径前缀 `/v1/{project_id}/agent-manager/datasource`，所有接口均需 `workspace_id` 查询参数）：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/{project_id}/agent-manager/datasource?workspace_id={wid}` | 创建数据源 |
| GET | `/v1/{project_id}/agent-manager/datasource?workspace_id={wid}` | 列表查询 |
| GET | `/v1/{project_id}/agent-manager/datasource/{datasource_id}?workspace_id={wid}` | 查询详情 |
| PUT | `/v1/{project_id}/agent-manager/datasource/{datasource_id}?workspace_id={wid}` | 修改数据源 |
| DELETE | `/v1/{project_id}/agent-manager/datasource/{datasource_id}?workspace_id={wid}` | 删除数据源 |
| POST | `/v1/{project_id}/agent-manager/datasource/batch-delete?workspace_id={wid}` | 批量删除 |
| GET | `/v1/{project_id}/agent-manager/datasource/{datasource_id}/tables?workspace_id={wid}` | 查询表列表 |
| GET | `/v1/{project_id}/agent-manager/datasource/{datasource_id}/tables/{table_name}/columns?workspace_id={wid}` | 查询列信息 |

SQL 执行接口（`DatasourceExecuteController`，供 Python 运行时调用）：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/studio/datasources/{datasource_id}/execute` | 执行 SQL |

---

## 七、常见问题

### Q1: SQL 节点报错 "manager not deployed"

**原因**：`AGENT_MANAGER_ENDPOINT` 环境变量未配置或为空。

**解决**：在 `studio-runtime.yaml` 中配置 `AGENT_MANAGER_ENDPOINT` 指向 manager 服务地址。

### Q2: PostgreSQL 查询报类型错误

**原因**：参数值以 VARCHAR 类型发送，PostgreSQL 严格类型检查拒绝隐式转换。

**解决**：已通过 `stringtype=unspecified` 连接属性修复。如果仍有问题，确认连接池已重建（修改数据源或重启 manager）。

### Q3: SQL 执行超时

**原因**：查询耗时超过 `datasource.execute.timeout`（默认 25 秒）。

**解决**：调大 `datasource.execute_timeout`（manager 侧）和 `DATASOURCE_EXECUTE_TIMEOUT`（runtime 侧），注意 runtime 侧应略大于 manager 侧。

### Q4: 连接池缓存与重建机制

**说明**：连接池以 Caffeine LRU 缓存按 `datasource.cache.hours`（默认 24 小时）TTL 管理。在数据源管理页面修改数据源时，`modifyDatasource` 会主动调用 `removeConnectionPool` 销毁旧连接池，下次执行 SQL 时自动创建新连接池，无需重启 manager。

**注意**：若直接在数据库侧修改了连接信息（如密码变更），因数据源配置未变更，连接池不会重建。此时需在数据源管理页面编辑该数据源（触发重建），或等待缓存 TTL 过期后自动清理。
