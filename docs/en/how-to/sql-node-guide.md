# SQL Custom Node Configuration Guide

## 1. Overview

The SQL custom node (Sql / DataQuery) allows workflows to access external databases via SQL statements, enabling data query and write capabilities. SQL execution is deployed in the Java manager; the Python runtime invokes it via HTTP.

### Architecture Overview

```
Workflow Execution → Python FlowSql Node → HTTP POST → Java manager DatasourceExecuteService
                                                           ↓
                                           HikariCP Connection Pool → Target Database (MySQL/PostgreSQL/GaussDB)
```

### Supported Database Types

| Database Type | JDBC Driver | Connection Property |
|---------------|------------|---------------------|
| MySQL | `org.mariadb.jdbc.Driver` | `allowLoadLocalInfile=false`, `allowUrlInLocalInfile=false` |
| PostgreSQL | `org.postgresql.Driver` | `stringtype=unspecified` (allows implicit type conversion) |
| GaussDB | `com.huawei.opengauss.jdbc.Driver` | `stringtype=unspecified` (allows implicit type conversion) |

> PostgreSQL and GaussDB are configured with `stringtype=unspecified`, which causes the JDBC driver to send string parameters as `unknown` type, allowing the database to infer and implicitly convert to the target column type (e.g., INTEGER, BOOLEAN), consistent with MySQL's lenient type behavior.

---

## 2. Configuration Reference

### 2.1 SQL Execution Configuration (Java Manager Side)

The following configuration items apply to the `studio-manager` service and control SQL execution security policies and resource limits.

| Configuration Key | Environment Variable | Default | Description |
|-------------------|---------------------|---------|-------------|
| `datasource.execute.timeout` | `datasource_execute_timeout` | `25` | SQL execution timeout (seconds); queries are automatically interrupted on timeout |
| `datasource.execute.max-response` | `datasource_execute_max_response` | `1000` | Maximum number of rows returned by a SQL query to prevent OOM from large result sets |
| `datasource.execute.sql-limit` | `datasource_execute_sql_limit` | `8000` | Maximum SQL statement length (characters); statements exceeding this are rejected |
| `datasource.execute.allowed-operations` | `datasource_execute_allowed_operations` | `SELECT,INSERT,UPDATE` | Allowed SQL operation types (comma-separated); DELETE, DROP, etc. are disabled by default |

### 2.2 Connection Pool Configuration (Java Manager Side)

The following configuration items control HikariCP connection pool and Caffeine LRU cache behavior.

| Configuration Key | Environment Variable | Default | Description |
|-------------------|---------------------|---------|-------------|
| `datasource.cache.hours` | `datasource_cache_hours` | `24` | Datasource connection pool cache TTL (hours); idle pools are automatically cleaned up after expiration |
| `datasource.cache.pool-size` | `datasource_cache_pool_size` | `150` | Maximum number of cached datasource connection pools (LRU eviction) |
| `datasource.max-connections-per-host` | `datasource_max_connections_per_host` | `5` | Maximum connections per datasource (HikariCP `maximumPoolSize`) |

> **Case Sensitivity Note**: Manager-side environment variables use lowercase snake_case format in the K8s YAML (e.g., `datasource_execute_timeout`), compatible with Spring Boot Relaxed Binding. Do **not** add uppercase variants (e.g., `DATASOURCE_EXECUTE_TIMEOUT`) alongside the lowercase ones — when both exist, Spring's `SystemEnvironmentPropertySource` resolves the lowercase variable first, and the uppercase value will not take effect. Runtime-side environment variables (see Section 2.3) use uppercase format because Python's `os.getenv()` is case-sensitive.

> Fixed connection pool parameters (not configurable): `minimumIdle=2`, `idleTimeout=300000ms` (5 min), `maxLifetime=1800000ms` (30 min), `keepaliveTime=120000ms` (2 min), `connectionTimeout=10000ms` (10 sec).

### 2.3 Runtime Configuration (Python Runtime Side)

The following configuration items apply to the `studio-runtime` service and control HTTP call behavior for SQL nodes on the Python side.

| Environment Variable | Default | Description |
|----------------------|---------|-------------|
| `AGENT_MANAGER_ENDPOINT` | `http://studio-manager:31111` | Java manager service address; SQL nodes call the SQL execution API via this address |
| `DATASOURCE_EXECUTE_TIMEOUT` | `25` | SQL execution HTTP call timeout (seconds); should match or be slightly larger than the manager-side `datasource.execute.timeout` |

> When `AGENT_MANAGER_ENDPOINT` is empty, the SQL node will raise an error (code 101755) indicating the manager is not deployed. When HTTPS is enabled, change the prefix to `https://`.

