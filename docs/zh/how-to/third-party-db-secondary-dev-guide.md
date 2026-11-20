# Studio 三方数据库二次开发适配指导

本文教你在**不改 Studio 产品源码**的前提下，自己做出一个「外部扩展包」，把 `studio-manager` 接到三方关系库（以 **SQL Server** 为完整示例；达梦 / Oracle 等按同一步骤改方言规则即可）。

**边界说明**：

- 这是**部署侧外部扩展**，扩展包与方言规则需自行维护、按第 9 节验收；上游产品升级后可能要重测/微调改写规则。  
- 本文 SQL Server 示例可按步骤落地；**达梦 / Oracle 没有整份可直接粘贴的完整改写代码**，只保证流程相同（改识别、`rewrite()`、profile、DDL）。

---

## 0. 做完长什么样

最终你本地会有一个扩展目录（名字自定，下文用 `studio-db-ext`）：

```text
studio-db-ext/
  src/com/openjiuwen/studio/ext/
    ExtJdbcUrlDatabaseIdProvider.java
    VendorSqlRewriteInterceptor.java
    ExtDbAutoConfiguration.java
  src/META-INF/spring/
    org.springframework.boot.autoconfigure.AutoConfiguration.imports
  mapper/                           # 可选：databaseId=sqlserver 的外部 Mapper XML
    AgentMapperSqlServer.xml        # 例：FROM_UNIXTIME → DATEADD
    McpServerRatingMapperSqlServer.xml  # 可选：评分 upsert 用 MERGE（Interceptor 已有兜底）
  classes/                          # javac 输出（打 jar 前把 mapper 拷到 classes/ext-mapper/）
  ext/
    studio-db-ext.jar               # 打好的扩展包
  lib/
    mssql-jdbc-x.y.z.jre11.jar      # 目标库驱动（自行下载）
    mybatis-3.5.x.jar                 # 编译 Interceptor 用（与产品 MyBatis 大版本接近即可）
    spring-context-*.jar …          # 编译 @Configuration 用（见第 3 步）
  config/
    application-sqlserver.yml
  sql/
    ddl_sqlserver.sql               # 你翻译后的建表脚本
    ddl_knowledge_sqlserver.sql
    dml_empty.sql
  bin/
    start-with-ext.sh
```

运行时把该目录挂进 manager 容器（如 `/opt/ext`），用包装脚本启动，使扩展 jar + 驱动进入应用类路径。

---

## 1. 原理（先看 1 分钟）

产品默认按 MySQL 语法跑。换三方库时，通过产品已开放的能力注入下面几件事：

| 做什么 | 用什么开放能力 |
|---|---|
| 告诉 MyBatis「当前是 sqlserver/dm/…」 | 自定义 `DatabaseIdProvider`（`@Primary` Bean） |
| 把 SQL 里的 MySQL 写法改成目标库写法 | MyBatis `Interceptor`（运行时改写） |
| 个别语句用目标库专用 SQL | 外部 Mapper XML（`databaseId=sqlserver`，且**排在**内置 mapper 之前） |
| 加载你的扩展 jar 和 JDBC 驱动 | `PropertiesLauncher` + `-Dloader.path=...`（不要用 `java -jar`） |
| 换连接串、方言、DDL 路径 | 环境变量 / 外部 `application-*.yml` |

业务 REST 不用改；改的是**部署与扩展包**。

> Interceptor 适合改 LIMIT / 布尔 / 反引号 / `UUID()` / `NOW()` / 已知的 `ON DUPLICATE` 等碎片。  
> `FROM_UNIXTIME` 这类整段函数更适合用**外部 Mapper** 写成 `DATEADD`（见步骤 3.6）。  
> 裸 MySQL `SELECT ... FOR UPDATE` 不要指望 Interceptor 自动改；定时任务锁走 Quartz `MSSQLDelegate`。

---

## 2. 准备环境

1. JDK 17（与产品 manager 一致）  
2. 目标库已安装，能建库（示例库名 `agentbuilder`；产品默认部署里常见 `agent-builder`，**名字自定，只要与 JDBC URL 一致**）  
3. 已有可运行的 `studio-manager` 镜像/进程（仍连着原库也可以，稍后切换）  
4. 下载目标库 JDBC 驱动，放到 `studio-db-ext/lib/`  
5. 为编译准备依赖 jar（放到 `lib/`）：
   - `mybatis-3.5.x.jar`（Interceptor API）
   - 编译 `@Configuration`：再准备 `spring-context` / `spring-beans` / `spring-core` / `spring-jcl`（版本接近产品即可）

> 驱动与依赖 jar **由你自行从厂商/Maven 中央仓库获取**，本文不附带二进制。

---

## 3. 写扩展代码

包名可用 `com.openjiuwen.studio.ext`（示例），也可改成你们公司包名，但 AutoConfiguration 注册名要一致。

### 步骤 3.1 建目录

```bash
mkdir -p studio-db-ext/src/com/openjiuwen/studio/ext
mkdir -p studio-db-ext/src/META-INF/spring
mkdir -p studio-db-ext/{classes,ext,lib,config,sql,bin,mapper}
```

### 步骤 3.2 方言识别：`ExtJdbcUrlDatabaseIdProvider.java`

创建文件 `studio-db-ext/src/com/openjiuwen/studio/ext/ExtJdbcUrlDatabaseIdProvider.java`：

```java
package com.openjiuwen.studio.ext;

import org.apache.ibatis.mapping.DatabaseIdProvider;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.Properties;

public class ExtJdbcUrlDatabaseIdProvider implements DatabaseIdProvider {
    private Properties properties;

    @Override
    public void setProperties(Properties p) {
        this.properties = p;
    }

    @Override
    public String getDatabaseId(DataSource dataSource) throws SQLException {
        try (Connection conn = dataSource.getConnection()) {
            String url = conn.getMetaData().getURL();
            System.out.println("[ExtJdbc] JDBC URL = " + url);
            if (url != null) {
                String u = url.toLowerCase();
                if (u.contains("jdbc:dm:") || u.contains(":dm://")) return "dm";
                if (u.contains("oracle") || u.contains(":thin:@")) return "oracle";
                if (u.contains("sqlserver") || u.contains("jdbc:sqlserver:")) {
                    System.out.println("[ExtJdbc] detected SQL Server -> sqlserver");
                    return "sqlserver";
                }
                if (u.contains("postgresql")) return "postgres";
                if (u.contains("mysql") || u.contains("mariadb") || u.contains("opengauss")) return "mysql";
            }
            String product = conn.getMetaData().getDatabaseProductName();
            if (product != null) {
                String p = product.toLowerCase();
                if (p.contains("dm") || p.contains("dameng")) return "dm";
                if (p.contains("oracle")) return "oracle";
                if (p.contains("microsoft") || p.contains("sql server")) return "sqlserver";
            }
            return null;
        }
    }
}
```

达梦 / Oracle：保证 URL 能命中上面的分支即可。

### 步骤 3.3 SQL 改写：`VendorSqlRewriteInterceptor.java`

创建 `VendorSqlRewriteInterceptor.java`（SQL Server 完整可跑版本；其他库改 `rewrite()` 即可）：