---

## 3. K8s Deployment Configuration

### 3.1 studio-manager.yaml

SQL node/datasource execution configuration is pre-configured in `deploy/k8s/studio-manager.yaml` under the `[Optional] SQL Node / Datasource Execution Configuration` section. The default values usually require no modification:

```yaml
# ======== [Optional] SQL Node / Datasource Execution Configuration ========
# SQL execution timeout (seconds); queries are automatically interrupted on timeout
- name: datasource_execute_timeout
  value: '25'
# Maximum rows returned by SQL execution to prevent OOM from large result sets
- name: datasource_execute_max_response
  value: '1000'
# Maximum SQL statement length (characters); statements exceeding this are rejected
- name: datasource_execute_sql_limit
  value: '8000'
# Allowed SQL operation types (comma-separated); only SELECT/INSERT/UPDATE allowed by default
- name: datasource_execute_allowed_operations
  value: 'SELECT,INSERT,UPDATE'
# Datasource connection pool cache TTL (hours); idle pools are automatically cleaned up after expiration
- name: datasource_cache_hours
  value: '24'
# Maximum number of cached datasource connection pools (LRU eviction)
- name: datasource_cache_pool_size
  value: '150'
# Maximum connections per datasource (HikariCP maximumPoolSize)
- name: datasource_max_connections_per_host
  value: '5'
```

### 3.2 studio-runtime.yaml

SQL node runtime configuration is pre-configured in `deploy/k8s/studio-runtime.yaml` under the `[Optional] SQL Node Configuration` section:

```yaml
# ======== [Optional] SQL Node Configuration ========
# Java manager service address (SQL nodes call manager via HTTP to execute SQL); change to https for HTTPS
- name: AGENT_MANAGER_ENDPOINT
  value: 'http://studio-manager:31111'
# SQL execution HTTP call timeout (seconds)
- name: DATASOURCE_EXECUTE_TIMEOUT
  value: '25'
```

### 3.3 Configuration Adjustment Examples

**Scenario: Increase max query rows to 5000 and timeout to 60 seconds**

Modify `studio-manager.yaml`:
```yaml
- name: datasource_execute_max_response
  value: '5000'
- name: datasource_execute_timeout
  value: '60'
```

Synchronize `studio-runtime.yaml` (HTTP timeout should be >= manager timeout):
```yaml
- name: DATASOURCE_EXECUTE_TIMEOUT
  value: '65'
```

**Scenario: Allow DELETE operations**

Modify `studio-manager.yaml`:
```yaml
- name: datasource_execute_allowed_operations
  value: 'SELECT,INSERT,UPDATE,DELETE'
```

---

## 4. Configuration-to-Code Mapping

| Configuration Key | Code Location | Description |
|-------------------|---------------|-------------|
| `datasource.execute.timeout` | `DatasourceExecuteService.java` `@Value("${datasource.execute.timeout:25}")` | `statement.setQueryTimeout()` |
| `datasource.execute.max-response` | `DatasourceExecuteService.java` `@Value("${datasource.execute.max-response:1000}")` | `convertResultSetToResp()` row limit |
| `datasource.execute.sql-limit` | `DatasourceExecuteService.java` `@Value("${datasource.execute.sql-limit:8000}")` | `validateSqlStatement()` length check |
| `datasource.execute.allowed-operations` | `DatasourceExecuteService.java` `@Value("${datasource.execute.allowed-operations:SELECT,INSERT,UPDATE}")` | `validateSqlStatement()` whitelist |
| `datasource.cache.hours` | `DatasourceConnectionFactory.java` `@Value("${datasource.cache.hours:24}")` | Caffeine `expireAfterAccess` |
| `datasource.cache.pool-size` | `DatasourceConnectionFactory.java` `@Value("${datasource.cache.pool-size:150}")` | Caffeine `maximumSize` |
| `datasource.max-connections-per-host` | `DatasourceConnectionFactory.java` `@Value("${datasource.max-connections-per-host:5}")` | HikariCP `maximumPoolSize` |
| `AGENT_MANAGER_ENDPOINT` | `flow_sql.py` `os.getenv("AGENT_MANAGER_ENDPOINT", "")` | HTTP call target address |
| `DATASOURCE_EXECUTE_TIMEOUT` | `flow_sql.py` `int(os.getenv("DATASOURCE_EXECUTE_TIMEOUT", "25"))` | aiohttp request timeout |

---

## 5. SQL Security Policies

The SQL execution service includes multiple layers of security protection:

| Protection Layer | Description | Related Configuration |
|------------------|-------------|----------------------|
| Operation whitelist | Only SELECT/INSERT/UPDATE allowed (configurable) | `datasource.execute.allowed-operations` |
| Length limit | SQL statements max 8000 characters (configurable) | `datasource.execute.sql-limit` |
| Multi-statement prohibition | Rejects semicolon-delimited multiple SQL statements | Fixed rule |
| Comment prohibition | Rejects `--`, `/* */` comments | Fixed rule |
| Injection detection | Rejects `OR 1=1`, `AND 1=1` | Fixed rule |
| Hexadecimal detection | Rejects `0x` encoding | Fixed rule |
| Dangerous function detection | Rejects `LOAD_FILE`, `INTO OUTFILE`, `SLEEP`, `BENCHMARK` | Fixed rule |
| Parameterized queries | Uses PreparedStatement `?` placeholders to prevent SQL injection | Fixed rule |
| Inline variable validation | `{{{variable}}}` inline replacement must pass character whitelist and keyword blacklist checks | Fixed rule |

---

## 6. Datasource Management

Datasources are managed via the frontend **Development Configuration → Datasource Management** page, which supports creation, editing, deletion, and connectivity checks.

### Datasource Connection Parameters

| Parameter | Description |
|-----------|-------------|
| Datasource name | Max 64 characters, unique within the workspace |
| Description | Max 2048 characters (optional) |
| Database type | MySQL / PostgreSQL / GaussDB |
| Network type | Public access |
| Host address | Database IP or domain name |
| Port | MySQL default 3306, PostgreSQL/GaussDB default 5432 |
| Database name | Target database name |
| SASL_SSL | Whether to enable SSL connection |
| Username | Database login username |
| Password | Database login password (encrypted at rest) |

### REST API

Datasource management endpoints (`DatasourceController`, path prefix `/v1/{project_id}/agent-manager/datasource`; all endpoints require the `workspace_id` query parameter):

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/{project_id}/agent-manager/datasource?workspace_id={wid}` | Create datasource |
| GET | `/v1/{project_id}/agent-manager/datasource?workspace_id={wid}` | List datasources |
| GET | `/v1/{project_id}/agent-manager/datasource/{datasource_id}?workspace_id={wid}` | Get datasource details |
| PUT | `/v1/{project_id}/agent-manager/datasource/{datasource_id}?workspace_id={wid}` | Update datasource |
| DELETE | `/v1/{project_id}/agent-manager/datasource/{datasource_id}?workspace_id={wid}` | Delete datasource |
| POST | `/v1/{project_id}/agent-manager/datasource/batch-delete?workspace_id={wid}` | Batch delete |
| GET | `/v1/{project_id}/agent-manager/datasource/{datasource_id}/tables?workspace_id={wid}` | List tables |
| GET | `/v1/{project_id}/agent-manager/datasource/{datasource_id}/tables/{table_name}/columns?workspace_id={wid}` | Get column info |

SQL execution endpoint (`DatasourceExecuteController`, called by the Python runtime):

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/studio/datasources/{datasource_id}/execute` | Execute SQL |

---

## 7. FAQ

### Q1: SQL node reports "manager not deployed"

**Cause**: The `AGENT_MANAGER_ENDPOINT` environment variable is not configured or is empty.

**Solution**: Configure `AGENT_MANAGER_ENDPOINT` in `studio-runtime.yaml` to point to the manager service address.

### Q2: PostgreSQL query reports type error

**Cause**: Parameter values are sent as VARCHAR type; PostgreSQL's strict type checking rejects implicit conversion.

**Solution**: This has been fixed via the `stringtype=unspecified` connection property. If the issue persists, ensure the connection pool has been rebuilt (modify the datasource or restart the manager).

### Q3: SQL execution timeout

**Cause**: Query execution time exceeds `datasource.execute.timeout` (default 25 seconds).

**Solution**: Increase `datasource_execute_timeout` (manager side) and `DATASOURCE_EXECUTE_TIMEOUT` (runtime side). Note that the runtime-side timeout should be slightly larger than the manager-side timeout.

### Q4: Connection Pool Caching and Rebuild Mechanism

**Description**: Connection pools are managed by a Caffeine LRU cache with a TTL of `datasource.cache.hours` (default 24 hours). When a datasource is modified on the datasource management page, `modifyDatasource` proactively calls `removeConnectionPool` to destroy the old connection pool; a new pool is automatically created on the next SQL execution. No manager restart is required.

**Note**: If connection information (e.g., password) is changed directly on the database side without updating the datasource configuration, the connection pool will not be rebuilt. In this case, edit the datasource on the management page (to trigger a rebuild), or wait for the cache TTL to expire for automatic cleanup.