```java
package com.openjiuwen.studio.ext;

import org.apache.ibatis.executor.statement.StatementHandler;
import org.apache.ibatis.mapping.BoundSql;
import org.apache.ibatis.mapping.ParameterMapping;
import org.apache.ibatis.plugin.Interceptor;
import org.apache.ibatis.plugin.Intercepts;
import org.apache.ibatis.plugin.Invocation;
import org.apache.ibatis.plugin.Plugin;
import org.apache.ibatis.plugin.Signature;
import org.apache.ibatis.reflection.MetaObject;
import org.apache.ibatis.reflection.SystemMetaObject;

import java.sql.Connection;
import java.util.List;
import java.util.Properties;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Intercepts({
    @Signature(type = StatementHandler.class, method = "prepare",
        args = {Connection.class, Integer.class})
})
public class VendorSqlRewriteInterceptor implements Interceptor {

    private static final Pattern LIMIT_OFFSET =
        Pattern.compile("(?i)\\blimit\\s+(\\d+|\\?)\\s+offset\\s+(\\d+|\\?)");
    private static final Pattern LIMIT_COMMA =
        Pattern.compile("(?i)\\blimit\\s+(\\d+|\\?)\\s*,\\s*(\\d+|\\?)");
    private static final Pattern LIMIT_ONLY =
        Pattern.compile("(?i)\\blimit\\s+(\\d+|\\?)");
    private static final Pattern FETCH_NEXT_ZERO =
        Pattern.compile("(?i)\\boffset\\s+(\\d+|\\?)\\s+rows\\s+fetch\\s+next\\s+0\\s+rows\\s+only");
    private static final Pattern FETCH_NEXT_PARAM =
        Pattern.compile("(?i)\\bfetch\\s+next\\s+\\?\\s+rows\\s+only\\s*$");

    @Override
    public Object intercept(Invocation invocation) throws Throwable {
        StatementHandler handler = (StatementHandler) invocation.getTarget();
        BoundSql boundSql = handler.getBoundSql();
        String sql = boundSql.getSql();
        if (sql == null) {
            return invocation.proceed();
        }
        String lower = sql.toLowerCase();
        if (needsRewrite(sql, lower)) {
            String rewritten = rewrite(sql);
            if (!rewritten.equals(sql)) {
                SystemMetaObject.forObject(boundSql).setValue("sql", rewritten);
                sql = rewritten;
                lower = sql.toLowerCase();
                System.out.println("[VendorSqlRewrite] rewrote dialect fragments");
            }
        }
        if (lower.contains("fetch next")) {
            clampZeroFetch(boundSql);
        }
        return invocation.proceed();
    }

    private static boolean needsRewrite(String sql, String lower) {
        return lower.contains("limit")
            || lower.contains(" false") || lower.contains(" true")
            || lower.contains("=false") || lower.contains("=true")
            || lower.contains(" is true") || lower.contains(" is false")
            || sql.indexOf('`') >= 0
            || lower.contains("uuid(") || lower.contains("now(")
            || lower.contains("on duplicate key update");
    }

    /** SQL Server 完整规则；达梦/Oracle 请按厂商语法改此方法 */
    static String rewrite(String sql) {
        String s = sql;
        s = s.replaceAll("`([^`]+)`", "[$1]");                 // 反引号 -> []
        s = s.replaceAll("(?i)\\bUUID\\s*\\(\\s*\\)", "NEWID()");
        s = s.replaceAll("(?i)\\bNOW\\s*\\(\\s*\\)", "SYSUTCDATETIME()");
        s = s.replaceAll("(?i)\\bis\\s+not\\s+true\\b", "<> 1");
        s = s.replaceAll("(?i)\\bis\\s+not\\s+false\\b", "<> 0");
        s = s.replaceAll("(?i)\\bis\\s+true\\b", "= 1");
        s = s.replaceAll("(?i)\\bis\\s+false\\b", "= 0");
        s = s.replaceAll("(?i)=\\s*true\\b", "= 1");
        s = s.replaceAll("(?i)=\\s*false\\b", "= 0");
        // ON DUPLICATE → MERGE（产品当前命中：ws_mcp_server_rating 评分 upsert）
        s = rewriteOnDuplicateKeyUpdate(s);

        Matcher m = LIMIT_OFFSET.matcher(s);
        if (m.find()) {
            return m.replaceAll("OFFSET $2 ROWS FETCH NEXT $1 ROWS ONLY");
        }
        m = LIMIT_COMMA.matcher(s);
        if (m.find()) {
            return m.replaceAll("OFFSET $1 ROWS FETCH NEXT $2 ROWS ONLY");
        }
        m = LIMIT_ONLY.matcher(s);
        if (m.find()) {
            s = m.replaceAll("OFFSET 0 ROWS FETCH NEXT $1 ROWS ONLY");
        }
        s = FETCH_NEXT_ZERO.matcher(s)
            .replaceAll("AND 1 = 0 OFFSET $1 ROWS FETCH NEXT 1 ROWS ONLY");
        return s;
    }

    /** 仅覆盖产品现网 ODKU：McpServerRatingMapper.insertRating；其他表请加外部 Mapper */
    static String rewriteOnDuplicateKeyUpdate(String sql) {
        String lower = sql.toLowerCase();
        if (!lower.contains("on duplicate key update") || !lower.contains("ws_mcp_server_rating")) {
            return sql;
        }
        return "MERGE INTO ws_mcp_server_rating AS target "
            + "USING (SELECT #{serverId} AS server_id, #{tenantId} AS tenant_id, #{score} AS score) AS source "
            + "ON (target.server_id = source.server_id AND target.tenant_id = source.tenant_id) "
            + "WHEN MATCHED THEN UPDATE SET score = source.score, updated_date = SYSUTCDATETIME() "
            + "WHEN NOT MATCHED THEN INSERT (server_id, tenant_id, score, created_date, updated_date) "
            + "VALUES (source.server_id, source.tenant_id, source.score, SYSUTCDATETIME(), SYSUTCDATETIME())";
    }

    static boolean clampZeroFetch(BoundSql boundSql) {
        String sql = boundSql.getSql();
        if (sql == null) return false;
        Matcher lit = FETCH_NEXT_ZERO.matcher(sql);
        if (lit.find()) {
            String patched = forceEmptyBeforeOffset(sql);
            patched = FETCH_NEXT_ZERO.matcher(patched)
                .replaceAll("OFFSET $1 ROWS FETCH NEXT 1 ROWS ONLY");
            SystemMetaObject.forObject(boundSql).setValue("sql", patched);
            return true;
        }
        String trimmed = sql.trim().replaceAll(";\\s*$", "");
        if (!FETCH_NEXT_PARAM.matcher(trimmed).find()) return false;
        List<ParameterMapping> mappings = boundSql.getParameterMappings();
        if (mappings == null || mappings.isEmpty()) return false;
        ParameterMapping fetchPm = mappings.get(mappings.size() - 1);
        Object val = readParam(boundSql, fetchPm.getProperty());
        if (!(val instanceof Number) || ((Number) val).longValue() != 0L) return false;
        SystemMetaObject.forObject(boundSql).setValue("sql", forceEmptyBeforeOffset(sql));
        writeParam(boundSql, fetchPm.getProperty(), 1);
        return true;
    }

    private static String forceEmptyBeforeOffset(String sql) {
        String patched = sql.replaceFirst("(?i)\\bORDER\\s+BY\\b", "AND 1 = 0 ORDER BY");
        if (!patched.equals(sql)) return patched;
        return sql.replaceFirst("(?i)(\\s+OFFSET\\s+)", " AND 1 = 0$1");
    }

    private static Object readParam(BoundSql boundSql, String prop) {
        try {
            if (boundSql.hasAdditionalParameter(prop)) {
                return boundSql.getAdditionalParameter(prop);
            }
            Object po = boundSql.getParameterObject();
            if (po == null) return null;
            MetaObject meta = SystemMetaObject.forObject(po);
            if (meta.hasGetter(prop)) return meta.getValue(prop);
            if (meta.hasGetter("pageSize")) return meta.getValue("pageSize");
        } catch (Exception ignored) { }
        return null;
    }

    private static void writeParam(BoundSql boundSql, String prop, Object value) {
        try {
            if (boundSql.hasAdditionalParameter(prop)) {
                boundSql.setAdditionalParameter(prop, value);
            }
            Object po = boundSql.getParameterObject();
            if (po == null) return;
            MetaObject meta = SystemMetaObject.forObject(po);
            if (meta.hasSetter(prop)) meta.setValue(prop, value);
            else if (meta.hasSetter("pageSize")) meta.setValue("pageSize", value);
        } catch (Exception ignored) { }
    }

    @Override
    public Object plugin(Object target) {
        return Plugin.wrap(target, this);
    }

    @Override
    public void setProperties(Properties properties) { }
}
```

### 步骤 3.4 注册 Bean：`ExtDbAutoConfiguration.java`

```java
package com.openjiuwen.studio.ext;

import org.apache.ibatis.mapping.DatabaseIdProvider;
import org.apache.ibatis.plugin.Interceptor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

@Configuration
public class ExtDbAutoConfiguration {

    @Bean
    @Primary
    public DatabaseIdProvider extDatabaseIdProvider() {
        return new ExtJdbcUrlDatabaseIdProvider();
    }

    @Bean
    public Interceptor vendorSqlRewriteInterceptor() {
        return new VendorSqlRewriteInterceptor();
    }
}
```

### 步骤 3.5 Spring Boot 自动装配清单

创建 `studio-db-ext/src/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`，内容**只有一行**：

```text
com.openjiuwen.studio.ext.ExtDbAutoConfiguration
```

### 步骤 3.6 外部 Mapper（处理 Interceptor 不好改的整段 SQL）

Interceptor 改不了或不适合改的语句（典型：`FROM_UNIXTIME`），用**同 namespace、同 id、带 `databaseId="sqlserver"`** 的外部 XML 覆盖。

1. 在 `studio-db-ext/mapper/` 新建例如 `AgentMapperSqlServer.xml`（核心是把 `FROM_UNIXTIME(updated_at/1000)` 写成 `DATEADD(...)`）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
  "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.openjiuwen.studio.agent.manager.mapper.AgentMapper">
  <!-- 与产品内置语句同 id；仅当 DatabaseIdProvider 返回 sqlserver 时选用 -->
  <select id="selectByProjectIdAndSearchKey" databaseId="sqlserver"
          resultType="com.openjiuwen.studio.agent.manager.dto.AgentApplicationInfo">
    SELECT * FROM (
      SELECT agent_id AS id, name, icon, description, type, workspace_id,
             updated_on AS updated_at, prologue
      FROM t_agent
      WHERE project_id = #{projectId,jdbcType=VARCHAR} AND deleted = 0
      UNION ALL
      SELECT id, name, avatar AS icon, description, workflow_type AS type, workspace_id,
             DATEADD(SECOND, CAST(updated_at / 1000 AS INT),
                     CAST('1970-01-01' AS datetime2)) AS updated_at,
             NULL AS prologue
      FROM t_agent_workflow
      WHERE project_id = #{projectId,jdbcType=VARCHAR}
        AND (deleted IS NULL OR deleted = 0)
    ) t
    ORDER BY updated_at DESC
    OFFSET 0 ROWS FETCH NEXT 100 ROWS ONLY
  </select>
</mapper>
```

> 上面是**形态示例**；完整条件分支请对照产品内置同名语句补齐，或先跑通主链路再按日志缺啥补啥。

2. 评分 upsert（`ON DUPLICATE KEY UPDATE`）文档第 3.3 节 Interceptor 已对 `ws_mcp_server_rating` 做 MERGE 兜底；也可再放一份 `McpServerRatingMapperSqlServer.xml`（`insertRating` + `databaseId="sqlserver"`）双保险。

3. **加载顺序**：外部 XML 必须排在内置 `classpath*:mapper/**/*.xml` **之前**（见第 5 节 `mybatis.mapper-locations`），否则可能 duplicate statement id。

---

## 4. 编译打 jar

在 `studio-db-ext` 目录执行（按你本机 jar 文件名改 classpath）：

```bash
cd studio-db-ext

# 编译（Linux / macOS：classpath 用冒号 :）
javac --release 17 \
  -cp "lib/mybatis-3.5.17.jar:lib/spring-context-6.2.8.jar:lib/spring-beans-6.2.8.jar:lib/spring-core-6.2.8.jar:lib/spring-jcl-6.2.8.jar" \
  -d classes \
  src/com/openjiuwen/studio/ext/*.java

# Windows（cmd）把上面 -cp 里的冒号改成分号，例如：
# -cp "lib\mybatis-3.5.17.jar;lib\spring-context-6.2.8.jar;..."

# 拷贝 AutoConfiguration 清单进 classes
mkdir -p classes/META-INF/spring
cp src/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports \
   classes/META-INF/spring/

# 拷贝外部 Mapper（目录名须与第 5 节 mapper-locations 一致）
mkdir -p classes/ext-mapper
cp mapper/*.xml classes/ext-mapper/ 2>/dev/null || true

# 打包
jar cf ext/studio-db-ext.jar -C classes .

# 自检
jar tf ext/studio-db-ext.jar | head
```

确认 jar 内同时有：

- `com/openjiuwen/studio/ext/*.class`
- `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
- （若做了 3.6）`ext-mapper/*.xml`

---

## 5. 写配置 profile

创建 `studio-db-ext/config/application-sqlserver.yml`：

```yaml
spring:
  main:
    allow-bean-definition-overriding: true
  sql:
    init:
      mode: never          # 建议先手工/脚本建表，再启动
      continue-on-error: true
  jpa:
    database-platform: org.hibernate.dialect.SQLServerDialect
    properties:
      hibernate:
        dialect: org.hibernate.dialect.SQLServerDialect
  quartz:
    properties:
      org:
        quartz:
          jobStore:
            driverDelegateClass: org.quartz.impl.jdbcjobstore.MSSQLDelegate

# 外部 Mapper 必须排在内置之前
mybatis:
  mapper-locations:
    - classpath:ext-mapper/*.xml
    - classpath*:mapper/*.xml
    - classpath*:mapper/**/*.xml

pagehelper:
  helper-dialect: sqlserver
  reasonable: true
```

达梦 / Oracle：把 `hibernate.dialect`、`pagehelper.helper-dialect`、Quartz `driverDelegateClass` 换成厂商文档推荐值；外部 Mapper 的 `databaseId` 与 `ExtJdbcUrlDatabaseIdProvider` 返回值保持一致。

---

## 6. 准备 DDL

### 6.1 从哪里来

产品自带的是 **MySQL 版**建表脚本，通常在 manager 安装包 / 镜像资源里：

| 文件（产品内路径） | 内容 |
|---|---|
| `sql/ddl.sql`（classpath） | manager 业务表 + 常见含 QRTZ |
| `sql/knowledge-base/ddl.sql` | 知识库表 |

获取方式（任选）：

1. 向交付方索取上述两份 MySQL DDL  
2. 从已部署的 `studio-manager` 镜像/安装目录中导出对应资源（打在 jar 内时为 `classpath:sql/...`）

拿到后：

1. 按 6.2 翻译成目标库语法  
2. 放到 `studio-db-ext/sql/`（如 `ddl_sqlserver.sql`、`ddl_knowledge_sqlserver.sql`）

> 库名：产品默认部署常见 `agent-builder`；本文示例用 `agentbuilder`。**两者都可，只要建库名与 `spring_datasource_url` 里的库名一致。**
### 6.2 SQL Server 常见替换（对照改）

| MySQL | SQL Server |
|---|---|
| `` `name` `` | `[name]` 或去掉引号 |
| `AUTO_INCREMENT` | `IDENTITY(1,1)` |
| `TINYINT(1)` | `BIT` 或 `TINYINT` |
| `DATETIME` / `TIMESTAMP` | `DATETIME2` |
| `TEXT` / `MEDIUMTEXT` / `LONGTEXT` | `NVARCHAR(MAX)` / `VARCHAR(MAX)` |
| `ENGINE=InnoDB` / `ROW_FORMAT` / `COLLATE=utf8mb4_*` | 删除 |
| `ON UPDATE CURRENT_TIMESTAMP` | 删除或改触发器 |
| `UNIQUE KEY` / `KEY ... USING BTREE` | `CREATE UNIQUE INDEX` / `CREATE INDEX` |
| `CREATE TABLE IF NOT EXISTS` | 用 `IF OBJECT_ID(...) IS NULL CREATE TABLE` 或预执行工具 |

### 6.3 翻译示例（单表对照）

产品 MySQL 原文（节选形态）大致如下：

```sql
CREATE TABLE IF NOT EXISTS `t_common_license_record` (
    `id` varchar(36) NOT NULL,
    `sku_code` varchar(64) NOT NULL,
    `created_date` timestamp NOT NULL,
    PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=Dynamic;
```

按 6.2 翻成 SQL Server 后，写入你的 `sql/ddl_sqlserver.sql`，形态如下：

```sql
IF OBJECT_ID(N'dbo.t_common_license_record', N'U') IS NULL
BEGIN
CREATE TABLE dbo.t_common_license_record (
    id varchar(36) NOT NULL,
    sku_code varchar(64) NOT NULL,
    created_date datetime2 NOT NULL,
    PRIMARY KEY (id)
);
END;
```

对照这一张表实际做了什么：

- 去掉反引号 `` ` ``；需要时可用 `[]`
- `timestamp` → `datetime2`
- 删除 `ENGINE` / `CHARSET` / `COLLATE` / `ROW_FORMAT` / `USING BTREE`
- `CREATE TABLE IF NOT EXISTS` → `IF OBJECT_ID(...) IS NULL` 再 `CREATE TABLE`

> 完整 `ddl_sqlserver.sql` / `ddl_knowledge_sqlserver.sql` 需对产品全部表按同样规则翻译，本文只给形态示例，不附带整份成品脚本。有自增列时另见对照表：`AUTO_INCREMENT` → `IDENTITY(1,1)`（如 `t_sessions`）。

### 6.4 执行顺序建议

```text
1) 创建数据库 agentbuilder
2) 执行 ddl_sqlserver.sql（manager 表 + QRTZ）
3) 执行 ddl_knowledge_sqlserver.sql
4) dml 可先空文件
5) 抽查：表数量、t_sessions 是否 IDENTITY、QRTZ 表是否齐全
```

把空 DML 写成 `sql/dml_empty.sql`（可以只有一行注释）。

> **重要**：启动参数建议 `spring_sql_init_mode=never`，避免启动时半失败半成功。

---

## 7. 启动包装脚本

创建 `studio-db-ext/bin/start-with-ext.sh`（路径按镜像实际调整）：

```bash
#!/bin/bash
set -euo pipefail

APP_PATH=${APP_PATH:-/opt/cloud/studio-manager}
EXT_DIR=${EXT_DIR:-/opt/ext}
ACTIVE_PROFILES="${ACTIVE_PROFILES:-manager,sqlserver}"
APP_JAR="${APP_PATH}/app/studio-manager.jar"
LOADER_PATH="${EXT_DIR}/ext,${EXT_DIR}/lib"

echo "INFO: loader.path=${LOADER_PATH}"
echo "INFO: profiles=${ACTIVE_PROFILES}"
ls -la "${EXT_DIR}/ext" "${EXT_DIR}/lib" || true

exec java -Xms512m -Xmx2048m \
  -Dfile.encoding=UTF-8 \
  -Dloader.path="${LOADER_PATH}" \
  -cp "${APP_JAR}" \
  org.springframework.boot.loader.launch.PropertiesLauncher \
  --spring.config.additional-location="${APP_PATH}/config/,optional:${EXT_DIR}/config/" \
  --spring.profiles.active="${ACTIVE_PROFILES}" \
  --logging.config="${APP_PATH}/config/log4j2.xml"
```

```bash
chmod +x studio-db-ext/bin/start-with-ext.sh
```

**禁止**再用裸 `java -jar studio-manager.jar`，否则扩展包进不了类路径。

---

## 8. 接到运行中的 manager

### 方式 A：Docker Compose overlay（推荐）

在原 compose 旁增加 overlay 文件，例如 `docker-compose.db-ext.yml`：

```yaml
services:
  studio-manager:
    volumes:
      - /绝对路径/studio-db-ext:/opt/ext:ro
    entrypoint: ["/bin/bash", "/opt/ext/bin/start-with-ext.sh"]
    environment:
      EXT_DIR: /opt/ext
      ACTIVE_PROFILES: manager,sqlserver
      spring_datasource_url: jdbc:sqlserver://<db-host>:1433;databaseName=agentbuilder;encrypt=false;trustServerCertificate=true
      spring_datasource_username: sa
      spring_datasource_password: "<your-password>"
      spring_datasource_driver_class_name: com.microsoft.sqlserver.jdbc.SQLServerDriver
      spring_sql_init_mode: never
      spring_sql_manager_ddl: file:/opt/ext/sql/ddl_sqlserver.sql
      spring_sql_knowledge_ddl: file:/opt/ext/sql/ddl_knowledge_sqlserver.sql
      spring_sql_manager_dml: file:/opt/ext/sql/dml_empty.sql
      spring_sql_knowledge_dml: file:/opt/ext/sql/dml_empty.sql
      org_quartz_jobStore_driverDelegateClass: org.quartz.impl.jdbcjobstore.MSSQLDelegate
      SPRING_MAIN_ALLOW_BEAN_DEFINITION_OVERRIDING: "true"
```

然后：

```bash
docker compose -f docker-compose.yml -f docker-compose.db-ext.yml \
  up -d --no-deps --pull never --force-recreate studio-manager
```

### 方式 B：已有进程

1. 把 `studio-db-ext` 放到机器固定目录  
2. 用 `start-with-ext.sh` 替换原启动命令  
3. 注入同上环境变量  

---

## 9. 验收（按顺序勾）

把 `<host>`、`<token>`、`<workspace_id>` 换成你的环境。

### 9.1 启动与方言

```bash
# 健康检查
curl -sk http://<host>:31111/health
# 期望：200

# 日志应出现
# [ExtJdbc] detected SQL Server -> sqlserver
# 以及 Hibernate SQLServerDialect / Quartz MSSQLDelegate（视配置）
docker logs <manager容器> 2>&1 | grep -E 'ExtJdbc|SQLServerDialect|MSSQLDelegate|Started'
```

### 9.2 登录 / Token（simple-auth 部署）

```bash
curl -sk 'http://<host>:31111/auth/token?user_id=testUser&project_id=0'
# 期望：{"auth_token":"testUser|0"}
TOKEN=testUser|0
```

### 9.3 主链路列表（注意参数）

```bash
WS=<你的workspace_id>

# Agent / 工作流：用 limit/offset
curl -sk -H "X-Auth-Token: $TOKEN" \
  "http://<host>:31111/v1/0/agent-manager/agents?workspace_id=$WS&limit=1&offset=0"

curl -sk -H "X-Auth-Token: $TOKEN" \
  "http://<host>:31111/v1/0/agent-manager/workflows?workspace_id=$WS&limit=2&offset=0"

# 知识库：必须是带 project_id 的正确路径
curl -sk -H "X-Auth-Token: $TOKEN" \
  "http://<host>:31111/v2/0/agent-manager/knowledge-bases?workspace_id=$WS&limit=10&offset=0"

# 提示词任务
curl -sk -H "X-Auth-Token: $TOKEN" \
  "http://<host>:31111/v2/0/prompt/tasks?workspace_id=$WS&limit=10&offset=0"
```

期望均为 **HTTP 200**（列表可为空，但不能是方言 SQL 500）。

### 9.4 分页

同一列表 `limit=2&offset=0` 与 `limit=2&offset=2`，条数截断且两页 ID 不重叠。

### 9.5 导入导出

1. 创建或选定一个 `workflow_id`  
2. `POST .../workflows/export` 得到 jsonl  
3. `POST .../workflows/import?import_workflows=<该workflow_id>&import_tools=` 上传文件  
4. 期望 `succeed_len >= 1`  

> `import_workflows` 填 **ID**，不要填 `true`。

### 9.6 会话表 IDENTITY（可选但建议）

用 JDBC 对 `t_sessions` 做插入并 `getGeneratedKeys`，确认能取到自增主键。

### 9.7 MCP 评分 upsert（`ON DUPLICATE` → MERGE）

产品里带 `ON DUPLICATE KEY UPDATE` 的典型路径是 MCP 评分。库中先有一条可评分的 MCP server 记录后：

```bash
# 第一次：插入
curl -sk -X POST -H "X-Auth-Token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"server_id":"<mcp_server_id>","score":"4"}' \
  "http://<host>:31111/v1/0/mcp/server/rating?workspace_id=$WS"
# 期望：HTTP 200

# 第二次：更新同一 (server_id, tenant) ，仍应成功且库中只有 1 行
curl -sk -X POST -H "X-Auth-Token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"server_id":"<mcp_server_id>","score":"9"}' \
  "http://<host>:31111/v1/0/mcp/server/rating?workspace_id=$WS"
# 期望：HTTP 200；查 ws_mcp_server_rating 该 server 仅 1 行且 score=9
```

若报 `ON DUPLICATE` 语法错误：检查 Interceptor 的 `rewriteOnDuplicateKeyUpdate` 是否进 jar，或补外部 `McpServerRatingMapperSqlServer.xml`。

### 9.8 回滚

去掉 overlay / 恢复原环境变量与原 `entrypoint`，确认仍能连回原库并 `health=200`。

### 9.9 建议顺带确认（非阻塞）

| 项 | 做法 |
|---|---|
| Quartz 方言 | 日志出现 `MSSQLDelegate`；`QRTZ_SCHEDULER_STATE` 有签到行 |
| 列表参数 | 分页用 `limit`/`offset`；不要用 `page_size` 当截断依据 |
| 工作流 DELETE | 若失败且日志含 `UUID()`，确认已改写为 `NEWID()` |

---

## 10. 出问题怎么办（按日志对）

| 现象 | 处理 |
|---|---|
| 启动了但扩展没生效 | 是否仍用 `java -jar`？改为 PropertiesLauncher；检查 `loader.path`、jar 内 AutoConfiguration 清单 |
| `Invalid column name 'false'` | Interceptor 未加载或未改写布尔；查日志是否有 `[VendorSqlRewrite]` |
| `` Incorrect syntax near '`' `` | 补反引号改写 |
| `UUID()` 相关失败 | 确认 `UUID()`→目标库函数已写入 `rewrite()` |
| `FETCH NEXT 0` | 确认 `clampZeroFetch` 生效 |
| `FROM_UNIXTIME` / 日期函数报错 | Interceptor 一般不改；补外部 Mapper（步骤 3.6）并用 `DATEADD`；检查 `mapper-locations` 外部是否排在前面 |
| `ON DUPLICATE KEY UPDATE` 语法错 | 确认 `rewriteOnDuplicateKeyUpdate` 对 `ws_mcp_server_rating` 生效，或加外部 MERGE Mapper |
| `FOR UPDATE` 语法错 | 不要指望 Interceptor 自动改写裸 MySQL `FOR UPDATE`；定时任务依赖 Quartz `MSSQLDelegate`；业务 SQL 改用 `WITH (UPDLOCK)` 等目标库写法（外部 Mapper） |
| duplicate statement id | 外部 `databaseId` Mapper 与加载顺序：外部路径必须在内置 mapper 之前 |
| 导入一直 0 成功 | `import_*=` 改成真实资源 ID |
| 知识库 400 项目 ID | 换正确带 `{project_id}` 的 URL |
| 表缺失但进程起来了 | `continue-on-error` 吞错；改用预建表 + `init_mode=never` |
| 带插件导出缺版本 | 同步工具/版本元数据表，不是方言问题 |
| Windows 编译找不到类 | `-cp` 分隔符用 `;`，不要用 Linux 的 `:` |

每出现一次 SQL 500：从 manager 日志复制完整 SQL → 在 Interceptor 增加一条改写规则 **或** 增加外部 Mapper → 重新编译打包 → 重启。

---

## 11. 换到达梦 / Oracle（同一套流程）

只改下列几处，其余步骤不变（**没有**像 SQL Server 那样整份可粘贴的完整 `rewrite()` / DDL）：

1. **`ExtJdbcUrlDatabaseIdProvider`**：确保 URL 返回 `dm` / `oracle`  
2. **`VendorSqlRewriteInterceptor.rewrite()`**：  
   - LIMIT → 达梦可保留或按文档；Oracle 常用 `FETCH FIRST` / `OFFSET…FETCH`  
   - 引号、`UUID()`/`SYS_GUID()`、布尔、`ON DUPLICATE` 等按厂商改  
3. **外部 Mapper**：`databaseId` 与上一步返回值一致  
4. **profile**：驱动类、Hibernate dialect、PageHelper、Quartz delegate、DDL 翻译规则  

验收 Checklist 与第 9 节相同。

---

## 12. 交付物清单

做完后你应能交出：

1. `ext/studio-db-ext.jar`（含 class、AutoConfiguration；若有则含 `ext-mapper/*.xml`）  
2. `lib/<jdbc-driver>.jar`  
3. `config/application-<vendor>.yml`（含 `mybatis.mapper-locations`）  
4. `sql/ddl_*.sql`（已在目标库执行成功）  
5. `bin/start-with-ext.sh` + compose/环境变量说明  
6. 第 9 节验收截图或请求日志（health / 列表 200 / 导入导出 / 评分 upsert） 

---

## 附录：开放配置项速查

| 配置项 | 作用 |
|---|---|
| `spring_datasource_url` | JDBC URL |
| `spring_datasource_username` / `password` | 账号密码 |
| `spring_datasource_driver_class_name` | 驱动类 |
| `spring_sql_manager_ddl` / `knowledge_ddl` | DDL 文件 |
| `spring_sql_manager_dml` / `knowledge_dml` | DML 文件 |
| `spring_sql_init_mode` | `always` / `never` |
| `org_quartz_jobStore_driverDelegateClass` | Quartz 方言 |
| `pagehelper.helper-dialect` | 分页方言 |
| `spring.jpa.properties.hibernate.dialect` | JPA 方言 |
| `spring.profiles.active` | 如 `manager,sqlserver` |
| `spring.config.additional-location` | 外部 config 目录 |
| `-Dloader.path` | 扩展 jar + 驱动目录 |
| `mybatis.mapper-locations` | 外部 Mapper 路径（须排在内置之前） |
